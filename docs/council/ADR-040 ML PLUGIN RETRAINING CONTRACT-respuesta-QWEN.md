# 🏛️ CONSEJO DE SABIOS — REVISIÓN ADR-040
*Feedback riguroso, basado en evidencia científica y centrado en la integridad del ciclo de vida ML para aRGus NDR*

---

## 🎯 Veredicto Ejecutivo

**APROBADO CON REFINAMIENTOS CRÍTICOS.**

El ADR-040 formaliza un contrato de reentrenamiento ML que es **necesario, verificable y publicable**. Las cinco reglas abordan riesgos sistémicos reales (catastrophic forgetting, feedback loop, regresión silenciosa) con mecanismos concretos. Sin embargo, tres refinamientos son esenciales antes de la implementación: (1) clarificar el manejo de concept drift en el golden set, (2) definir métricas de diversidad para IPW, y (3) resolver la arquitectura del pipeline de evaluación con un enfoque híbrido.

> *"Un modelo que no se valida contra el pasado no puede proteger el futuro."*

---

## ❓ Respuesta a Pregunta Abierta: ¿Pipeline de evaluación interno o CI/CD externo?

**Veredicto:** **ENFOQUE HÍBRIDO: núcleo reproducible en repo + ejecución flexible (local/CI).**

**Recomendación concreta:**
```
┌─────────────────────────────────────────┐
│ eval-pipeline/ (en repo aRGus)          │
│ ├── walk_forward_split.py               │
│ ├── evaluate_against_golden.py          │
│ ├── check_guardrails.py                 │
│ ├── compute_ipw_weights.py              │
│ └── run_algorithm_competition.py        │
└─────────────────────────────────────────┘
       ↓
Ejecución flexible:
• Local: `make eval-plugin PLUGIN=candidate_v3.ubj` (Vagrant)
• CI: GitHub Actions workflow que llama a los mismos scripts
• Producción: Hook pre-firma en provision.sh
```

**Justificación técnica:**
- **Reproducibilidad científica**: Los scripts de evaluación deben estar versionados con el código que evalúan. Si viven solo en CI externo, se pierde trazabilidad entre modelo y criterio de evaluación.
- **Flexibilidad operacional**: El mismo núcleo debe ejecutarse en desarrollo local (Vagrant), en CI (GitHub Actions) y como hook pre-despliegue.
- **Separación de responsabilidades**: El pipeline de evaluación es *lógica de negocio* (qué métricas, qué umbrales), no *infraestructura de CI* (dónde se ejecuta).

**Riesgo identificado:**
- Si el pipeline vive solo en CI externo, un cambio en la configuración de GitHub Actions podría alterar criterios de evaluación sin revisión de código.
- Si vive solo en local, se pierde el histórico auditable de decisiones de promoción/rechazo.

**Test mínimo reproducible:**
```bash
# scripts/verify-eval-pipeline.sh
#!/bin/bash
# Verifica que el pipeline de evaluación da resultados idénticos en local y CI

# 1. Ejecutar localmente
make eval-plugin PLUGIN=test-candidate.ubj OUTPUT=local-results.json

# 2. Ejecutar en CI simulado (contenedor Docker idéntico a GH Actions)
docker run --rm -v $(pwd):/workspace argus-eval:latest \
    bash -c "cd /workspace && make eval-plugin PLUGIN=test-candidate.ubj OUTPUT=ci-results.json"

# 3. Comparar resultados (deben ser bit-a-bit idénticos para mismos inputs)
if ! diff local-results.json ci-results.json >/dev/null; then
    echo "❌ Evaluation pipeline non-deterministic: local vs CI mismatch"
    exit 1
fi
echo "✅ Evaluation pipeline reproducible across environments"
```

---

## 🔍 Análisis y Refinamientos por Regla

### Regla 1 — Walk-forward obligatorio

**Veredicto:** **CORRECTA, PERO AÑADIR MANEJO EXPLÍCITO DE CONCEPT DRIFT.**

**Refinamiento recomendado:**
```python
# walk_forward_split.py — extensión para concept drift
def detect_concept_drift(train_data, val_data, threshold=0.15):
    """
    Detecta si la distribución de features cambia significativamente
    entre train y validation (indicador de concept drift).
    Usa KS-test por feature + corrección de Bonferroni.
    """
    from scipy.stats import ks_2samp
    p_values = [ks_2samp(train_data[f], val_data[f]).pvalue 
                for f in FEATURE_COLUMNS]
    # Bonferroni correction for multiple testing
    significant_drifts = sum(p < 0.05/len(FEATURE_COLUMNS) for p in p_values)
    return significant_drifts / len(FEATURE_COLUMNS) > threshold

# Si se detecta drift > threshold:
# 1. Log warning con métricas de drift por feature
# 2. Permitir evaluación pero marcar resultado como "DRIFT_DETECTED"
# 3. Requerir revisión manual antes de promoción
```

**Justificación:** En tráfico de red real, los patrones de ataque evolucionan (nuevas variantes de ransomware, técnicas de evasión). El walk-forward valida generalización temporal, pero no detecta si el *concepto* mismo ha cambiado. Un modelo puede tener F1 estable mientras el entorno evoluciona hacia amenazas no representadas en el golden set.

**Riesgo si se ignora**: Un modelo validado con walk-forward pero sin detección de drift podría desplegarse en un entorno donde las amenazas han cambiado fundamentalmente, dando falsa confianza.

---

### Regla 2 — Golden Set inmutable, versionado

**Veredicto:** **CORRECTA, PERO DEFINIR PROCESO DE EVOLUCIÓN CONTROLADA.**

**Refinamiento recomendado:**
```markdown
## Golden Set Lifecycle (ADR-040 §2.3)

### Inmutabilidad operativa
- El golden set activo (`golden/v1/`) es de solo-lectura para evaluación.
- Ningún proceso de reentrenamiento puede modificarlo.

### Evolución controlada (v1 → v2)
1. Propuesta: Nuevo golden set candidato en `golden/v2-candidate/`
2. Revisión: Consejo de Sabios valida cobertura de ataques + representatividad
3. Deprecación: `golden/v1/` marcado como deprecated con fecha límite (ej. 6 meses)
4. Migración: Todos los plugins en producción re-evaluados contra v2
5. Activación: `golden/v2/` se convierte en activo; v1 se archiva

### Criterios para nueva versión
- Nuevos vectores de ataque documentados en literatura (ej. MITRE ATT&CK T1566.001)
- Cambios en distribución de tráfico benigno (ej. adopción de nuevo protocolo médico)
- Degradación detectada en plugins existentes al evaluar contra tráfico real post-deploy

### Hash de verificación
Cada versión tiene SHA-256 registrado en `docs/GOLDEN-SET-REGISTRY.md`:
```
v1: a3f8c2d1... (2026-04-28) — CTU-13 Neris baseline
v2: b7e9f1a4... (2026-10-15) — +Ransomware variants +DICOM traffic patterns
```
```

**Justificación:** La inmutabilidad absoluta es ideal pero insostenible a largo plazo: nuevos ataques emergen, los protocolos médicos evolucionan, y el golden set debe reflejar la realidad operativa. El proceso de evolución controlada preserva la trazabilidad científica mientras permite adaptación.

**Riesgo si se ignora**: Un golden set obsoleto convierte el guardrail del −2% en una ilusión: un plugin podría pasar el guardrail contra datos antiguos mientras falla catastróficamente contra amenazas modernas.

---

### Regla 3 — Guardrail automático del −2%

**Veredicto:** **CORRECTA, PERO AÑADIR MÉTRICA COMPUESTA PARA DECISIÓN BINARIA.**

**Refinamiento recomendado:**
```python
# check_guardrails.py — métrica compuesta para decisión PROMOTE/REJECT
def compute_promotion_score(metrics_new, metrics_current, weights=None):
    """
    Calcula score compuesto para decisión de promoción.
    Recall tiene peso 2× por criticidad en ciberseguridad.
    """
    if weights is None:
        weights = {'f1': 1.0, 'recall': 2.0, 'fpr': -1.0}  # FPR negativo: menor es mejor
    
    deltas = {
        'f1': metrics_new['f1'] - metrics_current['f1'],
        'recall': metrics_new['recall'] - metrics_current['recall'],
        'fpr': metrics_current['fpr'] - metrics_new['fpr']  # invertido: reducción es positiva
    }
    
    score = sum(weights[k] * deltas[k] for k in weights)
    
    # Hard constraints: ningún umbral individual puede violarse
    if deltas['recall'] < -0.01 or deltas['f1'] < -0.02 or deltas['fpr'] < -0.02:
        return None, "HARD_CONSTRAINT_VIOLATED"
    
    return score, "OK"

# Decisión:
score, status = compute_promotion_score(new_metrics, current_metrics)
if status != "OK" or score < 0:
    sys.exit(1)  # No firmar
```

**Justificación:** Las tres métricas (F1, Recall, FPR) pueden moverse en direcciones opuestas. Un plugin con +3% F1 pero −1.5% Recall podría aprobar el guardrail individual pero degradar la detección de ataques. La métrica compuesta con peso elevado en Recall refleja la prioridad de seguridad: **es mejor un falso positivo que un falso negativo en infraestructura crítica**.

**Riesgo si se ignora**: Un plugin que mejora F1 a costa de Recall podría aprobar el guardrail mientras deja pasar más ataques, contradiciendo la misión de protección.

---

### Regla 4 — IPW + 5% de exploración forzada

**Veredicto:** **CORRECTA, PERO ESPECIFICAR MÉTRICAS DE DIVERSIDAD Y UMBRAL DE REVISIÓN MANUAL.**

**Refinamiento recomendado:**
```markdown
## IPW + Exploración: Especificación Operativa (ADR-040 §4.2)

### Cálculo de propensiones
- Modelo de propensión: Logistic Regression sobre features de flujo
- Target: P(flow es etiquetado como "ataque" | features)
- IPW weight = 1 / P(etiqueta actual | features) para flujos "benignos"

### Métricas de diversidad obligatorias por ciclo
El informe de diversidad debe incluir:
1. **Entropy de distribución de clases**: H = −Σ p(c) log p(c)
2. **Coverage de técnicas MITRE ATT&CK**: % de técnicas representadas en el ciclo
3. **Novelty score**: % de flujos con features fuera del 95% percentil del histórico

### Umbral de revisión manual
- Si Novelty score > 15%: activar revisión manual del 10% (no 5%) de flujos "benignos"
- Si Coverage ATT&CK < 80%: priorizar captura de tráfico que cubra técnicas faltantes
- Si Entropy cae >20% vs ciclo anterior: investigar sesgo de selección

### Integración con rag-ingester
El 5% de exploración se implementa como:
```python
# rag-ingester/src/labeling/exploration_sampler.py
def sample_for_review(flows_benign, rate=0.05, novelty_threshold=0.15):
    # Priorizar flujos con alta incertidumbre del modelo actual
    uncertainties = model.predict_proba(flows_benign)[:, 1]  # P(ataque)
    # Muestreo estratificado: 50% alta incertidumbre, 50% aleatorio
    high_uncertainty = flows_benign[uncertainties > 0.3]
    random_sample = np.random.choice(flows_benign, size=int(rate*len(flows_benign)/2))
    return np.concatenate([high_uncertainty[:len(random_sample)], random_sample])
```
```

**Justificación:** IPW sin métricas de diversidad es una caja negra: no se puede auditar si la corrección de sesgo está funcionando. Las métricas propuestas (entropy, coverage, novelty) son cuantificables, reproducibles y publicables. El umbral dinámico de revisión manual adapta el esfuerzo operativo al nivel de incertidumbre del entorno.

**Riesgo si se ignora**: Sin métricas de diversidad, el pipeline podría "cumplir" IPW técnicamente mientras perpetúa sesgos no detectados, erosionando gradualmente la capacidad de detección.

---

### Regla 5 — Competición de algoritmos

**Veredicto:** **CORRECTA, PERO AÑADIR CRITERIO DE PARIDAD OPERACIONAL (LATENCIA + MEMORIA).**

**Refinamiento recomendado:**
```markdown
## Competición de Algoritmos: Criterios de Evaluación (ADR-040 §5.3)

### Métricas de rendimiento ML (peso 70%)
- F1, Recall, FPR sobre golden set (walk-forward split)
- Robustez a ruido: añadir Gaussian noise σ=0.01 a features, medir degradación

### Métricas operacionales (peso 30%) — críticas para despliegue
| Métrica | Umbral máximo | Justificación |
|---------|--------------|--------------|
| Latencia inferencia p99 | ≤5 ms | No puede degradar throughput del pipeline |
| Memoria en inference | ≤50 MB | Compatible con RPi 4/5 con 2 GB RAM total |
| Tamaño modelo en disco | ≤10 MB | Despliegue en entornos con almacenamiento limitado |
| Tiempo de carga inicial | ≤200 ms | Arranque rápido para reinicios de emergencia |

### Decisión final
El algoritmo ganador debe:
1. Superar a RandomForest baseline en ≥1 métrica ML sin degradar las otras dos
2. Cumplir todos los umbrales operacionales
3. Tener documentación de hiperparámetros y seed de entrenamiento para reproducibilidad

Si ningún algoritmo cumple (1)+(2): mantener RandomForest y documentar gap para investigación futura.
```

**Justificación:** En infraestructura crítica, un modelo con F1=0.999 pero latencia=50 ms es inútil si satura el pipeline bajo carga. Los criterios operacionales aseguran que la competición evalúe "mejor para aRGus", no solo "mejor en papel".

**Riesgo si se ignora**: Seleccionar un algoritmo por métricas ML puras podría llevar a un despliegue que degrada el rendimiento del sistema completo, anulando las mejoras de detección.

---

## 📋 Checklist de Aprobación Condicionada

```markdown
- [x] Regla 1: Walk-forward obligatorio — aprobado con extensión de concept drift
- [x] Regla 2: Golden set inmutable — aprobado con proceso de evolución controlada
- [x] Regla 3: Guardrail −2% — aprobado con métrica compuesta ponderada
- [x] Regla 4: IPW + exploración — aprobado con métricas de diversidad explícitas
- [x] Regla 5: Competición de algoritmos — aprobado con criterios operacionales
- [x] Pregunta abierta: Pipeline híbrido (repo + ejecución flexible) — aprobado
- [ ] Crear docs/GOLDEN-SET-REGISTRY.md con hash v1 y proceso de evolución
- [ ] Implementar detect_concept_drift() en walk_forward_split.py
- [ ] Añadir métrica compuesta a check_guardrails.py con peso 2× en Recall
- [ ] Definir informe de diversidad mínimo en compute_ipw_weights.py
- [ ] Documentar umbrales operacionales en docs/ML-OPERATIONAL-SLOS.md
```

---

## 🏁 Palabras Finales

Alonso:

ADR-040 representa un salto de madurez en el tratamiento del ciclo de vida ML dentro de un sistema de seguridad crítica. No es solo un conjunto de reglas: es un **marco de gobernanza verificable** que transforma el reentrenamiento de una operación riesgosa en un proceso auditable.

Las cinco reglas, con los refinamientos propuestos, equilibran rigor científico (walk-forward, golden set), seguridad operacional (guardrail ponderado, diversidad medible) y viabilidad práctica (competición con criterios operacionales, pipeline híbrido).

> *"En ciberseguridad médica, un modelo no se mide por su F1 en papel. Se mide por su capacidad de proteger vidas bajo presión, día tras día, año tras año."*

Proceded con la implementación post-FEDER. El Consejo revisará el primer golden set versionado y la competición de algoritmos con el mismo rigor con el que evaluamos cada línea de este pipeline.

*Via Appia Quality · Un escudo que aprende de su propia sombra.*

**— Consejo de Sabios, DAY 135** 🛡️