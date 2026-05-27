## 📋 CONSEJO DE SABIOS — DAY 120

---

### ¿Qué hemos hecho hoy?

**Infraestructura (3 DEBTs bloqueantes cerrados):**

`DEBT-PUBKEY-RUNTIME-001` — La pubkey Ed25519 de verificación de plugins ya no está hardcodeada en `plugin-loader/CMakeLists.txt`. Un script `tools/extract-pubkey-hex.sh` la lee de `/etc/ml-defender/plugins/plugin_signing.pk` en cmake-time via `execute_process()`. `make sync-pubkey` marcado DEPRECATED.

`DEBT-BOOTSTRAP-001` — `make bootstrap` implementado: encadena 8 pasos canónicos post `vagrant up` en un único comando. Incluye `make post-up-verify` y `make check-system-deps` (DEBT-INFRA-VERIFY-001/002). Regla permanente establecida: lógica compleja con quoting anidado → script en `tools/`, nunca inline en Makefile.

**Idempotencia validada 2/2** — `vagrant destroy × 2` verde ambas iteraciones.

**ADR-026 XGBoost Track 1 — 5 pasos completados:**

- **PASO 4a** — Feature set documentado: 23 features LEVEL1, mismo que RF. Fuente canónica `feature_extractor.cpp`. Dataset: CIC-IDS-2017 (no CTU-13 como se creía).
- **PASO 4b** — `docs/xgboost/plugin-contract.md`: contrato `ctx->payload` float32[23], invariantes fail-closed, flujo de invocación.
- **PASO 4c** — `scripts/train_xgboost_baseline.py` entrenado sobre 2.83M flows CIC-IDS-2017: **F1=0.9978** (RF=0.9968, +0.001), **Precision=0.9973** (RF=0.9944, +0.003), ROC-AUC=1.0000. Gates pasados.
- **PASO 4d** — `make sign-models` + `tools/sign-model.sh`: modelo `.ubj` firmado con Ed25519 (mismo esquema ADR-025).
- **PASO 4e** — `TEST-INTEG-XGBOOST-1 PASSED`: inferencia real implementada en `plugin_process_message`. CASO A BENIGN score=0.000706 ∈ [0,1], CASO B ATTACK score=0.003414 ∈ [0,1].

**Descubrimiento importante:** Los modelos ransomware y DDoS del pipeline fueron entrenados con **datos sintéticos generados por DeepSeek** (no datasets académicos — los académicos daban modelos sesgados). Los datasets están localizados: `ddos_detection_dataset.json` (27MB) y `data/*_guaranteed.csv` (ransomware). DAY 121 entrenaremos las versiones XGBoost de ambos.

---

### ¿Qué haremos mañana? (DAY 121)

1. **PASO 0 tercera iteración** — `vagrant destroy + make bootstrap` para certificar idempotencia definitiva antes del merge.
2. **Verificar DEBT-SEED** — ¿está la seed aún hardcodeada en algún CMakeLists.txt? Si sí, mismo patrón que pubkey: script runtime que lee `/etc/ml-defender/<component>/seed.bin`, lo inyecta en cmake-time, y el fichero nunca viaja en plaintext por el filesystem.
3. **XGBoost DDoS** — `scripts/ddos_detection/train_xgboost_ddos.py` con `ddos_detection_dataset.json`.
4. **XGBoost Ransomware** — `scripts/ransomware/train_xgboost_ransomware.py` con los 3 CSVs sintéticos.
5. **Extender `make sign-models`** para los 3 modelos.
6. **Tabla comparativa RF vs XGBoost** para `§4` del paper — latencia + F1 + Precision para los 3 detectores.

---

### Preguntas al Consejo

**P1 — Scores XGBoost en TEST-INTEG-XGBOOST-1:**
BENIGN=0.000706, ATTACK=0.003414. Ambos scores son muy bajos — el modelo clasifica todo como BENIGN con alta confianza. Los features sintéticos del test (valores extremos para ATTACK) no representan la distribución de CIC-IDS-2017. ¿Es correcto ignorar el valor absoluto del score y validar únicamente que esté en [0,1] y no sea NaN? ¿O deberíamos construir features de test tomadas directamente del CSV de entrenamiento para verificar que el modelo clasifica correctamente?

**P2 — Integridad científica del paper:**
El RF level1 fue entrenado con CIC-IDS-2017 real. Los detectores ransomware/DDoS/internal fueron entrenados con datos sintéticos DeepSeek. ¿Debemos presentar ambas familias por separado en §4, con subsecciones explícitas "real dataset" vs "synthetic dataset"? ¿O hay riesgo de que los revisores rechacen la contribución del XGBoost sintético por no tener comparativa externa?

**P3 — Entrenamiento in-situ (idea DAY 120):**
El modelo XGBoost es ligero (~2MB). Alonso propone explorar en el futuro entrenamiento incremental in-situ en la VM (hospital/municipio) con tráfico real local, exportar el modelo reentrenado comprimido, y distribuirlo via BitTorrent a la red aRGus. ¿Es viable con XGBoost incremental (`xgb.train` con `xgb_model` para warm start)? ¿Qué gates de calidad mínimos exigiría el Consejo antes de aceptar un modelo distribuido por este canal?

**P4 — DEBT-SEED:**
La seed ChaCha20 se genera en provisioning y se copia a 6 componentes. ¿Está hardcodeada en algún CMakeLists.txt igual que la pubkey? Si es así, ¿el mismo patrón `execute_process()` + script runtime es suficiente, o la seed requiere un mecanismo más robusto (memoria protegida, borrado explícito post-uso)?

---

*"Via Appia Quality — un escudo, nunca una espada."*
*DAY 120 — 17 Abril 2026*

---

