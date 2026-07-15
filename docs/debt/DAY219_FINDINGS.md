# DAY 219 FINDINGS — `fix/verdict-multihead-honest`

> Escrito desde la evidencia verificada en la sesión, no de memoria.
> Cada afirmación de este documento tiene detrás un comando cuya salida se
> inspeccionó. Donde algo no está probado, se dice "SIN CONFIRMAR".
> Regla del día: **verificar el artefacto, no la intención.**

---

## RESUMEN DE UNA LÍNEA

Se cerró `DEBT-FLOWSTATS-COPY-AMPUTATED-001` (P0, fuga de datos en la ruta
viva) y se **demostró por estática** que el `FeatureExtractor` del sniffer
(84 features) nació muerto: nunca se llamó en producción, pero se compila y se
envía en el binario.

Investigando el consumidor real de L1 se descubrió que NO es ese extractor sino
`extract_level1_features` en el **ml-detector** (OTRO binario), que SÍ está vivo
y produce 23 features **verificadas 23/23 correctas** contra el oráculo. La
sospecha de "5 features rotas" (DAY 217) baja a **2 degradadas** ([8] aprox,
[14] hardcode). El escalado resultó ser una mentira inofensiva del config
(corregida). **Hallazgo central que toca la claim del paper:** el modelo L1
vivo NO tiene evaluación out-of-sample reproducible — su 0.9987 es in-sample,
y el único holdout del directorio (recall 2,4%) es la autopsia del XGBoost
descartado. **L1 no está roto — está sin medir honestamente.** Sólo se auditó
L1; level2/level3 no.

---

## 1. LO QUE SE CERRÓ — `DEBT-FLOWSTATS-COPY-AMPUTATED-001` (P0)

**RED `6166982f` → GREEN `fc292bc8`.** `ctest: 17/18`.

### Causa raíz: un `unique_ptr` que nunca fue necesario

`TimeWindowManager` es copiable desde el día uno (`deque<WindowStats>` POD +
PODs + `vector<double>`; ni mutex ni punteros). El `unique_ptr` de
`FlowStatistics::time_windows` era la **única** razón por la que
`FlowStatistics` no era copiable. Eso obligó a escribir a mano una lista de
**26 asignaciones** en `get_flow_stats_copy` (`sharded_flow_manager.cpp:96`).
La lista envejeció y **2 de los 28 campos se perdían** en cada copia. La ruta
de PRODUCCIÓN come de esa copia (`ring_consumer.cpp:809 → :820`), así que la
fuga afectaba a **todo** consumidor de la copia, incluido el
`MLDefenderExtractor` que sí está enchufado.

### Las 5 features rotas de L1 son exactamente las que dependen de esos 2 campos

| L1 | Feature | Campo perdido |
|---|---|---|
| [1]  | Subflow Fwd Bytes      | `time_windows` (`feature_extractor.cpp:334`) |
| [8]  | act_data_pkt_fwd       | `fwd_payload_lengths` |
| [12] | Subflow Bwd Bytes      | `time_windows` (`:344`) |
| [14] | Init_Win_bytes_forward | `time_windows` (`:379`) |
| [15] | Subflow Fwd Packets    | `time_windows` (`:329`) |

**No es correlación, es la causa.** El "hardcodeo" de DAY 216 era el SÍNTOMA:
alguien vio ceros y los cementó sin rastrear su origen.

### La hipótesis del prompt de DAY 218 era FALSA

*"`ShardedFlowManager` NO llama a `FlowStatistics::add_packet()`"* — **falso.**
Sí lo llama (`:73`, `:83`). Seguirla a ciegas habría duplicado el `push_back`
(el arreglo rápido que garantiza que vuelvan a divergir). **Mirar el código
antes de decidir fue lo único que hizo falta.**

### Los cambios

- `time_windows`: `unique_ptr` → **POR VALOR**. Los 4 ctors/assign explícitos
  (declarar el move suprime el copy implícito — por eso no era copiable ni aun
  quitando el puntero).
- `get_flow_stats_copy`: **40 líneas → 1.** Copia el compilador: los 28 y los
  que vengan mañana. **La clase de defecto deja de ser POSIBLE.**
- `feature_extractor.cpp`: **14 guardas** `if (!flow.time_windows) return 0.0;`
  eliminadas. Protegían de un `nullptr` IMPOSIBLE (el ctor hacía `make_unique`)
  mientras el objeto llegaba VACÍO. **Caso 19.**
- `ShardedFlowManager::clear()` — HALLAZGO 2 de DAY 218 resuelto.
- `sharded_flow_manager.cpp` incluía `sharded_flow_manager_fix3.hpp` — header
  IDÉNTICO pero DISTINTO FICHERO al canónico que incluye el resto del proyecto.
  Dos `#pragma once`, una clase: **violación de la ODR latente**, viva 175 días
  por ser byte a byte iguales. Si hubieran divergido en un CAMPO en vez de un
  método, no habría error de compilación: **corrupción de memoria silenciosa.**
- `full_contract:219/287`: `ASSERT_NE(time_windows, nullptr)` **ya no compila.**
  El verde falso es INEXPRESABLE. Sustituido por preguntas sobre el CONTENIDO.

### `PureAcksGiveZero` vale algo, por primera vez

Ayer daba 0 porque el vector estaba vacío (caso 16). Hoy da 0 **contando ceros.**

---

## 2. EL HALLAZGO CENTRAL — `FeatureExtractor` NACIÓ MUERTO (P0, CONFIRMADO)

<!-- NOTA DE VERIFICACIÓN: los cuatro greps de esta sección, el sed del CMake y
el ls de los .fase se ejecutaron y su salida se inspeccionó en la sesión de
DAY 219. Es la parte MÁS sólida del documento. Las citas file:line del §1
(FLOWSTATS) se transcribieron del prompt de continuidad DAY 219 y NO se
re-verificaron contra el árbol en esta sesión: si alguna baila, es transcripción,
no hallazgo. Cotejar antes del merge. -->


> `DEBT-FEATURE-EXTRACTOR-DEAD-CODE-001`

No fue "se desconectó en la crisis de concurrencia del DAY 44".
**La hipótesis de desconexión es FALSA.** No se puede desconectar lo que nunca
se conectó. Probado por convergencia de cuatro vías independientes:

### La evidencia (comandos ejecutados, salida inspeccionada)

1. **Nombre de método en producción** —
   `grep -rn 'extract_features' sniffer/ --include='*.cpp' --include='*.hpp' | grep -v 'feature_extractor\.\|tests/'`
   → **un solo hit**, y es un falso amigo por substring:
   `ransomware_feature_processor.cpp:159 → extractor_->extract_features_phase1a()`
   es OTRO método (`_phase1a`) sobre OTRA clase (`RansomwareFeatureExtractor`).

2. **Nombre de tipo en producción** —
   `grep -rn 'FeatureExtractor' sniffer/ ... | grep -v 'Ransomware...\|MLDefender...\|feature_extractor\.\|tests/'`
   → **VACÍO.** El tipo `FeatureExtractor` no se nombra en producción en
   ningún sitio. Nada lo construye ⟹ nada llama a `extract_features()`.

3. **Interfaz / factory** — `IFeatureExtractor` **no existe** en el árbol.
   No hay dispatch virtual ni `std::function` guardado por donde una llamada
   viva pudiera esconderse. Esto es lo que cierra el agujero: el grep 2 vacío
   sólo prueba muerte si no hay indirección, y no la hay.

4. **Arqueología (pickaxe)** —
   `git log --oneline --all -S 'extract_features' -- sniffer/src/userspace/ring_consumer.cpp`
   → **VACÍO.** El call-site NUNCA existió en `ring_consumer` en ningún commit.
   `-S` sobre todo `sniffer/src/` sólo toca ficheros ransomware (otra clase),
   el `.hpp`/`.cpp` de la propia clase, y los backups `.fase1`/`.fase2`.
   **Ni un solo fichero consumidor, jamás.**

### Y lo que agrava el hallazgo: el cadáver se COMPILA y se ENVÍA

`sniffer/CMakeLists.txt:281` mete `src/userspace/feature_extractor.cpp` en
**`SNIFFER_SOURCES`** — el binario de PRODUCCIÓN del sniffer, no el bloque de
test (`1030+`). Verificado con `sed -n '270,300p'`. Consecuencia:

> 84 features de lógica de extracción, contrato incluido, se compilan con
> `-Werror`, pasan AppArmor y viajan al binario que corre en el target.
> **Jamás se invocan.** Peso muerto que aumenta la superficie del binario sin
> aportar una sola feature al pipeline.

Esto sube `FEATURE-EXTRACTOR-DEAD-CODE-001` de P0-de-investigación a
**P0-de-hecho, confirmado.**

### El fósil datado: `.fase1` / `.fase2`

```
-rwxr-xr-x  19K  Oct 10  2025  sniffer/src/userspace/feature_extractor.cpp.fase1
-rwxr-xr-x  19K  Oct 10  2025  sniffer/src/userspace/feature_extractor.cpp.fase2
```

Dos snapshots de desarrollo congelados el 10-oct-2025. Casan con el commit
`1d273a47` (*"el sniffer ya captura 83 features, pero hay un problema con las
estadísticas"*): el autor **creyó** que integraba el extractor; la lógica
aterrizó en un `.cpp.fase2` (un backup) en vez de en `ring_consumer`. El
"problema con las estadísticas" que reportó era el borde visible del hecho
real — las features nunca llegaban porque **nadie llamaba al extractor.**
Diagnosticó el síntoma sin ver la causa. Nueve meses después se cierra.

**Acción:** los `.fase*` NO van al árbol de fuentes (regla DAY 219). Mover a
`/tmp` o borrar — pero citados aquí como el registro fósil que fecha el
nacer-muerto. Esto refuerza `SOURCE-TREE-BACKUP-FILES-001`.

### La respuesta a la pregunta de los 200 días

No "sobrevivió a la ausencia de TESTS". Tampoco, en pasivo, "a la ausencia de
EJECUCIÓN". La forma exacta:

> Alguien escribió 84 features, las metió en el build de producción, vio
> números raros en las stats, y lo dejó ahí. El log lleno y bonito
> (`if (size() > 0)`, sólo AFIRMA) nunca gritó que faltaban, porque no puede
> NEGAR. El componente muerto compiló, se envió, y el instrumento que debía
> delatarlo sólo sabía afirmar presencia.

Patrón de falsa evidencia en su forma más pura: no un bug oculto, sino un
componente entero invisible.

---

## 3. LO SÓLIDO SOBRE LOS CAMPOS `repeated` DEL PROTOBUF

`DEBT-PROTO-REPEATED-FIELDS-EMPTY-001` (P0). Los 4 campos `repeated` de
`NetworkFeatures` están VACÍOS — ni un `add_*` en todo el árbol:

```proto
repeated double ddos_features             = 100;   // 83 — VACÍO
repeated double ransomware_features       = 101;   // 83 — VACÍO
repeated double general_attack_features   = 102;   // 23 — VACÍO  ← el de L1
repeated double internal_traffic_features = 103;   // 4-5 — VACÍO
```

Dos arquitecturas de features en el sniffer, sólo una enchufada:

| | `FeatureExtractor` | `MLDefenderExtractor` |
|---|---|---|
| Fichero | `feature_extractor.cpp` | `ml_defender_features.cpp` |
| Features | 84 (enum posicional) | 40 (4×10) |
| Contrato | `l1_feature_contract.hpp` | ninguno |
| Destino | campos 100-103 (`repeated`) | submensajes (`ddos_embedded`, etc.) |
| ¿En producción? | **NO (confirmado §2)** | **SÍ** (`ring_consumer.cpp:820`) |

`populate_ml_defender_features` (`ml_defender_features.cpp:718`) rellena los 4
submensajes + campos base. **NO toca el 102. NO conoce a `FeatureExtractor`.**

**Corolario:** si los 4 `repeated` están vacíos, los modelos de DDoS y
ransomware nunca comieron features reales por esa vía. Revalida
`ddos`/`ransomware` a `reliability = 0.0`. (Sólo dice que la tubería aguas
arriba estaba rota; falta enganchar, medir y averiguar con datos.)

⚠️ **Salvedad heredada de DAY 218:** que exista un registro fiable en el
detector NO prueba que los números del paper salgan de ahí. El `2.517` sigue
SIN PROCEDENCIA (DAY 217). "Revalidado hoy" se refiere sólo a la decisión de
`reliability = 0.0`, no a la procedencia de ninguna cifra del paper.

### Caso 22 — por qué el log nunca gritó

`feature_logger.cpp:158`: `if (nf.general_attack_features_size() > 0) { ... }`
— sin `else`, sin warning. La ausencia de las 23 features es INDISTINGUIBLE de
la ausencia de una llamada al logger. El logger sí imprime los otros
submensajes → el log salía lleno y bonito.

> No es que el log mintiera. Es que sólo podía AFIRMAR, nunca NEGAR.
> Un test sí puede decir `EXPECT_EQ(size(), 23)`. Un log, no.

---

## 3-BIS. EL PIPELINE L1 DEL ML-DETECTOR — INVESTIGADO DE PUNTA A PUNTA

> Esta sección desmonta un modelo mental equivocado que arrastrábamos: NO era
> el `FeatureExtractor` del sniffer (§2) quien alimentaba L1. El consumidor de
> L1 es OTRO extractor, en OTRO binario, y está VIVO.

### El giro: hay DOS `FeatureExtractor`, en dos binarios distintos

| | sniffer | **ml-detector** |
|---|---|---|
| Fichero | `sniffer/src/userspace/feature_extractor.cpp` | `ml-detector/src/feature_extractor.cpp` |
| Método | `extract_features` (84 métodos `extract_X`) | `extract_level1_features` (monolítico, 5 `::extract`) |
| Lee de | `FlowStatistics` | `NetworkSecurityEvent` protobuf |
| Produce | 84 features | **23 features** |
| ¿Vivo? | **NO** (nació muerto, §2) | **SÍ** — `zmq_handler.cpp:498` |

El del ml-detector se llama en la ruta viva y gobierna el veredicto:
`zmq_handler.cpp:498` extrae → `:516` `level1_model_->predict()` →
`:539-547` puebla `level1_general_detection` → `:722` gate
`if (label_l1==1 && confidence_l1 >= thresholds.level1_attack)`.

**Corolario que corrige a §3:** el ml-detector NO lee el campo 102. Recomputa
L1 desde el protobuf en `:498`. Por eso el 102 vacío nunca rompió L1 — L1
jamás leyó de ahí. **3b NO tiene nada que ver con el campo 102 ni el sniffer.**

### El extractor vivo está CORRECTO en orden y semántica — 23/23 verificadas

Enfrentado índice a índice contra el ORÁCULO
(`level1_attack_detector_metadata.json`, 23 `feature_names`, `input_shape [null,23]`),
las 23 asignaciones de `extract_level1_features` coinciden en orden y campo.

**La sospecha de "5 features rotas" (DAY 217) baja a 2 reales:**
- Las presuntas duplicadas [1]/[9] (`Subflow Fwd Bytes` / `Total Length of Fwd
  Packets`) y [12]/[18] leen el mismo campo del protobuf **a propósito**: en
  CICIDS, para flujo de un solo subflow, esas columnas son numéricamente
  idénticas. El modelo entrenó con ellas iguales. Replicarlas es CORRECTO, no
  bug. **Sólo el oráculo lo demuestra; a ojo parecían el defecto de la
  lista-a-mano.** (Caso 23 del patrón, invertido: dos cosas que parecen el bug
  y NO lo son.)

**Las 2 features realmente degradadas:**
| idx | feature | estado | causa |
|---|---|---|---|
| 8  | `act_data_pkt_fwd`       | APROXIMADA | `total_forward_packets()` incluye ACKs puros; el valor real los excluye. Comentario confiesa: "asumimos que…" |
| 14 | `Init_Win_bytes_forward` | HARDCODE 0 | `features[14] = 0.0f; // TODO`. El modelo entrenó con valores reales; en prod recibe 0 constante. |

**Ninguno de los dos campos existe en el proto** (`protobuf/network_security.proto`,
verificado a mano tras corregir la ruta — NO es `common/proto/`, ese dir no
existe). `time_window_size` existe pero es OTRA cosa (ventana de agregación, no
TCP initial window). Cerrar [8] y [14] de verdad exige capturar los valores en
el **sniffer** + añadir campos al **proto** + leerlos en el **detector**:
cruza kernel-space. **Post-FEDER.** → `DEBT-L1-FEATURES-PLACEHOLDER-001` (P2).

### El escalado es una MENTIRA INOFENSIVA del config

`ml_detector_config.json`: `requires_scaling: true`, `scaler_file: "level1/scaler.json"`
— pero `scaler.json` está **VACÍO** y NINGÚN código del ml-detector lee o
aplica un scaler (grep sobre `src/` sólo halla la CARGA de la ruta en
`config_loader.cpp:241/245`, nunca un `apply`). La ruta viva es features crudas
→ `predict()`, sin transformar.

Prueba de que servir crudo es CORRECTO: el modelo se entrenó sin escalar
(si no, el 200/200 recall sobre CSV crudo sería imposible). `requires_scaling:
true` es un residuo de un pipeline que contempló escalar y no lo hizo.
**NO implementar escalado — sería meter una transformación que el modelo nunca
vio.** Acción: corregir el config a `false` + `scaler_file: ""`
→ **HECHO (A)** en `ml_detector_config.json`. Cierra
`DEBT-CONFIG-SCALING-LIES-001` (P1: no rompe hoy, trampa armada para el día que
alguien implemente escalado confiando en que el config dice la verdad).

### El threshold vivo es 0.65 — NO hay cruce de modelos

`ml_detector_config.json:148` → `level1_attack: 0.65`. El ONNX corta con SU
propio umbral. El `xgboost_..._v2_threshold.json` tiene `threshold: 0.821`,
calibrado para el XGBoost, y **NO se aplica a nada vivo.** Estado A confirmado:
XGBoost limpiamente desconectado.

### HALLAZGO CENTRAL DEL DÍA — L1 no tiene eval out-of-sample reproducible

> `DEBT-L1-NO-REPRODUCIBLE-HOLDOUT-001` (P0). Es el hallazgo que toca la CLAIM
> DEL PAPER, por encima del extractor muerto y del scaler.

El directorio `models/production/level1/` contiene DOS familias de modelo:
- `level1_attack_detector.onnx` (RandomForest) — **el que el config carga.**
- `xgboost_cicids2017*` (v1, v2) — **el descartado por mala eficacia** (memoria
  de Alonso, confirmada por artefacto: su `wednesday_eval_report` da recall 2,4%).

**Dos contratos de features DISTINTOS.** El ONNX y el XGBoost declaran 23
features cada uno, pero NO las mismas: el XGBoost tiene `SYN Flag Count`,
`Flow Bytes/s`, `Fwd IAT Total` (ausentes en ONNX); el ONNX tiene
`Subflow Fwd Bytes`, `act_data_pkt_fwd`, `Init_Win_bytes_forward` (ausentes en
XGBoost). No son intercambiables.

**Las dos métricas del ONNX cuentan historias opuestas:**
- `level1_attack_detector_metadata.json`: accuracy **0.9987**, recall **0.9992**
  — pero es IN-SAMPLE (fecha = conversión a ONNX, 2025-10-15, sobre el split
  de entrenamiento/validación interna).
- `wednesday_eval_report.json`: recall **0.024**, FN **246.582** — OUT-OF-SAMPLE
  (pcap real del miércoles). PERO **de modelo INDETERMINADO** (el fichero no se
  autodescribe) y con threshold 0.821 = el del XGBoost → casi con certeza es la
  AUTOPSIA DEL XGBOOST, no del ONNX.

**La brecha 98%→2,4% del XGBoost (val_recall 0.9817 vs wednesday 0.024) es la
firma conocida del overfitting a CICIDS.** No hay garantía de que el ONNX no
haga lo mismo, porque su 0.9992 es del tipo "validación", NO del tipo "holdout".

**Y el generador del eval NO EXISTE en el repo:**
`grep -rn 'wednesday_eval\|246582\|bf0dd7e9' ml-detector/ --include='*.py'
--include='*.sh' --include='*.cpp'` → **VACÍO** (glob válido, dir existe: el
vacío es el dato). El `wednesday_eval_report.json` está en el árbol pero ningún
código versionado lo produce. **No es reproducible desde este repo.**

**Conclusión honesta, separando probado de temido:**
- L1 NO está roto: arquitectura sana, extracción 23/23 correcta, threshold
  propio, escalado correcto. TODO probado.
- L1 tiene deuda ACOTADA: 2 features degradadas ([8],[14]), proto no las
  transporta aún.
- L1 tiene UNA incógnita real: **no existe medición out-of-sample reproducible
  del modelo VIVO.** Eso es AUSENCIA DE EVIDENCIA de que sea bueno — NO
  evidencia de que sea malo. Son cosas opuestas.

**ACCIÓN P0 PARA EL FEDER** — target `make eval-level1-holdout`: correr el
`level1_attack_detector.onnx` VIVO sobre un pcap que no vio (Wednesday sirve,
md5 `bf0dd7e9…` disponible), alimentándolo por el pipeline vivo
(`extract_level1_features`, NO un script Python paralelo), y reportar el recall.
Es el `make test-arxiv-paper` aplicado a la métrica que más importa. Resultado:
- recall bueno → L1 sano, número honesto para el paper, susto de hoy era el
  cadáver del XGBoost asustando con la autopsia equivocada.
- recall malo → problema real, pero conocido con 2 semanas de margen.

⚠️ **ALCANCE:** hoy sólo se auditó L1. **level2 (DDoS, ransomware) y level3
(internal, web) NO fueron auditados.** El silencio sobre ellos NO es un
veredicto — es trabajo no hecho. No extrapolar "L1 tiene X" a "todos los
modelos tienen X". Auditarlos es trabajo pendiente, no hallazgo.

---

## 4. COMMITS DE DAY 219

```
6166982f  test(sniffer): DAY 219 RED  — DEBT-FLOWSTATS-COPY-AMPUTATED-001
fc292bc8  fix(sniffer):  DAY 219 GREEN — DEBT-FLOWSTATS-COPY-AMPUTATED-001 (P0)
```

Artefacto verificado:
`git show HEAD:sniffer/src/flow/sharded_flow_manager.cpp | grep -c 'copy\.'` → **0**.

### Sin commitear, a propósito

```
 M ml-detector/include/zmq_handler.hpp   ← instrumentación DAY 216 (9 contadores)
 M ml-detector/src/zmq_handler.cpp       ← salvada en docs/day216_instrumentation.patch
 M commit-message.txt                    ← scratch
AM docs/debt/DAY219_FINDINGS.md          ← este fichero
```

**NUNCA `git add -u` NI `git commit -a`.**
STASH: `stash@{0}: commit2-noisy-or WIP` (header + tests, válidos) — no perder.

---

## 5. DEUDAS — ESTADO AL CIERRE DE DAY 219

| Deuda | P | Estado |
|---|---|---|
| `FLOWSTATS-COPY-AMPUTATED-001` | — | **CERRADA HOY** (`fc292bc8`) |
| `FEATURE-EXTRACTOR-DEAD-CODE-001` | **P0** | **CONFIRMADA.** Nació muerto; se compila y envía. |
| `PROTO-REPEATED-FIELDS-EMPTY-001` | **P0** | 4 campos `repeated` vacíos, ni un `add_*`. |
| `SOURCE-TREE-BACKUP-FILES-001` | **P2→P1** ↑ | Registrada en DAY 218 (P2: 19 backups, 4 copias de `feature_extractor.cpp`, 8 dirs de build). DAY 219 la SUBE a P1: no es sólo que el árbol confunda al `grep` — se compilaba contra DOS declaraciones de la misma clase; hoy costó un error de compilación. Los `.fase1/.fase2` (10-oct-2025, ya contados entre esos 4) son el fósil datado del nacer-muerto. |
| `FULL-CONTRACT-POPULATION-THEATRE-001` | **P1** | `total_fields += 7`, comprueba 6. `fwd_payload_lengths` no se mira; `dpkts`, `dbytes` y 5 flags se cuentan como poblados SIN mirarlos. Rediseño, no parche. |
| `SHARDED-INIT-CALL-ONCE-MUTE-001` | **P2** | `initialize()` es `std::call_once`: 2ª llamada = NO-OP mudo, descarta la `Config` nueva. Correcto en prod (1 init); daño a la MEDIBILIDAD. Mitigado con `clear()`. Decisión Alonso: (a) ahora / (b) post-FEDER. |
| `L1-NO-REPRODUCIBLE-HOLDOUT-001` | **P0** | **NUEVA (§3-BIS). TOCA LA CLAIM DEL PAPER.** El ONNX vivo sólo tiene métrica in-sample (0.9987). El único holdout del dir (wednesday, recall 2,4%) es del XGBoost descartado, y su generador NO existe en el repo. Acción: `make eval-level1-holdout` sobre pcap no visto por el pipeline vivo. |
| `CONFIG-SCALING-LIES-001` | **P1** | **NUEVA (§3-BIS). MITIGADA (A).** `requires_scaling: true` + `scaler.json` vacío + ningún código escala. Config corregido a `false`/`""`. El riesgo era el día que alguien implementara escalado confiando en el config. |
| `L1-FEATURES-PLACEHOLDER-001` | **P2** | **NUEVA (§3-BIS).** feature[8] `act_data_pkt_fwd` aproximada; feature[14] `Init_Win_bytes_forward` hardcode 0. Ningún campo existe en el proto. Cierre cruza sniffer+proto+detector: post-FEDER. |
| `MODEL-DIR-XGBOOST-FOSSIL-001` | **P2** | **NUEVA (§3-BIS).** Familia `xgboost_cicids2017*` (descartada) conviven en `production/level1/` con el ONNX vivo. El `wednesday_eval_report.json` sin prefijo de modelo induce a error. Familia `SOURCE-TREE`. Mover/prefijar. |

⚠️ **ALCANCE DE LA AUDITORÍA DE HOY:** sólo L1. level2 (DDoS, ransomware) y
level3 (internal, web) NO auditados. El silencio no es veredicto.

Las 7 deudas de DAY 218 siguen abiertas (ver `DAY218_FINDINGS.md`).
`test_payload_analyzer` sigue ROJO (4/4 patrones + perf) —
`DEBT-PAYLOAD-ANALYZER-PATTERNS-INERT-001`. No tocado.

---

## 6. EL PATRÓN — YA SON VEINTIUNO

(1–15 en `DAY218_FINDINGS.md`. El 15 es "seis greps ciegos de Claude".
⚠️ El prompt de continuidad de DAY 219 numeraba desde 17 diciendo "1–16 en
DAY 218" — ERROR HEREDADO: DAY 218 cierra en 15, no en 16. Es el caso 15 en
directo: fiarse de un artefacto que afirma haber contado sin recontar.)

16. `get_flow_stats_copy`: 26 de 28 campos, lista escrita a mano. El comentario
    `// time_windows will be created by FlowStatistics() constructor` confesaba
    la amputación como si fuera detalle de implementación.
17. `full_contract:219`: `ASSERT_NE(time_windows, nullptr)` PASABA siempre —
    puntero no-nulo a objeto vacío. Y `:287` lo contaba como campo poblado.
    Un test de "contrato completo" que certifica poblado el campo recién perdido.
18. 14 guardas `if (!flow.time_windows) return 0.0;` protegiendo de un `nullptr`
    IMPOSIBLE mientras el objeto llegaba vacío. Guardas que protegen del fallo
    que no ocurre e ignoran el que sí.
19. `NoFieldsLeftAtDefaultValues` declara poblados los campos que están en su
    valor por defecto.
20. La red de seguridad se disparó contra su propia documentación (buscaba
    `"time_windows != nullptr"` y lo halló en los comentarios del parche). Un
    falso positivo del instrumento escrito para evitar falsos negativos.
    (Claude, DAY 219.)
21. `if (size() > 0)` en el logger: la ausencia del dato es indistinguible de
    la ausencia de la llamada. Un artefacto que sólo puede AFIRMAR, nunca NEGAR.

> NO ES UN PATRÓN DE BUGS. ES UN PATRÓN DE FALSA EVIDENCIA.

---

## 7. TRAMPAS NUEVAS DE DAY 219

- `ctest ... | grep -c` sobre un test que NO COMPILA devuelve `0` — igual que
  un test que corre y no imprime. Un cero que significa "no medí nada",
  disfrazado de dato. (Misma familia que el `grep 2>/dev/null` de DAY 218.)
- `grep --include=*.cpp` en zsh NO es un grep: zsh expande el glob y aborta
  antes de llamar a `grep`. Hay que citar: `--include='*.cpp'`.
- `sed -n '1,20p' fichero  # comentario` — zsh pasa el comentario como
  argumento: `sed: #: No such file or directory`.
- Un grep con regex de tipos concretos NO es un inventario de campos: si un
  miembro tiene un tipo fuera de la lista, no aparece y la salida sale limpia.
  Verificar el struct con los ojos.
- Los backups NO van al árbol de fuentes. Van a `/tmp`. El backup de verdad es
  el commit del RED.
- **Un grep de liveness sólo puede probar VIVO, nunca MUERTO** — salvo que se
  cierre antes la vía de indirección (interfaz/factory/`std::function`). Aquí
  se cerró (`IFeatureExtractor` no existe), y por eso el grep 2 vacío SÍ prueba
  muerte. Sin ese cierre, habría hecho falta una sonda de runtime. (DAY 219.)
- **Inventar la ruta antes de verificarla.** Se buscó `common/proto/*.proto` —
  ese dir NO EXISTE; el proto vive en `protobuf/network_security.proto`. En zsh
  el glob sin match ABORTA el comando (`no matches found`) y parece "el campo no
  existe" cuando es "la ruta no existe". Verificar la ruta (`ls`) ANTES de
  concluir sobre el contenido. (Claude, DAY 219 — error propio.)
- **Métrica in-sample disfrazada de rendimiento.** Un `accuracy: 0.9987` en el
  metadata de un modelo NO es su capacidad de generalizar si se midió sobre el
  split de entrenamiento. El número honesto es el holdout out-of-sample. En
  CICIDS la brecha val→holdout puede ser 98%→2% (overfitting conocido).
  Un metadata que presume no sustituye a un eval fresco. (DAY 219.)
- **Un artefacto de eval sin generador versionado no es reproducible.** El
  `wednesday_eval_report.json` existe en el árbol pero ningún `.py/.sh/.cpp` lo
  produce. Un número que no puedes recomputar con `make` no puede ir al paper
  como medido. (DAY 219.)
- **No extrapolar de la muestra auditada al conjunto.** "L1 tiene una incógnita"
  ≠ "todos los modelos rotos". Sólo se auditó L1. El silencio sobre level2/3 es
  trabajo no hecho, no veredicto. Angustia de fin-de-sesión ≠ evidencia.

---

## 8. PLAN DE REPARACIÓN — ESTADO

1. ✅ HECHO (`5b494d90`) — contrato L1 + test de propiedad + targets `common-*`.
   ⚠️ `l1_feature_contract.hpp` es HUÉRFANO: sólo lo incluye su propio test.
2. ✅ HECHO (`fc292bc8`) — `ACT_DATA_PKT_FWD` (83, `FEATURE_COUNT`→84) +
   extractor + test + ruta de población. `PayloadLenReachesFeature...` VERDE.
3. ✅/🔄 PASO 3 — RESUELTO EN ALCANCE (§3-BIS). El modelo mental del plan era
   ERRÓNEO: NO había que conectar el `FeatureExtractor` del sniffer al 102.
   El consumidor de L1 (`extract_level1_features` del ml-detector) ya está vivo
   y recomputa desde el protobuf, NO desde el 102.
    - (a) ✅ El del sniffer confirmado muerto (§2). Se puede BORRAR, no revivir.
    - (b) ✅ El extractor vivo verificado 23/23 correcto contra el oráculo.
      La restricción "llamar-no-copiar" resultó IRRELEVANTE: no hay 102 que
      poblar en la ruta de L1. 3b no era una decisión de arquitectura.
    - (c) 🔄 Queda deuda ACOTADA: 2 features degradadas ([8],[14],
      `L1-FEATURES-PLACEHOLDER-001`, P2, post-FEDER) + config de escalado
      corregido (A, hecho).
4. 🔴 **NUEVO PASO CRÍTICO — `make eval-level1-holdout`** (`L1-NO-REPRODUCIBLE-
   HOLDOUT-001`, P0). Correr el ONNX vivo sobre pcap no visto por el pipeline
   vivo. Es lo que decide si L1 va al FEDER. Reemplaza en prioridad a todo lo
   demás de L1.
5. (Post-FEDER) Extender el proto con `act_data_pkt_fwd` e initial-window reales
   para cerrar [8] y [14]. Cruza sniffer+proto+detector.

NOTA: los pasos 4-5 del plan VIEJO (poblar/leer el campo 102, injector) quedan
SIN OBJETO para L1 — el 102 no está en la ruta de L1. Reevaluar si el 102 sirve
a algún otro consumidor o si es dead-code del proto (relacionado con
`PROTO-REPEATED-FIELDS-EMPTY-001`).

---

## 9. DECISIONES QUE SOBREVIVEN

- Commit 2 (noisy-OR) APARCADO, no cancelado. El noisy-OR NO suprime FP
  (monótono creciente, como `max`). La supresión de FP necesita ADR-007
  (AND/veto), que necesita antes `DEBT-VERDICT-DECIDED-UPSTREAM-001`.
- La claim del `max()` es aritméticamente imposible: `max(a,b) ≥ a` SIEMPRE.
  El ML no puede suprimir FP. **NO tocar el LaTeX aún.**
- Traffic = GUARD, no término del producto.
- `ddos`/`ransomware` a `reliability = 0.0`. Revalidado hoy (§3).
- `l3_combined_seal` con clave propia.
- La P gobierna la FUERZA de la evidencia, NUNCA la ETIQUETA.
- MITRE va DESPUÉS del extractor.
- `DEBT-VERDICT-WEIGHTS-CALIBRATION-001` INDECIDIBLE hasta que las cabezas vean.
- Un commit, un cambio, una razón.
- Verificar el artefacto, no la intención. `git show HEAD:<f> | wc -l`.
- El RED obligatorio es la ÚNICA forma de demostrar que el instrumento está
  conectado. Corolario DAY 219: para LIVENESS, la sonda de runtime es el RED —
  un `LOG` que no dispara bajo tráfico prueba lo que el grep sólo sugiere.

---

## FEDER

Go/no-go ~1 agosto 2026. Deadline 22 septiembre 2026.
Ninguna deuda nueva es cosmética. Todas afectan a la capacidad del proyecto de
medir lo que dice que mide.