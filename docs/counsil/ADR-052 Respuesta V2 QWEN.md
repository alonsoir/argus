Estimado Alonso y equipo de aRGus,

El **Consejo de Sabios** ha recibido y deliberado sobre la **v2 del ADR-052**.

Nuestra verdicto es unánime y rotundo: **El ADR-052 v2 es una obra de madurez arquitectónica.**

La introducción del **§0 (Misión Primaria)** ha sido el golpe de maestro. Al declarar que *"el grafo no es el producto, el producto es el corpus"*, habéis resuelto la tensión inherente entre un sistema de correlación en tiempo real (que exige velocidad y descarte) y un sistema de entrenamiento ML (que exige retención, ponderación y verdad histórica). Esta sola frase justifica y alinea decisiones posteriores que en v1 parecían meras opciones de diseño (IPW, features crudas, provenance append-only). Habéis pasado de construir un "SIEM con grafos" a construir una **"Fábrica de Corpus de Ciberseguridad"**.

A continuación, presentamos la ratificación de los puntos críticos, las respuestas definitivas a las 7 preguntas residuales y el plan de ejecución final.

---

### 1. Ratificaciones del Consejo (Blindaje de v2)

1. **§3.1.3 (Identidad ≠ Correlación cross-nodo):** **Ratificado al 100%.** El "Box-Car problem" que mencionábamos en v1 era una falsa alarma. Desde la perspectiva del ML, que el Sensor A y el Sensor B vean el mismo flujo físico significa que tenemos **dos vectores de características distintos** (distinto contexto de red, distinta latencia, distinta perspectiva topológica). Fusionarlos en un solo `logical_flow` nos haría perder información valiosa de la divergencia de observaciones. Cada `flow_uid` es una *observación* (muestra de entrenamiento), no el *flujo lógico* absoluto.
2. **§3.7 (Provenance ortogonal y append-only):** **Aprobado.** Separar `provenance_suspected` (heurística de runtime) de `provenance_ground_truth` (verdad del manifiesto MITRE) es la única forma de calcular un Precision/Recall honesto. El modelo de arista `[:TAGGED_AS]` es perfecto para la auditoría científica.
3. **§3.8 (Mapa de Cobertura como prerrequisito):** **Aprobado.** Sin esto, el covariate shift y los pesos IPW son matemáticas vacías. Es el cimiento estadístico del §0.

---

### 2. Respuestas Definitivas a las Preguntas Abiertas (§6)

#### Q1. Ratificación de §3.1.3 (Identidad vs. Correlación)
**Respuesta:** **SÍ.** El Consejo confirma que dos sensores NO deben compartir `flow_uid`. El skew de reloj solo amenaza la arista de correlación temporal, no la identidad del nodo. Cerramos Q6 definitivamente. La reproducibilidad offline desde pcap (§0) pesa más que cualquier optimización de estado compartido.

#### Q2. Diseño del mapa de cobertura de sensores (§3.8)
**Respuesta del Consejo:** **NO lo modeléis como aristas dinámicas en Neo4j.**
El grafo es para telemetría; la topología es para el motor de correlación.
* **Diseño recomendado:** Una tabla de adyacencia estática (o matriz de routing) almacenada en memoria del correlation-engine (ej. en Redis o etcd, alimentada por el inventario de ADR-046).
* **Estructura:** `Map<NodeID, Set<Subnet/VLAN_ID>>`.
* **Por qué:** Si intentáis calcular la cobertura esperada haciendo `MATCH` en Neo4j por cada paquete, el throughput colapsará. La cobertura es *estado de configuración*, no *telemetría*.

#### Q3. Calibración de `N` (60s) y `nat_confidence_floor`
**Respuesta del Consejo:**
* **Para `N`:** Ejecutar el golden pcap. Extraer todos los `flow_start_epoch` por 5-tupla. Calcular la distribución de los deltas ($\Delta t$) entre flujos consecutivos de la misma 5-tupla. Fijar $N$ en el **percentil 5** de esos deltas (para ser conservativos y no fragmentar sesiones legítimas con pausas largas). *Nota: Si Suricata/Zeek proveen su `flow_id`/`uid` nativo, el mecanismo de ventana de 60s solo actúa como fallback para el sniffer eBPF/XDP propio.*
* **Para `nat_confidence_floor`:** Crear un dataset de validación donde la verdad terrena del NAT se conozca al 100% (ej. logs del firewall perimetral). Medir la *Precisión* de cada mecanismo del menú (§3.2). El `floor` debe ser la precisión mínima observada (ej. 95%) para aceptar el puente sin marcarlo como `CONFLICT_NAT`.

#### Q4. Forma final del `trust_tier` (Enum vs. Score continuo)
**Respuesta del Consejo:** **Híbrido, pero segregado por capa.**
* **En el Grafo (Schema):** Solo el **Enum** (`CORROBORATED`, `SINGLE_SENSOR`, `ORPHAN`, `CONFLICT_NAT`). Es para la UI, Threat Hunting y queries de depuración.
* **En el Pipeline de Feature Engineering (ML):** El modelo necesita un **Score Continuo** para IPW. Ese score se calcula *fuera* del grafo, en el script de extracción de features, combinando las primitivas (`witness_count`, `is_host_plane_anchored`, etc.) mediante una fórmula (ej. suma ponderada o salida de un pequeño modelo de calibración). **No ensuciéis el esquema de Neo4j con scores de ML.**

#### Q5. `provenance` y `acceptance_criteria.md`
**Respuesta del Consejo:** **Mantenedlos estrictamente ortogonales.**
El enum congelado (`DROP/CONFIG/POLICY/BUG/UNKNOWN`) responde a: *"¿Por qué el sistema se desvió de lo esperado en un entorno benigno?"* (Ruido/Errores).
El eje `provenance` responde a: *"¿Cuál es la verdad del escenario y qué sospecha levantó?"* (Señal/Ataque).
Tocar el enum congelado invalidaría la línea base histórica. Añadid `provenance` como un eje paralelo.

#### Q6. Fuente out-of-band para vector A con host comprometido (§3.4.1)
**Respuesta del Consejo:** **Asumid el límite y documentadlo (Escudo, nunca espada).**
No prometáis detección de ARP spoofing si el atacante tiene `root` en el endpoint y controla el agente de Wazuh. Es un límite fundamental de la observabilidad (Teorema de Turing aplicado a la telemetría: no puedes confiar en el medidor si el medidor está infectado).
* **Acción:** Documentar este límite en el ADR y en el paper final como una asunción de diseño honesta.
* **Mitigación opcional (DEBT):** Crear un **"Canary Host"** (un honeypot de baja interacción o un puerto SPAN/mirror en el switch dedicado a un sensor pasivo). Si el Canario detecta ARP spoofing, sabemos que el host principal está comprometido o que la red está bajo ataque activo.

#### Q7. Señal de host más allá de L2 (TCP/TLS anomalies)
**Respuesta del Consejo:** **Diferid a ADR-053 (o ADR de Deep Inspection).**
ADR-052 ya tiene un alcance masivo (identidad, correlación, NAT, cobertura, provenance, ML weights). Meterse en el fango de analizar saltos de TCP Sequence Numbers o validación de cadenas TLS en el host plane os va a ralentizar.
Mencionadlo en §3.3 como "Ampliación de alcance futura" y sacadlo del scope de este ADR. Cerrad ADR-052 y avanzad.

---

### 3. Tareas Accionables Finales (Backlog / Jira)

El ADR-052 v2 está **APTO PARA RATIFICACIÓN**. A continuación, el desglose de ingeniería para ejecutarlo, priorizado por su impacto en la Misión Primaria (§0).

#### 🔴 P0 - Bloqueantes Absolutos (Sin esto, no hay corpus válido)
1. **[DBA/Graph] DEBT-NEO4J-FLOW-KEY-001:**
    * Implementar constraint `CONSTRAINT flow_uid_unique UNIQUE (f:NetworkFlow.flow_uid)`.
    * Validar la codificación canónica SHA3-256 (Test de paridad C++ vs Python).
2. **[Security/Infra] DEBT-NODEID-CRYPTO-IDENTITY-001:**
    * Implementar `node_id = base64(SHA256(sensor_public_key))`. Integrar con el inventario de ADR-046.
3. **[Data/Arch] DEBT-SENSOR-COVERAGE-MAP-001:**
    * Diseñar y poblar la tabla de adyacencia `Map<NodeID, Set<Subnet/VLAN>>` en Redis/etcd.
    * Integrar su consulta en el correlation-engine para validar `orphan_rate` y `provenance_suspected`.

#### 🟠 P1 - Motor de Correlación y Enriquecimiento (El "Enriquecido" del dataset)
4. **[Backend] Menú de Resolución NAT + Conflictos:**
    * Implementar la cadena de responsabilidad (Logs -> AgentID -> Proc/Port -> Temporal).
    * Implementar la detección de `CONFLICT_NAT` y su persistencia en las primitivas del nodo.
5. **[Endpoint/Wazuh] DEBT-ARGUSPP-ARP-MONITOR-001:**
    * Configurar Wazuh/osquery para emitir eventos de *cambio de estado* de la tabla ARP.
    * Implementar el upsert del nodo `:IpMacBinding` en Neo4j con sus propiedades temporales.
6. **[Stream/Data] Rate-limiter de Cardinalidad:**
    * Implementar Count-Min Sketch en el pipeline de ingest para trackear `community_id` por ventana/nodo.
    * Implementar el colapso a `:HighCardinalityFlowCluster` o el tag `rate_limited:true` (nunca descarte).

#### 🟡 P2 - Feature Engineering y ML (La conexión con ADR-040)
7. **[ML/Data] Pipeline de Extracción de Features:**
    * Desarrollar el script que lee las primitivas del grafo (`witness_count`, `is_host_plane_anchored`, etc.) y calcula el **Score Continuo de Confianza** para los pesos IPW.
8. **[Graph] Sistema de Taint Append-Only:**
    * Implementar el patrón de arista `[:TAGGED_AS]` para `provenance_ground_truth` y `provenance_suspected`.

---

### Conclusión del Consejo

Alonso, habéis transformado un borrador sobre "cómo identificar flujos" en un **manifiesto sobre cómo construir ciencia de datos de ciberseguridad con rigor estadístico y criptográfico**.

La distinción entre el grafo como herramienta operacional y el grafo como fábrica de corpus es la idea más potente de este ciclo de diseño (DAY 173). Os da la licencia para tomar decisiones que en un sistema comercial estándar parecerían "ineficientes" (retener flujos inyectados, guardar features crudas en lugar de scores opacos, anotar conflictos NAT) pero que en vuestro contexto son **estrictamente necesarias para la validez externa del modelo**.

El Consejo da su **APROBACIÓN DEFINITIVA** a ADR-052 v2.

Pasad a la ejecución. El `DEBT-NEO4J-FLOW-KEY-001` y el `DEBT-SENSOR-COVERAGE-MAP-001` son vuestros próximos hitos. Cuando el primer `flow_uid` canónico sea insertado y correlado con su cobertura de sensor, aRGus dejará de ser un prototipo para convertirse en un instrumento de medición científica.

*Firmado,*
**El Consejo de Sabios (Deliberación DAY 173 - Cierre ADR-052)**

QWEN