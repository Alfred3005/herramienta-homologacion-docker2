"""
Página de Resultados Detallados
Muestra análisis guardados con métricas y descarga de reportes
"""
import streamlit as st
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
import sys

# Añadir directorio src al path para importar módulos
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.utils.report_humanizer import humanize_report
from src.adapters.rhnet_report_generator import RHNetReportGenerator
from src.adapters.report_exporters import exportar_reporte

def show():
    st.title("📊 Resultados Detallados de Análisis")

    # Obtener análisis guardados
    output_dir = Path("output/analisis")
    if not output_dir.exists():
        st.warning("📁 No se encontraron análisis guardados")
        return

    json_files = sorted(output_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)

    if not json_files:
        st.info("🔍 No hay análisis disponibles. Realiza un análisis en la página 'Nuevo Análisis'")
        return

    # Selector de análisis
    st.markdown("### 🗂️ Seleccionar Análisis")

    file_options = {}
    for f in json_files[:10]:  # Mostrar últimos 10
        try:
            with open(f, 'r') as file:
                data = json.load(file)
                timestamp = datetime.fromisoformat(data.get('timestamp', ''))
                fecha_str = timestamp.strftime('%d/%m/%Y %H:%M:%S')
                total = data.get('total_puestos', 0)
                label = f"{fecha_str} - {total} puestos"
                file_options[label] = f
        except:
            continue

    if not file_options:
        st.error("❌ No se pudieron cargar los análisis")
        return

    selected_label = st.selectbox(
        "Análisis disponibles:",
        options=list(file_options.keys())
    )

    selected_file = file_options[selected_label]

    # Cargar datos
    with open(selected_file, 'r') as f:
        data = json.load(f)

    # Separador
    st.markdown("---")

    # SECCIÓN 1: Resumen General
    st.markdown("## 📈 Resumen General")

    total_puestos = data['total_puestos']
    resultados = data['resultados']

    aprobados = [r for r in resultados if r.get('validacion', {}).get('resultado') in ['APROBADO_CON_OBSERVACIONES', 'APROBADO_PLENO']]
    rechazados = [r for r in resultados if r.get('validacion', {}).get('resultado') == 'RECHAZADO']

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="📋 Total Analizado",
            value=total_puestos
        )

    with col2:
        st.metric(
            label="✅ Aprobados",
            value=len(aprobados),
            delta=f"{len(aprobados)/total_puestos*100:.0f}%"
        )

    with col3:
        st.metric(
            label="❌ Rechazados",
            value=len(rechazados),
            delta=f"-{len(rechazados)/total_puestos*100:.0f}%",
            delta_color="inverse"
        )

    with col4:
        # Calcular confianza promedio de manera segura
        confianzas = [r['validacion'].get('confianza', 0.0) for r in resultados if 'confianza' in r.get('validacion', {})]
        confianza_prom = sum(confianzas) / len(confianzas) if confianzas else 0.0
        st.metric(
            label="🎯 Confianza Promedio",
            value=f"{confianza_prom:.2f}"
        )

    # SECCIÓN 2: Gráficos
    st.markdown("---")
    st.markdown("## 📊 Visualizaciones")

    tab1, tab2, tab3 = st.tabs(["Distribución", "Por Criterio", "Detalle Puestos"])

    with tab1:
        # Gráfico de pastel
        fig_pie = go.Figure(data=[go.Pie(
            labels=['Aprobados', 'Rechazados'],
            values=[len(aprobados), len(rechazados)],
            marker=dict(colors=['#4CAF50', '#F44336']),
            hole=0.4
        )])
        fig_pie.update_layout(
            title="Distribución de Resultados",
            height=400
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with tab2:
        # Análisis por criterio
        criterios_data = {
            'Criterio': [],
            'PASS': [],
            'FAIL': []
        }

        for criterio_key, criterio_name in [
            ('criterio_1_verbos', 'Verbos Débiles'),
            ('criterio_2_contextual', 'Contextual'),
            ('criterio_3_impacto', 'Impacto de Grupo Jerárquico')
        ]:
            pass_count = sum(1 for r in resultados
                           if r.get('validacion', {}).get('criterios', {}).get(criterio_key, {}).get('resultado') == 'PASS')
            fail_count = sum(1 for r in resultados
                           if r.get('validacion', {}).get('criterios', {}).get(criterio_key, {}).get('resultado') == 'FAIL')

            criterios_data['Criterio'].append(criterio_name)
            criterios_data['PASS'].append(pass_count)
            criterios_data['FAIL'].append(fail_count)

        df_criterios = pd.DataFrame(criterios_data)

        fig_criterios = go.Figure(data=[
            go.Bar(name='PASS', x=df_criterios['Criterio'], y=df_criterios['PASS'], marker_color='#4CAF50'),
            go.Bar(name='FAIL', x=df_criterios['Criterio'], y=df_criterios['FAIL'], marker_color='#F44336')
        ])
        fig_criterios.update_layout(
            title="Resultados por Criterio",
            barmode='stack',
            height=400
        )
        st.plotly_chart(fig_criterios, use_container_width=True)

        # Estadísticas de criterios
        col1, col2, col3 = st.columns(3)

        with col1:
            c1_tasas = [r.get('validacion', {}).get('criterios', {}).get('criterio_1_verbos', {}).get('tasa_critica', 0)
                       for r in resultados]
            c1_tasas = [t for t in c1_tasas if t is not None]
            c1_prom = sum(c1_tasas)/len(c1_tasas) if c1_tasas else 0
            st.metric("Criterio 1 - Tasa Crítica Prom.", f"{c1_prom:.0%}")

        with col2:
            c2_confianzas = [r.get('validacion', {}).get('criterios', {}).get('criterio_2_contextual', {}).get('alineacion', {}).get('confianza', 0)
                            for r in resultados]
            c2_confianzas = [c for c in c2_confianzas if c is not None]
            c2_prom = sum(c2_confianzas)/len(c2_confianzas) if c2_confianzas else 0
            st.metric("Criterio 2 - Confianza Prom.", f"{c2_prom:.2f}")

        with col3:
            c3_tasas = [r.get('validacion', {}).get('criterios', {}).get('criterio_3_impacto', {}).get('metricas', {}).get('tasa_critica', 0)
                       for r in resultados]
            c3_tasas = [t for t in c3_tasas if t is not None]
            c3_prom = sum(c3_tasas)/len(c3_tasas) if c3_tasas else 0
            st.metric("Criterio 3 - Tasa Crítica Prom.", f"{c3_prom:.0%}")

    with tab3:
        # Tabla detallada de puestos
        st.markdown("### 📋 Detalle de Todos los Puestos")

        tabla_data = []
        for r in resultados:
            puesto = r.get('puesto', {})
            val = r.get('validacion', {})
            c1 = val.get('criterios', {}).get('criterio_1_verbos', {})
            c2 = val.get('criterios', {}).get('criterio_2_contextual', {})
            c3 = val.get('criterios', {}).get('criterio_3_impacto', {})

            tabla_data.append({
                'Código': puesto.get('codigo', 'N/A'),
                'Denominación': puesto.get('denominacion', 'N/A'),
                'Nivel': puesto.get('nivel', puesto.get('nivel_salarial', 'N/A')),
                'Resultado': val.get('resultado', 'N/A'),
                'Confianza': f"{val.get('confianza', 0.0):.2f}",
                'C1 (Verbos)': c1.get('resultado', 'N/A'),
                'C1 Tasa': f"{c1.get('tasa_critica', 0):.0%}",
                'C2 (Context)': c2.get('resultado', 'N/A'),
                'C2 Conf': f"{c2.get('alineacion', {}).get('confianza', 0.0):.2f}",
                'C3 (Impacto)': c3.get('resultado', 'N/A'),
                'C3 Tasa': f"{c3.get('metricas', {}).get('tasa_critica', 0):.0%}"
            })

        df_detalle = pd.DataFrame(tabla_data)

        # Aplicar estilo
        def color_resultado(val):
            if 'APROBADO' in val:
                return 'background-color: #C8E6C9'
            elif 'RECHAZADO' in val:
                return 'background-color: #FFCDD2'
            return ''

        def color_criterio(val):
            if val == 'PASS':
                return 'background-color: #C8E6C9'
            elif val == 'FAIL':
                return 'background-color: #FFCDD2'
            return ''

        styled_df = df_detalle.style.applymap(
            color_resultado, subset=['Resultado']
        ).applymap(
            color_criterio, subset=['C1 (Verbos)', 'C2 (Context)', 'C3 (Impacto)']
        )

        st.dataframe(styled_df, use_container_width=True, height=600)

    # SECCIÓN 3: Descargas
    st.markdown("---")
    st.markdown("## 💾 Descargar Reportes")

    col1, col2 = st.columns(2)

    with col1:
        # Descargar JSON completo
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        st.download_button(
            label="📄 Descargar JSON Completo",
            data=json_str,
            file_name=f"analisis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )

    with col2:
        # Descargar Excel con resultados
        excel_data = df_detalle.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📊 Descargar CSV",
            data=excel_data,
            file_name=f"resultados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

    # SECCIÓN 3.5: Humanización de Reportes con LLM
    st.markdown("---")
    st.markdown("## 🤖 Generar Reporte Humanizado")
    st.markdown("Convierte el análisis técnico a lenguaje natural comprensible para auditoría y revisión humana.")

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        modo_reporte = st.selectbox(
            "Selecciona el tipo de reporte:",
            options=["simplificado", "detallado"],
            format_func=lambda x: "📋 Resumen Ejecutivo (1-2 páginas)" if x == "simplificado" else "📊 Análisis Completo para Auditoría",
            help="Simplificado: Resumen breve para decisiones rápidas. Detallado: Análisis exhaustivo con evidencias."
        )

    with col2:
        generar_btn = st.button("🚀 Generar Reporte", type="primary", use_container_width=True)

    with col3:
        if 'reporte_humanizado' in st.session_state:
            st.download_button(
                label="💾 Descargar MD",
                data=st.session_state['reporte_humanizado'],
                file_name=f"reporte_{modo_reporte}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown",
                use_container_width=True
            )

    if generar_btn:
        with st.spinner(f"🤖 Generando reporte {modo_reporte}... (esto puede tomar 10-30 segundos)"):
            try:
                # Generar reporte usando LLM
                reporte = humanize_report(str(selected_file), modo_reporte)

                # Guardar en session_state para descargar
                st.session_state['reporte_humanizado'] = reporte

                # Mostrar reporte
                st.success(f"✅ Reporte {modo_reporte} generado exitosamente!")
                st.markdown("### 📄 Vista Previa del Reporte")

                # Mostrar en expander para no ocupar mucho espacio
                with st.expander("📖 Ver reporte completo", expanded=True):
                    st.markdown(reporte)

            except Exception as e:
                st.error(f"❌ Error al generar reporte: {str(e)}")
                st.exception(e)

    # Mostrar reporte previo si existe
    elif 'reporte_humanizado' in st.session_state:
        st.info("💡 Hay un reporte generado previamente. Usa el botón 'Descargar MD' o genera uno nuevo.")

    # SECCIÓN 4: Análisis Detallado de Puestos
    st.markdown("---")
    st.markdown("## 🔍 Explorar Puesto Individual")

    puestos_dict = {f"{r.get('puesto', {}).get('codigo', 'N/A')} - {r.get('puesto', {}).get('denominacion', 'N/A')}": r for r in resultados}
    selected_puesto = st.selectbox(
        "Selecciona un puesto para ver detalles:",
        options=list(puestos_dict.keys())
    )

    if selected_puesto:
        puesto_data = puestos_dict[selected_puesto]
        puesto = puesto_data.get('puesto', {})
        val = puesto_data.get('validacion', {})

        st.markdown(f"### {puesto.get('denominacion', 'N/A')}")
        st.markdown(f"**Código:** {puesto.get('codigo', 'N/A')} | **Nivel:** {puesto.get('nivel', puesto.get('nivel_salarial', 'N/A'))}")

        # Resultado general
        resultado = val.get('resultado', 'N/A')
        if resultado in ['APROBADO_CON_OBSERVACIONES', 'APROBADO_PLENO']:
            st.success(f"✅ {resultado}")
        else:
            st.error(f"❌ {resultado}")

        st.markdown(f"**Confianza Global:** {val.get('confianza', 0.0):.2f}")
        st.markdown(f"**Criterios Aprobados:** {val.get('criterios_aprobados', 0)}/3")

        # SECCIÓN: Descargar Reporte RHNet
        st.markdown("---")
        st.markdown("#### 📄 Descargar Reporte RHNet (Control y Auditoría)")
        st.caption("Genera reporte del puesto en formato RH Net para contrastar información de entrada vs resultados del análisis")
        st.info("ℹ️ **Nota:** El reporte incluye los datos disponibles del análisis. Algunos campos como perfil, escolaridad y competencias pueden no estar disponibles según la fuente de datos original.")

        # Preparar datos para el generador
        try:
            # Extraer funciones desde la validación (ubicación real en el JSON)
            funciones_extraidas = []
            c1_data = val.get('criterios', {}).get('criterio_1_verbos', {})
            detalles = c1_data.get('detalles', {})

            # Agregar funciones de todas las categorías
            for categoria in ['aprobadas', 'observadas', 'rechazadas']:
                for func in detalles.get(categoria, []):
                    funcion_texto = func.get('funcion_text', func.get('descripcion', func.get('descripcion_completa', '')))
                    if funcion_texto:
                        funciones_extraidas.append({"descripcion_completa": funcion_texto})

            # Si no hay funciones en detalles, intentar desde el puesto directamente
            if not funciones_extraidas and puesto.get('funciones'):
                funciones_extraidas = [
                    {"descripcion_completa": f.get('descripcion', f.get('descripcion_completa', f.get('texto', '')))}
                    for f in puesto.get('funciones', [])
                ]

            # Construir estructura de datos compatible con RHNetReportGenerator
            datos_reporte = {
                "identificacion_puesto": {
                    "codigo_puesto": puesto.get('codigo', 'N/A'),
                    "denominacion_puesto": puesto.get('denominacion', 'N/A'),
                    "caracter_ocupacional": puesto.get('caracter_ocupacional', 'N/A'),
                    "nivel_salarial": {
                        "codigo": puesto.get('nivel', puesto.get('nivel_salarial', 'N/A')),
                        "descripcion": ""
                    },
                    "persona_en_puesto": puesto.get('persona_en_puesto', 'N/A'),
                    "puestos_dependientes": puesto.get('puestos_dependientes', 'N/A'),
                    "unidad_responsable": puesto.get('unidad_responsable', puesto.get('ur', 'N/A')),
                    "ramo": puesto.get('ramo', 'N/A'),
                    "estatus": puesto.get('estatus', 'N/A')
                },
                "objetivo_general": {
                    "descripcion_completa": puesto.get('objetivo_general', 'No disponible (datos no incluidos en análisis)')
                },
                "funciones": funciones_extraidas if funciones_extraidas else [{"descripcion_completa": "No disponible (datos no incluidos en análisis)"}],
                "escolaridad": puesto.get('escolaridad', {
                    "nivel_estudios": "NO APLICA",
                    "grado_avance": "NO APLICA",
                    "area_general": "NO APLICA",
                    "carrera_generica": "NO APLICA"
                }),
                "experiencia": puesto.get('experiencia', {
                    "anos_experiencia": "NO APLICA",
                    "area_general": "NO APLICA",
                    "area_experiencia": "NO APLICA"
                }),
                "condiciones_trabajo": puesto.get('condiciones_trabajo', {
                    "horario": "Diurno",
                    "disponibilidad_viajar": "A veces",
                    "periodos_especiales": "NO",
                    "cambio_residencia": "NO"
                }),
                "entorno_operativo": puesto.get('entorno_operativo', {
                    "tipo_relacion": "Ambas",
                    "explicacion": "No disponible",
                    "caracteristica_informacion": "No disponible"
                }),
                "competencias": puesto.get('competencias', []),
                "observaciones": puesto.get('observaciones', {
                    "observaciones_generales": "",
                    "observaciones_especialista": ""
                })
            }

            # Generar reporte
            generador = RHNetReportGenerator()
            reporte_texto = generador.generar_reporte_completo(datos_reporte)

            # Metadata para exportadores
            metadata = {
                "codigo_puesto": puesto.get('codigo', 'N/A'),
                "fecha_generacion": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            # Botones de descarga en columnas
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                # TXT
                txt_bytes = exportar_reporte(reporte_texto, 'txt', metadata)
                st.download_button(
                    label="📝 TXT",
                    data=txt_bytes,
                    file_name=f"reporte_rhnet_{puesto.get('codigo', 'puesto')}.txt",
                    mime="text/plain",
                    use_container_width=True,
                    help="Descargar como texto plano"
                )

            with col2:
                # HTML
                html_bytes = exportar_reporte(reporte_texto, 'html', metadata)
                st.download_button(
                    label="🌐 HTML",
                    data=html_bytes,
                    file_name=f"reporte_rhnet_{puesto.get('codigo', 'puesto')}.html",
                    mime="text/html",
                    use_container_width=True,
                    help="Descargar como página web"
                )

            with col3:
                # PDF
                try:
                    pdf_bytes = exportar_reporte(reporte_texto, 'pdf', metadata)
                    st.download_button(
                        label="📕 PDF",
                        data=pdf_bytes,
                        file_name=f"reporte_rhnet_{puesto.get('codigo', 'puesto')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        help="Descargar como PDF (requiere fpdf2)"
                    )
                except ImportError:
                    st.button("📕 PDF", disabled=True, use_container_width=True, help="Instalar fpdf2: pip install fpdf2")

            with col4:
                # DOCX
                try:
                    docx_bytes = exportar_reporte(reporte_texto, 'docx', metadata)
                    st.download_button(
                        label="📘 DOCX",
                        data=docx_bytes,
                        file_name=f"reporte_rhnet_{puesto.get('codigo', 'puesto')}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                        help="Descargar como Word (requiere python-docx)"
                    )
                except ImportError:
                    st.button("📘 DOCX", disabled=True, use_container_width=True, help="Instalar python-docx: pip install python-docx")

            # Preview del reporte (opcional)
            with st.expander("👁️ Vista Previa del Reporte RHNet"):
                st.text(reporte_texto)

        except Exception as e:
            st.error(f"⚠️ Error al generar reporte RHNet: {str(e)}")
            st.caption("Algunos datos pueden no estar disponibles en el análisis")

        st.markdown("---")

        # Detalles por criterio
        st.markdown("#### 📊 Detalles por Criterio")

        c1, c2, c3 = st.columns(3)

        with c1:
            c1_data = val.get('criterios', {}).get('criterio_1_verbos', {})
            with st.container():
                st.markdown("**Criterio 1: Verbos Débiles**")
                if c1_data.get('resultado') == 'PASS':
                    st.success("✅ PASS")
                else:
                    st.error("❌ FAIL")
                st.metric("Tasa Crítica", f"{c1_data.get('tasa_critica', 0):.0%}")
                st.caption(f"Rechazadas: {c1_data.get('funciones_rechazadas', 0)}/{c1_data.get('total_funciones', 0)}")

        with c2:
            c2_data = val.get('criterios', {}).get('criterio_2_contextual', {})
            with st.container():
                st.markdown("**Criterio 2: Contextual**")
                if c2_data.get('resultado') == 'PASS':
                    st.success("✅ PASS")
                else:
                    st.error("❌ FAIL")
                st.metric("Confianza", f"{c2_data.get('alineacion', {}).get('confianza', 0.0):.2f}")
                st.caption(f"Alineación: {c2_data.get('alineacion', {}).get('clasificacion', 'N/A')}")

        with c3:
            c3_data = val.get('criterios', {}).get('criterio_3_impacto', {})
            with st.container():
                st.markdown("**Criterio 3: Impacto**")
                if c3_data.get('resultado') == 'PASS':
                    st.success("✅ PASS")
                else:
                    st.error("❌ FAIL")
                st.metric("Tasa Crítica", f"{c3_data.get('metricas', {}).get('tasa_critica', 0):.0%}")
                st.caption(f"Critical: {c3_data.get('metricas', {}).get('funciones_critical', 0)}")

        # Razonamiento
        with st.expander("📝 Ver Razonamiento Detallado"):
            st.markdown(val.get('razonamiento', 'N/A'))
            st.markdown(f"**Acción Requerida:** {val.get('accion_requerida', 'N/A')}")

if __name__ == "__main__":
    show()
