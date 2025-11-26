# 🐳 Sistema de Homologación APF v5 - Edición Docker Local

Sistema de validación de puestos de la Administración Pública Federal con **LLM 100% local** (Phi-3.5 Mini) vía Ollama.

**Costo operativo: $0 MXN** | **Privacidad: 100%** | **Optimizado para 6GB VRAM**

---

## 🎯 ¿Qué es esto?

Esta es la **versión dockerizada** del Sistema de Homologación APF v5 que utiliza **modelos de IA locales** en lugar de APIs en la nube. Ideal para:

- ✅ **Privacidad total** - Datos nunca salen del servidor
- ✅ **Costo $0** - Sin gastos de APIs
- ✅ **Sin internet** - Funciona offline una vez instalado
- ✅ **POCs y experimentación** - Perfecto para pruebas de concepto

---

## ⚡ Inicio Rápido (5 minutos)

> 📘 **¿Primera vez?** Lee [DEPLOY_COMPLETO.md](./DEPLOY_COMPLETO.md) para instrucciones detalladas paso a paso

### Pre-requisitos

- 🖥️ **Hardware:** 16GB RAM, 6GB VRAM (GPU NVIDIA)
- 🐳 **Software:** Docker + Docker Compose + NVIDIA Docker
- 🐧 **OS:** Linux (Ubuntu recomendado) o Windows (Docker Desktop + WSL2)

### Instalación

```bash
# 1. Clonar repositorio
git clone https://github.com/Alfred3005/herramienta-homologacion-docker2.git
cd herramienta-homologacion-docker2

# 2. Configurar
cp .env.docker .env

# 3. Iniciar (descarga automática de Qwen2.5 3B ~1.9GB)
docker compose up -d

# 4. Acceder
# http://localhost:8501
```

**Primera vez:** La descarga del modelo toma 5-10 minutos (Qwen2.5 3B - optimizado para 6GB VRAM).

---

## 📚 Documentación

- **🚀 [Guía Rápida](QUICKSTART_DOCKER.md)** - Empieza aquí (5 minutos)
- **📖 [Guía Completa](README_DOCKER.md)** - Documentación detallada
- **🔧 [Troubleshooting](docker/TROUBLESHOOTING.md)** - Soluciones a problemas comunes
- **📊 [Análisis Técnico](ANALISIS_DOCKERIZACION_LLM_LOCAL.md)** - Viabilidad y comparativas

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────┐
│         Docker Host (Linux/WSL2)        │
│                                         │
│  ┌──────────────┐  ┌────────────────┐  │
│  │  Streamlit   │  │  Ollama        │  │
│  │  (Web App)   │◄─┤  (Qwen2.5 3B) │  │
│  │  :8501       │  │  :11434        │  │
│  └──────────────┘  └────────────────┘  │
│         CPU              GPU (6GB)      │
└─────────────────────────────────────────┘
```

**3 contenedores:**
1. `apf-ollama` - Servidor LLM con GPU (Ollama)
2. `apf-homologacion` - Aplicación web Streamlit
3. `apf-ollama-init` - Inicializador automático (descarga modelo en primer arranque)

---

## 📊 Comparativa vs Versión API

| Aspecto | API (GPT-4o-mini) | Docker Local (Qwen2.5 3B) |
|---------|-------------------|---------------------------|
| **Costo/puesto** | $0.35 MXN | **$0.00 MXN** |
| **Privacidad** | Datos en cloud | **100% local** |
| **Precisión** | 86% | 75-80% (-6 a -11%) |
| **Velocidad** | ~60s/puesto | ~120-150s/puesto (2-2.5x) |
| **Internet** | Requerido | **Opcional** |
| **VRAM** | N/A | **~3.5GB** |

**Nota:** Sistema optimizado para **6GB VRAM**. Otros modelos disponibles:
- `qwen2.5:7b` (>8GB VRAM, ~80-85% precisión)
- `phi3.5` (~4.5GB VRAM, ~70-75% precisión)
- `llama3.2:3b` (~3.5GB VRAM, ~73-78% precisión)

### 💰 Ahorro Estimado

- **100 puestos/mes:** $420 MXN/año
- **1,000 puestos/año:** $4,200 MXN/año

---

## 🎓 Casos de Uso Ideales

### ✅ Recomendado para:

- Pruebas de concepto (POC)
- Volúmenes bajos (<100 puestos/mes)
- Datos altamente sensibles (gobierno/militar)
- Sin presupuesto para APIs
- Desarrollo y experimentación
- Ambientes sin internet

### ❌ No recomendado para:

- Producción con altos volúmenes (>500 puestos/mes)
- Necesidad de máxima precisión (>85%)
- Tiempo de respuesta crítico (<1 min/puesto)
- Hardware limitado (<6GB VRAM)

---

## 🛠️ Comandos Útiles

```bash
# Iniciar sistema
docker compose up -d

# Ver logs
docker compose logs -f

# Monitorear VRAM
./docker/monitor-vram.sh

# Diagnosticar problemas
./docker/diagnose.sh

# Detener sistema
docker compose down

# Limpiar todo (incluye modelos descargados)
docker compose down -v
```

---

## 🔧 Optimizaciones Implementadas

- ✅ **Qwen2.5 3B** (3B parámetros) con cuantización Q4 - Optimizado para 6GB VRAM
- ✅ Alternativas disponibles: Phi-3.5, Llama 3.2 3B, Qwen2.5 7B (>8GB)
- ✅ **VRAM optimizada**: ~3.5GB usado de 6GB disponibles (margen seguro)
- ✅ Un solo modelo en memoria (OLLAMA_MAX_LOADED_MODELS=1)
- ✅ Sin procesamiento paralelo (OLLAMA_NUM_PARALLEL=1)
- ✅ Flash Attention activado (reduce VRAM adicional)
- ✅ Timeout extendido para LLM local (120s)
- ✅ Parsing JSON robusto con reparación automática
- ✅ Arquitectura de microservicios (fácil escalar)
- ✅ Inicialización automática con descarga de modelo
- ✅ **Balance ideal**: Precisión ~75-80% con solo 3.5GB VRAM

---

## 🆘 Soporte

**Problemas comunes:**
- Ver [docker/TROUBLESHOOTING.md](docker/TROUBLESHOOTING.md)

**Issues de GitHub:**
- https://github.com/Alfred3005/herramienta-homologacion-docker/issues

**Versión API (producción):**
- https://github.com/Alfred3005/herramienta-homologacion-v5

---

## 📄 Licencia

MIT License

---

## 🔗 Proyectos Relacionados

- **[Versión API (v5)](https://github.com/Alfred3005/herramienta-homologacion-v5)** - Versión oficial con GPT-4o-mini (máxima precisión)
- **[Versión v4 (legacy)](https://github.com/Alfred3005/HerramientaHomologacionDocker)** - Versión anterior

---

## 🚀 Próximos Pasos

1. Lee [QUICKSTART_DOCKER.md](QUICKSTART_DOCKER.md)
2. Ejecuta `docker compose up -d`
3. Accede a http://localhost:8501
4. Analiza 5-10 puestos de prueba
5. Compara resultados
6. ¡Contribuye con mejoras!

---

**Versión:** 1.0.0
**Fecha:** Noviembre 2025
**Mantenido por:** Sistema de Homologación APF
**Base:** Sistema v5.42 + Ollama + Phi-3.5 Mini
