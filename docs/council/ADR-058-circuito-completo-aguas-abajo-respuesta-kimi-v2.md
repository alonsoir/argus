Voy a analizar la V2 del ADR-058 como miembro del Consejo, manteniendo el modo adversario. El contexto es crítico: este pipeline protege hospitales con poco recursos contra ransomware.

---

## Revisión Adversarial de ADR-058 v2

### 🔴 **DEFECTO-1: La "partición D/E" es una distinción filosófica, no una barrera técnica**

La V2 excluye `ingested_at` y `temporal_anomaly` del predicado por ser "deterministas-de-ejecución". Pero **el grafo Kuzu sí las almacena** (`schema.cypher` las declara, `cypher_builder.hpp:86` las computa). El predicado dice "equivalencia del grafo" pero **ignora propiedades que existen en el grafo**.

**Problema concreto:** Si Camino 0 y Flujo A+B producen grafos donde `temporal_anomaly` difiere para el **mismo flujo** (porque `ingested_at` cambió y la window cae en el margen), los dashboards mostrarán **alertas diferentes** para el mismo dato. El predicado dirá "equivalente" pero el usuario verá divergencia.

> "La equivalencia de dos caminos debe definirse sobre lo que deriva del dato" — esto es **votar**, no medir. Lo que deriva del dato **incluye** `temporal_anomaly` porque la fórmula (`window_to_epoch_nanos(window) > ingested_at_ns + margen`) es **determinista dado un par (window, ingested_at)**. El problema no es el determinismo, es que `ingested_at` es un **dato del grafo**, no metadata externa.

**Recomendación:** O bien (a) el predicado incluye `temporal_anomaly` con `ingested_at` fijado en el test (control de ejecución, no exclusión del predicado), o (b) `temporal_anomaly` se computa **en query-time del dashboard**, no en write-time del grafo. Si es write-time, es parte del grafo; si es parte del grafo, es parte de la equivalencia.

---

### 🔴 **DEFECTO-2: "Orden de inserción determinista" es una precondición no verificable en el predicado**

La V2 acepta la objeción del Consejo (Gemini/Kimi/Qwen) y añade: "el Flujo B inserta en orden determinista por `(flow_start_window, seq_in_window)` antes del sink Kuzu; el test de equivalencia asume y verifica esta precondición".

**Pero el predicado §3.1 NO verifica el orden de inserción.** Verifica `set(flow_uid)` y propiedades, no el orden. Si Flujo B inserta en paralelo (bulk load optimizado), el orden puede cambiar y el predicado **no lo detecta** — pero el grafo resultante puede diferir en propiedades de colisiones.

**Peor:** La "verificación de esta precondición" no está en el predicado. ¿Es un test separado? ¿Quién lo escribe? ¿Qué pasa si falla? El ADR dice "asume y verifica" pero no define **cómo** ni **dónde**. Es una promesa sin mecanismo.

> En un hospital con poco recursos, el bulk load será la norma (rendimiento). Si el operador activa bulk load para sobrevivir a un pico, el test de equivalencia sigue pasando pero el grafo es **semánticamente diferente** (perdió flujos en colisiones que Camino 0 no perdió, o viceversa).

**Recomendación:** El predicado debe incluir una cláusula de orden: `∀ uid: first_inserted(uid)_C0 == first_inserted(uid)_AB` (la primera inserción gana en ambos). O, más robusto: eliminar la dependencia de orden usando `ON MATCH SET` con regla determinista (e.g., "mantener el más antiguo"), lo cual también resolvería `DEBT-FLOWUID-SEQ-COLLISION-001` como mejora de fidelidad.

---

### 🟡 **DEFECTO-3: `event_id` = bronce col 2 — la traza `correlation_reader.cpp:85` no demuestra unicidad**

La V2 refuta la objeción de que `event_id` podría ser UUID v4 diciendo que es "bronce col 2". Pero **no mide si es único por fila**.

Si el productor (aguas arriba del bronce) reutiliza `event_id` para múltiples eventos (e.g., batch de alertas con mismo ID de correlación), `set(event_id)_C0` tendrá colisiones. El MERGE en `Alert/TelemetryEvent` con `ON CREATE SET` únicamente **descartaría eventos reales** de forma silenciosa, igual que con `flow_uid`.

El ADR mide que `event_id` existe (`correlation_reader.cpp:85`) pero **no mide su cardinalidad** ni su comportamiento bajo colisión. El argumento "mismo set por construcción" asume unicidad implícita.

> En un hospital, un sensor Wazuh podría emitir 10 alertas con el mismo `event_id` de correlación (ataque en progreso). El grafo guardaría 1. El predicado diría "equivalente" porque ambos caminos guardan 1. Pero el operador perdió 9 alertas.

**Recomendación:** Medir la cardinalidad de `event_id` en el bronce. Si hay duplicados, documentar que el grafo es un **conjunto** (no multiset) por diseño, o cambiar la PK de `Alert` a compuesta. Esto es `DEBT-ALERT-KEY-COMPOSITE-001` (nueva, P1).

---

### 🟡 **DEFECTO-4: La canonicalización NaN/`-0.0` es correcta pero incompleta**

La V2 propone canonicalizar NaN a quiet `0x7ff8000000000000` y `-0.0` a `+0.0`. Esto es sólido para IEEE 754.

**Pero omite dos bordes más de binary64 que pueden surgir en el round-trip AVRO→Parquet→Kuzu:**

1. **Denormales (subnormales):** ¿El converter preserva denormales? Algunas implementaciones de Parquet los flush a cero.
2. **Infinities:** `+Inf`/`-Inf` son válidos en IEEE 754. ¿El schema Kuzu los acepta? `DOUBLE` en Kuzu es `double` de C++ (sí), pero ¿el conector Parquet→Kuzu maneja el mapping correcto?

El ADR dice "el único punto de pérdida real es texto" — pero esto asume que AVRO/Parquet/Kuzu no tienen bugs de edge-case. "Medir, no votar" implicaría **congelar vectores de prueba** para estos bordes, no asumir que el análisis de tipos los cubre.

**Recomendación:** Añadir vectores golden para NaN, `-0.0`, `+Inf`, `-Inf`, y el menor subnormal positivo (`0x0000000000000001`) al test de equivalencia. No es gold-plating; es **cobertura del dominio del tipo**.

---

### 🟡 **DEFECTO-5: `DEBT-GOLD-INTEGRITY-HMAC-001` sigue sin especificación en P0**

La V2 acepta que `hmac_row` sale del predicado y se reubica como "control de integridad bronce↔oro-ledger". Pero **no define el mecanismo**:

- ¿Clave simétrica compartida? ¿Por nodo? ¿Por fila?
- ¿El HMAC del Parquet consolidado (§2 corolario 6) usa la misma clave que el HMAC por-fila del bronce?
- ¿Quién verifica? ¿Cuándo? ¿En el test de equivalencia o en producción?

El ADR dice "la definición del mecanismo vive en `DEBT-GOLD-INTEGRITY-HMAC-001`" — pero esa deuda está en P0 y **este ADR la deja abierta**. Un P0 sin especificación es un agujero en el diseño de seguridad de un pipeline que "salvará vidas".

> Si un atacante modifica el Parquet oro en tránsito (MITM en la LZ), ¿cómo lo detecta el hospital? El ADR dice "HMAC" pero no dice quién tiene la clave, quién verifica, ni qué pasa si falla.

**Recomendación:** El ADR debe incluir al menos la **arquitectura** del HMAC (clave por-nodo en `config.json`, verificación en el conector Flujo B, fallo = rechazo de batch), aunque los detalles de implementación vayan a la deuda.

---

### 🟡 **DEFECTO-6: "Eslabón 0 en el mismo PR que el ADR" — el problema de la v1 persiste**

La V2 no cambia §7: "El ADR entra en el mismo PR que el Eslabón 0". El changelog (§9, #1) corrige "6 verificaciones" a "9" pero **no aborda la objeción de proceso**.

Si el ADR se mergea con la implementación, la ratificación del Consejo es **retrospectiva**. El ADR dice "confirmar lo medido" — pero si el código ya está en `main`, la confirmación es **académica**. El Consejo no puede bloquear sin revertir código.

**Recomendación:** Separar el PR del ADR (solo documento, ratificación previa) del PR de implementación. O, si el proceso del proyecto permite ADRs retrospectivos, renombrar este documento como "ADR-058-RETROSPECTIVE" y abrir un proceso de ratificación formal post-hoc. No es gold-plating; es **gobierno de decisiones en un sistema crítico**.

---

### 🟢 **DEFECTO-7: `DEBT-CIRCUIT-TEMPORAL-ANOMALY-PARITY-001` es un síntoma de diseño**

La nueva deuda P2 reconoce que `temporal_anomaly` debe verificarse como "test unitario de la fórmula". Pero **¿por qué la fórmula toca `ingested_at` en write-time?**

Si `temporal_anomaly` depende del momento de ingestión, un flujo re-ingestado (recuperación de desastre, re-procesamiento de un batch) tendrá `temporal_anomaly` diferente. Esto rompe la **idempotencia** del pipeline — un requisito implícito para cualquier sistema que "salva vidas" (debe recuperarse consistentemente).

**Recomendación:** Considerar si `temporal_anomaly` debería computarse en **query-time** (dashboard lee `window` y compara con `now()`) en vez de write-time. O usar un `ingested_at` determinista (e.g., timestamp del bronce, no del sink). Esto eliminaría la deuda y haría el grafo reproducible.

---

## Resumen para el Consejo (v2)

| # | Severidad | Defecto | Bloquea cierre? |
|---|-----------|---------|-----------------|
| 1 | 🔴 Alto | Partición D/E excluye propiedades que el grafo almacena y el dashboard usa | **SÍ** — falso positivo de equivalencia |
| 2 | 🔴 Alto | Orden determinista es precondición no verificada por el predicado | **SÍ** — el test no detecta violaciones |
| 3 | 🟡 Medio | `event_id` no medido para unicidad/colisiones | No, pero riesgo de pérdida silenciosa de alertas |
| 4 | 🟡 Medio | Bordes IEEE 754 incompletos (denormales, infinities) | No, pero cobertura insuficiente |
| 5 | 🟡 Medio | HMAC en P0 sin arquitectura de clave/verificación | No, pero agujero de seguridad |
| 6 | 🟡 Medio | ADR + implementación en mismo PR = ratificación post-hoc | No, pero debilita gobierno |
| 7 | 🟢 Bajo | `temporal_anomaly` en write-time rompe idempotencia | No, pero deuda técnica semántica |

### Mi recomendación:

**No ratificar** hasta que:

1. **El predicado incluya `temporal_anomaly`** con `ingested_at` controlado en el test (o se documente explícitamente que el dashboard no la usa para decisiones críticas).
2. **El predicado verifique el orden de inserción** (e.g., hash del orden de `flow_uid` por `(window, seq)`) o se elimine la dependencia de orden (mejor: `ON MATCH SET` con regla determinista).
3. Se mida la cardinalidad de `event_id` en el bronce y se documente el comportamiento bajo duplicados.

Las correcciones de la v2 son de calidad (NaN/`-0.0`, `hmac` fuera del predicado, partición D/E como concepto), pero **el predicado sigue siendo más débil de lo que parece**. En un hospital con poco recursos, un falso positivo de equivalencia ("el test pasa, el grafo está bien") que oculta pérdida de alertas o divergencia de anomalías temporales **es peor que un fallo explícito**.

FDO
KIMI