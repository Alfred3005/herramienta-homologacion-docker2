#!/bin/bash

# Script de diagnóstico completo para Sistema APF v5 Docker
# Ejecutar: ./docker/diagnose.sh

set -e

echo "==========================================================="
echo "  DIAGNÓSTICO COMPLETO - Sistema APF v5 Docker"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "==========================================================="
echo ""

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para checks
check_ok() {
    echo -e "${GREEN}✓${NC} $1"
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

check_error() {
    echo -e "${RED}✗${NC} $1"
}

echo "1. VERIFICACIÓN DE REQUISITOS"
echo "-----------------------------------------------------------"

# Docker
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    check_ok "Docker instalado: $DOCKER_VERSION"
else
    check_error "Docker NO encontrado"
fi

# Docker Compose
if command -v docker compose &> /dev/null; then
    COMPOSE_VERSION=$(docker compose version)
    check_ok "Docker Compose instalado: $COMPOSE_VERSION"
else
    check_error "Docker Compose NO encontrado"
fi

# NVIDIA SMI
echo ""
if command -v nvidia-smi &> /dev/null; then
    check_ok "nvidia-smi encontrado"
    echo ""
    echo "2. INFORMACIÓN DE GPU"
    echo "-----------------------------------------------------------"
    nvidia-smi --query-gpu=index,name,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu --format=csv,noheader | \
    while IFS=',' read -r index name total used free temp util; do
        echo "  GPU $index: $name"
        echo "    VRAM Total: $total"
        echo "    VRAM Usada: $used"
        echo "    VRAM Libre: $free"
        echo "    Temperatura: $temp"
        echo "    Utilización: $util"
        echo ""
    done
else
    check_error "nvidia-smi NO encontrado"
    echo ""
fi

# NVIDIA Docker
echo "3. VERIFICACIÓN DE NVIDIA DOCKER"
echo "-----------------------------------------------------------"
if docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
    check_ok "NVIDIA Docker funcional"
else
    check_error "NVIDIA Docker NO funcional"
fi
echo ""

# Contenedores
echo "4. ESTADO DE CONTENEDORES"
echo "-----------------------------------------------------------"
if docker compose ps &> /dev/null; then
    docker compose ps
else
    check_warn "No se pudo obtener estado de contenedores (¿docker-compose.yml existe?)"
fi
echo ""

# Uso de recursos
echo "5. USO DE RECURSOS"
echo "-----------------------------------------------------------"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" 2>/dev/null || \
    check_warn "No se pudo obtener estadísticas de contenedores"
echo ""

# Modelos de Ollama
echo "6. MODELOS DE OLLAMA"
echo "-----------------------------------------------------------"
if docker compose ps | grep -q "apf-ollama"; then
    if docker compose exec -T ollama ollama list 2>/dev/null; then
        check_ok "Modelos listados correctamente"
    else
        check_warn "No se pudo listar modelos (¿Ollama corriendo?)"
    fi
else
    check_warn "Contenedor apf-ollama no está corriendo"
fi
echo ""

# Health checks
echo "7. HEALTH CHECKS"
echo "-----------------------------------------------------------"

# Ollama
if docker ps | grep -q "apf-ollama"; then
    OLLAMA_HEALTH=$(docker inspect apf-ollama 2>/dev/null | grep -A 1 '"Status"' | tail -1 | awk -F'"' '{print $4}')
    if [ "$OLLAMA_HEALTH" == "healthy" ]; then
        check_ok "apf-ollama: healthy"
    else
        check_warn "apf-ollama: $OLLAMA_HEALTH"
    fi
else
    check_error "apf-ollama no está corriendo"
fi

# App
if docker ps | grep -q "apf-homologacion"; then
    APP_HEALTH=$(docker inspect apf-homologacion 2>/dev/null | grep -A 1 '"Status"' | tail -1 | awk -F'"' '{print $4}')
    if [ "$APP_HEALTH" == "healthy" ]; then
        check_ok "apf-homologacion: healthy"
    else
        check_warn "apf-homologacion: $APP_HEALTH"
    fi
else
    check_error "apf-homologacion no está corriendo"
fi
echo ""

# Conectividad
echo "8. PRUEBAS DE CONECTIVIDAD"
echo "-----------------------------------------------------------"

# Ollama API desde host
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    check_ok "Ollama API accesible desde host (localhost:11434)"
else
    check_error "Ollama API NO accesible desde host"
fi

# Streamlit desde host
if curl -s http://localhost:8501/_stcore/health > /dev/null 2>&1; then
    check_ok "Streamlit accesible desde host (localhost:8501)"
else
    check_warn "Streamlit NO accesible desde host (¿iniciando?)"
fi

# Ollama desde contenedor de app
if docker compose ps | grep -q "apf-homologacion"; then
    if docker compose exec -T app curl -s http://ollama:11434/api/tags > /dev/null 2>&1; then
        check_ok "App puede conectar con Ollama (red Docker OK)"
    else
        check_error "App NO puede conectar con Ollama (verificar red Docker)"
    fi
fi
echo ""

# Volúmenes
echo "9. VOLÚMENES DOCKER"
echo "-----------------------------------------------------------"
docker volume ls | grep herramienta-homologacion || check_warn "No se encontraron volúmenes del proyecto"
echo ""

# Espacio en disco
echo "10. ESPACIO EN DISCO"
echo "-----------------------------------------------------------"
docker system df
echo ""

# Logs recientes
echo "11. LOGS RECIENTES (últimas 10 líneas)"
echo "-----------------------------------------------------------"
docker compose logs --tail=10 2>/dev/null || check_warn "No se pudieron obtener logs"
echo ""

# Resumen
echo "==========================================================="
echo "  RESUMEN"
echo "==========================================================="
echo ""

# Contar checks
OK_COUNT=$(grep -c "✓" <<< "$(cat /tmp/diagnose_output.tmp 2>/dev/null)" || echo 0)
WARN_COUNT=$(grep -c "⚠" <<< "$(cat /tmp/diagnose_output.tmp 2>/dev/null)" || echo 0)
ERROR_COUNT=$(grep -c "✗" <<< "$(cat /tmp/diagnose_output.tmp 2>/dev/null)" || echo 0)

echo "Estado general:"
if docker compose ps | grep -q "Up"; then
    check_ok "Sistema operativo"
else
    check_error "Sistema con problemas"
fi

echo ""
echo "Próximos pasos recomendados:"
echo "  1. Acceder a la aplicación: http://localhost:8501"
echo "  2. Monitorear VRAM: ./docker/monitor-vram.sh"
echo "  3. Ver logs completos: docker compose logs -f"
echo "  4. Si hay problemas: consultar docker/TROUBLESHOOTING.md"
echo ""

echo "==========================================================="
echo "  Diagnóstico completado"
echo "  Guardar este reporte: ./docker/diagnose.sh > diagnostico.txt"
echo "==========================================================="
