Aquí el informe para el Consejo:

---

**CONSEJO DE SABIOS — DAY 137 — 2026-04-30**
**Rama:** `feature/variant-b-libpcap`
**Commit HEAD:** `26059f78`

---

**TRABAJO REALIZADO HOY**

EMECAS completo (dev + hardened) pasado al inicio de sesión. KNOWN-FAIL-001 (`test_config_parser` en dev VM) documentado en `docs/KNOWN-DEBTS-v0.6.md` — comportamiento correcto por diseño, no regresión.

ADR-029 Variant B iniciada. Decisión arquitectónica clave tomada durante la sesión: **dos binarios completamente separados, cero `#ifdef` en código existente** (KISS). Intentamos el enfoque `#ifdef` sobre el código existente (`ring_consumer`, `main.cpp`, etc.) y lo descartamos tras constatar que el acoplamiento eBPF en `RingBufferConsumer` es profundo y legítimo — no debe tocarse.

Arquitectura final implementada:
- `capture_backend.hpp` — interfaz abstracta `CaptureBackend`
- `ebpf_backend.hpp/cpp` — wrapper `EbpfLoader` (Variant A)
- `pcap_backend.hpp/cpp` — stub libpcap compilable (Variant B)
- `main_libpcap.cpp` — main limpio, solo `PcapBackend`
- `sniffer-libpcap` target en CMakeLists.txt + Makefile

Resultado: `make sniffer` ✅ y `make sniffer-libpcap` ✅ compilan independientemente. `sniffer-libpcap eth1` arranca, abre la interfaz con libpcap y termina limpio.

`DEBT-VARIANT-B-PCAP-IMPL-001` registrada: `pcap_loop → ZeroMQ → ml-detector` pendiente pre-FEDER.

`libpcap-dev` añadido al `Vagrantfile` dev. `libpcap0.8` runtime en `vagrant/hardened-arm64/Vagrantfile`.

**PREGUNTA AL CONSEJO**

La interfaz abstracta `CaptureBackend` define `attach_skb()`, `get_ringbuf_fd()` y filter map fds con defaults no-op para Variant B. ¿Es correcto mantener estos métodos en la interfaz base o deberían moverse a `EbpfBackend` únicamente y eliminarlos de la interfaz? El criterio actual es mantenerlos para que `main.cpp` (Variant A) pueda usar `CaptureBackend*` directamente sin downcast.

**MÉTRICAS DEL DÍA**
- Commits: 4
- Ficheros nuevos: 8 (6 código + 1 Vagrantfile + .gitignore)
- Líneas añadidas: ~500
- Tests rotos: 0
- Deudas nuevas: 1 (DEBT-VARIANT-B-PCAP-IMPL-001)
- Deudas cerradas: 0
- KNOWN-FAIL documentados: 1

---

Pega este informe a cada uno de los 7 modelos del Consejo y cuando tengas sus respuestas lo consolidamos en las actas. ¿Procedemos con el ritual de documentación mientras tanto?