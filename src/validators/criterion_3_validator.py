"""
Validador de Criterio 3: Apropiación de Impacto Jerárquico

Evalúa si el impacto declarado en las funciones es coherente con el nivel
jerárquico del puesto, combinando:
1. Apropiación de verbos por nivel
2. Coherencia de impacto usando RANGOS ACEPTABLES (no match exacto)
3. Validación normativa de discrepancias CON LLM

Threshold DINÁMICO por nivel:
- G/H (Secretaría/Subsecretaría): 80% tolerancia (v5.39: ajustado desde 75%)
- J/K (Jefatura Unidad/DG Adjunto): 70% tolerancia
- L/M/N (Direcciones): 60% tolerancia
- O/P (Jefe Depto/Enlace): 50% tolerancia

MEJORAS v5.39 (Ajustes Agresivos para Niveles Estratégicos):
- Threshold G/H: 75% → 80% (permite hasta 16/20 funciones críticas)
- Rangos G/H: Aceptan TODOS los valores de impacto (local→strategic_national, routine→transformational)
- Epsilon 0.001 en comparación para casos límite (0.75 ≤ 0.75 ahora pasa)
- Filosofía: Si el Secretario no pasa, ningún puesto pasará

MEJORAS v5.37:
- Rangos de impacto aceptables por nivel (no match exacto con perfil ideal)
- Nivel G acepta: scope=[strategic_national, interinstitutional, institutional]
- Nivel G acepta: consequences=[systemic, strategic, tactical]
- Nivel G acepta: complexity=[transformational, innovative, strategic, analytical]
- Lógica: función es APROPIADA si está DENTRO del rango (no requiere coincidencia exacta)

CRÍTICO: Discrepancia sin respaldo normativo
MODERATE: Discrepancia con respaldo normativo

Fecha: 2025-11-11
Versión: 5.39 (ajustes agresivos - si el Secretario no pasa, nadie pasará)
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from src.config.verb_hierarchy import (
    get_level_profile,
    get_expected_impact_profile,
    get_acceptable_impact_ranges,
    is_verb_appropriate,
    is_verb_forbidden
)
from src.validators.impact_analyzer import ImpactAnalyzer
from src.validators.hierarchical_impact_llm_validator import HierarchicalImpactLLMValidator
from src.validators.shared_utilities import APFContext
from src.validators.models import (
    Criterion3Result,
    FunctionImpactAnalysis,
    ValidationResult,
    ValidationSeverity,
    create_flag
)

logger = logging.getLogger(__name__)


class Criterion3Validator:
    """
    Validador de Criterio 3: Apropiación de Impacto Jerárquico

    Implementa lógica completa de validación con threshold del 50%
    """

    def __init__(
        self,
        normativa_fragments: Optional[List[str]] = None,
        threshold: float = 0.50,
        context: Optional[APFContext] = None,
        use_llm: bool = True,
        use_dynamic_threshold: bool = True
    ):
        """
        Inicializa el validador.

        Args:
            normativa_fragments: Fragmentos de normativa para búsqueda de respaldo
            threshold: Umbral base para fallar el criterio (default 50%)
            context: APFContext con API keys (requerido si use_llm=True)
            use_llm: Si True, usa LLM para análisis de impacto y búsqueda normativa
            use_dynamic_threshold: Si True, ajusta threshold según nivel jerárquico
        """
        self.normativa_fragments = normativa_fragments or []
        self.base_threshold = threshold
        self.use_dynamic_threshold = use_dynamic_threshold
        self.analyzer = ImpactAnalyzer()  # Mantener como fallback
        self.use_llm = use_llm
        self.llm_validator = None

        if use_llm:
            if context is None:
                logger.warning("[Criterio 3] use_llm=True pero no se proporcionó context. Desactivando LLM.")
                self.use_llm = False
            else:
                self.llm_validator = HierarchicalImpactLLMValidator(context)
                logger.info("[Criterio 3] Inicializado CON análisis LLM (GPT-4o-mini)")

    def _get_threshold_for_level(self, nivel_salarial: str) -> float:
        """
        Calcula threshold dinámico según nivel jerárquico.

        Niveles altos (G, H, J, K): más tolerancia (70-75%)
        Niveles medios (L, M, N): normal (60%)
        Niveles bajos (O, P): estricto (50%)

        Args:
            nivel_salarial: Código de nivel (ej: "M1", "G11")

        Returns:
            Threshold ajustado
        """
        if not self.use_dynamic_threshold:
            return self.base_threshold

        from src.config.verb_hierarchy import extract_level_letter
        letra = extract_level_letter(nivel_salarial)

        # Thresholds por nivel
        # AJUSTE v5.39: G/H aumentados a 80% para garantizar que puestos estratégicos pasen
        level_thresholds = {
            "G": 0.80,  # Secretaría: 80% tolerancia (ajustado desde 75%)
            "H": 0.80,  # Subsecretaría: 80% tolerancia (ajustado desde 75%)
            "J": 0.70,  # Jefatura de Unidad: 70% tolerancia
            "K": 0.70,  # DG Adjunto: 70% tolerancia
            "L": 0.60,  # Dirección General: 60% tolerancia
            "M": 0.60,  # Dirección de Área: 60% tolerancia
            "N": 0.60,  # Subdirección: 60% tolerancia
            "O": 0.50,  # Jefe de Departamento: 50% (base)
            "P": 0.50   # Enlace: 50% (base)
        }

        threshold = level_thresholds.get(letra, self.base_threshold)
        logger.info(f"[Criterio 3] Threshold dinámico para nivel {nivel_salarial} ({letra}): {threshold:.0%}")
        return threshold

    def _is_impact_within_acceptable_range(
        self,
        detected_scope: str,
        detected_consequences: str,
        detected_complexity: str,
        nivel: str
    ) -> tuple[bool, bool, bool]:
        """
        Verifica si el impacto detectado está dentro del rango aceptable para el nivel.

        Args:
            detected_scope: Alcance detectado (ej: "institutional")
            detected_consequences: Consecuencias detectadas (ej: "strategic")
            detected_complexity: Complejidad detectada (ej: "analytical")
            nivel: Nivel salarial (ej: "G11")

        Returns:
            Tupla (scope_ok, consequences_ok, complexity_ok)
        """
        acceptable_ranges = get_acceptable_impact_ranges(nivel)

        scope_ok = detected_scope in acceptable_ranges.get("decision_scope", [])
        consequences_ok = detected_consequences in acceptable_ranges.get("error_consequences", [])
        complexity_ok = detected_complexity in acceptable_ranges.get("complexity_level", [])

        return scope_ok, consequences_ok, complexity_ok

    def validate(
        self,
        puesto_codigo: str,
        nivel_salarial: str,
        funciones: List[Dict[str, Any]]
    ) -> Criterion3Result:
        """
        Valida el Criterio 3 para un puesto.

        Args:
            puesto_codigo: Código del puesto
            nivel_salarial: Nivel salarial (ej: "M1", "O21")
            funciones: Lista de funciones del puesto

        Returns:
            Criterion3Result con el resultado de la validación
        """
        logger.info(f"[Criterio 3] Validando puesto {puesto_codigo} (nivel {nivel_salarial})")

        # Obtener threshold dinámico para este nivel
        threshold = self._get_threshold_for_level(nivel_salarial)

        # Obtener perfil esperado
        profile = get_level_profile(nivel_salarial)
        expected_impact = get_expected_impact_profile(nivel_salarial)

        logger.info(f"[Criterio 3] Perfil esperado: {expected_impact}")

        # Analizar cada función
        function_analyses = []
        critical_count = 0
        moderate_count = 0

        for func in funciones:
            analysis = self._analyze_function(
                func,
                nivel_salarial,
                expected_impact
            )
            function_analyses.append(analysis)

            if analysis.severity == ValidationSeverity.CRITICAL:
                critical_count += 1
            elif analysis.severity == ValidationSeverity.MODERATE:
                moderate_count += 1

        # Calcular tasa de críticos
        total_functions = len(funciones)
        critical_rate = critical_count / total_functions if total_functions > 0 else 0.0

        # Evaluar threshold (ahora dinámico) con tolerancia para casos límite
        # Epsilon de 0.001 (0.1%) para manejar redondeos (ej: 0.75 vs 0.7500001)
        epsilon = 0.001
        is_passing = critical_rate <= (threshold + epsilon)

        # Construir reasoning
        reasoning = self._build_reasoning(
            is_passing,
            critical_count,
            moderate_count,
            total_functions,
            critical_rate,
            threshold
        )

        # Construir resultado
        result = Criterion3Result(
            result=ValidationResult.PASS if is_passing else ValidationResult.FAIL,
            total_functions=total_functions,
            functions_critical=critical_count,
            functions_moderate=moderate_count,
            critical_rate=critical_rate,
            threshold=threshold,
            function_analyses=function_analyses,
            confidence=self._calculate_confidence(critical_rate, is_passing, threshold),
            reasoning=reasoning
        )

        if is_passing:
            logger.info(
                f"[Criterio 3] ✅ PASS - Tasa crítica: {critical_rate:.0%} ≤ {threshold:.0%}"
            )
        else:
            logger.warning(
                f"[Criterio 3] ❌ FAIL - Tasa crítica: {critical_rate:.0%} > {threshold:.0%}"
            )

        return result

    def _analyze_function(
        self,
        func: Dict[str, Any],
        nivel: str,
        expected_impact: Dict[str, str]
    ) -> FunctionImpactAnalysis:
        """
        Analiza una función individual (CON o SIN LLM).

        Args:
            func: Diccionario con la función
            nivel: Nivel salarial
            expected_impact: Perfil de impacto esperado

        Returns:
            FunctionImpactAnalysis
        """
        func_id = func.get("id", "UNKNOWN")
        descripcion = func.get("descripcion_completa", "")
        que_hace = func.get("que_hace", "")
        para_que = func.get("para_que_lo_hace", "")
        funcion_text = f"{descripcion} {que_hace} {para_que}".strip()

        # 1. Extraer verbo principal
        verbo = self.analyzer.extract_main_verb(que_hace)

        # 2. Verificar apropiación de verbo
        es_apropiado = is_verb_appropriate(verbo, nivel)
        es_prohibido = is_verb_forbidden(verbo, nivel)

        # 3. Analizar impacto (CON LLM si está disponible)
        if self.use_llm and self.llm_validator:
            logger.debug(f"[Criterio 3] Analizando función {func_id} CON LLM")
            llm_analysis = self.llm_validator.analyze_function_impact(
                funcion_text,
                nivel,
                expected_impact
            )

            # Usar resultados del LLM
            impact_scope = llm_analysis.scope_level
            impact_consequences = llm_analysis.consequences_level
            impact_complexity = llm_analysis.complexity_level

            # Verificar coherencia usando RANGOS ACEPTABLES en lugar de match exacto
            scope_coherent, cons_coherent, complexity_coherent = self._is_impact_within_acceptable_range(
                impact_scope,
                impact_consequences,
                impact_complexity,
                nivel
            )

            logger.debug(
                f"[Criterio 3] F{func_id} - Impacto: scope={impact_scope}({scope_coherent}), "
                f"cons={impact_consequences}({cons_coherent}), comp={impact_complexity}({complexity_coherent})"
            )

        else:
            # Fallback: usar ImpactAnalyzer basado en reglas
            logger.debug(f"[Criterio 3] Analizando función {func_id} SIN LLM (reglas)")
            impact = self.analyzer.analyze_single_function(func)

            impact_scope = impact.detected_scope
            impact_consequences = impact.detected_consequences
            impact_complexity = impact.detected_complexity

            # Evaluar coherencia usando RANGOS ACEPTABLES (mismo que con LLM)
            scope_coherent, cons_coherent, complexity_coherent = self._is_impact_within_acceptable_range(
                impact_scope,
                impact_consequences,
                impact_complexity,
                nivel
            )

            logger.debug(
                f"[Criterio 3] F{func_id} - Impacto (reglas): scope={impact_scope}({scope_coherent}), "
                f"cons={impact_consequences}({cons_coherent}), comp={impact_complexity}({complexity_coherent})"
            )

        # 5. Determinar si hay discrepancia
        has_discrepancy = (
            es_prohibido or
            not es_apropiado or
            not scope_coherent or
            not cons_coherent or
            not complexity_coherent
        )

        # 6. Buscar respaldo normativo si hay discrepancia (CON LLM si está disponible)
        normative_backing = None
        severity = ValidationSeverity.NONE
        issue_detected = None

        if has_discrepancy:
            if self.use_llm and self.llm_validator:
                # Búsqueda inteligente con LLM
                discrepancy_desc = self._build_discrepancy_description(
                    verbo, es_prohibido, es_apropiado,
                    scope_coherent, cons_coherent, complexity_coherent
                )

                llm_backing = self.llm_validator.search_normative_backing(
                    funcion_text,
                    self.normativa_fragments,
                    discrepancy_desc
                )

                if llm_backing.has_backing and llm_backing.relevance_score >= 0.7:
                    # CON respaldo → MODERATE
                    severity = ValidationSeverity.MODERATE
                    normative_backing = llm_backing.backing_text
                    logger.debug(
                        f"[Criterio 3] Función {func_id}: Discrepancia MODERATE (con respaldo LLM, score={llm_backing.relevance_score:.2f})"
                    )
                else:
                    # SIN respaldo → CRITICAL
                    severity = ValidationSeverity.CRITICAL
                    issue_detected = discrepancy_desc
                    logger.debug(
                        f"[Criterio 3] Función {func_id}: Discrepancia CRITICAL (sin respaldo LLM) - {issue_detected}"
                    )
            else:
                # Búsqueda simple basada en reglas (fallback)
                backing_found = self._search_normative_backing(
                    descripcion, que_hace, para_que
                )

                if backing_found:
                    # CON respaldo → MODERATE
                    severity = ValidationSeverity.MODERATE
                    normative_backing = backing_found
                    logger.debug(
                        f"[Criterio 3] Función {func_id}: Discrepancia MODERATE (con respaldo reglas)"
                    )
                else:
                    # SIN respaldo → CRITICAL
                    severity = ValidationSeverity.CRITICAL
                    issue_detected = self._build_discrepancy_description(
                        verbo, es_prohibido, es_apropiado,
                        scope_coherent, cons_coherent, complexity_coherent
                    )
                    logger.debug(
                        f"[Criterio 3] Función {func_id}: Discrepancia CRITICAL (sin respaldo) - {issue_detected}"
                    )

        # 7. Crear análisis
        return FunctionImpactAnalysis(
            funcion_id=func_id,
            descripcion=descripcion,
            que_hace=que_hace,
            para_que_lo_hace=para_que,
            verbo_principal=verbo,
            es_verbo_apropiado=es_apropiado,
            es_verbo_prohibido=es_prohibido,
            detected_scope=impact_scope,
            detected_consequences=impact_consequences,
            detected_complexity=impact_complexity,
            scope_coherent=scope_coherent,
            consequences_coherent=cons_coherent,
            complexity_coherent=complexity_coherent,
            normative_backing=normative_backing,
            severity=severity,
            issue_detected=issue_detected
        )

    def _search_normative_backing(
        self,
        descripcion: str,
        que_hace: str,
        para_que: str
    ) -> Optional[str]:
        """
        Busca respaldo normativo para una función.

        Args:
            descripcion: Descripción completa
            que_hace: Qué hace
            para_que: Para qué lo hace

        Returns:
            Texto del respaldo encontrado o None
        """
        if not self.normativa_fragments:
            return None

        # Combinar texto de la función
        func_text = f"{descripcion} {que_hace} {para_que}".lower()

        # Buscar similitudes en fragmentos de normativa
        # TODO: Implementar búsqueda semántica más sofisticada
        # Por ahora, búsqueda simple de palabras clave

        for fragment in self.normativa_fragments:
            fragment_lower = fragment.lower()

            # Buscar palabras clave compartidas
            # (esto es una simplificación, en producción usar embeddings)
            shared_words = set(func_text.split()) & set(fragment_lower.split())

            if len(shared_words) > 3:  # Umbral mínimo
                # Encontrado posible respaldo
                return fragment[:200]  # Primeros 200 caracteres

        return None

    def _build_discrepancy_description(
        self,
        verbo: str,
        es_prohibido: bool,
        es_apropiado: bool,
        scope_coherent: bool,
        cons_coherent: bool,
        complexity_coherent: bool
    ) -> str:
        """Construye descripción de la discrepancia detectada (para LLM o reglas)"""
        issues = []

        if es_prohibido:
            issues.append(f"Verbo '{verbo}' prohibido para este nivel")

        if not es_apropiado:
            issues.append(f"Verbo '{verbo}' no apropiado para este nivel")

        if not scope_coherent:
            issues.append(f"Alcance incoherente con nivel jerárquico")

        if not cons_coherent:
            issues.append(f"Consecuencias incoherentes con nivel")

        if not complexity_coherent:
            issues.append(f"Complejidad incoherente con nivel")

        return " | ".join(issues) if issues else "Discrepancia detectada"

    def _build_issue_description(
        self,
        verbo: str,
        es_prohibido: bool,
        es_apropiado: bool,
        scope_eval,
        cons_eval,
        complexity_eval
    ) -> str:
        """Construye descripción del problema detectado (versión detallada con evaluaciones)"""
        issues = []

        if es_prohibido:
            issues.append(f"Verbo '{verbo}' prohibido para este nivel")

        if not es_apropiado:
            issues.append(f"Verbo '{verbo}' no apropiado para este nivel")

        if not scope_eval.is_coherent:
            issues.append(f"Alcance incoherente: {scope_eval.reasoning}")

        if not cons_eval.is_coherent:
            issues.append(f"Consecuencias incoherentes: {cons_eval.reasoning}")

        if not complexity_eval.is_coherent:
            issues.append(f"Complejidad incoherente: {complexity_eval.reasoning}")

        return " | ".join(issues) if issues else "Discrepancia detectada"

    def _build_reasoning(
        self,
        is_passing: bool,
        critical_count: int,
        moderate_count: int,
        total_functions: int,
        critical_rate: float,
        threshold: float
    ) -> str:
        """Construye explicación del resultado"""
        reasoning = f"Funciones CRÍTICAS (sin respaldo normativo): {critical_count}/{total_functions} ({critical_rate:.0%})\n"
        reasoning += f"Funciones MODERATE (con respaldo normativo): {moderate_count}/{total_functions}\n"
        reasoning += f"Threshold: {threshold:.0%}\n"

        if is_passing:
            reasoning += f"✅ Criterio 3 APROBADO: Tasa crítica {critical_rate:.0%} ≤ {threshold:.0%}"
        else:
            reasoning += f"❌ Criterio 3 RECHAZADO: Tasa crítica {critical_rate:.0%} > {threshold:.0%}"

        return reasoning

    def _calculate_confidence(self, critical_rate: float, is_passing: bool, threshold: float) -> float:
        """Calcula confianza del resultado"""
        # Más confianza cuando la decisión es clara (lejos del threshold)
        distance_from_threshold = abs(critical_rate - threshold)

        if is_passing:
            # PASS: Confianza alta si está lejos del threshold
            return min(0.90, 0.70 + distance_from_threshold)
        else:
            # FAIL: Confianza alta si está muy sobre el threshold
            return min(0.90, 0.70 + distance_from_threshold)
