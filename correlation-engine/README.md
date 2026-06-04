# correlation-engine (C++20)

Engine de correlación de aRGus NDR (ADR-048). Arquitectura lambda / medallion:
recoge los registros de correlación de bronce (CSV `correlation_v1`), valida su
integridad, los convertirá a Avro para transporte distribuido, y aguas abajo en el
servidor se transforman a Parquet (plata→gold) para ingesta en el grafo Kuzu.

## Estado (DAY 174)
- `include/correlation_engine/flow_uid.hpp` — flow_uid canónico (BLAKE2b, libsodium). Verificado.
- `include/correlation_engine/correlation_record.hpp` — contrato correlation_v1 (19 cols, consumidor).
- `include/correlation_engine/correlation_reader.hpp` + `src/correlation_reader.cpp`
  — lector resiliente de bronce: valida HMAC por fila, descarta tampering/truncado. Verificado.
- `schema/schema.cypher` — esquema Kuzu 5.x (PK=flow_uid: dedup+obligatoriedad nativos). Verificado.
- `tests/` — GoogleTest: flow_uid (vectores) + correlation_reader (6 casos de frontera). VERDE.

## Frontera de confianza
El writer (en ml-detector) escribe append NO-atómico. El reader valida HMAC ANTES de parsear:
una fila truncada o manipulada no valida y se DESCARTA (no lanza). El HMAC por fila es a la vez
anti-tampering y detector de escritura-a-medias.

## Build & test (en el guest Debian)
    cmake -S . -B build && cmake --build build && ctest --test-dir build --output-on-failure
