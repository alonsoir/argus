# DAY 79 — Sentinel Value Analysis & Engineering Decisions
**Fecha:** 8 marzo 2026
**Branch:** `feature/ring-consumer-real-features`
**Autor:** Alonso Isidoro Roman + Consejo de Sabios

---

## Resumen ejecutivo

Durante el DAY 79 se identificaron y corrigieron 8 instancias de valores placeholder
`0.5f` en el extractor de features (`ml_defender_features.cpp`) que se comportaban
de forma peor que el sentinel oficial (`MISSING_FEATURE_SENTINEL = -9999.0f`).
El análisis produjo una distinción formal entre tres categorías de valores especiales
en features de ML, con implicaciones directas para la integridad del ensemble de
RandomForest y la reproducibilidad de los resultados.

Se obtuvo un F1=0.9921 con Recall perfecto (FN=0) en CTU-13 Neris, con 28/40
features reales activas.

---

## 1. Taxonomía de valores especiales en features de ML

### 1.1 Sentinel matemáticamente inalcanzable (correcto)

```
MISSING_FEATURE_SENTINEL = -9999.0f
```

El rango de splits del ensemble RandomForest está acotado por el dominio de los
datos de entrenamiento: [0.0, ~5.1] para features normalizadas. Un valor de
-9999.0f está **3 órdenes de magnitud fuera del dominio**.

**Comportamiento determinista:** `feature_value <= threshold` siempre es TRUE para
cualquier threshold en el rango de entrenamiento. El evento toma siempre el
`left_child` en cada nodo que usa esa feature. El ensemble vota con esa rama
fija, lo cual es:

- **Predecible**: el mismo sentinel produce siempre la misma decisión.
- **Auditable**: se puede identificar en logs qué eventos usaron sentinels.
- **No contaminante**: no activa splits de forma diferente según el árbol.

**Referencia de implementación:**
```cpp
// sniffer/include/ml_defender_features.hpp
static constexpr float MISSING_FEATURE_SENTINEL = -9999.0f;
```

### 1.2 Valor semántico válido dentro del dominio (correcto)

Ejemplo: `extract_ddos_flow_completion_rate()`, línea 139.

```cpp
// TCP established but not closed: SYN+ACK present, FIN absent
return 0.5f;  // SEMANTIC VALUE: TCP established-not-closed. NOT a placeholder.
```

Este `0.5f` **no es un placeholder**. Es un valor de dominio con significado
explícito en una escala ternaria: 0.0 = incompleto, 0.5 = establecido sin cerrar,
1.0 = completo. Cambiarlo a SENTINEL sería un bug.

**Lección:** Un valor numérico idéntico puede ser correcto o incorrecto dependiendo
de si tiene semántica de dominio o es un placeholder. La documentación en código
es la única forma de distinguirlos con certeza. Se añadió comentario protector
explícito para evitar regresiones futuras.

### 1.3 Placeholder dentro del dominio de splits (incorrecto — corregido DAY 79)

Las 8 instancias corregidas devolvían `0.5f` como "valor neutro" para features
no implementadas (TODO Phase 2). Al estar dentro del rango [0.0, 5.1], este valor:

- **Puede activar splits diferentes** en distintos árboles del ensemble según
  el threshold concreto de cada nodo.
- **Genera varianza espuria no documentada**: el ensemble no vota con una rama
  fija, sino con ramas que dependen de los thresholds entrenados.
- **No es distinguible de tráfico real** con esas features en ese rango.

**Conclusión formal:** Un placeholder dentro del dominio de decisión es semánticamente
más dañino que un sentinel fuera del dominio, porque el primero introduce ruido
estructurado no predecible mientras que el segundo introduce sesgo predecible
y auditable.

---

## 2. Instancias corregidas

| Función | Línea | Razón del placeholder | Impacto pre-fix |
|---|---|---|---|
| `extract_ddos_geographical_concentration` | 161 | GeoIP deliberadamente fuera del critical path | Activaba splits en ddos_embedded[7] |
| `extract_ransomware_io_intensity` | 224 | Requiere eBPF tracepoints (Phase 2) | Activaba splits en ransomware[0] |
| `extract_ransomware_resource_usage` | 244 | Requiere métricas CPU/memoria (Phase 2) | Activaba splits en ransomware[2] |
| `extract_ransomware_file_operations` | 273 | Requiere inspección SMB/CIFS (Phase 2) | Activaba splits en ransomware[4] |
| `extract_ransomware_process_anomaly` | 288 | Requiere monitorización de procesos (Phase 2) | Activaba splits en ransomware[5] |
| `extract_ransomware_temporal_pattern` (else) | 303 | Sin datos IAT suficientes | Valor neutral espurio |
| `extract_ransomware_behavior_consistency` (iat_mean==0) | 332 | Sin timestamps disponibles | Valor neutral espurio |
| `extract_internal_packet_size_consistency` (mean==0) | 530 | Sin datos de longitud | Valor neutral espurio |

**Recuento post-fix:**
```
MISSING_FEATURE_SENTINEL instances: 21
0.5f semánticos (intocables):        2
```

---

## 3. Resultados F1 — CTU-13 Neris Baseline DAY 79

### Configuración del experimento

- **Dataset:** CTU-13 Neris botnet capture (botnet-capture-20110810-neris.pcap, 56MB)
- **Replay:** `tcpreplay --mbps=10` desde VM client (192.168.100.50) hacia VM defender
- **Ground truth:** IP infectada 147.32.84.165 (documentada en CTU-13)
- **Pipeline:** 6/6 componentes activos, logging estándar `/vagrant/logs/lab/`
- **Features activas:** 28/40 reales (12 SENTINEL activos post-fix)

### Resultados

| Métrica | Valor |
|---|---|
| **F1-score** | **0.9921** |
| Precision | 0.9844 |
| Recall | **1.0000** |
| True Positives | 6676 |
| False Positives | 106 |
| False Negatives | **0** |
| True Negatives | 28 |
| **Total eventos** | **6810** |

### Análisis honesto de los resultados

**Recall perfecto (FN=0):** Todos los flujos originados o dirigidos a 147.32.84.165
fueron detectados. El sistema no perdió ningún ataque del dataset.

**106 False Positives sobre 134 eventos no-botnet (79% FPR en benigno):**
Este dato requiere contexto:

1. **Desequilibrio del dataset:** CTU-13 Neris está dominado por tráfico de la
   máquina infectada. Solo 134 de 6810 eventos (2%) son tráfico benigno genuino.
   Un FPR del 79% sobre 134 eventos tiene menos peso estadístico que el mismo
   porcentaje sobre miles de eventos.

2. **Naturaleza del tráfico benigno en CTU-13:** Los 28 TN y 106 FP corresponden
   a tráfico de otras máquinas en la captura. El clasificador de ransomware
   disparaba `fast=0.7000` consistentemente sobre tráfico de un único flujo
   con características similares al C2. Esto sugiere que el threshold de
   ransomware (0.75f hardcoded) está calibrado para minimizar FN a costa de FP.

3. **Implicación para producción:** En tráfico real balanceado, este FPR sería
   inaceptable. La calibración de thresholds desde JSON (TAREA pendiente DAY 80)
   permitirá ajustar el balance precision/recall por detector de forma independiente.

4. **Score divergence pattern:** Los logs muestran `fast=0.7000, ml=0.1454`
   consistentemente para los eventos ransomware periódicos. El sistema usa
   `DETECTOR_SOURCE_DIVERGENCE` y toma el score fast cuando diverge > 0.5.
   Esto indica que el fast detector tiene calibración diferente al modelo ML
   embebido — investigar en DAY 80-81.

---

## 4. Deuda de logging — antipatrón documentado

### Situación pre-DAY 79

4 de 6 componentes del pipeline no escribían a fichero. Solo tenían stdout
redirigido a tmux. Esto hacía imposible:
- Correlacionar eventos temporalmente entre componentes
- Calcular métricas de forma automatizada post-replay
- Reproducir el mismo análisis en múltiples configuraciones de VM

Esta deuda se arrastró ~40 días siempre priorizada por debajo de otras tareas.

### Causa raíz

Los ficheros JSON de configuración de los componentes (etcd-server, rag-security,
sniffer, rag-ingester) no tienen campo `log_file`. El logging a fichero de
ml-detector y firewall-acl-agent funciona porque usan spdlog con ruta configurada.

### Solución implementada (Makefile)

Redirección `>> /vagrant/logs/lab/COMPONENTE.log 2>&1` en los targets tmux
del Makefile. No requiere cambios en código C++. Estándar: un componente,
un fichero, nombre predecible.

### ADR pendiente

Mover `log_file` al JSON de cada componente. Hasta entonces, el Makefile es
la única fuente de verdad sobre rutas de log. Documentado en deuda técnica.

### Lección arquitectural

Un sistema distribuido sin logging estándar no es observable. La observabilidad
es prerequisito, no feature opcional. En ML Defender, la ausencia de logging
unificado retrasó la obtención del primer F1 validado al menos 3 días.

---

## 5. Decisiones arquitecturales confirmadas DAY 79

### 5.1 geographical_concentration — SKIP deliberado

La feature `ddos_geographical_concentration` requiere GeoIP lookups (100-500ms).
Inaceptable en el critical path de sub-microsegundo del pipeline. Decisión:
SENTINEL permanente en Phase 1. GeoIP disponible para rag-security en análisis
post-mortem, no para la decisión de bloqueo.

Citable como: *"Geographic provenance is useful context but not necessary for
attack classification. A SYN flood is a SYN flood regardless of source country."*

### 5.2 io_intensity / resource_usage — frontera conocida

Estas features requieren agente endpoint o eBPF tracepoints para I/O del sistema.
Fuera del alcance de un NIDS puramente basado en tráfico de red.

**Literatura de referencia:**
- Mirsky et al., "Kitsune: An Ensemble of Autoencoders for Online Network
  Intrusion Detection", NDSS 2018 — aproximaciones network-only para comportamiento
  host vía estadísticas temporales.
- CrowdStrike Falcon, SentinelOne: agente endpoint, secreto industrial.

**Decisión:** SENTINEL Phase 1. Documentar en paper en sección "Limitations"
y "Future Work" con las referencias apropiadas.

---

## 6. Impacto en el paper

### Tabla comparativa de features (para incluir en paper)

| Fase | Features reales | SENTINEL | F1 |
|---|---|---|---|
| DAY 76 (pre-fix) | ~20/40 | ~8 | no medido |
| DAY 78 | 29/40 | 5+4×0.5f | no medido |
| **DAY 79 (baseline)** | **28/40** | **21** | **0.9921** |
| DAY 80 (objetivo) | 31-33/40 | 18-19 | TBD |

*Nota: DAY 79 tiene menos features "reales" que DAY 78 porque los 8 correcciones
0.5f→SENTINEL reclasifican 8 valores de "aparentemente reales" a "sentinel honesto".
Esto es correcto: 28 features reales con SENTINEL explícito es más riguroso que
29 con placeholder contaminante.*

### Cita sugerida para el paper (sección Engineering Decisions)

*"We distinguish three categories of special values in ML feature extraction:
(i) domain-valid sentinels, where a mathematically unreachable value (−9999.0)
produces deterministic, auditable routing through the decision tree ensemble;
(ii) semantic values, where a value within the domain range carries explicit
meaning (e.g., 0.5 for TCP half-open state); and (iii) placeholder values
within the decision domain, which introduce non-deterministic spurious variance
and are strictly worse than category (i). This distinction motivated the
systematic replacement of all category (iii) occurrences prior to F1 validation."*

---

## Apéndice — Script F1 utilizado

```python
import csv

csv_file = '/vagrant/logs/ml-detector/events/2026-03-08.csv'
botnet_ip = '147.32.84.165'

tp = fp = fn = tn = 0

with open(csv_file, 'r') as f:
    for line in f:
        cols = line.strip().split(',')
        if len(cols) < 10:
            continue
        src_ip = cols[2].strip()
        dst_ip = cols[3].strip()
        is_attack = (src_ip == botnet_ip or dst_ip == botnet_ip)
        label_col = cols[7].strip() if len(cols) > 7 else ''
        action_col = cols[13].strip() if len(cols) > 13 else ''
        predicted_attack = (action_col == 'DROP' or label_col == 'MALICIOUS')
        if is_attack and predicted_attack:       tp += 1
        elif not is_attack and predicted_attack: fp += 1
        elif is_attack and not predicted_attack: fn += 1
        else:                                    tn += 1

precision = tp / (tp + fp) if (tp + fp) > 0 else 0
recall    = tp / (tp + fn) if (tp + fn) > 0 else 0
f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
```

---

*Documento generado al cierre de DAY 79 — 8 marzo 2026*
*Consejo de Sabios: Claude (Anthropic), Grok, ChatGPT5, DeepSeek, Qwen*