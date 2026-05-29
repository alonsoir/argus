# Consejo de Sabios — Respuesta Técnica Consolidada

## Integración multi-motor aRGus / Suricata / Zeek / Wazuh

**DAY 169 — Pasada de arquitectura previa a contrato wire**

El escrito identifica correctamente el verdadero punto crítico: el problema no es “correlacionar cuatro motores”, sino reconciliar **dos ontologías distintas de observabilidad**:

* sensores de flujo/red (aRGus, Suricata, Zeek),
* sensores de estado/host (Wazuh).

El Consejo coincide en que intentar forzar ambos mundos sobre una PK puramente flow-centric produciría deuda estructural temprana.

---

# Dictamen General del Consejo

## Veredicto principal

El Consejo recomienda por consenso técnico:

1. **NO usar `community_id` como PK única global.**
2. Adoptar un modelo dual:

    * `community_id` → identidad de flujo.
    * `host_key` → identidad de host.
3. Tratar el correlation-engine como un **grafo temporal heterogéneo**, no como un simple agregador keyed por flujo.
4. Mantener el contrato wire (`network_security.proto`) minimalista y extensible antes de FEDER.
5. Separar explícitamente:

    * correlación determinista,
    * enriquecimiento contextual,
    * inferencia de crisis.

El Consejo considera que esta decisión evita una reescritura completa futura del engine.

---

# Respuestas por pregunta

---

# Q1 — ¿PK única o modelo dual?

## Decisión del Consejo

**Modelo dual obligatorio.**

### Motivo

`community_id` resuelve perfectamente:

* equivalencia de flujo,
* correlación cross-engine de red,
* deduplicación flow-centric,
* alineación temporal de sensores pasivos.

Pero NO puede representar:

* FIM,
* procesos,
* autenticación,
* integridad,
* SCA,
* rootcheck,
* actividad de usuario,
* estado del endpoint.

Eso no es una limitación accidental.
Es una diferencia semántica fundamental.

---

## Recomendación formal

### Identidades primarias independientes

```text
FLOW DOMAIN
-----------
community_id

HOST DOMAIN
-----------
host_key
```

---

## Recomendación crítica

NO intentar derivar `host_key` desde `community_id`.

El puente debe ser:

```text
community_id
    ↕
(flow endpoints)
    ↕
host inventory
    ↕
host_key
```

No al revés.

---

# Q2 — ¿Modelo de grafo?

## Decisión del Consejo

Sí. Grafo temporal multi-arista.

---

## Tipos mínimos de arista

### A. Flow Identity Edge

```text
(event) --[SAME_FLOW]--> (community_id)
```

---

### B. Host Locality Edge

```text
(event) --[HOST_ACTIVITY]--> (host_key)
```

---

### C. Temporal Correlation Edge

```text
(flow_event) --[TEMPORALLY_ASSOCIATED]--> (host_event)
```

condicionada por:

* ventana temporal,
* endpoint interno reconocido,
* dirección del flujo,
* contexto del motor.

---

## Observación importante

La correlación host↔flujo NO es equivalencia.

Es:

* contextual,
* probabilística,
* temporal,
* direccional.

Eso cambia completamente cómo debe pensarse el engine.

---

# Q3 — Semántica de “fuente esperada”

## Decisión del Consejo

La opción correcta es:

> (b) “esperada” = fuentes cuyo dominio aplica a la clave de la crisis.

Coincidencia con Claude.

---

## Modelo recomendado

### Crisis flow-centric

Esperan:

* aRGus,
* Suricata,
* Zeek.

Wazuh solo si:

* existe endpoint interno gestionado,
* y hay actividad host correlacionable.

---

### Crisis host-centric

Esperan:

* Wazuh,
* y opcionalmente sensores de red asociados al host.

---

## Regla crítica

Las fuentes esperadas deben calcularse dinámicamente.

Nunca:

```text
expected_sources = ALL_SOURCES
```

Eso convertiría el sistema en un “distributed wait engine”.

---

## Recomendación adicional

Separar:

```text
correlation_window
late_arrival_window
```

No usar un único timeout para ambos problemas.

---

# Q4 — ¿Wazuh debe ingerir `eve.json`?

## Decisión del Consejo

Para FEDER: **NO.**

---

## Motivos

Evita:

* duplicados,
* eco semántico,
* severidad inflada,
* grafos contaminados,
* dependencia circular,
* deduplicación compleja.

---

## Arquitectura recomendada

```text
Suricata → adapter propio
Zeek      → adapter propio
Wazuh     → adapter propio
aRGus     → adapter propio
```

Todos convergen exclusivamente en el correlation-engine.

---

## Excepción futura

Wazuh podría ingerir logs de red:

* para dashboards,
* SIEM,
* archivado.

Pero NO como fuente primaria del engine de correlación.

---

# Q5 — Timestamp canónico

## Decisión del Consejo

Usar:

```text
event_time_utc
```

normalizado por adapter.

---

## Definición

Debe representar:

> “momento en que el motor afirma que ocurrió el evento”.

NO:

* ingest time,
* adapter receive time,
* Kafka publish time,
* DB insert time.

---

## Recomendación de envelope

```proto
message SecurityEvent {
  string source_engine;
  string native_event_id;

  optional string community_id;
  optional string host_key;

  google.protobuf.Timestamp event_time_utc;

  Severity severity;

  bytes raw_payload;
}
```

---

## Tolerancia temporal

Consejo:

| Entorno            | Drift máximo |
| ------------------ | ------------ |
| LAB FEDER          | ≤ 50 ms      |
| Producción pequeña | ≤ 250 ms     |
| Distribuido real   | ≤ 1 s        |

---

## Recomendación importante

NTP no basta.

Debe existir:

* monitorización continua,
* alerta de drift,
* invalidación de correlación si el drift excede tolerancia.

Porque el tiempo es parte de la corrección lógica del sistema.

---

# Q6 — Recursos y VMs

## Decisión del Consejo

Las 5 VMs simultáneas son viables en M2 Pro 32 GB, PERO:

* no con stack completo permanente,
* no con Elasticsearch sobredimensionado,
* no con retención pesada.

---

## Recomendación práctica FEDER

### Perfil ligero obligatorio

| Componente    | RAM objetivo |
| ------------- | ------------ |
| Wazuh manager | 3–4 GB       |
| Suricata      | 1 GB         |
| Zeek          | 1–2 GB       |
| aRGus         | 1 GB         |
| Gateway/infra | 1 GB         |

---

## Recomendación CI

Separar tiers:

### Tier A — determinista

* golden pcap,
* reproducible,
* rápido.

### Tier B — integración viva

* ataques reales,
* herramientas ofensivas,
* smoke tests.

No mezclar ambos.

---

# Q7 — Cota de crisis abiertas

## Decisión del Consejo

Debe existir límite duro.

No negociable.

---

## Recomendación inicial

```text
MAX_OPEN_CRISES = configurable
```

LAB inicial:

```text
10k–25k
```

---

## Política recomendada

### Estrategia

1. prioridad por severidad,
2. expiración LRU temporal,
3. degradación controlada,
4. jamás bloqueo global.

---

## Regla de oro ADR-047

En saturación:

```text
emitir parcial > bloquear
```

---

## Recomendación crítica

Instrumentar métricas desde DAY 1:

* crisis_open_total,
* evictions_total,
* late_arrivals_total,
* dropped_correlations_total,
* correlation_latency_ms.

---

# Q8 — Alcance protocolo

## Decisión del Consejo

Para FEDER:

| Protocolo | Estado    |
| --------- | --------- |
| TCP       | soportado |
| UDP       | soportado |
| SCTP      | soportado |
| ICMP      | diferido  |

---

## Recomendación formal

Firmar:

```text
DEBT-ARGUSPP-COMMUNITY-ID-ICMP-001
```

Explícitamente.

---

## Motivo

ICMP introduce:

* type/code mapping,
* pseudo-port semantics,
* edge cases,
* inconsistencias cross-engine.

No merece el riesgo pre-FEDER.

---

# Q9 — ¿Pipeline vivo o corpus reproducible?

## Respuesta más importante del Consejo

La prioridad FEDER debe ser:

# CORPUS REPRODUCIBLE Y ETIQUETADO

El pipeline vivo es demostración.
El corpus reproducible es ciencia.

---

## Motivo

Lo que realmente sobrevive auditoría técnica y académica es:

* reproducibilidad,
* trazabilidad,
* ground truth,
* datasets,
* determinismo,
* capacidad de repetir resultados.

---

## Consecuencia estratégica enorme

El orden de fases cambia.

---

# Orden recomendado por el Consejo

## PRIORIDAD 1

Golden corpus + pcaps deterministas.

---

## PRIORIDAD 2

Contrato wire estable.

---

## PRIORIDAD 3

Correlación determinista multi-engine.

---

## PRIORIDAD 4

Pipeline vivo.

---

## PRIORIDAD 5

Ataques realistas.

---

# Punto crítico detectado por el Consejo

El verdadero activo estratégico de aRGus no es:

> “correlacionar Suricata y Zeek”.

Eso ya existe en partes del mercado.

El activo diferencial es:

# Construir un corpus multi-engine correlacionado y reproducible

donde:

* cada flujo,
* cada alerta,
* cada host-event,
* cada crisis,

queden enlazados de forma verificable.

Eso tiene valor:

* científico,
* defensivo,
* de entrenamiento ML,
* forense,
* académico,
* operacional.

---

# Recomendación final del Consejo

## Antes de escribir el correlation-engine completo:

Cerrar YA:

1. `network_security.proto`
2. modelo dual (`community_id` + `host_key`)
3. timestamp canónico
4. semántica de “expected sources”
5. envelope común
6. política de deduplicación
7. golden corpus determinista

Porque todo lo demás dependerá de eso.

---

# Veredicto Final

El Consejo considera que el análisis presentado detecta correctamente el punto arquitectónico más peligroso antes de FEDER:

> confundir correlación de flujo con correlación de incidente.

Resolver esto ahora probablemente evita meses de deuda estructural posterior.
CHATGPT