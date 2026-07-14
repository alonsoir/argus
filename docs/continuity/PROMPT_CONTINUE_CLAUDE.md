# PROMPT DE CONTINUIDAD — DAY 219 → 220
## Rama `fix/verdict-multihead-honest`

> Memoria de sesión. Claude no recuerda entre ventanas. La fuente de verdad del PLAN
> sigue siendo el PLAN. Aquí sólo el estado operativo.

---

## 📕 LEE ESTO PRIMERO

👉 **`docs/debt/DAY219_FINDINGS.md`** — ⚠️ **SÓLO 1.1K. El de DAY 218 son 19K.**
**VERIFICAR SU CONTENIDO ANTES DE FIARSE.** Un fichero en el árbol no prueba que diga
la verdad — es literalmente el patrón (caso 4: `test_l1_feature_contract.cpp` se
commiteó VACÍO). **Si está a medias, completarlo con esto de abajo.**

👉 **`docs/debt/DAY218_FINDINGS.md`** (19K, commit `ebd3cac9`) — 7 deudas, todas PRE-FEDER.
👉 **`docs/debt/DEBT-FEATURE-EXTRACTOR-L1-BROKEN-001.md`** — el hallazgo de DAY 216.
👉 **Anexo DAY 216 del PLAN DE CAMPAÑA.**
👉 DAY 217: **la claim del `max()` es aritméticamente imposible.** `max(a,b) ≥ a` SIEMPRE.
El ML no puede suprimir FP. El noisy-OR TAMPOCO (monótono creciente). Hace falta
**ADR-007** (AND/veto). **NO tocar el LaTeX aún.**

---

## 🔴 EL HALLAZGO DE DAY 219 — Y ESTÁ SIN CONFIRMAR

> ### **`FeatureExtractor` (83+1 features) PARECE NO EJECUTARSE EN PRODUCCIÓN. NUNCA.**

```zsh
grep -rn 'extract_features\|FeatureExtractor' sniffer/src/ --include='*.cpp' | grep -v feature_extractor.cpp
# → VACÍO (sólo hits de RansomwareFeatureExtractor, que es OTRA clase)
```

**⚠️ ESE GREP NO MIRÓ LOS `.hpp`.** Puede ser un falso negativo — la trampa nº 15,
otra vez. **PRIMER COMANDO DE MAÑANA, ANTES DE NADA:**

```zsh
grep -rn 'extract_features\|FeatureExtractor' sniffer/ --include='*.cpp' --include='*.hpp' | grep -v 'feature_extractor\.\|tests/'
grep -rn 'FeatureExtractor' sniffer/CMakeLists.txt
git log --oneline --all -- sniffer/src/userspace/feature_extractor.cpp | tail -5
```

**Si se confirma**, responde la pregunta de los 200 días de forma definitiva:
> **El extractor roto no sobrevivió a la ausencia de TESTS. Sobrevivió a la ausencia
> de EJECUCIÓN.** Nadie lo probó porque **nadie lo llamaba.** Un componente muerto no
> puede tener bugs — hasta el día en que lo conectas.

**HIPÓTESIS DE ALONSO (a verificar con `git log`, NO con intuición):** se desconectó en
la **crisis de concurrencia del DAY 44** (el "FIX #3 thread-safe" que reescribió
`ShardedFlowManager`, dejó los `_fix1/_fix2/_fix3` y escribió `get_flow_stats_copy`
con su lista a mano). Encaja. **No está probado.**

### LO QUE SÍ ES SÓLIDO (grep sin filtro de directorio)

**Los 4 campos `repeated` del protobuf están VACÍOS. Ninguno tiene un `add_*` en todo el árbol:**
```proto
repeated double ddos_features = 100;              // 83 features — VACÍO
repeated double ransomware_features = 101;        // 83 — VACÍO
repeated double general_attack_features = 102;    // 23 — VACÍO  ← el de L1
repeated double internal_traffic_features = 103;  // 4-5 — VACÍO
```
Viven en `NetworkFeatures` (`event.network_features()`, `feature_logger.cpp:90`).

**HAY DOS ARQUITECTURAS DE FEATURES EN EL SNIFFER, Y SÓLO UNA ESTÁ ENCHUFADA:**

| | `FeatureExtractor` | `MLDefenderExtractor` |
|---|---|---|
| Fichero | `feature_extractor.cpp` | `ml_defender_features.cpp` |
| Features | 84 (enum posicional) | 40 (4×10) |
| Contrato | `l1_feature_contract.hpp` | ninguno |
| Destino | campos 100-103 (`repeated`) | **submensajes** (`ddos_embedded`, etc.) |
| **¿En producción?** | **NO (a confirmar)** | **SÍ** (`ring_consumer.cpp:820`) |

`populate_ml_defender_features` (`ml_defender_features.cpp:718`) rellena los 4
submensajes + los campos base. **NO toca el 102. NO conoce a `FeatureExtractor`.**

### 🩸 CASO 22 — POR QUÉ EL LOG NUNCA GRITÓ

`feature_logger.cpp:158`:
```cpp
if (nf.general_attack_features_size() > 0) { ... }   // sin else. sin warning.
```
**La ausencia de las 23 features es INDISTINGUIBLE de la ausencia de una llamada al
logger.** Y el logger SÍ imprime los otros submensajes → **el log salía lleno, bonito,
con números.** Nadie echa de menos un bloque que no sabe que debería estar.

> **No es que el log mintiera. Es que sólo podía AFIRMAR, nunca NEGAR.**
> Un test sí puede decir `EXPECT_EQ(size(), 23)`. Un log, no.

**Es la misma idea que los 14 guardas `if (!flow.time_windows)` y que
`ASSERT_NE(ptr, nullptr)`. Toda la sesión de hoy es UNA sola idea repetida:
el código estaba lleno de comprobaciones QUE SÓLO PODÍAN PASAR.**

---

## ✅ LO QUE SE CERRÓ HOY — `DEBT-FLOWSTATS-COPY-AMPUTATED-001` (P0)

**RED `6166982f` → GREEN `fc292bc8`.** `ctest: 17/18`.

### La causa raíz: **un `unique_ptr` que nunca fue necesario**

`TimeWindowManager` es copiable desde el día uno (`deque<WindowStats>` POD + PODs +
`vector<double>`; ni mutex, ni punteros). El `unique_ptr` de
`FlowStatistics::time_windows` era la **única** razón por la que `FlowStatistics` no
era copiable ⟹ alguien escribió a mano una lista de **26 asignaciones** en
`get_flow_stats_copy` (`sharded_flow_manager.cpp:96`) ⟹ la lista envejeció ⟹ **2 de
los 28 campos se perdían.** Y la ruta de PRODUCCIÓN come de esa copia
(`ring_consumer.cpp:809` → `:820`).

**LAS 5 FEATURES ROTAS DE L1 SON EXACTAMENTE LAS 5 QUE DEPENDEN DE ESOS 2 CAMPOS:**

| L1 | Feature | Campo perdido |
|---|---|---|
| **[1]** | Subflow Fwd Bytes | `time_windows` (`feature_extractor.cpp:334`) |
| **[8]** | act_data_pkt_fwd | `fwd_payload_lengths` |
| **[12]** | Subflow Bwd Bytes | `time_windows` (`:344`) |
| **[14]** | Init_Win_bytes_forward | `time_windows` (`:379`) |
| **[15]** | Subflow Fwd Packets | `time_windows` (`:329`) |

**No es correlación. Es la causa.** El "hardcodeo" de DAY 216 era el **SÍNTOMA**:
alguien vio ceros y los cementó sin rastrear de dónde venían.

### La hipótesis del prompt de DAY 218 era FALSA
*"`ShardedFlowManager` NO llama a `FlowStatistics::add_packet()`"* — **falso.** Sí lo
llama (`:73`, `:83`). **Seguirla a ciegas habría duplicado el `push_back`** — el arreglo
rápido, el que garantiza que vuelvan a divergir. **Mirar el código antes de decidir
fue lo único que hizo falta.**

### Los cambios
- `time_windows`: `unique_ptr` → **POR VALOR**. Los 4 ctors/assign **explícitos**
  (⚠️ **declarar el move suprime el copy implícito** — por eso no era copiable *ni aun*
  quitando el puntero).
- `get_flow_stats_copy`: **40 líneas → 1.** Copia el compilador: los 28, y los que
  vengan mañana. **La clase de defecto deja de ser POSIBLE.**
- `feature_extractor.cpp`: **14 guardas** `if (!flow.time_windows) return 0.0;`
  eliminados. Protegían de un `nullptr` **IMPOSIBLE** (el ctor hacía `make_unique`)
  mientras el objeto llegaba **VACÍO**. **Caso 19.**
- **`ShardedFlowManager::clear()`** — HALLAZGO 2 de DAY 218 resuelto.
- **`sharded_flow_manager.cpp` incluía `sharded_flow_manager_fix3.hpp`** — header
  IDÉNTICO pero **DISTINTO FICHERO**. Todo el resto del proyecto incluye el canónico.
  **Dos `#pragma once`, una clase: violación de la ODR latente**, viva 175 días porque
  eran byte a byte iguales. **Si hubieran divergido en un CAMPO en vez de un método,
  no habría error de compilación: habría corrupción de memoria silenciosa.**
- `full_contract:219/287`: **`ASSERT_NE(time_windows, nullptr)` YA NO COMPILA.**
  El verde falso es **INEXPRESABLE**. Sustituido por preguntas sobre el CONTENIDO.

### `PureAcksGiveZero` vale algo, por primera vez
Ayer daba 0 **porque el vector estaba vacío** (caso 16). Hoy da 0 **contando ceros.**

---

## 📦 COMMITS DE DAY 219

```
6166982f  test(sniffer): DAY 219 RED — DEBT-FLOWSTATS-COPY-AMPUTATED-001
fc292bc8  fix(sniffer): DAY 219 GREEN — DEBT-FLOWSTATS-COPY-AMPUTATED-001 (P0)
```
Verificado el artefacto: `git show HEAD:sniffer/src/flow/sharded_flow_manager.cpp | grep -c 'copy\.'` → **0**.

**⚠️ SIGUE SIN COMMITEAR, A PROPÓSITO:**
```
 M ml-detector/include/zmq_handler.hpp    ← instrumentación DAY 216 (9 contadores)
 M ml-detector/src/zmq_handler.cpp        ← salvada en docs/day216_instrumentation.patch
 M commit-message.txt                     ← scratch
AM docs/debt/DAY219_FINDINGS.md           ← ¡1.1K! VERIFICAR CONTENIDO
```
**NUNCA `git add -u` NI `git commit -a`.**

**STASH:** `stash@{0}: commit2-noisy-or WIP` (header + tests, VÁLIDOS) — **no lo pierdas.**

---

## 🩸 DEUDAS NUEVAS DE DAY 219

| Deuda | P | Qué es |
|---|---|---|
| `FLOWSTATS-COPY-AMPUTATED-001` | ~~P0~~ | **CERRADA HOY.** |
| **`FEATURE-EXTRACTOR-DEAD-CODE-001`** | **P0?** | **`FeatureExtractor` parece no ejecutarse en producción. SIN CONFIRMAR — el grep no miró `.hpp`.** |
| **`PROTO-REPEATED-FIELDS-EMPTY-001`** | **P0** | **Los 4 campos `repeated` (100-103) están VACÍOS. Ni un `add_*` en el árbol.** |
| `SOURCE-TREE-BACKUP-FILES-001` | **P1** ↑ | **Subida de P2.** Razón nueva: **no es que el árbol confunda al `grep` — es que el proyecto compilaba contra DOS declaraciones de la misma clase.** Hoy costó un error de compilación. |
| `FULL-CONTRACT-POPULATION-THEATRE-001` | **P1** | `total_fields += 7`, comprueba **6**. `fwd_payload_lengths` **no se mira**. `dpkts`, `dbytes` y **5 flags se cuentan como poblados SIN MIRARLOS.** Un `population_rate` bonito por construcción. **Rediseño, no parche.** |
| `SHARDED-INIT-CALL-ONCE-MUTE-001` | P2 | `initialize()` es `std::call_once`: **la 2ª llamada es un NO-OP MUDO** y descarta la `Config` nueva en silencio. En producción es correcto (1 proceso, 1 init); **el daño es a la MEDIBILIDAD.** Mitigado con `clear()`. El defecto sigue. **Decisión Alonso: (a) ahora, (b) post-FEDER.** |

**Las 7 de DAY 218 siguen abiertas** (ver `DAY218_FINDINGS.md`). `test_payload_analyzer`
sigue **ROJO** (4/4 patrones + perf) — `DEBT-PAYLOAD-ANALYZER-PATTERNS-INERT-001`. **No tocado.**

---

## 📐 EL PATRÓN — YA SON VEINTIDÓS

(1–16 en `DAY218_FINDINGS.md`)

17. **`get_flow_stats_copy`: 26 de 28 campos**, en una lista escrita a mano el día que se
    escribió. Y el comentario `// time_windows will be created by FlowStatistics()
    constructor` **confesaba la amputación como si fuera un detalle de implementación.**
18. **`test_sharded_flow_full_contract:219`**: `ASSERT_NE(time_windows, nullptr)` PASABA
    siempre — puntero no-nulo a objeto **vacío**. Y `:287` lo contaba como **campo poblado.**
    **Un test de "contrato completo" que certifica como poblado el campo que se acaba de perder.**
19. **14 guardas `if (!flow.time_windows) return 0.0;`** protegiendo de un `nullptr`
    IMPOSIBLE, mientras el objeto llegaba vacío. **Guardas que protegen del fallo que no
    ocurre e ignoran el que sí.**
20. **`NoFieldsLeftAtDefaultValues`** declara poblados los campos que están en su valor
    por defecto.
21. **Mi red de seguridad se disparó contra su propia documentación** (buscaba
    `"time_windows != nullptr"` y lo encontró en los comentarios del parche). Un falso
    positivo del instrumento escrito para evitar falsos negativos. (Claude, DAY 219.)
22. **`if (size() > 0)` en el logger**: la ausencia del dato es indistinguible de la
    ausencia de la llamada. **Un artefacto que sólo puede AFIRMAR, nunca NEGAR.**

> **NO ES UN PATRÓN DE BUGS. ES UN PATRÓN DE FALSA EVIDENCIA.**

---

## 🩸 TRAMPAS NUEVAS DE DAY 219

- **`ctest ... | grep -c` sobre un test que NO COMPILA devuelve `0`** — exactamente igual
  que un test que corre y no imprime. **Un cero que significa "no medí nada", disfrazado
  de dato.** (Claude, DAY 219. Misma familia que el `grep 2>/dev/null` de DAY 218.)
- **`grep --include=*.cpp` en zsh NO ES UN GREP** — zsh expande el glob y aborta antes de
  llamar a `grep`. **Hay que citar: `--include='*.cpp'`.**
- **`sed -n '1,20p' fichero  # comentario`** — zsh pasa el comentario como argumento.
  `sed: #: No such file or directory`.
- **Un grep con un regex de tipos concretos NO ES UN INVENTARIO DE CAMPOS.** Si un miembro
  tiene un tipo que no está en la lista, **no aparece, y la salida sale limpia.**
  **Verificar el struct con los ojos.** (Claude, DAY 219.)
- **Los backups NO van al árbol de fuentes.** Van a `/tmp`. El backup de verdad es el
  commit del RED.

---

## 📋 PLAN DE REPARACIÓN — ESTADO CORREGIDO

1. ✅ **HECHO (`5b494d90`)** — contrato L1 + test de propiedad + targets `common-*`.
   ⚠️ **Pero `l1_feature_contract.hpp` es HUÉRFANO: sólo lo incluye su propio test.**
2. ✅ **HECHO (`fc292bc8`)** — `ACT_DATA_PKT_FWD` (83, `FEATURE_COUNT`→84) + extractor +
   test + **la ruta de población.** `PayloadLenReachesFeatureFromSimpleEvent` **VERDE.**
3. 🔴 **PASO 3 — ES MÁS GRANDE DE LO QUE EL PLAN DECÍA.**
   No es "rellenar el campo 102 con un bucle". **`FeatureExtractor` NO ESTÁ EN EL
   CIRCUITO.** Hay que:
    - (a) **Confirmar** que está muerto (el grep de arriba).
    - (b) **Decidir la arquitectura**: ¿el ml-detector lee del **102** o de los
      **submensajes**? ⚠️ **NO ESCRIBIR EL TEST ANTES DE DECIDIR** — un test contra un
      diseño no decidido es cómo se producen los verdes falsos.
    - (c) Conectar `FeatureExtractor` ↔ `populate_ml_defender_features`. Recorrer el mapa
      de las 23. `add_general_attack_features()` × 23.
4. **El ml-detector LEE el campo 102** → borrar la reconstrucción entera. *(depende de 3b)*
5. **El injector RELLENA el 102** (`tools/synthetic_sniffer_injector.cpp`).
   ⚠️ **SIN ESTO SEGUIREMOS MIDIENDO UN PIPELINE CIEGO Y CREYENDO QUE LO ARREGLAMOS.**

**Criterio de Alonso (DAY 219):** *"La decisión más limpia, sencilla y con menor coste
computacional y de memoria, para un componente que ya de por sí está exigido."*
**Y con datos: enganchar, medir, averiguar.**

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

**BASELINE DAY 216 (extractor ROTO Y DESCONECTADO):**
```
                   ruido          ataque
l1_class1      =      0               0     ← L1 NUNCA dice ATTACK
traffic_class1 =    100             100     ← constante, prob 0.96 ± 0.005
internal_class1=     69               0     ← INVERTIDA
```
**Tras el PASO 5, `l1_class1` DEBE subir con `--attack`.** Criterio escrito ANTES de medir.

**⚠️ Y AHORA SABEMOS POR QUÉ:** si los 4 campos `repeated` están vacíos, **los modelos de
DDoS y ransomware nunca comieron features reales.** Alonso, DAY 219: *"es imposible que
funcionara. Aunque esto sólo dice que la tubería aguas arriba estaba rota, nada más.
Todavía hay que enganchar, medir y averiguar con datos y medidas."*

---

## ▶️ DAY 220 — POR DÓNDE EMPEZAR

```zsh
git log --oneline -3 && git status --short
# ⚠️ zmq_handler.hpp/.cpp DEBEN seguir M-sin-stagear. NO los commitees.

# 1. CONFIRMAR O DESMENTIR EL HALLAZGO. Con .hpp esta vez.
grep -rn 'extract_features\|FeatureExtractor' sniffer/ --include='*.cpp' --include='*.hpp' | grep -v 'feature_extractor\.\|tests/'
grep -rn 'FeatureExtractor' sniffer/CMakeLists.txt

# 2. ARQUEOLOGÍA: ¿cuándo se desconectó? (hipótesis: crisis de concurrencia, DAY 44)
git log --oneline --all -- sniffer/src/userspace/feature_extractor.cpp
git log --oneline --all -S 'extract_features' -- sniffer/src/userspace/ring_consumer.cpp

# 3. VERIFICAR DAY219_FINDINGS.md (1.1K es sospechosamente poco)
wc -l docs/debt/DAY219_FINDINGS.md && cat docs/debt/DAY219_FINDINGS.md
```

**Y ENTONCES decidir la arquitectura del PASO 3. Con datos. Sin prisa.**

---

## 🎯 DECISIONES QUE SOBREVIVEN

- **Commit 2 (noisy-OR) APARCADO**, no cancelado. **El noisy-OR NO suprime FP**
  (monótono creciente, como el `max`). **La supresión de FP necesita ADR-007 (AND/veto)**
  — y ADR-007 necesita antes `DEBT-VERDICT-DECIDED-UPSTREAM-001`.
- **Traffic = GUARD, no término del producto.**
- **`ddos`/`ransomware` a `reliability = 0.0`.** ✅ **REVALIDADO HOY**: sus campos
  `repeated` están **vacíos**.
- **`l3_combined_seal` con clave propia.**
- **La P gobierna la FUERZA de la evidencia, NUNCA la ETIQUETA.**
- **MITRE va DESPUÉS del extractor.**
- **`DEBT-VERDICT-WEIGHTS-CALIBRATION-001` INDECIDIBLE** hasta que las cabezas vean.
- **Un commit, un cambio, una razón.**
- **Verificar el artefacto, no la intención.** `git show HEAD:<f> | wc -l`.
- **El RED obligatorio es la ÚNICA forma de demostrar que el instrumento está conectado.**

---

## FEDER

Go/no-go **~1 agosto 2026** — **18 días.** Deadline **22 septiembre 2026**.

> *"No pienso entregar nada que no esté bien fundamentado. El pipeline tiene que
> funcionar bien."* — Alonso, DAY 216.

**Ninguna de las deudas nuevas es cosmética. Todas afectan a la capacidad del proyecto
de medir lo que dice que mide.**