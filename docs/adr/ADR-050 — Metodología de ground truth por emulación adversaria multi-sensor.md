# ADR-050 v2 — Consolidación DAY 194

**Qué es esto:** la pieza de consolidación que DAY 194 aporta a ADR-050
(*Ground Truth Manifest — metodología de emulación adversaria*). El cuerpo del ADR
(§1–§12, §14–§18) quedó afilado por el Consejo al final de DAY 193 y vive en tu V1.
Esta sesión solo tenía que cambiar **una** sección: el §13, la descripción del
detector de ransomware, que en V1 estaba marcada *pendiente de reescritura*. Aquí está
reescrita y verificada contra el código, más el registro de cambios v1→v2 y las
instrucciones de fusión.

> **Nota de método (coherencia con el propio ADR).** No reconstruyo §1–§12/§14 aquí
> porque no tengo su texto verbatim, solo fragmentos de memoria. El ADR-050 establece
> como regla que las afirmaciones de memoria de un modelo se verifican contra el
> fichero, no se confían por aserción (lección DeepSeek). Reconstruir esas secciones de
> memoria violaría esa regla. Por eso la fusión es **quirúrgica sobre tu V1**: se
> reemplaza el §13 y se anexan las deudas. Lo de abajo está verificado al 100 %; el
> resto de tu V1 no se toca.

---

## A · §13 reescrito — listo para reemplazar el §13 de la V1

```markdown
## 13 · El detector de ransomware: procedencia y mecánica (verificado DAY 194)

### 13.1 · Detector canónico

El detector de ransomware en la ruta de producción es un **RandomForest de 100
árboles** (3.764 nodos), embebido en tiempo de compilación como datos `constexpr`
en `ml-detector/src/forest_trees_inline.hpp`. No es un modelo cargado en runtime: es
parte del binario compilado.

La cadena de ejecución está verificada contra el código (DAY 194):

- `main.cpp:328` — instanciación: `make_shared<RansomwareDetector>()`.
- `zmq_handler.cpp:21` — inyección por constructor al handler.
- `zmq_handler.cpp:649` — construcción del struct `Features` de 10 campos.
- `zmq_handler.cpp:677` — decisión: `is_ransomware(config_.ml.thresholds.level2_ransomware)`.

El binario se autodescribe en el contrato protobuf en cada predicción
(`zmq_handler.cpp:669-671`): `model_name = "ransomware_detector_embedded_cpp20"`,
`model_version = "1.0.0"`, `model_type = RANDOM_FOREST_RANSOMWARE`. Esta
autodescripción es la fuente de procedencia: no es memoria, es lo que el binario
afirma de sí mismo.

### 13.2 · El XGBoost-45 es un experimento comparativo concluido

`DEBT-RANSOMWARE-TWO-DETECTORS-001` queda **resuelta**. El XGBoost de 45 features
existe en disco pero **no se carga** (grep de `xgboost`, `.ubj`, `plugin_init`,
`dlopen` sobre `main.cpp` y el handler: vacío). No es un detector divergente activo: es
un **experimento comparativo concluido** (RF-10 vs XGBoost-45), conservado por
trazabilidad — el proyecto casi no borra artefactos, lo cual es disciplina, no
descuido. El RF-10 resultó superior en el pcap relay contra CTU-13 Neris, y por eso es
el embebido en producción. Se reclasifica a `DEBT-MODEL-ORPHAN-XGBOOST-001` (gobernanza:
documentar el experimento, no retirar el dato).

> **Caveat de validez (DAY 122, recuperado DAY 194).** El XGBoost-45 se entrenó sobre
> **CIC-IDS-2017 real**, mientras que el RF-10 se entrenó sobre datos sintéticos. La
> comparación que corona al RF-10 cruza datasets distintos — la conclusión "RF-10 mejor"
> puede ser cierta, pero la evidencia tiene sesgo de datasets cruzados y no es un
> sustituto científicamente limpio para el paper. Para una comparación válida habría
> que entrenar ambos sobre el mismo dataset. Pendiente de criterio del Consejo (DAY 195):
> ¿se reporta la comparación con su caveat, o se omite del paper por no concluyente?

### 13.3 · Espacio de features (host-dominante)

Diez features, con su peso de importancia:

| # | Feature | Importancia |
|---|---|---|
| 0 | io_intensity | 24 % |
| 1 | entropy | **36 %** ⭐ |
| 2 | resource_usage | 25 % |
| 3 | network_activity | 8 % |
| 4 | file_operations | 2 % |
| 5 | process_anomaly | <1 % |
| 6 | temporal_pattern | <1 % |
| 7 | access_frequency | 2 % |
| 8 | data_volume | 1 % |
| 9 | behavior_consistency | 2 % |

El 85 % del peso está en señales **host** (entropy + resource_usage + io_intensity).
`network_activity` pesa 8 %. Es un modelo dominantemente de host con la red casi
decorativa.

### 13.4 · Mecánica del ensemble

Agregación por **soft-voting**: cada árbol desciende hasta hoja
(`feature_value <= threshold → izquierda`), acumula `value[1]` = P(ransomware) de la
hoja, y se promedia entre los 100 árboles. Es equivalente a `predict_proba` de
`sklearn.RandomForestClassifier`. **No es votación dura por mayoría de clase.**

### 13.5 · Umbral operativo

El umbral de bloqueo es **0,75**, definido en `ml_detector_config.json:150` y cargado
con `get_required<float>` (`config_loader.cpp:231`) — campo obligatorio, fail-closed
si falta. Gobierna por configuración, no por hardcode; el `0.5` interno del `class_id`
y el `0.75` por defecto del helper quedan ambos sobrescritos por el valor de config.

### 13.6 · Path de features y validación

`extract_level2_ransomware_features(nf)` produce un `vector<float>` de 10 desde
`NetworkFeatures`, con **guard de contrato** (`zmq_handler.cpp:635`:
`if (vec.size() != 10) throw`, fail-closed). El struct se rellena índice a índice con
el orden de `to_array()`. Path único verificado; no hay dualpath.

### 13.7 · Desajuste de dominio: CONFIRMADO (verificado DAY 194)

`DEBT-RANSOMWARE-FEATURE-SEMANTICS-001` (P1, pre-paper, **a Consejo DAY 195**).

Las 10 features con nombre de semántica **host** se derivan **todas** de
`NetworkFeatures` (`feature_extractor.cpp:272`). El extractor del sniffer (83 features)
es red pura: el sensor aRGus es arquitectónicamente incapaz de medir señal host. Mapa
verificado nombre→cálculo real:

| # | Feature (nombre) | Cálculo real | Veredicto |
|---|---|---|---|
| 0 | io_intensity | paquetes/duración | proxy de red |
| 1 | **entropy (36 %)** | **varianza de longitud de paquete / 1e5** | **proxy roto** |
| 2 | resource_usage | bytes/seg | proxy de red |
| 3 | network_activity | paquetes/seg | honesto |
| 4 | file_operations | ratio flags PSH | proxy débil |
| 5 | process_anomaly | ratio flags ACK | proxy ruido |
| 6 | temporal_pattern | desviación IAT | proxy de red |
| 7 | access_frequency | paquetes totales | colineal con [0] |
| 8 | data_volume | bytes totales | honesto |
| 9 | behavior_consistency | simetría fwd/bwd | proxy de red |

**El nudo es la feature [1].** Pesa el 36 % del modelo, se llama `entropy`, y calcula
varianza de longitud de paquete (el propio comentario lo admite: *"Usar packet length
variance como proxy de entropía"*). No tiene relación matemática con la entropía de
Shannon, que es **la** señal canónica del ransomware al cifrar. El modelo no mide
cifrado; mide dispersión de tamaños de paquete y lo nombra entropía.

**Dos escenarios, sin dirimir** (lo decide el script de entrenamiento, no este código):

- **Escenario A — coherente, mal nombrado.** Si el entrenamiento usó este mismo
  extractor (la columna `entropy` también fue varianza de paquete), entrenamiento e
  inferencia son consistentes. El F1 es válido *en el espacio de red*. El modelo
  detecta la **fase de red** del ransomware (C2, lateral), no el cifrado. El §13 debe
  renombrar honestamente: no es un detector de entropía.
- **Escenario B — desajuste de distribución.** Si el entrenamiento usó entropía de
  fichero real (RanSMAP host o sintético host con entropía verdadera), producción
  alimenta varianza de paquete → input fuera de distribución. **El F1 de entrenamiento
  es inválido como predictor de producción.** Exige re-entrenar o re-validar.

**Acción:** dirimir A vs B localizando el script de entrenamiento y la definición de la
columna `entropy`. Hasta entonces el §13 no puede afirmar "detector de ransomware
basado en entropía" en ningún caso. Conecta con `DEBT-WAZUH-COMMUNITYID-001`
(ADR-052): la entropía de fichero real solo puede venir de telemetría Wazuh, no del
cable.

### 13.8 · Validez del rendimiento

El F1 del RF se obtuvo con datos de entrenamiento sintéticos. Ese número **no** es el
resultado del paper. El resultado es la caída de rendimiento que produzca el
C2/cifrado emulado del laboratorio (ADR-050 §11, catálogo de ataques) contra este
modelo. Hasta ese experimento, todo F1 reportado es de entrenamiento, no de evaluación
adversaria.
```

---

## B · Registro de cambios v1 → v2

1. **§13 reescrito por completo** (era *pendiente de reescritura* en V1). Contenido en
   el bloque A de arriba.
2. **Deuda resuelta:** `DEBT-RANSOMWARE-TWO-DETECTORS-001` → cerrada a favor del
   RF-100 embebido. Anotar en §18 (deudas) como RESUELTA con fecha DAY 194.
3. **Deuda nueva (gobernanza):** `DEBT-MODEL-ORPHAN-XGBOOST-001` — XGBoost-45 entrenado
   sin ruta de carga; decidir si se retira, se documenta como reserva, o se cablea.
4. **Deuda nueva (P1, pre-paper):** `DEBT-RANSOMWARE-FEATURE-SEMANTICS-001` —
   desajuste de dominio host vs red en el extractor. Bloquea la afirmación del §13.
5. **Deudas descartadas (no proceden):** doble umbral (resuelto por config) y dualpath
   de features (path único verificado). No crear entrada para ninguna.
   5-bis. **`DEBT-RANSOMWARE-FEATURE-SEMANTICS-001` actualizada a CONFIRMADA**: el
   desajuste de dominio ya no es hipótesis, es hecho verificado (§13.7). Pendiente solo
   dirimir A (renombrar) vs B (re-entrenar) con el script de entrenamiento. Va al
   Consejo en DAY 195 como hallazgo P1.
6. **Higiene:** retirar `zmq_handler.cpp.backup` de `src/`.

---

## C · Cómo fusionar (quirúrgico, sin deriva)

1. Abrir tu V1 real: `docs/adr/ADR-050-mitre-ground-truth-manifest.md`.
2. Localizar el §13 actual (el marcado *pendiente de reescritura*).
3. Reemplazarlo por el bloque A de este documento.
4. En §18 (pendientes y deudas), aplicar el registro de cambios B (resolver
   TWO-DETECTORS; añadir ORPHAN-XGBOOST y FEATURE-SEMANTICS).
5. Subir versión a **v2** en el encabezado y dejar el estado en **Propuesto** (sigue
   pendiente de la ronda de votos del Consejo sobre el ADR completo).
6. Verificar integridad antes de commit:
   `grep -n '^## ' docs/adr/ADR-050-*.md | sort | uniq -d` (regla
   `DEBT-DOCS-BACKLOG-DEDUP-001`).

> Si prefieres que la fusión la haga yo en la próxima sesión: pégame tu V1 real y hago
> el reemplazo del §13 + las deudas con `str_replace` quirúrgico sobre el texto exacto,
> sin reescribir nada que el Consejo ya afiló.

---

*Via Appia Quality. §13 verificado contra el fichero. El resto de la V1, intacto.*