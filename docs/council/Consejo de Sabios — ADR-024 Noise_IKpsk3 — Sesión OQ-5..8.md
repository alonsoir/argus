# Consejo de Sabios — ADR-024 Noise_IKpsk3 — Sesión OQ-5..8
**Fecha:** 2026-04-12 (DAY 115)
**Árbitro:** Alonso Isidoro Román
**Contexto:** ADR-024 aprobado DAY 104. arXiv publicado. PHASE 3 activa.
Implementación de ADR-024 bloqueada hasta resolver estas 4 preguntas.

---

## Sistema: aRGus NDR (ML Defender)

6 componentes C++20 en pipeline: sniffer → ml-detector → firewall-acl-agent
+ rag-ingester + rag-security + etcd-server.

Entorno objetivo: hospitales, escuelas, municipios.
Hardware: commodity ARMv8 (~150–200 USD), sin TPM, sin PKI.
Crypto actual: libsodium 1.0.19, ChaCha20-Poly1305, HKDF-SHA256.
ADR-024 propone: Noise_IKpsk3 (noise-c vendored) + X25519 estáticos
por componente + PSK derivado de seed_family.

---

## OQ-5 — Revocación de clave estática X25519

**Escenario:** Un nodo físico (Raspberry Pi en sala de servidores de hospital)
es robado. Ese nodo tiene su keypair X25519 estático en disco.
Sin PKI ni CRL, el nodo robado puede participar en futuros handshakes
Noise_IKpsk3 indefinidamente, siempre que conozca el PSK (seed_family).

**Candidatos identificados:**
A) Fingerprint Blocklist distribuida vía etcd (clave pública → bloqueada).
Todos los componentes consultan la lista antes de aceptar un handshake.
B) Emergency re-provision: ejecutar provision.sh en todos los nodos restantes
con nuevos keypairs X25519 + rotar seed_family.
C) Combinación: Blocklist para respuesta inmediata + re-provision en ventana
de mantenimiento.

**Preguntas específicas:**
1. ¿Es la Fingerprint Blocklist vía etcd suficiente como mecanismo primario
   de revocación, dado que etcd es un componente del pipeline que puede estar
   comprometido si el nodo robado conoce seed_family?
2. ¿Qué garantías ofrece cada candidato si seed_family TAMBIÉN fue exfiltrada
   junto con el nodo robado?
3. ¿Existe un mecanismo más simple que no introduzca dependencia adicional
   en etcd para la ruta crítica de handshake?

---

## OQ-6 — Continuidad de sesión durante rotación de clave

**Escenario:** Un componente es re-provisionado (nuevo keypair X25519).
Sus 5 peers tienen el public key antiguo en deployment.yml.
El nuevo handshake falla: los peers rechazan la nueva clave estática.

**Restricción operacional:** Hospitales no pueden tolerar downtime del pipeline.
Re-provisionar los 6 componentes simultáneamente es inaceptable.

**Candidatos identificados:**
A) Dual-key acceptance window: cada componente acepta temporalmente
tanto la clave antigua como la nueva durante un período de gracia (T).
Al cabo de T, la clave antigua se invalida.
B) Versioned deployment.yml: etcd distribuye una nueva versión de
deployment.yml con el nuevo public key. Componentes la adoptan
en el siguiente ciclo de heartbeat (sin restart).
C) Coordinator-driven rotation: etcd-server actúa como coordinador,
notifica a todos los peers el cambio de clave, espera ACKs antes
de activar la nueva clave.

**Preguntas específicas:**
1. ¿Es la ventana de gracia dual-key (opción A) segura en el contexto
   de Noise_IKpsk3, o introduce vectores de downgrade?
2. ¿Puede deployment.yml actualizarse hot (sin restart de componentes)
   de forma segura dado que los static keys están en pre-message?
3. ¿Cuál es la secuencia mínima de pasos para rotar un keypair con
   cero downtime en un pipeline de 6 componentes?

---

## OQ-7 — Replay protection en primer mensaje del handshake

**Estado actual en ADR-024:** El primer mensaje (→ e, es, s, ss) no lleva
nonce de frescura. Es técnicamente replayable. Decisión provisional:
aceptado para v1 dado que sin PSK (seed_family) el replay no puede
completar el handshake.

**Mitigación opcional identificada:** Incluir timestamp o challenge nonce
en el payload del primer mensaje (Noise permite payload en handshake messages).

**Preguntas específicas:**
1. ¿Es suficiente el binding PSK como protección anti-replay para el
   escenario de amenaza de aRGus (LAN hospitalaria, no Internet)?
2. Si se añade timestamp en el payload del primer mensaje, ¿qué ventana
   de aceptación es razonable (±30s, ±5m)? ¿Requiere NTP sincronizado?
3. ¿Existe algún escenario realista donde un adversario con acceso a la LAN
   hospitalaria pueda explotar el replay del primer mensaje, incluso sin PSK?
4. Veredicto solicitado: ¿ACEPTAR riesgo documentado para v1, o IMPLEMENTAR
   mitigación timestamp antes de producción?

---

## OQ-8 — Rendimiento ARMv8 + comparación Noise_IKpsk3 vs Noise_KK

**Hardware objetivo:** Raspberry Pi 4/5 (ARMv8, ~150–200 USD).
**Criterios de aceptación ya definidos (R10):**
- noise-c binary footprint: < 200 KB
- Handshake latency: < 50 ms en ARMv8

**Comparación pendiente: Noise_IKpsk3 vs Noise_KK**

| Propiedad | Noise_IKpsk3 | Noise_KK |
|-----------|-------------|---------|
| RTT | 1-RTT | 1-RTT |
| Identity hiding | ✅ initiator oculto | ❌ ambas identidades visibles |
| Pre-requisito | Responder's static key | Ambos static keys mutuamente conocidos |
| KCI resistance | Parcial | Mejor |
| PSK binding | psk3 (post-handshake) | No nativo (extensión) |
| Complejidad impl. | Moderada | Menor |

**Preguntas específicas:**
1. Para despliegues cerrados (6 componentes en LAN de hospital), donde todas
   las claves estáticas son pre-provisionadas vía deployment.yml, ¿aporta
   Noise_IKpsk3 algún beneficio real de identity hiding sobre Noise_KK?
2. ¿Es la resistencia KCI de Noise_KK un argumento suficiente para cambiar
   la decisión de v1 si los benchmarks ARMv8 muestran paridad de rendimiento?
3. Si noise-c supera el límite de 200 KB en ARMv8, ¿la implementación directa
   sobre libsodium (X25519 + HKDF + ChaCha20-Poly1305) es criptográficamente
   equivalente a noise-c para Noise_IKpsk3? ¿Qué se pierde?
4. Estimación analítica de handshake latency en ARMv8 Cortex-A72 (Pi 4):
   ¿es < 50 ms razonable para X25519 + 2×ChaCha20-Poly1305 + HKDF?

---

## Formato de respuesta solicitado

Para cada OQ (5, 6, 7, 8):
- **Veredicto:** ACEPTAR / IMPLEMENTAR / CONDICIONAL (con condición explícita)
- **Recomendación técnica:** máximo 5 líneas
- **Riesgo residual si no se implementa:** 1 línea
- **Posición minoritaria registrada:** si la hay

**Restricciones del proyecto:**
- No introducir nuevas dependencias de sistema sin Consejo previo
- noise-c debe ser vendored (commit-pinned), no sistema
- seed_family es el único root of trust disponible (sin TPM, sin HSM)
- Entorno: LAN cerrada, no Internet, no PKI externa
- Operadores: personal no especializado en seguridad