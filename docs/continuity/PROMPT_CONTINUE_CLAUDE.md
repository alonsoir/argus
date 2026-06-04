# DAY 174 — correlation-engine (C++20) + zona bronce. Prompt de continuidad.

═══════════════════════════════════════════════════════════════════════════════
ARRANQUE DAY 175 — LEER ESTO PRIMERO. Integrar el writer en ml-detector.
═══════════════════════════════════════════════════════════════════════════════
El correlation-engine (consumidor) está VERDE en el guest (libsodium 1.0.19, OpenSSL 3.0.20,
GTest 1.12.1, 2/2 suites). PERO su productor —el CorrelationWriter— sigue SUELTO en el ml-detector.
Hasta cablearlo NO hay datos de bronce reales. Cuatro pasos, en orden:

1. ALTA EN ml-detector/CMakeLists.txt
    - Añadir correlation_writer.cpp a las fuentes del ejecutable.
    - Confirmar OpenSSL::Crypto/SSL linkado (el HMAC lo necesita; csv_event_writer ya usa OpenSSL → casi seguro está).

2. HOOK EN zmq_handler.cpp
    - Construir correlation_writer_ junto a csv_writer_ (~líneas 124-133): base_dir=/vagrant/logs/correlation/argus,
      hmac_key_hex del config (nueva sección en config_loader).
    - Llamada en el PUNTO ÚNICO del bucle, ANTES de la bifurcación rag/no-rag (~línea 516),
      NO dentro del if(!rag_logger_ && csv_writer_) de la 518 (bug de los dos caminos).
    - Filtro: if (correlation_writer_ && !event.network_features().community_id().empty()) write_record(event);

3. TEST UNITARIO DEL WRITER (en ml-detector, contra el .pb.h REAL)
    - Construir un NetworkSecurityEvent, escribir, releer, validar HMAC + 19 columnas.
    - Esto cierra el ROUND-TRIP real: writer (ml-detector) produce → parse_and_verify (correlation-engine) consume.
      Es la PRUEBA DE ORO de que ambos lados hablan correlation_v1 byte a byte (principio de los vectores congelados).

4. TEST DE INTEGRACIÓN / EMECAS
    - Arrancar ml-detector, inyectar tráfico, confirmar CSV en /vagrant/logs/correlation/argus/ con filas válidas.

DOS AVISOS:
- RIESGO VIVO: el writer se compiló contra STUBS, no contra tu network_security.pb.h. Si overall_threat_score()
  o authoritative_source() tienen otro nombre exacto en el proto generado, el build del ml-detector lo canta
  al instante (fallo de compilación obvio, no silencioso). Es lo PRIMERO que puede chirriar.
- ROUND-TRIP es la prueba de oro: hoy cada lado se probó por separado (writer vs stubs, reader vs fila a mano).
  El test que escribe con CorrelationWriter y lee con parse_and_verify garantiza cero deriva entre las 19 columnas.

PRIMER COMANDO DAY 175:
vagrant ssh -c "grep -n 'csv_writer_\|add_executable\|target_link\|target_sources\|OpenSSL' /vagrant/ml-detector/CMakeLists.txt"
# ver dónde dar de alta el .cpp y si OpenSSL ya está linkado. Luego paso 1→2→3→4.

═══════════════════════════════════════════════════════════════════════════════
RESUMEN DAY 174
═══════════════════════════════════════════════════════════════════════════════
Día de construcción, no de ADR. Nació el correlation-engine como componente C++20 sobre Debian.
Se diseñó la arquitectura lambda/medallion de correlación, se eligió el motor de grafo, y se escribió
el primer eslabón de la zona bronce (writer en ml-detector) + su consumidor (reader en correlation-engine).
Todo verde y verificado.

## Decisiones de arquitectura (cerradas)

1. flow_uid se calcula en el lado servidor (Kuzu), NO en el transporte. Hash de
   node_id || community_id || flow_start_window. Encoding canónico: length-prefix, tag de versión
   "argus-flowuid-v1", seq_in_window siempre presente. BLAKE2b (libsodium), digest_size=32 OBLIGATORIO.

2. node_id = NetworkSecurityEvent.originating_node_id (campo 3), poblado por el sniffer desde config_.node_id.
   Identidad opaca del PUNTO DE CAPTURA (sensor), no de la organización.

3. Motor de grafo: Kuzu v0.11.3 vendoreado (embebido, Cypher, C++, MIT, Parquet nativo). Tras un IGraphSink
   con contrato Cypher (patrón ICryptoProvider) para ser sustituible (LadybugDB si Kuzu se depreca del todo).
   Kuzu archivado 2025-10; riesgo asumido conscientemente.
    - Consecuencia: PRIMARY KEY(flow_uid) da dedup + obligatoriedad NATIVOS. Desaparece el split
      Community/Enterprise de Neo4j. node_id obligatorio pasa a invariante de engine (Kuzu 0.11.3 no tiene
      NOT NULL en no-PK ni PK compuesta). flow_uid único por construcción → PK simple = dedup compuesto.

4. Arquitectura lambda / medallion para escala (miles de nodos: hospitales, ayuntamientos, pymes; España→Europa).
    - Bronce: registro mínimo CSV correlation_v1 por componente (replayable).
    - Transporte: Avro (row-oriented, optimizado para transmisión distribuida).
    - Plata: Parquet por fichero/fuente. Gold: Parquet con el join hecho.
    - El JOIN cross-sensor ocurre en Kuzu por community_id, NO casando ficheros en el sensor
      (timestamps no comparables, hallazgo DAY 172).

5. Un contrato, una responsabilidad. El CSV de 127 columnas del RAG (csv_event_writer v1.0) queda INTACTO.
   El registro de correlación es OTRO fichero/contrato/directorio (/vagrant/logs/correlation/argus/).

6. Bronce PRESERVA, gold DECIDE. El registro lleva los 4 scores + authoritative_source; Kuzu elige la
   confianza de la :Alert con todas las señales (aRGus hoy; Suricata/Zeek/Wazuh mañana).

7. NO se parte el contrato protobuf todavía. Cambio de máximo radio (6 componentes); se aplaza hasta
   estabilizar, con su propio ADR + EMECAS.

## Entregables verificados (verdes)

### ml-detector (productor) — PENDIENTE DE INTEGRAR (ver ARRANQUE DAY 175)
- correlation_writer.hpp + .cpp — escribe correlation_v1 (19 cols + HMAC). Patrón del CsvEventWriter
  (HMAC OpenSSL, rotación fecha+tamaño, append no-atómico, thread-safe). Descarta community_id vacío.
  Compilado + smoke test verde CONTRA STUBS del proto.

### correlation-engine (consumidor) — árbol completo, VERDE en el guest
- flow_uid.hpp — flow_uid canónico, vectores verdes.
- correlation_record.hpp — struct del contrato correlation_v1.
- correlation_reader.{hpp,cpp} — valida HMAC (tiempo constante) + parsea; descarta tampering, truncado,
  col count erróneo, no numérico. 6 casos de test verdes.
- schema/schema.cypher — esquema Kuzu, verificado (carga, idempotencia, dedup sobre vectores reales).
- CMakeLists alineado con convenciones del proyecto (LIBSODIUM pkg-config, nlohmann fallback header-only
  a ../third_party/json/include, OpenSSL, GoogleTest). TODO COMPILA EN EL GUEST DEBIAN, nunca en macOS host.

## Contrato correlation_v1 (19 columnas, sin header, validación por fila)
0 schema_version · 1 source_sensor · 2 event_id · 3 node_id · 4 community_id (clave join) ·
5 flow_start_sec · 6 flow_start_nano · 7 src_ip · 8 dst_ip · 9 src_port · 10 dst_port ·
11 protocol · 12 final_classification · 13 threat_category · 14 fast_detector_score ·
15 ml_detector_score · 16 overall_threat_score · 17 authoritative_source · 18 HMAC-SHA256(cols 0-17)

## Frontera de confianza de bronce
El writer escribe append NO-atómico. El reader valida HMAC ANTES de parsear: una fila truncada
(escritura a medias) o manipulada (tampering) no valida y se DESCARTA, no lanza. El HMAC por fila
es a la vez anti-tampering y detector de escritura-a-medias. Comparación de HMAC en tiempo constante.

## Deudas abiertas (no bloqueantes)
- DEBT-NODEID-CRYPTO-IDENTITY-001: node_id = UUID opaco generado en aprovisionamiento, fijado en
  deployment.yaml (inventario firmado, rellenado vía Jinja2 al config.json de cada componente). Atributos
  mutables (organización, tipo, país, dirección) como propiedades de un nodo :Node en el grafo, NUNCA dentro
  del id (lección: Hospital Infanta Cristina → Universitario sin partir la historia del nodo). Lo que importa
  es la GOBERNANZA de la unicidad global, no el tipo.
- firewall-acl-agent: su BlockedEvent y el mensaje proto Detection no llevan community_id. Requiere campo
  aditivo en proto para correlacionar. Entra como ENRIQUECIMIENTO ("flujo bloqueado"), no espina dorsal.
- Suricata/Zeek/Wazuh: adaptadores a correlation_v1 desde eve.json / conn.log / alerts. Otra batalla.
- IGraphSink + backend libkuzu: el sink Cypher en src/ del correlation-engine, con test que inserte
  vectores y reproduzca en C++ real el dedup probado hoy en Python (binding Kuzu, solo banco de pruebas).
- Lado Avro/transporte del correlation-engine: file_watch de bronce → conversión Avro → ZMQ al servidor.

## Entorno y reglas vigentes
- TODO compila en el guest Debian (eBPF/XDP es Linux-only). macOS = anfitrión. NUNCA cmake en el host
  sobre este repo (contamina CMakeCache.txt por el montaje /vagrant compartido → rm -rf build).
- vagrant ssh siempre con -c. -Werror invariante. Python3 heredoc en macOS (nunca sed -i sin -e '').
- Kuzu como banco de pruebas se usó vía binding Python en sandbox; PRODUCCIÓN es C++ embebiendo libkuzu.