# CONTINUIDAD DAY270 — La compuerta level1 es el hallazgo del día. Mañana: medir la compuerta con tráfico DDoS REAL (CICDDoS2019) ANTES de decidir Path A/Path B de Fase 2. El "FPR 0.7% sobre Neris" está DESCARTADO (era ficción: puntuaba flujos que en producción no llegan a A).

## EL HALLAZGO (medido, no re-litigar)
**El detector DDoS desplegado (level2) solo corre si level1 clasificó ATTACK.**
Guard exacto — `ml-detector/src/zmq_handler.cpp:549`:
```cpp
if (label_l1 == 1 && confidence_l1 >= config_.ml.thresholds.level1_attack) {
    ... // Level 2: DDoS aquí dentro (línea ~558)
}
```
`DDoSDetector::predict` (`ddos_detector.cpp:11`) es cálculo puro, SIN filtro. Toda la
compuerta vive en el llamador. → La fiabilidad de CUALQUIER cabeza DDoS está acotada
por el enrutado de level1. **La P0 de la misión es la coordinación level1→level2, no A en aislado.**

### Medición de la compuerta (replay Neris, HECHO)
- Replay: `Actual: 320524 packets in 61.05s, 5.79 Mbps, 19135 flows, Failed 2630 (~0.8%)`.
- 11208 bloques `Feature Extraction:` en el log.
- **Solo 6 pasaron la compuerta**: `grep -c 'Running Level 2 DDoS'` = 6.
- **A marcó 0 como DDoS**: `grep -c 'DDoS: class=1'` = 0.
- FPR desplegado sobre Neris = **0/6** → N ridículo, NO es medición de especificidad.
  Mide la SELECTIVIDAD de level1 ante botnet no-DDoS: ~99.95% despachado BENIGN antes de A.

## DOS MODELOS DISTINTOS (crítico, no confundir)
- **(a) ddos_head_A.pkl** = candidato OFFLINE. RandomForestClassifier (cargar con
  `joblib`, NO pickle plano). 9 features CICFlowMeter = subconjunto del vector level1-23.
  En `ml-training/scripts/ddos_detection/artifacts_ddos_A/`. **NO cableado al pipeline.**
- **(b) detector DESPLEGADO** = `ddos_trees_inline.hpp` synthetic-9 (syn_ack_ratio,
  packet_symmetry, source_ip_dispersion, ...). Es el que gobierna la compuerta 6/0.
- El eval de hoy fue del candidato (a); la compuerta es del desplegado (b).
- **PENDIENTE**: aclarar cómo (a) se relaciona con el fork Path A/Path B de Fase 2.

## ddos_head_A — metadata (el artefacto es árbitro)
- La teoría de DAY267 de "2 pares alias (A#0≡A#7, A#1≡A#8)" queda **REFUTADA**: son 9
  features independientes, sin duplicar. `feature_names.json` = `metadata.json["features"]`.
- 9 features: Total Length of Fwd/Bwd Packets, Fwd/Bwd Packet Length Max,
  Bwd Packet Length Mean, Packet Length Mean, Avg Fwd Segment Size, Subflow Fwd/Bwd Bytes.
- classes_=[0,1] (columna positiva = 1), `sep_min=0.6`, train_rows 2.6M,
  `fp_benign_cic=0.0878` (8.8% ref benigno CIC), recall Syn=0.577 (débil → ancla la
  vieja pendiente A+regla Syn), `median_impute` con TODO lo bwd = 0.0.
- Eval offline sobre el log (todos los bloques, sin compuerta): FP@0.5=23.7%, @0.6=1.1%,
  @0.7=0.7% sobre 2291 flujos 1-paquete de .165. Acantilado 0.5→0.6 (×20). **DESCARTADO
  como número de producción** — la compuerta deja pasar casi nada a la cabeza.

## CORRECCIONES DE HECHO (arrastran desde DAY268 — corregir donde aparezcan)
- **Myth grep**: `grep 'bwd, [1-9]'` cuenta el TOTAL, no el bwd (casa "bwd, <total>").
  El **"7756 bidireccional abundante" de DAY268 es FALSO**. Conteo real bwd≥1
  (`grep -cE ' [1-9][0-9]* bwd,'`) = **0**. Neris llega ENTERO unidireccional (1 paquete)
  o vacío (broadcast .255 / multicast 224.0.0.22). El artefacto MTU de VirtualBox degrada el C&C.
- **Higiene de logs**: `make logs-lab-clean` MUEVE el fichero → rompe el fd del proceso
  vivo (sigue escribiendo al inodo ya movido a archive/, mezclando ambiente+replay). Con
  el pipeline ARRIBA, rotar con `truncate -s 0` en sitio (conserva el inodo O_APPEND).
  logs-lab-clean = solo rotación en frío. Backlog: target `logs-lab-truncate`.
- Ambiente separable de Neris por IP: Neris = 147.32.x (principal .84.165); ambiente =
  192.168.100.x + DNS/NTP públicos.

## PENDIENTE DAY270 (en orden, despacito) — MEDIR LA COMPUERTA CON DDoS REAL
Objetivo: ¿deja pasar level1 los DDoS reales hasta A, o los bloquea igual que a Neris?
El número decide si Fase 2 (la cabeza) es la batalla, o si la P0 es level1.

1. **RESOLVER PRIMERO — ¿hay PCAP de CICDDoS2019?** (bloqueante del método)
    - El replay Neris usa `tcpreplay` sobre un PCAP. CICDDoS2019 descargado son **CSVs
      CICFlowMeter** (`ml-training/datasets/CICDDoS2019/`, ~22GB train + ~8.7GB test), NO
      PCAP confirmado. `tcpreplay` necesita paquetes, no CSV.
    - Comprobar si CIC provee PCAP del día y si cabe/interesa bajarlo:
      `ls -la ml-training/datasets/CICDDoS2019/` y buscar `.pcap`.
    - **Bifurcación de método**:
        - **(A) Con PCAP** → ctu-start customizado (clonar `ctu-start`/`test-replay-neris`,
          apuntar al PCAP DDoS). Mide la compuerta COMPLETA (sniffer→extractor→level1→level2),
          incluida la feature viva `source_ip_dispersion` que depende del aggregator de
          ransomware (ver [[grieta-b-source-ip-dispersion]]). Es la medición fiel.
        - **(B) Solo CSV** → eval OFFLINE de level1 sobre las features del CSV: ¿level1
          marca ATTACK los floods? Mide el enrutado de level1 pero NO la ruta viva (el
          extractor serve, source_ip_dispersion con su acople). Más barato, menos fiel.
          CAVEAT obligado: no reproduce la ventana del aggregator.
    - Decidir A vs B según exista PCAP. Empezar por A si es viable.

2. **Preparar el driver** (si A): hermano de `mitre-start`/`ctu-start`. Reusar el patrón
   ya documentado en [[ctu-start]]. Rotar log con `truncate -s 0` (NO logs-lab-clean)
   inmediatamente antes del replay. `make pipeline-start VERBOSE=1` y confirmar
   `--verbose` por pgrep.

3. **Medir la compuerta sobre DDoS real** (mismos contadores que hoy):
    - `grep -c 'Running Level 2 DDoS'`  → cuántos floods pasaron level1.
    - `grep -c 'DDoS: class=1'`         → cuántos marcó el detector desplegado.
    - Filtrar por IPs de ataque del ground-truth CICDDoS2019 (columna Label / Source IP).
    - **Lectura**: si pasan MUCHOS → la compuerta funciona, Fase 2 (la cabeza) importa.
      Si level1 los BLOQUEA → la P0 es level1, y Fase 2 esperaría a arreglar level1
      (recuerda su propia P0: `Init_Win_bytes_forward` hardcodeado a 0.0f en serve).

4. **Con la compuerta medida sobre DDoS real: decidir Path A/Path B de Fase 2.**
   (ver [[grieta-b-source-ip-dispersion]] "Giro a FASE 2"): Path A = reconstruir las 9
   features aRGus offline y entrenar sobre ellas; Path B = entrenar sobre features nativas
   CICFlowMeter del extractor BASE. Argumento medido que empuja a B: source_ip_dispersion
   degenera bajo flood (cap 10000 muerde). Fork vivo, pendiente de este dato de compuerta.

## INVARIANTES
`main` protegida (PR only). Rama de trabajo actual = `docs/ml-heads-grieta-b`. El Makefile
es la verdad (nivel de log por Makefile, nunca JSON a mano — muere en destroy→up).
`git grep` / fichero concreto, NUNCA `grep -rn` desde raíz. NO encadenar salidas grandes.
Rotar el log ANTES de cada replay que vaya a medir (con truncate si el pipeline está vivo).
Compilador/medición = árbitro. HECHO ≠ SOSPECHADO. El grep orienta; el parser/artefacto mide.

## BACKLOG (anotar, NO perseguir)
- `fpr_neris_A.py` sin commitear (untracked en raíz del repo). Decidir ubicación
  (¿ml-training/scripts/ddos_detection/tools/?) al trackearlo.
- `GenerateDDOSCPPForest.py` footgun L277 (ya cerrado en diag/ml-heads, commit 9090cedb —
  NO en docs/ml-heads-grieta-b; ojo si hay que portar).
- El eval de hoy usó `predict_proba(X)` con array pelado → UserWarning "X does not have
  valid feature names". Correcto por orden posicional, pero para paper: pasar DataFrame
  con nombres. Cosmético.
- Warning GPG apt HashiCorp (`NO_PUBKEY FC9CA96ACA026560`) en provisión — no bloquea.