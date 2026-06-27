## CONSEJO DE SABIOS — DAY 161 — Respuesta Claude

---

**Q1 — Wire Protocol Test: ¿añadir test con CryptoTransport completo?**

No es necesario duplicar. El invariante crítico es el formato binario (`[uint32_t LE][LZ4 datos]`), que es exactamente lo que `test_wire_protocol.cpp` verifica. Los tests existentes de `crypto-transport` ya cubren ChaCha20-Poly1305 de forma exhaustiva. Un test que combine ambas capas sería un test de integración, no de protocolo — y eso ya lo hace `TEST-E2E-SYNTHETIC-FULL`. La separación actual es correcta: cada test verifica una sola cosa.

**Q2 — Jenkinsfile.dev con `agent any`**

Correcto para la fase actual. `agent any` es honesto: dice "corre donde Jenkins esté", que ahora es el Mac del fundador. Mover a `agent { label 'argus-server' }` tiene sentido exactamente cuando el servidor FEDER esté físicamente disponible y Jenkins esté instalado en él. No antes. Forzarlo ahora sería infraestructura prematura.

**Q3 — Valores de config: ¿calculados en runtime o fijos por perfil?**

Fijos por perfil hasta tener benchmarks reales (BACKLOG-ZMQ-TUNING-001). El auto-tuning en runtime añade complejidad sin datos que lo justifiquen. El flujo correcto es: benchmark físico en BM-A/BM-B/BM-C/BM-D → valores medidos → codificados en `edge-low/medium/high`. El script selecciona el perfil, no lo calcula. Auto-tuning es post-FEDER.

**Q4 — test-e2e-live: tráfico orgánico vs sintético mínimo**

El test debe inyectar tráfico sintético mínimo garantizado — al menos 1 evento. La dependencia de tráfico orgánico en Vagrant sobre Mac es frágil por definición: no hay garantía de paquetes reales en una red NAT virtualizada. La solución limpia es: snapshot → inyectar N eventos sintéticos mínimos (sin parar el sniffer real) → 60s → check delta ≥ N. Esto da reproducibilidad sin sacrificar que el pipeline real también procese. El test sintético puro ya existe; el live debe ser una combinación.

**Q5 — Prioridad DAY 162**

**B primero, luego A.**

`DEBT-ARGUSPP-NTP-001` es prerequisito de todo lo demás en ADR-048. Sin NTP sincronizado como P0 boot gate, la correlación multi-engine con community_id no es fiable — los timestamps de Suricata, Zeek y aRGus pueden diferir segundos, haciendo el ground truth inválido para el paper. NTP es infraestructura crítica que no se puede parchear después.

`DEBT-ARGUSPP-SURICATA-001` (F2) va inmediatamente después de NTP — es el primer hito científico real para Andrés.

C y D son importantes pero no bloquean la hipótesis científica del paper.

---

Ahora envíaselo al resto del Consejo y recogemos feedback.