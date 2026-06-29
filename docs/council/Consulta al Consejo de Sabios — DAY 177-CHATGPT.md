# Consejo de Sabios — Respuesta DAY 177

Asumiendo el papel de un consejo técnico compuesto por arquitectos de sistemas distribuidos, ingeniería de datos, detección de amenazas y fiabilidad operacional.

## Veredicto general del día

La conclusión principal es positiva: el hallazgo del `protocol_number` explica de forma convincente el síntoma de "bronce vacío" y además destapa una inconsistencia semántica real del injector (proto numérico y proto textual divergentes).

Lo importante no es que el fix haya producido 100% de `community_id`, sino que ha eliminado una fuente de aleatoriedad que estaba invalidando la prueba E2E.

La secuencia causal parece sólida:

```
protocol_number aleatorio
        ↓
community_id = nullopt
        ↓
hook descarta
        ↓
bronce vacío
```

La evidencia presentada encaja con el comportamiento esperado de Community ID.

---

# Ratificación de decisiones

## Q0-A. authoritative_source como string

### Ratificación: 8/8

La decisión es correcta.

El dato almacenado en bronce no es un valor de ejecución sino un artefacto de interoperabilidad.

Guardar:

```cpp
4
```

acopla el almacenamiento al orden interno del enum.

Guardar:

```cpp
DETECTOR_SOURCE_ML_PRIORITY
```

preserva significado semántico.

Además:

* permite inspección humana;
* evita migraciones si cambia la numeración protobuf;
* elimina dependencia protobuf en el reader.

La separación de capas sigue limpia:

```
protobuf
   ↓
serialization boundary
   ↓
correlation engine
```

No vemos ventaja significativa en rehidratar el enum dentro del engine.

---

## Q0-B. node_id fijo synth-node-00

### Ratificación: 8/8

Correcto para el modo actual.

El injector está modelando:

> "un único sensor observando muchos flujos"

No:

> "muchos sensores observando muchos flujos"

Por tanto:

```text
node_id constante
community_id variable
```

es exactamente lo esperado.

De hecho, introducir múltiples node_id sintéticos por defecto añadiría ruido innecesario.

La recomendación es:

```text
Modo actual:
  synth-node-00

Futuro:
  --multi-node N
```

cuando llegue ADR-054.

---

## Q1 — ROWGAP-001

Esta es la pregunta más importante.

### Opinión del Consejo

No aceptamos (d) como solución final.

Aceptamos (d) únicamente como explicación temporal.

---

### Razón

El injector es una herramienta de prueba.

Una herramienta de prueba debe ser más determinista que producción, no menos.

El objetivo del injector es responder:

> "¿ha funcionado el pipeline?"

No:

> "¿qué ha ocurrido esta vez?"

Si el injector introduce incertidumbre propia:

```text
eventos enviados ≠ eventos observados
```

entonces deja de ser un buen oracle de CI.

---

### Recomendación

#### Corto plazo

(a) + métrica por conjuntos

Comprobar:

```cpp
auto ok = publisher_.send(...);
```

y registrar fallo.

Mantener:

```text
sent_event_ids
vs
bronze_event_ids
```

como métrica oficial.

Ese cambio tiene valor incluso si luego se modifica el transporte.

---

#### Medio plazo

(b)

Para CI:

```cpp
send bloqueante
timeout corto
```

es preferible.

La latencia no importa.

La reproducibilidad sí.

---

#### Largo plazo

No vemos necesidad inmediata de abandonar PUSH/PULL.

El patrón no parece ser el problema principal.

El problema es:

```cpp
dontwait
+
ignorando return code
```

Eso elimina cualquier garantía observable.

---

### Veredicto

Convergencia estimada:

```
(a) Sí
(b) Sí
(c) No urgente
(d) No como solución final
```

---

# Reencuadre de ROWGAP

### Ratificación: 8/8

El reencuadre es acertado.

La deuda ya no parece ser:

```text
missing rows
```

sino:

```text
delivery semantics unknown
```

Ese es un framing mucho más preciso.

De hecho el nuevo nombre podría ser algo parecido a:

```text
DEBT-INJECTOR-DELIVERY-SEMANTICS-001
```

porque describe la causa, no el síntoma.

---

# Q2 — TCP/UDP 100% vs cobertura del descarte

La respuesta del Consejo es:

## Tener ambos modos

No mezclar objetivos.

### Modo CI

Determinista.

```text
100% TCP/UDP
100% community_id
```

El test valida correlación.

Nada más.

---

### Modo realista

Con ruido controlado.

Ejemplo:

```text
90% TCP/UDP
5% ICMP
5% otros
```

El test valida:

* correlación;
* descarte;
* robustez.

---

Intentar que un único escenario haga ambas cosas suele degradar las dos.

Por ello proponemos:

```text
--profile deterministic
--profile realistic
```

o equivalente.

### Veredicto

8/8 a favor de dos perfiles.

---

# Q3 — ¿Debe entrar en ADR-055?

### Sí.

Todo lo descrito hoy pertenece al dominio del injector.

Los tres hallazgos son reglas de comportamiento del injector:

1. node_id sintético.
2. coherencia protocol_number/protocol_name.
3. semántica de entrega.

Por tanto ADR-055 parece el lugar natural.

---

### Excepción

Si la investigación futura descubre un problema genérico de mensajería ZeroMQ que afecte:

* injector,
* sniffer,
* ml-detector,
* correlation-engine,

entonces sí justificaría ADR propio.

Con la evidencia actual no parece el caso.

---

# Q4 — ¿Nueva deuda para el bug de proto?

### No.

El Consejo lo considera:

```text
bug funcional descubierto durante la implementación
```

no deuda arquitectónica.

La deuda ya existía implícitamente:

```text
A = poblar community_id
```

Simplemente se encontró la causa raíz.

No vemos valor en crear:

```text
DEBT-INJECTOR-PROTO-001
```

para algo ya corregido.

---

# Q5 — Divergence propagándose a bronce

Observación importante.

Hoy sólo sabemos que:

```text
bronze preserva authoritative_source
```

Lo cual es correcto.

La recomendación es no fijar aún comportamiento gold.

---

Lo único que sugerimos registrar para ADR futuro es esta regla:

> La procedencia de una decisión nunca debe perderse durante una transformación de datos.

Es decir:

```text
DETECTOR_SOURCE_ML_PRIORITY
```

y

```text
DETECTOR_SOURCE_DIVERGENCE
```

deben llegar íntegros al consumidor final.

Qué haga Gold con ellos es una decisión posterior.

Pero la trazabilidad debe mantenerse extremo a extremo.

---

# Resumen ejecutivo

| Tema                                   | Veredicto                                |
| -------------------------------------- | ---------------------------------------- |
| authoritative_source string            | Ratificado                               |
| reader sin protobuf                    | Ratificado                               |
| synth-node-00 fijo                     | Ratificado                               |
| Reencuadre ROWGAP → delivery semantics | Ratificado                               |
| Solución ROWGAP                        | (a)+(b), no confiar en (d)               |
| PUSH/PULL                              | Mantener por ahora                       |
| Benigno TCP/UDP 100%                   | Sí para CI                               |
| Cobertura de descartes                 | Perfil separado                          |
| ADR-055                                | Debe absorber los hallazgos              |
| Nueva deuda para proto                 | No necesaria                             |
| Divergence hacia Gold                  | Mantener trazabilidad, decidir más tarde |

La observación más valiosa del día no es el fix de `community_id`; es el cambio de diagnóstico de ROWGAP. Pasar de "faltan filas" a "las garantías de entrega son desconocidas" transforma una anomalía difícil de perseguir en una hipótesis verificable mediante conjuntos `{enviado}` vs `{observado}`. Ese reencuadre reduce significativamente el espacio de búsqueda para los próximos días.
FDO
CHATGPT