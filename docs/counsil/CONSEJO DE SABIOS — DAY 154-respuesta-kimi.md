**Consejo de Sabios — Dictamen DAY 154**

Compañero, la descomposición de `VaultClient` en ADR-045 es un trabajo de arquitectura limpia. Las interfaces inyectables (`ICryptoDeriver`, `IEtcdRegistrar`) y el `FirewallAutonomyReactor` testable sin root demuestran que el proyecto ha cruzado a madurez de ingeniería. EMECAS verde con `hardened-full` y `check-prod-all` es la confirmación operativa.

Vamos a tus cuatro preguntas.

---

## P1 — Polling vs. ZMQ pub/sub para señal de autonomía

**ZMQ pub/sub directamente. No hagas polling como trampolín.**

Un loop de polling cada 30s introduce una latencia de detección de hasta 30s. En el escenario hospital-corte-WAN-ransomware, esos 30s son el tiempo que el adversario necesita para pivotar lateralmente. El reactor ya existe; lo que falta es el cableado.

**Implementación concreta:**

```cpp
// CryptoAutonomyStateMachine publica
zmq::socket_t autonomy_pub(zmq_ctx, zmq::socket_type::pub);
autonomy_pub.bind("inproc://argus.autonomy");

// FirewallAutonomyReactor se suscribe
zmq::socket_t autonomy_sub(zmq_ctx, zmq::socket_type::sub);
autonomy_sub.connect("inproc://argus.autonomy");
autonomy_sub.set(zmq::sockopt::subscribe, "AUTONOMOUS");
autonomy_sub.set(zmq::sockopt::subscribe, "DEGRADED");
autonomy_sub.set(zmq::sockopt::subscribe, "NORMAL");
```

**Por qué `inproc://`:** Es zero-copy entre threads del mismo proceso. Si firewall y state machine corren en procesos separados, usa `ipc:///run/argus/autonomy.sock`. No uses TCP para señalización intra-nodo; es overhead innecesario y falla si la interfaz loopback tiene problemas.

**Mensaje:** JSON mínimo, 3 campos.
```json
{"state":"AUTONOMOUS","timestamp_utc_ns":1715842800000000000,"fingerprint":"007908..."}
```

**Tiempo estimado:** 2-3h. Menos que implementar polling robusto con backoff y jitter.

---

## P2 — Granularidad del default-deny: ¿total o selectivo?

**Selectivo. El default-deny total en un hospital puede matar pacientes.**

`iptables -I INPUT 1 -j DROP` es una trampa. Bloquea:
- Loopback (127.0.0.1) → rompe IPC interno, health checks, métricas.
- Conexiones establecidas (ESTABLISHED, RELATED) → rompe sesiones activas de médicos en el HIS.
- Subred interna del hospital (imaging, monitorización, HL7, DICOM) → para el quirofano.
- SSH de management (si no hay BMC/IPMI alternativo) → deja al sysadmin fuera.

**Regla correcta para modo AUTONOMOUS:**

```bash
# 1. Loopback siempre abierto
iptables -I INPUT 1 -i lo -j ACCEPT -m comment --comment "argus-autonomy-lo"

# 2. Conexiones establecidas (no romper sesiones activas)
iptables -I INPUT 2 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT \
  -m comment --comment "argus-autonomy-established"

# 3. Subredes internas whitelist (configurables por Ansible/Jinja2)
iptables -I INPUT 3 -s 192.168.10.0/24 -j ACCEPT \
  -m comment --comment "argus-autonomy-internal"

# 4. Puertos de management críticos (SSH por interfaz de management, no de captura)
#    Esto debe ser configurable; en algunos hospitales no hay BMC.
iptables -I INPUT 4 -i mgmt0 -p tcp --dport 22 -j ACCEPT \
  -m comment --comment "argus-autonomy-mgmt"

# 5. FAIL-CLOSED: todo lo demás nuevo
iptables -I INPUT 5 -m comment --comment "argus-autonomy-deny" -j DROP
```

**Nota crítica:** La regla 5 usa `-I INPUT 5`, no `-I INPUT 1`. El orden importa. `argus-autonomy-deny` debe ser la **última** regla de INPUT, no la primera.

**Configuración:** Las subnets whitelist deben venir de `ansible/group_vars/all.yml`, no hardcodeadas. Un hospital en Badajoz no tiene la misma LAN que uno en Cáceres.

**Postura:** Es "fail-closed para tráfico nuevo no clasificado", no "fail-closed total". La diferencia es la que hay entre un hospital que sigue operando y un hospital que para.

---

## P3 — BACKLOG-ZMQ-TUNING-001: ¿Qué parámetros primero?

**Orden de tuning para benchmarks de capacidad:**

| Prioridad | Parámetro | Qué controla | Valor inicial sugerido | Por qué primero |
|-----------|-----------|------------|------------------------|-----------------|
| **1** | `ZMQ_SNDHWM` / `ZMQ_RCVHWM` | Backpressure vs. drop silencioso | 10000 (mensajes) | Si HWM=0 (default), ZMQ bloquea el sender cuando el receiver lento. En un IDS, bloquear el sniffer es inaceptable. Si HWM=infinito, OOM. Este es el parámetro que determina si tu benchmark mide throughput real o throughput antes del colapso. |
| **2** | `ZMQ_LINGER` | Tiempo de espera en `zmq_close()` | 0 (no esperar) | Si un componente muere y linger>0, el sender bloquea en `send()` hasta timeout. En autonomía o fallo, queremos drop inmediato, no bloqueo. |
| **3** | `ZMQ_TCP_KEEPALIVE` + `IDLE` + `INTVL` + `CNT` | Detección de peer muerto | IDLE=30, INTVL=5, CNT=3 | Sin keepalive, ZMQ no detecta que `ml-detector` ha muerto hasta que el TCP stack del SO lo note (puede ser minutos). El sniffer sigue enviando a un socket zombie. |
| **4** | `ZMQ_RECONNECT_IVL` / `RECONNECT_IVL_MAX` | Frecuencia de reconexión | IVL=100ms, MAX=10s | Si Vault o etcd reinician, los sockets ZMQ reconectan agresivamente. Sin cap, el reconnect storm satura CPU y red. |
| **5** | `ZMQ_SNDTIMEO` / `ZMQ_RCVTIMEO` | Timeout de operaciones bloqueantes | SND=100ms, RCV=1000ms | Evita que un `send()` o `recv()` bloquee indefinidamente si el peer está lento. |

**Prerequisito para `BACKLOG-BENCHMARK-CAPACITY-001`:** Solo necesitas HWM y LINGER para el benchmark. Los demás son para robustez operativa, no para throughput puro.

**Métrica clave del benchmark:** No solo Mbps. Mide **paquetes droppeados por ZMQ** (`ZMQ_SOCKET_MONITOR` o contadores internos). Un benchmark que muestra 10 Gbps pero con 50% de drops silenciosos es una mentira.

---

## P4 — DEBT-CAPTURE-BACKEND-ISP-001: ¿Ahora o después?

**Después. Consolidar ZMQ reactor primero.**

El `get_xdp_stats()` en `CaptureBackend` es una violación ISP, pero:
1. No está en el path caliente de captura (no se llama por paquete; se llama periódicamente para telemetría).
2. No afecta el benchmark de capacidad si los benchmarks miden `pcap_dispatch()` o `xdp_rx()`, no `get_stats()`.
3. Es P2 por una razón: no bloquea FEDER.

**Riesgo de hacerlo ahora:** Refactorizar jerarquías de herencia en `sniffer/` mientras estás cableando ZMQ en `firewall/` es context-switching costoso. Además, cualquier cambio en `CaptureBackend` requiere re-testear eBPF y libpcap en ambas variantes, lo que consume un día completo.

**Momento correcto:** Después de que `BACKLOG-BENCHMARK-CAPACITY-001` esté completo. En ese punto, sabrás si `get_xdp_stats()` introduce overhead de vtable en el path caliente (improbable, pero medible). Si no hay overhead, el refactor es por limpieza, no por rendimiento. Si hay overhead, el refactor se justifica con datos.

---

## Plan de acción propuesto para DAY 155

| Orden | Tarea | Tiempo | Bloquea FEDER? |
|-------|-------|--------|----------------|
| 1 | **ZMQ pub/sub intra-nodo** (`inproc://argus.autonomy`) | 2-3h | **Sí** — sin esto el reactor no se activa |
| 2 | **Granularidad selectiva del default-deny** (whitelist loopback + established + internal subnets) | 1.5h | **Sí** — sin esto el hospital se desconecta en autonomía |
| 3 | **ZMQ HWM + LINGER** en todos los sockets del pipeline | 1h | No — pero bloquea benchmark |
| 4 | `DEBT-AUTONOMY-STATE-PERSISTENCE-001` (tmpfs entre reinicios de proceso) | 1h | No |
| 5 | `DEBT-CAPTURE-BACKEND-ISP-001` | — | No — posponer a post-benchmark |

**Total DAY 155:** ~6h de trabajo técnico. Deja ISP para DAY 158+.

---

## Nota final sobre el default-deny

Tu `FirewallAutonomyReactor` actual usa `iptables -I INPUT 1 -j DROP`. **Cámbialo antes de cualquier demo en un entorno real.** Un `vagrant up` en un laptop no sufre. Un hospital sí. El Consejo anterior (DAY 149) aprobó la autonomía extendida para proteger al hospital; sería irónico que la implementación de esa protección desconecte el quirofano.

*El Consejo ha hablado. Que el pub/sub sea inproc, que el deny sea selectivo, y que el benchmark no mida mentiras.* 🛡️