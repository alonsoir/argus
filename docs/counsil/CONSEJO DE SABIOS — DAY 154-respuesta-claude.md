## CONSEJO DE SABIOS — DAY 154 — Respuesta Claude (Anthropic)

---

### P1 — Señal de autonomía: polling vs. eventos ZMQ

**Recomendación: Opción A (polling) primero, como trampolín.**

El reactor existe y funciona — lo que falta es la señal. Polling en el health-check loop (30s) es suficiente para DAY 155: el escenario real es un hospital que pierde conectividad con Vault durante minutos u horas, no milisegundos. La latencia de 30s es aceptable y el coste de implementación es mínimo — una llamada a `etcd_client->get()` en `perform_health_checks()`.

ZMQ directo es la arquitectura correcta a largo plazo pero introduce un nuevo canal pub/sub que necesita gestión de reconexión, serialización del estado, y tests de integración end-to-end. Eso es DAY 156+, después de tener el reactor funcionando con señal real.

**Voto: Polling DAY 155, ZMQ DAY 156.**

---

### P2 — Granularidad del default-deny

**Recomendación: fail-closed selectivo, no total.**

El default-deny total (`-I INPUT 1 -j DROP`) en un hospital en autonomía extendida rompe cosas legítimas: monitorización interna, acceso SSH de administración, tráfico entre subredes propias. Un hospital sin conectividad a Vault no es un hospital bajo ataque — es un hospital con un problema de infraestructura.

La regla debería preservar explícitamente:
- `127.0.0.1` (loopback)
- Subredes internas configuradas (`whitelist_cidrs` en config)
- Puerto 22 SSH desde IPs de administración
- Tráfico ya establecido (`-m conntrack --ctstate ESTABLISHED,RELATED`)

Solo bloquear tráfico **nuevo** desde **fuera** de la red de confianza. Esto es lo que hace `argus-network-isolate` en ADR-042 — el mismo modelo debería aplicar aquí.

**Voto: default-deny selectivo con whitelist configurable.**

---

### P3 — Parámetros ZMQ críticos para benchmarks

**Orden recomendado: HWM primero, luego linger, luego reconnect.**

El `HWM` (High Water Mark) es el parámetro que más impacta el comportamiento bajo carga: determina cuándo el publisher empieza a descartar mensajes. Con HWM arbitrario los benchmarks de capacidad son no reproducibles — un HWM de 1000 vs 100000 cambia completamente el perfil de pérdida de paquetes.

Secuencia sugerida para `BACKLOG-ZMQ-TUNING-001`:
1. **HWM** (`ZMQ_SNDHWM` / `ZMQ_RCVHWM`): medir throughput máximo antes de pérdida
2. **Linger** (`ZMQ_LINGER`): cuánto espera al cerrar — afecta al shutdown limpio
3. **Reconnect interval** (`ZMQ_RECONNECT_IVL`): relevante para AUTONOMOUS (Vault caído = posible inestabilidad de red)
4. **IO threads** (`ZMQ_IO_THREADS`): últimos, solo si los anteriores no saturan

**Voto: HWM primero, es el bloqueante real de los benchmarks.**

---

### P4 — `DEBT-CAPTURE-BACKEND-ISP-001` vs. integración ZMQ del reactor

**Recomendación: integración ZMQ del reactor primero.**

`DEBT-CAPTURE-BACKEND-ISP-001` es deuda arquitectural importante pero no bloquea nada funcional hoy — Variant A y Variant B compilan y pasan tests. El Consejo DAY 145 lo registró como P2 por esta razón.

La integración ZMQ del reactor sí bloquea algo funcional: sin señal real, `FirewallAutonomyReactor` es código muerto. Un componente de seguridad sin activación no aporta protección real.

Secuencia correcta: DAY 155 reactor+ZMQ → DAY 156 ZMQ tuning → DAY 157+ ISP.

**Voto: ISP puede esperar. Reactor con señal real no puede.**

---

*Claude (Anthropic) — Consejo de Sabios DAY 154 — 2026-05-16*