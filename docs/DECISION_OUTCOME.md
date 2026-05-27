# Decision Outcome - Ground Truth for Closed-Loop Learning

## Concepto

El campo `decision_outcome` registra **qué pasó REALMENTE** con un evento, no solo qué decidió el modelo.

## Estados

### 1. blocked
```
Evento bloqueado por firewall
Ground truth: Sistema actuó preventivamente
```

### 2. allowed
```
Evento permitido (score < threshold)
Ground truth: Sistema consideró legítimo
```

### 3. false_positive
```
Bloqueado pero era legítimo (verificado manualmente)
Ground truth: Error del modelo (FP)
Acción: Reentrenar para evitar este patrón
```

### 4. false_negative
```
Permitido pero era ataque (descubierto después)
Ground truth: Error del modelo (FN)
Acción: Reentrenar para detectar este patrón
```

### 5. unknown
```
Outcome aún no determinado
Default: eventos recientes sin validación
```

### 6. shadow
```
Solo observado (shadow mode)
No bloqueado, solo logeado
```

## Pipeline
```
Detección (T+0):
  decision_outcome = "unknown"

Acción Firewall (T+1ms):
  if blocked:
    decision_outcome = "blocked"
  else:
    decision_outcome = "allowed"

Validación Manual (T+1 day):
  if manual_review == "legitimate":
    decision_outcome = "false_positive"
  if forensic_analysis == "attack":
    decision_outcome = "false_negative"
```

## Reentrenamiento
```python
# Dataset para reentrenamiento
df = pd.read_json('events.jsonl', lines=True)

# Ground truth validado
validated = df[df['decision_outcome'].isin(['false_positive', 'false_negative'])]

# False positives → Añadir como benign
fps = validated[validated['decision_outcome'] == 'false_positive']

# False negatives → Añadir como malicious  
fns = validated[validated['decision_outcome'] == 'false_negative']

# Reentrenar con ejemplos corregidos
retrain_dataset = pd.concat([fps, fns])
```

## Valor para Paper

**Closed-Loop Learning:**
- Sistema aprende de sus errores
- Ground truth real (no synthetic)
- Reentrenamiento automático
- Paper: "Self-improving IDS"

**Métricas Honestas:**
```
Accuracy reportada: 95%
Accuracy real (con outcomes): 92%

False positive rate: 3%
False negative rate: 5%
```

**Transparencia científica:**
- No ocultar errores
- Documentar drift
- Via Appia Quality