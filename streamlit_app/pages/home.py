"""
Página Principal - Dashboard
Muestra resumen de análisis, estadísticas y acceso rápido a funcionalidades
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path

def show():
    """Renderiza la página de inicio / dashboard"""

    # Header
    st.title("🏛️ Sistema de Homologación APF")
    st.markdown("### Bienvenido al sistema de análisis y validación de puestos")

    # Banner v5.42
    st.info("""
    🎉 **Nueva versión v5.42** - Sistema de Reportes RH Net Multi-Formato

    Ahora puedes descargar reportes de puestos en formato RH Net oficial en 4 formatos diferentes:
    📝 TXT | 🌐 HTML | 📕 PDF | 📘 DOCX

    Ideal para control, auditoría y contrastar información de entrada vs análisis.
    Disponible en la página de **Resultados** → Sección de puesto individual.
    """)

    st.markdown("---")

    # Métricas principales
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>1,847</h3>
            <p>🎯 Puestos Totales</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="metric-card" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
            <h3>1,652</h3>
            <p>✅ Aceptados</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="metric-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
            <h3>195</h3>
            <p>❌ Rechazados</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown("""
        <div class="metric-card" style="background: linear-gradient(135deg, #ffa726 0%, #fb8c00 100%);">
            <h3>3</h3>
            <p>⏱️ En Proceso</p>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown("""
        <div class="metric-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
            <h3>89.4%</h3>
            <p>📊 Tasa Aprobación</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Gráfica de análisis por mes
    st.subheader("📈 Análisis Ejecutados (Últimos 6 Meses)")

    # Datos de ejemplo
    months = ["Jun", "Jul", "Ago", "Sep", "Oct", "Nov"]
    values = [45, 52, 48, 63, 58, 67]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=months,
        y=values,
        marker=dict(
            color=values,
            colorscale='Viridis',
            showscale=False
        ),
        text=values,
        textposition='outside',
    ))

    fig.update_layout(
        height=300,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis_title="Mes",
        yaxis_title="Cantidad",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Gráfica de criterios de fallo
    st.subheader("🚫 Criterios Más Comunes de Rechazo")

    # Datos de ejemplo de criterios de fallo
    criterios = [
        "Verbos débiles sin respaldo",
        "Desalineación contextual",
        "Referencias institucionales incorrectas",
        "Falta de herencia jerárquica",
        "Funciones genéricas no verificables"
    ]

    frecuencias = [78, 52, 34, 21, 10]

    # Crear gráfica de barras horizontales
    fig_criterios = go.Figure()
    fig_criterios.add_trace(go.Bar(
        y=criterios,
        x=frecuencias,
        orientation='h',
        marker=dict(
            color=frecuencias,
            colorscale='Reds',
            showscale=False
        ),
        text=frecuencias,
        textposition='outside',
    ))

    fig_criterios.update_layout(
        height=350,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis_title="Número de Rechazos",
        yaxis_title="",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        yaxis={'categoryorder':'total ascending'}
    )

    st.plotly_chart(fig_criterios, use_container_width=True)

    st.markdown("---")

    # Análisis recientes
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("🔥 Análisis Recientes")

        # Cargar análisis reales del output si existen
        output_dir = Path("output")
        recent_analyses = []

        if output_dir.exists():
            # Buscar directorios de análisis
            analysis_dirs = sorted(
                [d for d in output_dir.iterdir() if d.is_dir() and "Reporte" in d.name],
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )[:5]  # Últimos 5

            for analysis_dir in analysis_dirs:
                # Extraer información del nombre del directorio
                name_parts = analysis_dir.name.split("_")
                status = "✅ Completo"

                # Buscar archivo de resumen
                resumen_file = analysis_dir / "resumen.txt"
                puestos_count = "?"

                if resumen_file.exists():
                    with open(resumen_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if "Total de puestos encontrados:" in content:
                            for line in content.split('\n'):
                                if "Total de puestos encontrados:" in line:
                                    puestos_count = line.split(':')[1].strip()
                                    break

                # Fecha de modificación
                mtime = datetime.fromtimestamp(analysis_dir.stat().st_mtime)
                fecha = mtime.strftime("%Y-%m-%d %H:%M")

                recent_analyses.append({
                    "nombre": analysis_dir.name[:50] + "..." if len(analysis_dir.name) > 50 else analysis_dir.name,
                    "status": status,
                    "puestos": puestos_count,
                    "fecha": fecha,
                    "path": str(analysis_dir)
                })

        # Si no hay análisis, mostrar datos de ejemplo
        if not recent_analyses:
            recent_analyses = [
                {"nombre": "TURISMO G-K", "status": "✅ Completo", "puestos": "25", "fecha": "2025-11-04 08:26", "path": "output/turismo"},
                {"nombre": "SABG Nivel M", "status": "🔄 Procesando", "puestos": "15/20", "fecha": "2025-11-03 14:30", "path": ""},
                {"nombre": "SADER Niveles 1-3", "status": "✅ Completo", "puestos": "82", "fecha": "2025-11-02 10:15", "path": ""},
            ]

        # Mostrar análisis
        for idx, analysis in enumerate(recent_analyses):
            with st.container():
                col_a, col_b, col_c, col_d = st.columns([3, 2, 2, 1])

                with col_a:
                    st.markdown(f"**📄 {analysis['nombre']}**")

                with col_b:
                    st.markdown(f"{analysis['status']}")

                with col_c:
                    st.markdown(f"🔢 {analysis['puestos']} puestos")

                with col_d:
                    if analysis.get('path') and Path(analysis['path']).exists():
                        if st.button("Ver", key=f"view_{idx}"):
                            st.session_state.current_analysis = analysis['path']
                            st.session_state.page = 'results'
                            st.rerun()

                st.caption(f"📅 {analysis['fecha']}")

                if idx < len(recent_analyses) - 1:
                    st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.3;'>", unsafe_allow_html=True)

    with col_right:
        st.subheader("📊 Estadísticas")

        st.metric(
            label="Funciones Extraídas",
            value="12,458",
            delta="↑ 360 esta semana"
        )

        st.metric(
            label="Tiempo Promedio",
            value="11.2 min",
            delta="↓ -1.3 min"
        )

        st.metric(
            label="Puestos Procesados",
            value="1,847",
            delta="↑ 125 este mes"
        )

    st.markdown("---")

    # Tips y ayuda
    st.subheader("💡 Tips y Ayuda")

    tab1, tab2, tab3 = st.tabs(["🚀 Inicio Rápido", "📖 Guías", "❓ FAQ"])

    with tab1:
        st.markdown("""
        ### Cómo empezar:

        1. **Preparar archivos**:
           - Base de datos Sidegor (.xlsx)
           - Normativa o reglamento (.txt, .pdf)

        2. **Ir a "Nuevo Análisis"**:
           - Subir archivos
           - Configurar filtros (nivel, UR, código)
           - Ejecutar análisis

        3. **Ver resultados**:
           - Dashboard con estadísticas
           - Tablas interactivas
           - Exportar reportes (PDF, Excel, JSON)

        **💡 Tip**: Empieza con un filtro pequeño (ej: 10-20 puestos) para probar.
        """)

    with tab2:
        st.markdown("""
        ### Guías Disponibles:

        - 📘 [Guía de Procesamiento en Lote](../GUÍA_PROCESAMIENTO_LOTE.md)
        - 📗 [Estrategia de Validación](../VALIDATION_STRATEGY.md)
        - 📙 [Diseño de Sistema](../DISEÑO_PROCESAMIENTO_LOTE_SIDEGOR.md)

        ### Videos Tutoriales:
        - 🎥 Análisis Básico (5 min)
        - 🎥 Filtros Avanzados (8 min)
        - 🎥 Interpretación de Resultados (10 min)
        """)

    with tab3:
        st.markdown("""
        ### Preguntas Frecuentes:

        **¿Qué formatos de archivo acepta?**
        - Excel Sidegor: `.xlsx`
        - Normativas: `.txt`, `.pdf`, `.docx`

        **¿Cuánto tarda un análisis?**
        - Depende del número de puestos (≈30s por puesto)
        - 25 puestos: ~12 minutos
        - 100 puestos: ~50 minutos

        **¿Puedo pausar un análisis?**
        - Sí, desde la página de procesamiento

        **¿Se guardan los resultados?**
        - Sí, todos los análisis se guardan automáticamente

        **¿Puedo exportar los resultados?**
        - Sí, en formatos PDF, Excel y JSON
        """)

    st.markdown("---")

    # Footer informativo
    st.info("""
    **💡 Nota**: Este sistema utiliza GPT-4o para análisis inteligente de funciones.
    Los resultados son generados automáticamente y deben ser revisados por expertos en la materia.
    """)

if __name__ == "__main__":
    show()
