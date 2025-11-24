"""
Generador de reportes consolidados para procesamiento en lote.
Soporta múltiples formatos de salida (Excel, JSON, HTML).
"""

from typing import List, Dict, Any
from pathlib import Path
import json
from datetime import datetime

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class BatchReporter:
    """
    Genera reportes consolidados de procesamiento en lote.

    Soporta:
    - Reportes en Excel (múltiples hojas)
    - Reportes en JSON
    - Estadísticas agregadas
    - Análisis por nivel salarial
    """

    def __init__(self, resultado_batch: Any):
        """
        Inicializa reporter con resultado de batch.

        Args:
            resultado_batch: BatchProcessingResult del procesamiento
        """
        self.resultado = resultado_batch

    def generar_reporte_excel(self, archivo: str):
        """
        Genera reporte completo en Excel con múltiples hojas.

        Args:
            archivo: Ruta del archivo Excel de salida

        Raises:
            ImportError: Si pandas no está disponible
        """
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas requerido para generar reportes Excel. Instalar con: pip install pandas openpyxl")

        print(f"📊 Generando reporte Excel: {archivo}")

        with pd.ExcelWriter(archivo, engine='openpyxl') as writer:
            # Hoja 1: Resumen
            self._generar_hoja_resumen(writer)

            # Hoja 2: Detalle de puestos
            self._generar_hoja_detalle(writer)

            # Hoja 3: Errores (si hay)
            self._generar_hoja_errores(writer)

            # Hoja 4: Estadísticas por nivel
            self._generar_hoja_estadisticas_nivel(writer)

        print(f"✅ Reporte Excel generado: {archivo}")

    def _generar_hoja_resumen(self, writer):
        """Genera hoja de resumen general"""
        tasa_exito = (self.resultado.exitosos / self.resultado.procesados * 100) if self.resultado.procesados > 0 else 0

        datos_resumen = {
            "Métrica": [
                "Total de puestos encontrados",
                "Puestos procesados",
                "Puestos exitosos",
                "Puestos fallidos",
                "Tasa de éxito (%)",
                "Tiempo inicio",
                "Tiempo fin",
                "Duración (segundos)",
                "Filtros aplicados"
            ],
            "Valor": [
                self.resultado.total_puestos,
                self.resultado.procesados,
                self.resultado.exitosos,
                self.resultado.fallidos,
                f"{tasa_exito:.1f}",
                self.resultado.tiempo_inicio,
                self.resultado.tiempo_fin,
                f"{self.resultado.duracion_segundos:.1f}",
                len(self.resultado.filtros_aplicados)
            ]
        }

        df_resumen = pd.DataFrame(datos_resumen)
        df_resumen.to_excel(writer, sheet_name='Resumen', index=False)

        # Agregar filtros en otra tabla
        if self.resultado.filtros_aplicados:
            df_filtros = pd.DataFrame({
                "Filtro": self.resultado.filtros_aplicados
            })
            df_filtros.to_excel(writer, sheet_name='Resumen', index=False, startrow=len(datos_resumen["Métrica"]) + 3)

    def _generar_hoja_detalle(self, writer):
        """Genera hoja con detalle de cada puesto"""
        datos_detalle = []

        for resultado in self.resultado.resultados:
            datos_detalle.append({
                "Código": resultado.get("codigo", "N/A"),
                "Denominación": resultado.get("denominacion", "N/A"),
                "Nivel": resultado.get("nivel", "N/A"),
                "UR": resultado.get("ur", "N/A"),
                "Status": resultado.get("status", "N/A"),
                "Conversión": resultado.get("conversion_status", "N/A"),
                "Num. Funciones": resultado.get("num_funciones", 0),
                "Documento": Path(resultado.get("documento_path", "")).name if resultado.get("documento_path") else "N/A",
                "Error": resultado.get("error", "")
            })

        df_detalle = pd.DataFrame(datos_detalle)
        df_detalle.to_excel(writer, sheet_name='Detalle', index=False)

    def _generar_hoja_errores(self, writer):
        """Genera hoja con puestos que tuvieron errores"""
        errores = [r for r in self.resultado.resultados if r.get("status") != "success"]

        if not errores:
            # Crear hoja vacía con mensaje
            df_errores = pd.DataFrame({
                "Mensaje": ["No se encontraron errores"]
            })
        else:
            datos_errores = []
            for error in errores:
                datos_errores.append({
                    "Código": error.get("codigo", "N/A"),
                    "Status": error.get("status", "N/A"),
                    "Error": error.get("error", "N/A")
                })

            df_errores = pd.DataFrame(datos_errores)

        df_errores.to_excel(writer, sheet_name='Errores', index=False)

    def _generar_hoja_estadisticas_nivel(self, writer):
        """Genera hoja con estadísticas por nivel salarial"""
        # Agrupar por nivel
        stats_por_nivel = {}

        for resultado in self.resultado.resultados:
            nivel = resultado.get("nivel", "N/A")

            if nivel not in stats_por_nivel:
                stats_por_nivel[nivel] = {
                    "total": 0,
                    "exitosos": 0,
                    "fallidos": 0
                }

            stats_por_nivel[nivel]["total"] += 1

            if resultado.get("status") == "success":
                stats_por_nivel[nivel]["exitosos"] += 1
            else:
                stats_por_nivel[nivel]["fallidos"] += 1

        # Convertir a DataFrame
        datos_nivel = []
        for nivel, stats in sorted(stats_por_nivel.items()):
            tasa = (stats["exitosos"] / stats["total"] * 100) if stats["total"] > 0 else 0
            datos_nivel.append({
                "Nivel": nivel,
                "Total": stats["total"],
                "Exitosos": stats["exitosos"],
                "Fallidos": stats["fallidos"],
                "Tasa Éxito (%)": f"{tasa:.1f}"
            })

        df_nivel = pd.DataFrame(datos_nivel)
        df_nivel.to_excel(writer, sheet_name='Por Nivel', index=False)

    def generar_reporte_json(self, archivo: str):
        """
        Genera reporte en formato JSON.

        Args:
            archivo: Ruta del archivo JSON de salida
        """
        self.resultado.exportar_json(archivo)

    def generar_resumen_texto(self, archivo: str):
        """
        Genera resumen en texto plano.

        Args:
            archivo: Ruta del archivo de texto de salida
        """
        with open(archivo, 'w', encoding='utf-8') as f:
            f.write(self.resultado.get_summary())

        print(f"✅ Resumen guardado en: {archivo}")

    def get_estadisticas_por_nivel(self) -> Dict[str, Dict[str, int]]:
        """
        Calcula estadísticas agrupadas por nivel salarial.

        Returns:
            Dict con estadísticas por nivel
        """
        stats_por_nivel = {}

        for resultado in self.resultado.resultados:
            nivel = resultado.get("nivel", "N/A")

            if nivel not in stats_por_nivel:
                stats_por_nivel[nivel] = {
                    "total": 0,
                    "exitosos": 0,
                    "fallidos": 0,
                    "puestos": []
                }

            stats_por_nivel[nivel]["total"] += 1
            stats_por_nivel[nivel]["puestos"].append(resultado.get("codigo", "N/A"))

            if resultado.get("status") == "success":
                stats_por_nivel[nivel]["exitosos"] += 1
            else:
                stats_por_nivel[nivel]["fallidos"] += 1

        return stats_por_nivel

    def imprimir_estadisticas_por_nivel(self):
        """Imprime estadísticas por nivel en consola"""
        stats = self.get_estadisticas_por_nivel()

        print(f"\n{'='*70}")
        print("📊 ESTADÍSTICAS POR NIVEL SALARIAL")
        print(f"{'='*70}\n")

        for nivel in sorted(stats.keys()):
            data = stats[nivel]
            tasa = (data["exitosos"] / data["total"] * 100) if data["total"] > 0 else 0

            print(f"Nivel {nivel}:")
            print(f"  Total: {data['total']}")
            print(f"  Exitosos: {data['exitosos']} ({tasa:.1f}%)")
            print(f"  Fallidos: {data['fallidos']}")
            print()
