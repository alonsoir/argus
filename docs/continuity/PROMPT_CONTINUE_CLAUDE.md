# PROMPT DE CONTINUIDAD — DAY 217 → 218
## Rama `fix/verdict-multihead-honest` · REPARACIÓN DEL EXTRACTOR L1, paso 1 de 5 HECHO

> Memoria de sesión. Claude no recuerda entre ventanas. La fuente de verdad del PLAN
> sigue siendo el PLAN. Aquí sólo el estado operativo.

---

## ⚠️ AL ABRIR — LEE ESTO PRIMERO

👉 **`docs/debt/DEBT-FEATURE-EXTRACTOR-L1-BROKEN-001.md`** — el hallazgo de DAY 216.
👉 **Anexo DAY 216 del PLAN DE CAMPAÑA** — falsifica H5 y H7, vindica H6.

**En una frase:** el modelo L1 es perfecto sobre CIC-IDS2017 (200/200 DDoS, 0/200 FP,
verificado contra el ONNX de producción). El pipeline no detecta NADA (0/100 ataques
sintéticos). Causa raíz PROBADA: `ml-detector/src/feature_extractor.cpp` entrega
**5 de 23 features incorrectas** a L1. **No hay tres cabezas rotas: hay un extractor
que rompe tres cabezas.**

### 🔴 CORRECCIÓN PENDIENTE AL DEBT (hacer YA, antes de que llegue al paper)
El documento `DEBT-FEATURE-EXTRACTOR-L1-BROKEN-001.md` dice **6 features rotas**.
**Son 5.** Error de Claude, cazado al cruzar contra el protobuf:
- `[9]` (`total_forward_bytes` → id 10 `Total Length of Fwd Packets`) — **CORRECTA**, no rota.
- `[18]` (`total_backward_bytes` → id 19 `Total Length of Bwd Packets`) — **CORRECTA**, no rota.
- **`[12]`** (`total_backward_bytes` → id 13 **`Subflow Bwd Bytes`**) — **ROTA**, y no estaba en la lista.

**Las 5 rotas, definitivas:** `[1]`, `[8]`, `[12]`, `[14]`, `[15]`.
Y coinciden EXACTAMENTE con las 5 features que el protobuf **no transporta como escalar**.
No fue descuido: fue un apaño ante un contrato incompleto.

---

## ✅ HALLAZGO CENTRAL DE DAY 217 — el dato EXISTE, el cable está suelto

```protobuf
repeated double general_attack_features = 102;  // 23 features para RF general
```

**El campo lleva ahí desde diciembre y NUNCA se ha rellenado.** Nadie hace
`add_general_attack_features(...)` en código real. `feature_logger.cpp` sólo LEE.
Y **`ml-detector/src/contract_validator.cpp.backup:78` ya avisaba**:
*"Missing: general_attack_features (array empty)"* — **el validador que lo habría cazado
está en un `.backup`.**

El sniffer **SÍ calcula** 4 de las 5 huérfanas y las tira:
`SUBFLOW_FWD_BYTES` (59), `SUBFLOW_BWD_BYTES` (61), `SUBFLOW_FWD_PACKETS` (58),
`INIT_FWD_WIN_BYTES` (68). Sólo falta implementar `act_data_pkt_fwd`.

⟹ **NO hay que tocar el `.proto`.** La reparación es de días, no semanas.

---

## 📦 ESTADO DEL ÁRBOL

```
Rama: fix/verdict-multihead-honest
Último commit: 9b58fd6e  (paso 1/5 — contrato L1 + test + targets common-*)
Anterior:      a032b38d  (docs DAY 216)

MODIFICADO SIN COMMITEAR — instrumentación DAY 216 (9 contadores):
  ml-detector/include/zmq_handler.hpp
  ml-detector/src/zmq_handler.cpp
  ⟹ SALVADO EN: docs/day216_instrumentation.patch (7281 B, verificado con
     `git apply --check` ✅). NO commitear estos dos ficheros (decisión Alonso:
     el parche va a fichero, no a rama — evita choques en el merge).
  ⚠️ OJO con `git commit -a`: se los llevaría.

STASH — NO LO PIERDAS:
  stash@{0}: On master: commit2-noisy-or WIP   ← header + tests de commit 2, VÁLIDOS
  stash@{1}: WIP on day204/emecas-plus-plus-target
  stash@{2}: WIP on main
```

---

## ▶️ PRIMER COMANDO DEL DÍA — PASO 2 de 5

```zsh
git log --oneline -3 && git status --short
make common-test            # debe dar 14/14 (incl. test_l1_feature_contract)
```

### PASO 2 — `ACT_DATA_PKT_FWD` en el sniffer

**Definición CICFlowMeter:** *paquetes forward con ≥ 1 byte de payload TCP*.

**VERIFICADO** (`sniffer/include/flow_manager.hpp:80,83`): `fwd_lengths[i]` y
`fwd_header_lengths[i]` se rellenan en el MISMO bloque, MISMO paquete ⟹ **están
alineados índice a índice.** La implementación es EXACTA, no aproximada. No hay que
tocar el datapath eBPF ni inventar umbrales.

```cpp
// sniffer/src/userspace/feature_extractor.cpp
// act_data_pkt_fwd (CIC-IDS2017): paquetes forward con >= 1 byte de payload TCP.
// fwd_lengths[i] y fwd_header_lengths[i] son el MISMO paquete (flow_manager.hpp:80,83).
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

⚠️ **`ACT_DATA_PKT_FWD` va al FINAL del enum** (`sniffer/include/feature_extractor.hpp`,
índice **83**), NUNCA en medio: el enum es posicional y `ddos_features` (83) depende de él.
**`FEATURE_COUNT` pasa de 83 a 84.**

Test unitario: flujo con 3 paquetes fwd (2 con payload, 1 puro ACK) → debe dar 2.
**RED→GREEN o no vale.**

---

## 🗺️ EL MAPA — 23 features L1 → enum del sniffer (VERIFICADO índice a índice, DAY 216)

Vive en `common/include/argus/l1_feature_contract.hpp` (commit `9b58fd6e`), al final.

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

**AMBIGÜEDADES RESUELTAS (DAY 217), no volver a abrirlas:**
- **idx 9 → `FWD_LEN_TOT`, no `SBYTES`.** `extract_fwd_len_tot()` =
  `calculate_sum(flow.fwd_lengths)` (`feature_extractor.cpp:221`), y
  `fwd_lengths[i] = pkt.packet_len` (`flow_manager.hpp:80`) = longitud del paquete
  completo. Es la semántica de CIC-IDS2017.
- **idx 18 → `BWD_LEN_TOT`, no `DBYTES`.** Idem (`:233`).

---

## 📋 PLAN DE REPARACIÓN — 5 pasos

1. ✅ **HECHO (`9b58fd6e`)** — `common/include/argus/l1_feature_contract.hpp` + test de
   propiedad + targets `common-build` / `common-test`.
2. 🔜 **`ACT_DATA_PKT_FWD` en el sniffer** (enum al final + función + test unitario).
3. **El sniffer RELLENA `general_attack_features`** recorriendo el mapa del header.
4. **El ml-detector LEE el campo 102.** `extract_level1_features` → **borrar la
   reconstrucción entera**. Ya no reconstruye: lee.
5. **El injector RELLENA el campo 102** (`tools/synthetic_sniffer_injector.cpp`).
   ⚠️ **SIN ESTO SEGUIREMOS MIDIENDO UN PIPELINE CIEGO Y CREYENDO QUE LO ARREGLAMOS.**

**De propina:** reactivar `contract_validator` (está en `.backup` y ya sabía la verdad).

**Test de cierre (el que nunca existió):**
> *N filas de CIC-IDS2017 → protobuf → detector → ONNX reproducen la etiqueta del CSV.*
**RED→GREEN obligatorio:** romper una feature a propósito debe ponerlo ROJO.

---

## ✅ PASO 1 — lo que quedó (commit `9b58fd6e`)

- `common/include/argus/l1_feature_contract.hpp` — **fuente de verdad del orden**.
  El campo 102 es `repeated double`: POSICIONAL, SIN NOMBRES. Si productor y consumidor
  no comparten el orden, el ONNX come basura ordenada y devuelve una constante confiada.
- `common/tests/test_l1_feature_contract.cpp` — **test de PROPIEDAD**: cada nombre del
  header debe aparecer en `rf_23_features.json`, **y EN ORDEN** (cursor que sólo avanza).
  **RED→GREEN verificado:** reordenar dos features del JSON → ROJO con
  *"EXISTE, pero FUERA DE ORDEN"*. 4/4 PASS con el JSON íntegro.
- Makefile: **`common-build`** y **`common-test`**.

---

## 🩸 DEUDAS NUEVAS (DAY 217)

### `DEBT-TEST-AUTONOMY-PUBLISHER-FLAKY-001` — ⚠️ NO DETERMINISTA
`common/tests/test_autonomy_publisher.cpp:86` (`recv_two`, 3er caso).
**Observado ROJO UNA VEZ** dentro de la suite completa. Después: **3/3 aislado y 5/5 en
suite, todos verdes.** Sospecha: carrera ZMQ slow-joiner (el PUB hace `bind()` por caso;
el SUB puede no haber conectado). Regla del proyecto: `bind()` antes de `connect()`.

> **LECCIÓN (va al paper):** cinco verdes NO prueban determinismo. Un rojo SÍ prueba
> no-determinismo. Asimetría popperiana. **Si no lo llegamos a ver, hoy escribiríamos
> "common-test: 14/14, determinista" — con 5 ejecuciones de evidencia a favor, y sería
> FALSO.** Es el TERCER tipo de "verde que miente" de esta semana, y es distinto de los
> otros dos: allí el verde era *estable y falso*; aquí es *inestable y engañosamente
> estable*. Un CI que corre una vez por commit no lo vería NUNCA.

> ACTUALIZACION
> test_autonomy_publisher.cpp:86 (recv_two, 3er caso). 
> Tasa medida: 1/20 (~5%) en ctest secuencial. ctest -j8: 14/14. Aislado (-R): 3/3. 
> El socket /tmp/test-autonomy-publisher.sock persiste entre runs y el test no lo limpia. 
> Sospecha: slow joiner ZMQ (PUB bind() → SUB connect() sin sincronización). 
> Con common/ en el gate, EMECAS fallaría ~1 de cada 20 runs.
> 
### `DEBT-MAKEFILE-COMMON-NO-TARGET-001` (menor, ya mitigado)
`common/` no tenía target propio: se compilaba como **efecto secundario** de
`test-dual-compilation`, `test-e2e-vault` y `vault-client-test`, y su `ctest` vivía dentro
de **`test-alert-client`** (`:1175`). Mitigado con `common-build`/`common-test`, pero
**`common/` sigue sin estar en el gate por derecho propio.** Revisar si `test-all` lo cubre.

### `DEBT-STATS-E2E-COUNTERS-001` (menor)
`check_e2e_pipeline.py` reporta `ml-detector: received 0 → 0` mientras los contadores
internos cuentan 100 eventos procesados. **Los contadores del snapshot mienten.**

---

## 🔧 CÓMO REPRODUCIR LAS MEDICIONES DE DAY 216

**`etcd-server` DEBE estar arrancado o el detector aborta**
(`❌ [etcd] Failed to initialize - REQUIRED for ml-detector`).

```zsh
make etcd-server-start
vagrant ssh -c 'sudo truncate -s 0 /vagrant/logs/lab/ml-detector.log'   # ¡SIEMPRE! (usa >>)
make ml-detector-start
vagrant ssh -c 'pgrep -af ml-detector'    # NO SIGAS SI SALE VACÍO

# BENIGN (ruido uniforme rand_float(0,1)):
vagrant ssh -c "sudo env LD_LIBRARY_PATH=/usr/local/lib /vagrant/tools/build-debug/synthetic_sniffer_injector 100 10"
# ATTACK (DDoS signature):
vagrant ssh -c "sudo env LD_LIBRARY_PATH=/usr/local/lib /vagrant/tools/build-debug/synthetic_sniffer_injector 100 10 --attack"

sleep 65   # el volcado sale cada stats_interval (60s)
vagrant ssh -c 'grep -A 14 "DBG DEUDA-3" /vagrant/logs/lab/ml-detector.log | tail -15'
vagrant ssh -c 'tmux kill-session -t ml-detector'   # MÁTALO al acabar
```

**Baseline DAY 216 (con el extractor ROTO) — para comparar tras la reparación:**
```
                   ruido          ataque
l1_class1      =      0               0     ← L1 NUNCA dice ATTACK
traffic_class1 =    100             100     ← constante, prob 0.96 ± 0.005
internal_class1=     69               0     ← INVERTIDA: dispara en ruido, calla en ataque
```
**Tras el paso 5, `l1_class1` DEBE subir con `--attack`.** Ese es el criterio de éxito.

---

## 🩸 TRAMPAS QUE COSTARON TIEMPO (no repetirlas)

- **`grep --include='*.json'` SIN comillas simples** ⟹ zsh intenta expandir el glob, no
  encuentra, y **ABORTA EL COMANDO ENTERO**. Pasó 5 veces seguidas.
- **`#` NO es comentario para git.** `git stash pop   # comentario` → *"Too many
  revisions specified"*. El comando NO se ejecuta.
- **`fprintf` en el `while` sin `last_stats_report_ = now`** ⟹ **128 MB de log.**
- **`-Werror=format=`**: un `fprintf` por clase de formato. No mezclar `%llu` y `%.2f`.
- **El detector NO es systemd**: vive en tmux (Makefile `:661-662`). `journalctl` sale
  vacío SIN error. stderr → `/vagrant/logs/lab/ml-detector.log`.
- **Binario en `build-debug/`, no en `build/`.**
- **`Error 124` = `timeout(1)`** (`test-e2e-synthetic-full:1340`).
- **CMake hay que reconfigurar** para que un test nuevo aparezca. Ante la duda:
  `rm -rf common/build` y recompilar.
- **`ctest` NO muestra el stdout de los tests que pasan.** "Passed" sólo significa
  `exit=0`. Para ver que el test hace lo que dice: `ctest -R <nombre> -V`.
- **Localizar por CONTENIDO, no por número de línea.** Los parches desplazan todo.

---

## 🎯 DECISIONES QUE SOBREVIVEN

- **Commit 2 (noisy-OR) APARCADO**, no cancelado. Se retoma cuando las cabezas discriminen.
- **Traffic = GUARD, no término del producto** (opción (a), Alonso DAY 216).
- **`ddos`/`ransomware` a `reliability = 0.0`.** Factor neutro. Reconectar = un peso.
- **`l3_combined_seal` con clave propia** en config.
- **La P gobierna la FUERZA de la evidencia, NUNCA la ETIQUETA.**
- **MITRE es imprescindible y va DESPUÉS del extractor.** Con las cabezas ciegas, MITRE
  tampoco mediría nada.
- **DEBT-VERDICT-WEIGHTS-CALIBRATION-001 sigue INDECIDIBLE** hasta que las cabezas vean.

---

## FEDER
Go/no-go **~1 agosto 2026**. Deadline **22 septiembre 2026**.
*"No pienso entregar nada que no esté bien fundamentado. El pipeline tiene que
funcionar bien."* — Alonso, DAY 216.