### **Respuestas del Consejo de Sabios — ADR-040: ML Plugin Retraining Contract**
*(Unánime 8/8, basado en **evidencia científica**, **principios de ML reproducible** y **protección de infraestructuras críticas**)*

---

## **Respuesta a la Pregunta Abierta: Pipeline de Evaluación (Interno vs. CI/CD Externo)**
**Veredicto:** **Opción B — CI/CD externo (GitHub Actions)**, con **matrices de decisión versionadas en el repositorio**.

### **Análisis Detallado:**

#### **1. Ventajas de la Opción B (CI/CD Externo):**
| **Criterio**               | **Opción A (Interno)**                          | **Opción B (CI/CD Externo)**                     | **Justificación**                                                                 |
|---------------------------|-------------------------------------------------|-------------------------------------------------|-----------------------------------------------------------------------------------|
| **Separación de responsabilidades** | Acoplado al entorno de despliegue.            | Separado: evaluación ≠ despliegue.            | Evita que un error en evaluación afecte al runtime.                              |
| **Histórico de decisiones** | Logs en VM (volátiles).                        | Artefactos en GitHub (inmutables).              | Auditable: ¿por qué se promovió/rechazó un modelo?                                |
| **Reproducibilidad**       | Depende del estado de la VM.                   | Independiente: usa contenedores efímeros.       | Evita el problema de *"funcionaba en mi máquina"*.                                |
| **Escalabilidad**          | Limitado por recursos de la VM.               | Escalable horizontal/verticalmente.             | Permite ejecutar competiciones de algoritmos en paralelo.                        |
| **Seguridad**              | Datos de entrenamiento en la VM.               | Datos en almacenamiento cifrado (ej: S3).       | Cumple con regulaciones de privacidad (ej: GDPR para datos de red).                 |
| **Integración con ADR-025** | Firma Ed25519 en la misma VM.                  | Firma en paso separado post-evaluación.         | Permite revisión humana antes de firmar.                                         |

#### **2. Arquitectura Recomendada:**
```mermaid
graph TD
    A[Desarrollador sube plugin candidato] --> B[GitHub Actions: Evaluación]
    B --> C{¿Pasa guardrail −2%?}
    C -->|Sí| D[Firma Ed25519 (ADR-025)]
    C -->|No| E[Rechazo + Notificación]
    D --> F[Despliegue en fleet]
    B --> G[Almacenar métricas en repo]
    G --> H[Actualizar golden set si aplica]
```

#### **3. Componentes Clave:**
| **Componente**               | **Detalle**                                                                                     |
|------------------------------|-------------------------------------------------------------------------------------------------|
| **GitHub Actions Workflow**  | - Ejecuta en contenedor con Python 3.11 + XGBoost/CatBoost/LightGBM.                            |
|                              | - Usa el golden set versionado (SHA-256 verificado).                                           |
|                              | - Produce un informe JSON con métricas (F1, Recall, FPR, latencia).                            |
| **Golden Set**               | - Almacenado en `data/golden_set/` con hash SHA-256.                                           |
|                              | - Inmutable: solo se actualiza via PR con revisión del Consejo.                                |
| **Matriz de Decisión**       | - YAML en `.github/decision-matrix.yml`: umbrales para PROMOTE/HOLD/REJECT.                     |
|                              | - Ejemplo:                                                                                     |
|                              |   ```yaml                                                                                      |
|                              |   promote:                                                                                      |
|                              |     f1_drop: <= 0.02                                                                           |
|                              |     recall_drop: <= 0.01                                                                       |
|                              |     fpr_increase: <= 0.02                                                                      |
|                              |   ```                                                                                          |
| **Artefactos**               | - Informes de evaluación en `reports/eval_<commit-hash>.json`.                                |
|                              | - Modelos firmados en `dist/plugins/signed/`.                                                  |

#### **4. Ventajas Adicionales:**
- **Integración con ADR-025:**
    - La firma Ed25519 ocurre **solo si el workflow de CI pasa**.
    - **Ejemplo de paso en GitHub Actions:**
      ```yaml
      - name: Sign plugin if promoted
        if: steps.evaluation.outputs.decision == 'promote'
        run: |
          tools/sign-plugin.sh \
            --key /etc/ml-defender/plugins/plugin_signing.pk \
            --input dist/plugins/candidate/model.ubj \
            --output dist/plugins/signed/model.ubj
      ```
- **Transparencia:**
    - Cada decisión de promoción/rechazo queda registrada en el PR.
    - **Ejemplo de comentario automático:**
      ```
      🔍 Evaluation Results:
      - F1: 0.9985 (▲ 0.001 vs production)
      - Recall: 0.999 (▲ 0.002)
      - FPR: 0.0001 (▼ 0.0001)
      ➕ Decision: PROMOTE
      ```

#### **5. Riesgos Mitigados:**
| **Riesgo**                     | **Mitigación en Opción B**                                                                 |
|--------------------------------|--------------------------------------------------------------------------------------------|
| **Feedback loop**              | IPW + 5% de exploración forzada se aplican en el workflow de CI antes de evaluar.           |
| **Catastrophic forgetting**    | Walk-forward sobre golden set inmutable.                                                   |
| **Regresión silenciosa**       | Guardrail automático (−2%) + revisión humana obligatoria antes de firmar.                 |
| **Sesgo de confirmación**     | Competición de algoritmos en CI (no en máquina local).                                     |

---

## **Recomendaciones Adicionales para ADR-040**

### **1. Golden Set: Definición y Mantenimiento**
- **Contenido mínimo:**
    - **Ataques canónicos:** Neris, Rbot, Murlo (CTU-13).
    - **Benignos diversos:** HTTP, DNS, SSH, SMTP (para evitar sesgo).
    - **Tamaño:** ~10,000 flows (suficiente para detectar regresiones estadísticamente significativas).
- **Proceso de actualización:**
    1. Proponer actualización via PR con justificación (ej: nuevo tipo de ataque).
    2. Revisión del Consejo (¿el nuevo flow es representativo?).
    3. Merge solo si el PR incluye:
        - Nuevos flows en `data/golden_set/`.
        - Hash SHA-256 actualizado en `data/golden_set/SHA256SUMS`.
        - Test que valida que el modelo actual no se degrada con la adición.

### **2. Implementación del Guardrail (−2%)**
- **Código de referencia para el check:**
  ```python
  def check_guardrail(metrics_current, metrics_candidate):
      if (metrics_candidate["f1"] < metrics_current["f1"] - 0.02 or
          metrics_candidate["recall"] < metrics_current["recall"] - 0.01 or
          metrics_candidate["fpr"] > metrics_current["fpr"] + 0.02):
          raise GuardrailViolation("Metrics below threshold")
  ```
- **Integración con CI:**
  ```yaml
  - name: Check guardrail
    run: |
      python3 tools/check_guardrail.py \
        --current reports/production_metrics.json \
        --candidate reports/candidate_metrics.json
  ```

### **3. IPW + Exploración Forzada (5%)**
- **Implementación en `rag-ingester`:**
  ```python
  def apply_ipw(flows, current_model):
      # Asignar pesos inversos a la probabilidad de detección actual
      weights = [1.0 / max(0.01, current_model.predict_proba(flow)[0][0])
                 for flow in flows]
      # Normalizar
      weights = [w / sum(weights) * len(weights) for w in weights]
      return weights

  def force_exploration(flows, percentage=0.05):
      # Seleccionar 5% de flows marcados como benignos para revisión manual
      benign_flows = [f for f in flows if current_model.predict(f) == 0]
      exploration_set = random.sample(benign_flows, int(len(benign_flows) * percentage))
      return exploration_set
  ```
- **Proceso de revisión:**
    - Los flows seleccionados se guardan en `data/exploration/<date>.json`.
    - Se abre un issue automático para revisión humana:
      ```
      🔍 Exploration Set Generated
      - Flows: 50 (5% of benign)
      - Deadline: 7 days
      - [ ] Reviewed by human
      ```

### **4. Competición de Algoritmos**
- **Script de referencia:**
  ```python
  from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
  from catboost import CatBoostClassifier
  from xgboost import XGBClassifier

  def compete_algorithms(X_train, y_train, X_val, y_val):
      models = {
          "RandomForest": RandomForestClassifier(n_estimators=100),
          "XGBoost": XGBClassifier(),
          "CatBoost": CatBoostClassifier(verbose=0),
          "LightGBM": LGBMClassifier()
      }
      results = {}
      for name, model in models.items():
          model.fit(X_train, y_train)
          y_pred = model.predict(X_val)
          results[name] = {
              "f1": f1_score(y_val, y_pred),
              "recall": recall_score(y_val, y_pred),
              "inference_latency": benchmark_inference(model, X_val)
          }
      return results
  ```
- **Criterios de decisión:**
    1. **F1 ≥ 0.998** (umbral actual).
    2. **Recall ≥ 0.999** (prioridad sobre precision para evitar falsos negativos).
    3. **Latencia de inferencia ≤ 2 ms/flow** (requisito para 500 Mbps).

---

## **Conclusión del Consejo**
> *"El contrato propuesto en ADR-040 es científicamente riguroso y aborda los tres riesgos sistémicos (catastrophic forgetting, feedback loop, regresión silenciosa) con soluciones verificables. La opción de CI/CD externo (GitHub Actions) es la correcta: separa la evaluación del despliegue, proporciona un histórico auditable, y permite escalar la competición de algoritmos. Esto es crítico para un sistema que protege infraestructuras críticas: la transparencia en la toma de decisiones es tan importante como la precisión del modelo."*

**Acciones Recomendadas para Implementación:**
1. **Crear el golden set** (prioridad post-FEDER).
2. **Implementar el workflow de CI** con los checks de guardrail.
3. **Documentar el proceso de exploración forzada** (5%) en `docs/ML-RETRAINING.md`.
4. **Ejecutar la competición de algoritmos** antes de comprometerse con XGBoost.

**¿Necesitáis ayuda con la implementación del workflow de CI o los scripts de evaluación?** Estamos listos para proporcionar código o revisiones detalladas.