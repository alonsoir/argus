## 📋 PUBLICACIÓN CONSEJO DE SABIOS — DAY 138

---

**aRGus NDR | DAY 138 | 2026-05-01**
**Branch:** `feature/variant-b-libpcap` @ `da1badf7`
**Quorum:** 8 modelos (Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral)

---

### ✅ COMPLETADO DAY 138

**DEBT-CAPTURE-BACKEND-ISP-001 — CERRADA** `1a7f723a`

`CaptureBackend` refactorizada a interfaz mínima de 5 métodos puros:
```cpp
virtual bool open(const std::string&, PacketCallback, void*) = 0;
virtual int  poll(int timeout_ms) = 0;
virtual void close() = 0;
virtual int  get_fd() const = 0;
virtual uint64_t get_packet_count() = 0;
```

Los 7 métodos eBPF-específicos (`attach_skb`, `detach_skb`, `get_ringbuf_fd`, 4× filter map fds) eliminados de la base y movidos a `EbpfBackend` como métodos públicos no-virtuales. Veredicto Consejo DAY 137: 5-2-1. Test de cierre: ambos binarios compilan sin nuevos warnings.

---

**DEBT-VARIANT-B-PCAP-IMPL-001 — CERRADA** `22df0099` + `da1badf7`

Pipeline completo `sniffer-libpcap`:

```
pcap_dispatch(64 pkts) → pcap_packet_handler()
→ ETH/IP/TCP/UDP parse → NetworkSecurityEvent proto
→ SerializeToString()
→ [uint32_t orig_size LE] + LZ4_compress_default()
→ CryptoTransport::encrypt() [HKDF-SHA256 + ChaCha20-Poly1305]
→ zmq::socket_t::send(dontwait) → tcp://127.0.0.1:5571
```

Wire format **idéntico** a Variant A (`ring_consumer.cpp` DAY 98). Mismo `SeedClient("/etc/ml-defender/sniffer/sniffer.json")` + `CTX_SNIFFER_TO_ML`. Mismo endpoint ZMQ. ml-detector recibe ambos formatos sin modificación.

**Mecanismo de callback:** `PcapCallbackData{cb, ctx}` pasado como `u_char* user` a `pcap_dispatch` — evita acceso a miembros privados sin `friend`.

**Suite de tests — 8/8 PASSED en `make test-all`:**

| Test | Tipo | Resultado |
|---|---|---|
| `test_pcap_backend_lifecycle` | Unit | ✅ |
| `test_pcap_backend_poll_null` | Unit | ✅ |
| `test_pcap_backend_callback` | Unit | ✅ |
| `test_pcap_backend_error` | Unit | ✅ |
| `test_pcap_proto_parse_tcp` | Integration | ✅ |
| `test_pcap_proto_parse_udp` | Integration | ✅ |
| `test_pcap_backend_stress` | Stress | ✅ |
| `test_pcap_backend_regression` | Regression | ✅ |

---

**DEBT-VARIANT-B-CONFIG-001 — REGISTRADA** (no iniciada)

Decisión de diseño DAY 138: `sniffer-libpcap` tendrá su propio JSON de configuración simplificado. Los campos de multihilo (`zmq_sender_threads`, `io_thread_pools`, `ring_buffer_*`) **desaparecen del JSON** y se hardcodean en el binario con comentario explícito. Variant B es monohilo por diseño de `libpcap` — no es configurable, no es negociable. Se documentará en código y documentación.

---

### 🔴 DEUDAS P0 PENDIENTES (rama `feature/variant-b-libpcap`)

| Deuda | Descripción | Estimación |
|---|---|---|
| `DEBT-VARIANT-B-CONFIG-001` | JSON propio, campos multihilo hardcodeados, test e2e | 1 sesión |
| `DEBT-COMPILER-WARNINGS-CLEANUP-001` | ODR, Protobuf dual-copy, signed/unsigned, OpenSSL EVP | 3 sesiones |
| `DEBT-IRP-NFTABLES-001` | `argus-network-isolate` + refactor IPTables→nftables + AppArmor | 2 sesiones |

---

### ❓ PREGUNTAS AL CONSEJO

**[Q1] — Arquitectura `PcapCallbackData` vs alternativas**

El callback estático de `pcap_dispatch` recibe `u_char* user`. La solución adoptada es un struct plano `PcapCallbackData{PacketCallback cb, void* ctx}` pasado como `user`. Alternativas rechazadas: `friend` (conflicto de linkage), miembros públicos (rompe encapsulación).

¿Veis algún riesgo de lifetime en `PcapCallbackData`? El struct es miembro de `PcapBackend` — su vida útil está ligada a la instancia. `pcap_dispatch` es síncrono. ¿Es suficiente esta garantía o debéis proponer un mecanismo más robusto?

**[Q2] — Wire format: `dontwait` vs bloqueante**

`main_libpcap.cpp` usa `zmq::send_flags::dontwait`. Si el socket ZMQ está lleno (HWM=1000), el paquete se descarta silenciosamente con `send_failures++`. Variant A tiene el mismo comportamiento. Para Variant B monohilo, ¿es aceptable esta política de descarte, o debéis proponer backpressure (sleep + retry) dado que no hay threads separados para absorber picos?

**[Q3] — `sniffer-libpcap.json`: campos a preservar vs eliminar**

Los campos de multihilo que desaparecen del JSON: `zmq_sender_threads`, `io_thread_pools`, `zmq.socket_pools.push_sockets`, `threading.*`, `ring_buffer.*`. Los campos que se preservan: `capture.interface`, `output_socket.address/port`, `capture.filter.*`.

¿Hay campos adicionales del `sniffer.json` de Variant A que debáis considerar irrelevantes para Variant B y que deberían también desaparecer o hardcodearse? ¿O hay campos de Variant A ausentes que Variant B necesita y que no hemos identificado?

**[Q4] — Test e2e: estrategia para dev VM sin tráfico real**

`DEBT-VARIANT-B-CONFIG-001` incluye test end-to-end. Sin cliente VM activo, la única fuente de tráfico en dev es loopback + `tcpreplay` contra un pcap de CIC-IDS-2017. ¿Proponéis usar `tcpreplay` sobre `lo` o `eth1`, o preferís un enfoque diferente — por ejemplo, `pcap_open_dead()` + `pcap_inject()` para inyectar frames sintéticos desde el propio test sin necesidad de root en ctest?

**[Q5] — `DEBT-IRP-NFTABLES-001`: atomicidad de `argus-network-isolate`**

El aislamiento de emergencia debe ser atómico: o se aplican todas las reglas nftables o ninguna (rollback). nftables soporta transacciones via `nft -f` con un fichero de reglas completo — aplica todo o falla todo. ¿Adoptáis este enfoque transaccional, o proponéis un mecanismo diferente? ¿Cómo gestionáis el rollback si el proceso muere a mitad de la aplicación de reglas?

**[Q6] — `DEBT-COMPILER-WARNINGS-CLEANUP-001`: prioridad ODR**

Las ODR violations (`InternalNode`/`TrafficNode`) son las más peligrosas — comportamiento indefinido en C++20, puede manifestarse como corrupción silenciosa en producción. Las otras warnings son ruidosas pero inofensivas en runtime. ¿Confirmáis que ODR debe ser la primera sub-tarea, bloqueante para el resto? ¿Alguno de vosotros tiene experiencia con ODR en sistemas con protobuf + múltiples translation units que pueda aportar contexto específico?

**[Q7] — Threading model: ARM64 + seL4 a largo plazo**

Variant B es monohilo. ARM64 + AppArmor es el objetivo pre-FEDER (monohilo). ARM64 + seL4 es research track post-FEDER. En seL4 no existe `std::thread` ni memoria compartida — el modelo es capabilities + IPC entre dominios. La pregunta no es si Variant B puede ser multihilo en seL4 (no puede, el modelo es incompatible), sino: ¿qué partes de la arquitectura actual de `PcapBackend` + `CaptureBackend` son reutilizables en un port seL4, y cuáles requieren reescritura completa? ¿Vale la pena diseñar ya con seL4 en mente, o es prematuro y añade complejidad innecesaria ahora?

---

### 🔮 PLAN DAY 139

1. Recoger feedback del Consejo sobre Q1-Q7
2. Según feedback: iniciar `DEBT-VARIANT-B-CONFIG-001` (JSON propio + hardcoding)
3. O: iniciar `DEBT-COMPILER-WARNINGS-CLEANUP-001` sub-tarea ODR (si el Consejo confirma prioridad)
4. EMECAS obligatorio al inicio

---
