He analizado a fondo el ADR-052 v3. La iteración es sólida, coherente con el principio ordenador (§0) y cierra todas las cuestiones que el Consejo había planteado. Procedo a responder cada pregunta en el espíritu de la ratificación final.

---

## Análisis global

La v3 demuestra madurez. Los cambios respecto a v2 (N1–N12) resuelven los conflictos detectados —especialmente la separación entre identidad de corpus y keypair del sensor (N1), la función de hash congelada (N5) y el WAL externo para no-repudio del etiquetado (N4). La incorporación de las señales TCP/TLS por decisión de Alonso (§3.11) está delimitada y es razonable: el vector A no es solo L2, y postergar esas señales habría dejado cojo el modelo de amenaza.

No detecto contradicciones internas ni violaciones del invariante *“el grafo es un corpus”*. Las métricas de calidad (§0.1) convierten la misión en algo medible.

---

## Respuesta a las preguntas del Consejo

### Q1 – Rate-limit de cardinalidad (1ª pasada, §3.10)
**Decisión:** correcta.  
La cardinalidad exacta en el correlation-engine para la etiqueta `rate_limited` es factible (docenas de sensores, ventana pequeña) y elimina el riesgo de sesgo de HLL/Count-Min. Las estructuras probabilísticas quedan relegadas a dashboards, nunca al corpus.  
El backpressure en el sensor es solo IPC; el control real en el motor y la marca `rate_limited:true` (nunca descarte) preservan la evidencia. Voto a favor.

### Q2 – Mapa de cobertura/visibilidad de sensores (§3.8)
**Decisión:** correcta.  
Tabla declarativa versionada, fuente de verdad en el orquestador, con validación por beacons. Esto evita circularidad bajo data‑plane hostil y hace posible el cómputo honesto de `orphan_rate` y score IPW. La prohibición de `MATCH` en Neo4j por paquete es sensata. Voto a favor.

### Q3 – Marca de confianza (§3.6)
**Decisión:** correcta.  
Guardar primitivas (`witness_count`, `is_host_plane_anchored`, etc.) y derivar `trust_tier` como vista es la estrategia correcta para un corpus científico. Evita el `float` opaco congelado y permite recalcular la confianza con nuevos criterios. Voto a favor.

### Q4 – `trust_tier` vs score IPW (§3.6)
**Decisión:** correcta.  
Separar el `trust_tier` (enum en el grafo) del score IPW continuo (en el pipeline ML, no en Neo4j) resuelve la tensión entre operación y entrenamiento. La normalización por `expected_witnesses` y el rol inverso de `witness_count` en el IPW son sutiles pero exactos: evitan el covariate shift sin penalizar la cobertura única. Voto a favor.

### Q5 – Provenance ortogonal (§3.7)
**Decisión:** correcta.  
Mantener `provenance_suspected` y `provenance_ground_truth` como campos separados es la única forma de medir honestamente el rendimiento del detector. La dependencia circular se rompe. El `provenance` no se mezcla con el enum de `acceptance_criteria.md`. Voto a favor.

### Q6 – `flow_start_window` y `seq_in_window` (§3.1.4)
**Decisión:** correcta.  
`CrisisWindow` quedaba descartada con razón. El bucket fijo `floor(epoch/N)` determinista, calibrado por protocolo, y el `seq_in_window` transportado desde el sensor (no recomputado) garantizan reproducibilidad offline. El gate NTP/chrony es load‑bearing, pero ya estaba cerrado. Voto a favor.

---

## Preguntas adicionales (surgidas en la 2ª pasada) – todas resueltas

- **N1 – `node_id` desacoplado de la clave efímera:** bien resuelto, con identidad declarada y `deployment_epoch`.
- **N2 – `seq_in_window` transportado:** elimina dependencia de reordenado. Correcto.
- **N3 – `sensor_native_flow_id` nunca componente del hash:** mantiene la fórmula tool‑independiente. Correcto.
- **N4 – WAL externo con hash‑chain:** excelente para no‑repudio; Neo4j es vista materializada. Correcto.
- **N5 – Función de hash congelada:** BLAKE2b vía libsodium congelada, sin drift. Correcto.
- **N6 – Cardinalidad exacta para `rate_limited`:** correcto.
- **N7 – Ventanas host↔red en event time con watermark:** correcto, aborda el buffering de Wazuh.
- **N8 – Resolución de conflictos NAT y peso IPW:** `CONFLICT_NAT` + penalización sin fallback silencioso. Correcto.
- **N9 – `FlowObservation` vs `FlowIdentity`:** anotado como deuda de nomenclatura, no bloquea.
- **N10 – Métricas de calidad del corpus:** dan concreción a §0, bien.
- **N11 – `agent_id` canónico:** `hostname ‖ domain ‖ os_uuid`, estable bajo DHCP. Correcto.
- **N12 – Almacenamiento por niveles:** mencionado en §7 (implícito), no hay conflicto.

---

## Veredicto final

**Ratifico ADR-052 v3.**  
No se prevé tercera deliberación completa; los cambios introducidos en v3 y la resolución de las preguntas del Consejo satisfacen todos los requisitos de integridad del corpus, trazabilidad y defensa arquitectónica. El ADR está listo para pasar a implementación y desbloquear DEBT-NEO4J-FLOW-KEY-001.

Firmado: Alonso (vía DeepSeek, como parte del Consejo).

en realidad, firma DeepSeek