# INFORME DAY266 — Cabeza DDoS: el reentreno no era la pregunta

**Titular del día:** la cabeza DDoS **desplegada es específica** (0 FP sobre Neris), el
"reentrenar sobre A con labels reales" del PENDIENTE 1 **ya estaba medido** (es el
0,9269 macro del baseline, no una mejora escondida), y el 69 % de "MALICIOUS" sobre
Neris **no lo dispara DDoS sino un fast-path de ransomware con score constante 0,750**
(bug medido, deuda nueva). Camino 2 (reentreno Python) CERRADO con artefacto persistido;
Camino 1 (especificidad de A sobre Neris) a un comando de arrancar. Cero producción
escrita, `main` protegida intacta.

---

## Lo hecho hoy (medido, en orden)

### 1. Censo del binetflow de Neris → HECHO: Neris NO contiene DDoS
- Fichero: `datasets/ctu13/capture20110810.binetflow`, **2.824.636 flujos**.
- Desglose (censo limpio, cuadra al flujo): Background **2.753.288** / Normal **30.387**
  / From-Botnet **40.961** / Otros 0.
- Los `From-Botnet-V42` leídos enteros = DNS (~29 k), SPAM (~8,5 k), C&C
  (`CC1/16/53/54/55…`), click-fraud (constelación `HTTP-Ad-N`), descargas de binario y
  `TCP-Attempt` (escaneo). **Ni un flood.** El `grep` de keywords DDoS salió vacío, pero
  eso era el chequeo débil; lo que decide es el desglose: botnet C&C+spam+scan de manual.
- **Consecuencia (fork zanjado con dato):** el sustrato de **recall** de la cabeza A es
  **CICDDoS2019** (único corpus con el fenómeno). Medir recall de A contra Neris mediría
  el vacío. Neris **cambia de rol** → banco de **especificidad/FPR contra tráfico real**
  (lo que CIC no puede dar: su benigno es ~0,11 %, homogéneo, misma captura) + banco del
  **FP de la regla de handshake** (los **105.438** `Background-TCP-Attempt` = conexión
  rota real, el modo de FP predicho de la regla Syn).

### 2. Baseline de reproducibilidad (ancla)
- `train_ddos_head_v2.py` sobre CICDDoS2019 **reproduce byte-idéntico el DAY265**.
- Recall A: LDAP/MSSQL/NetBIOS/UDP **0,9999** · Portmap held-out **0,9972** ·
  UDPLag **0,9204** · **Syn 0,5713**. macro A **0,9269**. Δ(B−A) **+0,0047**,
  IC95 **[+0,0000, +0,0113]**. FPR reales A=5,88 % / B=2,58 % (defecto conocido, ignorado).
- SEED + core anti-leakage heredados de `train_ddos_head.py` = deterministas. Ancla firme.

### 3. Reconocimiento que reencuadra el PENDIENTE 1
- **"Reentrenar A con labels reales" = ES este harness.** Entrena un RF sobre las 9
  features de A con labels reales de CIC. El **0,9269 macro ES la cabeza A**; no hay una
  versión mejor esperando al reentreno. El PENDIENTE 1 **no sube recall**: sustituye la
  cabeza vieja (Betas sintéticas + geo + `syn_ack_ratio` + sintético-9) por A limpia, y
  mata dos grietas del pipeline viejo. Es higiene + artefacto, no mejora de detección.

### 4. Especificidad de la cabeza DDoS VIEJA (desplegada) sobre Neris
Vía el oro del paper `logs/lab/argus-20260804-080140.parquet` (1369 flujos; `.165` domina
con 970; sensor argus 100 % → es Neris, confirmado).
- **Hallazgo de diseño:** el oro **NO persiste features**, solo el veredicto (5-tupla +
  `final_classification` + scores). No hay vector que auditar. → obliga a recomputar para
  el Camino 1 (ver Deudas).
- `final_classification`: MALICIOUS **945** / BENIGN **424**.
- **Pero** `threat_category`: `RANSOMWARE_FAST_DETECTION` **945** / `RAW_CAPTURE` **424**
  → los 945 los dispara el **fast-path de ransomware**, NO la cabeza DDoS.
- `ml_detector_score` (el de DDoS): rango **0,0118–0,3949**, media **0,0974**,
  **0 flujos > 0,5**, 0 > 0,8. → **la cabeza DDoS vieja NO alucina sobre Neris: es
  específica (0 FP sobre 1369).** Buena noticia sobria.
- `fast_detector_score` **clavado en 0,750 exacto** en los 945 → huele a valor
  hardcodeado / rama con literal, no a medición. **Deuda nueva** (ver abajo).

### 5. Reentreno Python de la cabeza A — Camino 2 CERRADO
- Script hermano nuevo: `retrain_ddos_head_A.py` (124 líneas, en
  `ml-training/scripts/ddos_detection/`, **untracked**). Importa `load_day` /
  `pick_features` / `SEED` de `train_ddos_head.py` y `RF23_SERVED` / `EXCLUDE_MEASURED`
  de v2 (no reescribe de memoria — lección Init_Win).
- **A derivada, no tecleada:** `pick_features(0.60) ∩ RF23_SERVED − EXCLUDE_MEASURED` →
  las **9 exactas**, verificado en seco (mismo orden que el baseline).
- `syn_ack_ratio` y el sintético-9 **mueren por ausencia** (no están en RF23_SERVED ni en
  el summary de CIC); assert `FORBIDDEN_OLD` lo convierte en garantía medida.
- **Novedad frente a los dos harness** (que solo miden y tiran el modelo): **persiste**
  `ddos_head_A.pkl` (joblib) + `feature_names.json` (**el contrato del cableado C++**) +
  `metadata.json` en `artifacts_ddos_A/`.
- Resultado (umbral 0,5, otro punto de la curva que el baseline): reflexión **0,9999** ·
  Portmap **0,9973** · UDPLag **0,9254** · **Syn 0,5766** · **FP benigno CIC 0,0878**.
  **Perfil fiel al baseline** (reflexión saturada, Syn roto) → es la misma cabeza,
  ahora persistida. Objetivo cumplido: fidelidad + artefacto auditable, no mejora.

---

## Deudas nuevas MEDIDAS (no de hoy, no perder)
- **`fast_detector_score` constante 0,750** marcando el 69 % de Neris como MALICIOUS →
  huele a hardcode. Familia de `DEBT-RANSOMWARE-ML-HEAD-INERT-001` (P0 del BACKLOG), ahora
  con NÚMERO medido. Verificar en `main` si es la cabeza ML o una rama del fast-path.
- **El oro no persiste el vector de features servido**, solo el veredicto → impide auditar
  "dado este veredicto, ¿sobre qué evidencia?" y obliga a recomputar features para
  cualquier test de especificidad. Nombre propuesto (verificar contra BACKLOG):
  `DEBT-GOLD-FEATURES-NOT-PERSISTED-001`. Si se arreglara, cada decisión del clasificador
  sería auditable = "medir, no votar" aplicado al propio artefacto. **Rediseño grande, NO
  de hoy.**

## Pendiente / abierto
- **Camino 1 pleno:** especificidad de la cabeza **A** (el `.pkl` nuevo) sobre Neris.
  Necesita computar las 9 features sobre `botnet-capture-20110810-neris.pcap`. Fork sin
  resolver: **S1** CICFlowMeter (transferencia pura; según registros NO está en VM, es
  tool Java de host `ahlashkari/CICFlowMeter`; sus columnas casan literalmente con
  `feature_names`) vs **S2** extractor de aRGus (despliegue real; hoy el pipeline no
  persiste features → habría que desarrollarlo). **Decisión de prioridad diferida a
  cabeza fresca.** Primer comando: verificar si CICFlowMeter está en el host.
- **PENDIENTE 2 (cableado C++ de A):** el contrato es `artifacts_ddos_A/feature_names.json`
  (9 features, orden fijo; compilador = árbitro). Sin empezar.
- **PENDIENTE 3 (regla de handshake Syn):** `syn_count alto ∧ connection_established==false
  ∧ ack_count bajo`. FP a medir sobre los 105.438 `Background-TCP-Attempt` de Neris.
  Sin empezar. El sniffer YA cuenta bien (no re-litigar).

## Untracked (decidir rama/PR)
- `retrain_ddos_head_A.py` (nuevo hoy) + `artifacts_ddos_A/`.
- `train_ddos_head_v2.py` (DAY265) + los 7 scripts DDoS del DAY264.

## Invariantes (no re-litigar)
`main` protegida (PR only). Un commit una idea. `add` explícito por fichero. `git grep` o
fichero concreto — NUNCA `grep -rn` desde raíz. No encadenar salidas grandes en un bloque.
Manivela en la VM, push desde el HOST. Compilador/ctest = árbitro. El sniffer cuenta flags
BIEN (DAY265). El FPR de despliegue sale de `operating_point.py`, no del harness de ranking.
`ACK Flag Count`/`PSH Flag Count`/`Init_Win_bytes_forward` fuera del vector servible.
Verificar la SEMÁNTICA del conteo, no solo que sea no-cero.