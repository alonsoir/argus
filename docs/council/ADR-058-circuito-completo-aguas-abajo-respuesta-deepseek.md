He revisado el ADR-058 en profundidad. El diseño es sólido en muchos frentes y la trazabilidad a mediciones en código es excelente. Sin embargo, identifico varios defectos o puntos que necesitan aclaración antes de la ratificación, especialmente en la definición del predicado de equivalencia y en la coherencia de los elementos que se compararán.

## Principales defectos encontrados

### 1. El predicado §3.1 incluye HMAC, pero no está en la proyección común (Kuzu)
La equivalencia se define **únicamente sobre la proyección Kuzu** (único output común). El predicado dice:
```
 ∧ ∀ fila: hmac_row preservado de bronce
```
Pero el grafo Kuzu **no almacena HMAC** (ni lo almacena Camino 0 ni está previsto almacenarlo). Esto convierte esta condición en **inverificable** como parte del test de equivalencia.  
➜ **Acción:** Eliminar esa cláusula del predicado o, alternativamente, añadir que el HMAC se verifica aparte como control de integridad del oro (no como condición del gate).

### 2. Camino 0 no almacena `flow_start_window` ni `seq_in_window` en Kuzu, pero el predicado las exige
El predicado incluye:
```
props_identidad(uid)_C0 == props_identidad(uid)_AB  # node_id, community_id, flow_start_window, seq_in_window
```
Pero el Camino 0 actual (`correlation-engine/src/main.cpp`) no escribe `flow_start_window` ni `seq_in_window` como propiedades en los nodos `NetworkFlow`. La V1 decide materializar `flow_start_window` en el oro, pero **no se ha previsto añadir esa propiedad en Camino 0**. Sin esa modificación, la comparación de propiedades fallará incluso sin errores en Flujo A+B.  
➜ **Acción:** O bien añadir estas propiedades a la escritura de Camino 0 (requiere modificar el sink existente), o bien posponer su inclusión en el predicado hasta que ambos caminos las soporten. De otro modo, el test de equivalencia no podrá ejecutarse.

### 3. Falta una estrategia de deduplicación para el oro ante entrega at-least-once
El ZMQ se define como PUSH/PULL at-least-once. El bronce (CSV) simplemente añade filas; si hay duplicados, estos pasarán al oro y el ledger contendrá filas repetidas. Aunque Kuzu use MERGE y las ignore, el **oro-ledger tendrá duplicados**, rompiendo la unicidad esperada de un ledger y complicando la verificación de integridad (varias filas con mismo contenido y distinto HMAC).  
➜ **Acción:** Incorporar una deuda que documente explícitamente si se toleran duplicados en el oro o si se implementará deduplicación (por ejemplo, mediante un identificador único de evento de correlación o un offset de Kafka). Esto afecta a la calidad del “oro único”.

### 4. Ambigüedad en la escritura atómica del bronce (Eslabón 0)
El Eslabón 0 dice: “escritura atómica .tmp → rename + cierre por tiempo absoluto”. El bronce actual es un CSV diario al que se añaden filas continuamente. Una escritura atómica por fila con rename **no es compatible con el modo append**: requeriría reescribir todo el fichero en cada inserción o renunciar a la atomicidad real. La intención probable es atomicidad en la rotación (al cambiar de día), pero el texto induce a confusión.  
➜ **Acción:** Clarificar el alcance exacto de la atomicidad (solo en la rotación, o si se usa un journal) y cómo se garantiza que el reader no vea ficheros parciales durante el día.

### 5. El guarda NaN para los scores requiere especificar el patrón canónico
El ADR dice: “el converter Flujo A normaliza el patrón de NaN. No bloquea el cierre del predicado.” Pero no se define **cuál es el patrón canónico** (por ejemplo, el NaN silencioso estándar de IEEE 754 o un payload concreto). Como ambos caminos deben producir el mismo patrón de bits para que la comparación bit-exacta funcione, es necesario fijarlo explícitamente.  
➜ **Acción:** Definir el valor exacto de NaN canónico (por ejemplo, `0x7ff8000000000000`) y asegurar que ambos lados lo usen.

### 6. `window_micros()` debe ser replicable de forma exacta en el converter Flujo A
Para que el `flow_start_window` materializado coincida, el converter Flujo A (posiblemente en Python) debe implementar la misma aritmética que `window_micros(sec, nano)`. Aunque la fórmula es trivial, cualquier diferencia (p.ej., redondeo de nanosegundos a microsegundos) puede romper la bit-exactitud del `flow_uid`.  
➜ **Acción:** Verificar que la función esté especificada (p.ej., `sec*1_000_000 + nano/1000` con truncamiento entero) y que el converter la use exactamente igual; añadir tests de vectores de ejemplo.

### 7. Predicado de equivalencia: falta enumeración explícita de las columnas 12‑17
Aunque se referencia a `schema.cypher` y `cypher_builder.hpp`, para un lector del ADR no es inmediato qué columnas son las 12‑17 (más allá de los “3 scores”). Una tabla breve o una remisión concreta a la definición del contrato de 19 columnas ayudaría a evitar malentendidos en la implementación del test.  
➜ **Acción:** Incluir en el ADR la lista de propiedades concretas que se comparan (nombre y tipo), o una referencia inequívoca al documento donde se definen.

## Otros riesgos menores / observaciones
- La cláusula de caducidad (§3.2) es sensata, pero el ticket `DEBT-JOIN-CONFIDENCE-001` no detalla qué se considera “join adaptativo/no-determinista”. Podría ser necesario un esbozo para que el Consejo entienda cuándo se activaría.
- La rotación del bronce y el watcher `inotify` para el reader requieren manejar correctamente el cierre del fichero antiguo y la aparición del nuevo; un error aquí podría producir pérdida de eventos en el arranque de la rotación. Valdría la pena incluir una deuda de vigilancia específica para esa transición.

## Resumen
Los defectos 1 y 2 son bloqueantes para la definición del predicado tal cual está redactado. El defecto 3 es una carencia en la integridad del oro que debería documentarse explícitamente. Los puntos 4, 5 y 6 son ambigüedades que deben resolverse antes de implementar para evitar bloqueos posteriores. El punto 7 es una mejora de claridad.

Si se ajustan estos puntos, el ADR quedará robusto y listo para la implementación de esta misma semana.

FDO

DEEPSEEK