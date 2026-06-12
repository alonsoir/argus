// schema.cypher — esquema Kuzu v0.11.3 del correlation-engine (aRGus NDR).
// DEBT-NEO4J-FLOW-KEY-001 (ADR-052). El engine C++ ejecuta este DDL al inicializar la BD.
//
// flow_uid PRIMARY KEY = dedup (uniqueness) + obligatorio (non-null) NATIVOS. Sin split Community/Enterprise.
// node_id NO puede ser NOT NULL en Kuzu 0.11.3 (no-PK) -> INVARIANTE DE ENGINE: IGraphSink rechaza
//   escribir cualquier nodo sin node_id. Es contrato de código, no de BD.
// flow_uid es único por construcción (hash de node_id||community_id||window): PK simple = dedup compuesto.
//
// -- DAY 180: enriquecimiento de veredicto en Alert + TelemetryEvent --------------
// NetworkFlow se mantiene IDENTIDAD PURA: la 5-tupla (ip/puerto/proto) vive en
// bronce + Parquet ORO, NO en el grafo. Para cruzar senales en formato tabular
// (datasets ML) se usa el plano ORO (joins columnares por community_id), no el grafo.
//
// PERO el veredicto de aRGus (final_classification, threat_category, los 3 scores,
// authoritative_source -- cols 12-17 del contrato correlation_v1) SI entra en los
// nodos Alert/TelemetryEvent. Motivo: habilita consultas GRAPH-NATIVE que filtran o
// navegan POR el veredicto (subgrafos por score, densidad de amenaza en un vecindario,
// features derivadas de topologia) sin tener que volver al bronce en cada consulta.
// Es desnormalizacion deliberada de una vista DERIVADA: el bronce HMAC sigue siendo la
// fuente de verdad inmutable; el grafo es reconstruible desde el. No es deuda, es diseno.
// El veredicto es INTRINSECO a la entidad (define que es la alerta) -> va en el NODO.
// method/confidence describen la RELACION evento<->flujo -> van en la ARISTA (*_ABOUT).

CREATE NODE TABLE IF NOT EXISTS NetworkFlow (
    flow_uid          STRING,
    node_id           STRING,
    community_id      STRING,
    flow_start_window UINT64,
    seq_in_window     UINT32 DEFAULT 0,
    ingested_at       UINT64,                 // + ns UTC (CLOCK_REALTIME), first_seen, ON CREATE SET por el engine
    temporal_anomaly  BOOLEAN   DEFAULT false,   // + ON CREATE SET (unilateral: flow_start_window > ingested_at + margen)
    PRIMARY KEY (flow_uid)
);

CREATE NODE TABLE IF NOT EXISTS Alert (
    event_id             STRING,
    node_id              STRING,
    flow_uid             STRING,
    community_id         STRING,
    final_classification STRING,
    threat_category      STRING,
    fast_detector_score  DOUBLE,
    ml_detector_score    DOUBLE,
    overall_threat_score DOUBLE,
    authoritative_source STRING,
    ingested_at          UINT64,   // + first_seen, ON CREATE SET
    PRIMARY KEY (event_id)
);

// TelemetryEvent = clase NEGATIVA (sin amenaza). Espeja el veredicto de Alert para que
// el grafo soporte consultas sobre la poblacion completa (p.ej. benignos cercanos a una
// alerta con sus scores) y features derivadas que necesiten ambas clases. Si los datasets
// salieran SIEMPRE del Parquet ORO y nunca del grafo, este nodo podria volver a quedar
// magro (solo identidad) -- DECISION A CONFIRMAR (ver nota de la conversacion).
CREATE NODE TABLE IF NOT EXISTS TelemetryEvent (
    event_id             STRING,
    node_id              STRING,
    flow_uid             STRING,
    community_id         STRING,
    final_classification STRING,
    threat_category      STRING,
    fast_detector_score  DOUBLE,
    ml_detector_score    DOUBLE,
    overall_threat_score DOUBLE,
    authoritative_source STRING,
    ingested_at          UINT64,   // + first_seen, ON CREATE SET
    PRIMARY KEY (event_id)
);

// Correlacion flujo<->flujo intra-nodo por community_id; host<->flujo anotando SIEMPRE metodo+confianza (NAT, DAY 170).
CREATE REL TABLE IF NOT EXISTS CORRELATES_FLOW (FROM NetworkFlow TO NetworkFlow, community_id STRING, method STRING, confidence DOUBLE);
CREATE REL TABLE IF NOT EXISTS ALERT_ABOUT (FROM Alert TO NetworkFlow, method STRING, confidence DOUBLE);
CREATE REL TABLE IF NOT EXISTS TELEMETRY_ABOUT (FROM TelemetryEvent TO NetworkFlow, method STRING, confidence DOUBLE);
