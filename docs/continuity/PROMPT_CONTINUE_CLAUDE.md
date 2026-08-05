# PROMPT DE CONTINUIDAD — aRGus NDR — DAY 251

## Punto de entrada (mide, no asumas)
    git log --oneline -6
    git status
    git branch --show-current
    vagrant status
Tras DAY 250: rama `feat/ctu-start` con el commit `feat(bias-report)...`
(scripts/join_bias_labels.py + scripts/fetch_neris_labels.sh + targets Makefile
`bias-report`/`fetch-neris-labels` + `.PHONY`). Si algo quedó sin commitear o el
guard de fetch_neris_labels.sh no arranca (`make fetch-neris-labels` → `OK ...
verificado`), ciérralo primero. VMs probablemente aborted (bias-report NO las
necesita: corre solo en host).

## Estado que ordena el día — sesgo por-lente MEDIDO, AUTOMATIZADO y bancado
- ✅ Instrumento de datasets A/B/C en main (DAY 248) + 2º driver `ctu-start` (DAY 249).
- ✅ 🟢🟢🟢 BATALLA DAY 250 CERRADA: **join bias-vs-ground-truth**. El dataset modo A
  (STAMP 20260804-080140) cruzado por 5-TUPLA CANONICALIZADA (sin ventana: el replay
  --mbps=10 reescribió el reloj) contra el binetflow del CTU-13
  (`datasets/ctu13/capture20110810.binetflow`, 2.8 M flujos, labels Botnet/Normal/
  Background). Join FIEL: 99.3% de nuestras 14466 5-tuplas casan; clave limpia salvo
  2 ambiguas (0.014%). Fondo de lab auto-limpia como sin-label (predicción confirmada).
- ✅ 🎯 EL NÚMERO DEL PAPER (divergencia por-lente, sin fundir lentes — decisión Alonso):
    - **zeek** = observador 1:1, visibilidad **99.9%** (14178/14188) del botnet, cero veredicto.
    - **suricata** = 1:1, visibilidad **1.5%**, y sus 237 solapes son TODOS "Generic Protocol
      Command Decode" = **anomalía de protocolo, NO firma de botnet** (ET Open F1=0 preciso).
      precision 0.975 / recall 0.015.
    - **argus** = lente **gruesa y event-heavy** (74 flujos distintos, ×18.5 eventos/flujo),
      capta el **C&C persistente** no el fan-out efímero; matriz por-fila TP=894 FP=0 FN=248
      → recall 0.783, y esa detección es **100% fast-path con el ML CIEGO** (945 MALICIOUS,
      todos overall=0.75 literal / ml≈0.07 / DETECTOR_SOURCE_DIVERGENCE).
- ✅ AUTOMATIZADO como comando (reproducibilidad = propiedad del repo): `make bias-report`
  (mismo STAMP que dataset-export, escribe `logs/datasets/bias-report-$STAMP.txt`) +
  `make fetch-neris-labels` (baja el binetflow del MCFP, cierra la trampa del destroy&up).

## CAVEATS que van al paper con los números (NO sobre-cantar — la medición ya corrigió 2 veces)
1. `precision=1.000` de argus es TRIVIAL: 0 flujos clean-etiquetados en su vista → nada
   sobre lo que dar FP. NO es "nunca falsa-alarma".
2. `recall 0.783` es del HEURÍSTICO, no del ML (ML ciego, 0.07). Es la tesis Sommer & Paxson
   en el ground-truth (el ML no transfiere, la firma lleva lo poco que se detecta). NO
   redactar "argus detecta el 78%" sin ese split.
3. El "0.2% de visibilidad" de argus es GRANULARIDAD, no ceguera (argus cuantiza en 74 flujos
   gruesos vs los ~14000 micro-flujos de zeek). Redactar como sesgo de granularidad por-lente.
4. El fast-path disparó MALICIOUS también sobre ~51 flujos de fondo de lab (sin-label) → esos
   FP reales NO se miden contra las labels del CTU (el lab no está etiquetado). Declararlo.
5. Denominador LENS-OBSERVABLE (flujos botnet vistos por ≥1 lente): un flujo botnet que
   ninguna lente capturó no cuenta. El denominador VERDADERO exige tshark sobre el pcap.

## Batalla candidata DAY 251 — redactar el sesgo por-lente en el paper (encuadre DAY 249)
Roadmap Alonso: "esta semana se escribe la renovación del paper con los datos actuales +
los 2 datasets". Con el número del sesgo por-lente ya medido y reproducible, la batalla
natural = **escribir la sección de caracterización del sesgo por-lente** con: la tabla de
las 3 lentes (visibilidad / detección heterogénea), los 5 caveats de arriba TAL CUAL, y el
hilo argumental "el ML está ciego sobre Neris, la firma/heurístico lleva la detección" =
S&P confirmado empíricamente con trazas reproducibles. Medir primero: releer el estado del
paper actual antes de redactar (qué secciones existen, dónde encaja esto). Alternativas que
Alonso puede priorizar en su lugar: (a) refinamiento del denominador verdadero (tshark sobre
el pcap → flujos botnet que NINGUNA lente vio, cierra el caveat 5); (b) decisión de merge
`feat/ctu-start` → main (el trabajo del instrumento+drivers+bias está listo); (c) README final.

## Deudas nuevas DAY 250 (en BACKLOG, correlacionadas con tareas — BACKLOG↔PROMPT trazables)
`DEBT-BIAS-DENOMINATOR-LENS-OBSERVABLE-001` (denominador del bias-report es lens-observable;
verdadero = tshark 5-tuplas del pcap; correlaciona con una tarea `bias-denominator-true`
futura) · `DEBT-BIAS-KEY-5TUPLE-AMBIGUITY-001` (2 5-tuplas botnet∧clean, 0.014%, del propio
etiquetado del CTU; declarar en data card, no bug) · `DEBT-BIAS-FASTPATH-LAB-FP-UNMEASURED-001`
(el fast-path disparó sobre ~51 flujos de lab sin-label; FP real no medible desde labels CTU) ·
`DEBT-DATASETS-FETCH-NOT-AUTOMATED-001` (ACTUALIZADA: mitad de labels CERRADA con
fetch-neris-labels + sha pineado; pcap ya pineado DAY 249 → ambos ficheros CTU reproducibles).

## Diferidas (apuntadas, NO bloqueantes)
`DEBT-PIPELINE-STATUS-ALL-VMS-001` · `DEBT-PIPELINE-START-DISABLE-RAG-001` ·
`DEBT-PIPELINE-START-BINARY-GUARD-001` · `DEBT-DATASET-XSENSOR-TELEMETRY-ONLY-001` (el 217
cross-sensor es co-visibilidad, no detección corroborada) · `DEBT-EVENT-ID-COLLISION-001`
(argus 1369→424 en grafo, colapso 69% en Neris; = la ×18.5 event-multiplicity del bias) ·
`DEBT-CTU-REPLAY-GSO-DROP-001` (2630/323154=0.81% frames GSO no replayables, deterministas) ·
`DEBT-DATASET-DRIVER-CONTRACT-001` (seam=1 línea, 2 drivers demostrados, falta enforcement 3º) ·
DEBT-HMAC-KEY-INSECURE-TRANSPORT-001 · Vault productivo · rotación.

## Para el PAPER (redacción ESTA SEMANA)
- La contribución = el INSTRUMENTO (traffic driver [VARIABLE] | downstream [INVARIANTE]),
  2 drivers demostrados. El sesgo por-lente es ahora un NÚMERO REPRODUCIBLE por `make bias-report`.
- Las 3 lentes son heterogéneas por diseño y COMPLEMENTARIAS; el valor es caracterizar el sesgo
  de cada una, NO normalizarlas. Divergencia total: nadie ve lo mismo, y ahí está la historia.
- El hallazgo fuerte: sobre el Neris el ML de argus está ciego (0.07) y la detección la lleva el
  fast-path/heurístico → confirma empíricamente Sommer & Paxson con trazas reproducibles.
- Alcance declarado: C valida el VEREDICTO no la 5-tupla; join por 5-tupla sin ventana (reloj
  reescrito por --mbps=10); denominador lens-observable; una corrida por driver.

## Invariantes (no negociar)
- Medir, no votar. HECHO ≠ SOSPECHADO; cada afirmación a salida de comando/fichero. (DAY 250:
  el "0.2% de argus" parecía ceguera y era granularidad; los awks lo corrigieron. Y el guard de
  fetch_neris_labels.sh: cazado por LEER el fichero pegado, no por asumir.)
- Un día, una batalla. Vía Appia (bronce/oro = fuente de verdad; grafo = proyección modo C).
- Reproducibilidad = propiedad del repo: todo dato del paper, generable por un comando del Makefile.
- Grafo RED = fresco por medición. sed de macOS/BSD exige sufijo: `sed -i ''`.
- Alonso no tiene str_replace: entregar script completo o parcheador idempotente (ancla por texto).
  Al pinear un sha, tocar SOLO la línea `SHA256=`, NUNCA el guard (comparación con el centinela).
- No `grep -rn` desde la raíz (arrastra build/.git/.venv, tarda horas): `git grep` o fichero concreto.

## Recordatorio de tono
Alonso pilota; mide contra fichero y pega salida. Hilos de memoria: [[join-bias-ground-truth]]
(la batalla del día: join, los números por-lente, los 5 caveats, la automatización),
[[ctu-start]] (2º driver + la corrida), [[cierre-paper]] (tesis honesta + las 3 lentes),
[[dashboard-export]] (instrumento A/B/C + loader fiel).