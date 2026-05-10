# ADR-0043 — Memoria Episódica Distribuida con Coherencia Temporal

| Campo | Valor |
|-------|-------|
| **Estado** | Aceptado — Consejo de Sabios, DAY 147 |
| **Fecha** | 2026-05-10 |
| **Autor** | Alonso Isidoro Román |
| **Versión** | v4 (final) |
| **ADRs relacionados** | ADR-004, ADR-021, ADR-025, ADR-032, ADR-034, ADR-035, ADR-038, ADR-040 |
| **ADRs modificados** | ADR-035 (cierra OQ-2), ADR-038 (supersede §Anonimización y §Canal de distribución) |
| **Deudas abiertas** | DEBT-PARQUET-SCHEMA-001, DEBT-VAULT-FEDERATION-001, DEBT-LEGAL-DATA-RETENTION-001, DEBT-KPSEUDO-ROTATION-MIGRATION-001, DEBT-GDPR-ERASURE-001, DEBT-KPSEUDO-HKDF-HIERARCHY-001 |

---

## Historial de versiones

| Versión | Cambios principales |
|---------|---------------------|
| v1 | Borrador inicial (sesión ChatGPT, DAY ~145). Ciclos permitidos, anonimización con salt rotante, BitTorrent. |
| v2 | Reescritura completa. Elimina ciclos (DAG), HMAC determinista, ZeroMQ. Consolida ADR-035 OQ-2 y ADR-038. |
| v3 | Incorpora dictamen Consejo ronda 1: MAC como identidad primaria, idempotencia Ed25519, UTC epoch ns, ontología Neo4j mínima, schema Parquet candidato, eliminación de PRECEDES, DEBT-GDPR-ERASURE-001. |
| v4 | Incorpora dictamen Consejo ronda 2: OQ-1 convertida en D9 (cola local persistente), filtro MAC unicast en D2, installation_id y node_id en schema Parquet, almacenamiento duradero de batches en paso 5. Estado → Aceptado. |

---

## Propósito de este documento

Doble rol:

1. **Decisión nueva**: arquitectura de memoria episódica distribuida del sistema federado aRGus — modelo de grafo Neo4j, pseudonimización de telemetría, paquete mensual edge→central, jerarquía de Vault, schema Parquet candidato, cola local de batches pendientes.

2. **Consolidación**: resuelve conflictos abiertos en ADR-035 (OQ-2) y ADR-038 (§Anonimización, §Canal de distribución). Los apartados supersedidos deben anotarse con referencia a este documento.

---

## Contexto

aRGus NDR despliega nodos edge en instalaciones de infraestructura crítica (hospitales, colegios, municipios). Cada instalación agrupa uno o más nodos bajo una entidad organizativa común. Un servidor central compartido consolida información de todas las instalaciones de la red aRGus.

El pipeline C++20 existente produce telemetría operativa continua (`ml-detector`, `firewall-acl-agent`) almacenada en SQLite local con horizonte de ~30 días. No existe mecanismo para consolidar esa telemetría en una memoria histórica global coherente, ni para representar la evolución causal de entidades a lo largo del tiempo y a través de instalaciones.

### Restricciones no negociables

- **GDPR**: datos personales (IPs, MACs, hostnames) no pueden abandonar el nodo en claro. La pseudonimización es obligatoria antes de cualquier transmisión al servidor central.
- **Misión crítica**: el nodo edge no puede degradar su capacidad de detección para consolidar memoria. Todo proceso de consolidación es asíncrono y de baja prioridad.
- **Soberanía de datos**: cada instalación es dueña de sus datos. El servidor central recibe contribuciones, no extrae datos.
- **Coherencia temporal**: la misma entidad física debe producir el mismo identificador en todos los batches, independientemente de cuándo se envíen o cuántos reintentos haya habido.
- **Escala global**: el sistema debe poder desplegarse en múltiples países. Todos los timestamps son UTC. No existe formato de fecha local en ninguna interfaz entre componentes.

---

## Arquitectura de referencia

```
SERVIDOR CENTRAL
├── Neo4j cluster            ← memoria consolidada e histórica
├── Vault central            ← root of trust, wrapping keys globales
├── Jenkins cluster          ← CI/CD, aprovisionamiento de instalaciones
├── etcd replicas (learner)  ← ≥1 observer/learner por instalación, sin voto Raft
└── Wazuh, OpenCanary, RAG, Falco...

POR INSTALACIÓN (ej. Hospital General de Badajoz)
├── Vault local              ← claves operativas de la instalación
├── etcd cluster HA          ← topología parametrizada por tamaño (ver D6)
└── N nodos edge
    ├── SQLite               ← fuente de verdad local, episódica (~30 días, sin anonimizar)
    ├── /var/spool/argus/batches/  ← cola local de batches pendientes (ver D9)
    ├── Pipeline C++20       ← sniffer, ml-detector, firewall-acl-agent, ml-trainer
    └── ZeroMQ + Ed25519     ← transporte cifrado
```

Flujo de telemetría (unidireccional):
```
nodo edge → [batch mensual pseudonimizado] → cola local → servidor central
```

Canal de comando bidireccional:
```
Jenkins → Vault central → etcd (cifrado, ZeroMQ) → Vault local → nodo edge
```

---

## Decisiones

### D1 — Tres niveles de memoria

| Nivel | Ubicación | Horizonte | Contenido | Patrón de acceso |
|-------|-----------|-----------|-----------|-----------------|
| **Episódica** | SQLite por nodo | ~30 días | Eventos crudos, identidades reales | Write-heavy, read-light |
| **Consolidada** | Neo4j central | Indefinido | Snapshots mensuales pseudonimizados | Read-heavy, write-batch |
| **Histórica** | Neo4j central | Indefinido | Patrones agregados, campañas | Read-heavy, write-raro |

Los eventos crudos nunca abandonan el nodo sin pseudonimización previa. SQLite es la fuente de verdad operativa local; Neo4j es la fuente de verdad histórica global. La cola local de batches (D9) es una capa de resiliencia de transmisión, no un nivel de memoria adicional.

---

### D2 — Identidad de entidad: MAC unicast como campo primario

La IP es un arrendamiento DHCP, no una identidad. En una red hospitalaria típica, un dispositivo puede obtener IPs distintas en días consecutivos. Usar la IP como campo de identidad produce nodos `Host` duplicados en Neo4j para el mismo dispositivo físico.

**La MAC unicast es el campo de identidad primario.** En infraestructura crítica gestionada (hospitales, colegios, municipios), la randomización de MAC está desactivada por política de red. La MAC identifica de forma estable al dispositivo físico.

**Lo que viaja al servidor central no es la MAC.** Es `HMAC-SHA256(K_pseudo, MAC)`: una cadena opaca de 32 bytes sin contenido recuperable sin conocer `K_pseudo`. La posición legal bajo GDPR es equivalente a cualquier otro esquema de pseudonimización.

#### Filtro MAC unicast

Solo se usan MACs unicast globalmente asignadas como identidad primaria. MACs multicast, broadcast o con bit de administración local activo se tratan como `NetworkPresence` y caen al fallback.

```python
def is_valid_primary_mac(mac: str) -> bool:
    # Primer byte: bit 0 = 0 (unicast), bit 1 = 0 (globally assigned)
    first_byte = int(mac[0:2], 16)
    return (first_byte & 0x03) == 0x00
```

#### Jerarquía de resolución de identidad

Ejecutada en el nodo, antes de serializar a Parquet:

```
función resolve_identity(registro):
    si registro.mac_src existe y is_valid_primary_mac(registro.mac_src):
        return HMAC-SHA256(K_pseudo, registro.mac_src)      → nodo Host
    si registro.hostname existe y es estable:
        return HMAC-SHA256(K_pseudo, registro.hostname)     → nodo Host (fallback)
    return HMAC-SHA256(K_pseudo, registro.ip_src)           → nodo NetworkPresence
```

`Host` representa un dispositivo físico identificable. `NetworkPresence` representa un punto de presencia en la red con identidad no garantizada (dispositivos IoT sin nombre ni MAC estable). Son semánticamente distintos y se etiquetan de forma diferente en Neo4j.

#### Pseudonimización de flujos

```
anon_flow_id = HMAC-SHA256(K_pseudo, concat(MAC_src, MAC_dst, proto, dst_port))
```

Si `MAC_dst` es externa (salida a internet), se usa el literal `"external"`.

#### Limitación conocida: identidades múltiples del mismo dispositivo

Si un dispositivo cambia de identidad primaria entre períodos (MAC → hostname → IP por cambio de hardware o política), genera `anon_id` distintos en Neo4j. El derecho al olvido (D8) opera sobre identidades individuales; no alcanza automáticamente a las identidades alternativas del mismo dispositivo. La mitigación es de política operativa: las instalaciones deben mantener inventario de activos con MAC estática para dispositivos críticos.

---

### D3 — Pseudonimización determinista con clave por instalación

La clave de pseudonimización (`K_pseudo`) es única por instalación y se custodia en el **Vault local**. Es generada por Jenkins en el aprovisionamiento y nunca abandona el Vault local en claro.

**La rotación de `K_pseudo` es un evento excepcional**, no periódico. Una rotación rompe la continuidad del `anon_id` en Neo4j salvo re-pseudonimización retroactiva. El procedimiento de migración está registrado como `DEBT-KPSEUDO-ROTATION-MIGRATION-001`. La disciplina de cooldown y máximo 2 claves concurrentes establecida en ADR-004 se aplica como constraint.

**Si se rota `K_pseudo`**, el `anon_id` se versiona: `HMAC-SHA256(K_pseudo_vN, MAC)`. Los nodos históricos en Neo4j conservan el `anon_id` de su versión y se vinculan al nuevo mediante una relación `:PREVIOUS_IDENTITY`. Las queries de evolución histórica a través de múltiples rotaciones requieren recursividad Cypher con límite de profundidad explícito; vigilar rendimiento a partir de 3+ rotaciones por instalación.

**Canal de rotación:**
```
Jenkins → genera K_pseudo_new → cifra con wrapping key del Vault central
→ distribuye via etcd (ChaCha20-Poly1305 + Ed25519)
→ nodo edge → desencripta → almacena en Vault local
→ cooldown: nodos siguen usando K_pseudo_old hasta drenado completo de batches en vuelo
→ activación de K_pseudo_new coordinada por Jenkins
```

Una jerarquía de derivación HKDF (`K_pseudo_host`, `K_pseudo_flow`, `K_pseudo_model` desde una `K_root`) reduciría el radio de daño ante compromiso de subclave y permitiría rotación selectiva. Registrado como `DEBT-KPSEUDO-HKDF-HIERARCHY-001` (P3, post-FEDER) para instalaciones de alto valor.

---

### D4 — Paquete mensual por nodo

Cada nodo genera, una vez al mes, un batch comprimido y firmado que se deposita en la cola local (D9) para transmisión al servidor central.

#### D4a — Clave de idempotencia

```
idempotency_key = firma Ed25519(batch_content)
```

El batch tiene contenido determinista. La firma no cambia entre reintentos si el contenido no cambia. El servidor central verifica `IF EXISTS Batch WHERE idempotency_key = $key → ACK, skip` antes de procesar. Estable a través de cualquier número de reintentos en cualquier ventana de tiempo.

#### D4b — Dos ficheros Parquet por nodo por mes

El schema es un **candidato** que será validado y ajustado contra los CSVs reales del pipeline (`DEBT-PARQUET-SCHEMA-001`). Granularidad de eventos (por flow vs. por paquete) y política de registro (todos los eventos vs. solo alertas) se confirman con datos reales; esto determina volumen esperado y necesidad de fragmentación.

**Schema candidato: `ml-detector-YYYY-MM-{anon_node_id}.parquet`**

| Campo | Tipo Arrow | Descripción |
|-------|-----------|-------------|
| `timestamp_utc_ns` | int64 | Epoch nanoseconds UTC. Sin timezone. |
| `installation_id` | utf8 | Identificador opaco de instalación. |
| `node_id` | utf8 | HMAC(K_pseudo, node_identifier). |
| `anon_host_id` | utf8 | HMAC(K_pseudo, MAC_src). Hex lowercase. |
| `anon_flow_id` | utf8 | HMAC(K_pseudo, concat(MAC_src, MAC_dst, proto, dst_port)). |
| `event_type` | utf8 | `normal`, `anomaly`, `attack` |
| `confidence` | float32 | Score del modelo [0.0, 1.0] |
| `model_version` | utf8 | Versión del plugin activo |
| `protocol` | int8 | Número de protocolo IP |
| `dst_port_class` | utf8 | `well-known`, `registered`, `dynamic` |
| `bytes_count` | int64 | Bytes del flow |
| `packets_count` | int32 | Paquetes del flow |
| `alert_severity` | utf8 | `low`, `medium`, `high`, `critical`; null si event_type=normal |

**Schema candidato: `firewall-acl-agent-YYYY-MM-{anon_node_id}.parquet`**

| Campo | Tipo Arrow | Descripción |
|-------|-----------|-------------|
| `timestamp_utc_ns` | int64 | Epoch nanoseconds UTC. |
| `installation_id` | utf8 | Identificador opaco de instalación. |
| `node_id` | utf8 | HMAC(K_pseudo, node_identifier). |
| `anon_src_id` | utf8 | HMAC(K_pseudo, MAC_src) |
| `anon_dst_id` | utf8 | HMAC(K_pseudo, MAC_dst) si LAN; null si externo |
| `action` | utf8 | `ALLOW`, `DENY`, `DROP` |
| `rule_id` | utf8 | ID de la regla que disparó la acción |
| `protocol` | int8 | Número de protocolo IP |
| `dst_port` | int32 | Puerto destino |
| `direction` | utf8 | `inbound`, `outbound`, `lateral` |
| `bytes_count` | int64 | |
| `reason` | utf8 | Motivo de la decisión |

Los ficheros Parquet son autocontenidos: `installation_id` y `node_id` están embebidos en cada fichero, no solo en los metadatos JSON del batch. Esto garantiza que el fichero no pierde su contexto ante cualquier tipo de reenvío parcial, procesamiento manual o auditoría futura.

**Timestamps**: epoch nanoseconds int64 UTC en Parquet. ISO 8601 con sufijo `Z` explícito en metadatos JSON. No existe formato local en ninguna interfaz. Los nodos convierten a UTC antes de escribir. El código C++20 usa `std::chrono::system_clock` (wall clock), nunca `steady_clock`.

#### D4c — Plugin de modelo ensemble firmado (desactivado)

Modelo XGBoost local del período, empaquetado como plugin aRGus (ADR-025, ADR-032), firmado con Ed25519, en estado desactivado. El servidor central lo valida, agrega con modelos de otros nodos (ADR-038 §Agregación, pendiente) y puede redistribuir modelo global mejorado. Cualquier agregación debe incluir defensa contra envenenamiento (robust aggregation + outlier detection) antes de redistribuir.

#### D4d — Metadatos del batch

```json
{
  "node_id":           "anon-node-{hmac}",
  "installation_id":   "inst-{opaque_id}",
  "period_start":      "2026-01-01T00:00:00Z",
  "period_end":        "2026-01-31T23:59:59Z",
  "pipeline_version":  "v0.7.0-variant-b",
  "active_model_hash": "sha256:...",
  "idempotency_key":   "ed25519:...",
  "batch_signature":   "ed25519:..."
}
```

`installation_id` es un identificador opaco generado por Jenkins en el aprovisionamiento. El mapping a nombre real (hospital, municipio) se almacena solo en Vault central, accesible únicamente a roles autorizados.

---

### D5 — Modelo de grafo Neo4j: DAG temporal sin ciclos

**Los ciclos en el grafo de causalidad quedan explícitamente rechazados.** Los comportamientos cíclicos reales (beaconing, reconexiones, retries) se representan mediante tipos de relación semánticamente distintos (`:RECURRENCE`, `:BEHAVIORAL_PATTERN`) sobre el DAG, sin introducir ciclos estructurales.

#### Ontología mínima viable (MVP FEDER)

```
Nodos:
  Host            — dispositivo físico con MAC unicast estable
  NetworkPresence — punto de presencia en red (sin MAC estable)
  Flow            — comunicación entre dos identidades en un episodio
  Alert           — detección generada por ml-detector
  Episode         — snapshot mensual de un nodo en una instalación
  Installation    — entidad organizativa (hospital, colegio, municipio)
  Batch           — registro de batch procesado (garantía de idempotencia)

Relaciones:
  (Host|NetworkPresence)-[:OBSERVED_IN]->(Episode)
  (Flow)-[:OCCURRED_IN]->(Episode)
  (Alert)-[:TRIGGERED_BY]->(Flow)
  (Episode)-[:BELONGS_TO]->(Installation)
  (Host)-[:PREVIOUS_IDENTITY]->(Host)    ← solo tras rotación de K_pseudo
```

Entidades como `Campaign` están fuera del scope MVP FEDER. La Graph Reconciliation Layer que convierte histórico consistente en conocimiento interpretable es investigación de siguiente fase, no objetivo de este ADR.

#### Ordenamiento temporal sin aristas materializadas

La relación `PRECEDES` entre episodios **no se materializa**. El ordenamiento temporal usa comparación del campo `Episode.period` (string ISO 8601: `"2026-01"` < `"2026-02"`), ordenable directamente en Cypher.

```cypher
// Evolución de un host en los últimos 6 meses
MATCH (h:Host {id: $anon_id})-[:OBSERVED_IN]->(e:Episode)
WHERE e.period >= "2025-11" AND e.period <= "2026-04"
RETURN e.period, e.node_id ORDER BY e.period ASC
```

#### Merge en ingesta (idempotente)

```cypher
// Verificar idempotencia antes de procesar
MERGE (b:Batch {idempotency_key: $idempotency_key})
  ON CREATE SET b.ingested_at = $now, b.status = "processed"
  ON MATCH SET b.status = "duplicate_ignored"
WITH b WHERE b.status = "processed"

// Solo si el batch es nuevo, proceder con la ingesta
MERGE (h:Host {id: $anon_host_id, installation: $inst_id})
MERGE (e:Episode {period: $period, node_id: $anon_node_id, installation: $inst_id})
MERGE (h)-[:OBSERVED_IN]->(e)
```

#### Índices recomendados en el playbook de despliegue

```cypher
CREATE INDEX FOR (h:Host) ON (h.id);
CREATE INDEX FOR (b:Batch) ON (b.idempotency_key);
CREATE INDEX episode_period_installation FOR (e:Episode) ON (e.period, e.installation);
```

---

### D6 — Topología etcd: parametrizable por instalación (cierra ADR-035 OQ-2)

| Tipo | Miembros locales (con voto Raft) | En servidor central | SPOF |
|------|----------------------------------|---------------------|------|
| Pequeña (1-2 nodos) | 1 single-node | 1 observer/learner | Sí, documentado y aceptado |
| Mediana (3-9 nodos) | 3, uno por nodo edge | 1 observer/learner | No |
| Grande (10+ nodos) | 3, hardware dedicado | 1-2 observers/learners | No |

Tres miembros etcd en la misma máquina física no aportan tolerancia a fallos. El observer en el servidor central recibe replicación sin participar en Raft.

Para instalaciones pequeñas: single-node etcd es SPOF documentado y aceptado. Mitigación: snapshot diario automático, retención 7 días, destino cifrado con wrapping key del Vault local (ADR-035 D5).

**ADR-035 OQ-2 queda cerrada.**

---

### D7 — Jerarquía de Vault

```
Vault central (servidor central)
├── Custodia: wrapping keys globales, keypairs Jenkins, CA raíz
├── Mapping installation_id opaco → nombre real (acceso autorizado)
└── Rol: root of trust

Vault local (por instalación)
├── Custodia: K_pseudo, keypairs Ed25519 de nodos, seeds etcd
└── Rol: operativo
```

**Procedimiento de recuperación de Vault local** ante desastre físico o ransomware:
1. Jenkins detecta pérdida de heartbeat del Vault local durante >72h.
2. Nuevo hardware de instalación genera Vault local vacío.
3. Administrador autorizado aprueba la recuperación via Jenkins (aprobación manual auditada, log firmado con timestamp en servidor central).
4. Vault central entrega backup cifrado via canal seguro (etcd + Ed25519).
5. Nuevo Vault local desencripta con wrapping key pre-registrada.
6. Post-restauración: rotación forzosa de `K_pseudo`; ruptura temporal de coherencia registrada en Neo4j como evento `VaultRestored`.

---

### D8 — Flujo de derecho al olvido (GDPR Art. 17)

Registrado como `DEBT-GDPR-ERASURE-001` (P1 pre-FEDER). Flujo conceptual:

```
Solicitud de borrado (identidad real: MAC o IP)
→ Instalación local calcula anon_id = HMAC(K_pseudo, identidad)
→ Borra registros en SQLite local
→ Envía comando firmado (Ed25519) al servidor central:
  {"action": "erase", "anon_id": "...", "installation": "inst-...", "timestamp": "...Z"}
→ Servidor central ejecuta DELETE en Neo4j para ese anon_id
→ Registra auditoría firmada del borrado (inmutable)
→ Instalación recibe confirmación y certifica cumplimiento
```

El borrado opera sobre el `anon_id` resuelto. Si el mismo dispositivo generó múltiples `anon_id` por cambio de identidad primaria (ver limitación en D2), el borrado de uno no alcanza automáticamente a los demás. Documentado como limitación conocida.

La implementación completa requiere validación jurídica con INCIBE/UEx (Dr. Andrés Caro Lindo). Pregunta específica: ¿cuándo exactamente los datos pseudonimizados con HMAC dejan de ser datos personales si la clave de reversión existe pero está técnicamente aislada en un Vault destruido?

---

### D9 — Cola local de batches pendientes (resuelve OQ-1)

La generación mensual del batch y su transmisión al servidor central son operaciones desacopladas. Un nodo edge en infraestructura crítica puede estar desconectado durante días o semanas por mantenimiento, fallo de ISP o incidente. La cola local garantiza que ningún batch se pierde por conectividad intermitente, independientemente de SQLite.

#### Estructura de la cola

```
/var/spool/argus/batches/
├── pending/    ← batches firmados listos para envío
│   └── {period}-{idempotency_key}.tar.zst
├── sent/       ← batches con ACK confirmado (retención 7 días, luego purga)
└── expired/    ← batches no enviados tras 90 días (alerta administrativa)
```

#### Ciclo de vida de un batch

1. El pipeline de consolidación genera el batch mensual y lo serializa en `pending/`.
2. El agente de transmisión intenta envío al servidor central via ZeroMQ + Ed25519.
3. Si el servidor responde ACK: mueve el fichero a `sent/`.
4. Si falla: reintenta con backoff exponencial (1h, 2h, 4h, 8h, 16h, 24h, luego cada 24h).
5. A los 90 días sin ACK: mueve a `expired/`, emite alerta administrativa (log local + etcd si hay conectividad).

#### Propiedades de la cola

- **Independiente de SQLite**: el batch, una vez generado y firmado, no requiere los datos crudos para ser retransmitido. SQLite puede haber rotado sus datos sin afectar a la cola.
- **Idempotente en el servidor**: el servidor central identifica batches duplicados por `idempotency_key` y descarta los reintentos sin reprocesar.
- **Ordenada FIFO**: el agente de transmisión envía batches en orden cronológico de generación, priorizando los más antiguos para minimizar la ventana de memoria no consolidada.
- **Retención de 90 días**: cubre 3 ciclos mensuales sin conectividad. Si un nodo está aislado más de 90 días sin enviar, los batches se archivan y se emite alerta; los datos de SQLite habrán rotado, pero los batches firmados están intactos en `expired/`.

#### Almacenamiento duradero en el servidor central

Antes de procesar un batch en Neo4j, el servidor central lo persiste en almacenamiento de objetos duradero (MinIO u equivalente). Esto convierte el sistema en event sourcing real: Neo4j puede reconstruirse desde cero a partir de los batches almacenados sin depender de los nodos edge. Los batches crudos son la fuente de verdad para disaster recovery del grafo Neo4j.

---

## Deudas técnicas registradas

| ID | Prioridad | Descripción |
|----|-----------|-------------|
| `DEBT-PARQUET-SCHEMA-001` | **P0 bloqueante** | Validar schema candidato contra CSVs reales de `ml-detector` y `firewall-acl-agent` en entorno Vagrant. Confirmar granularidad de eventos y política de registro. |
| `DEBT-VAULT-FEDERATION-001` | P1 pre-FEDER | Procedimiento de offboarding: destrucción certificada de Vault local, retención de datos históricos en Neo4j post-offboarding. |
| `DEBT-LEGAL-DATA-RETENTION-001` | P1 pre-FEDER | Dictamen jurídico GDPR sobre retención de datos pseudonimizados post-cliente. Interlocutor: Dr. Andrés Caro Lindo (UEx/INCIBE). |
| `DEBT-KPSEUDO-ROTATION-MIGRATION-001` | P1 pre-FEDER | Procedimiento de migración de identidades en Neo4j tras rotación de K_pseudo: coordinación con drenado de batches en vuelo, atomicidad, auditoría. |
| `DEBT-GDPR-ERASURE-001` | P1 pre-FEDER | Implementar flujo de derecho al olvido (D8): comando firmado de borrado de anon_id en Neo4j, auditoría certificada. |
| `DEBT-KPSEUDO-HKDF-HIERARCHY-001` | P3 post-FEDER | Jerarquía HKDF para K_pseudo (K_pseudo_host, K_pseudo_flow, K_pseudo_model desde K_root). Reduce radio de daño ante compromiso de subclave. Para instalaciones de alto valor. |

---

## Impacto sobre ADRs existentes

| ADR | Impacto | Acción requerida |
|-----|---------|-----------------|
| ADR-004 | Compatible. Cooldown y máximo 2 claves concurrentes se extienden como constraint a K_pseudo. | Añadir referencia a ADR-043 en §8 Future Work. |
| ADR-025 | Compatible. Ed25519 firma el batch e idempotency_key. Sin cambios. | Ninguna. |
| ADR-032 | Compatible. Plugin modelo mensual sigue Plugin Distribution Chain. Sin cambios. | Ninguna. |
| ADR-034 | Compatible. Topología etcd parametrizada se expresa en `deployment.yml`. | Añadir campo `etcd.topology_class` a spec de deployment.yml. |
| ADR-035 | **OQ-2 cerrada** por D6. | Actualizar OQ-2 a CLOSED con referencia a ADR-043 D6. |
| ADR-038 | **Dos secciones supersedidas**: §Anonimización (D2-D3 de este ADR) y §Canal de distribución (D4, ZeroMQ sobre BitTorrent). El resto de ADR-038 permanece vigente. | Marcar secciones supersedidas con referencia a ADR-043. |
| ADR-040 | Compatible. Contrato de reentrenamiento ML se aplica al plugin modelo mensual. Sin cambios. | Ninguna. |

---

## Próximos pasos

El orden es estricto.

1. Esbozar ontología Neo4j mínima completa (D5 es el punto de partida; validar con queries forenses de ejemplo antes de tocar el schema Parquet).
2. **[DEBT-PARQUET-SCHEMA-001]** Examinar CSVs reales en Vagrant. Validar y ajustar schema candidato. Este schema es el contrato de interfaz; todo el pipeline depende de él.
3. Implementar pseudonimización en nodo: jerarquía de identidad con filtro MAC unicast, `K_pseudo` del Vault local.
4. Implementar empaquetado mensual y cola local (D9): Parquet ×2 + plugin firmado + metadatos + `idempotency_key` → `pending/`.
5. Diseñar pipeline de ingesta en servidor central: verificación Ed25519 → persistencia en almacenamiento duradero → check idempotencia → deserialización Parquet → MERGE Neo4j.
6. Actualizar ADR-035 (cerrar OQ-2) y ADR-038 (marcar secciones supersedidas).
7. **[DEBT-VAULT-FEDERATION-001 + DEBT-LEGAL-DATA-RETENTION-001 + DEBT-GDPR-ERASURE-001]** Iniciar validación jurídica en paralelo con pasos técnicos.

---

## Alcance FEDER

Los pasos 1–5 están dentro del horizonte técnico del proyecto FEDER (deadline 22 septiembre 2026). Constituyen la contribución de investigación aplicada: una arquitectura de memoria episódica distribuida para NDR en infraestructura crítica de bajo presupuesto, con pseudonimización verificable, coherencia histórica garantizada, identidad estable frente a condiciones de red reales (DHCP, conectividad intermitente) y resiliencia ante particiones de red prolongadas.

Los pasos 6–7 son de gestión técnica y legal, sin dependencia de financiación externa.

---

*Consejo de Sabios: Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral*
*Via Appia Quality — DAY 147*