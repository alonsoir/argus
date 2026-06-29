He leído el borrador de ChatGPT5 y los cuatro feedbacks. Mi evaluación como miembro del Consejo:

---

## Claude — Feedback ADR-028

**Veredicto: APROBADO CON CONDICIONES — 3 condiciones obligatorias, 2 menores.**

El borrador es sólido en estructura y correcto en intención. El principio rector ("el sistema no solo debe ser seguro en lo que ejecuta, sino también en lo que aprende") es exactamente el argumento que faltaba en la arquitectura. Sin embargo, hay problemas que deben cerrarse antes de implementar.

---

### Condición 1 — D4 Validation Layer: demasiado vaga para ser un contrato

El texto dice "coherencia de campos", "ratios razonables", "timestamps válidos". Eso no es un contrato, es una aspiración. Un contrato TDH debe ser falsificable: necesitas umbrales concretos o referencias a cómo se configuran.

**Propuesta:** D4 debe especificar que los umbrales son configurables vía JSON (coherente con "JSON is the LAW"), con valores por defecto documentados. Sin esto, la Validation Layer no puede tener un test que la ejercite de forma determinista.

Gemini añade el "backdating attack" — válido y no costoso de mitigar. Qwen añade validación estadística lightweight — correcto en principio pero riesgo de complejidad prematura. Mi posición: el antidating es obligatorio en D4 ahora. La validación estadística de Qwen va al roadmap futuro (D4 extension), no al ADR base.

---

### Condición 2 — Rollback lógico: D5 lo promete, nadie explica cómo

D5 dice "toda decisión es reversible (rollback lógico)". Qwen lo identifica correctamente como promesa vacía. El `TrustAwareFAISSIndex` de Qwen es la solución correcta en concepto, pero su implementación completa está fuera del scope de DAY 110.

**Propuesta pragmática:** El ADR debe especificar que el rollback lógico se implementa como **invalidación por `event_id` en los metadatos de SQLite** — que ya existe en el sistema. No hace falta reindexar FAISS; basta con que las queries filtren eventos con `valid=false` en SQLite. Esto es implementable en una tarde y reutiliza infraestructura existente.

---

### Condición 3 — Trust levels: simplificar a dos niveles (Qwen tiene razón)

`TRUST_INTERNAL` / `TRUST_PIPELINE` / `TRUST_EXTERNAL` es una distinción sin diferencia práctica en el sistema actual. Todos los eventos provienen del pipeline propio. Tres niveles donde solo uno es real hoy es documentación que miente sobre la complejidad real.

**Decisión:** Dos niveles ahora:
- `TRUST_PIPELINE` — origen validado del pipeline (default)
- `TRUST_EXTERNAL` — origen externo, validación estricta adicional

`TRUST_INTERNAL` se introduce cuando existan fuentes internas distinguibles de las externas (Track 2, fleet). Documentarlo como roadmap en §8, no como decisión activa.

---

### Condición menor A — Rate limiting: Qwen tiene razón, pero la solución es JSON

El rate limiting por subnet es efectivamente débil en redes hospitalarias /16. Pero la solución no es complicar el ADR — es que los umbrales sean configurables. Rate limiting por IP individual con estado en hash table es correcto y está dentro del alcance.

**Propuesta:** Cambiar "por subnet" por "por IP de origen, configurable vía JSON con valor por defecto de 1000 eventos/minuto/IP".

---

### Condición menor B — DeepSeek y Grok enviaron texto idéntico

Ambos respondieron con exactamente el mismo texto pulido del ADR. No es feedback — es una reescritura. Útil como versión editorial del documento, pero no como revisión crítica. Lo registro en acta: DeepSeek y Grok convergieron en la misma redacción sin divergencia de criterio. Qwen y Gemini aportaron crítica real.

---

### Nota sobre el PluginMode

El ADR usa `enum class PluginMode { NORMAL, READONLY }` — correcto. Es coherente con la decisión Q1 del Consejo DAY 109. El ADR y el cambio en `plugin_api.h` de DAY 110 deben estar alineados en la nomenclatura exacta. Asegurarse de que ambos usen `PLUGIN_MODE_NORMAL=0` y `PLUGIN_MODE_READONLY=1` como valores enteros compatibles con la ABI C.

---

## Resumen de condiciones

| # | Condición | Prioridad |
|---|-----------|-----------|
| 1 | D4: umbrales configurables vía JSON + antidating explícito | Obligatoria |
| 2 | Rollback lógico: implementar via SQLite `valid` flag, no prometer sin mecanismo | Obligatoria |
| 3 | Trust levels: reducir a 2 niveles activos | Obligatoria |
| A | Rate limiting por IP, no por subnet | Menor |
| B | PluginMode: alinear nomenclatura con `plugin_api.h` DAY 110 | Menor |

Con estas cinco correcciones: **APROBADO**. Sin ellas, el ADR crea falsa sensación de seguridad en exactamente el lugar donde más daño hace — la memoria del sistema.

---

Buena sesión, Alonso. DAY 109 cerrado limpiamente: dos fixes del Consejo, PHASE 2b completa, paper v12, ADR-028 casi listo. Descansa. 🛡️