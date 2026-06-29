# Dictamen del Consejo — ADR-052 v3 (Confirmación de fidelidad)

## Resumen ejecutivo

La v3 es una **candidata madura a ratificación**. Corrige los tres huecos estructurales detectados en la 2ª pasada y añade una arquitectura de identidad de corpus que sobrevive a los ciclos de desarrollo (`destroy+up`). La separación entre identidad de corpus (`node_id` declarativo) e identidad de autenticación (keypair rotativo) es el parche de diseño más valioso de esta iteración. El WAL externo con hash-chain, la cardinalidad exacta y el mapa de cobertura como cache declarativa son técnicamente correctos.

La **única decisión controvertida** —la anulación de árbitro incorporando señales TCP/TLS (§3.11)— es **sostenible** si se mantiene estrictamente delimitada como está escrita, pero introduce una dependencia de implementación (Wazuh/osquery) que debe ser tracked como deuda explícita.

A continuación: fortalezas consolidadas, debilidades residuales con parche, respuesta a las 7 cuestiones de la 2ª pasada, y veredicto.

---

## 1. Fortalezas a apuntalar (no tocar)

### 1.1 Separación identidad de corpus / identidad de autenticación (§3.1.2 N1)
Este es el aporte arquitectónico más valioso de v3. La observación de que `vagrant destroy+up` regenera el keypair pero **no debe regenerar la identidad de flujo** es la prueba de fuego del principio §0. El `node_id` como identidad declarativa, estable, persistida en el inventario del orquestador, con `deployment_epoch` como único mecanismo de generación deliberada, es un patrón de diseño reutilizable para cualquier sistema de ML que reconstruya datasets históricos tras rebuilds de infraestructura.

### 1.2 `seq_in_window` transportado, no recomputado (§3.1.4 N2)
Resuelve elegantemente el problema de reproducibilidad desde pcap. Al transportar el contador en el evento Protobuf, el `flow_uid` se vuelve **determinista dado el evento**, inmune a reordenamiento de NIC, drops de ring buffer o diferencias de tcpreplay. Esto es la materialización práctica del principio §0.

### 1.3 libsodium congelada como única fuente de hash (§3.1.1 N5)
El invariante "la función de hash es la que provea la libsodium congelada del pipeline" es disciplina de stack ejecutada correctamente. Elimina el riesgo de drift entre C++ y Python y evita debates teológicos de algoritmo. BLAKE2b (en libsodium 1.0.19) es apropiado: rápido, nativo, y el argumento de length-extension no aplica porque el `flow_uid` no es un control de seguridad (§3.5).

### 1.4 Mapa de cobertura como cache declarativa, no MATCH en Neo4j (§3.8)
La decisión de representar la cobertura como **tabla/cache en Redis/etcd** y no como consulta Cypher por paquete es crítica para la viabilidad del sistema. Neo4j no es un lookup de alta frecuencia por evento; es un grafo de análisis. Separar la topología declarativa (fuente de verdad del orquestador) de la materialización en grafo (visualización) preserva el throughput del pipeline.

### 1.5 Cardinalidad exacta para etiquetado, probabilística solo para métricas (§3.10 N6)
Esta corrección elimina el riesgo de falsos positivos/negativos en la etiqueta `rate_limited` que alimenta el corpus. Con docenas de sensores y ventanas de 60s, un contador exacto en memoria es trivialmente factible y matemáticamente preferible.

### 1.6 Etiquetado ortogonal con WAL externo (§3.7 N4)
La arquitectura de no-repudio vía WAL append-only con hash-chain (soportado por etcd HA / ADR-048) y Neo4j como vista materializada es la única forma de garantizar integridad de etiqueta ante un motor comprometido. La interfaz está bien delimitada: el ADR define el contrato, no el binding concreto.

### 1.7 Score IPW normalizado por `expected_witnesses` (§3.6)
La fórmula `score = min(1.0, corroboration_count / expected_witnesses)` con `expected_witnesses` del mapa de cobertura resuelve el covariate shift por la puerta de atrás. Es la conexión matemática correcta entre el grafo de topología y el pipeline de entrenamiento (ADR-040).

---

## 2. Debilidades y parches propuestos

### 2.1 El WAL de etiquetado necesita esquema de serialización canónico

**Problema:** §3.7 N4 define un WAL externo append-only con hash-chain, pero no especifica el formato de las entradas. Si el sensor (C++) y el correlation-engine (Python) escriben entradas de etiquetado con esquemas distintos (ej. JSON ad-hoc vs. Protobuf), la hash-chain no es verificable cross-implementación y el corpus pierde reproducibilidad.

**Parche:** Especificar que el WAL usa **Protobuf con schema registry** (o MessagePack con esquema versionado) para las entradas de etiquetado. Cada entrada contiene:
```
wal_entry = { sequence: uint64, prev_hash: bytes[32], payload: TagEvent, timestamp: uint64, node_id: string }
hash = BLAKE2b( canonical_serialize(wal_entry_without_hash) )
```
El schema registry garantiza que todas las implementaciones serializan idénticamente antes de hashear.

**Tarea:** Añadir §3.7.1 "Serialización canónica del WAL de etiquetado".

---

### 2.2 `deployment_epoch` en `node_id` tiene riesgo de colisión generacional

**Problema:** El `node_id` usa `deployment_epoch` para marcar generaciones de despliegue. Si dos generaciones distintas reutilizan el mismo `declared_sensor_id` (ej. `argus-sensor-gw-lan-01`) con un `deployment_epoch` idéntico por error humano, los `flow_uid` de generaciones distintas colisionan y el corpus histórico se contamina.

**Parche:** Añadir una regla de orquestador: `deployment_epoch` debe ser **monótono creciente y único global** (ej. timestamp UNIX de la creación del manifiesto, o un contador central en etcd). El orquestador debe rechazar un manifiesto cuyo `(declared_sensor_id, deployment_epoch)` ya exista en el inventario.

**Tarea:** Añadir invariante en §3.1.2: "`deployment_epoch` es monótono y único global por `declared_sensor_id`; el orquestador lo valida contra el inventario histórico."

---

### 2.3 Calibración por protocolo: UDP necesita un `N` distinto o un `seq_in_window` obligatorio siempre

**Problema:** §3.1.4 pto 5 calibra `N` por protocolo. TCP tiene TIME-WAIT (~60s), pero UDP es stateless: un puerto efímero UDP puede reutilizarse inmediatamente tras cerrar el socket. Si `N=60s` para UDP, un cliente que haga DNS query (puerto 54321 → 53/udp) y luego inmediatamente otra query reutilizando el mismo puerto efímero, caería en el mismo bucket y requeriría `seq_in_window`. Esto funciona, pero **si el sensor pierde el estado del contador** (crash sin persistencia), el `seq_in_window` se reinicia y el segundo flujo colisiona con el primero en la reconstrucción offline.

**Parche:** Para UDP, considerar un `N` más agresivo (ej. 5s) **o** hacer que `seq_in_window` sea **persistido en disco por el sensor** (WAL local) con fsync periódico. Esto ya es una deuda implícita; debe ser explícita.

**Tarea:** Añadir nota en §3.1.4: "Para UDP, `seq_in_window` debe persistirse en disco local del sensor (WAL con fsync) para sobrevivir a reinicios; alternativamente, calibrar `N_UDP ≪ N_TCP`."

---

### 2.4 El meta-nodo `:GraphFloodingAnomaly` necesita especificación de esquema

**Problema:** §3.10 menciona que el flooding se colapsa en un meta-nodo `:GraphFloodingAnomaly` o `:HighCardinalityFlowCluster`. Pero no se define cómo se relaciona con los flujos individuales. ¿Es un nodo que agrupa muchos `:NetworkFlow` vía aristas `:PART_OF`? ¿O reemplaza a los flujos en el grafo? Si reemplaza, el corpus pierde granularidad.

**Parche:** Especificar que el meta-nodo es **aditivo**, no sustitutivo:
```cypher
(:GraphFloodingAnomaly {node_id, window, cid_count})-[:CONTAINS]->(:NetworkFlow)
```
Los flujos individuales **permanecen** en el grafo (retención, §0); el meta-nodo es una arista de agregación para queries de análisis. El corpus conserva la muestra atómica.

**Tarea:** Añadir §3.10.1 "Modelo del meta-nodo de flooding".

---

### 2.5 La señal TCP/TLS (§3.11) introduce una dependencia no modelada en el esquema P0

**Problema:** §3.11 añade nodos `:HostAnomaly` para RST, seq_num, TLS mismatch. Esto es conceptualmente correcto, pero el esquema P0 de Neo4j (DEBT-NEO4J-FLOW-KEY-001) debe incluir este nodo y sus aristas para que el grafo no quede incompleto. Si ADR-052 se ratifica con §3.11 pero el esquema P0 no lo contempla, hay un desfase.

**Parche:** Asegurar que `DEBT-NEO4J-FLOW-KEY-001` se actualice para incluir `:HostAnomaly` con propiedades `{agent_id, anomaly_type, layer, timestamp, evidence}` y aristas `:HOST_ANOMALY` → `:NetworkFlow` (coincidencia temporal) y `:OBSERVED_BY` → `:Sensor`. Esto no debe bloquear ADR-052, pero debe ser una tarea vinculada de cierre.

**Tarea:** Añadir tarea de esquema a la lista de deudas.

---

### 2.6 El documento está truncado

**Problema:** El archivo subido se corta en §5 ("co"). Faltan las alternativas rechazadas completas, las preguntas abiertas (§6), consecuencias (§7), validación (§8), deudas (§9) y referencias (§10). Aunque el contenido esencial de decisiones está en §3, la incompletitud impide verificar si las tareas accionables y la validación EMECAS++ se mantienen coherentes con v2.

**Parche:** No bloquear la ratificación por esto, pero exigir que la versión final subida al repositorio incluya las secciones 5–10 completas, con las tareas de la 2ª pasada incorporadas.

---

## 3. Respuestas a las preguntas de la 2ª pasada (§6 de v2)

### Q1 — Ratificación de §3.1.3 (identidad ≠ correlación cross-nodo)

**RATIFICADO POR EL CONSEJO (confirmación de fidelidad).** La v3 incorpora correctamente la ratificación. Dos sensores producen `flow_uid` distintos por diseño; el skew solo amenaza la arista `FLOW_IDENTITY`. El test EMECAS++ debe incluir el caso de dos sensores + arista correcta.

### Q2 — Diseño del mapa de cobertura de sensores

**RATIFICADO.** La v3 define el modelo como tabla/cache declarativa con fuente en el orquestador, validación por beacons, y uso en el correlation-engine como lookup (no MATCH en Neo4j). Esto es técnicamente correcto y escalable. La versión del mapa debe archivarse junto al corpus (ground truth de topología).

### Q3 — Calibración de `N` y `nat_confidence_floor`

**RATIFICADO CON PRECISIÓN ADICIONAL.** La v3 añade calibración por protocolo (arbitraje 6), que es la respuesta correcta. Se requiere la nota adicional sobre UDP (§2.3 arriba). La metodología sobre golden pcap (percentil de intervalo de reúso) es estadísticamente sólida.

### Q4 — Forma final del `trust_tier`

**RATIFICADO.** La v3 implementa la recomendación del Consejo: enum en el grafo (`trust_tier`) + score continuo (`ipw_weight`) en el pipeline ML. La fórmula con `expected_witnesses` es la conexión matemática correcta con ADR-040.

### Q5 — `provenance` y `acceptance_criteria.md`

**RATIFICADO.** La v3 mantiene la ortogonalidad: `provenance` es eje de etiquetado separado, no se mete `INJECTED` en el enum congelado de presencia. La ratificación 8/8 se refleja correctamente.

### Q6 — Fuente out-of-band para vector A con host comprometido

**RATIFICADO CON DOCUMENTACIÓN DEL LÍMITE.** La v3 mantiene §3.4.1 como límite fundamental documentado. Se recomienda abrir `DEBT-ARGUSPP-OOB-MITM-001` (P2) para port-security/Dynamic ARP Inspection en el switch, pero no bloquea ADR-052.

### Q7 — Señales de host más allá de L2 (TCP/TLS)

**VALIDADO EL ARBITRAJE.** Aunque la mayoría del Consejo recomendó diferir a ADR-053, la decisión de Alonso de incorporarlas en §3.11 es **técnicamente sostenible** porque: (a) el threat model sin detección es incompleto, (b) las señales son de primera clase y simples (no requieren fingerprinting profundo), (c) no alteran el esquema P0 de forma incompatible (solo añaden `:HostAnomaly`). **Condición:** §3.11 debe mantenerse estrictamente delimitado como está; cualquier señal adicional (JA3, BGP, traceroute) va a ADR-053 o backlog.

---

## 4. Tareas accionables derivadas (para cierre de v3)

| ID | Tarea | Prioridad | Dueño |
|---|---|---|---|
| **ADR-052-v3-A1** | Especificar serialización canónica del WAL de etiquetado (Protobuf + schema registry) | P0 | Backend/ADR-048 |
| **ADR-052-v3-A2** | Validar `deployment_epoch` monótono único global en el orquestador | P0 | Infra |
| **ADR-052-v3-A3** | Persistencia de `seq_in_window` en disco para UDP (WAL local con fsync) o calibrar `N_UDP` separado | P1 | Sensor/C++ |
| **ADR-052-v3-A4** | Especificar esquema del meta-nodo `:GraphFloodingAnomaly` (aditivo, no sustitutivo) | P1 | Backend/Grafo |
| **ADR-052-v3-A5** | Actualizar `DEBT-NEO4J-FLOW-KEY-001` para incluir nodo `:HostAnomaly` y aristas asociadas | P1 | Backend/Grafo |
| **ADR-052-v3-A6** | Completar secciones 5–10 del ADR (alternativas, preguntas, consecuencias, validación, deudas, refs) | P0 | Redacción |
| **ADR-052-v3-A7** | Test EMECAS++: paridad C++/Python de `flow_uid` + caso de dos sensores + arista `FLOW_IDENTITY` | P0 | QA |
| **ADR-052-v3-A8** | Calibrar `N_TCP` y `N_UDP` sobre golden pcap con tests dedicados | P1 | Data/ML |
| **ADR-052-v3-A9** | Crear `DEBT-ARGUSPP-OOB-MITM-001` (port-security en switch) | P2 | Red Team |

---

## 5. Veredicto del Consejo

**Estado recomendado:** `RATIFICAR v3` (con condiciones de cierre menores).

**Condiciones de cierre para la versión final:**
1. Incorporar los parches de las secciones 2.1–2.5 (especificación de WAL, `deployment_epoch`, UDP, meta-nodo, esquema `:HostAnomaly`).
2. Completar las secciones truncadas 5–10 con las tareas A1–A9 vinculadas.
3. Ejecutar el test de paridad C++/Python de `flow_uid` como gate de cierre (bloqueante).
4. Validar que `DEBT-NEO4J-FLOW-KEY-001` absorbe el esquema de `:HostAnomaly`.

**Evaluación:** La v3 es **fiel a las deliberaciones previas del Consejo** y corrige los huecos detectados. La dirección arquitectónica —corpus como producto, identidad compuesta reproducible, defensa arquitectónica, hash no como control de seguridad, etiquetado ortogonal con no-repudio— es correcta y estable. El ADR está listo para ratificación una vez completadas las secciones finales y las tareas de cierre.

---

*Dictamen de confirmación de fidelidad emitido por Kimi (Consejo de Sabios), DAY 173, revisión v3.*

FDO KIMI
