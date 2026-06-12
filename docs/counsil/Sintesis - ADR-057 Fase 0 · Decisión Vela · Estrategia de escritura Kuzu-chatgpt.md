# Consejo — Segunda Pasada Adversarial sobre la Síntesis

La síntesis mejora mucho el ADR. Sin embargo, todavía veo tres puntos donde el Consejo corre el riesgo de declarar victoria demasiado pronto.

---

# Objeción S1 — Q4 no está tan resuelta como parece

La síntesis corrige correctamente la extrapolación lineal RSS→OOM.

Eso era una mala inferencia.

Pero ahora existe una nueva asunción no demostrada:

> "Si capamos `bufferPoolSize`, Q4 deja de ser bloqueante."

Eso tampoco está medido.

Porque el riesgo real no es OOM.

El riesgo real es:

```text
working_set > buffer_pool
```

↓

```text
page thrashing
```

↓

```text
reader latency explode
```

↓

```text
detección inútil
```

Un NDR puede sobrevivir a RSS estable.

No puede sobrevivir a consultas que pasan de 50 ms a 20 segundos.

### Experimento

No medir RSS.

Medir:

```text
reader_p99
writer_p99
page_faults
cache_hit_ratio
```

con:

```text
bufferPool = 256 MB
bufferPool = 512 MB
bufferPool = 1 GB
bufferPool = 2 GB
```

y:

```text
100k
500k
1M
5M
```

flows.

### Revisión

Movería Q4 desde:

```text
Hardening
```

a:

```text
Condicional
```

hasta medir thrashing.

---

# Objeción S2 — Falta un bloqueante de observabilidad

La síntesis añade backpressure.

Bien.

Pero sigue faltando una pregunta:

### ¿Cómo sabes que estás entrando en backpressure?

Un sistema crítico no puede depender de mirar logs.

Necesita señales.

### Invariantes operativos

Exportar:

```text
graph_writer_queue_depth
graph_writer_batch_age_ms
graph_writer_batch_size
graph_writer_flush_latency
graph_writer_retry_count
graph_writer_quarantine_size
```

### Experimento

Inducir:

```text
producer = 2x writer
```

y verificar:

```text
queue_depth sube
alert dispara
RSS permanece acotada
```

### Clasificación

**Bloqueante de producción.**

No del código.

De la operación.

Sin telemetría no sabrás que has entrado en degradación hasta que ya estés ciego.

---

# Objeción S3 — El mayor riesgo no es WAL, es ACK semántico

Q7 sigue estando formulada demasiado cerca del almacenamiento.

La pregunta correcta es:

> ¿Qué significa "committed" para el productor?

Ejemplo:

```text
Flow recibido
↓
Encolado
↓
ACK al productor
↓
Proceso muere
↓
Nunca llegó a Kuzu
```

El WAL está perfecto.

Y aun así has perdido datos.

### Experimento

Trazar:

```text
packet_id
queue_id
batch_id
tx_id
```

fin a fin.

Verificar:

```text
ACK emitido
    ⇒
visible tras recovery
```

siempre.

### Invariante

No:

```text
ACK cuando entra en cola
```

Sí:

```text
ACK cuando commit retorna
```

o bien:

```text
cola persistente antes del ACK
```

### Clasificación

**Bloqueante.**

Porque afecta a la semántica de durabilidad real.

---

# Lo mejor de la síntesis

Tres conclusiones me parecen especialmente sólidas:

### 1. Registry > Singleton

Es la solución correcta.

Resuelve simultáneamente:

* corrupción in-process
* evolución futura a shards
* ownership claro del `Database`

Es probablemente la decisión arquitectónica más limpia de todo ADR-057.

---

### 2. Separar Gate A y Gate B

Ésta es la corrección conceptual más importante.

Antes el debate mezclaba:

```text
schema
```

con

```text
producción
```

Ahora ya no.

Eso evita meses de discusiones inútiles.

---

### 3. Q10 Backpressure

Sigo pensando que es el agujero más peligroso.

La mayoría de sistemas no fallan porque el throughput medio sea insuficiente.

Fallen porque un pico de tráfico rompe una asunción implícita.

Y la asunción implícita aquí es:

```text
producer_rate <= consumer_rate
```

que nunca es cierta para siempre.

---

# Veredicto actualizado

Mantengo:

### Gate A (schema/ingest)

Aprobado.

No veo nada en la síntesis que justifique retrasarlo.

### Gate B (sink de producción)

No declararía production-ready hasta cerrar:

1. Q7 WAL + semántica de ACK.
2. Q5 poison batch.
3. Q9 DatabaseRegistry.
4. Q2 staleness.
5. Q3 reader real.
6. Q10 backpressure + métricas operativas.

Y rebajaría Q4 a:

```text
CONDICIONAL
```

hasta medir thrashing en lugar de RSS.

La síntesis ha convertido un ADR ambiguo en una lista concreta de experimentos. Eso es una mejora importante: ahora casi todas las discusiones restantes pueden resolverse con números en lugar de opiniones.

FDO

CHATGPT