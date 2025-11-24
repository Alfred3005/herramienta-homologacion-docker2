"""
Página de Nuevo Análisis - Wizard de 4 Pasos
Permite configurar y ejecutar análisis de puestos
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import time
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno (override=True para sobrescribir env vars del sistema)
load_dotenv(override=True)

# Agregar path al sistema
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

# Importar parser de texto
from src.utils.text_puesto_parser import parse_and_convert

def show():
    """Renderiza la página de nuevo análisis"""

    st.title("🆕 Nuevo Análisis")
    st.markdown("### Wizard de Configuración - 4 Pasos")

    # Inicializar estado si no existe
    if 'wizard_step' not in st.session_state:
        st.session_state.wizard_step = 1

    if 'uploaded_sidegor' not in st.session_state:
        st.session_state.uploaded_sidegor = None

    if 'uploaded_normativa' not in st.session_state:
        st.session_state.uploaded_normativa = None

    if 'uploaded_puesto_txt' not in st.session_state:
        st.session_state.uploaded_puesto_txt = None

    if 'input_mode' not in st.session_state:
        st.session_state.input_mode = 'excel'  # 'excel' o 'txt'

    if 'filters_config' not in st.session_state:
        st.session_state.filters_config = {}

    if 'analysis_options' not in st.session_state:
        st.session_state.analysis_options = {
            'generate_pdf': True,
            'generate_excel': True,
            'save_json': True,
            'contextual_validation': False,
        }

    # Mostrar indicador de progreso
    steps = ["📂 Archivos", "🔍 Filtros", "⚙️ Opciones", "🚀 Ejecutar"]
    current_step = st.session_state.wizard_step

    cols = st.columns(4)
    for idx, (col, step_name) in enumerate(zip(cols, steps), 1):
        with col:
            if idx < current_step:
                st.success(f"✅ {step_name}")
            elif idx == current_step:
                st.info(f"▶️ {step_name}")
            else:
                st.markdown(f"⚪ {step_name}")

    st.markdown("---")

    # Renderizar paso correspondiente
    if current_step == 1:
        step_1_upload_files()
    elif current_step == 2:
        step_2_configure_filters()
    elif current_step == 3:
        step_3_analysis_options()
    elif current_step == 4:
        step_4_execute()


def step_1_upload_files():
    """Paso 1: Subir archivos necesarios"""

    st.subheader("📂 Paso 1: Subir Archivos")

    # Selector de modo de entrada
    st.markdown("#### 🔀 Modo de Entrada")
    input_mode = st.radio(
        "Selecciona el tipo de entrada:",
        options=['excel', 'txt'],
        format_func=lambda x: "📊 Base de Datos Excel (Sidegor)" if x == 'excel' else "📝 Puesto Individual (Texto Plano)",
        horizontal=True,
        key='input_mode_selector'
    )

    st.session_state.input_mode = input_mode
    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        # Mostrar uploader según el modo seleccionado
        if input_mode == 'excel':
            st.markdown("#### 📊 Base de Datos Sidegor (Requerido)")
            st.markdown("Formato: archivo Excel (.xlsx)")

            uploaded_sidegor = st.file_uploader(
                "Subir archivo Excel Sidegor",
                type=['xlsx'],
                key='sidegor_uploader',
                help="Archivo Excel con formato Sidegor (11 hojas: PUESTOS, OBJ_FUNCIONES, etc.)"
            )

            if uploaded_sidegor is not None:
                st.session_state.uploaded_sidegor = uploaded_sidegor

                # Validar archivo
                with st.spinner("Validando archivo..."):
                    try:
                        # Leer hojas del Excel
                        excel_file = pd.ExcelFile(uploaded_sidegor)
                        sheets = excel_file.sheet_names

                        # Verificar hojas requeridas
                        required_sheets = ['PUESTOS', 'OBJ_FUNCIONES']
                        has_required = all(sheet in sheets for sheet in required_sheets)

                        if has_required:
                            # Contar puestos
                            df_puestos = pd.read_excel(uploaded_sidegor, sheet_name='PUESTOS')
                            num_puestos = len(df_puestos)

                            st.success(f"✅ Archivo válido")
                            st.info(f"""
                            **Información del archivo:**
                            - 📦 Tamaño: {uploaded_sidegor.size / 1024:.1f} KB
                            - 📋 Puestos detectados: **{num_puestos}**
                            - 📄 Hojas encontradas: {len(sheets)}
                            """)

                            # Guardar info en session state
                            st.session_state.sidegor_info = {
                                'num_puestos': num_puestos,
                                'sheets': sheets,
                                'df_puestos': df_puestos
                            }
                        else:
                            st.error(f"❌ Formato inválido. Faltan hojas requeridas: {', '.join(required_sheets)}")

                    except Exception as e:
                        st.error(f"❌ Error al leer archivo: {str(e)}")

        else:  # modo 'txt'
            st.markdown("#### 📝 Descripción de Puesto (Texto Plano)")
            st.markdown("Formato: archivo .txt con descripción del puesto")

            uploaded_puesto_txt = st.file_uploader(
                "Subir documento de puesto (.txt)",
                type=['txt'],
                key='puesto_txt_uploader',
                help="Documento de texto plano con la descripción completa del puesto"
            )

            if uploaded_puesto_txt is not None:
                st.session_state.uploaded_puesto_txt = uploaded_puesto_txt

                # Parsear documento con LLM
                with st.spinner("🤖 Extrayendo información del documento con LLM..."):
                    try:
                        # Leer contenido del archivo
                        content = uploaded_puesto_txt.getvalue().decode('utf-8')

                        # Parsear usando LLM
                        puesto_data = parse_and_convert(content)

                        # Guardar datos parseados en session state
                        st.session_state.parsed_puesto_data = puesto_data

                        # Mostrar información extraída
                        st.success("✅ Documento parseado exitosamente")

                        puesto_info = puesto_data.get('puesto', {})
                        funciones = puesto_data.get('funciones', [])
                        metadatos = puesto_data.get('metadatos', {})

                        st.info(f"""
                        **Información Extraída:**
                        - 📄 Código: **{puesto_info.get('codigo', 'N/A')}**
                        - 🏷️ Denominación: **{puesto_info.get('denominacion', 'N/A')}**
                        - 📊 Nivel: **{puesto_info.get('nivel_salarial', 'N/A')}**
                        - 🏢 UR: **{puesto_info.get('unidad_responsable', 'N/A')}**
                        - ✅ Funciones detectadas: **{len(funciones)}**
                        - 🎯 Calidad extracción: **{metadatos.get('calidad_extraccion', 'N/A')}**
                        """)

                        # Preview de funciones
                        with st.expander("👁️ Preview de Funciones Extraídas"):
                            for i, func in enumerate(funciones[:5], 1):  # Mostrar primeras 5
                                st.markdown(f"""
                                **{i}. {func.get('verbo_accion', 'N/A')}**
                                - Descripción: {func.get('descripcion_completa', 'N/A')[:100]}...
                                """)

                            if len(funciones) > 5:
                                st.caption(f"... y {len(funciones) - 5} funciones más")

                        # Preview del objetivo
                        if puesto_data.get('objetivo'):
                            with st.expander("🎯 Objetivo del Puesto"):
                                st.markdown(puesto_data['objetivo'][:300] + "...")

                    except Exception as e:
                        st.error(f"❌ Error al parsear documento: {str(e)}")
                        st.exception(e)
                        # Limpiar datos parciales
                        if 'parsed_puesto_data' in st.session_state:
                            del st.session_state.parsed_puesto_data

    with col2:
        st.markdown("#### 📜 Normativa / Reglamento (Requerido)")
        st.markdown("Formatos: .txt, .pdf, .docx")

        uploaded_normativa = st.file_uploader(
            "Subir normativa o reglamento",
            type=['txt', 'pdf', 'docx'],
            key='normativa_uploader',
            help="Documento normativo contra el cual se validarán los puestos"
        )

        if uploaded_normativa is not None:
            st.session_state.uploaded_normativa = uploaded_normativa

            st.success(f"✅ Archivo cargado")
            st.info(f"""
            **Información del archivo:**
            - 📦 Tamaño: {uploaded_normativa.size / 1024:.1f} KB
            - 📄 Tipo: {uploaded_normativa.type}
            - 📝 Nombre: {uploaded_normativa.name}
            """)

            # Si es TXT, mostrar preview
            if uploaded_normativa.name.endswith('.txt'):
                content = uploaded_normativa.getvalue().decode('utf-8')
                with st.expander("👁️ Preview del contenido"):
                    st.text(content[:500] + "..." if len(content) > 500 else content)

    st.markdown("---")

    # Botones de navegación
    col_left, col_right = st.columns([1, 1])

    with col_left:
        if st.button("🏠 Volver al Inicio", use_container_width=True):
            st.session_state.page = 'home'
            st.rerun()

    with col_right:
        # Validar requisitos según el modo seleccionado
        if input_mode == 'excel':
            can_proceed = (st.session_state.uploaded_sidegor is not None and
                           st.session_state.uploaded_normativa is not None)
            warning_msg = "⚠️ Por favor sube el archivo Sidegor y la normativa para continuar"
        else:  # modo 'txt'
            can_proceed = ('parsed_puesto_data' in st.session_state and
                           st.session_state.uploaded_normativa is not None)
            warning_msg = "⚠️ Por favor sube el documento de puesto (.txt) y la normativa para continuar"

        if st.button("Siguiente →", use_container_width=True,
                     type="primary", disabled=not can_proceed):
            # En modo txt, saltar directamente al paso 3 (no hay filtros para un solo puesto)
            if input_mode == 'txt':
                st.session_state.wizard_step = 3
            else:
                st.session_state.wizard_step = 2
            st.rerun()

    if not can_proceed:
        st.warning(warning_msg)


def step_2_configure_filters():
    """Paso 2: Configurar filtros de selección"""

    st.subheader("🔍 Paso 2: Configurar Filtros")

    if 'sidegor_info' not in st.session_state:
        st.error("❌ No se ha cargado información del archivo Sidegor")
        return

    df_puestos = st.session_state.sidegor_info['df_puestos']

    # Filtro por Nivel Salarial
    st.markdown("### 🎯 Filtro por Nivel Salarial")

    enable_nivel_filter = st.checkbox("✓ Activar filtro por nivel salarial", value=True)

    if enable_nivel_filter:
        # Detectar tipo de niveles (alfabético o numérico)
        if 'GRUPO' in df_puestos.columns:
            grupos_unicos = df_puestos['GRUPO'].dropna().unique()
            tiene_alfabeticos = any(str(g).isalpha() for g in grupos_unicos)

            if tiene_alfabeticos:
                st.info("📊 Niveles detectados: **Alfabéticos** (G, H, I, J, K, M, N, O, P)")

                niveles_disponibles = sorted([str(g) for g in grupos_unicos if pd.notna(g)])

                selected_niveles = st.multiselect(
                    "Seleccionar niveles:",
                    options=niveles_disponibles,
                    default=[],
                    help="Puedes seleccionar múltiples niveles"
                )

                st.session_state.filters_config['niveles'] = selected_niveles
                st.session_state.filters_config['tipo_nivel'] = 'alfabetico'

        if 'GRADO' in df_puestos.columns and not tiene_alfabeticos:
            grados_unicos = sorted(df_puestos['GRADO'].dropna().unique())
            st.info("📊 Niveles detectados: **Numéricos** (1, 2, 3, ...)")

            selected_grados = st.multiselect(
                "Seleccionar grados:",
                options=[int(g) if not pd.isna(g) else g for g in grados_unicos],
                default=[],
            )

            st.session_state.filters_config['niveles'] = [str(g) for g in selected_grados]
            st.session_state.filters_config['tipo_nivel'] = 'numerico'

    else:
        st.session_state.filters_config['niveles'] = []

    st.markdown("---")

    # Filtro por UR
    st.markdown("### 🏢 Filtro por Unidad Responsable (UR)")

    enable_ur_filter = st.checkbox("✓ Activar filtro por UR", value=False)

    if enable_ur_filter:
        if 'UR' in df_puestos.columns:
            urs_disponibles = sorted(df_puestos['UR'].dropna().unique())

            # Contar puestos por UR
            ur_counts = df_puestos['UR'].value_counts()

            ur_options = [f"{ur} ({ur_counts[ur]} puestos)" for ur in urs_disponibles]

            selected_ur_with_count = st.selectbox(
                "Seleccionar UR:",
                options=ur_options,
                help="Unidad Responsable a filtrar"
            )

            # Extraer solo el código de UR
            selected_ur = selected_ur_with_count.split(' ')[0] if selected_ur_with_count else None

            st.session_state.filters_config['ur'] = selected_ur
        else:
            st.warning("⚠️ Columna 'UR' no encontrada en el archivo")
    else:
        st.session_state.filters_config['ur'] = None

    st.markdown("---")

    # Filtro por Código de Puesto
    st.markdown("### 🔢 Filtro por Código de Puesto (Opcional)")

    enable_codigo_filter = st.checkbox("✓ Activar filtro por código", value=False)

    if enable_codigo_filter:
        codigo_pattern = st.text_input(
            "Patrón de código:",
            placeholder="Ej: 21-410-*, 21-*-1-*, *-E-L-C",
            help="Usa * como wildcard para cualquier secuencia"
        )

        st.session_state.filters_config['codigo_pattern'] = codigo_pattern if codigo_pattern else None
    else:
        st.session_state.filters_config['codigo_pattern'] = None

    st.markdown("---")

    # Previsualización de resultados
    st.markdown("### 📊 Previsualización de Filtros")

    # Aplicar filtros para previsualizar
    filtered_df = df_puestos.copy()

    if enable_nivel_filter and st.session_state.filters_config.get('niveles'):
        if st.session_state.filters_config['tipo_nivel'] == 'alfabetico':
            filtered_df = filtered_df[filtered_df['GRUPO'].isin(st.session_state.filters_config['niveles'])]
        else:
            niveles_int = [int(float(n)) for n in st.session_state.filters_config['niveles']]
            filtered_df = filtered_df[filtered_df['GRADO'].isin(niveles_int)]

    if enable_ur_filter and st.session_state.filters_config.get('ur'):
        filtered_df = filtered_df[filtered_df['UR'] == int(st.session_state.filters_config['ur'])]

    num_filtered = len(filtered_df)

    if num_filtered > 0:
        st.success(f"✅ **{num_filtered} puestos** coinciden con los filtros aplicados")

        # Distribución por nivel
        if enable_nivel_filter and st.session_state.filters_config.get('niveles'):
            st.markdown("**Distribución por nivel:**")

            if st.session_state.filters_config['tipo_nivel'] == 'alfabetico':
                nivel_counts = filtered_df['GRUPO'].value_counts()
            else:
                nivel_counts = filtered_df['GRADO'].value_counts()

            for nivel, count in nivel_counts.items():
                st.markdown(f"- {nivel}: {count} puestos")

    else:
        st.error("❌ No se encontraron puestos con los filtros aplicados")

    st.session_state.filters_config['num_puestos_filtrados'] = num_filtered

    st.markdown("---")

    # Navegación
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("← Atrás", use_container_width=True):
            st.session_state.wizard_step = 1
            st.rerun()

    with col2:
        if st.button("🧹 Limpiar Filtros", use_container_width=True):
            st.session_state.filters_config = {}
            st.rerun()

    with col3:
        can_proceed = num_filtered > 0

        if st.button("Siguiente →", use_container_width=True,
                     type="primary", disabled=not can_proceed):
            st.session_state.wizard_step = 3
            st.rerun()

    if not can_proceed:
        st.warning("⚠️ Los filtros deben resultar en al menos 1 puesto")


def step_3_analysis_options():
    """Paso 3: Configurar opciones de análisis"""

    st.subheader("⚙️ Paso 3: Opciones de Análisis")

    # Nombre del análisis
    st.markdown("### 📝 Identificación del Análisis")

    default_name = f"Analisis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    analysis_name = st.text_input(
        "Nombre del análisis:",
        value=default_name,
        help="Identifica este análisis para encontrarlo después"
    )

    st.session_state.analysis_options['name'] = analysis_name

    st.markdown("---")

    # Opciones de salida
    st.markdown("### 📊 Opciones de Salida")

    col1, col2 = st.columns(2)

    with col1:
        generate_pdf = st.checkbox("📥 Generar reporte PDF", value=True)
        generate_excel = st.checkbox("📥 Generar reporte Excel", value=True)

    with col2:
        save_json = st.checkbox("📥 Guardar JSONs individuales", value=True)
        generate_charts = st.checkbox("📥 Generar gráficas PNG", value=False)

    st.session_state.analysis_options.update({
        'generate_pdf': generate_pdf,
        'generate_excel': generate_excel,
        'save_json': save_json,
        'generate_charts': generate_charts,
    })

    st.markdown("---")

    # Análisis avanzado
    st.markdown("### 🧠 Análisis Avanzado")

    contextual_validation = st.checkbox(
        "🔍 Ejecutar validación contextual (LLM)",
        value=False,
        help="Usa GPT-4o para validar funciones contra normativa (más lento pero más preciso)"
    )

    weak_verbs_analysis = st.checkbox(
        "⚠️ Análisis de verbos débiles",
        value=True,
        help="Detecta verbos sin potencia normativa"
    )

    st.session_state.analysis_options.update({
        'contextual_validation': contextual_validation,
        'weak_verbs_analysis': weak_verbs_analysis,
    })

    st.markdown("---")

    # Configuración técnica
    with st.expander("🔧 Configuración Técnica Avanzada"):
        model = st.selectbox(
            "Modelo LLM:",
            options=["openai/gpt-4o", "openai/gpt-4", "openai/gpt-3.5-turbo"],
            index=0
        )

        temperature = st.slider(
            "Temperature:",
            min_value=0.0,
            max_value=1.0,
            value=0.1,
            step=0.1,
            help="Menor = más determinista, Mayor = más creativo"
        )

        max_tokens = st.number_input(
            "Max tokens:",
            min_value=1000,
            max_value=8000,
            value=4000,
            step=500
        )

        st.session_state.analysis_options.update({
            'model': model,
            'temperature': temperature,
            'max_tokens': max_tokens,
        })

    st.markdown("---")

    # Navegación
    col1, col2 = st.columns(2)

    with col1:
        if st.button("← Atrás", use_container_width=True):
            st.session_state.wizard_step = 2
            st.rerun()

    with col2:
        if st.button("Siguiente →", use_container_width=True, type="primary"):
            st.session_state.wizard_step = 4
            st.rerun()


def step_4_execute():
    """Paso 4: Confirmar y ejecutar análisis"""

    st.subheader("🚀 Paso 4: Ejecutar Análisis")

    # Mostrar resumen de configuración
    st.markdown("### ✅ Resumen de Configuración")

    with st.container():
        # Modo de entrada
        input_mode = st.session_state.input_mode

        if input_mode == 'excel':
            # Resumen modo Excel
            st.markdown(f"""
            **🔀 Modo:** Base de Datos Excel (Sidegor)

            **📊 Archivo Sidegor:**
            - Nombre: {st.session_state.uploaded_sidegor.name}
            - Tamaño: {st.session_state.uploaded_sidegor.size / 1024:.1f} KB
            - Total puestos: {st.session_state.sidegor_info['num_puestos']}

            **📜 Normativa:**
            - Nombre: {st.session_state.uploaded_normativa.name}
            - Tamaño: {st.session_state.uploaded_normativa.size / 1024:.1f} KB

            **🔍 Filtros Aplicados:**
            - Niveles: {', '.join(st.session_state.filters_config.get('niveles', ['Ninguno']))}
            - UR: {st.session_state.filters_config.get('ur', 'Ninguna')}
            - Código: {st.session_state.filters_config.get('codigo_pattern', 'Ninguno')}

            **🎯 Puestos a Procesar:** {st.session_state.filters_config.get('num_puestos_filtrados', 0)}

            **⚙️ Opciones:**
            - Validación contextual: {'✅ Sí' if st.session_state.analysis_options.get('contextual_validation') else '❌ No'}
            - Análisis verbos débiles: {'✅ Sí' if st.session_state.analysis_options.get('weak_verbs_analysis') else '❌ No'}
            - Generar PDF: {'✅ Sí' if st.session_state.analysis_options.get('generate_pdf') else '❌ No'}
            - Generar Excel: {'✅ Sí' if st.session_state.analysis_options.get('generate_excel') else '❌ No'}

            **⏱️ Tiempo Estimado:** ~{st.session_state.filters_config.get('num_puestos_filtrados', 0) * 0.5:.1f} minutos
            """)
        else:  # modo 'txt'
            # Resumen modo texto
            puesto_data = st.session_state.parsed_puesto_data
            puesto_info = puesto_data.get('puesto', {})
            funciones = puesto_data.get('funciones', [])

            st.markdown(f"""
            **🔀 Modo:** Puesto Individual (Texto Plano)

            **📝 Puesto a Analizar:**
            - Código: {puesto_info.get('codigo', 'N/A')}
            - Denominación: {puesto_info.get('denominacion', 'N/A')}
            - Nivel: {puesto_info.get('nivel_salarial', 'N/A')}
            - Unidad Responsable: {puesto_info.get('unidad_responsable', 'N/A')}
            - Funciones: {len(funciones)}

            **📜 Normativa:**
            - Nombre: {st.session_state.uploaded_normativa.name}
            - Tamaño: {st.session_state.uploaded_normativa.size / 1024:.1f} KB

            **🎯 Puestos a Procesar:** 1 (modo individual)

            **⚙️ Opciones:**
            - Validación contextual: {'✅ Sí' if st.session_state.analysis_options.get('contextual_validation') else '❌ No'}
            - Análisis verbos débiles: {'✅ Sí' if st.session_state.analysis_options.get('weak_verbs_analysis') else '❌ No'}
            - Generar PDF: {'✅ Sí' if st.session_state.analysis_options.get('generate_pdf') else '❌ No'}
            - Generar Excel: {'✅ Sí' if st.session_state.analysis_options.get('generate_excel') else '❌ No'}

            **⏱️ Tiempo Estimado:** ~0.5 minutos
            """)

    st.markdown("---")

    # Botones de acción
    col1, col2 = st.columns(2)

    with col1:
        if st.button("← Atrás", use_container_width=True):
            st.session_state.wizard_step = 3
            st.rerun()

    with col2:
        if st.button("🚀 Ejecutar Análisis", use_container_width=True, type="primary"):
            # Guardar configuración y ejecutar
            execute_analysis()

def execute_analysis():
    """Ejecuta el análisis con la configuración guardada"""

    # Verificar archivos según modo de entrada
    input_mode = st.session_state.input_mode

    if input_mode == 'excel':
        if st.session_state.uploaded_sidegor is None:
            st.error("❌ No se ha cargado el archivo Sidegor")
            return
    else:  # modo 'txt'
        if 'parsed_puesto_data' not in st.session_state:
            st.error("❌ No se ha parseado el documento de puesto")
            return

    if st.session_state.uploaded_normativa is None:
        st.error("❌ No se ha cargado el archivo de normativa")
        return

    st.info("🔄 Iniciando análisis con sistema de validación v5.40 (Estable) - Criterio 3 con LLM + GPT-4o-mini...")

    try:
        # Importar validador
        from src.validators.integrated_validator import IntegratedValidator
        from src.adapters.sidegor_adapter import SidegorAdapter

        # Crear containers para progreso
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Paso 1: Leer normativa
        status_text.text("📜 Leyendo archivo de normativa...")
        progress_bar.progress(10)

        normativa_text = ""
        if st.session_state.uploaded_normativa.type == "text/plain":
            normativa_text = st.session_state.uploaded_normativa.read().decode('utf-8')
        else:
            # Para PDFs y otros formatos, usar texto simple por ahora
            st.warning("⚠️ Tipo de archivo de normativa no soportado completamente. Usando modo simplificado.")
            normativa_text = "Normativa cargada (parsing completo pendiente)"

        # Dividir en fragmentos (simplificado - por párrafos)
        normativa_fragments = [p.strip() for p in normativa_text.split('\n\n') if p.strip()]

        # Paso 2: Cargar adaptador Sidegor (solo en modo Excel)
        adapter = None
        temp_file_path = None

        if input_mode == 'excel':
            status_text.text("📊 Cargando archivo Sidegor...")
            progress_bar.progress(20)

            try:
                # SidegorAdapter necesita ruta de archivo, no objeto de archivo
                # Guardar temporalmente el archivo subido
                import tempfile

                with tempfile.NamedTemporaryFile(mode='wb', suffix='.xlsx', delete=False) as tmp_file:
                    st.session_state.uploaded_sidegor.seek(0)
                    tmp_file.write(st.session_state.uploaded_sidegor.read())
                    temp_file_path = tmp_file.name

                # Crear adaptador e intentar cargar
                adapter = SidegorAdapter()
                if adapter.cargar_archivo(temp_file_path):
                    st.success("✅ Archivo Sidegor cargado correctamente")
                else:
                    st.warning("⚠️ Error al cargar Sidegor con adapter")
                    adapter = None
            except Exception as e:
                st.error(f"❌ Error al cargar Sidegor: {str(e)}")
                st.info("Usando modo de prueba con datos del session state...")
                adapter = None
        else:
            # En modo texto, no necesitamos adaptador
            status_text.text("📝 Modo texto: Saltando carga de Sidegor...")
            progress_bar.progress(20)

        # Paso 3: Extraer puestos a validar
        status_text.text("🔍 Aplicando filtros y extrayendo puestos...")
        progress_bar.progress(30)

        puestos_to_validate = []

        # Si estamos en modo texto, usar datos parseados directamente
        if st.session_state.input_mode == 'txt' and 'parsed_puesto_data' in st.session_state:
            status_text.text("📝 Preparando puesto desde documento de texto...")

            puesto_data = st.session_state.parsed_puesto_data
            puesto_info = puesto_data.get('puesto', {})
            funciones = puesto_data.get('funciones', [])

            # Convertir al formato esperado por el validador
            puesto_for_validator = {
                "codigo": puesto_info.get('codigo', 'UNKNOWN'),
                "denominacion": puesto_info.get('denominacion', ''),
                "nivel_salarial": puesto_info.get('nivel_salarial', ''),
                "unidad_responsable": puesto_info.get('unidad_responsable', ''),
                "funciones": []
            }

            # Convertir funciones
            for func in funciones:
                puesto_for_validator["funciones"].append({
                    "id": func.get('id', f"F{func.get('id', 'XX')}"),
                    "descripcion_completa": func.get('descripcion_completa', ''),
                    "que_hace": func.get('complemento', ''),  # Mapeo de campos
                    "para_que_lo_hace": func.get('resultado', '')
                })

            puestos_to_validate = [puesto_for_validator]

            st.success(f"✅ Puesto listo para validar: {puesto_info.get('denominacion', 'N/A')}")
            st.info(f"""
            📊 **Información del Puesto:**
            - Código: {puesto_for_validator['codigo']}
            - Denominación: {puesto_for_validator['denominacion']}
            - Nivel: {puesto_for_validator['nivel_salarial']}
            - Funciones: {len(puesto_for_validator['funciones'])}
            """)

        elif adapter:
            # Usar adaptador real
            try:
                # Listar todos los códigos de puesto
                codigos_puestos = adapter.listar_puestos(limite=9999)  # Sin límite

                st.info(f"📋 DEBUG: Se encontraron {len(codigos_puestos)} códigos de puesto en total")

                # Aplicar filtros
                filters = st.session_state.filters_config
                st.info(f"🔍 DEBUG: Filtros activos: {filters}")

                status_text.text(f"🔍 Procesando {len(codigos_puestos)} puestos...")

                # Contadores para debugging
                procesados = 0
                rechazados_por_ur = 0
                rechazados_por_nivel = 0
                sin_funciones = 0
                con_error = 0

                for idx, codigo_puesto in enumerate(codigos_puestos):
                    # Actualizar progreso cada 10 puestos
                    if idx % 10 == 0:
                        progress_bar.progress(30 + int((idx / len(codigos_puestos)) * 15))

                    # Convertir puesto al formato APF
                    puesto_data = adapter.convertir_puesto(codigo_puesto)
                    procesados += 1

                    if 'error' in puesto_data:
                        con_error += 1
                        continue

                    # Aplicar filtros básicos
                    if filters.get('unidad_responsable'):
                        ur = puesto_data.get('identificacion_puesto', {}).get('unidad_responsable', '')
                        if filters['unidad_responsable'] and filters['unidad_responsable'] not in ur:
                            rechazados_por_ur += 1
                            continue

                    if filters.get('niveles'):
                        # nivel_salarial es un diccionario {"codigo": "O11", "descripcion": ...}
                        nivel_obj = puesto_data.get('identificacion_puesto', {}).get('nivel_salarial', {})

                        # Extraer el código
                        if isinstance(nivel_obj, dict):
                            nivel_codigo = nivel_obj.get('codigo', '')
                        else:
                            nivel_codigo = str(nivel_obj) if nivel_obj else ''

                        if nivel_codigo and len(nivel_codigo) > 0:
                            # Extraer primera letra del nivel (G, H, J, K, etc.)
                            nivel_letra = nivel_codigo[0].upper()
                            if nivel_letra not in filters['niveles']:
                                rechazados_por_nivel += 1
                                continue
                        else:
                            # Si no hay nivel, saltar este puesto
                            rechazados_por_nivel += 1
                            continue

                    # Convertir al formato esperado por el validador
                    identificacion = puesto_data.get('identificacion_puesto', {})

                    # Extraer nivel_salarial correctamente (es un dict)
                    nivel_obj = identificacion.get('nivel_salarial', {})
                    if isinstance(nivel_obj, dict):
                        nivel_codigo = nivel_obj.get('codigo', '')
                    else:
                        nivel_codigo = str(nivel_obj) if nivel_obj else ''

                    puesto_for_validator = {
                        "codigo": identificacion.get('codigo_puesto', codigo_puesto),
                        "denominacion": identificacion.get('denominacion_puesto', ''),
                        "nivel_salarial": nivel_codigo,
                        "unidad_responsable": identificacion.get('unidad_responsable', ''),
                        "funciones": []
                    }

                    # Extraer funciones - están directamente en puesto_data['funciones']
                    funciones_list = puesto_data.get('funciones', [])

                    for func in funciones_list:
                        # Manejar campos que pueden ser None
                        desc_completa = func.get('descripcion_completa') or ''
                        que_hace = func.get('que_hace')
                        para_que = func.get('para_que_lo_hace')

                        # Si que_hace es None, usar primeros 100 chars de descripcion_completa
                        if que_hace is None or not que_hace:
                            que_hace = desc_completa[:100] if desc_completa else ''

                        puesto_for_validator["funciones"].append({
                            "id": func.get('numero', 'FXX'),
                            "descripcion_completa": desc_completa,
                            "que_hace": que_hace,
                            "para_que_lo_hace": para_que or ''
                        })

                    if len(puesto_for_validator["funciones"]) > 0:
                        puestos_to_validate.append(puesto_for_validator)
                    else:
                        sin_funciones += 1

                # Mostrar resumen de filtrado
                st.success(f"✅ {len(puestos_to_validate)} puestos listos para validar")
                st.info(f"""
                📊 **Resumen de Filtrado:**
                - Total procesados: {procesados}
                - Con errores: {con_error}
                - Rechazados por UR: {rechazados_por_ur}
                - Rechazados por nivel: {rechazados_por_nivel}
                - Sin funciones: {sin_funciones}
                - **Aprobados**: {len(puestos_to_validate)}
                """)

            except Exception as e:
                st.error(f"Error extrayendo puestos: {str(e)}")
                with st.expander("Ver detalles del error"):
                    import traceback
                    st.code(traceback.format_exc())
                puestos_to_validate = []

        # Si no hay puestos, crear datos de ejemplo
        if len(puestos_to_validate) == 0:
            st.warning("⚠️ No se pudieron extraer puestos. Usando ejemplo de demostración...")
            puestos_to_validate = [{
                "codigo": "EJEMPLO-001",
                "denominacion": "DIRECTOR DE EJEMPLO",
                "nivel_salarial": "M1",
                "unidad_responsable": "EJEMPLO - PRUEBA",
                "funciones": [
                    {
                        "id": "F001",
                        "descripcion_completa": "Coordinar actividades del área",
                        "que_hace": "Coordinar actividades",
                        "para_que_lo_hace": "para asegurar el cumplimiento"
                    }
                ]
            }]

        # Paso 4: Inicializar validador
        status_text.text("⚙️ Inicializando sistema de validación...")
        progress_bar.progress(40)

        # Obtener API key
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            st.error("❌ OPENAI_API_KEY no configurada en .env")
            return

        validator = IntegratedValidator(
            normativa_fragments=normativa_fragments,
            openai_api_key=openai_api_key
        )

        # Paso 5: Validar puestos
        status_text.text(f"🔍 Validando {len(puestos_to_validate)} puestos...")
        progress_bar.progress(50)

        def update_progress(pct):
            # Mapear 0-100 a 50-90
            adjusted = 50 + int(pct * 0.4)
            progress_bar.progress(adjusted)
            status_text.text(f"🔍 Validando puestos... {pct}%")

        resultados = validator.validate_batch(
            puestos_to_validate,
            progress_callback=update_progress
        )

        # Paso 6: Guardar resultados
        status_text.text("💾 Guardando resultados...")
        progress_bar.progress(95)

        # Guardar en session state
        st.session_state.analysis_results = {
            'timestamp': datetime.now().isoformat(),
            'total_puestos': len(resultados),
            'resultados': resultados,
            'config': {
                'filtros': st.session_state.filters_config,
                'opciones': st.session_state.analysis_options
            }
        }

        # Exportar a JSON si se solicitó
        if st.session_state.analysis_options.get('save_json', True):
            output_dir = Path("output/analisis")
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_path = output_dir / f"analisis_{timestamp}.json"

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(st.session_state.analysis_results, f, ensure_ascii=False, indent=2)

            st.session_state.analysis_results['json_path'] = str(json_path)

        # Finalizar
        progress_bar.progress(100)
        status_text.text("✅ Análisis completado!")

        st.success(f"""
        ✅ **Análisis completado exitosamente**

        - Puestos analizados: **{len(resultados)}**
        - Sistema: **v5.40 (Estable)** con Criterio 3 usando LLM (GPT-4o-mini)
        - Modelo LLM: **GPT-4o-mini** (ahorro 94.6% vs GPT-4o)
        - Criterios aplicados: **3** (Análisis Semántico, Contextual, Impacto de Grupo Jerárquico con LLM)
        - Validaciones adicionales: Duplicados, Malformadas, Marco Legal, Objetivo
        - Matriz de decisión: **2-of-3**
        """)

        st.balloons()

        # Mostrar resumen rápido
        aprobados = sum(1 for r in resultados if r['validacion']['resultado'] in ['APROBADO', 'APROBADO_CON_OBSERVACIONES'])
        rechazados = len(resultados) - aprobados

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Analizados", len(resultados))
        with col2:
            st.metric("✅ Aprobados", aprobados)
        with col3:
            st.metric("❌ Rechazados", rechazados)

        st.markdown("---")

        if st.button("📊 Ver Resultados Detallados", type="primary", use_container_width=True):
            st.session_state.page = 'results'
            st.rerun()

    except Exception as e:
        # Limpiar archivo temporal si existe
        if 'temp_file_path' in locals() and temp_file_path:
            try:
                os.unlink(temp_file_path)
            except:
                pass
        st.error(f"""
        ❌ **Error durante el análisis**

        {str(e)}
        """)

        with st.expander("🔍 Ver detalles del error"):
            import traceback
            st.code(traceback.format_exc())


if __name__ == "__main__":
    show()
