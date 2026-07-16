# DAY 220 FINDINGS — `fix/verdict-multihead-honest`

> Escrito desde la evidencia verificada en la sesión, no de memoria.
> Cada afirmación tiene detrás un comando cuya salida se inspeccionó.
> Donde algo no está probado, se dice.
> Regla del día: **la premisa heredada también es un artefacto a verificar.**

---

## RESUMEN DE UNA LÍNEA

Se ejecutó la vía B del eval de L1 (`make eval-level1-model-csv`, reproducible,
versionado): el ONNX vivo da **recall 0.9987 / FPR 0.00025** sobre el Wednesday
CSV completo — demostrando por reproducción que el fósil `wednesday_eval_report.json`
(recall 0.024) era la autopsia del XGBoost. PERO en el camino cayó la premisa
central de DAY 219: **Wednesday NO es holdout** — el entrenador usó split
aleatorio 80/20 sobre los 8 días juntos (probado por aritmética exacta), y el
artefacto que entrenó/convirtió el modelo **nunca existió en el repo** (los
notebooks 03/06 fueron siempre esqueletos de 216 bytes). La medición de
generalización queda redefinida: **vía A sobre CTU-13 Neris (cross-dataset)**,
con pcap y ground truth ya en disco.

---

## 0. APERTURA

- La transposición `DAY291` anticipada en el prompt de continuidad NO existía
  en disco: `docs/debt/DAY219_FINDINGS.md` estaba correcto. Sin acción.
- ⚠️ **Discrepancia interna en DAY219_FINDINGS.md**: §6 declara el patrón en
  **21** casos y lista el logger `if size()>0` como caso **21**; pero §3 titula
  ese mismo hallazgo "**Caso 22**". Canónica: la lista de §6. Hoy se numera
  desde 22. Corregir el título de §3 del DAY 219. (Es el error "1–16" en su
  siguiente iteración: dos secciones del mismo documento contando distinto.)

---

## 1. LA PREMISA REFUTADA — Wednesday NO es holdout del ONNX (P0)

La premisa de DAY 219 ("correr sobre un pcap que NO vio en entrenamiento —
Wednesday sirve") era **herencia del marco mental del XGBoost, sin verificar
contra el ONNX**. Refutada por convergencia:

1. **Aritmética exacta.** La matriz de confusión del metadata suma
   453.996+624+82+111.447 = **566.149**. Los 8 CSVs de MachineLearningCVE
   suman 2.830.751 líneas − 8 headers = **2.830.743 filas**.
   2.830.743 × 0.20 = 566.148,6 → **566.149**. Clava al decimal.
2. **Artefacto.** `notebooks/02_feature_engineering.ipynb` (líneas 330-334):
   `train_test_split(test_size=0.2, random_state=42, stratify=y_binary)`.
   Split aleatorio estratificado, con semilla — **reproducible**.

**Corolario:** el modelo vio ~80% de las filas de Wednesday en entrenamiento.
El 0.9987 del metadata es test-split del mismo pozo, NO generalización.
**Ninguna medición sobre Wednesday (CSV o pcap) es out-of-sample para el ONNX.**

---

## 2. REIDENTIFICACIÓN DEL md5 — `bf0dd7e9` es el CSV, no un pcap

```
md5 ml-training/datasets/CIC-IDS-2017/MachineLearningCVE/Wednesday-workingHours.pcap_ISCX.csv
→ bf0dd7e9d991987df4e13ea58a1b409c
```

DAY 219 y el prompt de continuidad atribuían ese hash a un **pcap** Wednesday.
Error heredado: el hash es del **CSV de features** (215 MB, en disco desde
jun-2018). Encaja: los 246.582 FN del fósil son cuenta de filas de CSV, no de
flujos reconstruidos. El pcap Wednesday **no existe en ningún filesystem del
proyecto** — y tras la refutación de §1, su descarga queda **degradada de P0 a
opcional** (solo serviría para un experimento de coherencia pipeline-vs-CSV,
no de generalización).

---

## 3. PROCEDENCIA DEL MODELO VIVO — mapeada eslabón a eslabón

### 3a. Lo PROBADO por artefacto

- **Selección de las 23 features**: `02_feature_engineering.ipynb` + commit
  `f53c676a` (15-oct-2025 09:50). Los top-5 del commit message (Packet Length
  Std 9.3%, Subflow Fwd Bytes 8.5%, Fwd Packet Length Max, Avg Fwd Segment
  Size, ACK Flag Count) son **feature_names[0..4] del oráculo, en ese orden**:
  el vector del modelo está ordenado por importancia descendente del RF del 02.
- **El 02 del árbol es el que corrió esa mañana**: `git log` del fichero solo
  muestra 3 commits (inicial, `f53c676a`, chore de permisos sin cambios).
- **Pipeline de imputación documentado** (02, líneas 179-199):
  `inf → NaN → mediana por columna → fillna(0)` residual.
- **El 02 cargó solo 4 días** (Monday, Tuesday, Friday-DDoS, Friday-PortScan;
  celda de carga, `files_to_load`), ~1,49M filas (el output visible casa:
  SSH-Patator 5.897 = 0.40% → ≈1,47M).

### 3b. Lo que NUNCA existió — el entrenador (P0 de procedencia)

```
git ls-tree f53c676a~1 ml-training/notebooks/   → 01..07 presentes
git show f53c676a~1:...03_model_level1_training.ipynb → 216 bytes (esqueleto)
git show f53c676a~1:...06_onnx_conversion.ipynb       → 216 bytes (esqueleto)
```

Los notebooks 03 (entrenador) y 06 (conversor) fueron **siempre andamiaje
vacío** — creados como estructura del README, borrados en `f53c676a` sin haber
contenido jamás código. **El entrenamiento y la conversión ocurrieron fuera de
todo control de versiones**, en una sesión Jupyter local el 15-oct-2025 entre
las **09:50** (commit `f53c676a`) y las **10:06** (`conversion_date` del
metadata). Dieciséis minutos. Únicos rastros: el metadata y el checkpoint del
02 fechado ese día.

### 3c. Discrepancias documentadas

- El commit message dice "**1.67M flows**"; el 02 cargó ~1,49M; el entrenador
  usó 2,83M. El número del commit no casa con nada: **memoria imprecisa del
  autor, no medida**. (Caso 22 del patrón.)
- Las **medianas de imputación del entrenador son irrecuperables**: el 02
  computó las suyas sobre 4 días; el entrenador operó sobre 8. La vía B usa
  medianas del concat de 8 días (universo del entrenador por aritmética),
  registradas íntegras en el report.
- **Hiperparámetros del RF de producción: irrecuperables** (el RF del 02 es
  `n_estimators=10, max_depth=10`, "rápido, solo para feature importance" —
  NO es el modelo de producción).

→ **`DEBT-L1-TRAINER-MISSING-001` (P2, post-FEDER)**: reconstruir entrenador
versionado. Receta de partida ya inferida: 8 CSVs (md5 fijados), split
42/0.2/stratify, 23 features del oráculo, imputación inf→NaN→mediana→0.
Encaja con ADR-040 (walk-forward corregiría además el pecado original del
split aleatorio sobre días mezclados).

---

## 4. VÍA B EJECUTADA — `make eval-level1-model-csv` (VERDE)

Nuevo, versionado: `tools/eval/eval_level1_model_csv.py` + targets
`eval-level1-model-csv` / `eval-level1-model-csv-smoke`. Fail-closed en todo:
23 features por NOMBRE desde el oráculo; threshold localizado por walk del
config (aborta si ≠1 candidato — halló `ml.thresholds.level1_attack = 0.65`);
md5 de modelo/oráculo/config/8 CSVs en el report; medianas registradas.

**Resultado (692.703 filas de Wednesday):**

| métrica | valor |
|---|---|
| recall | **0.9987** (tp 252.355, fn 317) |
| precision | 0.9996 (fp 112) |
| FPR | **0.00025** |
| accuracy | 0.9994 |

**SCOPE (grabado dentro del report):** sanity check del modelo aislado sobre
datos reales, **mayormente in-sample** (§1). NO es holdout. NO es el pipeline.
Lo que certifica: contrato de features + imputación + conversión ONNX +
threshold vivo, sanos de punta a punta.

### La autopsia del fósil, ahora demostrada por reproducción

Wednesday tiene **252.672 filas de ataque** (tp+fn, medido hoy). El fósil
declaraba FN 246.582 con recall 0.024 → TP ≈ 6.064; 6.064 + 246.582 = 252.646
≈ 252.672. **Mismo universo de entrada, dos modelos: 0.024 vs 0.9987.** La
hipótesis de DAY 219 ("el 2,4% es la autopsia del XGBoost, no del ONNX") pasa
de "casi con certeza" a **demostrada**. `DEBT-L1-NO-REPRODUCIBLE-HOLDOUT-001`:
mitad diagnóstica RESUELTA; la mitad de generalización sigue abierta (§6).

---

## 5. INJECTOR AUDITADO — descalificado para eval, POR DISEÑO

`tools/synthetic_sniffer_injector.cpp`: genera valores `rand_*` sobre rangos
plausibles (no datos), fuerza el veredicto en modos `--attack`/`--ransomware`
(`fast_detector_score(0.9f)` a mano), y no tiene entrada de datos externa. El
propio código lo confiesa (Day 66): *"valores sintéticos caen fuera de su
distribución de entrenamiento"*. Los "142 features" del header = suma de campos
del proto que puebla (básicos + 4 submensajes + ransomware20). A su favor:
NO puebla los `repeated` 100-103 — coherente con producción, no maquilla.
**Veredicto: herramienta de estrés honesta; se queda como está, fuera del eval.**

---

## 6. VÍA A REDEFINIDA — CTU-13 Neris (cross-dataset genuino)

Tras §1, el holdout real ya estaba en disco:

- `datasets/ctu13/botnet-capture-20110810-neris.pcap` — md5
  `172c6b4eb9be9a14fb5703a83f747a6c` (fijado hoy).
- `datasets/ctu13/capture20110810.binetflow` (369 MB) — **ground truth flujo a
  flujo con 5-tupla** (lo que a MachineLearningCVE le falta).
- Infraestructura de replay ya en el Makefile (`test-replay-neris`), mismo
  pcap del experimento comparativo Suricata/Zeek del paper (ground truth
  147.32.84.165).

**Alcance a declarar:** "generalización cross-dataset a tráfico botnet"
(Neris es botnet; L1 entrenó con Botnet entre sus clases de ATTACK). Claim
más fuerte que un holdout intra-dataset, con alcance más estrecho. Es el
candidato a número del paper. Diseño: DAY 221.

Decisión de timing pendiente (heredada): tcpreplay a `--mbps` fijo reescribe
los tiempos entre paquetes; varias features de las 23 son sensibles a timing
(Flow Duration, Fwd IAT Min, Flow Packets/s, Fwd Packets/s). Verificar
sensibilidad antes de elegir velocidad, o replay a timing original.

---

## 7. HALLAZGOS COLATERALES DEL MAKEFILE (registrar, no tocar hoy)

- **`deploy-models` despliega el fósil**: copia `xgboost_cicids2017.ubj` a
  `/etc/ml-defender/models/`; `sign-models` firma 4 modelos — **los 4 XGBoost,
  ningún ONNX**; `post-up-verify` exige `libplugin_xgboost.so`. Ruta de
  despliegue entera apuntando al modelo descartado. Extiende
  `MODEL-DIR-XGBOOST-FOSSIL-001` al Makefile: el día que alguien lea de
  `/etc/ml-defender/models/` cargará el XGBoost en silencio.
- **`ml-detector-start` hardcodea `build-debug`**, ignora `$(PROFILE)`. El
  número del eval del pipeline debe declarar el perfil; con esto, un
  `PROFILE=production` serviría el binario equivocado sin avisar.
  → `DEBT-MAKEFILE-MLDETECTOR-START-PROFILE-001` (P2).

---

## 8. COMMITS DE DAY 220

```
048d0e09..73fac317  fix/verdict-multihead-honest -> fix/verdict-multihead-honest  feat(eval): DAY 220 — vía B reproducible del modelo L1 (Wednesday CSV)
```
(script + Makefile + report; add explícito fichero a fichero)

(.venv) aironman@MacBook-Pro-de-Alonso test-zeromq-docker % make eval-level1-model-csv-smoke
[config] threshold level1_attack = 0.65 (en ml.thresholds.level1_attack)
[imputación] computando medianas sobre 8 CSVs (universo del entrenador)...
cargando Monday-WorkingHours.pcap_ISCX.csv...
cargando Tuesday-WorkingHours.pcap_ISCX.csv...
cargando Wednesday-workingHours.pcap_ISCX.csv...
cargando Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv...
cargando Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv...
cargando Friday-WorkingHours-Morning.pcap_ISCX.csv...
cargando Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv...
cargando Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv...
[smoke] limitado a 1000 filas
[onnx] input='float_input' outputs=['label', 'probabilities']
[onnx] 1000/1000
{
"confusion": {
"tp": 0,
"fn": 0,
"fp": 0,
"tn": 1000
},
"recall": null,
"precision": null,
"fpr": 0.0,
"accuracy": 1.0,
"threshold": {
"value": 0.65,
"config_path_in_json": "ml.thresholds.level1_attack",
"source_file": "ml-detector/config/ml_detector_config.json",
"config_md5": "cf71fe2bc059b226872b3d84d3557e7d"
}
}

Report completo: /tmp/eval_level1_smoke.json
(.venv) aironman@MacBook-Pro-de-Alonso test-zeromq-docker % make eval-level1-model-csv
[config] threshold level1_attack = 0.65 (en ml.thresholds.level1_attack)
[imputación] computando medianas sobre 8 CSVs (universo del entrenador)...
cargando Monday-WorkingHours.pcap_ISCX.csv...
cargando Tuesday-WorkingHours.pcap_ISCX.csv...
cargando Wednesday-workingHours.pcap_ISCX.csv...
cargando Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv...
cargando Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv...
cargando Friday-WorkingHours-Morning.pcap_ISCX.csv...
cargando Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv...
cargando Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv...
[onnx] input='float_input' outputs=['label', 'probabilities']
[onnx] 692703/692703
{
"confusion": {
"tp": 252355,
"fn": 317,
"fp": 112,
"tn": 439919
},
"recall": 0.9987454090678825,
"precision": 0.9995563776651998,
"fpr": 0.00025452752192459165,
"accuracy": 0.9993806869610785,
"threshold": {
"value": 0.65,
"config_path_in_json": "ml.thresholds.level1_attack",
"source_file": "ml-detector/config/ml_detector_config.json",
"config_md5": "cf71fe2bc059b226872b3d84d3557e7d"
}
}

Report completo: ml-detector/models/production/level1/eval_level1_model_csv_report.json

### Sin commitear, a propósito
```
 M ml-detector/include/zmq_handler.hpp   ← instrumentación DAY 216
 M ml-detector/src/zmq_handler.cpp       ← salvada en docs/day216_instrumentation.patch
 M commit-message.txt                    ← scratch
?? tools/temporal.md                     ← scratch de sesión (limpieza de salidas)
```
STASH intacto: `stash@{0}: commit2-noisy-or WIP` — no perder.

### Decisión pendiente de Alonso
`wednesday_eval_report.json` (el fósil) ahora convive con el report nuevo en el
mismo directorio e induce a error activamente. Propuesta: renombrar a
`xgboost_wednesday_autopsy_UNPROVENANCED.json` o mover con la familia
`xgboost_*` al ejecutar `MODEL-DIR-XGBOOST-FOSSIL-001`.

---

## 9. DEUDAS — MOVIMIENTOS DE HOY

| Deuda | P | Movimiento |
|---|---|---|
| `L1-NO-REPRODUCIBLE-HOLDOUT-001` | P0 | **Mitad diagnóstica RESUELTA** (fósil = XGBoost, demostrado). Mitad de generalización ABIERTA → vía A sobre Neris. |
| `L1-TRAINER-MISSING-001` | **P2 NUEVA** | Entrenador/conversor nunca versionados (§3b). Reconstruir post-FEDER con ADR-040. |
| `MODEL-DIR-XGBOOST-FOSSIL-001` | P2 | **EXTENDIDA**: deploy-models/sign-models/post-up-verify del Makefile apuntan al fósil (§7). |
| `MAKEFILE-MLDETECTOR-START-PROFILE-001` | **P2 NUEVA** | `ml-detector-start` ignora `$(PROFILE)` (§7). |

Resto de deudas de DAY 218/219: sin movimiento.

---

## 10. EL PATRÓN — YA SON VEINTICUATRO

(1-21 en DAY 218/219; ver §0 sobre la discrepancia de numeración del DAY 219.)

22. **El commit message que cuenta sin contar.** `f53c676a` declara "Analyzed
    1.67M flows"; el notebook cargó ~1,49M y el entrenador usó 2,83M. Un número
    en un commit es una AFIRMACIÓN del autor, no una medida — y sobrevivió 9
    meses como si fuera dato.
23. **El md5 correcto adherido al artefacto equivocado.** `bf0dd7e9` circuló
    dos días como "el pcap Wednesday"; era el CSV. Un hash verificable con la
    identidad mal atribuida genera MÁS confianza falsa que ningún hash.
24. **La procedencia fantasma por andamiaje.** Los notebooks 01-07 commiteados
    como esqueletos hicieron que el README describiera un pipeline "completo"
    (01→07) que solo existió en un 14%. Durante 9 meses, quien mirara el
    README + el ls creería que el entrenador estuvo versionado y "se perdió" —
    nunca estuvo. La estructura vacía es evidencia falsa de contenido.

> NO ES UN PATRÓN DE BUGS. ES UN PATRÓN DE FALSA EVIDENCIA.

---

## 11. TRAMPAS NUEVAS DE DAY 220

- **`git show ref:path > out` falla en SILENCIO hacia el redirect**: el error
  va a stderr y el `>` crea el fichero (vacío) igual. `ls -la` del resultado
  ANTES de greparlo. (Hoy los 216 bytes eran reales, pero el instrumento se
  verificó antes de concluir — tres greps vacíos seguidos = verificar el
  instrumento, no concluir.)
- **Un checkpoint de Jupyter fecha una sesión, no la preserva**: el
  `.ipynb_checkpoints` del 15-oct delató el DÍA del entrenamiento perdido sin
  contener nada de él.
- **La premisa del prompt de continuidad es un artefacto más**: "Wednesday
  sirve como holdout" viajó de DAY 217 a DAY 220 sin que nadie la enfrentara
  al metadata. La matriz de confusión llevaba la refutación escrita (566.149)
  desde octubre.
- **`pd.read_csv(usecols=...)` con nombres**: los headers de CICIDS traen
  espacios iniciales inconsistentes; comparar siempre con `.strip()` en ambos
  lados, y leer con `encoding='latin-1'` (paridad con el 02).

---

## 12. DECISIONES QUE SOBREVIVEN

- Todas las de DAY 219 (noisy-OR aparcado, claim del max() intocable en LaTeX,
  reliability 0.0 para ddos/ransomware, MITRE después del extractor, un
  commit/un cambio/una razón).
- El `2.517` sigue SIN PROCEDENCIA.
- **NUEVA**: el número de L1 para el paper saldrá de la vía A (Neris,
  cross-dataset, alcance "botnet") — no de Wednesday en ninguna forma.
- **NUEVA**: la vía B (0.9987) se cita SOLO con su scope ("sanity in-sample");
  el report lo lleva grabado para que no pueda citarse sin él.
- level2/level3 siguen SIN AUDITAR. El silencio no es veredicto.

---

## FEDER

Go/no-go ~1 agosto 2026. Deadline 22 septiembre. Estado de L1 tras hoy:
inferencia sana y demostrada (vía B), fósil explicado y demostrado,
procedencia mapeada con sus agujeros nombrados, y UNA incógnita abierta con
plan concreto: generalización cross-dataset (vía A, Neris, DAY 221).
Un escudo, nunca una espada.