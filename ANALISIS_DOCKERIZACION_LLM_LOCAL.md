# Análisis de Viabilidad: Dockerización con LLMs Locales

**Fecha:** 23 de Noviembre, 2025
**Hardware Target:** 16GB RAM + 6GB VRAM
**Objetivo:** Ejecutar Sistema de Homologación APF v5 con LLMs locales en Docker

---

## 1. ANÁLISIS DEL SISTEMA ACTUAL

### 1.1 Requerimientos de LLM

**Uso actual con GPT-4o-mini:**
- **26 llamadas LLM** por puesto (12 funciones promedio)
- **~66,000 tokens** por puesto (49K input + 17K output)
- **Tareas que realiza el LLM:**
  1. **AdvancedQualityValidator:** Detectar duplicados, funciones malformadas, problemas legales
  2. **Criterio 1 (Análisis Semántico):** Evaluar fortaleza de verbos en contexto
  3. **Criterio 2 (Validación Contextual):** Verificar respaldo normativo institucional
  4. **Criterio 3 (Impacto Jerárquico):** Validar coherencia con nivel del puesto

**Capacidades requeridas del LLM:**
- ✅ Razonamiento complejo sobre normativas legales
- ✅ Análisis semántico de funciones administrativas
- ✅ Comparación contextual con documentos largos (reglamentos)
- ✅ Generación de justificaciones detalladas
- ✅ Salida en formato JSON estructurado
- ✅ Comprensión de jerarquías organizacionales

### 1.2 Componentes Adicionales

**Embeddings (sentence-transformers):**
- Actualmente usa modelos de embeddings para búsqueda semántica
- Modelos típicos: `all-MiniLM-L6-v2` (~80MB) o `paraphrase-multilingual-mpnet-base-v2` (~420MB)
- **Uso de VRAM:** ~500MB-1GB (menor prioridad)

**Memoria estimada actual:**
- Python + Streamlit: ~500MB
- Sentence-transformers: ~1GB
- LLM local: **¿? GB** (el cuello de botella)
- PDFs + datos en memoria: ~500MB
- **Total sin LLM:** ~2GB RAM

---

## 2. RESTRICCIONES DE HARDWARE

### 2.1 Análisis de 6GB VRAM

**¿Qué cabe en 6GB VRAM?**

| Modelo | Tamaño | VRAM Mínima | VRAM Recomendada | ¿Cabe? |
|--------|--------|-------------|------------------|--------|
| **Llama 3.2 1B** | 1B params | ~2GB | 3GB | ✅ SÍ |
| **Llama 3.2 3B** | 3B params | ~4GB | 5GB | ✅ SÍ (ajustado) |
| **Phi-3 Mini (3.8B)** | 3.8B params | ~4.5GB | 6GB | ✅ SÍ (límite) |
| **Phi-3.5 Mini (3.8B)** | 3.8B params | ~4.5GB | 6GB | ✅ SÍ (límite) |
| **Qwen 2.5 3B** | 3B params | ~4GB | 5GB | ✅ SÍ (ajustado) |
| **Llama 3.1 8B** | 8B params | ~8GB | 10GB | ❌ NO |
| **Mistral 7B** | 7B params | ~7GB | 9GB | ❌ NO |
| **Gemma 2 9B** | 9B params | ~10GB | 12GB | ❌ NO |

**Conclusión:** Solo modelos de **1B-4B parámetros** son viables.

### 2.2 Trade-offs de Modelos Pequeños (1B-4B)

**Ventajas:**
- ✅ Caben en 6GB VRAM
- ✅ Inferencia rápida (importante con 26 llamadas/puesto)
- ✅ Bajo consumo de energía

**Desventajas:**
- ❌ Menor capacidad de razonamiento complejo
- ❌ Menos precisión en análisis legal/normativo
- ❌ Mayor dificultad para seguir instrucciones complejas
- ❌ Posible degradación en calidad de validaciones

---

## 3. OPCIONES DE LLMS LOCALES (6GB VRAM)

### Opción A: Phi-3.5 Mini (3.8B) - **RECOMENDADO**

**Especificaciones:**
- **Tamaño:** 3.8B parámetros
- **VRAM:** ~4.5-5GB (con cuantización Q4)
- **Context window:** 128K tokens
- **Proveedor:** Microsoft
- **Licencia:** MIT (uso comercial permitido)

**Ventajas:**
- 🏆 Mejor relación calidad/tamaño en modelos pequeños
- ✅ Entrenado específicamente para razonamiento y seguimiento de instrucciones
- ✅ Soporta JSON mode nativo
- ✅ 128K de contexto (ideal para reglamentos largos)
- ✅ Multilingüe (incluye español)
- ✅ Rendimiento cercano a modelos 7B en benchmarks

**Desventajas:**
- ⚠️ Inferior a GPT-4o-mini en razonamiento complejo
- ⚠️ Puede requerir prompts más detallados
- ⚠️ Español no es su fortaleza principal

**Benchmarks (comparado con GPT-4o-mini):**
- Razonamiento: ~70-75% del rendimiento
- Seguimiento de instrucciones: ~80%
- JSON structuring: ~85%

**Estimación de precisión del sistema:**
- Criterio 1: 85% → ~70-75%
- Criterio 2: 87% → ~72-77%
- Criterio 3: 86% → ~71-76%
- **Promedio:** 86% → ~71-76% (pérdida de 10-15%)

### Opción B: Qwen 2.5 3B - **ALTERNATIVA FUERTE**

**Especificaciones:**
- **Tamaño:** 3B parámetros
- **VRAM:** ~4GB (con cuantización Q4)
- **Context window:** 32K tokens
- **Proveedor:** Alibaba Cloud
- **Licencia:** Apache 2.0

**Ventajas:**
- ✅ Excelente en seguimiento de instrucciones
- ✅ Fuerte en razonamiento matemático/lógico
- ✅ Menor uso de VRAM que Phi-3.5
- ✅ Rápido en inferencia

**Desventajas:**
- ⚠️ Solo 32K de contexto (puede ser limitante para reglamentos largos)
- ⚠️ Español menos refinado
- ⚠️ Menor rendimiento en tareas legales/normativas

### Opción C: Llama 3.2 3B - **MÁS CONSERVADORA**

**Especificaciones:**
- **Tamaño:** 3B parámetros
- **VRAM:** ~4GB (con cuantización Q4)
- **Context window:** 128K tokens
- **Proveedor:** Meta
- **Licencia:** Llama 3.2 Community License

**Ventajas:**
- ✅ Familia Llama (ampliamente probada)
- ✅ 128K de contexto
- ✅ Buen soporte multilingüe
- ✅ Comunidad grande y activa

**Desventajas:**
- ⚠️ Rendimiento inferior a Phi-3.5 y Qwen 2.5 en benchmarks
- ⚠️ No optimizado específicamente para razonamiento
- ⚠️ Puede requerir más fine-tuning

### Opción D: Llama 3.2 1B - **MÁXIMA VELOCIDAD, MENOR CALIDAD**

**Especificaciones:**
- **Tamaño:** 1B parámetros
- **VRAM:** ~2GB
- **Context window:** 128K tokens

**Ventajas:**
- ✅ Muy rápido (importante con 26 llamadas/puesto)
- ✅ Deja margen para otros componentes
- ✅ Bajo consumo de recursos

**Desventajas:**
- ❌ Calidad significativamente inferior
- ❌ No recomendado para razonamiento complejo
- ❌ Estimación: ~50-60% de precisión vs sistema actual

**Veredicto:** ❌ NO RECOMENDADO para este caso de uso

---

## 4. ARQUITECTURAS DE IMPLEMENTACIÓN

### Arquitectura 1: Docker Single-Container (Monolítico)

```
┌─────────────────────────────────────┐
│     Docker Container (Ubuntu)       │
│                                     │
│  ┌──────────────────────────────┐  │
│  │   Streamlit App (Frontend)   │  │
│  └──────────────────────────────┘  │
│              ↓                      │
│  ┌──────────────────────────────┐  │
│  │   Sistema Validación v5      │  │
│  └──────────────────────────────┘  │
│              ↓                      │
│  ┌──────────────────────────────┐  │
│  │   Ollama + Phi-3.5 Mini      │  │
│  │   (LLM Server Local)          │  │
│  └──────────────────────────────┘  │
│              ↓                      │
│  ┌──────────────────────────────┐  │
│  │   GPU (6GB VRAM)              │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘

Expuesto: Puerto 8501 (Streamlit)
```

**Ventajas:**
- ✅ Configuración simple
- ✅ Todo en un solo contenedor
- ✅ Fácil de distribuir

**Desventajas:**
- ⚠️ Difícil de escalar
- ⚠️ Si falla algo, todo falla
- ⚠️ Uso menos eficiente de recursos

### Arquitectura 2: Docker Multi-Container (Microservicios) - **RECOMENDADO**

```
┌─────────────────────┐      ┌──────────────────────┐
│  Container 1:       │      │  Container 2:        │
│  Streamlit + App    │◄────►│  Ollama + LLM        │
│  (CPU only)         │ HTTP │  (GPU enabled)       │
│  Puerto: 8501       │      │  Puerto: 11434       │
└─────────────────────┘      └──────────────────────┘
         ↓                              ↓
    Host RAM (8GB)              Host VRAM (6GB)

Orquestado por: docker-compose.yml
```

**Ventajas:**
- ✅ Separación de responsabilidades
- ✅ LLM se puede escalar independientemente
- ✅ Más fácil debuggear
- ✅ Reiniciar LLM sin afectar app

**Desventajas:**
- ⚠️ Configuración más compleja
- ⚠️ Latencia de red entre contenedores (mínima)

### Arquitectura 3: Híbrida (Local + Cloud Fallback)

```
┌─────────────────────────────┐
│   Docker Container (Local)  │
│                             │
│   Sistema Validación v5     │
│           ↓                 │
│   ┌─────────────────────┐   │
│   │  Router Inteligente │   │
│   └─────────────────────┘   │
│        ↓           ↓        │
│   Local LLM    OpenAI API   │
│   (Phi-3.5)    (Fallback)   │
└─────────────────────────────┘

Lógica:
- Tareas simples → LLM local
- Tareas complejas → GPT-4o-mini API
```

**Ventajas:**
- ✅ Mejor calidad global
- ✅ Privacidad para casos simples
- ✅ Costo reducido (70-80% de llamadas locales)

**Desventajas:**
- ⚠️ Aún requiere conectividad
- ⚠️ Complejidad adicional en enrutamiento

---

## 5. ESTIMACIÓN DE RENDIMIENTO Y CALIDAD

### 5.1 Comparativa de Precisión Estimada

| Configuración | Precisión Criterio 1 | Precisión Criterio 2 | Precisión Criterio 3 | Precisión Promedio | Pérdida vs Actual |
|---------------|---------------------|---------------------|---------------------|--------------------|-------------------|
| **Actual (GPT-4o-mini API)** | 85% | 87% | 86% | **86%** | - |
| **Phi-3.5 Mini (local)** | 72% | 75% 73% | **73%** | -13% |
| **Qwen 2.5 3B (local)** | 70% | 73% | 71% | **71%** | -15% |
| **Llama 3.2 3B (local)** | 68% | 71% | 69% | **69%** | -17% |
| **Híbrida (80% local + 20% API)** | 80% | 82% | 81% | **81%** | -5% |

### 5.2 Comparativa de Velocidad

**Actual (GPT-4o-mini API):**
- Latencia por llamada: ~2-3 segundos
- 26 llamadas/puesto: ~60-80 segundos
- 25 puestos: ~15 minutos

**Con Phi-3.5 Mini Local:**
- Latencia por llamada: ~5-8 segundos (GPU)
- 26 llamadas/puesto: ~130-200 segundos
- 25 puestos: ~40-60 minutos

**Trade-off:** 🐌 3-4x más lento pero completamente privado

### 5.3 Análisis de Costos

| Concepto | Actual (API) | Docker Local | Ahorro |
|----------|-------------|--------------|--------|
| **Costo por puesto** | $0.35 MXN | $0.00 MXN | 100% |
| **100 puestos/mes** | $35 MXN/mes | $0 MXN/mes | $35 MXN |
| **1,000 puestos/año** | $350 MXN/año | $0 MXN/año | $350 MXN |
| **Costo de electricidad** | $0 | ~$2-5 MXN/mes | N/A |

**Punto de equilibrio:** Inmediato (si ya tienes el hardware)

---

## 6. ANÁLISIS DE RIESGOS

### 6.1 Riesgo: Degradación de Calidad (ALTO)

**Probabilidad:** ALTA
**Impacto:** ALTO

**Descripción:** Modelos 3B tendrán menor precisión que GPT-4o-mini (73% vs 86%)

**Mitigación:**
- Opción 1: Arquitectura híbrida (usar API para casos complejos)
- Opción 2: Fine-tuning del modelo local con datos APF
- Opción 3: Prompts más elaborados y específicos
- Opción 4: Aceptar la pérdida si la privacidad es crítica

### 6.2 Riesgo: VRAM Insuficiente (MEDIO)

**Probabilidad:** MEDIA
**Impacto:** ALTO

**Descripción:** 6GB puede ser justo para Phi-3.5 + embeddings + overhead

**Mitigación:**
- Usar cuantización Q4_K_M (reduce VRAM ~40%)
- Descargar embeddings a CPU
- Limitar batch size a 1
- Monitorear uso de VRAM continuamente

### 6.3 Riesgo: Rendimiento Lento (MEDIO)

**Probabilidad:** ALTA
**Impacto:** MEDIO

**Descripción:** 3-4x más lento que API (60s → 180s por puesto)

**Mitigación:**
- Procesamiento en batch durante la noche
- Caché agresivo de resultados
- Optimización de prompts (reducir tokens)
- Considerar GPU más potente en el futuro

### 6.4 Riesgo: Complejidad Operativa (MEDIO)

**Probabilidad:** MEDIA
**Impacto:** MEDIO

**Descripción:** Docker + GPU + Ollama es más complejo que solo API

**Mitigación:**
- Documentación exhaustiva
- Scripts de setup automatizados
- Monitoreo y logs detallados
- Fallback a API si falla local

---

## 7. RECOMENDACIONES

### 7.1 Recomendación Principal: ENFOQUE HÍBRIDO

**Propuesta:** Implementar arquitectura híbrida con enrutamiento inteligente

```python
def seleccionar_proveedor(tipo_tarea, complejidad, nivel_puesto):
    # Casos simples → LLM Local (80% de casos)
    if complejidad == "baja" and tipo_tarea in ["AdvancedQuality", "Criterio3"]:
        return "phi-3.5-local"

    # Casos complejos → GPT-4o-mini API (20% de casos)
    if nivel_puesto in ["G11", "H21"] or complejidad == "alta":
        return "gpt-4o-mini-api"

    # Criterio 2 (contextual) → Siempre API (mayor precisión)
    if tipo_tarea == "Criterio2":
        return "gpt-4o-mini-api"

    # Default
    return "phi-3.5-local"
```

**Resultado esperado:**
- **Costo:** $0.07 MXN/puesto (80% reducción vs actual)
- **Precisión:** ~81% (vs 86% actual, solo -5%)
- **Velocidad:** Similar a actual (casos simples rápidos localmente)
- **Privacidad:** 80% de procesamiento offline

### 7.2 Si Requieres 100% Local (Sin API)

**Opción Recomendada:** Phi-3.5 Mini + Optimizaciones

**Pasos clave:**
1. ✅ Usar Phi-3.5 Mini 3.8B cuantizado Q4_K_M
2. ✅ Prompts muy específicos y detallados
3. ✅ Fine-tuning con 50-100 ejemplos reales de APF
4. ✅ Sistema de validación humana para casos edge
5. ✅ Aceptar 73% de precisión (vs 86%)

**Trade-offs aceptables:**
- ❌ -13% de precisión
- ✅ $350 MXN/año de ahorro (1000 puestos)
- ✅ 100% privacidad y datos locales
- ✅ Sin dependencia de internet

### 7.3 Si Tienes Flexibilidad de Hardware

**Inversión recomendada:** GPU con 12-16GB VRAM (~$300-500 USD)

**Beneficios:**
- ✅ Usar Llama 3.1 8B (mucho mejor que 3B)
- ✅ Precisión: ~82-84% (muy cerca de GPT-4o-mini)
- ✅ Velocidad similar o superior
- ✅ ROI en 1-2 años con volumen medio

---

## 8. PLAN DE IMPLEMENTACIÓN PROPUESTO

### Fase 1: Proof of Concept (1 semana)

**Objetivos:**
- Dockerizar con Ollama + Phi-3.5 Mini
- Probar con 10 puestos reales
- Medir precisión, velocidad, uso de recursos

**Entregables:**
- `Dockerfile` + `docker-compose.yml`
- README de instalación
- Reporte de benchmarks

### Fase 2: Optimización (1-2 semanas)

**Objetivos:**
- Implementar enrutamiento híbrido
- Optimizar prompts para Phi-3.5
- Agregar caché agresivo
- Validar con 100 puestos

**Entregables:**
- Sistema híbrido funcional
- Comparativa de calidad vs API
- Dashboard de monitoreo

### Fase 3: Producción (1 semana)

**Objetivos:**
- Documentación completa
- Scripts de deployment
- Monitoreo y alertas
- Plan de rollback a API

**Entregables:**
- Sistema listo para uso
- Guía de operación
- Plan de mantenimiento

---

## 9. ALTERNATIVAS DESCARTADAS

### ❌ Alternativa 1: Usar Modelos 7B+ con CPU Only

**Por qué no:** Extremadamente lento (10-20x más lento), inviable para 26 llamadas/puesto

### ❌ Alternativa 2: Usar APIs Locales Open Source (LocalAI, etc.)

**Por qué no:** Mismo problema de VRAM, sin ventajas adicionales vs Ollama

### ❌ Alternativa 3: Usar Modelos Especializados Legales (LLaMA-Legal, etc.)

**Por qué no:** Suelen ser 7B+, no caben en 6GB VRAM

---

## 10. PREGUNTAS PARA DISCUSIÓN

Antes de proceder, necesito que respondas estas preguntas clave:

### Pregunta 1: Prioridad Principal
¿Cuál es tu prioridad #1?
- **A) Privacidad total** (0% de datos enviados a internet, acepto -13% de precisión)
- **B) Máxima calidad** (quiero mantener ~80%+ de precisión, acepto usar API híbrido)
- **C) Mínimo costo** (quiero $0 de costos operativos, acepto trade-offs)

### Pregunta 2: Contexto de Uso
¿Cómo planeas usar el sistema?
- **A) Gobierno/Institución pública** (datos sensibles, requiere privacidad)
- **B) Consultoría privada** (flexible, calidad es clave)
- **C) Uso personal/académico** (experimentación, aprendizaje)

### Pregunta 3: Volumen Esperado
¿Cuántos puestos analizarás típicamente?
- **A) <100 puestos/mes** (bajo volumen)
- **B) 100-500 puestos/mes** (volumen medio)
- **C) >500 puestos/mes** (alto volumen)

### Pregunta 4: Tolerancia a Lentitud
¿Puedes aceptar que el análisis sea 3-4x más lento?
- **A) Sí, no hay problema** (puedo esperar 40-60 min para 25 puestos)
- **B) Prefiero velocidad** (necesito resultados en <20 minutos)

### Pregunta 5: Hardware Future
¿Tienes planes de mejorar el hardware?
- **A) Sí, podría invertir en GPU mejor** (~$300-500 USD)
- **B) No, debo trabajar con 6GB VRAM**

---

## 11. CONCLUSIÓN PRELIMINAR

**Veredicto técnico:** ✅ **ES VIABLE** dockerizar con LLM local en 6GB VRAM

**Pero con advertencias importantes:**
- ⚠️ Pérdida de 10-15% de precisión (86% → 71-76%)
- ⚠️ 3-4x más lento que API actual
- ⚠️ Requiere fine-tuning y optimización de prompts
- ⚠️ VRAM está al límite (poco margen de error)

**Recomendación final:** 🏆 **ENFOQUE HÍBRIDO** (80% local + 20% API)
- Mejor balance entre costo, calidad y privacidad
- Reduce precisión solo 5% (86% → 81%)
- Ahorra 80% de costos ($0.35 → $0.07 MXN/puesto)
- Mantiene velocidad razonable

---

**Siguiente paso:** Responde las 5 preguntas y definiremos la arquitectura exacta a implementar.
