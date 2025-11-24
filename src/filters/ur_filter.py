"""
Filtro por Unidad Responsable (UR).
Permite filtrar puestos por código de UR.
"""

from typing import List, Dict, Any, Set


class URFilter:
    """
    Filtra puestos por Unidad Responsable (UR).

    Ejemplos de uso:
        - UR única: ["27"]  (SABG)
        - Múltiples URs: ["27", "06", "21"]  (SABG, HACIENDA, TURISMO)
    """

    def __init__(self, ur_codes: List[str]):
        """
        Inicializa filtro de UR.

        Args:
            ur_codes: Lista de códigos de UR (ej: ["27", "06"])
        """
        # Normalizar a strings sin espacios
        self.ur_codes: Set[str] = set(str(code).strip() for code in ur_codes)

    def match(self, puesto_data: Dict[str, Any]) -> bool:
        """
        Verifica si el puesto pertenece a una de las URs especificadas.

        Args:
            puesto_data: Datos del puesto

        Returns:
            True si el UR del puesto está en la lista
        """
        ur = puesto_data.get('UR', '')

        # Manejar None y convertir a string
        if ur is None:
            return False

        ur_str = str(ur).strip()

        return ur_str in self.ur_codes

    def get_description(self) -> str:
        """Descripción del filtro"""
        urs_ordenadas = sorted(list(self.ur_codes))
        return f"Unidad Responsable: {', '.join(urs_ordenadas)}"
