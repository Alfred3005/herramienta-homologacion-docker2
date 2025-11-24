# 🏛️ Sistema de Homologación APF - Interfaz Streamlit

Interfaz web para el análisis y validación de puestos de la Administración Pública Federal.

## 🚀 Inicio Rápido

### Instalación

```bash
cd streamlit_app
pip install -r requirements.txt
```

### Ejecutar la Aplicación

```bash
streamlit run app.py
```

La aplicación se abrirá automáticamente en tu navegador en `http://localhost:8501`

## 📁 Estructura del Proyecto

```
streamlit_app/
├── app.py                    # Aplicación principal
├── pages/                    # Páginas de la aplicación
│   ├── home.py              # Dashboard principal
│   ├── new_analysis.py      # Wizard de nuevo análisis
│   ├── results.py           # Visualización de resultados
│   └── history.py           # Historial de análisis
├── utils/                    # Utilidades
├── components/              # Componentes reusables
├── requirements.txt         # Dependencias
└── README.md               # Este archivo
```

## 🎯 Funcionalidades

### ✅ Implementado

- Dashboard principal con métricas
- Wizard de nuevo análisis (4 pasos)
- Upload de archivos (Sidegor Excel + Normativa)
- Configuración de filtros (Nivel, UR, Código)
- Opciones de análisis
- Navegación entre páginas

### 🔄 En Desarrollo

- Integración con sistema v5.0
- Procesamiento en tiempo real
- Visualización de resultados
- Exportación de reportes
- Historial de análisis

## 📖 Uso

### 1. Crear Nuevo Análisis

1. Haz clic en **"Nuevo Análisis"** en el sidebar
2. **Paso 1**: Sube tu archivo Excel Sidegor y el reglamento
3. **Paso 2**: Configura filtros (nivel salarial, UR, código)
4. **Paso 3**: Selecciona opciones de análisis
5. **Paso 4**: Confirma y ejecuta

### 2. Ver Resultados

- Los análisis completados aparecen en el dashboard
- Haz clic en **"Ver"** para ver detalles
- Exporta resultados en PDF, Excel o JSON

## 🔧 Configuración

### Variables de Entorno

```bash
# Opcional: API Key de OpenAI
export OPENAI_API_KEY="sk-..."
```

### Personalización

Edita `app.py` para modificar:
- Colores del tema
- Logo de la aplicación
- Textos y mensajes
- Enlaces de ayuda

## 🚀 Deployment

### Streamlit Cloud (Gratis)

1. Sube el código a GitHub
2. Ve a [share.streamlit.io](https://share.streamlit.io)
3. Conecta tu repositorio
4. ¡Listo! Tu app estará en línea

### Docker

```bash
docker build -t apf-homologacion .
docker run -p 8501:8501 apf-homologacion
```

## 📝 TODO

- [ ] Integrar con pipeline v5.0
- [ ] Implementar procesamiento asíncrono
- [ ] Añadir gráficas de resultados
- [ ] Exportación de reportes
- [ ] Sistema de notificaciones
- [ ] Autenticación de usuarios

## 💡 Soporte

- 📖 [Documentación Completa](../PROPUESTA_INTERFACES_WEB.md)
- 🐛 [Reportar Bug](https://github.com/tu-repo/issues)
- 💬 [Contacto](mailto:soporte@example.com)

---

**Versión**: 1.0.0
**Última actualización**: 2025-11-04
