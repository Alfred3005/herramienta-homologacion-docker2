"""
Generador de Reportes RHNet Completos
Genera reportes de puestos en formato RHNet para control y auditoría.

Versión: 1.0
Fecha: 2025-11-20
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


class RHNetReportGenerator:
    """
    Genera reportes completos de puestos en formato RHNet.

    Emula el formato oficial de RH Net para facilitar contraste
    entre información de entrada vs resultados de análisis.
    """

    def __init__(self):
        """Inicializa el generador de reportes"""
        pass

    def generar_reporte_completo(self, datos_puesto: Dict[str, Any]) -> str:
        """
        Genera reporte completo en formato RHNet.

        Args:
            datos_puesto: Datos del puesto en formato APF (incluye todas las secciones)

        Returns:
            String con reporte formateado completo
        """
        # Extraer secciones
        ident = datos_puesto.get("identificacion_puesto", {})
        objetivo = datos_puesto.get("objetivo_general", {})
        funciones = datos_puesto.get("funciones", [])
        escolaridad = datos_puesto.get("escolaridad", {})
        experiencia = datos_puesto.get("experiencia", {})
        competencias = datos_puesto.get("competencias", [])
        condiciones = datos_puesto.get("condiciones_trabajo", {})
        entorno = datos_puesto.get("entorno_operativo", {})
        observaciones = datos_puesto.get("observaciones", {})

        # Construir reporte
        reporte = []

        # 1. ENCABEZADO DEL PUESTO
        reporte.append(self._seccion_encabezado(ident))

        # 2. DIRECCIÓN (si está disponible)
        if "direccion" in datos_puesto:
            reporte.append(self._seccion_direccion(datos_puesto.get("direccion", {})))

        # 3. OBJETIVO GENERAL Y FUNCIONES
        reporte.append(self._seccion_objetivo_funciones(objetivo, funciones))

        # 4. PERFIL
        reporte.append(self._seccion_perfil(
            entorno, escolaridad, experiencia,
            condiciones, competencias, observaciones
        ))

        return "\n".join(reporte)

    def _seccion_encabezado(self, ident: Dict[str, Any]) -> str:
        """Genera sección de encabezado del puesto"""
        # Extraer datos
        codigo = ident.get('codigo_puesto', 'N/A')
        denominacion = ident.get('denominacion_puesto', 'N/A')
        caracter = ident.get('caracter_ocupacional', 'N/A')

        # Nivel salarial
        nivel_sal = ident.get('nivel_salarial', {})
        if isinstance(nivel_sal, dict):
            nivel_str = f"{nivel_sal.get('codigo', 'N/A')} - {nivel_sal.get('descripcion', '')}"
        else:
            nivel_str = str(nivel_sal) if nivel_sal else 'N/A'

        persona = ident.get('persona_en_puesto', 'N/A')
        puestos_dep = ident.get('puestos_dependientes', 'N/A')

        return f"""Puesto: {codigo}
Nombre    {denominacion}     Caracter ocupacional    {caracter}
Nivel salarial    {nivel_str}     Persona en el puesto    {persona}
Puestos dependientes    {puestos_dep}"""

    def _seccion_direccion(self, direccion: Dict[str, Any]) -> str:
        """Genera sección de dirección física"""
        edificio = direccion.get('edificio', 'N/A')
        calle = direccion.get('calle', 'N/A')
        colonia_num = direccion.get('colonia_numero', 'N/A')
        poblacion = direccion.get('poblacion', '')
        calles_ady = direccion.get('calles_adyacentes', '')

        pais = direccion.get('pais', 'MEXICO')
        estado = direccion.get('estado', 'N/A')
        municipio = direccion.get('municipio', 'N/A')
        colonia = direccion.get('colonia', 'N/A')
        cp = direccion.get('codigo_postal', 'N/A')
        email = direccion.get('email', '')
        telefono = direccion.get('telefono', '')

        return f"""
Dirección: {edificio}
Calle    {calle}     Colonia    {colonia_num}
Población    {poblacion}     Calles adyacentes    {calles_ady}
Pais:    {pais}     Estado:    {estado}
Municipio:    {municipio}     Colonia:    {colonia}
Codigo postal:    {cp}     E-mail:    {email}
Tel:    {telefono}"""

    def _seccion_objetivo_funciones(self, objetivo: Dict[str, Any], funciones: List[Dict[str, Any]]) -> str:
        """Genera sección de objetivo general y funciones"""
        obj_texto = objetivo.get('descripcion_completa', 'No disponible')

        seccion = f"""
Objetivo General y Funciones.
Objetivo General
{obj_texto}"""

        # Agregar funciones
        for i, func in enumerate(funciones, 1):
            desc = func.get('descripcion_completa', 'No disponible')
            seccion += f"\nFunción {i}\n{desc}"

        return seccion

    def _seccion_perfil(self, entorno: Dict[str, Any], escolaridad: Dict[str, Any],
                        experiencia: Dict[str, Any], condiciones: Dict[str, Any],
                        competencias: List[Dict[str, Any]], observaciones: Dict[str, Any]) -> str:
        """Genera sección de perfil completo"""

        # ENTORNO OPERATIVO
        tipo_rel = entorno.get('tipo_relacion', 'Ambas')
        explicacion = entorno.get('explicacion', 'No disponible')
        caract_info = entorno.get('caracteristica_informacion', 'No disponible')

        # ESCOLARIDAD
        nivel_est = escolaridad.get('nivel_estudios', 'NO APLICA')
        grado_av = escolaridad.get('grado_avance', 'NO APLICA')
        area_gen = escolaridad.get('area_general', 'NO APLICA')
        carrera = escolaridad.get('carrera_generica', 'NO APLICA')

        # EXPERIENCIA
        anos_req = experiencia.get('anos_experiencia', 'NO APLICA')
        area_exp_gen = experiencia.get('area_general', 'NO APLICA')
        area_exp = experiencia.get('area_experiencia', 'NO APLICA')

        # CONDICIONES DE TRABAJO
        horario = condiciones.get('horario', 'Diurno')
        viajar = condiciones.get('disponibilidad_viajar', 'A veces')
        periodos = condiciones.get('periodos_especiales', 'NO')
        cambio_res = condiciones.get('cambio_residencia', 'NO')

        seccion = f"""
Perfil.
Entorno Operativo
Tipo de Relación:    {tipo_rel}
Explicación:    {explicacion}
Característica de la Información:    {caract_info}
Escolaridad
Nivel de Estudios:    {nivel_est}    Grado de Avance:    {grado_av}
Área General:    Carrera Genérica:
{area_gen}    {carrera}
Experiencia Laboral
Años requeridos:    {anos_req}
Área General:    Área de Experiencia:
{area_exp_gen}    {area_exp}
Condiciones de Trabajo
Horario de Trabajo:    {horario}
Disponibilidad para Viajar:    {viajar}
Periodos Especiales de Trabajo:    {periodos}    Cambio de Residencia:    {cambio_res}"""

        # CAPACIDADES PROFESIONALES
        if competencias:
            seccion += "\nCapacidades Profesionales"
            for comp in competencias:
                cap_id = comp.get('codigo_capacidad', 'N/A')
                cap_nombre = comp.get('competencia', 'N/A')
                nivel = comp.get('nivel_requerido', 'N/A')
                dac = comp.get('desarrollo_admin_calidad', '0')
                seccion += f"\nCapacidad:    {cap_id}    {cap_nombre}"
                seccion += f"\nNivel:    {nivel}    Desarrollo Administrativo y Calidad:    {dac}"

        # OBSERVACIONES
        obs_gen = observaciones.get('observaciones_generales', '')
        obs_esp = observaciones.get('observaciones_especialista', '')

        if obs_gen or obs_esp:
            seccion += "\nObservaciones"
            if obs_gen:
                seccion += f"\nObservaciones:    {obs_gen}"
            if obs_esp:
                seccion += f"\nObservaciones Especialista:    {obs_esp}"

        return seccion

    def generar_reporte_desde_excel(self, row_puesto: Dict[str, Any],
                                     funciones_list: List[Dict[str, Any]]) -> str:
        """
        Genera reporte directamente desde datos del Excel Sidegor.

        Args:
            row_puesto: Fila del DataFrame PUESTOS (como dict)
            funciones_list: Lista de funciones del puesto desde OBJ_FUNCIONES

        Returns:
            String con reporte formateado
        """
        # Construir estructura de datos_puesto compatible
        datos_puesto = {
            "identificacion_puesto": {
                "codigo_puesto": row_puesto.get('CODIGO', 'N/A'),
                "denominacion_puesto": row_puesto.get('DENOMINACION', 'N/A'),
                "caracter_ocupacional": row_puesto.get('CARACTER', 'N/A'),
                "nivel_salarial": {
                    "codigo": row_puesto.get('NIVEL', 'N/A'),
                    "descripcion": row_puesto.get('NIVEL_DESC', '')
                },
                "persona_en_puesto": row_puesto.get('PERSONA', 'N/A'),
                "puestos_dependientes": row_puesto.get('PUESTOS_DEP', 'N/A'),
                "unidad_responsable": row_puesto.get('UR', 'N/A'),
                "ramo": row_puesto.get('RAMO', 'N/A'),
                "estatus": row_puesto.get('ESTATUS', 'N/A')
            },
            "objetivo_general": {
                "descripcion_completa": funciones_list[0].get('DESCRIPCION', 'No disponible') if funciones_list else 'No disponible'
            },
            "funciones": [
                {"descripcion_completa": f.get('DESCRIPCION', '')}
                for f in funciones_list[1:] if f.get('TIPO') == 'FUNCION'
            ],
            "escolaridad": {
                "nivel_estudios": row_puesto.get('ESC_NIVEL', 'NO APLICA'),
                "grado_avance": row_puesto.get('ESC_GRADO', 'NO APLICA'),
                "area_general": row_puesto.get('ESC_AREA_GEN', 'NO APLICA'),
                "carrera_generica": row_puesto.get('ESC_CARRERA', 'NO APLICA')
            },
            "experiencia": {
                "anos_experiencia": row_puesto.get('EXP_ANOS', 'NO APLICA'),
                "area_general": row_puesto.get('EXP_AREA_GEN', 'NO APLICA'),
                "area_experiencia": row_puesto.get('EXP_AREA', 'NO APLICA')
            },
            "condiciones_trabajo": {
                "horario": row_puesto.get('COND_HORARIO', 'Diurno'),
                "disponibilidad_viajar": row_puesto.get('COND_VIAJAR', 'A veces'),
                "periodos_especiales": row_puesto.get('COND_PERIODOS', 'NO'),
                "cambio_residencia": row_puesto.get('COND_CAMBIO_RES', 'NO')
            },
            "entorno_operativo": {
                "tipo_relacion": row_puesto.get('ENT_TIPO_REL', 'Ambas'),
                "explicacion": row_puesto.get('ENT_EXPLICACION', 'No disponible'),
                "caracteristica_informacion": row_puesto.get('ENT_CARACT_INFO', 'No disponible')
            },
            "competencias": [],
            "observaciones": {
                "observaciones_generales": row_puesto.get('OBS_GENERAL', ''),
                "observaciones_especialista": row_puesto.get('OBS_ESPECIALISTA', '')
            }
        }

        return self.generar_reporte_completo(datos_puesto)
