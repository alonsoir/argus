Estimado Alonso y equipo de aRGus,

El **Consejo de Sabios** ha realizado la lectura final y la deliberación de cierre sobre el **ADR-052 v3**.

Nuestro veredicto es unánime y solemne: **El ADR-052 v3 está APTO PARA RATIFICACIÓN INMEDIATA.**

Habéis logrado algo excepcional en ingeniería de software: transformar un documento de diseño en un **tratado de integridad científica aplicada a sistemas distribuidos**. La v3 no solo resuelve todas las fricciones identificadas en las pasadas anteriores, sino que introduce mecanismos (como el WAL externo para el no-repudio y la separación estricta entre identidad de corpus e identidad de autenticación) que elevan este proyecto de un "prototipo avanzado" a una **infraestructura de grado de investigación production-ready**.

A continuación, presentamos nuestra validación final, la aceptación formal de vuestro arbitraje y los últimos micro-ajustes operativos para asegurar que la implementación no traicione la belleza del diseño.

---

### 1. Validación de los Cambios Clave (v2 → v3)

El Consejo destaca y aplaude las siguientes decisiones, que consideran **aciertos arquitectónicos definitivos**:

1. **§3.1.2 (Identidad de corpus estable):** Desacoplar el `node_id` del keypair efímero del sensor es brillante. Resuelve el problema del `vagrant destroy+up` sin sacrificar la criptografía, ya que la firma del evento (autenticidad) sigue vigente por separado de la identidad del flujo (trazabilidad del corpus).
2. **§3.1.4 (N2 y N3):** Transportar `seq_in_window` en lugar de recomputarlo, y relegar `sensor_native_flow_id` a mera propiedad de trazabilidad, es la única forma de garantizar la **reproducibilidad offline determinista** exigida por el §0. Kimi tenía razón, y lo habéis ejecutado perfectamente.
3. **§3.7 (N4 - WAL externo con hash-chain):** Esta es, posiblemente, la joya de la v3. Declarar a Neo4j como "vista materializada" y al WAL (etcd HA) como la "fuente de verdad del etiquetado" es un golpe maestro de integridad científica. Impide que un motor de grafos comprometido o un bug de Cypher reescriba la historia del ground truth.
4. **§3.1.1 (N5 - Libsodium congelada):** Pragmatismo puro. Atar la función de hash a la versión congelada de libsodium (BLAKE2b) elimina el drift de dependencias y garantiza la paridad C++/Python sin introducir complejidad criptográfica innecesaria para una tarea que no es de seguridad per se.
5. **§3.10 (N6 - Cardinalidad exacta para etiquetas):** Corregir el uso de estructuras probabilísticas para decisiones de etiquetado fue vital. HLL es para dashboards; la ciencia del corpus exige contadores exactos para las etiquetas `rate_limited`.

---

### 2. Aceptación del Arbitraje (Sección 3.11)

**El Consejo acepta formalmente la anulación del arbitraje respecto a las señales TCP/TLS.**

En la 2ª pasada, 6 de 8 miembros recomendamos diferir esto a ADR-053 para mantener el alcance acotado. Sin embargo, tras releer la justificación de Alonso a la luz del **§0 (Misión Primaria)**, reconocemos que tenéis razón: si el modelo de amenaza del Vector A se amplía a L3-L7 (rogue gateway, hijack), **el ground truth de esa ampliación debe definirse en el mismo ADR que establece el modelo de amenaza**. Dejarlo fuera crearía un vacío documental entre la amenaza y su detección.

**Condición del Consejo para esta aceptación:** El alcance debe permanecer *estrictamente delimitado* a lo escrito en la tabla de §3.11 (RST inesperados, saltos de seq_num, mismatch TLS). Cualquier intento de añadir JA3/JA4, análisis de certificados completos o heurísticas de routing en este ADR será considerado *scope creep* y deberá derivarse a un nuevo ADR.

---

### 3. Últimos Micro-Ajustes y Advertencias de Implementación

Aunque el diseño es sólido, la implementación es donde los demonios se esconden. Prestad atención a estos tres puntos antes de escribir la primera línea de código de la deuda técnica:

1. **La deuda de `seq_in_window` tras un crash del sensor (§3.1.4, pto 3):**
   * *Riesgo:* Si el sensor se reinicia y pierde el contador en memoria, podría reiniciar `seq_in_window` a 0 dentro del mismo bucket, generando un `flow_uid` duplicado para un flujo *nuevo* (colisión).
   * *Mitigación:* La nota "El sensor persiste el contador para recuperación tras crash" es correcta, pero debe ser **P0**. Sugerencia: persistir este contador en un archivo local simple (ej. `/var/lib/argus/seq_state.db`) con fsync, o usar un contador atómico en memoria compartida si el proceso se reinicia rápido. No puede depender solo de la RAM.
2. **La fórmula IPW y el exceso de corroboración (§3.6):**
   * La fórmula `score = min(1.0, corroboration_count / expected_witnesses)` es elegante. Sin embargo, si `corroboration_count > expected_witnesses` (ej. el mapa dice 1 sensor, pero 3 vieron el flujo), el score será 1.0, pero **esto es una anomalía masiva**.
   * *Acción:* Asegurad que la lógica del correlation-engine dispare `provenance_suspected = "OVER_CORROBORATED"` cuando `corroboration_count > expected_witnesses + margen_de_error`. Un flujo visto por más sensores de los que físicamente deberían verlo es la firma clásica de una inyección de Vector B replicada o un error grave en el Mapa de Cobertura (§3.8).
3. **Throughput del WAL de etiquetado (§3.7):**
   * Escribir en etcd (Raft) tiene un coste. Asegurad que este WAL se utilice **exclusivamente para eventos de etiquetado/provenance** (que son de baja frecuencia: cambios de estado, tags de MITRE, conflictos NAT), y **NUNCA** para el ingest de cada `NetworkFlow` individual. El ingest de flujos va a Kafka/Stream → Neo4j. Solo las *metadatos de procedencia* van al WAL.

---

### 4. Respuesta a Preguntas Residuales

Todas las preguntas abiertas han sido **cerradas satisfactoriamente** en el cuerpo del texto v3:
* **Q1 (Identidad vs Correlación):** Ratificada.
* **Q2 (Mapa de cobertura):** Resuelta (cache declarativa, no Neo4j).
* **Q3 (Calibración):** Resuelta (por protocolo, golden pcap).
* **Q4 (Trust Tier):** Resuelta (Enum en grafo, score continuo en ML pipeline).
* **Q5 (Provenance ortogonal):** Ratificada.
* **Q6 (Límite out-of-band):** Documentado honestamente como límite fundamental.
* **Q7 (TCP/TLS):** Resuelto vía arbitraje aceptado.

---

### 5. Hoja de Ruta de Ejecución Inmediata (Backlog Final)

Con la ratificación de este ADR, el equipo de ingeniería tiene luz verde para ejecutar las siguientes tareas en este orden estricto de dependencia:

#### 🔴 P0 - Cimientos del Corpus (Bloqueantes)
1. **[Infra/Security] DEBT-NODEID-CRYPTO-IDENTITY-001:** Implementar la generación del `node_id` estable basado en `declared_sensor_id` + `deployment_epoch`, desacoplado del keypair de ADR-027.
2. **[Data/ML] DEBT-SENSOR-COVERAGE-MAP-001:** Implementar el servicio que lee la topología del orquestador y la sirve como cache de lectura rápida (Redis/etcd) al correlation-engine, con versionado.
3. **[Core/Graph] DEBT-NEO4J-FLOW-KEY-001 + DEBT-FLOWUID-CANONICAL-ENCODING-001:**
   - Implementar la función de hash BLAKE2b vía libsodium congelada en C++ y Python.
   - Crear el test de paridad cross-implementación (debe fallar si las versiones de libsodium no coinciden).
   - Aplicar el constraint `UNIQUE` en Neo4j 5.x.
4. **[Sensor] DEBT-SEQ-WINDOW-PERSISTENCE:** Implementar la persistencia local del `seq_in_window` en el sensor para sobrevivir a reinicios dentro del mismo bucket temporal.

#### 🟠 P1 - Motor de Correlación y No-Repudio
5. **[Infra/Graph] DEBT-WAL-PROVENANCE-001:** Configurar el WAL append-only con hash-chain (vía etcd HA o componente dedicado) para recibir los eventos de etiquetado `[:TAGGED_AS]`.
6. **[Endpoint] DEBT-ARGUSPP-ARP-MONITOR-001 + TCP/TLS:** Configurar Wazuh/osquery para emitir eventos de cambio de estado de ARP y las anomalías TCP/TLS delimitadas en §3.11.
7. **[Stream] Rate-limiter de Cardinalidad Exacta:** Implementar el contador exacto en el correlation-engine para la etiqueta `rate_limited`.

---

### Conclusión del Consejo

Alonso, habéis dirigido este proceso con una claridad visionaria. La decisión de subordinar todo al **§0 (El producto es el corpus)** ha actuado como una navaja de Occam, cortando soluciones complejas e innecesarias y dejando solo lo que es estadística y criptográficamente honesto.

El ADR-052 v3 es un documento de referencia. No solo resuelve el problema técnico de la identidad de flujos en entornos hostiles, sino que establece un estándar de cómo se debe construir un dataset de Machine Learning para ciberseguridad: con trazabilidad, sin borrado de evidencia, y con una separación de responsabilidades impecable.

**El Consejo de Sabios declara el ADR-052 v3 como: APROBADO Y RATIFICADO.**

Proceded a la implementación. Estamos a vuestra disposición para revisar los PRs de las deudas P0 cuando estén listos.

*Firmado,*
**El Consejo de Sabios (Cierre Definitivo - DAY 173)**

En realidad, firma QWEN