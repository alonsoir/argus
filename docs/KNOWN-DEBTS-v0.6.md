# aRGus NDR — KNOWN-DEBTS-v0.6.md
# Deudas técnicas documentadas
# Última actualización: 2026-05-01 (DAY 138)

---

## DEBT-COMPILER-WARNINGS-CLEANUP-001
**Severidad:** 🔴 Alta — ODR es P0 bloqueante (Consejo DAY 138: 8/8 unánime)
**Componente:** etcd-client, ml-detector, sniffer, rag-ingester
**Descripción:**
Sub-tareas en orden estricto de prioridad:
1. [P0 BLOQUEANTE] ODR violations: InternalNode vs TrafficNode en ml-detector
   y sniffer. Comportamiento indefinido en C++20. Diagnóstico: `nm -C | grep`.
   Fix: unificar flags CMake, añadir `-Werror=odr` si GCC >= 10.
2. [P1] Protobuf dual-copy en ml-detector — `.pb.cc` compilado dos veces.
3. [P2] signed/unsigned en zmq_handler.cpp, rag_logger.cpp, feature_extractor.cpp.
4. [P3] OpenSSL SHA256_Init/Update/Final deprecated → migrar a EVP_DigestInit_ex.
5. [P4] -Wreorder en ring_consumer.hpp, zmq_handler.hpp, dual_nic_manager.hpp.
6. [P5] -Wunused-parameter en ml_defender_features.cpp stubs.
7. Linker: libsodium.so.26 vs libsodium.so.23 conflict warning (cosmético).
   **Corrección:** Pre-FEDER. ODR sub-tarea P0 bloqueante para cualquier tag posterior.
   **Decisión:** Consejo DAY 138 — ODR primero, sin discusión.
   **Estimación:** 3 sesiones completas.

---

## DEBT-VARIANT-B-CONFIG-001
**Severidad:** 🔴 Alta — pre-demo FEDER
**Componente:** sniffer / main_libpcap.cpp, sniffer-libpcap.json (pendiente crear)
**Descripción:**
`sniffer-libpcap` tiene endpoint ZMQ, seed path e interface hardcodeados en el
binario. Necesita JSON de configuración propio simplificado.

Campos que DESAPARECEN del JSON (hardcodeados en binario con comentario explícito):
- `zmq_sender_threads` → 1 (monohilo por diseño de libpcap, no configurable)
- `io_thread_pools` → 1
- `zmq.socket_pools.push_sockets` → 1
- `threading.*` → eliminado
- `ring_buffer.*` → eliminado (no hay ring buffer eBPF)
- `numa_node`, `cpu_affinity` → no aplica
- `batch_size`, `flush_interval` → no aplica en callback síncrono
- `capture.snaplen` → 65535 fijo
- `capture.promiscuous` → 1 fijo (NDR siempre promiscuo)

Campos que SE PRESERVAN:
- `capture.interface`, `capture.filter.*`, `capture.timeout_ms`
- `output_socket.address/port`
- `crypto.*` / seed path, `logging.*`

Campos NUEVOS específicos de Variant B:
- `capture.buffer_size_mb` → buffer kernel libpcap (crítico en ARM64)
- `capture.sampling.mode` / `rate` → sampleo bajo alta carga ("none" por defecto)

Observabilidad: exponer `send_failures` como métrica. Alerta si drop_rate > 0.1%.

También pendiente:
- Test e2e con `pcap_open_dead()` + inject (CI, sin root)
- Test manual con `tcpreplay` sobre `lo` (fuera de ctest, REQUIRES_ROOT)
- Validación en hardened-arm64 VM
  **Corrección:** Pre-demo FEDER (1 agosto 2026)
  **Consejo DAY 138:** Ver actas Q2, Q3, Q4
  **Estimación:** 1 sesión

---

## DEBT-IRP-NFTABLES-001
**Severidad:** 🔴 Alta — post-merge, pre-demo FEDER
**Componente:** /usr/local/bin/argus-network-isolate (pendiente implementar)
**Descripción:**
ExecStartPre de argus-apt-integrity.service referencia argus-network-isolate
pero el script no está implementado. Aislamiento actual vía `ip link set down`
es insuficiente.

Protocolo aprobado por Consejo DAY 138 (8/8):
1. Snapshot ruleset previo: `nft list ruleset > /tmp/argus-backup-$$.nft`
2. Generar fichero de reglas de aislamiento
3. Validar: `nft -c -f /tmp/argus-isolate-$$.nft`
4. Aplicar atómico: `nft -f /tmp/argus-isolate-$$.nft`
5. Timer rollback automático 300s (si admin no confirma, restaurar)
6. Fallback emergencia si `nft -f` falla: `ip link set eth0 down`
7. Firma Ed25519 del fichero de reglas (consistente con ADR-025, pendiente decisión)

iptables rechazado — obsoleto en Debian 12 Bookworm. nftables es el backend
nativo. No mezclar ambos.
**Corrección:** Primera iteración post-merge, antes de demo FEDER
**ADR relacionado:** ADR-042 IRP enmienda E1
**Consejo DAY 138:** Ver actas Q5
**Estimación:** 2 sesiones (refactor + tests + AppArmor)

---

## DEBT-IRP-QUEUE-PROCESSOR-001
**Severidad:** 🔴 Alta — post-merge
**Componente:** ADR-042 IRP
**Descripción:** La cola irp-queue no tiene límites de tamaño ni procesador
systemd dedicado. Sin límites puede crecer sin control bajo ataque sostenido.
Requiere unidad systemd irp-queue-processor con límites explícitos
(enmienda E3 ADR-042).
**Corrección:** Primera iteración post-merge

---

## DEBT-PCAP-CALLBACK-LIFETIME-DOC-001
**Severidad:** 🟢 Baja — documentación
**Componente:** sniffer/include/pcap_backend.hpp, sniffer/src/userspace/pcap_backend.cpp
**Descripción:**
Añadir comentario explícito de contrato de lifetime de `PcapCallbackData`:
- Válido durante toda la sesión de captura
- No destruir PcapBackend durante pcap_dispatch() activo
- Señalización asíncrona (SIGALRM + shutdown concurrente) no soportada
- Si se añade threading posterior → requiere weak_ptr refactoring
  **Corrección:** Próxima sesión, trivial
  **Consejo DAY 138:** Q1 — ChatGPT, Kimi

---

## DEBT-SEEDS-SECURE-TRANSFER-001
**Severidad:** 🔴 Alta — mitigado en Vagrant, inaceptable en producción real
**Componente:** scripts/prod-deploy-seeds.sh
**Descripción:** Seeds pasan por Mac host vía /vagrant durante el despliegue.
Actualmente solo válido para entorno Vagrant dev/test. En producción real
los seeds deben generarse directamente en el nodo hardened sin salir del HSM
o del canal seguro.
**Corrección:** post-FEDER (protocolo de distribución out-of-band)
**Decisión:** D2 Consejo DAY 134

---

## DEBT-SEEDS-LOCAL-GEN-001
**Severidad:** 🟡 Media
**Componente:** scripts/prod-deploy-seeds.sh
**Descripción:** Los seeds se generan en la dev VM y se extraen al Mac host
antes de instalarse en hardened. En producción real deben generarse
localmente en cada nodo sin atravesar ningún host intermediario.
**Corrección:** post-FEDER

---

## DEBT-SEEDS-BACKUP-001
**Severidad:** 🟡 Media
**Componente:** /etc/ml-defender/*/seed.bin
**Descripción:** No existe protocolo de backup/recovery para seeds. Si un nodo
falla catastróficamente los seeds se pierden y el pipeline no puede arrancar.
Requiere procedimiento de regeneración documentado.
**Corrección:** post-FEDER

---

## KNOWN-TEST-FAILURES (expected — no action required)

### KNOWN-FAIL-001: test_config_parser (rag-ingester, dev VM)
**Severidad:** ℹ️ Informativo — comportamiento correcto por diseño
**Componente:** rag-ingester / safe_path guard
**Descripción:** El test falla en dev VM porque carga el config desde
`/vagrant/rag-ingester/config/rag-ingester.json`, path fuera del prefix
permitido `/etc/ml-defender/`. El safe_path guard emite SECURITY VIOLATION
y aborta — exactamente como debe comportarse.
En hardened VM el config vive en `/etc/ml-defender/` y el test pasaría.
**Acción:** Ninguna. No es regresión. No confundir con un bug.
**Referencia:** ADR-028, DEBT-SAFE-PATH-TEST-PRODUCTION-001
**Descubierto:** DAY 137 — 2026-04-30

---

## DEUDAS CERRADAS

### ✅ DEBT-CAPTURE-BACKEND-ISP-001 — CERRADA DAY 138
**Commit:** 1a7f723a
**Descripción:** CaptureBackend refactorizada a interfaz mínima de 5 métodos
puros. Los 7 métodos eBPF-específicos movidos a EbpfBackend como métodos
públicos no-virtuales. Veredicto Consejo DAY 137: 5-2-1.

### ✅ DEBT-VARIANT-B-PCAP-IMPL-001 — CERRADA DAY 138
**Commits:** 22df0099, da1badf7
**Descripción:** Pipeline completo pcap_dispatch → NetworkSecurityEvent proto →
LZ4 → ChaCha20-Poly1305 → ZMQ. Wire format idéntico a Variant A.
Suite de 8 tests (unit/integ/stress/regression) — 8/8 PASSED.

---

## Notas
- Deudas 🔴 Alta post-merge se abordan antes de demo FEDER (1 agosto 2026)
- Deudas 🟡 Media se abordan antes de deadline FEDER (22 septiembre 2026)
- Deudas 🟢 Baja se abordan oportunísticamente
- Ver también: BACKLOG.md sección DEBT para deudas anteriores a v0.6
- Keypair activo: b5b6cbdf67dad75cdd7e3169d837d1d6d4c938b720e34331f8a73f478ee85daa