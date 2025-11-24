"""
Generador de documentos virtuales en formato RHNet.
Convierte datos APF a formato texto compatible con el pipeline de validación.
"""

from typing import Dict, Any, List


class RHNetDocumentGenerator:
    """
    Genera documentos de texto simulando formato RHNet.

    El formato RHNet es el formato estándar de texto que usa
    el pipeline de extracción y validación APF.

    Soporta dos templates:
        - "default": Formato estándar compatible con pipeline
        - "extended": Incluye información adicional (competencias, etc.)
    """

    def __init__(self, template: str = "default"):
        """
        Inicializa generador de documentos RHNet.

        Args:
            template: Template a usar ("default" o "extended")

        Raises:
            ValueError: Si template no es reconocido
        """
        valid_templates = ["default", "extended"]
        if template not in valid_templates:
            raise ValueError(f"Template debe ser uno de {valid_templates}, recibido: {template}")

        self.template = template

    def generar_documento(self, datos_apf: Dict[str, Any]) -> str:
        """
        Genera documento RHNet desde datos APF.

        Args:
            datos_apf: Datos en formato APF (output de SidegorAdapter)

        Returns:
            String con documento formateado estilo RHNet

        Raises:
            ValueError: Si datos_apf tiene formato inválido
        """
        if "error" in datos_apf:
            raise ValueError(f"Datos APF contienen error: {datos_apf['error']}")

        if self.template == "default":
            return self._generar_formato_default(datos_apf)
        elif self.template == "extended":
            return self._generar_formato_extendido(datos_apf)

    def _generar_formato_default(self, datos_apf: Dict[str, Any]) -> str:
        """
        Genera documento en formato RHNet estándar.

        Este es el formato compatible con el pipeline actual de extracción.

        Args:
            datos_apf: Datos en formato APF

        Returns:
            Documento RHNet formateado
        """
        ident = datos_apf.get("identificacion_puesto", {})
        obj = datos_apf.get("objetivo_general", {})
        funciones = datos_apf.get("funciones", [])
        escolaridad = datos_apf.get("escolaridad", {})
        experiencia = datos_apf.get("experiencia", {})

        # Construir header
        doc = self._construir_header(ident)

        # Agregar objetivo y funciones
        doc += "\nObjetivo General y Funciones.\n"
        doc += "Objetivo General\n"
        doc += f"{obj.get('descripcion_completa', 'No disponible')}\n\n"

        # Agregar funciones
        doc += self._construir_funciones(funciones)

        # Agregar perfil
        doc += self._construir_perfil(escolaridad, experiencia)

        return doc

    def _generar_formato_extendido(self, datos_apf: Dict[str, Any]) -> str:
        """
        Genera documento en formato extendido con información adicional.

        Args:
            datos_apf: Datos en formato APF

        Returns:
            Documento RHNet extendido
        """
        # Empezar con formato default
        doc = self._generar_formato_default(datos_apf)

        # Agregar información adicional
        info_adicional = datos_apf.get("informacion_adicional", {})
        competencias = datos_apf.get("competencias", [])

        if competencias or info_adicional:
            doc += "\n\nInformación Adicional.\n"

        # Competencias
        if competencias:
            doc += self._construir_competencias(competencias)

        # Condiciones de trabajo
        if "condiciones_trabajo" in info_adicional:
            doc += self._construir_condiciones_trabajo(info_adicional["condiciones_trabajo"])

        # Entorno operativo
        if "entorno_operativo" in info_adicional:
            doc += self._construir_entorno_operativo(info_adicional["entorno_operativo"])

        return doc

    def _construir_header(self, ident: Dict[str, Any]) -> str:
        """Construye header del documento"""
        nivel_salarial = ident.get('nivel_salarial', {})
        nivel_codigo = nivel_salarial.get('codigo', 'N/A') if isinstance(nivel_salarial, dict) else 'N/A'

        header = f"""Puesto: {ident.get('codigo_puesto', 'N/A')}
Nombre\t{ident.get('denominacion_puesto', 'N/A')}\tCaracter ocupacional\t{ident.get('caracter_ocupacional', 'N/A')}
Nivel salarial\t{nivel_codigo}\tEstatus\t{ident.get('estatus', 'N/A')}
Ramo\t{ident.get('ramo', 'N/A')}\tUnidad Responsable\t{ident.get('unidad_responsable', 'N/A')}
"""
        return header

    def _construir_funciones(self, funciones: List[Dict[str, Any]]) -> str:
        """Construye sección de funciones"""
        if not funciones:
            return "Función 1\nNo disponible\n\n"

        doc = ""
        for i, func in enumerate(funciones, 1):
            doc += f"Función {i}\n"
            doc += f"{func.get('descripcion_completa', 'No disponible')}\n"

        doc += "\n"
        return doc

    def _construir_perfil(self, escolaridad: Dict[str, Any], experiencia: Dict[str, Any]) -> str:
        """Construye sección de perfil"""
        doc = """Perfil.
Escolaridad
"""
        doc += f"Nivel de Estudios:\t{escolaridad.get('nivel_estudios', 'NO APLICA')}\n"
        doc += f"Grado de Avance:\t{escolaridad.get('grado_avance', 'NO APLICA')}\n"
        doc += f"Área General:\t{escolaridad.get('area_general', 'NO APLICA')}\n"
        doc += f"Carrera Genérica:\t{escolaridad.get('carrera_generica', 'NO APLICA')}\n\n"

        doc += """Experiencia Laboral
"""
        doc += f"Años requeridos:\t{experiencia.get('anos_experiencia', 'NO APLICA')}\n"
        doc += f"Área de Experiencia:\t{experiencia.get('area_experiencia', 'NO APLICA')}\n"

        return doc

    def _construir_competencias(self, competencias: List[Dict[str, Any]]) -> str:
        """Construye sección de competencias"""
        if not competencias:
            return ""

        doc = "\nCompetencias:\n"
        for comp in competencias:
            competencia = comp.get('competencia', 'N/A')
            nivel = comp.get('nivel_requerido', 'N/A')
            doc += f"  - {competencia}: {nivel}\n"

        return doc

    def _construir_condiciones_trabajo(self, condiciones: Dict[str, Any]) -> str:
        """Construye sección de condiciones de trabajo"""
        doc = "\nCondiciones de Trabajo:\n"
        doc += f"  Horario: {condiciones.get('horario', 'N/A')}\n"
        doc += f"  Disponibilidad para viajar: {condiciones.get('disponibilidad_viajar', 'N/A')}\n"
        doc += f"  Cambio de residencia: {condiciones.get('cambio_residencia', 'N/A')}\n"

        return doc

    def _construir_entorno_operativo(self, entorno: Dict[str, Any]) -> str:
        """Construye sección de entorno operativo"""
        doc = "\nEntorno Operativo:\n"
        doc += f"  Tipo de relación: {entorno.get('tipo_relacion', 'N/A')}\n"
        doc += f"  Explicación: {entorno.get('explicacion', 'N/A')}\n"

        return doc

    def generar_lote(self, lote_datos_apf: List[Dict[str, Any]]) -> List[str]:
        """
        Genera múltiples documentos RHNet en lote.

        Args:
            lote_datos_apf: Lista de datos APF

        Returns:
            Lista de documentos RHNet generados
        """
        documentos = []

        for datos_apf in lote_datos_apf:
            try:
                doc = self.generar_documento(datos_apf)
                documentos.append(doc)
            except Exception as e:
                # Agregar documento de error
                codigo = datos_apf.get("identificacion_puesto", {}).get("codigo_puesto", "UNKNOWN")
                doc_error = f"ERROR generando documento para {codigo}: {str(e)}"
                documentos.append(doc_error)

        return documentos
