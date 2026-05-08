**Consejo de Sabios — Respuesta Unánime al Day 138 (feature/variant-b-libpcap)**

Quórum: 8 modelos. Veredicto global: **aprobado con matices menores**. La refactorización de `CaptureBackend` a interfaz mínima (5 métodos puros) es limpia y correcta. La eliminación de los métodos eBPF-específicos hacia `EbpfBackend` (no-virtuales) mejora la separación de concerns y evita polución de la interfaz base. El pipeline completo de `sniffer-libpcap` mantiene **compatibilidad wire-for-wire** con Variant A, lo que es excelente para la transición y testing.

### [Q1] — Arquitectura `PcapCallbackData`

La solución actual (`PcapCallbackData{cb, ctx}` pasado como `u_char* user`) es **correcta y estándar** en C++ con libpcap.

- `pcap_dispatch` es **síncrono**: el callback se ejecuta en el hilo que llamó a `dispatch` y retorna antes de que `dispatch` continúe. No hay riesgo de lifetime mientras `PcapCallbackData` viva al menos tanto como la llamada a `pcap_dispatch` (garantizado porque es miembro de `PcapBackend`).
- El `struct` plano evita `friend`, mantiene encapsulación y es trivial de copiar/pasar.
- Alternativas peores: miembros públicos (rompe encapsulación), `std::function` (overhead innecesario y posible heap), o puntero crudo sin struct (menos legible).

**Riesgo residual bajo**: solo si alguien llama `pcap_dispatch` desde fuera del ciclo de vida normal de `PcapBackend` (lo cual ya sería un bug de uso). Recomendación: añadir un comentario claro en el struct y en `open()` indicando que el user-data debe permanecer válido durante toda la sesión de captura. No se necesita mecanismo más robusto ahora.

### [Q2] — `dontwait` vs backpressure

Para **Variant B monohilo**, la política actual (`zmq::send_flags::dontwait` + contador de fallos) es **aceptable y consistente** con Variant A.

Razones:
- Mantener paridad wire y comportamiento entre variantes simplifica el `ml-detector` y debugging.
- En monohilo, cualquier backpressure (sleep + retry) bloquearía el propio `pcap_dispatch`, lo que podría causar pérdida de paquetes en el nivel del kernel/ring-buffer de libpcap (peor que descartar en ZMQ).
- HWM=1000 es razonable para bursts cortos. Los descarte silenciosos deben ser **monitoreados** (log a warning cada N fallos, o exponer métrica `send_failures` vía etcd/Falco).

Propuesta: mantener `dontwait` por ahora. En el futuro (si se observa pérdida excesiva en pruebas de estrés), considerar un buffer intermedio pequeño (std::deque o ring) en el propio `PcapBackend` antes del send, pero eso añade complejidad y latencia. Para Variant B puro, descarte controlado es preferible a bloquear la captura.

### [Q3] — Campos del JSON para `sniffer-libpcap.json`

**Acuerdo total** con la decisión: Variant B es monohilo por diseño → los campos multihilo (`zmq_sender_threads`, `io_thread_pools`, `ring_buffer_*`, `threading.*`, etc.) **deben desaparecer** del JSON y hardcodearse en el binario con comentario explícito (incluyendo rationale y referencia al ADR).

Campos a **preservar** (útiles y relevantes):
- `capture.interface`
- `output_socket.address` / `port`
- `capture.filter.*` (BPF filter, etc.)

Campos adicionales de Variant A que recomendamos **eliminar o hardcodear** en Variant B:
- Cualquier cosa relacionada con ring buffers eBPF (`ring_buffer_size`, `consumer_batch`, etc.).
- Configuraciones de afinidad de CPU o prioridades de threads.
- Parámetros de pooling de sockets ZMQ más allá del endpoint básico.
- Cualquier timeout o buffer size que sea específico de la implementación eBPF (ej. map sizes).

Campos que Variant B **podría necesitar** y que no mencionáis:
- `capture.snaplen` (snapshot length) — muy útil para optimizar en entornos ARM64 con recursos limitados.
- `capture.promiscuous` o `capture.buffer_timeout_ms` (timeout de pcap_open_live).
- `capture.direction` (in/out/inout) si nftables o aislamiento lo requiere.
- Un campo simple `capture.pcap_flags` o similar para opciones avanzadas de libpcap.

Mantened el JSON lo más minimalista posible. Documentad claramente en `docs/` la divergencia entre variantes.

### [Q4] — Test e2e sin tráfico real

**Recomendación fuerte**: usar `pcap_open_dead()` + `pcap_inject()` (o `pcap_sendpacket()`) **desde el propio test**, sin necesidad de `tcpreplay` ni root adicional en `ctest`.

Ventajas:
- Totalmente determinista y reproducible en CI/dev VM.
- No depende de interfaces reales (loopback puede tener restricciones).
- Permite inyectar frames sintéticos precisos (incluyendo casos edge: fragmentados, malformed, etc.).
- Más rápido y portable que `tcpreplay` sobre `lo` o `eth1`.

`tcpreplay` sigue siendo válido para pruebas de estrés/end-to-end manuales con el dataset CIC-IDS-2017 completo. Combinad ambos: tests unit/integration con inyección sintética, y un test de estrés opcional con tcpreplay (marcado como `REQUIRES_ROOT` o similar).

### [Q5] — Atomicidad en `argus-network-isolate` (nftables)

**Adoptad el enfoque transaccional nativo de nftables**: `nft -f <file>` con un fichero completo de reglas.

Es el mecanismo diseñado exactamente para esto: carga todo en memoria, valida, y aplica atómicamente (swap completo o fallo). No hay ventana de reglas parciales.

Para rollback si el proceso muere a mitad:
- La transacción `nft -f` ya es atómica; si falla, no se aplica nada.
- Para mayor robustez: generar el fichero de reglas en un temporal (`/tmp/argus-isolate-XXXXXX`), validarlo primero con `nft -c -f`, luego aplicar.
- Persistencia/rollback a nivel superior: guardar el ruleset anterior (`nft list ruleset > backup`) antes de aplicar el de aislamiento. En caso de emergencia, el script de isolate puede restaurar desde backup o aplicar un "fail-closed" minimal (drop all + allow loopback/management).
- Si el proceso muere durante `nft -f`, el kernel ya ha aplicado o no nada → estado consistente.

Evitad aplicar reglas una a una. Usad `flush ruleset` con cuidado (o `delete table` selectivo) si no queréis afectar otras tablas.

### [Q6] — `DEBT-COMPILER-WARNINGS-CLEANUP-001`: Prioridad ODR

**Sí, ODR violations (`InternalNode`/`TrafficNode` y cualquier cosa con Protobuf en múltiples TUs) deben ser la sub-tarea #1 y bloqueante.**

Razones:
- Comportamiento indefinido en C++20 (puede manifestarse como corrupción silenciosa, crashes intermitentes, o "funciona en mi máquina").
- Protobuf es especialmente propenso cuando se generan archivos .pb.cc en múltiples contextos o se incluyen headers de forma inconsistente.
- Las otras warnings (signed/unsigned, EVP OpenSSL, etc.) son ruidosas pero suelen ser benignas en runtime.

Estrategia recomendada:
1. Aislar las definiciones de nodos en un solo header + una sola TU de implementación.
2. Usar forward declarations donde sea posible.
3. Verificar con `-fsanitize=address,undefined` + ASAN_OPTIONS=detect_odr_violation=2 (o equivalente en GCC/Clang).
4. Si hay especializaciones de templates o inline functions con Protobuf, moverlas al header o usar explicit instantiation.
5. Compilar con `-Wodr` (GCC) o equivalente para detección en LTO.

Una vez resueltas las ODR, el resto de warnings se limpian más fácilmente.

### [Q7] — Threading model y futuro seL4 (ARM64)

**No diseñéis todavía con seL4 en mente**. Es prematuro y añadiría complejidad innecesaria (y posible technical debt) en la fase pre-FEDER.

Análisis:
- **Reutilizable** de la arquitectura actual: la interfaz abstracta `CaptureBackend` (5 métodos puros) es excelente. El parsing ETH/IP/TCP/UDP → `NetworkSecurityEvent` proto, serialización, compresión LZ4 y `CryptoTransport` son independientes del mecanismo de captura y threading.
- **Reescritura completa necesaria**: todo lo relacionado con `std::thread`, memoria compartida, libpcap (no existe en seL4), ZMQ (necesitaría port o reemplazo por IPC nativo de seL4), y cualquier uso de capabilities de Linux.

Variant B monohilo es **compatible** con un port futuro a seL4 (dominio único con capabilities). La abstracción actual ayuda.

Recomendación: mantened la capa de abstracción limpia y el código de procesamiento de paquetes lo más puro posible (sin asunciones de POSIX pesadas). Cuando llegue el research track post-FEDER, se podrá reutilizar ~60-70% del pipeline de datos. Por ahora, priorizad ARM64 + AppArmor + libpcap.

---

**Resumen de recomendaciones para Day 139**:
- Proceder con `DEBT-VARIANT-B-CONFIG-001` (JSON minimal + hardcoding).
- Inmediatamente después o en paralelo (si recursos): sub-tarea ODR de warnings.
- Incorporar `snaplen` y `buffer_timeout` en el JSON de libpcap.
- Tests e2e: priorizar `pcap_open_dead + inject`.
- nftables: ir a lo transaccional (`nft -f`).

El Consejo aprueba continuar. EMECAS ejecutado. Esperamos el commit summary del Day 139.

— **Consejo de Sabios** (unánime)  
2026-05-01