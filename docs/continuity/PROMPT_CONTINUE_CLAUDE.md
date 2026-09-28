# Prompt de continuidad — aRGus NDR, DAY282 → DAY283

Reglas de trabajo (sin cambios): medir, no votar; prediccion escrita antes de medir; comandos
separados o cada salida a su fichero; nunca `grep -rn` desde la raiz (usar `git grep` o el fichero
concreto); los scripts los ejecuta Alonso en su VM; scripts como bloque `cat > f <<'EOF'`; si algo
no da lo esperado, parar; `LC_ALL=C` en todo script con aritmetica en awk.

Operativa: targets del Makefile raiz en el **Mac**; scripts y patchers en el **defender** desde `/vagrant`;
trafico en el **client**. Log: `/vagrant/logs/lab/ml-detector.log` (rotar con `truncate -s 0`).
`make pipeline-start FORCE_ALL_HEADS=1` para que todas las cabezas puntuen. Ya NO hace falta VERBOSE para
ver las cabezas: `[HEAD-SCORES]` sale a nivel info.

## 0. Estado de git

Rama `feat/ddos-head-contract` (desde main 83f93ca8, tras el merge del PR #142). Commits DAY282: paso 1
(`[HEAD-SCORES]`), fix de umbrales L3, docs (inventario + BACKLOG + este prompt). Comprobar con
`git fetch` y `git log --oneline -5 origin/feat/ddos-head-contract` que el push esta hecho. NO mergeada.

## 1. Lo que DAY282 dejo medido

- **Paso 1 CERRADO.** `[HEAD-SCORES] event, src:port, dst:port, gate, l1=clase:conf, fast, ddos, ransom,
  traffic, internal (clase:p o na), cat`. Script: `scripts/d282_head_scores.sh LOG [REGEX|!REGEX]`.
- **Subida TCP legitima 50 KB/s** (`d281_tcp_sink.py` / `d281_tcp_upload.py`, puerto 9999): DDoS class1 100 %
  en 3 corridas. La cabeza DDoS emite solo ~5 valores distintos en 2000+ eventos ⇒ espacio de entrada efectivo
  casi sin dimensiones (confirma "umbral de caudal" de DAY281 desde la salida).
- **FP en ambiente**: DNS sin respuesta del client a 8.8.8.8/1.1.1.1 ⇒ DDOS.
- **Bug de configuracion cerrado**: `level3_web`/`level3_internal` nunca se leian (UB). Tras el fix, la subida
  legitima pasa a SUSPICIOUS_INTERNAL 100 %.
- **Orden de ejecucion del ml-detector**: decision, bronce y CSV ANTES de las cabezas L2/L3.
- **Inventario del contrato DDoS**: `docs/ddos-head-contract-inventory.md`. Resumen: TRES definiciones por
  rasgo (train, ml-detector, sniffer); un unico modelo ejecutado en DOS procesos (el sniffer corre las 4 cabezas
  por evento y el ml-detector pisa su resultado). El sniffer tiene por flujo todo lo necesario para symmetry,
  entropy, syn_ack, amplification, completion, protocol y caudal; por victima, delta de pkts/bytes de la ventana
  del kernel ya sellado en cada evento. Huecos de DISENO: H1 dispersion de origenes por victima, H2 linea base
  por victima para escalation, H3 significado de protocol_anomaly.

Deuda nueva: ver `docs/BACKLOG.md`, seccion DAY282.

## 2. Orden propuesto para DAY283 (paso 2 del orden DAY281, continuacion)

1. **D2 — coste de la inferencia en el sniffer** (decide si el sniffer infiere o solo calcula). Medir
   `stats_.ml_detection_time_us` por evento bajo la subida de 50 KB/s y bajo el replay CICDDoS2019 a 100 pps.
   Prediccion antes de medir. Localizar primero donde se imprime ese contador.
2. **D1 — definicion unica rasgo a rasgo**, partiendo de la del sniffer. Symmetry y escalation se redefinen
   con intencion; decidir H1/H2/H3 (¿sketch de origenes por victima en el tablero? ¿EWMA por victima?).
   Recordar DAY255: cambiar la definicion en serve sin reentrenar crea skew.
3. **Dataset por el mismo codigo**: replay de pcaps por el sniffer (metodo DAY270), recoger `ddos_embedded`,
   entrenar SIN scaler, medir importancias. Solo entonces quitar rasgos.
4. Pasos 4-5 del orden DAY281 sin cambios (fast-alert como entrada propia a la fusion; fusion + firewall
   obedeciendo final_decision; ahora sabemos ademas que la decision se toma antes de las cabezas).

Comprobaciones baratas pendientes (hipotesis sin medir): col 9 del CSV = categoria del sniffer;
`traffic_context` del sniffer siempre INTERNAL; FP DNS por duracion ≈ 0.

Siguen abiertas de DAY279-281: DEBT-FIREWALL-GATES-ON-LEVEL1-001 (P0), DEBT-ML-DETECTOR-VERDICT-LOG-IS-L1-001,
DEBT-ML-DETECTOR-LAG-UNDER-LOAD-001, DEBT-ML-DETECTOR-EVENT-PER-PACKET-001, DEBT-DDOS-HEAD-* de DAY281.
