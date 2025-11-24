"""
Parser de Descripción de Puesto desde Texto Plano

Extrae automáticamente información estructurada de documentos .txt
usando LLM para identificar: código, denominación, nivel, objetivo, funciones, etc.

Autor: Claude Code v5.29
Fecha: 2025-11-07
"""

import json
import re
from typing import Dict, Any, List, Optional
from litellm import completion


LLM_CONFIG = {
    "model": "openai/gpt-4o-mini",
    "temperature": 0.1,  # Determinístico para parsing
    "max_tokens": 12000,  # Aumentado para soportar ~50+ funciones
}


def parse_puesto_from_text(text_content: str) -> Dict[str, Any]:
    """
    Parsea un documento de texto plano con descripción de puesto
    y extrae información estructurada usando LLM.

    Args:
        text_content: Contenido completo del archivo .txt

    Returns:
        Diccionario con información estructurada del puesto
    """

    prompt = f"""Eres un experto en la Administración Pública Federal (APF) de México.

Tu tarea es extraer información estructurada de la siguiente descripción de puesto.

**IMPORTANTE: Debes extraer TODAS las funciones del documento, sin importar cuántas sean.**

**DOCUMENTO DEL PUESTO:**
```
{text_content[:20000]}  # Aumentado para documentos extensos con 40+ funciones
```

---

**INSTRUCCIONES:**

Extrae la siguiente información del documento. Si algún campo no está presente en el texto, usa null.

1. **Código del Puesto**: Identificador único (ej: "27-100-1-M1C035P-0000661-E-X-V")
2. **Denominación**: Nombre del puesto (ej: "SECRETARIO(A) ANTICORRUPCIÓN Y BUEN GOBIERNO")
3. **Nivel Salarial**: Nivel jerárquico (ej: "G11", "H11", "J11", "K11")
4. **Unidad Responsable**: Código de la unidad (ej: "0" si no se especifica)
5. **Objetivo del Puesto**: Objetivo general o propósito del puesto (párrafo completo)
6. **Funciones**: Lista de TODAS las funciones del puesto (extrae todas sin omitir ninguna). Cada función debe tener:
   - verbo_accion: El verbo principal (ej: "Emitir", "Dirigir", "Coordinar")
   - descripcion_completa: Texto completo de la función
   - complemento: Qué hace (objeto de la acción)
   - resultado: Para qué lo hace (propósito)

**FORMATO DE SALIDA:**

Debes responder ÚNICAMENTE con un JSON válido (sin texto adicional) con esta estructura:

```json
{{
  "codigo": "string o null",
  "denominacion": "string",
  "nivel": "string o null",
  "unidad_responsable": "string",
  "objetivo": "string",
  "funciones": [
    {{
      "verbo_accion": "string",
      "descripcion_completa": "string",
      "complemento": "string",
      "resultado": "string"
    }}
  ],
  "metadatos": {{
    "tiene_codigo": boolean,
    "tiene_nivel": boolean,
    "num_funciones": number,
    "calidad_extraccion": "ALTA|MEDIA|BAJA"
  }}
}}
```

**IMPORTANTE:**
- NO inventes información que no esté en el documento
- Si el código o nivel no están presentes, usa null
- Extrae TODAS las funciones mencionadas
- Cada función debe tener los 4 campos (verbo, descripción, complemento, resultado)
- La descripción_completa es el texto completo sin modificar
- Responde SOLO con el JSON, sin explicaciones adicionales
"""

    try:
        response = completion(
            model=LLM_CONFIG["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=LLM_CONFIG["temperature"],
            max_tokens=LLM_CONFIG["max_tokens"]
        )

        # Extraer JSON de la respuesta
        llm_response = response.choices[0].message.content.strip()

        # Intentar parsear JSON (el LLM debe responder solo JSON)
        # Limpiar markdown code blocks si los hay
        if llm_response.startswith("```json"):
            llm_response = llm_response.replace("```json", "").replace("```", "").strip()
        elif llm_response.startswith("```"):
            llm_response = llm_response.replace("```", "").strip()

        puesto_data = json.loads(llm_response)

        # Validación básica
        if not isinstance(puesto_data, dict):
            raise ValueError("LLM no retornó un diccionario válido")

        if "funciones" not in puesto_data or not isinstance(puesto_data["funciones"], list):
            raise ValueError("Formato de funciones inválido")

        # Añadir campos adicionales para compatibilidad
        puesto_data["origen"] = "TEXT_PARSER"
        puesto_data["raw_text"] = text_content

        return puesto_data

    except json.JSONDecodeError as e:
        raise ValueError(f"Error al parsear JSON del LLM: {str(e)}. Respuesta: {llm_response[:200]}")
    except Exception as e:
        raise RuntimeError(f"Error al parsear documento de puesto: {str(e)}")


def convert_to_sidegor_format(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convierte el formato parseado a formato compatible con el pipeline
    (similar al que se obtiene del Excel Sidegor).

    Args:
        parsed_data: Datos extraídos por parse_puesto_from_text()

    Returns:
        Diccionario en formato Sidegor compatible
    """

    # Construir estructura similar a Sidegor
    sidegor_format = {
        "puesto": {
            "codigo": parsed_data.get("codigo", "UNKNOWN"),
            "denominacion": parsed_data.get("denominacion", ""),
            "nivel_salarial": parsed_data.get("nivel", ""),
            "unidad_responsable": parsed_data.get("unidad_responsable", "0")
        },
        "objetivo": parsed_data.get("objetivo", ""),
        "funciones": []
    }

    # Convertir funciones al formato esperado
    for idx, func in enumerate(parsed_data.get("funciones", []), 1):
        sidegor_format["funciones"].append({
            "id": idx,
            "verbo_accion": func.get("verbo_accion", ""),
            "descripcion_completa": func.get("descripcion_completa", ""),
            "complemento": func.get("complemento", ""),
            "resultado": func.get("resultado", ""),
            "origen": "TEXT_PARSER"
        })

    # Añadir metadatos
    sidegor_format["metadatos"] = {
        "origen": "TEXT_PARSER",
        "num_funciones": len(sidegor_format["funciones"]),
        "calidad_extraccion": parsed_data.get("metadatos", {}).get("calidad_extraccion", "MEDIA")
    }

    return sidegor_format


def parse_and_convert(text_content: str) -> Dict[str, Any]:
    """
    Función de conveniencia que parsea y convierte en un solo paso.

    Args:
        text_content: Contenido del archivo .txt

    Returns:
        Diccionario en formato Sidegor listo para usar en el pipeline
    """

    parsed_data = parse_puesto_from_text(text_content)
    sidegor_format = convert_to_sidegor_format(parsed_data)
    return sidegor_format


# Testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Uso: python text_puesto_parser.py <archivo.txt>")
        sys.exit(1)

    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        content = f.read()

    print("\n🔄 Parseando documento...")
    try:
        result = parse_and_convert(content)
        print("\n✅ Parseo exitoso!")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
