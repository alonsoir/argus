El Consejo considera que ADR-046 es probablemente la transición arquitectónica más importante del proyecto desde Variant B. El documento ya tiene una dirección muy sólida: la separación edge/servidor está bien razonada, el rechazo del join en edge es correcto, y la idea de usar Suricata como mecanismo de etiquetado automático es científicamente interesante.

Pero también aparecen varios puntos peligrosos que todavía no están suficientemente explicitados en la ADR. Algunos son técnicos; otros son epistemológicos: riesgo de creer que el enriquecimiento automáticamente mejora el sistema.

El análisis:

---

# 1. Riesgo principal no explicitado: explosión de complejidad operacional

La ADR habla mucho de:

* más señal
* mejor ground truth
* ensemble
* grafo

Pero aún no cuantifica suficientemente el coste operacional.

Estáis pasando de:

```text id="lvcv3d"
NDR autónomo ligero
```

a:

```text id="ggvq0g"
pipeline distribuido de observabilidad + correlación multi-fuente
```

Eso cambia radicalmente:

* superficie de fallo
* sincronización temporal
* mantenimiento
* tuning
* storage growth
* cardinalidad
* debugging

El Consejo recomienda añadir explícitamente una sección:

```text id="ojb5kp"
"Complejidad operacional incremental"
```

porque ahora:

* cualquier drift NTP rompe joins
* cualquier pérdida parcial rompe correlación
* cualquier skew temporal produce falsos negativos silenciosos

Esto debe quedar documentado como riesgo sistémico.

---

# 2. El join por 5-tupla ±500ms es más frágil de lo que parece

Ahora mismo:

```text id="avq16q"
(src_ip, dst_ip, src_port, dst_port, proto)
```

*

```text id="l7axlm"
±500ms
```

parece razonable.

Pero el Consejo detecta varios problemas.

---

## Problema A — NAT y proxies

En hospitales reales aparecerán:

* NAT masivo
* proxies HTTP
* balanceadores
* TLS termination
* middleboxes

Dos eventos distintos pueden compartir:

* misma 5-tupla
* misma ventana temporal

Especialmente con:

* DNS
* HTTP/2 multiplexado
* QUIC
* conexiones persistentes

---

## Problema B — relojes imperfectos

Aunque tengáis NTP:

* Zeek timestampa distinto
* Suricata timestampa distinto
* kernel capture introduce skew
* buffering cambia ordering

500ms puede:

* unir eventos incorrectos
* o perder correlaciones reales

---

# Recomendación importante

## La correlación debe tener “confidence score”

NO:

```text id="pnxbhu"
join binario
```

Sino:

```text id="6d9gfu"
correlation confidence
```

Ejemplo:

| Señal                    | Peso |
| ------------------------ | ---- |
| misma 5-tupla            | +0.5 |
| misma ventana temporal   | +0.3 |
| mismo JA3                | +0.1 |
| mismo dominio DNS previo | +0.1 |

Resultado:

```text id="5vkmwl"
correlation_score = 0.93
```

Eso os salvará muchísimo dolor futuro.

---

# 3. Riesgo científico importante: “label leakage”

Esta es probablemente la observación más importante del Consejo.

Ahora mismo el ADR asume:

```text id="1g6yk7"
Suricata alert -> etiqueta fiable
```

Pero cuidado.

Si entrenáis modelos usando:

* features Zeek
* features Suricata
* labels Suricata

podéis acabar entrenando:

```text id="i3w9lj"
"aprender las reglas ET indirectamente"
```

y no comportamiento real.

Eso produce:

* métricas artificialmente altas
* pobre generalización
* leakage oculto

---

# Recomendación muy importante

Separar explícitamente:

## A. Features de entrenamiento

vs

## B. Fuentes de etiquetado

Y documentar:

```text id="7d65rb"
Suricata-derived labels cannot be reused as direct model features in the same training sample without leakage controls.
```

Esto es importantísimo para publicación científica seria.

---

# 4. El grafo Neo4j puede explotar en cardinalidad

Ahora mismo el ADR trata el grafo como casi gratis.

No lo es.

---

## Problema real

Con:

* DNS
* TLS certs
* files
* processes
* flows

la cardinalidad crece brutalmente.

Especialmente:

* Domain
* File
* Certificate

---

# Riesgo oculto

Un hospital mediano puede generar:

* millones de nodos/día
* decenas de millones de relaciones

Neo4j empieza a sufrir muchísimo si:

* modeláis demasiado granular
* no hacéis TTL
* no agregáis

---

# Recomendación

La ADR necesita YA una política de retención:

## Ejemplo

| Tipo nodo           | TTL         |
| ------------------- | ----------- |
| Flow                | 7 días      |
| DNS                 | 30 días     |
| Certificate         | persistente |
| Process             | 7 días      |
| File hash malicioso | persistente |

Sin eso el grafo crecerá sin control.

---

# 5. Wazuh probablemente NO cabe inicialmente

El Consejo es bastante claro aquí.

## Prioridad correcta:

### Fase 1

* aRGus
* Suricata
* Zeek

---

### Fase 2

* Wazuh

Porque Wazuh:

* cambia completamente perfil RAM
* añade IO
* añade indexing
* añade host hooks
* añade complejidad operacional enorme

Y además:

* rompe parcialmente vuestra elegancia edge-lightweight

---

# Recomendación fuerte

Mover Wazuh explícitamente a:

```text id="t3v5qv"
P2 experimental enrichment
```

No P1 core.

---

# 6. El “sin Python” necesita matización

El Consejo entiende perfectamente la intención:

* consistencia
* rendimiento
* despliegue simple

Pero cuidado con convertirlo en dogma.

---

# Riesgo

Podéis terminar implementando:

* ETL
* parquet tooling
* feature engineering
* graph analytics

en C++20 donde el ecosistema Python está muchísimo más maduro.

---

# Recomendación

La ADR debería distinguir:

## Runtime production plane

→ C++20

## Research/training plane

→ Python permitido

Porque:

* pandas
* pyarrow
* scikit
* graph tooling

siguen dominando brutalmente el ecosistema científico.

No merece la pena luchar ideológicamente contra eso.

---

# 7. El descubrimiento “synthetic > academic” es MUY interesante

Pero aún insuficientemente demostrado.

El Consejo cree que esta puede ser una contribución real.

Pero ahora mismo la ADR mezcla:

* observación empírica
* hipótesis causal
* explicación teórica

como si fueran equivalentes.

No lo son.

---

# Problema científico

La afirmación:

```text id="h36rj8"
synthetic-only > mixed datasets
```

es extraordinaria.

Y requiere muchísimo rigor.

---

# Lo que falta

## 1. Curvas completas

No solo:

```text id="yg70jq"
0%, 50%, 100%
```

sino:

* 0
* 10
* 20
* 30
* ...
* 100

---

## 2. Múltiples seeds

---

## 3. Distintos modelos

---

## 4. Separación:

* train
* validation
* replay-runtime

---

## 5. Statistical significance

Ahora mismo la ADR habla casi como si ya fuera una ley establecida.

Todavía no.

---

# Recomendación fuerte

Cambiar lenguaje:

De:

```text id="2ft4rv"
"el único que funcionó"
```

A:

```text id="ohd7bk"
"in our experiments, synthetic-only datasets consistently outperformed mixed datasets under replay-runtime evaluation"
```

Mucho más sólido científicamente.

---

# 8. El `correlation-engine` necesita su propia filosofía

Ahora mismo parece:

* ETL
* joiner
* parquet producer

Pero realmente está evolucionando hacia:

```text id="g5d8c5"
distributed telemetry fusion engine
```

Eso merece ADR propia.

Porque aparecerán decisiones enormes:

* ordering guarantees
* late events
* replay
* idempotencia
* watermarking
* backpressure
* retention
* partial correlation

---

# 9. Atomic Red Team vs implementación propia

## Recomendación fuerte:

### Atomic Red Team externo

NO reinventar ATT&CK.

Vuestra innovación no está en:

* scripts ofensivos

sino en:

* correlación
* datasets
* autonomía
* aprendizaje federado

---

# 10. Observación estratégica importante

La ADR aún presenta aRGus++ como:

```text id="sk8xom"
más fuentes -> mejores modelos
```

Pero probablemente la verdadera contribución futura es otra:

```text id="iqhklm"
correlated multi-perspective behavioral security datasets
```

Eso es muchísimo más raro y científicamente interesante.

Muchos sistemas:

* detectan
* alertan

Muy pocos:

* generan datasets multi-capa coherentes y etiquetados temporalmente.

Ahí puede haber una contribución seria.

---

# Respuestas directas a las preguntas

## Q1 — Ventana ±500ms

Sí, configurable.

Y probablemente:

* adaptativa
* dependiente protocolo
* dependiente fuente

Más adelante incluso:

```text id="j5l0gx"
event-time watermarking
```

---

## Q2 — Suricata o Zeek primero

### Suricata primero

Porque:

* da labels inmediatos
* produce valor científico rápido
* permite validar correlación
* simplifica v1

---

## Q3 — Wazuh

### P2 clara

No meter aún.

---

## Q4 — correlation-engine mínimo viable

### v1:

* aRGus + Suricata
* join temporal
* parquet enriquecido

Eso ya es publicable y científicamente útil.

---

## Q5 — mitre-generator

### ADR propia

Porque:

* reproducibilidad
* ética
* seguridad
* orquestación
* manifests

merecen diseño independiente.

---

## Q6 — Experimento mezcla datasets

Si los datos existen:

### PRIORIDAD ALTA recuperarlos

Porque esa curva puede acabar siendo una de las partes más interesantes del paper.

Especialmente si el resultado resiste repetición rigurosa.
