# Reparación de la cabeza ML DDoS

**DAY 255+.** Reparación del skew train/serve de la cabeza DDoS. Ataca la P0 de
clasificación. Rama de trabajo `diag/ml-heads` (NO main; main protegida).

Deriva de la investigación del impacto ML del byte order y de la P0 de clasificación del
cierre del paper (DAY 254: "LA deuda; sin ella aRGus es instrumento+generador, no
defensor"). Es la línea de i+d+i que se retoma tras subir el paper v25.

---

## Diagnóstico (CERRADO extremo a extremo DAY 255, no re-medir)

- **El bug con nombre exacto** (material de paper, tesis S&P): NO es feature rota ni
  negligencia. Son DOS decisiones individualmente correctas y colectivamente
  incoherentes.
    - **Serving** sirve `geographical_concentration` como `MISSING_FEATURE_SENTINEL`
      (decisión de arquitectura documentada: GeoIP = REST 100-500 ms, inaceptable en
      pipeline sub-µs; geo se calcularía después, en el RAG/grafo post-mortem).
    - **Training** se hizo sobre un dataset SINTÉTICO que SÍ incluía geo (beta 1,9 normal
      vs 12,2 http-flood) → el bosque aprende a partir 16 veces sobre ella.
    - Nadie cerró el lazo: el contrato de features no es único ni compartido entre train y
      serve. El sentinel es el síntoma, no el villano.
- **Lección Vía Appia:** en ML embebido, una decisión de arquitectura sensata en
  inferencia (excluir feature costosa) produce skew silencioso si el entrenamiento no se
  entera. El contrato de features debe ser único y compartido.
- **El vector DDoS NO está muerto entero** (hipótesis "vector muerto" REFUTADA): 9
  features VIVAS desde `flow` real + 1 sentinel por diseño (geo). `source_ip_dispersion`
  CONFIRMADA VIVA (desde aggregator, ventana 30 s).
- **Hallazgo arquitectura (Fase 2, NO ahora):** conviven 40 features embedded sintéticas
  (lo que el RF consume, con huecos) + 102+ base network features computadas desde `flow`
  REAL (linaje CICIDS/XGBoost) sin sentinel, que ninguna cabeza consume. El activo de
  datos reales ya está construido y desperdiciado. Aprovecharlo = entrenar cabezas sobre
  features reales + labels Neris sirviendo por el MISMO extractor.

## La manivela DDoS (medida DAY 255, en `ml-training/scripts/ddos_detection/`)

- Cadena canónica de 3 scripts, rutas RELATIVAS al CWD:
  `SyntheticDDOSGenerator.py` → dataset json ; `DDosModelTrainer.py` (RF
  `random_state=42` en split y bosque) → `ddos_detection_model.pkl` + `ddos_scaler.pkl` ;
  `GenerateDDOSCPPForest.py <pkl> <hpp>` (normaliza thresholds con MinMaxScaler) → el `.hpp`.
- `generate_ddos_inline.py` es un MUÑÓN MUERTO (`ddos_predict` devuelve `0.0f`, carga
  `models/ddos_model.pkl` inexistente, header no funcional). NO es la manivela; mina para
  quien herede el repo.
- **Feature order (`DDOSFeatures.py`):** 0 syn_ack_ratio, 1 packet_symmetry,
  2 source_ip_dispersion, 3 protocol_anomaly_score, 4 packet_size_entropy,
  5 traffic_amplification_factor, 6 flow_completion_rate, **7 geographical_concentration**,
  8 traffic_escalation_rate, 9 resource_saturation_score.

## Plan de 5 pasos (cada uno = commit atómico en `diag/ml-heads`)

1. **SEMILLA** ✅ CERRADO DAY 255. Parche `np.random.seed(42)` + `random_state=42` en
   `sample()` del generador. `verify_seed_repro.sh` = GO (2 regeneraciones
   byte-idénticas). Commits `f434c57d` + `0ac2729b`.
2. **REPRODUCIR SIN EDITAR** ✅ CERRADO DAY 255. 2a (dataset trackeado) → `.hpp`
   byte-idéntico al desplegado (sha `ba63c6da`, geo=16, 612 nodos). 2b (dataset fresco
   sembrado) → sha `76ea86df`, geo=18, 634 nodos. El estado-2 baseline para el paso 3 es
   **2b** (la comparación servicio-vs-servicio exige el mismo régimen de dataset en los
   dos lados). Geo ni está en top-5 de importancia del RF → las 9 vivas deberían absorber
   su hueco.
3. **QUITAR GEO** ✅ CERRADO DAY 255+ (commiteado). Confirmado por medición que TODO el
   pipeline lee por NOMBRE (`df[DDOS_FEATURES]`, `feature_names` en metadata; cero
   `iloc`/`[7]` posicional) → reindex automático seguro. `.hpp` de 9 features sha
   `56f0c5ae`, geo ausente, reindex materializado (idx7=traffic_escalation,
   idx8=resource_saturation). Las 9 vivas absorbieron los 18 splits de geo sin drama;
   traffic_escalation_rate pasa a dominar importancia (0.33).
    - 3bis. **FOOTGUN CLI** ✅ CERRADO DAY 255+ (commit `9090cedb`).
      `GenerateDDOSCPPForest.py` parseaba `argv[1]`/`argv[2]` pero los IGNORABA. Firma
      sigue `<pkl> <hpp>`. Invariante al sha confirmado.
4. **PROPAGAR** ✅ CERRADO DAY 255+ (commit `b179faa0`). Consumidor =
   `ml-detector/src/ddos_detector.cpp` con `#include "ml_defender/ddos_trees_inline.hpp"`;
   fichero físico (única copia trackeada) =
   `ml-detector/include/ml_defender/ddos_trees_inline.hpp`. Copiado el `56f0c5ae`,
   shasum de las 2 copias idéntico.
5. **LADO SERVICIO** ✅ CERRADO DAY 255+. `patch_service_vector_9feat.py` acabó con 13
   ediciones sobre 6 ficheros (los 4 de producción + `main.cpp` + `test_detectors.cpp`),
   que la compilación fue destapando de uno en uno. `num_features()` del DDoS a `return 9`.
   `make ml-detector` verde 100 %, `test_detectors` pasa anunciando "9 features". Commit
   atómico de 6 ficheros. Cierra el MÉTODO de reparación del skew.

**Aviso honesto (paper, no sobre-vender):** quitar geo elimina el sesgo de esos ~16-18
nodos, pero el modelo sigue entrenado sobre Betas sintéticas y evaluado sobre Neris real.
Fase 1 prueba el MÉTODO de reparación; NO promete detector DDoS útil sobre Neris. Eso es
Fase 2 (features reales + labels Neris).

---

## DAY261-263 — grieta A refutada, arranca grieta B

Ver el documento dedicado `grieta-b-source-ip-dispersion.md`.

- **Grieta A (geo) REFUTADA como fantasma en DAY261-262.** DAY261 confundió dos
  `extract_ddos_features` homónimas (productor en `ml_defender_features.cpp:23` vs
  extractor del vector en `ring_consumer.cpp:1457`); ambos lados leen por NOMBRE de campo
  protobuf → skew posicional imposible. El reindex del sniffer sospechado en DAY261 nunca
  hizo falta; Fase 1 ya estaba completa en productor y consumidor desde DAY255. Deuda
  derivada: **DEBT-DDOS-GEO-DEADCODE** (geo write-only-dead hasta deprecar la col 83 del
  RAG). La rama `fase2/sniffer-reindex-ddos` describe trabajo fantasma (renombrar/anotar
  antes de mergear).
- **La grieta viva es B = `source_ip_dispersion`,** la única de las 9 que el bosque SÍ
  come. Definición operacional del lado serve MEDIDA, acople estructural con la ruta
  ransomware (la feature DDoS no tiene ventana propia; lee de un `TimeWindowAggregator`
  que POSEE el processor de ransomware, inyectado lazy en `ring_consumer.cpp:819`),
  dataset CICDDoS2019 validado y plan del análogo offline → todo en
  `grieta-b-source-ip-dispersion.md`.