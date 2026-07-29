# PROMPT DE CONTINUIDAD — aRGus NDR — DAY 237

## Punto de entrada (mide, no asumas)
    git log --oneline -6
    git status
    vagrant status
DAY 236 cerró **Zeek EN EL GRAFO**: bronce→oro→Kuzu de punta a punta, criterio cumplido y
flow_uid verificado. Config P3 corregida y commiteada (`1eca3ca0`, config a valores Zeek).
Lo primero al arrancar: confirmar el commit de docs del cierre (prompt de continuidad + BACKLOG
DAY 236). Si no se hizo, hacerlo antes de tocar nada. `git add` explícito (nunca -a/-u por la
instrumentación WIP en zmq_handler.cpp).

## El estado que ordena el día
**Los TRES sensores tienen adapter y saben llegar al grafo, cada uno probado E2E:**
- aRGus nativo (bronce→oro→Kuzu, DAY 226-228).
- Suricata (adapter→bronce→oro→Kuzu, DAY 226-228; 2.870 alertas → 775 NetworkFlow).
- Zeek (adapter→bronce→oro→Kuzu, DAY 235-236; 31.735 telemetría → 31.735 NetworkFlow, 1:1).

Lo que FALTA del objetivo declarado: que **UNA corrida de `mitre-start` arrastre a los tres a la
MISMA BD Kuzu**. Hoy cada sensor aterriza en su propia BD; el mecanismo multi-sensor en una BD
compartida está PROBADO (Suricata cargó sin tocar el loader, DAY 228; CORRELATES_FLOW poblado
DAY 232), pero nunca se ha corrido con los tres a la vez desde el target.

## Candidato de batalla DAY 237 (Alonso decide el corte)
Objetivo: **incluir Zeek en `mitre-start` para que el grafo del ataque tenga TRES telemetrías.**
Son varios sub-pasos; "un día, una batalla" — cortar midiendo, no forzando.
1. **LO PRIMERO A MEDIR — cómo ve Zeek el tráfico del MITRE.** nmap -A dispara contra los
   servicios del `defender`. aRGus esnifa en vivo; Suricata lee su eve.json (producido en vivo en
   la VM suricata). ¿Cómo llega ese MISMO tráfico a la VM `zeek`? ¿Captura en vivo, o replay de un
   pcap de la ventana del nmap? MEDIR el setup actual antes de escribir wiring — es el paso que
   puede no ser trivial.
2. **Windowing de Zeek a T0.** El conn.log acumulará conexiones entre corridas igual que el
   eve.json de Suricata (DEBT-MITRE-SURICATA-EVE-NOT-WINDOWED-001). El adapter necesita filtrar a
   `mtime>T0` o cada run arrastra el tráfico del anterior. El baseline `destroy -f && up` lo
   neutraliza (nace vacío), así que es hardening, NO bloqueo del MVP.
3. **Tramo Zeek dentro del script**, espejando la mitad Suricata de `mitre_start.sh`: zeek adapter
   (toy key exportada inline en el MISMO `-c`) → converter (toy key, verifica HMAC) → loader a la
   BD **compartida** del run (la misma `mitre-*.kuzu`, no una fresca). El loader es idempotente
   (MERGE + ON CREATE SET) → cargar los tres oro en la misma BD es seguro.
4. **Poblador CORRELATES_FLOW + consultas.** Tras cargar los tres, correr el poblador (DAY 232) y
   medir el titular cross-sensor de TRES vías. Aquí se mide POR FIN si Zeek y Suricata (ambos epoch
   real del mismo tráfico, mismo node_id) **convergen en UN NetworkFlow** (si el window bucketea
   igual) o quedan como nodos separados unidos por CORRELATES_FLOW. Es la medida jugosa del día.

## Después de DAY 237
- Promoción de `mitre-start` a tarea de **EMECAS+++** (decisión DAY 234): test de aceptación
  `destroy -f && up` desde cero + gate auto-verify (titular_grafo ≤ intersección grep). Se hace
  cuando `mitre-start` esté COMPLETO con los sensores.
- **Wazuh** (4º sensor, mismo estándar de adapter). El ADAPTER_TOOLCHAIN ya está en el Vagrantfile
  y el scaffold funciona (arreglado DAY 235). Con Wazuh, las cuatro señales al grafo → cierre del
  pipeline.

## Invariantes (no negociar)
- Medir, no votar. HECHO ≠ SOSPECHADO; cada afirmación a salida de comando.
- flow_uid = **BLAKE2b(node_id ‖ community_id ‖ flow_start_window ‖ seq_in_window)** — el window SÍ
  entra (medido DAY 236 en flow_uid.hpp:53, 17 call sites 3-arg). El invariante viejo "sin tiempo,
  Opción B" del prompt es DERIVA DOCUMENTAL (DEBT-FLOWUID-INVARIANT-DOC-DRIFT-001): corregirlo en
  docs/paper. node_id = punto de observación, NO el host. Join cross-sensor por community_id.
- Un día, una batalla. Vía Appia (un criterio que no puede ponerse rojo no mide).
- No `grep -rn` desde raíz (usa `git grep`). No encadenar salidas grandes.
  `git add` explícito. macOS: nunca `sed -i` sin `-e ''`. Build/commit/push desde el host.
  A horas malas, parar.
- SIN switches en JSON (DAY 222): grafo data-driven. Cada componente su config con su source_sensor;
  mismo buzón de bronce plano /vagrant/logs/correlation.
- Export de la clave HMAC SIEMPRE inline en el MISMO `vagrant ssh <vm> -c '...'` (un export en un
  `-c` separado muere con ese shell). La toy key (0123…×4) es la clave end-to-end de mitre-start.

## Estado del tramo Zeek (DAY 236, HECHO y medido)
- Config P3 cerrada (`1eca3ca0`): input_path → /vagrant/logs/day235-zeek-neris/conn.log,
  node_id cpp_sniffer_v33_day12, hmac_key_env = NOMBRE de var ARGUS_BRONZE_HMAC_KEY_HEX.
- Bronce de referencia (toy key): /vagrant/logs/correlation/zeek-2026-07-29-010814.csv (31.735 filas).
- Oro: /vagrant/logs/day236-zeek-gold/zeek.{avro,parquet} (31.735 válidas, 0 descartadas).
- Kuzu: /vagrant/logs/day236-zeek-kuzu/zeek.kuzu (Escritas 31.735, fallidas 0). Padre a mano
  (`mkdir -p`), Kuzu no crea la ruta.
- Criterio: `MATCH (e:TelemetryEvent)-[:TELEMETRY_ABOUT]->(f:NetworkFlow) RETURN e.source_sensor,
  e.event_id, f.flow_uid LIMIT 3` → filas `zeek|zeek:…|…`. flow_uid diana
  `MSPLWl/54skxbMNSmGOsOzDbyun6+K8s/gVFsivQtcE=` = idéntico al recompute del converter (fontanería
  converter→loader→sink, no oráculo). Todas TelemetryEvent, 0 Alert.
- Censo: `count(NetworkFlow)` = 31.735, 1:1 con TelemetryEvent, cero colapso (conn.log = una fila
  por conexión, cada una con su ts → window distinto → flow_uid distinto). Contraste con Suricata
  (775): la granularidad de la fuente manda. Número de paper.

## A medir (afecta al día, no se asume)
- Cómo llega el tráfico del MITRE a la VM zeek (ver batalla, punto 1). Es el desbloqueo del día.
- Convergencia Zeek↔Suricata en la BD compartida: ¿UN NetworkFlow (window igual) o dos + arista
  CORRELATES_FLOW? Medir con los dos oros en una BD, no antes.
- El binario `parquet_to_kuzu_loader` accede a las cols del Parquet por índice posicional sin
  validar esquema (fragilidad DAY 228). Inofensivo mientras el oro salga del MISMO converter — que
  es el caso. No re-medir salvo que cambie el converter.

## Deudas registradas DAY 236 (en docs/BACKLOG.md, sección DAY 236)
- ✅ DEBT-ZEEK-ADAPTER-CONFIG-SURICATA-RESIDUE-001 (P3) — RESUELTA (1eca3ca0).
- DEBT-MITRE-ZEEK-CONN-NOT-WINDOWED-001 (P3, nueva) — windowing de Zeek a T0 en mitre-start.
- DEBT-FLOWUID-INVARIANT-DOC-DRIFT-001 (P4, nueva) — el invariante "sin tiempo" no coincide con el
  código; corregir docs/paper.
- DEBT-DOWNSTREAM-INGESTION-NOT-ORCHESTRATED-001 (P2) — reforzada: bronce→oro→Kuzu se corrió a mano.
- DEBT-ZEEK-PROTO-CASE-001 (P3) — proto minúsculas (Zeek) vs mayúsculas (Suricata); decidir antes
  del cross-sensor (protocol del nodo puede oscilar por orden de escritura, ON CREATE SET).

## Notas de fontanería (medidas, no re-medir)
- Binarios en `/vagrant/correlation-engine/build/{bronze_to_gold_converter,parquet_to_kuzu_loader,
  kuzu_query}` del 25-jul, funcionan sin rebuild (usados DAY 228/232/236).
- CLIs: converter `<bronce.csv> <avro.out> <parquet.out>` (verifica HMAC → necesita la clave);
  loader `<oro.parquet> <kuzu_db> <schema.cypher>` (NO verifica HMAC → sin clave);
  kuzu_query `<kuzu_db> <cypher>`. Schema en correlation-engine/schema/schema.cypher.
- Consultas Cypher sin literales de string dentro de `vagrant ssh -c '...'` (evita el infierno de
  comillas); si hace falta filtrar por 'zeek', mejor RETURN el source_sensor y leerlo, no WHERE.
- Loader ~108-117 filas/s (flush por lotes de 512 filas / 1e9 ns).

## Recordatorio de tono
Alonso pilota; mide contra fichero y pega salida. `make pipeline-stop` al cerrar. zeek-adapter.md
está al tope (~30KB/32KB): al condensar, sacar el tramo aguas abajo a /areas/zeek-a-grafo.md,
espejando parquet-a-kuzu.md de Suricata.