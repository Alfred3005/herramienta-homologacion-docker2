"""
DataValidator - Validación de esquemas y datos

Implementa Single Responsibility Principle (SRP):
- Solo responsable de validar estructura y contenido de datos
- No extrae ni transforma datos (eso lo hacen otros módulos)
- Define esquemas esperados para puestos APF
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class ValidationSeverity(Enum):
    """Severidad de un problema de validación"""
    ERROR = "error"  # Dato faltante o inválido que impide procesamiento
    WARNING = "warning"  # Dato incompleto pero procesable
    INFO = "info"  # Sugerencia de mejora


@dataclass
class ValidationIssue:
    """Representa un problema encontrado durante validación"""
    field: str
    severity: ValidationSeverity
    message: str
    current_value: Any = None
    expected_type: Optional[str] = None


@dataclass
class ValidationResult:
    """Resultado de validación de datos"""
    is_valid: bool
    issues: List[ValidationIssue]
    data: Dict[str, Any]

    @property
    def errors(self) -> List[ValidationIssue]:
        """Retorna solo los errores"""
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> List[ValidationIssue]:
        """Retorna solo los warnings"""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    @property
    def error_count(self) -> int:
        """Cuenta de errores"""
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        """Cuenta de warnings"""
        return len(self.warnings)


class DataValidator:
    """
    Valida estructura y contenido de datos extraídos de puestos APF.

    Características:
    - Validación de esquema JSON
    - Validación de tipos de datos
    - Validación de campos requeridos
    - Validación de valores válidos
    - Detección de inconsistencias
    """

    # Campos requeridos en identificación_puesto
    REQUIRED_IDENTIFICACION = [
        "denominacion_puesto"
    ]

    # Campos requeridos en objetivo_general
    REQUIRED_OBJETIVO = [
        "descripcion_completa",
        "verbo_accion"
    ]

    # Campos requeridos en cada función
    REQUIRED_FUNCION = [
        "numero",
        "verbo_accion",
        "descripcion_completa"
    ]

    # Niveles salariales válidos (códigos comunes)
    VALID_NIVEL_CODES = ["G", "M", "N", "O", "P"]  # Gabinete, Mando, Enlace, Operativo, Honorarios

    def __init__(self, strict_mode: bool = False):
        """
        Inicializa el validador.

        Args:
            strict_mode: Si True, warnings se tratan como errores
        """
        self.strict_mode = strict_mode

    def validate_extraction(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Valida datos extraídos de un puesto.

        Args:
            data: Diccionario con datos extraídos

        Returns:
            ValidationResult con resultados de validación
        """
        issues: List[ValidationIssue] = []

        # Validar estructura de alto nivel
        if not isinstance(data, dict):
            issues.append(ValidationIssue(
                field="root",
                severity=ValidationSeverity.ERROR,
                message="Los datos deben ser un diccionario",
                current_value=type(data).__name__,
                expected_type="dict"
            ))
            return ValidationResult(is_valid=False, issues=issues, data=data)

        # Validar secciones principales
        self._validate_identificacion(data.get("identificacion_puesto"), issues)
        self._validate_objetivo(data.get("objetivo_general"), issues)
        self._validate_funciones(data.get("funciones"), issues)

        # Determinar si es válido
        error_count = sum(1 for i in issues if i.severity == ValidationSeverity.ERROR)
        is_valid = error_count == 0

        if self.strict_mode:
            warning_count = sum(1 for i in issues if i.severity == ValidationSeverity.WARNING)
            is_valid = is_valid and warning_count == 0

        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            data=data
        )

    def _validate_identificacion(
        self,
        identificacion: Optional[Dict[str, Any]],
        issues: List[ValidationIssue]
    ):
        """Valida sección de identificación del puesto"""
        if identificacion is None:
            issues.append(ValidationIssue(
                field="identificacion_puesto",
                severity=ValidationSeverity.ERROR,
                message="Falta sección 'identificacion_puesto'",
                current_value=None
            ))
            return

        if not isinstance(identificacion, dict):
            issues.append(ValidationIssue(
                field="identificacion_puesto",
                severity=ValidationSeverity.ERROR,
                message="'identificacion_puesto' debe ser un diccionario",
                current_value=type(identificacion).__name__,
                expected_type="dict"
            ))
            return

        # Validar campos requeridos
        for field in self.REQUIRED_IDENTIFICACION:
            if field not in identificacion or identificacion[field] is None:
                issues.append(ValidationIssue(
                    field=f"identificacion_puesto.{field}",
                    severity=ValidationSeverity.ERROR,
                    message=f"Campo requerido '{field}' faltante o null",
                    current_value=identificacion.get(field)
                ))
            elif not isinstance(identificacion[field], str) or not identificacion[field].strip():
                issues.append(ValidationIssue(
                    field=f"identificacion_puesto.{field}",
                    severity=ValidationSeverity.ERROR,
                    message=f"Campo '{field}' debe ser un string no vacío",
                    current_value=identificacion[field]
                ))

        # Validar nivel salarial si existe
        if "nivel_salarial" in identificacion and identificacion["nivel_salarial"]:
            nivel = identificacion["nivel_salarial"]
            if isinstance(nivel, dict):
                codigo = nivel.get("codigo", "")
                if codigo and isinstance(codigo, str):
                    primer_letra = codigo[0].upper() if codigo else ""
                    if primer_letra not in self.VALID_NIVEL_CODES:
                        issues.append(ValidationIssue(
                            field="identificacion_puesto.nivel_salarial.codigo",
                            severity=ValidationSeverity.WARNING,
                            message=f"Código de nivel '{codigo}' no reconocido",
                            current_value=codigo
                        ))

    def _validate_objetivo(
        self,
        objetivo: Optional[Dict[str, Any]],
        issues: List[ValidationIssue]
    ):
        """Valida sección de objetivo general"""
        if objetivo is None:
            issues.append(ValidationIssue(
                field="objetivo_general",
                severity=ValidationSeverity.WARNING,
                message="Falta sección 'objetivo_general'",
                current_value=None
            ))
            return

        if not isinstance(objetivo, dict):
            issues.append(ValidationIssue(
                field="objetivo_general",
                severity=ValidationSeverity.ERROR,
                message="'objetivo_general' debe ser un diccionario",
                current_value=type(objetivo).__name__,
                expected_type="dict"
            ))
            return

        # Validar campos requeridos
        for field in self.REQUIRED_OBJETIVO:
            if field not in objetivo or objetivo[field] is None:
                issues.append(ValidationIssue(
                    field=f"objetivo_general.{field}",
                    severity=ValidationSeverity.WARNING,
                    message=f"Campo '{field}' faltante o null",
                    current_value=objetivo.get(field)
                ))
            elif not isinstance(objetivo[field], str) or not objetivo[field].strip():
                issues.append(ValidationIssue(
                    field=f"objetivo_general.{field}",
                    severity=ValidationSeverity.WARNING,
                    message=f"Campo '{field}' debe ser un string no vacío",
                    current_value=objetivo[field]
                ))

    def _validate_funciones(
        self,
        funciones: Optional[List[Dict[str, Any]]],
        issues: List[ValidationIssue]
    ):
        """Valida sección de funciones"""
        if funciones is None:
            issues.append(ValidationIssue(
                field="funciones",
                severity=ValidationSeverity.ERROR,
                message="Falta sección 'funciones'",
                current_value=None
            ))
            return

        if not isinstance(funciones, list):
            issues.append(ValidationIssue(
                field="funciones",
                severity=ValidationSeverity.ERROR,
                message="'funciones' debe ser una lista",
                current_value=type(funciones).__name__,
                expected_type="list"
            ))
            return

        if len(funciones) == 0:
            issues.append(ValidationIssue(
                field="funciones",
                severity=ValidationSeverity.ERROR,
                message="La lista de funciones está vacía",
                current_value=[]
            ))
            return

        # Validar cada función
        for idx, funcion in enumerate(funciones):
            if not isinstance(funcion, dict):
                issues.append(ValidationIssue(
                    field=f"funciones[{idx}]",
                    severity=ValidationSeverity.ERROR,
                    message=f"La función {idx} debe ser un diccionario",
                    current_value=type(funcion).__name__,
                    expected_type="dict"
                ))
                continue

            # Validar campos requeridos de la función
            for field in self.REQUIRED_FUNCION:
                if field not in funcion or funcion[field] is None:
                    issues.append(ValidationIssue(
                        field=f"funciones[{idx}].{field}",
                        severity=ValidationSeverity.ERROR,
                        message=f"Campo requerido '{field}' faltante en función {idx+1}",
                        current_value=funcion.get(field)
                    ))

            # Validar que el número sea correcto
            numero = funcion.get("numero")
            if numero is not None and numero != idx + 1:
                issues.append(ValidationIssue(
                    field=f"funciones[{idx}].numero",
                    severity=ValidationSeverity.WARNING,
                    message=f"Número de función inconsistente: esperado {idx+1}, encontrado {numero}",
                    current_value=numero
                ))

    def validate_quick(self, data: Dict[str, Any]) -> bool:
        """
        Validación rápida: solo verifica si tiene lo mínimo requerido.

        Args:
            data: Datos a validar

        Returns:
            True si tiene los campos mínimos
        """
        try:
            has_denominacion = (
                isinstance(data.get("identificacion_puesto"), dict) and
                data["identificacion_puesto"].get("denominacion_puesto")
            )
            has_funciones = (
                isinstance(data.get("funciones"), list) and
                len(data["funciones"]) > 0
            )
            return has_denominacion and has_funciones
        except:
            return False
