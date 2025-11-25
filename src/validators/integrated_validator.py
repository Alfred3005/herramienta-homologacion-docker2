"""
Validador Integrado - Sistema Completo de 3 Criterios

Orquesta la validación completa de un puesto usando:
- Criterio 1: Congruencia de Verbos Débiles (CON LLM)
- Criterio 2: Validación Contextual (Referencias Institucionales CON LLM)
- Criterio 3: Apropiación de Impacto Jerárquico

Decisión Final: Matriz 2-of-3

OPTIMIZACIÓN v5.38:
Caché de NormativaLoader - Cuando se analizan múltiples puestos con la misma
normativa, el loader (con embeddings) se reutiliza automáticamente, evitando:
- Re-procesamiento de fragmentos
- Re-generación de embeddings
- Re-creación de índice semántico

Ahorro estimado: 80-90% del tiempo de inicialización en análisis múltiples.

Fecha: 2025-11-11
Versión: 5.38 - Con caché de normativa para análisis múltiples
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from src.validators.criterion_3_validator import Criterion3Validator
from src.validators.contextual_verb_validator import ContextualVerbValidator
from src.validators.verb_semantic_analyzer import VerbSemanticAnalyzer
from src.validators.function_semantic_evaluator import FunctionSemanticEvaluator
from src.validators.advanced_quality_validator import AdvancedQualityValidator
from src.validators.shared_utilities import APFContext
from src.validators.in_memory_normativa_adapter import create_loader_from_fragments
from src.validators.models import (
    Criterion1Result,
    Criterion2Result,
    Criterion3Result,
    FinalDecision,
    ValidationResult,
    calculate_final_decision
)

logger = logging.getLogger(__name__)


class IntegratedValidator:
    """
    Validador integrado que ejecuta los 3 criterios y calcula decisión final.

    VERSIÓN ADAPTADA: Usa validadores LLM reales de v4 para Criterio 1 y 2.

    OPTIMIZACIÓN v5.38:
    Caché de NormativaLoader - Cuando se analizan múltiples puestos con la misma
    normativa, el loader se reutiliza en lugar de recrearse para cada puesto.
    """

    # Class-level cache para NormativaLoader
    _normativa_cache = {}
    _normativa_cache_key = None

    def __init__(
        self,
        normativa_fragments: Optional[List[str]] = None,
        openai_api_key: Optional[str] = None,
        llm_provider: Optional[Any] = None,
        use_normativa_cache: bool = True
    ):
        """
        Inicializa el validador integrado.

        Args:
            normativa_fragments: Fragmentos de normativa para validación
            openai_api_key: API key de OpenAI (DEPRECATED - usar llm_provider)
            llm_provider: Provider LLM (OpenAIProvider u OllamaProvider)
            use_normativa_cache: Si True, reutiliza NormativaLoader de caché (default: True)
        """
        self.normativa_fragments = normativa_fragments or []
        self.openai_api_key = openai_api_key
        self.llm_provider = llm_provider
        self.use_normativa_cache = use_normativa_cache

        # Crear contexto APF para validadores v4
        self.context = APFContext()

        # Si se provee un llm_provider, almacenarlo en el contexto
        if llm_provider:
            self.context.set_data('llm_provider', llm_provider, 'IntegratedValidator')
            logger.info(f"[IntegratedValidator] Usando LLM provider: {type(llm_provider).__name__}")
        elif openai_api_key:
            # Fallback: crear OpenAIProvider si solo se pasó API key
            from src.providers.openai_provider import OpenAIProvider
            self.llm_provider = OpenAIProvider(api_key=openai_api_key)
            self.context.set_data('llm_provider', self.llm_provider, 'IntegratedValidator')
            self.context.set_data('openai_api_key', openai_api_key, 'IntegratedValidator')
            self.context.set_data('api_key', openai_api_key, 'IntegratedValidator')
            logger.info("[IntegratedValidator] Creado OpenAIProvider desde API key (modo compatibilidad)")

        # Crear o reutilizar NormativaLoader con caché
        self.normativa_loader = None
        if normativa_fragments:
            # Generar cache key basado en contenido de fragmentos
            cache_key = hash(tuple(normativa_fragments))

            if use_normativa_cache and cache_key == IntegratedValidator._normativa_cache_key:
                # Reutilizar loader del caché
                self.normativa_loader = IntegratedValidator._normativa_cache.get('loader')
                if self.normativa_loader:
                    logger.info(f"[IntegratedValidator] ✅ Reutilizando NormativaLoader del caché ({len(normativa_fragments)} fragmentos)")

            if not self.normativa_loader:
                # Crear nuevo loader y guardarlo en caché
                try:
                    logger.info(f"[IntegratedValidator] Creando NormativaLoader con {len(normativa_fragments)} fragmentos")
                    self.normativa_loader = create_loader_from_fragments(
                        text_fragments=normativa_fragments,
                        document_title="Reglamento Interior",
                        use_embeddings=True,  # Habilitado para precisión semántica (fix v5.26)
                        context=self.context
                    )
                    logger.info("[IntegratedValidator] NormativaLoader creado exitosamente")
                    logger.info(f"[IntegratedValidator] embedding_mode: {self.normativa_loader.embedding_mode}")
                    logger.info(f"[IntegratedValidator] semantic_search disponible: {hasattr(self.normativa_loader, 'semantic_search')}")

                    # Guardar en caché
                    if use_normativa_cache:
                        IntegratedValidator._normativa_cache = {'loader': self.normativa_loader}
                        IntegratedValidator._normativa_cache_key = cache_key
                        logger.info("[IntegratedValidator] 💾 NormativaLoader guardado en caché para reutilización")
                except Exception as e:
                    logger.error(f"[IntegratedValidator] Error creando NormativaLoader: {e}")
                    self.normativa_loader = None

        # Inicializar validadores LLM de v4
        self.verb_analyzer = VerbSemanticAnalyzer(context=self.context)
        self.contextual_validator = ContextualVerbValidator(
            normativa_loader=self.normativa_loader,
            context=self.context
        )

        # Inicializar FunctionSemanticEvaluator v5.20 (Protocolo SABG)
        self.function_evaluator = FunctionSemanticEvaluator(
            normativa_loader=self.normativa_loader,
            context=self.context
        )

        # Inicializar Criterion3Validator v5.34 (CON LLM para análisis de impacto)
        self.criterion3_validator = Criterion3Validator(
            normativa_fragments=normativa_fragments,
            threshold=0.50,
            context=self.context,  # Pasar context para habilitar LLM
            use_llm=True  # Activar análisis LLM
        )

        # Inicializar AdvancedQualityValidator v5.33-new (análisis holístico de calidad)
        self.quality_validator = AdvancedQualityValidator(context=self.context)

        provider_name = type(self.llm_provider).__name__ if self.llm_provider else "Sin Provider"
        logger.info(f"[IntegratedValidator] Inicializado con validadores LLM v4 + FunctionEvaluator v5.20 + Criterion3 v5.34 CON LLM + QualityValidator v5.33 | Provider: {provider_name}")

    def validate_puesto(
        self,
        puesto_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Valida un puesto completo usando los 3 criterios + validaciones de calidad.

        Args:
            puesto_data: Diccionario con datos del puesto
                {
                    "codigo": str,
                    "denominacion": str,
                    "nivel_salarial": str,
                    "unidad_responsable": str,
                    "funciones": List[Dict],
                    "objetivo_general": str (opcional)
                }

        Returns:
            Diccionario con resultados completos de validación
        """
        codigo = puesto_data.get("codigo", "UNKNOWN")
        nivel = puesto_data.get("nivel_salarial", "P")
        funciones = puesto_data.get("funciones", [])

        logger.info(f"[IntegratedValidator] Validando puesto {codigo}")

        # Ejecutar análisis de calidad holístico (v5.33-new)
        # Este análisis detecta: duplicados, malformadas, problemas legales, objetivo inadecuado
        logger.info(f"[IntegratedValidator] Ejecutando análisis de calidad holístico...")
        try:
            # Obtener texto completo de normativa si está disponible
            normativa_text = None
            if self.normativa_loader and hasattr(self.normativa_loader, 'documents'):
                # Concatenar primeros 3 documentos (limitar tamaño)
                try:
                    docs_list = list(self.normativa_loader.documents) if not isinstance(self.normativa_loader.documents, list) else self.normativa_loader.documents
                    docs = docs_list[:3]
                    normativa_text = "\n\n".join([doc.content[:1000] for doc in docs])
                except Exception as doc_error:
                    logger.warning(f"[IntegratedValidator] Error accediendo a documents: {doc_error}")
                    normativa_text = None

            quality_result = self.quality_validator.validate_puesto_completo(
                puesto_data=puesto_data,
                normativa_text=normativa_text
            )
            logger.info(
                f"[IntegratedValidator] Análisis de calidad completado: "
                f"{quality_result.total_flags} flags detectados "
                f"(CRITICAL: {quality_result.flags_critical}, HIGH: {quality_result.flags_high}, "
                f"MODERATE: {quality_result.flags_moderate}, LOW: {quality_result.flags_low})"
            )
        except Exception as e:
            logger.error(f"[IntegratedValidator] Error en análisis de calidad: {e}")
            # Crear resultado vacío si falla
            from src.validators.advanced_quality_validator import QualityValidationResult
            quality_result = QualityValidationResult(
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

        # Ejecutar 3 criterios CON LLM
        criterion_1 = self._validate_criterion_1(codigo, funciones, nivel, puesto_data)
        criterion_2 = self._validate_criterion_2(codigo, puesto_data)
        criterion_3 = self.criterion3_validator.validate(
            puesto_codigo=codigo,
            nivel_salarial=nivel,
            funciones=funciones
        )

        # Calcular decisión final
        final_decision = calculate_final_decision(
            criterion_1,
            criterion_2,
            criterion_3
        )

        # Construir resultado con estructura robusta
        result = {
            "puesto": {
                "codigo": codigo,
                "denominacion": puesto_data.get("denominacion", ""),
                "nivel": nivel,  # Campo principal
                "nivel_salarial": nivel,  # Alias para compatibilidad (evita KeyError)
                "unidad_responsable": puesto_data.get("unidad_responsable", "")
            },
            "validacion": {
                "resultado": final_decision.resultado,
                "clasificacion": final_decision.clasificacion.value,
                "criterios_aprobados": final_decision.criteria_passed,
                "total_criterios": 3,  # Evitar hardcoding (v5.33)
                "confianza": round(final_decision.confidence_global, 2),
                "criterios": {
                    "criterio_1_verbos": self._format_criterion_1(criterion_1, quality_result),
                    "criterio_2_contextual": self._format_criterion_2(criterion_2, quality_result),
                    "criterio_3_impacto": self._format_criterion_3(criterion_3)
                },
                "accion_requerida": final_decision.accion_requerida,
                "razonamiento": final_decision.reasoning
            }
        }

        return result

    def _validate_criterion_1(
        self,
        codigo: str,
        funciones: List[Dict[str, Any]],
        nivel_salarial: str = "P",
        puesto_data: Optional[Dict[str, Any]] = None
    ) -> Criterion1Result:
        """
        Criterio 1 v5.20: Análisis Semántico Contextual con LLM (Protocolo SABG).

        Evalúa cada función usando 5 criterios:
        1. Verbo (25%) - ¿Autorizado para el nivel?
        2. Normativa (25%) - ¿Respaldo en reglamento?
        3. Estructura (20%) - ¿VERBO+COMPLEMENTO+RESULTADO?
        4. Semántica (20%) - ¿Alineación significado función vs normativa?
        5. Jerárquica (10%) - ¿Corresponde al nivel del puesto?

        Args:
            codigo: Código del puesto
            funciones: Lista de funciones del puesto
            nivel_salarial: Nivel jerárquico (G11, H, J, K, etc.)
            puesto_data: Datos completos del puesto (denominación, unidad, etc.)

        Returns:
            Criterion1Result con evaluación semántica completa
        """
        logger.info(f"[Criterio 1 v5.20 SABG] Análisis semántico de {len(funciones)} funciones")

        # Extraer información del puesto
        puesto_nombre = puesto_data.get("denominacion", "") if puesto_data else ""
        unidad = puesto_data.get("unidad_responsable", "") if puesto_data else ""

        total_functions = len(funciones)
        aprobadas = []
        observadas = []
        rechazadas = []

        # Evaluar cada función con FunctionSemanticEvaluator
        for idx, func in enumerate(funciones, 1):
            try:
                # Obtener texto completo de la función
                funcion_text = func.get("descripcion_completa", "") or func.get("que_hace", "")
                verbo = func.get("verbo_accion", "").strip()

                # Fallback: extraer primer verbo si no está explícito
                if not verbo and funcion_text:
                    verbo = funcion_text.split()[0] if funcion_text.split() else "DESCONOCIDO"

                # Evaluar función completa con 5 criterios LLM
                evaluation = self.function_evaluator.evaluate_function(
                    funcion_text=funcion_text,
                    verbo=verbo,
                    nivel_jerarquico=nivel_salarial[0] if nivel_salarial else "P",
                    puesto_nombre=puesto_nombre,
                    unidad=unidad
                )

                # Clasificar según resultado
                if evaluation.clasificacion == "APROBADO":
                    aprobadas.append(evaluation)
                    logger.debug(f"   Función {idx}: APROBADO (score={evaluation.score_global:.2f})")
                elif evaluation.clasificacion == "OBSERVACION":
                    observadas.append(evaluation)
                    logger.debug(f"   Función {idx}: OBSERVACION (score={evaluation.score_global:.2f})")
                else:  # RECHAZADO
                    rechazadas.append(evaluation)
                    logger.warning(f"   Función {idx}: RECHAZADO (score={evaluation.score_global:.2f}) - {verbo}")

            except Exception as e:
                logger.error(f"[Criterio 1 v5.20] Error evaluando función {idx}: {e}")
                # Fallback: clasificar como RECHAZADO
                rechazadas.append(None)  # Placeholder para contar

        # Calcular tasas
        tasa_aprobadas = len(aprobadas) / total_functions if total_functions > 0 else 0.0
        tasa_rechazadas = len(rechazadas) / total_functions if total_functions > 0 else 0.0

        # Decisión: FAIL solo si > 50% críticas (v4 compatibility - funciones observadas cuentan como OK)
        is_passing = tasa_rechazadas <= 0.50

        logger.info(
            f"[Criterio 1 v5.27 SABG] Aprobadas: {len(aprobadas)} ({tasa_aprobadas:.0%}), "
            f"Observadas: {len(observadas)} ({len(observadas)/total_functions:.0%}), "
            f"Rechazadas: {len(rechazadas)} ({tasa_rechazadas:.0%}) → "
            f"{'PASS' if is_passing else 'FAIL'} (umbral: críticas ≤ 50%)"
        )

        return Criterion1Result(
            result=ValidationResult.PASS if is_passing else ValidationResult.FAIL,
            total_functions=total_functions,
            functions_approved=len(aprobadas),
            functions_moderate=len(observadas),
            functions_critical=len(rechazadas),
            approval_rate=tasa_aprobadas,
            critical_rate=tasa_rechazadas,
            threshold=0.50,
            confidence=0.95,  # Alta confianza con análisis semántico LLM de 5 criterios
            reasoning=(
                f"Análisis semántico Protocolo SABG v4-compatible: {len(aprobadas)} aprobadas "
                f"({tasa_aprobadas:.0%}), {len(observadas)} observadas ({len(observadas)/total_functions:.0%}), "
                f"{len(rechazadas)} rechazadas ({tasa_rechazadas:.0%}). "
                f"Umbral: funciones críticas ≤ 50%. Resultado: {'PASS' if is_passing else 'FAIL'}."
            ),
            details={
                "aprobadas": [e.to_dict() for e in aprobadas if e],
                "observadas": [e.to_dict() for e in observadas if e],
                "rechazadas": [e.to_dict() for e in rechazadas if e]
            }
        )

    def _validate_criterion_2(
        self,
        codigo: str,
        puesto_data: Dict[str, Any]
    ) -> Criterion2Result:
        """
        Valida Criterio 2: Validación Contextual.

        VERSIÓN LLM: Usa ContextualVerbValidator de v4 con análisis LLM real.

        Args:
            codigo: Código del puesto
            puesto_data: Datos del puesto

        Returns:
            Criterion2Result
        """
        logger.info(f"[Criterio 2 LLM] Validando puesto {codigo}")

        # Extraer datos del puesto
        denominacion = puesto_data.get("denominacion", "")
        objetivo = puesto_data.get("objetivo_general", "")
        funciones = puesto_data.get("funciones", [])
        nivel = puesto_data.get("nivel_salarial", "P")

        # Detectar verbos débiles para pasar al validador contextual
        weak_verbs = []
        for func in funciones:
            verbo = func.get("verbo_accion", "").strip()
            if verbo:
                weak_verbs.append(verbo)

        try:
            # Llamar a contextual_validator con LLM
            validation_result = self.contextual_validator.validate_global(
                puesto_nombre=denominacion,
                objetivo_general=objetivo,
                funciones=funciones,
                nivel_jerarquico=nivel[0] if nivel else "P",
                weak_verbs_detected=weak_verbs
            )

            # Mapear resultado de v4 a Criterion2Result de v5
            alignment = validation_result.alignment_level.upper()
            is_aligned = alignment in ["ALIGNED", "PARTIALLY_ALIGNED"]

            logger.info(
                f"[Criterio 2 LLM] Alineación: {alignment}, "
                f"Confianza: {validation_result.confidence:.2f}, "
                f"Resultado: {'PASS' if is_aligned else 'FAIL'}"
            )

            return Criterion2Result(
                result=ValidationResult.PASS if is_aligned else ValidationResult.FAIL,
                institutional_references_match=validation_result.institutional_references_match,
                alignment_classification=alignment,
                alignment_confidence=validation_result.confidence,
                reasoning=validation_result.reasoning or f"Análisis LLM: {alignment}"
            )

        except Exception as e:
            logger.error(f"[Criterio 2 LLM] Error en validación: {e}")
            # Fallback: rechazar con baja confianza
            return Criterion2Result(
                result=ValidationResult.FAIL,
                institutional_references_match=False,
                alignment_classification="ERROR",
                alignment_confidence=0.30,
                reasoning=f"Error en validación LLM: {str(e)}"
            )

    def _format_criterion_1(self, criterion: Criterion1Result, quality_result=None) -> Dict[str, Any]:
        """
        Formatea resultado de Criterio 1 para JSON (v5.33+).

        Incluye validaciones adicionales de calidad (duplicación, malformación).
        """
        result = {
            "resultado": criterion.result.value,
            "tasa_aprobadas": round(criterion.approval_rate, 2),
            "tasa_critica": round(criterion.critical_rate, 2),
            "threshold": criterion.threshold,
            "funciones_aprobadas": criterion.functions_approved,
            "funciones_observadas": criterion.functions_moderate,
            "funciones_rechazadas": criterion.functions_critical,
            "total_funciones": criterion.total_functions,
            "metodo": "Análisis Semántico Protocolo SABG v1.1"
        }

        # AGREGAR DETALLES DE EVALUACIÓN POR FUNCIÓN (v5.20+)
        if criterion.details:
            result["detalles"] = criterion.details

        # AGREGAR VALIDACIONES ADICIONALES DE CALIDAD (v5.33+)
        if quality_result:
            result["validaciones_adicionales"] = {
                "duplicacion": quality_result.duplicacion,
                "malformacion": quality_result.malformacion
            }
        else:
            # Estructura vacía si no hay quality_result
            result["validaciones_adicionales"] = {
                "duplicacion": {
                    "tiene_duplicados": False,
                    "total_duplicados": 0,
                    "pares_duplicados": []
                },
                "malformacion": {
                    "tiene_malformadas": False,
                    "total_malformadas": 0,
                    "funciones_problematicas": []
                }
            }

        return result

    def _format_criterion_2(self, criterion: Criterion2Result, quality_result=None) -> Dict[str, Any]:
        """
        Formatea resultado de Criterio 2 para JSON con máxima transparencia (v5.33+).

        Incluye razonamiento LLM, evidencias, flags y validaciones adicionales de calidad
        (marco legal, objetivo general).
        """
        result = {
            # ========== RESULTADO ==========
            "resultado": criterion.result.value,

            # ========== ANÁLISIS DE REFERENCIAS INSTITUCIONALES ==========
            "referencias_institucionales": {
                "coinciden": criterion.institutional_references_match,
                "explicacion": "Organismos/secretarías mencionadas en puesto coinciden con normativa proporcionada"
            },

            # ========== ANÁLISIS DE ALINEACIÓN ==========
            "alineacion": {
                "clasificacion": criterion.alignment_classification,  # ALIGNED, PARTIALLY_ALIGNED, NOT_ALIGNED
                "confianza": round(criterion.alignment_confidence, 2),
                "respaldo_jerarquico": criterion.has_hierarchical_backing,
                "explicacion_respaldo": "Funciones derivables de atribuciones del jefe directo" if criterion.has_hierarchical_backing else "No aplica o no detectado"
            },

            # ========== RAZONAMIENTO DETALLADO LLM ==========
            "razonamiento": criterion.reasoning,

            # ========== EVIDENCIAS NORMATIVAS USADAS ==========
            "evidencias": [
                {
                    "fuente": ev.source,
                    "fragmento": ev.content_snippet,
                    "similarity_score": round(ev.similarity_score, 3),
                    "articulo": ev.article_reference
                }
                for ev in criterion.evidence_found
            ] if criterion.evidence_found else [],

            # ========== FLAGS/PROBLEMAS DETECTADOS ==========
            "flags": [
                {
                    "id": flag.flag_id,
                    "severidad": flag.severity.value,
                    "titulo": flag.title,
                    "descripcion": flag.description,
                    "riesgo_legal": flag.legal_risk,
                    "solucion_sugerida": flag.suggested_fix,
                    "referencia_normativa": flag.normative_reference
                }
                for flag in criterion.flags_detected
            ] if criterion.flags_detected else []
        }

        # AGREGAR VALIDACIONES ADICIONALES DE CALIDAD (v5.33+)
        if quality_result:
            result["validaciones_adicionales"] = {
                "marco_legal": quality_result.marco_legal,
                "objetivo_general": quality_result.objetivo_general
            }
        else:
            # Estructura vacía si no hay quality_result
            result["validaciones_adicionales"] = {
                "marco_legal": {
                    "tiene_problemas": False,
                    "total_problemas": 0,
                    "problemas": []
                },
                "objetivo_general": {
                    "es_adecuado": True,
                    "calificacion": 1.0,
                    "problemas": []
                }
            }

        return result

    def _format_criterion_3(self, criterion: Criterion3Result) -> Dict[str, Any]:
        """
        Formatea resultado de Criterio 3 para JSON con máxima transparencia.

        Incluye análisis detallado de impacto jerárquico por función y evidencias.
        """
        result = {
            # ========== RESULTADO ==========
            "resultado": criterion.result.value,

            # ========== MÉTRICAS AGREGADAS ==========
            "metricas": {
                "tasa_critica": round(criterion.critical_rate, 2),
                "threshold": criterion.threshold,
                "total_funciones": criterion.total_functions,
                "funciones_critical": criterion.functions_critical,  # Sin respaldo normativo
                "funciones_moderate": criterion.functions_moderate,  # Con respaldo (anotación)
                "funciones_con_verbo_inapropiado": criterion.functions_with_inappropriate_verbs,
                "funciones_con_verbo_prohibido": criterion.functions_with_forbidden_verbs,
                "funciones_con_alcance_discrepante": criterion.functions_with_scope_discrepancy,
                "funciones_con_consecuencias_discrepantes": criterion.functions_with_consequences_discrepancy
            },

            # ========== ANÁLISIS DETALLADO POR FUNCIÓN ==========
            "analisis_funciones": [
                {
                    "funcion_id": fa.funcion_id,
                    "descripcion": fa.descripcion,
                    "que_hace": fa.que_hace,
                    "para_que_lo_hace": fa.para_que_lo_hace,

                    "verbo": {
                        "verbo_principal": fa.verbo_principal,
                        "es_apropiado": fa.es_verbo_apropiado,
                        "es_prohibido": fa.es_verbo_prohibido
                    },

                    "impacto_detectado": {
                        "alcance": fa.detected_scope,  # local, institutional, interinstitutional, strategic_national
                        "consecuencias": fa.detected_consequences,  # operational, tactical, strategic, systemic
                        "complejidad": fa.detected_complexity  # routine, analytical, strategic, transformational
                    },

                    "coherencia": {
                        "alcance_coherente": fa.scope_coherent,
                        "consecuencias_coherentes": fa.consequences_coherent,
                        "complejidad_coherente": fa.complexity_coherent
                    },

                    "respaldo_normativo": {
                        "tiene_respaldo": fa.normative_backing is not None,
                        "fragmento": fa.normative_backing,
                        "confianza": round(fa.normative_confidence, 3) if fa.normative_confidence else 0.0
                    },

                    "severidad": fa.severity.value,
                    "problema_detectado": fa.issue_detected,
                    "solucion_sugerida": fa.suggested_fix
                }
                for fa in criterion.function_analyses
            ] if criterion.function_analyses else [],

            # ========== RAZONAMIENTO GENERAL ==========
            "razonamiento": criterion.reasoning,

            # ========== FRAGMENTOS NORMATIVOS USADOS ==========
            "fragmentos_normativos": criterion.normative_fragments_used if criterion.normative_fragments_used else [],

            # ========== FLAGS/PROBLEMAS DETECTADOS ==========
            "flags": [
                {
                    "id": flag.flag_id,
                    "severidad": flag.severity.value,
                    "titulo": flag.title,
                    "descripcion": flag.description,
                    "riesgo_legal": flag.legal_risk,
                    "solucion_sugerida": flag.suggested_fix,
                    "referencia_normativa": flag.normative_reference
                }
                for flag in criterion.flags_detected
            ] if criterion.flags_detected else [],

            # ========== EVIDENCIAS ==========
            "evidencias": [
                {
                    "fuente": ev.source,
                    "fragmento": ev.content_snippet,
                    "similarity_score": round(ev.similarity_score, 3),
                    "articulo": ev.article_reference
                }
                for ev in criterion.evidence_found
            ] if criterion.evidence_found else []
        }

        return result

    def _get_verb_normativa_context(self, verbo: str) -> Optional[str]:
        """
        Busca fragmentos de normativa relevantes para un verbo.

        Args:
            verbo: El verbo a buscar en la normativa

        Returns:
            Texto con fragmentos relevantes o None si no hay normativa
        """
        if not self.normativa_loader or not hasattr(self.normativa_loader, 'documents'):
            return None

        try:
            # Buscar fragmentos relevantes usando búsqueda semántica
            search_results = self.normativa_loader.semantic_search(
                query=f"funciones atribuciones {verbo}",
                max_results=3
            )

            if not search_results:
                return None

            # Construir contexto con los fragmentos encontrados
            context_parts = []
            for match in search_results:
                # Truncar fragmentos muy largos
                snippet = match.content_snippet[:300] if len(match.content_snippet) > 300 else match.content_snippet
                context_parts.append(f"- {snippet}")

            return "\n".join(context_parts) if context_parts else None

        except Exception as e:
            logger.warning(f"[IntegratedValidator] Error buscando contexto para verbo '{verbo}': {e}")
            return None

    def validate_batch(
        self,
        puestos: List[Dict[str, Any]],
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Valida múltiples puestos en lote.

        Args:
            puestos: Lista de puestos a validar
            progress_callback: Callback(progreso_pct) para reportar progreso

        Returns:
            Lista de resultados de validación
        """
        results = []
        total = len(puestos)

        for idx, puesto in enumerate(puestos):
            try:
                result = self.validate_puesto(puesto)
                results.append(result)

                # Reportar progreso
                if progress_callback:
                    progress_pct = int((idx + 1) / total * 100)
                    progress_callback(progress_pct)

            except Exception as e:
                logger.error(f"Error validando puesto {puesto.get('codigo')}: {e}")
                # Agregar resultado de error
                results.append({
                    "puesto": {
                        "codigo": puesto.get("codigo", "UNKNOWN"),
                        "error": str(e)
                    },
                    "validacion": {
                        "resultado": "ERROR",
                        "mensaje": f"Error al procesar: {str(e)}"
                    }
                })

        return results
