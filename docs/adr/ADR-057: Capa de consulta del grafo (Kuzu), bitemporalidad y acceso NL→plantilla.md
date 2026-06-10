# ADR-057: Capa de consulta del grafo (Kuzu), bitemporalidad y acceso NL→plantilla

- **Estado:** Provisional / Embrionario (a madurar poco a poco)
- **Fecha:** 2026-06-09
- **Autor:** Alonso (con revisión Consejo pendiente)
- **Relacionados:** ADR-051 (Community ID Parity Gate), ADR-052 (Multi-node Flow Identity), ADR-055 (Synthetic Injectors / trace_id), ADR-056 (depreciación rag-ingester/rag-security)
- **Supuesto de numeración:** ADR-055 es el último cerrado; ADR-056 queda reservado a la depreciación RAG. Si colisiona, renumerar.

---

## Contexto

Una vez que el pipeline deja datos en las zonas del medallón (BRONZE CSV → Avro → Parquet PLATA → joins ORO → grafo Kuzu), aparece la pregunta de **qué estructuras de grafo construir** y **cómo se consultan**. El objetivo declarado es triple:

1. Responder el máximo de preguntas de un operador SOC.
2. Cruzar pasado remoto + pasado cercano + presente con baja latencia.
3. Caso de uso definitivo: **generar datasets de calidad a medida**.

El error a evitar es perseguir "el esquema más abierto posible" (estilo entidad-atributo-valor): responde a todo y nada rápido, porque no se puede indexar ni podar. La apertura real va en tres ejes concretos: **tiempo, extensibilidad y procedencia**, no en diluir el núcleo tipado.

---

## Decisiones

### D1. Separar sustrato de almacenamiento (tabular) del motor de grafo
- **Iceberg/Parquet (tabular, frío, columnar):** zonas PLATA/ORO, histórico profundo. Brilla en scans, filtros, agregaciones, particionado temporal. **Aquí vive la verdad.**
- **Kuzu (grafo, caliente, ~90 días):** proyección de presente + pasado cercano. Brilla en travesías multi-salto, caminos de longitud variable, blast radius, movimiento lateral. **Aquí se recorre rápido.**
- El grafo es una **proyección desechable**: regenerable desde la verdad tabular con el esquema que la pregunta del día pida. Kuzu se alimenta de Parquet (`COPY FROM`); Iceberg no modela el grafo ni sustituye a Kuzu.

### D2. Almacenamiento por niveles; claves de puente inmutables
- Grafo caliente (Kuzu) + frío inmutable (Parquet/Iceberg).
- Puente = claves inmutables `flow_uid` y `community_id`. Un scan frío devuelve un conjunto de `flow_uid` → se **rehidratan** selectivamente en Kuzu como subgrafo de investigación transitorio.

### D3. HDFS + Kudu **descartado** para los objetivos de despliegue
- La intuición caliente/mutable + frío/inmutable es correcta (es para lo que se diseñó Kudu+HDFS), pero el coste operativo (clúster JVM, ZooKeeper, NameNode/DataNodes, masters/tablet servers) es inviable en hospital comarcal o ayuntamiento.
- **Sucesor 2026, diferido (YAGNI):** almacenamiento de objetos (MinIO on-prem / S3) + formato de tabla abierto (**Apache Iceberg**) + motor embebido (**DuckDB**). Da ACID, time-travel, evolución de esquema/partición sobre Parquet plano, sin daemons.
- La copia-por-zonas actual **evoluciona hacia** Iceberg sin reescribir nada (ya son Parquet; Iceberg es capa de metadatos por encima). Se envuelve, no se migra.

### D4. Bitemporalidad como ciudadano de primera clase
- Separar **event_time** (cuándo ocurrió el flujo) de **knowledge_time** (cuándo nos enteramos).
- Indicadores/IOC se **anotan** sobre flujos históricos; **nunca se reescribe** el flujo.
- DHCP: IP ≠ identidad. La unión Host↔IP se resuelve **as-of-event-time**, no as-of-now. El `:Host` se clava a MAC/inventario, nunca a IP.
- Los *snapshots* de Iceberg aportan el eje knowledge_time del lado tabular casi gratis.

### D5. Interfaz de consulta = NL→plantilla parametrizada (camino 2), sin LLM al inicio
- **Rechazado:** NL→Cypher libre (superficie de inyección, productos cartesianos, respuestas plausibles pero falsas — inaceptable en SOC).
- **Elegido:** el (futuro) modelo solo mapea `lenguaje natural → (intent, parámetros)` contra plantillas Cypher vetadas, parametrizadas, probadas en plan y coste.
- **El catálogo de preguntas de primera clase ES la biblioteca de plantillas** (triaje, scoping, retro-hunt, beaconing, novedad…). Catalogar produce la lista blanca; no es jaula añadida.
- **Fase 1: sin LLM.** Plantillas vía CLI, demostrar correcto + rápido (EXPLAIN, coste acotado, índices). La capa NL se añade después como azúcar intercambiable (Via Appia: plantillas = calzada; parser NL = superficie).
- **Válvula de escape Tier 3:** modo "Cypher crudo" fuera del camino del LLM, autenticado, rol solo-lectura, límite de coste, log de auditoría.

### D6. Soberanía del modelo (cuando se añada la capa NL)
- Datos sanitarios/ciudadanos no pueden ir a nube de proveedor sujeto a derecho extranjero (CLOUD Act fuerza entrega con independencia de la ubicación física; Schrems II lo enfrenta al RGPD; análogos en otras jurisdicciones).
- Distinción clave: **el locus de ejecución** (dónde corre y quién puede obligar a acceder) gobierna la confidencialidad; **la nacionalidad de los pesos** gobierna la confianza en la cadena de suministro. Dos ejes, no mezclar.
- Postura: modelo **local** (o europeo/nacional sobre infraestructura de la jurisdicción de despliegue). El híbrido "modelo nacional sobre nube de tercero" se considera transición, no destino.
- La tarea es clasificación restringida, no generación abierta → un modelo local modesto basta.

---

## Pregunta canónica que guía el diseño: retro-hunt de IOC

> "Llega inteligencia: la IP `X` es C2. ¿Algún host interno habló con ella ALGUNA VEZ? ¿Quiénes, cuándo, cuántos bytes, y qué tocaron después?"

Ejercita las dos mitades a la vez:
- **Kuzu (caliente):** ¿activo AHORA? + blast radius lateral (travesía).
- **Parquet/ORO (frío):** ¿ALGUNA VEZ? (scan columnar con pruning por event_time).
- **Puente:** los `flow_uid` del frío rehidratan historia selecta en el grafo.
- **Bitemporalidad:** se crea `:Indicator` con knowledge_time y aristas `:IMPLICATES`; el flujo queda intacto.

---

## DDL provisional (Kuzu) — a madurar

> Nota: nombres de tablas de relación elegidos para evitar palabras reservadas (p. ej. `TARGETS` en lugar de `TO`).

```cypher
// --- Nodos ---
CREATE NODE TABLE Host (
    host_id      STRING,     // = MAC o id de inventario, NUNCA IP
    primary_mac  STRING,
    inventory_id STRING,
    criticality  STRING,     // p.ej. PACS, EHR, IoT_medico, DC, generic
    PRIMARY KEY (host_id)
);

CREATE NODE TABLE Endpoint (
    ip          STRING,
    ja3         STRING,
    dns_name    STRING,
    is_internal BOOLEAN,
    PRIMARY KEY (ip)
);

CREATE NODE TABLE NetworkFlow (
    flow_uid          STRING,     // PK; BLAKE2b-256(node_id ‖ community_id ‖ ventana)
    community_id      STRING,
    bytes_out         INT64,
    bytes_in          INT64,
    packets           INT64,
    flow_start_window TIMESTAMP,  // EVENT TIME
    ml_score          DOUBLE,
    PRIMARY KEY (flow_uid)
);

CREATE NODE TABLE Indicator (
    value          STRING,       // p.ej. la IP/ja3/hash
    ioc_type       STRING,
    knowledge_time TIMESTAMP,    // CUÁNDO LO SUPIMOS
    source         STRING,
    PRIMARY KEY (value)
);

// --- Relaciones ---
CREATE REL TABLE INITIATED   (FROM Host TO NetworkFlow);
CREATE REL TABLE TARGETS     (FROM NetworkFlow TO Endpoint);
CREATE REL TABLE COMMUNICATES_WITH (
    FROM Host TO Host,
    bytes INT64, flows INT64,
    first_seen TIMESTAMP, last_seen TIMESTAMP
);
CREATE REL TABLE IMPLICATES  (FROM Indicator TO NetworkFlow, knowledge_time TIMESTAMP);
CREATE REL TABLE HAD_IP      (   // unión temporal Host↔IP (DHCP)
    FROM Host TO Endpoint,
    ip STRING, valid_from TIMESTAMP, valid_to TIMESTAMP
);
```

### Plantilla 1 (caliente): `retro_hunt_ioc_hot`
```cypher
// Params: $ip
MATCH (h:Host)-[:INITIATED]->(f:NetworkFlow)-[:TARGETS]->(e:Endpoint {ip: $ip})
RETURN h.host_id, f.flow_uid, f.flow_start_window, f.bytes_out, f.bytes_in
ORDER BY f.flow_start_window;
```

### Scan frío (DuckDB/Iceberg, NO Cypher): `retro_hunt_ioc_cold`
```sql
-- Param: ?ip
SELECT node_id,
       MIN(flow_start_window) AS first_seen,
       MAX(flow_start_window) AS last_seen,
       SUM(bytes_out)         AS total_out,
       COUNT(*)               AS n_flows
FROM gold.network_flows
WHERE dst_ip = ?            -- pruning por partición event_time + metadatos Iceberg
GROUP BY node_id;
```

### Anotación bitemporal (no reescribe el flujo)
```cypher
// Params: $ip, $now, $source
MERGE (i:Indicator {value: $ip})
  ON CREATE SET i.ioc_type='ip', i.knowledge_time=$now, i.source=$source;
// luego, por cada flow_uid implicado (de caliente + rehidratado del frío):
MATCH (i:Indicator {value:$ip}), (f:NetworkFlow {flow_uid:$flow_uid})
CREATE (i)-[:IMPLICATES {knowledge_time:$now}]->(f);
```

### Pendiente de madurar (no resuelto aquí)
- Plantilla `blast_radius_lateral`: travesía `COMMUNICATES_WITH*1..3` con filtro temporal "después del contacto C2" (la longitud variable + filtro de propiedad de arista necesita afinarse en Kuzu).
- Resolución Host as-of-event-time vía `HAD_IP` (la consulta exacta de validez temporal).
- Mecánica de rehidratación frío→Kuzu (subgrafo transitorio: namespace, TTL, limpieza).

---

## Consecuencias

**Positivas**
- Grafo desechable y regenerable; sin miedo a perder información (la verdad está en el medallón, niveles fríos incluidos).
- Generación de datasets pasa de proyecto a consulta (tiempo de primera clase + procedencia multi-sensor).
- Camino de migración limpio a Iceberg/DuckDB sin reescritura.
- Capa NL aplazable sin coste; soberanía preservada por diseño.

**Negativas / costes**
- Doble representación (flujo como nodo + arista agregada) a mantener coherente.
- Mantener catálogo de plantillas + clasificador NL→intent (cuando llegue) con su set de evaluación.
- Bitemporalidad añade complejidad de modelado (validez temporal de Host).

---

## Cuestiones abiertas (candidatas a Consejo — medir, no votar)

- **DEBT-GRAPH-QUERY-001:** ¿índice/resumen compacto en caliente ("endpoints contactados alguna vez", tipo bloom o nodo-resumen) para preguntar lo barato antes del scan frío? Trade índice-vs-scan.
- **DEBT-GRAPH-QUERY-002:** ubicación del clasificador NL→intent (local pequeño vs externo). Apuesta: local. Medir pérdida de precisión.
- **DEBT-GRAPH-QUERY-003:** enumeración formal del catálogo de preguntas SOC de primera clase (= biblioteca de plantillas).
- **DEBT-GRAPH-QUERY-004:** modelado bitemporal de `:Host` (esquema `HAD_IP`, granularidad de ventanas de validez).