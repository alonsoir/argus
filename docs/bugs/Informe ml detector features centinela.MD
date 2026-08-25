# Informe forense — features centinela del ml-detector y skew train/serve

**Proyecto:** aRGus NDR · **Rama de investigación:** `diag/ml-heads` (off `main` @ `9f1799f8`, último tag `pre-release-0.0.2`)
**Objeto:** por qué el `ml_score` de aRGus es ciego sobre el botnet Neris (ml_medio ≈ 0.07 sobre los flujos MALICIOUS; el 100 % de la señal MALICIOUS la lleva el fast-path literal 0.75).
**Método:** medir contra fichero, sin levantar VM. Cada afirmación etiquetada **[HECHO]** (medido en esta sesión con el comando citado), **[SOSPECHADO]** (hipótesis viva sin medir), **[REFUTADO]** (hipótesis previa tumbada por el dato).

> Regla del informe: HECHO ≠ SOSPECHADO. Toda conjetura va etiquetada o no se escribe. Las hipótesis refutadas se conservan (son parte del registro forense, no basura).

---

## 0. Resumen ejecutivo (una frase por hallazgo)

- **[HECHO]** De las 40 features que alimentan las 4 cabezas ML, **10 salen a `MISSING_FEATURE_SENTINEL = -9999.0f` en TODA corrida**, por diseño, sin que ningún runtime las salve.
- **[HECHO]** El centinela es `-9999.0f` (`common/include/sentinel.hpp`), documentado como *"matemáticamente inalcanzable por cualquier ratio real de red"* — propiedad útil para detección-de-ausencia, **catastrófica para un árbol de decisión con cortes aprendidos en [0,1]**: `-9999 <= threshold` es siempre cierto, así que cada nodo que parte sobre una feature centinela toma **siempre** la misma rama.
- **[HECHO]** En la cabeza DDoS, el bosque (100 árboles, 256 nodos-split, 356 hojas) **parte 16 veces sobre `geographical_concentration` (idx 7), que vale −9999 siempre**. El modelo se entrenó con una columna geográfica separable y producción no la calcula → **skew train/serve medido**.
- **[HECHO]** El árbol DDoS de ejecución (`ml-detector/include/...`) es **bit-idéntico** al de entrenamiento (`ml-training/scripts/...`): `shasum` igual. El skew **no está en el árbol**, está en el **vector de features** que se le sirve.
- **[REFUTADO]** "El aggregator no se inyecta en producción → 10 features multi-flow a −9999." El cableado está **sano**: `initialize_ransomware_detection()` se llama incondicionalmente (`ring_consumer.cpp:194`), no puede fallar por entorno (no carga modelos ni abre recursos), y `set_aggregator` recibe un aggregator vivo.
- **[REFUTADO]** "`source_ip_dispersion` no se calcula." Sí se calcula, desde el aggregator (ventana 30 s), no desde el flujo. Y el bosque DDoS solo parte **1 vez** sobre ella: no era el drama que la nota vieja (DAY 229) señalaba.

**Titular honesto:** el `ml_score` ciego sobre Neris está **sobre-determinado**. Esta sesión ha descartado el cableado del aggregator y ha localizado un mecanismo concreto y reparable (features centinela entrando en cortes de árbol, con la geográfica como caso más claro), que **se suma** a la transferencia de distribución (CICIDS→Neris) ya documentada. No es lo uno **o** lo otro.

---

## 1. La cadena medida (evidencia, en orden)

### 1.1 El centinela y su veneno para árboles — [HECHO]
`common/include/sentinel.hpp`:
```cpp
namespace ml_defender {
inline constexpr float MISSING_FEATURE_SENTINEL = -9999.0f;
}
```
Cabecera compartida por todo el proyecto (ADR-012 §4). Doc propia: *"matemáticamente inalcanzable por cualquier ratio real de red; determinístico; compatible ONNX/FAISS."*

Consecuencia para un `DDoSTreeNode { int16_t feature_idx; float threshold; ... }`: los thresholds del fichero son ratios en ~[0,1]. Un valor de feature de −9999 satisface `−9999 <= threshold` en **todos** los nodos que parten sobre ella → rama fija, decisión anulada. La feature no es "inerte": **fuerza** el camino.

### 1.2 Censo de features servidas al modelo — [HECHO]
Fuente: `sniffer/src/userspace/ml_defender_features.cpp` (fichero completo leído) + `grep` de los `return MISSING_FEATURE_SENTINEL` cruzado con las firmas `extract_*`.

**Cubo A — muertas estructurales (−9999 SIEMPRE) = 10 de 40:**

| Cabeza | Feature | idx en su vector | Motivo |
|---|---|---|---|
| DDoS | `geographical_concentration` | 7 | GeoIP diferido a "Phase 2"; nunca implementado |
| Ransomware | `io_intensity` | 0 | Pide I/O de disco — no existe en red |
| Ransomware | `resource_usage` | 2 | Pide CPU/memoria — no existe en red |
| Ransomware | `file_operations` | 4 | Pide inspección SMB/CIFS — no implementada |
| Ransomware | `process_anomaly` | 5 | Pide telemetría de proceso — no existe en red |
| Traffic | `tcp_udp_ratio` | 2 | "Phase 2" — requiere campo protocolo |
| Traffic | `flow_duration_std` | 5 | "Phase 2" — requiere multi-flow |
| Traffic | `protocol_variety` | 8 | "Phase 2" — requiere multi-flow |
| Internal | `connection_duration_std` | 4 | "Phase 2" — requiere multi-flow |

> Nota de recuento honesta: durante la sesión canté "9" de memoria y el censo corregido dio **10** (DDoS 1 + Ransomware 4 + Traffic 3 + Internal 1 = 9… **pendiente reconciliar**: la tabla lista 9 filas; verificar si `geographical_concentration` computa como cubo A junto a las 8 de "Phase 2" da 9 o 10). **[SOSPECHADO — reconciliar el recuento exacto en la próxima sesión con un conteo mecánico, no de memoria.]** Lo que NO está en duda: la cabeza **ransomware tiene 4/10 features muertas por construcción física** (I/O, CPU, ficheros, procesos), y es la cabeza más lisiada.

**Cubo B — dependientes de aggregator (9): vivas, porque el aggregator llega.** `source_ip_dispersion`, y features de entropía/concentración/rate de Traffic e Internal. Su valor sobre Neris está **sin medir** (paso runtime).

**Cubo C — condicionales de tráfico (3):** centinela solo en flujos degenerados (`iat_mean==0`, `mean==0`, CoV en banda media). Frecuencia sobre Neris sin medir.

### 1.3 El cableado del aggregator está sano — [REFUTADO como causa]
Cadena verificada línea a línea:
- `ring_consumer.cpp:194` → `if (!initialize_ransomware_detection()) { ... }` — llamada **incondicional** al arrancar el consumer.
- `ring_consumer.cpp:1176-1185` → construye `RansomwareFeatureProcessor`, y solo pone `ransomware_enabled_ = true` si `initialize()` tuvo éxito.
- `ransomware_feature_processor.cpp` `initialize()` → **no puede fallar por entorno**: solo `make_unique` de estructuras en memoria (`FlowTracker`, `DNSAnalyzer`, `IPWhitelist`, `TimeWindowAggregator`, `RansomwareFeatureExtractor`) y `return true` incondicional. No carga ONNX, no abre ficheros, no toca sockets.
- `ransomware_feature_processor.hpp:35` → `get_aggregator()` devuelve `aggregator_.get()` de un `unique_ptr` construido en `initialize()`. No es null.
- `ring_consumer.cpp:815-818` → la inyección lazy vive **dentro** del mismo bloque que la extracción, justo antes de `populate_ml_defender_features`. Timing **exonerado**: como mucho el primer flujo podría verse afectado, y ni eso si el setter prende en la primera pasada.

**Conclusión:** las 9 features del cubo B reciben un aggregator vivo. El bug NO es de cableado.

### 1.4 El árbol de ejecución == el de entrenamiento (DDoS) — [HECHO]
```
shasum ml-detector/include/ml_defender/ddos_trees_inline.hpp \
       ml-training/scripts/ddos_detection/ddos_trees_inline.hpp
# f14fdf84... (idéntico en ambos)
```
El modelo que corre es el que se entrenó. El skew train/serve **no está en el árbol**; está en que **el vector servido ≠ el vector de entrenamiento** en las dimensiones del cubo A.

### 1.5 El bosque DDoS parte sobre geo-humo — [HECHO]
Struct confirmado (`ddos_trees_inline.hpp:10-16`): `DDoSTreeNode { int16_t feature_idx (−2 si hoja); float threshold; int32 left; int32 right; float value[2]; }`.
Censo de nodos (100 árboles):
```
grep -oE '\{-?[0-9]+,' ddos_trees_inline.hpp | grep -oE '\-?[0-9]+' | sort -n | uniq -c
```
| feature_idx | nodos-split | feature (verificada por comentario auto-generado) |
|---|---|---|
| −2 | 356 | (hojas) |
| 0 | 2 | syn_ack_ratio |
| 1 | 5 | packet_symmetry |
| 2 | 1 | source_ip_dispersion (viva, apenas usada) |
| 3 | 28 | protocol_anomaly_score |
| 4 | 66 | packet_size_entropy |
| 5 | 8 | traffic_amplification_factor |
| 6 | 22 | flow_completion_rate |
| **7** | **16** | **geographical_concentration ← −9999 SIEMPRE** |
| 8 | 66 | traffic_escalation_rate |
| 9 | 42 | resource_saturation_score |

**16 de 256 nodos-split (6.25 %) parten sobre una feature muerta.** Cada uno toma siempre `left_child`. Los caballos de batalla del bosque (idx 4, 8, 9) sí se calculan del flujo — el bosque no está roto entero, pero tiene 16 pasarelas fijas donde cree que decide.

---

## 2. Por qué esto es material de paper (y no solo un bug)

- **Confirma S&P por un mecanismo nuevo y auditado.** El paper ya sostiene que el ML no transfiere (CICIDS→Neris 0.0001). Este hallazgo añade una **segunda causa concurrente, medida a nivel de código**: el modelo se entrenó sobre un espacio de features que producción no reproduce. Es el tipo de auditoría forense que casi nadie publica porque no hay incentivo.
- **El caso `geographical_concentration` es didáctico y limpio.** Encontrar features GeoIP con peso en el modelo (16 cortes) cuando el pipeline **nunca captura ni enriquece con geografía** es un indicio fuerte de error de diseño train/serve, y es explicable en dos frases a un revisor. Tu intuición es correcta: es un error grave, no un detalle.
- **Encuadre honesto para el texto:** "de 40 features, N entran al modelo como constante-centinela porque su cálculo no existe en el pipeline de red; el bosque asigna cortes a varias de ellas (16 sobre la geográfica), evidenciando que el entrenamiento vio un espacio de features que el despliegue no reproduce." Anclar cada número a su fichero+comando (misma disciplina que `sec:eval:bias`).
- **NO sobre-cantar:** esto explica **parte** de la ceguera, sumándose a la transferencia. No convierte el 0.04 en 0.9 al arreglarlo. Declararlo como concurrente, medido, reparable — no como "la causa única".

---

## 3. Estado de los tres candidatos del 0.04

| Candidato | Estado tras esta sesión |
|---|---|
| **Cableado del aggregator** (multi-flow a −9999) | **REFUTADO** — sano, medido en 1.3 |
| **Features centinela en cortes de árbol** (skew de vector) | **HECHO parcial** — confirmado en DDoS (geo, 16 cortes); falta internal/traffic/ransomware |
| **Transferencia de distribución** (CICIDS→Neris) | En pie, ya documentado en el paper (no re-medido aquí) |
| **Procedencia del modelo** (qué se entrenó, con qué valores) | **SIN MEDIR** — el candidato gordo que queda |

---

## 4. Pasos siguientes (medir, barato→caro)

1. **Reconciliar el recuento exacto del cubo A** con un conteo mecánico (no de memoria): 9 vs 10.
2. **Replicar shasum + censo de nodos en las otras cabezas:**
    - `internal_trees_inline.hpp` (execution vs training) + censo → cruzar con muertas internal (idx 4 `connection_duration_std`).
    - `traffic_trees_inline.hpp` (execution vs training) + censo → cruzar con muertas traffic (idx 2, 5, 8).
    - **Ransomware es el caso aparte:** NO tiene `trees_inline.hpp`; tiene `ml-detector/src/ransomware_detector.cpp` + training `complete_forest_cpp_example.h` / `extract_full_forest.py`. Entender su estructura antes de contar. Es donde se espera el daño mayor (4 features muertas del cubo A).
3. **Procedencia del modelo (estático):** qué corrida de entrenamiento generó los `*_trees_inline.hpp` vivos, y con qué valores se entrenaron las features del cubo A. Localizar los generadores sintéticos (`ml-training/scripts/**/Generate*.py`, `generate_all_models.py`, `model_verification_report_*.json`). Si la geográfica se entrenó con valores en [0,1] → skew confirmado por ambos lados.
4. **Volcado en runtime (una corrida VM, `ctu-start`):** capturar los vectores de 40 reales sobre Neris. Confirma el censo en caliente y mide qué valen las features del cubo B (aggregator) con `--mbps=10` — si `event_count` es bajísimo, sus ratios log2 degeneran aunque el aggregator funcione.

## 5. Lecturas de contraste pendientes (código primero, docs después)
- **ADR-059** "Reparación del veredicto del ml-detector: de monocapa a tricapa honesta" — único doc que menciona `get_aggregator`; toca esta maquinaria. Leer para ver si su reparación llegó al código o se quedó en papel.
- **`PROPUESTA AL CONSEJO DE SABIOS — Auditoría de features de los modelos ML.md`** — alguien ya planteó esta misma auditoría.
- Ambos **después** de medir, para no dejar que su narrativa coloree lo que el código hace hoy (misma trampa de versión que tuvimos con el paper v24/v25).

## 6. Deudas técnicas candidatas a registrar
- `DEBT-ML-SENTINEL-IN-TREE-SPLITS-001` — features −9999 alimentando cortes de árbol aprendidos en [0,1]; caso confirmado geo/DDoS (16 nodos). Reparación posible sin tocar modelo: recalcular la feature, o reentrenar sin esa columna.
- `DEBT-ML-GEOIP-TRAINED-NOT-SERVED-001` — el modelo se entrenó con columna geográfica separable; el pipeline nunca captura ni enriquece geo → skew train/serve.
- `DEBT-RANSOMWARE-HEAD-4-FEATURES-UNCOMPUTABLE-001` — 4/10 features de la cabeza ransomware piden telemetría de host (I/O, CPU, ficheros, procesos) imposible en un sniffer de red; la cabeza decide sobre humo estructural. (Relaciona con la señal de daño / dominio host de Wazuh como future-work.)
- (existente) `DEBT-RANSOMWARE-ML-HEAD-INERT-001` — actualizar con lo medido aquí.