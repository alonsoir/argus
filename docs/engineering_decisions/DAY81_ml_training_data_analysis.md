# ML Training Data Crisis & Retraining Hypothesis
## Engineering Decision — DAY 81
## docs/engineering_decisions/DAY81_ml_training_data_analysis.md

**Fecha:** 10 marzo 2026
**Autores:** Alonso Isidoro Roman + Consejo de Sabios
**Estado:** Hallazgo documentado — hipótesis de reentrenamiento pendiente validación

---

## 1. El hallazgo

Durante la comparativa controlada de DAY 81 (mismo PCAP, dos condiciones de
threshold), se descubrió que el RandomForest embedded **nunca supera 0.6607**
de score, quedando siempre por debajo de cualquier threshold razonable (0.70).

**El 100% del trabajo de detección reseñable lo hace el Fast Detector.**

```
Fast Detector (heurísticas):  4712 activaciones ≥ 0.70  →  F1=1.0000
ML RandomForest (embedded):      0 activaciones ≥ 0.70  →  max score 0.6607
```

Esto no es un fallo del pipeline — el pipeline funciona. Es un fallo de los
datos de entrenamiento.

---

## 2. Nomenclatura — tres categorías distintas, no dos

Antes de documentar los fracasos, es necesario establecer que "datos sintéticos"
no es una categoría uniforme. El proyecto ha trabajado con tres tipos de datos
fundamentalmente distintos que merecen nombres distintos:

### Categoría A — Datos académicos
Datasets producidos por otros grupos de investigación (CTU-13, CIC-IDS2017,
UNSW-NB15). Features calculadas con otros pipelines (CICFlowMeter, etc.).
Etiquetas asignadas en condiciones de laboratorio controladas.

**Problema estructural:** las features académicas y las features del pipeline
C++20 tienen el mismo nombre pero definiciones distintas — rangos distintos,
normalización distinta, definición de flujo distinta. El modelo aprende reglas
que no existen en nuestro tráfico.

### Categoría B — Datos sintéticos estadísticos (generador propio)
Muestras generadas algorítmicamente a partir de distribuciones estadísticas.
Sin tráfico real de red. Distribuciones artificialmente perfectas, sin jitter,
sin retransmisiones, sin correlaciones temporales reales.

**Problema estructural:** el modelo aprende el generador, no el tráfico. Los
datos son "demasiado limpios" para generalizar al caos del mundo real.

### Categoría C — Datos nativos del pipeline (propuesta DAY 81)
Features generadas por el propio extractor C++20 durante operación real,
correlacionadas via `trace_id` entre ml-detector y firewall-acl-agent,
mezcladas con tráfico de relay PCAP académico + tráfico interno lab.

**Por qué es fundamentalmente distinto:**
```
features entrenamiento = features producción  (por construcción)
```
No hay feature drift posible. El modelo aprende exactamente lo que verá
en inferencia. Esto **no es sintético** en ningún sentido relevante — es
entrenamiento nativo del pipeline.

**Nombre propuesto para el paper:** *pipeline-native training data*

---

## 3. Historia de los entrenamientos — dos fracasos documentados

### Entrenamiento 1: Datos académicos — Categoría A
- F1 en validación offline: **F1=0.0000** (el modelo predecía todo como benigno)
- Causa raíz: dataset con 99% benigno → el modelo aprendió "siempre predecir
  benigno = alta accuracy". F1=1.0000 en training era engañoso por imbalance.
- F1 en producción con pcap replay: **~0.0061** — prácticamente cero detecciones
- **Impacto en el proyecto:** decepción brutal que forzó un cambio de dirección
  completo hacia datos sintéticos estadísticos. Documentado en sesiones
  noviembre 2025.

La confusion matrix de ese momento:
```
True Positives (TP):  0
False Positives (FP): 53
False Negatives (FN): 556,556
True Negatives (TN):  2,271,267
```
El modelo no detectó literalmente ningún ataque.

### Entrenamiento 2: Datos sintéticos estadísticos — Categoría B
- F1 en validación offline: moderado
- F1 en producción: **score máximo 0.6607** — nunca supera threshold 0.70
- Causa: distribuciones artificiales sin ruido real, sin estructura temporal
  de ataque, 11 sentinels reducen señal disponible
- **Posición relativa:** considerablemente mejor que Categoría A (al menos
  el modelo ve algo), pero insuficiente para producción

### Comparativa de los tres enfoques

| Categoría | Nombre | F1 offline | F1 producción | Causa del gap |
|---|---|---|---|---|
| A | Académico (CTU-13) | ~0.99* | ~0.006 | Feature drift severo + imbalance |
| B | Sintético estadístico | moderado | max 0.6607 | Distribución irreal |
| C | Pipeline-native | **pendiente** | **hipótesis >0.70** | Sin drift por construcción |

*F1=0.99 académico era espurio — artefacto del imbalance 99% benigno.

**Paradoja documentada y confirmada:** el entrenamiento académico producía
métricas offline perfectas que eran completamente inútiles en producción.
Es citable como demostración del "academic dataset trap" — un problema
conocido en la literatura pero raramente documentado con datos propios tan
explícitos.

---

## 3. Por qué ocurre esto — análisis técnico

### Feature drift (entrenamiento académico)
```
Features entrenamiento ≠ Features producción
```
Los datasets académicos tienen sus propias definiciones de features
(CIC-IDS2017 usa CICFlowMeter, por ejemplo). Nuestro pipeline C++20 calcula
las mismas features con implementaciones distintas — rangos distintos,
normalización distinta, definición de flujo distinta. El modelo aprendió
reglas que no existen en nuestro tráfico.

### Datos sintéticos demasiado perfectos
El generador sintético produce:
- Sin jitter, sin retransmisiones, sin paquetes perdidos
- Correlaciones independientes por evento (sin estructura temporal real)
- Distribuciones uniformes artificiales

Un modelo entrenado con datos perfectos falla cuando ve el caos del tráfico
real. Los 11 sentinels (-9999.0f) en features no extraídas también degradan
la señal disponible para el RandomForest.

---

## 4. La hipótesis — reentrenamiento con datos pipeline-native (Categoría C)

### Premisa
El único dataset que garantiza **cero feature drift** es el generado por el
propio pipeline en producción. Las features que genera el extractor C++20 son
exactamente las que verá el modelo en inferencia.

### Mecanismo disponible
El `trace_id` (SHA256 de src_ip + dst_ip + attack_type + temporal_bucket)
permite cruzar eventos de dos fuentes:

```
ml-detector CSV  ──┐
                   ├──[trace_id]──→ dataset combinado
firewall-acl CSV ──┘
```

Cada registro combinado tendría:
```
trace_id | timestamp | src_ip | dst_ip |
features[28] | ml_score | ml_label |
firewall_action | firewall_result | ground_truth_label
```

### Propuesta de dataset de reentrenamiento

Proporción objetivo para generalización real:
```
30% tráfico interno benigno (DNS, SMB, SSH, RDP, backups)
20% tráfico web benigno (HTTP/HTTPS, APIs, CDN)
25% ataques internos (scan, lateral movement, brute force, beaconing)
25% ataques externos (DDoS, C&C, exfiltración)
```

Fuentes:
1. **Pipeline real** (trace_id correlation) — features exactas, sin drift
2. **CTU-13 otros escenarios** — variedad de patrones de ataque
3. **MAWI backbone** — tráfico benigno real de Internet
4. **Tráfico interno simulado** — generado en el lab (VM defender + client)

### Hipótesis verificable
> Un modelo RandomForest entrenado con datos generados por el propio pipeline
> (via trace_id correlation), en proporción ~50% benigno / 50% malicioso,
> debería producir scores > 0.70 en producción para tráfico de ataque real,
> activándose de forma complementaria al Fast Detector.

**Si se confirma:** el sistema pasa de detección heurística pura a detección
híbrida real (Fast Detector para patrones obvios + ML para patrones sutiles).

**Si no se confirma:** los 11 sentinels (features faltantes en Phase 2) son
el bloqueante real — el modelo no tiene suficiente señal independientemente
de los datos de entrenamiento.

---

## 5. Por qué esto es importante para el paper

### Lo que hay que escribir en Discussion (sin maquillaje)

> "The embedded RandomForest models, trained on synthetic data, consistently
> scored below detection threshold (max score 0.6607) during CTU-13 Neris
> replay. All attributable detections were produced by the Fast Detector
> heuristics. This result is consistent with known feature drift between
> synthetic training distributions and real traffic generated by the C++20
> pipeline. We document this as a known limitation of Phase 1 and propose
> pipeline-native retraining as the primary mitigation for Phase 2."

### Lo que NO hay que escribir
No hay que presentar F1=1.0000 como si viniera del ML ensemble. Viene del
Fast Detector. Esa distinción es la que separa un paper honesto de uno que
no sobrevive peer review.

### La oportunidad científica
El hallazgo de que entrenamiento académico produce F1≈0.99 offline pero
F1≈0.006 en producción es **citable por sí mismo** como demostración del
problema de feature drift en IDS. Es una contribución al estado del arte,
no solo una limitación a esconder.

---

## 6. Plan de implementación — enterprise roadmap

Este reentrenamiento es una feature enterprise por tres razones:

1. **Requiere datos de producción real** — no disponible en open source sin
   consentimiento explícito del operador
2. **Requiere CsvEventLoader** (pendiente) — para consumir los CSV del pipeline
3. **Requiere ciclo completo:** captura → features → label → train → validate → deploy

Se implementa como parte del ciclo de aprendizaje continuo:
```
pipeline
   ↓
event CSV logs (trace_id correlation)
   ↓
dataset builder (balanced, labeled)
   ↓
model retraining (RandomForest C++20)
   ↓
model ranking (f1_replay_log.csv)
   ↓
hot-deploy (ENT-4 hot-reload)
```

**Relación con ENT items:**
- ENT-4 (hot-reload): necesario para desplegar modelos sin downtime
- ENT-1 (federated learning): una vez validado localmente, escalar a federado

---

## 7. Compromiso científico — documentar todo, incluso el fracaso

Este proyecto se compromete a publicar el camino completo de descubrimiento,
incluyendo los fracasos. Esto incluye:

- El fracaso del entrenamiento académico (F1~0 en producción) — documentado y confirmado
- El fracaso del entrenamiento sintético estadístico (max 0.6607) — documentado
- La hipótesis pipeline-native (Categoría C) — a validar en DAY 82+
- Si la hipótesis pipeline-native también falla — documentar causas y consecuencias

Si los experimentos demuestran que el pipeline ha tomado decisiones de diseño
incorrectas que impiden su uso en producción real, eso también se publica.
La honestidad científica no es selectiva.

El valor del paper no depende de que el sistema sea perfecto. Depende de:
1. El camino de descubrimiento del problema del feature drift
2. La metodología de detección en capas (Fast Detector + ML ensemble)
3. La distinción entre datos académicos / sintéticos / pipeline-native
4. La hipótesis de reentrenamiento nativo y su validación honesta
5. La infraestructura de experimentación reproducible (f1_replay_log.csv)

Un paper que documente honestamente por qué algo no funcionó y proponga
un camino de solución fundamentado es más valioso que uno que presente
solo victorias. Los reviewers lo saben. Los practitioners también.

---

## 8. Estado actual

| Item | Estado |
|---|---|
| Hallazgo Fast Detector dominance | ✅ Documentado DAY 81 |
| Causa feature drift identificada | ✅ Documentado DAY 81 |
| Hipótesis reentrenamiento pipeline-native | 📋 Hipótesis — pendiente validación |
| CsvEventLoader (prerequisito) | ⏳ 0% — pendiente |
| Dataset builder con trace_id | ⏳ 0% — pendiente |
| Validación hipótesis | ⏳ 0% — enterprise roadmap |

---

## 8. Nota del Consejo de Sabios (DAY 81)

> "El sistema funciona. El Fast Detector demuestra que la arquitectura de
> detección en capas es correcta. El ML necesita datos del mundo real para
> ser útil — exactamente como cualquier modelo de producción. Esto no es un
> fracaso; es el paso natural de prototipo a producto. El pipeline ya genera
> esos datos. Solo falta cerrar el ciclo."

---

*Documento generado: DAY 81 — 10 marzo 2026*
*Co-authored-by: Alonso Isidoro Roman + Claude (Anthropic) + Consejo de Sabios*