# schema/

Esquema Kuzu v0.11.3 del correlation-engine (DEBT-NEO4J-FLOW-KEY-001, ADR-052).

## schema.cypher — HECHO, verificado
El engine C++ ejecuta este DDL al inicializar la BD. Verificado: carga, idempotencia (`IF NOT EXISTS`),
y dedup nativo sobre vectores reales (V1/V2 distintos entran; V1 duplicado rechazado por PK).

## Decisiones horneadas (verificadas contra Kuzu 0.11.3)
- `PRIMARY KEY (flow_uid)` = dedup + obligatoriedad NATIVOS. Sin split Community/Enterprise (a diferencia de Neo4j).
- `flow_uid` único por construcción (hash compuesto) -> PK simple sustituye al "constraint compuesto" de Neo4j.
- Kuzu 0.11.3 NO soporta `NOT NULL` en no-PK ni PK compuesta. Consecuencia:
  **`node_id` obligatorio es INVARIANTE DE ENGINE** -> el `IGraphSink` rechaza escribir nodo sin `node_id`.
  No es constraint de BD; es contrato de código C++.
