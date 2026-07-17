# PROMPT DE CONTINUIDAD — DAY 221 (17-jul-2026)

Rama: `fix/verdict-multihead-honest`. HEAD al cierre: `b4271076` ("added
honests results" — Makefile fix + findings + prompt + report neris).
FEDER: go/no-go ~1 agosto. Calidad no negociable sobre deadline.
La sesion de madrugada (02:23-05:00) resolvio la paradoja Neris COMPLETA.
Este prompt la contiene entera; no re-derivar.

## RESULTADO DE LA VIA A (replay Neris, run completo, limpio)

323.152/323.154 pkts (Failed: 2), 17.298s timing original. Bronce: 765
segmentos, 519.397 eventos, 286.420 CTU.
Report commiteado: `tools/eval/out/eval_level1_neris_report.json`.

| metrica | valor |
|---|---|
| GT (cids botnet unicos) | 8.935 |
| coverage | 0.886 (7.916 cubiertos; 1.019 rio-arriba) |
| **recall L1 (col15 >= 0.65)** | **0.0** (detected: 0) |
| max(ml_score) del run | 0.626477 |
| ml_scores unicos | 11.261; top-12 formas ~76% |
| ml >= 0.6 / 0.5 / 0.4 | 47 / 756 / 62.763 (de 519.397) |
| fast en eventos CTU | 0.0 en 286.318 (99,96%); 0.75 en 102 |
| fast en eventos NO-CTU | 0.75 en 224.357 (96%); 0.0 en 8.624 |
| a nivel SISTEMA (final=max>=0.7) | ~224K MALICIOUS sobre chatter benigno; ~102 aciertos accidentales sobre CTU |

## LA PARADOJA NERIS — RESUELTA (la sintesis mas importante)

**"¿Por que Neris daba recall 1.0 en primavera y 0.0 hoy?"** Respuesta,
probada con el events CSV del 2026-05-08 (31.503 eventos CTU de un replay
real de mayo):

1. **L1 NUNCA detecto Neris por el pipeline — ni en mayo ni hoy.** El
   ml_score de mayo al trafico CTU era **0.041933** — EXACTAMENTE el valor
   mas frecuente del run de anoche (95.001 eventos). L1 es coherentemente
   ciego al flujo parcial desde siempre.
2. **El recall de primavera lo fabricaba el FAST path**, que entonces
   disparaba 0.75 AL BOTNET (muestra de mayo: 147.32.84.165→C&C,
   RANSOMWARE_FAST_DETECTION, fast=0.75, DROP). Un detector "ransomware"
   sintetico acertando sobre botnet 2011 = **correcto por accidente**.
3. **El fast path SE INVIRTIO entre el 8-may y hoy**: anoche dio 0.0 al
   botnet y 0.75 al chatter benigno. Esa es la regresion real, con ventana
   acotada. **Sospechoso principal: `fc292bc8` (fix DAY 219,
   get_flow_stats_copy 26→28 campos)** — si los embebidos se asentaron
   sobre FlowStats amputadas, repararles la entrada les cambio la
   distribucion y los volteo. Alternativo: `de87a1b5` (hardening parsers).
   HIPOTESIS, no veredicto — test concreto abajo.

## LAS DEUDAS P0/P1 NUEVAS DE LA NOCHE

- **DEBT-L1-PARTIAL-FLOW-SCORING-001 (P0)**: pipeline puntua POR EVENTO con
  features de flujo PARCIAL; modelo entrenado con agregados COMPLETOS.
  Tenaza: via B (flujo completo → 0.9987) exonera modelo; coverage 0.886
  exonera captura; techo 0.626 + solo 756 eventos >=0.5 exonera threshold
  como fix (puerta CLAVADA con numero — no reabrir). Señal comprimida: 12%
  de eventos en banda 0.4-0.626 → reentrenar-con-parciales tiene esperanza.
- **DEBT-FAST-PATH-INVERTED-DISCRIMINATION-001 (P0/P1)**: numeros arriba;
  invertido en algun punto post-8-mayo.
- **DEBT-FIREWALL-AGENT-SILENT-SINCE-FEB-001 (P1)**: unico log del agente
  es del 7-feb (y ya mostraba DEGRADED, ipset_failures=200, ZMQ not
  connected). Proceso RUNNING anoche, cero rastro escrito. ipset actual: 0
  entradas (pero timeout 3600 — no prueba inactividad nocturna).
- **DEBT-TABLE11-INTEGRITY-001 (P1, paper)**: la Table 11 (recall 1.0,
  F1 0.9985, TP=646) esta contradicha por la medicion honesta. El 646 ya
  era irreconstruible (8 criterios). Sospecha adicional: el experimento
  corrio en las VMs propias `experiment-suricata-ids`/`experiment-zeek-*`
  (ADR-029), NO en este pipeline. Con go/no-go a 2 semanas, es cuestion de
  integridad: que midio, y como se reescribe.

## PLAN DE APERTURA DAY 221 (en orden)

1. **Verificar commits de madrugada**: `git log --oneline -5` + `git status`
   (b4271076 deberia contener Makefile+findings+prompt+report; el apendice
   §13-19 del findings — ¿entro entero, incluida la seccion de la paradoja?
   Si no, redactar §20 con la sintesis de arriba).
2. **El experimento que decide la arquitectura de L1** (barato, decisivo):
   Neris pcap → CICFlowMeter (o equiv.) → 23 features de flujo COMPLETO →
   ONNX offline. Recall alto → el fix es solo CUANDO puntuar (cierre/
   timeout). Recall ~0 → CUANDO + reentrenar. Decide entre las 3 opciones
   (puntuar-al-cierre / re-puntuar por ventanas / reentrenar con parciales)
   ANTES de la ronda del Consejo. Conecta con ADR-040 y con
   L1-TRAINER-MISSING-001 (reconstruir el entrenador mata 2 deudas).
3. **Test de la hipotesis fc292bc8** (fast path invertido): ¿que campos de
   FlowStatistics consume el detector ransomware embebido? ¿Alguna feature
   depende de los 2 campos resucitados por fc292bc8? Si si → mecanismo
   hallado. Complemento: git log sniffer/ + ml-detector/ entre 08-may y hoy.
4. **Forense del firewall**: ¿donde loguea hoy (si loguea)? ¿le llegaron los
   ~224K MALICIOUS de anoche? ¿hay gate rio-arriba?
5. **Arqueologia Table 11**: `sed -n '1,60p'
   experiments/suricata-comparative/parse_results.py` (que fichero parsea,
   que cuenta como TP) + ¿corrio en las VMs experiment-*?

## FE DE ERRATAS DE LA MADRUGADA (patron → 27 casos)

- Caso 27 (Claude): `grep -rl` sin `-c` como evidencia de "replays
  historicos en abril-junio". Realidad: 2026-04-16 → 1 linea (y es un
  evento sintetico ransomware con IPs vacias, ni siquiera trafico);
  2026-06-06 → 1 linea; **solo 2026-05-08 fue replay real (31.503)**.
  Corregir §15.4 del apendice si dice "funciono siempre": lo probado es
  "dual funciona HOY (smoke 1.355 lineas post-marca) + hubo UN replay real
  el 8-may". `grep -l` es un head disfrazado.
- Casos 25-26 (Claude, ya en el apendice): head truncado; grep sin eje
  temporal.
- El events writer historico serializa IPs BIEN → BYTEORDER-001 se acota
  al correlation writer.

## TRAMPAS NUEVAS (reglas desde hoy)

- awk en la VM con locale es_ES compara "0,5" como TEXTO → aritmetica en VM
  SIEMPRE `LC_ALL=C` y `$1+0`.
- Comentario inline en asignacion de Make inyecta espacios finales en el
  valor (rompio el glob del report; ya arreglado en b4271076).
- `nohup &` bajo `vagrant ssh -c` muere → `sudo sh -c 'setsid nohup CMD >
  log 2>&1 < /dev/null &'`.
- Frames CTU >1500: MTU 9000 ambos extremos (NO persiste reboots); NUNCA
  --mtu-trunc.
- `grep -l`/`head -N` amputan; MARCA temporal + awk en logs acumulativos.

## ESTADO DEL ENTORNO

- Replay TERMINADO. VM client apagable (`vagrant halt client`).
- Bronce del run = DATO PRIMARIO del report — NO borrar (candidato a
  tar.gz y archivar). Todo lo previo en `archive-pre-neris/`.
- Config sniffer: `dual` (estado commiteado; el desvio por gateway-only fue
  error de Claude, revertido; gateway-only NO consume eth2 → deuda P3).
- Sin commitear a proposito: zmq_handler.{hpp,cpp} (instrumentacion DAY216),
  commit-message.txt, tools/temporal.md. STASH intacto (commit2-noisy-or).

## HITOS DE DAY 220 (no re-litigar)

- "Wednesday es holdout" REFUTADO (566149 = 0.2*2830743; notebook 02 seed
  42, split sobre los 8 dias juntos).
- Via B commiteada (73fac317): recall 0.9987 / FPR 0.00025, scope sanity
  in-sample. Fosil del 2,4% = autopsia del XGBoost, DEMOSTRADO.
- Procedencia: seleccion de features probada (02 + f53c676a, orden top-5 =
  orden del oraculo); entrenador/conversor NUNCA versionados (03/06 =
  esqueletos 216 bytes; sesion Jupyter 15-oct-2025 09:50→10:06) →
  L1-TRAINER-MISSING-001 (P2).
- md5 bf0dd7e9 = CSV de Wednesday (no pcap). GT nuevo con procedencia:
  8.935 cids (commiteado en tools/eval/out/).
- Otras deudas del dia: MAKEFILE-MLDETECTOR-START-PROFILE (P2),
  BRONZE-IP-BYTEORDER (P2, solo correlation writer),
  SNIFFER-GATEWAY-ONLY-NO-CONSUMER (P3), extension XGBOOST-FOSSIL al
  Makefile. El 2.517 sigue SIN PROCEDENCIA. level2/level3 SIN AUDITAR.

## LA LECTURA PARA ANDRES/CONSEJO (borrador honesto)

El sistema desplegado hoy no detecta trafico real: L1 ciego al flujo
parcial (P0, mecanismo probado por tenaza), fast path invertido (P0/P1,
regresion post-mayo con sospechoso), capa de decision max()+0.7
amplificando al peor detector (~224K FP / 0 TP anoche). PERO: cada fallo
esta medido, aislado, con causa nombrada y plan — con dos evals
reproducibles commiteados que se demuestran mutuamente. El recall 1.0
historico era un detector sintetico acertando por accidente; el metodo que
lo descubrio es la contribucion. El paper se reescribe con la tenaza
(0.9987 modelo / 0.0 desplegado / por que) — es MEJOR paper. La rama
`fix/verdict-multihead-honest` acaba de ganar su argumento con datos: el
monocapa quedo medido amplificando al peor detector y silenciando al menos
malo.

Reglas permanentes: medir no votar; un commit/un cambio/una razon; git add
explicito (NUNCA -u/-a); verificar ruta antes de concluir del contenido;
la premisa heredada tambien es un artefacto a verificar; EMECAS antes de
merge.