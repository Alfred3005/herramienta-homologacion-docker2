"""
Interface para proveedores de cache

Implementa el principio de Segregación de Interfaces (ISP):
- Interface pequeña con solo los métodos necesarios para caching
- Los clientes solo dependen de lo que necesitan
"""

from typing import Protocol, Any, Optional
from datetime import timedelta


class ICacheProvider(Protocol):
    """
    Interface para proveedores de cache.

    Implementaciones pueden usar:
    - Cache en memoria (dict)
    - Redis
    - Memcached
    - Archivos pickle
    """

    def get(self, key: str) -> Optional[Any]:
        """
        Obtiene un valor del cache.

        Args:
            key: Clave del valor a obtener

        Returns:
            Valor almacenado o None si no existe
        """
        ...

    def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> None:
        """
        Almacena un valor en el cache.

        Args:
            key: Clave bajo la cual almacenar el valor
            value: Valor a almacenar
            ttl: Time-to-live opcional (tiempo de expiración)
        """
        ...

    def delete(self, key: str) -> bool:
        """
        Elimina un valor del cache.

        Args:
            key: Clave del valor a eliminar

        Returns:
            True si se eliminó, False si no existía
        """
        ...

    def exists(self, key: str) -> bool:
        """
        Verifica si una clave existe en el cache.

        Args:
            key: Clave a verificar

        Returns:
            True si existe, False en caso contrario
        """
        ...

    def clear(self) -> None:
        """
        Limpia todo el cache.
        """
        ...

    def get_stats(self) -> dict:
        """
        Obtiene estadísticas del cache.

        Returns:
            Dict con estadísticas (hits, misses, size, etc.)
        """
        ...
