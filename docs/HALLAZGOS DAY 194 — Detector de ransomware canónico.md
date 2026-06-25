# HALLAZGOS DAY 194 — Detector de ransomware canónico

**Fecha:** 23 de junio de 2026
**Sesión:** DAY 194 (continuación de DAY 193)
**Ámbito:** Arqueología de procedencia del detector de ransomware en `ml-detector`
**Estado de la deuda madre:** `DEBT-RANSOMWARE-TWO-DETECTORS-001` → **RESUELTA**
**Método:** verificación contra el código fuente, no contra memoria. Cuatro comandos
encadenados, cada conclusión trazable a línea de fichero.

---

## 0 · Por qué esta sesión

DAY 193 dejó abierta la pregunta que ningún grep de ficheros podía cerrar: existen
dos detectores de ransomware en el repo —un RandomForest de 100 árboles embebido en
C++ (10 features) y un XGBoost de producción (45 features)—, ambos llamándose
"detector de ransomware", con espacios de features incompatibles. La pregunta no era
*qué ficheros existen* sino **cuál carga y ejecuta el binario en producción**. Eso
solo lo dice el cableado, no el inventario. Esta sesión lo cierra.

---

## 1 · El detector canónico es el RandomForest embebido

**Verificado.** La cadena de ejecución está probada de punta a punta contra el código:

| Eslabón | Fichero : línea | Qué hace |
|---|---|---|
| Instanciación | `ml-detector/src/main.cpp:328` | `make_shared<RansomwareDetector>()` |
| Inyección | `ml-detector/src/zmq_handler.cpp:21` | el detector entra al handler por constructor |
| Construcción de features | `zmq_handler.cpp:649` | se rellena el struct `Features` de 10 campos |
| Predicción | `zmq_handler.cpp:679` (aprox.) | `ransomware_detector_->predict(...)` |
| Decisión de bloqueo | `zmq_handler.cpp:677` | `is_ransomware(config_.ml.thresholds.level2_ransomware)` |

El segundo bloque del grep —`xgboost`, `XGBoost`, `.ubj`, `plugin_init`, `dlopen` en
`main.cpp` y el handler— **vino vacío**. El XGBoost-45 **no se carga** en la ruta de
ransomware del binario.

**Conclusión:** el detector de producción es el **RandomForest de 100 árboles, 10
features, embebido en tiempo de compilación** (`forest_trees_inline.hpp`,
3.764 nodos). El XGBoost-45 queda reclasificado de "detector divergente activo" a
**modelo entrenado huérfano** — existe en disco, no se ejecuta.

---

## 2 · El binario se autodescribe (procedencia por evidencia interna)

**Verificado** en `zmq_handler.cpp:669-671`. En cada predicción el binario emite al
contrato protobuf su propia identidad:

- `model_name = "ransomware_detector_embedded_cpp20"`
- `model_version = "1.0.0"`
- `model_type = protobuf::ModelPrediction::RANDOM_FOREST_RANSOMWARE`
- `confidence_score = ransomware_result.ransomware_prob`

Esto es la fuente más limpia de procedencia posible: no es lo que recuerda nadie, es
lo que el binario afirma de sí mismo en cada evento que clasifica. El enum
`RANDOM_FOREST_RANSOMWARE` es testigo en el contrato de que la ruta canónica es el RF.

---

## 3 · Cómo clasifica (mecánica del ensemble)

**Verificado** en `ransomware_detector.cpp::predict()`:

- Recorre los 100 árboles. En cada uno desciende desde la raíz mientras
  `feature_idx >= 0`; las hojas se marcan con `feature_idx == -2`.
- Regla de nodo: `feature_value <= threshold → hijo izquierdo`, si no, derecho.
- En hoja acumula `value[1]` = P(ransomware) de esa hoja.
- Promedia: `prob_ransomware = votes_ransomware / 100`.

**Es soft-voting por promediado de probabilidades de hoja, no votación dura por
mayoría de clase.** Es byte-equivalente a cómo `sklearn.RandomForestClassifier.
predict_proba` agrega. Para el paper: describirlo como "majority vote" sería incorrecto.

---

## 4 · El umbral operativo es 0.75, desde config y fail-closed

**Verificado.** `ml_detector_config.json:150` define `"level2_ransomware": 0.75`.
Se carga en `config_loader.cpp:231` vía `get_required<float>(...)` — si el campo
falta, el arranque **falla**, no hay default silencioso. El caller
(`zmq_handler.cpp:677`) pasa ese valor explícitamente a `is_ransomware(...)`,
sobrescribiendo tanto el `0.5` del `class_id` interno como el `0.75` por defecto del
helper en el `.hpp`.

**Consecuencia:** el doble umbral que parecía deuda (`0.5` en `predict()` vs `0.75`
en `is_ransomware()`) **no es deuda**: se resuelve por configuración, no por hardcode.
El número que gobierna cada decisión de bloqueo en producción es **0.75**, y es
auditable en un único fichero.

---

## 5 · El path de features es único y validado (no hay dualpath)

**Verificado** en `zmq_handler.cpp:632-658`. La sospecha de DAY 194 (dos rutas de
features conviviendo) queda **descartada por evidencia directa**:

1. `extract_level2_ransomware_features(nf)` produce un `std::vector<float>` desde
   `NetworkFeatures`.
2. **Guard de contrato** (línea 635): `if (vec.size() != 10) throw` → fail-closed,
   suma a `feature_extraction_errors`. El detector no puede recibir un vector mal
   dimensionado.
3. El struct `Features{...}` se rellena del vector **índice a índice**, con el mapeo
   idéntico al de `to_array()` en el `.hpp`:

   ```
   vec[0]→io_intensity   vec[1]→entropy   vec[2]→resource_usage
   vec[3]→network_activity   vec[4]→file_operations   vec[5]→process_anomaly
   vec[6]→temporal_pattern   vec[7]→access_frequency   vec[8]→data_volume
   vec[9]→behavior_consistency
   ```

No hay cálculo muerto, no hay segunda ruta, no hay desajuste de índices.
`DEBT-RANSOMWARE-FEATURE-DUALPATH-001` **no existe**.

---

## 6 · La única deuda viva: semántica de dominio

**Abierta.** `DEBT-RANSOMWARE-FEATURE-SEMANTICS-001` (P1, pre-paper).

El mapeo de índices es correcto, pero queda una pregunta que el path único no
contesta y que es la que de verdad importa para la honestidad del paper:

> ¿Qué **calcula** `extract_level2_ransomware_features` para `entropy`,
> `io_intensity` y `resource_usage` a partir de un `NetworkFeatures`?

El modelo lleva nombres de features con semántica **host** (entropía de ficheros,
intensidad de I/O de disco, uso de recursos del sistema). Pero el input en producción
es un **flujo de red**. Si el extractor deriva esos campos de señales de red y los
renombra con la semántica del entrenamiento, hay un **desajuste de dominio**: el
nombre coincide, el significado no. No es un bug —compila y corre— pero es justo lo
que un revisor de arXiv preguntará, y la respuesta determina si el §13 puede afirmar
que el modelo "detecta ransomware" o solo que "clasifica flujos con un modelo
entrenado en features renombradas".

**Dónde se resuelve:** `feature_extractor.cpp:272`, cuerpo de
`extract_level2_ransomware_features`. Es el primer acto de DAY 195. Es decisión de
diseño y de honestidad científica, no más arqueología.

---

## 7 · Higiene pendiente

- **`zmq_handler.cpp.backup` dentro de `src/`** — un `.backup` en el árbol de fuentes
  confunde greps futuros y, según el CMake, podría llegar a compilarse. Retirar a
  `docs/attic/` o eliminar si ya está en el historial de git.

---

## 8 · Bloque listo para el §13 del paper (tres frases trazables)

> El detector de ransomware es un RandomForest de 100 árboles (3.764 nodos) embebido
> en tiempo de compilación como `constexpr`, identificado en el contrato protobuf como
> `ransomware_detector_embedded_cpp20` v1.0.0 (`RANDOM_FOREST_RANSOMWARE`). Opera sobre
> 10 features host-dominantes (entropy 36 %, resource_usage 25 %, io_intensity 24 % —
> 85 % del peso en señales de host; network_activity 8 %). La agregación es soft-voting
> por promediado de probabilidades de hoja (equivalente a `predict_proba` de sklearn);
> el umbral de decisión, configurable, es 0,75 en producción.

Cada afirmación es trazable a línea de código.

---

## 9 · Advertencia viva (heredada de DAY 193, no se reabre)

El F1 del RF se obtuvo con datos de entrenamiento sintéticos. **Ese número no es el
resultado del paper; el resultado es la caída que produzca tu C2/cifrado emulado contra
el modelo.** El log de debug en `zmq_handler.cpp:638` imprime `entropy`, `io`,
`resource` en cada predicción — trazabilidad gratis para ese experimento, sin
instrumentar nada nuevo.

---

## 10 · Cierre de deudas

| Deuda | Estado tras DAY 194 |
|---|---|
| `DEBT-RANSOMWARE-TWO-DETECTORS-001` | **RESUELTA** — canónico = RF-100; XGBoost-45 = huérfano |
| `DEBT-RANSOMWARE-THRESHOLD-DUAL` (tentativa) | **NO PROCEDE** — resuelta por config (0,75) |
| `DEBT-RANSOMWARE-FEATURE-DUALPATH-001` (tentativa) | **NO EXISTE** — path único verificado |
| `DEBT-RANSOMWARE-FEATURE-SEMANTICS-001` | **ABIERTA (P1)** — desajuste de dominio host vs red |
| `DEBT-DATASET-PROVENANCE-RANSMAP-001` | sigue abierta (licencia/cita de RanSMAP, de DAY 193) |
| Higiene `zmq_handler.cpp.backup` | pendiente, trivial |

---

*Via Appia Quality — construido para durar décadas. Verificado contra el fichero, no
contra la memoria.*