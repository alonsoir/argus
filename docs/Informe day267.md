# Informe DAY267 — Fork CICFlowMeter resuelto por medición. A = reemplazo de la cabeza DDoS zombi.

**Naturaleza de la sesión:** diagnóstico puro. Nueve mediciones encadenadas, cero
líneas de fuente de producción tocadas. El objetivo del día era resolver *cómo*
computar las 9 features de la cabeza A sobre el Neris para medir su especificidad
(Camino 1). Se resolvió eso y, de paso, se destaparon cuatro anomalías del extractor
y una decisión de rumbo.

---

## Decisión de rumbo (firme)

Jubilar la cabeza DDoS vieja; **A la reemplaza**. No es un experimento paralelo: el
trabajo de DAY264-266 (derivar A por intersección, reentrenarla con labels reales de
CICDDoS2019, persistir el artefacto) **fue** el arreglo de la cabeza DDoS. Lo que
falta es enchufarla y medirla.

Orden acordado, por honestidad científica:
1. Medir el FPR de A sobre Neris **antes** de cablear.
2. Si el número es bueno → cablear A (PENDIENTE 3). Si es malo → averiguar por qué.
3. Cubrir después las tres opciones (A sola / A+regla Syn / cabeza nueva con flags)
   para comparar, aprender y medir en condiciones.

---

## HECHOS DAY267 (medidos, no re-litigar)

### El fork CICFlowMeter

- **CICFlowMeter NO está** — ni en host ni en VM. `find ~ /opt /usr/local -iname
  'CICFlowMeter*.jar'` vacío; `mdfind` sobre el volumen indexado vacío; `git grep -Ein
  'cic.?flow'` solo devuelve documentación, el índice de mkdocs (`site/`,
  `search_index.json`) y scripts Python que **leen columnas** de datasets CIC ya
  extraídos (`profile_cicddos.py`, `offline_source_ip_dispersion.py`), nunca invocan
  la herramienta. El Vagrantfile está limpio.
- **Consecuencia:** aRGus nunca ejecutó CICFlowMeter; siempre consumió datasets CIC ya
  extraídos por sus autores. Para S1 no hay andamio que reaprovechar. Y el HECHO de
  julio del prompt queda ratificado, no refutado: no en VM *y* no en host.
- **S1 descartado** (instalar el jar): mediría A alimentada por un jar de 2017 con bugs
  de teardown TCP conocidos (documentados en `Informe day264.md`) — un régimen que el
  despliegue **no vive**. El `pip install cicflowmeter` (port de Python de hieulw) sería
  aún peor: un **tercer** régimen de cómputo, distinto de CIC y del C++ de aRGus.
- **Vía elegida = S2**: computar las features con el extractor C++ real de aRGus.

### El contrato de features de A

- Las 9 de A (`artifacts_ddos_A/feature_names.json`) son **todas volumétricas de
  bytes/longitud, cero flags**: Total Length Fwd/Bwd Packets, Fwd/Bwd Packet Length Max,
  Bwd Packet Length Mean, Packet Length Mean, Avg Fwd Segment Size, Subflow Fwd/Bwd Bytes.
- **Gotcha SYN descartado por medición:** `SYN Flag Count` no está en A. Y CICFlowMeter-V3
  puebla ese flag a 0 (`Informe day264.md:67`), así que aunque hubiera estado, A se habría
  entrenado ciega a él. No es el caso: A no mira flags en absoluto.
- **Las 9 salen del vector level1 de 23.** En `ml-detector/src/feature_extractor.cpp`,
  `extract_level1_features` rellena `features(23)` por índice explícito;
  `LEVEL1_FEATURE_NAMES` (L11-33) es el contrato de orden, con nombres **limpios sin
  espacio** → casan con `feature_names.json`. El vector se **devuelve** (L192), no se
  escribe a disco aquí. Mapa A → índice level1:

  | A idx | nombre (contrato)             | campo protobuf                     | idx level1 |
    |-------|-------------------------------|------------------------------------|-----------:|
  | 0     | Total Length of Fwd Packets   | `total_forward_bytes()`            | 9          |
  | 1     | Total Length of Bwd Packets   | `total_backward_bytes()`           | 18         |
  | 2     | Fwd Packet Length Max         | `forward_packet_length_max()`      | 2          |
  | 3     | Bwd Packet Length Max         | `backward_packet_length_max()`     | 7          |
  | 4     | Bwd Packet Length Mean        | `backward_packet_length_mean()`    | 19         |
  | 5     | Packet Length Mean            | `packet_length_mean()`             | 17         |
  | 6     | Avg Fwd Segment Size          | `average_forward_segment_size()`   | 3          |
  | 7     | Subflow Fwd Bytes             | `total_forward_bytes()`            | 1          |
  | 8     | Subflow Bwd Bytes             | `total_backward_bytes()`           | 12         |

- **A tiene 2 pares ALIAS (contrato con duplicados), medidos INOCUOS.** A#0 ≡ A#7 (ambos
  `total_forward_bytes`); A#1 ≡ A#8 (ambos `total_backward_bytes`). El compilador jamás lo
  vería (9 nombres, 9 huecos, casan). Se comprobó con las medianas del train persistidas en
  `metadata.json`: 1438.0 ≡ 1438.0 y 0.0 ≡ 0.0 → en CICDDoS2019 eran la misma columna
  (Subflow Bytes == Total Length, subflow sin segmentar) → train y serve colapsan igual →
  **no hay skew**. Matiz para el paper: A = "9 columnas, **7 señales independientes**".
- **String mismatch = FANTASMA para A.** `LEVEL1_FEATURE_NAMES` limpio, `feature_names.json`
  limpio. Los nombres con-espacio (`" Subflow Fwd Bytes"`) son de
  `level1_attack_detector_metadata.json`, **otro linaje** (metadata cruda CIC del detector
  viejo), fuera de la ruta de A.
- **Las 9 están las 9 en el extractor C++**, incluidas las dos subflow con cómputo presente
  (`feature_extractor.cpp` L100, L134). S2 no tiene incógnitas de existencia: es
  **selección** (7 índices distintos del vector de 23) + reconstrucción del vector de 9 en
  orden de A duplicando alias.

### El oro y la auditabilidad

- **El oro NO persiste features.** `logs/lab/argus-20260804-080140.parquet`: 22 columnas,
  solo identidad de flujo (`community_id`, IPs, puertos, `flow_uid`), veredictos
  (`final_classification`, `fast_detector_score`, `ml_detector_score`,
  `overall_threat_score`), procedencia y `hmac_row`. Cero features. DAY266 ratificado.
- `DEBT-GOLD-FEATURES-NOT-PERSISTED-001` es real y grave: un clasificador cuyo oro no
  guarda sus entradas es **no auditable** — no se puede reconstruir por qué marcó un flujo
  sin volver a correr el pipeline. Es lo contrario de Vía Appia. Material honesto de paper.

### La cabeza DDoS vieja está ZOMBI

- `extract_level2_ddos_features` (`feature_extractor.cpp` L240):
  `features[2] = normalize(1.0f, 0.0f, 10.0f)` — `source_ip_dispersion` es una **constante
  hardcodeada** disfrazada de proxy ("using protocol variety as proxy"). Era la ÚNICA
  feature que el bosque viejo comía de verdad (grieta B).
- **Reinterpreta el "0 FP sobre Neris" de DAY266:** la cabeza vieja no daba 0 FP por ser
  específica, sino por estar **muda** — cero señal, cero positivos. No era buena noticia,
  era una cabeza inerte. Se retira la lectura optimista de ayer.

### El log-debug no sale hoy (y por qué)

- El binario es debug-*compiled* (`build-debug`, `-DDEBUG` por `PROFILE ?= debug`, Makefile
  L92-93, L125) **pero spdlog corre en info**: `ml_detector_config.json` L363
  `"level": "INFO"`; el Makefile no pasa `--verbose` (grep vacío); `main.cpp` L222 =
  `verbose ? debug : string_to_log_level(config.logging.level)`. El volcado de las 23
  features (L185-189, gated a `logger_->level() <= debug`) está **dormido**. El log de julio
  lo confirma: solo `[warning]`, ninguna línea `[debug] Feature[`.
- **Bug confirmado** (diagnóstico de Alonso): `ml-detector-start` (Makefile L664) arranca
  con `cd .../build-debug` **hardcodeado** (ignora `build-$(PROFILE)`) y **sin palanca de
  nivel** → arranque mudo, nivel solo controlable desde el JSON sellado, contra el principio
  "el Makefile es la verdad".

---

## SOSPECHADO (medir antes de creer)

- El FPR de A sobre Neris caerá sobre todo en **flujos fwd-pesados sin backward**: las
  medianas bwd de A en el train son todas 0 (`metadata.json`) → A trata "sin vuelta" como
  firma de ataque, y Neris real es bidireccional. Los flujos con `Fwd IAT Min = 3.00e+10`
  (centinela de flujo de 1 paquete, visto en los warnings de julio) son los sospechosos nº1.
- El C++ de A puede estar **medio hecho** si el vector de 23 por índice es reutilizable
  directamente; a confirmar al cablear.

---

## Perfil medido de A (de `metadata.json`, sin re-medir)

Recall por ataque a umbral 0.5: LDAP 0.9999 · MSSQL 0.9999 · NetBIOS 0.9999 · Portmap 0.9973
· UDP 0.9999 · UDPLag 0.9254 · **Syn 0.5766**. FP benigno CIC held-out (0.5): 0.0878.

**Frontera estructural de A:** ciega a Syn *por diseño*. Un Syn flood son paquetes SYN
diminutos casi sin payload y sin backward; sobre features de volumen de bytes, se confunde
con ruido de fondo pequeño. No es un bug de A — es que sus 9 features no miran donde vive la
señal de Syn (las flags). Por eso la **regla de handshake Syn** (PENDIENTE 4) no es opcional:
es el complemento que cubre el punto ciego de A, no una redundancia.

---

## BACKLOG afloradas DAY267 (anotar, NO perseguir)

- **Familia de features corruptas del extractor** (patrón, material forense del paper):
    - `source_ip_dispersion = normalize(1.0f,...)` constante (cabeza level2 zombi).
    - `Fwd IAT Min = 3.00e+10` (≈8,3 h): centinela de flujo de 1 paquete metido como valor.
    - `Init_Win_bytes_forward = 0.0f` hardcodeado con TODO (`feature_extractor.cpp` L153).
    - `act_data_pkt_fwd` = aproximación (`total_forward_packets()`, "asumimos que incluye
      data packets").
- **TRES cosas llamadas "cabeza DDoS"** — mapear config→modelo→cabeza ANTES del cableado de
  A, hay que saber cuál jubila A:
    1. `extract_level2_ddos_features` — la función C++ zombi.
    2. `xgboost_ddos.ubj` firmado en `production/level2/ddos/` (Makefile L497).
    3. el bloque `level2` del config (`ml_detector_config.json` L166).
- **Umbral de despliegue DDoS = 0.7**, no 0.5 (config L149 `level2_ddos: 0.7`). A se midió a
  0.5. → medir el FPR a **ambos** umbrales.
- **Arranque mudo del log** (bug): sin palanca de nivel desde el Makefile; `build-debug`
  hardcodeado ignora PROFILE. Se arregla en el PENDIENTE 1 de mañana.

---

## PENDIENTE DAY268 (en orden, despacito)

1. **Palanca VERBOSE en el Makefile** (arregla el arranque mudo + habilita el volcado).
   Cambio aditivo a `ml-detector-start` (y hermanos por simetría): `VERBOSE ?=` +
   `$(if $(VERBOSE),--verbose,)` en el arranque; de paso `build-debug` hardcodeado →
   `build-$(PROFILE)`. Commit propio:
   *"feat(makefile): palanca VERBOSE + build-$(PROFILE) en *-start (cierra arranque mudo del log)"*.
2. **Correr Neris con volcado:** `make ml-detector-start VERBOSE=1` + pipeline arriba +
   rotar el log de julio + `make test-replay-neris`.
3. **Capturar formato:** `grep -m 5 '\[debug\].*Feature\[' logs/lab/ml-detector.log`.
   Decidir clave de agrupación bloque-features ↔ flujo (5-tupla de la línea "Flow:" =
   robusto; orden secuencial = frágil si el log entrelaza hilos).
4. **Script FPR** (Python, offline sobre el log): parsear 23 features/flujo → seleccionar
   los 7 índices distintos → reconstruir el vector de 9 en orden de A (duplicar alias) →
   cargar `ddos_head_A.pkl` → `predict_proba` → contar > umbral. **FPR a 0.5 y a 0.7.**
   Marcar cuántos FP son los flujos degenerados del IAT centinela. Neris no tiene DDoS →
   todo positivo = FP (mide ESPECIFICIDAD; el recall vive en CIC).

---

## Invariantes

`main` protegida (PR only). **El Makefile es la verdad** — el nivel de log se controla desde
el Makefile, NUNCA editando el JSON sellado a mano (muere en `destroy→up`). `git grep` /
fichero concreto, nunca `grep -rn` desde raíz. No encadenar salidas grandes. Compilador /
medición = árbitro. HECHO ≠ SOSPECHADO.