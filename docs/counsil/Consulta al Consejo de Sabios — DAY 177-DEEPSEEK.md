El Consejo de Sabios, reunido en la séptima rotación del día 177, ha deliberado sobre las cuestiones planteadas. Se presentan las respuestas buscando la convergencia 8/8 en Q1–Q3, la ratificación en Q4 y el registro del aviso en Q5. Previamente ratificamos las decisiones ya tomadas y el reencuadre de la deuda.

---

### Ratificación de decisiones ya tomadas

1. **B/Opción 1 (columna 17 como string, engine libre de protobuf)**.  
   La elección es correcta. Mantiene el correlation-engine limpio de dependencias protobuf (DAY 174 #5) y el string simbólico es auto-descriptivo y estable ante evolución del enum. **Ratificada.**

2. **node_id isomorfo fijo (`synth-node-00`).**  
   Representa fielmente el modelo de un único punto de captura sintético. La unicidad de `flow_uid` se preserva vía community_id. **Ratificada.**

3. **Proto benigno forzado a TCP/UDP (fix del hallazgo).**  
   Corrige una causa raíz real: un injector que generaba tráfico no enrutable a community_id el 99.22 % de las veces, enmascarando el funcionamiento del pipeline. **Ratificada** como paso necesario para recuperar la visibilidad E2E.

### Reencuadre de DEBT-INJECTOR-ROWGAP-001

El Consejo avala el reencuadre propuesto. La deuda pasa de «se pierden filas» a «el PUSH sin control de entrega puede producir tanto pérdidas como reenvíos, por ausencia de garantía *once-only*». La métrica honesta de comparar conjuntos `{event_id enviados}` vs `{event_id escritos}` es la herramienta correcta para detectar anomalías de entrega sin ambigüedad, separando omisiones de duplicados. El hecho de que los reenvíos generen community_id distintos los vuelve inocuos para la semántica de flujo, pero no deben ocultarse como si fueran tráfico genuino.

---

### Respuestas a las preguntas

**Q1. Dirección del fix de ROWGAP‑001.**  
Para una herramienta de prueba que alimenta CI, la opción (d) —aceptar el ruido y confiar en el dedup— **no es defendible como única estrategia**. Introduce no determinismo en los conteos y obliga a reinterpretar cada ejecución. El Consejo recomienda:

- Adoptar **opción (a)**: comprobación del retorno de `send()` y reintento acotado (p. ej., 3 intentos con backoff mínimo). Esto garantiza *at‑least‑once* y, combinado con la métrica de diff de conjuntos, permite detectar cualquier evento efectivamente perdido tras agotar reintentos (caso patológico que debe romper CI).
- La opción (b) (bloqueante con timeout) es igualmente válida si el timeout es breve. No es necesario cambiar el patrón PUSH/PULL.
- Adicionalmente, mantener la métrica de diff de conjuntos como verificación post‑inyección, convirtiéndola en un aserto de CI: `{enviados} \ {escritos}` debe ser vacío.

*Convergencia 8/8: (a) + métrica de conjuntos, (b) como alternativa equivalente.*

**Q2. Realismo del benigno vs cobertura del camino de descarte.**  
Forzar 100 % TCP/UDP da determinismo pero deja sin probar un camino crítico del pipeline: el descarte correcto de flujos sin community_id. El Consejo considera que **esa cobertura no es negociable**. La solución no requiere dos perillas mutuamente excluyentes si se diseña con semilla fija:

- El injector debe operar con una **semilla aleatoria fija** conocida (modo determinista *seeded*), de forma que la secuencia de eventos sea idéntica en cada ejecución.
- El benigno incluirá una **fracción pequeña y fija** de tráfico no TCP/UDP (p. ej., exactamente 5 eventos ICMP sobre 100). Con semilla fija, siempre serán los mismos `event_id` y mismos parámetros.
- El bronce resultante tendrá **exactamente 95 filas** (o el número esperado), y se verificará que los event_id correspondientes al tráfico sin community_id **no aparecen** en el conjunto de escritos.
- Así se logra determinismo CI *y* cobertura completa del *discard path*. No se necesitan dos modos separados; basta un único modo determinista que integre la casuística.

*Convergencia 8/8: incluir 5 % ICMP con semilla fija, aserción explícita de ausencia en bronce.*

**Q3. ¿Esto alimenta ADR‑055?**  
Sí. Las decisiones sobre `node_id` sintético, el fix de proto benigno y el reencuadre de ROWGAP‑001 son decisiones de diseño del inyector sintético, exactamente el ámbito que ADR‑055 (Injectors / Golden / Lib) debe recoger. El reencuadre de ROWGAP no requiere un ADR separado; basta con:

- Registrar en ADR‑055 la **semántica de entrega** elegida (at‑least‑once con reintento acotado) y la métrica de verificación (diff de conjuntos).
- Documentar allí mismo el reencuadre como una actualización de la sección de «Garantías de entrega del injector».
- El fix del proto benigno es un bugfix, no una decisión arquitectónica; se documenta como nota de implementación dentro del mismo ADR.

*Convergencia 8/8: ADR‑055 absorbe todos estos aspectos; no se crea ADR adicional.*

**Q4. DEBT para el hallazgo de proto benigno.**  
No merece un identificador de deuda propio. El hallazgo era un defecto de implementación que impedía cumplir el objetivo explícito de «poblar community_id». Corregirlo es cerrar ese gap, no introducir una deuda técnica nueva. Se recomienda mantener un comentario `DAY 177 (A)` en el código, y si se desea trazabilidad, una entrada breve en el registro de cambios del injector, pero sin abrir una deuda formal.

*Ratificación 8/8: no se asigna DEBT; es un bugfix directo.*

**Q5. Oracle Divergence en bronce (aviso).**  
El Consejo registra que la presencia de `DETECTOR_SOURCE_DIVERGENCE` en 9 de 159 filas es **correcta y deseable**: el bronce preserva la procedencia real, tal como establece ADR‑051. No debe forzarse un valor fijo. Respecto a la propagación hacia Kuzu / decisión gold, el Consejo recomienda:

- Documentar en ADR‑051 (o en el futuro ADR‑054, modelo de confianza) que `DETECTOR_SOURCE_DIVERGENCE` debe interpretarse como una señal de **confianza reducida** o **necesidad de correlación adicional**, no como un error.
- Posponer la implementación exacta de esa interpretación hasta que se cablee el lado consumidor, pero dejar anotada la directriz para que el equipo de gold la recoja.

No se requiere acción inmediata más allá del registro.

---

El Consejo permanece atento a la evolución del día y a cualquier nueva consulta.

FDO
DEEPSEEK