# Veredicto general del Consejo

Mi valoración es que este ADR está bastante maduro técnicamente. La decisión principal —separar claramente **identidad**, **correlación** y **seguridad**— es correcta y evita uno de los errores más frecuentes en sistemas de observabilidad distribuidos: convertir un identificador de correlación en una identidad global.

Los puntos más fuertes son:

* Reconocer explícitamente que `community_id` es correlación y no identidad.
* Tratar el data-plane como hostil.
* Introducir `node_id` como parte de la identidad.
* Formalizar NAT como un problema de correlación con niveles de confianza.
* Insistir en etiquetar tráfico sospechoso en vez de eliminarlo del dataset.
* Vincular el problema a validación científica (MITRE/ground truth) y no solo a ingeniería.

Los puntos más débiles son:

* `flow_start_window` aún está insuficientemente definido.
* Falta distinguir entre identidad lógica de flujo y observación de flujo.
* El modelo de confianza necesita formalización matemática mínima.
* El control de cardinalidad debe diseñarse cuidadosamente para no convertirse en una herramienta de evasión.

---

# Observación importante: ¿Qué es realmente un Flow?

Aquí veo la principal cuestión arquitectónica pendiente.

Actualmente:

```text
flow_uid =
hash(node_id || community_id || flow_start_window)
```

resuelve unicidad.

Pero realmente identifica:

> "la observación de un flujo por un sensor"

no necesariamente

> "el flujo real"

En grafos distribuidos suele existir una separación:

```text
FlowIdentity
    ^
    |
observed_as
    |
FlowObservation
```

Ejemplo:

```text
FlowIdentity
    community_id=XYZ

FlowObservation
    sensor=A
    first_seen=...

FlowObservation
    sensor=B
    first_seen=...
```

Esto permite:

* múltiples sensores observando el mismo flujo
* múltiples niveles de confianza
* reconstrucción temporal posterior

Mi recomendación:

No usar `flow_uid` como identidad absoluta del flujo.

Usarlo como:

```text
flow_observation_uid
```

y reservar la posibilidad futura de introducir:

```text
logical_flow_uid
```

si el sistema madura.

No es obligatorio ahora.

Pero sí dejarlo documentado.

---

# Pregunta 1 — Rate limiting de community_id

## No hacerlo en Neo4j

Descartaría:

```text
Neo4j
```

porque el daño ya ocurrió.

El grafo ya recibió la explosión de cardinalidad.

---

## Mejor ubicación

### Nivel 1: sensor

Detecta:

```text
new_cid_rate
```

por ventana.

Genera telemetría.

NO bloquea.

---

### Nivel 2: correlation-engine

Aplica:

```text
soft quota
```

y marca:

```text
GRAPH_FLOOD_SUSPECT
```

---

### Nivel 3: ingest

Última línea de defensa.

Puede:

```text
sample
```

o

```text
degrade priority
```

pero jamás eliminar evidencia.

---

## Métrica sugerida

No usar valor fijo.

Usar desviación respecto al baseline.

Por ejemplo:

```text
current_rate >
10 × p95_historical_rate
```

por nodo.

Mucho más robusto.

---

# Pregunta 2 — ARP/NDP

Mi respuesta es clara:

**primera clase.**

No enriquecimiento.

Razón:

El ADR reconoce que:

> vector A es invisible para network telemetry.

Entonces ARP/NDP deja de ser accesorio.

Se convierte en sensor primario.

Yo introduciría:

```text
:NeighborBinding
```

o

```text
:ARPObservation
```

como entidad explícita.

---

# Pregunta 3 — Confianza de flujo

Sí.

Muy recomendable.

No binaria.

Escalar.

Ejemplo:

```text
confidence = 0..100
```

Factores:

* sensores coincidentes
* host corroborado
* NAT confirmado
* orfandad
* anomalías temporales

---

## Evitar

```text
trusted=true
```

porque envejece mal.

---

# Pregunta 4 — Etiquetado de inyección

Coincido completamente con el ADR.

No borrar.

No filtrar.

No excluir.

Etiquetar.

Añadiría:

```text
flow.labels = {
    INJECTED,
    MITM_SUSPECT,
    NAT_TRANSLATED,
    SINGLE_SENSOR,
    LOW_CONFIDENCE
}
```

Porque en investigación defensiva:

```text
datos malos
```

también son datos.

---

# Pregunta 5 — MITRE

Sí.

Yo incluiría Bettercap.

Por dos motivos:

1. Valida host↔red.
2. Valida ARP/NDP.

Si no se prueba Bettercap, nunca se valida realmente el vector A.

---

# Pregunta 6 — flow_start_window

Aquí está la decisión más delicada.

No usaría:

```text
bucket fijo de 30s
```

ni

```text
bucket fijo de 60s
```

porque fragmenta arbitrariamente.

---

## Mejor alternativa

Usar:

```text
flow_first_seen_timestamp
```

normalizado.

Ejemplo:

```text
epoch_ms(first_packet)
```

o

```text
epoch_us(first_packet)
```

según disponibilidad.

Entonces:

```text
flow_uid =
hash(
 node_id ||
 community_id ||
 first_seen
)
```

ya elimina la necesidad de buckets.

---

Si realmente queréis buckets:

```text
5 segundos
```

es probablemente el máximo razonable.

Nunca usaría una CrisisWindow entera.

---

# Pregunta 7 — ¿ADR único o dividir?

Mi recomendación:

Mantener juntos.

Porque P1 y P3 comparten una tesis común:

> La identidad no surge de la red sola.

La identidad surge de:

```text
red
+
host
+
tiempo
+
origen del sensor
```

Separarlos ahora probablemente produciría referencias cruzadas difíciles de mantener.

---

# Tareas accionables que veo salir de este ADR

## P0

### DEBT-NEO4J-FLOW-KEY-001

Implementar:

```text
flow_uid
node_id mandatory
constraint
```

antes de poblar Neo4j.

---

### FLOW-CONFIDENCE-001

Diseñar:

```text
confidence_score
```

0–100.

Definir factores.

---

### ARP-MONITOR-001

Recolector host-plane:

```text
ARP
NDP
neighbor cache
```

para Wazuh.

---

## P1

### GRAPH-FLOOD-GUARD-001

Métricas:

```text
new_cid_rate
cid_entropy
orphan_rate
```

por nodo.

---

### FLOW-LABELS-001

Taxonomía inicial:

```text
INJECTED
MITM_SUSPECT
LOW_CONFIDENCE
NAT_TRANSLATED
SINGLE_SENSOR
```

---

### HOSTNET-BRIDGE-001

Persistir:

```text
bridge_method
bridge_confidence
```

como propiedades obligatorias.

---

# Conclusión

La decisión fundamental del ADR me parece sólida: **`community_id` debe permanecer como mecanismo de correlación, jamás como identidad ni como control de seguridad.** Además, la insistencia en que la detección de MITM vive en la correlación multi-fuente (host + red) está alineada con cómo se diseñan los sistemas modernos de detección distribuida.

El único cambio arquitectónico que consideraría antes de ratificarlo es documentar explícitamente la diferencia entre:

```text
FlowIdentity
```

y

```text
FlowObservation
```

aunque inicialmente ambas acaben representadas por el mismo `flow_uid`.

Esa pequeña aclaración puede evitar una migración compleja dentro de uno o dos años, cuando aRGus++ empiece a correlacionar múltiples observaciones del mismo flujo a escala.

CHATGPT