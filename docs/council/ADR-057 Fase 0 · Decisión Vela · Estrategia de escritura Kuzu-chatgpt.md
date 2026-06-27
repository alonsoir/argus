# Consejo de Sabios — Revisión Adversarial ADR-057

Voy a asumir el papel de un arquitecto de sistemas distribuidos paranoico cuya misión es demostrar que D1-D4 son falsos.

---

# Q1 — ¿El ×61 transfiere o es un artefacto de la VM?

### Objeción

No has demostrado que el cuello de botella de run1 sea el parser/planner de Kuzu. Podría ser simplemente que VirtualBox esté amplificando brutalmente el coste de `fsync`.

Si es así, el ×61 es una ilusión experimental.

### Experimento

Separar explícitamente:

**A. Coste de transacción**

```text
BEGIN;
COMMIT;
```

100.000 veces.

**B. Coste de query**

```text
MERGE ...
```

dentro de una única transacción larga.

**C. Coste total actual**

```text
BEGIN;
MERGE ...
COMMIT;
```

por fila.

Métrica:

```text
Tquery
Ttx
Ttotal
```

Si:

```text
Tquery >> Ttx
```

el ×61 es estructural.

Si:

```text
Ttx ≈ Ttotal
```

el ×61 depende de almacenamiento.

### Número objetivo

Quiero:

```text
Tquery/Ttx
```

en:

* VirtualBox
* N100
* RPi5

Si la razón cambia menos de 20%, el resultado transfiere.

### Veredicto

**Bloqueante.**

Porque D2 depende directamente de ello.

---

# Q2 — Staleness a bajo caudal

### Objeción

El benchmark sólo mide régimen saturado.

Un NDR no detecta ataques durante una tormenta permanente.

Detecta ataques durante horas aburridas.

### Experimento

Medir:

```text
flush(size=1000,time=x)
```

con:

```text
1 flow/s
3 flows/s
10 flows/s
100 flows/s
```

y calcular:

```text
event_time → query_visible_time
```

p50/p95/p99.

### Mi propuesta

No aceptaría:

```text
staleness_p99 > 2s
```

para correlación activa.

Por tanto:

```text
flush_interval = 1000 ms
```

es el punto de partida.

El tamaño queda subordinado al tiempo:

```text
flush(batch_size >= 1000)
OR
flush(age >= 1000ms)
```

### Veredicto

**Bloqueante.**

Porque afecta directamente a la capacidad de detección.

---

# Q3 — Reader de juguete

### Objeción

`count(*)` no representa el workload real.

Representa el mejor caso imaginable.

### Query representativa

Yo metería algo parecido a:

```cypher
MATCH
    (src:Host)-[:FLOW]->(f1:Flow)
        -[:CONNECTED_TO]->(f2:Flow)
        -[:CONNECTED_TO]->(f3:Flow)
WHERE
    src.community_id = $community
RETURN count(*)
```

o la traversal real que use el motor de correlación.

### Experimento

Repetir run2 y run3 con:

```text
Traversal 3-hop
Traversal 5-hop
```

Medir:

```text
reader_p50
reader_p95
reader_p99
```

bajo ingestión.

### Criterio

Aceptable:

```text
reader_p99 < 5x idle
```

No aceptable:

```text
reader_p99 > 10x idle
```

### Veredicto

**Bloqueante.**

Porque toda la tesis de Kuzu depende de consultas de grafo.

---

# Q4 — Memoria

### Objeción

Éste es probablemente el verdadero cuello de botella.

No la escritura.

### Experimento

Medir:

```text
100k
500k
1M
5M
10M
```

nodos.

Métricas:

```text
RSS
page faults
cache hit ratio
reader latency
```

### Número objetivo

Quiero la pendiente:

```text
dRSS/dNodo
```

no snapshots.

Porque eso permite extrapolar.

### Riesgo

Si ves algo cercano a:

```text
8 bytes → 80 bytes → 800 bytes
```

por entidad almacenada, la historia cambia completamente.

### Tiering

Yo impondría:

```text
Hot graph:
últimos 7 días

Warm:
Parquet

Cold:
Parquet + DuckDB
```

No porque hoy haga falta.

Porque Kuzu carece de índices temporales de rango suficientemente ricos para ser tu almacén histórico infinito.

### Veredicto

**Bloqueante.**

Porque puede invalidar ADR-041 completo.

---

# Q5 — Flow envenenado

### Objeción

Si una fila rompe una transacción de 1000 elementos, has creado un amplificador de fallo ×1000.

### Experimento

Inyectar:

```text
999 válidas
1 corrupta
```

en posiciones:

```text
1
500
1000
```

y medir resultado.

### Si hay rollback total

Aplicar estrategia:

```text
Batch
 ↓
Fail
 ↓
Binary split
 ↓
Identificar fila tóxica
 ↓
Quarantine queue
```

Complejidad:

```text
O(log n)
```

aislamiento.

### Número objetivo

```text
999 válidas sobreviven
1 inválida aislada
```

### Veredicto

**Bloqueante.**

Porque el tráfico es hostil por definición.

---

# Q6 — Batch=1000 es magia negra

### Objeción

No existe evidencia de optimalidad.

### Experimento

Barrido:

```text
1
10
100
500
1000
2500
5000
10000
```

Medir simultáneamente:

```text
throughput
RSS
staleness
rollback blast radius
```

### Lo que espero

Una curva tipo:

```text
1      -> muy malo
10     -> enorme mejora
100    -> enorme mejora
500    -> mejora moderada
1000   -> pequeña mejora
5000   -> saturación
10000  -> empeora
```

Si ocurre eso, el óptimo operativo probablemente será:

```text
500
```

y no:

```text
1000
```

### Veredicto

**Bloqueante.**

Porque D1 depende explícitamente de ese parámetro.

---

# Q7 — WAL

### Objeción

La mayor bandera roja del documento.

Borrar WAL es exactamente lo contrario de validar durabilidad.

### Experimento

Loop:

```text
writer activo
↓
SIGKILL aleatorio
↓
reopen
↓
recovery
↓
verificar commits
```

1000 iteraciones.

### Métrica

```text
committed_before_kill
==
visible_after_recovery
```

### Número objetivo

```text
0 pérdidas
```

No:

```text
99.9%
```

No:

```text
casi siempre
```

Cero.

### Veredicto

**Bloqueante crítico.**

Si esto falla, el ADR entero queda suspendido.

---

# Q8 — Sharding

### Objeción

Ésta es la pregunta más estratégica del documento.

No se trata de implementar sharding.

Se trata de no impedirlo.

### Invariante mínimo

Todo write debe portar:

```text
tenant_id
community_id
shard_key
```

aunque hoy siempre resuelvan a:

```text
shard=0
```

Además:

```text
QueryPlanner
```

no debe asumir:

```text
single graph
```

internamente.

### Test

Simular:

```text
Shard0
Shard1
Shard2
```

aunque todos apunten al mismo Kuzu.

Verificar que el routing existe.

### Veredicto

**Hardening previo a ADR-041.**

No bloquea Fase 0.

Pero debe entrar antes de crecimiento real.

---

# Q9 — Footgun Database

### Objeción

Una deuda documentada no es una mitigación.

### Solución

No singleton.

Los singletons acaban rompiéndose.

Prefiero:

```cpp
DatabaseRegistry
```

con:

```cpp
std::unordered_map<path, weak_ptr<Database>>
```

y:

```cpp
acquire(path)
```

como único punto de creación.

### Test obligatorio

```cpp
acquire("/data")
acquire("/data")
```

debe devolver exactamente el mismo objeto.

Y:

```cpp
Database(...)
```

debe ser imposible fuera del registry.

### Invariante

```text
1 path
=
1 Database
```

siempre.

### Veredicto

**Bloqueante.**

Porque ya has demostrado corrupción potencial.

---

# Agujero que veo y no aparece en las preguntas

### Backpressure

El ADR asume implícitamente:

```text
producer_rate <= writer_rate
```

¿Qué ocurre cuando:

```text
50k eventos/s
```

entran durante 20 minutos y el writer sólo absorbe:

```text
10k/s
```

?

Necesitas una respuesta medible para:

```text
cola llena
```

porque en producción ocurrirá.

Experimento:

```text
producer = 2× writer
```

durante:

```text
30 min
```

Medir:

```text
RSS
queue depth
event loss
staleness
```

Invariante que exigiría:

```text
RSS acotada
```

y

```text
backpressure explícita
```

sin crecimiento infinito.

### Clasificación

**Bloqueante.**

Porque una arquitectura con throughput alto pero sin backpressure es estable únicamente mientras todo va bien. Y los sistemas críticos se diseñan para cuando no va bien.

FDO

ChatGPT