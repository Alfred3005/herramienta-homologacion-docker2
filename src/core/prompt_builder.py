"""
PromptBuilder - Construcción de prompts para LLM

Implementa Single Responsibility Principle (SRP):
- Solo responsable de construir prompts optimizados
- No ejecuta llamadas LLM (eso lo hace el provider)
- No valida respuestas (eso lo hace el validator)
"""

from typing import Optional, Dict, Any
from enum import Enum


class ExtractionMode(Enum):
    """Modos de extracción disponibles"""
    FAST = "fast"
    INTELLIGENT = "intelligent"
    THOROUGH = "thorough"


class PromptBuilder:
    """
    Construye prompts optimizados para extracción de información de puestos APF.

    Características:
    - Prompts estructurados con instrucciones claras
    - Múltiples modos de extracción (rápido, inteligente, exhaustivo)
    - Ejemplos incluidos para few-shot learning
    - Validación de estructura de salida
    """

    def __init__(self):
        """Inicializa el constructor de prompts."""
        self._prompt_cache: Dict[str, str] = {}

    def build_extraction_prompt(
        self,
        content: str,
        mode: ExtractionMode = ExtractionMode.INTELLIGENT
    ) -> str:
        """
        Construye prompt para extracción de información de puesto.

        Args:
            content: Contenido del documento a analizar
            mode: Modo de extracción (fast, intelligent, thorough)

        Returns:
            Prompt completo listo para enviar al LLM
        """
        # Usar cache para el prompt base
        cache_key = f"base_{mode.value}"
        if cache_key in self._prompt_cache:
            base_prompt = self._prompt_cache[cache_key]
        else:
            base_prompt = self._build_base_extraction_prompt(mode)
            self._prompt_cache[cache_key] = base_prompt

        # Construir prompt completo con el contenido
        full_prompt = f"""{base_prompt}

**DOCUMENTO A ANALIZAR:**

```
{content}
```

**TU RESPUESTA (JSON válido):**
"""
        return full_prompt

    def build_evaluation_prompt(
        self,
        puesto_data: Dict[str, Any],
        normativa_fragments: list[str]
    ) -> str:
        """
        Construye prompt para evaluación de puesto contra normativa.

        Args:
            puesto_data: Datos extraídos del puesto
            normativa_fragments: Fragmentos de normativa relevantes

        Returns:
            Prompt para evaluación
        """
        prompt = """
Eres un experto en análisis normativo de la Administración Pública Federal (APF) de México.

**TAREA:** Evaluar si las funciones de un puesto están respaldadas por la normativa proporcionada.

**CRITERIOS DE EVALUACIÓN:**

1. **Alineación Directa**: La función está explícitamente mencionada en la normativa
2. **Alineación Derivada**: La función es una derivación lógica de atribuciones generales
3. **Alineación por Ámbito**: La función está dentro del ámbito de competencia del organismo
4. **Desalineación**: La función no tiene respaldo en la normativa proporcionada

**PUESTO A EVALUAR:**

Denominación: {denominacion}
Objetivo: {objetivo}

Funciones:
{funciones}

**NORMATIVA DE REFERENCIA:**

{normativa}

**TU ANÁLISIS (JSON válido):**

Debes responder con un JSON con esta estructura:

```json
{{
  "alineacion_general": "ALIGNED" | "PARTIALLY_ALIGNED" | "NOT_ALIGNED",
  "score": 0.0-1.0,
  "funciones_evaluadas": [
    {{
      "numero": 1,
      "verbo": "conducir",
      "alineacion": "DIRECT" | "DERIVED" | "SCOPE" | "NONE",
      "fragmento_normativo": "texto que respalda la función",
      "confidence": 0.0-1.0,
      "justificacion": "explicación de la evaluación"
    }}
  ],
  "recomendaciones": ["lista de recomendaciones"]
}}
```
"""
        # Formatear puesto
        denominacion = puesto_data.get("identificacion_puesto", {}).get("denominacion_puesto", "N/A")
        objetivo = puesto_data.get("objetivo_general", {}).get("descripcion_completa", "N/A")

        funciones_text = []
        for i, func in enumerate(puesto_data.get("funciones", []), 1):
            funciones_text.append(f"{i}. {func.get('descripcion_completa', 'N/A')}")

        normativa_text = "\n\n---\n\n".join(normativa_fragments[:5])  # Limitar a 5 fragmentos

        return prompt.format(
            denominacion=denominacion,
            objetivo=objetivo,
            funciones="\n".join(funciones_text),
            normativa=normativa_text
        )

    def _build_base_extraction_prompt(self, mode: ExtractionMode) -> str:
        """
        Construye el prompt base para extracción según el modo.

        Args:
            mode: Modo de extracción

        Returns:
            Prompt base
        """
        common_instructions = """
Eres un experto analista de recursos humanos de la Administración Pública Federal (APF) de México.

**TAREA CRÍTICA:** Extraer TODA la información del documento, incluso si está en formatos no convencionales.

**REGLAS FUNDAMENTALES:**
1. **LEE TODO EL DOCUMENTO** - No te detengas en las primeras líneas
2. **SÉ FLEXIBLE CON FORMATOS** - La información puede estar en cualquier parte y con diferentes etiquetas
3. **BUSCA VARIACIONES** - "Puesto:", "Nombre:", "Denominación:", "Nombre del puesto:" son equivalentes
4. **NUNCA DEJES CAMPOS NULL** - Si encuentras información, extráela aunque no sea perfecta
5. **USA INFERENCIA INTELIGENTE** - Si ves "G11", sabes que el nivel es "G"

**PATRONES COMUNES A BUSCAR:**

Para IDENTIFICACIÓN:
- "Puesto:" o "Nombre:" o "Denominación:" → denominacion_puesto
- Cualquier código alfanumérico largo (ej: 38-100-1-M1C035P-0000002) → codigo_puesto
- "Nivel salarial:" o "Nivel:" o códigos como "G11", "M33", "O21" → nivel_salarial
- "Carácter ocupacional:" o "Carácter:" → caracter_ocupacional

Para OBJETIVO:
- "Objetivo General:" o "Objetivo:" o "Propósito:"
- El objetivo suele empezar con un verbo infinitivo (Conducir, Dirigir, Coordinar)

Para FUNCIONES:
- Busca listas numeradas: "Función 1:", "1.", "I.", "a)"
- Busca bloques de texto que empiecen con verbos de acción
- Las funciones pueden tener subnumeración o estar en párrafos

**ESTRUCTURA DEL JSON DE SALIDA:**

```json
{
  "identificacion_puesto": {
    "codigo_puesto": "38-100-1-M1C035P-0000002-E-X-V",
    "denominacion_puesto": "DIRECTOR(A) DE ÁREA",
    "nivel_salarial": {
      "codigo": "M33",
      "descripcion": "Mando Medio"
    },
    "caracter_ocupacional": "Confianza",
    "estatus": "Activo"
  },
  "objetivo_general": {
    "descripcion_completa": "Dirigir y coordinar las actividades...",
    "verbo_accion": "dirigir",
    "objeto_contribucion": "actividades del área",
    "finalidad": "cumplir objetivos institucionales"
  },
  "funciones": [
    {
      "numero": 1,
      "verbo_accion": "coordinar",
      "descripcion_completa": "Coordinar las actividades del área...",
      "que_hace": "coordina actividades",
      "para_que_lo_hace": "para el cumplimiento de objetivos",
      "fundamento_normativo": "Reglamento Interior"
    }
  ]
}
```

**IMPORTANTE:**
- Si NO encuentras un dato específico, usa null SOLO como último recurso
- Para nivel_salarial, extrae CUALQUIER código que parezca un nivel (G11, M33, etc.)
- Para funciones, extrae TODAS las que encuentres, sin importar su formato
- El verbo_accion debe estar en infinitivo minúscula
"""

        mode_specific_instructions = {
            ExtractionMode.FAST: """
**MODO RÁPIDO:** Prioriza velocidad pero NO sacrifiques datos críticos.
- Extrae al menos: denominación, nivel y 3 funciones principales
- Usa inferencia rápida para campos faltantes
""",
            ExtractionMode.INTELLIGENT: """
**MODO INTELIGENTE:** Balance entre precisión y velocidad.
- Extrae TODA la información disponible con validación cruzada
- Si un campo parece incorrecto, verifica dos veces antes de extraer
- Busca patrones y relaciones entre campos
""",
            ExtractionMode.THOROUGH: """
**MODO EXHAUSTIVO:** Máxima precisión y completitud.
- Analiza el documento línea por línea
- Extrae CADA función, incluso subnumeraciones
- Valida coherencia entre campos extraídos
- Busca información en todo el documento
"""
        }

        examples = """
**EJEMPLO DE EXTRACCIÓN EXITOSA:**

Documento:
```
Código: 06-100-1-M1C020P-0000698
Denominación: DIRECTOR(A) DE TRANSPARENCIA
Nivel: M33
Carácter: Confianza

Objetivo General:
Dirigir y coordinar las acciones para garantizar el acceso a la información pública.

Funciones:
1. Coordinar la implementación de políticas de transparencia
2. Supervisar el cumplimiento de normativas aplicables
```

Extracción:
```json
{
  "identificacion_puesto": {
    "codigo_puesto": "06-100-1-M1C020P-0000698",
    "denominacion_puesto": "DIRECTOR(A) DE TRANSPARENCIA",
    "nivel_salarial": {
      "codigo": "M33",
      "descripcion": "Mando Medio"
    },
    "caracter_ocupacional": "Confianza",
    "estatus": null
  },
  "objetivo_general": {
    "descripcion_completa": "Dirigir y coordinar las acciones para garantizar el acceso a la información pública",
    "verbo_accion": "dirigir",
    "objeto_contribucion": "acciones de transparencia",
    "finalidad": "garantizar acceso a información pública"
  },
  "funciones": [
    {
      "numero": 1,
      "verbo_accion": "coordinar",
      "descripcion_completa": "Coordinar la implementación de políticas de transparencia",
      "que_hace": "coordina implementación de políticas",
      "para_que_lo_hace": "para garantizar transparencia",
      "fundamento_normativo": null
    },
    {
      "numero": 2,
      "verbo_accion": "supervisar",
      "descripcion_completa": "Supervisar el cumplimiento de normativas aplicables",
      "que_hace": "supervisa cumplimiento normativo",
      "para_que_lo_hace": "para asegurar legalidad",
      "fundamento_normativo": null
    }
  ]
}
```
"""

        return f"{common_instructions}\n{mode_specific_instructions[mode]}\n{examples}"

    def clear_cache(self):
        """Limpia el cache de prompts."""
        self._prompt_cache.clear()
