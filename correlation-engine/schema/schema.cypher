// schema.cypher — esquema Kuzu v0.11.3 del correlation-engine (aRGus NDR).
// DEBT-NEO4J-FLOW-KEY-001 (ADR-052). El engine C++ ejecuta este DDL al inicializar la BD.
//
// flow_uid PRIMARY KEY = dedup (uniqueness) + obligatorio (non-null) NATIVOS. Sin split Community/Enterprise.
// node_id NO puede ser NOT NULL en Kuzu 0.11.3 (no-PK) -> INVARIANTE DE ENGINE: IGraphSink rechaza
//   escribir cualquier nodo sin node_id. Es contrato de código, no de BD.
// flow_uid es único por construcción (hash de node_id||community_id||window): PK simple = dedup compuesto.

CREATE NODE TABLE IF NOT EXISTS NetworkFlow (
    flow_uid          STRING,
    node_id           STRING,
    community_id      STRING,
    flow_start_window UINT64,
    seq_in_window     UINT32 DEFAULT 0,
    PRIMARY KEY (flow_uid)
);

CREATE NODE TABLE IF NOT EXISTS Alert (
    event_id     STRING,
    node_id      STRING,
    flow_uid     STRING,
    community_id STRING,
    PRIMARY KEY (event_id)
);

CREATE NODE TABLE IF NOT EXISTS TelemetryEvent (
    event_id     STRING,
    node_id      STRING,
    flow_uid     STRING,
    community_id STRING,
    PRIMARY KEY (event_id)
);

// Correlación flujo<->flujo intra-nodo por community_id; host<->flujo anotando SIEMPRE método+confianza (NAT, DAY 170).
CREATE REL TABLE IF NOT EXISTS CORRELATES_FLOW (FROM NetworkFlow TO NetworkFlow, community_id STRING, method STRING, confidence DOUBLE);
CREATE REL TABLE IF NOT EXISTS ALERT_ABOUT (FROM Alert TO NetworkFlow, method STRING, confidence DOUBLE);
CREATE REL TABLE IF NOT EXISTS TELEMETRY_ABOUT (FROM TelemetryEvent TO NetworkFlow, method STRING, confidence DOUBLE);
