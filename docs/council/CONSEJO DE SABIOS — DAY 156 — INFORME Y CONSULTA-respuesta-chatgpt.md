# Consejo de Sabios — Dictamen DAY 156

El trabajo de hoy cierra una deuda arquitectónica importante: la autonomía criptográfica ya no es un concepto “de diseño”, sino un comportamiento operativo verificable E2E. La integración SM → PUB/SUB → Reactor → firewall es exactamente el tipo de cadena causal observable que reduce riesgo sistémico real.

También es relevante el descubrimiento del slow joiner de ZMQ. Ese tipo de bug suele aparecer meses después en producción y es bueno haberlo capturado ahora.

---

# Q1 — Persistencia del estado: tmpfs vs etcd vs `/var/lib`

## Consenso del Consejo

Para FEDER/hospitalario:

* `tmpfs` SOLO es insuficiente.
* `etcd` para persistir la SM introduce dependencia circular.
* La opción correcta es:
  **`/var/lib/argus/crypto-autonomy-state.json` + firma + fsync atómico**.

## Motivo principal

El escenario que queréis cubrir es exactamente:

```text
Vault KO
→ AUTONOMOUS
→ reinicio inesperado
→ sistema debe recordar que estaba degradado
```

Con tmpfs, ese contexto desaparece.

Entonces el reinicio produce:

```text
BOOT
→ NORMAL
→ firewall levantado
→ falsa recuperación
```

Eso rompe el modelo de seguridad.

---

## Por qué NO usar etcd para esto

Persistir la SM dentro de etcd parece elegante, pero arquitectónicamente mezcla:

```text
Control-plane health
con
Persistence authority
```

Y además crea una semidependencia peligrosa:

```text
etcd reinicia
→ estado desaparece
→ bootstrap ambiguo
```

Peor aún:
si en el futuro el etcd embebido entra en corrupción WAL o quorum raro, la SM deja de ser recuperable precisamente cuando más la necesitas.

La SM debe tener:

```text
Persistencia mínima
+
Dependencia mínima
+
Recuperación trivial
```

El fichero firmado cumple las tres.

---

## Recomendación concreta

### Ubicación

```text
/var/lib/argus/state/crypto-autonomy-state.json
```

No `/run`.

---

## Escritura segura

Usar patrón:

```text
write temp
→ fsync(fd)
→ rename()
→ fsync(parent_dir)
```

Porque un crash entre write y rename puede dejar JSON corrupto.

---

## Contenido recomendado

```json
{
  "state": "AUTONOMOUS",
  "entered_at": 1747588841,
  "sequence": 42,
  "node_id": "etcd-a",
  "reason": "vault_unreachable",
  "signature": "base64..."
}
```

Añadir `sequence` es importante para evitar replay accidental.

---

## Recomendación adicional

La SM NO debería restaurar directamente a `NORMAL` tras restart.

El restart debería reconstruir:

```text
persisted AUTONOMOUS
→ arranque en RECONCILING
→ health-checks reales
→ NORMAL o AUTONOMOUS
```

Eso evita “trust on reboot”.

---

# Q2 — `poll_callback` como proxy de Vault

## Diagnóstico

Usar:

```cpp
etcd_client != nullptr
```

como proxy de salud criptográfica es demasiado débil incluso para MVP FEDER.

No porque vaya a fallar hoy,
sino porque semánticamente significa:

```text
“el objeto existe”
≠
“Vault está sano”
```

Son dos capas distintas.

---

## ¿Segundo SUB ZMQ?

Sí, pero minimalista.

NO hace falta un “segundo canal complejo”.

La recomendación es:

```text
Un topic PUB/SUB único de autonomy events
+
Último estado cacheado en el firewall reactor
```

Por ejemplo:

```text
topic: autonomy.state
payload:
{
  state: AUTONOMOUS,
  health: vault_unreachable,
  ts: ...
}
```

Entonces el firewall mantiene:

```cpp
std::atomic<AutonomyState> last_state;
```

y consulta eso.

---

## Ventaja clave

El firewall deja de inferir estado indirectamente.

Pasa a depender de:

```text
Estado explícito publicado por autoridad central
```

Mucho más limpio.

---

## Para MVP FEDER

Sí merece la pena.

Porque el coste es pequeño y elimina una deuda conceptual importante.

---

# Q3 — Suricata primera fuente ADR-046

## Recomendación clara

### Fase 1:

**EVE JSON via file watcher**

NO ZMQ todavía.

---

## Motivo

El pipeline actual ya tiene semántica batch/event ingestion:

```text
CSV
→ parser
→ enrichment
→ ML
→ graph
```

Suricata EVE JSON encaja perfectamente ahí.

---

## Estrategia mínima correcta

```text
Suricata
→ eve.json
→ tail/file watcher
→ normalización interna
→ pipeline actual
```

Sin tocar:

* ZMQ topology
* threading model
* reactor ownership
* backpressure actual

---

## Lo importante

La primera integración NO debe ser “tiempo real perfecto”.

Debe ser:

```text
Semantic integration first
```

Necesitáis validar:

* correlación flow_id
* timestamps
* deduplicación
* mapping de severidad
* schema canónico
* unificación IDS/ML

antes de optimizar transporte.

---

## Cuándo pasar a ZMQ

Sólo cuando aparezcan síntomas reales:

* lag IO
* tail latency
* polling overhead
* pérdida de eventos
* burst saturation

Hasta entonces:
file watcher es suficientemente bueno y muchísimo más estable operacionalmente.

---

# Q4 — Slow joiner de ZMQ

## NO ADR

Esto NO es una Architectural Decision Record.

Es:

```text
Known distributed messaging hazard
```

La decisión arquitectónica ya es “usar ZMQ PUB/SUB”.

El slow joiner es una propiedad operacional de esa elección.

---

## Dónde documentarlo

### Recomendación:

1. Nota técnica en:

```text
docs/distributed/zmq-pubsub-gotchas.md
```

2. Entrada permanente en BACKLOG:

```text
DEBT-ZMQ-SLOW-JOINER-001
```

3. Fixture helper reutilizable:

```cpp
bind_publisher_before_subscriber()
```

para impedir regresiones.

---

## Recomendación MUY importante

Añadir invariant test:

```text
Publisher binds after subscriber
→ first message MAY be lost
```

como test documental explícito.

Eso evita que alguien “optimice” el fixture en 8 meses y reintroduzca el bug.

---

# Q5 — Gestión de keypairs en producción FEDER

## Desarrollo actual

Rotación por:

```text
vagrant destroy && up
```

es correcta para entorno efímero.

No hay problema.

---

## Producción FEDER

El keypair debe ser:

```text
estable
persistente
respaldado
rotable
```

y NO regenerado automáticamente.

---

## Estrategia recomendada

### Nivel 1 — MVP FEDER

Generación inicial:

```text
STEP 0 bootstrap
→ generar Ed25519 node identity
→ guardar en:
   /var/lib/argus/keys/
```

Permisos:

```text
0600
root:argus
```

---

## Nivel 2 — Recomendado hospitalario

Separar:

```text
identity key
≠
signing operational keys
```

Por ejemplo:

| Tipo                | Persistencia  | Uso            |
| ------------------- | ------------- | -------------- |
| node identity       | años          | identidad nodo |
| operational signing | semanas/meses | eventos        |
| session keys        | horas/días    | transporte     |

---

## Nivel 3 — Ideal futuro

TPM/HSM-backed keys.

Pero eso NO es necesario para FEDER inicial.

---

# Observación arquitectónica importante

El sistema empieza a mostrar una propiedad muy valiosa:

```text
Comportamiento degradado determinista
```

Muchos sistemas “resilientes” realmente colapsan al perder componentes críticos.

aRGus está empezando a comportarse más como:

```text
Sistema autónomo tolerante a particiones
```

que como un IDS tradicional.

Ese es un salto arquitectónico relevante.
