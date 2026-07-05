Me pongo en el papel del Consejo, pero en su función crítica — la misma que ejercieron DeepSeek/GLM/Qwen contra el ADR-058 v2. No voy a ratificar la propuesta tal cual está escrita; voy a atacarla punto por punto, igual que le harían a cualquier propuesta nueva antes de dejarla pasar.

---

## Objeciones a la propuesta "Flujo B — parquet_to_kuzu_loader" (DAY 207)

### 1. La tabla de mapeo de columnas tiene un hueco silencioso — cols 18-20 desaparecen sin explicación

La tabla de la sección 4 salta de "0-4, 7-8, 11-13, 17" directamente a "21 (flow_uid)". **¿Y las columnas 18, 19 y 20?**

- **Col 18 = `hmac_row`**. No es parte de `CorrelationRecord` (el HMAC se valida y se descarta en `parse_and_verify`), así que no se reconstruye — correcto que no aparezca en el struct, pero la tabla debería decirlo explícitamente, no simplemente omitirlo. Un lector del documento (o del Consejo) puede interpretar el salto como un olvido, no como una decisión.
- **Cols 19-20 = `flow_start_window`, `seq_in_window`** (ya materializadas por Flujo A). La propuesta dice que `flow_uid` (col 21) "se usa directamente, sin recomputar" — pero **`sink.write(rec, flow_uid)` no acepta un `window` precomputado**. `KuzuGraphSink`/`cypher_builder.hpp::make_bindings` recalcula `window_micros(r.flow_start_sec, r.flow_start_nano)` internamente, ignorando cols 19-20 del Parquet por completo. Eso significa: **cols 19-20 se leen (si se leen) y no se usan para nada**, o simplemente no hace falta leerlas en absoluto.

**Pregunta real, no retórica:** si no se van a usar, ¿por qué el diseño dice "cols 0-21" como si las 22 columnas fueran insumo del loader? Esto no es cosmético — es una inconsistencia entre lo que el documento afirma ("usa flow_uid directamente sin recomputar") y lo que implícitamente admite que sí recomputa (`window`). Corregir la tabla y ser explícito: **cols 19-20 son redundantes para Flujo B tal como está diseñado; se leen solo si se quiere verificar cruzado contra el recálculo, no como fuente de verdad.**

### 2. Afirmación no verificada: "recompute == stored" para `flow_start_window`

Directamente relacionado con el punto 1. La propuesta asume que recalcular `window_micros` desde `flow_start_sec`/`flow_start_nano` (cols 5-6) dará el mismo valor que ya está materializado en col 19. Es determinista y debería ser cierto — pero **"debería" no es "medir, no votar"**. Si Flujo B no verifica esto contra el propio Parquet (por ejemplo, con un `assert`/log de discrepancia si `window_micros(rec) != col19_leída`), estás introduciendo la primera verificación cruzada real del predicado §3.1 sin aprovecharla. Es gratis tenerla — el dato ya está en el Parquet, solo hay que comparar.

**Objeción:** el diseño debería incluir esta comprobación cruzada como parte del loader, no descartarla.

### 3. Pregunta de arquitectura que la propuesta evita por completo: ¿Flujo B corre contra el MISMO Kuzu que Camino 0, o contra uno de test aislado?

Esto es más grave que los dos anteriores. Si Camino 0 y Flujo A+B **procesan el mismo segmento bronce en producción, contra el mismo Kuzu**, el `MERGE ... ON CREATE SET` (sin `ON MATCH`) hace que **el segundo escritor en llegar sea un no-op silencioso** — no falla, pero tampoco actualiza nada. Esto tiene dos lecturas posibles, y la propuesta no elige ninguna:

- **(a)** Si la intención es que ambos caminos coexistan en producción contra el mismo grafo (¿redundancia? ¿migración gradual?), el comportamiento MERGE-idempotente es correcto por diseño, pero **nadie lo ha dicho explícitamente** — y significa que el "test de equivalencia" nunca podría ejecutarse contra producción real, solo contra bases de datos Kuzu separadas y comparadas después.
- **(b)** Si la intención es que Flujo B corra **solo contra un Kuzu de test aislado** (para el propio test de equivalencia, no para producción), eso también hay que decirlo — porque cambia completamente el propósito de este componente: ¿es infraestructura de test, o es un camino de producción alternativo?

**Objeción de bloqueo real:** sin responder esto, no se puede evaluar si el diseño es correcto, porque el propósito del componente no está definido. Esto debería ser la primera pregunta al Consejo, no una nota al margen.

### 4. Sin plan de test para el propio loader

`bronze_to_gold_converter.cpp` tuvo un README, un smoke test previo, y ahora un test de equivalencia parcial verificado hoy. **Flujo B no tiene ningún test propuesto** — ni unitario ni de integración. Dado el patrón ya establecido (`test_bronze_to_kuzu_circuit.cpp` para Camino 0), lo mínimo exigible antes de escribir código de producción sería un test equivalente: escribir Parquet con el converter real → leer con el loader real → `MATCH` en Kuzu confirma nodos/aristas — mismo patrón, mismo espíritu "cero reimplementación en el test".

**Objeción:** la propuesta pide ratificación de un diseño sin comprometerse a cómo se prueba. Eso no debería pasar el gate.

### 5. Integridad del Parquet en sí — ¿se re-verifica algo al entrar a Flujo B, o se confía ciegamente?

El HMAC por fila ya se verificó cuando Flujo A leyó el bronce (`parse_and_verify`). Pero el propio ADR-058 v3 dice que el HMAC en el oro se reubicó como **"control de integridad bronce↔oro-ledger"** (`DEBT-GOLD-INTEGRITY-HMAC-001`) — es decir, se reconoce que hace falta verificar que el oro no se corrompió/manipuló *después* de escribirse. La propuesta no dice si Flujo B participa en esa verificación o si asume que el Parquet es confiable por el simple hecho de estar en el filesystem de gold.

**Pregunta sin responder:** ¿un atacante con acceso de escritura al directorio de gold (pero no al bronce) podría inyectar filas falsas que Flujo B escribiría a Kuzu sin detectarlo? Si la respuesta es "sí, pero es un problema de otra capa (permisos de filesystem, no de este componente)", hay que decirlo explícitamente como límite de responsabilidad, no dejarlo implícito.

### 6. El límite de "un solo chunk" está bien declarado — pero la verificación que lo sostiene es de una sola muestra

Este es el punto que la propuesta ya reconoce, pero vale la pena presionar más: **24 filas en un fichero es la única muestra medida.** No sabemos si `num_chunks() == 1` es un contrato garantizado por la API de Arrow 24.0.0-1 para cualquier fichero de un row-group, o si es simplemente lo que pasó a ocurrir con `row_group_size=1024` (el converter usa ese tamaño, y 24 < 1024, así que cabe entero en un row-group — probablemente por eso sale 1 chunk). Si algún día el converter procesa un segmento con más de 1024 filas (más eventos por rotación de 30s bajo carga real), **no tenemos evidencia de qué pasaría.**

**Objeción moderada, no bloqueante:** la propuesta debería decir esto con más precisión — no es "ficheros pequeños = 1 chunk" en general, es "ficheros con menos filas que `row_group_size` = previsiblemente 1 chunk, sin garantía documentada de la librería".

---

## Veredicto adversarial sobre las peticiones (a)-(d) del documento

- **(a) Componente lector-puro-reusa-sink:** ratificable en principio, pero **condicionado** a resolver el punto 3 (¿contra qué Kuzu corre?) antes de escribir código.
- **(b) Límite de un-solo-chunk:** **no ratificable tal cual** — exigiría o bien el bucle multi-chunk desde el primer commit (más seguro, poco coste extra), o una medición adicional con un segmento de >1024 filas antes de aceptar el límite como está.
- **(c) `ingested_at`/`seq_in_window` sin tratamiento especial:** ratificable — está bien fundamentado en la exclusión ya existente del predicado §3.1.
- **(d) Nombre/ubicación del componente:** no se puede decidir con seriedad hasta que (3) esté resuelto — el nombre y la ubicación dependen de si esto es infraestructura de test o un camino de producción.

**Recomendación:** no llevar esto al Consejo real todavía. Antes, resolver el punto 3 (arquitectura: ¿mismo Kuzu o aislado?) porque es la pregunta que determina si el resto del diseño tiene sentido, y decidir si el bucle multi-chunk se implementa ya (punto 6) en vez de diferirlo. Los puntos 1, 2, 4 y 5 son correcciones de precisión y alcance que cualquier revisor serio (Qwen/DeepSeek en el patrón que ya habéis visto) señalaría en la primera pasada.

¿Quieres que resolvamos primero la pregunta arquitectónica del punto 3 antes de tocar nada más del documento?

fdo

Claude