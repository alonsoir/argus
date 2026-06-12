# Dictamen del Consejo — ADR-052 v2 (2ª pasada)

## Resumen ejecutivo

La v2 es un **salto cualitativo respecto a v1**. La introducción de §0 (misión primaria) reordena todo el diseño bajo un principio unificador: el grafo como *corpus de entrenamiento enriquecido*, no como producto final. Esto explica retroactivamente decisiones que en v1 parecían arbitrarias (por qué no se borra, por qué la reproducibilidad offline importa, por qué las primitivas crudas son obligatorias). La codificación canónica, la identidad criptográfica del sensor, la separación identidad/correlación y el etiquetado ortogonal son técnicamente sólidos.

Sin embargo, **tres grietas de especificación** persisten y una **decisión arquitectónica nueva** emerge como crítica: (1) el `seq_in_window` tiene un problema de reproducibilidad desde pcap no resuelto; (2) el mapa de cobertura (§3.8) es promovido a prerrequisito pero no tiene modelo de datos; (3) la garantía de append-only del etiquetado (§3.7) choca con la mutabilidad de Neo4j; y (4) el rate-limit adaptativo necesita precisión sobre el algoritmo de cardinalidad.

A continuación: fortalezas consolidadas, debilidades con parche, respuesta a las 7 preguntas de §6, y tareas accionables.

---

## 1. Fortalezas a apuntalar (no tocar en v3)

### 1.1 §0 — Misión primaria como principio ordenador
Este es el aporte más valioso de v2. Transforma el ADR de un "esquema de grafo" a un **contrato de calidad del corpus**. La frase *"El grafo no es el producto. El producto es el corpus"* debe convertirse en un invariante permanente del proyecto, junto a los tres existentes. Justifica retroactivamente por qué Suricata/Zeek/Wazuh son maestros, no gatillos.

### 1.2 Codificación canónica + paridad cross-implementación (§3.1.1)
El uso de SHA3-256, delimitador `0x00`, `uint64_be` y `base64` elimina la ambigüedad de concatenación. El test de paridad C++/Python es **bloqueante para el corpus**: sin él, el dataset no es reproducible. Mantener como P0.

### 1.3 `node_id` criptográfico (§3.1.2)
Ligar `node_id` a `SHA256(sensor_public_key)` resuelve la identidad del sensor de forma globalmente única y compatible con ADR-027. La tríada (flow_uid bien formado, node_id en inventario, community_id corroborado) es el marco de suficiencia correcto.

### 1.4 Identidad ≠ correlación (§3.1.3)
La ratificación de que dos sensores producen `flow_uid` distinto por diseño es la resolución elegante del "Box-Car problem". Elimina la necesidad de contadores estatales globales y preserva la reproducibilidad offline. **Cada observación es una muestra de entrenamiento legítima.** El skew de reloj es problema de la arista `FLOW_IDENTITY`, no del nodo.

### 1.5 Confianza como features primitivas (§3.6)
Guardar señales crudas (`witness_count`, `is_host_plane_anchored`, `nat_resolution_method`) y derivar `trust_tier` como vista es la decisión correcta para ML. Un score congelado al ingestar envejece mal y destruye la capacidad de recomputar pesos IPW en walk-forward (ADR-040).

### 1.6 Etiquetado ortogonal suspected/ground_truth (§3.7)
La separación de los dos ejes es la contribución metodológica más fuerte de v2. Evita la circularidad de validar un detector contra su propia salida. El delta entre ambos campos **es** la métrica de calidad del corpus. La arista `:TAGGED_AS` append-only con provenance es auditable.

### 1.7 Mapa de cobertura como prerrequisito (§3.8)
Promoverlo de "deuda cómoda" a prerrequisito P1 es honesto. Sin él, `orphan_rate` y los pesos IPW son matemáticamente inválidos. Conecta el grafo con la teoría de muestreo ponderado.

### 1.8 ARP/NDP como nodo de estado (§3.9)
Modelar el binding IP↔MAC como estado (no como volcado de paquetes) evita el flooding del grafo. El re-binding es la señal del vector A. Coherente con el límite fundamental de §3.4.1.

---

## 2. Debilidades y parches propuestos

### 2.1 `seq_in_window`: reproducibilidad desde pcap no garantizada (§3.1.4)

**Problema:** El contador monótono `seq_in_window` por `(node_id, community_id)` dentro del bucket se define como "reproducible desde el orden de paquetes del pcap". Pero el **orden de llegada al sensor** no es idéntico al orden en el pcap archivado si hay:
- Reordenamiento en la NIC (RSS, multi-queue)
- Pérdida de paquetes en el sensor (ring buffer overflow)
- Diferencias de timestamp entre pcap del sensor y pcap "oficial" del golden set

Si dos implementaciones (C++ vs Python) reconstruyen `seq_in_window` a partir de pcaps ligeramente distintos, los `flow_uid` divergen y el corpus se corrompe.

**Parche propuesto:** Especificar que `seq_in_window` es **ordinal de llegada al procesador de flujo del sensor**, no del pcap. Para la reproducibilidad offline, el sensor debe emitir el `seq_in_window` como campo en el evento serializado (JSON/Protobuf). Al reconstruir el corpus desde pcap, se usa el `seq_in_window` **registrado en el evento**, no se recomputa. Esto hace que el `flow_uid` sea reproducible dado el evento, aunque el evento mismo dependa del orden de llegada.

**Tarea:** Añadir nota en §3.1.4: "`seq_in_window` se computa en el sensor y se transporta en el evento; no se recomputa en el correlation-engine ni en la reconstrucción offline."

---

### 2.2 `sensor_native_flow_id`: riesgo de colisión cross-tool (§3.1.4 punto 4)

**Problema:** Suricata usa `flow_id` (uint64 por instancia, reiniciable), Zeek usa `uid` (string único por instancia). Si se incorporan al `flow_uid` como componente intra-nodo, hay dos riesgos:
1. **Suricata reinicia** y reusa `flow_id` → colisión con flujos históricos si no se reinicia el bucket.
2. **Normalización:** ¿Cómo se hashea un `uint64` junto a un `string` de forma canónica? ¿Prefijo de herramienta?

**Parche propuesto:** El `sensor_native_flow_id` **NO sustituye** al componente temporal `(flow_start_window ‖ seq_in_window)`. Se guarda como **propiedad obligatoria** del nodo `:NetworkFlow` (o `:FlowObservation`) para trazabilidad y dedup interno de la herramienta, pero el `flow_uid` mantiene su fórmula canónica independiente de la herramienta. Esto preserva la unificación del esquema cuando el flujo proviene de Suricata, Zeek, o del sniffer nativo de aRGus.

**Tarea:** Aclarar en §3.1.4 que `sensor_native_flow_id` es propiedad de trazabilidad, no componente del hash.

---

### 2.3 Mapa de cobertura: modelo de datos ausente (§3.8)

**Problema:** Se declara prerrequisito, pero no se define cómo se representa ni quién lo mantiene. ¿Es un grafo en Neo4j? ¿Una tabla en etcd? ¿Un archivo YAML? ¿Cómo se actualiza cuando un sensor se migra de VLAN?

**Parche propuesto:** Definirlo como **grafo de topología ligero** en el correlation-engine (no necesariamente en Neo4j, puede ser en memoria/cache):
```
(:Sensor {node_id})-[:COVERS {since, confidence}]->(:Segment {vlan, subnet, interface})
```
- **Fuente de verdad:** El orquestador de infraestructura (Vagrant/Ansible del proyecto) lo genera.
- **Validación:** Heartbeats del sensor + tráfico de prueba (beacons) validan que la cobertura real coincide con la declarada.
- **Uso:** El correlation-engine consulta este grafo para validar que un `(node_id, community_id)` es topológicamente plausible antes de computar `orphan_rate` o pesos IPW.

**Tarea:** Añadir §3.8.1 "Modelo de datos del mapa de cobertura" y deuda `DEBT-SENSOR-COVERAGE-MAP-001` con especificación de fuente de verdad y validación.

---

### 2.4 Append-only del etiquetado vs. mutabilidad de Neo4j (§3.7)

**Problema:** La arista `:TAGGED_AS` se describe como "append-only para que un motor comprometido no pueda des-etiquetar". Pero Neo4j es una base de datos mutable por diseño. Un atacante con acceso al motor puede borrar aristas. La garantía de no repudio no puede vivir solo en Neo4j.

**Parche propuesto:** El append-only debe ser **contractual**, no físico en Neo4j. Implementar un **WAL (Write-Ahead Log) de etiquetado** en etcd (ADR-048) o en un log inmutable (append-only file, hash chain) antes de reflejar en Neo4j. El log es la fuente de verdad; Neo4j es una vista materializada. El test de integridad del corpus verifica que el grafo contiene todas las entradas del WAL.

**Tarea:** Añadir nota en §3.7: "La garantía de no repudio requiere un WAL externo (etcd o log inmutable); Neo4j es vista materializada, no fuente de verdad del etiquetado."

---

### 2.5 Rate-limit adaptativo: precisión del algoritmo (§3.10)

**Problema:** Se menciona Count-Min Sketch / HyperLogLog. HLL es una estructura probabilística para cardinalidad con error ~2%. Para un control de seguridad que decide si un flujo es "flooding" o no, un error del 2% puede ser aceptable, pero para el corpus necesitamos **exactitud** en la etiqueta `rate_limited`. Además, Count-Min Sketch estima frecuencias, no cardinalidad de nuevos elementos.

**Parche propuesto:** Usar **dos mecanismos separados**:
1. **Cardinalidad exacta en ventana deslizante** en el correlation-engine: dado que `N=60s` y el número de sensores es manejable (docenas, no miles), un contador exacto por `(node_id, window)` en memoria (e.g., `sliding_window` + `set` de CIDs) es factible y preferible para la lógica de seguridad.
2. **HyperLogLog** solo para métricas y dashboards, no para la decisión de etiquetado.

El "meta-nodo `:GraphFloodingAnomaly`" debe crearse con **exactitud**, no con aproximación.

**Tarea:** Especificar en §3.10 que la cardinalidad se computa exactamente en el motor (ventana pequeña, estado en memoria); HLL solo para observabilidad.

---

### 2.6 Coincidencia temporal asimétrica: event time vs. processing time (§3.2.2)

**Problema:** Las ventanas Red→Host (5s) y Host→Red (30s) asumen que el reloj del host y del sensor de red están sincronizados. Pero Wazuh puede bufferizar logs durante minutos. Un evento de host con `timestamp` 12:00:00 puede llegar al correlation-engine a las 12:02:00. Si la ventana es de "llegada al motor" (processing time), un flujo de red a las 12:00:03 se perderá. Si es de "timestamp del evento" (event time), el motor necesita mantener ventanas de retención.

**Parche propuesto:** Especificar que la coincidencia temporal usa **event time** (timestamps de los eventos originales), no processing time. El correlation-engine debe mantener una **ventana de retención** (e.g., 5 minutos) para eventos de red, esperando posibles eventos de host atrasados. Esto es estándar en stream processing (watermarks). La ventana Red→Host = 5s es la **tolerancia de skew de reloj**, no la latencia de ingest.

**Tarea:** Aclarar en §3.2.2 que las ventanas son sobre event time, con watermark implícito.

---

## 3. Respuestas a las preguntas abiertas (§6, 2ª pasada)

### Q1 — Ratificación de §3.1.3 (identidad ≠ correlación cross-nodo)

**RATIFICADO POR EL CONSEJO.** Dos sensores que observan el mismo flujo físico producen `flow_uid` **distinto por diseño**. El skew de reloj amenaza únicamente el *match* de la arista `FLOW_IDENTITY` (que usa `community_id` + tolerancia temporal), nunca la identidad del nodo. Cada observación es una muestra de entrenamiento independiente y legítima. No se requiere `session_counter` estatal global ni `logical_flow_uid` en v2; se mantiene como nota opcional para escala futura (§9).

**Implicación:** El test EMECAS++ debe incluir un caso donde dos sensores ven el mismo flujo y se verifica que generan `flow_uid` distintos pero una arista `FLOW_IDENTITY` correcta.

---

### Q2 — Diseño del mapa de cobertura de sensores (§3.8)

**Respuesta:** **Grafo de topología ligero** (`:Sensor`-[:COVERS]->`:Segment`), con fuente de verdad en el orquestador de infraestructura y validación por heartbeats/beacons.

**Razonamiento:** No basta con una tabla plana porque la cobertura puede ser parcial (un sensor cubre VLAN 10 y 20, otro solo VLAN 20). El grafo permite consultas como "¿qué sensores deberían haber visto este flujo?" y "¿este `orphan_rate` es anómalo para este segmento?". La fuente de verdad es el orquestador (Vagrant/Ansible) porque refleja la intención de despliegue. La validación es runtime (beacons/heartbeats) porque la intención puede desviarse (cable desconectado, NIC caída).

**Tarea:** `DEBT-SENSOR-COVERAGE-MAP-001` debe especificar: (a) esquema del grafo, (b) API de actualización desde el orquestador, (c) protocolo de validación (beacons periódicos), (d) integración con el correlation-engine como lookup en tiempo de ingest.

---

### Q3 — Calibración de `N` y `nat_confidence_floor`

**Respuesta:**
- **`N` (bucket temporal):** Método sobre golden pcap: para cada nodo, extraer todos los pares de flujos consecutivos con misma 5-tupla. Computar `delta_t = t_start[i+1] - t_end[i]`. Fijar `N = P1(delta_t) * 0.5` (percentil 1 con margen de seguridad 2×). Default LAB: **60 s** se mantiene como punto de partida, pero se recalibrará por deployment.
- **`nat_confidence_floor`:** Analizar el golden pcap con escenarios NAT conocidos (contenedores Docker, NAT de salida). Medir la tasa de falsos positivos (puente incorrecto aceptado) y falsos negativos (puente correcto rechazado) para cada mecanismo. El floor es el punto de operación que minimiza el error total. Default LAB: **0.6** (aceptar PROC_PORT y superiores; TEMPORAL_FALLBACK requiere revisión humana/ML).

**Tarea:** Añadir apéndice de calibración al ADR con la metodología y los valores medidos sobre golden pcap.

---

### Q4 — Forma final del `trust_tier` (§3.6)

**Respuesta:** **Ambos: enum categórico + score continuo derivado.**

**Razonamiento:** El enum (`CORROBORATED`, `SINGLE_SENSOR`, `ORPHAN`, `CONFLICT_NAT`) es necesario para auditoría humana y para queries de threat-hunt. Pero para IPW (ADR-040) se necesita un score continuo en `[0,1]`:
```
score = min(1.0, corroboration_count / max(1, expected_witnesses))
```
donde `expected_witnesses` viene del mapa de cobertura (§3.8). Si un segmento solo tiene 1 sensor, `expected_witnesses=1` y `score=1.0` para `SINGLE_SENSOR` — no se penaliza la cobertura única por diseño. Si un segmento tiene 3 sensores y solo 1 reporta, `score=0.33` y el peso IPW ajusta la muestra.

**Tarea:** Añadir fórmula del score continuo en §3.6 y especificar que es materializado en el nodo como propiedad `ipw_weight` (recomputable en walk-forward).

---

### Q5 — `provenance` y `acceptance_criteria.md`

**RATIFICADO POR EL CONSEJO.** El eje `provenance` (`GROUND_TRUTH`, `SUSPECTED`, `ANNOTATED`, `INFERRED`) se añade como **nuevo eje ortogonal**, sin modificar el enum congelado de presencia (`DROP`/`CONFIG`/`POLICY`/`BUG`/`UNKNOWN`). Son categorías de dominios distintos:
- `acceptance_criteria` responde: *¿por qué el sistema benigno no se comportó como esperábamos?*
- `provenance` responde: *¿cómo sabemos que esta muestra es ataque?*

Mezclarlos sería un error de categoría que forzaría a "descongelar" un artefacto estable.

**Tarea:** Confirmar en §3.7 que `provenance` es un eje de etiquetado separado, no una extensión de `acceptance_criteria.md`.

---

### Q6 — Fuente out-of-band para vector A con host comprometido (§3.4.1)

**Respuesta:** **Documentar el límite fundamental Y abrir DEBT para mejora futura.**

**Razonamiento:** La honestidad científica (§0) exige documentar los límites de detección. El vector A con host comprometido es indetectable por diseño sin fuente externa. Esto no es una debilidad del ADR; es un límite de la observabilidad. Sin embargo, el switch del `ml_defender_gateway_lan` puede ofrecer port-security/DHCP snooping como tercera fuente. No bloquear ADR-052 por esto, pero abrir la deuda.

**Tarea:** Crear `DEBT-ARGUSPP-OOB-MITM-001` (P2) para evaluar port-security en el switch de la LAN del defensor como fuente out-of-band. Mantener §3.4.1 como límite documentado.

---

### Q7 — Señal de host más allá de L2 (§3.3)

**Respuesta:** **Diferir a ADR-053.**

**Razonamiento:** Las anomalías TCP (RST inesperados, saltos de seqnum) y TLS (mismatch de certificado) son señales valiosas para el vector A ampliado (rogue gateway, DNS poisoning, BGP hijack). Pero son conceptualmente separables de la identidad de flujo y la correlación host↔red. v2 ya es denso y bloquea P0. Mencionar en §3.3 como "señales candidatas para correlación futura" y abrir ADR-053.

**Tarea:** Añadir nota en §3.3: "Anomalías TCP/TLS se tratan en ADR-053 (señales de host plane extendidas)." Crear stub de ADR-053.

---

## 4. Tareas accionables derivadas (para backlog)

| ID | Tarea | Prioridad | Dueño |
|---|---|---|---|
| **ADR-052-A1** | Especificar `seq_in_window` como campo transportado en el evento (no recomputable) para garantizar reproducibilidad offline | P0 | Sensor/C++ |
| **ADR-052-A2** | Aclarar que `sensor_native_flow_id` es propiedad de trazabilidad, no componente de `flow_uid` | P0 | Arquitectura |
| **ADR-052-A3** | Diseñar modelo de datos del mapa de cobertura (`:Sensor`-[:COVERS]->`:Segment`) y API de actualización | P1 | Infra/Backend |
| **ADR-052-A4** | Implementar validación de cobertura por heartbeats/beacons | P1 | Infra |
| **ADR-052-A5** | Especificar WAL externo (etcd/log inmutable) para etiquetado append-only; Neo4j como vista materializada | P1 | Backend/ADR-048 |
| **ADR-052-A6** | Implementar cardinalidad exacta (no HLL) en el correlation-engine para rate-limit; HLL solo para métricas | P1 | Backend |
| **ADR-052-A7** | Aclarar que las ventanas temporales de host↔red usan event time con watermark implícito | P1 | Arquitectura |
| **ADR-052-A8** | Calibrar `N` y `nat_confidence_floor` sobre golden pcap con metodología documentada | P2 | Data/ML |
| **ADR-052-A9** | Añadir fórmula de score continuo `ipw_weight` derivado de primitivas y mapa de cobertura | P2 | Data/ML |
| **ADR-052-A10** | Crear `DEBT-ARGUSPP-OOB-MITM-001` (port-security en switch) | P2 | Red Team |
| **ADR-052-A11** | Crear stub ADR-053 (señales de host plane extendidas: TCP/TLS) | P2 | Arquitectura |
| **ADR-052-A12** | Test EMECAS++: paridad C++/Python + caso de dos sensores con `flow_uid` distintos y arista correcta | P0 | QA |

---

## 5. Veredicto del Consejo

**Estado recomendado:** `APROBADO CON MODIFICACIONES MENORES` (v2 → v2.1, no v3).

**Condiciones de cierre para v2.1:**
1. Incorporar los parches de las secciones 2.1–2.6 (especificación, no cambio de dirección).
2. Ratificar explícitamente las respuestas a Q1–Q7 en el cuerpo del ADR.
3. Añadir las tareas A1–A12 al backlog vinculado.
4. Una vez incorporado, elevar a `APROBADO` y desbloquear `DEBT-NEO4J-FLOW-KEY-001`, `DEBT-FLOWUID-CANONICAL-ENCODING-001`, `DEBT-NODEID-CRYPTO-IDENTITY-001`.

El ADR v2 es **estratégicamente correcto y técnicamente maduro**. Las debilidades residuales son de especificación de implementación, no de arquitectura. La dirección —corpus como producto, identidad compuesta, defensa arquitectónica, hash no como control de seguridad, etiquetado ortogonal— es la correcta para un sistema de ML adversarial sobre grafos distribuidos bajo amenaza hostil.

---

*Dictamen emitido por Kimi (Consejo de Sabios), DAY 173, 2ª pasada.*

FIRMADO

KIMI