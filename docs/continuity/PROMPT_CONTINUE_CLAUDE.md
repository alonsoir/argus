# Prompt de continuidad — aRGus NDR, DAY281 → DAY282

Reglas de trabajo (sin cambios): medir, no votar; predicción escrita antes de medir; comandos
separados o cada salida a su fichero; nunca `grep -rn` desde la raíz (usar `git grep` o el fichero
concreto); los scripts los ejecuta Alonso en su VM; scripts como bloque `cat > f <<'EOF'`; si algo
no da lo esperado, parar; `LC_ALL=C` en todo script con aritmética en awk.

Operativa (DAY280-281):
- Targets del Makefile raíz (`make pipeline-start`, `make emecas+++`) en el **Mac**. Scripts de medida
  en el **defender** desde `/vagrant`. Tráfico en el **client**. En el Mac las rutas son relativas
  (`logs/lab/...`); dentro de las VMs, `/vagrant/logs/lab/...`.
- Log del ml-detector: `/vagrant/logs/lab/ml-detector.log` (rotar con `truncate -s 0`, nunca logs-lab-clean).
- Todo cruce por evento: por `seq` de `[VICTIM-WINDOW]` o por la línea `  Flow: `; NUNCA por hora.
- FAST/NORM se separan por id: `event=fast-alert-…` frente a `event=<id>_<n>`.
- Con VERBOSE el ml-detector va muy retrasado: esperar a que `wc -l` del log se estabilice.

## 0. Primero: comprobar el estado de git

Al cerrar DAY281 el plan era: commits (scripts d281, prompt, BACKLOG) → push → EMECAS+++ → PR y
merge de `docs/ml-heads-grieta-b` a main. **No dar el merge por hecho sin medirlo**:
`git fetch` y `git log --oneline -3 origin/main`. Recordar la trampa DAY230: rebasar contra
`origin/main`, no contra `main` local.

## 1. Lo que DAY281 dejó medido (cabeza DDoS)

**La cabeza que evalúa el bosque NO consume `ddos_embedded` del sniffer.** El ml-detector recalcula
los 9 rasgos en `feature_extractor.cpp::extract_level2_ddos_features(nf)` desde campos genéricos de
flujo, y ese vector es el que recibe el bosque (`zmq_handler.cpp:581-605`). Lo que imprime la línea
`DDoS Features:` es exactamente lo que come el modelo.

Definiciones serve reales (verificadas contra el evento `12514083606146_51`):

| Rasgo | Fórmula serve (ml-detector) |
|---|---|
| [7] escalation | `flow_bytes_per_second / 1e6` |
| [8] saturation | `total_packets / max(dur_s, 1) / 1000` |
| [1] symmetry | `fwd / (fwd+bwd)` |
| [2] disp | `normalize(1,0,10)` = **0,1 constante** |
| [3] protocol | `(1.0 > 5) ? 1 : 0` = **0 constante** |
| [4] entropy | `packet_length_std / 1500` |

Dos desajustes apilados en el rasgo principal (importancia 0,33):
1. **Semántica**: train = "tasa de crecimiento" sintética (normal N(0,05; 0,02); ataque lognormal con
   medianas 1,8–3,3); serve = bytes/s del flujo en MB/s.
2. **Unidad**: `GenerateDDOSCPPForest.py` escala cada umbral con el MinMaxScaler de train; serve pasa
   valores crudos. Rasgo 7: 64 splits en 0,0038–0,0134 ⇒ **frontera efectiva = 3,8–13,4 KB/s por flujo**.
   Rasgo 8: 37 splits en 0,166–0,471 frente a serve ≈ 0,001 ⇒ muerto.

Resultado: **la cabeza DDoS es, en la práctica, un umbral de caudal por flujo.**

| Prueba | Resultado |
|---|---|
| Mini flood (seq 4814–4874) | recall NORM 70,9 %; sobre todos los eventos 18,5 % (74 % son fast-alert con vector vacío) |
| DNS 200 clientes | 0 FP (DNS mueve pocos bytes, no porque la cabeza "entienda") |
| Subida TCP legítima 2 KB/s | 100 % `class=0` |
| Subida TCP legítima 50 KB/s | **100 % `class=1` (FP puro)**; el firewall no bloqueó (obedece a L1) |

Correcciones a conclusiones previas (ya en BACKLOG, DEBT-DDOS-DUAL-SERVE-DEFINITIONS-001):
- DAY261-263: "ambos lados leen por nombre del proto" → falso para el consumidor ML.
- DAY272: disp clavada en 0,100 "por el cap del aggregator" → es hardcodeado.
- Grieta B trabajó sobre la definición del sniffer, que el bosque no come.

Deuda nueva DAY281 (detalle en BACKLOG): DEBT-DDOS-HEAD-ESCALATION-TRAIN-SERVE-SEMANTICS-001 (P0),
DEBT-DDOS-HEAD-SCALED-THRESHOLDS-RAW-INPUT-001 (P0), DEBT-DDOS-HEAD-CONSTANT-FEATURES-001,
DEBT-DDOS-DUAL-SERVE-DEFINITIONS-001, DEBT-DDOS-HEAD-MIXED-SCOPE-VECTOR-001,
DEBT-DDOS-HEAD-SCORES-FAST-ALERTS-001, DEBT-ML-DETECTOR-EVENT-PER-PACKET-001.

## 2. Orden ACORDADO (Alonso, DAY281)

Antes de nada: estado de git (§0). Si el merge está hecho, abrir **rama nueva** para el rediseño de
la cabeza DDoS (los rediseños no van en `docs/ml-heads-grieta-b`).

1. **Observabilidad**: que el ml-detector registre SIEMPRE la puntuación de cada cabeza por evento
   (L1, DDoS, ransomware, traffic, internal, fast). Barato, independiente de lo demás y prerrequisito
   para medir todo lo posterior y para la fusión. Relacionado: DEBT-ML-DETECTOR-VERDICT-LOG-IS-L1-001.

2. **Contrato de la cabeza DDoS**: UNA sola definición de los rasgos, compartida train/serve.
    - **Dónde se calculan: preferencia de Alonso = el SNIFFER** (el ml-detector ya está sobrecargado,
      DEBT-ML-DETECTOR-LAG-UNDER-LOAD-001), **condicionada a que sea factible al 100 %** con lo que el
      sniffer tiene. NO darlo por hecho. Primer paso = inventario MEDIDO, con predicción escrita antes:
      qué hay disponible en el punto de extracción del sniffer (`FlowStatistics`: spkts/dpkts,
      sbytes/dbytes, duración, `all_lengths`, IAT, flags; el `TimeWindowAggregator`; la ventana por
      víctima del kernel `ddos_victims`) frente a lo que necesita cada rasgo.
    - Ventaja si es el sniffer: el dataset de train se genera con EL MISMO código, replayando pcaps
      (CICDDoS2019) por el sniffer y recogiendo `ddos_embedded` (método de replay DAY270 ya medido).
      Sin reimplementar el extractor en Python ⇒ skew imposible por construcción.
    - Consecuencia: el ml-detector deja de recalcular (`extract_level2_ddos_features`) y consume
      `ddos_embedded` del proto. Se retira la definición duplicada (DEBT-DDOS-DUAL-SERVE-DEFINITIONS-001).
    - Riesgos a medir: coste en el hot path del sniffer; ~1 evento por paquete
      (DEBT-ML-DETECTOR-EVENT-PER-PACKET-001); acople con el aggregator de ransomware y su cap de
      10 000 (grieta B).
    - El sniffer produce un contrato de rasgos único y versionado; cada cabeza toma su subconjunto.
      NO recortar el sniffer "a medida de esta cabeza": lo que no use DDoS puede servir a otra.
    - **Sin scaler**: un bosque aleatorio es invariante a la escala. Entrenar sin MinMaxScaler y exportar
      umbrales en crudo elimina DEBT-DDOS-HEAD-SCALED-THRESHOLDS-RAW-INPUT-001 de raíz.
    - "Escalation" con sentido real (¿desde la ventana por víctima, relativa a su línea base?).
      CUIDADO lección DAY255: cambiar la definición en serve sin reentrenar crea skew.
    - Quitar 2-3 rasgos y reentrenar con el generador sintético NO basta: escalation seguiría
      significando otra cosa en train. El arreglo es el contrato + dataset calculado por el extractor de serve.

3. **Reentrenar y medir importancias**; SOLO entonces decidir qué rasgos sobran. Los constantes
   (disp, protocol) casi seguro fuera; saturation NO se quita a priori (hoy está muerto por el
   escalado; con definición coherente puede vivir).

4. **Fast-alert**: NO quitarlo del sniffer (es la detección rápida de capa 1, señal propia; ya aparece
   como `fast=` en el DUAL-SCORE). Dejar de enrutarlo por las cabezas de flujo (74 % de eventos del
   flood con vector vacío) y que entre en la fusión como una puntuación más.

5. **Fusión y firewall**: fórmula final con las puntuaciones de todas las cabezas (L411) y que el
   firewall obedezca `final_decision` (L583). Va al final a propósito: dar pesos a una cabeza que hoy
   es un umbral de caudal haría que la fórmula compense un defecto en vez de combinar señales.

Opcional (confirma la tesis): FP sobre ambiente real, con la predicción escrita de que los FP son
flujos de caudal > ~13 KB/s (`d281_esc_bins_flow.sh` con regex por IP).

Siguen abiertas de DAY279-280: DEBT-FIREWALL-GATES-ON-LEVEL1-001 (P0),
DEBT-ML-DETECTOR-VERDICT-LOG-IS-L1-001, DEBT-FAST-DETECTOR-REASON-MISMATCH-001,
DEBT-ML-DETECTOR-LAG-UNDER-LOAD-001, DEBT-XDP-INGRESS-ONLY-NO-SYMMETRY-001,
DEBT-FLOW-COUNTS-SCOPE-MISMATCH-001, DEBT-LAB-VM-CLOCK-DRIFT-001, DEBT-LAB-CLIENT-NO-EGRESS-001,
DEBT-VAGRANT-HASHICORP-APT-KEY-001, DEBT-VERIFY-PROTOBUF-FIND-SLOW-001, DEBT-PROTO-DISTRIBUTE-PROFILES-001.

## 3. Herramientas DAY281

- `scripts/d281_hpp_thr.sh [IDX] [HPP]` — distribución de umbrales del bosque por rasgo (espacio MinMax).
- `scripts/d281_esc_bins.sh LOG [SEQ_LO] [SEQ_HI]` — FAST/NORM × tramo de escalation × clase, por seq.
- `scripts/d281_esc_bins_flow.sh LOG REGEX` — igual, filtrando por la línea `Flow:`.
- `scripts/d281_tcp_sink.py HOST PORT` (defender) + `scripts/d281_tcp_upload.py HOST PORT KB_S SEG` (client)
  — carga TCP legítima a caudal fijo.
- Log DAY280 completo guardado en `/vagrant/logs/lab/d281_ml_detector_pre_upload.log`.