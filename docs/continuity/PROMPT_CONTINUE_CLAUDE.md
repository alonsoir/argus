# DAY 175 — Zona bronce correlation_v1 cableada + verificada E2E. Prompt de continuidad.

═══════════════════════════════════════════════════════════════════════════════
ARRANQUE DAY 176 — LEER ESTO PRIMERO.
═══════════════════════════════════════════════════════════════════════════════
DAY 175 cerró el cableado del bronce: el CorrelationWriter (ml-detector) produce
correlation_v1 REAL, consumible por el reader del correlation-engine. 4 pasos verdes
(CMake + hook punto único + round-trip unitario + pipeline vivo: 3712 filas reales
con community_id, una validada con la clave de PRODUCCIÓN de etcd).

DOS BATALLAS DAY 176, ninguna bloqueada por lo de hoy:

(A) INJECTORS SINTÉTICOS pueblan community_id — AMBOS modos (decisión Alonso, Q1):
    1. ISOMORFO REALISTA: calcular community_id con la MISMA función que el sniffer
       real (sniffer::flow::compute_community_id), NO reimplementación. Empezar por
       tools/synthetic_sniffer_injector.cpp (alimenta el camino que hoy ejercita el
       bronce). Sin esto, los E2E sintéticos NO ejercitan el bronce (community_id
       vacío -> el hook lo descarta).
    2. MOCK AUTO-IDENTIFICABLE: formato distinguible (estilo "synth:test:hash") para
       no contaminar análisis con tráfico falso. El correlation-engine lo descarta
       antes de Kuzu.
    -> Esto desbloquea bronce DETERMINISTA en CI (hoy dependemos de pcap+eBPF, caro y
       no determinista).

(B) CAMBIO col 17 a STRING simbólico (decisión Alonso, Q2):
    - correlation_writer.cpp: escribir DetectorSource_Name() en vez de
      static_cast<int>. Reader (correlation_record.hpp) lee string.
    - Motivo: contrato auto-descriptivo, estable frente a evolución del enum en el
      .proto. Coste de tamaño irrelevante (dictionary-encoding Parquet aguas arriba).
    - Es el momento más barato: primer día con bronce real (las 3712 filas son de
      prueba, no histórico de valor).

(C) LADO CONSUMIDOR del engine (cuando toque): file_watch de bronce -> lectura de
    clave desde etcd /secrets/<componente> -> parse_and_verify -> Avro -> ZMQ.
    Aquí aterriza DEBT-BRONZE-KEY-PROVISIONING-001. parse_and_verify debe ser el
    PRIMER paso del consumidor (validar antes de tocar Kuzu) — riesgo señalado por
    Mistral: clave mala corrompe el grafo.

PENDIENTE DE REDACCIÓN — ADR-054 (modelo de confianza bronce multi-nodo, Q3):
    HMAC simétrico vale intra-nodo; no escala a N sensores -> Kuzu central. Explorar
    Ed25519 (ya en uso, ADR-025) CON o EN VEZ DE HMAC. Eje de decisión: coste CPU/RAM
    del central validando fila por fila con Ed25519 sobre cientos/miles de ficheros
    bronce. Opción jerárquica (Kimi): Ed25519 firma clave de sesión HMAC corta;
    HMAC valida el volumen. Flujo borrador -> Consejo -> aprobación, ANTES del lado
    consumidor cross-nodo. (OJO numeración: ADR-053 ya RESERVADO para JA3/JA4+TLS+BGP.)

LECCIONES DAY 175 (no repetir):
- STALE PROTO: construir SIEMPRE vía `make <target>` (corre dep `proto`, regenera y
  distribuye network_security.pb.h fresco a build-debug/proto/, aplica -Werror del
  Makefile). NUNCA `cmake -S . -B build` directo -> compila contra .pb.h rancio y
  rompe confuso (incidente DAY 175: "NetworkFeatures has no member community_id").
- KEY PROVISIONING: la clave HMAC del bronce NO es seed.hex, es la de etcd
  /secrets/<componente> (campo key). El round-trip con clave hardcodeada valida el
  contrato pero OCULTA el provisioning. El consumidor en prod DEBE pedirla a etcd.
- INVARIANTE community_id: TODAS las variantes del sniffer (x86/ARM, eBPF/libpcap,
  special/plain) DEBEN poblar community_id — es el punto de unión con Suricata/Zeek.

PRIMER COMANDO DAY 176:
vagrant ssh -c "grep -rn 'community_id\|compute_community_id\|set_community_id' /vagrant/tools/synthetic_sniffer_injector.cpp"
# confirmar que el injector NO puebla community_id hoy, y localizar dónde sellar la
# 5-tupla para invocar compute_community_id. Luego (A) modo isomorfo -> mock -> (B).

═══════════════════════════════════════════════════════════════════════════════
RESUMEN DAY 175 — Bronce cableado (los 4 pasos)
═══════════════════════════════════════════════════════════════════════════════
Día de cableado y verificación, no de ADR. El CorrelationWriter pasó de suelto a
cableado y produciendo bronce real consumible.

PASO 1 — CMake: correlation_writer.cpp dado de alta en SOURCES del ml-detector
  (lista explícita, no GLOB). OpenSSL ya linkado por CsvEventWriter.
PASO 2 — Hook punto único: correlation_writer_ construido junto a csv_writer_ en
  zmq_handler, reutilizando el MISMO hmac_key_hex_ (cero divergencia de clave por
  construcción). write_record() cableado ANTES de la bifurcación rag/no-rag (NO
  dentro del if rag/csv) — evita el "bug de los dos caminos". Filtro:
  if (correlation_writer_ && !community_id().empty()).
PASO 3 — Round-trip unitario (prueba de oro): test_correlation_roundtrip en
  ml-detector/tests/integration/. Escribe NetworkSecurityEvent con CorrelationWriter
  REAL, relee última línea, parse_and_verify REAL del engine. 18 campos + HMAC.
  El test vive en ml-detector (ya linka protobuf/OpenSSL) e incluye el reader del
  engine, NO al revés — el correlation-engine se mantiene limpio de protobuf.
  Gateado contra rebuild limpio (make ml-detector && make test-components). PASSED.
PASO 4 — Pipeline vivo: replay smallFlows.pcap (14261 paquetes, 1209 flujos).
  3712 filas reales en /vagrant/logs/correlation/argus/2026-06-05.csv, todas con
  community_id poblado por el sniffer eBPF (formato 1:wKZ...=). Sello final: una
  fila REAL validada por parse_and_verify con la clave de PRODUCCIÓN de etcd
  (/secrets/ml-detector campo key) — NO seed.hex.

DECISIONES DEL CONSEJO (8/8 respondieron):
- Q1 injectors primero (unánime) -> AMBOS modos (Alonso).
- Q2 col 17 -> STRING simbólico (Alonso; statu quo rechazado por consenso).
- Q3 abrir ADR-054 modelo de confianza Ed25519 con/en-vez-de HMAC (Alonso).
DEUDAS NUEVAS: DEBT-BRONZE-KEY-PROVISIONING-001, DEBT-BRONZE-PROVISIONING-E2E-001.

═══════════════════════════════════════════════════════════════════════════════
RESUMEN DAY 174 (histórico)
═══════════════════════════════════════════════════════════════════════════════
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