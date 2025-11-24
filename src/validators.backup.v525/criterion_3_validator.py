"""
Validador de Criterio 3: Apropiación de Impacto Jerárquico

Evalúa si el impacto declarado en las funciones es coherente con el nivel
jerárquico del puesto, combinando:
1. Apropiación de verbos por nivel
2. Coherencia de impacto (alcance, consecuencias, complejidad)
3. Validación normativa de discrepancias

Threshold: >50% funciones CRÍTICAS (sin respaldo) → FAIL
CRÍTICO: Discrepancia sin respaldo normativo
MODERATE: Discrepancia con respaldo normativo

Fecha: 2025-11-05
Versión: 5.0
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from src.config.verb_hierarchy import (
    get_level_profile,
    get_expected_impact_profile,
    is_verb_appropriate,
    is_verb_forbidden
)
from src.validators.impact_analyzer import ImpactAnalyzer
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
        threshold: float = 0.50
    ):
        """
        Inicializa el validador.

        Args:
            normativa_fragments: Fragmentos de normativa para búsqueda de respaldo
            threshold: Umbral para fallar el criterio (default 50%)
        """
        self.normativa_fragments = normativa_fragments or []
        self.threshold = threshold
        self.analyzer = ImpactAnalyzer()

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

        # Evaluar threshold
        is_passing = critical_rate <= self.threshold

        # Construir reasoning
        reasoning = self._build_reasoning(
            is_passing,
            critical_count,
            moderate_count,
            total_functions,
            critical_rate
        )

        # Construir resultado
        result = Criterion3Result(
            result=ValidationResult.PASS if is_passing else ValidationResult.FAIL,
            total_functions=total_functions,
            functions_critical=critical_count,
            functions_moderate=moderate_count,
            critical_rate=critical_rate,
            threshold=self.threshold,
            function_analyses=function_analyses,
            confidence=self._calculate_confidence(critical_rate, is_passing),
            reasoning=reasoning
        )

        if is_passing:
            logger.info(
                f"[Criterio 3] ✅ PASS - Tasa crítica: {critical_rate:.0%} ≤ {self.threshold:.0%}"
            )
        else:
            logger.warning(
                f"[Criterio 3] ❌ FAIL - Tasa crítica: {critical_rate:.0%} > {self.threshold:.0%}"
            )

        return result

    def _analyze_function(
        self,
        func: Dict[str, Any],
        nivel: str,
        expected_impact: Dict[str, str]
    ) -> FunctionImpactAnalysis:
        """
        Analiza una función individual.

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

        # 1. Extraer verbo principal
        verbo = self.analyzer.extract_main_verb(que_hace)

        # 2. Verificar apropiación de verbo
        es_apropiado = is_verb_appropriate(verbo, nivel)
        es_prohibido = is_verb_forbidden(verbo, nivel)

        # 3. Analizar impacto
        impact = self.analyzer.analyze_single_function(func)

        # 4. Evaluar coherencia de dimensiones
        scope_eval = self.analyzer.evaluate_scope_coherence(
            impact.detected_scope,
            expected_impact.get("decision_scope", "local"),
            nivel
        )

        cons_eval = self.analyzer.evaluate_consequences_coherence(
            impact.detected_consequences,
            expected_impact.get("error_consequences", "operational"),
            nivel
        )

        complexity_eval = self.analyzer.evaluate_complexity_coherence(
            impact.detected_complexity,
            expected_impact.get("complexity_level", "routine"),
            nivel
        )

        # 5. Determinar si hay discrepancia
        has_discrepancy = (
            es_prohibido or
            not es_apropiado or
            not scope_eval.is_coherent or
            not cons_eval.is_coherent or
            not complexity_eval.is_coherent
        )

        # 6. Buscar respaldo normativo si hay discrepancia
        normative_backing = None
        severity = ValidationSeverity.NONE
        issue_detected = None

        if has_discrepancy:
            # Buscar en normativa
            backing_found = self._search_normative_backing(
                descripcion, que_hace, para_que
            )

            if backing_found:
                # CON respaldo → MODERATE
                severity = ValidationSeverity.MODERATE
                normative_backing = backing_found
                logger.debug(
                    f"[Criterio 3] Función {func_id}: Discrepancia MODERATE (con respaldo)"
                )
            else:
                # SIN respaldo → CRITICAL
                severity = ValidationSeverity.CRITICAL
                issue_detected = self._build_issue_description(
                    verbo, es_prohibido, es_apropiado,
                    scope_eval, cons_eval, complexity_eval
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
            detected_scope=impact.detected_scope,
            detected_consequences=impact.detected_consequences,
            detected_complexity=impact.detected_complexity,
            scope_coherent=scope_eval.is_coherent,
            consequences_coherent=cons_eval.is_coherent,
            complexity_coherent=complexity_eval.is_coherent,
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

    def _build_issue_description(
        self,
        verbo: str,
        es_prohibido: bool,
        es_apropiado: bool,
        scope_eval,
        cons_eval,
        complexity_eval
    ) -> str:
        """Construye descripción del problema detectado"""
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
        critical_rate: float
    ) -> str:
        """Construye explicación del resultado"""
        reasoning = f"Funciones CRÍTICAS (sin respaldo normativo): {critical_count}/{total_functions} ({critical_rate:.0%})\n"
        reasoning += f"Funciones MODERATE (con respaldo normativo): {moderate_count}/{total_functions}\n"
        reasoning += f"Threshold: {self.threshold:.0%}\n"

        if is_passing:
            reasoning += f"✅ Criterio 3 APROBADO: Tasa crítica {critical_rate:.0%} ≤ {self.threshold:.0%}"
        else:
            reasoning += f"❌ Criterio 3 RECHAZADO: Tasa crítica {critical_rate:.0%} > {self.threshold:.0%}"

        return reasoning

    def _calculate_confidence(self, critical_rate: float, is_passing: bool) -> float:
        """Calcula confianza del resultado"""
        # Más confianza cuando la decisión es clara (lejos del threshold)
        distance_from_threshold = abs(critical_rate - self.threshold)

        if is_passing:
            # PASS: Confianza alta si está lejos del threshold
            return min(0.90, 0.70 + distance_from_threshold)
        else:
            # FAIL: Confianza alta si está muy sobre el threshold
            return min(0.90, 0.70 + distance_from_threshold)
