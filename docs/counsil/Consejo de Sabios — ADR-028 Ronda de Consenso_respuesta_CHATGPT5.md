Resolución propuesta del Consejo — directa y ejecutable.

---

# **Veredicto ADR-028 — Ronda de Consenso (DAY 109)**

## **P1 — D4 Validation Layer**

**Opción elegida:** **Opción 3** (JSON + antidating + validación estadística ligera)

**Argumento (1 línea):** Aporta protección real contra poisoning secuencial con coste despreciable, manteniendo implementabilidad inmediata; la similitud coseno es cara y diferible.

**Condición:** **Obligatoria (parcial)**

* JSON thresholds + antidating → **obligatorio ahora**
* Validación estadística → **obligatoria si <100ns/evento**, si no → fallback a Opción 1

---

## **P2 — Rollback lógico**

**Opción elegida:** **Opción 3** (SQLite `valid` ahora + wrapper en roadmap)

**Argumento (1 línea):** Permite rollback O(1) inmediato sin bloquear implementación; el wrapper puede llegar cuando haya presión real.

**Condición:** **Obligatoria (fase 1)**

* `valid=false` + filtrado en retrieval → **debe implementarse ya**
* `TrustAwareFAISSIndex` → **roadmap explícito §8 con criterios de activación**

---

## **P3 — Trust levels**

**Opción elegida:** **Opción 1** (dos niveles ahora)

**Argumento (1 línea):** Introducir niveles inexistentes hoy degrada la veracidad del sistema; la complejidad debe corresponder a la realidad operativa.

**Condición:** **Obligatoria**

* `TRUST_PIPELINE` y `TRUST_EXTERNAL` ahora
* `TRUST_INTERNAL` documentado en roadmap con trigger claro (ej: multi-tenant fleet)

---

## **P4 — Rate limiting**

**Opción elegida:** **Opción 2** (híbrido: subnet + IP)

**Argumento (1 línea):** Defensa en profundidad: subnet captura flooding masivo y IP captura comportamiento individual; ambos son necesarios en entornos hospitalarios.

**Condición:** **Obligatoria**

* IP-level → límite principal
* Subnet → límite secundario configurable (desactivable vía JSON)

---

## **P5 — PluginMode ABI**

**Opción elegida:** **Opción 1** (`typedef enum` C + `uint8_t mode`)

**Argumento (1 línea):** La ABI C es una restricción dura del sistema de plugins; cualquier desviación introduce UB potencial.

**Condición:** **Obligatoria (no negociable)**

---

# **Resumen consolidado**

| Punto         | Decisión                               | Estado |
| ------------- | -------------------------------------- | ------ |
| P1 D4         | JSON + antidating + estadística ligera | ✅      |
| P2 Rollback   | SQLite ahora + wrapper roadmap         | ✅      |
| P3 Trust      | 2 niveles reales                       | ✅      |
| P4 Rate limit | Híbrido IP + subnet                    | ✅      |
| P5 ABI        | C enum + uint8_t                       | ✅      |

---

# **Decisión final del Consejo**

## **APROBADO CON CONDICIONES (cumplidas en esta ronda)**

El ADR-028 puede considerarse **APROBADO y listo para commit** si:

1. D4 incluye **antidating + thresholds JSON**
2. Se implementa **rollback vía SQLite (`valid`)**
3. Se reduce a **2 niveles de trust reales**
4. Rate limiting es **híbrido configurable**
5. `plugin_api.h` mantiene **ABI C estricta**

---

# **Notas críticas (importantes para calidad a largo plazo)**

* Este ADR cierra correctamente un vector serio: **poisoning en la memoria del sistema (RAG/FAISS)**

* La decisión clave aquí no es técnica sino de principio:
  **el sistema deja de confiar en lo que aprende por defecto**

* El mayor riesgo restante NO cubierto en esta fase:

  * Poisoning **lento y estadísticamente plausible** (low-and-slow)
  * Se mitiga parcialmente con D4 estadístico, pero no completamente

→ Esto debe quedar explícito en el ADR como **limitación conocida**

---

# **Recomendación final (no bloqueante)**

Añadir en ADR-028:

> “El sistema prioriza detección de anomalías evidentes y consistencia temporal.
> Ataques de poisoning lento (low-and-slow) quedan parcialmente fuera de cobertura en esta fase.”

Esto evita sobreprometer en el paper y refuerza credibilidad académica.

---

Si quieres, en la siguiente iteración puedo devolverte **ADR-028 final ya integrado con estas decisiones**, listo para commit sin más rondas.
