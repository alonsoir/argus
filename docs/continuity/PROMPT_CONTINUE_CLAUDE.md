# PROMPT DE CONTINUIDAD — DAY 218 → 219
## Rama `fix/verdict-multihead-honest`

> Memoria de sesión. Claude no recuerda entre ventanas. La fuente de verdad del PLAN
> sigue siendo el PLAN. Aquí sólo el estado operativo.

---

## 📕 LEE ESTO PRIMERO — EL DOCUMENTO DEL DÍA

👉 **`docs/debt/DAY218_FINDINGS.md`** (commit `ebd3cac9`) — **SIETE DEUDAS NUEVAS,
todas con `file:line`, todas PRE-FEDER.**

**Van a `docs/BACKLOG.md` en rojo** — mañana o pasado, tras el merge a `main`.
(Recordatorio: `BACKLOG.md` y `README.md` NO se tocan hasta el merge.)

👉 **`docs/debt/DEBT-FEATURE-EXTRACTOR-L1-BROKEN-001.md`** — el hallazgo de DAY 216.
👉 **Anexo DAY 216 del PLAN DE CAMPAÑA.**
👉 El hallazgo del paper (DAY 217): **la claim del `max()` es aritméticamente imposible.**
`max(a,b) ≥ a` SIEMPRE. El ML no puede suprimir FP. Y el noisy-OR TAMPOCO
(monótono creciente). Hace falta **ADR-007** (AND/veto). **NO tocar el LaTeX aún.**

---

## 🎯 QUÉ PASÓ EN DAY 218

**El objetivo era el PASO 2. No se llegó.** En su lugar se auditaron los
**INSTRUMENTOS DE MEDIDA** del proyecto.

**Y eso respondió la pregunta de los 200 días:**
*¿cómo sobrevivió el extractor roto a 13 tests verdes, EMECAS+++ y libFuzzer 2.4M runs?*

> **Porque NADIE ESTABA MIDIENDO AHÍ.**
> El `FeatureExtractor` (83 features) **nunca tuvo test**. Cinco tests del sniffer se
> compilaban y **nunca se ejecutaban**. El gate de `test-components` **no puede ponerse
> en rojo** (`|| echo` traga el exit code). Y de los 11 tests que sí corrían, **OCHO
> prueban la Variante B — que no computa features de flujo en absoluto.**

**El termómetro estaba bien calibrado y apuntando al componente equivocado.**

---

## 📦 COMMITS DE DAY 218

```
5d9bd43e  fix(common): DEBT-TEST-AUTONOMY-PUBLISHER-FLAKY-001 — handshake real PUB/SUB
92ce8a09  test(sniffer): DEBT-SNIFFER-TESTS-NOT-REGISTERED-001 — registrar 5 huérfanos
ebd3cac9  docs(DAY 218): DAY218_FINDINGS.md — 7 deudas, todas pre-FEDER
<nuevo>   test(sniffer): PASO 2 RED — act_data_pkt_fwd + primera suite del FeatureExtractor
<nuevo>   chore(common): include-what-you-use — cstring para std::strlen
<este>    docs(DAY 218): prompt de continuidad
```

**⚠️ SIGUE SIN COMMITEAR, A PROPÓSITO:**
```
 M ml-detector/include/zmq_handler.hpp    ← instrumentación DAY 216 (9 contadores)
 M ml-detector/src/zmq_handler.cpp        ← salvada en docs/day216_instrumentation.patch
```
**NUNCA `git add -u` NI `git commit -a`. Se los llevaría.**
Decisión de Alonso: parche a fichero, no a rama. `git apply --check` ✅ verificado.

**STASH — NO LO PIERDAS:**
```
stash@{0}: On master: commit2-noisy-or WIP   ← header + tests, VÁLIDOS
stash@{1}: WIP on day204/emecas-plus-plus-target
stash@{2}: WIP on main
```

---

## 🔴 EL RED QUE HAY QUE RESOLVER MAÑANA — EMPIEZA AQUÍ

```zsh
vagrant ssh -c 'cd /vagrant/sniffer/build-debug && ctest -R test_feature_extractor --output-on-failure'
```

**6/8 PASS. 2 FAIL. El rojo es CORRECTO y es un ACTIVO. No lo borres.**

```
[  OK  ]  5/5 FeatureExtractorUnitTest        ← la sección A (unidad) pasa
[  OK  ]  PureAcksGiveZero_KillsTheEthernetTrap
[FAILED]  PayloadLenReachesFeatureFromSimpleEvent
            features[ACT_DATA_PKT_FWD] == 0, esperado 2
[FAILED]  AlignmentHolds_PayloadVectorTracksFwdLengths
            fwd_lengths.size() == 10   ← ¡metimos 3!
            fwd_payload_lengths.size() == 0
```

### HALLAZGO 1 — **HAY DOS RUTAS DE POBLACIÓN DE `FlowStatistics`**

El `push_back(pkt.payload_len)` se añadió a `FlowStatistics::add_packet()`
(`sniffer/include/flow_manager.hpp`, bloque `if (is_fwd)`).
**Pero `fwd_payload_lengths` sale con `size()==0` mientras `fwd_lengths` tiene datos.**

⟹ **`ShardedFlowManager` NO llama a `FlowStatistics::add_packet()`.** Tiene su propia
implementación que rellena `fwd_lengths` por su cuenta.

**PRIMER COMANDO DE MAÑANA:**
```zsh
grep -n 'fwd_lengths\|add_packet\|payload' sniffer/src/flow/sharded_flow_manager.cpp
```

**Decisión arquitectónica pendiente (NO parchear a ciegas):**
- (a) `ShardedFlowManager::add_packet` delega en `FlowStatistics::add_packet` — **unificar.**
- (b) Duplicar el `push_back` en la ruta shardeada — **rápido, y garantiza que
  volverán a divergir.** Es como nació el bug de las 5 features.

**Recomendación: (a).** La duplicación de la lógica de población ES la causa raíz de
esta clase de defecto. Pero **mirar el código antes de decidir.**

### HALLAZGO 2 — el singleton acumula estado entre tests

`fwd_lengths.size() == 10` habiendo metido 3 paquetes. **3 + 4 + 3 = 10.**
`ShardedFlowManager::instance()` es un singleton; `initialize()` en el `SetUp` **no
limpia los flujos**. Los tres tests de contrato comparten estado.

**Arreglo:** o un `clear()`/`reset()` en el `SetUp`, o una `FlowKey` distinta por test.
La primera es correcta; la segunda esconde el problema.

### 🩸 Y EL CASO 16 DEL PATRÓN — LO PRODUJIMOS HOY

> **`PureAcksGiveZero_KillsTheEthernetTrap` PASÓ EN FALSO.**
> Dio 0 **porque el vector está vacío**, no porque contara ceros.
> **Un verde falso en el test escrito precisamente para cazar verdes falsos.**

**Cuando se arregle el HALLAZGO 1, ese test volverá a ser significativo.**
Hasta entonces, su verde NO VALE. Anotado.

---

## ✅ LO QUE SÍ SE CERRÓ HOY

### `DEBT-TEST-AUTONOMY-PUBLISHER-FLAKY-001` — MITIGADO (`5d9bd43e`)
Causa raíz probada: `connect()` antes de `bind()` + `sleep(300ms)` contra
`reconnect_ivl=100ms` (`autonomy_publisher.cpp:20`). **T3 fallaba porque era el único
caso cuyo mensaje viene de una transición idempotente: sin reintento posible.**
Arreglo: handshake real (`sync_pub_sub`), no `sleep`.
**No reproducido en 40 iteraciones secuenciales EN LA VM.** P(suerte) ≈ 13%.
**NO se declara CERRADO** hasta sobrevivir **3 EMECAS completos**.

### `DEBT-SNIFFER-TESTS-NOT-REGISTERED-001` — REGISTRADO (`92ce8a09`)
5 `add_executable()` sin `add_test()`. **`ctest -N`: 11 → 16 → 17** (con el nuevo).
Al registrarlos apareció un rojo de meses: ver abajo.

### El camino de datos NO ha perdido flujos en 200 días ✅
`sniffer PUSH connect` → `ml-detector PULL bind`. **PUSH/PULL no descarta como PUB/SUB.**
Era la pregunta cara. La respuesta es buena.

### El slow joiner NO sesgó los conteos del paper ✅
`set_final_decision()` (`zmq_handler.cpp:624`) → `csv_writer_->write_event()` (`:685`)
→ **y SÓLO DESPUÉS** `output_socket_->send()` (`:996`). El veredicto se persiste
**aguas arriba del socket**.
**SALVEDAD:** esto prueba que *existía* un registro fiable. **NO prueba que los números
del paper salgan de ahí.** El **`2.517` SIGUE SIN PROCEDENCIA.** Arqueología pendiente.

---

## 🩸 DEUDAS NUEVAS — TODAS EN `docs/debt/DAY218_FINDINGS.md`

| Deuda | P | Qué es |
|---|---|---|
| `PAYLOAD-ANALYZER-PATTERNS-INERT-001` | **P1** | 4/4 tests de detección de patrones devuelven `false`. **SEGUNDA causa independiente de la ceguera del ransomware.** |
| `VARIANT-B-FEATURE-PATH-001` | **P1** | **La Variante B (libpcap) NO computa features de flujo.** `main_libpcap.cpp:110`: *"NetworkSecurityEvent mínimo"*. Amenaza el delta A vs C del paper. |
| `VERDICT-DECIDED-UPSTREAM-001` | **P1** | `zmq_handler.cpp:623` — el detector ya decidió. **POR ESO ADR-007 lleva desde DAY 83 sin implementarse: NO TENÍA DÓNDE VIVIR.** Prerrequisito de ADR-007. |
| `GATE-COMPONENTS-SWALLOWED-EXIT-001` | **P1** | `Makefile:1197,1200,1203,1205` — `\|\| echo` traga el exit code de **los 4 componentes**. **BLOQUEADO** hasta cerrar el rojo del PayloadAnalyzer. |
| `AUTONOMY-SUBSCRIBER-SLOW-JOINER-001` | P2 | Canal de **estado** tratado como **eventos**. Misma anatomía que T3. |
| `DDOS-FEATURES-CONSTANT-001` | P2 | 2/10 features del DDoS son constantes. **Valida `reliability=0.0` de DAY 216.** |
| `SOURCE-TREE-BACKUP-FILES-001` | P2 | 19 `.backup` en un solo dir, 8 dirs de build. **El árbol miente al `grep`.** |
| `PAYLOAD-LEN-SEMANTICS-001` | P3 | `payload_len` son BYTES COPIADOS (máx 512), no la longitud real. |

---

## 🔧 CORRECCIONES AL PROMPT ANTERIOR (DAY 217)

1. **`payload_len` YA EXISTE en `SimpleEvent`** (`main.h:32`) **y el kernel LO RELLENA**
   (`sniffer.bpf.c:337-338`), para TODO el tráfico, sin filtro de protocolo.
   ⟹ **NO hay que tocar eBPF, ni la struct, ni el `.proto`.**
2. **`ransomware_feature_processor.cpp:102` MIENTE:** *"SimpleEvent NO tiene payload"*
   — **es FALSO.** ⟹ El `entropy = varianza ÷ 100.000` se construyó como apaño ante
   una carencia **que no existía**.
3. El `83` de `ddos_features` es el **número de features** (`= 100` es el campo).
   La dependencia posicional con el enum **SÍ existe**.

---

## ⚠️ LA TRAMPA QUE CASI ENTRA EN EL CÓDIGO

```cpp
if (flow.fwd_lengths[i] > flow.fwd_header_lengths[i]) ++count;   // ❌ MAL
```
`packet_len` **INCLUYE Ethernet** (`sniffer.bpf.c:239`, XDP: `data_end - data`).
`total_header` **NO** (`flow_manager.hpp:99`: `ip_header_len + l4_header_len`).

ACK puro: `54 > 40` ⟹ **contaría TODOS los paquetes forward, siempre.** Un `SPKTS`
con nombre de feature de CICFlowMeter.

**La solución correcta NO RECONSTRUYE: usa `payload_len`.**

---

## 🩸 TRAMPAS NUEVAS DE DAY 218 (no repetirlas)

- **`ctest` desde el HOST macOS falla SIEMPRE** — `CTestTestfile.cmake` apunta a
  `/vagrant/...`. Correr **dentro de la VM**: `vagrant ssh -c 'cd /vagrant/... && ctest'`.
  Un bucle mal puesto dio **40 fallos falsos**.
- **`SNIFFER_BUILD_DIR = /vagrant/sniffer/build-$(PROFILE)` = `build-debug`.**
  **NO `sniffer/build/`** — es un directorio huérfano. Mirar el equivocado casi produce
  un **P0 falso**.
- **`SimpleEvent` es `__attribute__((packed))`**: `std::swap(pkt.src_ip, pkt.dst_ip)`
  NO compila (*"cannot bind packed field"*). Copiar por valor.
- **Una coma que falta en un enum produce 200 líneas de error**, ninguna de las cuales
  menciona la coma. **LEER EL PRIMER ERROR, NO EL ÚLTIMO.**
- **`grep -rn '\.bind('` NO ve `->bind()`.** Los `unique_ptr` llaman con flecha.
- **`grep ... 2>/dev/null` se traga *"No such file or directory"***. Un grep sobre un
  directorio inexistente devuelve una salida **limpia y engañosa**.

---

## 📐 EL PATRÓN — YA SON DIECISÉIS. Y TIENE NOMBRE.

> **Un artefacto que afirma haber verificado algo, sin haberlo verificado.**

1. `entropy` ransomware = varianza ÷ 100.000
2. `level3_web`/`level3_internal` nunca parseados (DAY 215)
3. 5/23 features de L1 rotas (DAY 216)
4. `test_l1_feature_contract.cpp` commiteado VACÍO (DAY 217)
5. El `max()` que no puede suprimir FP — claim del abstract (DAY 217)
6. `test_autonomy_publisher`: `sleep` en vez de handshake (DAY 218)
7. `contract_validator.cpp` en `.backup` — el testigo amordazado
8. 5 `add_executable` sin `add_test`
9. `Makefile:1197` — `|| echo` traga el exit code
10. `PayloadAnalyzer`: 4/4 tests de patrones devuelven `false`
11. Variante B: 8 tests sobre el camino que no calcula features
12. 2/10 features del DDoS son constantes
13. `set_final_decision()` — ADR-007 sin sitio donde vivir
14. Comentario que afirma que un campo no existe, y existe
15. **Seis greps ciegos, cada uno con salida limpia** (Claude, DAY 218)
16. **`PureAcksGiveZero` pasó EN FALSO** — verde por vector vacío, en el test escrito
    para cazar verdes falsos (DAY 218)

**NO ES UN PATRÓN DE BUGS. ES UN PATRÓN DE FALSA EVIDENCIA.**
Y por eso ninguno lo cazó el testing convencional: **el testing convencional TAMBIÉN es
un artefacto que afirma haber verificado.**

> **El método (Alonso, DAY 218):** *"Estamos arreglando los componentes de medición
> científicos del proyecto. Uno a uno y con paciencia. Con método. Encontramos lo roto,
> establecemos hipótesis de por qué está roto, se escribe el test, al principio sale
> rojo, se arregla, debe salir verde. Uno a uno."*
>
> **El RED obligatorio es la ÚNICA forma de demostrar que el instrumento está conectado.**
> **Un test que nunca has visto fallar no es un test: es una hipótesis sobre un test.**

---

## 📋 PLAN DE REPARACIÓN — 5 PASOS (estado)

1. ✅ **HECHO (`5b494d90`)** — contrato L1 + test de propiedad + targets `common-*`.
2. 🔴 **EN CURSO — RED capturado.** `ACT_DATA_PKT_FWD` en el enum (índice 83,
   `FEATURE_COUNT` 83→84) ✅. Extractor ✅. Test ✅. **FALTA: la ruta de población
   del `ShardedFlowManager`.**
3. **El sniffer RELLENA `general_attack_features` (campo 102)** recorriendo el mapa
   de 23 features.
4. **El ml-detector LEE el campo 102.** `extract_level1_features` → **borrar la
   reconstrucción entera.** Ya no reconstruye: lee.
5. **El injector RELLENA el campo 102** (`tools/synthetic_sniffer_injector.cpp`).
   ⚠️ **SIN ESTO SEGUIREMOS MIDIENDO UN PIPELINE CIEGO Y CREYENDO QUE LO ARREGLAMOS.**

**De propina:** reactivar `contract_validator` (está en `.backup` y ya sabía la verdad).

**Test de cierre (el que nunca existió):**
> *N filas de CIC-IDS2017 → protobuf → detector → ONNX reproducen la etiqueta del CSV.*
**RED→GREEN obligatorio.**

---

## 🗺️ EL MAPA — 23 features L1 → enum del sniffer (VERIFICADO)

Vive en `common/include/argus/l1_feature_contract.hpp` (`5b494d90`).

```
 L1  contrato                       FeatureIndex del sniffer
  0  Packet Length Std              PACKET_LEN_STD          (15)
  1  Subflow Fwd Bytes              SUBFLOW_FWD_BYTES       (59)  ✅
  2  Fwd Packet Length Max          FWD_LEN_MAX             (33)
  3  Avg Fwd Segment Size           AVG_FWD_SEGMENT_SIZE    (79)
  4  ACK Flag Count                 ACK_FLAG_COUNT          (21)
  5  Packet Length Variance         PACKET_LEN_VAR          (16)
  6  PSH Flag Count                 PSH_FLAG_COUNT          (20)
  7  Bwd Packet Length Max          BWD_LEN_MAX             (36)
  8  act_data_pkt_fwd               ACT_DATA_PKT_FWD        (83)  ← DAY 218 ✅
  9  Total Length of Fwd Packets    FWD_LEN_TOT             (35)  ← NO SBYTES
 10  Fwd Packet Length Std          FWD_LEN_STD             (57)
 11  Fwd Packets/s                  SRATE                   (25)
 12  Subflow Bwd Bytes              SUBFLOW_BWD_BYTES       (61)  ✅
 13  Destination Port               🟡 de la 5-tupla, no del enum
 14  Init_Win_bytes_forward         INIT_FWD_WIN_BYTES      (68)  ✅
 15  Subflow Fwd Packets            SUBFLOW_FWD_PACKETS     (58)  ✅
 16  Fwd IAT Min                    FWD_IAT_MIN             (46)
 17  Packet Length Mean             PACKET_LEN_MEAN         (14)
 18  Total Length of Bwd Packets    BWD_LEN_TOT             (39)  ← NO DBYTES
 19  Bwd Packet Length Mean         DMEAN                   (7)
 20  Bwd Packet Length Min          BWD_LEN_MIN             (37)
 21  Flow Duration                  DURATION                (0)
 22  Flow Packets/s                 FLOW_PKTS_PER_SEC       (75)
```

**Las 5 features rotas: `[1]`, `[8]`, `[12]`, `[14]`, `[15]`** — coinciden EXACTAMENTE
con las 5 que el protobuf no transporta como escalar. **No fue descuido: fue un apaño
ante un contrato incompleto.**

**AMBIGÜEDADES RESUELTAS (DAY 217), no reabrir:** idx 9 → `FWD_LEN_TOT` (no `SBYTES`);
idx 18 → `BWD_LEN_TOT` (no `DBYTES`).

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
internal_class1=     69               0     ← INVERTIDA
```
**Tras el paso 5, `l1_class1` DEBE subir con `--attack`.** Criterio de éxito, escrito
ANTES de medir.

---

## 🎯 DECISIONES QUE SOBREVIVEN

- **Commit 2 (noisy-OR) APARCADO**, no cancelado. **El noisy-OR NO suprime FP**
  (monótono creciente, como el `max`). Resuelve OTRO problema: agregar N cabezas en L3.
  **La supresión de FP necesita ADR-007 (AND/veto)** — y ADR-007 necesita antes
  `DEBT-VERDICT-DECIDED-UPSTREAM-001`.
- **Traffic = GUARD, no término del producto** (opción (a), DAY 216).
- **`ddos`/`ransomware` a `reliability = 0.0`.** ✅ **VALIDADO HOY** — `ddos` tiene
  2/10 features constantes; `ransomware` está ciego por DOS causas.
- **`l3_combined_seal` con clave propia** en config.
- **La P gobierna la FUERZA de la evidencia, NUNCA la ETIQUETA.**
- **MITRE es imprescindible y va DESPUÉS del extractor.**
- **DEBT-VERDICT-WEIGHTS-CALIBRATION-001 sigue INDECIDIBLE** hasta que las cabezas vean.
- **Un commit, un cambio, una razón.**
- **Tras commitear un fichero nuevo: `git show HEAD:<fichero> | wc -l`.**
  **Verificar el artefacto, no la intención.**

---

## ▶️ DAY 219 — POR DÓNDE EMPEZAR

```zsh
git log --oneline -5 && git status --short
# ⚠️ zmq_handler.hpp/.cpp DEBEN seguir modificados-sin-stagear. NO los commitees.

# 1. El RED de ayer, para verlo con tus ojos
vagrant ssh -c 'cd /vagrant/sniffer/build-debug && ctest -R test_feature_extractor --output-on-failure'

# 2. EL COMANDO QUE DESBLOQUEA EL PASO 2
grep -n 'fwd_lengths\|add_packet\|payload' sniffer/src/flow/sharded_flow_manager.cpp
```

**Decidir: ¿`ShardedFlowManager` delega en `FlowStatistics::add_packet` (unificar), o se
duplica el `push_back` (rápido, y garantiza que volverán a divergir)?**

**Recomendación: unificar.** La duplicación de la lógica de población **ES la causa raíz
de esta clase de defecto.** Pero mirar el código antes de decidir.

Luego: aislar el singleton entre tests, verde, commit. **Y entonces PASOS 3, 4 y 5.**

---

## FEDER

Go/no-go **~1 agosto 2026** — **19 días.** Deadline **22 septiembre 2026**.

> *"No pienso entregar nada que no esté bien fundamentado. El pipeline tiene que
> funcionar bien."* — Alonso, DAY 216.

**Las 7 deudas de `DAY218_FINDINGS.md` son PRE-FEDER.** Ninguna es cosmética. Todas
afectan a la capacidad del proyecto de **medir lo que dice que mide.**