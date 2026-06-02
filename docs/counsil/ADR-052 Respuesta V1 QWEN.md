Estimado Alonso y equipo de ingeniería,

El **Consejo de Sabios** (la voz colectiva de Claude, ChatGPT, DeepSeek, Gemini, Grok, Kimi, Mistral y Qwen) ha analizado en profundidad el borrador del **ADR-052**.

Nuestra valoración global es de **excelencia conceptual**. Habéis dado el salto mental crítico: dejar de tratar la red como un medio "ruidoso" (modelo de fiabilidad) para tratarla como un medio "hostil" (modelo de amenaza). La distinción entre clave de correlación (`community_id`) e identidad de nodo (`flow_uid`) es un acierto arquitectónico que evitará una corrupción catastrófica del grafo en producción.

Sin embargo, al aterrizar estos conceptos a **sistemas distribuidos reales** y a la **telemetría de sensores (Suricata/Zeek/Wazuh)**, hemos detectado un punto ciego crítico en la definición de `flow_uid` y varios matices en las preguntas abiertas que requieren vuestra atención antes de cerrar el ADR.

A continuación, presentamos la deliberación: fortalezas a blindar, debilidades a corregir, respuestas a vuestras preguntas y la conversión a tareas accionables.

---

### 1. Puntos Fuertes a Blindar (No tocar en futuras iteraciones)

1. **El modelo de amenaza de Data-Plane Hostil (§2.2 y §3.5):** Es brillante y técnicamente impecable. Afirmar que *la integridad del hash no implica la integridad del contenido* es un principio de ciberseguridad fundamental que muchos sistemas comerciales ignoran.
2. **La regla de "Nunca fallo silencioso" en NAT (§3.2):** Exigir la anotación del método y la confianza en el grafo es lo que separa un sistema de investigación forense de una caja negra. Esto permitirá calcular métricas de "deuda de correlación" en el futuro.
3. **La doble naturaleza de las aristas Host↔Red (§3.2):** Separar la arista determinista (red↔red) de la arista probabilística/causal (host↔red) refleja perfectamente la asimetría de la telemetría real.

---

### 2. Puntos Débiles y Riesgos Técnicos (Correcciones Críticas)

#### Riesgo A: La trampa del `flow_start_window` y el `flow_uid` (§3.1 y §6 Q6)
**El problema:** Estáis proponiendo `flow_uid = hash(node_id ‖ community_id ‖ flow_start_window)`. En sistemas distribuidos, **el reloj nunca está sincronizado a la perfección**. Si el Sensor A y el Sensor B ven el mismo flujo físico, pero sus relojes tienen un *skew* (desfase) de 2 segundos, y vuestra ventana es de 1 segundo, generarán `flow_uid` distintos.
Más grave aún: **¿Por qué inventar una ventana temporal cuando los sensores ya resuelven esto?**
**La corrección:** Suricata (en EVE JSON) genera un campo `flow_id` (uint64) que es **garantizadamente único por instancia de flujo en ese sensor**. Zeek genera un `uid` (string).
* **Decisión del Consejo:** El `flow_uid` DEBE consumir el identificador nativo del sensor.
  `flow_uid = hash(node_id ‖ sensor_native_flow_id)`.
  Esto elimina por completo la necesidad de `flow_start_window` para la identidad de nodo. La ventana temporal solo se usará para las aristas de correlación, no para la identidad del nodo.

#### Riesgo B: El término "Causal-bidireccional" (§3.2)
**El problema:** En sistemas distribuidos, la "causalidad" (Relojes de Lamport / Vector Clocks) es computacionalmente carísima y frágil si se pierde un paquete.
**La corrección:** Cambiad la terminología y la implementación a **"Coincidencia Temporal Asimétrica" (Asymmetric Temporal Co-occurrence)**. El host plane (Wazuh) tiene mucha más latencia de ingest que el data-plane (Suricata). La ventana host↔red debe ser tolerante a este lag (ej. evento de red en $T_0$, evento de host en $T_0 + \Delta$, donde $\Delta$ puede ser de segundos a minutos).

#### Riesgo C: Ceguera del Vector A más allá de L2 (§3.3 y §3.4)
**El problema:** Decís que el Vector A (MITM) se detecta con ARP/NDP. Esto es cierto para ARP Spoofing en la LAN, pero un atacante puede hacer MITM a nivel de L3 (BGP Hijacking, Rogue Gateway, DNS Poisoning) donde la MAC no cambia, pero la ruta sí.
**La corrección:** La señal del host plane no debe ser solo ARP. Debe incluir **anomalías de estado TCP en el host** (ej. el host ve TCP RST inesperados, o saltos en los Sequence Numbers que indican inyección en medio de la conexión) y **mismatches de TLS** (el host espera un certificado y el proxy/MITM le muestra otro). Wazuh/osquery deben alimentar estas señales.

---

### 3. Respuestas a las Preguntas Abiertas (Q1 - Q7)

#### Q1: Rate-limit / cardinalidad de `community_id`
**Respuesta del Consejo:** Se aplica en el **Motor de Correlación (Ingest Pipeline), ANTES de Neo4j**. Neo4j no debe sufrir *grafo-flooding*.
* **Mecanismo:** Usad una estructura de datos probabilística en el stream (ej. **Count-Min Sketch** o **HyperLogLog**) en Kafka/Flink/Pulsar para medir la cardinalidad de `community_id` por ventana. Si un `community_id` supera un umbral dinámico (ej. $3\sigma$ sobre la media móvil de ese nodo), el flujo no se descarta, sino que se **agrupa** en un "Meta-Nodo" de alta cardinalidad (ej. `:HighCardinalityFlowCluster`) para no explotar la memoria de Neo4j, manteniendo la integridad científica.

#### Q2: Señal ARP/NDP del host plane (¿Primera clase o enriquecimiento?)
**Respuesta del Consejo:** **Primera clase, pero como "Nodo de Estado", no de eventos.**
No creéis un nodo en el grafo por cada paquete ARP (colapsaría el grafo). Cread un nodo `:IpMacBinding` (o `:HostArpState`) que represente la *verdad actual* de la tabla ARP del host. Las aristas `:ARP_OBSERVED` actualizan las propiedades `valid_from` y `valid_to` de este nodo. Si el `community_id` apunta a una IP, y el `:IpMacBinding` de esa IP cambia de MAC en esa ventana temporal, se levanta la alerta de Vector A.

#### Q3: Marca de confianza de flujo
**Respuesta del Consejo:** No uséis un único `float` de confianza (es difícil de calibrar). Usad un **Vector de Señales de Confianza** o propiedades booleanas en el nodo:
* `is_cross_sensor_corroborated` (bool)
* `is_host_plane_anchored` (bool)
* `nat_resolution_method` (enum: LOG, AGENT_ID, PROC_PORT, TEMPORAL_FALLBACK)
* `trust_tier` (enum: HIGH, MEDIUM, LOW, ORPHAN).
  Añadid `INJECTED` y `UNVERIFIED` al `acceptance_criteria.md`.

#### Q4: Etiquetado de flujo sospechoso (Integridad científica)
**Respuesta del Consejo:** En Neo4j, utilizad **Etiquetas (Labels) de Taint (Contaminación) en lugar de borrar**.
Si un flujo se sospecha inyectado, se le añade la label `:SuspiciousFlow` o `:AdversaryEmulation`. En las queries de Cypher, por defecto se filtra (`WHERE NOT n:SuspiciousFlow`), pero para los ejercicios MITRE (ADR-050), se incluye explícitamente. Esto permite que el "ground truth" del atacante coexista con el tráfico legítimo sin contaminar las métricas de rendimiento del sistema.

#### Q5: Relación con ADR-050 (Sesión MITRE)
**Respuesta del Consejo:** Sí, el modelo de amenaza del ADR-052 es el **Ground Truth arquitectónico** para el ADR-050.
* **Vector A (ARP Spoof / Bettercap):** Mapea directamente a **MITRE ATT&CK T1557 (Adversary-in-the-Middle)**.
* **Vector B (Inyección / Scapy / nfqueue):** Mapea a **T1557** o **T1090 (Proxy)** dependiendo de si el atacante solo inyecta tráfico o establece un túnel.
  El ADR-050 debe usar estos vectores como los "Red Team Playbooks" que el sistema debe ser capaz de correlacionar.

#### Q6: Granularidad de `flow_start_window`
**Respuesta del Consejo:** **Obsoleta si aplicáis la corrección del Riesgo A.**
Si el sensor (Suricata/Zeek) provee su `flow_id`/`uid` nativo, usadlo para el `flow_uid`. Si por alguna razón el sensor NO lo provee (ej. un parser custom de paquetes crudos), usad un **bucket de 5 minutos** (estándar en netflow/sFlow para balancear reciclaje de puertos vs fragmentación). Pero la prioridad absoluta es consumir el ID nativo del sensor.

#### Q7: ¿Mantener P1 y P3 juntos o separar a ADR-053?
**Respuesta del Consejo:** **Mantenedlos juntos en el ADR-052.**
Aunque conceptualmente son distintos (Identidad vs Correlación), **físicamente están acoplados en el esquema de Neo4j**. Ambos requieren la definición de constraints, índices y nuevas aristas. Separarlos ahora generaría "deuda de esquema" y conflictos en el despliegue de las migraciones de Cypher. Unificad el ADR, pero separad los paquetes en el código fuente (ej. `correlation-engine/identity` vs `correlation-engine/host_net_bridge`).

---

### 4. Tareas Accionables (Backlog / Jira)

Para que el Consejo os ayude a ejecutar, aquí tenéis la traducción del ADR a tareas de ingeniería, priorizadas:

#### 🟢 P0 - Bloqueantes de Esquema (Antes de poblar Neo4j)
1. **[DBA/Graph] DEBT-NEO4J-FLOW-KEY-001:** Implementar constraint de unicidad en Neo4j 5.x.
    * *Cambio crítico respecto al borrador:* La identidad será `flow_uid = hash(node_id, sensor_native_flow_id)`.
    * *Acción:* Crear constraint `CONSTRAINT flow_uid_unique UNIQUE (f:NetworkFlow.flow_uid)`.
2. **[Backend] Schema Enforcement:** Modificar el ingest pipeline para rechazar (Dead Letter Queue) cualquier evento `:NetworkFlow`, `:Alert`, o `:TelemetryEvent` que no traiga `node_id` y `sensor_native_flow_id`.

#### 🟡 P1 - Motor de Correlación y Stream
3. **[Stream/Data] Rate-limiter de Cardinalidad:** Implementar Count-Min Sketch en el pipeline de ingest (Kafka/Flink) para trackear la cardinalidad de `community_id` por `node_id` y ventana de 5 min.
4. **[Backend] Menú de Resolución NAT:** Implementar la cadena de responsabilidad (Translation logs -> Agent ID -> Proc/Port -> Temporal) y asegurar que el resultado (método + confianza) se persista como propiedad en la arista `:HOST_OBSERVED_FLOW`.

#### 🔵 P2 - Host Plane y Detección (Vector A)
5. **[Endpoint/Wazuh] DEBT-ARGUSPP-ARP-MONITOR-001:** Configurar Wazuh/osquery para extraer cambios de estado en la tabla ARP/NDP y enviarlos como eventos de "State Change", no como logs crudos.
6. **[Graph] Nodo de Estado `:IpMacBinding`:** Diseñar e implementar la lógica de *upsert* en Neo4j para los bindings IP-MAC, gestionando sus propiedades temporales (`valid_from`, `valid_to`).

#### 🟣 P3 - Ground Truth y MITRE (ADR-050)
7. **[SecOps/MITRE] Alineación de Vectores:** Actualizar el borrador del ADR-050 para que los scripts de Bettercap (Vector A) y Scapy/nfqueue (Vector B) se etiqueten explícitamente con `is_adversary_emulation: true` y `mitre_technique: T1557`.
8. **[Graph] Sistema de Taint:** Implementar el label `:SuspiciousFlow` en Neo4j y ajustar las queries de la UI/Dashboard para filtrar estos nodos por defecto, pero permitir su inspección en el "Modo Threat Hunt".

---

### Conclusión del Consejo

El borrador del ADR-052 es **apte para ser ratificado con las correcciones indicadas** (especialmente la sustitución de `flow_start_window` por el `sensor_native_flow_id` y el ajuste de la terminología de "causal" a "coincidencia temporal asimétrica").

Habéis construido una base teórica sólida. Ahora toca ensuciarse las manos con el esquema de Neo4j y el pipeline de stream. Si implementáis el rate-limiter probabilístico y el nodo de estado ARP, vuestro sistema será capaz de detectar no solo lo que la red dice que pasa, sino lo que el host *siente* que pasa, que es donde la verdad realmente reside.

Quedamos a la espera de vuestra validación para marcar el ADR como **APROBADO** y dar paso a la ejecución.

*Firmado,*
**El Consejo de Sabios (DeliberaciónDAY 173)**

QWEN