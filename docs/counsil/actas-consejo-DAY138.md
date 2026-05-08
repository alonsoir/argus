# ACTAS CONSEJO DE SABIOS — DAY 138
# aRGus NDR | 2026-05-01 | feature/variant-b-libpcap @ da1badf7
# Quórum: 8/8 (Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral)

---

## VEREDICTOS CONSOLIDADOS

### [Q1] PcapCallbackData — Lifetime y seguridad
**Consenso: 8/8 — Correcto hoy. Documentar invariante.**

La solución `PcapCallbackData{cb, ctx}` como miembro de `PcapBackend` es segura
porque `pcap_dispatch` es síncrono y el struct vive al menos mientras dura la llamada.
No hay riesgo de dangling pointer en el diseño actual.

**Acción registrada:** Añadir comentario de contrato de lifetime en `pcap_backend.hpp`:
```
// LIFETIME CONTRACT: PcapCallbackData es válido durante toda la sesión
// de captura. No destruir PcapBackend durante pcap_dispatch() activo.
// Señalización asíncrona (SIGALRM + shutdown concurrente) no soportada
// en este diseño monohilo — requeriría weak_ptr refactoring.
```

ChatGPT propone blindaje futuro con `std::atomic<bool> active` en el struct.
Registrado como mejora opcional post-FEDER, no bloqueante ahora.

---

### [Q2] dontwait vs backpressure
**Consenso: 8/8 — Mantener `dontwait`. Añadir observabilidad.**

`dontwait` es la única política correcta para monohilo: si ZMQ bloquea,
`pcap_dispatch` se congela y el kernel dropa en la NIC ring buffer, que es
peor que descartar en userspace con contador.

**Acción registrada (DEBT-VARIANT-B-CONFIG-001):** Exponer `send_failures`
como métrica observable. Alerta si drop_rate > 0.1% (ChatGPT, DeepSeek, Kimi).
No implementar sleep+retry — introduce latencia impredecible en monohilo.

---

### [Q3] sniffer-libpcap.json — Campos a preservar/eliminar
**Consenso: 8/8 — JSON propio simplificado.**

**Eliminar definitivamente (hardcodear en binario):**
- `zmq_sender_threads` → hardcode 1
- `io_thread_pools` → hardcode 1
- `zmq.socket_pools.push_sockets` → hardcode 1
- `threading.*` → eliminar sección completa
- `ring_buffer.*` → eliminar sección completa
- `numa_node`, `cpu_affinity` → no aplica
- `batch_size`, `flush_interval` → no aplica en callback síncrono
- Cualquier campo `ebpf.*`, `xdp.*`, `bpf.*`

**Preservar:**
- `capture.interface`
- `capture.filter.*` (BPF filter expression)
- `capture.timeout_ms` → controla el poll() (Gemini, ChatGPT, DeepSeek)
- `output_socket.address` / `port`
- `crypto.*` / seed path
- `logging.*`

**Hardcodear (no configurar — error humano evitado):**
- `capture.snaplen` → 65535 fijo (Grok confirma)
- `capture.promiscuous` → 1 fijo (NDR siempre promiscuo)

**Añadir campos nuevos específicos de Variant B:**
- `capture.buffer_size_mb` → tamaño buffer kernel libpcap (Gemini, ChatGPT)
  crítico en ARM64 con recursos limitados
- `capture.sampling.mode` / `rate` → sampleo bajo alta carga (Kimi)
  "none" por defecto, "count_based" como degradado controlado

**Dissenso menor:** DeepSeek propone `capture.endpoint_id` para identificación
en ml-detector. Registrado como opcional, baja prioridad.

---

### [Q4] Test e2e — estrategia
**Consenso: 8/8 — `pcap_open_dead()` + inject para CI. tcpreplay para stress manual.**

**CI/ctest:** `pcap_open_dead(DLT_EN10MB, 65535)` + frames sintéticos construidos
en el test. Determinista, sin root, portable. Valida parseo proto y pipeline completo.

**Validación manual:** `tcpreplay` sobre `lo` o `eth1` con pcap CIC-IDS-2017.
Requiere root, no va en ctest automático. Marcado como `REQUIRES_ROOT`.

**Estrategia de dos niveles confirmada por:** ChatGPT, DeepSeek, Gemini, Grok, Kimi, Mistral.

---

### [Q5] nftables atomicidad — argus-network-isolate
**Consenso: 8/8 — `nft -f` transaccional. Snapshot + timeout de rollback.**

Protocolo aprobado:
1. `nft list ruleset > /tmp/argus-backup-$$.nft` (snapshot previo)
2. Generar `/tmp/argus-isolate-$$.nft` con reglas de aislamiento
3. `nft -c -f` (validar sin aplicar)
4. `nft -f /tmp/argus-isolate-$$.nft` (aplicar atómico)
5. Timer rollback automático 300s (Kimi) — si admin no confirma, restaurar
6. Fallback de emergencia si `nft -f` falla: `ip link set eth0 down` (ChatGPT)

Firma Ed25519 del fichero de reglas pendiente de discusión (consistente con ADR-025).
iptables rechazado — obsoleto en Debian 12 Bookworm (Kimi).

---

### [Q6] ODR violations — prioridad
**Consenso: 8/8 UNÁNIME — ODR es P0, bloqueante para el resto del cleanup.**

Comportamiento indefinido en C++20. Puede manifestarse como corrupción silenciosa
de datos, vtables inconsistentes, crashes no reproducibles. Con Protobuf + múltiples
TUs es especialmente peligroso.

**Causa probable identificada:** `InternalNode`/`TrafficNode` definidos en headers
incluidos en TUs con diferentes flags de compilación (ml-detector -O0/DEBUG vs
sniffer -O0/DEBUG pero con diferente expansión de macros).

**Diagnóstico recomendado (Kimi, Grok):**
```bash
nm -C build/ml-detector | grep "InternalNode" | sort
nm -C build/sniffer    | grep "InternalNode" | sort
# Si coinciden → mismo símbolo → buscar flags distintos
# Si difieren → renombrar una de las dos clases
```

**Fix:** Unificar flags CMake para todas las TUs que comparten headers.
Añadir `-Werror=odr` si GCC >= 10 (Kimi, Grok).

**Orden sub-tareas DEBT-COMPILER-WARNINGS-CLEANUP-001:**
1. ODR violations (InternalNode/TrafficNode) — P0 bloqueante
2. Protobuf dual-copy en ml-detector — P1
3. signed/unsigned en zmq_handler/rag_logger/feature_extractor — P2
4. OpenSSL SHA256_Init → EVP_DigestInit_ex — P3
5. -Wreorder en ring_consumer/zmq_handler/dual_nic_manager — P4
6. -Wunused-parameter en ml_defender_features stubs — P5

---

### [Q7] ARM64 + seL4 — threading model
**Consenso: 8/8 — No diseñar para seL4 ahora. CaptureBackend ya es compatible por accidente.**

**Reutilizable en seL4:**
- `CaptureBackend` interfaz (5 métodos puros, agnóstica de threading) — 100%
- Lógica de parseo ETH/IP/TCP/UDP — 100%
- `NetworkSecurityEvent` proto serialización — con protobuf-lite
- ChaCha20-Poly1305 (stateless) — con libsodium sin threading
- ~60-70% del pipeline de datos (DeepSeek)

**Reescritura completa en seL4:**
- `PcapBackend` — libpcap no existe en seL4, driver NIC en userspace
- ZeroMQ — reemplazar por IPC capabilities de seL4 (seL4CP/CAmkES)
- `std::thread` / `std::mutex` — eliminar completamente
- ONNX Runtime — single-threaded inference o reescritura

**Decisión:** Variant B monohilo es "seL4-compatible by design" sin esfuerzo adicional.
No añadir abstracciones de threading a `CaptureBackend`. No diseñar para seL4 ahora.
YAGNI hasta que el equipo especializado esté disponible (post-FEDER research track).

---

## NUEVAS DEUDAS REGISTRADAS EN ESTA SESIÓN

### DEBT-VARIANT-B-CONFIG-001
**Severidad:** 🟡 Media
**Componente:** sniffer / main_libpcap.cpp, sniffer-libpcap.json (pendiente crear)
**Descripción:**
`sniffer-libpcap` tiene endpoint ZMQ, seed path e interface hardcodeados en el
binario. Necesita su propio JSON de configuración simplificado.
Campos multihilo (`zmq_sender_threads`, `io_thread_pools`, `ring_buffer.*`,
`threading.*`) NO aparecen en el JSON — se hardcodean en el binario con comentario
explícito. Variant B es monohilo por diseño de libpcap, no es configurable.
Campos nuevos a añadir: `capture.buffer_size_mb`, `capture.timeout_ms`,
`capture.sampling.mode/rate`. Campos hardcodeados: `snaplen=65535`, `promiscuous=1`.
Exponer `send_failures` como métrica observable.
**Pendiente también:** test e2e con `pcap_open_dead()` + inject (sin root, en CI).
Test manual con `tcpreplay` sobre `lo` (fuera de ctest).
**Corrección:** pre-demo FEDER
**Consejo DAY 138:** Ver síntesis Q2, Q3, Q4

### DEBT-PCAP-CALLBACK-LIFETIME-DOC-001
**Severidad:** 🟢 Baja — documentación
**Componente:** sniffer/include/pcap_backend.hpp
**Descripción:** Añadir comentario explícito de contrato de lifetime de
`PcapCallbackData`. Documentar que señalización asíncrona no está soportada.
**Corrección:** próxima sesión, trivial

---

## DECISIONES ARQUITECTÓNICAS CONFIRMADAS

- `dontwait` es la política correcta para NDR monohilo — no se revisita
- `nft -f` transaccional para argus-network-isolate — no iptables
- ODR es P0 bloqueante para DEBT-COMPILER-WARNINGS-CLEANUP-001
- seL4 es research track post-FEDER — no diseñar ahora
- CaptureBackend 5 métodos puros es correcto — no se revisita
- Variant B es monohilo por diseño de libpcap — no es configurable

---

## ESTADO DEUDAS POST-DAY 138

| Deuda | Estado | Prioridad |
|---|---|---|
| DEBT-CAPTURE-BACKEND-ISP-001 | ✅ CERRADA DAY 138 | — |
| DEBT-VARIANT-B-PCAP-IMPL-001 | ✅ CERRADA DAY 138 | — |
| DEBT-VARIANT-B-CONFIG-001 | 🔴 Abierta | Pre-demo FEDER |
| DEBT-COMPILER-WARNINGS-CLEANUP-001 | 🔴 Abierta | Sub-tarea ODR P0 bloqueante |
| DEBT-IRP-NFTABLES-001 | 🔴 Abierta | Pre-demo FEDER |
| DEBT-IRP-QUEUE-PROCESSOR-001 | 🔴 Abierta | Post-merge |
| DEBT-PCAP-CALLBACK-LIFETIME-DOC-001 | 🟢 Abierta | Trivial |

---

*Keypair activo: b5b6cbdf67dad75cdd7e3169d837d1d6d4c938b720e34331f8a73f478ee85daa*
*Via Appia Quality — DAY 138 cerrado.*