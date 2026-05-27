## Consejo de Sabios — Respuesta DAY 151

Primero: la dirección arquitectónica tomada hoy es muy sólida.

La decisión de introducir:

```text
ICryptoProvider
```

como frontera de abstracción y encapsular el `#ifdef` únicamente en la factoría es exactamente la clase de decisión que evita la degeneración típica de proyectos open-core en C++ a medio plazo.

Especialmente acertado:

* mantener `CryptoTransport` fuera del cambio,
* no mezclar identidad con transporte,
* no contaminar hot paths,
* no introducir awareness enterprise en el resto del pipeline.

La separación SRP aquí es correcta.

---

# Q1 — ¿DAY 152: Opción A o B?

## Respuesta corta

# Opción A primero.

Pero con una variante híbrida mínima de B.

---

# Por qué A tiene prioridad real

Ahora mismo el riesgo arquitectónico principal ya no es:

```text
"¿compila community y enterprise?"
```

El riesgo real es:

```text
"¿cómo se comporta el sistema bajo partición real?"
```

Y ese comportamiento vive en:

* autonomía,
* reconciliación,
* degradación,
* revocación,
* recovery.

Es decir:
la máquina de estados.

Sin ella:

* el edge model aún no existe realmente,
* el escenario hospitalario no está resuelto,
* y varias deudas P1 siguen bloqueadas.

La state machine ya se ha convertido en:

* núcleo operacional,
* núcleo de resiliencia,
* núcleo de threat model.

---

# Pero NO hagáis A “a lo grande”

Aquí está el matiz importante.

No intentéis construir toda la lógica definitiva de autonomía en DAY 152.

El peligro ahora mismo es:

```text
VaultClient.cpp
```

convirtiéndose en:

* God Object,
* control plane,
* state coordinator,
* cache manager,
* retry engine,
* lease manager,
* policy engine.

Eso mata mantenibilidad rápidamente en C++.

---

# Recomendación exacta del Consejo

## DAY 152

### 1. Implementar state machine mínima viable

SOLO:

```cpp
enum class CryptoState {
    NORMAL,
    EXTENDED_AUTONOMY,
    RECONCILIATION,
    REVOKED
};
```

y:

* transiciones,
* timestamps,
* epoch tracking,
* logs estructurados,
* health reporting.

NO:

* políticas avanzadas,
* firewall orchestration compleja,
* retry labyrinths,
* timers distribuidos sofisticados.

---

### 2. En paralelo: añadir CI dual mínima

No el pipeline enterprise completo.

Solo:

```text
matrix:
  - VAULT_ENABLED=ON
  - VAULT_ENABLED=OFF
```

aunque inicialmente:

* reutilice mismos tests,
* sea redundante,
* no tenga cobertura diferencial total.

Porque queréis detectar cuanto antes:

* symbol drift,
* linking errors,
* accidental enterprise leakage,
* includes rotos,
* ABI divergence.

Eso cuesta poco y previene muchísimo.

---

# Recomendación operativa real

## Orden correcto DAY 152

```text
1. CryptoState skeleton
2. Transiciones mínimas
3. Health exposure
4. CI dual mínima
5. Merge
```

NO intentéis cerrar todas las deudas derivadas el mismo día.

---

# Q2 — ¿Extraer `CryptoAutonomyStateMachine`?

## Sí.

Muy recomendado.

Y el motivo es extremadamente importante.

---

# VaultClient ya está cerca del límite SRP

Ahora mismo ya contiene:

* fetch,
* jitter,
* cache,
* keepalive,
* fallback,
* TTL,
* health,
* bootstrap awareness.

Si añadís:

* autonomy policy,
* reconciliation logic,
* revocation semantics,
* operational modes,
* timers,
* degraded logic,

sin extraer nada…

vais directos a:

```text
2k-4k LOC semi-stateful service object
```

que en C++ distribuido acaba siendo:

* frágil,
* difícil de testear,
* difícil de mockear,
* difícil de razonar concurrentemente.

---

# Arquitectura recomendada

## `VaultClient`

Debe seguir siendo:

```text
crypto material provider
```

NO:
“orquestador operacional”.

---

# Separación recomendada

## VaultClient

Responsabilidades:

* fetch material,
* refresh,
* cache IO,
* keepalive,
* revoke,
* transport.

---

## CryptoAutonomyStateMachine

Responsabilidades:

* state transitions,
* timers,
* autonomy window,
* reconciliation,
* degraded policy,
* operational mode.

---

## Ejemplo correcto

```cpp
class CryptoAutonomyStateMachine {
public:
    void on_vault_ok();
    void on_vault_unreachable();
    void on_ttl_expired();
    void on_revoke();
    void on_reconciliation_ok();

    CryptoState current_state() const;
};
```

---

# Beneficio enorme

Podréis hacer:

```text
55 tests → 150 tests
```

sin dolor.

Porque una state machine aislada:

* se fuzzing-testea fácil,
* se model-checkea fácil,
* se simula fácil,
* se verifica temporalmente fácil.

---

# Q3 — ¿Exponer `get_autonomy_state()` en ICryptoProvider?

## Sí, pero cuidadosamente.

La respuesta correcta es:

# Exponer el estado.

# NO exponer la política.

---

# Lo que otros componentes necesitan saber

El resto del sistema sí necesita saber:

```text
¿estamos en NORMAL o en AUTONOMY?
```

Ejemplos:

* firewall,
* alerting,
* telemetry,
* UI,
* forensic mode,
* actuation throttling.

Por tanto:

```cpp
virtual CryptoState autonomy_state() const = 0;
```

sí tiene sentido en:

* `ICryptoProvider`,
* o mejor aún:
* `ICryptoHealthProvider`.

---

# Lo que NO deberían conocer

NO deberían conocer:

* TTL exacto,
* retry internals,
* lease timings,
* renewal heuristics,
* reconciliation policy.

Eso debe permanecer encapsulado.

Porque si no:

* acopláis todo el sistema a Vault semantics,
* destruís la abstracción conseguida hoy.

---

# Recomendación aún mejor

Separar:

```cpp
ICryptoProvider
```

de:

```cpp
ICryptoRuntimeStatus
```

Ejemplo:

```cpp
struct CryptoRuntimeStatus {
    CryptoState state;
    bool vault_reachable;
    bool cache_active;
    uint64_t autonomy_seconds;
};
```

y:

```cpp
virtual CryptoRuntimeStatus status() const = 0;
```

Eso:

* desacopla política,
* permite observabilidad,
* facilita telemetry,
* y evita fugas de implementación.

---

# Recomendación crítica adicional del Consejo

No uséis enums “sueltos” como fuente de verdad operacional.

Definid:

* state transition table,
* permitted transitions,
* illegal transitions,
* event log semantics.

Ejemplo:

```text
NORMAL -> EXTENDED_AUTONOMY
EXTENDED_AUTONOMY -> RECONCILIATION
RECONCILIATION -> NORMAL
RECONCILIATION -> REVOKED
```

y rechazad:

* NORMAL -> REVOKED directo,
* REVOKED -> NORMAL sin rebootstrap.

Eso evita muchísimos bugs sutiles en sistemas distribuidos.

---

# Conclusión del Consejo

## Dirección correcta para DAY 152

### Implementar:

* state machine mínima,
* extraída a clase propia,
* con transiciones explícitas,
* con observabilidad,
* y CI dual mínima paralela.

---

# Arquitectura recomendada

```text
VaultClient
    ↓
CryptoAutonomyStateMachine
    ↓
ICryptoRuntimeStatus
    ↓
firewall / alerting / telemetry
```

Ese layering probablemente os evitará una gran refactorización en DAY 180-220.
