# CONTINUIDAD DAY268 — Fork CICFlowMeter RESUELTO por medición. A = reemplazo de la cabeza DDoS zombi. Mañana: activar el volcado de features (palanca VERBOSE en el Makefile) → correr Neris → sacar el FPR de A. Despacito y con buena letra.

## Decisión de rumbo (firme)
Jubilar la cabeza DDoS vieja; **A la reemplaza** (no es experimento paralelo: A ES el
arreglo — labels reales de CICDDoS2019 + features vivas, frente a la vieja con
`source_ip_dispersion` hardcodeada). Orden: (1) medir FPR de A sobre Neris ANTES de
cablear; (2) si el número es bueno, cablear A (PENDIENTE 3); si es malo, averiguar por
qué. Luego cubrir las tres opciones (A sola / A+regla Syn / cabeza nueva con flags) para
comparar y medir en condiciones.

## HECHOS DAY267 (medidos, no re-litigar)
- **CICFlowMeter NO está** (host ni VM): `find ~ /opt /usr/local` + `mdfind` vacíos;
  `git grep -Ein 'cic.?flow'` solo da docs/site/scripts que leen columnas CIC, nunca
  invocan la herramienta; Vagrantfile limpio. aRGus nunca ejecutó CICFlowMeter. → **S1
  descartado** (mediría proxy en régimen no-vivo; el port pip sería un 3er régimen).
  **Vía = S2** (features del extractor C++ real).
- **Las 9 de A** (`artifacts_ddos_A/feature_names.json`) son **todas volumétricas de
  bytes/longitud, cero flags** → gotcha SYN descartado (SYN Flag Count no está en A; y
  CICFlowMeter-V3 lo puebla a 0, day264).
- **Las 9 salen del vector level1 de 23**: `ml-detector/src/feature_extractor.cpp::extract_level1_features`,
  `LEVEL1_FEATURE_NAMES` L11-33, nombres LIMPIOS sin espacio = casan con feature_names.json.
  Mapa A→índice level1: Total Fwd Bytes=9, Total Bwd=18, Fwd Pkt Len Max=2, Bwd Pkt Len
  Max=7, Bwd Pkt Len Mean=19, Pkt Len Mean=17, Avg Fwd Seg Size=3, Subflow Fwd Bytes=1,
  Subflow Bwd Bytes=12. Cómputo presente para las 9 (subflow L100/L134). El vector se
  **devuelve** (L192), NO se escribe a disco aquí.
- **A tiene 2 pares ALIAS** (contrato con duplicados): A#0 "Total Length of Fwd Packets"
  ≡ A#7 "Subflow Fwd Bytes" (ambos `total_forward_bytes`); A#1 ≡ A#8 (`total_backward_bytes`).
  Medido **INOCUO**: medianas del train idénticas (1438/1438, 0/0 en metadata.json) → en
  CICDDoS2019 eran la misma columna → train y serve colapsan igual, no hay skew. Matiz
  paper: A = "9 columnas, 7 señales independientes".
- **String mismatch = FANTASMA para A**: LEVEL1_FEATURE_NAMES limpio, feature_names.json
  limpio. Los nombres con-espacio son de `level1_attack_detector_metadata.json` (otro
  linaje, fuera de la ruta de A).
- **El oro NO persiste features** (confirmado: `logs/lab/argus-20260804-080140.parquet`,
  22 cols, solo identidad+veredicto+hmac, cero features). DAY266 ratificado.
  `DEBT-GOLD-FEATURES-NOT-PERSISTED-001` real: clasificador no auditable.
- **La cabeza DDoS VIEJA está ZOMBI**: `extract_level2_ddos_features` L240 →
  `source_ip_dispersion = normalize(1.0f,...)` **constante hardcodeada** (la única feature
  que el bosque viejo comía = grieta B, muerta). Explica los "0 FP sobre Neris" de DAY266:
  no era específica, era muda. NO era señal de que funcionara.
- **El log-debug del extractor NO sale hoy**: binario debug-*compiled* (`build-debug`,
  `-DDEBUG`, PROFILE?=debug) PERO spdlog corre en **info** (`ml_detector_config.json` L363
  `"level":"INFO"`; Makefile no pasa `--verbose`, grep vacío; main.cpp L222:
  `verbose ? debug : config.level`). El volcado de 23 features (L185-189) está gated a
  runtime-debug → dormido. Log de julio: solo warnings, cero `[debug] Feature[`.
- **BUG confirmado (Alonso)**: `ml-detector-start` L664 arranca con `cd .../build-debug`
  HARDCODEADO (ignora PROFILE) y SIN palanca de nivel → arranque mudo; el nivel solo es
  controlable por el JSON sellado, contra "el Makefile es la verdad".

## SOSPECHADO (medir antes de creer)
- El FPR de A sobre Neris caerá sobre todo en **flujos fwd-pesados sin backward** (medianas
  bwd de A todas =0 → A trata "sin vuelta" como firma de ataque; Neris real tiene backward).
  Los flujos con `Fwd IAT Min = 3.00e+10` (centinela de flujo de 1 paquete, visto en
  warnings) son los sospechosos nº1 de FP.
- El C++ de A puede ser **selección** (7 índices del vector de 23), no construcción — a
  confirmar al cablear.

## BACKLOG afloradas DAY267 (anotar, NO perseguir)
- Familia de features corruptas del extractor: `Fwd IAT Min = 3.00e+10` (centinela 8h),
  `Init_Win_bytes_forward = 0.0f` hardcodeado (L153 TODO), `act_data_pkt_fwd` = aproximación,
    + `source_ip_dispersion` constante. Patrón forense (material del paper).
- **TRES cosas llamadas "cabeza DDoS"**: (a) `extract_level2_ddos_features` C++ zombi,
  (b) `xgboost_ddos.ubj` firmado en `production/level2/ddos/` (Makefile L497), (c) bloque
  `level2` del config (L166). + A sin cablear. Mapear config→modelo→cabeza ANTES de cablear
  A: hay que saber cuál jubila A.
- **Umbral de despliegue DDoS = 0.7**, no 0.5 (config L149 `level2_ddos: 0.7`). A se midió a
  0.5. → medir FPR a AMBOS umbrales.

## PENDIENTE DAY268 (en orden, despacito)
1. **Palanca VERBOSE en el Makefile** (arregla el bug del arranque mudo + habilita el
   volcado). Cambio aditivo a `ml-detector-start` (y hermanos por simetría): `VERBOSE ?=` +
   `$(if $(VERBOSE),--verbose,)` en el arranque; de paso `build-debug` hardcodeado →
   `build-$(PROFILE)`. Commit propio:
   *"feat(makefile): palanca VERBOSE + build-$(PROFILE) en *-start (cierra arranque mudo del log)"*.
   Ver bloque Makefile L661-665.
2. **Correr Neris con volcado**: `make ml-detector-start VERBOSE=1` + pipeline arriba +
   rotar log julio + `make test-replay-neris`.
3. **Capturar formato**: `grep -m 5 '\[debug\].*Feature\[' logs/lab/ml-detector.log` →
   decidir clave de agrupación bloque-features↔flujo (5-tupla de línea "Flow:" = robusto;
   orden secuencial = frágil).
4. **Script FPR** (Python, offline sobre el log): parsear 23 features/flujo → seleccionar
   los 7 índices distintos → reconstruir vector de 9 en orden de A (duplicar alias) →
   cargar `ddos_head_A.pkl` → `predict_proba` → contar > umbral. **FPR a 0.5 Y 0.7**.
   Marcar cuántos FP son flujos degenerados del IAT centinela. Neris no tiene DDoS → todo
   positivo = FP (mide ESPECIFICIDAD; el recall vive en CIC: floods 0.99, Syn 0.58).

## Invariantes
`main` protegida (PR only). **El Makefile es la verdad** — nivel de log por el Makefile,
NUNCA editar el JSON sellado a mano (muere en destroy→up). `git grep` / fichero concreto,
nunca `grep -rn` desde raíz. No encadenar salidas grandes. Compilador/medición = árbitro.
HECHO ≠ SOSPECHADO.

> Nota de repo: el checkout local se llama `test-zeromq-docker` (nombre fósil del arranque:
> la idea original era portar upgraded-happiness Python/Docker a C++20/Docker; se pivotó a
> Vagrant/VMs al medir que Docker no convive con procesos root). Remoto =
> github.com/alonsoir/argus. Mismo repo; las rutas de este prompt son relativas a su raíz.