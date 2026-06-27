# Consejo de Sabios — DAY 176

**Fecha:** Sábado 6 de junio de 2026
**Rama:** `feature/day170-community-id-protobuf`
**Arbitro final:** Alonso
**Tipo de día:** cableado y verificación E2E (no ADR)

---

## 1. Qué hicimos hoy

DAY 175 dejó el bronce cableado (CorrelationWriter produciendo `correlation_v1` real). DAY 176 ataca el desbloqueo (A) del plan: que los **injectors sintéticos pueblen `community_id`** para tener bronce determinista en CI, sin depender de pcap + eBPF (caro y no determinista).

Resultado: **(A) cerrado y verificado E2E.** El injector sintético (`tools/synthetic_sniffer_injector.cpp`) ahora puebla `community_id` en dos modos, seleccionables por variable de entorno `ARGUS_CID_MODE`.

### Decisiones de Alonso aplicadas hoy

- **Default = `isomorphic`.** `community_id` es una feature que se calcula SIEMPRE; el injector la puebla por defecto, coherente con la invariante "todas las variantes del sniffer pueblan community_id".
- **Modo isomorfo no determinista** (IPs aleatorias, como ya hacía el injector). El determinismo de bytes lo aporta el modo mock; el isomorfo aporta realismo de formato.
- **Selección por env var, no por flag posicional.** El parser de argumentos del injector es posicional rígido (`<total> <rate> [--attack|--ransomware]`, con guarda `argc > 4`). Añadir un flag habría obligado a reescribir el parser y roto invocaciones existentes en scripts. Env var = radio mínimo.

### Implementación (3 cambios, todos compilan bajo `-Werror`)

1. **`tools/CMakeLists.txt`**: el target `synthetic_sniffer_injector` ahora enlaza `../sniffer/src/flow/community_id.cpp` (fuente COMPARTIDA con el sniffer, con include `../sniffer/include`). NO es reimplementación: es la misma función pura `sniffer::flow::compute_community_id` (SHA1 vía EVP, spec Corelight) que usa el sniffer real en producción. Esto protege la paridad cross-sensor con Suricata/Zeek por construcción.
2. **Modo isomorfo**: tras sellar la 5-tupla, el injector llama `compute_community_id(src, dst, sport, dport, proto)` exactamente como el call site de producción (`ring_consumer.cpp:884`), respetando el contrato `std::optional` (nullopt -> community_id "" diferido para proto no soportado).
3. **Modo mock**: `community_id = "synth:test:<event_id>"`, formato auto-identificable, determinista, que el correlation-engine descartará antes de Kuzu. NO llama a `compute_community_id` (escribe directo).
4. **Fail-closed**: `ARGUS_CID_MODE` con valor inválido aborta con `exit(2)` ANTES de tocar etcd/crypto/ZMQ. Un typo no degrada silenciosamente al default.

### Verificación E2E (cadena completa, sin pcap ni eBPF)

Cadena ejercitada: **injector -> ChaCha20-Poly1305 -> ZMQ -> ml-detector (multi-thread) -> hook CorrelationWriter -> bronce `correlation_v1`.**

- **Isomorfo `--attack`** (proto=6 forzado): bronce con `community_id` Corelight real, formato `1:NUKDY48U154ryx1LQNdSZUNgxfc=`. Ej.: `1,argus,synthetic-36,,1:NUKDY48U154ryx1LQNdSZUNgxfc=,...`
- **Mock `--attack`** sobre fichero limpio: 42 filas `synth:test:`, **0 filas `1:`**, **0 vacíos**. El modo mock es puro (no produce Corelight jamás, y como siempre setea, no descarta por vacío).
- **Fail-closed**: `ARGUS_CID_MODE=typo` -> exit 2, sin registrar en etcd ni abrir socket.

### Dos confirmaciones de comportamiento que salieron del proceso

- **El ml-detector NO recalcula `community_id`.** Grep exhaustivo de su `src/`: solo lecturas (`community_id()` en el hook y el writer), ningún `set_community_id` ni `compute_community_id`. El valor que llega del injector se transcribe **intacto** al bronce. **El contrato de autoridad se respeta**: `community_id` es identidad del punto de captura (sniffer), el ml-detector no tiene voz sobre él. (Esto importa para la paridad cross-sensor: si el ml-detector recalculara, rompería el match string-for-string con Suricata/Zeek.)
- **La escritura concurrente del bronce NO se entrelaza.** Con todos los componentes multi-hilo, verificamos byte a byte (`grep '1:.*synth:test:'` = 0): ninguna fila mezcla campos de dos escrituras. El mutex del CorrelationWriter (patrón CsvEventWriter) protege también entre threads del mismo proceso, no solo entre procesos.

### Lecciones operativas del día (al cuaderno)

- **Recetas `make` se lanzan desde el HOST** (ellas hacen el `vagrant ssh` internamente). Envolver `make` en `vagrant ssh -c` rompe con `vagrant: not found` dentro del guest (incidente real hoy con `proto-unified`).
- **Limpiar bronce SIEMPRE con ml-detector parado**: `tmux kill-session -t ml-detector -> rm -> make ml-detector-start`. Borrar en caliente deja las filas en un **inode huérfano** (fichero borrado pero con handle abierto por el proceso): el bronce "desaparece" por nombre y los datos van a la nada. Crítico para el script de limpieza del CI determinista que (A) habilita.
- **El injector requiere `sudo` + `LD_LIBRARY_PATH=/usr/local/lib`**, igual que el ml-detector: lee `seed.bin` (0400 root) para CryptoTransport. Sin sudo, falla con `[safe_path] Cannot open seed file` (EACCES, no ausencia).
- **STALE PROTO (recordatorio DAY 175, respetado hoy)**: construir vía `make tools` (corre dep `proto`, regenera `.pb.h` fresco). El target `tools: proto etcd-client-build crypto-transport-build` copia protobuf fresco antes de cmake.

---

## 2. Qué haremos mañana (DAY 177)

Orden tentativo, sujeto a vuestro feedback:

1. **(B) col 17 -> STRING simbólico** (decisión Alonso ya tomada en Q2 DAY 175). `correlation_writer.cpp`: escribir `DetectorSource_Name()` en vez de `static_cast<int>`. Reader (`correlation_record.hpp`) lee string. Writer + reader + el golden `test_correlation_roundtrip` cambian en el **mismo commit** (el HMAC cubre cols 0-17; cambiar col 17 mueve los bytes firmados). Las filas de prueba de hoy quedan incompatibles — ya descartables.
2. **Fix node_id vacío** (deuda nueva, ver abajo).
3. Entender el gap de filas (deuda nueva, ver abajo).

Y pendiente de redacción, sin fecha aún: **ADR-054** (modelo de confianza bronce multi-nodo, Ed25519 con/en-vez-de HMAC) — antes del lado consumidor cross-nodo.

---

## 3. Deudas nuevas abiertas hoy (no bloqueantes)

- **DEBT-INJECTOR-NODEID-001 (propuesta)**: el injector deja `node_id` (col 3, `originating_node_id`) VACÍO. En producción lo puebla el sniffer desde `config_.node_id`. Con node_id vacío, el `flow_uid` aguas arriba (`hash(node_id ‖ community_id ‖ flow_start_window)`) sale **degenerado**. El modo isomorfo "realista" debería setear un node_id sintético configurable.
- **DEBT-INJECTOR-ROWGAP-001 (propuesta)**: incluso en `--attack` (proto=6 fijo, mock que nunca descarta por vacío), llegan ~42 de 50 eventos al bronce. El ml-detector reporta `received=50, processed=50`. El gap NO es por `community_id` (mock lo tiene siempre y aun así faltan). Sospechosos: threshold del CorrelationWriter, o pérdida silenciosa en `publisher_.send(msg, zmq::send_flags::dontwait)`. Hay que cuantificarlo para que el bronce sintético sea **contable exacto** en CI (un test determinista necesita saber cuántas filas esperar).
- **Cosmético**: `enum CidMode` quedó dentro de la clase con validación duplicada en `main` (lee `getenv` dos veces). DRY perfecto = mover a scope de archivo. Trivial, no urgente.

---

## 4. Preguntas al Consejo

**Q1 — node_id sintético: ¿qué valor?**
El injector simula un sniffer pero no tiene node_id. Opciones para el modo isomorfo:
(a) un node_id sintético fijo configurable (ej. `synth-node-00`),
(b) leer el node_id real del `config.json` del sniffer (más fiel, pero acopla el injector a config de producción),
(c) un node_id auto-identificable estilo `synth:node:<n>` análogo al community_id mock.
¿Cuál respeta mejor el doble objetivo (realismo isomorfo / trazabilidad mock) sin contaminar análisis? ¿O el node_id debe seguir el MISMO eje de modo que community_id (isomorfo->real, mock->marcado)?

**Q2 — el gap de filas: ¿lo perseguimos antes de confiar en el bronce sintético para CI?**
Para CI determinista necesitamos un conteo esperado exacto. Si el gap es threshold (determinista), podemos predecirlo; si es pérdida ZMQ `dontwait` (no determinista bajo carga), el bronce sintético NO sirve para asserts de conteo exacto y habría que cambiar a `send` bloqueante en el injector o subir HWM. ¿Prioridad: investigarlo en DAY 177 antes de (B), o (B) primero (decisión ya tomada) y el gap después? ¿Alguien ve un tercer sospechoso además de threshold / `dontwait`?

**Q3 — orden DAY 177: ¿(B) col 17 primero, o estabilizar (A) primero?**
Argumento para (B) primero: decisión ya tomada, es el momento más barato (bronce aún de prueba, sin valor histórico), y cuanto antes se congele el contrato string mejor. Argumento para (A) primero: arreglar node_id + gap deja el bronce sintético plenamente fiable como herramienta de verificación ANTES de usarlo para validar el propio cambio (B). ¿Validar (B) con un injector que aún tiene node_id vacío es aceptable, o nos muerde?

**Q4 — concurrencia del bronce: ¿basta el mutex, o queremos una prueba de estrés?**
Hoy verificamos que la escritura no se entrelaza con 50 eventos a 25/s. Pero todos los componentes son multi-hilo y producción verá tasas mucho mayores. ¿Merece una prueba de estrés del CorrelationWriter (N threads, miles de filas/s, verificar 0 entrelazado + todos los HMAC válidos) antes de confiar el bronce a despliegue real? ¿O el patrón CsvEventWriter ya está suficientemente probado en producción y esto es over-engineering?

**Q5 — fuente compartida injector<->sniffer: ¿acoplamiento aceptable o frontera a formalizar?**
El injector ahora compila `community_id.cpp` desde `../sniffer/src/flow/`. Es la misma TU física (cero divergencia de implementación, respeta "no reimplementación"), pero `tools/` ahora depende del layout interno de `sniffer/`. Lo dejamos con un comentario en el CMake ("fuente compartida, no duplicar"). ¿Suficiente, o `flow/community_id` merece extraerse a una librería propia (`libs/flow-identity/`) con su contrato, dado que ya la consumen sniffer + tests + injector y mañana quizá los adaptadores Suricata/Zeek?

---

## 5. Recordatorio de contexto para el Consejo

- `community_id` usa **SHA1** (estándar Corelight, NO HMAC-SHA256). Seed uint16 = 0 (las 4 herramientas).
- El bronce `correlation_v1` son 19 columnas + HMAC-SHA256(cols 0-17). Col 4 = `community_id` (clave de join cross-sensor).
- HMAC del bronce: clave de etcd `/secrets/<componente>` campo `key`, derivada del seed maestro en provisioning (ADR-013), NO `seed.hex` crudo.
- `flow_uid` se calcula server-side en Kuzu, NO en transporte: `hash(node_id ‖ community_id ‖ flow_start_window)`, BLAKE2b-256.