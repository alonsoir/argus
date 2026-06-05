#!/usr/bin/env python3
"""
update_docs_day175.py — Actualización documental idempotente DAY 175.

Ejecutar EN EL HOST, desde la raíz del repo (test-zeromq-docker), sobre el
repo montado. NO commitea nada: al final sugiere `git diff` para revisión.

Cada inserción comprueba su marca ANTES de tocar el fichero. Re-ejecutar el
script no duplica nada (idempotente por marcador).

Cierra DAY 175:
  - Zona bronce correlation_v1 CABLEADA y verificada E2E (3712 filas reales).
  - 4 pasos verdes: CMake + hook + round-trip test + pipeline vivo.
  - Decisiones del Consejo: injectors primero (ambos modos), col 17 -> string
    simbólico, ADR-054 modelo de confianza (Ed25519 con/en-vez-de HMAC).
  - 2 deudas nuevas: KEY-PROVISIONING y PROVISIONING-E2E.

Uso:
    python3 update_docs_day175.py            # aplica cambios
    python3 update_docs_day175.py --check    # solo informa, no escribe
"""

import sys
import os

CHECK_ONLY = "--check" in sys.argv

# Rutas reales relativas a la raíz del repo (donde se ejecuta el script).
BACKLOG = "docs/BACKLOG.md"
README = "README.md"
PROMPT = "docs/continuity/PROMPT_CONTINUE_CLAUDE.md"

# Contador de acciones para el resumen final.
results = []


def log(status, msg):
    results.append((status, msg))
    tag = {"ok": "[ok]", "skip": "[skip]", "err": "[ERR]"}[status]
    print(f"{tag} {msg}")


def read(path):
    if not os.path.isfile(path):
        log("err", f"NO EXISTE: {path}")
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write(path, content):
    if CHECK_ONLY:
        return
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def insert_after(path, content, anchor, block, marker):
    """Inserta `block` justo DESPUES de la primera aparición de `anchor`.
    No hace nada si `marker` ya está presente en el fichero."""
    if marker in content:
        log("skip", f"{path}: '{marker}' ya presente")
        return content
    idx = content.find(anchor)
    if idx == -1:
        log("err", f"{path}: ancla no encontrada -> {anchor[:60]!r}")
        return content
    pos = idx + len(anchor)
    new = content[:pos] + block + content[pos:]
    log("ok", f"{path}: insertado bloque con marca '{marker}'")
    return new


def insert_before(path, content, anchor, block, marker):
    """Inserta `block` justo ANTES de la primera aparición de `anchor`.
    `anchor` puede ser un prefijo de la línea (no exige fin de línea).
    No hace nada si `marker` ya está presente."""
    if marker in content:
        log("skip", f"{path}: '{marker}' ya presente")
        return content
    idx = content.find(anchor)
    if idx == -1:
        log("err", f"{path}: ancla no encontrada -> {anchor[:60]!r}")
        return content
    new = content[:idx] + block + content[idx:]
    log("ok", f"{path}: insertado bloque con marca '{marker}'")
    return new


def replace_once(path, content, old, new_text, marker):
    """Reemplaza la primera aparición de `old` por `new_text`.
    No hace nada si `marker` ya está presente."""
    if marker in content:
        log("skip", f"{path}: '{marker}' ya presente")
        return content
    if old not in content:
        log("err", f"{path}: texto a reemplazar no encontrado -> {old[:60]!r}")
        return content
    new = content.replace(old, new_text, 1)
    log("ok", f"{path}: reemplazado con marca '{marker}'")
    return new


# ════════════════════════════════════════════════════════════════════
# 1) docs/BACKLOG.md
# ════════════════════════════════════════════════════════════════════
def update_backlog():
    c = read(BACKLOG)
    if c is None:
        return

    # 1a. Sección de cierre DAY 175, insertada justo ANTES de la primera
    #     sección de día ratificado ("## ✅ RATIFICADO DAY 173 — ADR-052 ...").
    #     Insertamos delante del ancla (no detrás) para que DAY 175 quede arriba.
    anchor_175 = "## ✅ RATIFICADO DAY 173 — ADR-052 v3.2"
    block_175 = """## ✅ CERRADO DAY 175 — Zona bronce correlation_v1 cableada + verificada E2E

### Bronce correlation_v1 — writer CABLEADO en ml-detector (4 pasos verdes)
- **Status:** ✅ COMPLETADO DAY 175 — rama `feature/day175-bronze-wiring`
- **Hito del día:** el `CorrelationWriter` (productor, ml-detector) deja de estar
  suelto. Cadena completa demostrada con datos REALES:
  sniffer eBPF → community_id → ZMQ → ml-detector → bronce → reader valida.
- **Paso 1 — CMake:** `correlation_writer.cpp` dado de alta en SOURCES del
  ml-detector (lista explícita, no GLOB). OpenSSL ya linkado por `CsvEventWriter`.
- **Paso 2 — Hook punto único:** `correlation_writer_` construido en `zmq_handler`
  junto a `csv_writer_`, reutilizando el MISMO `hmac_key_hex_` (cero divergencia de
  clave por construcción). `write_record()` cableado ANTES de la bifurcación
  rag/no-rag — evita el "bug de los dos caminos". Filtro:
  `if (correlation_writer_ && !community_id().empty())`.
- **Paso 3 — Round-trip unitario (prueba de oro):** `test_correlation_roundtrip`
  en `ml-detector/tests/integration/`. Escribe un `NetworkSecurityEvent` con el
  `CorrelationWriter` REAL, relee la última línea y la pasa al `parse_and_verify`
  REAL del correlation-engine. Verifica 18 campos + HMAC. El test vive en
  ml-detector (que ya linka protobuf/OpenSSL) e incluye el reader del engine, NO al
  revés — el correlation-engine se mantiene limpio de protobuf. Gateado contra
  rebuild limpio (`make ml-detector && make test-components`). PASSED.
- **Paso 4 — Pipeline vivo:** replay de `smallFlows.pcap` (14.261 paquetes, 1.209
  flujos) por la interfaz del cliente. **3.712 filas reales** en
  `/vagrant/logs/correlation/argus/2026-06-05.csv`, todas con `community_id`
  poblado por el sniffer eBPF (formato `1:wKZ...=`). Sello final: una fila REAL
  validada por el `parse_and_verify` del engine con la clave de PRODUCCIÓN de etcd.

### Lección DAY 175 — la trampa del provisioning de clave
- El round-trip unitario (paso 3) era necesario pero NO suficiente: validaba
  writer↔reader con una clave de test compartida por construcción, lo que ocultaba
  el problema de *provisioning*. La clave HMAC del ml-detector NO es `seed.hex`
  sino la servida por etcd en `/secrets/ml-detector` (campo `key`). Validar una
  fila real con `seed.hex` fue RECHAZADO (bien rechazado); con la clave de etcd,
  VALIDÓ. Lección: el consumidor en producción debe pedir la clave a
  `/secrets/<componente>` de etcd, igual que el ml-detector. → DEBT-BRONZE-KEY-PROVISIONING-001.

### REGLA PERMANENTE nueva DAY 175
- **REGLA PERMANENTE (DAY 175):** Construir SIEMPRE vía target del Makefile raíz
  (`make ml-detector`, etc.), NUNCA `cmake -S . -B build` directo. El target corre
  la dependencia `proto` (regenera y distribuye `network_security.pb.h` fresco a
  `build-debug/proto/`) y aplica los flags `-Werror` desde el Makefile (fuente
  única de verdad). Un `cmake` directo puede compilar contra un `.pb.h` RANCIO y
  romper de forma confusa (incidente DAY 175: `NetworkFeatures has no member
  community_id` con proto stale).

### INVARIANTE confirmado DAY 175 — community_id en TODAS las variantes del sniffer
- `community_id` es el punto de unión con Suricata/Zeek (y futuro Wazuh). TODAS las
  variantes del sniffer (x86/ARM, eBPF/libpcap, special/plain) DEBEN poblarlo.
  Confirmado por grep: solo el sniffer real lo puebla hoy (`ring_consumer.cpp` para
  eBPF, `main_libpcap.cpp` para libpcap). Los injectors sintéticos NO lo rellenan
  todavía → los tests sintéticos no ejercitan el bronce. → tarea DAY 176.

### Council of Sages DAY 175 — decisiones (8/8 respondieron)
- **Q1 — Orden de batalla: injectors PRIMERO (unánime 8/8).** Sin injectors que
  pueblen community_id no hay bronce determinista en CI (pcap+eBPF es caro y no
  determinista). Decisión Alonso: implementar AMBOS modos de injector — isomorfo
  realista (reusa el algoritmo del sniffer real, `compute_community_id`) Y mock
  auto-identificable (estilo `synth:test:hash`, no se confunde con tráfico real).
- **Q2 — authoritative_source (col 17): cambiar a STRING simbólico.** El statu quo
  (int crudo con mapeo implícito en el reader) fue rechazado por consenso. Decisión
  Alonso: escribir el nombre simbólico (`ML_PRIORITY`, etc.) vía `DetectorSource_Name()`.
  Argumento clínico (Qwen): Parquet aplica dictionary-encoding nativo aguas arriba,
  así que el ahorro de tamaño del int es ~nulo tras compresión; gana la estabilidad
  de contrato frente a la evolución del enum en el .proto. Es el momento más barato
  de la historia del proyecto para el cambio (primer día con bronce real).
- **Q3 — Modelo de confianza a escala: abrir ADR.** HMAC simétrico vale intra-nodo,
  pero no escala a N sensores → Kuzu central (gestión de N claves + sin no-repudio).
  Todos apuntan a Ed25519 (ya en uso para plugins, ADR-025). Matiz de Kimi: Ed25519
  por-fila es lento a volumen → esquema jerárquico (Ed25519 firma una clave de sesión
  HMAC de corta vida; HMAC valida el volumen de filas). → ADR-054 (ver abajo).

### DEBT-BRONZE-KEY-PROVISIONING-001 — Clave HMAC del bronce desde etcd /secrets
**Severidad:** 🟡 P1
**Estado:** ABIERTO — DAY 175
**Componente:** `correlation-engine` (lado consumidor) + `ml-detector` (productor)
La clave HMAC del bronce NO es `seed.hex` — es la servida por etcd en
`/secrets/<componente>` (campo `key`). El writer (ml-detector) ya la obtiene así.
Cuando el correlation-engine consuma bronce en producción (file_watch → Avro), su
arranque DEBE pedir la clave a etcd `/secrets/<componente>` EXACTAMENTE igual,
no leerla de `seed.hex`. Descubierto DAY 175 al validar una fila real: `seed.hex`
fue rechazado, la clave de etcd validó. Si esto se descubre con el lado Kuzu y
miles de filas "que no validan", es un incidente de medianoche.
**Test de cierre:** el consumidor obtiene la clave del mecanismo real de
provisioning (etcd `/secrets/<componente>`) y valida una fila real escrita por el
ml-detector. Validar con `seed.hex` → RECHAZO esperado.
**Estimación:** 1 sesión (junto al file_watch del consumidor).

### DEBT-BRONZE-PROVISIONING-E2E-001 — Test de provisioning real (no clave hardcodeada)
**Severidad:** 🟡 P1
**Estado:** ABIERTO — DAY 175 (propuesta ChatGPT + refinamiento Qwen — Consejo 8/8)
**Componente:** `ml-detector/tests/integration/test_correlation_roundtrip.cpp`
El round-trip actual usa una clave de test compartida por construcción (`KEY_HEX`
hardcodeada en ambos lados), lo que VALIDA el contrato pero OCULTA fallos de
provisioning. Modificar el test para que la clave venga de una variable de entorno
o de un mock de etcd que AMBOS lados (writer y reader) consulten — validando así el
*mecanismo de obtención de la confianza*, no solo el contrato de datos. El fallo
real de DAY 175 pertenecía al provisioning, no al contrato de bronce; merece su
propio test.
**Test de cierre:** writer y reader obtienen la misma clave del mismo mecanismo
real (env-var o mock etcd). Divergencia de clave entre lados → fila rechazada.
**Estimación:** 1 sesión.

### Tarea DAY 176 — Injectors sintéticos pueblan community_id (ambos modos)
**Severidad:** 🟡 P1 — desbloquea bronce determinista en CI
**Estado:** ABIERTO — DAY 175 (Consejo 8/8, Q1)
**Componente:** `tools/synthetic_sniffer_injector.cpp` (primero) + resto de injectors
Hoy solo el sniffer real puebla `community_id`; los injectors sintéticos lo dejan
vacío y el hook del bronce los descarta → los E2E sintéticos NO ejercitan el bronce.
Implementar AMBOS modos (decisión Alonso): (1) **isomorfo realista** — calcula el
community_id con la MISMA función que el sniffer real (`compute_community_id`), no
reimplementación, para que el bronce de CI sea byte a byte como el de producción;
(2) **mock auto-identificable** — formato distinguible (estilo `synth:test:hash`)
para no contaminar análisis con tráfico falso. Empezar por `synthetic_sniffer_injector`
(alimenta el camino que hoy ejercita el bronce).
**Test de cierre:** injector isomorfo → bronce de CI con community_id idéntico al de
producción para la misma 5-tupla. Injector mock → community_id reconocible como
sintético, descartado por el correlation-engine antes de Kuzu.
**Estimación:** 1-2 sesiones.

### Cambio DAY 176 — authoritative_source (col 17) a string simbólico
**Severidad:** 🟡 P1 — contrato correlation_v1
**Estado:** ABIERTO — DAY 175 (Consejo, Q2; decisión Alonso)
**Componente:** `ml-detector/src/correlation_writer.cpp` + `correlation-engine` reader
La columna 17 del contrato `correlation_v1` pasa de int crudo (`static_cast<int>`
del enum `DetectorSource`) a nombre simbólico (`DetectorSource_Name()`:
`ML_PRIORITY`, `DIVERGENCE`, etc.). El reader (`correlation_record.hpp`) se adapta a
leer string. Motivo: bronce auto-descriptivo, estable frente a reordenación/inserción
de valores del enum en el .proto; coste de tamaño irrelevante (dictionary-encoding en
Parquet aguas arriba). Es el primer día con bronce real → el momento más barato para
cambiarlo.
**Test de cierre:** writer escribe `ML_PRIORITY` en col 17; reader parsea el string;
round-trip verde. Bronce histórico migrado o re-generado (3.712 filas de DAY 175 son
de prueba, no histórico de valor).
**Estimación:** 0.5-1 sesión.

### ADR-054 — Modelo de confianza de la zona bronce a escala multi-nodo (PENDIENTE redacción)
**Estado:** ⏳ BORRADOR PENDIENTE — DAY 175 (Consejo 8/8, Q3; decisión Alonso)
**Nota de numeración:** ADR-053 ya está RESERVADO (stub DAY 173: JA3/JA4 + cadena TLS
profunda + anomalía L3/BGP). Por tanto este ADR toma el **054**. Verificado contra el
BACKLOG antes de asignar.
**Contenido a redactar:** el HMAC simétrico por-componente vale para integridad
intra-nodo (detectar fila corrupta/truncada por append no-atómico), pero NO escala a
la arquitectura medallion multi-nodo (N sensores → Kuzu central): obliga a que el
central conozca N claves simétricas (superficie de ataque enorme; comprometer el
central permite FALSIFICAR bronce de cualquier sensor) o a un llavero de N claves
(pesadilla de rotación), y no da no-repudio. Explorar Ed25519 (ya en uso para plugins,
ADR-025) JUNTO CON o EN VEZ DE HMAC. **Eje de decisión central (preocupación Alonso):**
coste CPU/RAM del servidor central validando fila por fila con Ed25519 sobre
cientos/miles de ficheros bronce. Opción jerárquica de Kimi sobre la mesa desde el
día uno: Ed25519 firma una clave de sesión HMAC de corta vida (no-repudio +
rotación granular del asimétrico) y el HMAC valida el volumen de filas (velocidad del
simétrico). Flujo: borrador → Consejo → aprobación → implementación, ANTES de escribir
el lado consumidor cross-nodo.

"""
    c = insert_before(BACKLOG, c, anchor_175, block_175 + "\n\n",
                      marker="CERRADO DAY 175 — Zona bronce correlation_v1")

    write(BACKLOG, c)


# ════════════════════════════════════════════════════════════════════
# 2) README.md  — conservador: solo el estado que cambió.
# ════════════════════════════════════════════════════════════════════
def update_readme():
    c = read(README)
    if c is None:
        return

    # 2a. Bloque de hitos DAY 175, insertado justo antes de "### Hitos DAY 173".
    anchor = "### Hitos DAY 173 🏛️"
    block = """### Hitos DAY 175 🎉
- **Zona bronce `correlation_v1` CABLEADA y verificada E2E.** El `CorrelationWriter`
  (productor, ml-detector) deja de estar suelto. Cadena completa con datos reales:
  sniffer eBPF → community_id → ZMQ → ml-detector → bronce → `parse_and_verify` del
  correlation-engine. **3.712 filas reales** en `/vagrant/logs/correlation/argus/`,
  todas con community_id poblado; una fila real validada con la clave de PRODUCCIÓN
  de etcd. 4 pasos verdes: alta CMake + hook en punto único (antes de la bifurcación
  rag/no-rag) + round-trip unitario (prueba de oro writer↔reader) + pipeline vivo.
  - **Lección (DEBT-BRONZE-KEY-PROVISIONING-001):** la clave HMAC del bronce no es
    `seed.hex` sino la de etcd `/secrets/<componente>`. El round-trip con clave
    hardcodeada validaba el contrato pero ocultaba el provisioning.
  - **REGLA PERMANENTE (DAY 175):** construir siempre vía `make <target>` (corre la
    dependencia `proto` y aplica `-Werror` del Makefile), nunca `cmake` directo
    (riesgo de `.pb.h` rancio).
  - **INVARIANTE:** community_id es el punto de unión con Suricata/Zeek — TODAS las
    variantes del sniffer (x86/ARM, eBPF/libpcap) deben poblarlo.
  - **Consejo 8/8:** injectors sintéticos primero (ambos modos: isomorfo + mock) ·
    col 17 `authoritative_source` → string simbólico · ADR-054 (modelo de confianza
    Ed25519 con/en-vez-de HMAC a escala multi-nodo) pendiente de redacción.

"""
    c = insert_before(README, c, anchor, block, marker="Hitos DAY 175")

    write(README, c)


# ════════════════════════════════════════════════════════════════════
# 3) docs/continuity/PROMPT_CONTINUE_CLAUDE.md
#    Reescribe el bloque de ARRANQUE para DAY 176.
# ════════════════════════════════════════════════════════════════════
def update_prompt():
    c = read(PROMPT)
    if c is None:
        return

    new_arranque = """# DAY 175 — Zona bronce correlation_v1 cableada + verificada E2E. Prompt de continuidad.

═══════════════════════════════════════════════════════════════════════════════
ARRANQUE DAY 176 — LEER ESTO PRIMERO.
═══════════════════════════════════════════════════════════════════════════════
DAY 175 cerró el cableado del bronce: el CorrelationWriter (ml-detector) produce
correlation_v1 REAL, consumible por el reader del correlation-engine. 4 pasos verdes
(CMake + hook punto único + round-trip unitario + pipeline vivo: 3712 filas reales
con community_id, una validada con la clave de PRODUCCIÓN de etcd).

DOS BATALLAS DAY 176, ninguna bloqueada por lo de hoy:

(A) INJECTORS SINTÉTICOS pueblan community_id — AMBOS modos (decisión Alonso, Q1):
    1. ISOMORFO REALISTA: calcular community_id con la MISMA función que el sniffer
       real (sniffer::flow::compute_community_id), NO reimplementación. Empezar por
       tools/synthetic_sniffer_injector.cpp (alimenta el camino que hoy ejercita el
       bronce). Sin esto, los E2E sintéticos NO ejercitan el bronce (community_id
       vacío -> el hook lo descarta).
    2. MOCK AUTO-IDENTIFICABLE: formato distinguible (estilo "synth:test:hash") para
       no contaminar análisis con tráfico falso. El correlation-engine lo descarta
       antes de Kuzu.
    -> Esto desbloquea bronce DETERMINISTA en CI (hoy dependemos de pcap+eBPF, caro y
       no determinista).

(B) CAMBIO col 17 a STRING simbólico (decisión Alonso, Q2):
    - correlation_writer.cpp: escribir DetectorSource_Name() en vez de
      static_cast<int>. Reader (correlation_record.hpp) lee string.
    - Motivo: contrato auto-descriptivo, estable frente a evolución del enum en el
      .proto. Coste de tamaño irrelevante (dictionary-encoding Parquet aguas arriba).
    - Es el momento más barato: primer día con bronce real (las 3712 filas son de
      prueba, no histórico de valor).

(C) LADO CONSUMIDOR del engine (cuando toque): file_watch de bronce -> lectura de
    clave desde etcd /secrets/<componente> -> parse_and_verify -> Avro -> ZMQ.
    Aquí aterriza DEBT-BRONZE-KEY-PROVISIONING-001. parse_and_verify debe ser el
    PRIMER paso del consumidor (validar antes de tocar Kuzu) — riesgo señalado por
    Mistral: clave mala corrompe el grafo.

PENDIENTE DE REDACCIÓN — ADR-054 (modelo de confianza bronce multi-nodo, Q3):
    HMAC simétrico vale intra-nodo; no escala a N sensores -> Kuzu central. Explorar
    Ed25519 (ya en uso, ADR-025) CON o EN VEZ DE HMAC. Eje de decisión: coste CPU/RAM
    del central validando fila por fila con Ed25519 sobre cientos/miles de ficheros
    bronce. Opción jerárquica (Kimi): Ed25519 firma clave de sesión HMAC corta;
    HMAC valida el volumen. Flujo borrador -> Consejo -> aprobación, ANTES del lado
    consumidor cross-nodo. (OJO numeración: ADR-053 ya RESERVADO para JA3/JA4+TLS+BGP.)

LECCIONES DAY 175 (no repetir):
- STALE PROTO: construir SIEMPRE vía `make <target>` (corre dep `proto`, regenera y
  distribuye network_security.pb.h fresco a build-debug/proto/, aplica -Werror del
  Makefile). NUNCA `cmake -S . -B build` directo -> compila contra .pb.h rancio y
  rompe confuso (incidente DAY 175: "NetworkFeatures has no member community_id").
- KEY PROVISIONING: la clave HMAC del bronce NO es seed.hex, es la de etcd
  /secrets/<componente> (campo key). El round-trip con clave hardcodeada valida el
  contrato pero OCULTA el provisioning. El consumidor en prod DEBE pedirla a etcd.
- INVARIANTE community_id: TODAS las variantes del sniffer (x86/ARM, eBPF/libpcap,
  special/plain) DEBEN poblar community_id — es el punto de unión con Suricata/Zeek.

PRIMER COMANDO DAY 176:
vagrant ssh -c "grep -rn 'community_id\\|compute_community_id\\|set_community_id' /vagrant/tools/synthetic_sniffer_injector.cpp"
# confirmar que el injector NO puebla community_id hoy, y localizar dónde sellar la
# 5-tupla para invocar compute_community_id. Luego (A) modo isomorfo -> mock -> (B).

═══════════════════════════════════════════════════════════════════════════════
RESUMEN DAY 175 — Bronce cableado (los 4 pasos)
═══════════════════════════════════════════════════════════════════════════════
Día de cableado y verificación, no de ADR. El CorrelationWriter pasó de suelto a
cableado y produciendo bronce real consumible.

PASO 1 — CMake: correlation_writer.cpp dado de alta en SOURCES del ml-detector
  (lista explícita, no GLOB). OpenSSL ya linkado por CsvEventWriter.
PASO 2 — Hook punto único: correlation_writer_ construido junto a csv_writer_ en
  zmq_handler, reutilizando el MISMO hmac_key_hex_ (cero divergencia de clave por
  construcción). write_record() cableado ANTES de la bifurcación rag/no-rag (NO
  dentro del if rag/csv) — evita el "bug de los dos caminos". Filtro:
  if (correlation_writer_ && !community_id().empty()).
PASO 3 — Round-trip unitario (prueba de oro): test_correlation_roundtrip en
  ml-detector/tests/integration/. Escribe NetworkSecurityEvent con CorrelationWriter
  REAL, relee última línea, parse_and_verify REAL del engine. 18 campos + HMAC.
  El test vive en ml-detector (ya linka protobuf/OpenSSL) e incluye el reader del
  engine, NO al revés — el correlation-engine se mantiene limpio de protobuf.
  Gateado contra rebuild limpio (make ml-detector && make test-components). PASSED.
PASO 4 — Pipeline vivo: replay smallFlows.pcap (14261 paquetes, 1209 flujos).
  3712 filas reales en /vagrant/logs/correlation/argus/2026-06-05.csv, todas con
  community_id poblado por el sniffer eBPF (formato 1:wKZ...=). Sello final: una
  fila REAL validada por parse_and_verify con la clave de PRODUCCIÓN de etcd
  (/secrets/ml-detector campo key) — NO seed.hex.

DECISIONES DEL CONSEJO (8/8 respondieron):
- Q1 injectors primero (unánime) -> AMBOS modos (Alonso).
- Q2 col 17 -> STRING simbólico (Alonso; statu quo rechazado por consenso).
- Q3 abrir ADR-054 modelo de confianza Ed25519 con/en-vez-de HMAC (Alonso).
DEUDAS NUEVAS: DEBT-BRONZE-KEY-PROVISIONING-001, DEBT-BRONZE-PROVISIONING-E2E-001.

═══════════════════════════════════════════════════════════════════════════════
RESUMEN DAY 174 (histórico)
═══════════════════════════════════════════════════════════════════════════════"""

    # El bloque viejo va desde el título del fichero hasta el marcador de
    # "RESUMEN DAY 174" (incluido), y lo sustituimos entero por new_arranque.
    start = c.find("# DAY 174 — correlation-engine")
    end_marker = "RESUMEN DAY 174\n"
    end = c.find(end_marker)
    if "ARRANQUE DAY 176" in c:
        log("skip", f"{PROMPT}: 'ARRANQUE DAY 176' ya presente")
        return
    if start == -1 or end == -1:
        log("err", f"{PROMPT}: no se localizó el bloque de arranque viejo a sustituir")
        return
    # end apunta al inicio de "RESUMEN DAY 174"; subimos a incluir la línea de
    # cabecera de banda "═══" que lo precede.
    band = "═══════════════════════════════════════════════════════════════════════════════\n"
    # Buscar la banda inmediatamente anterior a end.
    pre = c.rfind(band, 0, end)
    pre2 = c.rfind(band, 0, pre) if pre != -1 else -1
    if pre2 == -1:
        log("err", f"{PROMPT}: no se localizó la banda previa a RESUMEN DAY 174")
        return
    new = c[:start] + new_arranque + "\n" + c[end + len(end_marker):]
    log("ok", f"{PROMPT}: bloque de arranque reescrito para DAY 176")
    write(PROMPT, new)


# ════════════════════════════════════════════════════════════════════
def main():
    root_ok = all(os.path.isfile(p) for p in (BACKLOG, README, PROMPT))
    if not root_ok:
        print("ERROR: ejecuta el script desde la RAÍZ del repo (test-zeromq-docker).")
        print("Esperados:")
        for p in (BACKLOG, README, PROMPT):
            print(f"  - {p} {'OK' if os.path.isfile(p) else 'NO ENCONTRADO'}")
        sys.exit(1)

    print("=" * 70)
    print("update_docs_day175.py" + ("  [CHECK ONLY]" if CHECK_ONLY else ""))
    print("=" * 70)

    update_backlog()
    update_readme()
    update_prompt()

    print("=" * 70)
    oks = sum(1 for s, _ in results if s == "ok")
    skips = sum(1 for s, _ in results if s == "skip")
    errs = sum(1 for s, _ in results if s == "err")
    print(f"Resumen: {oks} aplicados · {skips} omitidos (ya presentes) · {errs} errores")
    if errs:
        print("\n⚠️  Hubo errores — revisa las anclas antes de confiar en el resultado.")
        sys.exit(2)
    if CHECK_ONLY:
        print("\n(CHECK ONLY — no se escribió nada.)")
    else:
        print("\nRevisa los cambios antes de commitear:")
        print("  git diff docs/BACKLOG.md README.md docs/continuity/PROMPT_CONTINUE_CLAUDE.md")
        print("\nEl script NO commitea nada por diseño.")


if __name__ == "__main__":
    main()