# ADR-026: Arquitectura P2P, Distribución de Modelos y Aprendizaje de Flota

**Estado**: BORRADOR — pendiente de implementación (post segundo nodo activo)  
**Fecha**: 2026-04-05  
**Contexto**: DAY 104 — Consejo de Sabios, PRE-ADR-026 v2  
**Deciders**: Alonso Isidoro Román, Consejo de Sabios DAY 104  
**Árbitro**: Alonso Isidoro Román

---

## Contexto

aRGus NDR está diseñado para desplegarse en flotas de nodos en 
organizaciones con recursos limitados (hospitales, escuelas, municipios). 
Una vez que el nodo único funciona de forma estable, surge la necesidad 
de definir cómo se coordina una flota: distribución de modelos, 
telemetría, aprendizaje colaborativo y privacidad de datos.

El Consejo de Sabios deliberó sobre PRE-ADR-026 v2 en DAY 104. Esta ADR 
formaliza las decisiones del árbitro derivadas de esa deliberación.

---

## Decisiones

### D1 — Principio Arquitectónico Inamovible: Asimetría Nodo/Servidor

Los nodos son consumidores ligeros de inteligencia. El servidor central 
es el único punto de entrenamiento, validación y distribución de modelos. 
Los nodos no se coordinan entre sí directamente — toda comunicación 
pasa por el servidor.

**Unánime.**

### D2 — Modelo de detección: XGBoost

XGBoost para detección tabular en Track 1 (nodo) y Track 2 (servidor 
central). FT-Transformer únicamente como experimento académico con GPU 
disponible y si se demuestra ganancia >3% F1 sobre XGBoost.

Benchmarks en datasets NIDS reales (DeepSeek, DAY 104):

| Dataset      | XGBoost F1 | FT-T F1 | XGBoost lat. | FT-T lat. |
|--------------|-----------|---------|-------------|----------|
| CTU-13       | 0.992     | 0.989   | 0.8 μs      | 12.3 μs  |
| CIC-IDS2017  | 0.978     | 0.975   | 1.2 μs      | 18.7 μs  |
| UNSW-NB15    | 0.965     | 0.961   | 0.9 μs      | 15.4 μs  |

**Unánime.**

### D3 — Federated Learning clásico: POSPONER indefinidamente

Para nodos con hardware N100/RPi4 y conectividad hospitalaria, FL clásico 
(FedAvg) no es viable en el horizonte actual. La arquitectura hub-and-spoke 
con XGBoost es suficiente y más operable.

**Unánime.**

### D4 — Distribución de plugins: BitTorrent

BitTorrent exclusivamente para distribución de plugins firmados 
(Ed25519, ADR-025). No para telemetría ni modelos en primera iteración.

**Unánime.**

### D5 — Protocolo de telemetría nodo→servidor

**HTTPS:443 como default.** ZeroMQ como opción para despliegues LAN 
controlados. Razón: los firewalls hospitalarios bloquean puertos no 
estándar; HTTPS:443 siempre está abierto. La elección es configuración, 
no estándar único.

**Dividido (3 ZeroMQ vs 2 HTTPS). Árbitro decide: HTTPS default.**

### D6 — Thresholds de validación de plugins/modelos

- F1 ≥ 0.95 (todos los entornos)
- FPR ≤ 0.001 (todos los entornos)
- **Precision ≥ 0.99** (entornos médicos) — un FP que bloquea acceso 
  a base de datos de anestesia es más catastrófico que un FN (Gemini, DAY 104)
- Canary deployment (5-10% nodos) antes de distribución global
- Evaluación mínima en 2 nodos reales antes de promoción

**Consenso con matiz médico aprobado.**

### D7 — Privacidad LOPD/GDPR: anonimización en origen

Hash salado solo es insuficiente. Los flujos de red en hospitales pueden 
contener datos de salud bajo GDPR Art. 9 (inferencia de actividad clínica).

Requisitos antes de cualquier producción con datos hospitalarios reales:
1. Anonimización irreversible en el nodo, antes del envío
2. DPIA (Data Protection Impact Assessment) formal
3. Acuerdo legal explícito con cada institución
4. Considerar ISO 27001 para servidor central

**Unánime.**

### D8 — Rollback: obligatorio desde el diseño inicial

El nodo retiene mínimo versión N-1 de cada plugin. Rollback activable 
remotamente desde servidor, firmado Ed25519. Métricas de salud 
reportadas periódicamente; rollback automático si FPR supera threshold 
durante 3 periodos consecutivos.

Mecanismo preferido: integración en `deployment.yml` como SSOT 
(consistente con ADR-021). Plugin-loader mantiene Shadow Directory.

**Unánime.**

### D9 — DEBT-PROTO-002: bloqueante duro antes del segundo nodo

El versionado de schema CSV es prerequisito de reproducibilidad y 
reentrenamiento consistente. Debe implementarse antes de activar el 
segundo nodo. Decisión de formato (CSV inline vs Protobuf) diferida.

**Unánime.**

### D10 — Modelo vLLM (servidor central): DIFERIDO

Phi-3 Mini si CPU-only (8-16GB RAM). Mistral 7B si GPU disponible 
(T4 o similar). Decisión condicionada al hardware del servidor central. 
Se decide cuando ese hardware esté definido.

**Diferido.**

---

## Ítems pendientes de ADRs propios

| Ítem | ADR futuro | Prerequisito |
|------|-----------|-------------|
| Model Lifecycle & Telemetry Governance | ADR-028 | 2+ nodos activos |
| `required_features` en plugin manifest | ADR-029 | post ADR-025 |
| Dataset governance (acceso, licencia) | ADR-030 | pre-publicación |
| ISO 27001 servidor central | ADR-031 | pre-piloto hospitalario |

---

## Consecuencias

- **Positivas**: arquitectura definida para escalar de 1 a N nodos sin 
  rediseño; privacidad de datos hospitalarios protegida desde el diseño; 
  rollback garantizado desde el primer plugin distribuido
- **Bloqueantes antes de activar segundo nodo**: DEBT-PROTO-002, ADR-025
- **No bloqueantes ahora**: modelo vLLM, ISO 27001, nodos agregadores 
  regionales (relevante con flota >20 nodos)

---

## Referencias

- Consejo de Sabios DAY 104 — síntesis completa en 
  `docs/consejo/CONSEJO-DAY104-sintesis-PRE-ADR-026.md`
- ADR-021: deployment.yml como SSOT
- ADR-025: Plugin Integrity Verification (Ed25519)
- DEBT-PROTO-002: Schema versionado CSV
