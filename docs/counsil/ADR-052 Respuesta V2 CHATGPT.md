# Veredicto de la v2

La v2 es significativamente más fuerte que la v1.

La diferencia más importante no es técnica sino conceptual: el nuevo §0 elimina una ambigüedad que aparecía constantemente en las discusiones previas.

Ahora existe una jerarquía clara:

```text
Producto
    ↓
Corpus
    ↓
Correlación
    ↓
Grafo
```

y no al revés.

Eso permite evaluar cada decisión preguntando:

> "¿mejora la calidad del corpus?"

que es una brújula arquitectónica mucho más estable que:

> "¿mejora la correlación?"

porque muchas optimizaciones de correlación destruyen evidencia valiosa para entrenamiento.

---

# Lo que considero ya cerrado

## §3.1.1 Codificación canónica

Muy buena incorporación.

Era un riesgo real.

He visto sistemas distribuidos donde:

```text
Go -> little endian
Python -> big endian
Java -> UTF16
```

generaban IDs distintos para el mismo evento durante años sin que nadie lo detectara.

Convertirlo en P0 es correcto.

---

## §3.1.2 node_id criptográfico

Ratifico completamente.

Un UUID aleatorio habría sido un error.

La derivación:

```text
node_id = SHA256(public_key)
```

aporta:

* unicidad
* verificabilidad
* trazabilidad
* compatibilidad futura con firmas

sin añadir estado.

Muy buena decisión.

---

## §3.6 confianza como señales primitivas

Ésta es probablemente la mejora conceptual más importante de la v2.

Estoy de acuerdo con abandonar:

```text
confidence=0.83
```

como dato persistido.

Los modelos futuros necesitarán:

```text
corroboration_count
nat_confidence
orphan_rate
host_anchor
```

no un resumen irreversible.

Es exactamente el mismo motivo por el que en ML se almacenan features y no predicciones.

---

## §3.7 procedencia separada de ground truth

Totalmente correcto.

La separación:

```text
provenance_suspected
```

vs

```text
provenance_ground_truth
```

es imprescindible.

Si no:

```text
detector -> etiqueta -> validación
```

forma un círculo cerrado.

La evaluación deja de ser científica.

---

# Respuesta a Q1

# Ratificación de §3.1.3

Mi respuesta:

**Sí.**

La identidad y la correlación deben permanecer separadas.

Dos sensores observando el mismo flujo deben producir:

```text
flow_uid_A
flow_uid_B
```

distintos.

y estar unidos mediante:

```text
FLOW_IDENTITY
```

o equivalente.

---

La consecuencia positiva es enorme:

cada observación conserva:

```text
latencia
sensor
posición topológica
calidad
```

propias.

Para el corpus eso es información útil.

Fusionarlas destruiría información.

---

Por tanto ratifico:

> El skew amenaza correlación, no identidad.

---

# Respuesta a Q2

# Diseño del mapa de cobertura

Aquí sí veo una decisión importante pendiente.

Mi recomendación:

## Modelo híbrido

No sólo grafo.

No sólo tabla.

---

Persistir:

```text
SensorCoverage
```

como tabla materializada.

Ejemplo:

```text
sensor_A
  VLAN10
  VLAN20

sensor_B
  DMZ

sensor_C
  WAN
```

---

y derivar desde ella:

```text
SENSOR_CAN_OBSERVE
```

en Neo4j.

---

Razón:

El motor necesita consultas rápidas:

```text
can sensor X see segment Y?
```

millones de veces.

Neo4j no es el mejor lugar para esa consulta crítica.

---

Mi propuesta:

```text
Autoridad:
    tabla

Visualización:
    grafo

```

---

# Respuesta a Q3

# Calibración de N

Aquí sigo teniendo reservas.

La propuesta actual:

```text
N = 60s
```

es razonable como default.

Pero me preocupa:

```text
UDP
DNS
QUIC
VoIP
```

porque pueden reutilizar 5-tuplas más agresivamente.

---

Yo mediría:

```text
reuse_interval
```

sobre:

* tráfico normal
* tráfico MITRE
* golden pcap

y obtendría:

```text
p1
p5
p50
```

---

Después elegir:

```text
N < p1
```

como ya sugerís.

---

No fijaría el valor en el ADR.

Lo dejaría:

```text
60s (LAB)
```

y explícitamente sujeto a evidencia.

---

# Respuesta a Q4

# trust_tier

Creo que faltan dos cosas.

Actualmente:

```text
CORROBORATED
SINGLE_SENSOR
ORPHAN
CONFLICT_NAT
```

es útil para queries.

---

Pero para ADR-040 yo añadiría:

```text
trust_score
```

derivado.

No persistido.

Calculado.

---

Ejemplo:

```text
trust_score ∈ [0,1]
```

obtenido desde:

```text
corroboration_count
nat_confidence
orphan_rate
host_anchor
coverage
```

---

No almacenado.

Recomputable.

---

Mi respuesta:

### Sí al enum.

### Sí también al score derivado.

---

# Respuesta a Q5

# provenance y acceptance_criteria

Ratificación completa.

No tocaría:

```text
DROP
CONFIG
POLICY
BUG
UNKNOWN
```

---

Son ejes distintos.

Tenéis:

```text
presencia
```

y

```text
procedencia
```

---

Un flujo puede ser simultáneamente:

```text
BUG
```

y

```text
INJECTED
```

sin contradicción.

---

Fusionarlos sería mezclar semánticas.

---

# Respuesta a Q6

# Fuente out-of-band para vector A

Aquí creo que el ADR aún es demasiado optimista.

La frase:

> "host comprometido → ARP puede mentir"

es correcta.

Pero no es el único problema.

También puede mentir:

* osquery
* Wazuh
* eBPF local
* tabla ARP

---

Por tanto:

si el host está comprometido:

```text
host plane
```

ya no es una fuente independiente.

---

Mi recomendación:

abrir deuda explícita.

Algo tipo:

```text
DEBT-OUTOFBAND-L2-001
```

---

Opciones:

* switch port-security
* DHCP snooping
* Dynamic ARP Inspection
* SPAN/TAP
* sensor dedicado

---

No para resolverlo ahora.

Pero sí para reconocer que la independencia observacional es un requisito futuro.

---

# Respuesta a Q7

# TCP/TLS en v2 o ADR-053

Mi recomendación:

ADR-053.

Razón:

ADR-052 ya tiene una responsabilidad muy clara:

```text
identidad
+
correlación
+
procedencia
```

---

Si añadís:

```text
TLS mismatch
TCP anomaly
JA3
JA4
```

el documento empieza a transformarse en:

```text
motor de detección MITM
```

que es otro problema.

---

Mantendría:

```text
ARP/NDP
```

porque son estructurales para el vector A.

---

Y movería:

```text
TCP
TLS
JA3
JA4
```

a ADR-053.

---

# Observación adicional (la más importante de esta revisión)

La v2 menciona varias veces:

```text
flow_uid
```

como identidad de flujo.

y al final añade:

> GPT: FlowObservation vs FlowIdentity
> opcional

Yo cambiaría ese estado.

Ya no lo veo opcional.

Lo veo como:

```text
DEBT-ARCH-FLOW-OBSERVATION-001
```

aunque sea P3.

---

Porque cuanto más leo el ADR, más claro queda que:

```text
flow_uid
```

identifica realmente:

```text
observación de flujo
```

no

```text
flujo lógico
```

---

Y eso no es una crítica.

De hecho me parece correcto.

Simplemente creo que merece quedar registrado explícitamente para evitar que dentro de un año alguien intente reutilizar `flow_uid` como identidad global de sesión.

---

# Conclusión

Si tuviera que votar hoy:

```text
ADR-052 v2
```

recibiría un:

```text
APROBADO CON OBSERVACIONES
```

Las únicas observaciones que considero relevantes antes de congelarlo son:

1. Formalizar el mapa de cobertura como autoridad materializada + representación en grafo.
2. Mantener `trust_score` derivado además del `trust_tier`.
3. Abrir una deuda explícita para observabilidad L2 out-of-band.
4. Promover `FlowObservation vs FlowIdentity` de nota opcional a deuda arquitectónica documentada.

Fuera de eso, la arquitectura ya parece coherente con la misión declarada del proyecto: construir un corpus reproducible, trazable y científicamente defendible para entrenar los modelos de aRGus++.
