// host_domain_v1 — esquema del grafo host (Wazuh → BD Kuzu propia)
// aRGus NDR · Pieza 3 (DEBT-HOST-PIEZA-3-KUZU-001) · DAY 245
// ISLA: BD separada, NUNCA el $KUZU de red. Lo aplica host_parquet_to_kuzu_loader.
// Decisión DAY 245: tactics/groups quedan como STRING JSON (props de Rule);
// MitreTechnique = {technique_id, name}. Control/REQUIRES aparcados (P4).

// ---- Nodos ----

CREATE NODE TABLE IF NOT EXISTS Host (
    host_id     STRING,
    name        STRING,
    ip          STRING,
    os_hostname STRING,
    PRIMARY KEY (host_id)
);

CREATE NODE TABLE IF NOT EXISTS HostEvent (
    event_id       STRING,
    timestamp      STRING,
    rule_id        STRING,
    level          INT32,
    decoder        STRING,
    location       STRING,
    full_log       STRING,
    srcuser        STRING,
    dstuser        STRING,
    srcip          STRING,
    srcport        STRING,
    uid            STRING,
    command        STRING,
    data_json      STRING,
    wazuh_alert_id STRING,
    PRIMARY KEY (event_id)
);

CREATE NODE TABLE IF NOT EXISTS Rule (
    rule_id     STRING,
    level       INT32,
    description STRING,
    groups      STRING,
    tactics     STRING,
    PRIMARY KEY (rule_id)
);

CREATE NODE TABLE IF NOT EXISTS MitreTechnique (
    technique_id STRING,
    name         STRING,
    PRIMARY KEY (technique_id)
);

// ---- Aristas ----

CREATE REL TABLE IF NOT EXISTS ON_HOST (FROM HostEvent TO Host);
CREATE REL TABLE IF NOT EXISTS MATCHED (FROM HostEvent TO Rule);
CREATE REL TABLE IF NOT EXISTS MAPS_TO (FROM Rule TO MitreTechnique);