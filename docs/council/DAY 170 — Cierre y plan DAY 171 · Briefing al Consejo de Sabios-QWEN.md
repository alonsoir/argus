Aquí tienes la respuesta fundamentada del Consejo, estructurada para integración directa en la `Síntesis` y como guía de arquitectura para DAY 171.

---

# 🏛️ Respuesta del Consejo de Sabios · DAY 170 → DAY 171

## 🔍 P1 — Correlación Wazuh (host) ↔ Sensores de Red
**Veredicto:** Adoptar **(A) + (C)** combinados. Descartar (B).

### Fundamento técnico
- **Por qué (A)+(C) es la arquitectura correcta:** `community_id` es un identificador de *flujo de red*, no de *actividad de endpoint*. Forzar su generación parcial en Wazuh (opción B) rompe el principio de responsabilidad única, añade lógica de red al agente host y solo cubriría una fracción ruidosa de los eventos. El grafo es el lugar natural para unir dimensiones heterogéneas: los sensores de red aportan aristas `FLOW↔FLOW` por `community_id`; Wazuh aporta nodos `HOST` y aristas `HOST↔FLOW` por IP/ventana temporal.
- **NAT / Proxy:** La IP que ve la red (`observed_ip`) ≠ la IP interna del endpoint (`host_ip`). En el grafo, modela esto explícitamente:
    - Nodo `Host` con propiedad `internal_ip`.
    - Arista `(:Host)-[:SEEN_AS {type: 'NAT', valid_from, valid_to}]->(:NetworkFlow {ip: observed_ip})`.
    - Si Zeek detecta `conn.log` con `id.orig_h` interna y `id.resp_h` externa, esa mapping puede inyectarse al grafo desde el enriquecedor, no desde Wazuh.
- **Ventanas de correlación:**
    - `red↔red`: estricta (±5s o duración del flujo). Los sensores miden el mismo instante físico.
    - `host↔red`: laxa (±30s a ±120s, configurable por `CrisisWindow.multiplier_host`). Un proceso malicioso (`process_start`) suele anteceder al tráfico de C2 por segundos o minutos; una alerta de integridad de fichero puede dispararse después de la descarga. ADR-046 v3 `late_arrival: true` cubre esto, pero el índice temporal en Neo4j debe indexar por `event_time` con tolerancia configurable por tipo de arista.

**Acción recomendada:** Modelar el grafo con dos espacios de relación (`:SHARES_COMMUNITY_ID` y `:OCCURRED_ON_HOST_WITHIN_WINDOW`). Dejar la lógica de matching en el correlation-engine, no en los agentes.

---

## 🔍 P2 — Invariante `seed=0` y Gate de Arranque
**Veredicto:** **Gate P0 obligatorio + Health-check de deriva continua.** No basta con IaC.

### Fundamento técnico
- **El fallo silencioso es crítico:** Si un sensor emite con `seed=1` y los otros con `0`, el join devuelve `0 matches` sin error. El sistema parece "sano" pero está ciego. Esto viola el principio de *fail-fast* en pipelines de seguridad.
- **Arquitectura del Gate P0:**
    1. Al iniciar el `correlation-engine`, solicitar a cada collector/sensor su `effective_seed` vía control-plane (heartbeat inicial o probe de configuración validada).
    2. Validar paridad: `len(set(seeds)) == 1`. Si falla → `CRITICAL: abort startup`. Log + métrica `seed_parity_check.status`.
    3. No confiar en parseo estático de YAML/scripts: la configuración puede ser sobrescrita en runtime o por paquetes del sistema. La única verdad es la que el binario en ejecución expone.
- **Health-check continuo:**
    - Monitorizar ratio `cross_sensor_matches / total_flows`. Una caída súbita a <5% durante N ventanas indica deriva o pérdida de paridad.
    - Alertar sobre `community_id` huérfanos (>3 ventanas sin match en otro sensor). En condiciones normales, un flujo real debe ser visible en ≥2 sensores (por diseño de captura en `eth1`).
- **Invariante en IaC:** Mantener el seed en un único repositorio de configuración con validación pre-commit, pero el gate runtime es el seguro operativo. Equivalente al gate NTP: la sincronización lógica es tan crítica como la cronológica.

**Acción recomendada:** Implementar `SeedParityGate` en el bootstrap del correlation-engine + métrica `community_id.orphan_rate` en el dashboard de salud. Documentar en ADR-047 (nuevo).

---

## 🔍 P3 — `community_id` en Despliegues Multi-nodo
**Veredicto:** **`(node_id, community_id)` debe ser la clave compuesta explícita en Neo4j desde el diseño.** No confiar en metadatos implícitos del pipeline.

### Fundamento técnico
- **Colisión semántica real:** Dos nodos distintos (p.ej., `edge-fw-01` y `edge-fw-02`) pueden observar el mismo flujo `10.0.0.5:1027 → 8.8.8.8:443` (misma 5-tupla, seed 0 → mismo `community_id`). Si el grafo usa solo `community_id` como identificador único, fusionará flujos de nodos distintos, corrompiendo métricas de volumen, patrones GDS y alertas.
- **Por qué explícito > implícito:**
    - El pipeline de ingestión puede añadir `node_id` como propiedad, pero si no es parte del constraint de unicidad ni de la clave de correlación, las queries `MATCH (f:NetworkFlow {community_id: $cid})` devolverán nodos de distintas topologías sin distinción.
    - Neo4j 5.x soporta constraints compuestos nativamente:
      ```cypher
      CREATE CONSTRAINT unique_flow_key FOR (f:NetworkFlow) REQUIRE (f.node_id, f.community_id) IS UNIQUE;
      ```
    - Los algoritmos GDS (PageRank, Louvain, ShortestPath) requieren particionamiento explícito para escalar. `node_id` permite ejecutar análisis por nodo y federar resultados solo cuando sea necesario.
- **Estrategia de clave:**
    - Mantener `community_id` como propiedad legible para debugging y queries ad-hoc.
    - Usar `(node_id, community_id)` como clave de join en el correlation-engine.
    - Opcional: generar `flow_global_id = sha256(node_id || ':' || community_id || ':' || flow_start_ts)` para índices de alto rendimiento, pero nunca como sustituto de la clave estructural.
- **Migración futura:** Añadir `node_id` a un grafo ya poblado es costoso (reindexado, re-particionado de relaciones, validación de consistencia). Definirlo ahora es gratis operativamente y evita deuda arquitectónica.

**Acción recomendada:** Actualizar el esquema del grafo en el blueprint de DAY 171 para incluir `node_id` como propiedad obligatoria en `:NetworkFlow`, `:Alert`, y `:TelemetryEvent`. Ajustar queries de join y GDS para scope explícito. Documentar en ADR-046 v4.

---

## 📌 Síntesis para DAY 171
1. **E2E Cross-check:** Proceder con el replay `.50` → validación de paridad `community_id` en los tres sensores. Si verde, el join red↔red está listo.
2. **Modelo de correlación:** Implementar aristas duales en Neo4j (`:SHARES_COMMUNITY_ID` + `:OCCURRED_ON_HOST`). Definir ventanas temporales diferenciadas.
3. **Gates & Keys:** Añadir `SeedParityGate` P0 al arranque. Declarar `(node_id, community_id)` como clave compuesta única en el esquema del grafo antes de la primera ingesta multi-nodo.
4. **Documentación:** Crear ADR-047 (`Seed Parity & Health Checks`) y actualizar ADR-046 a v4 (`Multi-node Flow Identity & Host-Net Correlation`).

El Consejo aprueba el plan de DAY 171 bajo estas condiciones. Sin bloqueos. Avanzad con el E2E y el ajuste de esquema. 🛡️📈