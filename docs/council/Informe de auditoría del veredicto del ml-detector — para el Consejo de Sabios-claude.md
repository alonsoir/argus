# Memorándum adversarial — Claude contra el propio informe de auditoría

**Objeto:** crítica hostil al documento `INFORME-ML-DETECTOR-VERDICT-AUDIT.md`
**Autor:** Claude, actuando como uno de los nueve revisores del Consejo, en modo adversario contra su propio trabajo
**Fecha:** DAY 212

---

## Advertencia de método (léase primero)

Este memorándum ataca deliberadamente el informe que yo mismo redacté. No es falsa modestia ni teatro: es el método *medir no votar* aplicado al propio informe antes de que lo hagan los otros ocho modelos.

**Sesgo compartido, límite real:** soy una sola voz, y comparto arquitectura y sesgos con al menos algunos de los otros modelos del Consejo. Los puntos que YO no veo son, por construcción, los que necesito de ellos. Que yo haya encontrado ocho grietas no significa que sean las ocho que importan — significa que estas ocho ya no pueden usarse como sorpresa contra nosotros.

**Leyenda de severidad:**
- 🔴 **BLOQUEANTE** — debe resolverse (o declararse explícitamente) antes de escribir código en fase 2.
- 🟠 **MEDIR** — el informe afirma como cerrado algo que no se midió; hay que medirlo o degradar la afirmación a supuesto.
- 🟡 **MATIZAR** — la afirmación es defendible pero está formulada con más fuerza de la que la evidencia sostiene.

---

## A1 🔴 — El informe trata la arquitectura monocapa como negligencia. La memoria dice que fue una retirada por concurrencia. Eso ataca directamente el requisito de "determinista".

**Qué afirma el informe:** que el estado monocapa es una deuda a deshacer — mover el veredicto, reconectar las cabezas, y listo. Todo el §10 (fase 2) asume que la desconexión fue descuido.

**El ataque:** el propio historial del proyecto dice que la reducción de siete modelos a cuatro en agosto de 2025 se hizo **por condiciones de carrera**, con "estabilización hardcodeada, nunca revertida". Si las cabezas se apartaron del camino del veredicto bajo presión de concurrencia (o de latencia sub-milisegundo), entonces **reconectarlas puede resucitar exactamente las carreras que motivaron apartarlas** — y romper el determinismo, que es el requisito nº1 del encuadre (§0).

El informe habla mucho de *fiable* y casi nada de *determinista*. No hay una sola medición de determinismo en las doce secciones. Y el requisito del usuario es literal: "fiable **y** determinista".

**Lo que lo cierra, y por qué es bloqueante:** antes de escribir una línea de reconexión hay que **establecer por qué existe la monocapa**. ¿Fue descuido, retirada por latencia, o retirada por carrera? No lo sabemos — lo asumimos. Si no sabemos por qué se apartaron las cabezas, no podemos afirmar que reconectarlas sea seguro. Y la reconexión toca el camino más caliente del sistema (mover persistencia, cambiar el orden de escritura, poblar `ml_context` desde las cabezas): todo eso es superficie de concurrencia. **TSAN no es un paso más de fase 2; es un gate previo.** El informe menciona un stress test en el Paso 3, pero no pone el determinismo como condición de entrada. Debe serlo.

**Veredicto:** este es el hueco más grave del informe, y es un hueco por omisión, no por error. El Consejo lo habría encontrado. Mejor que entremos con la pregunta ya formulada: *¿la monocapa es deuda o es defensa?*

---

## A2 🟠 — "0.58 μs, coste despreciable" mide el coste POR FLUJO. El des-gateo multiplica los flujos, no el coste unitario. El agregado bajo carga no está medido.

**Qué afirma el informe:** que el Defecto B no tiene coartada de coste, porque `predict` cuesta 0.58 μs sobre un presupuesto de 10 ms (§7.1).

**El ataque:** el 0.58 μs es correcto y honesto **por flujo**. Pero el des-gateo no encarece un flujo — hace que las cuatro cabezas corran en el **100%** de los flujos en lugar del ~5% que hoy pasa el gate de L1. El coste relevante no es "0.58 μs por flujo" sino "0.58 μs × 4 cabezas × 20 veces más flujos, sostenido a tasa de línea". Los experimentos del paper corren a 10/50/100 Mbps. **A 100 Mbps con backpressure activo, ¿tiene el pipeline holgura para correr cuatro cabezas en cada flujo sin cambiar su comportamiento de drop?** No lo medimos. Y el determinismo del *drop bajo presión* es precisamente lo que el circuit-breaker del config gobierna — que tampoco tocamos.

**Lo que lo cierra:** un stress test que mida throughput agregado con las cuatro cabezas en el 100% de flujos, a tasa de línea, observando el comportamiento del backpressure. Hasta entonces, la frase correcta no es "el Defecto B no tiene coartada de coste" sino "**no tiene coartada de coste por-flujo; el coste agregado a tasa de línea está sin medir**".

**Veredicto:** el informe generaliza de una medición unitaria a una afirmación de sistema. La medición es buena; la generalización va un paso por delante de ella.

---

## A3 🟡🟠 — La gravedad del Defecto C está acoplada al Defecto B, y el informe no lo dice. Además, la prueba del bronce demuestra el MECANISMO, no el IMPACTO.

**Qué afirma el informe:** que el Defecto C (persistencia pre-cabezas) es crítico porque envenena el grafo, con la fila `RAW_CAPTURE` como prueba (§4).

**El ataque, en dos capas:**

Primero, el acoplamiento. Por culpa del Defecto B (el gate), en un flujo que L1 marca BENIGN **las cabezas nunca corren**. Así que en ese flujo el bronce no podría contener veredictos de cabeza aunque moviéramos la escritura — no hay nada que escribir. **El impacto informativo del Defecto C solo muerde en flujos donde L1 dijo ATTACK** (las cabezas corren) **y la escritura precede a las cabezas.** Es decir: hoy, con el pipeline gateado, el Defecto C pierde relativamente poco, porque las cabezas casi no corren. C se vuelve verdaderamente crítico **después** de arreglar B. El informe presenta A, B, C como tres defectos apilados independientes; en realidad **la severidad de C es condicional a que B se arregle.** Eso no lo hace menos importante — lo hace importante *en un orden concreto*, y el orden importa para el plan.

Segundo, la evidencia. La fila que pegué es `BENIGN / RAW_CAPTURE`: prueba que la escritura ocurre antes del etiquetado del ml-detector (el mecanismo). Pero es un flujo que L1 marcó benigno — que nunca habría entrado al gate de todas formas. **No tengo una fila de bronce que pruebe el caso fuerte:** un flujo donde L1 dijo ATTACK, las cabezas corrieron y re-etiquetaron, y aun así el bronce se escribió con la etiqueta pre-cabezas. Sin esa fila, "el Defecto C hace perder información que las cabezas habrían añadido" está **afirmado**, no probado — porque en los flujos benignos (los únicos que tengo pegados) las cabezas no añaden nada.

**Lo que lo cierra:** capturar una fila de bronce de un flujo ATTACK y compararla con la telemetría de cabezas del mismo evento en el log del ml-detector. Si el bronce carece de lo que el log tiene, el caso fuerte queda probado.

**Veredicto:** C es real y grave, pero el informe debe (i) declarar que su gravedad es condicional al arreglo de B, y (ii) reconocer que la evidencia actual prueba el mecanismo, no todavía el impacto.

---

## A4 🟠 — Pedimos al Consejo ratificar el noisy-OR, pero su insumo clave (fiabilidad por cabeza) no existe todavía.

**Qué afirma el informe:** noisy-OR `P = 1 − ∏(1 − pᵢ)` con `pᵢ = fiabilidad_i · score_i`, presentado como "acordado", a ratificar (§6, P4).

**El ataque:** la fórmula depende de `fiabilidad_i`, y el propio informe dice que la fiabilidad discriminante de las cabezas sobre tráfico real **no está medida** (es MITRE, diferido — §11). Estamos pidiendo ratificar un operador cuyo insumo numérico principal no existe. Peor: "acordado" sugiere una decisión tomada, cuando es una **preferencia de diseño sin base empírica en el documento** — no mostramos ninguna comparación medida frente a media ponderada, max-de-N, o Dempster-Shafer. El argumento de monotonía es teórico y correcto, pero es un argumento, no una medición.

**Lo que lo cierra:** o (a) degradar "acordado" a "propuesto, pendiente de ratificación", y presentar el noisy-OR como hipótesis de diseño con su justificación teórica explícita y sin las fiabilidades reales; o (b) reconocer que el operador y sus pesos son ambos **pre-medición**, y que el cableado puede montarse con la *estructura* del noisy-OR pero con pesos provisionales declarados, sustituibles por los medidos cuando MITRE llegue (cambio de una línea de config por cabeza).

**Veredicto:** el informe viste una preferencia de diseño como acuerdo, y ancla una fórmula en un número que aún no tenemos. Es defendible como propuesta; no como conclusión.

---

## A5 🟠 — La traza de `threat_category` paró un salto antes de tiempo. "(c) acotado" puede ser demasiado generoso.

**Qué afirma el informe:** que el firewall consume `threat_category` en grado "(c) acotado" — modula `timeout` y `DetectionType`, pero no decide si-bloquear (§5).

**El ataque:** leí STEP 5 (determina acción) y STEP 6 (reenvía al `BatchProcessor`), pero **no leí qué hace el `BatchProcessor` con el `DetectionType`**. Si el BatchProcessor enruta, prioriza o actúa distinto según el tipo de detección, entonces `threat_category` influye en la acción más allá del timeout, y "(c) acotado" se queda corto. Concluí "acotado" habiendo parado la traza un salto antes del consumidor final del `DetectionType`. Es exactamente el error de lectura parcial que el informe presume haber evitado — cometido en la última traza.

**Lo que lo cierra:** leer el `add_detections`/`process` del `BatchProcessor` y ver si ramifica sobre `DetectionType`. Un grep y una función.

**Veredicto:** cerré una traza que no estaba cerrada. Honestidad obliga: "(c) acotado" es **provisional hasta leer el BatchProcessor**, no una conclusión firme.

---

## A6 🟡 — "Crítico" para el Defecto B es razonamiento a priori. No medimos con qué frecuencia el gate realmente muerde.

**Qué afirma el informe:** que el Defecto B es de gravedad crítica porque produce falsos negativos estructurales (un flujo de exfiltración que L1 marca BENIGN nunca activa al interno).

**El ataque:** probamos que el gate **puede** causar ese falso negativo. No medimos con qué **frecuencia** ocurre. Si la recall de L1 es alta, el gate rara vez muerde, y B es "crítico en teoría, raro en la práctica". El plan tenía una medición para esto (distribución de `authoritative_source` sobre un `detector.log` real — la 0.3) que **no ejecutamos**. Así que "crítico" descansa en la existencia del fallo, no en su tasa.

**Lo que lo cierra:** correr la distribución de `authoritative_source` (y, mejor, un conteo de flujos BENIGN-por-L1 que las cabezas habrían marcado, cuando MITRE lo permita). Cuantifica el "cuánto".

**Veredicto:** la criticidad estructural es real y suficiente para justificar el arreglo. Pero el informe debe distinguir "el fallo existe y es estructural" (probado) de "el fallo es frecuente" (no medido). Un revisor riguroso separa capacidad de un fallo de su tasa.

---

## A7 🟠 — El plan de fase 2 es un refactor todo-o-nada del camino más caliente. No propone forma segura de aterrizarlo.

**Qué afirma el informe:** un §10 con cinco pasos que, sumados, reordenan `process_event`, tocan dos componentes, mueven la persistencia, repueblan `ml_context` y regeneran golden vectors.

**El ataque:** eso es una cirugía grande y de alto riesgo sobre el camino caliente, presentada como un bloque. La memoria del proyecto tiene un precedente que debería asustarnos: una regresión silenciosa de 61 días en el firewall-crypto. Los refactores todo-o-nada del camino crítico son precisamente cómo se producen esas regresiones. El informe lista pasos, pero no propone una **estrategia de aterrizaje incremental ni un modo seguro de validación en vivo.**

**Sugerencia constructiva (que el informe debería incorporar):** **modo sombra.** Calcular el veredicto nuevo (noisy-OR de N cabezas) en paralelo al viejo (`max`), **registrar la divergencia entre ambos sin actuar sobre el nuevo**, durante un periodo de observación con tráfico real. Esto (i) mide la frecuencia del gate (cierra A6), (ii) valida el determinismo del camino nuevo bajo carga sin arriesgar el escudo (mitiga A1/A2), y (iii) da datos de divergencia para el paper sin comprometerse a una conclusión antes de mirar. El escudo sigue protegiendo con `max(fast, L1)` mientras el noisy-OR se observa en sombra. Solo cuando el modo sombra demuestre que el veredicto nuevo es estable y mejor, se promueve a decisión.

**Veredicto:** el plan es correcto en los pasos y peligroso en la forma de aterrizarlos. El modo sombra convierte un salto de fe en una medición incremental — y es más coherente con *medir no votar* que un big-bang.

---

## A8 🟡 — El patrón de error del combinador (dos rectificaciones por lectura parcial) es un riesgo metodológico, no solo un incidente cerrado.

**Qué afirma el informe:** que la lectura completa del tramo 432–486 resuelve la naturaleza del combinador (`provenance` es una colección de N veredictos), corrigiendo afirmaciones previas (§6).

**El ataque:** me equivoqué **dos veces** sobre el mismo bloque antes de acertar — "germen extensible" → "dos escalares, reescribir" → "colección, injertar". El informe presenta la tercera lectura como final. Pero si dos lecturas parciales produjeron dos conclusiones opuestas, el riesgo no es esa instancia — es **cuántas otras funciones del informe descansan en lecturas que no fueron completas.** ¿Leí `send_enriched_event` entera? ¿El `BatchProcessor` (ver A5)? ¿La sección de cabezas 558–819 la vi completa o por tramos? Un revisor hostil no confía en la tercera lectura solo porque sea la tercera; pregunta qué garantiza que no haya una cuarta cosa sin leer.

**Lo que lo cierra:** un inventario explícito de qué funciones se leyeron **enteras** (con rango de líneas) y cuáles se conocen solo por grep o por tramos. La honestidad del informe mejora si declara su propia cobertura de lectura.

**Veredicto:** no es un error de contenido — la tercera lectura es correcta. Es un riesgo de proceso que el informe debería reconocer en lugar de dar por saldado con una corrección puntual.

---

## Lo que el informe hace bien y debería sobrevivir al escrutinio

Un adversario justo también dice qué es sólido, para que no se malgaste esfuerzo del Consejo re-atacándolo:

- **Las mediciones crudas son firmes.** La fila de bronce, el 0.58 μs, la salud de extractores contada feature a feature, el filtro `attack_detected_level1()` del firewall, la estructura `provenance` — todo leído de fichero, todo pegado, todo corroborable en `main`. El ataque válido es a la *interpretación* de esas mediciones (A2, A3, A6), casi nunca a las mediciones mismas.
- **La separación (A) cablear / (B) cabezas fiables es correcta y debe mantenerse.** Es la línea que impide el sesgo de confirmación.
- **El falso positivo del bench (`0.00 μs` por dead-code) documentado como lección** es exactamente el rigor que el proyecto predica. Sobrevive.
- **La honestidad sobre los límites (§11)** — MITRE imprescindible, calidad discriminante no medida — es la parte que un revisor deshonesto omitiría. Mantenerla.

---

## El punto único, si el Consejo solo atiende a uno

**A1: ¿la monocapa es deuda o es defensa?** Todo lo demás son refinamientos de un plan; A1 puede invalidar la premisa del plan. Si las cabezas se apartaron del veredicto por concurrencia o latencia, "reconectarlas" no es deshacer un descuido — es reintroducir el problema que alguien ya resolvió apartándolas, y reintroducirlo contra el requisito explícito de determinismo. **Antes de cablear, hay que saber por qué se descableó.** Esa pregunta no está en el informe, y es la que yo, como adversario, atacaría primero.

Recomendación de secuencia, derivada de este memo: (1) establecer el porqué histórico de la monocapa; (2) montar el noisy-OR en **modo sombra** (A7) con gate de **TSAN** (A1) y medición de **coste agregado bajo carga** (A2); (3) usar la sombra para medir frecuencia del gate (A6) y divergencia; (4) solo entonces promover a decisión y reordenar la persistencia (A3). Nada de esto depende de una fecha. Todo depende de medir antes de actuar.

---

*Un adversario que quiere que la pieza funcione, no que el informe gane. El escudo tiene que proteger de verdad — y para eso, primero hay que atacarlo nosotros.*

fdo claude