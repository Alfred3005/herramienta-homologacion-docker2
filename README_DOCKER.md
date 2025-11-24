# 🐳 Dockerización del Sistema de Homologación APF v5 con LLM Local

Sistema completamente dockerizado con **Phi-3.5 Mini** ejecutándose localmente vía **Ollama**. Optimizado para hardware con **6GB VRAM**.

---

## 📋 Tabla de Contenidos

- [Requisitos](#-requisitos)
- [Arquitectura](#-arquitectura)
- [Instalación](#-instalación)
- [Uso](#-uso)
- [Monitoreo](#-monitoreo)
- [Optimización](#-optimización)
- [Troubleshooting](#-troubleshooting)
- [Comparativa](#-comparativa-local-vs-api)

---

## 🔧 Requisitos

### Hardware Mínimo

| Componente | Mínimo | Recomendado |
|------------|--------|-------------|
| **RAM** | 16 GB | 24 GB |
| **VRAM** | 6 GB | 8-12 GB |
| **Disco** | 20 GB libres | 50 GB libres |
| **GPU** | NVIDIA con CUDA | NVIDIA RTX serie |
| **CPU** | 4 cores | 8+ cores |

### Software

- ✅ **Docker** >= 20.10
- ✅ **Docker Compose** >= 2.0
- ✅ **NVIDIA Docker Runtime** (nvidia-docker2)
- ✅ **Drivers NVIDIA** >= 525.60.13
- ✅ **CUDA** >= 12.0 (incluido en drivers)

### Verificación de Requisitos

```bash
# Verificar Docker
docker --version
docker compose version

# Verificar GPU NVIDIA
nvidia-smi

# Verificar NVIDIA Docker
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi
```

---

## 🏗️ Arquitectura

### Diagrama de Contenedores

```
┌─────────────────────────────────────────────────┐
│              Docker Host (Ubuntu/Linux)         │
│                                                 │
│  ┌──────────────────────┐  ┌─────────────────┐ │
│  │   apf-homologacion   │  │   apf-ollama    │ │
│  │   (Streamlit App)    │◄─┤   (LLM Server)  │ │
│  │                      │  │                 │ │
│  │   Port: 8501         │  │   Port: 11434   │ │
│  │   CPU only           │  │   GPU enabled   │ │
│  └──────────────────────┘  └─────────────────┘ │
│           ↓                        ↓            │
│      [app_data]             [ollama_models]     │
│      [app_cache]                 (~3GB)         │
└─────────────────────────────────────────────────┘
         ↓                           ↓
   Usuario Web                  GPU (6GB VRAM)
  (localhost:8501)
```

### Componentes

1. **apf-homologacion** (Contenedor Python + Streamlit)
   - Interfaz web del sistema
   - Lógica de validación
   - Comunicación con Ollama

2. **apf-ollama** (Contenedor Ollama)
   - Servidor de LLM local
   - Phi-3.5 Mini pre-cargado
   - Optimizado para 6GB VRAM

3. **apf-ollama-init** (Contenedor temporal)
   - Descarga Phi-3.5 Mini al inicio
   - Se ejecuta una vez y termina

---

## 📦 Instalación

### Paso 1: Instalar Docker + NVIDIA Runtime

#### Ubuntu/Debian

```bash
# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Agregar usuario al grupo docker
sudo usermod -aG docker $USER
newgrp docker

# Instalar NVIDIA Docker
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker

# Verificar instalación
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi
```

### Paso 2: Clonar Repositorio

```bash
cd ~
git clone https://github.com/Alfred3005/herramienta-homologacion-v5.git
cd herramienta-homologacion-v5
```

### Paso 3: Configurar Variables de Entorno

```bash
# Copiar archivo de ejemplo
cp .env.docker .env

# Editar si es necesario (opcional)
nano .env
```

**Configuración por defecto (.env):**
```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://ollama:11434
LLM_MODEL=phi3.5
MAX_CONCURRENT_ANALYSIS=1
OLLAMA_MAX_LOADED_MODELS=1
```

### Paso 4: Construir e Iniciar Contenedores

```bash
# Construir imágenes
docker compose build

# Iniciar servicios (incluye descarga automática de Phi-3.5)
docker compose up -d

# Ver logs en tiempo real
docker compose logs -f
```

**⏳ Primera vez:** La descarga de Phi-3.5 Mini toma **5-15 minutos** (~2.3GB).

### Paso 5: Verificar Instalación

```bash
# Verificar que todos los contenedores estén corriendo
docker compose ps

# Verificar logs de Ollama
docker compose logs ollama

# Verificar logs de la app
docker compose logs app

# Probar conexión con Ollama
curl http://localhost:11434/api/tags
```

**Salida esperada:**
```json
{
  "models": [
    {
      "name": "phi3.5",
      "size": 2300000000,
      ...
    }
  ]
}
```

---

## 🚀 Uso

### Acceder a la Aplicación

1. Abrir navegador: **http://localhost:8501**
2. La interfaz de Streamlit debería cargar
3. Subir archivo Excel con puestos
4. Subir PDF del reglamento
5. Ejecutar análisis

### Comandos Básicos

```bash
# Iniciar servicios
docker compose up -d

# Detener servicios
docker compose down

# Ver logs
docker compose logs -f

# Reiniciar solo la app (sin reiniciar Ollama)
docker compose restart app

# Reiniciar todo
docker compose restart

# Ver uso de recursos
docker stats

# Acceder al contenedor de la app
docker compose exec app bash

# Acceder al contenedor de Ollama
docker compose exec ollama bash
```

### Monitorear VRAM

```bash
# Una vez
./docker/monitor-vram.sh

# Monitoreo continuo
./docker/monitor-vram.sh --continuous
```

**Salida esperada:**
```
📊 Uso de VRAM:
   Total:       6144 MB (6.00 GB)
   Usada:       4800 MB (4.69 GB)
   Libre:       1344 MB (1.31 GB)
   Porcentaje:  78.1%

🌡️  Temperatura: 68°C
⚙️  Utilización: 85%
```

---

## 🔍 Monitoreo

### Ver Logs en Tiempo Real

```bash
# Todos los servicios
docker compose logs -f

# Solo Ollama
docker compose logs -f ollama

# Solo App
docker compose logs -f app

# Últimas 100 líneas
docker compose logs --tail=100
```

### Verificar Salud de Servicios

```bash
# Health checks
docker compose ps

# Inspeccionar contenedor
docker inspect apf-ollama
docker inspect apf-homologacion
```

### Métricas de Rendimiento

```bash
# Uso de CPU, RAM, VRAM en tiempo real
docker stats

# Solo contenedores APF
docker stats apf-homologacion apf-ollama
```

### Dashboard Web (Opcional)

Instalar Portainer para UI web:

```bash
docker run -d -p 9000:9000 --name portainer \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  portainer/portainer-ce:latest
```

Acceder: **http://localhost:9000**

---

## ⚡ Optimización

### Reducir Uso de VRAM

Si experimentas errores de OOM (Out of Memory):

**1. Usar cuantización más agresiva:**

```bash
# Editar docker-compose.yml, cambiar modelo a versión Q4
# En lugar de "phi3.5", usar "phi3.5:q4_0"
```

**2. Reducir context window:**

Editar `.env`:
```bash
OLLAMA_CONTEXT_SIZE=2048  # Default: 4096
```

**3. Desactivar modelos adicionales:**

```bash
# Asegurar solo 1 modelo cargado
OLLAMA_MAX_LOADED_MODELS=1
OLLAMA_NUM_PARALLEL=1
```

### Mejorar Velocidad

**1. Usar SSD para volúmenes:**

```bash
# Mover volúmenes Docker a SSD
sudo systemctl stop docker
sudo mv /var/lib/docker /mnt/ssd/docker
sudo ln -s /mnt/ssd/docker /var/lib/docker
sudo systemctl start docker
```

**2. Pre-calentar el modelo:**

```bash
# Ejecutar análisis dummy al inicio
docker compose exec ollama ollama run phi3.5 "test"
```

**3. Ajustar parámetros de Ollama:**

Editar `.env`:
```bash
OLLAMA_FLASH_ATTENTION=1  # Reduce latencia
OLLAMA_NUM_GPU=1           # Usar solo 1 GPU
```

### Reducir Espacio en Disco

```bash
# Limpiar imágenes no usadas
docker system prune -a

# Limpiar volúmenes huérfanos
docker volume prune

# Verificar espacio usado
docker system df
```

---

## 🛠️ Troubleshooting

### Problema 1: Ollama no inicia

**Síntomas:**
```
Error: CUDA out of memory
Error: Could not load model
```

**Solución:**
```bash
# Verificar VRAM disponible
nvidia-smi

# Cerrar otros procesos usando GPU
pkill -f python
pkill -f ollama

# Reiniciar contenedor con límites
docker compose down
docker compose up -d
```

### Problema 2: Modelo no descarga

**Síntomas:**
```
Error: Model not found
Error: Connection refused to ollama:11434
```

**Solución:**
```bash
# Descargar manualmente
docker compose exec ollama ollama pull phi3.5

# Verificar descarga
docker compose exec ollama ollama list

# Ver logs de descarga
docker compose logs ollama-init
```

### Problema 3: App no conecta con Ollama

**Síntomas:**
```
LLMProviderError: Could not connect to Ollama
Connection refused: http://ollama:11434
```

**Solución:**
```bash
# Verificar que Ollama esté corriendo
docker compose ps ollama

# Probar conexión manual
docker compose exec app curl http://ollama:11434/api/tags

# Verificar red Docker
docker network inspect herramienta-homologacion-v5_apf-network

# Reiniciar servicios
docker compose restart
```

### Problema 4: Respuestas lentas o timeout

**Síntomas:**
```
LLMProviderTimeoutError: Timeout after 120s
```

**Solución:**

Editar `.env`:
```bash
# Aumentar timeout
LLM_TIMEOUT=300  # 5 minutos

# Reducir tokens generados
MAX_TOKENS=1000  # Reducir si es muy largo
```

### Problema 5: VRAM insuficiente

**Síntomas:**
```
CUDA out of memory
RuntimeError: GPU memory exhausted
```

**Solución:**
```bash
# Opción 1: Usar modelo más pequeño
docker compose down
# Editar .env: LLM_MODEL=llama3.2:1b
docker compose up -d

# Opción 2: Usar cuantización agresiva
# Editar .env: LLM_MODEL=phi3.5:q4_0

# Opción 3: Liberar VRAM
docker compose restart ollama
```

### Problema 6: Puerto 8501 ya en uso

**Síntomas:**
```
Error: bind: address already in use
```

**Solución:**
```bash
# Encontrar proceso usando el puerto
sudo lsof -i :8501

# Matar proceso
kill -9 <PID>

# O cambiar puerto en docker-compose.yml
# ports: - "8502:8501"
```

---

## 📊 Comparativa: Local vs API

### Precisión

| Criterio | GPT-4o-mini (API) | Phi-3.5 Mini (Local) | Diferencia |
|----------|-------------------|----------------------|------------|
| Criterio 1 | 85% | ~72% | -13% |
| Criterio 2 | 87% | ~75% | -12% |
| Criterio 3 | 86% | ~73% | -13% |
| **Promedio** | **86%** | **73%** | **-13%** |

### Velocidad

| Volumen | GPT-4o-mini (API) | Phi-3.5 Mini (Local) | Diferencia |
|---------|-------------------|----------------------|------------|
| 1 puesto | ~60s | ~180s | 3x más lento |
| 10 puestos | ~10 min | ~30 min | 3x más lento |
| 25 puestos | ~15 min | ~60 min | 4x más lento |

### Costos

| Volumen | GPT-4o-mini (API) | Phi-3.5 Mini (Local) | Ahorro |
|---------|-------------------|----------------------|--------|
| 100 puestos | $35 MXN | $0 MXN | 100% |
| 1,000 puestos | $350 MXN | $0 MXN | 100% |
| Electricidad | N/A | ~$5 MXN/mes | Despreciable |

### Trade-offs

| Aspecto | API (GPT-4o-mini) | Local (Phi-3.5) |
|---------|-------------------|-----------------|
| **Precisión** | ⭐⭐⭐⭐⭐ Alta (86%) | ⭐⭐⭐ Media (73%) |
| **Velocidad** | ⭐⭐⭐⭐⭐ Rápida | ⭐⭐ Lenta (3-4x) |
| **Costo** | ⭐⭐⭐ $0.35/puesto | ⭐⭐⭐⭐⭐ $0 |
| **Privacidad** | ⭐⭐ Datos en cloud | ⭐⭐⭐⭐⭐ 100% local |
| **Setup** | ⭐⭐⭐⭐⭐ Fácil | ⭐⭐⭐ Medio |
| **Mantenimiento** | ⭐⭐⭐⭐⭐ Ninguno | ⭐⭐⭐ Moderado |
| **Escalabilidad** | ⭐⭐⭐⭐⭐ Ilimitada | ⭐⭐ Limitada por HW |

**Recomendación:**
- **API:** Si necesitas máxima precisión y velocidad, presupuesto bajo ($35/mes para 100 puestos)
- **Local:** Si necesitas privacidad total, costo $0, y puedes aceptar -13% precisión + 3x lentitud

---

## 🎯 Casos de Uso Ideales para Docker Local

### ✅ Recomendado

- Pruebas de concepto (POC)
- Volúmenes bajos (<100 puestos/mes)
- Datos altamente sensibles (gobierno/militar)
- Sin presupuesto para APIs
- Desarrollo y experimentación
- Ambientes sin internet

### ❌ No Recomendado

- Producción con altos volúmenes (>500 puestos/mes)
- Necesidad de máxima precisión (>85%)
- Tiempo de respuesta crítico (<1 min/puesto)
- Hardware limitado (<6GB VRAM)
- Equipo sin conocimientos Docker/Linux

---

## 🔄 Actualización del Sistema

### Actualizar Código de la App

```bash
# Pull últimos cambios
git pull origin main

# Reconstruir solo la app
docker compose build app

# Reiniciar app (Ollama sigue corriendo)
docker compose up -d app
```

### Actualizar Modelo de Ollama

```bash
# Descargar nueva versión
docker compose exec ollama ollama pull phi3.5:latest

# Listar modelos
docker compose exec ollama ollama list

# Eliminar modelo antiguo (opcional)
docker compose exec ollama ollama rm phi3.5:old_version
```

### Actualizar Ollama

```bash
# Pull nueva imagen
docker pull ollama/ollama:latest

# Recrear contenedor
docker compose up -d --force-recreate ollama
```

---

## 🗑️ Desinstalación

### Eliminar Contenedores y Volúmenes

```bash
# Detener y eliminar todo
docker compose down -v

# Eliminar imágenes
docker rmi ollama/ollama:latest
docker rmi herramienta-homologacion-v5-app

# Limpiar sistema completo
docker system prune -a --volumes
```

### Eliminar Configuración

```bash
# Eliminar archivos de configuración
rm -rf ~/.ollama
rm -f .env

# Eliminar repositorio
cd ..
rm -rf herramienta-homologacion-v5
```

---

## 📚 Recursos Adicionales

- **Documentación Ollama:** https://ollama.ai/docs
- **Modelos disponibles:** https://ollama.ai/library
- **Phi-3.5 Mini:** https://ollama.ai/library/phi3.5
- **Docker Compose:** https://docs.docker.com/compose/
- **NVIDIA Docker:** https://github.com/NVIDIA/nvidia-docker

---

## 🆘 Soporte

**Problemas técnicos:**
- GitHub Issues: https://github.com/Alfred3005/herramienta-homologacion-v5/issues

**Documentación del proyecto:**
- Análisis de viabilidad: [ANALISIS_DOCKERIZACION_LLM_LOCAL.md](./ANALISIS_DOCKERIZACION_LLM_LOCAL.md)
- Reporte ejecutivo: [REPORTE_EJECUTIVO_VERSION_5.md](./REPORTE_EJECUTIVO_VERSION_5.md)

---

**Versión:** 1.0
**Fecha:** Noviembre 2025
**Mantenido por:** Sistema de Homologación APF v5
