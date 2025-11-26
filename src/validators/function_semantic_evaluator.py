"""
Evaluador Semántico de Funciones - Protocolo SABG v1.1

Implementa análisis contextual de funciones con 5 criterios:
1. Verbo (25%) - ¿Está autorizado para el nivel?
2. Normativa (25%) - ¿Tiene respaldo en reglamento?
3. Estructura (20%) - ¿Tiene VERBO+COMPLEMENTO+RESULTADO?
4. Semántica (20%) - ¿Alineación entre significado función vs normativa?
5. Jerárquica (10%) - ¿Corresponde al nivel del puesto?

Fecha: 2025-11-07
Versión: 5.20 - ANÁLISIS SEMÁNTICO CON LLM
"""

import logging
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

from src.validators.shared_utilities import APFContext, robust_openai_call

logger = logging.getLogger(__name__)


@dataclass
class CriterionScore:
    """Score de un criterio individual"""
    score: float  # 0.0 a 1.0
    reasoning: str
    metadata: Dict[str, Any]


@dataclass
class FunctionEvaluationResult:
    """Resultado de evaluación de una función con 5 criterios"""
    funcion_text: str
    verbo: str

    # Scores por criterio
    criterio_verbo: CriterionScore
    criterio_normativa: CriterionScore
    criterio_estructura: CriterionScore
    criterio_semantica: CriterionScore
    criterio_jerarquica: CriterionScore

    # Score global ponderado
    score_global: float  # 0.0 a 1.0
    clasificacion: str  # APROBADO | OBSERVACION | RECHAZADO
    razonamiento_final: str

    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte a diccionario para serialización COMPLETA.

        OBJETIVO: Máxima transparencia y auditabilidad.
        Documenta CÓMO se evaluó cada criterio y POR QUÉ se dio cada score.
        """
        return {
            # ========== FUNCIÓN EVALUADA (COMPLETA) ==========
            "funcion_text": self.funcion_text,  # ✅ Función completa, sin truncar
            "verbo": self.verbo,

            # ========== SCORES Y RAZONAMIENTO POR CRITERIO ==========
            "criterios": {
                "verbo": {
                    "score": round(self.criterio_verbo.score, 3),
                    "peso": 0.25,
                    "razonamiento": self.criterio_verbo.reasoning,
                    "metadata": self.criterio_verbo.metadata
                },
                "normativa": {
                    "score": round(self.criterio_normativa.score, 3),
                    "peso": 0.25,
                    "razonamiento": self.criterio_normativa.reasoning,
                    "metadata": self.criterio_normativa.metadata
                },
                "estructura": {
                    "score": round(self.criterio_estructura.score, 3),
                    "peso": 0.20,
                    "razonamiento": self.criterio_estructura.reasoning,
                    "metadata": self.criterio_estructura.metadata
                },
                "semantica": {
                    "score": round(self.criterio_semantica.score, 3),
                    "peso": 0.20,
                    "razonamiento": self.criterio_semantica.reasoning,
                    "metadata": self.criterio_semantica.metadata
                },
                "jerarquica": {
                    "score": round(self.criterio_jerarquica.score, 3),
                    "peso": 0.10,
                    "razonamiento": self.criterio_jerarquica.reasoning,
                    "metadata": self.criterio_jerarquica.metadata
                }
            },

            # ========== RESULTADO FINAL ==========
            "score_global": round(self.score_global, 3),
            "clasificacion": self.clasificacion,
            "razonamiento_final": self.razonamiento_final,

            # ========== RESUMEN PARA VISUALIZACIÓN RÁPIDA ==========
            "scores_summary": {
                "verbo": round(self.criterio_verbo.score, 2),
                "normativa": round(self.criterio_normativa.score, 2),
                "estructura": round(self.criterio_estructura.score, 2),
                "semantica": round(self.criterio_semantica.score, 2),
                "jerarquica": round(self.criterio_jerarquica.score, 2),
                "global": round(self.score_global, 2)
            }
        }


class FunctionSemanticEvaluator:
    """
    Evaluador semántico de funciones basado en Protocolo SABG v1.1.

    Usa LLM para análisis contextual profundo de cada función contra normativa.
    """

    # Ponderaciones de criterios (deben sumar 1.0)
    WEIGHTS = {
        "verbo": 0.25,
        "normativa": 0.25,
        "estructura": 0.20,
        "semantica": 0.20,
        "jerarquica": 0.10
    }

    def __init__(self, normativa_loader, context: APFContext):
        """
        Inicializa el evaluador semántico.

        Args:
            normativa_loader: NormativaLoader con documentos normativos cargados
            context: APFContext con configuración (API keys, etc.)
        """
        self.normativa_loader = normativa_loader
        self.context = context

        logger.info("[FunctionSemanticEvaluator] Inicializado con Protocolo SABG v1.1")

    def evaluate_function(
        self,
        funcion_text: str,
        verbo: str,
        nivel_jerarquico: str,
        puesto_nombre: str,
        unidad: str
    ) -> FunctionEvaluationResult:
        """
        Evalúa una función completa usando 5 criterios con LLM.

        Args:
            funcion_text: Texto completo de la función
            verbo: Verbo principal identificado
            nivel_jerarquico: Nivel del puesto (G, H, J, K, etc.)
            puesto_nombre: Denominación del puesto
            unidad: Unidad responsable

        Returns:
            FunctionEvaluationResult con evaluación completa
        """
        logger.debug(f"[FunctionSemanticEvaluator] Evaluando función con verbo '{verbo}'")

        # Obtener contexto normativo relevante
        contexto_normativo = self._get_normativa_context(funcion_text, verbo, puesto_nombre)

        # Llamar a LLM con prompt de evaluación
        try:
            llm_response = self._call_llm_evaluation(
                funcion_text=funcion_text,
                verbo=verbo,
                nivel_jerarquico=nivel_jerarquico,
                puesto_nombre=puesto_nombre,
                unidad=unidad,
                contexto_normativo=contexto_normativo
            )

            # Parsear respuesta LLM
            result = self._parse_llm_response(llm_response, funcion_text, verbo)

            logger.debug(
                f"[FunctionSemanticEvaluator] Función evaluada: "
                f"Score={result.score_global:.2f}, Clasificación={result.clasificacion}"
            )

            return result

        except Exception as e:
            logger.error(f"[FunctionSemanticEvaluator] Error en evaluación LLM: {e}")
            # Fallback: clasificar como RECHAZADO con baja confianza
            return self._create_fallback_result(funcion_text, verbo, str(e))

    def _get_normativa_context(
        self,
        funcion_text: str,
        verbo: str,
        puesto_nombre: str
    ) -> str:
        """
        Busca fragmentos de normativa relevantes para la función.

        Args:
            funcion_text: Texto de la función
            verbo: Verbo principal
            puesto_nombre: Nombre del puesto

        Returns:
            Texto con fragmentos de normativa relevantes
        """
        if not self.normativa_loader or not hasattr(self.normativa_loader, 'semantic_search'):
            return "No hay normativa cargada para validación."

        try:
            # Buscar fragmentos relevantes usando búsqueda semántica
            query = f"{puesto_nombre} {verbo} {funcion_text[:100]}"
            search_results = self.normativa_loader.semantic_search(
                query=query,
                max_results=15  # Aumentado para cobertura normativa completa (fix v5.26)
            )

            if not search_results:
                return "No se encontraron fragmentos normativos relevantes."

            # Construir contexto con los mejores fragmentos
            context_parts = ["FRAGMENTOS NORMATIVOS RELEVANTES:\n"]
            for i, match in enumerate(search_results, 1):
                snippet = match.content_snippet[:400] if len(match.content_snippet) > 400 else match.content_snippet
                context_parts.append(f"\n[Fragmento {i}] (Relevancia: {match.confidence_score:.2f})")
                context_parts.append(f"{snippet}\n")

            return "\n".join(context_parts)

        except Exception as e:
            logger.warning(f"[FunctionSemanticEvaluator] Error buscando contexto normativo: {e}")
            return "Error al buscar normativa relevante."

    def _call_llm_evaluation(
        self,
        funcion_text: str,
        verbo: str,
        nivel_jerarquico: str,
        puesto_nombre: str,
        unidad: str,
        contexto_normativo: str
    ) -> Dict[str, Any]:
        """
        Llama al LLM con prompt de evaluación de 5 criterios.

        Returns:
            Respuesta JSON del LLM parseada
        """
        prompt = self._create_evaluation_prompt(
            funcion_text=funcion_text,
            verbo=verbo,
            nivel_jerarquico=nivel_jerarquico,
            puesto_nombre=puesto_nombre,
            unidad=unidad,
            contexto_normativo=contexto_normativo
        )

        # Preparar prompt completo (system + user)
        system_instruction = "Eres un experto en evaluación de descripciones de puestos de la Administración Pública Federal mexicana. Respondes únicamente en JSON válido."
        full_prompt = f"{system_instruction}\n\n{prompt}"

        # Llamar a LLM
        response = robust_openai_call(
            prompt=full_prompt,
            temperature=0.1,  # Baja temperatura para mayor consistencia
            max_tokens=2500,  # Aumentado para Phi-3.5 (evitar truncamiento)
            context=self.context
        )

        # Verificar estado de respuesta
        if response.get("status") != "success":
            error_msg = response.get("error", "Error desconocido en llamada LLM")
            raise Exception(f"Error en evaluación LLM: {error_msg}")

        # Extraer datos (ya parseados como JSON)
        return response["data"]

    def _create_evaluation_prompt(
        self,
        funcion_text: str,
        verbo: str,
        nivel_jerarquico: str,
        puesto_nombre: str,
        unidad: str,
        contexto_normativo: str
    ) -> str:
        """Crea el prompt de evaluación para el LLM"""

        return f"""Eres un experto en evaluación de descripciones de puestos de la APF mexicana.

TAREA: Evaluar esta función usando el Protocolo SABG v1.1 (5 criterios).

**CONTEXTO DEL PUESTO:**
- Denominación: {puesto_nombre}
- Nivel Jerárquico: {nivel_jerarquico} (G=Dirección General, H=Subdirección, J=Jefatura, K=Enlace)
- Unidad: {unidad}

**FUNCIÓN A EVALUAR:**
"{funcion_text}"

**VERBO PRINCIPAL:** {verbo}

**NORMATIVA APLICABLE:**
{contexto_normativo}

---

EVALÚA LOS 5 CRITERIOS CON ANÁLISIS SEMÁNTICO (NO LÉXICO):

**1. CRITERIO VERBO (25%)**
- ¿El verbo está autorizado para nivel {nivel_jerarquico}?
- Verbos típicos DG (G): EMITIR, APROBAR, PROPONER, ESTABLECER, DIRIGIR, ORDENAR
- ¿Hay excepción normativa explícita (ej: REFRENDAR, RESOLVER, DESIGNAR en fragmentos)?
- Score: 1.0 (autorizado) | 0.5 (excepción válida) | 0.0 (no autorizado)

**2. CRITERIO NORMATIVA (25%)**
- ¿Existe respaldo normativo en los fragmentos proporcionados?
- Tipos de correspondencia:
  * DIRECTA: Mismo concepto, mismas palabras
  * SEMANTICA: Mismo concepto, palabras diferentes (ej: "emitir normas" = "expedir disposiciones")
  * LEJANA: Concepto relacionado pero no claro
  * NINGUNA: Sin respaldo
- Score: 1.0 (directa) | 0.7 (semántica) | 0.4 (lejana) | 0.0 (ninguna)

**3. CRITERIO ESTRUCTURA (20%)**
- ¿Tiene VERBO + COMPLEMENTO (qué/a quién) + RESULTADO (para qué)?
- Ejemplo completo: "EMITIR [verbo] los procedimientos [complemento] para la recopilación de información [resultado]"
- Score: 1.0 (los 3 componentes claros) | 0.7 (2 componentes) | 0.4 (1 componente) | 0.0 (ninguno)

**4. CRITERIO SEMÁNTICA (20%)**
- PASO 1: Extraer NÚCLEO SEMÁNTICO de la función (significado esencial en 1 frase)
- PASO 2: Extraer NÚCLEO NORMATIVO de fragmentos (significado esencial en 1 frase)
- PASO 3: Comparar núcleos (¿son equivalentes/similares/distintos?)
- IMPORTANTE: Comparar SIGNIFICADOS, no palabras exactas
- Score: 1.0 (equivalentes) | 0.7 (superposición clara) | 0.4 (superposición débil) | 0.0 (distintos)

**5. CRITERIO JERÁRQUICA (10%)**
- ¿Corresponde al nivel {nivel_jerarquico}?
  * Nivel G (DG): Estratégico, políticas, decisiones de alto nivel
  * NO Nivel G: Operacional, ejecución, tareas administrativas
- ¿Hay INVERSIÓN JERÁRQUICA? (Director hace tareas de operador)
  * Síntomas: "interpretar normas" (trabajo jurídico), "ejecutar", "compilar", "verificar"
- Score: 1.0 (corresponde) | 0.5 (requiere ajuste) | 0.0 (inversión clara)
- IMPORTANTE: Si score = 0.0, la función se RECHAZA automáticamente

---

RESPONDE EN JSON (sin comentarios adicionales):
{{
    "criterio_verbo": {{
        "score": 0.0,
        "reasoning": "explicación breve (1-2 oraciones)",
        "esta_autorizado": false,
        "tiene_excepcion_normativa": false
    }},
    "criterio_normativa": {{
        "score": 0.0,
        "reasoning": "explicación",
        "articulo_respaldo": "Fragmento X" o null,
        "tipo_correspondencia": "DIRECTA|SEMANTICA|LEJANA|NINGUNA"
    }},
    "criterio_estructura": {{
        "score": 0.0,
        "reasoning": "explicación",
        "tiene_verbo": false,
        "tiene_complemento": false,
        "tiene_resultado": false
    }},
    "criterio_semantica": {{
        "score": 0.0,
        "reasoning": "explicación",
        "nucleo_semantico": "significado esencial de la función",
        "nucleo_normativo": "significado esencial de la normativa",
        "tipo_alineacion": "EQUIVALENTE|SUPERPONE_CLARA|SUPERPONE_DEBIL|DISTINTA"
    }},
    "criterio_jerarquica": {{
        "score": 0.0,
        "reasoning": "explicación",
        "corresponde_nivel": false,
        "hay_inversion_jerarquica": false
    }},
    "score_global": 0.0,
    "clasificacion": "APROBADO|OBSERVACION|RECHAZADO",
    "razonamiento_final": "justificación integrada de 2-3 oraciones"
}}

CÁLCULO DE SCORE GLOBAL:
score_global = (verbo×0.25) + (normativa×0.25) + (estructura×0.20) + (semantica×0.20) + (jerarquica×0.10)

CLASIFICACIÓN:
- Score >= 0.85: "APROBADO"
- Score 0.60-0.84: "OBSERVACION"
- Score < 0.60: "RECHAZADO"
- Si jerarquica = 0.0: "RECHAZADO" (anula todo)
"""

    def _parse_llm_response(
        self,
        llm_data: Dict[str, Any],
        funcion_text: str,
        verbo: str
    ) -> FunctionEvaluationResult:
        """Parsea la respuesta JSON del LLM a FunctionEvaluationResult"""

        # Extraer criterios
        criterio_verbo = CriterionScore(
            score=llm_data["criterio_verbo"]["score"],
            reasoning=llm_data["criterio_verbo"]["reasoning"],
            metadata={
                "esta_autorizado": llm_data["criterio_verbo"].get("esta_autorizado", False),
                "tiene_excepcion_normativa": llm_data["criterio_verbo"].get("tiene_excepcion_normativa", False)
            }
        )

        criterio_normativa = CriterionScore(
            score=llm_data["criterio_normativa"]["score"],
            reasoning=llm_data["criterio_normativa"]["reasoning"],
            metadata={
                "articulo_respaldo": llm_data["criterio_normativa"].get("articulo_respaldo"),
                "tipo_correspondencia": llm_data["criterio_normativa"].get("tipo_correspondencia", "NINGUNA")
            }
        )

        criterio_estructura = CriterionScore(
            score=llm_data["criterio_estructura"]["score"],
            reasoning=llm_data["criterio_estructura"]["reasoning"],
            metadata={
                "tiene_verbo": llm_data["criterio_estructura"].get("tiene_verbo", False),
                "tiene_complemento": llm_data["criterio_estructura"].get("tiene_complemento", False),
                "tiene_resultado": llm_data["criterio_estructura"].get("tiene_resultado", False)
            }
        )

        criterio_semantica = CriterionScore(
            score=llm_data["criterio_semantica"]["score"],
            reasoning=llm_data["criterio_semantica"]["reasoning"],
            metadata={
                "nucleo_semantico": llm_data["criterio_semantica"].get("nucleo_semantico", ""),
                "nucleo_normativo": llm_data["criterio_semantica"].get("nucleo_normativo", ""),
                "tipo_alineacion": llm_data["criterio_semantica"].get("tipo_alineacion", "DISTINTA")
            }
        )

        criterio_jerarquica = CriterionScore(
            score=llm_data["criterio_jerarquica"]["score"],
            reasoning=llm_data["criterio_jerarquica"]["reasoning"],
            metadata={
                "corresponde_nivel": llm_data["criterio_jerarquica"].get("corresponde_nivel", False),
                "hay_inversion_jerarquica": llm_data["criterio_jerarquica"].get("hay_inversion_jerarquica", False)
            }
        )

        # Score global y clasificación
        score_global = llm_data.get("score_global", 0.0)
        clasificacion = llm_data.get("clasificacion", "RECHAZADO")
        razonamiento_final = llm_data.get("razonamiento_final", "Sin razonamiento proporcionado")

        return FunctionEvaluationResult(
            funcion_text=funcion_text,
            verbo=verbo,
            criterio_verbo=criterio_verbo,
            criterio_normativa=criterio_normativa,
            criterio_estructura=criterio_estructura,
            criterio_semantica=criterio_semantica,
            criterio_jerarquica=criterio_jerarquica,
            score_global=score_global,
            clasificacion=clasificacion,
            razonamiento_final=razonamiento_final
        )

    def _create_fallback_result(
        self,
        funcion_text: str,
        verbo: str,
        error_msg: str
    ) -> FunctionEvaluationResult:
        """Crea un resultado fallback en caso de error"""

        fallback_score = CriterionScore(
            score=0.0,
            reasoning=f"Error en evaluación LLM: {error_msg}",
            metadata={}
        )

        return FunctionEvaluationResult(
            funcion_text=funcion_text,
            verbo=verbo,
            criterio_verbo=fallback_score,
            criterio_normativa=fallback_score,
            criterio_estructura=fallback_score,
            criterio_semantica=fallback_score,
            criterio_jerarquica=fallback_score,
            score_global=0.0,
            clasificacion="RECHAZADO",
            razonamiento_final=f"Error en evaluación LLM. Clasificado como RECHAZADO por seguridad. Error: {error_msg}"
        )
