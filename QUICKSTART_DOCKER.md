# ⚡ Guía Rápida - Docker con LLM Local

Puesta en marcha en **5 minutos** del Sistema de Homologación APF v5 con Phi-3.5 Mini local.

---

## 📋 Pre-requisitos (Verificación Rápida)

```bash
# ¿Tienes Docker?
docker --version
# Esperado: Docker version 20.10+

# ¿Tienes GPU NVIDIA?
nvidia-smi
# Esperado: Ver información de tu GPU

# ¿Tienes NVIDIA Docker?
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi
# Esperado: Ver nvidia-smi dentro del contenedor
```

❌ **Si alguno falla:** Ver [README_DOCKER.md](./README_DOCKER.md#-instalación) para instalación completa.

---

## 🚀 Instalación (3 comandos)

```bash
# 1. Clonar repositorio
git clone https://github.com/Alfred3005/herramienta-homologacion-v5.git
cd herramienta-homologacion-v5

# 2. Configurar variables de entorno
cp .env.docker .env

# 3. Iniciar sistema (descarga automática de Phi-3.5)
docker compose up -d
```

⏳ **Primera vez:** Descarga de modelo toma 5-15 minutos (~2.3GB).

---

## 🎯 Verificación

```bash
# Ver progreso de descarga
docker compose logs -f ollama-init

# Verificar que todo esté corriendo
docker compose ps

# Deberías ver:
# ✅ apf-ollama       (Up, healthy)
# ✅ apf-homologacion (Up, healthy)
```

---

## 🌐 Acceder a la Aplicación

**URL:** http://localhost:8501

**¿No carga?** Espera 1-2 minutos más y refresca el navegador.

---

## 📊 Monitorear VRAM

```bash
# Ver uso de VRAM una vez
./docker/monitor-vram.sh

# Monitoreo continuo (Ctrl+C para salir)
./docker/monitor-vram.sh --continuous
```

**Esperado:**
- VRAM usada: ~4.5-5GB de 6GB
- Temperatura: <80°C
- Utilización: 0% (en espera), 80-100% (durante análisis)

---

## 🧪 Primer Análisis

1. **Abrir:** http://localhost:8501
2. **Clic en:** "Nuevo Análisis"
3. **Subir:**
   - Excel con puestos (formato SIDEGOR)
   - PDF del reglamento
4. **Configurar filtros** (opcional)
5. **Ejecutar análisis**
6. **Esperar:** ~3 minutos por puesto (26 llamadas LLM)

---

## 📝 Comandos Útiles

```bash
# Ver logs en tiempo real
docker compose logs -f

# Reiniciar sistema
docker compose restart

# Detener sistema
docker compose down

# Ver uso de recursos
docker stats

# Diagnosticar problemas
./docker/diagnose.sh
```

---

## ❓ Problemas Comunes

### Error: "CUDA out of memory"

```bash
# Solución rápida: Usar modelo cuantizado
echo "LLM_MODEL=phi3.5:q4_0" >> .env
docker compose restart
```

### Error: "Could not connect to Ollama"

```bash
# Verificar que Ollama esté corriendo
docker compose ps ollama

# Si no está, reiniciar
docker compose restart ollama
```

### Error: "Model not found"

```bash
# Descargar manualmente
docker compose exec ollama ollama pull phi3.5

# Verificar
docker compose exec ollama ollama list
```

---

## 🔧 Más Ayuda

- **Documentación completa:** [README_DOCKER.md](./README_DOCKER.md)
- **Troubleshooting:** [docker/TROUBLESHOOTING.md](./docker/TROUBLESHOOTING.md)
- **Análisis de viabilidad:** [ANALISIS_DOCKERIZACION_LLM_LOCAL.md](./ANALISIS_DOCKERIZACION_LLM_LOCAL.md)

---

## 🎓 Comandos de Limpieza (al terminar)

```bash
# Detener y eliminar contenedores (mantiene modelos descargados)
docker compose down

# Eliminar TODO (incluye modelos, requiere re-descarga)
docker compose down -v
```

---

## 📈 Comparativa Rápida

| Aspecto | Local (Phi-3.5) | API (GPT-4o-mini) |
|---------|-----------------|-------------------|
| **Costo** | $0 | $0.35/puesto |
| **Velocidad** | ~3 min/puesto | ~1 min/puesto |
| **Precisión** | 73% | 86% |
| **Privacidad** | 100% local | Datos en cloud |
| **Setup** | 15 min primera vez | 2 min |

**¿Cuándo usar local?**
- ✅ Datos sensibles (gobierno)
- ✅ Sin presupuesto para APIs
- ✅ <100 puestos/mes
- ✅ Privacidad es crítica

**¿Cuándo usar API?**
- ✅ Necesitas máxima precisión
- ✅ Urgencia (velocidad crítica)
- ✅ >500 puestos/mes
- ✅ Sin hardware adecuado

---

## ⭐ Próximos Pasos

1. **Analiza 5-10 puestos de prueba**
2. **Compara resultados con tus expectativas**
3. **Ajusta modelo si es necesario** (ver opciones en README)
4. **Revisa documentación completa** si vas a usar en producción

---

**¿Listo? ¡Empieza ahora!**

```bash
docker compose up -d && docker compose logs -f
```

Luego abre: **http://localhost:8501** 🚀
