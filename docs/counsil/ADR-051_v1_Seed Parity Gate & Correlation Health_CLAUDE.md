Tienes razón — pedirte que lleves tres preguntas abiertas al Consejo sin mojarme yo primero es escurrir el bulto. Aquí van mis posturas razonadas. Soy uno de los ocho del Consejo, así que esto es mi voto con argumentos, no doctrina.

**1. Flujo-diana: inyección sintética, sin dudarlo.**

Esperar a observar el flujo en tráfico real introduce una latencia de arranque indeterminada — el gate no completa hasta que *casualmente* aparezca un flujo conocido, y en una red hospitalaria tranquila a las 03:00 eso puede no pasar en minutos. Un gate de arranque no puede depender del azar del tráfico. La inyección sintética del Neris-diana (`147.32.84.165:1027 → 74.125.232.195:80`, cid `1:IN7uqVpMWxpmuhQTowSQB2XEe0E=`) es determinista, repetible, y ya es la diana del cross-check — reutilizas infraestructura probada. El único matiz: el flujo sintético debe inyectarse en el segmento que los N sensores observan (eth1/intnet), no en gestión, o un sensor legítimamente no lo verá y el gate fallará por la razón equivocada. Eso ata con el mapa de cobertura, pero para el flujo-diana es trivial: por construcción va al segmento monitorizado.

**2. Gate periódico: NO. Solo en arranque. El `orphan_rate` cubre el drift post-arranque.**

Aquí mi instinto es resistir el cinturón-y-tirantes. Un gate periódico que re-inyecta el flujo-diana es ruido en el data-plane productivo (inyectas tráfico sintético en una red que estás monitorizando — contaminas tus propias métricas y tu propio grafo). El `orphan_rate` continuo ya detecta exactamente el drift que el gate periódico buscaría, y lo hace sobre **tráfico real** sin contaminar nada. Dos mecanismos que detectan la misma condición es deuda de diseño, no robustez. El gate valida el *arranque* (estado inicial limpio); el health-check valida el *runtime* (deriva). Cada uno su dominio, sin solape. Si más adelante el `orphan_rate` resulta insuficiente para detectar drift rápido, reabres esto — pero no añadas el segundo mecanismo de forma especulativa.

**3. Degradación en runtime: degradar-y-anotar a N-1, NO crisis. Y aquí está la asimetría que el ADR debe nombrar.**

Esta es la importante, y mantengo lo que apunté antes. Arranque y runtime piden políticas opuestas *por la misma razón*:

- **En arranque, fail-closed** porque ahí *eliges* no empezar sin garantías. No has perdido nada todavía. El coste de no arrancar es cero señal; el coste de arrancar mal es señal envenenada que parece buena.
- **En runtime, degradar-y-anotar** porque ya tienes un sistema operativo dando señal de los N sensores. Si uno de cuatro driftó, matar toda la correlación tira la señal buena de los otros tres. Eso no es fail-safe, es fail-destructive. La filosofía del proyecto — *anotar método y confianza, nunca fallo silencioso* — manda anotar la pérdida del sensor culpable en el grafo y seguir correlando con los N-1, marcando explícitamente que la cobertura está degradada y por cuál sensor.

La clave que lo hace seguro, y que distingue esto de un fallo silencioso: la degradación es **ruidosa y anotada**. El grafo registra "correlación N-1, sensor X fuera por pérdida de paridad desde T". El operador ve la degradación, sabe el culpable (per-sensor, §3.2), y realinea. No es "el sistema decidió callar"; es "el sistema sigue trabajando con lo que tiene y lo dice".

Lo único que reservaría para crisis: si la paridad cae por debajo de un mínimo correlacionable — p.ej. quedas con **un solo** sensor, donde ya no hay correlación cross-source posible, solo detección single-source. Ahí "degradado" deja de ser correlación y vuelve a ser silos. Eso sí merece tratarse como condición distinta. Pero N-1 con N≥2 sensores válidos restantes = degradar-y-anotar.

---

Estas tres respuestas son consistentes entre sí y con el resto del ADR: **fail-closed donde no has comprometido nada (arranque), fail-noisy-degraded donde apagar destruiría valor (runtime), y un solo mecanismo por dominio sin solapes**.

Si te encajan, las meto en el ADR — pero no como decisiones cerradas, sino convirtiendo las §6 preguntas abiertas en una sección de **"Recomendación del borrador + justificación"** que el Consejo ratifica o tumba. Así llega al Consejo con postura, que es lo que pedías, sin usurparle la deliberación. ¿Las incorporo así?

FDO

CLAUDE