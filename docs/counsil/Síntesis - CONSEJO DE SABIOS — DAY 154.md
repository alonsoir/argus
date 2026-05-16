# CONSEJO DE SABIOS — DAY 154 — Síntesis de Dictámenes
**Fecha:** 2026-05-16
**Modelos consultados:** Claude, ChatGPT, DeepSeek, Gemini, Grok, Kimi, Mistral, Qwen (8)
**Versión:** v0.8.0-adr045

---

## VOTOS POR PREGUNTA

### P1 — Señal de autonomía: polling vs. eventos ZMQ

| Modelo | Voto | Matiz |
|---|---|---|
| Claude | Polling DAY 155, ZMQ DAY 156 | Latencia 30s aceptable para escenario hospital |
| ChatGPT | ZMQ directo + polling reconciliador 60-120s | Event-driven es el modelo correcto; polling como self-healing |
| DeepSeek | ZMQ directo sin escalas | `TransitionCallback` ya definido en `crypto_autonomy.h` |
| Gemini | ZMQ directo DAY 155 | Arquitectura ya preparada para eventos reactivos |
| Grok | ZMQ directo + fallback polling ligero | Event-driven escala mejor; polling como safety net |
| Kimi | ZMQ `inproc://` directo, sin polling | `inproc://` es zero-copy entre threads del mismo proceso |
| Mistral | (ver respuesta completa) | Coincide con mayoría ZMQ |
| Qwen | Polling etcd como trampolín + migración documentada | Simplicidad operativa en infra crítica |

**CONSENSO (7/8): ZMQ pub/sub directo.**
Claude y Qwen son minoría (polling primero). El argumento decisivo: el `TransitionCallback` ya existe en `CryptoAutonomyStateMachine`; el cableado es mínimo y la latencia de 30s es inaceptable en entornos ransomware.

**Topic acordado:** `argus.crypto.autonomy`
**Payload mínimo:**
```json
{"state":"AUTONOMOUS","timestamp_utc_ns":...,"fingerprint":"..."}
```
**Transport:** `inproc://argus.autonomy` (mismo proceso) o `ipc:///run/argus/autonomy.sock` (procesos separados). NO TCP para señalización intra-nodo.
**Añadir:** polling reconciliador lento (60-120s) para detectar eventos perdidos, NO como mecanismo principal.

---

### P2 — Granularidad del default-deny

| Modelo | Voto |
|---|---|
| Claude | Selectivo: loopback + whitelist + ESTABLISHED |
| ChatGPT | Selectivo estricto: fail-closed externo, continuidad interna |
| DeepSeek | Total externo + ACCEPT interno explícito (loopback, gestión, ESTABLISHED) |
| Gemini | Selectivo: loopback + subredes clínicas + ESTABLISHED |
| Grok | Selectivo: total + excepciones explícitas mínimas (least privilege) |
| Kimi | Selectivo. **Advertencia explícita: regla actual puede matar pacientes** |
| Mistral | Selectivo estricto |
| Qwen | Selectivo: loopback + RFC1918 + ESTABLISHED + configurable por JSON |

**CONSENSO (8/8): fail-closed SELECTIVO. La regla actual `-I INPUT 1 -j DROP` es INCORRECTA.**

**Regla correcta (orden crítico):**
```bash
# 1. Loopback siempre abierto
iptables -I INPUT 1 -i lo -j ACCEPT --comment "argus-autonomy-lo"

# 2. Sesiones establecidas (no romper sesiones activas de médicos)
iptables -I INPUT 2 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT \
  --comment "argus-autonomy-established"

# 3. Subredes internas (configurables por JSON/Ansible)
iptables -I INPUT 3 -s 10.0.0.0/8 -j ACCEPT --comment "argus-autonomy-rfc1918-a"
iptables -I INPUT 4 -s 172.16.0.0/12 -j ACCEPT --comment "argus-autonomy-rfc1918-b"
iptables -I INPUT 5 -s 192.168.0.0/16 -j ACCEPT --comment "argus-autonomy-rfc1918-c"

# 4. DROP todo lo demás (tráfico nuevo externo)
iptables -I INPUT 6 -j DROP --comment "argus-autonomy-deny"
```

**Nota Kimi (crítica):** La regla DROP debe ser la ÚLTIMA de INPUT, no la primera. El orden de inserción importa.
**Configuración:** subnets whitelist deben venir de JSON de configuración, no hardcodeadas.

---

### P3 — Parámetros ZMQ críticos para benchmarks

| Modelo | Orden recomendado |
|---|---|
| Claude | HWM → Linger → Reconnect → IO threads |
| ChatGPT | HWM → Linger → Reconnect → Send/recv timeout |
| DeepSeek | HWM → Linger → RCVTIMEO/SNDTIMEO → Reconnect |
| Gemini | HWM → Linger → (timeouts secundarios) |
| Grok | HWM → Linger → Reconnect → Heartbeats |
| Kimi | HWM → Linger → TCP Keepalive → Reconnect → Timeouts |
| Mistral | HWM → Linger → Reconnect → Send/recv |
| Qwen | HWM → Reconnect IVL → Timeouts → Linger |

**CONSENSO (8/8): HWM primero, sin excepción.**

**Valores iniciales recomendados:**
- `ZMQ_SNDHWM` / `ZMQ_RCVHWM`: 1000–10000 mensajes (empezar conservador, escalar)
- `ZMQ_LINGER`: 0 (no bloquear en shutdown/fallo)
- `ZMQ_RECONNECT_IVL`: 100ms / `ZMQ_RECONNECT_IVL_MAX`: 5000-10000ms
- `ZMQ_SNDTIMEO` / `ZMQ_RCVTIMEO`: -1 (bloqueante) para benchmark de throughput puro

**Advertencia ChatGPT + Kimi:** El benchmark debe medir tres estados:
1. `steady-state` (throughput nominal)
2. `failure-state` (HWM alcanzado, drops)
3. `recovery-state` (reconexión post-fallo)

Un benchmark que solo mide steady-state es engañoso.

**Métrica clave adicional:** paquetes descartados por ZMQ (`ZMQ_SOCKET_MONITOR`). Throughput alto con 50% de drops silenciosos es una mentira.

---

### P4 — `DEBT-CAPTURE-BACKEND-ISP-001`: ¿ahora o después?

| Modelo | Voto |
|---|---|
| Claude | Después. Reactor ZMQ primero |
| ChatGPT | Después. DAY 156-157 |
| DeepSeek | Después. DAY 156 |
| Gemini | Después. Post-reactor |
| Grok | DAY 155 o 156, pero después de ZMQ |
| Kimi | Después de benchmark. Refactor se justifica con datos |
| Mistral | Después |
| Qwen | DAY 156 AM |

**CONSENSO (8/8): ISP después de integración ZMQ del reactor.**

Argumento Kimi: si `get_xdp_stats()` no introduce overhead en el path caliente (medible post-benchmark), el refactor es por limpieza, no por rendimiento. Mejor hacerlo con datos.

---

## PLAN DAY 155 — CONSENSO DEL CONSEJO

| Orden | Tarea | Tiempo est. | Bloquea FEDER |
|---|---|---|---|
| 1 | ZMQ pub/sub `argus.crypto.autonomy` (inproc o ipc) | 2-3h | **Sí** |
| 2 | Default-deny selectivo (whitelist loopback + ESTABLISHED + RFC1918) | 1.5h | **Sí** (hospital) |
| 3 | HWM + Linger en todos los sockets del pipeline | 1h | No (bloquea benchmark) |
| 4 | `DEBT-AUTONOMY-STATE-PERSISTENCE-001` (tmpfs) | 1h | No |
| 5 | `DEBT-CAPTURE-BACKEND-ISP-001` | — | No — postponer DAY 156 |

---

## OBSERVACIONES ADICIONALES DESTACADAS

**ChatGPT — sobre la transición arquitectónica:**
> *"El sistema ya no es solo un NDR. Empieza a comportarse como una plataforma resiliente distribuida. A partir de aquí, propagación de estado, reconciliación, persistencia, backpressure y recovery semantics son más importantes que añadir features nuevas."*

**Kimi — sobre el default-deny actual:**
> *"Tu `FirewallAutonomyReactor` actual usa `iptables -I INPUT 1 -j DROP`. Cámbialo antes de cualquier demo en un entorno real. Un `vagrant up` en un laptop no sufre. Un hospital sí."*

**DeepSeek — sobre la señal ZMQ:**
> *"El callback ya existe en `crypto_autonomy.h`; solo falta instanciarlo. DAY 155 = cerrar el circuito de autonomía edge."*

**ChatGPT — sobre `dry_run` que modifica `deny_active_`:**
> *"Muy buena decisión. Preserva semantic state, permite tests deterministas, desacopla side effects de logical state. Suele indicar madurez de diseño."*

---

## DEUDAS REGISTRADAS POST-CONSEJO

| Deuda | Estado | Prioridad | DAY |
|---|---|---|---|
| DEBT-AUTONOMY-ZMQ-EVENTS-001 | ⏳ P1 | Conectar reactor ZMQ real | 155 |
| DEBT-FIREWALL-DENY-SELECTIVE-001 | ⚠️ **NUEVA P0** | Regla actual rompe hospitales | 155 |
| DEBT-AUTONOMY-STATE-PERSISTENCE-001 | ⏳ P1 | Tmpfs | 155 |
| BACKLOG-ZMQ-TUNING-001 | ⏳ P1 | HWM primero | 155-156 |
| DEBT-CAPTURE-BACKEND-ISP-001 | ⏳ P2 | Post-benchmark | 156+ |
| BACKLOG-BENCHMARK-CAPACITY-001 | ⏳ P1 | Post-tuning | 157+ |

**NOTA:** `DEBT-FIREWALL-DENY-SELECTIVE-001` se eleva a P0 por unanimidad del Consejo. La regla actual es funcionalmente incorrecta para el escenario hospitalario y debe corregirse en DAY 155 antes de cualquier demo.

---

*Consejo de Sabios — 8 modelos — DAY 154 — 2026-05-16*
*Via Appia Quality: construir para que dure, no para que funcione en el laptop.*