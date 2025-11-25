# 🚀 DEPLOY COMPLETO - Sistema de Homologación APF v5 Docker

**Instrucciones desde CERO para deployment 100% funcional**

Última actualización: Noviembre 2025
Estado: ✅ VERIFICADO - Deploy limpio sin errores

---

## ✅ Pre-requisitos Verificados

### Hardware Mínimo
- **RAM:** 16GB
- **VRAM:** 6GB (GPU NVIDIA)
- **Disco:** 10GB libres

### Software Requerido

#### Windows (Docker Desktop)
```powershell
# Verificar Docker Desktop instalado y corriendo
docker --version
# Esperado: Docker version 20.10+ o superior

# Verificar Docker Compose
docker compose version
# Esperado: Docker Compose version v2.x+

# Verificar WSL2 activo
wsl --list -v
# Esperado: VERSION 2

# Verificar GPU NVIDIA en WSL
wsl nvidia-smi
# Esperado: Información de tu GPU
```

#### Linux
```bash
# Verificar Docker
docker --version

# Verificar Docker Compose
docker compose version

# Verificar GPU NVIDIA
nvidia-smi

# Verificar NVIDIA Docker
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi
```

---

## 📦 PASO 1: Clonar Repositorio Limpio

### Opción A: Windows (PowerShell)

```powershell
# 1. Ir a tu carpeta de proyectos
cd C:\Users\TuUsuario\Documents

# 2. Clonar repositorio
git clone https://github.com/Alfred3005/herramienta-homologacion-docker2.git

# 3. Entrar al directorio
cd herramienta-homologacion-docker2

# 4. Verificar archivos
ls
```

### Opción B: Linux / WSL

```bash
# 1. Ir a tu carpeta de proyectos
cd ~

# 2. Clonar repositorio
git clone https://github.com/Alfred3005/herramienta-homologacion-docker2.git

# 3. Entrar al directorio
cd herramienta-homologacion-docker2

# 4. Verificar archivos
ls -la
```

**Deberías ver:**
```
.dockerignore
.env.docker
.env.example
.gitignore
docker-compose.yml
Dockerfile
README.md
QUICKSTART_DOCKER.md
docker/
src/
streamlit_app/
config/
```

---

## ⚙️ PASO 2: Configurar Variables de Entorno

```bash
# Copiar archivo de configuración
cp .env.docker .env

# Ver contenido (opcional)
cat .env
```

**Contenido del .env:**
```env
# Configuración Ollama Local
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=phi3.5
LLM_PROVIDER=ollama

# Streamlit
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
```

**NO necesitas configurar OPENAI_API_KEY** - El sistema usa Ollama local automáticamente.

---

## 🐳 PASO 3: Iniciar Sistema Completo

### Comando Principal

```bash
docker compose up -d
```

### ¿Qué va a pasar?

**Primera vez (5-15 minutos):**

1. **Construcción de imagen de la app** (~2-3 min)
   ```
   [+] Building 663.7s
   => [app builder 7/7] RUN pip install -r requirements.txt
   => [app] exporting to image
   ```

2. **Descarga de imagen Ollama** (~1 min)
   ```
   [+] Running 6/6
   ✔ ollama Pulled
   ✔ ollama-init Pulled
   ```

3. **Inicio de Ollama** (~30 segundos)
   ```
   ✔ Container apf-ollama Started
   apf-ollama | time=... level=INFO msg="Listening on [::]:11434"
   ```

4. **Descarga del modelo Phi-3.5** (~5-10 min)
   ```
   apf-ollama-init | pulling b5374915da53: 100% ▕████████▏ 2.2 GB
   apf-ollama-init | ✅ Modelo funcionando correctamente!
   ```

5. **Inicio de la aplicación** (~10 segundos)
   ```
   ✔ Container apf-homologacion Started
   apf-homologacion | You can now view your Streamlit app in your browser.
   ```

---

## 🔍 PASO 4: Verificar Estado

### Ver Logs en Tiempo Real

```bash
# Logs de todo el sistema
docker compose logs -f

# Solo logs de descarga del modelo
docker compose logs -f ollama-init

# Solo logs de la aplicación
docker compose logs -f app
```

**Presiona Ctrl+C para salir** (los contenedores siguen corriendo)

### Verificar Contenedores

```bash
docker compose ps
```

**Estado esperado (después de 5-15 min):**
```
NAME               STATUS
apf-ollama         Up 10 minutes (healthy)
apf-homologacion   Up 10 minutes (healthy)
apf-ollama-init    Exited (0)
```

✅ **"Exited (0)" en apf-ollama-init es NORMAL** - Solo se ejecuta una vez para descargar el modelo.

### Verificar Modelo Descargado

```bash
curl http://localhost:11434/api/tags
```

**Respuesta esperada:**
```json
{
  "models": [
    {
      "name": "phi3.5:latest",
      "size": 2176178843,
      ...
    }
  ]
}
```

---

## 🌐 PASO 5: Acceder a la Aplicación

**URL:** http://localhost:8501

**Si no carga:**
1. Espera 1-2 minutos más
2. Refresca el navegador (F5)
3. Verifica logs: `docker compose logs app`

**Deberías ver:**
```
🏛️ Sistema de Homologación APF v5
Edición Docker Local - Phi-3.5 Mini
```

---

## 🧪 PASO 6: Prueba Funcional

### Preparar Archivos de Prueba

1. **Archivo Excel (Sidegor):** Base de datos de puestos
2. **Archivo TXT (Normativa):** Reglamento Interior en texto plano

### Ejecutar Análisis

1. **Ir a:** http://localhost:8501
2. **Click:** "Nuevo Análisis" (sidebar)
3. **Paso 1 - Archivos:**
   - Seleccionar "Base de Datos Excel (Sidegor)"
   - Subir archivo Excel
   - Subir archivo de normativa (TXT)
   - Click "Siguiente"

4. **Paso 2 - Filtros:**
   - Seleccionar nivel (ej: "G")
   - Configurar filtros opcionales
   - Click "Siguiente"

5. **Paso 3 - Opciones:**
   - Activar "Validación contextual" ✅
   - Activar "Análisis verbos débiles" ✅
   - Click "Siguiente"

6. **Paso 4 - Ejecutar:**
   - Revisar resumen
   - Click "🚀 Ejecutar Análisis"

### Verificar LLM Local

**Deberías ver este mensaje:**
```
🔄 Iniciando análisis con sistema de validación v5.42 (Estable) - LLM: Ollama (Phi-3.5 Local)...
⚙️ Inicializando sistema de validación...
🤖 Usando LLM local: Ollama (phi3.5) en http://ollama:11434
```

❌ **NO deberías ver:** "OPENAI_API_KEY no configurada"

### Tiempo Estimado

- **Por puesto:** ~3-4 minutos (con Phi-3.5 local)
- **10 puestos:** ~30-40 minutos
- **100 puestos:** ~5-7 horas

---

## 📊 PASO 7: Monitorear Recursos

### VRAM (GPU)

**Windows:**
```powershell
# Desde PowerShell
wsl nvidia-smi

# O desde WSL
wsl
nvidia-smi
```

**Linux:**
```bash
# Una vez
nvidia-smi

# Continuo (actualiza cada 2 segundos)
watch -n 2 nvidia-smi
```

**Uso esperado:**
- **En espera:** ~4.5GB VRAM
- **Durante análisis:** ~5-5.5GB VRAM
- **Temperatura:** <80°C
- **Utilización:** 80-100% durante inferencia

### CPU y RAM (Docker)

```bash
docker stats
```

**Uso esperado:**
- **CPU:** 20-40% en espera, 80-100% durante análisis
- **RAM (app):** ~2-4GB
- **RAM (ollama):** ~6-8GB

---

## 🛠️ Comandos Útiles

### Gestión de Contenedores

```bash
# Reiniciar todo
docker compose restart

# Detener todo
docker compose down

# Detener y eliminar TODO (incluye volúmenes con modelo)
docker compose down -v

# Ver logs de un servicio específico
docker compose logs -f ollama
docker compose logs -f app

# Ejecutar comando dentro del contenedor
docker compose exec app bash
docker compose exec ollama bash
```

### Re-descargar Modelo (si hay problemas)

```bash
# Entrar al contenedor de Ollama
docker compose exec ollama bash

# Dentro del contenedor, descargar modelo
ollama pull phi3.5

# Verificar
ollama list

# Salir
exit
```

### Limpiar Docker Completamente

```bash
# CUIDADO: Borra TODOS los contenedores, imágenes y volúmenes
docker system prune -a --volumes
```

---

## 🚨 Troubleshooting

### Problema 1: "Error: no GPU detected"

**Síntoma:**
```
Error: GPU not available
```

**Solución Windows:**
```powershell
# Verificar GPU en WSL
wsl nvidia-smi

# Si no funciona, instalar drivers NVIDIA más recientes
# Descargar de: https://www.nvidia.com/Download/index.aspx
```

**Solución Linux:**
```bash
# Instalar NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### Problema 2: Puerto 8501 ocupado

**Síntoma:**
```
Error: port is already allocated
```

**Solución:**
```bash
# Ver qué está usando el puerto
sudo lsof -i :8501

# Cambiar puerto en docker-compose.yml
# Cambiar "8501:8501" a "8502:8501"
# Luego reiniciar
docker compose down
docker compose up -d
```

### Problema 3: Modelo no descarga

**Síntoma:**
```
apf-ollama-init | Error pulling model
```

**Solución:**
```bash
# Ver logs completos
docker compose logs ollama-init

# Descargar manualmente
docker compose exec ollama ollama pull phi3.5
```

### Problema 4: App muestra "OPENAI_API_KEY no configurada"

**Síntoma:**
```
❌ OPENAI_API_KEY no configurada en .env
```

**Causa:** El código no está actualizado

**Solución:**
```bash
# Actualizar código
git pull origin main

# Reconstruir imagen
docker compose down
docker compose build --no-cache app
docker compose up -d
```

---

## ✅ Checklist de Verificación Final

Antes de reportar problemas, verifica:

- [ ] Docker Desktop corriendo (Windows) o Docker daemon activo (Linux)
- [ ] GPU NVIDIA visible con `nvidia-smi`
- [ ] Repositorio clonado correctamente
- [ ] Archivo `.env` creado (`cp .env.docker .env`)
- [ ] `docker compose up -d` ejecutado sin errores
- [ ] 3 contenedores creados (`docker compose ps`)
- [ ] Modelo phi3.5 descargado (`curl http://localhost:11434/api/tags`)
- [ ] http://localhost:8501 accesible
- [ ] Mensaje muestra "Ollama (Phi-3.5 Local)" al analizar

---

## 📞 Soporte

**Problemas comunes:** Ver sección Troubleshooting arriba

**Issues GitHub:** https://github.com/Alfred3005/herramienta-homologacion-docker2/issues

**Versión API (producción):** https://github.com/Alfred3005/herramienta-homologacion-v5

---

## 🎯 Próximos Pasos Después del Deploy

1. ✅ Deploy exitoso
2. ✅ Prueba con 1-2 puestos
3. 📊 Evaluar precisión vs versión API
4. ⚖️ Decidir: ¿Usar local para POC o API para producción?
5. 📈 Escalar según necesidades

---

**Versión:** 1.0.1
**Última actualización:** Noviembre 2025
**Estado:** ✅ Verificado y funcional
**Commits incluidos:** Initial + FIX Ollama + DOC URLs
