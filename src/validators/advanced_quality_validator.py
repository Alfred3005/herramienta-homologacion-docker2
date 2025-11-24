"""
Advanced Quality Validator - Análisis Holístico Inteligente v5.36

Validador único que analiza el puesto COMPLETO en una sola llamada LLM para detectar:
1. Duplicación semántica entre funciones
2. Funciones malformadas/vacías/sin sentido
3. Problemas de marco legal (organismos extintos, leyes obsoletas)
4. Problemas de objetivo general (longitud, claridad, finalidad)

Filosofía: Un LLM viendo TODO el contexto puede detectar problemas mejor
que múltiples validadores viendo fragmentos.

MEJORAS v5.36:
- Límites de objetivo relajados: 30-800 chars (antes 50-500)
- Tolerancia para objetivos extensos en puestos de alto nivel (500-700 chars es NORMAL)
- Severidades más graduales para problemas de objetivo
- Guidance específica para evitar falsos positivos en Secretarías/Subsecretarías

Autor: Claude Code
Fecha: 2025-11-11
Versión: 5.36 (tolerante con objetivos de alto nivel)
"""

import logging
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

from src.validators.shared_utilities import APFContext, robust_openai_call

logger = logging.getLogger(__name__)


@dataclass
class QualityValidationResult:
    """Resultado completo de validación de calidad"""
    duplicacion: Dict[str, Any]
    malformacion: Dict[str, Any]
    marco_legal: Dict[str, Any]
    objetivo_general: Dict[str, Any]

    # Metadata
    total_flags: int
    flags_critical: int
    flags_high: int
    flags_moderate: int
    flags_low: int


class AdvancedQualityValidator:
    """
    Validador avanzado que analiza calidad del puesto en una sola pasada.

    Ventajas:
    - 1 llamada LLM vs 4+ (más eficiente y económico)
    - Contexto completo del puesto (mejor análisis)
    - Detecta patrones globales y correlaciones
    """

    def __init__(self, context: APFContext):
        """
        Inicializa el validador.

        Args:
            context: APFContext con API keys y configuración
        """
        self.context = context
        logger.info("[AdvancedQualityValidator] Inicializado con análisis holístico v5.33")

    def validate_puesto_completo(
        self,
        puesto_data: Dict[str, Any],
        normativa_text: Optional[str] = None
    ) -> QualityValidationResult:
        """
        Analiza el puesto COMPLETO y detecta todos los problemas de calidad.

        Args:
            puesto_data: Diccionario con datos completos del puesto
                {
                    "codigo": str,
                    "denominacion": str,
                    "nivel_salarial": str,
                    "objetivo_general": str,
                    "funciones": List[Dict]
                }
            normativa_text: Texto completo de normativa institucional (opcional)

        Returns:
            QualityValidationResult con todos los flags detectados
        """
        logger.info(f"[AdvancedQualityValidator] Analizando puesto {puesto_data.get('codigo', 'UNKNOWN')}")

        # Construir prompt inteligente
        prompt = self._build_analysis_prompt(puesto_data, normativa_text)

        # Construir prompt completo con system message
        full_prompt = """Eres un auditor experto de la Administración Pública Federal de México. Tu tarea es analizar puestos de trabajo y detectar problemas de calidad de manera exhaustiva y precisa.

""" + prompt

        # Llamar a LLM con robust_openai_call
        try:
            response = robust_openai_call(
                prompt=full_prompt,
                model="openai/gpt-4o-mini",  # Migrado a GPT-4o-mini (ahorro 94.6%)
                temperature=0.1,  # Baja para consistencia
                max_tokens=3000,  # Aumentar para respuesta JSON completa
                context=self.context
            )

            # Parsear respuesta de robust_openai_call
            if response.get("status") == "success":
                result_dict = response.get("data")
                # Convertir a dataclass
                return self._parse_llm_response(result_dict)
            else:
                # Error en la llamada LLM
                error_msg = response.get("error", "Error desconocido")
                logger.error(f"[AdvancedQualityValidator] Error en llamada LLM: {error_msg}")
                raise Exception(f"Error en llamada LLM: {error_msg}")

        except Exception as e:
            logger.error(f"[AdvancedQualityValidator] Error en análisis: {e}")
            # Retornar resultado vacío en caso de error
            return QualityValidationResult(
                duplicacion={"tiene_duplicados": False, "total_duplicados": 0, "pares_duplicados": []},
                malformacion={"tiene_malformadas": False, "total_malformadas": 0, "funciones_problematicas": []},
                marco_legal={"tiene_problemas": False, "total_problemas": 0, "problemas": []},
                objetivo_general={"es_adecuado": True, "calificacion": 1.0, "problemas": []},
                total_flags=0,
                flags_critical=0,
                flags_high=0,
                flags_moderate=0,
                flags_low=0
            )

    def _build_analysis_prompt(self, puesto_data: Dict[str, Any], normativa_text: Optional[str]) -> str:
        """Construye el prompt de análisis holístico"""

        codigo = puesto_data.get("codigo", "N/A")
        denominacion = puesto_data.get("denominacion", "N/A")
        nivel = puesto_data.get("nivel_salarial", "N/A")
        objetivo = puesto_data.get("objetivo_general", "")
        funciones = puesto_data.get("funciones", [])

        # Preparar lista de funciones para análisis
        funciones_text = ""
        for i, func in enumerate(funciones, 1):
            desc = func.get("descripcion_completa", func.get("descripcion", ""))
            verbo = func.get("verbo_accion", "")
            funciones_text += f"{i}. [{verbo}] {desc}\n"

        # Preparar contexto normativo (si existe)
        normativa_context = ""
        if normativa_text:
            # Truncar normativa a ~2000 chars para no exceder tokens
            normativa_context = f"\n**NORMATIVA INSTITUCIONAL:**\n{normativa_text[:2000]}\n"

        prompt = f"""
Analiza EXHAUSTIVAMENTE este puesto de trabajo de la Administración Pública Federal y detecta TODOS los problemas de calidad.

════════════════════════════════════════════════════════════════════════════════
📋 DATOS DEL PUESTO
════════════════════════════════════════════════════════════════════════════════

**Código:** {codigo}
**Denominación:** {denominacion}
**Nivel Salarial:** {nivel}

**OBJETIVO GENERAL:**
{objetivo}

**FUNCIONES ({len(funciones)} total):**
{funciones_text}
{normativa_context}

════════════════════════════════════════════════════════════════════════════════
🔍 INSTRUCCIONES DE ANÁLISIS
════════════════════════════════════════════════════════════════════════════════

Detecta los siguientes problemas de calidad:

### 1. DUPLICACIÓN SEMÁNTICA
Analiza TODAS las funciones y compara entre sí para detectar:
- Funciones que describen la misma actividad con palabras diferentes
- Funciones con >80% de similitud semántica
- Redundancias obvias (mismo verbo + objeto similar)

**IMPORTANTE:** Compara TODAS contra TODAS. Si hay 10 funciones, debes comparar 45 pares.

### 2. FUNCIONES MALFORMADAS
Detecta funciones que tengan:
- **VACÍAS**: Sin contenido o solo espacios
- **PLACEHOLDERS**: Contienen solo "...", "N/A", "xxx", etc.
- **MUY CORTAS**: Menos de 15 caracteres (probablemente incompletas)
- **SIN VERBO**: No inician con un verbo de acción
- **SIN COMPLEMENTO**: Solo verbo sin especificar QUÉ se hace
- **SIN RESULTADO**: No explican PARA QUÉ se hace (finalidad)
- **TEXTO SIN SENTIDO**: Palabras aleatorias, caracteres incoherentes

### 3. PROBLEMAS DE MARCO LEGAL
Analiza referencias legales y detecta:
- **ORGANISMOS EXTINTOS**: Referencias a instituciones que ya no existen (ej: CONACYT reorganizado)
- **LEYES OBSOLETAS**: Referencias a leyes derogadas o reformadas
- **REFERENCIAS INVÁLIDAS**: Artículos que ya no existen
- **INCONSISTENCIAS**: Conflictos entre referencias legales

Si se proporciona normativa institucional, valida que las funciones estén alineadas con ella.

### 4. OBJETIVO GENERAL
Evalúa si el objetivo general es adecuado:
- **MUY CORTO**: <30 caracteres (extremadamente incompleto)
- **MUY LARGO**: >800 caracteres (excesivamente verboso - puestos de alto nivel pueden tener objetivos extensos)
- **SIN VERBO**: No tiene verbo rector claro al inicio
- **SIN FINALIDAD**: No explica el PARA QUÉ del puesto (cláusula con "a fin de", "para", "con el objetivo de")
- **GENÉRICO**: Demasiado vago o aplicable a cualquier puesto
- **INCOHERENTE**: No corresponde a la denominación del puesto

**IMPORTANTE**: Puestos de alto nivel (Secretarías, Subsecretarías) típicamente tienen objetivos más extensos y detallados.
Sé TOLERANTE con objetivos de 200-700 caracteres si están bien estructurados y son coherentes con el nivel del puesto.

════════════════════════════════════════════════════════════════════════════════
📤 FORMATO DE RESPUESTA
════════════════════════════════════════════════════════════════════════════════

Retorna un JSON con la siguiente estructura EXACTA:

{{
  "duplicacion": {{
    "tiene_duplicados": boolean,
    "total_duplicados": int,
    "pares_duplicados": [
      {{
        "funcion_1_id": int,
        "funcion_2_id": int,
        "similitud_porcentaje": int (0-100),
        "descripcion": "string explicando POR QUÉ son similares",
        "sugerencia": "string con recomendación"
      }}
    ]
  }},
  "malformacion": {{
    "tiene_malformadas": boolean,
    "total_malformadas": int,
    "funciones_problematicas": [
      {{
        "funcion_id": int,
        "problemas": [
          {{
            "tipo": "string (VACIA|PLACEHOLDER|MUY_CORTA|SIN_VERBO|SIN_COMPLEMENTO|SIN_RESULTADO|SIN_SENTIDO)",
            "severidad": "string (CRITICAL|HIGH|MODERATE|LOW)",
            "descripcion": "string explicando el problema",
            "texto_problematico": "string con fragmento del texto (max 100 chars)"
          }}
        ]
      }}
    ]
  }},
  "marco_legal": {{
    "tiene_problemas": boolean,
    "total_problemas": int,
    "problemas": [
      {{
        "tipo": "string (ORGANISMO_EXTINTO|LEY_OBSOLETA|REFERENCIA_INVALIDA|INCONSISTENCIA)",
        "severidad": "string (CRITICAL|HIGH|MODERATE|LOW)",
        "descripcion": "string explicando el problema detectado",
        "referencia_problematica": "string con texto específico",
        "sugerencia": "string con recomendación de corrección"
      }}
    ]
  }},
  "objetivo_general": {{
    "es_adecuado": boolean,
    "calificacion": float (0.0-1.0),
    "problemas": [
      {{
        "tipo": "string (MUY_CORTO|MUY_LARGO|SIN_VERBO|SIN_FINALIDAD|GENERICO|INCOHERENTE)",
        "severidad": "string (CRITICAL|HIGH|MODERATE|LOW)",
        "descripcion": "string explicando el problema"
      }}
    ]
  }}
}}

════════════════════════════════════════════════════════════════════════════════
⚠️ IMPORTANTE
════════════════════════════════════════════════════════════════════════════════

1. SÉ EXHAUSTIVO: Revisa cada función detenidamente
2. SÉ ESPECÍFICO: Explica claramente POR QUÉ algo es un problema
3. SÉ PRECISO: Usa los IDs correctos de las funciones (1-indexed)
4. SÉ CONSERVADOR: Si no estás seguro, NO lo marques como problema
5. RETORNA JSON VÁLIDO: Sin comentarios, sin trailing commas

**CRITERIOS DE SEVERIDAD PARA OBJETIVO GENERAL:**
- CRITICAL: Solo si el objetivo está completamente vacío o es incomprensible
- HIGH: Solo si falta verbo rector O finalidad (pero no ambos)
- MODERATE: Si es muy largo (>800 chars) o genérico pero funcional
- LOW: Si es largo (500-800 chars) pero bien estructurado y coherente

**SÉ TOLERANTE**: Un objetivo de 500-700 caracteres en un puesto de Secretaría/Subsecretaría
es NORMAL y APROPIADO. NO lo marques como problema a menos que sea realmente excesivo (>800).

Si NO encuentras problemas en alguna categoría, retorna arrays vacíos:
- "pares_duplicados": []
- "funciones_problematicas": []
- "problemas": []

════════════════════════════════════════════════════════════════════════════════

**FORMATO DE SALIDA:**
RETORNA ÚNICAMENTE UN OBJETO JSON VÁLIDO CON LA ESTRUCTURA ESPECIFICADA ARRIBA.
NO incluyas texto adicional, comentarios, ni markdown.
SOLO el JSON puro.

Procede con el análisis:
"""

        return prompt

    def _parse_llm_response(self, result_dict: Dict[str, Any]) -> QualityValidationResult:
        """Parsea la respuesta del LLM y crea el resultado"""

        # Extraer secciones
        duplicacion = result_dict.get("duplicacion", {})
        malformacion = result_dict.get("malformacion", {})
        marco_legal = result_dict.get("marco_legal", {})
        objetivo = result_dict.get("objetivo_general", {})

        # Asegurar estructura mínima
        if not isinstance(duplicacion, dict):
            duplicacion = {"tiene_duplicados": False, "total_duplicados": 0, "pares_duplicados": []}
        if not isinstance(malformacion, dict):
            malformacion = {"tiene_malformadas": False, "total_malformadas": 0, "funciones_problematicas": []}
        if not isinstance(marco_legal, dict):
            marco_legal = {"tiene_problemas": False, "total_problemas": 0, "problemas": []}
        if not isinstance(objetivo, dict):
            objetivo = {"es_adecuado": True, "calificacion": 1.0, "problemas": []}

        # Contar flags por severidad
        all_problems = []

        # Duplicados (siempre MODERATE)
        for dup in duplicacion.get("pares_duplicados", []):
            all_problems.append({"severidad": "MODERATE"})

        # Malformadas
        for func_prob in malformacion.get("funciones_problematicas", []):
            for prob in func_prob.get("problemas", []):
                all_problems.append({"severidad": prob.get("severidad", "MODERATE")})

        # Marco legal
        for prob in marco_legal.get("problemas", []):
            all_problems.append({"severidad": prob.get("severidad", "HIGH")})

        # Objetivo
        for prob in objetivo.get("problemas", []):
            all_problems.append({"severidad": prob.get("severidad", "MODERATE")})

        # Contar por severidad
        flags_critical = sum(1 for p in all_problems if p["severidad"] == "CRITICAL")
        flags_high = sum(1 for p in all_problems if p["severidad"] == "HIGH")
        flags_moderate = sum(1 for p in all_problems if p["severidad"] == "MODERATE")
        flags_low = sum(1 for p in all_problems if p["severidad"] == "LOW")

        return QualityValidationResult(
            duplicacion=duplicacion,
            malformacion=malformacion,
            marco_legal=marco_legal,
            objetivo_general=objetivo,
            total_flags=len(all_problems),
            flags_critical=flags_critical,
            flags_high=flags_high,
            flags_moderate=flags_moderate,
            flags_low=flags_low
        )


# Testing
if __name__ == "__main__":
    # Ejemplo de uso
    from src.validators.shared_utilities import APFContext

    context = APFContext()
    validator = AdvancedQualityValidator(context)

    # Puesto de prueba con problemas obvios
    puesto_test = {
        "codigo": "TEST-001",
        "denominacion": "Puesto de Prueba",
        "nivel_salarial": "H",
        "objetivo_general": "Hacer cosas",  # MUY CORTO
        "funciones": [
            {"id": 1, "verbo_accion": "Dirigir", "descripcion_completa": "Dirigir las actividades del área"},
            {"id": 2, "verbo_accion": "Coordinar", "descripcion_completa": "Coordinar las actividades del área"},  # DUPLICADO
            {"id": 3, "verbo_accion": "", "descripcion_completa": "..."},  # PLACEHOLDER
            {"id": 4, "verbo_accion": "Aplicar", "descripcion_completa": "Aplicar la Ley Extinta de CONACYT"}  # LEY OBSOLETA
        ]
    }

    result = validator.validate_puesto_completo(puesto_test)

    print("=== RESULTADOS ===")
    print(f"Total flags: {result.total_flags}")
    print(f"  CRITICAL: {result.flags_critical}")
    print(f"  HIGH: {result.flags_high}")
    print(f"  MODERATE: {result.flags_moderate}")
    print(f"  LOW: {result.flags_low}")
    print(f"\nDuplicados: {result.duplicacion['total_duplicados']}")
    print(f"Malformadas: {result.malformacion['total_malformadas']}")
    print(f"Problemas legales: {result.marco_legal['total_problemas']}")
    print(f"Objetivo adecuado: {result.objetivo_general['es_adecuado']}")
