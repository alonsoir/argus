# Consejo de Sabios — Revisión ADR-045 CryptoEpoch Coordination

## 1. Leslie Lamport — Coordinación temporal: `not_before` no es suficiente por sí solo

El diseño actual es correcto como base operacional, pero `not_before` implementa únicamente una **coordinación temporal débil**. Eso funciona si:

* todos los componentes tienen reloj estable,
* etcd watcher entrega eventos sin retraso,
* el reload tarda menos que el grace period,
* y no existen stalls internos.

En sistemas distribuidos reales, incluso en un solo nodo, esto no garantiza convergencia simultánea.

### Recomendación

Mantener `not_before`, pero añadir:

```text
/argus/crypto/epoch/current
/argus/crypto/epoch/pending
/argus/crypto/epoch/acks/<component_id>
```

Flujo recomendado:

1. etcd-server publica `pending_epoch`
2. Componentes descargan seed y preparan provider
3. Componentes escriben ACK READY
4. Cuando quorum READY alcanzado:

    * etcd-server promueve `current_epoch`
5. Todos activan epoch localmente

No hace falta 2PC completo.

Esto es más parecido a:

* staged rollout,
* barrier synchronization,
* distributed rendezvous.

Mucho más robusto que “todos cambian a T”.

### Punto importante

El ACK no debe significar:

> “ya cambié”

Debe significar:

> “puedo cambiar inmediatamente”.

Eso evita deadlocks parciales.

---

## 2. Martin Kleppmann — Grace period de 30s

Para 6 componentes en el mismo nodo:

* 30s es conservador,
* probablemente demasiado alto,
* pero seguro para FASE 2 inicial.

El verdadero problema no es el tiempo de propagación.

Es:

* reload de certificados,
* recreación de sockets,
* stalls internos,
* GC de shared_ptr antiguos,
* reconexión ZMQ.

### Recomendación

Mantener:

```yaml
grace_period_default: 30s
```

Pero permitir override por componente:

```yaml
crypto:
  transition_timeout: 10s
```

Porque:

* sniffer puede tolerar latencia,
* firewall probablemente no,
* dashboard sí,
* correlator quizá no.

### Consejo adicional

Separar:

```text
prepare_window
activation_window
dual_accept_window
```

Son conceptos distintos y terminarán creciendo independientemente.

---

## 3. Werner Vogels — Único escritor de `/argus/crypto/epoch`

El writer debe ser:

# `etcd-server`

No Jenkins.
No Vault agent.
No proceso CI/CD externo.

### Motivo arquitectónico

El epoch representa:

* estado runtime distribuido,
* no pipeline state.

Por tanto, el coordinador debe vivir:

* dentro del control plane de aRGus,
* cerca del runtime,
* cerca de la lógica de autonomía.

### Diseño recomendado

```text
Vault
  ↓
etcd-server
  ↓
componentes
```

Donde:

* Vault = source of secrets
* etcd-server = source of truth operacional

Eso evita:

* múltiples writers,
* race conditions,
* epochs huérfanos,
* CI/CD inconsistente con runtime.

### Recomendación crítica

Usar CAS/revision en etcd:

```text
compare-and-swap on epoch_id
```

para evitar rollback accidental de epochs.

---

## 4. Barbara Liskov — Split-brain y recovery

La transición de epoch es un estado operativo real.

Por tanto:

# Sí, necesitáis `EPOCH_TRANSITION`

La autonomy machine actual probablemente modela:

* HEALTHY
* DEGRADED
* ISOLATED
* etc.

Pero una transición criptográfica introduce propiedades únicas:

* dual trust,
* aceptación temporal de dos epochs,
* retries controlados,
* tolerancia parcial.

Eso merece estado explícito.

### Estado recomendado

```text
HEALTHY
  ↓
EPOCH_PREPARING
  ↓
EPOCH_TRANSITION
  ↓
HEALTHY
```

y fallbacks:

```text
EPOCH_TRANSITION
  ↓ timeout
DEGRADED_CRYPTO
```

### Muy importante

El split-brain no debe detectarse por:

> “socket muerto”

Eso es demasiado tarde.

Debe detectarse por:

```text
peer epoch mismatch
```

explícito.

---

## 5. Pieter Hintjens — Dual-key ZMQ y wire protocol

La respuesta corta:

# Necesitáis `epoch_id` en el wire header.

Sin eso:

* no podéis distinguir epoch N vs N+1,
* no podéis enrutar claves correctamente,
* no podéis hacer observabilidad,
* no podéis detectar split-brain limpio.

### Problema actual

Si sólo cambiáis claves:

```text
decrypt fail
```

no diferencia:

* corrupción,
* replay,
* attacker,
* key rotation,
* downgrade,
* desync.

### Recomendación

Añadir header mínimo:

```cpp
struct CryptoHeader {
    uint16_t version;
    uint64_t epoch_id;
}
```

antes de payload comprimido.

### Beneficios enormes

Permite:

* dual-key lookup,
* métricas,
* replay protection futura,
* forensic tracing,
* observabilidad,
* rollback controlado.

### Compatibilidad

Esto probablemente convierte ADR-045 en:

* FASE 2 = coordinación epoch
* FASE 3 = wire protocol evolution

Y eso es correcto arquitectónicamente.

Intentar dual-key “sin tocar wire protocol” probablemente acabará en:

* heurísticas frágiles,
* decrypt retries,
* complejidad invisible,
* bugs imposibles de depurar.

---

# Consenso General del Consejo

## Lo sólido del ADR-045

El Consejo considera acertados:

* `CryptoProviderHandle` con RCU
* etcd como coordinador
* `not_before`
* dual-key temporal
* evitar 2PC completo
* asumir fallos parciales

La dirección arquitectónica es correcta.

---

# Cambios que el Consejo recomienda antes de FASE 2

## Mínimos imprescindibles

### 1. Añadir `epoch_id` al wire header

Sin esto la observabilidad criptográfica será muy limitada.

### 2. Introducir ACK READY ligero

No 2PC completo, pero sí barrier synchronization básica.

### 3. Crear estado autonomy explícito

`EPOCH_TRANSITION`

### 4. Separar:

* prepare phase
* activation phase
* dual-accept phase

---

# Riesgo principal identificado

El mayor riesgo no es Vault.

Ni etcd.

Ni ZeroMQ.

Es:

# divergencia silenciosa de epoch

porque puede parecer:

* packet loss,
* timeout,
* congestión,
* fallo de red.

Cuando realmente es:

```text
peer(epoch=41) ↔ peer(epoch=42)
```

Si eso no queda explícito en wire + métricas + logs, el debugging operacional será extremadamente difícil en producción.
