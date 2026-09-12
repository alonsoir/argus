# CONTINUIDAD DAY267 — Camino 2 CERRADO (cabeza A reentrenada + artefacto persistido). Mañana: (1) resolver el fork de CÓMO computar las 9 features sobre Neris para el Camino 1 (especificidad de A), empezando por VERIFICAR si CICFlowMeter está en el host; (2) medir esa especificidad; (3) según el número, decidir cableado C++ y regla de handshake Syn.

## Estado (verificar al retomar)
- **Camino 2 (reentreno Python) CERRADO.** Artefacto en `ml-training/scripts/ddos_detection/artifacts_ddos_A/`:
  `ddos_head_A.pkl` + `feature_names.json` (**contrato del cableado C++**, 9 features, orden fijo) + `metadata.json`.
- Herramienta nueva UNTRACKED: `retrain_ddos_head_A.py` (124 líneas, hermano de v2). Importa el core de
  `train_ddos_head.py` y `RF23_SERVED`/`EXCLUDE_MEASURED` de v2. Deriva A por intersección (no teclea).
- `main` PROTEGIDA sin tocar. Cero producción escrita. Siguen untracked: `train_ddos_head_v2.py` (DAY265) + los 7 del DAY264.

## HECHOS DAY266 (medición — no re-litigar)
- **Neris NO tiene DDoS.** Censo de `capture20110810.binetflow` (2.824.636 flujos): Background 2.753.288 /
  Normal 30.387 / Botnet 40.961. Los From-Botnet = C&C+SPAM+click-fraud+scan. → sustrato de RECALL de A =
  CICDDoS2019; Neris = banco de ESPECIFICIDAD/FPR contra tráfico real + banco del FP de la regla Syn
  (105.438 `Background-TCP-Attempt` = conexión rota real).
- **Baseline reproduce byte-idéntico el DAY265** (v2): reflexión 0,9999 · Portmap 0,9972 · UDPLag 0,9204 ·
  Syn 0,5713 · macro 0,9269. Ancla firme.
- **"Reentrenar A con labels reales" YA estaba medido = el 0,9269.** El PENDIENTE 1 no sube recall; sustituye
  la cabeza vieja (Betas+geo+syn_ack_ratio+sintético-9) por A limpia. Reentreno confirma perfil (umbral 0,5):
  reflexión 0,9999 · Portmap 0,9973 · UDPLag 0,9254 · **Syn 0,5766** · FP benigno CIC 0,0878. FIEL, no mejor.
- **Especificidad de la cabeza DDoS VIEJA sobre Neris = 0 FP** (oro `argus-20260804-080140.parquet`, 1369 flujos,
  .165 domina). `ml_detector_score` máx 0,3949, media 0,097, **0 flujos > 0,5**. La cabeza DDoS NO alucina.
- **El 69 % "MALICIOUS" del oro NO es DDoS**: es el fast-path de ransomware (`RANSOMWARE_FAST_DETECTION` en los
    945) con `fast_detector_score` **constante 0,750** → huele a hardcode. DEUDA nueva medida.
- **El oro NO persiste features**, solo el veredicto → obliga a recomputar para el Camino 1. DEUDA de diseño.

## PENDIENTE (en orden)
1. **Fork del Camino 1 — cómo computar las 9 sobre `datasets/ctu13/botnet-capture-20110810-neris.pcap`.**
   PRIMER comando (cabeza fresca): `which cicflowmeter; find / -iname 'CICFlowMeter*.jar' 2>/dev/null | head`.
    - Registros (jul): CICFlowMeter NO está en VM (las VMs candidatas no existían); es tool Java de HOST
      (`ahlashkari/CICFlowMeter`); sus columnas casan LITERALMENTE con `feature_names` (espacios incluidos).
    - Si está → **S1** (transferencia pura, misma herramienta que el entreno): jar → CSV → cargar las 9 por
      nombre → puntuar con `artifacts_ddos_A/ddos_head_A.pkl` → FPR (todo positivo = FP, Neris no tiene DDoS).
    - Si NO está → decidir (descansado, con dato): instalar CICFlowMeter (una tarde + validar versión) vs
      desarrollar que el extractor de aRGus persista features (S2, despliegue real, más caro). NO decidir a horas malas.
2. **Medir la especificidad de A sobre Neris** con la vía elegida. HECHO = número (FP de A sobre Neris),
   persistiendo el vector de 9 + score en un CSV propio (parche local a la deuda del oro).
3. **Cableado C++ de la cabeza A** (PENDIENTE 2): el contrato es `feature_names.json`. El extractor level1 ya
   emite las 9; confirmar orden/nombres contra el JSON (compilador = árbitro). Solo vale la pena si (2) sale bien.
4. **Regla de handshake Syn** (PENDIENTE 3): `syn_count alto ∧ connection_established==false ∧ ack_count bajo`.
   Medir recall/FPR sobre CTU/mitre-start; su FP predicho = los 105 k `Background-TCP-Attempt` de Neris. El
   sniffer YA cuenta bien (no es un fix, es un veredicto nuevo que consume `connection_established`).

## DEUDAS (BACKLOG — anotar, no perseguir hoy)
- `fast_detector_score` constante 0,750 → 69 % de Neris MALICIOUS. Familia `DEBT-RANSOMWARE-ML-HEAD-INERT-001`
  (P0), ahora con número. Verificar en `main` si es la cabeza ML o rama del fast-path.
- El oro persiste veredicto pero no el vector servido (propuesto `DEBT-GOLD-FEATURES-NOT-PERSISTED-001`,
  verificar contra BACKLOG). Rediseño grande. Arreglarlo = decisiones del clasificador auditables (Vía Appia).
- Untracked a decidir rama/PR: `retrain_ddos_head_A.py` + `artifacts_ddos_A/` + los del DAY264/265.

## Invariantes
`main` protegida (PR only). Un commit una idea. `add` explícito. `git grep`/fichero concreto — NUNCA `grep -rn`
desde raíz. No encadenar salidas grandes. Manivela en VM / push desde HOST. Compilador/ctest = árbitro. El
sniffer cuenta flags BIEN. FPR de despliegue de `operating_point.py`, no del harness. Verificar SEMÁNTICA del
conteo, no solo no-cero.

---

## PROMPT DE CONTINUIDAD DAY267 (pegar al arrancar)

> Retomas aRGus (arXiv:2604.04952) en DAY267. Ayer (DAY266) CERRÉ el Camino 2: la cabeza DDoS **A**
> reentrenada sobre CIC con labels reales, artefacto persistido en
> `ml-training/scripts/ddos_detection/artifacts_ddos_A/` (`ddos_head_A.pkl` + `feature_names.json` = el
> CONTRATO de 9 features para el cableado C++ + `metadata.json`). El script es `retrain_ddos_head_A.py`
> (hermano de v2, importa el core, deriva A por intersección; untracked). El perfil es FIEL al baseline
> (reflexión 0,9999, Portmap 0,997, **Syn sigue roto ~0,58**, FP benigno CIC 0,088): no sube recall, es
> higiene + artefacto.
>
> HECHOS de ayer, no re-litigar: (a) **Neris NO tiene DDoS** (censo del binetflow: es C&C+spam+click-fraud
> +scan) → Neris es banco de ESPECIFICIDAD, no de recall; (b) la cabeza DDoS **vieja** es **específica**
> sobre Neris (0 FP, ml_score máx 0,39 sobre 1369 flujos); (c) el 69 % "MALICIOUS" del oro es el **fast-path
> de ransomware con score CONSTANTE 0,750** (deuda, no es DDoS); (d) el oro NO persiste features (deuda de
> diseño; por eso hay que recomputar).
>
> Trabajo de hoy, en orden: (1) resolver CÓMO computar las 9 features sobre
> `datasets/ctu13/botnet-capture-20110810-neris.pcap` para medir la especificidad de la cabeza A. PRIMER
> comando: `which cicflowmeter; find / -iname 'CICFlowMeter*.jar' 2>/dev/null | head` — los registros dicen
> que NO está en VM (es tool Java de host, `ahlashkari/CICFlowMeter`, columnas literales = `feature_names`).
> Si está → S1 (jar→CSV→puntuar con el .pkl→FPR, todo positivo=FP). Si no → decidir instalar vs desarrollar
> que el extractor persista features (NO a horas malas). (2) medir especificidad de A. (3) según el número:
> cableado C++ (contrato = feature_names.json, level1 ya emite las 9, compilador árbitro) y regla de handshake
> Syn (FP sobre los 105 k `Background-TCP-Attempt` de Neris). Invariantes: main protegida (PR only), un commit
> una idea, `git grep`/fichero concreto nunca `grep -rn` desde raíz, manivela en VM / push desde HOST, no
> encadenar salidas grandes.