# PROMPT DE CONTINUIDAD — aRGus NDR — DAY 252

## Punto de entrada (mide, no asumas)
    git log --oneline -6
    git status
    git branch --show-current
    vagrant status
Tras DAY 251: rama `feat/ctu-start`. Debe existir un commit `feat(bias-denominator)`
con `scripts/bias_denominator_true.py` + `scripts/autopsy_67.py`. Si el `git status`
del cierre de ayer mostraba los 2 scripts a la vez staged (versión vieja) Y modified
(versión nueva) → se hizo `git add scripts/bias_denominator_true.py scripts/autopsy_67.py`
antes del commit (misma trampa DAY 250). `scripts/__pycache__/` a `.gitignore` o sin añadir.
VMs probablemente aborted (los scripts de ayer corren solo en host).

## Estado que ordena el día — OBJETIVO (a) CERRADO, empieza la redacción
DAY 251 cerró el **denominador verdadero** y su hueco, todo medido, sin conjeturas
(medir corrigió mis 3 hipótesis seguidas: GSO, S0, flush — las tres falsas).

- ✅ 🎯 DENOMINADOR VERDADERO (tshark sobre el pcap offline, `bias_denominator_true.py`):
    - P (5-tuplas distintas en el pcap) = 14520 · B_full (botnet en el binetflow entero) = 14257.
    - **denominador verdadero = P ∩ B_full = 14255** (COTA SUPERIOR del pcap offline).
    - **lens-observable (== gt_botnet del join) = 14188** (denominador OPERATIVO).
    - salud de la clave L−P = 0 (canon fiel, reuso de `join_bias_labels.py` validado).
- ✅ 🎯 PUNTO CIEGO COMPARTIDO = 14255 − 14188 = **67 flujos = 0.47%**. Caracterizado:
    - NO GSO (split frame.len: 0 GSO-only) · NO intentos S0 (67/67 con respuesta, 6–46662 pkts).
    - `autopsy_67.py` lo localiza por medición: NO en oro zeek, **NO en el conn.log crudo de
      zeek (0/67)** → mueren ANTES del pipeline, en captura/cable. `dataset_export.py` medido:
      el modo A no deduplica ni filtra → export exonerado.
    - ETAPA 3 (posición temporal): repartido por casi todo el pcap, sesgo ×4 al arranque
      (17/67 en el 1er 5% vs 6.3% de los vistos). NO borde limpio.
    - ETAPA 4 (argus eth2, otra pila): **0/67**. Dos pilas, dos interfaces, mismo veredicto.
    - **VEREDICTO: el 0.47% es PÉRDIDA DE FIDELIDAD DE REPLAY en el cable** (consistente con
      los 2630 GSO EMSGSIZE, 0.81%). NO detección, NO pipeline, NO drop de una pila.
- ✅ Contraste conn_state de los 14178 vistos: S0=9831, SF=3650, RSTO=490, REJ=212, RSTR=35
  → zeek→oro NO filtra por estado (emitió 9831 S0 sin problema).

## Frase honesta para el paper (redáctala tal cual, sin interpretar de más)
> El denominador "verdadero" (14255) se calcula sobre el pcap OFFLINE. El observable por el
> banco (14188) difiere en 67 flujos (0.47%). Esos 67 no aparecen en el conn.log crudo de
> zeek ni en el bronce de argus (dos pilas de captura independientes, dos interfaces), luego
> no llegaron al cable replayado — límite de fidelidad de replay, consistente con los 2630
> frames GSO no replayables medidos. El denominador operativo es 14188; el "verdadero" es
> cota superior. No se atribuye la pérdida más allá de lo que miden tshark y el pipeline.

## LÍMITE DE PROCEDENCIA (regla dura de Alonso, DAY 251 — rige toda la redacción)
El CTU-13 Neris es un pcap de 2011, NO capturado por nosotros, condiciones de captura
desconocidas salvo origen universitario. Declararlo como límite. Solo lo que dicen tshark +
pipeline; cualquier conjetura, etiquetada como tal o no se dice.

## Batallas DAY 252 (el trabajo que queda; una por día, mide primero)
1. **PAPER** — redactar con lo medido: (a) la sección del sesgo por-lente (tabla 3 lentes +
   los 5 caveats de [[join-bias-ground-truth]]); (b) el denominador verdadero + los 67 como
   límite de fidelidad de replay; (c) el hilo S&P (ML ciego 0.07, la firma/heurístico lleva la
   detección). Medir primero: releer el estado ACTUAL del paper (qué secciones existen).
2. **MAKEFILE para revisores** — cada número del paper detrás de un comando. `bias-report` ya.
   Añadir targets: `bias-denominator-true` (`python3 scripts/bias_denominator_true.py $(STAMP)`,
   requiere el raw de tshark → target `neris-pcap-5tuples` que lo genera) y `autopsy-67`. A `.PHONY`.
3. **OVERHAUL pipeline-start/status** (cierra DEBT-PIPELINE-START-DISABLE-RAG-001,
   -BINARY-GUARD-001, -STATUS-ALL-VMS-001, -STATUS-LOGFILES-001): pipeline-start levanta TODOS
   los componentes/VMs MENOS rag-security y rag-ingester (no se borran, no arrancan, no se
   muestran); compila lo que falte con el MISMO profile que los demás; pipeline-status muestra
   todos los que corren, incluye el driver usado (ctu-start/mitre-start) si se ejecutó, y por
   componente su ruta de log + el `vagrant ssh <vm>` para verlo.
4. **README final** + repo read-only.

## Artefactos de la corrida de referencia (STAMP 20260804-080140, en el HOST, logs/lab/)
argus-*.bronce.csv (crudo, SIN cabecera, posicional: 7 src_ip,8 dst_ip,9 src_port,10 dst_port,
11 protocol) · zeek-*.conn.log (crudo) · eve-*.json (suricata crudo) · {argus,suricata,zeek}-*.parquet
(oro) · logs/datasets/dataset-modeA-20260804-080140.csv (el join lo consume) ·
logs/datasets/neris-pcap-5tuples-raw.csv (tshark 8 campos, lo consume bias_denominator_true).

## Deudas nuevas / actualizadas DAY 251 (al BACKLOG, correlacionadas con tareas)
`DEBT-REPLAY-OFFLINE-VS-WIRE-FIDELITY-001` (el denominador true del pcap offline sobre-cuenta
vs el cable; 0.47% no llega, medido en 2 pilas; cota superior, declarar) ·
`DEBT-BIAS-DENOMINATOR-LENS-OBSERVABLE-001` ACTUALIZADA → medida y cerrada como cota superior
(no era ceguera del banco). Diferidas sin cambios: DEBT-EVENT-ID-COLLISION-001,
DEBT-CTU-REPLAY-GSO-DROP-001, DEBT-DATASET-DRIVER-CONTRACT-001, DEBT-HMAC-KEY-INSECURE-TRANSPORT-001.

## Invariantes (no negociar)
- Medir, no votar. HECHO ≠ SOSPECHADO. Conjetura etiquetada como tal o no se dice.
  (DAY 251: 3 hipótesis mías falsas seguidas; el dato mandó cada vez. Los scripts se
  construyeron para TUMBAR mi propia corazonada con un número, no para confirmarla.)
- Fidelidad de reuso: los scripts nuevos IMPORTAN `canon()`/loaders de `join_bias_labels.py`
  y `dataset_export.py`, no reimplementan (bug silencioso proto-case/orientación = la clase que
  cazamos). Verificar en fixture antes de correr sobre datos reales.
- Reproducibilidad = propiedad del repo: todo dato del paper, generable por un comando del Makefile.
- Alonso pilota; mide contra fichero y pega salida. Alonso no tiene str_replace: script completo.
- No `grep -rn` desde la raíz (arrastra build/.git/.venv, tarda horas): `git grep` o fichero concreto.
- sed de macOS/BSD exige sufijo: `sed -i ''`.

## Hilos de memoria
[[join-bias-ground-truth]] (la batalla del denominador verdadero: los 67, la autopsia, el
veredicto de fidelidad de replay) · [[cierre-paper]] (tesis honesta, las 3 lentes, agenda de
cierre) · [[ctu-start]] (2º driver + la corrida) · [[dashboard-export]] (instrumento A/B/C).