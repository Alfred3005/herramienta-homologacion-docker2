# 🔧 Guía Avanzada de Troubleshooting - Docker + Ollama

Soluciones detalladas para problemas comunes al ejecutar el Sistema de Homologación APF v5 con LLM local.

---

## 📑 Índice

1. [Problemas de Instalación](#1-problemas-de-instalación)
2. [Problemas de VRAM](#2-problemas-de-vram)
3. [Problemas de Red/Conectividad](#3-problemas-de-redconectividad)
4. [Problemas de Rendimiento](#4-problemas-de-rendimiento)
5. [Problemas de Modelos](#5-problemas-de-modelos)
6. [Problemas de Datos](#6-problemas-de-datos)
7. [Diagnóstico Avanzado](#7-diagnóstico-avanzado)

---

## 1. Problemas de Instalación

### Error: `nvidia-smi` no encontrado

**Síntoma:**
```
bash: nvidia-smi: command not found
```

**Causa:** Drivers NVIDIA no instalados o PATH incorrecto

**Solución:**

```bash
# Verificar si la GPU es detectada
lspci | grep -i nvidia

# Instalar drivers NVIDIA (Ubuntu)
sudo ubuntu-drivers autoinstall

# O instalar manualmente
sudo apt install nvidia-driver-525

# Reiniciar sistema
sudo reboot

# Verificar después de reinicio
nvidia-smi
```

### Error: NVIDIA Docker runtime no configurado

**Síntoma:**
```
Error response from daemon: could not select device driver "" with capabilities: [[gpu]]
```

**Solución:**

```bash
# Verificar si nvidia-docker2 está instalado
dpkg -l | grep nvidia-docker

# Si no está, instalar
sudo apt-get update
sudo apt-get install -y nvidia-docker2

# Reiniciar Docker
sudo systemctl restart docker

# Probar
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi
```

### Error: Permiso denegado al ejecutar docker

**Síntoma:**
```
permission denied while trying to connect to the Docker daemon socket
```

**Solución:**

```bash
# Agregar usuario al grupo docker
sudo usermod -aG docker $USER

# Aplicar cambios sin reiniciar
newgrp docker

# Verificar
docker ps
```

---

## 2. Problemas de VRAM

### Error: CUDA Out of Memory

**Síntoma:**
```
RuntimeError: CUDA out of memory. Tried to allocate X.XX GiB
```

**Diagnóstico:**

```bash
# Ver uso actual de VRAM
nvidia-smi

# Ver procesos usando GPU
nvidia-smi pmon

# Monitorear en tiempo real
watch -n 1 nvidia-smi
```

**Soluciones (en orden de preferencia):**

#### Solución 1: Usar modelo cuantizado

```bash
# Editar docker-compose.yml o .env
# Cambiar LLM_MODEL de "phi3.5" a "phi3.5:q4_0"
LLM_MODEL=phi3.5:q4_0

# Reiniciar
docker compose down
docker compose up -d
```

**Comparativa de cuantización:**

| Modelo | VRAM | Calidad | Velocidad |
|--------|------|---------|-----------|
| phi3.5 (FP16) | ~5.5 GB | 100% | Lenta |
| phi3.5:q4_0 | ~2.5 GB | 95% | Rápida |
| phi3.5:q3_K_M | ~2.0 GB | 90% | Muy rápida |
| phi3.5:q2_K | ~1.5 GB | 80% | Ultra rápida |

#### Solución 2: Liberar VRAM

```bash
# Detener contenedores
docker compose down

# Limpiar procesos zombie de GPU
sudo fuser -v /dev/nvidia*
sudo kill -9 <PID>

# Reiniciar
docker compose up -d
```

#### Solución 3: Limitar VRAM de Ollama

Editar `docker-compose.yml`:

```yaml
ollama:
  environment:
    - OLLAMA_GPU_OVERHEAD=500M  # Reservar 500MB para overhead
    - OLLAMA_MAX_VRAM=5G        # Limitar a 5GB
```

#### Solución 4: Usar modelo más pequeño

```bash
# Cambiar a Llama 3.2 1B (solo 2GB VRAM)
LLM_MODEL=llama3.2:1b

# O Qwen 2.5 1.5B
LLM_MODEL=qwen2.5:1.5b
```

### Error: GPU memory fragmentation

**Síntoma:**
```
CUDA out of memory despite showing free VRAM
```

**Solución:**

```bash
# Reiniciar Ollama para defragmentar
docker compose restart ollama

# Esperar 30 segundos
sleep 30

# Verificar
nvidia-smi
```

---

## 3. Problemas de Red/Conectividad

### Error: App no puede conectar a Ollama

**Síntoma:**
```
LLMProviderError: Could not connect to http://ollama:11434
Connection refused
```

**Diagnóstico:**

```bash
# Verificar que Ollama esté corriendo
docker compose ps ollama

# Verificar health check
docker inspect apf-ollama | grep Health -A 10

# Probar conexión desde host
curl http://localhost:11434/api/tags

# Probar conexión desde contenedor de app
docker compose exec app curl http://ollama:11434/api/tags
```

**Soluciones:**

#### Solución 1: Verificar red Docker

```bash
# Listar redes
docker network ls

# Inspeccionar red APF
docker network inspect herramienta-homologacion-v5_apf-network

# Verificar que ambos contenedores estén en la misma red
docker inspect apf-ollama | grep NetworkMode
docker inspect apf-homologacion | grep NetworkMode
```

#### Solución 2: Recrear contenedores

```bash
# Bajar servicios
docker compose down

# Eliminar red
docker network rm herramienta-homologacion-v5_apf-network

# Recrear
docker compose up -d
```

#### Solución 3: Usar IP directa (workaround)

```bash
# Obtener IP de Ollama
OLLAMA_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' apf-ollama)

# Editar .env
OLLAMA_BASE_URL=http://$OLLAMA_IP:11434

# Reiniciar app
docker compose restart app
```

### Error: Puerto 8501 o 11434 ya en uso

**Síntoma:**
```
Error: Bind for 0.0.0.0:8501 failed: port is already allocated
```

**Solución:**

```bash
# Encontrar proceso usando el puerto
sudo lsof -i :8501
sudo lsof -i :11434

# Matar proceso
sudo kill -9 <PID>

# O cambiar puerto en docker-compose.yml
ports:
  - "8502:8501"  # Usar 8502 en host
```

---

## 4. Problemas de Rendimiento

### Problema: Respuestas muy lentas (>5 min por puesto)

**Diagnóstico:**

```bash
# Ver uso de GPU
nvidia-smi

# Ver logs de Ollama
docker compose logs ollama | tail -50

# Verificar temperature throttling
nvidia-smi -q -d TEMPERATURE
```

**Soluciones:**

#### Solución 1: Verificar que GPU se esté usando

```bash
# Ver uso de GPU mientras se ejecuta análisis
watch -n 1 nvidia-smi

# Si utilización es 0%, verificar:
docker compose exec ollama ollama ps
```

#### Solución 2: Reducir tokens generados

Editar `.env`:

```bash
MAX_TOKENS=800  # Reducir de 1500 a 800
LLM_TIMEOUT=180  # Aumentar timeout
```

#### Solución 3: Usar modelo más rápido

```bash
# Qwen es más rápido que Phi para texto simple
LLM_MODEL=qwen2.5:3b
```

#### Solución 4: Pre-calentar GPU

```bash
# Ejecutar análisis dummy al inicio
docker compose exec ollama ollama run phi3.5 "test" --verbose
```

### Problema: Alto uso de CPU

**Diagnóstico:**

```bash
# Ver uso de recursos
docker stats

# Ver procesos dentro del contenedor
docker compose exec app top
```

**Solución:**

```bash
# Limitar CPUs del contenedor de app
# Editar docker-compose.yml
app:
  deploy:
    resources:
      limits:
        cpus: '2'  # Limitar a 2 CPUs
```

---

## 5. Problemas de Modelos

### Error: Model not found

**Síntoma:**
```
Error: model 'phi3.5' not found
```

**Solución:**

```bash
# Verificar modelos disponibles
docker compose exec ollama ollama list

# Descargar manualmente
docker compose exec ollama ollama pull phi3.5

# Verificar descarga
docker compose exec ollama ollama list | grep phi3.5

# Si falla, ver logs
docker compose logs ollama-init
```

### Error: Model download interrupted

**Síntoma:**
```
Error: download interrupted at 45%
```

**Solución:**

```bash
# Reanudar descarga
docker compose exec ollama ollama pull phi3.5

# Si persiste, eliminar descarga parcial
docker compose exec ollama ollama rm phi3.5
docker compose exec ollama ollama pull phi3.5
```

### Problema: Quiero cambiar de modelo

**Proceso:**

```bash
# 1. Descargar nuevo modelo
docker compose exec ollama ollama pull llama3.2:3b

# 2. Verificar que está disponible
docker compose exec ollama ollama list

# 3. Actualizar .env
echo "LLM_MODEL=llama3.2:3b" >> .env

# 4. Reiniciar app
docker compose restart app

# 5. (Opcional) Eliminar modelo anterior para liberar espacio
docker compose exec ollama ollama rm phi3.5
```

### Problema: Modelo corrupto

**Síntoma:**
```
Error: invalid model format
Error: checksum mismatch
```

**Solución:**

```bash
# Eliminar modelo corrupto
docker compose exec ollama ollama rm phi3.5

# Limpiar caché
docker compose down -v
docker volume rm herramienta-homologacion-v5_ollama_models

# Volver a crear e inicializar
docker compose up -d
```

---

## 6. Problemas de Datos

### Error: Upload failed

**Síntoma:**
```
Error uploading file: File too large
```

**Solución:**

Editar `.env`:

```bash
MAX_UPLOAD_SIZE=500  # Aumentar límite a 500MB
```

Reiniciar:

```bash
docker compose restart app
```

### Error: Invalid Excel format

**Diagnóstico:**

```bash
# Ver logs de la app
docker compose logs app | grep -i error

# Acceder al contenedor
docker compose exec app bash

# Verificar archivo subido
ls -lh /app/uploads/
```

**Solución:**

- Verificar que el Excel esté en formato SIDEGOR correcto
- Probar con archivo de ejemplo
- Ver documentación de formato esperado

### Problema: Caché corrupto

**Síntoma:**
```
Error loading cached results
```

**Solución:**

```bash
# Limpiar caché
docker compose exec app rm -rf /app/cache/*

# O eliminar volumen completo
docker compose down
docker volume rm herramienta-homologacion-v5_app_cache
docker compose up -d
```

---

## 7. Diagnóstico Avanzado

### Script de Diagnóstico Completo

```bash
#!/bin/bash

echo "=== Diagnóstico del Sistema APF v5 ==="
echo ""

echo "1. Docker:"
docker --version
docker compose version

echo ""
echo "2. GPU:"
nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free,temperature.gpu --format=csv,noheader

echo ""
echo "3. Contenedores:"
docker compose ps

echo ""
echo "4. Uso de recursos:"
docker stats --no-stream

echo ""
echo "5. Modelos disponibles:"
docker compose exec ollama ollama list

echo ""
echo "6. Health checks:"
docker inspect apf-ollama | grep -A 5 Health
docker inspect apf-homologacion | grep -A 5 Health

echo ""
echo "7. Conectividad Ollama:"
curl -s http://localhost:11434/api/tags | jq '.models[] | .name'

echo ""
echo "8. Logs recientes (últimas 20 líneas):"
docker compose logs --tail=20

echo ""
echo "=== Fin del diagnóstico ==="
```

Guardar como `diagnose.sh` y ejecutar:

```bash
chmod +x diagnose.sh
./diagnose.sh > diagnostico_$(date +%Y%m%d_%H%M%S).txt
```

### Habilitar Debug Mode

Editar `.env`:

```bash
DEBUG=true
LOG_LEVEL=DEBUG
OLLAMA_DEBUG=1
```

Reiniciar:

```bash
docker compose down
docker compose up -d

# Ver logs detallados
docker compose logs -f | tee debug.log
```

### Exportar Logs para Reporte

```bash
# Crear reporte completo
mkdir -p ~/apf_debug_$(date +%Y%m%d)
cd ~/apf_debug_$(date +%Y%m%d)

# Exportar información del sistema
nvidia-smi > nvidia_smi.txt
docker compose ps > containers.txt
docker stats --no-stream > stats.txt
docker compose logs > docker_logs.txt

# Comprimir
cd ..
tar -czf apf_debug_$(date +%Y%m%d).tar.gz apf_debug_$(date +%Y%m%d)/

echo "Reporte guardado en: apf_debug_$(date +%Y%m%d).tar.gz"
```

---

## 🆘 Soporte Adicional

Si ninguna de estas soluciones funciona:

1. **Crear reporte de diagnóstico:**
   ```bash
   ./docker/diagnose.sh > mi_diagnostico.txt
   ```

2. **Abrir issue en GitHub:**
   - URL: https://github.com/Alfred3005/herramienta-homologacion-v5/issues
   - Incluir: `mi_diagnostico.txt`
   - Describir: Problema, pasos para reproducir, errores

3. **Revisar documentación:**
   - [README_DOCKER.md](../README_DOCKER.md)
   - [ANALISIS_DOCKERIZACION_LLM_LOCAL.md](../ANALISIS_DOCKERIZACION_LLM_LOCAL.md)

---

**Última actualización:** Noviembre 2025
