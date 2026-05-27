Perfecto. Leo los 5 y consolido.ChatGPT5 tiene razón — hay un error en el paper. La narrativa actual dice "contextos idénticos → claves idénticas → MAC verifica cuando no debería". Pero el bug real (según el memory: "asymmetric context bug causing MAC failures") era lo contrario: TX usaba `"ml-defender:sniffer:1.0"`, RX usaba `"ml-defender:ml-detector:1.0"` → contextos **distintos** → claves **distintas** → **MAC failures**.

Necesito corregir el paper antes de consolidar. Un momento:Confirmado. ChatGPT5 tiene razón. El paper tiene la lógica invertida:

- **Texto actual (INCORRECTO):** "both sides derive identical subkeys" → "MAC tags verified correctly" → bug latente
- **Realidad (CORRECTO):** sniffer usa `"ml-defender:sniffer:1.0"`, ml-detector usa `"ml-defender:ml-detector:1.0"` → contextos **distintos** → claves **distintas** → **MAC failures** inmediatas

Corrijo antes de consolidar el Consejo:Paper corregido. Ahora la consolidación del Consejo:

---

## Consejo DAY 103 — Decisiones consolidadas

### Q1 — Separación PacketContext / MessageContext / SkillContext
**Unanimidad 5/0 — APROBADO**

Todos confirman que la separación es correcta y necesaria. Sobre campos adicionales en `MessageContext`, hay tres propuestas con justificación sólida:

| Campo | Propuesto por | Justificación | Veredicto |
|-------|--------------|---------------|-----------|
| `const char* channel_id` | Qwen (crítico) | Sin él el plugin no puede seleccionar contexto HKDF correcto — directamente relacionado con ADR-022 | **✅ AÑADIR — crítico** |
| `uint8_t version` | DeepSeek | Evolución ABI sin romper contratos | **✅ AÑADIR — barato** |
| `uint64_t sequence_number` | ChatGPT5, Grok | Replay protection futura | **⏳ RESERVAR — `uint8_t reserved[8]`** |
| `uint64_t timestamp_ns` | Gemini | Correlación de latencia | **⏳ RESERVAR** |
| `uint8_t authenticated` | ChatGPT5 | Estado de validación MAC | **❌ REDUNDANTE — ya cubierto por `result_code`** |
| `void* user_data` | Grok | Estado privado del plugin | **⏳ PHASE 3** |

`MessageContext` final para ADR-023:
```c
typedef struct {
    uint8_t   version;       // MESSAGE_CONTEXT_VERSION = 1
    uint8_t   direction;     // MLD_TX = 0, MLD_RX = 1
    uint8_t   nonce[12];     // 96-bit monotonic counter
    uint8_t   tag[16];       // Poly1305 tag (16 bytes)
    uint8_t*  payload;       // buffer (in/out)
    size_t    length;        // longitud actual
    size_t    max_length;    // capacidad — siempre >= length + 16
    const char* channel_id;  // "sniffer-to-ml-detector" — HKDF context selector
    int32_t   result_code;   // 0=OK, -1=MAC failure, -2=buffer overflow
    uint8_t   reserved[8];   // para sequence_number / timestamp futuro
} MessageContext;
```

**Nota DeepSeek/Gemini:** `max_length` debe garantizar siempre `length + 16` bytes para el tag Poly1305. El componente host es responsable de alocar el buffer con ese margen.

---

### Q2 — `plugin_process_message()` opcional vs obligatorio
**4/1 — OPCIONAL en PHASE 2a**

- ChatGPT5, DeepSeek, Grok, Qwen: opcional vía `dlsym`, `PLUGIN_API_VERSION=1` sin bump
- Gemini: bump inmediato a v2 (argumento: fragilidad silenciosa si plugin falla y sigue como plugin de red)

**El árbitro decide:** La divergencia de Gemini tiene mérito técnico (fail-closed ante ambigüedad) pero el riesgo real es mínimo porque el loader ya loguea qué hooks existen. **OPCIONAL en PHASE 2a** — con mejora de Grok/DeepSeek: log INFO cuando se detecta que un plugin implementa `plugin_process_message`. Bump a VERSION=2 en PHASE 2b cuando el JSON descriptor declare `"layer": "transport"`.

---

### Q3 — ADR-024: Group Key Agreement
**Unanimidad 5/0 — Noise Protocol IK**

Todos recomiendan Noise IK. Propuesta de Qwen/Gemini más precisa:

```
PSK = HKDF(seed_family, "noise-ik-psk")  ← derivado del seed de familia (ADR-021)

Handshake:
  Initiator (nuevo componente): -> e, es
  Responder (miembro existente): <- e, ee, se

Output: clave de sesión con forward secrecy + autenticación mutua
Sin PKI central. 1-RTT. Ocurre solo en arranque.
```

**Implementación:** Noise-c (C puro, compatible con libsodium 1.0.19). No añade dependencia grande.

---

### Q4 — Secuenciación ADR-023 / ADR-024
**4/1 — Diseño en paralelo, implementación ADR-023 primero**

- DeepSeek, Gemini, Grok, Qwen: diseñar ADR-024 ahora en paralelo (suficiente para el paper como Future Work planificado), implementar ADR-023 primero
- ChatGPT5: secuencial estricto

**Árbitro decide:** Paralelo para diseño — ADR-024 puede escribirse como documento de arquitectura sin bloquear la implementación de ADR-023.

---

### Alerta crítica de ChatGPT5 — resuelta ✅

El error en la descripción del bug HKDF ha sido **corregido en el paper v7**. El PDF actualizado está disponible abajo.

---**Paper v7 corregido** — 21 páginas. El bug HKDF ahora describe correctamente: contextos **distintos** (component-scoped) → claves **distintas** → **MAC failures**. La corrección la detectó ChatGPT5, buen ejemplo de por qué existe el Consejo.

**Resumen de lo que queda para DAY 104:**

1. Redactar ADR-023 formal con `MessageContext` revisado (incluye `channel_id`, `version`, `reserved[8]`)
2. Redactar ADR-024 borrador (Noise IK + PSK derivado de seed_family)
3. PR `feature/bare-metal-arxiv` → `main`
4. Nueva rama `feature/plugin-crypto`
5. Llamada Andrés Caro Lindo

¿Hacemos el commit del paper corregido antes de cerrar el día?