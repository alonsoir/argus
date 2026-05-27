# Shadow Authority - Non-Destructive Model Lifecycle

## Concepto

**Authoritative Model:**
- Modelo que DECIDE (bloquea/permite)
- Un solo modelo por detección
- Campo: `authoritative_model`

**Shadow Models:**
- Modelos que OBSERVAN (no bloquean)
- Múltiples permitidos simultáneamente
- Campo: `shadow_models[]`

## Casos de Uso

### 1. A/B Testing Natural
```
Producción:
  authoritative_model: "ddos_v2"
  shadow_models: ["ddos_v3_beta"]

Si ddos_v3_beta detecta más sin false positives:
  → Promover a authoritative
```

### 2. Legacy Attack Detection
```
Escenario: Atacante usa técnica antigua (2020)

Producción:
  authoritative_model: "ddos_v5" (2025)
  shadow_models: ["ddos_v1", "ddos_v2"]  (2020-2022)

Si ddos_v1 detecta pero v5 no:
  → Alert: "Legacy technique detected"
  → Mantener v1 en shadow mode
```

### 3. Regression Detection
```
Antes de promover v3 a producción:

1. Deploy v3 en shadow mode (1 semana)
2. Comparar detecciones:
   - v3 vs v2 (authoritative)
3. Analizar divergencias:
   - ¿v3 detecta más? → Mejora
   - ¿v3 detecta menos? → Regression
4. Decision basada en datos reales
```

## Implementación (Futuro)

### ml-detector config
```json
{
  "models": {
    "ddos": {
      "version": "v2",
      "mode": "authoritative"
    },
    "ddos_legacy": {
      "version": "v1", 
      "mode": "shadow"
    }
  }
}
```

### Logging
```cpp
if (model.mode == "shadow") {
    // Detecta y logea
    log_shadow_detection(event, model);
    
    // NO envía a firewall
    return;
}
```

### Analysis
```python
# Comparar authoritative vs shadow
df = pd.read_json('events.jsonl', lines=True)

auth_detections = df[df['authoritative_model'] == 'ddos_v2']
shadow_detections = df[df['shadow_models'].str.contains('ddos_v1')]

# Eventos que v1 vio pero v2 no
v1_unique = shadow_detections[~shadow_detections['src_ip'].isin(auth_detections['src_ip'])]

print(f"Shadow model detectó {len(v1_unique)} eventos únicos")
```

## Valor para Paper

**Contribución Única:**
- "Non-destructive model lifecycle management"
- A/B testing on real traffic
- Legacy technique preservation
- Regression detection before deployment

**No existe en academia:**
- Papers: modelo nuevo reemplaza anterior
- Nosotros: múltiples modelos observan simultáneamente
- Ground truth: comparación en producción