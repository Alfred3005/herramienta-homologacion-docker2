# Dockerfile Multi-Stage para Sistema de Homologación APF v5
# Optimizado para uso con Ollama local y modelos pequeños (Phi-3.5 Mini)
# Hardware mínimo: 16GB RAM, 6GB VRAM

# ==========================================
# STAGE 1: Builder - Construcción de dependencias
# ==========================================
FROM python:3.12-slim as builder

LABEL maintainer="Sistema Homologación APF"
LABEL description="Sistema de validación de puestos APF con LLM local"

# Variables de entorno para optimización
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalar dependencias del sistema necesarias para compilar
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar archivos de requerimientos
COPY requirements.txt .
COPY streamlit_app/requirements.txt ./streamlit_requirements.txt

# Instalar dependencias Python en entorno virtual
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Instalar dependencias principales
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install -r streamlit_requirements.txt

# ==========================================
# STAGE 2: Runtime - Imagen final optimizada
# ==========================================
FROM python:3.12-slim

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_HEADLESS=true

# Instalar solo dependencias runtime mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copiar entorno virtual desde builder
COPY --from=builder /opt/venv /opt/venv

# Crear usuario no-root para seguridad
RUN useradd -m -u 1000 apfuser && \
    mkdir -p /app /data && \
    chown -R apfuser:apfuser /app /data

# Cambiar a usuario no-root
USER apfuser

# Directorio de trabajo
WORKDIR /app

# Copiar código fuente
COPY --chown=apfuser:apfuser . .

# Crear directorios necesarios
RUN mkdir -p /app/logs /app/cache /app/uploads

# Exponer puerto de Streamlit
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Comando por defecto: ejecutar Streamlit app
CMD ["streamlit", "run", "streamlit_app/app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
