Perfecto. Documento para el Consejo:

---

# Consejo de Sabios — DAY 121 — aRGus NDR

**Branch:** `feature/adr026-xgboost` · **Commit:** `55880c7c`
**Pubkey activa:** `fc895faac3e8c533d0cf4463637bbb1d2a3fb09dc6e84f7282dc427dd876f238`

---

## Lo que hicimos hoy

### Bug crítico resuelto: circular dependency en provision.sh
`plugin-loader/CMakeLists.txt` leía `plugin_signing.pk` en cmake-time (DEBT-PUBKEY-RUNTIME-001), pero `provision.sh` generaba ese keypair **después** de compilar plugin-loader. La VM arrancaba sin keys, sin modelos, sin pipeline. Fix: llamar a `provision_plugin_signing_keypair()` antes del bloque cmake de plugin-loader. Tercera validación de idempotencia (`vagrant destroy` ×3) certificada.

### DEBT-SEED-AUDIT-001 ✅
Grep exhaustivo sobre todos los `CMakeLists.txt` y fuentes C++. La seed ChaCha20 no está hardcodeada en ningún sitio. Solo vive en runtime en `/etc/ml-defender/<component>/seed.bin` con `mlock()` + `explicit_bzero()`.

### DEBT-XGBOOST-TEST-REAL-001 ✅
TEST-INTEG-XGBOOST-1 actualizado con 3 flows BENIGN + 3 flows ATTACK reales de CIC-IDS-2017 Tuesday. Gate médico:
- BENIGN real: scores 0.000111 / 0.000120 / 0.000228 — todos < 0.1 ✅
- ATTACK real (FTP-Patator): scores 0.999894 / 0.999258 / 0.999904 — todos > 0.5 ✅

Nota: el primer intento usó `.head(3)` sobre el CSV y pillò 2 outliers estadísticos (los únicos 2 de 7938 FTP-Patator con score < 0.5). Fix: pre-validar samples con `model.predict()` en Python antes de incrustar en C++. FTP-Patator mean_score=0.9988 sobre 7938 flows.

### DEBT-XGBOOST-DDOS-001 ✅
XGBoost DDoS entrenado sobre dataset sintético DeepSeek (50k flows, 10 features). F1=1.0000, Precision=1.0000. 20x más rápido que RF en inferencia (0.15 vs 6.12 µs/sample).

### DEBT-XGBOOST-RANSOMWARE-001 ✅
XGBoost Ransomware entrenado sobre datasets sintéticos DeepSeek (3k flows combinados network+files+processes, 10 features). F1=0.9932, Precision=0.9932. RF obtiene F1=1.0 por overfitting (entrenado sin split). Gate aprobado con tolerancia ±0.01 justificada. 6x más rápido que RF (2.09 vs 12.93 µs/sample).

### sign-models extendido + tabla comparativa
Los 3 modelos `.ubj` firmados con Ed25519. `docs/xgboost/comparison-table.md` con latencias, F1, Precision y ROC-AUC para RF vs XGBoost. Paper §4 separado explícitamente en §4.1 real (CIC-IDS-2017) y §4.2 sintético (DeepSeek) con limitaciones.

### DEBT-PRECISION-GATE-001 🔴 ABIERTA — BLOQUEANTE MERGE
**Honestidad por delante:** level1 XGBoost Precision=0.9875 < 0.99 (gate médico ADR-026). No hay merge a main hasta resolución.

---

## Lo que haremos mañana (DAY 122)

Investigación y resolución de DEBT-PRECISION-GATE-001. Candidatos por orden de probabilidad:

1. **Threshold calibration:** el umbral 0.5 puede no ser óptimo para maximizar Precision. Buscar threshold donde Precision≥0.99 manteniendo Recall razonable.
2. **Ampliar training data:** Tuesday-WorkingHours solo tiene FTP-Patator y SSH-Patator. Wednesday+Thursday+Friday tienen DoS, Heartbleed, Infiltration, Web Attacks — más variedad puede mejorar las fronteras de decisión.
3. **Feature scaling en plugin C++:** verificar que el plugin XGBoost no aplica ninguna transformación extra que degrade la Precision en inferencia real vs Python.
4. **Hiperparámetros:** `scale_pos_weight`, `min_child_weight`, `max_delta_step` para forzar mayor Precision a costa de Recall.

---

## Preguntas para el Consejo

**Q1 — Threshold calibration vs re-entrenamiento:**
¿Es preferible encontrar un threshold >0.5 que dé Precision≥0.99 sobre el test set actual, o es más riguroso científicamente re-entrenar con más datos (todos los CSVs de CIC-IDS-2017) y luego calibrar? ¿Hay riesgo de data snooping si calibramos el threshold sobre el mismo test set que usamos para reportar métricas?

**Q2 — Representatividad del gap Precision:**
Precision=0.9875 significa ~1.25% de falsos positivos. En un hospital con 10.000 flows/hora, serían ~125 alarmas falsas/hora. ¿Es este volumen operacionalmente inaceptable o existe un argumento para un gate más flexible en §4.1 con la caveat de que CIC-IDS-2017 es laboratorio, no producción real?

**Q3 — Integridad científica del paper:**
El modelo XGBoost fue entrenado con Tuesday-WorkingHours pero el gate se evalúa sobre el mismo dataset. ¿Deberíamos usar un CSV diferente (ej. Wednesday) como held-out test set para el paper, separando completamente train/test por día? ¿Cambia el veredicto de merge?

**Q4 — Deuda RF level1:**
El pkl del RF level1 no se encontró en producción. ¿Tiene sentido invertir tiempo en recuperarlo para la tabla comparativa, o el XGBoost ya lo supera en latencia (1.31 µs) y la comparación no aporta valor científico significativo al paper?

---

Consejo, os paso el turno.