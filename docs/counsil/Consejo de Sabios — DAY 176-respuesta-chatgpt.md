### Resumen ejecutivo

El avance del DAY 176 es sólido. Habéis cerrado una pieza importante: convertir `community_id` en una feature presente también en el camino sintético y hacerlo reutilizando exactamente la misma implementación que producción. Eso elimina una clase entera de falsos positivos de CI por divergencia de cálculo.

Sin embargo, la deuda más importante que veo no es `node_id`. Es el **gap 50 → 42**. Mientras no sepáis exactamente dónde desaparecen esos 8 eventos, el bronce sintético no puede considerarse una base fiable para tests deterministas.

---

# Q1 — node_id sintético

Mi voto es:

**Modo isomorfo:** `synth-node-00` (configurable por env var)

**Modo mock:** `synth:node:<n>`

No leería el `config.json` real.

### Motivos

La opción (b) introduce un acoplamiento innecesario:

* El injector deja de ser autónomo.
* Los tests dependen de configuración local.
* Dos desarrolladores pueden ejecutar exactamente el mismo test y obtener distintos `flow_uid`.

La propiedad más valiosa de un injector es:

> "misma entrada → mismo resultado"

no

> "parecerse al despliegue real"

Para eso ya existe el sniffer real.

Además, dado que el `flow_uid` futuro depende de:

```
hash(node_id || community_id || flow_start_window)
```

queréis que el `node_id` sintético sea:

* explícito
* reconocible
* imposible de confundir con producción

Por tanto:

```text
isomorphic:
  synth-node-00

mock:
  synth:node:00
```

me parece el equilibrio correcto.

---

# Q2 — gap de filas

Esto es lo que perseguiría primero.

No mañana.

**Inmediatamente.**

Porque hay una inconsistencia lógica:

```text
received = 50
processed = 50
bronze = 42
```

Eso significa que la pérdida ocurre después de procesar.

Si los números son correctos, el espacio de búsqueda es pequeño.

---

## Sospechoso 1 — CorrelationWriter threshold

Es el primer candidato.

Preguntas:

* ¿Existe batching?
* ¿Existe flush diferido?
* ¿Existe cierre ordenado del proceso tras el último evento?
* ¿Existe temporizador de vaciado?

He visto muchas veces:

```cpp
49 eventos escritos
1 evento en buffer
proceso termina
evento perdido
```

pero aquí faltan 8.

---

## Sospechoso 2 — ZMQ dontwait

Segundo candidato.

Si existe:

```cpp
publisher_.send(..., zmq::send_flags::dontwait)
```

entonces debéis comprobar SIEMPRE el retorno.

Algo parecido a:

```cpp
auto ok = publisher_.send(...);

if (!ok)
{
    dropped_messages++;
}
```

Si actualmente no estáis contabilizando los fallos de envío, podéis estar perdiendo eventos silenciosamente.

---

## Sospechoso 3 — Shutdown race

También lo he visto muchas veces.

Patrón:

```text
injector envía 50
injector termina
consumer aún tiene eventos pendientes
proceso receptor cierra
buffer parcial
```

Los síntomas encajan bastante bien.

---

## Sospechoso 4 — filtro interno

Yo revisaría cualquier condición tipo:

```cpp
if (score < threshold)
    return;
```

o

```cpp
if (!community_id.empty())
```

aunque el modo mock ya reduce bastante esta probabilidad.

---

## Qué haría mañana

Instrumentación.

Nada de hipótesis.

Añadir contadores exactos:

```text
events_generated
events_sent
events_send_failed
events_received
events_processed
events_written
```

y emitirlos todos al final.

En cuanto aparezca el primer contador divergente tendréis localizado el problema.

---

# Q3 — orden DAY 177

Mi recomendación:

1. (B) col 17 → string
2. gap de filas
3. node_id

### Razón

El cambio de col 17 es:

* pequeño
* acotado
* decisión ya tomada
* rompe compatibilidad igualmente

El coste de hacerlo mañana o dentro de una semana es el mismo.

En cambio el gap es una investigación.

No bloquearía un cambio de contrato ya decidido por una investigación todavía abierta.

---

# Q4 — prueba de estrés del CorrelationWriter

Sí.

Pero después de resolver el gap.

Porque ahora mismo ya tenéis evidencia de posible pérdida.

No tiene sentido medir:

```text
10.000 eventos/s
```

si todavía no sabéis por qué desaparecen 8 de cada 50.

---

### Prueba que propondría

Algo del estilo:

```text
16 threads
100.000 filas
CSV único
verificar:

- número exacto de filas
- HMAC válido en todas
- ninguna línea truncada
- ninguna línea fusionada
```

Si pasa eso, el mutex está prácticamente validado.

---

# Q5 — community_id.cpp compartido

Mi opinión es que ya habéis cruzado el umbral donde merece librería propia.

Actualmente lo consumen:

* sniffer
* injector
* tests

Y mañana potencialmente:

* adaptador Suricata
* adaptador Zeek
* herramientas offline
* generadores de datasets

Cuando un componente tiene:

* múltiples consumidores
* contrato estable
* relevancia semántica alta

deja de ser implementación interna.

Pasa a ser infraestructura.

Visualmente lo vería así:

```text
libs/
 └── flow_identity/
      ├── include/
      │    └── community_id.hpp
      └── src/
           └── community_id.cpp
```

y todos los consumidores dependen de esa librería.

No lo considero urgente para DAY 177, pero sí una buena candidata para un ADR futuro.

---

# Mi orden de prioridad real

1. Cambiar col 17 a string.
2. Instrumentar y localizar exactamente el gap 50→42.
3. Introducir `node_id` sintético explícito.
4. Stress test del CorrelationWriter.
5. Extraer `community_id` a `libs/flow_identity`.

La única cuestión que considero potencialmente bloqueante para confiar en el bronce sintético de CI es el punto 2. Mientras exista una pérdida no explicada de eventos, cualquier test basado en conteos exactos queda en terreno inestable.
fdo
chatgpt