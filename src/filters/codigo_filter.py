"""
Filtro por patrón de código de puesto.
Soporta wildcards para filtrado flexible.
"""

from typing import List, Dict, Any
import re


class CodigoPuestoFilter:
    """
    Filtra puestos por patrón de código.

    Soporta wildcards:
        - "*" coincide con cualquier secuencia de caracteres
        - "?" coincide con un solo carácter

    Ejemplos de uso:
        - Código exacto: ["27-100-1-M1C035P-0000661-E-X-V"]
        - Wildcards: ["27-100-*", "27-244-*"]
        - Prefijo: ["27-*"]
        - Múltiples patrones: ["27-100-*", "06-200-*"]
    """

    def __init__(self, patrones: List[str]):
        """
        Inicializa filtro de código de puesto.

        Args:
            patrones: Lista de patrones (pueden incluir wildcards)
        """
        self.patrones = patrones
        # Compilar patrones regex para eficiencia
        self.regex_patrones = [self._compile_pattern(p) for p in patrones]

    def _compile_pattern(self, pattern: str) -> re.Pattern:
        """
        Convierte patrón con wildcards a expresión regular.

        Args:
            pattern: Patrón con wildcards (* y ?)

        Returns:
            Patrón regex compilado
        """
        # Escapar caracteres especiales de regex excepto * y ?
        escaped = re.escape(pattern)

        # Reemplazar wildcards escapados con regex equivalentes
        regex_pattern = escaped.replace(r'\*', '.*').replace(r'\?', '.')

        # Anclar al inicio y fin
        regex_pattern = f'^{regex_pattern}$'

        return re.compile(regex_pattern)

    def match(self, puesto_data: Dict[str, Any]) -> bool:
        """
        Verifica si el código del puesto coincide con algún patrón.

        Args:
            puesto_data: Datos del puesto

        Returns:
            True si el código coincide con al menos un patrón
        """
        codigo = puesto_data.get('CÓDIGO_DE_PUESTO', '')

        # Manejar None
        if codigo is None:
            return False

        codigo_str = str(codigo).strip()

        # Verificar contra todos los patrones
        return any(regex.match(codigo_str) for regex in self.regex_patrones)

    def get_description(self) -> str:
        """Descripción del filtro"""
        if len(self.patrones) == 1:
            return f"Código de puesto: {self.patrones[0]}"
        else:
            return f"Códigos de puesto: {len(self.patrones)} patrones"
