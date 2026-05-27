# Síntesis del Consejo de Sabios — DAY 164

## Q1 — `HttpEtcdRegistrar`: `etcd-cpp-apiv3` vs HTTP directo

### Recomendación mayoritaria: `etcd-cpp-apiv3`

Para el contexto concreto de aRGus NDR, el Consejo converge en que el coste operacional real ya fue pagado en el momento en que etcd entró en la arquitectura. Intentar “simplificar” evitando el cliente oficial desplaza complejidad hacia código custom crítico.

### Motivos técnicos

#### A favor de `etcd-cpp-apiv3`

* Watch gRPC ya resuelto y battle-tested.
* Lease keepalive robusto.
* Manejo correcto de revision numbers.
* Reconexión y stream semantics ya implementadas.
* Menor riesgo de edge cases sutiles:

    * pérdida silenciosa de eventos
    * desincronización tras reconnect
    * ABA temporal de epochs
    * race entre lease expiry y refresh
* Reduce deuda futura en FASE 5 (`AUTONOMOUS_EPOCH_STALE`).

### En contra de HTTP manual

El Consejo considera que “HTTP directo es más simple” es una simplificación engañosa.

El problema no es hacer `PUT`/`GET`.
El problema es implementar correctamente:

* watches persistentes
* retry semantics
* monotonic revisions
* reconnect coherente
* backpressure
* jitter
* timeout recovery
* split-brain temporal

Eso termina creando un “mini etcd client” interno, menos probado y más peligroso.

### Recomendación concreta

Arquitectura sugerida:

```text
IRegistrar
 ├── StubEtcdRegistrar
 └── HttpEtcdRegistrar
        └── etcd-cpp-apiv3 encapsulado internamente
```

No exponer tipos gRPC fuera del registrar.

El resto del sistema debe seguir viendo:

```cpp
watch()
put()
get()
lease()
keepalive()
```

sin conocer la implementación subyacente.

### Recomendación adicional

Aislar el cliente etcd en un único módulo compilable:

```text
common/etcd/
```

para evitar contaminación de includes gRPC en todo el árbol.

---

# Q2 — Watch: polling vs long-poll vs gRPC watch

## Recomendación: watch real (gRPC)

El Consejo considera que el polling de 1s “funciona”, pero no cumple el espíritu del diseño de coordinación distribuida que ADR-045 intenta construir.

## Razones

### Polling cada 1s introduce:

* latencia artificial
* sincronización en dientes de sierra
* wakeups innecesarios
* posibilidad de drift acumulado
* carga constante aunque no haya eventos

### El grace period de 10s NO justifica polling

El argumento importante no es el grace period.

El argumento importante es:

> “¿Queremos un sistema event-driven o un sistema de sondeo?”

ADR-045 ya eligió coordinación por epoch.
Eso naturalmente implica modelo orientado a eventos.

### gRPC watch aporta:

* propagación inmediata
* menor carga
* semántica natural
* ordering garantizado por revision
* mejor observabilidad
* menor complejidad conceptual en FASE 5

### Sobre long-poll HTTP

El Consejo lo considera el peor punto intermedio:

* conserva complejidad de reconnect
* sin ventajas reales frente a gRPC
* menos robusto
* más código manual

Conclusión:

| Opción         | Consejo                                    |
| -------------- | ------------------------------------------ |
| Polling        | Aceptable solo como fallback de emergencia |
| HTTP long-poll | No recomendado                             |
| gRPC watch     | Recomendación principal                    |

---

# Q3 — `CryptoEpochCoordinator`: hilo dedicado o loop compartido

## Recomendación mayoritaria: hilo dedicado encapsulado

### Razón principal

El coordinador representa una responsabilidad autónoma de infraestructura distribuida.

Acoplarlo al health loop:

```cpp
while(running) {
    health_check();
    coordinator.poll();
}
```

introduce:

* coupling temporal
* dependencia accidental del scheduler externo
* menor testabilidad
* más fragilidad evolutiva

## El Consejo considera especialmente importante:

### El coordinador NO es “health”.

Es:

* coordinación distribuida
* gestión criptográfica
* reacción a eventos
* transición de epoch

Son dominios distintos.

---

# Arquitectura recomendada

```text
CryptoEpochCoordinator
    ├── internal watch thread
    ├── callback on_epoch_change()
    ├── VaultProvider::refresh()
    ├── handle.reload()
    └── observability ACK
```

Con interfaz mínima:

```cpp
start()
stop()
current_epoch()
```

y threading completamente encapsulado.

---

# Objeción esperada: “más hilos”

El Consejo considera irrelevante el coste.

6 componentes × 1 hilo adicional:

* es trivial en footprint moderno
* muchísimo más barato que coupling arquitectónico
* más seguro operacionalmente

La prioridad aquí es:

```text
claridad > micro-optimización de hilos
```

---

# Recomendaciones adicionales del Consejo

## 1. Persistir `last_seen_revision`

Muy importante para reconnect seguro.

Sin revision tracking:

```text
disconnect → reconnect → evento perdido
```

Guardar:

```cpp
last_revision_seen
```

y reanudar watch desde ahí.

---

## 2. Definir comportamiento ante watch failure

Recomendado:

```text
WATCH_CONNECTED
WATCH_DEGRADED
WATCH_STALE
```

porque FASE 5 probablemente necesitará distinguir:

* pérdida temporal
* pérdida permanente
* epoch stale real

---

## 3. ACKs deben incluir timestamps monotónicos

No solo:

```json
{"ack":42}
```

sino:

```json
{
  "epoch": 42,
  "component": "vault_client",
  "ack_ts_monotonic_ns": ...
}
```

Esto facilitará análisis forense y debugging distribuido.

---

# Conclusión del Consejo

## Decisión recomendada

| Tema         | Recomendación             |
| ------------ | ------------------------- |
| Cliente etcd | `etcd-cpp-apiv3`          |
| Propagación  | gRPC watch real           |
| Coordinador  | hilo dedicado encapsulado |
| Polling      | solo fallback             |
| HTTP manual  | evitar                    |
| Arquitectura | event-driven real         |

La arquitectura actual ya cruzó el umbral donde “menos dependencias” equivale a “menos complejidad”.

A partir de DAY 164, el riesgo principal ya no es dependencia externa.

Es complejidad distribuida accidental escrita a mano.
