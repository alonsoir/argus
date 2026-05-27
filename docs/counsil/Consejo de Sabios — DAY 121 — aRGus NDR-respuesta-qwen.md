# 🏛️ CONSEJO DE SABIOS — REVISIÓN DAY 121
*Feedback riguroso, directo y centrado en la integridad científica y operacional del pipeline*

---

## 🎯 Reconocimiento Inicial

**Ejecución técnica impecable en DAY 121.** Habéis resuelto una dependencia circular crítica, validado idempotencia ×3, auditado la seed en runtime, y actualizado los tests con flujos reales de CIC-IDS-2017. La corrección de outliers mediante pre-validación en Python demuestra madurez en ML engineering.

> *"La honestidad científica no es un lujo. Es el único camino hacia un sistema que no engaña a sus operadores."*

Sin embargo, **DEBT-PRECISION-GATE-001 es un muro necesario**. No es un fallo de implementación; es un recordatorio de que los gates existen para evitar que el ruido se disfrace de detección.

---

## ❓ Respuestas a Preguntas — Formato Solicitado

### Q1 — Threshold calibration vs re-entrenamiento: ¿riesgo de data snooping?

**Veredicto:** **RE-ENTRENAR + calibrar umbral SOLO en conjunto de validación. NUNCA en test set.**

**Justificación:** Calibrar el threshold sobre el mismo test set que se usará para reportar métricas en §4.1 es *data snooping* explícito. Infla la Precision artificialmente y invalida la validez científica del paper. La metodología correcta exige: `Train` (ajuste de pesos) → `Validation` (calibración de umbral) → `Test` (reporte final, intocable).

**Riesgo si se ignora:** Rechazo por reviewers, modelo desplegado con confianza inflada, y métricas irreproducibles en tráfico real.

**Código verificable (split estricto sin leakage):**
```python
from sklearn.metrics import precision_recall_curve
import numpy as np

# 1. Split temporal puro (NO shuffle)
df_train = pd.read_csv("Tuesday-WorkingHours.csv")
df_test  = pd.read_csv("Wednesday-WorkingHours.csv")  # Held-out real

X_train, y_train = extract_features(df_train)
X_test,  y_test  = extract_features(df_test)

# 2. Calibrar umbral SOLO en train/validation (cross-val interno o 20% de train)
probas = model.predict_proba(X_train)[:, 1]
precision, recall, thresholds = precision_recall_curve(y_train, probas)

# 3. Elegir threshold donde Precision >= 0.99 y Recall no colapse
valid_mask = precision >= 0.99
if not any(valid_mask):
    raise ValueError("No threshold achieves Precision >= 0.99 on validation")
optimal_threshold = thresholds[valid_mask.argmax()]

# 4. Evaluar SOLO EN TEST con ese threshold fijo
y_pred_test = (model.predict_proba(X_test)[:, 1] >= optimal_threshold).astype(int)
print(f"TEST Precision: {precision_score(y_test, y_pred_test):.4f}")
```

---

### Q2 — ¿Es aceptable 0.9875 de Precision (1.25% FPR) en hospital?

**Veredicto:** **INACEPTABLE operacionalmente. Mantener gate ≥0.99. No negociar.**

**Justificación:** 1.25% de FPR en 10.000 flows/hora = ~125 falsas alarmas/hora. En entornos con equipos de seguridad reducidos (1-2 personas), esto genera *alert fatigue* inmediata. El NDR pasa de ser un escudo a un generador de ruido que se silencia manualmente. El gate médico no es arbitrario; es un límite de viabilidad operativa derivado de estándares SOC reales.

**Riesgo si se ignora:** Despliegue que degrada la postura de seguridad, operadores desactivando el NDR, y pérdida de credibilidad académica y comercial.

**Acción:** Si el modelo actual no alcanza ≥0.99 en validación independiente, no se merge. Documentar el gap en §4.1 como *"Current baseline requires additional feature engineering/data augmentation to meet clinical SOC thresholds"*, pero **no bajar el listón**.

---

### Q3 — Integridad científica: ¿usar día distinto como held-out test?

**Veredicto:** **OBLIGATORIO. Split temporal por día es estándar en literatura IDS. El merge se retrasa hasta validación en día independiente.**

**Justificación:** CIC-IDS-2017 tiene correlación temporal masiva: IPs, sesiones, campañas de ataque y configuraciones de red persisten por días. Un random split filtra información del futuro al entrenamiento, inflando métricas. La comunidad IDS rechaza papers que no usan day-based splits. Separar train/test por día fortalece el paper, aunque retrase el merge.

**Riesgo si se ignora:** Paper vulnerable a críticas metodológicas, métricas no generalizables, y posible rechazo en revisión por pares.

**Protocolo de evaluación:**
- `Train + Validation`: Tuesday + Wednesday
- `Test`: Thursday + Friday
- Reportar métricas **exclusivamente** sobre Thursday+Friday.
- Si Precision < 0.99 → iterar hiperparámetros/features, NO ajustar umbral post-hoc.

---

### Q4 — Deuda RF level1: ¿recuperar pkl o descartar comparación?

**Veredicto:** **NO recuperar. Documentar RF como baseline excluido por overfitting.**

**Justificación:** El RF alcanzó F1=1.0 sin split, lo que indica sobreajuste a patrones específicos del dataset. Comparar un modelo sobreajustado con un XGBoost validado bajo split temporal es metodológicamente deshonesto y resta rigor a §4.1. La comparación pierde valor científico si el baseline no cumple los mismos criterios de evaluación.

**Riesgo si se ignora:** Tabla comparativa asimétrica, reviewers cuestionando la validez del estudio, y dilución del mensaje principal (XGBoost como reemplazo validado).

**Acción:** Añadir en §4.1:
> *"Random Forest baseline excluded from final comparison due to overfitting on unsplit data (F1=1.0). XGBoost evaluated under strict temporal day-split to ensure generalizability. Latency comparison retained for architectural context only."*

---

## 📋 Plan de Acción DAY 122 (Concreto y Verificable)

```markdown
1. Implementar split temporal: Train=Tue+Wed, Test=Thu+Fri
2. Calibrar threshold en 20% de train (validación), NO en test
3. Validar Precision ≥ 0.99 y Recall ≥ 0.85 en Thursday+Friday
4. Si no pasa: ajustar `scale_pos_weight`, `min_child_weight`, o añadir feature scaling consistente
5. Actualizar docs/xgboost/comparison-table.md con métricas de día independiente
6. Ejecutar `make test-all` + `make plugin-integ-test` con modelo nuevo
7. Solo si gate pasa → solicitar revisión de merge al Consejo
```

**Código de validación rápida para CI:**
```bash
#!/bin/bash # scripts/validate_precision_gate.sh
set -euo pipefail
PRECISION=$(python3 scripts/evaluate_temporal_split.py --mode precision)
if (( $(echo "$PRECISION >= 0.99" | bc -l) )); then
  echo "✅ Precision gate passed: $PRECISION"
else
  echo "❌ Precision gate failed: $PRECISION < 0.99"
  exit 1
fi
```

---

## 🏁 Palabras Finales

Alonso:

Habéis hecho un trabajo técnico excepcional. Pero la excelencia no se mide por lo rápido que se avanza, sino por lo que se resiste a romper cuando los datos reales golpean. DEBT-PRECISION-GATE-001 no es un obstáculo; es el **sistema inmune del proyecto** diciendo: *"Aún no es hora"*.

No bajéis el gate. No calibréis sobre el test set. No recuperéis un RF sobreajustado. Dividid por días. Validad con rigor. Documentad las limitaciones con transparencia. Eso es lo que convierte un repositorio académico en un sistema que protege vidas sin engañar a sus operadores.

> *"La ciencia no premia la velocidad. Premia la verificabilidad. Y la seguridad premia la paciencia."*

Proceded con el split temporal. El Consejo revisará los resultados de Thursday+Friday con el mismo rigor con el que evaluamos cada línea de este pipeline.

*Via Appia Quality · Un escudo, nunca una espada.*

**— Consejo de Sabios, DAY 121** 🛡️