# PROMPT DE CONTINUIDAD — DAY 220

> Rama: `fix/verdict-multihead-honest`. Escrito al cierre de DAY 219 (15-jul-2026).
> Fuente: sólo lo verificado en la sesión de DAY 219. Lo no probado se marca.
> Referencia completa: `docs/debt/DAY219_FINDINGS.md` (536 líneas).

---

## LO PRIMERO AL ABRIR

Verificar nombre del findings de ayer: se guardó y puede haber quedado como
`DAY291` (transposición de 219). Comprobar:
```
ls docs/debt/DAY219*.md docs/debt/DAY291*.md
```
Si está traspuesto, renombrar a `DAY219_FINDINGS.md`. Es desorden SOURCE-TREE.

---

## LA ÚNICA ACCIÓN QUE DECIDE EL GO/NO-GO (P0)

**`make eval-level1-holdout`** — `DEBT-L1-NO-REPRODUCIBLE-HOLDOUT-001`.

Correr el modelo VIVO `level1_attack_detector.onnx` sobre un pcap que NO vio en
entrenamiento (Wednesday sirve, md5 `bf0dd7e9d991987df4e13ea58a1b409c`),
alimentándolo por el PIPELINE VIVO (`extract_level1_features` del ml-detector,
NO un script Python paralelo), y reportar el recall.

Por qué es lo único que importa de L1: su métrica actual (accuracy 0.9987,
recall 0.9992 en `level1_attack_detector_metadata.json`) es IN-SAMPLE. El único
holdout out-of-sample del directorio (`wednesday_eval_report.json`, recall
**2,4%**) es casi con certeza la AUTOPSIA DEL XGBOOST descartado (threshold
0.821 = el del XGBoost; el ONNX vivo usa 0.65), NO del ONNX. Y su generador NO
existe en el repo → no es reproducible.

Resultado esperado:
- recall bueno → L1 sano, número honesto para el paper, FEDER con la cabeza alta.
- recall malo → problema real, pero conocido con 2 semanas de margen.

Es el `make test-arxiv-paper` aplicado a la métrica que más importa.

---

## ESTADO PROBADO DE L1 (no re-investigar, está verificado)

- El consumidor de L1 es `extract_level1_features` en el **ml-detector**
  (`ml-detector/src/feature_extractor.cpp`), VIVO en `zmq_handler.cpp:498→516→722`.
  NO es el `FeatureExtractor` del sniffer (ese nació muerto, ver abajo).
- Produce 23 features, **verificadas 23/23** en orden y semántica contra el
  oráculo `level1_attack_detector_metadata.json`.
- Features [1]/[9] y [12]/[18] leen el mismo campo A PROPÓSITO (redundancia
  legítima de CICIDS). NO son bug. La sospecha DAY 217 de "5 rotas" era 2.
- 2 features degradadas reales → `DEBT-L1-FEATURES-PLACEHOLDER-001` (P2, post-FEDER):
    - [8] `act_data_pkt_fwd`: aproximada con `total_forward_packets()` (incluye ACKs).
    - [14] `Init_Win_bytes_forward`: hardcode `0.0f`.
    - Ningún campo existe en `protobuf/network_security.proto`. Cerrarlas cruza
      sniffer+proto+detector (kernel-space). Post-FEDER.
- Escalado: `DEBT-CONFIG-SCALING-LIES-001` (P1) **MITIGADO (A)**. El config
  mentía (`requires_scaling: true` + `scaler.json` vacío + ningún código escala).
  Corregido a `false`/`""`. El modelo se entrenó SIN escalar; servir crudo es
  CORRECTO. NO implementar escalado.
- Threshold vivo: `level1_attack: 0.65` (`ml_detector_config.json:148`), propio
  del ONNX. XGBoost (0.821) desconectado. Sin cruce de modelos.

---

## SNIFFER — CERRADO Y CONFIRMADO AYER

- `DEBT-FLOWSTATS-COPY-AMPUTATED-001` (P0) **CERRADA** RED `6166982f` → GREEN
  `fc292bc8`. `ctest 17/18`. `get_flow_stats_copy`: 40 líneas a mano → 1 (copia
  el compilador). La clase de defecto ya no es EXPRESABLE. `time_windows`:
  `unique_ptr` → por valor.
- `DEBT-FEATURE-EXTRACTOR-DEAD-CODE-001` (P0, CONFIRMADA): el `FeatureExtractor`
  del sniffer (84 features) NACIÓ MUERTO — nunca se llamó en producción en
  ningún commit, pero SE COMPILA Y ENVÍA (`CMakeLists.txt:281`, `SNIFFER_SOURCES`).
  Se puede BORRAR, no revivir. Fósil: `.fase1/.fase2` (10-oct-2025).

---

## DEUDAS NUEVAS DE DAY 219 (registradas, no cerradas)

| Deuda | P | Acción |
|---|---|---|
| `L1-NO-REPRODUCIBLE-HOLDOUT-001` | P0 | `make eval-level1-holdout` (arriba) |
| `CONFIG-SCALING-LIES-001` | P1 | MITIGADA (A). Verificar que el config quedó bien. |
| `L1-FEATURES-PLACEHOLDER-001` | P2 | [8],[14]. Post-FEDER, extender proto. |
| `MODEL-DIR-XGBOOST-FOSSIL-001` | P2 | Mover/prefijar `xgboost_*` fuera de `production/`. |

`SOURCE-TREE-BACKUP-FILES-001` subió P2→P1 (se compilaba contra 2 declaraciones
de la misma clase). Las 7 deudas de DAY 218 siguen abiertas.

---

## ALCANCE — LO QUE NO SE AUDITÓ

Ayer SÓLO se auditó **level1**. **level2 (DDoS, ransomware) y level3 (internal,
web) NO fueron auditados.** El silencio NO es veredicto. NO extrapolar "L1 tiene
X" a "todos los modelos rotos" — eso sería votar, no medir.

Auditar level2/3 es trabajo pendiente candidato a DAY 220+ SI el eval de L1 sale
bien. Si el eval de L1 sale mal, L1 tiene prioridad absoluta.

---

## REGLAS PERMANENTES (no violar)

- `git add` EXPLÍCITO del fichero. NUNCA `git add -u` NI `git commit -a` en esta
  rama (arrastraría `zmq_handler` instrumentado de DAY 216).
- Sin commitear a propósito: `ml-detector/src/zmq_handler.cpp` (instrumentación,
  salvada en `docs/day216_instrumentation.patch`), `commit-message.txt`.
- STASH a NO perder: `stash@{0}: commit2-noisy-or WIP` (header + tests válidos).
- Verificar la RUTA antes de concluir sobre el contenido: en zsh un glob sin
  match ABORTA el comando (`no matches found`) y parece "no existe el campo"
  cuando es "no existe el dir". El proto está en `protobuf/`, NO `common/proto/`.
- Un grep vacío puede significar "no medí", no "medí cero". Distinguir.
- Métrica in-sample ≠ rendimiento. El número honesto es el holdout.
- El patrón de falsa evidencia va por **21** casos (DAY 218 cerró en 15, NO 16 —
  el "1–16" del prompt anterior era error heredado). No re-arrancar en 17.
- Makefile = única fuente de verdad. EMECAS antes de merge. Builds vía `make`
  desde host macOS. Vagrant siempre con `-c`. macOS: nunca `sed -i` sin `-e ''`.

---

## DECISIONES QUE SOBREVIVEN

- Commit 2 (noisy-OR) APARCADO, no cancelado. NO suprime FP (monótono, como max).
- Claim del `max()` aritméticamente imposible (`max(a,b)≥a`). NO tocar el LaTeX aún.
- `ddos`/`ransomware` a `reliability = 0.0`.
- El `2.517` sigue SIN PROCEDENCIA (DAY 217). "Revalidado" ≠ procedencia probada.
- MITRE va DESPUÉS del extractor. Un commit, un cambio, una razón.
- Calidad innegociable sobre la fecha.

---

## FEDER

Go/no-go ~1 agosto 2026. Deadline 22 septiembre. La pregunta abierta de L1
(eval holdout) es la que toca la claim del paper. Todo lo demás de L1 es deuda
acotada o cerrado. Un escudo, nunca una espada.