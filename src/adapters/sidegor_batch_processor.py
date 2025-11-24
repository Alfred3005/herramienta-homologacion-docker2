"""
Procesador en lote de puestos desde Excel Sidegor.
Coordina filtrado, conversión a RHNet y validación masiva.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field
import json
from datetime import datetime

from .sidegor_adapter import SidegorAdapter
from .rhnet_document_generator import RHNetDocumentGenerator
from ..filters.base_filter import PuestoFilter


@dataclass
class BatchProcessingResult:
    """Resultado de procesamiento en lote"""
    total_puestos: int
    procesados: int
    exitosos: int
    fallidos: int
    resultados: List[Dict[str, Any]]
    filtros_aplicados: List[str] = field(default_factory=list)
    tiempo_inicio: str = ""
    tiempo_fin: str = ""
    duracion_segundos: float = 0.0

    def get_summary(self) -> str:
        """Genera resumen textual"""
        tasa_exito = (self.exitosos / self.procesados * 100) if self.procesados > 0 else 0

        summary = f"""
📊 RESUMEN DE PROCESAMIENTO EN LOTE
{'='*70}
Inicio: {self.tiempo_inicio}
Fin: {self.tiempo_fin}
Duración: {self.duracion_segundos:.1f} segundos

Total de puestos encontrados: {self.total_puestos}
Procesados: {self.procesados}
Exitosos: {self.exitosos} ({tasa_exito:.1f}%)
Fallidos: {self.fallidos}

Filtros aplicados ({len(self.filtros_aplicados)}):
"""
        for filtro in self.filtros_aplicados:
            summary += f"  • {filtro}\n"

        return summary

    def exportar_json(self, archivo: str):
        """
        Exporta resultado a archivo JSON.

        Args:
            archivo: Ruta del archivo de salida
        """
        # Crear directorio si no existe
        Path(archivo).parent.mkdir(parents=True, exist_ok=True)

        data = {
            "resumen": {
                "total_puestos": self.total_puestos,
                "procesados": self.procesados,
                "exitosos": self.exitosos,
                "fallidos": self.fallidos,
                "tasa_exito": (self.exitosos / self.procesados * 100) if self.procesados > 0 else 0,
                "tiempo_inicio": self.tiempo_inicio,
                "tiempo_fin": self.tiempo_fin,
                "duracion_segundos": self.duracion_segundos
            },
            "filtros_aplicados": self.filtros_aplicados,
            "resultados": self.resultados
        }

        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✅ Resultado exportado a: {archivo}")


class SidegorBatchProcessor:
    """
    Procesador en lote de puestos desde Excel Sidegor.

    Coordina:
    1. Filtrado de puestos según criterios
    2. Conversión a formato APF
    3. Generación de documentos RHNet
    4. Validación (opcional) con pipeline APF
    """

    def __init__(self,
                 adapter: SidegorAdapter,
                 document_generator: RHNetDocumentGenerator,
                 validation_pipeline: Optional[Any] = None):
        """
        Inicializa procesador en lote.

        Args:
            adapter: Adaptador Sidegor con archivo cargado
            document_generator: Generador de documentos RHNet
            validation_pipeline: Pipeline APF para validación (opcional)
        """
        self.adapter = adapter
        self.generator = document_generator
        self.pipeline = validation_pipeline
        self.filtros: List[PuestoFilter] = []

    def add_filter(self, filtro: PuestoFilter):
        """
        Agrega filtro al procesador.

        Args:
            filtro: Filtro a agregar
        """
        self.filtros.append(filtro)

    def clear_filters(self):
        """Limpia todos los filtros"""
        self.filtros.clear()

    def obtener_puestos_filtrados(self) -> List[Dict[str, Any]]:
        """
        Obtiene todos los puestos que cumplen los filtros.

        Returns:
            Lista de diccionarios con datos de puestos filtrados
        """
        if not self.adapter.extractor:
            raise ValueError("Adaptador no tiene archivo cargado")

        df_puestos = self.adapter.extractor.get_all_puestos()
        puestos_filtrados = []

        for idx, row in df_puestos.iterrows():
            puesto_dict = row.to_dict()

            # Aplicar todos los filtros (AND lógico)
            if all(f.match(puesto_dict) for f in self.filtros):
                puestos_filtrados.append(puesto_dict)

        return puestos_filtrados

    def procesar_lote(self,
                     validar: bool = False,
                     generar_documentos: bool = True,
                     output_dir: str = "output/batch",
                     guardar_intermedios: bool = True) -> BatchProcessingResult:
        """
        Procesa lote completo de puestos filtrados.

        Args:
            validar: Si ejecutar validación con pipeline (requiere pipeline configurado)
            generar_documentos: Si generar documentos RHNet
            output_dir: Directorio de salida
            guardar_intermedios: Si guardar archivos intermedios (docs RHNet, JSONs APF)

        Returns:
            BatchProcessingResult con estadísticas y resultados
        """
        tiempo_inicio = datetime.now()

        print(f"\n{'='*70}")
        print("🚀 PROCESAMIENTO EN LOTE - SIDEGOR")
        print(f"{'='*70}\n")

        # Obtener puestos filtrados
        print(f"🔍 Aplicando filtros...")
        print(f"   Filtros activos: {len(self.filtros)}")
        for filtro in self.filtros:
            print(f"   • {filtro.get_description()}")

        puestos = self.obtener_puestos_filtrados()

        print(f"\n📋 Puestos encontrados: {len(puestos)}")

        if len(puestos) == 0:
            print("⚠️ No se encontraron puestos con los filtros especificados")
            return BatchProcessingResult(
                total_puestos=0,
                procesados=0,
                exitosos=0,
                fallidos=0,
                resultados=[],
                filtros_aplicados=[f.get_description() for f in self.filtros],
                tiempo_inicio=tiempo_inicio.strftime("%Y-%m-%d %H:%M:%S"),
                tiempo_fin=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                duracion_segundos=0.0
            )

        # Crear directorios de salida
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        if guardar_intermedios:
            (output_path / "documentos").mkdir(exist_ok=True)
            (output_path / "datos_apf").mkdir(exist_ok=True)

        print(f"📁 Directorio de salida: {output_dir}")
        print(f"\n{'='*70}")
        print("PROCESANDO PUESTOS")
        print(f"{'='*70}\n")

        # Procesar cada puesto
        resultados = []

        for i, puesto_data in enumerate(puestos, 1):
            codigo = puesto_data.get('CÓDIGO_DE_PUESTO', 'UNKNOWN')

            print(f"[{i}/{len(puestos)}] Procesando: {codigo}")

            try:
                # 1. Convertir a formato APF
                datos_apf = self.adapter.convertir_puesto(codigo)

                if "error" in datos_apf:
                    print(f"  ❌ Error en conversión: {datos_apf['error']}")
                    resultados.append({
                        "codigo": codigo,
                        "status": "error_conversion",
                        "error": datos_apf["error"]
                    })
                    continue

                # Guardar datos APF
                if guardar_intermedios:
                    apf_path = output_path / "datos_apf" / f"{codigo.replace('/', '_')}_apf.json"
                    with open(apf_path, 'w', encoding='utf-8') as f:
                        json.dump(datos_apf, f, ensure_ascii=False, indent=2)

                # 2. Generar documento RHNet virtual
                doc_rhnet = None
                doc_path = None

                if generar_documentos:
                    doc_rhnet = self.generator.generar_documento(datos_apf)

                    # Guardar documento
                    doc_path = output_path / "documentos" / f"{codigo.replace('/', '_')}_rhnet.txt"
                    with open(doc_path, 'w', encoding='utf-8') as f:
                        f.write(doc_rhnet)
                    print(f"  📄 Documento generado")

                # 3. Validar (si está habilitado)
                resultado_validacion = None

                if validar and self.pipeline and doc_rhnet and doc_path:
                    print(f"  🔍 Validando...")
                    try:
                        resultado_validacion = self.pipeline.extract_from_file(str(doc_path))
                        status_validacion = resultado_validacion.get('status', 'unknown')
                        print(f"  ✅ Validación: {status_validacion}")
                    except Exception as e:
                        print(f"  ⚠️ Error en validación: {str(e)}")
                        resultado_validacion = {"error": str(e)}

                # Consolidar resultado
                resultados.append({
                    "codigo": codigo,
                    "denominacion": datos_apf.get("identificacion_puesto", {}).get("denominacion_puesto"),
                    "nivel": puesto_data.get('GRADO'),
                    "ur": puesto_data.get('UR'),
                    "status": "success",
                    "conversion_status": datos_apf.get("conversion_status"),
                    "num_funciones": len(datos_apf.get("funciones", [])),
                    "documento_path": str(doc_path) if doc_path else None,
                    "validacion": resultado_validacion
                })

                print(f"  ✅ Completado\n")

            except Exception as e:
                print(f"  ❌ Error procesando: {str(e)}\n")
                resultados.append({
                    "codigo": codigo,
                    "status": "error",
                    "error": str(e)
                })

        # Consolidar resultado
        tiempo_fin = datetime.now()
        duracion = (tiempo_fin - tiempo_inicio).total_seconds()

        resultado_final = self._consolidar_resultados(
            resultados,
            puestos,
            tiempo_inicio,
            tiempo_fin,
            duracion
        )

        # Mostrar resumen
        print(f"\n{'='*70}")
        print(resultado_final.get_summary())
        print(f"{'='*70}\n")

        return resultado_final

    def _consolidar_resultados(self,
                               resultados: List[Dict],
                               puestos_originales: List[Dict],
                               tiempo_inicio: datetime,
                               tiempo_fin: datetime,
                               duracion: float) -> BatchProcessingResult:
        """Consolida resultados de procesamiento en lote"""
        exitosos = sum(1 for r in resultados if r.get("status") == "success")
        fallidos = len(resultados) - exitosos

        return BatchProcessingResult(
            total_puestos=len(puestos_originales),
            procesados=len(resultados),
            exitosos=exitosos,
            fallidos=fallidos,
            resultados=resultados,
            filtros_aplicados=[f.get_description() for f in self.filtros],
            tiempo_inicio=tiempo_inicio.strftime("%Y-%m-%d %H:%M:%S"),
            tiempo_fin=tiempo_fin.strftime("%Y-%m-%d %H:%M:%S"),
            duracion_segundos=duracion
        )
