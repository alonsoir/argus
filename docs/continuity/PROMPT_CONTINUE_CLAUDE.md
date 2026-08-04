# PROMPT DE CONTINUIDAD — aRGus NDR — DAY 250

## Punto de entrada (mide, no asumas)
    git log --oneline -6
    git status
    git branch --show-current
    vagrant status
Tras DAY 249: rama `feat/dataset-export` con `scripts/ctu_start.sh` + `scripts/fetch_neris.sh`
+ targets `ctu-start`/`fetch-neris` (commit `feat(ctu-start)...`). Si algo quedó sin commitear,
  ciérralo primero. VMs probablemente aborted.

## Estado que ordena el día — 2º driver HECHO y validado; empieza el join bias-vs-ground-truth
- ✅ Instrumento de datasets A/B/C en main (DAY 248, loader fiel 4195/4195 modo C).
- ✅ 2º TRAFFIC DRIVER `ctu-start` (DAY 249): hermano de `mitre_start.sh`, replay del Neris
  (CTU-13 sc.1, `botnet-capture-20110810-neris.pcap`) con `tcpreplay -i eth1 --mbps=10`. El SEAM
  driver↔harness es UNA línea (la de tráfico); el downstream bronce→oro→grafo→veredicto→
  `dataset_export` es IDÉNTICO y agnóstico del driver. `KUZU` y rutas de oro se dejaron iguales
  a mitre a propósito → `dataset_export` consume la corrida CTU sin tocar el tool.
- ✅ 🟢🟢🟢 1ª corrida medida (STAMP `20260804-080140`): las TRES lentes convergen sobre el Neris.
  awk sobre el CSV: **argus-neris=1249 (91%), zeek-neris=16466, suricata-neris=243**; lab de fondo
  argus=120/zeek=18/suricata=0; invariante=0; **217 community_id cross-sensor** (co-visibilidad).
  2º dataset generado por el mismo instrumento: `dataset-modeA-20260804-080140.csv` (18096 filas).
- ✅ La TESIS DEL INSTRUMENTO pasa de 1 capa a **DOS drivers demostrados** (nmap sintético + CTU
  Neris etiquetado) — exactamente lo que el paper vende.
- 🟢 REFUTADA (medido) una alarma del propio Claude: "aRGus no capturó el replay / sniffer
  subred-scoped / hace falta tcprewrite" era FALSA — voté desde 9 filas ordenadas sesgadas al
  fondo de lab. aRGus captura IPs foráneas en promisc sin remapear. El registro dice "refutada".

## Batalla candidata DAY 250 — join bias-vs-ground-truth (mide primero)
1. OBJETIVO (encuadre DAY 247, en pie): caracterizar el SESGO de cada lente contra el ground-truth
   ETIQUETADO del CTU — TP/FP/FN por lente frente a la verdad. NO "reproducimos el CTU".
2. MEDIR primero: ¿dónde están las labels del CTU en disco y en qué formato? El dir del dataset
   (`/vagrant/datasets/ctu13/` + el MCFP `CTU-Malware-Capture-Botnet-42`) trae
   `detailed-bidirectional-flow-labels/` (.binetflow) y `capture20110810.binetflow.2format`. Ancla
   del ground-truth = host infectado **147.32.84.165** (646 flujos maliciosos de los 19135, ya en el paper).
3. El join es por 5-TUPLA (+ ventana temporal), a nivel de ORO, NO de grafo — el modo C no valida
   la 5-tupla a propósito; la 5-tupla vive en el oro (cols 7-11) y en el CSV modo A (src/dst/ports/proto).
4. Salida: por lente (argus/suricata/zeek), qué fracción de los 646 maliciosos ve, qué marca de más
   (FP), qué se le escapa (FN). Ése es el número honesto del sesgo por-lente para el paper.
   CAVEAT: filtrar el fondo de lab (a 147.32) antes del join, o el join lo auto-limpia (filas sin label caen).

## Deudas nuevas DAY 249 (en BACKLOG, correlacionadas con tareas — BACKLOG↔PROMPT trazables)
`DEBT-DATASET-DRIVER-CONTRACT-001` (ACTUALIZADA: seam = 1 línea, contrato escribible, 2 drivers demostrados;
falta enforcement para el 3º) · `DEBT-CTU-REPLAY-GSO-DROP-001` (2630/323154=0.81% frames GSO no replayables,
deterministas; declarar; NO --mtu-trunc que corrompe; opción: pre-filtrar `tcpdump ... 'less 1515'`) ·
`DEBT-DATASET-LAB-BACKGROUND-IN-WINDOW-001` (la ventana mtime>T0 recoge fondo de lab; filtrar a 147.32 o
auto-limpia el join) · `DEBT-DATASET-XSENSOR-TELEMETRY-ONLY-001` (el titular cross-sensor cuenta solo
TelemetryEvent → Alert de argus fuera; el 217 es co-visibilidad, no detección corroborada).

## Diferidas (apuntadas, NO bloqueantes)
`DEBT-PIPELINE-STATUS-ALL-VMS-001` (status muestre TODAS las VMs, quitar rag-security/rag-ingester) ·
`DEBT-PIPELINE-START-DISABLE-RAG-001` (desactivar rag-security/rag-ingester del arranque; NO deprecar) ·
`DEBT-PIPELINE-START-BINARY-GUARD-001` (pipeline-start compruebe/compile binarios; onboarding) ·
DEBT-HMAC-KEY-INSECURE-TRANSPORT-001 · Vault productivo · rotación · DEBT-EVENT-ID-COLLISION-001 (argus
1369→424 en grafo, colapso 69% en Neris) · DEBT-DATASETS-FETCH-NOT-AUTOMATED-001 (fetch-neris HECHO,
falta pinear sha256).

## Para el PAPER (redacción ESTA SEMANA con los datos actuales + los 2 datasets)
- La contribución = el INSTRUMENTO, no el dataset. Dos capas: traffic driver [VARIABLE] | downstream
  [INVARIANTE]. DOS drivers demostrados; contrato del 3º especificado (DEBT-DATASET-DRIVER-CONTRACT-001).
- Números honestos ya medidos: loader fiel 4195/4195; 3 lentes convergen sobre el Neris (argus 1249,
  zeek 16466, suricata 243); 217 co-visibilidad cross-sensor; overall=0.75 literal; 43% divergencia de
  detectores; reloj 0 en fast-alert; 2630 GSO drops (0.81%); Alert SOLO de argus.
- LAS 3 LENTES son heterogéneas por diseño (ML / firmas / telemetría), COMPLEMENTARIAS, no a igualdad
  de condiciones — el valor es caracterizar el sesgo de cada una, no normalizarlas. Future-work: mejorar
  lentes con el harness invariante y re-medir.
- Alcance declarado: C valida el VEREDICTO no la 5-tupla; una corrida por driver; nmap -A / CTU Neris.

## Invariantes (no negociar)
- Medir, no votar. HECHO ≠ SOSPECHADO; cada afirmación a salida de comando/fichero. (DAY 249: sobre-canté
  el 217 como victoria y luego sobre-canté una alarma de captura — la medición corrigió las dos. No votar.)
- Un día, una batalla. Vía Appia (bronce/oro = fuente de verdad; grafo = proyección certificada modo C).
- Reproducibilidad = propiedad del repo: todo dato del paper, generable por un comando del Makefile.
- Grafo RED = fresco por medición. sed -i de macOS/BSD exige sufijo: `sed -i ''`.
- Alonso no tiene str_replace: entregar script completo o parcheador idempotente (ancla por texto).
- No `grep -rn` desde la raíz (arrastra build/.git/.venv, tarda horas): `git grep` o fichero concreto.

## Recordatorio de tono
Alonso pilota; mide contra fichero y pega salida. Hilos de memoria: [[ctu-start]] (2º driver + la corrida
+ awk que refutó la alarma), [[dashboard-export]] (instrumento A/B/C + los 4 hallazgos + loader fiel),
  [[cierre-paper]] (tesis honesta + framing del instrumento + las 3 lentes), [[mitre-start-repro]] (el driver
  mitre = molde de ctu-start).