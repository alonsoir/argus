# PROMPT DE CONTINUIDAD — aRGus NDR — DAY 238

## Punto de entrada (mide, no asumas)
    git log --oneline -6
    git status
    vagrant status
DAY 237 cerró **los TRES sensores en un grafo por `mitre-start`**: una corrida, cero comandos
manuales, aRGus + Suricata + Zeek a la MISMA BD Kuzu. Rama `feat/zeek-to-graph`. Lo primero al
arrancar: confirmar el commit del cierre DAY 237 (cableado de `scripts/mitre_start.sh` + prompt de
continuidad + BACKLOG DAY 237). Si no se hizo, hacerlo antes de tocar nada. `git add` explícito
(nunca -a/-u por la instrumentación WIP en zmq_handler.cpp). **NO mergear a main** (decisión DAY 237):
antes hay que actualizar EMECAS+++ y probarlo en esta misma rama.

## El estado que ordena el día
**Los TRES sensores llegan al grafo por una sola corrida de `mitre-start`, probado E2E DAY 237:**
- aRGus nativo (sniffer eBPF, eth2 intnet) — bronce 2554 → TelemetryEvent 1466 (colapso event_id).
- Suricata (systemd vivo, eth1=100.10) — alert-only, 162 alertas.
- Zeek (zeekctl live, eth1=100.11) — conn.log 1126 → 1126 NetworkFlow (1:1).

Lo que FALTA del objetivo declarado: el **4º sensor, Wazuh**, mismo estándar de adapter. Con Wazuh,
las cuatro señales al grafo → cierre del pipeline multi-sensor. La VM `wazuh` está **not created**.

## Candidato de batalla DAY 238 (Alonso decide el corte midiendo)
Objetivo: **Wazuh al grafo, y a `mitre-start` como 4ª telemetría.** Son varios sub-pasos; "un día,
una batalla".
1. **LO PRIMERO A MEDIR — ¿qué emite Wazuh y lleva community_id?** Wazuh es HIDS (host-based:
   integridad de ficheros, reglas de log, rootkit), NO un sensor de flujo de red como Zeek/Suricata.
   La correlación del grafo va por `community_id` (5-tupla). MEDIR si Wazuh produce ALGO con
   community_id / 5-tupla que pueda unirse a un NetworkFlow, o si su aportación es de OTRA naturaleza
   (contexto de host, no corroboración de flujo). Esto decide si Wazuh entra por el mismo molde de
   adapter o si su integración es distinta. Es el paso que puede no ser trivial — NO asumir que
   Wazuh encaja en correlation_v1 tal cual.
2. **Levantar la VM `wazuh` de cero.** `vagrant up wazuh` (nombrada; está not created). El
   provisioning (install-wazuh + adapter-toolchain) entra en la RUTA CRÍTICA por primera vez, igual
   que zeek DAY 235 — un fallo ahí tumba la corrida, y eso es lo deseado. El ADAPTER_TOOLCHAIN ya
   está en el Vagrantfile y el scaffold funciona (arreglado DAY 235).
3. **Scaffold + adapter** siguiendo el estándar [[suricata-adapter]] / [[zeek-adapter]]:
   `scaffold_adapter.py --sensor wazuh` → escribir el to_row del formato de salida de Wazuh
   (JSON de alertas, probablemente). Decidir event_id de campos ESTABLES (no de un uid volátil,
   lección Zeek DAY 235), prefijo `wazuh:`. Cols de veredicto según sea alerta o telemetría.
4. **Tramo aguas abajo + wiring en `mitre-start`** espejando la mitad Suricata/Zeek: adapter (toy
   key inline en el MISMO `-c`) → converter → loader a la BD **compartida** del run → poblador. El
   ciclo de vida (si Wazuh corre como servicio persistente, como Suricata, o hay que arrancarlo, como
   Zeek) se MIDE en el paso 1/2.

## Después de DAY 238 — la promoción a EMECAS+++ (en ESTA rama, sin merge)
- Con los CUATRO sensores en `mitre-start`, promocionarlo a tarea de **EMECAS+++** (decisión DAY 234):
  test de aceptación `destroy -f && up` desde CERO (baseline limpio → todos los eve.json/conn.log
  nacen vacíos, censos limpios de un solo ataque) + gate auto-verify (`titular_grafo ≤ intersección
  grep`, relación honesta: `>` imposible = bug de consulta; `<` = colisión event_id, WARN+log no
  abort; `==` verde).
- **DECISIÓN DAY 237 (Alonso): probar la nueva versión de EMECAS+++ en la rama `feat/zeek-to-graph`
  ANTES de cualquier merge a main.** No se mergea hasta que EMECAS+++ pase verde en la rama con los
  cuatro sensores. El merge a main es el paso final del pipeline multi-sensor, no de DAY 238.

## Invariantes (no negociar)
- Medir, no votar. HECHO ≠ SOSPECHADO; cada afirmación a salida de comando.
- flow_uid = **BLAKE2b(node_id ‖ community_id ‖ flow_start_window ‖ seq_in_window)** — el window SÍ
  entra (flow_uid.hpp:53). node_id = punto de observación, NO el host. Join cross-sensor por
  community_id. El invariante viejo "sin tiempo, Opción B" es DERIVA DOCUMENTAL
  (DEBT-FLOWUID-INVARIANT-DOC-DRIFT-001): corregir en docs/paper.
- Un día, una batalla. Vía Appia (un criterio que no puede ponerse rojo no mide).
- No `grep -rn` desde raíz (usa `git grep`). No encadenar salidas grandes. `git add` explícito.
  macOS: nunca `sed -i` sin `-e ''`. Build/commit/push desde el host. A horas malas, parar.
- SIN switches en JSON (DAY 222): grafo data-driven. Cada componente su config con su source_sensor;
  mismo buzón de bronce plano /vagrant/logs/correlation (o /vagrant/logs/lab en mitre-start).
- Export de la clave HMAC SIEMPRE inline en el MISMO `vagrant ssh <vm> -c '...'` (un export en un
  `-c` separado muere con ese shell). La toy key (0123…×4) es la clave end-to-end de mitre-start;
  la clave REAL solo la usa el converter de aRGus (curl al etcd :2379, inseguro, deuda P1).
- **Zeek en mitre-start = zeekctl LIVE** (DAY 237): `deploy` tras el marker T0 (conn.log nace ~T0,
  windowing por construcción) → nmap → drenaje → **cosechar del spool ANTES del `stop`** (el stop
  archiva el conn.log fuera del spool, gzip+fechado) → adapter SOLO-config (input_path en el json,
  base_dir=$LAB) → converter → loader a la BD compartida. Visibilidad por FLOODING del intnet de
  VirtualBox (eth1 sale NO-promisc pero captura igual, como Suricata@.10).

## Estado del tramo multi-sensor (DAY 237, HECHO y medido)
- `make mitre-start` E2E verde: pipeline-start (8 servicios) → clave HMAC real → zeek deploy →
  nmap -A (113 s) → drenaje → cosecha spool + stop → oros de los tres → 3 loaders a
  `/vagrant/logs/day234-kuzu/mitre-20260729-065150.kuzu` (fallidas=0) → poblador CORRELATES_FLOW.
- Censo: `argus|1466 · suricata|162 · zeek|1126`. invariante (community_id distinto en extremos) = 0.
- **TITULAR HONESTO = 44 flujos corroborados por los TRES sensores** (y la corroboración heterogénea
  sniffer↔IDS argus/zeek↔suricata = el MISMO 44; estable con los 44 de DAY 233 → el número no se
  movió al añadir Zeek, que es lo que queremos). Descomposición medida (sin re-correr):
    - Por par: argus↔zeek = 1089 · argus↔suricata = 44 · suricata↔zeek = 44.
    - Por nº de sensores: 1 sensor = 131 cids · 2 = 1045 · **3 = 44**. Cuadra: 1089 = 44 + 1045.
    - **1089** = acuerdo de community_id IMPLEMENTACIÓN-INDEPENDIENTE aRGus(eBPF)↔Zeek sobre tráfico
      adversarial → valida el estándar community_id a escala, NO es "detección corroborada" (homogéneo,
      dos sniffers del mismo wire; claim más débil que sniffer↔IDS). No vender 1089 como "flujos
      corroborados".
    - Predicción CONFIRMADA: los sensores NO convergen en un NetworkFlow, quedan separados unidos por
      CORRELATES_FLOW (window micros-exacto, ADR-052 §3.1.4 sin implementar → distinto flow_uid).
- El windowing asimétrico NO infló el titular: Suricata en caliente (eve acumulado, 162 con pre-T0)
  solo corroboró 44 — las pre-T0 no tienen pareja windowed en argus/zeek. El inflado queda en el
  censo de nodos de Suricata, no en el 44.

## Cableado de Zeek en scripts/mitre_start.sh (DAY 237, para referencia)
- Variables: `ZEEKCTL=/opt/zeek/bin/zeekctl`, `ZEEK_ADAPTER=/vagrant/zeek-adapter/build-zeek/zeek_adapter`
  (confirmado, 2.2M), `ZEEK_SPOOL=/opt/zeek/spool/zeek` (conn.log vivo en texto plano).
- 5 bloques insertados con `mitre_start_add_zeek.py` (v2, anclado/all-or-nothing/idempotente/backup):
  vars, `zeekctl deploy` tras el marker, cosecha+`stop` tras el drenaje, oro 4b (adapter→converter),
  3ª carga a `$KUZU`. `bash -n` limpio. El adapter Zeek se invoca SOLO-config (leidas=1126, sin arg2).

## A medir DAY 238 (afecta al día, no se asume)
- ¿Wazuh emite community_id / 5-tupla? (ver batalla, punto 1). Es el desbloqueo del día — decide si
  Wazuh entra por correlation_v1 o su integración es de otra naturaleza (host-context).
- Ciclo de vida de Wazuh: ¿servicio persistente (como Suricata) o hay que arrancarlo (como Zeek)?
- `parquet_to_kuzu_loader` accede a las cols del Parquet por índice posicional sin validar esquema
  (fragilidad DAY 228). Inofensivo mientras el oro salga del MISMO converter — el caso. No re-medir.

## Deudas registradas DAY 237 (en docs/BACKLOG.md, sección DAY 237)
- ✅ DEBT-MITRE-ZEEK-CONN-NOT-WINDOWED-001 (P3) — NEUTRALIZADA por el `zeekctl deploy` fresco
  (conn.log nace ~T0). Queda como hardening opcional para correr en caliente sin destroy&up, NO bloqueo.
- 🆕 DEBT-ZEEK-WEBSOCKETS-MISSING-001 (P4) — falta el módulo py `websockets` en la VM zeek →
  zeekctl `print`/`netstats` muertos (introspección live, drops de captura). NO afecta captura ni
  pipeline. Añadir al provisioning de zeek / ADAPTER_TOOLCHAIN.
- DEBT-EVENT-ID-COLLISION-001 (P2) — reconfirmada: argus 2554 bronce → 1466 TelemetryEvent
  (~1088 colapsados). No afecta el titular (community_id) pero pierde nodos argus.
- DEBT-MITRE-SURICATA-EVE-NOT-WINDOWED-001 (P3) — reconfirmada: en caliente el eve.json acumulado
  infla el censo de Suricata; NO infla el titular (medido DAY 237). Mismo hardening que el de Zeek.
- DEBT-DOWNSTREAM-INGESTION-NOT-ORCHESTRATED-001 (P2) — mitre-start automatiza ya los TRES sensores
  E2E; reduce pero NO cierra (sigue siendo one-shot, no un orquestador full-time / plano de control).
- DEBT-FLOWUID-INVARIANT-DOC-DRIFT-001 (P4) — abierta; el invariante "sin tiempo" no coincide con el
  código que hashea window. Corregir docs/paper.
- DEBT-ZEEK-PROTO-CASE-001 (P3) — proto minúsculas (Zeek) vs mayúsculas (Suricata); no medido si
  afloró en el grafo hoy; decidir antes de pulir el cross-sensor.

## Notas de fontanería (medidas, no re-medir)
- Binarios en `/vagrant/correlation-engine/build/{bronze_to_gold_converter,parquet_to_kuzu_loader,
  kuzu_query}` (jul 25), funcionan sin rebuild. Adapters: suricata_adapter
  `/vagrant/suricata-adapter/build-suricata/`, zeek_adapter `/vagrant/zeek-adapter/build-zeek/`.
- CLIs: converter `<bronce.csv> <avro.out> <parquet.out>` (verifica HMAC → necesita clave);
  loader `<oro.parquet> <kuzu_db> <schema.cypher>` (NO verifica HMAC → sin clave); kuzu_query
  `<kuzu_db> <cypher>`. adapters: `<config.json>` posicional (input_path DENTRO del config).
  Schema en correlation-engine/schema/schema.cypher.
- Consultas Cypher sin literales de string dentro de `vagrant ssh -c '...'`. Para filtrar por
  sensor, comparar propiedades (`ea.source_sensor < eb.source_sensor`) en vez de `WHERE ... = 'zeek'`.
  `collect(DISTINCT ...)` + `size()` SÍ corren en Kuzu 0.11.3 (medido DAY 237). MERGE de rel +
  ON CREATE SET también (DAY 232).
- Loader ~108-117 filas/s (flush por lotes de 512 filas / 1e9 ns).
- pipeline-start levanta 8 servicios (etcd, rag-security, rag-ingester, ml-detector, sniffer eBPF,
  firewall, vault dev, jenkins). mitre-start EXIGE pipeline-start arriba (clave HMAC del etcd :2379).

## Recordatorio de tono
Alonso pilota; mide contra fichero y pega salida. `make pipeline-stop` al cerrar. Rama de trabajo
`feat/zeek-to-graph`, sin merge a main hasta EMECAS+++ verde con los 4 sensores. zeek-adapter.md al
tope (~32KB): el tramo aguas abajo y el de mitre-start ya viven en [[mitre-start-zeek]] y
[[parquet-a-kuzu]]; no volver a engordar zeek-adapter.md.