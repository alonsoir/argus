### Evaluación del Consejo de Sabios — ADR-052 (borrador v1)

**Decisión colectiva**: El ADR es sólido en su núcleo, aborda correctamente la identidad de flujo y la correlación host↔red, y formaliza un modelo de amenaza explícito. Sin embargo, hay puntos débiles que requieren refuerzo antes de su ratificación. A continuación, análisis detallado, fortalezas, debilidades y respuestas a las siete preguntas abiertas.

---

## 1. Fortalezas — aspectos bien apuntalados

- **Desacoplamiento de `community_id` e identidad de nodo**: Correcto y fundamental. La reutilización de 5‑tuplas y el contexto multi‑nodo hacen que `community_id` no sea único. La tripleta `(node_id, community_id, flow_start_window)` resuelve la unicidad con elegancia.
- **Modelo de amenaza con dos vectores claramente diferenciados**: La tabla del §3.3 es un acierto. Destaca que `community_id` es ciego al vector A (MITM de capa 2) y manipulable en el vector B (inyección/reescritura). Esto impide depositar falsas expectativas de seguridad en el hash.
- **Puente host↔red con anotación de mecanismo y confianza**: La transparencia total en el método de resolución NAT (translation node, agent_id, puerto+timestamp) y la obligación de registrar el fallo sin silenciarlo son una práctica excelente para la auditabilidad.
- **Restricciones Neo4j como P0 de esquema**: Ratificar la deuda `DEBT-NEO4J-FLOW-KEY-001` antes de poblar el grafo es una decisión pragmática que evita retrabajos masivos.
- **Empleo de `flow_uid` con doble propósito** (identidad y defensa anti‑inyección): Reutilizar el mismo identificador para deduplicación y detección de anomalías reduce la complejidad.

---

## 2. Puntos débiles detectados y recomendaciones

### 2.1 Dependencia implícita no documentada: topología de sensores para la defensa anti‑inyección

El ADR afirma que “un flujo sin emisión del sensor de borde correspondiente es anomalía detectable” (§3.1 y §3.4). Sin embargo, **no define cómo se determina qué sensor «debería» haber visto un flujo**. Un atacante que inyecte paquetes y los reporte con un `node_id` legítimo (por ejemplo, comprometiendo un sensor o falsificando su identidad) eludiría esta defensa a menos que exista un modelo de cobertura de red que indique qué sensores pueden observar cada segmento (VLAN, subred, interfaz).  
**Recomendación**: Añadir explícitamente el requisito de un **grafo de topología de sensores** (o tabla de adyacencia sensor‑segmento) como entrada de primera clase. El correlation‑engine debe consultar ese modelo para validar que el `(node_id, comunidad_ip)` tiene sentido topológico. Sin él, la defensa se reduce a confiar en que el `node_id` del sensor es honesto, lo que no es suficiente ante un sensor comprometido.

### 2.2 `flow_start_window` y colisiones en protocolos sin estado (UDP)

La ventana temporal evita que dos flujos con la misma 5‑tupla y distinto inicio colapsen en el mismo `flow_uid`. Sin embargo, en UDP, donde no existe TIME_WAIT, un cliente puede reutilizar instantáneamente el mismo par (IP_origen, puerto_origen) hacia el mismo destino. Si dos flujos UDP distintos (separados por un timeout de flujo) comienzan dentro del mismo bucket, el `flow_uid` colisionará.  
**Recomendación**:
- Adoptar una granularidad de **1 segundo como default**, pero advertir que para tráfico UDP de alta frecuencia puede requerirse sub‑segundo o un contador monótono por `(node_id, community_id)` como componente adicional.
- Incluir en los tests una validación de no colisión con ráfagas UDP que simulen reutilización inmediata de puerto.

### 2.3 Ambigüedad en la cardinalidad del rate‑limit (Q1)

El ADR menciona un rate‑limit de `community_id` nuevos por ventana por nodo, pero no distingue entre `community_id` únicos (cambios de 5‑tupla) y flujos (que pueden tener el mismo `community_id` si se repiten). Un atacante podría saturar con muchas 5‑tuplas distintas (facilísimo con inyección) sin disparar el límite si éste se aplica a flujos totales.  
**Recomendación**: El rate‑limit debe ser sobre **la tasa de `community_id` distintos observados por un sensor** (cardinalidad del conjunto, no cantidad de eventos). Esto evita que un atacante inunde el grafo con miles de 5‑tuplas fabricadas. Aplicarlo en el ingestion pipeline hacia Neo4j, con una ventana deslizante y alerta temprana.

### 2.4 Falta de mecanismo para la “detección de sensor comprometido” mencionada en §3.4 línea 3

Se afirma que “un sensor que emite `community_id` que ningún otro corrobora puede ser sensor comprometido O tráfico inyectado”. Esto es correcto, pero no se especifica **cómo se detecta la falta de corroboración** en un sistema multi‑sensor sin acoplamiento fuerte. Se necesita una métrica de `orphan_rate` por sensor (ADR‑051) y un umbral adaptativo.  
**Recomendación**: Conectar explícitamente con ADR‑051 y definir que el `orphan_rate` por sensor se calculará sobre una ventana temporal; un sensor que consistentemente emite community_ids no corroborados (con una tasa anómala) dispara una alerta de posible compromiso. Debe documentarse en este ADR para cerrar el bucle.

### 2.5 La vigilancia ARP/NDP queda sin diseño concreto (Q2)

El ADR identifica correctamente que la señal ARP/NDP es el único detector del vector A. Sin embargo, pospone la decisión de si será nodo/arista de primera clase o enriquecimiento. Esto es peligroso: si no se implementa, el sistema es ciego al MITM clásico.  
**Recomendación**: Tratar la señal ARP/NDP como **entidad de primera clase** en el grafo: nodos `:ArpObservation` o `:NeighborObservation` con propiedades (MAC, IP, timestamp, interfaz), y aristas hacia `Host` y `NetworkSegment`. Esto permite consultas temporales del tipo “¿cambió la MAC de esta IP en los últimos X segundos alrededor de un flujo?” sin depender de enriquecimiento post‑procesado.

---

## 3. Respuestas a las preguntas abiertas (Q1–Q7)

### Q1 — Rate‑limit/cardinalidad de `community_id`
**Ubicación**: aplicar en el **correlation‑engine** justo antes de escribir en Neo4j, pero con retroalimentación al sensor para frenar en origen. La métrica debe ser **cardinalidad de `community_id` distintos por ventana por `node_id`**.  
**Mecanismo**: un contador HyperLogLog aproximado por sensor (para ahorro de memoria) en una ventana deslizante de 60 s. Si el incremento de cardinalidad supera un umbral (ej. 500 nuevos community_ids/ventana), se marca el sensor como “posiblemente inundado/comprometido” y se ralentiza la ingesta. Esto complementa la cuota anti‑pinning de ADR‑046.

### Q2 — Señal ARP/NDP del host plane
Debe ser **nodo/arista de primera clase** en el grafo.  
Fundamento: la detección del vector A (MITM silencioso) requiere una ventana temporal y la capacidad de correlacionar cambios MAC↔IP con flujos de red. Si la señal es solo enriquecimiento, se dificulta la indexación temporal y las consultas de grafo. Modelado sugerido:
- Nodo `:ArpCacheEntry` con `ip`, `mac`, `timestamp`, `host_id`.
- Arista `OBSERVED_ON` hacia el `Host`.
- Un cambio se detecta como dos nodos consecutivos con misma IP y distinta MAC.  
  Esto se alinea con DEBT‑ARGUSPP‑WAZUH‑001.

### Q3 — Marca de confianza en el flujo
Sí, añadir una propiedad `corroboration_count` (entero, ≥1) al nodo `:NetworkFlow` que indique cuántos sensores reportan el mismo `community_id`. Esto permite:
- `corroboration_count == 1` → baja confianza (posible inyección local o sensor aislado).
- `corroboration_count >= 2` → mayor confianza.  
  Además, se puede añadir una categoría `INJECTED` en el `acceptance_criteria.md` para flujos que fallen la validación topológica o de `node_id`. No se excluye, se etiqueta con un label adicional como `:SuspectedInjection`.

### Q4 — Etiquetado de flujo sospechoso de inyección sin excluirlo
Se recomienda:
- Añadir un label `:Anomaly` al nodo `:NetworkFlow` (además de sus labels normales).
- Añadir una propiedad `anomaly_type` con valor `"injection"`.
- Mantener el flujo en todas las métricas de ground truth (para entrenamiento/evaluación) e incluir un flag `excluded_from_correlation=False` (por defecto), para que los motores de detección puedan ignorarlos bajo configuración explícita si así se desea. Esto preserva la integridad científica.

### Q5 — Relación con ADR‑050 (sesión MITRE)
Si uno de los seis vectores incluye un ataque MITM con bettercap (ARP spoofing + posible inyección), entonces:
- El modelo de amenaza de este ADR es **el ground truth esperado** para ese vector.
- Los tests de validación de ADR‑050 deberían verificar exactamente las dos líneas de defensa descritas:
    - Vector A: que el cruce host↔red detecta el cambio de MAC.
    - Vector B: que la inyección se marca por `flow_uid` + topología.  
      Se recomienda coordinar la redacción de ADR‑050 para que cite este modelo como referencia de detección esperada.

### Q6 — Granularidad de `flow_start_window`
**Recomendación técnica**:
- Usar **1 segundo fijo** como bucket por defecto, alineado con la resolución temporal de los flow records típicos (NetFlow/IPFIX tienen marcas de tiempo con granularidad de milisegundos pero los inicios suelen ser redondeados al segundo).
- Para tráfico UDP de alta velocidad donde la reutilización de 5‑tupla pueda ocurrir en el mismo segundo, se debe incluir una **secuencia monotónica por `(node_id, community_id)` dentro del bucket**, que se concatena al hash en lugar de forzar una ventana más fina. Así, el `flow_uid` quedaría:  
  `flow_uid = hash(node_id ‖ community_id ‖ flow_start_window ‖ seq_in_window)`.  
  El contador se reinicia al cambiar de ventana. Esto elimina por completo el riesgo de colisión sin depender de la duración del bucket.
- Si se prefiere simplicidad y no se esperan colisiones UDP extremas, un bucket de 1 s es suficiente para el LAB inicial.

### Q7 — ¿Mantener P1 y P3 juntos o separar P1 a ADR‑053?
**Decisión del Consejo: mantener juntos en ADR‑052.**  
Razones:
- Las dos decisiones afectan el esquema de Neo4j y la definición de `flow_uid` (P3) es un prerrequisito para el puente host↔red (P1).
- La justificación de defensa anti‑inyección (P3) y la detección del vector A (P1) se entrelazan en el modelo de amenaza.
- Separarlos ahora introduciría una dependencia entre ADRs que complicaría la trazabilidad.  
  No obstante, si la complejidad de P1 crece sustancialmente (menú NAT, agente‑canónico, múltiples fuentes de host), puede extraerse más adelante un ADR‑053 que detalle exclusivamente el puente host↔red, referenciando a ADR‑052 para la identidad de flujo.

---

## 4. Conclusión del Consejo

El ADR‑052 establece una base sólida para la identidad de flujo en entornos hostiles multi‑nodo y para la correlación host↔red. Las debilidades detectadas (topología de sensores no explícita, colisiones UDP, granularidad de rate‑limit, diseño de señal ARP/NDP) son subsanables con los ajustes recomendados. Respondidas las siete preguntas, el Consejo considera que el borrador está **muy cerca de la ratificación**, condicionado a la incorporación de:

- Un modelo explícito de cobertura de sensores (grafo de topología) como entrada del correlation‑engine.
- La adopción de una secuencia por ventana en el `flow_uid` para UDP o, al menos, un test que demuestre la no colisión en escenarios de reutilización rápida.
- El diseño de la señal ARP/NDP como entidad de primera clase, esbozado en este ADR.

Con estas adiciones, se desbloquea DEBT‑NEO4J‑FLOW‑KEY‑001 y se avanza con seguridad hacia la población del grafo.

DEEPSEEK
