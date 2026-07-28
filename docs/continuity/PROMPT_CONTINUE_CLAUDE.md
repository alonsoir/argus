# PROMPT DE CONTINUIDAD — aRGus NDR — DAY 236

## Punto de entrada (mide, no asumas)
    git log --oneline -6
    git status
    vagrant status
DAY 235 cerró **Zeek en el bronce**: adapter escrito, `make zeek-adapter-test` verde, y
corrida real → 31.735 filas en /vagrant/logs/correlation/zeek-*.csv, TODAS pasando
validate(). OJO: al cerrar, el adapter quedó SIN commitear (rama feat/zeek-to-graph:
Makefile modificado + zeek-adapter/ untracked). Lo primero al arrancar: confirmar si el
commit + push del cierre se hizo. Si no, hacerlo antes de tocar nada.

## El estado que ordena el día
**Paso 5 (Zeek→bronce) GANADO y medido.** El contrato correlation_v1 acepta telemetría
con veredicto vacío — err_serialize=0 sobre 31.735 filas de Zeek (final_classification /
threat_category "" y scores 0.0). Son las PRIMERAS filas no-alerta que pasan por
validate() en la historia del contrato: el bronce es multi-sensor de verdad, no solo
alerta-shaped. Eso es una propiedad del contrato ahora probada, no supuesta.
**Siguiente: Zeek al GRAFO.** Como Suricata fue bronce (DAY 226) → oro (227) → Kuzu (228),
a Zeek le queda ese tramo aguas abajo.

## Candidato de batalla DAY 236 (Alonso decide el corte)
Objetivo declarado: **incluir Zeek en el test MITRE del Makefile (mitre-start) para que el
grafo tenga TRES telemetrías (aRGus + Suricata + Zeek).**
1. **LO PRIMERO — corregir config/zeek_adapter.json.** input_path apunta a
   logs/day225-zeek-neris/eve.json (resto Suricata, path inexistente). A la fuente Zeek.
   Revisar node_id (hoy cpp_sniffer_v33_day12, el de aRGus) — ver "A medir".
2. **Commitear el adapter** si el cierre no lo hizo (git add explícito, ver notas).
3. Tramo aguas abajo de Zeek, espejando Suricata: bronce Zeek → oro (Parquet) → Kuzu.
   OJO PUERTA MULTI-SENSOR: parquet_to_kuzu_loader declaraba alcance mono-fuente
   (source_sensor="argus") con aviso de no generalizar sin Consejo. ¿Se generalizó para
   Suricata en DAY 228? MEDIR contra fichero antes de meter Zeek por ahí.
4. Wiring en mitre-start para que la corrida del MITRE arrastre también a Zeek al grafo.
   Corte: "un día, una batalla". Llevar Zeek de bronce al grafo por mitre-start son varios
   sub-pasos y puede no caber en un día. Alonso corta midiendo, no forzando.

## Después de DAY 236
Wazuh (día siguiente o el mismo): cuarto sensor, mismo estándar de adapter. El
ADAPTER_TOOLCHAIN ya está en el Vagrantfile para wazuh y el scaffold ya funciona
(arreglado DAY 235). Con Wazuh, las cuatro señales al grafo → cierre del pipeline.

## Invariantes (no negociar)
- Medir, no votar. HECHO ≠ SOSPECHADO; cada afirmación a salida de comando.
- flow_uid = hash(node_id ‖ community_id), SIN tiempo (Opción B, DAY 225).
  node_id = punto de observación, NO el host. Join SIEMPRE por community_id.
- Un día, una batalla. Vía Appia (un criterio que no puede ponerse rojo no mide).
- No `grep -rn` desde raíz (usa `git grep`). No encadenar salidas grandes.
  `git add` explícito (nunca -a/-u: instrumentación WIP en zmq_handler.cpp).
  macOS: nunca `sed -i` sin `-e ''`. Build/commit/push desde el host. A horas malas, parar.
- SIN switches en JSON (DAY 222): grafo data-driven. Cada componente su propio config con
  su source_sensor; mismo buzón de bronce plano /vagrant/logs/correlation.

## Estado del adapter de Zeek (DAY 235, HECHO)
- zeek-adapter/ generado y escrito: to_row.hpp/.cpp (parseo POR NOMBRE del `#fields`,
  parse_zeek_ts epoch double, event_id = community_id‖ts con prefijo `zeek:`), main.cpp
  (captura la línea `#fields` + loop, salta el preámbulo `#`), test_to_row.cpp (vector
  diana real con \t explícitos). Targets en el Makefile (zeek-adapter-build/test/clean,
  construyen en la VM zeek).
- community_id = campo de DATOS 23 (token 24 del header por el prefijo literal `#fields`).
- Zeek = TELEMETRÍA: cols de veredicto vacías. "Todo el jugo" (dns/http/ssl/...) ya en
  /vagrant/logs/day235-zeek-neris/, pendiente para la batalla N-ficheros (hoy solo conn.log).

## A medir (afecta al día, no se asume)
- ¿node_id de Zeek? DAY 235 corrió con cpp_sniffer_v33_day12 (el de aRGus). Si Zeek
  comparte punto de observación con aRGus, converge en el MISMO nodo; si lleva el suyo, el
  join es cross-sensor por community_id. DECISIÓN DE DISEÑO del grafo; medir el efecto antes
  de fijarlo en el bronce definitivo. Regenerar el bronce si cambia = una corrida, sin lock-in.
- ¿parquet_to_kuzu_loader ya generaliza multi-sensor (tras Suricata DAY 228) o sigue
  mono-fuente? Medir contra fichero antes de meter Zeek por ahí.
- Convergencia cross-sensor SISTEMÁTICA: en DAY 235 se vio UN flujo con community_id y
  flow_start idénticos en Zeek y en el vector de Suricata
  (1:MuSlbWV2Dy5Z168c5sxOWncbYyQ=, 147.32.84.165:1040→94.63.149.152:80). La intersección
  completa Zeek∩Suricata (grep -Fxf con LC_ALL=C sobre los community_id de los dos bronces)
  es la prueba de convergencia — hacerla el día del grafo.

## Deudas registradas DAY 235 (en docs/BACKLOG.md, sección DAY 235)
- DEBT-DOWNSTREAM-INGESTION-NOT-ORCHESTRATED-001 (P2): el camino aguas abajo se invoca a
  mano, binario a binario; falta un componente orquestador full-time que gestione la ingesta
  hasta el grafo (responsable de mantener el grafo actualizado y alimentar el dashboard).
- DEBT-ZEEK-ADAPTER-CONFIG-SURICATA-RESIDUE-001 (P3): config con input_path de Suricata.
- DEBT-ZEEK-PROTO-CASE-001 (P3, decisión abierta): Zeek proto minúsculas vs Suricata mayúsculas.
- DEBT-SCAFFOLD-GUIDANCE-SURICATA-CENTRIC-001 (P4): la guía embebida del scaffold asume JSON.

## Notas de fontanería DAY 235 (medidas, no re-medir)
- Scaffold arreglado: tools/scaffold_adapter.py estaba DUPLICADO entero (doble concatenación,
  el segundo `from __future__` en la línea 1250 daba SyntaxError). Fix commiteado en 19cd389d
  (head -1222 + un entry-point). Desbloquea también wazuh/argus.
- Build de adapters de sensor = TARGET del Makefile (NO hay CMakeLists raíz), corre en la VM
  del sensor (`vagrant ssh zeek -c`), build-dir con sufijo (/vagrant es compartido).
- Corrida del adapter (paso 5):
  vagrant ssh zeek -c 'export ARGUS_BRONZE_HMAC_KEY_HEX=<64hex> && \
  cd /vagrant/zeek-adapter && \
  ./build-zeek/zeek_adapter config/zeek_adapter.json /vagrant/logs/day235-zeek-neris/conn.log'
  La clave real de aRGus solo hace falta cuando un LECTOR verifique el HMAC; para escribir el
  bronce vale cualquier clave de 64 hex. El binario acepta la entrada como arg2, sobrescribe input_path.
- Replay de Zeek: `zeek -C -r <pcap> local` (el -C ignora los ~68/1000 checksums inválidos
  del Neris). Diana seed 0: 1:IN7uqVpMWxpmuhQTowSQB2XEe0E=.
- El uid de Zeek NO es estable entre replays (por eso el event_id sale de community_id‖ts, no del uid).
- Con -Werror, un `[[nodiscard]]` cuyo retorno se ignora ROMPE el build (lección del adapter).

## Recordatorio de tono
Alonso pilota; mide contra fichero y pega salida. `make pipeline-stop` al cerrar.