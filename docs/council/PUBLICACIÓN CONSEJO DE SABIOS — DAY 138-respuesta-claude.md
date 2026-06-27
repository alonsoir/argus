## 📋 PUBLICACIÓN CONSEJO DE SABIOS — DAY 138

**Mis respuestas previas a que lleves esto al Consejo:**

**Q1:** El lifetime es seguro — `PcapCallbackData` es miembro de `PcapBackend`, `pcap_dispatch` es síncrono, no hay callbacks diferidos. No veo riesgo real.

**Q2:** `dontwait` con descarte es correcto para NDR — mejor perder paquetes que bloquear el loop de captura. En monohilo un bloqueo ZMQ congela toda la captura.

**Q3:** Mi estimación: también hardcodear `capture.snaplen` (siempre 65535 en libpcap), `capture.promisc` (siempre 1). El campo `capture.timeout_ms` sí tiene sentido configurarlo — controla el `poll()`.

**Q4:** `pcap_open_dead()` + frames sintéticos es la opción superior — no requiere root, reproducible en CI, determinista. `tcpreplay` requiere root y tráfico de red real.

**Q5:** El enfoque transaccional `nft -f` es el correcto. El rollback ante fallo parcial debe ser un fichero de reglas de "estado limpio" pre-generado y firmado, aplicado en el signal handler de SIGTERM/error.

**Q6:** Confirmo — ODR primero, es el único warning con riesgo de corrupción en runtime.

**Q7:** `CaptureBackend` como interfaz abstracta mínima (5 métodos) es el núcleo reutilizable. `PcapBackend` necesita reescritura completa en seL4. No diseñar para seL4 ahora — YAGNI hasta que el equipo especializado esté disponible.