**ADR-052 v2 es excelente.** Representa un salto de madurez significativo respecto a v1: incorpora la lente del **corpus** (§0) como principio ordenador (muy acertado), resuelve casi todas las preguntas abiertas con rigor técnico y honestidad científica, y eleva artefactos críticos (mapa de cobertura, codificación canónica, `node_id` criptográfico, etiquetado de procedencia) al nivel que merecen. El documento está bien estructurado, las justificaciones son profundas y las decisiones alineadas con las restricciones reales de sistemas distribuidos, grafos temporales y ciberseguridad adversaria.

### Fortalezas a Apuntalar
- **§0 (Misión primaria)**: Brillante. Subordina todo el diseño al corpus de entrenamiento y reconvierte Suricata/Zeek/Wazuh en "maestros". Esto da coherencia filosófica y práctica al proyecto. La invariante "*retención + integridad de la etiqueta*" es oro para reproducibilidad científica.
- **Codificación canónica de `flow_uid`** (§3.1.1): Resuelve el riesgo de paridad cross-implementación. SHA3-256 + delimitadores 0x00 + uint64_be es robusto y previene prefix collisions.
- **Separación `provenance_suspected` vs `provenance_ground_truth`** (§3.7): Excelente decisión de diseño. Evita circularidad y permite medir honestamente la calidad del detector. Append-only via aristas es correcto para auditabilidad.
- **Trust como features primitivas + IPW** (§3.6): Alineado con ADR-040. Guardar señales crudas (witness_count, nat_resolution_method, etc.) en vez de un veredicto opaco es la elección correcta para ML.
- **Mapa de cobertura** (§3.8): Promovido correctamente a prerrequisito. Sin él, `orphan_rate` e IPW colapsan.
- **Modelo de amenaza + límites honestos** (§3.4.1): Transparente sobre lo que *no* se puede detectar (host comprometido + vector A). Esto es madurez.

### Puntos Débiles / Riesgos a Mitigar
1. **Complejidad acumulada**: El esquema (`flow_uid` con seq, node_id crypto, múltiples primitivas de confianza, mapa de cobertura, NAT menú + conflictos, provenance dual) es rico pero aumenta la carga cognitiva y de implementación. Riesgo de errores en ingest o queries.
2. **`seq_in_window`**: Útil contra reúso UDP instantáneo, pero introduce un contador monótono local por sensor. Hay que definir bien su persistencia/recuperación (crash del sensor, reinicio) para mantener reproducibilidad offline desde pcap.
3. **Overhead en Neo4j**: Nodos `:IpMacBinding`, aristas de tagging append-only, primitivas de confianza y mapa de cobertura pueden aumentar cardinalidad y grado. Monitorear densidad temporal.
4. **Dependencias en cadena**: Muchas deudas nuevas (P0/P1). Si el mapa de cobertura o NTP skew no están sólidos, varios mecanismos se degradan.
5. **Reproducibilidad offline**: Bien enfatizada, pero hay que validar que todo (incluyendo `seq_in_window` y resolución NAT) sea reconstruible solo con pcap + inventario histórico + manifiesto MITRE.

### Respuestas a las Preguntas Abiertas (§6 — 2ª pasada)

**Q1. Ratificación de §3.1.3 (identidad ≠ correlación cross-nodo)**  
**Sí, ratificar.** Dos sensores que ven el mismo flujo físico **deben** producir `flow_uid` distintos (por diseño, porque `node_id` está dentro del hash). Esto es correcto y deseable: cada observación es una muestra de entrenamiento independiente y enriquecida (perspectiva multi-vantage). El skew de reloj solo afecta el *match* vía arista `FLOW_IDENTITY` (correlación), nunca la identidad del nodo.

Esto elimina la necesidad de `session_counter` global/estatal (buena decisión: mantiene reproducibilidad offline). Confirmado.

**Q2. Diseño del mapa de cobertura de sensores (§3.8)**  
**Recomendación: Grafo ligero + tabla materializada.**
- Nodos `:SensorCoverage` o relación `(:Sensor)-[:CAN_OBSERVE]->(:NetworkSegment)` (VLAN, subnet CIDR, interfaz, tap point).
- Propiedades: `confidence`, `valid_from/to`, `capture_mode` (promiscuo, routed, etc.).
- Derivar parcialmente del inventario de endpoints (ADR-046 §3.9) pero enriquecer manualmente/automáticamente con topología de red.
- Almacenar en Neo4j (para queries de correlación) **y** cache en el correlation-engine (Redis o etcd) para baja latencia en ingest.

Esto permite validar "flujo visto por sensor que no debería haberlo visto" o "flujo esperado pero ausente".

**Q3. Calibración de `N` y `nat_confidence_floor`**
- **`N` (flow_start_window)**: 60 s es un default LAB razonable. Calibrar sobre golden pcaps midiendo distribución de tiempo entre flujos con idéntica 5-tupla en el mismo sensor (percentil 0.1–1 del intervalo de reúso). Considerar bimodal: TCP (TIME_WAIT ~60-240s) vs UDP (más corto). Probar sensibilidad con flujos largos (SSH, C2).
- **`nat_confidence_floor`**: Definir por mecanismo (ej. LOG=0.9, AGENT_ID=0.75, PROC_PORT=0.5, TEMPORAL=0.3). Floor global inicial 0.4–0.5. Conflictos siempre marcan `CONFLICT_NAT` independientemente del floor.

**Q4. Forma final del `trust_tier`**  
Enum derivado (`CORROBORATED` / `SINGLE_SENSOR` / `ORPHAN` / `CONFLICT_NAT`) es suficiente para queries y UI.  
**Además**, exponer un **score continuo derivado** (0–1) para IPW en entrenamiento (ADR-040). Ejemplo simple:  
`trust_score = w1·(witness_count / expected_witness) + w2·nat_confidence + w3·is_host_anchored`  
(con pesos aprendidos o fijos). Guardar tanto el enum como el score computado en vistas/materialized.

**Q5. `provenance` y `acceptance_criteria.md`**  
**Confirmar**: Añadir eje `provenance` completamente ortogonal. No tocar el enum congelado de presencia (DROP/CONFIG/POLICY/BUG/UNKNOWN). Son dimensiones distintas: una es "por qué se observó vs esperado en benigno", la otra es "procedencia adversarial o ground-truth de ejercicio".

**Q6. Fuente out-of-band para vector A con host comprometido**  
Asumir y **documentar el límite** honestamente (§3.4.1 ya lo hace bien). Abrir DEBT opcional para port-security / mirroring en `ml_defender_gateway_lan` (switch), pero no bloquear v2. Es un límite fundamental de observabilidad cuando el endpoint está fully compromised.

**Q7. Señal de host más allá de L2 (TCP/TLS anomalies)**  
Incluir en v2 al menos las básicas (RST inesperados, seqnum jumps, TLS cert mismatch via osquery/Wazuh). Difere análisis profundo (JA3 fingerprinting post-MITM, etc.) a ADR-053 o backlog. Añadir como propiedades en `:IpMacBinding` o nodo `:HostAnomaly`.

### Sugerencias Adicionales
- **Reproducibilidad**: Añadir en validación un test completo de "pcap → flow_uid reconstruido → grafo replay".
- **Neo4j**: Composite constraint `(node_id, flow_uid)`. Indexes en `community_id`, `node_id`, `provenance_*`, timestamps. Considerar temporal graph features de Neo4j si escala.
- **Backpressure y rate-limit**: La distinción backpressure (sensor) vs seguridad (motor) es correcta.
- **Nueva deuda menor**: Definir serialización exacta de `seq_in_window` y recuperación post-crash del sensor.

**Conclusión**: ADR-052 v2 está listo para avanzar a **Approved** tras esta segunda pasada (con las ratificaciones menores arriba). Es uno de los ADR más sólidos del conjunto: combina rigor distribuido, pensamiento adversarial y honestidad científica.

**Tareas accionables recomendadas**:
1. Ratificar Q1, Q5 explícitamente en el Consejo.
2. Cerrar DEBT-NEO4J-FLOW-KEY-001 y las nuevas P0 (codificación, node_id).
3. Iniciar implementación del mapa de cobertura (DEBT-SENSOR-COVERAGE-MAP-001) en paralelo.
4. Golden pcap calibration campaign para `N` y ventanas.
5. Actualizar a v2.1 con las respuestas incorporadas y pasar a implementación.

Excelente evolución. El proyecto gana mucho con este nivel de detalle. Si quieres que redacte alguna sección específica, proponga Cypher de ejemplo, o ayude con el test de paridad `flow_uid`, dime.

GROK