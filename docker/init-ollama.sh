#!/bin/bash

# Script de inicialización de Ollama
# Descarga y configura Phi-3.5 Mini para el Sistema de Homologación APF
# Optimizado para 6GB VRAM

set -e

echo "=================================================="
echo "  Inicialización de Ollama - APF v5"
echo "=================================================="
echo ""

# Configuración
OLLAMA_HOST="${OLLAMA_HOST:-http://ollama:11434}"
MODEL_NAME="${MODEL_NAME:-phi3.5}"
MAX_RETRIES=30
RETRY_INTERVAL=5

# Función para verificar si Ollama está disponible
check_ollama_ready() {
    echo "🔍 Verificando si Ollama está disponible..."
    local retries=0

    while [ $retries -lt $MAX_RETRIES ]; do
        if curl -s "$OLLAMA_HOST/api/tags" > /dev/null 2>&1; then
            echo "✅ Ollama está disponible!"
            return 0
        fi

        retries=$((retries + 1))
        echo "⏳ Esperando a Ollama... (intento $retries/$MAX_RETRIES)"
        sleep $RETRY_INTERVAL
    done

    echo "❌ Error: Ollama no responde después de $MAX_RETRIES intentos"
    return 1
}

# Función para verificar si el modelo ya está descargado
check_model_exists() {
    echo "🔍 Verificando si el modelo '$MODEL_NAME' ya está descargado..."

    if curl -s "$OLLAMA_HOST/api/tags" | grep -q "\"name\":\"$MODEL_NAME\""; then
        echo "✅ Modelo '$MODEL_NAME' ya está disponible!"
        return 0
    else
        echo "📥 Modelo '$MODEL_NAME' no encontrado, se procederá a descargar..."
        return 1
    fi
}

# Función para descargar el modelo
pull_model() {
    echo ""
    echo "=================================================="
    echo "  Descargando modelo: $MODEL_NAME"
    echo "=================================================="
    echo ""
    echo "⚠️  IMPORTANTE:"
    echo "   - Este proceso puede tomar 5-15 minutos"
    echo "   - Tamaño del modelo: ~2.3GB (Phi-3.5 Mini cuantizado)"
    echo "   - VRAM requerida: ~4.5-5GB"
    echo ""

    # Usar API de Ollama para pull
    curl -X POST "$OLLAMA_HOST/api/pull" \
         -H "Content-Type: application/json" \
         -d "{\"name\": \"$MODEL_NAME\"}" \
         --no-buffer 2>&1 | while IFS= read -r line; do
        echo "$line"

        # Extraer progreso si existe
        if echo "$line" | grep -q '"status"'; then
            status=$(echo "$line" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
            echo "   Status: $status"
        fi
    done

    echo ""
    echo "✅ Descarga completada!"
}

# Función para verificar el modelo después de descargarlo
verify_model() {
    echo ""
    echo "🔍 Verificando instalación del modelo..."

    # Listar modelos disponibles
    echo "Modelos disponibles en Ollama:"
    curl -s "$OLLAMA_HOST/api/tags" | grep -o '"name":"[^"]*"' | cut -d'"' -f4 || echo "No se pudo listar modelos"

    # Hacer una llamada de prueba simple
    echo ""
    echo "🧪 Ejecutando prueba del modelo..."

    response=$(curl -s -X POST "$OLLAMA_HOST/api/generate" \
         -H "Content-Type: application/json" \
         -d "{
             \"model\": \"$MODEL_NAME\",
             \"prompt\": \"Test\",
             \"stream\": false,
             \"options\": {
                 \"num_predict\": 10
             }
         }")

    if echo "$response" | grep -q '"response"'; then
        echo "✅ Modelo funcionando correctamente!"
        return 0
    else
        echo "⚠️  Advertencia: El modelo podría no estar funcionando correctamente"
        echo "Respuesta: $response"
        return 1
    fi
}

# Función principal
main() {
    echo "🚀 Iniciando configuración de Ollama..."
    echo ""

    # Paso 1: Verificar que Ollama esté listo
    if ! check_ollama_ready; then
        exit 1
    fi

    echo ""

    # Paso 2: Verificar si el modelo ya existe
    if check_model_exists; then
        echo ""
        echo "✅ El modelo ya está disponible. No es necesario descargar."
    else
        # Paso 3: Descargar el modelo
        if ! pull_model; then
            echo "❌ Error al descargar el modelo"
            exit 1
        fi
    fi

    echo ""

    # Paso 4: Verificar el modelo
    if verify_model; then
        echo ""
        echo "=================================================="
        echo "  ✅ Inicialización completada exitosamente!"
        echo "=================================================="
        echo ""
        echo "📊 Información del sistema:"
        echo "   - Modelo: $MODEL_NAME"
        echo "   - Host: $OLLAMA_HOST"
        echo "   - VRAM estimada: ~4.5-5GB"
        echo ""
        echo "🎯 El sistema está listo para usarse!"
        echo ""
    else
        echo ""
        echo "⚠️  La inicialización completó con advertencias"
        echo "   Revisa los logs arriba para más detalles"
        echo ""
    fi
}

# Ejecutar función principal
main

# Exit code
exit 0
