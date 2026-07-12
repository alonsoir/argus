# DEBT-FEATURE-EXTRACTOR-L1-BROKEN-001

**Severidad:** P0 — BLOQUEANTE. Por delante de `correlation_v2`, del grafo y de MITRE.
**Abierta:** DAY 216 (12 julio 2026)
**Estado:** ABIERTA — causa raíz PROBADA, reparación pendiente.
**Rama de descubrimiento:** `fix/verdict-multihead-honest`
**Relacionadas:** DEBT-VERDICT-MONOCAPA-001, DEBT-RANSOMWARE-ML-HEAD-INERT-001,
DEBT-CONFIG-L3-THRESHOLDS-UNPARSED-001, DEBT-VERDICT-WEIGHTS-CALIBRATION-001

---

## RESUMEN EN UNA FRASE

**El modelo L1 es perfecto sobre CIC-IDS2017 (200/200 DDoS, 0/200 FP). El pipeline en
ejecución no detecta NADA (0/100 ataques sintéticos). La brecha está en
`ml-detector/src/feature_extractor.cpp`: 6 de las 23 features que entrega al modelo
son incorrectas — duplicadas o constantes.**

No hay tres cabezas rotas. **Hay un extractor roto que rompe tres cabezas.**

---

## 1. LA PRUEBA — el modelo está sano

Ejecutado en el host (macOS), contra el ONNX de producción, con features REALES del
dataset de entrenamiento, en el orden del contrato `sniffer/config/features/rf_23_features.json`:

```
BENIGN : label=1 en   0/200   (0.0%)     → 0 falsos positivos
DDoS   : label=1 en 200/200   (100.0%)   → recall 1.000
```

**Sin escalar.** Consecuencias, todas cerradas con evidencia:

- ✅ **El contrato `rf_23_features.json` es CORRECTO.** Las 23 columnas existen en el CSV
  con esos nombres exactos (con espacios delante) y en ese orden.
- ✅ **NO hace falta scaler.** El `validation.scaler_required: true` de ese JSON es RUIDO
  (el `level1/scaler.json` que referencia NO EXISTE). Los árboles no necesitan escalado.
  Descartado con prueba, no con argumento.
- ✅ **El modelo tiene el F1=0.9968 que declara su metadata.** No miente.
- ⚠️ El ONNX es un `TreeEnsembleClassifier` ÚNICO, sin nodos `Scaler`/`Normalizer`.
  Verificado leyendo el grafo.

### Script de la prueba (REPRODUCIBLE EN FRÍO — no reconstruir, copiar)

```python
import pandas as pd, numpy as np, onnxruntime as ort, json

CSV = "ml-training/datasets/CIC-IDS-2017/MachineLearningCVE/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv"
spec = json.load(open("sniffer/config/features/rf_23_features.json"))
cols = [f["model_name"] for f in spec["features"]]   # orden del contrato, CON espacios

df = pd.read_csv(CSV)
df.columns = df.columns.str.replace('\ufeff','')
falta = [c for c in cols if c not in df.columns]
assert not falta, falta

lab = [c for c in df.columns if c.strip().lower()=="label"][0]
df = df.replace([np.inf,-np.inf], np.nan).dropna(subset=cols)

ben = df[df[lab].str.strip()=="BENIGN"].sample(200, random_state=42)
atk = df[df[lab].str.strip()!="BENIGN"].sample(200, random_state=42)

s = ort.InferenceSession("ml-detector/models/production/level1/level1_attack_detector.onnx")
out = [o.name for o in s.get_outputs()]
for nombre, sub in (("BENIGN", ben), ("DDoS  ", atk)):
    X = sub[cols].to_numpy(dtype=np.float32)
    labels = np.array(s.run(out, {"float_input": X})[0])
    n1 = int((labels==1).sum())
    print(f"  {nombre}: label=1 en {n1}/{len(sub)}  ({100*n1/len(sub):.1f}%)")
```

---

## 2. LOS DEFECTOS — 6 de 23 features, con `file:line`

`ml-detector/src/feature_extractor.cpp`, `extract_level1_features` (`:83–166`).
Contrato: `sniffer/config/features/rf_23_features.json`.

| idx | contrato (id · nombre) | código actual | defecto |
|---|---|---|---|
| `[1]`  | 2 · `Subflow Fwd Bytes`          | `total_forward_bytes()` (:101)   | 🔴 no es subflow; **duplica `[9]`** |
| `[8]`  | 9 · `act_data_pkt_fwd`           | `total_forward_packets()` (:123) | 🔴 no es lo mismo; **duplica `[15]`** |
| `[9]`  | 10 · `Total Length of Fwd Packets` | `total_forward_bytes()` (:126) | 🔴 misma fuente que `[1]` |
| `[14]` | 15 · `Init_Win_bytes_forward`    | **`0.0f`** (:142) — *"TODO: Añadir campo al protobuf si es crítico"* | 🔴 **CONSTANTE**. Valores reales: 8192/16384/65535 |
| `[15]` | 16 · `Subflow Fwd Packets`       | `total_forward_packets()` (:145) | 🔴 misma fuente que `[8]` |
| `[18]` | 19 · `Total Length of Bwd Packets` | `total_backward_bytes()` (:138 y :157) | 🔴 **duplicada consigo misma** |

Un árbol entrenado con `Init_Win_bytes_forward ∈ {8192, 16384, 65535}` que recibe `0.0`
cae **siempre** por la misma rama. Las duplicadas colapsan el espacio de decisión.
Resultado: **salida constante y confiada.**

### El comentario de `:142` es la confesión

`// TODO: Añadir campo al protobuf si es crítico`
**Alguien ya sabía que faltaba.** La pregunta abierta es si el protobuf tiene los campos
(`Init_Win_bytes_forward`, `Subflow Fwd Bytes`, `act_data_pkt_fwd`) o si hay que subir
al **sniffer** — cuyo extractor, según `rf_23_features.json:extraction_info`, sí produce
las 83 features de CIC-IDS2017. **El dato puede existir y estar perdiéndose en el camino.**

### DOS EXTRACTORES DISTINTOS — ojo con esto

- `sniffer/src/userspace/feature_extractor.cpp` → 83 features, L1 usa las 23 primeras.
  Es el que el contrato dice que existe (`extraction_info.code_location`).
- `ml-detector/src/feature_extractor.cpp` → reconstruye 23 desde el **protobuf**.
  **Es el que corre en producción. Es el roto.**

---

## 3. LAS MEDICIONES — 3 runs, instrumentación de 9 contadores

Parche: `docs/day216_instrumentation.patch` (NO commiteado, a fichero por decisión Alonso).
Contadores en `struct Stats` + `fprintf` a stderr por evento. Volcado cada `stats_interval`.

### Run 1 — injector BENIGN (`100 10`, ruido uniforme `rand_float(0,1)`)

```
l1_ran = 100   l1_class1 = 0     l1_gate_open = 0
traffic_ran = 100   traffic_class1 = 100   traffic_internal = 100  (GUARD)
internal_ran = 100  internal_class1 = 69   internal_sealed = 69
inference_errors = 0
```
Distribuciones: `L1 conf∈[0.74,0.88]` · `internal susp_prob∈{0.08–0.09} ∪ {0.72–0.85}` ·
`traffic internal_prob∈{0.955, 0.96, 0.97}`

### Run 2 — injector ATTACK (`100 10 --attack`, DDoS signature)

```
l1_ran = 100   l1_class1 = 0     l1_gate_open = 0     ← 100 ATAQUES, 0 DETECCIONES
traffic_ran = 100   traffic_class1 = 100   traffic_internal = 100
internal_ran = 100  internal_class1 = 0    internal_sealed = 0
```
Distribuciones: `L1 conf∈[0.83,0.86]` (¡más CONCENTRADA que en ruido!) ·
`internal susp_prob∈[0.097, 0.14]` · `traffic internal_prob∈{0.96, 0.965}`

### Run 3 — modelo ONNX directo con CIC-IDS2017 real
Ver §1. **200/200 DDoS detectados.**

### Lectura por cabeza

| cabeza | ruido | ataque | veredicto |
|---|---|---|---|
| **L1**       | class1=0, conf 0.85 | class1=0, conf 0.85 | 🔴 **CONSTANTE.** No reacciona. |
| **internal** | class1=69 (0.72–0.85) | class1=0 (0.097–0.14) | 🔴 **INVERTIDA.** Dispara en ruido, calla en ataque. |
| **traffic**  | 100/100, σ≈0.005 | 100/100, σ≈0.003 | 🔴 **CONSTANTE.** 0.96±0.005 en 200 eventos de poblaciones opuestas. |

**Las tres fallan a la vez, y una está invertida. Firma de causa común aguas arriba.**

---

## 4. CONSECUENCIAS EN CASCADA

### a) La deuda 3 de DAY 215 queda CERRADA — con la respuesta incómoda
`SUSPICIOUS_INTERNAL = 0 sellados` **NO era un bug del veredicto**. El gate L1 nunca se
abrió porque **L1 no clasifica NADA como ATTACK**. Y los 69 sellados de `internal` en el
run de ruido eran **69 falsos positivos**.

### b) El `internal_l1_discrepancies` de DAY 212 medía FALSOS POSITIVOS
Lo llamamos "hueco de cobertura L3". Era `internal` disparando sobre ruido. **El contador
medía el fenómeno correcto con el nombre equivocado.**

### c) El GATE L1 no es un vestigio — y es su primera medida
Posición DAY 215: *"el gate es una optimización prematura, un vestigio"*.
**Primera medida: el gate filtró 69 falsos positivos.** Evidencia EN CONTRA de retirarlo.
No concluyente (el set es ruido, no tráfico real), pero es lo que hay.
⟹ *El verde hay que interrogarlo. También el rojo.*

### d) DEBT-VERDICT-WEIGHTS-CALIBRATION-001 es INDECIDIBLE hoy
Con las tres cabezas sin señal, `reliability` para las tres es **0.0**, no "pendiente de
calibrar". Un noisy-OR de todo ceros es `P = 0`. **No falta el instrumento de calibración:
no hay nada que calibrar hasta arreglar el extractor.**

### e) COMMIT 2 (noisy-OR) SE APARCA — no se pierde
El stash `stash@{0}: commit2-noisy-or WIP` (header + tests, validados con
`g++ -std=c++20 -Wall -Wextra -Werror`) **sigue siendo válido y valioso**. Combinar
señales de cabezas que no llevan señal es andamiaje sin edificio. Se retoma **cuando las
cabezas discriminen**.

---

## 5. EL PAPER — arXiv:2604.04952

**El paper reporta F1=0.9985 / Recall=1.000 para aRGus NDR.** Esos números salen de
evaluar **el modelo** contra el dataset — y son CIERTOS: acabamos de reproducirlos
(200/200). **Pero el pipeline en ejecución no los reproduce.**

Es la brecha entre *"el modelo detecta"* y *"el sistema detecta"*.

**Esa distinción hay que hacerla en el paper.** Un revisor de Cornell que descubra la
brecha por su cuenta hunde el trabajo; el autor que la mide, la localiza, la publica y la
arregla **demuestra exactamente lo que el paper afirma sobre método**.

Encaja con el hallazgo del config (DAY 215) en el mismo hilo de §6: **es el segundo caso
de "pipeline funcionando, produciendo números, sin significado"**, y el tercero contando
el `entropy` del ransomware. Tres instancias del mismo patrón ⟹ **no es mala suerte, es
una clase de defecto** que el testing convencional no captura. Ese es el argumento del
paper, y ahora tiene tres casos con `file:line`.

---

## 6. HOJA DE RUTA — reparación

1. **Auditar el protobuf**: ¿existen `Init_Win_bytes_forward`, `Subflow Fwd Bytes`,
   `act_data_pkt_fwd`? Si NO → subir al sniffer (que sí produce 83 features).
2. **Reparar las 6 features** de `extract_level1_features`, una a una, contra el contrato.
3. **Test de PROPIEDAD, no de espejo** (lección DAY 215): *"las 23 features que el
   extractor entrega, alimentadas al ONNX, reproducen la clasificación del CSV"*.
   Golden set: N filas de CIC-IDS2017 → protobuf → extractor → ONNX → label esperado.
   **RED→GREEN obligatorio**: romper una feature a propósito debe ponerlo ROJO.
4. **Repetir el ejercicio con `traffic` e `internal`** (contratos: `internal_4_features.json`
   NO EXISTE — sólo aparecen `rf_23_features.json` y `ransomware_20_features.json` en
   `sniffer/config/features/`. Los `*_metadata.json` de `ml-detector/models/metadata/`
   están **TODOS a 0 bytes**, igual que `ml-detector/config/feature_mapping.json`).
5. **Sólo entonces**: calibrar pesos, retomar commit 2, seguir aguas abajo.

---

## 7. DEUDAS MENORES ABIERTAS HOY

- **DEBT-STATS-E2E-COUNTERS-001**: `check_e2e_pipeline.py` reporta
  `ml-detector: received 0 → 0` mientras los `dbg_*` cuentan 100 eventos procesados.
  **Los contadores del snapshot mienten.** Bug menor, no bloquea.
- **`ml-detector/config/feature_mapping.json` está VACÍO** (0 bytes). Igual que los 5
  ficheros de `ml-detector/models/metadata/`. Toda la capa de metadatos son placeholders
  del 27 de mayo que nunca se rellenaron.
- **`rf_23_features.json` se contradice a sí mismo**: `usage_notes.normalization` dice que
  NO hace falta escalar; `validation.scaler_required` dice `true`. Y su `_source` confiesa:
  *"Reconstructed from ... and feature_extractor.cpp"* — **se documentó leyendo el código
  que debía validar**. Circular. (La prueba de §1 resuelve la contradicción: NO hace falta.)

---

## MÉTODO — lo que funcionó hoy

- **El contador que separa hipótesis vale más que el que cuenta.** `dbg_l1_class1` vs
  `dbg_l1_gate_open`: sin los dos, "el gate no se abre" y "L1 no detecta" son
  indistinguibles. Son diagnósticos opuestos.
- **La tabla de lectura se escribe ANTES de ver el número.** Elimina el margen para
  interpretar a conveniencia.
- **Verificar el `.cpp`, no el comentario.** `traffic_detector.hpp:48` dice
  `// Probability of predicted class`; hubo que ir a `traffic_detector.cpp:33-39` para
  confirmarlo. Dos veces esta sesión el comentario decía verdad; una vez (el contrato del
  scaler) mentía.
- **Ir al artefacto que no puede mentir.** Metadata vacía, contrato circular, comentarios
  ambiguos → se leyó **el grafo del ONNX** y **el CSV de entrenamiento**. Fin de la discusión.
- **Corregir el relato cuando el dato lo contradice.** El prompt de DAY 215 afirmaba
  *"`is_internal(0.0f)` → SIEMPRE true, TODO flujo era interno"*. **Es FALSO**:
  `traffic_detector.hpp:57` es `class_id == 1 && probability >= threshold` — el `&&` de
  clase siguió aplicándose. Lo que se perdió fue el **suelo de confianza**, no el guard.
  Corregir ANTES de escribirlo en el paper.