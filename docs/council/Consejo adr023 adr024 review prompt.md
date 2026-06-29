# Consejo de Sabios — Sesión de Revisión ADR-023 + ADR-024
## ML Defender (aRGus NDR) — DAY 104

---

Actúas como revisor técnico externo del proyecto **ML Defender (aRGus NDR)**,
un sistema NDR open-source en C++20 para organizaciones con recursos limitados
(hospitales, escuelas, ayuntamientos). El proyecto lleva 104 días de desarrollo
y utiliza una metodología de revisión multi-LLM llamada **Consejo de Sabios**.

Tu rol es el de un **revisor cs.CR / sistemas distribuidos** con criterio propio.
Se espera que identifiques fallos, contradicciones, riesgos no contemplados y
alternativas mejores. La unanimidad no es el objetivo; el rigor sí.

---

## Contexto del sistema

- **Pipeline:** 6 componentes (etcd-server, sniffer, ml-detector,
  firewall-acl-agent, rag-ingester, rag-security)
- **Transporte:** ZeroMQ + ChaCha20-Poly1305 + HKDF-SHA256 + libsodium 1.0.19
- **Plugin loader:** dlopen/dlsym, C pure ABI, ADR-012 PHASE 1b implementada
- **Restricción clave:** hardware sin AES-NI, ARMv8 commodity (~150-200 USD)
- **Tests:** 25/25 suites verdes

---

## ADR-023 — Multi-Layer Plugin Architecture

### Decisión

Plugins interactúan con la capa criptográfica exclusivamente a través de un
struct `MessageContext`. El componente host (sniffer, ml-detector, etc.) es
propietario de la derivación de claves y cifrado/descifrado. Los plugins
reciben y devuelven valores `MessageContext`; nunca acceden a HKDF ni libsodium
directamente.

### MessageContext

```c
typedef struct {
    uint8_t     version;       // MESSAGE_CONTEXT_VERSION = 1
    uint8_t     direction;     // MLD_TX = 0, MLD_RX = 1
    uint8_t     nonce[12];     // contador monotónico 96-bit
    uint8_t     tag[16];       // Poly1305 tag (16 bytes)
    uint8_t*    payload;       // buffer (in/out)
    size_t      length;        // longitud actual del payload
    size_t      max_length;    // capacidad — siempre >= length + 16
    const char* channel_id;    // e.g. "sniffer-to-ml-detector"
    int32_t     result_code;   // 0=OK, -1=MAC failure, -2=buffer overflow
    uint8_t     reserved[8];   // reservado para sequence_number / timestamp
} MessageContext;
```

### Plugin API (opcional, vía dlsym)

```c
// PLUGIN_API_VERSION = 1
int plugin_process_message(MessageContext* ctx);
```

- Si el símbolo está ausente: degradación elegante, plugin recibe payload raw.
- `result_code != 0` → el componente host invoca `std::terminate()` (fail-closed).

### Estrategia de integración: PHASE 2a/2b/2c

Orden aprobado: `firewall-acl-agent → rag-ingester → rag-security`

Gates: `TEST-INTEG-4a` antes de 2b, `TEST-INTEG-4b` antes de 2c.

**Restricción crítica (DAY 103):** `CryptoTransport` es read-only durante PHASE 2a.

### Minoría registrada

Gemini propuso bump inmediato a `PLUGIN_API_VERSION = 2` con `sequence_number`
y `timestamp` como campos no reservados. Desestimado: expansión prematura de API
antes de validación en producción. El campo `reserved[8]` provee migration path.

---

## ADR-024 — Dynamic Group Key Agreement (BORRADOR)

### Problema

El sistema actual deriva subclaves por canal mediante HKDF-SHA256 desde un
`seed.bin` estático provisionado en despliegue. Limitaciones:

1. Compromiso de `seed.bin` → derivación de todas las subclaves del componente.
2. Sin mecanismo para que dos nodos independientes establezcan clave de sesión
   compartida sin pre-compartir seed out-of-band.

### Decisión

Adoptar **Noise\_IKpsk3** como handshake de acuerdo de claves dinámico.

### Cadena de derivación

```
seed_family (32 bytes, ADR-021)
    └─ HKDF-SHA256(seed_family, info="noise-ik-psk")
         └─ PSK (32 bytes)  ← inyectado en Noise_IK como psk3
```

### Patrón de handshake

```
Noise_IKpsk3

Pre-message:
  → s   (clave estática pública del responder, conocida en deploy time)

Handshake (1-RTT, solo en arranque):
  → e, es, s, ss
  ← e, ee, se, psk
```

**Propiedades:** 1-RTT, identity hiding, forward secrecy por sesión,
PSK binding al seed de despliegue.

### Stack de implementación

- Handshake: noise-c (vendored, commit pinned)
- Primitivas: libsodium 1.0.19 (ya compilado desde fuente)
- Keypairs estáticos: X25519 (generados por extensión de `tools/provision.sh`)
- Transport post-handshake: CryptoTransport existente (sin cambio de API)

### Integración con CryptoTransport

Noise\_IK produce (tx\_key, rx\_key) al completar el handshake. Estas claves
de sesión **reemplazan** las subclaves HKDF estáticas. `MessageContext` (ADR-023)
y `contexts.hpp` no cambian.

### Timing

Handshake una vez por arranque, sincronizado con registro etcd.
Fallo → `std::terminate()` (fail-closed).

### Open questions (sin resolver)

1. ¿Rekeying periódico o solo por reinicio?
2. Distribución de claves públicas estáticas en despliegues multi-nodo.
3. Pinning de versión de noise-c.
4. Semántica de retry si el peer no está listo (propuesta: 5 intentos × 2s).

### Estado

**DISEÑO — implementación post-arXiv.** No bloquea PHASE 2a/2b/2c.

---

## Preguntas al Consejo

Por favor responde con criterio independiente a cada una:

**Sobre ADR-023:**

1. ¿El diseño de `MessageContext` expone alguna superficie de ataque no
   contemplada? ¿Hay campos que sobren o falten?

2. ¿El mecanismo de degradación elegante (`plugin_process_message` ausente →
   payload raw) es correcto, o debería ser fail-closed también?

3. ¿El orden de integración `firewall-acl-agent → rag-ingester → rag-security`
   es el correcto, o ves una razón para cambiarlo?

4. ¿La minoría de Gemini (bump inmediato a v2) debería reconsiderarse?

**Sobre ADR-024:**

5. ¿`Noise_IKpsk3` es el patrón correcto para este caso de uso, o hay un
   patrón Noise más adecuado (NK, XX, NX...)?

6. ¿El binding PSK al `seed_family` existente es seguro, o introduce riesgo
   de reutilización de material de clave entre contextos distintos?

7. ¿noise-c es la implementación correcta para un sistema C++20 embebido,
   o hay alternativas más apropiadas?

8. ¿Las 4 open questions están bien planteadas? ¿Hay riesgos de diseño no
   contemplados que deberían convertirse en open questions adicionales?

**General:**

9. ¿Hay alguna contradicción o inconsistencia entre ADR-023 y ADR-024?

10. ¿Cambiarías el status de ADR-024 de DISEÑO a algo más restrictivo dado
    que la implementación es post-arXiv?

---

## Formato de respuesta solicitado

Por favor estructura tu respuesta así:

```
REVISOR: [tu nombre/modelo]
FECHA: [hoy]

VEREDICTO GLOBAL ADR-023: [ACCEPTED / ACCEPTED CON CONDICIONES / RECHAZADO]
VEREDICTO GLOBAL ADR-024: [DISEÑO APROBADO / DISEÑO CON RESERVAS / RECHAZADO]

HALLAZGOS CRÍTICOS (bloquean aceptación):
- [lista]

HALLAZGOS RECOMENDADOS (no bloquean):
- [lista]

RESPUESTAS A PREGUNTAS ESPECÍFICAS:
Q1: ...
Q2: ...
[...]
Q10: ...

POSICIÓN DE MINORÍA (si aplica):
- [cualquier posición que el autor debería registrar aunque no adopte]
```

---

*Proyecto: ML Defender (aRGus NDR) — github.com/alonsoir/argus*
*Metodología: Consejo de Sabios — 7 revisores LLM + árbitro humano*
*Rama activa: feature/plugin-crypto — DAY 104*