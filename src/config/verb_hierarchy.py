"""
Jerarquía de Verbos por Nivel APF

Define perfiles jerárquicos para cada nivel salarial de la Administración
Pública Federal, incluyendo verbos apropiados/prohibidos y perfiles de impacto.

NOTA: El campo 'budget_range' en impact_profile se mantiene por compatibilidad
estructural, pero NO se usa en la lógica de decisión (decisión del equipo 2025-11-05).

MEJORAS v5.37:
- Nueva función get_acceptable_impact_ranges() que define rangos de impacto ACEPTABLES
- Filosofía: No match exacto - permite variedad legítima de funciones por nivel
- Ejemplo: Nivel G acepta scope=[strategic_national, interinstitutional, institutional]

Fecha: 2025-11-11
Versión: 5.37
"""

from typing import Dict, List, Any, Optional


# ==========================================
# JERARQUÍA DE VERBOS Y NIVELES APF
# ==========================================

VERB_HIERARCHY: Dict[str, Dict[str, Any]] = {
    # NIVEL G: Secretaría de Estado
    "G": {
        "level_name": "Secretaría de Estado",
        "description": "Máximo nivel jerárquico en la APF",
        "appropriate_verbs": [
            "dictar", "normar", "establecer", "definir", "sancionar",
            "expedir", "autorizar", "aprobar", "validar", "ratificar"
        ],
        "forbidden_verbs": [
            "ejecutar", "efectuar", "tramitar", "gestionar", "procesar",
            "capturar", "registrar", "archivar", "coadyuvar", "apoyar", "auxiliar"
        ],
        "impact_profile": {
            "decision_scope": "strategic_national",
            "budget_range": "strategic",  # NO SE USA en decisiones
            "error_consequences": "systemic",
            "complexity_level": "transformational"
        }
    },

    # NIVEL H: Subsecretaría
    "H": {
        "level_name": "Subsecretaría",
        "description": "Segundo nivel jerárquico en la APF",
        "appropriate_verbs": [
            "dictar", "normar", "establecer", "definir", "expedir",
            "autorizar", "aprobar", "validar", "dirigir", "coordinar"
        ],
        "forbidden_verbs": [
            "ejecutar", "efectuar", "tramitar", "gestionar", "procesar",
            "capturar", "registrar", "archivar", "coadyuvar", "apoyar", "auxiliar"
        ],
        "impact_profile": {
            "decision_scope": "strategic_national",
            "budget_range": "strategic",  # NO SE USA
            "error_consequences": "systemic",
            "complexity_level": "transformational"
        }
    },

    # NIVEL J: Jefatura de Unidad
    "J": {
        "level_name": "Jefatura de Unidad",
        "description": "Jefe de Unidad en la APF",
        "appropriate_verbs": [
            "normar", "establecer", "definir", "autorizar", "aprobar",
            "dirigir", "coordinar", "supervisar", "evaluar", "proponer"
        ],
        "forbidden_verbs": [
            "ejecutar", "efectuar", "tramitar", "capturar", "registrar",
            "archivar", "coadyuvar", "apoyar", "auxiliar"
        ],
        "impact_profile": {
            "decision_scope": "interinstitutional",
            "budget_range": "tactical",  # NO SE USA
            "error_consequences": "strategic",
            "complexity_level": "strategic"
        }
    },

    # NIVEL K: Dirección General Adjunta
    "K": {
        "level_name": "Dirección General Adjunta",
        "description": "Director General Adjunto en la APF",
        "appropriate_verbs": [
            "normar", "establecer", "definir", "autorizar", "aprobar",
            "dirigir", "coordinar", "supervisar", "evaluar", "proponer",
            "planificar", "diseñar"
        ],
        "forbidden_verbs": [
            "ejecutar", "efectuar", "tramitar", "capturar", "registrar",
            "archivar", "coadyuvar", "apoyar", "auxiliar"
        ],
        "impact_profile": {
            "decision_scope": "interinstitutional",
            "budget_range": "tactical",  # NO SE USA
            "error_consequences": "strategic",
            "complexity_level": "strategic"
        }
    },

    # NIVEL L: Dirección General
    "L": {
        "level_name": "Dirección General",
        "description": "Director General en la APF",
        "appropriate_verbs": [
            "normar", "establecer", "definir", "autorizar", "aprobar",
            "dirigir", "coordinar", "supervisar", "evaluar", "proponer",
            "planificar", "diseñar", "formular"
        ],
        "forbidden_verbs": [
            "ejecutar", "efectuar", "tramitar", "capturar", "registrar",
            "archivar", "coadyuvar", "apoyar", "auxiliar"
        ],
        "impact_profile": {
            "decision_scope": "institutional",
            "budget_range": "tactical",  # NO SE USA
            "error_consequences": "strategic",
            "complexity_level": "strategic"
        }
    },

    # NIVEL M: Dirección de Área
    "M": {
        "level_name": "Dirección de Área",
        "description": "Director de Área en la APF",
        "appropriate_verbs": [
            "establecer", "definir", "autorizar", "aprobar", "dirigir",
            "coordinar", "supervisar", "evaluar", "proponer", "planificar",
            "diseñar", "formular", "desarrollar", "elaborar"
        ],
        "forbidden_verbs": [
            "capturar", "registrar", "archivar", "coadyuvar", "apoyar", "auxiliar"
        ],
        "impact_profile": {
            "decision_scope": "institutional",
            "budget_range": "operational",  # NO SE USA
            "error_consequences": "tactical",
            "complexity_level": "analytical"
        }
    },

    # NIVEL N: Subdirección de Área
    "N": {
        "level_name": "Subdirección de Área",
        "description": "Subdirector de Área en la APF",
        "appropriate_verbs": [
            "definir", "autorizar", "aprobar", "coordinar", "supervisar",
            "evaluar", "proponer", "planificar", "diseñar", "formular",
            "desarrollar", "elaborar", "analizar", "revisar"
        ],
        "forbidden_verbs": [
            "capturar", "registrar", "archivar", "coadyuvar", "apoyar", "auxiliar"
        ],
        "impact_profile": {
            "decision_scope": "institutional",
            "budget_range": "operational",  # NO SE USA
            "error_consequences": "tactical",
            "complexity_level": "analytical"
        }
    },

    # NIVEL O: Jefatura de Departamento
    "O": {
        "level_name": "Jefatura de Departamento",
        "description": "Jefe de Departamento en la APF",
        "appropriate_verbs": [
            "coordinar", "supervisar", "evaluar", "proponer", "elaborar",
            "desarrollar", "analizar", "revisar", "ejecutar", "implementar",
            "verificar", "controlar", "programar"
        ],
        "forbidden_verbs": [
            "dictar", "normar", "sancionar", "expedir"
        ],
        "impact_profile": {
            "decision_scope": "local",
            "budget_range": "minimal",  # NO SE USA
            "error_consequences": "operational",
            "complexity_level": "routine"
        }
    },

    # NIVEL P: Enlace
    "P": {
        "level_name": "Enlace",
        "description": "Enlace en la APF",
        "appropriate_verbs": [
            "ejecutar", "efectuar", "elaborar", "desarrollar", "analizar",
            "revisar", "implementar", "verificar", "controlar", "registrar",
            "tramitar", "gestionar", "procesar", "capturar"
        ],
        "forbidden_verbs": [
            "dictar", "normar", "establecer", "sancionar", "expedir",
            "autorizar", "aprobar"
        ],
        "impact_profile": {
            "decision_scope": "local",
            "budget_range": "minimal",  # NO SE USA
            "error_consequences": "operational",
            "complexity_level": "routine"
        }
    }
}


# ==========================================
# MAPEOS Y UTILIDADES
# ==========================================

# Extrae solo la letra del nivel (ej: "M1" → "M")
def extract_level_letter(nivel: str) -> str:
    """
    Extrae la letra del nivel salarial.

    Args:
        nivel: Código de nivel (ej: "M1", "O21", "G")

    Returns:
        Letra del nivel (ej: "M", "O", "G")
    """
    if not nivel:
        return "P"  # Default: nivel más bajo

    # Tomar primer carácter
    letra = nivel[0].upper()

    # Validar que sea una letra válida
    if letra not in VERB_HIERARCHY:
        return "P"  # Default

    return letra


def get_level_profile(nivel: str) -> Dict[str, Any]:
    """
    Obtiene el perfil completo de un nivel.

    Args:
        nivel: Código de nivel (ej: "M1", "O21")

    Returns:
        Diccionario con el perfil del nivel
    """
    letra = extract_level_letter(nivel)
    return VERB_HIERARCHY.get(letra, VERB_HIERARCHY["P"])


def get_expected_impact_profile(nivel: str) -> Dict[str, str]:
    """
    Obtiene el perfil de impacto esperado para un nivel.

    Args:
        nivel: Código de nivel (ej: "M1", "O21")

    Returns:
        Diccionario con decision_scope, error_consequences, complexity_level
        (budget_range se incluye pero NO se usa en decisiones)
    """
    profile = get_level_profile(nivel)
    return profile.get("impact_profile", {
        "decision_scope": "local",
        "budget_range": "minimal",  # NO SE USA
        "error_consequences": "operational",
        "complexity_level": "routine"
    })


def get_acceptable_impact_ranges(nivel: str) -> Dict[str, List[str]]:
    """
    Obtiene los rangos de impacto ACEPTABLES para un nivel.

    A diferencia de get_expected_impact_profile que retorna el perfil IDEAL,
    esta función retorna TODOS los niveles de impacto que son APROPIADOS
    para el nivel jerárquico.

    Filosofía: Niveles altos pueden tener funciones con impacto variado.
    No todas las funciones de un Secretario deben ser "strategic_national".

    Args:
        nivel: Código de nivel (ej: "G11", "M1")

    Returns:
        Dict con listas de valores aceptables para cada dimensión:
        {
            "decision_scope": ["strategic_national", "interinstitutional", ...],
            "error_consequences": ["systemic", "strategic", ...],
            "complexity_level": ["transformational", "strategic", ...]
        }
    """
    letra = extract_level_letter(nivel)

    # Definir rangos por nivel
    # AJUSTE v5.39: Rangos más amplios para G/H - acepta CUALQUIER nivel excepto operacional
    ranges = {
        "G": {  # Secretaría
            "decision_scope": ["strategic_national", "interinstitutional", "institutional", "local"],
            "error_consequences": ["systemic", "strategic", "tactical", "operational"],
            "complexity_level": ["transformational", "innovative", "strategic", "analytical", "routine"]
        },
        "H": {  # Subsecretaría
            "decision_scope": ["strategic_national", "interinstitutional", "institutional", "local"],
            "error_consequences": ["systemic", "strategic", "tactical", "operational"],
            "complexity_level": ["transformational", "innovative", "strategic", "analytical", "routine"]
        },
        "J": {  # Jefatura de Unidad
            "decision_scope": ["interinstitutional", "institutional"],
            "error_consequences": ["strategic", "tactical"],
            "complexity_level": ["strategic", "analytical"]
        },
        "K": {  # DG Adjunto
            "decision_scope": ["interinstitutional", "institutional"],
            "error_consequences": ["strategic", "tactical"],
            "complexity_level": ["strategic", "analytical"]
        },
        "L": {  # Dirección General
            "decision_scope": ["institutional", "interinstitutional"],
            "error_consequences": ["strategic", "tactical"],
            "complexity_level": ["strategic", "analytical"]
        },
        "M": {  # Dirección de Área
            "decision_scope": ["institutional", "local"],
            "error_consequences": ["tactical", "operational"],
            "complexity_level": ["analytical", "routine"]
        },
        "N": {  # Subdirección
            "decision_scope": ["institutional", "local"],
            "error_consequences": ["tactical", "operational"],
            "complexity_level": ["analytical", "routine"]
        },
        "O": {  # Jefe de Departamento
            "decision_scope": ["local"],
            "error_consequences": ["operational", "tactical"],
            "complexity_level": ["routine", "analytical"]
        },
        "P": {  # Enlace
            "decision_scope": ["local"],
            "error_consequences": ["operational"],
            "complexity_level": ["routine"]
        }
    }

    return ranges.get(letra, ranges["P"])


def is_verb_appropriate(verbo: str, nivel: str) -> bool:
    """
    Verifica si un verbo es apropiado para el nivel.

    Args:
        verbo: Verbo en infinitivo (ej: "coordinar")
        nivel: Código de nivel (ej: "M1")

    Returns:
        True si el verbo está en la lista de apropiados
    """
    profile = get_level_profile(nivel)
    appropriate_verbs = profile.get("appropriate_verbs", [])
    return verbo.lower() in [v.lower() for v in appropriate_verbs]


def is_verb_forbidden(verbo: str, nivel: str) -> bool:
    """
    Verifica si un verbo está prohibido para el nivel.

    Args:
        verbo: Verbo en infinitivo (ej: "capturar")
        nivel: Código de nivel (ej: "M1")

    Returns:
        True si el verbo está en la lista de prohibidos
    """
    profile = get_level_profile(nivel)
    forbidden_verbs = profile.get("forbidden_verbs", [])
    return verbo.lower() in [v.lower() for v in forbidden_verbs]


def get_all_appropriate_verbs(nivel: str) -> List[str]:
    """
    Obtiene todos los verbos apropiados para un nivel.

    Args:
        nivel: Código de nivel (ej: "M1")

    Returns:
        Lista de verbos apropiados
    """
    profile = get_level_profile(nivel)
    return profile.get("appropriate_verbs", [])


def get_all_forbidden_verbs(nivel: str) -> List[str]:
    """
    Obtiene todos los verbos prohibidos para un nivel.

    Args:
        nivel: Código de nivel (ej: "M1")

    Returns:
        Lista de verbos prohibidos
    """
    profile = get_level_profile(nivel)
    return profile.get("forbidden_verbs", [])


# ==========================================
# JERARQUÍAS DE DIMENSIONES
# ==========================================

SCOPE_HIERARCHY: Dict[str, int] = {
    "local": 1,
    "institutional": 2,
    "interinstitutional": 3,
    "strategic_national": 4
}

CONSEQUENCES_HIERARCHY: Dict[str, int] = {
    "operational": 1,
    "tactical": 2,
    "strategic": 3,
    "systemic": 4
}

COMPLEXITY_HIERARCHY: Dict[str, int] = {
    "routine": 1,
    "analytical": 2,
    "strategic": 3,
    "transformational": 4,
    "innovative": 5
}

# NOTA: Budget no se usa en decisiones
BUDGET_HIERARCHY: Dict[str, int] = {
    "minimal": 1,
    "operational": 2,
    "tactical": 3,
    "strategic": 4,
    "executive": 5
}


# ==========================================
# TOLERANCIAS DE COHERENCIA
# ==========================================

COHERENCE_TOLERANCE: Dict[str, int] = {
    "scope": 1,           # ±1 nivel de alcance
    "consequences": 1,    # ±1 nivel de consecuencias
    "complexity": 1,      # ±1 nivel de complejidad
    # Budget no tiene tolerancia porque NO se usa
}
