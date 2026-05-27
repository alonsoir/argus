# Consejo de Sabios — Segunda Ronda Consolidada ADR-023 + ADR-024
## DAY 104 — 1 abril 2026

**Revisores:** ChatGPT (Gepeto), DeepSeek, Gemini, Grok, Qwen (→DeepSeek, patrón confirmado)
**Árbitro:** Alonso Isidoro Roman
**Rama:** feature/plugin-crypto
**Ronda:** 2 de 2 — validación de la sesión consolidada DAY 104

---

## Veredictos segunda ronda

| Revisor | ADR-023 | ADR-024 |
|---------|---------|---------|
| ChatGPT (Gepeto) | ACCEPTED (listo con 3 añadidos) | DISEÑO APROBADO |
| DeepSeek | ACCEPTED | DISEÑO APROBADO |
| Gemini | ACCEPTED CONSOLIDADO | DISEÑO APROBADO CONSOLIDADO |
| Grok | ACCEPTED | DISEÑO APROBADO |
| Qwen (→DeepSeek) | ACCEPTED | DISEÑO APROBADO |

**Resultado:** 5/5 ACCEPTED para ADR-023. 5/5 DISEÑO APROBADO para ADR-024.
**Unanimidad alcanzada en segunda ronda.**

---

## Nuevos hallazgos de la segunda ronda

La primera consolidación fue validada con alta convergencia. La segunda ronda
añade refinamientos de precisión, no reversiones de decisiones. Se incorporan
a continuación como decisiones D7–D11.

---

### 🔴 NUEVAS DECISIONES CRÍTICAS

---

**D7 — Modelo de confianza de plugins: declarar explícitamente**

Señalado por ChatGPT como el punto más importante no cerrado.

Hay una contradicción silenciosa en el diseño actual:
- D3 trata al plugin como potencialmente malicioso (security invariants)
- Pero el ABI C le da acceso total a memoria (punteros, escritura directa)

Los invariantes de seguridad de D3 no son enforceables contra un plugin
activamente malicioso en un ABI C. El host puede validar post-invocación,
pero un plugin con intención maliciosa puede modificar `direction`, `nonce`
o `tag` antes de que el host valide.

Decisión: declarar explícitamente el trust model en el ADR:

```
Plugin trust model:
- Plugins are considered trusted-but-potentially-buggy, not tamper-proof.
- The C ABI boundary does not enforce memory safety against malicious plugins.
- Security invariants (D3) are validated by the host post-invocation but are
  not cryptographically enforced against a malicious plugin actor.
- Malicious plugin resistance is out of scope for ADR-023.
- Defense against malicious plugins requires OS-level isolation (AppArmor,
  seccomp) outside the scope of this ADR.
```

Esto no debilita el diseño — lo hace honesto. Un revisor de seguridad detectará
esta contradicción inmediatamente si no está documentada.

---

**D8 — Validación post-invocación: especificar mecanismo operativo**

Señalado por ChatGPT y Gemini. D3 declara el principio pero no el mecanismo.
Un revisor preguntará: "¿cómo validas que el plugin no modificó direction o nonce?"

Decisión: añadir especificación operativa:

```
Post-invocation validation (host-enforced, after plugin returns):
1. direction: byte-wise identical to pre-invocation snapshot
2. nonce[12]: byte-wise identical to pre-invocation snapshot
3. channel_id: pointer equality must hold (same address)
4. length: must satisfy 0 < length <= max_length

Violation of any invariant → std::terminate() (fail-closed).
Implementation: host snapshots {direction, nonce, channel_id} before
plugin invocation and compares after return, before using the result.
```

Adicionalmente (Gemini):
```
Host must also validate: ctx->payload == original_ptr
(plugin must not reasign the payload pointer)
Violation → std::terminate()
```

---

**D9 — Plugins forman parte del TCB: declararlo**

Señalado por ChatGPT. Los plugins operan sobre plaintext antes del cifrado.
Esto implica que forman parte del Trusted Computing Base del canal cifrado.
No declararlo hace que el diseño parezca que el cifrado protege "todo",
cuando no es así frente a un plugin comprometido.

Decisión: añadir nota de seguridad en ADR-023:

```
Security note:
Plugins operate on plaintext prior to encryption (or on plaintext after
decryption) and are therefore part of the Trusted Computing Base (TCB)
of the secure channel. A compromised plugin can read or modify all
plaintext data processed by the host component.
This is an inherent consequence of the plugin architecture and is
documented here for transparency.
```

---

**D10 — MLD_DEV_MODE solo honrado en builds de desarrollo**

Señalado por DeepSeek como hallazgo de precisión sobre D1.

Si `MLD_DEV_MODE=1` es simplemente una variable de entorno comprobada en
runtime, un atacante con acceso al entorno podría forzar el modo degradado
en producción.

Decisión:

```
MLD_DEV_MODE is only honored when the component was built with
CMAKE_BUILD_TYPE=Debug OR when the compile-time flag MLD_ALLOW_DEV_MODE
is explicitly set at build time.
In production builds (CMAKE_BUILD_TYPE=Release/Production), MLD_DEV_MODE
is ignored and the component always behaves fail-closed.
```

---

**D11 — ADR-023 forward-compatible con ADR-024: declarar explícitamente**

Señalado por ChatGPT. El diseño de `MessageContext` (channel_id → HKDF context,
direction, nonce) está claramente preparado para soportar ADR-024, pero esto
no está declarado. Un revisor podría acusarlo de "hidden dependency".

Decisión: añadir una línea explícita en ADR-023:

```
Forward compatibility:
ADR-023 is forward-compatible with ADR-024 (Dynamic Group Key Agreement)
but does not require it. The channel_id, direction, and nonce fields in
MessageContext are designed to support session-derived keys (ADR-024)
without API changes. ADR-023 is fully functional with static HKDF-derived
keys (current implementation).
```

---

### 🟡 NUEVAS DECISIONES RECOMENDADAS

---

**R7 — Nota de implicación de compromiso de seed_family en Noise**

Señalado por ChatGPT. Si seed_family se compromete, no solo se rompen las
subclaves HKDF de canal — también se rompe la autenticación del handshake
Noise (el PSK se puede derivar). Forward secrecy protege sesiones pasadas,
pero no futuras. Añadir en ADR-024:

```
Security implication of seed_family compromise:
Compromise of seed_family allows derivation of the Noise PSK, enabling
an attacker to impersonate any component in future handshakes.
Forward secrecy of past sessions is preserved (ephemeral keys are not
derived from seed_family). Rotation of seed_family requires reprovisioning
all components (tools/provision.sh) and is addressed in OQ-6.
```

**R8 — Tabla de info strings prohibidos en ADR-024**

Señalado por Qwen. Previene errores en implementaciones futuras o de terceros:

```
Prohibited HKDF info strings (must not be used for Noise PSK derivation):
- "noise-ik-psk"         — too generic, collision risk
- "ml-defender:noise"    — missing version, prevents rotation
- "" (empty string)      — anti-pattern, weakens domain separation
Canonical approved string: "ml-defender:noise-ikpsk3:v1"
```

**R9 — OQ-7 (replay): aclaración sobre primer mensaje Noise**

Señalado por Qwen y Grok. El primer mensaje de Noise_IKpsk3 es técnicamente
replayable (no tiene nonce de frescura explícito), pero sin el PSK no es útil
para un atacante. Documentar en OQ-7:

```
OQ-7 (updated): The first handshake message (→ e, es, s, ss) is replayable
without explicit freshness. The PSK binding (psk3) renders a replay useless
without knowledge of the PSK (derived from seed_family). The threat model
therefore assumes seed_family is not compromised; if it is, the entire system
is compromised (documented in D4 and R7). An optional mitigation is to include
a timestamp or nonce in the first message payload (Noise permits payload in
handshake messages) — deferred to PHASE 3 evaluation.
```

**R10 — noise-c métricas de aceptación para evaluación post-arXiv**

Señalado por DeepSeek. Añadir criterios concretos a R4:

```
Acceptance criteria for noise-c evaluation (post-arXiv):
- Binary footprint increase: < 200 KB
- Handshake latency on target hardware: < 50 ms
- If either criterion is not met: implement Noise_IKpsk3 directly
  over libsodium primitives (X25519 + HKDF-SHA256 + ChaCha20-Poly1305).
```

---

## Minorías de segunda ronda

**Gemini — sequence_number:** Mantiene posición. Vigilará out-of-order delivery
en PHASE 2a; reabrirá propuesta para bump a v2 antes de PHASE 2c si hay evidencia
empírica de necesidad. Registrado como condición de reapertura.

**Grok — Noise_KK:** Mantiene posición. Solicita comparación explícita IKpsk3
vs KK en OQ-8 (latencia, código, propiedades de seguridad incluyendo KCI resistance).
Incorporado en OQ-8.

**ChatGPT — DEV_MODE:** Mantiene posición de eliminar escape hatch incluso en DEV.
→ No adoptado. D10 cierra el vector de ataque real (DEV_MODE solo en builds debug).

---

## Nota de sesión — Qwen / DeepSeek (segunda ronda)

En la segunda ronda, la respuesta de Qwen comienza: *"Soy DeepSeek — modelo de
DeepSeek Research (China, pero independiente de Alibaba/Tongyi Lab). Qwen es un
modelo distinto de Alibaba."*

Es decir: el modelo que respondió bajo el slot "Qwen" afirma ser DeepSeek y
distingue entre ambos. Dos interpretaciones posibles:

1. Qwen tiene entrenamiento contaminado que lo lleva a identificarse como DeepSeek.
2. La interfaz usada para invocar "Qwen" está sirviendo realmente un modelo DeepSeek.

En cualquier caso, la diversidad epistémica real del Consejo puede estar reducida
si dos slots están sirviendo el mismo modelo subyacente. Se registra para
investigación futura. La calidad técnica de las respuestas es independiente del
self-labeling y sigue siendo válida.

---

## Tabla de acciones final (D1–D11 + R1–R10)

### ADR-023 — acciones a incorporar

| ID | Acción | Prioridad |
|----|--------|-----------|
| D1 | Fail-closed en producción; DEV_MODE único escape con warning | 🔴 |
| D2 | Contrato ownership/lifetime: channel_id (solo durante invocación), payload (host owner), max_length ≥ length+16 | 🔴 |
| D3 | Security invariants: direction/nonce/tag read-only para plugin | 🔴 |
| D7 | Declarar trust model de plugins (trusted-but-buggy, not tamper-proof, TCB note) | 🔴 |
| D8 | Especificar validación post-invocación (snapshot + comparación byte a byte) | 🔴 |
| D9 | Declarar plugins como parte del TCB del canal cifrado | 🔴 |
| D10 | MLD_DEV_MODE solo honrado en builds Debug/MLD_ALLOW_DEV_MODE | 🔴 |
| D11 | Declarar forward-compatibility con ADR-024 explícitamente | 🟡 |
| R1 | reserved[8] → sequence_number en PLUGIN_API_VERSION=2 (PHASE 3) | 🟡 |
| R2 | Watchdog externo documentado como requisito de despliegue | 🟡 |
| R3 | TEST-FUZZ-1: fuzzing MessageContext antes de PHASE 2c | 🟡 |

### ADR-024 — acciones a incorporar

| ID | Acción | Prioridad |
|----|--------|-----------|
| D4 | Info string HKDF: "ml-defender:noise-ikpsk3:v1" + domain separation explícita | 🔴 |
| D5 | OQ-5 (revocación), OQ-6 (rotación), OQ-7 (replay), OQ-8 (perf ARMv8) | 🔴 |
| D6 | install_session_keys() + transición atómica + gate etcd READY | 🔴 |
| R7 | Nota implicación compromiso seed_family en Noise PSK | 🟡 |
| R8 | Tabla de info strings prohibidos | 🟡 |
| R9 | OQ-7 actualizado: primer mensaje replayable pero inútil sin PSK | 🟡 |
| R10 | noise-c métricas de aceptación: <200 KB, <50 ms | 🟡 |
| R4 | noise-c vs libsodium puro — evaluación post-arXiv con criterios R10 | 🟡 |
| R5 | noise-c: hardening flags + commit pinning en CMakeLists | 🟡 |
| R6 | Noise_KK comparación explícita vs IKpsk3 en OQ-8 | 🟡 |

---

## Veredicto final de sesión (segunda ronda)

**ADR-023: ACCEPTED — listo para cierre tras incorporar D1–D11**
**ADR-024: DISEÑO APROBADO — IMPLEMENTACIÓN POST-ARXIV tras incorporar D4–D6 + R7–R10**

La segunda ronda no revirtió ninguna decisión de la primera. Añadió precisión
donde el diseño era correcto en principio pero incompleto en especificación
operativa. El sistema criptográfico resultante es coherente, honesto sobre sus
límites y defendible en revisión externa cs.CR.

---

*Sesión segunda ronda cerrada — DAY 104 — 1 abril 2026*
*Árbitro: Alonso Isidoro Roman*
*Consejo: ChatGPT, DeepSeek, Gemini, Grok, Qwen (→DeepSeek)*
*Co-authored-by: Alonso Isidoro Roman + Claude (Anthropic)*