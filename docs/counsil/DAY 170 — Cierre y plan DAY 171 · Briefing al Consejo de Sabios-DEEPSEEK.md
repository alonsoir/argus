## Análisis del Consejo de Sabios — DAY 170

He estudiado el briefing con detalle. Celebro el cierre de los tres sensores y la madurez de las preguntas que planteáis. Os doy mi análisis razonado para cada una.

---

### P1 — Wazuh y la clave de correlación host↔red

**¿(A)+(C) combinados, como intuís?**  
Sí, la combinación de **(A) Correlación temporal + host** con **(C) Doble arista en Neo4j** es la arquitectura correcta para la mayoría de los casos, y además es elegante porque respeta la naturaleza de cada fuente:

- Para **red↔red**, `community_id` es la clave natural, determinista y sin ambigüedad.
- Para **host↔red**, la ventana de crisis (`CrisisWindow`) y el nodo `Host` (identificado por IP o, mejor, por `agent_id`/`hostname`) permiten unir eventos que no comparten 5‑tupla.

En Neo4j esto se traduce en:

- Aristas `FLOW` ↔ `FLOW` con propiedad `community_id` (o `CORRELATES_WITH`).
- Aristas `HOST` ↔ `FLOW` con propiedades `ip`, `timestamp` y `crisis_window_id`.  
  Así el grafo opera con dos dimensiones de correlación, explotando justo lo que hace fuerte a una base de grafos: consultas de camino variable que navegan tanto por la topología de red como por la temporal.

La opción **(B)** (community_id derivado en el ingestor para la fracción de eventos Wazuh que sí tienen 5‑tupla) puede añadirse más tarde como un *enriquecimiento puntual* sin complejidad excesiva, pero no es prioritaria. No conviene condicionar la arquitectura principal a una cobertura parcial.

**¿Qué pasa con NAT/proxy, donde la IP del endpoint no coincide con la IP del flujo?**  
Este es el punto delicado. En entornos con NAT o proxy, la IP observada por Wazuh (privada) y la IP que aparece en los flujos (pública o del proxy) **no casan directamente**. Hay tres vías, por orden de robustez:

1. **Mapa de traducción determinista**: si disponemos de logs de NAT (p. ej., del firewall o del proxy) o de un inventario (CMDB) que vincule IP interna ↔ IP pública en el momento del flujo, podemos crear un nodo `Translation` en el grafo y recorrerlo para unir `Host` → `Translation` → `Flow`. Es la solución más sólida.
2. **Identidad lógica en lugar de IP**: si Wazuh reporta un `agent_id` o `hostname` único, y en los flujos podemos inyectar esa misma identidad (p. ej., a través de metadata de NetFlow/IPFIX si la infraestructura lo soporta, o mediante logs de autenticación que liguen usuario/host a la IP pública), la correlación se hace por ese identificador lógico.
3. **Correlación puramente temporal**: sin ningún mapeo, la ventana de crisis uniría eventos de host y flujo por tiempo cuando el volumen de tráfico es bajo, pero es frágil y propensa a falsos positivos. Solo es aceptable como fallback si el coste de las alternativas anteriores es prohibitivo.

**Mi recomendación**: diseñar el modelo de grafos contemplando un nodo intermedio `Translation` o una propiedad `effective_ip` que el pipeline de ingestión pueda enriquecer si existe el mapeo, y dejar la correlación por `agent_id` como el mecanismo preferente cuando esté disponible.

**¿La ventana temporal host↔red debe ser más laxa que la de red↔red?**  
Totalmente de acuerdo. Un proceso malicioso puede ejecutarse minutos u horas antes de generar tráfico (o viceversa, el tráfico de C2 puede preceder a la descarga del payload). Por tanto, la `CrisisWindow` para aristas `HOST` ↔ `FLOW` debería ser configurable e independiente, y típicamente de mayor duración que la ventana de correlación entre flujos de red (que suele ser de segundos o pocos minutos). Esto encaja con el concepto `late_arrival` de ADR‑046: el grafo puede recibir el evento de red después y aún así establecer la arista si la ventana host↔red lo permite.

---

### P2 — Coste de mantener el seed=0 como invariante

El riesgo que identificáis es real: un seed distinto en un solo sensor provoca una pérdida de correlación **silenciosa**. La detección post-mortem de community_ids huérfanos es posible pero tardía. Por eso:

- **Gate de arranque**: sí, merece la pena implementar un *startup gate* en el correlation-engine (o en un servicio de health previo) que recupere el seed de cada sensor (ya sea consultando su API o leyendo una clave de configuración que el agente de despliegue exponga) y bloquee el arranque si detecta divergencias. Es análogo al gate NTP de ADR-046 y su coste de implementación es bajo.
- **Health-check complementario**: además, un monitor periódico que evalúe la tasa de community_ids que no encuentran correspondencia en otros sensores puede actuar como red de seguridad. Si, por ejemplo, el 100 % de los ids de un sensor permanecen sin match durante varios minutos, es muy probable que haya un problema de configuración (seed, zona horaria, etc.) y se debe alertar.

Ambos mecanismos no son excluyentes; juntos ofrecen una defensa en profundidad contra el fallo silencioso.

---

### P3 — ¿Es el `community_id` (seed 0, espacio global) la clave correcta a largo plazo en despliegues multi-nodo?

**Respuesta corta**: sí, es correcto usarlo como *clave de correlación*, pero **no como identificador único de un nodo Flow en el grafo**. El matiz es importante.

En un grafo de Neo4j, cada observación de un flujo por un sensor distinto puede modelarse como un nodo `FlowObservation` (o `Flow`) cuyas propiedades incluyen `sensor_id`, `timestamp_inicio`, `community_id`, etc. El `community_id` sirve para crear aristas entre observaciones del *mismo* flujo lógico, vistas por sensores diferentes. Si dos sensores ven exactamente la misma 5‑tupla en la misma ventana temporal, **es el mismo flujo** y queremos unirlos. No hay colisión semántica; al contrario, es una propiedad deseable.

La clave compuesta `(node_id, community_id)` que proponéis no es estrictamente necesaria si cada nodo `FlowObservation` tiene ya un identificador único (p. ej., un uuid generado en la ingesta o el `event_id` nativo del sensor). Sin embargo, si decidís modelar un único nodo `Flow` compartido por todos los sensores que lo vieron, entonces el `community_id` **sí** podría actuar como identificador del flujo (con la precaución de incluir también el `timestamp` de inicio porque la misma 5‑tupla puede reutilizarse en momentos distintos). En ese caso, la unicidad sería `(community_id, flow_start_time)` y la relación con los sensores se modela mediante aristas `OBSERVED_BY {sensor_id, timestamp}`.

**Mi consejo**: mantener la flexibilidad del grafo modelando `FlowObservation` por sensor (es decir, cada sensor genera su propio nodo) y utilizar `community_id` para crear relaciones `CORRELATES_WITH` entre esas observaciones. Así, la ingestión es natural (cada sensor es independiente), el `community_id` nunca colisiona de forma indeseada porque cada nodo ya tiene su contexto (`sensor_id`), y el grafo puede responder preguntas como “¿Qué sensores vieron este flujo?”. Esta decisión ahora evitará migraciones de esquema posteriores y es coherente con la arquitectura de doble arista de la P1.

---

Espero que este análisis os sirva para el plan de mañana y el diseño del correlation-engine. Quedo a vuestra disposición para cualquier aclaración.  
— El Consejo

FIRMADO 
DEEPSEEK