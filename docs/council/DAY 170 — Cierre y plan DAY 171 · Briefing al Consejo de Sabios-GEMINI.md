Estimado Alonso (PI, aRGus NDR),

El Consejo de Sabios se reúne para analizar el briefing del **DAY 170** y dar respuesta estructurada a las cuestiones técnicas planteadas por el equipo de desarrollo.

En primer lugar, **enhorabuena por los hitos alcanzados hoy**. Lograr la paridad byte a byte en la computación nativa de `community_id` en aRGus contra el oráculo `pycommunityid`, y asegurar la convergencia de Zeek y Suricata bajo el `seed = 0` mediante provisión automatizada e idempotente por línea, es un paso de gigante para el proyecto. Asimismo, la intervención quirúrgica en `docs/BACKLOG.md` (`DEBT-DOCS-BACKLOG-DEDUP-001`) demuestra una disciplina impecable respecto a la eliminación de deuda técnica documental, vital ante el objetivo de FEDER.

El plan para el **DAY 171** (cross-check E2E de tres ventanas mediante replay del flujo Neris) cuenta con el **visto bueno unánime del Consejo**. Validar la *paridad operacional* en caliente bajo tráfico real es el único criterio de aceptación válido antes de dar el join por consolidado.

A continuación, exponemos la opinión fundamentada del Consejo sobre las tres preguntas de arquitectura:

---

### P1 — Wazuh y la clave de correlación host↔red (Arquitectura del Grafo)

El Consejo descarta de forma categórica la Opción (B) (enriquecimiento puntual). Forzar la generación de un `community_id` en el agente o ingester de Wazuh para una fracción mínima de eventos introduce una complejidad heurística frágil, rompe la homogeneidad del pipeline de host y no soluciona el problema para la inmensa mayoría de la telemetría (logs de sistema, cambios en ficheros, escaladas de privilegios).

La recomendación del Consejo es una **combinación híbrida de (C) y (A): El modelo de Doble Arista con Ventana de Crisis Laxa.**

Neo4j brilla precisamente cuando no se intenta aplanar la realidad en una sola clave. Debemos explotar la naturaleza multidimensional del grafo:

1. **Dimensión Red (Determinista):** Los nodos de flujo de red (`NetworkFlow`) generados por aRGus, Suricata y Zeek se correlacionan e indexan de forma estricta mediante el `community_id` (arista `SAME_FLOW_AS`).
2. **Dimensión Host (Contextual):** Los eventos de Wazuh se vinculan directamente a un nodo central de tipo `Host` (identificado de forma unívoca por el `wazuh_host_id`, independiente de su IP cambiante).
3. **El Puente (La Arista Temporal/Espacial):** La correlación host-red se materializa mediante una arista que conecta el nodo `Host` con el nodo `NetworkFlow` si se cumplen dos condiciones mapeadas por el motor de correlación:
* **Coincidencia de Entidad:** La IP del host en ese instante de tiempo coincide con la `saddr` o `daddr` del flujo de red.
* **Ventana de Crisis (CrisisWindow):** Como bien intuyes, **la ventana temporal host-red debe ser obligatoriamente más laxa** que la de red-red. Un proceso comprometido puede ejecutar un binario malicioso (evento host) y tardar varios segundos (o minutos, en caso de balizamiento/beaconing) en abrir el socket y generar tráfico (evento red). Proponemos un parámetro de configuración `host_network_laxity_seconds` (por defecto, un umbral adaptativo de hasta 300 segundos, alineado con `late_arrival: true` de la ADR-046 v3).



**El desafío de NAT/Proxy:**
Si el endpoint está detrás de un NAT o proxy, la IP local reportada por Wazuh no coincidirá con la IP externa capturada por los sensores de red en la LAN de monitorización. Para resolver esto sin romper el diseño, el motor de correlación de Neo4j debe tratar la IP como un nodo dinámico o un histórico de asignación. Si aRGus o el pipeline de ingesta procesa logs de correlación intermedios (ej. tablas de estados de NAT o logs de DHCP), se añade un camino intermedio en el grafo: `(Host) -> [INTERNAL_IP] -> (NAT_Router) -> [EXTERNAL_IP] -> (NetworkFlow)`. Si no disponemos de esos logs, la arista directa host-red en presencia de NAT deberá apoyarse en indicadores alternativos de compromiso (IoCs) compartidos en la misma ventana temporal, o asumir que la visibilidad host-red se acota al segmento previo al NAT.

---

### P2 — Coste de mantener el seed=0 como invariante

El riesgo de un fallo silencioso por desalineación del seed en producción es crítico. El Consejo opina que **sí merece un mecanismo de salvaguarda**, pero debido a que Zeek y Suricata son herramientas externas cuyas configuraciones internas no siempre son accesibles programáticamente en tiempo de ejecución por un binario externo, un "gate de arranque" estricto que lea sus `.yaml` o `.zeek` puede ser frágil ante cambios de versión.

Proponemos una solución en dos capas:

1. **Gate de Arranque Interno (aRGus):** Un chequeo estricto al levantar el servicio que verifique que el motor nativo de aRGus está compilado o configurado con `seed = 0`. Si aRGus no cumple su propio invariante, pánico y parada de emergencia (Gate P0).
2. **Health-Check de Paridad en el Correlation-Engine (Anomalía Pasiva):** En lugar de inspeccionar ficheros externos, el motor de correlación de Neo4j / Ingestion Pipeline debe implementar una métrica de salud operativa (un "Canario de Correlación"). Si el pipeline detecta que está ingiriendo miles de eventos de Suricata y miles de aRGus, pero el ratio de joins exitosos por `community_id` cae estrepitosamente a **cero** durante una ventana de 5 minutos, el sistema debe disparar una alerta crítica: *“POSSIBLE COMMUNITY_ID SEED MISMATCH: High volume of network events but zero correlation matches between sensors.”*

---

### P3 — ¿Es el `community_id` la clave correcta a largo plazo en despliegues multi-nodo?

Rotundamente **no** si se usa como Clave Primaria Única (ID de nodo) en Neo4j. El `community_id` es una excelente **clave de correlación**, pero es pésima como **identificador único global (UUID)** en un sistema distribuido o multi-nodo, debido al riesgo de colisión semántica (reutilización de puertos, solapamiento de IPs privadas en diferentes subredes/clientes, o capturas en diferentes interfaces del mismo flujo).

**Veredicto del Consejo:** Debes implementar una **clave compuesta o un ID escopado** desde el diseño actual de la base de datos de grafos para evitar una migración dolorosa en el futuro.

El identificador único del nodo `NetworkFlow` en Neo4j debería ser un hash derivado de:


$$\text{flow\_id} = \text{hash}(\text{node\_id} + \text{community\_id} + \text{window\_timestamp\_epoch})$$

De este modo:

* El `node_id` (o `sensor_id`) actúa como namespace para aislar topologías.
* El `window_timestamp` (ej. truncado a bloques de la Ventana de Crisis) evita que tráficos idénticos ocurridos con días de diferencia colisionen en el mismo nodo del grafo.
* El `community_id` se almacena como una **propiedad indexada** (e indexable) del nodo, permitiendo que las consultas de Neo4j unan flujos que posean el mismo `community_id` y marcas de tiempo compatibles, pero manteniendo la identidad del nodo completamente aislada y unívoca por sensor y tiempo.

---

Quedamos a la espera de que se ejecute el plan del DAY 171 y se viertan los resultados en el repositorio. El Consejo mantiene su compromiso firme con la excelencia arquitectónica de aRGus NDR de cara al hito de septiembre.

*¡Adelante con el replay de Neris mañana!*

FIRMADO 
GEMINI