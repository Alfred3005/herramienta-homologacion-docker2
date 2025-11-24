"""
Adaptador para integrar datos de Excel Sidegor al pipeline APF.
Convierte estructura tabular/relacional a formato esperado por APFExtractor.

Basado en el script original degor_emulador_rhnet.ipynb
Refactorizado para cumplir con principios SOLID.
"""

import pandas as pd
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import re

warnings.filterwarnings('ignore')


# Mapeo de hojas Excel a secciones del schema APF
SHEET_MAPPING = {
    'PUESTOS': 'identificacion_puesto',
    'OBJ_FUNCIONES': 'funciones_y_objetivo',
    'ESCOLARIDAD': 'escolaridad',
    'EXP_LAB': 'experiencia',
    'COMPETENCIAS': 'competencias',
    'COND_TRABAJO': 'condiciones_trabajo',
    'ASPE_RELEV': 'aspectos_relevantes',
    'ENT_OPER': 'entorno_operativo',
    'CAP_PROF': 'capacidades_profesionales',
    'OBSERVACIONES': 'observaciones',
    'CAPACIDADES': 'capacidades_tecnicas'
}


class SidegorExtractor:
    """
    Extractor de información de puestos desde archivos Excel de Sidegor.
    """

    def __init__(self, archivo_excel: str):
        """
        Inicializa el extractor de Sidegor.

        Args:
            archivo_excel: Ruta al archivo Excel de Sidegor
        """
        self.archivo = archivo_excel
        self.archivo_path = Path(archivo_excel)
        self.hojas = {}
        self.hojas_cargadas = []
        self.errores_carga = []

        # Estadísticas
        self.stats = {
            "archivo": self.archivo_path.name,
            "hojas_disponibles": 0,
            "hojas_cargadas": 0,
            "codigos_encontrados": 0,
            "timestamp": datetime.now().isoformat()
        }

    def cargar_archivo(self) -> bool:
        """
        Carga todas las hojas esperadas del archivo Excel.

        Returns:
            True si se cargó al menos una hoja crítica
        """
        print(f"📂 Cargando archivo: {self.archivo_path.name}")

        try:
            excel_file = pd.ExcelFile(self.archivo)
            hojas_disponibles = excel_file.sheet_names

            self.stats["hojas_disponibles"] = len(hojas_disponibles)

            for hoja_nombre in SHEET_MAPPING.keys():
                if hoja_nombre in hojas_disponibles:
                    try:
                        df = pd.read_excel(self.archivo, sheet_name=hoja_nombre)

                        # Limpiar nombres de columnas
                        df.columns = [
                            col.strip() if isinstance(col, str) else col
                            for col in df.columns
                        ]

                        self.hojas[hoja_nombre] = df
                        self.hojas_cargadas.append(hoja_nombre)
                        print(f"  ✅ {hoja_nombre}: {len(df)} registros, {len(df.columns)} columnas")

                    except Exception as e:
                        error_msg = f"Error cargando hoja {hoja_nombre}: {str(e)}"
                        self.errores_carga.append(error_msg)
                        print(f"  ⚠️ {error_msg}")
                else:
                    print(f"  ⚠️ Hoja '{hoja_nombre}' no encontrada")

            self.stats["hojas_cargadas"] = len(self.hojas_cargadas)

            # Verificar hojas críticas
            hojas_criticas = ['PUESTOS', 'OBJ_FUNCIONES']
            hojas_criticas_cargadas = all(h in self.hojas_cargadas for h in hojas_criticas)

            if not hojas_criticas_cargadas:
                print(f"❌ Error: No se cargaron las hojas críticas: {hojas_criticas}")
                return False

            print(f"\n✅ Archivo cargado: {len(self.hojas_cargadas)}/{len(SHEET_MAPPING)} hojas")
            return True

        except Exception as e:
            print(f"❌ Error crítico cargando archivo: {str(e)}")
            return False

    def listar_codigos_disponibles(self, limite: int = 10) -> List[str]:
        """
        Lista códigos de puesto disponibles en el archivo.

        Args:
            limite: Número máximo de códigos a mostrar

        Returns:
            Lista de códigos de puesto
        """
        if 'PUESTOS' not in self.hojas:
            print("❌ Hoja PUESTOS no cargada")
            return []

        df_puestos = self.hojas['PUESTOS']

        # Buscar columna de código
        col_codigo = self._encontrar_columna_codigo(df_puestos)

        if col_codigo is None:
            print("❌ No se encontró columna de código de puesto")
            return []

        codigos = df_puestos[col_codigo].dropna().unique().tolist()
        self.stats["codigos_encontrados"] = len(codigos)

        print(f"\n📋 Códigos disponibles: {len(codigos)}")
        print(f"   Mostrando primeros {min(limite, len(codigos))}:")
        for i, codigo in enumerate(codigos[:limite], 1):
            print(f"   {i}. {codigo}")

        if len(codigos) > limite:
            print(f"   ... y {len(codigos) - limite} más")

        return codigos

    def extraer_puesto(self, codigo_puesto: str) -> Dict[str, Any]:
        """
        Extrae información completa de un puesto específico.

        Args:
            codigo_puesto: Código del puesto a extraer

        Returns:
            Dict con toda la información del puesto por hoja
        """
        resultado = {
            'codigo_puesto': codigo_puesto,
            'hojas_encontradas': [],
            'datos_por_hoja': {}
        }

        for nombre_hoja, df in self.hojas.items():
            # Buscar columna de código
            col_codigo = self._encontrar_columna_codigo(df)

            if col_codigo is not None:
                # Filtrar registros del código específico
                mask = df[col_codigo] == codigo_puesto
                registros = df[mask]

                if not registros.empty:
                    resultado['hojas_encontradas'].append(nombre_hoja)
                    resultado['datos_por_hoja'][nombre_hoja] = registros.to_dict('records')

        return resultado

    def _encontrar_columna_codigo(self, df: pd.DataFrame) -> Optional[str]:
        """Encuentra la columna de código de puesto en un DataFrame"""
        for col in df.columns:
            col_upper = str(col).upper()
            if 'CÓDIGO_DE_PUESTO' in col_upper or 'CODIGO_DE_PUESTO' in col_upper:
                return col
        return None

    def get_all_puestos(self) -> pd.DataFrame:
        """
        Obtiene DataFrame completo de PUESTOS.

        Returns:
            DataFrame de la hoja PUESTOS
        """
        if 'PUESTOS' not in self.hojas:
            raise ValueError("Hoja PUESTOS no cargada")

        return self.hojas['PUESTOS']


class SidegorAdapter:
    """
    Adaptador que convierte datos extraídos de Sidegor al formato APF estándar.
    Genera estructura compatible con APFExtractor.
    """

    def __init__(self):
        """Inicializa el adaptador"""
        self.extractor = None
        self.conversion_stats = {
            "puestos_procesados": 0,
            "conversiones_exitosas": 0,
            "conversiones_parciales": 0,
            "conversiones_fallidas": 0
        }

    def cargar_archivo(self, archivo_excel: str) -> bool:
        """
        Carga archivo Excel de Sidegor.

        Args:
            archivo_excel: Ruta al archivo

        Returns:
            True si se cargó correctamente
        """
        self.extractor = SidegorExtractor(archivo_excel)
        return self.extractor.cargar_archivo()

    def listar_puestos(self, limite: int = 10) -> List[str]:
        """Lista códigos de puesto disponibles"""
        if not self.extractor:
            print("❌ No hay archivo cargado")
            return []
        return self.extractor.listar_codigos_disponibles(limite)

    def convertir_puesto(self, codigo_puesto: str,
                        incluir_opcionales: bool = True) -> Dict[str, Any]:
        """
        Convierte datos de un puesto al formato esperado por APFExtractor.

        Args:
            codigo_puesto: Código del puesto
            incluir_opcionales: Si incluir campos opcionales

        Returns:
            Dict en formato compatible con el pipeline APF
        """
        if not self.extractor:
            return {"error": "No hay archivo cargado"}

        # Extraer datos del Excel
        datos_raw = self.extractor.extraer_puesto(codigo_puesto)

        if not datos_raw['hojas_encontradas']:
            self.conversion_stats["conversiones_fallidas"] += 1
            return {"error": f"Código {codigo_puesto} no encontrado"}

        # Convertir al formato APF
        datos_apf = self._convertir_a_formato_apf(datos_raw, incluir_opcionales)

        # Actualizar estadísticas
        self.conversion_stats["puestos_procesados"] += 1
        if datos_apf.get("conversion_status") == "completa":
            self.conversion_stats["conversiones_exitosas"] += 1
        elif datos_apf.get("conversion_status") == "parcial":
            self.conversion_stats["conversiones_parciales"] += 1
        else:
            self.conversion_stats["conversiones_fallidas"] += 1

        return datos_apf

    def _convertir_a_formato_apf(self, datos_raw: Dict[str, Any],
                                incluir_opcionales: bool) -> Dict[str, Any]:
        """Convierte estructura raw de Sidegor a formato APF estándar"""
        codigo_puesto = datos_raw['codigo_puesto']
        datos_hojas = datos_raw['datos_por_hoja']

        # Estructura base APF
        datos_apf = {
            "metadatos_extraccion": {
                "fecha_extraccion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "fuente_datos": "Sidegor_Excel",
                "archivo_origen": self.extractor.archivo_path.name if self.extractor else "unknown",
                "codigo_puesto": codigo_puesto,
                "version_adaptador": "1.0"
            },
            "identificacion_puesto": self._convertir_identificacion(datos_hojas),
            "objetivo_general": self._convertir_objetivo(datos_hojas),
            "funciones": self._convertir_funciones(datos_hojas),
            "escolaridad": self._convertir_escolaridad(datos_hojas),
            "experiencia": self._convertir_experiencia(datos_hojas),
            "competencias": self._convertir_competencias(datos_hojas)
        }

        # Campos opcionales
        if incluir_opcionales:
            datos_apf["informacion_adicional"] = self._extraer_campos_opcionales(datos_hojas)

        # Evaluar completitud
        datos_apf["conversion_status"] = self._evaluar_completitud(datos_apf)
        datos_apf["hojas_procesadas"] = datos_raw['hojas_encontradas']

        return datos_apf

    def _convertir_identificacion(self, datos_hojas: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Convierte datos de identificación del puesto"""
        if 'PUESTOS' not in datos_hojas or not datos_hojas['PUESTOS']:
            return {}

        registro = datos_hojas['PUESTOS'][0]

        # Extraer nivel salarial (GRUPO + GRADO + NIVEL)
        # En Sidegor el nivel viene en 3 columnas separadas que deben concatenarse
        # Ejemplo: GRUPO=O, GRADO=2, NIVEL=1 → O21
        grupo = registro.get('GRUPO', '')
        grado = registro.get('GRADO', '')
        nivel = registro.get('NIVEL', '')

        # Construir código de nivel salarial
        codigo_nivel = None
        if grupo or grado or nivel:
            # Convertir a strings y limpiar
            grupo_str = str(grupo) if grupo is not None and pd.notna(grupo) else ''
            grado_str = str(grado) if grado is not None and pd.notna(grado) else ''
            nivel_str = str(nivel) if nivel is not None and pd.notna(nivel) else ''

            # Remover ".0" de floats (ej: "2.0" -> "2")
            if grado_str.endswith('.0'):
                grado_str = grado_str[:-2]
            if nivel_str.endswith('.0'):
                nivel_str = nivel_str[:-2]

            # Concatenar
            codigo_nivel = f"{grupo_str}{grado_str}{nivel_str}"

            # Si quedó vacío, poner None
            if not codigo_nivel or codigo_nivel == '':
                codigo_nivel = None

        nivel_salarial = {
            "codigo": codigo_nivel,
            "descripcion": None
        }

        return {
            "codigo_puesto": registro.get('CÓDIGO_DE_PUESTO'),
            "denominacion_puesto": registro.get('DESCRIPCIÓN_DEL_PUESTO'),
            "nivel_salarial": nivel_salarial,
            "caracter_ocupacional": registro.get('CARACTERÍSTICA OCUPACIONAL'),
            "estatus": registro.get('ESTATUS', 'No especificado'),
            "ramo": str(registro.get('RAMO')) if registro.get('RAMO') is not None else None,
            "unidad_responsable": str(registro.get('UR')) if registro.get('UR') is not None else None,
            "tipo_plaza": registro.get('TIPO DE PLAZA'),
            "grupo_personal": registro.get('GRUPO_DE_PERSONAL'),
            "tipo_nombramiento": registro.get('TIPO_DE_NOMBRAMIENTO'),
            "fecha_aprobacion": registro.get('FECHA_DE_APROBACIÓN')
        }

    def _convertir_objetivo(self, datos_hojas: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Convierte objetivo general del puesto"""
        if 'OBJ_FUNCIONES' not in datos_hojas or not datos_hojas['OBJ_FUNCIONES']:
            return {}

        registros = datos_hojas['OBJ_FUNCIONES']

        # Buscar el objetivo
        objetivo_desc = None
        for reg in registros:
            desc_obj = reg.get('DESCRIPCIÓN_DEL_OBJETIVO')
            if desc_obj and pd.notna(desc_obj) and len(str(desc_obj).strip()) > 20:
                objetivo_desc = str(desc_obj).strip()
                break

        if not objetivo_desc:
            return {}

        # Extraer verbo de acción
        palabras = objetivo_desc.split()
        verbo_accion = palabras[0] if palabras else None

        return {
            "descripcion_completa": objetivo_desc,
            "verbo_accion": verbo_accion,
            "objeto_contribucion": None,
            "finalidad": None
        }

    def _convertir_funciones(self, datos_hojas: Dict[str, List[Dict]]) -> List[Dict[str, Any]]:
        """Convierte funciones del puesto"""
        if 'OBJ_FUNCIONES' not in datos_hojas or not datos_hojas['OBJ_FUNCIONES']:
            return []

        funciones = []
        registros = datos_hojas['OBJ_FUNCIONES']

        for i, reg in enumerate(registros, 1):
            desc_funcion = reg.get('DESCRIPCIÓN_DE_LAS_FUNCIONES')

            if not desc_funcion or pd.isna(desc_funcion):
                continue

            desc_funcion = str(desc_funcion).strip()
            if len(desc_funcion) < 20:
                continue

            # Extraer verbo de acción
            palabras = desc_funcion.split()
            verbo_accion = palabras[0] if palabras else None

            funcion = {
                "numero": reg.get('ID_FUNCIONES', i),
                "descripcion_completa": desc_funcion,
                "verbo_accion": verbo_accion,
                "que_hace": None,
                "para_que_lo_hace": None,
                "fundamento_normativo": None
            }

            funciones.append(funcion)

        return funciones

    def _convertir_escolaridad(self, datos_hojas: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Convierte requisitos de escolaridad"""
        if 'ESCOLARIDAD' not in datos_hojas or not datos_hojas['ESCOLARIDAD']:
            return {}

        registro = datos_hojas['ESCOLARIDAD'][0]

        return {
            "nivel_estudios": registro.get('DESCRIPCIÓN_DEL_NIVEL_DE_ESTUDIOS'),
            "grado_avance": registro.get('DESCRIPCIÓN_DEL_GRADO_DE_AVANCE'),
            "area_general": registro.get('DESCRIPCIÓN_DEL_ÁREA_GENERAL'),
            "carrera_generica": registro.get('DESCRIPCIÓN_DE_LA_CARRERA_GENÉRICA')
        }

    def _convertir_experiencia(self, datos_hojas: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Convierte requisitos de experiencia"""
        if 'EXP_LAB' not in datos_hojas or not datos_hojas['EXP_LAB']:
            return {}

        registro = datos_hojas['EXP_LAB'][0]

        return {
            "anos_experiencia": registro.get('DESCRIPCIÓN_DE_LOS_AÑOS_DE_EXPERIENCIA'),
            "area_experiencia": registro.get('DESCRIPCIÓN_DEL_ÁREA_DE_EXPERIENCIA')
        }

    def _convertir_competencias(self, datos_hojas: Dict[str, List[Dict]]) -> List[Dict[str, Any]]:
        """Convierte competencias requeridas"""
        competencias = []

        hojas_competencias = ['COMPETENCIAS', 'CAP_PROF', 'CAPACIDADES']

        for hoja in hojas_competencias:
            if hoja in datos_hojas and datos_hojas[hoja]:
                for reg in datos_hojas[hoja]:
                    competencia = {
                        "competencia": reg.get('DESCRIPCIÓN_DE_LA_COMPETENCIA') or reg.get('CAPACIDAD'),
                        "nivel_requerido": reg.get('DESCRIPCIÓN_DEL_NIVEL_REQUERIDO') or reg.get('NIVEL')
                    }

                    if competencia["competencia"]:
                        competencias.append(competencia)

        return competencias

    def _extraer_campos_opcionales(self, datos_hojas: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Extrae campos opcionales adicionales"""
        opcionales = {}

        # Condiciones de trabajo
        if 'COND_TRABAJO' in datos_hojas and datos_hojas['COND_TRABAJO']:
            reg = datos_hojas['COND_TRABAJO'][0]
            opcionales["condiciones_trabajo"] = {
                "horario": reg.get('HORARIO'),
                "disponibilidad_viajar": reg.get('DISPONIBILIDAD_VIAJAR'),
                "periodos_especiales": reg.get('PERIODOS_ESPECIALES'),
                "cambio_residencia": reg.get('CAMBIO_RESIDENCIA')
            }

        # Entorno operativo
        if 'ENT_OPER' in datos_hojas and datos_hojas['ENT_OPER']:
            reg = datos_hojas['ENT_OPER'][0]
            opcionales["entorno_operativo"] = {
                "tipo_relacion": reg.get('TIPO_RELACION'),
                "explicacion": reg.get('EXPLICACION'),
                "caracteristica_informacion": reg.get('CARACTERISTICA_INFORMACION')
            }

        return opcionales

    def _evaluar_completitud(self, datos_apf: Dict[str, Any]) -> str:
        """Evalúa completitud de la conversión"""
        campos_criticos = [
            datos_apf.get("identificacion_puesto", {}).get("denominacion_puesto"),
            datos_apf.get("objetivo_general", {}).get("descripcion_completa"),
            len(datos_apf.get("funciones", [])) > 0
        ]

        campos_presentes = sum(1 for campo in campos_criticos if campo)

        if campos_presentes == len(campos_criticos):
            return "completa"
        elif campos_presentes >= len(campos_criticos) / 2:
            return "parcial"
        else:
            return "incompleta"

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del adaptador"""
        return {
            "conversion_stats": self.conversion_stats,
            "extractor_stats": self.extractor.stats if self.extractor else {},
            "archivo_cargado": self.extractor.archivo_path.name if self.extractor else None,
            "hojas_disponibles": len(self.extractor.hojas) if self.extractor else 0
        }
