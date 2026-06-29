## 🏛️ Dictamen del Consejo de Sabios — DAY 121

*Hemos examinado el informe. El progreso es notable, pero la **Precision=0.9875** que bloquea el merge es un problema real, no administrativo. A continuación, nuestro análisis y respuestas, con la dureza que la situación exige.*

---

### ✅ Lo que está bien (y debe continuar)

1. **Bug de dependencia circular resuelto** – La corrección en `provision.sh` (generar keypair antes de compilar plugin-loader) era crítica. La tercera validación de idempotencia da confianza.

2. **DEBT-SEED-AUDIT-001** – Buen uso de `mlock()` + `explicit_bzero()`. Es el estándar para secretos en memoria.

3. **Test real de XGBoost con CIC-IDS-2017** – Los scores para BENIGN (<0.001) y ATTACK (>0.999) son excelentes. La prevalidación con Python para evitar outliers fue una acción inteligente.

4. **Modelos DDoS y Ransomware** – Aunque sintéticos, la mejora de latencia (20x y 6x) es relevante. La tabla comparativa y la separación en §4.2 del paper son correctas.

5. **Honestidad sobre la Precision baja** – Abrir `DEBT-PRECISION-GATE-001` y bloquear el merge es lo profesional. No ocultar métricas malas.

---

### ❌ Lo que está mal o es insuficiente

#### 1. El test de integridad del modelo XGBoost no es completo

El test `TEST-INTEG-XGBOOST-1` ahora usa 3 BENIGN y 3 ATTACK reales. Pero **no verifica que el modelo no esté sobreajustado a esos 6 puntos**. Un modelo podría memorizarlos y fallar en otros. Exigimos:

- **Test con una muestra aleatoria de al menos 100 flows** (50 benign, 50 attack) extraídos de un día diferente al de entrenamiento (ej: Wednesday). Esto debe ejecutarse en CI y fallar si alguna métrica baja del gate.
- **Código sugerido** (a añadir en `tests/xgboost_integration_test.cpp`):
  ```cpp
  TEST(XGBoostPlugin, RandomSampleFromWednesday) {
      // Cargar CSV de Wednesday desde un fixture
      // Para cada flow, predecir y comparar con etiqueta real
      // Calcular Precision, Recall, F1 sobre la muestra
      ASSERT_GE(precision, 0.99);
  }
  ```

#### 2. La calibración del threshold no puede hacerse sobre el mismo test set

Esto es **data snooping** y arruina la validez científica. Si ajustas el threshold para que Precision≥0.99 sobre el conjunto de test actual, ese conjunto deja de ser independiente. El umbral debe calibrarse sobre un **validation set** (por ejemplo, tomar parte de Tuesday como validación, otra como test). O mejor: usar un día completamente distinto (Wednesday) para test.

**Exigencia:** Antes de cualquier ajuste, dividir los datos disponibles en:
- Train: Tuesday-WorkingHours (sin solapamiento)
- Validation: parte de Tuesday (ej: últimas 2 horas) o un día diferente
- Test: Wednesday (nunca visto durante entrenamiento ni calibración)

---

### Respuestas a las preguntas del Consejo

#### Q1 — Threshold calibration vs re-entrenamiento con más datos

**Respuesta:** **Ninguna de las dos sobre el mismo test set.** El procedimiento correcto es:

1. **Separar un validation set** (ej: 20% de Tuesday, estratificado por clase).
2. **Calibrar threshold** sobre validation para maximizar Precision con Recall ≥ 0.95 (por ejemplo). Usar `sklearn.metrics.precision_recall_curve`.
3. **Evaluar en un test set independiente** (ej: Wednesday completo).
4. **Si aún no alcanza Precision≥0.99**, entonces **re-entrenar con más datos** (todos los días excepto Wednesday) y repetir la calibración.

**Código de calibración (Python):**
```python
from sklearn.metrics import precision_recall_curve
precisions, recalls, thresholds = precision_recall_curve(y_val, y_scores_val)
# Encontrar threshold donde precision >= 0.99 y recall máximo
idx = np.where(precisions >= 0.99)[0]
best_threshold = thresholds[idx[np.argmax(recalls[idx])]]
```

**Riesgo de data snooping:** Sí, si calibras sobre el mismo test set. Por eso necesitas validation set separado.

**Veredicto:** ✅ Rechazamos calibrar sobre el test actual. Exigimos validation set independiente.

---

#### Q2 — Representatividad del gap Precision: 125 falsos positivos/hora

**Análisis cuantitativo:**
- 10.000 flows/hora = 166 flows/minuto.
- 125 falsos positivos/hora = ~2 falsos positivos/minuto.
- En un hospital, cada falso positivo requiere investigación (un analista de seguridad revisa). 2 por minuto es insostenible. Si cada investigación lleva 1 minuto, se necesitarían 2 FTE solo para revisar falsos positivos.

**¿Es inaceptable?** Depende del contexto:
- Si el hospital tiene un SOC con 10 analistas, podría ser manejable (pero costoso).
- Si es un hospital pequeño sin personal de seguridad dedicado, es **completamente inaceptable**.

**Argumento para gate más flexible:** El paper podría mencionar que CIC-IDS-2017 es un dataset de laboratorio y que la precisión en producción real podría ser diferente. Pero **el gate de 0.99 se estableció en ADR-026 por consenso**, y cambiarlo ahora sería una traición a los principios de seguridad. El Consejo no acepta rebajar el gate.

**Veredicto:** ❌ No se flexibiliza el gate. Se resuelve el problema técnico (calibración, más datos, mejores features) o se descarta XGBoost para level1.

---

#### Q3 — Integridad científica del paper: ¿usar Wednesday como test set?

**Respuesta:** **Sí, absolutamente.** Entrenar con Tuesday y evaluar sobre Wednesday (o cualquier otro día) es la práctica estándar en detección de intrusiones para evitar fuga de temporales. El hecho de que hayas usado Tuesday para entrenar y también para test invalida las métricas reportadas.

**Acción obligatoria:**
- Re-entrenar el modelo con Tuesday (sin Wednesday).
- Evaluar en Wednesday completo.
- Reportar en el paper las métricas sobre Wednesday (test set independiente).
- Si la Precision baja aún más (posible), será un dato honesto. Podría argumentarse que la variabilidad entre días es real y que el modelo necesita más datos de entrenamiento.

**Impacto en el merge:** Si sobre Wednesday la Precision sigue siendo <0.99, **no se mergea**. Se debe iterar (más datos, calibración, etc.) hasta cumplir el gate.

**Veredicto:** ✅ Exigimos test set independiente (Wednesday) antes de cualquier decisión de merge.

---

#### Q4 — ¿Recuperar el RF level1 para la tabla comparativa?

**Respuesta:** **No.** Invertir tiempo en recuperar un pickle perdido de un modelo que ya sabes que es más lento (12 µs vs 1.3 µs) y que tiene F1 similar no aporta valor científico significativo. La tabla comparativa puede mostrar:

- **RF (level1):** No disponible para comparación directa; se asume rendimiento similar al reportado en trabajos previos (cita a algún paper). O simplemente omitirlo.
- **XGBoost (level1):** Latencia 1.31 µs, F1=0.9989, Precision=0.9875 (en Tuesday). Y luego en Wednesday (cuando lo tengas) se actualiza.

**Mejor aún:** Entrenar un nuevo RF con los mismos datos de Tuesday y medir su latencia y F1. Eso es trivial (unas pocas líneas en Python) y daría una comparación justa. Pero si no quieres, la omisión es aceptable siempre que expliques que XGBoost fue elegido por latencia.

**Veredicto:** ✅ No recuperar el pickle. Si acaso, entrenar RF nuevo para la comparación. No bloquea el merge.

---

## Resumen de acciones obligatorias para DAY 122

| Acción | Prioridad | Plazo |
|--------|-----------|-------|
| 1. Separar Tuesday en train/validation (80/20) y usar Wednesday como test | **Crítica** | DAY 122 |
| 2. Calibrar threshold sobre validation set (no sobre test) | **Crítica** | DAY 122 |
| 3. Evaluar XGBoost en Wednesday y reportar Precision, Recall, F1 | **Crítica** | DAY 122 |
| 4. Si Precision ≥ 0.99 en Wednesday → merge autorizado. Si no → re-entrenar con más días (Wednesday+Thursday+Friday) y repetir | **Crítica** | DAY 122-123 |
| 5. Añadir test aleatorio de 100 flows de Wednesday en `plugin-integ-test` | Alta | DAY 122 |
| 6. Documentar la metodología de calibración y separación de datos en `docs/xgboost/validation.md` | Media | DAY 122 |

---

## Veredicto final del Consejo

El trabajo de DAY 121 es sólido, pero el **error metodológico de usar el mismo dataset para entrenar y evaluar** invalida las métricas actuales. No se puede confiar en una Precision=0.9875 que no ha sido probada en datos no vistos.

**Decisión:**  
❌ **No se acepta el merge de `feature/adr026-xgboost` a `main` hasta que se demuestre Precision ≥ 0.99 en un test set independiente (Wednesday).**

Se autoriza a continuar con la investigación (threshold calibration, más datos, etc.) pero **no se etiquetará como `v0.5.0` ni se desplegará en producción hasta cumplir el gate**.

*La seguridad de los hospitales no admite atajos estadísticos.*

— **Consejo de Sabios, DAY 121**