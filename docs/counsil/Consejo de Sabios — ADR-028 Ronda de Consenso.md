# Consejo de Sabios — ADR-028 Ronda de Consenso
## ML Defender (aRGus NDR)
**Fecha:** 6 de Abril de 2026
**Objetivo:** Cerrar ADR-028 con veredicto unánime o mayoría cualificada (4/5)

---

## Contexto

ChatGPT5 redactó el borrador base de ADR-028. El resto del Consejo aportó feedback.
DeepSeek y Grok enviaron una reescritura editorial idéntica del documento — útil
como versión pulida, pero sin divergencia crítica entre ellos.
Gemini y Qwen aportaron crítica real con gaps identificados.
Claude identificó 3 condiciones obligatorias y 2 menores.

Esta ronda busca consenso sobre los **5 puntos abiertos**. No se pide reescribir
el ADR — se pide votar cada punto con argumento de una línea.

---

## Estado del borrador

El borrador de ChatGPT5 (pulido por DeepSeek/Grok) está **aprobado en estructura**
por todos los revisores. Las decisiones D1-D10 son correctas en intención.

Los puntos de debate son los siguientes:

---

## Punto 1 — D4 Validation Layer: ¿umbrales concretos o configurables vía JSON?

**Posición A (Claude):** Los umbrales de D4 deben ser configurables vía JSON
(coherente con "JSON is the LAW"). Sin umbrales concretos o referencia a cómo se
configuran, D4 no es un contrato falsificable — es una aspiración. Se añade también
validación anti-backdating explícita:
`ABS(event_timestamp - ingestion_timestamp) < MAX_DRIFT_THRESHOLD` (configurable,
default 5 minutos). Gemini propuso esto y es el único ataque de timestamp no cubierto.

**Posición B (Gemini):** Añadir también similitud de coseno básica contra los últimos
N registros para detectar "semantic flooding" (inundación semántica que desplaza
vectores legítimos).

**Posición C (Qwen):** Añadir validación estadística lightweight (<50ns) con
contadores atómicos precomputados para detectar poisoning sutil por secuencialidad
de IPs, burst anómalo de puertos, ratio de protocolo anómalo.

**Pregunta al Consejo:**
¿Qué versión de D4 aprobamos?
- **Opción 1:** Umbrales JSON + antidating (Claude) — implementable DAY 110
- **Opción 2:** Opción 1 + similitud coseno (Claude + Gemini) — más complejo
- **Opción 3:** Opción 1 + validación estadística ligera (Claude + Qwen) — medio
- **Opción 4:** Las tres capas (Gemini + Qwen + Claude) — más completo, más costoso

---

## Punto 2 — D5 Rollback lógico: ¿cómo se implementa?

**El problema:** D5 promete "toda decisión es reversible (rollback lógico)" pero
no define el mecanismo. Qwen lo identifica como "promesa vacía" y propone un
`TrustAwareFAISSIndex` con journaling interno.

**Posición Claude (pragmática):** El rollback lógico se implementa mediante un
flag `valid BOOLEAN` en la tabla SQLite de metadatos que ya existe en el sistema.
Las queries de retrieval filtran eventos con `valid=false`. No se reindexan los
embeddings en FAISS — se enmascaran en consulta. Rollback en O(1), reutiliza
infraestructura existente, implementable en una tarde.

**Posición Qwen (más robusta):** `TrustAwareFAISSIndex` wrapper con journaling
interno — más limpio arquitectónicamente pero requiere trabajo significativo.

**Posición Gemini:** Menciona que `pipeline_version` + `schema_version` en
metadatos ya permite rollback quirúrgico por versión — ortogonal a lo anterior.

**Pregunta al Consejo:**
¿Qué mecanismo de rollback aprobamos?
- **Opción 1:** SQLite `valid` flag + filtrado en retrieval (Claude) — mínimo viable
- **Opción 2:** TrustAwareFAISSIndex wrapper (Qwen) — más robusto, más trabajo
- **Opción 3:** Opción 1 ahora + Opción 2 en roadmap §8 (Claude + Qwen) — pragmático

---

## Punto 3 — Trust levels: ¿dos o tres niveles?

**Posición A (Claude + Qwen):** Reducir a dos niveles activos:
- `TRUST_PIPELINE` — origen validado del pipeline (default para todos los eventos actuales)
- `TRUST_EXTERNAL` — origen externo, validación estricta adicional
  `TRUST_INTERNAL` se introduce en Track 2/Fleet cuando existan fuentes distinguibles.
  Tres niveles donde solo uno es real hoy es documentación que sobreestima la
  complejidad actual.

**Posición B (borrador original ChatGPT5/DeepSeek/Grok):** Mantener tres niveles
(`TRUST_INTERNAL`, `TRUST_PIPELINE`, `TRUST_EXTERNAL`) para forward compatibility.
El coste de añadirlo ahora es mínimo; eliminarlo después es costoso.

**Posición Gemini:** No tomó posición explícita en este punto.

**Pregunta al Consejo:**
¿Dos o tres niveles de trust?
- **Opción 1:** Dos niveles ahora, `TRUST_INTERNAL` en roadmap (Claude + Qwen)
- **Opción 2:** Tres niveles desde el principio (ChatGPT5, DeepSeek, Grok)

---

## Punto 4 — Rate limiting: ¿por subnet o por IP individual?

**Posición A (Claude + Qwen):** Rate limiting por IP de origen individual, no por
subnet. En redes hospitalarias /16, todos los hosts comparten subnet — rate limiting
por subnet no detiene a un atacante que usa IPs distintas dentro del rango.
Implementación: hash table con estado por IP, O(1). Umbral configurable vía JSON.

**Posición B (borrador original):** Rate limiting por subnet como primera línea.

**Pregunta al Consejo:**
¿Rate limiting por IP o por subnet?
- **Opción 1:** Por IP individual, configurable vía JSON (Claude + Qwen)
- **Opción 2:** Por subnet como primera línea, por IP como segunda (híbrido)

---

## Punto 5 — PluginMode: ¿`enum class` C++ o `typedef enum` C?

**El problema:** El ADR usa `enum class PluginMode { NORMAL, READONLY }` (C++).
Pero `plugin_api.h` es una API con C ABI puro (todos los plugins lo usan con
`extern "C"`). Un `enum class` no es compatible con C ABI.

**Posición Claude:** Usar `typedef enum` C con valores enteros explícitos:
```c
typedef enum {
    PLUGIN_MODE_NORMAL   = 0,
    PLUGIN_MODE_READONLY = 1
} PluginMode;
```
Y en `MessageContext`, el campo como `uint8_t mode` (no el enum directamente,
para garantizar tamaño fijo en ABI).

**Pregunta al Consejo:**
¿`enum class` C++ o `typedef enum` C con `uint8_t`?
- **Opción 1:** `typedef enum` C + `uint8_t mode` en struct (Claude) — ABI segura
- **Opción 2:** `enum class` C++ en el ADR con nota de implementación (cosmético)

---

## Lo que NO está en debate

Los siguientes puntos tienen consenso previo y no necesitan nueva votación:

- **D2 (READ-ONLY + decisión binaria):** ✅ Unanimidad
- **D3 (separación de fases):** ✅ Unanimidad
- **D6 (metadatos obligatorios en FAISS):** ✅ Unanimidad (con `ingest_hash` de DeepSeek)
- **D8 (prohibición escritura plugins):** ✅ Unanimidad
- **D9 (modo READ-ONLY en API):** ✅ Unanimidad
- **D10 (observabilidad):** ✅ Unanimidad
- **Tests TEST-RAG-POISON-1 → TEST-RAG-INVARIANT-5:** ✅ Unanimidad
- **Principio rector:** ✅ Unanimidad — "El sistema no solo debe ser seguro en lo que ejecuta, sino también en lo que aprende y recuerda."

---

## Formato de respuesta solicitado

Para cada punto, indicad:
1. **Opción elegida** (número)
2. **Argumento de una línea** (por qué esa opción y no las otras)
3. **¿Condición obligatoria o puede diferirse?**

Al final, indicad: **APROBADO / APROBADO CON CONDICIONES / RECHAZADO**

El objetivo es tener ADR-028 APROBADO al cierre de esta ronda y commiteado
en `docs/adr/` antes del fin de DAY 109.

---

## Mi posición como Claude (para transparencia)

| Punto | Opción | Razón |
|-------|--------|-------|
| P1 D4 | Opción 1 (JSON + antidating) | Implementable hoy; coseno y estadística van al roadmap |
| P2 Rollback | Opción 3 (SQLite ahora + wrapper roadmap) | Reutiliza infraestructura; no bloquea DAY 110 |
| P3 Trust levels | Opción 1 (dos niveles) | Tres niveles hoy = documentación que miente |
| P4 Rate limiting | Opción 1 (por IP, JSON) | Subnet es inútil en /16 hospitalario |
| P5 PluginMode | Opción 1 (typedef C + uint8_t) | C ABI es no negociable en plugin_api.h |

**Mi veredicto:** APROBADO CON CONDICIONES — aprobado si se incorporan los 5 puntos.