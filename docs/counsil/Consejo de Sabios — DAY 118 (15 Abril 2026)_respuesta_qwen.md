# 🏛️ CONSEJO DE SABIOS — REVISIÓN DAY 118
*Feedback profesional, verificable y constructivo para ML Defender (aRGus NDR)*

---

## 🎯 Reconocimiento Inicial

**Excelente cierre de PHASE 3 y apertura disciplinada de PHASE 4.** Habéis demostrado madurez operativa: AppArmor 6/6 enforce sin denials, merge con `--no-ff` para trazabilidad científica, y un plugin XGBoost con esqueleto fail-closed desde el primer commit.

> *"La excelencia no es un acto, es un hábito. Y vosotros lo estáis construyendo commit a commit."*

---

## 🔍 Revisión Técnica de DAY 118

### ✅ Puntos Fuertes (verificables)
| Logro | Evidencia verificable | Por qué importa |
|-------|----------------------|-----------------|
| **AppArmor 6/6 enforce** | `aa-status \| grep -c "enforce"` → 6 | Hardening operativo validado en producción |
| **Merge --no-ff + tag anotado** | `git log --graph --oneline main..feature/phase3-hardening` | Trazabilidad científica para revisión por pares |
| **XGBoost 3.2.0 en Vagrant** | `vagrant ssh -c "python3 -c 'import xgboost; print(xgboost.__version__)'"` | Reproducibilidad garantizada desde cero |
| **Plugin skeleton fail-closed** | `plugins/xgboost/xgboost_plugin.cpp: plugin_init` con `std::terminate()` si `XGBoosterLoadModel` falla | Seguridad por diseño, no por esperanza |

### ⚠️ Puntos de Atención (con código verificable)
| Hallazgo | Riesgo | Mitigación propuesta + snippet verificable |
|----------|--------|-------------------------------------------|
| **`plugin_invoke` sin validación de input** | Si `MessageContext` llega malformado, `DMatrix` puede fallar silenciosamente | Añadir check explícito: <br>`if (ctx.features == nullptr \|\| ctx.feature_count == 0) { log_critical("empty features"); return -1; }` |
| **Modelo cargado en `plugin_init` sin cache** | Cada reload del plugin re-carga el modelo desde disco → latencia innecesaria | Implementar cache simple: <br>`static std::unique_ptr<BoosterHandle> cached_model; if (!cached_model) { XGBoosterLoadModel(...); }` |
| **`--break-system-packages` en pip** | Puede romper dependencias del sistema en Debian Bookworm | Usar virtualenv aislado: <br>`python3 -m venv /opt/ml-defender/xgboost-venv && source /opt/ml-defender/xgboost-venv/bin/activate && pip install xgboost==3.2.0` |

---

## ❓ Respuestas a Preguntas — Formato Solicitado

### Q1 — Feature set: ¿mismo que RF o recalcular?

**Veredicto:** **Opción A primero (mismo feature set), luego Opción B como experimento secundario**.

**Justificación:** Para que la comparativa RF vs XGBoost sea científicamente válida en el paper, el único variable debe ser el algoritmo, no el feature engineering. Usar el mismo feature set permite atribuir diferencias de métricas al modelo, no a los datos. Una vez validada la comparativa limpia, explorar feature selection de XGBoost como contribución adicional.

**Código verificable para Opción A:**
```python
# scripts/train_xgboost_baseline.py
import pandas as pd
from xgboost import XGBClassifier

# Cargar feature set idéntico al RF baseline
features_rf = pd.read_csv("data/ctu13_neris_features_rf.csv")  # columnas fijas
X_train = features_rf[RF_FEATURE_COLUMNS]  # lista explícita de 42 features
y_train = features_rf["label"]

# Entrenar con hiperparámetros conservadores
model = XGBClassifier(
    n_estimators=100,
    max_depth=6,
    learning_rate=0.1,
    random_state=42,  # reproducibilidad
    eval_metric="logloss"
)
model.fit(X_train, y_train)
model.save_model("models/xgboost_ctu13_same_features.json")
```

**Riesgo si se ignora:** Si XGBoost usa features distintas, cualquier mejora en métricas podría atribuirse erróneamente al algoritmo en lugar del feature engineering, comprometiendo la validez científica del paper.

---

### Q2 — Formato del modelo: JSON vs binary

**Veredicto:** **Ambos: JSON en repo para auditoría, binary en producción para rendimiento**.

**Justificación:** Para un proyecto open-source con paper académico, la transparencia es esencial: revisores deben poder inspeccionar la estructura del modelo sin herramientas especializadas. JSON permite `git diff` para detectar cambios. Pero en producción, binary es más rápido de cargar (~3×) y ocupa menos espacio. La solución es generar ambos desde el mismo entrenamiento.

**Código verificable para generación dual:**
```python
# scripts/export_model.py
import xgboost as xgb

model = xgb.Booster(model_file="models/xgboost_ctu13.json")

# Exportar JSON (auditoría)
model.save_model("models/xgboost_ctu13.json")  # ya está en JSON

# Exportar binary (producción)
model.save_model("models/xgboost_ctu13.ubj")   # Universal JSON binary

# Verificar equivalencia: ambas cargas deben producir mismas predicciones
import numpy as np
X_test = np.random.rand(10, 42).astype(np.float32)
pred_json = model.predict(xgb.DMatrix(X_test))
model_bin = xgb.Booster(model_file="models/xgboost_ctu13.ubj")
pred_bin = model_bin.predict(xgb.DMatrix(X_test))
assert np.allclose(pred_json, pred_bin), "Modelos no equivalentes"
```

**Riesgo si se ignora:** Usar solo binary dificulta la auditoría científica; usar solo JSON añade latencia de carga en producción que podría afectar el SLA del pipeline (<50ms handshake).

---

### Q3 — `plugin_invoke` y el MessageContext

**Veredicto:** **Opción B (ml-detector pre-procesa features) con interfaz explícita**.

**Justificación:** Separar responsabilidades es crítico para mantenibilidad: ml-detector conoce el dominio de features; plugin-loader solo ejecuta inferencia. Acoplar el plugin a la deserialización de payload crea deuda técnica y dificulta testing. La Opción B permite que el plugin sea agnóstico al formato de mensaje ZeroMQ.

**Código verificable para Opción B:**
```cpp
// === ml-detector: pre-procesa features ===
// src/ml-detector/feature_extractor.cpp
std::vector<float> extract_features(const MessageContext& ctx) {
    // Lógica específica de dominio: extraer 42 features del payload cifrado
    // Esta función es la única que conoce el formato interno del payload
    std::vector<float> features(42);
    // ... extracción ...
    return features;
}

// === plugin xgboost: solo inferencia ===
// plugins/xgboost/xgboost_plugin.cpp
extern "C" int plugin_invoke(const uint8_t* input, size_t input_len,
                             uint8_t* output, size_t* output_len) {
    // input ya es un vector de float32 serializado (no payload crudo)
    if (input_len != 42 * sizeof(float)) {
        log_critical("feature vector size mismatch");
        return -1;
    }
    
    const float* features = reinterpret_cast<const float*>(input);
    DMatrixHandle dmatrix;
    XGDMatrixCreateFromMat(features, 1, 42, -1, &dmatrix);
    
    // ... inferencia ...
    return 0;
}
```

**Riesgo si se ignora:** Opción A (deserializar en plugin) crea acoplamiento fuerte: cualquier cambio en el formato de payload requiere recompilar todos los plugins. Opción C (nuevo campo en MessageContext) rompe compatibilidad con plugins existentes.

---

### Q4 — Vagrantfile: ¿XGBoost via pip o apt?

**Veredicto:** **pip con virtualenv aislado + fallback a apt solo si PyPI inaccesible**.

**Justificación:** Fijar `xgboost==3.2.0` es esencial para reproducibilidad científica. Debian Bookworm's apt package (~1.7) es demasiado antiguo y carece de APIs necesarias. Pero hospitales con firewalls restrictivos pueden no tener acceso a PyPI. La solución es intentar pip primero, y si falla, caer back a apt con advertencia explícita.

**Código verificable para Vagrantfile:**
```ruby
# Vagrantfile — bloque XGBoost provisioning
config.vm.provision "shell", inline: <<-SHELL
  # Intentar pip con virtualenv aislado
  if ! python3 -m venv /opt/ml-defender/xgboost-venv 2>/dev/null; then
    echo "⚠️  virtualenv creation failed, trying system pip..."
  fi
  
  source /opt/ml-defender/xgboost-venv/bin/activate 2>/dev/null || true
  
  if ! pip3 install xgboost==3.2.0 --quiet 2>/dev/null; then
    echo "⚠️  PyPI inaccessible, falling back to apt (version may be outdated)"
    apt-get install -y python3-xgboost >/dev/null 2>&1 || true
    echo "❗  WARNING: Using system xgboost ($(python3 -c 'import xgboost; print(xgboost.__version__)' 2>/dev/null || echo 'unknown'))"
    echo "❗  For scientific reproducibility, ensure xgboost==3.2.0 in production"
  else
    echo "✓ xgboost==3.2.0 installed in isolated venv"
  fi
SHELL
```

**Riesgo si se ignora:** Usar solo pip sin fallback bloquea el provisioning en entornos offline; usar solo apt sacrifica reproducibilidad científica al permitir versiones no controladas.

---

## 🛠️ Recomendaciones Adicionales (con código verificable)

### 1. Añadir test de carga de modelo en CI
```bash
# tests/plugin-xgboost-load.sh
#!/bin/bash
set -euo pipefail

# Verificar que el plugin puede cargar el modelo de entrenamiento
export MLD_XGBOOST_MODEL_PATH=/etc/ml-defender/models/xgboost_ctu13.ubj
./build-debug/plugins/libplugin_xgboost.so --test-load

# Debe salir con código 0 y log: "[xgboost-plugin] Model loaded successfully"
```

### 2. Documentar hiperparámetros en el repo
```yaml
# docs/xgboost/hyperparameters.yml
model_version: "xgboost_ctu13_v1"
training_date: "2026-04-15"
dataset: "CTU-13 Neris"
features: "same_as_rf_baseline"  # Opción A
hyperparameters:
  n_estimators: 100
  max_depth: 6
  learning_rate: 0.1
  subsample: 0.8
  colsample_bytree: 0.8
  random_state: 42
evaluation:
  cv_folds: 5
  metrics: ["precision", "recall", "f1", "fpr"]
  threshold_optimization: "youden_index"
```

### 3. Validar equivalencia JSON/binary en CI
```makefile
# Makefile target
test-xgboost-model-equivalence:
	@python3 scripts/validate_model_equivalence.py \
		--json models/xgboost_ctu13.json \
		--binary models/xgboost_ctu13.ubj \
		--test-samples 100
	@echo "✓ JSON and binary models produce identical predictions"
```

---

## 📋 Checklist de Acciones Inmediatas (DAY 119)

```markdown
- [ ] Ejecutar `vagrant destroy && vagrant up` para validar provisioning XGBoost
- [ ] Compilar plugin_xgboost con `make pipeline-build` y verificar linkado
- [ ] Implementar cache de modelo en plugin_init (evitar reload por inferencia)
- [ ] Crear virtualenv aislado en Vagrantfile + fallback apt con warning
- [ ] Documentar feature set exacto en docs/xgboost/features.md (42 columnas)
- [ ] Generar modelo dual JSON+binary y validar equivalencia con script
- [ ] Añadir test de carga de modelo a `make test-all`
- [ ] Actualizar docs/XGBOOST-VALIDATION.md con Opción A como primary path
```

---

## 🏁 Palabras Finales

Alonso:

DAY 118 ha demostrado que PHASE 3 no fue un final, sino un cimiento. La apertura de PHASE 4 con XGBoost sigue los mismos principios que han guiado el proyecto: reproducibilidad, fail-closed por diseño, y trazabilidad científica.

Las cuatro preguntas que planteáis reflejan una mentalidad madura: no solo *"¿cómo lo hacemos funcionar?"*, sino *"¿cómo lo hacemos de forma que sea auditable, mantenible y científicamente válido?"*.

> *"En seguridad y ciencia, lo que no se puede verificar, no se puede confiar."*

Proceded con DAY 119. El Consejo estará atento a la primera inferencia end-to-end del plugin XGBoost y a la validación de métricas en CTU-13 Neris.

*Via Appia Quality · Un escudo, nunca una espada.*

**— Consejo de Sabios, DAY 118** 🛡️