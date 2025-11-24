"""
Report Humanizer - Convierte análisis técnico JSON a reportes en lenguaje natural.

Este módulo usa LLM para generar reportes humanizados a partir de los JSON de análisis,
facilitando la comprensión y auditoría de las decisiones de validación.

Incluye soporte para validaciones adicionales v5.33 (duplicados, malformadas, marco legal, objetivo).

Autor: Claude Code v5.33-new
Fecha: 2025-11-10
"""

import json
import os
from typing import Dict, Any, Literal
from datetime import datetime
from litellm import completion

# Configuración LLM
LLM_CONFIG = {
    "model": "openai/gpt-4o-mini",
    "temperature": 0.3,  # Un poco de creatividad para lenguaje natural
    "max_tokens": 4000,  # Permitir reportes extensos
}


def generate_simplified_report(analisis_json: Dict[str, Any]) -> str:
    """
    Genera un reporte simplificado (resumen ejecutivo) en lenguaje natural.

    Args:
        analisis_json: Diccionario con el análisis completo

    Returns:
        String con el reporte en markdown
    """

    # Extraer información clave
    puesto = analisis_json['resultados'][0]['puesto']
    validacion = analisis_json['resultados'][0]['validacion']

    prompt = f"""Eres un auditor experto de la Administración Pública Federal (APF) de México.
Tu tarea es generar un **RESUMEN EJECUTIVO** en lenguaje claro y profesional a partir del siguiente análisis técnico de validación de un puesto.

**INFORMACIÓN DEL PUESTO:**
- Código: {puesto['codigo']}
- Denominación: {puesto['denominacion']}
- Nivel Salarial: {puesto.get('nivel', puesto.get('nivel_salarial', 'N/A'))}

**RESULTADO DE VALIDACIÓN:**
- Decisión Final: {validacion['resultado']}
- Criterios Aprobados: {validacion['criterios_aprobados']}/3
- Confianza Global: {validacion['confianza']:.0%}

**DETALLES POR CRITERIO:**

**Criterio 1 - Análisis de Verbos:**
- Resultado: {validacion['criterios']['criterio_1_verbos']['resultado']}
- Funciones Aprobadas: {validacion['criterios']['criterio_1_verbos']['funciones_aprobadas']}/{validacion['criterios']['criterio_1_verbos']['total_funciones']}
- Funciones Observadas: {validacion['criterios']['criterio_1_verbos']['funciones_observadas']}/{validacion['criterios']['criterio_1_verbos']['total_funciones']}
- Funciones Rechazadas: {validacion['criterios']['criterio_1_verbos']['funciones_rechazadas']}/{validacion['criterios']['criterio_1_verbos']['total_funciones']}
- Tasa Crítica: {validacion['criterios']['criterio_1_verbos']['tasa_critica']:.0%}

**Validaciones Adicionales - Criterio 1:**
- Duplicados Detectados: {validacion['criterios']['criterio_1_verbos'].get('validaciones_adicionales', {}).get('duplicacion', {}).get('total_duplicados', 0)}
- Funciones Malformadas: {validacion['criterios']['criterio_1_verbos'].get('validaciones_adicionales', {}).get('malformacion', {}).get('total_malformadas', 0)}

**Criterio 2 - Validación Contextual:**
- Resultado: {validacion['criterios']['criterio_2_contextual']['resultado']}
- Alineación: {validacion['criterios']['criterio_2_contextual']['alineacion']['clasificacion']}
- Confianza: {validacion['criterios']['criterio_2_contextual']['alineacion']['confianza']:.2f}

**Validaciones Adicionales - Criterio 2:**
- Problemas Marco Legal: {validacion['criterios']['criterio_2_contextual'].get('validaciones_adicionales', {}).get('marco_legal', {}).get('total_problemas', 0)}
- Objetivo Adecuado: {'Sí' if validacion['criterios']['criterio_2_contextual'].get('validaciones_adicionales', {}).get('objetivo_general', {}).get('es_adecuado', True) else 'No'}
- Calificación Objetivo: {validacion['criterios']['criterio_2_contextual'].get('validaciones_adicionales', {}).get('objetivo_general', {}).get('calificacion', 1.0):.0%}

**Criterio 3 - Impacto Jerárquico:**
- Resultado: {validacion['criterios']['criterio_3_impacto']['resultado']}
- Tasa Crítica: {validacion['criterios']['criterio_3_impacto']['metricas']['tasa_critica']:.0%}
- Funciones Critical: {validacion['criterios']['criterio_3_impacto']['metricas'].get('funciones_critical', 0)}

---

**INSTRUCCIONES PARA EL REPORTE:**

Genera un **RESUMEN EJECUTIVO** de 1-2 páginas en formato Markdown con las siguientes secciones:

## 📋 RESUMEN EJECUTIVO - VALIDACIÓN DE PUESTO

### 1. Identificación del Puesto
- Presenta de manera clara los datos del puesto

### 2. Decisión Final
- Indica claramente si el puesto fue APROBADO o RECHAZADO
- Explica qué significa este resultado en términos prácticos
- Menciona la confianza global del análisis

### 3. Análisis por Criterios

#### Criterio 1: Análisis Semántico de Funciones
- Explica QUÉ se evaluó (uso apropiado de verbos y respaldo normativo)
- Resume los resultados (cuántas funciones pasaron/fallaron)
- Explica POR QUÉ se obtuvo este resultado
- Indica si el criterio PASÓ o FALLÓ y qué significa
- **Validaciones Adicionales:** Si se detectaron duplicados o funciones malformadas, explica cuántos y qué implica esto

#### Criterio 2: Validación Contextual
- Explica QUÉ se evaluó (alineación con normativa institucional)
- Indica el nivel de alineación encontrado
- Explica POR QUÉ se obtuvo este nivel de confianza
- Indica si el criterio PASÓ o FALLÓ
- **Validaciones Adicionales:** Si se detectaron problemas en el marco legal (organismos extintos, leyes obsoletas) o el objetivo general es inadecuado, explica qué problemas se encontraron

#### Criterio 3: Impacto Jerárquico
- Explica QUÉ se evaluó (coherencia del impacto de las funciones con el nivel salarial)
- Resume los resultados
- Indica si el criterio PASÓ o FALLÓ

### 4. Conclusión y Recomendaciones
- Resume la decisión final en términos comprensibles
- Indica acciones requeridas (si las hay)
- Proporciona recomendaciones claras

---

**IMPORTANTE:**
- Usa lenguaje profesional pero accesible (evita jerga técnica excesiva)
- Explica los conceptos técnicos cuando sea necesario
- Sé conciso pero completo
- Enfócate en el "QUÉ", "CÓMO" y "POR QUÉ" de cada decisión
- NO copies textualmente los datos técnicos, interprétalos
"""

    try:
        response = completion(
            model=LLM_CONFIG["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=LLM_CONFIG["temperature"],
            max_tokens=LLM_CONFIG["max_tokens"]
        )

        reporte = response.choices[0].message.content

        # Añadir metadatos
        header = f"""# 📄 REPORTE DE VALIDACIÓN - MODO SIMPLIFICADO

**Generado por:** Sistema de Validación APF v5.33-new
**Fecha de generación:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
**Tipo de reporte:** Resumen Ejecutivo

---

"""

        return header + reporte

    except Exception as e:
        return f"❌ Error al generar reporte simplificado: {str(e)}"


def generate_detailed_report(analisis_json: Dict[str, Any]) -> str:
    """
    Genera un reporte detallado con análisis completo de cada función.

    Args:
        analisis_json: Diccionario con el análisis completo

    Returns:
        String con el reporte en markdown
    """

    # Extraer información
    puesto = analisis_json['resultados'][0]['puesto']
    validacion = analisis_json['resultados'][0]['validacion']
    criterio_1 = validacion['criterios']['criterio_1_verbos']

    # Limitar el JSON para el prompt (solo información esencial)
    datos_compactos = {
        "puesto": puesto,
        "resultado_final": validacion['resultado'],
        "criterios_aprobados": validacion['criterios_aprobados'],
        "confianza": validacion['confianza'],
        "criterio_1": {
            "resultado": criterio_1['resultado'],
            "aprobadas": criterio_1['funciones_aprobadas'],
            "observadas": criterio_1['funciones_observadas'],
            "rechazadas": criterio_1['funciones_rechazadas'],
            "total": criterio_1['total_funciones'],
            # Incluir solo primeras 3 funciones de cada categoría para no exceder tokens
            "muestra_aprobadas": criterio_1['detalles']['aprobadas'][:3] if len(criterio_1['detalles']['aprobadas']) > 0 else [],
            "muestra_observadas": criterio_1['detalles']['observadas'][:3] if len(criterio_1['detalles']['observadas']) > 0 else [],
            "muestra_rechazadas": criterio_1['detalles']['rechazadas'][:3] if len(criterio_1['detalles']['rechazadas']) > 0 else [],
            # NUEVO v5.33: Validaciones adicionales CON DETALLE COMPLETO
            "validaciones_adicionales": {
                "duplicados": criterio_1.get('validaciones_adicionales', {}).get('duplicacion', {}).get('total_duplicados', 0),
                "malformadas": criterio_1.get('validaciones_adicionales', {}).get('malformacion', {}).get('total_malformadas', 0),
                # INCLUIR TODOS LOS PARES DUPLICADOS (no solo 3)
                "detalles_duplicados": criterio_1.get('validaciones_adicionales', {}).get('duplicacion', {}).get('pares_duplicados', []),
                # INCLUIR TODAS LAS FUNCIONES MALFORMADAS (no solo 3)
                "detalles_malformadas": criterio_1.get('validaciones_adicionales', {}).get('malformacion', {}).get('funciones_problematicas', [])
            }
        },
        "criterio_2": {
            "resultado": validacion['criterios']['criterio_2_contextual']['resultado'],
            "alineacion": validacion['criterios']['criterio_2_contextual']['alineacion']['clasificacion'],
            "confianza": validacion['criterios']['criterio_2_contextual']['alineacion']['confianza'],
            "razonamiento": validacion['criterios']['criterio_2_contextual']['razonamiento'][:500],  # Truncar
            # NUEVO v5.33: Validaciones adicionales CON DETALLE COMPLETO
            "validaciones_adicionales": {
                "problemas_legales": validacion['criterios']['criterio_2_contextual'].get('validaciones_adicionales', {}).get('marco_legal', {}).get('total_problemas', 0),
                "objetivo_adecuado": validacion['criterios']['criterio_2_contextual'].get('validaciones_adicionales', {}).get('objetivo_general', {}).get('es_adecuado', True),
                "calificacion_objetivo": validacion['criterios']['criterio_2_contextual'].get('validaciones_adicionales', {}).get('objetivo_general', {}).get('calificacion', 1.0),
                # INCLUIR TODOS LOS PROBLEMAS LEGALES (no solo 3)
                "detalles_problemas_legales": validacion['criterios']['criterio_2_contextual'].get('validaciones_adicionales', {}).get('marco_legal', {}).get('problemas', []),
                # INCLUIR TODOS LOS PROBLEMAS DE OBJETIVO (no solo 3)
                "detalles_problemas_objetivo": validacion['criterios']['criterio_2_contextual'].get('validaciones_adicionales', {}).get('objetivo_general', {}).get('problemas', [])
            }
        },
        "criterio_3": {
            "resultado": validacion['criterios']['criterio_3_impacto']['resultado'],
            "metricas": validacion['criterios']['criterio_3_impacto']['metricas']
        }
    }

    prompt = f"""Eres un auditor senior experto de la Administración Pública Federal (APF) de México.
Tu tarea es generar un **REPORTE DETALLADO DE AUDITORÍA** en lenguaje profesional y técnico a partir del siguiente análisis de validación.

**DATOS DEL ANÁLISIS:**
```json
{json.dumps(datos_compactos, indent=2, ensure_ascii=False)}
```

---

**INSTRUCCIONES PARA EL REPORTE DETALLADO:**

Genera un **REPORTE DE AUDITORÍA COMPLETO** en formato Markdown con las siguientes secciones:

## 🔍 REPORTE DE AUDITORÍA DETALLADO - VALIDACIÓN DE PUESTO

### 1. Identificación y Contexto
- Datos completos del puesto
- Contexto de la validación
- Fecha y sistema utilizado

### 2. Metodología de Validación
Explica brevemente cómo funciona el sistema de validación:
- Los 3 criterios evaluados
- La matriz 2-of-3 para decisión final
- Los umbrales utilizados

### 3. Resultado Final
- Decisión: APROBADO/RECHAZADO
- Clasificación (si aplica)
- Confianza global
- Criterios que pasaron/fallaron

### 4. Análisis Detallado por Criterio

#### 4.1 Criterio 1: Análisis Semántico de Funciones

**Objetivo del Criterio:**
Explica qué evalúa este criterio (verbos apropiados, respaldo normativo, estructura, semántica, jerarquía)

**Metodología:**
- Cómo se evaluó cada función
- Los 5 sub-criterios utilizados
- El sistema de scoring (0.0 - 1.0)

**Resultados Generales:**
- Total de funciones analizadas
- Distribución: aprobadas/observadas/rechazadas
- Tasa crítica vs umbral (≤50%)
- Decisión: PASS/FAIL

**Análisis de Funciones Representativas:**

Para cada categoría (aprobadas, observadas, rechazadas), analiza 1-2 ejemplos:
- Función específica
- Scores obtenidos
- Razonamiento del sistema
- Por qué fue clasificada así

**Validaciones Adicionales de Calidad (v5.33):**

**IMPORTANTE:** Si se detectaron problemas adicionales, DEBES incluir el **DETALLE COMPLETO** de TODOS los problemas detectados en una tabla clara:

**A) Funciones Duplicadas Semánticamente:**
Si hay duplicados (total_duplicados > 0), crea una tabla con:
- Función 1 ID y Función 2 ID
- Porcentaje de similitud
- Descripción de POR QUÉ son similares
- Sugerencia de corrección

**Formato de Tabla:**
| Par | Funciones | Similitud | Razón | Sugerencia |
|-----|-----------|-----------|-------|------------|
| 1 | F2 ↔ F3 | 90% | Ambas describen coordinar acciones... | Consolidar en una sola función |
| 2 | F5 ↔ F6 | 85% | Supervisar y vigilar son sinónimos... | Usar un solo verbo |

**B) Funciones Malformadas:**
Si hay malformadas (total_malformadas > 0), crea una tabla con:
- Función ID
- Tipo(s) de problema (VACIA, PLACEHOLDER, MUY_CORTA, SIN_VERBO, SIN_COMPLEMENTO, SIN_RESULTADO, SIN_SENTIDO)
- Severidad (CRITICAL, HIGH, MODERATE, LOW)
- Descripción del problema
- Fragmento de texto problemático (max 100 chars)

**Formato de Tabla:**
| Función | Tipo Problema | Severidad | Descripción | Texto Problemático |
|---------|---------------|-----------|-------------|-------------------|
| F4 | PLACEHOLDER | CRITICAL | Función vacía con "..." | "..." |
| F7 | MUY_CORTA | HIGH | Menos de 15 caracteres | "Hacer" |

**INSTRUCCIÓN CRÍTICA:** NO resumas ni omitas problemas. Incluye TODOS los pares duplicados y TODAS las funciones malformadas que aparecen en los datos JSON.

#### 4.2 Criterio 2: Validación Contextual

**Objetivo del Criterio:**
Validación mediante LLM de la alineación con normativa institucional

**Resultados:**
- Nivel de alineación: ALIGNED/PARTIALLY_ALIGNED/NOT_ALIGNED
- Confianza del LLM
- Razonamiento completo
- Evidencias normativas utilizadas (si disponibles)

**Interpretación:**
Explica qué significa este resultado y por qué el criterio PASÓ/FALLÓ

**Validaciones Adicionales de Calidad (v5.33):**

**IMPORTANTE:** Si se detectaron problemas adicionales, DEBES incluir el **DETALLE COMPLETO** de TODOS los problemas detectados en tablas claras:

**A) Problemas de Marco Legal:**
Si hay problemas legales (total_problemas > 0), crea una tabla con:
- Tipo de problema (ORGANISMO_EXTINTO, LEY_OBSOLETA, REFERENCIA_INVALIDA, INCONSISTENCIA)
- Severidad (CRITICAL, HIGH, MODERATE, LOW)
- Descripción del problema
- Referencia problemática (texto específico)
- Sugerencia de corrección

**Formato de Tabla:**
| # | Tipo | Severidad | Descripción | Referencia Problemática | Sugerencia |
|---|------|-----------|-------------|------------------------|------------|
| 1 | ORGANISMO_EXTINTO | HIGH | Referencia a CONACYT extinto | "Ley Orgánica del CONACYT" | Actualizar a nueva denominación |

**B) Problemas de Objetivo General:**
Si el objetivo es inadecuado (es_adecuado = false), crea una tabla con:
- Tipo de problema (MUY_CORTO, MUY_LARGO, SIN_VERBO, SIN_FINALIDAD, GENERICO, INCOHERENTE)
- Severidad (CRITICAL, HIGH, MODERATE, LOW)
- Descripción específica del problema
- Calificación obtenida (0.0 - 1.0)

**Formato de Tabla:**
| # | Tipo Problema | Severidad | Descripción | Calificación |
|---|---------------|-----------|-------------|--------------|
| 1 | MUY_CORTO | CRITICAL | Solo 11 caracteres | 20% |
| 2 | SIN_FINALIDAD | HIGH | No explica el para qué del puesto | 20% |

**INSTRUCCIÓN CRÍTICA:** NO resumas ni omitas problemas. Incluye TODOS los problemas legales y TODOS los problemas de objetivo que aparecen en los datos JSON.

#### 4.3 Criterio 3: Impacto Jerárquico

**Objetivo del Criterio:**
Evaluar si el impacto declarado en las funciones es coherente con el nivel jerárquico del puesto

**Metodología:**
- Evalúa apropiación de verbos, alcance de decisiones, consecuencias de errores y complejidad
- Clasifica discrepancias como CRITICAL (sin respaldo normativo) o MODERATE (con respaldo normativo)
- Umbral: ≤50% funciones CRITICAL para aprobar

**Resultados:**
Extrae del JSON los valores de criterio_3.metricas y preséntales así:
- Total funciones analizadas: [valor]
- Funciones CRITICAL (discrepancias sin respaldo): [valor]
- Funciones MODERATE (discrepancias con respaldo): [valor]
- **Tasa Crítica:** [valor]% (umbral: ≤50%)
- **Decisión:** [PASS o FAIL]

**Interpretación Importante:**
**⚠️ Tasa Crítica 0% = EXCELENTE**
Una tasa de 0% significa que **NO se detectaron funciones con discrepancias de impacto sin respaldo normativo**.
Esto es **POSITIVO** e indica que:
- Todas las funciones tienen impacto coherente con el nivel jerárquico del puesto
- No hay verbos prohibidos o inapropiados para el nivel
- El alcance, consecuencias y complejidad son adecuados
- Cualquier discrepancia menor está respaldada normativamente

**Nota:** El Criterio 3 evalúa coherencia jerárquica, NO cantidad de funciones. Una tasa de 0% indica máxima coherencia.

### 5. Aplicación de la Matriz 2-of-3

Explica cómo se llegó a la decisión final:
- Criterios que pasaron: X/3
- Lógica de decisión aplicada
- Por qué el resultado es APROBADO o RECHAZADO

### 6. Evidencias y Trazabilidad

Resume las evidencias clave utilizadas:
- Fragmentos normativos consultados
- Documentos de referencia
- Nivel de confianza en evidencias

### 7. Conclusiones y Recomendaciones

**Conclusión Principal:**
Declaración clara de la decisión y su justificación

**Recomendaciones:**
- Acciones requeridas (si las hay)
- Áreas de atención
- Sugerencias de mejora (si aplica)

**Consideraciones Finales:**
Observaciones importantes para la toma de decisiones

---

**ESTILO DEL REPORTE:**
- Lenguaje técnico y profesional
- Enfoque en explicar QUÉ se evaluó, CÓMO se evaluó, POR QUÉ se decidió así
- Incluir datos específicos y métricas
- Justificar cada decisión con evidencia
- Ser exhaustivo pero organizado
- Usar formato markdown con secciones claras
"""

    try:
        response = completion(
            model=LLM_CONFIG["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=LLM_CONFIG["temperature"],
            max_tokens=LLM_CONFIG["max_tokens"]
        )

        reporte = response.choices[0].message.content

        # Añadir metadatos
        header = f"""# 📋 REPORTE DE AUDITORÍA COMPLETO - ANÁLISIS DETALLADO

**Generado por:** Sistema de Validación APF v5.33-new
**Fecha de generación:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
**Tipo de reporte:** Análisis Detallado para Auditoría

---

"""

        return header + reporte

    except Exception as e:
        return f"❌ Error al generar reporte detallado: {str(e)}"


def humanize_report(
    analisis_json_path: str,
    mode: Literal["simplificado", "detallado"] = "simplificado"
) -> str:
    """
    Función principal para humanizar un reporte JSON.

    Args:
        analisis_json_path: Ruta al archivo JSON de análisis
        mode: Modo de reporte ("simplificado" o "detallado")

    Returns:
        String con el reporte humanizado en markdown
    """

    try:
        # Leer JSON
        with open(analisis_json_path, 'r', encoding='utf-8') as f:
            analisis_json = json.load(f)

        # Validar que tenga resultados
        if 'resultados' not in analisis_json or len(analisis_json['resultados']) == 0:
            return "❌ Error: El JSON no contiene resultados de análisis"

        # Generar reporte según modo
        if mode == "simplificado":
            return generate_simplified_report(analisis_json)
        else:
            return generate_detailed_report(analisis_json)

    except FileNotFoundError:
        return f"❌ Error: No se encontró el archivo {analisis_json_path}"
    except json.JSONDecodeError:
        return "❌ Error: El archivo no es un JSON válido"
    except Exception as e:
        return f"❌ Error inesperado: {str(e)}"


# Testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Uso: python report_humanizer.py <ruta_json> [simplificado|detallado]")
        sys.exit(1)

    json_path = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "simplificado"

    print(f"\n🔄 Generando reporte {mode}...")
    reporte = humanize_report(json_path, mode)
    print(reporte)
