#!/bin/bash

# Script de monitoreo de VRAM para Docker + Ollama
# Útil para verificar que no excedamos los 6GB disponibles

set -e

echo "=================================================="
echo "  Monitor de VRAM - Sistema APF v5"
echo "=================================================="
echo ""

# Verificar si nvidia-smi está disponible
if ! command -v nvidia-smi &> /dev/null; then
    echo "❌ Error: nvidia-smi no encontrado"
    echo "   Este script requiere drivers NVIDIA instalados"
    exit 1
fi

# Verificar si el contenedor de Ollama está corriendo
if ! docker ps | grep -q "apf-ollama"; then
    echo "⚠️  Advertencia: Contenedor 'apf-ollama' no está corriendo"
    echo "   Mostrando uso general de GPU..."
    echo ""
fi

# Función para obtener información de VRAM
get_vram_info() {
    # Memoria total
    total=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -n1)

    # Memoria usada
    used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -n1)

    # Memoria libre
    free=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -n1)

    # Porcentaje usado
    percentage=$(awk "BEGIN {printf \"%.1f\", ($used/$total)*100}")

    # Temperatura
    temp=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits | head -n1)

    # Utilización GPU
    utilization=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | head -n1)

    echo "📊 Uso de VRAM:"
    echo "   Total:       ${total} MB ($(awk "BEGIN {printf \"%.2f\", $total/1024}") GB)"
    echo "   Usada:       ${used} MB ($(awk "BEGIN {printf \"%.2f\", $used/1024}") GB)"
    echo "   Libre:       ${free} MB ($(awk "BEGIN {printf \"%.2f\", $free/1024}") GB)"
    echo "   Porcentaje:  ${percentage}%"
    echo ""
    echo "🌡️  Temperatura: ${temp}°C"
    echo "⚙️  Utilización: ${utilization}%"
    echo ""

    # Advertencias
    if (( $(echo "$percentage > 90" | bc -l) )); then
        echo "⚠️  ADVERTENCIA: Uso de VRAM crítico (>90%)"
        echo "   Considera reducir carga o reiniciar Ollama"
    elif (( $(echo "$percentage > 80" | bc -l) )); then
        echo "⚠️  ADVERTENCIA: Uso de VRAM alto (>80%)"
    fi

    if (( temp > 80 )); then
        echo "🔥 ADVERTENCIA: Temperatura alta (>80°C)"
        echo "   Verifica ventilación del sistema"
    fi
}

# Función para listar procesos usando GPU
list_gpu_processes() {
    echo "=================================================="
    echo "  Procesos usando GPU"
    echo "=================================================="
    echo ""

    nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader | while IFS=',' read -r pid name mem; do
        pid=$(echo $pid | xargs)
        name=$(echo $name | xargs)
        mem=$(echo $mem | xargs)

        echo "  PID: $pid"
        echo "  Proceso: $name"
        echo "  Memoria: $mem"
        echo ""
    done
}

# Función de monitoreo continuo
monitor_continuous() {
    echo "🔄 Modo de monitoreo continuo (Ctrl+C para salir)"
    echo ""

    while true; do
        clear
        echo "=================================================="
        echo "  Monitor de VRAM - Sistema APF v5"
        echo "  $(date '+%Y-%m-%d %H:%M:%S')"
        echo "=================================================="
        echo ""

        get_vram_info
        list_gpu_processes

        echo "Actualizando en 5 segundos..."
        sleep 5
    done
}

# Parsear argumentos
if [ "$1" == "--continuous" ] || [ "$1" == "-c" ]; then
    monitor_continuous
else
    get_vram_info
    list_gpu_processes
    echo ""
    echo "💡 Tip: Usa '$0 --continuous' para monitoreo en tiempo real"
    echo ""
fi
