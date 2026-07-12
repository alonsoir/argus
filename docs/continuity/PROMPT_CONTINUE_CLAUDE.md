# PROMPT DE CONTINUIDAD — DAY 217 → 218
## Rama `fix/verdict-multihead-honest`

> Memoria de sesión. Claude no recuerda entre ventanas. La fuente de verdad del PLAN
> sigue siendo el PLAN. Aquí sólo el estado operativo.

---

## 🚨 HALLAZGO DE LA TARDE DE DAY 217 — EL PAPER TIENE UNA CLAIM IMPOSIBLE

**NO ES UNA DEUDA DE CÓDIGO. ES UNA CLAIM CENTRAL DEL ABSTRACT.**
**NO TOCAR EL LATEX HASTA HABERLO DIGERIDO EN FRÍO.**

### La claim (arXiv:2604.04952 — abstract, §4.3, §8.3, §8.6, conclusión)

> *"The Fast Detector alone produces a FPR of 6.61% on purely benign traffic (bigFlows);
> **the ML layer cuts flagged benign flows from 2,517 to 5 (~500×)**."*

### La aritmética que la prohíbe — `ml-detector/src/zmq_handler.cpp`

```cpp
:550   double ml_score    = label_l1 == 1 ? confidence_l1 : (1.0 - confidence_l1);
:553   double final_score = std::max(fast_score, ml_score);
:625   DROP  ⟺  final_score >= config_.scoring.malicious_threshold
```

**`std::max` es MONÓTONO CRECIENTE. `max(a,b) ≥ a`, SIEMPRE.**
**Ningún valor de `ml_score` puede reducir un bloqueo. Ni con el modelo perfecto.
Ni con las 23 features arregladas.**

⟹ **La supresión de FP atribuida al ML es IMPOSIBLE bajo la Ecuación 1 del propio paper.**
No es un error de medición: **el mecanismo descrito no puede producir el efecto descrito.**
Un revisor con un lápiz lo ve en treinta segundos.

### Y encima, con el extractor roto (DAY 216), el ML es literalmente constante

Medido: `label_l1 = 0` en **200/200 eventos** (100 ruido + 100 ataque DDoS),
`confidence_l1 ≈ 0.85`. Por tanto:

```
ml_score    ≈ 1 − 0.85 = 0.15        ← CONSTANTE
final_score = max(fast_score, 0.15)
DROP        ⟺ max(fast_score, 0.15) ≥ 0.65   ⟺   fast_score ≥ 0.65
```

**El ML no ha influido NUNCA en una sola decisión de bloqueo.** Ni una.
Y el extractor está roto **desde `5ada889a` — el PRIMER commit del ml-detector.**
No se rompió: nació así. **Todas las mediciones del ML en el pipeline, en toda la
historia del proyecto, se hicieron con el extractor roto.**

### El número 2.517 NO TIENE PROCEDENCIA

`grep -rn "2517|2,517"` en `*.py *.sh *.csv *.log` → **VACÍO**. Sólo aparece en prosa
(drafts del paper, `main.tex`).

Lo que SÍ dice `docs/experiments/F1_replay_log.csv`, fila **DAY82-002** (bigFlows, el
corpus de la claim):
```
Fast Detector: 31.065 alertas     ← NO 2.517
ML: 2x attacks_detected (conf>=0.65), 7x label=1
FP: FP_UNKNOWN
notes: "IPs 172.16.133.x no en binetflow Neris — ground truth desconocido"
```
**El propio log dice `ground truth desconocido`.** No se pueden contar falsos positivos
sobre un corpus sin ground truth.

Y la fila **DAY82-001** (smallFlows): `F1 = 0.3818`, con la nota *"ML correcto
(attacks=0)"*. **Se anotó `attacks=0` como CORRECTO porque el tráfico era benigno.**
Ahora sabemos que el ML dice `attacks=0` **también sobre ataques**. En DAY 82,
`attacks=0` era indistinguible de una cabeza ciega, y nadie tenía cómo saberlo.

### El diagnóstico: ERROR DE CATEGORÍA, no de aritmética

El paper compara **alertas del Fast Detector** (`[FAST ALERT]`, umbral de *log*) contra
**bloqueos del pipeline** (umbral de *producción*, 0.65). **Dos métricas distintas,
presentadas como un antes/después causal.**

Los *"0 bloqueos en bigFlows"* de Config C son **reales** — pero porque `fast_score < 0.65`
en esos flujos, **no porque el ML filtrara nada.**

Y el paper YA lo admite en §8.6: *"Only Config C was fully validated end-to-end;
Config A and B are partial."* **Config A y Config C nunca se compararon flujo a flujo.**

### 🟢 LO QUE SÍ SE SOSTIENE — protegerlo

**F1 = 0.9985 / Recall = 1.0000 sobre CTU-13 Neris es del FAST DETECTOR**, y el paper
**ya lo declara honestamente** en la nota metodológica de §8.1:
*"`calculate_f1_neris.py` mide alertas del Fast Detector (`[FAST ALERT]` en sniffer.log)"*.
**Ese resultado está medido, tiene script, tiene log, y es reproducible.
El Fast Detector FUNCIONA.** No lo tocamos.

### 🔑 Y EL NOISY-OR TAMPOCO ES LA SOLUCIÓN A ESTO (importante)

Alonso, DAY 217: *"la función max es la que queremos sustituir por el noisy-OR"*.
Correcto — **pero el noisy-OR TAMPOCO REDUCE.**

`P = 1 − ∏(1 − rᵢ·sᵢ)` ⟹ **`P ≥ rᵢ·sᵢ` para cada término.** También monótono creciente.
**Agregar evidencia nunca la resta.**

⟹ Si lo que se quiere es que el ML **SUPRIMA** falsos positivos del fast, hace falta un
operador que pueda **BAJAR** el score: AND probabilístico, o veto explícito. **El paper
ya lo apunta en §11.4: "Alternative AND-based consensus policies are planned (ADR-007)."**

**ADR-007 es la respuesta a la claim del paper. El noisy-OR es la respuesta a OTRA
pregunta** (agregar N cabezas de sospecha en L3). **Dos operadores, dos problemas. No
confundirlos.**

### Qué hacer con esto (DAY 218, en frío)

1. **Localizar el experimento del 2.517.** Si no existe → el número sale del paper.
2. **Reescribir la claim** para decir lo que se midió de verdad: el Fast Detector produce
   FPR=6,61% en bigFlows; el ML, en su estado actual, **no lo corrige** — y ahora sabemos
   por qué (extractor roto + operador `max` que no puede reducir).
3. **La sección de DAY 216 encaja aquí**, no como apéndice: **como la EXPLICACIÓN de por
   qué la claim del ML era incorrecta.** El paper pasa de *"tenemos un ensemble que
   suprime FP"* a *"creíamos tenerlo; medimos; no lo teníamos; aquí está la causa raíz
   con `file:line`, y aquí está la reparación"*. Más difícil de escribir. **Mucho más fuerte.**
4. **Los datos crudos están en el chat de DAY 217.** Recuperables.

---

## ⚠️ EL RESTO — LEE ESTO PRIMERO

👉 **`docs/debt/DEBT-FEATURE-EXTRACTOR-L1-BROKEN-001.md`** — el hallazgo de DAY 216.
👉 **Anexo DAY 216 del PLAN DE CAMPAÑA** — falsifica H5 y H7, vindica H6.

**En una frase:** el modelo L1 es perfecto sobre CIC-IDS2017 (200/200 DDoS, 0/200 FP,
verificado contra el ONNX de producción). El pipeline no detecta NADA (0/100 ataques
sintéticos). Causa raíz PROBADA: `ml-detector/src/feature_extractor.cpp` entrega
**5 de 23 features incorrectas**.

### 🔴 CORRECCIÓN PENDIENTE AL DEBT (hacer YA)
El documento dice **6 features rotas**. **Son 5.** Error de Claude:
- `[9]` y `[18]` son **CORRECTAS**, no rotas.
- **`[12]`** (`total_backward_bytes` → id 13 `Subflow Bwd Bytes`) — **ROTA**, faltaba.

**Las 5 definitivas: `[1]`, `[8]`, `[12]`, `[14]`, `[15]`.** Coinciden EXACTAMENTE con las
5 que el protobuf no transporta como escalar. No fue descuido: fue un apaño ante un
contrato incompleto.

---

## ✅ HALLAZGO DE DAY 217 — el dato EXISTE, el cable está suelto

```protobuf
repeated double general_attack_features = 102;  // 23 features para RF general
```

**El campo lleva ahí desde diciembre y NUNCA se ha rellenado.** Nadie hace
`add_general_attack_features(...)`. `feature_logger.cpp` sólo LEE. Y
**`ml-detector/src/contract_validator.cpp.backup:78` YA AVISABA**:
*"Missing: general_attack_features (array empty)"* — **el validador que lo habría cazado
está en un `.backup`.**

El sniffer **SÍ calcula** 4 de las 5 huérfanas y **las tira**:
`SUBFLOW_FWD_BYTES` (59), `SUBFLOW_BWD_BYTES` (61), `SUBFLOW_FWD_PACKETS` (58),
`INIT_FWD_WIN_BYTES` (68). Sólo falta `act_data_pkt_fwd`.

⟹ **NO hay que tocar el `.proto`.** Reparación de días, no semanas.

---

## 📦 ESTADO DEL ÁRBOL

```
Rama: fix/verdict-multihead-honest
Commits de hoy:
  a032b38d  docs DAY 216
  9b58fd6e  paso 1/5 — contrato L1  (⚠️ el test se commiteó VACÍO)
  1855e901  (deuda flaky)
  5b494d90  fix: test_l1_feature_contract iba vacío en 9b58fd6e  ← EL BUENO

MODIFICADO SIN COMMITEAR — instrumentación DAY 216 (9 contadores):
  ml-detector/include/zmq_handler.hpp
  ml-detector/src/zmq_handler.cpp
  ⟹ SALVADO EN: docs/day216_instrumentation.patch (verificado con `git apply --check` ✅)
  NO commitear (decisión Alonso: parche a fichero, no a rama).
  ⚠️ OJO con `git commit -a`: se los llevaría.

STASH — NO LO PIERDAS:
  stash@{0}: On master: commit2-noisy-or WIP   ← header + tests, VÁLIDOS
  stash@{1}: WIP on day204/emecas-plus-plus-target
  stash@{2}: WIP on main
```

---

## ▶️ PASO 2 de 5 — `ACT_DATA_PKT_FWD` en el sniffer

```zsh
git log --oneline -3 && git status --short
make common-test            # debe dar 14/14
```

**Definición CICFlowMeter:** paquetes forward con ≥ 1 byte de payload TCP.

**VERIFICADO** (`sniffer/include/flow_manager.hpp:80,83`): `fwd_lengths[i]` y
`fwd_header_lengths[i]` se rellenan en el MISMO bloque, MISMO paquete ⟹ **alineados
índice a índice.** Implementación EXACTA, no aproximada. Sin tocar eBPF, sin inventar
umbrales.

```cpp
// sniffer/src/userspace/feature_extractor.cpp
double FeatureExtractor::extract_act_data_pkt_fwd(const FlowStatistics& flow) const {
    const std::size_t n = std::min(flow.fwd_lengths.size(),
                                   flow.fwd_header_lengths.size());
    std::size_t count = 0;
    for (std::size_t i = 0; i < n; ++i) {
        if (flow.fwd_lengths[i] > flow.fwd_header_lengths[i]) ++count;
    }
    return static_cast<double>(count);
}
```

⚠️ **`ACT_DATA_PKT_FWD` va al FINAL del enum** (índice **83**), NUNCA en medio: el enum es
posicional y `ddos_features` (83) depende de él. **`FEATURE_COUNT`: 83 → 84.**

Test unitario: flujo con 3 paquetes fwd (2 con payload, 1 puro ACK) → debe dar 2.
**RED→GREEN o no vale.**

---

## 🗺️ EL MAPA — 23 features L1 → enum del sniffer (VERIFICADO índice a índice)

Vive en `common/include/argus/l1_feature_contract.hpp` (commit `5b494d90`).

```
 L1  contrato                       FeatureIndex del sniffer
 --  ---------------------------    ------------------------------
  0  Packet Length Std              PACKET_LEN_STD          (15)
  1  Subflow Fwd Bytes              SUBFLOW_FWD_BYTES       (59)  ✅ existe
  2  Fwd Packet Length Max          FWD_LEN_MAX             (33)
  3  Avg Fwd Segment Size           AVG_FWD_SEGMENT_SIZE    (79)
  4  ACK Flag Count                 ACK_FLAG_COUNT          (21)
  5  Packet Length Variance         PACKET_LEN_VAR          (16)
  6  PSH Flag Count                 PSH_FLAG_COUNT          (20)
  7  Bwd Packet Length Max          BWD_LEN_MAX             (36)
  8  act_data_pkt_fwd               🔴 PASO 2 — implementar (índice 83)
  9  Total Length of Fwd Packets    FWD_LEN_TOT             (35)  ← NO SBYTES
 10  Fwd Packet Length Std          FWD_LEN_STD             (57)
 11  Fwd Packets/s                  SRATE                   (25)
 12  Subflow Bwd Bytes              SUBFLOW_BWD_BYTES       (61)  ✅ existe
 13  Destination Port               🟡 de la 5-tupla, no del enum
 14  Init_Win_bytes_forward         INIT_FWD_WIN_BYTES      (68)  ✅ existe
 15  Subflow Fwd Packets            SUBFLOW_FWD_PACKETS     (58)  ✅ existe
 16  Fwd IAT Min                    FWD_IAT_MIN             (46)
 17  Packet Length Mean             PACKET_LEN_MEAN         (14)
 18  Total Length of Bwd Packets    BWD_LEN_TOT             (39)  ← NO DBYTES
 19  Bwd Packet Length Mean         DMEAN                   (7)
 20  Bwd Packet Length Min          BWD_LEN_MIN             (37)
 21  Flow Duration                  DURATION                (0)
 22  Flow Packets/s                 FLOW_PKTS_PER_SEC       (75)
```

**AMBIGÜEDADES RESUELTAS (DAY 217), no reabrir:**
- **idx 9 → `FWD_LEN_TOT`, no `SBYTES`.** `extract_fwd_len_tot()` =
  `calculate_sum(flow.fwd_lengths)` (`feature_extractor.cpp:221`), y
  `fwd_lengths[i] = pkt.packet_len` (`flow_manager.hpp:80`) = paquete completo. Es la
  semántica de CIC-IDS2017.
- **idx 18 → `BWD_LEN_TOT`, no `DBYTES`.** Idem (`:233`).

---

## 📋 PLAN DE REPARACIÓN — 5 pasos

1. ✅ **HECHO (`5b494d90`)** — contrato L1 + test de propiedad + targets `common-*`.
2. 🔜 **`ACT_DATA_PKT_FWD` en el sniffer.**
3. **El sniffer RELLENA `general_attack_features`** recorriendo el mapa.
4. **El ml-detector LEE el campo 102.** `extract_level1_features` → **borrar la
   reconstrucción entera**. Ya no reconstruye: lee.
5. **El injector RELLENA el campo 102** (`tools/synthetic_sniffer_injector.cpp`).
   ⚠️ **SIN ESTO SEGUIREMOS MIDIENDO UN PIPELINE CIEGO Y CREYENDO QUE LO ARREGLAMOS.**

**De propina:** reactivar `contract_validator` (está en `.backup` y ya sabía la verdad).

**Test de cierre (el que nunca existió):**
> *N filas de CIC-IDS2017 → protobuf → detector → ONNX reproducen la etiqueta del CSV.*
**RED→GREEN obligatorio.**

---

## 🩸 DEUDAS

### `DEBT-TEST-AUTONOMY-PUBLISHER-FLAKY-001` — ⚠️ TASA MEDIDA: 1/20 (~5%)
`common/tests/test_autonomy_publisher.cpp:86` (`recv_two`, 3er caso).
**20 iteraciones de `ctest` secuencial → `.................X..`** — **REPRODUCIDO.**
`ctest -j8`: 14/14 (paralelo NO lo empeora ⟹ no es carga, es timing absoluto).
Aislado (`-R`): 3/3.
El socket `/tmp/test-autonomy-publisher.sock` **PERSISTE entre runs** y el test no lo limpia.
Sospecha: slow joiner ZMQ (PUB `bind()` → SUB `connect()` sin sincronización).
Regla del proyecto: `bind()` antes de `connect()`.

> **Con `common/` en el gate, EMECAS fallaría ~1 de cada 20 runs.** Vivo desde el 27-may.
> Sobrevivió porque `common/` **no tenía target propio** y su `ctest` estaba escondido
> dentro de `test-alert-client`. **La deuda del Makefile y la del flaky se protegían
> mutuamente.**

> ACTUALIZACION
> test_autonomy_publisher.cpp:86 (recv_two, 3er caso).
> Tasa medida: 1/20 (~5%) en ctest secuencial. ctest -j8: 14/14. Aislado (-R): 3/3.
> El socket /tmp/test-autonomy-publisher.sock persiste entre runs y el test no lo limpia.
> Sospecha: slow joiner ZMQ (PUB bind() → SUB connect() sin sincronización).
> Con common/ en el gate, EMECAS fallaría ~1 de cada 20 runs.
>
> 
### `DEBT-MAKEFILE-COMMON-NO-TARGET-001` (mitigado, no cerrado)
`common/` se compilaba como efecto secundario de `test-dual-compilation`,
`test-e2e-vault` y `vault-client-test`; su `ctest` vivía en `test-alert-client` (`:1175`).
Mitigado con `common-build`/`common-test`. **Sigue sin estar en el gate por derecho propio.**

### `DEBT-STATS-E2E-COUNTERS-001` (menor)
`check_e2e_pipeline.py` reporta `received 0 → 0` con 100 eventos procesados de verdad.

---

## 🔧 REPRODUCIR LAS MEDICIONES DE DAY 216

**`etcd-server` DEBE estar arrancado o el detector aborta.**

```zsh
make etcd-server-start
vagrant ssh -c 'sudo truncate -s 0 /vagrant/logs/lab/ml-detector.log'   # ¡SIEMPRE! (usa >>)
make ml-detector-start
vagrant ssh -c 'pgrep -af ml-detector'    # NO SIGAS SI SALE VACÍO

vagrant ssh -c "sudo env LD_LIBRARY_PATH=/usr/local/lib /vagrant/tools/build-debug/synthetic_sniffer_injector 100 10"           # BENIGN
vagrant ssh -c "sudo env LD_LIBRARY_PATH=/usr/local/lib /vagrant/tools/build-debug/synthetic_sniffer_injector 100 10 --attack"  # ATTACK

sleep 65
vagrant ssh -c 'grep -A 14 "DBG DEUDA-3" /vagrant/logs/lab/ml-detector.log | tail -15'
vagrant ssh -c 'tmux kill-session -t ml-detector'   # MÁTALO al acabar
```

**BASELINE DAY 216 (extractor ROTO) — comparar tras la reparación:**
```
                   ruido          ataque
l1_class1      =      0               0     ← L1 NUNCA dice ATTACK
traffic_class1 =    100             100     ← constante, prob 0.96 ± 0.005
internal_class1=     69               0     ← INVERTIDA: dispara en ruido, calla en ataque
```
**Tras el paso 5, `l1_class1` DEBE subir con `--attack`.** Criterio de éxito, escrito
ANTES de medir.

---

## 🩸 TRAMPAS QUE COSTARON TIEMPO (no repetirlas)

- **`git add` y LUEGO editar** ⟹ se commitea la versión vieja. Pasó con
  `test_l1_feature_contract.cpp`: **`9b58fd6e` commiteó el fichero VACÍO** (blob
  `e69de29b` = fichero vacío en git). El commit afirmaba tener una red y no la tenía.
  ⟹ **REGLA NUEVA: tras commitear un fichero nuevo, `git show HEAD:<fichero> | wc -l`.**
- **`grep --include='*.json'` SIN comillas simples** ⟹ zsh aborta el comando ENTERO.
- **`#` NO es comentario para git.** `git stash pop  # nota` → *"Too many revisions"*.
- **`fprintf` en el `while` sin `last_stats_report_ = now`** ⟹ **128 MB de log.**
- **`-Werror=format=`**: un `fprintf` por clase de formato. No mezclar `%llu` y `%.2f`.
- **El detector NO es systemd**: vive en tmux (Makefile `:661-662`). `journalctl` sale
  vacío SIN error. stderr → `/vagrant/logs/lab/ml-detector.log`.
- **Binario en `build-debug/`, no en `build/`.**
- **`Error 124` = `timeout(1)`** (`test-e2e-synthetic-full:1340`).
- **CMake hay que reconfigurar** para ver un test nuevo. Ante la duda: `rm -rf common/build`.
- **`ctest` NO muestra stdout de los tests que pasan.** "Passed" = `exit=0`, nada más.
  Para ver que el test hace lo que dice: `ctest -R <nombre> -V`.
- **Localizar por CONTENIDO, no por número de línea.** Los parches desplazan todo.

---

## 🎯 DECISIONES QUE SOBREVIVEN

- **Commit 2 (noisy-OR) APARCADO**, no cancelado. **Y ojo: el noisy-OR NO suprime FP**
  (es monótono creciente, como el `max`). Resuelve OTRO problema: agregar N cabezas de
  sospecha en L3. **La supresión de FP necesita ADR-007 (AND/veto).**
- **Traffic = GUARD, no término del producto** (opción (a), Alonso DAY 216).
- **`ddos`/`ransomware` a `reliability = 0.0`.** Factor neutro. Reconectar = un peso.
- **`l3_combined_seal` con clave propia** en config.
- **La P gobierna la FUERZA de la evidencia, NUNCA la ETIQUETA.**
- **MITRE es imprescindible y va DESPUÉS del extractor.**
- **DEBT-VERDICT-WEIGHTS-CALIBRATION-001 sigue INDECIDIBLE** hasta que las cabezas vean.

---

## 📐 EL PATRÓN — cinco casos, y va al §6 del paper

*El pipeline funcionando, produciendo números, sin significado.*

1. `entropy` del ransomware = varianza de longitud ÷ 100.000 (DEBT-RANSOMWARE-ML-HEAD-INERT-001).
2. `level3_web`/`level3_internal` nunca parseados del JSON (DAY 215, `8e03a264`).
3. 5/23 features de L1 duplicadas o constantes (DAY 216).
4. **`test_l1_feature_contract.cpp` commiteado VACÍO** (DAY 217) — un commit que afirmaba
   tener una red y no la tenía. **Lo produjimos NOSOTROS, con toda la atención puesta,
   sabiendo lo que cazábamos.**
5. **El `max()` que no puede suprimir FP** (DAY 217) — una claim del abstract que la
   aritmética del propio paper prohíbe.

**Cinco instancias ⟹ no es mala suerte, es una CLASE de defecto.** Ninguna la cazó el
testing convencional (13 tests verdes, EMECAS+++ verde, libFuzzer 2.4M runs). Todas se
cazaron **midiendo el verde en vez de celebrarlo**.

**Y el caso 4 es el más elocuente:** no basta con ser cuidadoso. Hace falta **verificar el
artefacto, no la intención.**

---

## FEDER
Go/no-go **~1 agosto 2026**. Deadline **22 septiembre 2026**.
*"No pienso entregar nada que no esté bien fundamentado. El pipeline tiene que
funcionar bien."* — Alonso, DAY 216.