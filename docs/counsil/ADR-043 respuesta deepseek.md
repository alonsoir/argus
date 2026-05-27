El Consejo de Sabios saluda a Alonso Isidoro Román y agradece la rápida iteración. La versión 3 del ADR-0043 es un salto cualitativo considerable. Se han abordado las principales preocupaciones de coherencia, identidad e idempotencia con soluciones elegantes y bien fundamentadas. El documento transmite ahora solidez y un pensamiento distribuido maduro.

Procedo a desglosar mi dictamen:

## Puntos resueltos satisfactoriamente

- **Identidad estable de entidades (D2)**. Usar la MAC como campo primario y la jerarquía *MAC → hostname → IP* es la decisión correcta para entornos gestionados de infraestructura crítica. El matiz de etiquetar los *fallbacks* a IP como `NetworkPresence` en lugar de `Host` es una muestra de rigor semántico que evitará dolores de cabeza analíticos. Bien resuelto.
- **Idempotencia (D4a, D5)**. La clave de idempotencia basada en la propia firma del batch determinista, junto con el `MERGE` sobre el nodo `Batch`, es una solución impecable. Elimina cualquier ambigüedad sobre reintentos causados por conectividad intermitente. La verificación previa (*IF EXISTS... SKIP*) antes de tocar el grafo minimiza el trabajo inútil en el servidor central.
- **Ordenación temporal sin aristas (D5)**. Eliminar la relación `PRECEDES` y utilizar la comparación lexicográfica del campo `period` (ISO 8601) es una simplificación valiente y técnicamente correcta. Reduce la complejidad del grafo, mejora el rendimiento y evita problemas de ordenación entre nodos de una misma instalación. La consulta de ejemplo es clara y demuestra que no se pierde funcionalidad.
- **Timestamps UTC (D4b, Restricciones)**. La decisión taxativa de usar *epoch nanoseconds int64 UTC* sin timezone ni formato local es ejemplar para un sistema distribuido global. Evita ambigüedades y simplifica la lógica de comparación en todos los componentes.
- **Rotación de K_pseudo con `PREVIOUS_IDENTITY` (D3)**. La introducción de una relación que vincule la identidad antigua con la nueva durante una rotación es una estrategia de migración perezosa muy apropiada. Evita reescribir históricos masivos y mantiene trazabilidad. La coordinación con el drenado de batches en vuelo está correctamente señalada como deuda pendiente.
- **Flujo de derecho al olvido (D8)**. Incluir desde el diseño un comando firmado de borrado, con auditoría certificada, demuestra previsión regulatoria y técnica. Es la base correcta sobre la que construir la validación jurídica.

## Recomendaciones complementarias (no bloqueantes, para futuras revisiones o ejecución)

Aunque el ADR está ya en un estado excelente para proceder, mi responsabilidad como *sabio* es señalar grietas que podrían manifestarse con escala o en escenarios de fallo prolongado. Las enumero para que se consideren en la fase de implementación o en un ADR de detalle.

### 1. Almacenamiento de los lotes crudos como fuente de verdad (event sourcing)

El batch mensual que llega al servidor central es un artefacto valiosísimo: inmutable, firmado y con todos los datos para reconstruir el estado del grafo Neo4j. Actualmente, el ADR asume que, si el ingestor falla, se reintenta desde el nodo (gracias a ZeroMQ). Pero ¿qué ocurre si el propio cluster Neo4j sufre un desastre y no hay backup, o si se necesita reprocesar meses de datos tras corregir un bug en la lógica de ingesta?

Recomendaría **exigir que el batch se persista en un almacenamiento de objetos duradero y barato** (tipo MinIO, o incluso un volumen NFS) **antes de invocar el pipeline de ingesta**. Esto proporciona:
- Una copia de seguridad cruda e inmutable de toda la memoria episódica enviada.
- La capacidad de reconstruir el grafo desde cero sin depender de los nodos edge, que a los 30 días habrán rotado sus SQLite.
- Una vía sencilla de auditoría y verificación independiente.

Dado que los lotes son mensuales y tienen un tamaño acotado, el coste es mínimo y el beneficio en resiliencia es enorme. No es necesario un ADR completo, pero sí una línea en las decisiones: *"Los batches se escriben en almacenamiento duradero antes de su ingesta. Este almacenamiento es la fuente de verdad para disaster recovery del grafo Neo4j."*

### 2. Detección proactiva de lotes perdidos

La pregunta abierta **OQ-1** atañe a la conectividad intermitente; pero el problema más grave no es cómo se reintenta, sino cómo se detecta que un nodo *nunca* ha enviado su lote del mes. Con un horizonte de 30 días en SQLite, si un nodo queda aislado durante 31 días por una negligencia operativa, los datos se pierden para siempre sin que nadie lo sepa.

El sistema debería incluir un **cronómetro de expectativa de lote** en el servidor central o en los observers etcd. Por ejemplo:
- El servidor central sabe qué nodos existen y qué instalaciones. Para el día 5 del mes siguiente, si no se ha registrado un `Episode` para un `node_id` dado en el periodo anterior, se emite una alerta.
- O bien, los propios nodos envían un pequeño heartbeat (apenas unos bytes) a través del mismo canal ZeroMQ cuando generan el lote, permitiendo monitorizar el extremo emisor.

Esto no requiere una decisión arquitectónica compleja, pero sí incluir un ítem en la sección de deuda técnica u operativa para no depender únicamente de la buena voluntad de la red.

### 3. Única emisión por periodo

La clave de idempotencia garantiza que un mismo lote no se procese dos veces, pero no impide que un nodo, por error de configuración o reinicio inesperado, genere *dos lotes distintos* para el mismo mes (con contenido ligeramente diferente) y los envíe ambos. Sus firmas serán distintas, por lo que el servidor los consideraría dos meses distintos y crearía entidades duplicadas o inconsistentes.

Conviene añadir una restricción: **cada nodo emite exactamente un batch por periodo de facturación**. Si se intenta ingerir un segundo batch distinto para el mismo `(node_id, period)`, el sistema debe rechazarlo con un error explícito (usando el nodo `Episode` como testigo). La lógica actual ya contiene `MERGE (e:Episode {period, node_id, installation})` — eso impide duplicar el episodio, pero no impide que el segundo lote intente añadir relaciones OBSERVED_IN adicionales desde entidades existentes. Haría falta un candado por periodo: *“si Episode ya existe y el batch entrante tiene distinta signature, rechazar con conflicto”*. Es un detalle de implementación, pero que protege la coherencia.

### 4. Escalabilidad de la ingesta a largo plazo (advertencia)

Controlado el volumen para el alcance FEDER. No obstante, si el sistema escala a cientos de instalaciones, la ingesta mensual concurrente de grandes lotes con múltiples `MERGE` individuales puede generar contención en el líder de Neo4j. La recomendación anterior de particionar por instalación (vía bases de datos virtuales en Neo4j 4.4+ o Aura) sigue siendo válida y encaja con la soberanía de datos: cada instalación podría tener su propia base de datos lógica, y los análisis cross-instalación se harían con consultas federadas o cubos OLAP. No es necesario ahora, pero una nota marginal ayudaría a los futuros mantenedores.

## Veredicto

La versión 3 es **técnicamente consistente, jurídicamente prudente y operativamente clara**. Las decisiones D2-D8 forman un núcleo sólido que resuelve los problemas distribuidos más espinosos (identidad, orden, idempotencia) sin sobrecargar el diseño. Las deudas y la pregunta abierta reflejan madurez en la gestión de riesgos.

**Dictamen: Aprobado para pasar a la fase de implementación de los pasos 1-5, con la recomendación de incorporar el almacenamiento de batches crudos (punto 1) y la detección de omisión de lotes (punto 2) en el diseño detallado del pipeline de ingesta.**

Quedo a disposición para el análisis de los esquemas Parquet cuando se validen contra los CSVs reales.