"""
Filtro base para puestos.
Define la interface que todos los filtros deben implementar.
"""

from typing import Protocol, Dict, Any


class PuestoFilter(Protocol):
    """
    Interface para filtros de puestos.

    Implementa patrón Strategy - permite agregar nuevos filtros
    sin modificar código existente (Open/Closed Principle).
    """

    def match(self, puesto_data: Dict[str, Any]) -> bool:
        """
        Determina si un puesto cumple con el criterio del filtro.

        Args:
            puesto_data: Diccionario con datos del puesto (fila del DataFrame)

        Returns:
            True si el puesto cumple el criterio, False en caso contrario
        """
        ...

    def get_description(self) -> str:
        """
        Obtiene descripción legible del filtro para logs y reportes.

        Returns:
            String describiendo el filtro
        """
        ...
