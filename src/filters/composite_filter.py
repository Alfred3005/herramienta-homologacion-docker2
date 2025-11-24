"""
Filtro compuesto que combina múltiples filtros.
Soporta lógica AND y OR.
"""

from typing import List, Dict, Any
from .base_filter import PuestoFilter


class CompositeFilter:
    """
    Combina múltiples filtros con lógica AND u OR.

    Ejemplos de uso:
        - AND: Nivel G-K AND UR=27
        - OR: Nivel K OR Nivel L OR Nivel M
        - Complejo: (Nivel G-K AND UR=27) OR (Nivel L-M AND UR=06)
    """

    def __init__(self, filters: List[PuestoFilter], logic: str = "AND"):
        """
        Inicializa filtro compuesto.

        Args:
            filters: Lista de filtros a combinar
            logic: "AND" o "OR" para combinar filtros

        Raises:
            ValueError: Si logic no es "AND" o "OR"
        """
        self.filters = filters
        self.logic = logic.upper()

        if self.logic not in ["AND", "OR"]:
            raise ValueError(f"Logic debe ser 'AND' o 'OR', recibido: {logic}")

    def match(self, puesto_data: Dict[str, Any]) -> bool:
        """
        Verifica si el puesto cumple con la combinación de filtros.

        Args:
            puesto_data: Datos del puesto

        Returns:
            True si cumple con la lógica especificada
        """
        if not self.filters:
            return True  # Sin filtros = todos pasan

        if self.logic == "AND":
            # Todos los filtros deben pasar
            return all(f.match(puesto_data) for f in self.filters)
        else:  # OR
            # Al menos un filtro debe pasar
            return any(f.match(puesto_data) for f in self.filters)

    def get_description(self) -> str:
        """Descripción del filtro"""
        if not self.filters:
            return "Sin filtros"

        descripciones = [f.get_description() for f in self.filters]

        if len(descripciones) == 1:
            return descripciones[0]

        separador = f" {self.logic} "
        return f"({separador.join(descripciones)})"

    def add_filter(self, filtro: PuestoFilter):
        """
        Agrega un filtro al composite.

        Args:
            filtro: Filtro a agregar
        """
        self.filters.append(filtro)

    def clear_filters(self):
        """Elimina todos los filtros"""
        self.filters.clear()
