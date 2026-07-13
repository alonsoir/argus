# DAY 218 — HALLAZGOS DE LA AUDITORÍA DE INSTRUMENTOS
## Rama `fix/verdict-multihead-honest` — 13 julio 2026

> **Qué es esto.** DAY 218 empezó con un objetivo: el PASO 2 del plan de reparación
> del extractor (`ACT_DATA_PKT_FWD`). No se llegó a él. En su lugar se auditaron los
> **instrumentos de medida** del proyecto y aparecieron **siete deudas nuevas**, todas
> con `file:line`, ninguna especulativa.
>
> **No son un desvío. Son la respuesta a la pregunta de los 200 días:**
> *¿cómo sobrevivió el extractor roto a 13 tests verdes, EMECAS+++ verde y libFuzzer
> con 2.4M runs?* Respuesta: **porque nadie estaba midiendo ahí.**
>
> **TODAS SON PRE-FEDER.** Van a `docs/BACKLOG.md` en rojo tras el merge a `main`.

---

## ✅ CERRADO HOY

### `DEBT-TEST-AUTONOMY-PUBLISHER-FLAKY-001` — MITIGADO (`5d9bd43e`)

**Causa raíz, probada:**
- `common/tests/test_autonomy_publisher.cpp` hacía `sub.connect()` **ANTES** de que
  `AutonomyPublisher` (cuyo ctor hace `socket_.bind()`, `autonomy_publisher.cpp:26`)
  existiera. **Violaba la regla permanente del proyecto.**
- El `sleep_for(300ms)` no era una sincronización: era **una apuesta contra
  `reconnect_ivl = 100ms`** (`autonomy_publisher.cpp:20`). Tres reintentos. A veces
  cabían dos.
- **Por qué fallaba T3 y no T1/T2/T4:** en T1/T2/T4 el `publish()` es una llamada
  directa, **repetible**. En T3 el mensaje es efecto colateral de
  `sm.on_vault_unreachable()` — una transición **idempotente que dispara UNA vez**.
  **T3 era el único caso sin reintento posible.** Los otros tres llevaban la misma
  bomba dentro y sobrevivían por casualidad.

**Arreglo:** `bind()` → `connect()` → `sync_pub_sub()` (handshake real: publica
warm-ups hasta que el SUB confirma, luego drena). `unlink()` del socket ipc para no
heredar estado entre runs.

**Evidencia:** **no reproducido en 40 iteraciones secuenciales dentro de la VM.**
Tasa previa medida: 1/20 (~5%). **P(los 40 verdes sean suerte) ≈ 13%.**

> **NO se declara CERRADO.** Se cierra si sobrevive **3 EMECAS completos** sin reaparecer.
> La honestidad también aplica a los arreglos propios.

### `DEBT-SNIFFER-TESTS-NOT-REGISTERED-001` — REGISTRADO (`92ce8a09`)

**Cinco tests tenían `add_executable()` pero NO `add_test()`.** Se compilaban, se
enlazaban, y **`ctest` no los conocía.** `ctest -N`: **11 registrados / 21 ficheros
en `sniffer/tests/`.**

Los cinco: `test_payload_analyzer`, `test_sharded_flow_full_contract`,
`test_ring_consumer_protobuf`, `test_proto3_embedded_serialization`,
`test_sharded_flow_multithread`.

**Y entre ellos, los DOS únicos que cubren el camino
`SimpleEvent → features → protobuf`** — justo el que DAY 216 encontró roto.

**Resultado tras registrarlos: `ctest -N` → 16. Primera ejecución: 15/16.**
Un rojo: `test_payload_analyzer` (ver abajo).

> ⚠️ **El COMMIT 2 (quitar el `|| echo`) queda BLOQUEADO** por ese rojo. Ver
> `DEBT-GATE-COMPONENTS-SWALLOWED-EXIT-001`.

---

## 🔴 P1 — PRE-FEDER, BLOQUEANTES DE CALIDAD

### `DEBT-PAYLOAD-ANALYZER-PATTERNS-INERT-001`

**Descubierto al registrar los huérfanos. El test existía y NUNCA se había ejecutado.**

`test_payload_analyzer`, casos **10, 11, 12 y 13** — **los cuatro de detección de
patrones** — fallan devolviendo `false`:

```
[TEST 10] Ransom note pattern detected...      ❌ Expected true, got false
[TEST 11] Crypto API pattern detected...       ❌ Expected true, got false
[TEST 12] Onion address detected...            ❌ Expected true, got false
[TEST 13] Case-insensitive pattern matching... ❌ Expected true, got false
```

**Lo que SÍ pasa:** entropía (7,8,9), cabecera PE (3,4,5,6), rendimiento (15),
thread-local (16). **14/18.**

**Diagnóstico:** no es un cálculo mal hecho. **Devuelve la nada, sistemáticamente.**
El matcher de patrones no está conectado, o la tabla de patrones está vacía.

**RELACIÓN CRÍTICA con `DEBT-RANSOMWARE-ML-HEAD-INERT-001`:**
Ya sabíamos que el `entropy` del ransomware era *varianza de longitud ÷ 100.000*.
Ahora sabemos que **el `PayloadAnalyzer` también está inerte.**
⟹ **La cabeza de ransomware está ciega por DOS causas independientes.**

### `DEBT-VARIANT-B-FEATURE-PATH-001`

**La Variante B (libpcap) NO computa features de flujo. En absoluto.**

Camino de la Variante A (eBPF):
```
sniffer.bpf.c → ring buffer → ring_consumer.cpp:514 (SimpleEvent)
              → flow_manager.add_packet(SimpleEvent)
              → FeatureExtractor → 83 features → protobuf
```

Camino de la Variante B (libpcap):
```
pcap_backend.cpp (104 líneas — fachada, entrega bytes crudos)
              → main_libpcap.cpp:110  "// Construir NetworkSecurityEvent MÍNIMO"
              → protobuf directo desde la trama ETH. SIN SimpleEvent. SIN FlowManager.
                SIN FeatureExtractor. SIN estado de flujo.
```

**`SimpleEvent` no aparece ni una vez en `main_libpcap.cpp` ni en `pcap_backend.cpp`.**
Verificado con `grep`.

**CONSECUENCIA PARA EL PAPER:** ADR-029 anuncia el **delta de rendimiento A vs C**
como contribución científica. Si esa comparación se hizo con este código,
**compara sistemas que no ven lo mismo.**

**IRONÍA MEDIDA:** de los 11 tests que `ctest` sí ejecutaba, **OCHO son de
`pcap_backend`/`pcap_proto_parse`** — la variante que no calcula features.
**El termómetro estaba bien calibrado y apuntando al componente equivocado.**

### `DEBT-VERDICT-DECIDED-UPSTREAM-001`

**El ml-detector ya decidió. El firewall no recibe evidencia: recibe una orden.**

```cpp
// ml-detector/src/zmq_handler.cpp:623-625
provenance->set_final_decision(
    final_score >= config_.scoring.malicious_threshold ? "DROP" : "ALLOW"
);
```

La arquitectura declarada (Alonso, DAY 218): *"el trabajo del detector es clasificar,
hallar un número y transmitirlo. El firewall decide qué hacer y loguea su decisión."*
**El código no la respeta.** El umbral se aplica aguas arriba.

**Consecuencias:**
- (a) El umbral de bloqueo no se puede ajustar por política de despliegue sin tocar
  el detector.
- (b) **ADR-007 (consenso AND / veto) NO TIENE DÓNDE VIVIR.** El punto de decisión
  está en el componente equivocado.

> **ESTE DEBT EXPLICA POR QUÉ ADR-007 LLEVA DESDE DAY 83 SIN IMPLEMENTARSE.**
> No era falta de tiempo. **No había sitio donde ponerlo.**
> Y ADR-007 es la respuesta a la claim imposible del paper (ver DAY 217: `max()` es
> monótono creciente y NO PUEDE suprimir falsos positivos).
> ⟹ **`DEBT-VERDICT-DECIDED-UPSTREAM-001` es PRERREQUISITO ARQUITECTÓNICO de ADR-007.**

### `DEBT-GATE-COMPONENTS-SWALLOWED-EXIT-001`

```makefile
# Makefile, target test-components
:1197  ctest --output-on-failure || echo "⚠️  No sniffer tests configured"
:1200  ctest --output-on-failure || echo "⚠️  No ml-detector tests configured"
:1203  ctest --output-on-failure || echo "⚠️  No rag-ingester tests configured"
:1205  ctest --output-on-failure || echo "⚠️  No etcd-server tests configured"
```

**El `|| echo` convierte CUALQUIER fallo en éxito.** `test-components` devuelve 0
pase lo que pase. **NINGÚN test de componente puede poner el gate en rojo, en TODO
el proyecto.**

Compárese con `Makefile:2150`, que sí propaga el exit code.

**Plan (piano piano — NO desgatear los cuatro a la vez a 19 días de FEDER):**
1. Sniffer primero — **bloqueado hasta cerrar `PAYLOAD-ANALYZER-PATTERNS-INERT`**.
2. Luego ml-detector, rag-ingester, etcd-server. **Uno a uno.** Cada desgateo puede
   abrir su propia caja.

---

## 🟡 P2

### `DEBT-AUTONOMY-SUBSCRIBER-SLOW-JOINER-001`

`firewall-acl-agent/src/core/autonomy_subscriber.cpp:35` — SUB `connect()`.
`common/autonomy_publisher.cpp:26` — PUB `bind()`. **Orden correcto**, pero
**sin handshake**.

**El slow joiner no lo arregla el orden: lo arregla el handshake.** Entre el
`connect()` y la propagación de la suscripción, el PUB **descarta en silencio**.

Y lo que viaja por ese canal es `NORMAL → AUTONOMOUS` — **un evento idempotente que
dispara una vez.** **Misma anatomía exacta que T3.**

**Escenario:** Vault caído al arrancar → el `vault-daemon` transita a AUTONOMOUS →
si el firewall-agent aún no ha propagado su suscripción, **nunca se entera de que el
sistema está en modo autónomo.** Sin error. Sin log. Silencio.

**Arreglo natural:** el canal es de **ESTADO**, no de **EVENTOS**. El publisher debería
republicar el estado actual periódicamente, no confiar en un disparo único.

### `DEBT-DDOS-FEATURES-CONSTANT-001`

`ml-detector/src/feature_extractor.cpp`, `extract_level2_ddos_features()`:

```cpp
features[2] = normalize(1.0f, 0.0f, 10.0f);          // CONSTANTE hardcodeada
float protocol_anomaly = (1.0f > 5) ? 1.0f : 0.0f;   // SIEMPRE FALSO. Constante 0.
features[3] = protocol_anomaly;
```

**2 de las 10 features del DDoS son constantes.** `[3]` es una comparación que el
compilador resuelve en tiempo de compilación.

Misma clase que el `entropy = varianza ÷ 100.000`. **Placeholder que se quedó.**

> **VALIDA RETROSPECTIVAMENTE la decisión de DAY 216:** `ddos` entra con
> `reliability = 0.0`. No era conservadurismo. **Era correcto.**

### `DEBT-SOURCE-TREE-BACKUP-FILES-001`

**19 ficheros de respaldo sólo en `sniffer/src/userspace/`**: `.backup`, `.fase1`,
`.fase2`, `.bak.day79`, `.v1.0`. **Cuatro de ellos son copias de `feature_extractor.cpp`.**
**Ocho directorios de build** en `sniffer/`: `build`, `build-active`, `build-debug`,
`build-debug-libpcap`, `build-libpcap`, `build-prod`, `build-production`,
`cmake-build-debug`.

**No es desorden estético. El árbol MIENTE AL `grep`** — y el `grep` es el microscopio
principal del proyecto. Hoy costó **seis búsquedas ciegas** y estuvo a punto de
producir un P0 falso (se auditó `sniffer/build/` — un directorio huérfano — en vez de
`sniffer/build-debug/`, que es el que usa el Makefile vía `SNIFFER_BUILD_DIR`).

**Precedente:** `contract_validator.cpp.backup` **sabía la verdad** (*"Missing:
general_attack_features (array empty)"*) y **nadie la leyó, porque estaba fuera del
build.** Un fichero que no compila no puede avisarte.

**Git es el respaldo.** `git rm` cuando el árbol esté limpio. **Antes del merge a `main`.**

---

## 🟢 P3

### `DEBT-PAYLOAD-LEN-SEMANTICS-001`

`sniffer.bpf.c:326-338`: el bucle copia **hasta 512 bytes** e incrementa `payload_len`
por cada byte copiado.

⟹ **`payload_len` NO es la longitud del payload. Son los bytes COPIADOS.**
Con payloads > 512 bytes, **miente por saturación.**

Irrelevante para `act_data_pkt_fwd` (sólo miramos `> 0`). **Peligroso para quien
mañana lo use como longitud.** Un comentario en la struct y listo.

---

## ✅ LO QUE SÍ SE AUDITÓ Y ESTÁ LIMPIO

### El camino de datos NO ha perdido flujos en 200 días

```
sniffer → socket_type::PUSH → connect()   (main_libpcap.cpp:258-260)
ml-detector → socket_type::PULL → bind()  (zmq_handler.cpp:85)
```

**PUSH/PULL NO es PUB/SUB.** Un PUSH sin peer **no descarta**: encola hasta el HWM.
**No hay slow joiner en el camino de datos.** El orden `connect`-antes-de-`bind` aquí
es inofensivo **por construcción del patrón**, no por suerte.

⟹ **Las mediciones de 200 días NO perdieron flujos iniciales.** Era la pregunta cara.
La respuesta es buena.

### El slow joiner NO sesgó los conteos del paper

```
zmq_handler.cpp:624   set_final_decision("DROP"/"ALLOW")   ← el veredicto se calcula
zmq_handler.cpp:685   csv_writer_->write_event(event)      ← se persiste a disco
zmq_handler.cpp:996   output_socket_->send(...)            ← y SÓLO DESPUÉS sale por el PUB
```

**El veredicto se escribe AGUAS ARRIBA del socket.** El slow joiner PUB/SUB
**no puede haber sesgado ningún conteo que salga de ese CSV.**

> **SALVEDAD, y es importante:** esto prueba que *existía* un registro fiable en el
> detector. **NO prueba que los números del paper salgan de ahí.** El `2.517` sigue
> **SIN PROCEDENCIA** (DAY 217). Eso es arqueología, y sigue pendiente.

### El endpoint de salida está bien configurado

`ml_detector_config.json`: `endpoint: tcp://0.0.0.0:5572`, `mode: "bind"`.
Detector `bind()`, firewall `connect()`. **No hay doble-connect.** El canal se
establece.

---

## 🔧 CORRECCIONES AL PROMPT DE CONTINUIDAD (DAY 217)

1. **El `83` de `ddos_features` es el NÚMERO DE FEATURES, no el número de campo.**
   `protobuf/*.proto:212`: `repeated double ddos_features = 100;  // 83 features`.
   El campo es el **100**. La dependencia posicional con el enum del sniffer **SÍ existe**.
   (Claude lo negó primero por error, y se retractó.)

2. **`payload_len` YA EXISTE en `SimpleEvent`** (`main.h:32`) **y el kernel SÍ LO
   RELLENA** (`sniffer.bpf.c:337-338`), **para TODO el tráfico** — sin filtro de
   protocolo ni de puerto.
   ⟹ **El PASO 2 NO necesita tocar eBPF, ni la struct, ni el `.proto`.**

3. **`ransomware_feature_processor.cpp:102` MIENTE:**
   `// ⚠️ LIMITACIÓN: SimpleEvent NO tiene payload` — **es FALSO. Sí lo tiene.**
   Comentario obsoleto que ha estado engañando a quien lo leyera.
   ⟹ **El `entropy = varianza ÷ 100.000` se construyó como apaño ante una carencia
   QUE NO EXISTÍA.** El dato estaba ahí.

4. **NO existe `test_feature_extractor.cpp`.** Ni registrado ni sin registrar.
   **El componente de 83 features nunca tuvo suite.** Ese es el PASO 2 real.

---

## ⚠️ LA TRAMPA QUE CASI ENTRA EN EL CÓDIGO (y por qué importa)

El PASO 2 iba a implementarse así:

```cpp
if (flow.fwd_lengths[i] > flow.fwd_header_lengths[i]) ++count;   // ❌ MAL
```

**Habría contado TODOS los paquetes forward, siempre.**

```
sniffer.bpf.c:239   event->packet_len = data_end - data;   ← INCLUYE Ethernet (14 bytes)
flow_manager.hpp:99 total_header = ip_header_len + l4_header_len;  ← NO incluye Ethernet

ACK puro:  packet_len = 14+20+20 = 54    total_header = 20+20 = 40
           54 > 40  ⟹  "tiene payload"   ❌ FALSO
```

Un `SPKTS` con nombre de feature de CICFlowMeter. **Un número perfecto,
perfectamente vacío.**

**Lo iba a escribir Claude, mientras arreglaba las 5 features rotas, con toda la
atención puesta y sabiendo exactamente lo que cazábamos.** Igual que el
`test_l1_feature_contract.cpp` commiteado vacío (DAY 217).

**La solución correcta no reconstruye: usa `payload_len`, que el kernel ya calculó
con los offsets REALES.**

---

## 📐 EL PATRÓN — actualizado. Ya son QUINCE. Y ahora tiene NOMBRE.

*Un artefacto que afirma haber verificado algo, sin haberlo verificado.*

| # | Caso | DAY |
|---|---|---|
| 1 | `entropy` del ransomware = varianza ÷ 100.000 | — |
| 2 | `level3_web`/`level3_internal` nunca parseados | 215 |
| 3 | 5/23 features de L1 duplicadas o constantes | 216 |
| 4 | `test_l1_feature_contract.cpp` commiteado VACÍO | 217 |
| 5 | El `max()` que NO PUEDE suprimir FP — claim del abstract | 217 |
| 6 | `test_autonomy_publisher` flaky: `sleep` en vez de handshake | 218 |
| 7 | `contract_validator.cpp` en `.backup` — el testigo amordazado | 218 |
| 8 | 5 `add_executable` **sin** `add_test` — tests que no corren | 218 |
| 9 | `Makefile:1197` — `\|\| echo` traga el exit code del gate | 218 |
| 10 | `PayloadAnalyzer`: 4/4 tests de patrones devuelven `false` | 218 |
| 11 | Variante B: 8 tests sobre el camino que **no** calcula features | 218 |
| 12 | 2/10 features del DDoS son constantes hardcodeadas | 218 |
| 13 | `set_final_decision()` — el detector decide, ADR-007 sin sitio | 218 |
| 14 | Comentario que afirma que un campo no existe, y existe | 218 |
| 15 | **Seis greps ciegos de Claude, cada uno con salida limpia** | 218 |

**NO ES UN PATRÓN DE BUGS. ES UN PATRÓN DE FALSA EVIDENCIA.**

Y por eso **ninguno lo cazó el testing convencional: el testing convencional TAMBIÉN
es un artefacto que afirma haber verificado.**

> **El caso 15 es el más incómodo, y va al paper.** Seis `grep` distintos, hoy, con
> patrones estrechos, devolviendo salidas **limpias y engañosas**. Un `grep` vacío
> **no es evidencia de ausencia**: es evidencia de que el patrón no casó. **Es el
> primo hermano del test vacío.** Cada patrón de búsqueda es una *hipótesis* sobre
> dónde está el bicho — y una hipótesis estrecha devuelve un resultado limpio que
> **parece una respuesta.**
>
> Uno de ellos (`sniffer/build/` en vez de `sniffer/build-debug/`) estuvo a punto de
> producir un **P0 falso**. Lo frenó Alonso: *"no me lo puedo creer, cómo se lanzan
> los tests del sniffer, porque haberlos, haylos."* **La intuición del que conoce el
> árbol, contra el artefacto limpio de la herramienta.**

---

## 🎯 EL MÉTODO, DESTILADO (Alonso, DAY 218)

> *"En el fondo estamos arreglando los componentes de medición científicos del
> proyecto. Uno a uno y con paciencia. Con método. Encontramos lo roto, establecemos
> hipótesis de por qué está roto, se escribe el test, al principio sale rojo, se
> arregla, debe salir verde. Uno a uno."*

**El RED obligatorio no es una formalidad: es la ÚNICA forma de demostrar que el
instrumento está conectado.**

**Un test que nunca has visto fallar no es un test: es una hipótesis sobre un test.**

---

## ▶️ SIGUIENTE — PASO 2, ahora con el terreno conocido

**Crear `sniffer/tests/test_feature_extractor.cpp`** — la primera suite del
`FeatureExtractor`. Primer caso: `act_data_pkt_fwd`.

**No se toca el kernel. No se toca el `.proto`. No se toca `SimpleEvent`.**

1. `flow_manager.hpp` — vector `fwd_payload_lengths`, apilado en el mismo bloque
   `if (is_fwd)` que `fwd_lengths` (~línea 96). **Alineado índice a índice por
   construcción.**
2. `feature_extractor.hpp` — `ACT_DATA_PKT_FWD` **AL FINAL** del enum (índice **83**).
   `FEATURE_COUNT`: **83 → 84**. Actualizar el comentario de
   `l1_feature_contract.hpp:92` ("enum de 83" → 84).
3. `feature_extractor.cpp` — `extract_act_data_pkt_fwd()`: contar `payload_len > 0`.
   Y la línea de despacho `features[ACT_DATA_PKT_FWD] = ...`.
4. **TEST PRIMERO. RED→GREEN.**
    - 3 paquetes fwd (2 con payload, 1 ACK puro) → **debe dar 2**
    - flujo de sólo-ACKs → **debe dar 0** ← *este mata el bug de Ethernet*
    - flujo vacío → **0**, sin crash

**RED de verdad:** el test no compila hasta que existe `ACT_DATA_PKT_FWD`.

---

## 📌 COMMITS DE DAY 218

```
5d9bd43e  fix(common): DEBT-TEST-AUTONOMY-PUBLISHER-FLAKY-001 — handshake real PUB/SUB
92ce8a09  test(sniffer): DEBT-SNIFFER-TESTS-NOT-REGISTERED-001 — registrar 5 huérfanos
```

**BLOQUEADO:** commit del `|| echo` (`DEBT-GATE-COMPONENTS-SWALLOWED-EXIT-001`),
hasta cerrar `DEBT-PAYLOAD-ANALYZER-PATTERNS-INERT-001`.

**SIGUE SIN COMMITEAR (a propósito):** instrumentación DAY 216 —
`ml-detector/include/zmq_handler.hpp`, `ml-detector/src/zmq_handler.cpp`.
Salvada en `docs/day216_instrumentation.patch`. **⚠️ OJO con `git commit -a`.**

---

## FEDER

Go/no-go **~1 agosto 2026** — **19 días.** Deadline **22 septiembre 2026**.

> *"No pienso entregar nada que no esté bien fundamentado. El pipeline tiene que
> funcionar bien."* — Alonso, DAY 216.

**Las siete deudas de este documento son PRE-FEDER.** Ninguna es cosmética. Todas
afectan a la capacidad del proyecto de **medir lo que dice que mide**.