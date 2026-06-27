# 🏛️ CONSEJO DE SABIOS — REVISIÓN DAY 120
*Feedback profesional, implacable y constructivo para ML Defender (aRGus NDR)*

---

## 🎯 Veredicto Ejecutivo

**Progreso notable, pero con señales de alerta crítica en P1 y P3.** Habéis cerrado DEBTs estructurales, validado idempotencia y superado los gates de F1/Precision. Sin embargo, **los scores de inferencia en P1 revelan un fallo de validación conceptual**, y la propuesta de distribución BitTorrent en P3 introduce un vector de ataque a la cadena de suministro que, en un sistema que protege vidas, es inaceptable sin salvaguardas de grado militar.

> *"En ciberseguridad médica, la transparencia no es opcional y la validación no es negociable."*

---

## ❓ Respuestas a Preguntas — Formato Solicitado

### P1 — Scores XGBoost en TEST-INTEG-XGBOOST-1 (BENIGN=0.000706, ATTACK=0.003414)

**Veredicto:** **NO ignorar el valor absoluto. Es un fallo de validación. Corregir inmediatamente.**

**Justificación:** Con `objective=binary:logistic`, XGBoost devuelve probabilidades de clase positiva (ataque). Scores de ~0.0007 y ~0.0034 significan que el modelo clasifica **ambos casos como BENIGN con 99.9% de confianza**. Si uno de los casos es sintéticamente malicioso, el modelo ha fallado. Usar features extremas fuera de la distribución de entrenamiento invalida el test. El test debe usar un conjunto de validación real (hold-out de CIC-IDS-2017) con labels conocidas, aplicar umbral optimizado (ej. Youden index), y verificar Accuracy/F1 ≥ 0.99.

**Riesgo si se ignora:** Desplegar un modelo que nunca detecta ataques en entornos reales, dando una falsa sensación de seguridad. En un hospital, esto significa ransomware sin alerta.

**Código verificable de corrección (Python + C++ test):**
```python
# scripts/validate_xgboost_test.py
import xgboost as xgb
import pandas as pd
import numpy as np

model = xgb.Booster(model_file="models/xgboost_cicids.ubj")
# Usar 1000 flows reales del hold-out (500 benign, 500 attack)
X_test = pd.read_csv("data/cicids_holdout_features.csv").values
y_true = pd.read_csv("data/cicids_holdout_labels.csv").values.ravel()

dtest = xgb.DMatrix(X_test)
y_pred_prob = model.predict(dtest)  # ya en [0,1] por binary:logistic
threshold = 0.5  # o optimizado: np.argmax(youden_index)
y_pred = (y_pred_prob >= threshold).astype(int)

f1 = f1_score(y_true, y_pred)
assert f1 >= 0.99, f"F1 {f1} < 0.99 gate médico no superado"
print(f"✅ F1={f1:.4f} | Precision={precision_score(y_true, y_pred):.4f}")
```
```cpp
// tests/test_xgboost_inference.cpp (plugin)
// Reemplazar features sintéticas por buffer extraído de hold-out real
// Validar: if (label == ATTACK && score < 0.5) FAIL_TEST("False negative on real attack")
```

---

### P2 — Integridad científica del paper: ¿Real vs Sintético?

**Veredicto:** **Separar explícitamente en §4.1 y §4.2. Transparencia total.**

**Justificación:** Mezclar resultados de datos reales y sintéticos en la misma tabla es metodológicamente incorrecto y será rechazado por revisores. La ciencia exige separar la evidencia empírica de la simulación controlada. Presentar los datos sintéticos como *"validación de comportamiento adversarial bajo condiciones aisladas"* es aceptable y hasta valioso, siempre que se documenten las limitaciones, el proceso de generación (DeepSeek + validación de consistencia de features), y no se equipare su F1 al del dataset real.

**Riesgo si se ignora:** Rechazo por falta de rigor metodológico, daño a la reputación académica del proyecto, y pérdida de credibilidad para despliegues reales.

**Estructura recomendada para §4:**
```markdown
§4.1 Evaluación en Tráfico de Red Real (CIC-IDS-2017)
- Dataset: 2.83M flows, split 80/20 estratificado
- RF vs XGBoost: F1, Precision, Latencia media (ms)
- Discusión: generalización, sesgo conocido del dataset

§4.2 Validación de Comportamiento Adversarial (Datasets Sintéticos)
- Generación: DeepSeek + validación de covarianza vs tráfico real
- DDoS/Ransomware: cobertura de patrones de ataque simulados
- Limitaciones explícitas: no sustituye validación en entornos productivos
- Uso: gate de regresión, no certificación final
```

---

### P3 — Entrenamiento in-situ + distribución BitTorrent

**Veredicto:** **Técnicamente viable con limitaciones. Distribución P2P sin curatoría centralizada → INACEPTABLE para v1.**

**Justificación:** XGBoost soporta warm-start vía `xgb_model="existing_model.ubj"` + `process_type="update"` + `refresh_leaf=True`, pero no es aprendizaje online verdadero: la estructura de árboles no crece dinámicamente, solo ajusta pesos/hojas. Además, distribuir modelos por BitTorrent sin un nodo de confianza introduce un ataque de cadena de suministro trivial: un nodo comprometido sube un modelo malicioso firmado con clave robada o manipulada, y la red lo despliega. En infraestructura crítica, la distribución debe ser **push desde autoridad verificada**, no pull descentralizado sin validación.

**Riesgo si se ignora:** Compromiso masivo de instalaciones hospitalarias por distribución de modelo adversarial. Latencia de convergencia federada incontrolable. Degradación silenciosa por overfitting local a ruido de red.

**Gates de calidad obligatorios (si se implementa en v2+):**
1. **Firma Ed25519 obligatoria** (ya disponible) + verificación de integridad SHA256.
2. **Sandbox de validación local**: antes de activar, el modelo se prueba contra `local_holdout.csv` (tráfico benigno real del hospital) + `known_attack_patterns.bin`. Si F1 local < 0.98 o FPR > 0.02, rechazo automático.
3. **Versionado + rollback atómico**: el modelo activo se mantiene hasta que el nuevo pase validación completa.
4. **Canal de distribución**: mirror oficial firmado (no BitTorrent puro). Si se usa P2P, solo como CDN caché de paquetes firmados por el vendor.
5. **Human-in-the-loop**: activación requiere aprobación del operador local.

**Snippet de validación pre-despliegue:**
```bash
#!/bin/bash # tools/validate_and_activate_model.sh
set -euo pipefail
MODEL="$1"
[ -f "$MODEL.sig" ] || { echo "❌ Sin firma"; exit 1; }
tools/verify-model.sh "$MODEL" || { echo "❌ Firma inválida"; exit 1; }
# Test local
python3 scripts/local_sanity_check.py --model "$MODEL" --holdout /etc/ml-defender/local_holdout.csv
[ $? -eq 0 ] || { echo "❌ Fallo gate local"; exit 1; }
# Activación atómica
cp "$MODEL" /etc/ml-defender/models/xgboost_active.ubj.tmp
mv /etc/ml-defender/models/xgboost_active.ubj.tmp /etc/ml-defender/models/xgboost_active.ubj
echo "✅ Modelo activado y validado"
```

---

### P4 — DEBT-SEED: ¿hardcoded en CMake? ¿Mismo patrón que pubkey?

**Veredicto:** **NO aplicar `execute_process()` a la seed. La seed es secreta; nunca debe tocar el sistema de build.**

**Justificación:** La pubkey es pública; leerla en `cmake-time` es seguro. La seed es material criptográfico secreto. Si `execute_process()` la lee durante la compilación, queda expuesta en logs de CMake, caché de CMake (`CMakeCache.txt`), y potencialmente en artefactos de CI. La seed debe vivir **exclusivamente en el dominio de provisioning/runtime**: `/etc/ml-defender/<comp>/seed.bin` con permisos `0640`, leída por el componente al inicio, y mantenida en memoria protegida.

**Riesgo si se ignora:** Fuga de seed en logs de build, CI público, o repositorio. Compromiso total de la familia de claves. Violación directa del principio de mínima exposición.

**Patrón seguro C++20 para manejo de seed:**
```cpp
// src/crypto/secure_buffer.hpp
#include <vector>
#include <cstring>
#include <sys/mman.h>

class SecureBuffer : public std::vector<uint8_t> {
public:
    explicit SecureBuffer(size_t n) : std::vector<uint8_t>(n) {
        mlock(this->data(), this->size()); // Evita swap a disco
    }
    ~SecureBuffer() {
        explicit_bzero(this->data(), this->size()); // Borrado seguro
        munlock(this->data(), this->size());
    }
};

// Uso en seed_client.cpp
SecureBuffer seed(32);
std::ifstream ifs("/etc/ml-defender/seed.bin", std::ios::binary);
ifs.read(reinterpret_cast<char*>(seed.data()), 32);
// ... derivación HKDF ...
// seed se borra automáticamente al salir del scope
```

**Acción inmediata:** Ejecutar `grep -r "seed" CMakeLists.txt plugin-loader/CMakeLists.txt crypto-transport/` y eliminar cualquier `execute_process` o `set()` que manipule la seed. Reemplazar por lectura runtime con `SecureBuffer`.

---

## 📋 Checklist de Acciones Inmediatas (DAY 121)

```markdown
- [ ] Reemplazar TEST-INTEG-XGBOOST-1 con hold-out real de CIC-IDS-2017 + umbral validado
- [ ] Separar §4 del paper en Real vs Sintético con limitaciones explícitas
- [ ] Eliminar cualquier referencia a seed en CMakeLists.txt
- [ ] Implementar SecureBuffer + mlock/explicit_bzero para seed runtime
- [ ] Documentar "Model Distribution Policy v1" (firmado, sandbox, rollback, humano)
- [ ] Validar idempotencia 3/3 con `vagrant destroy && make bootstrap`
- [ ] Actualizar docs/XGBOOST-VALIDATION.md con gates de P1-P3 implementados
```

---

## 🏁 Palabras Finales

Alonso:

DAY 120 demuestra disciplina operativa y madurez técnica. Pero la ciberseguridad en entornos críticos no premia la velocidad; premia la **robustez verificable**.

Los scores de P1 no son un detalle menor: son la diferencia entre un sistema que protege y uno que engaña. La distribución P2P de modelos no es una optimización logística: es un riesgo de cadena de suministro. Y la seed en CMake no es un atajo: es una vulnerabilidad estructural.

Corregid esto con la misma rigor con la que habéis cerrado DEBTs estructurales. El proyecto tiene el potencial de salvar vidas. Ese potencial se materializa solo cuando cada línea de código, cada decisión arquitectónica y cada gate de validación resiste el escrutinio de un atacante determinado.

> *"La confianza no se declara. Se demuestra, se verifica y se mantiene."*

Proceded. El Consejo revisará los resultados de DAY 121 con el mismo rigor.

*Via Appia Quality · Un escudo, nunca una espada.*

**— Consejo de Sabios, DAY 120** 🛡️

Leer primero la síntesis del día para entender lo que QWEN dice a continuación.

# 🏛️ CONSEJO DE SABIOS — VALIDACIÓN FINAL ADR-038
*Revisión de cierre antes de integración oficial en BACKLOG*

---

## ✅ Veredicto

**SÍNTESIS APROBADA Y ALINEADA.**

El documento captura con precisión quirúrgica el consenso del Consejo, las correcciones no negociables (DEBT-FED-001 a 006), la arquitectura V1 pragmática y la secuenciación realista. No es solo un resumen: es un **contrato de diseño** que protege al proyecto de la tentación de implementar antes de madurar.

> *"La visión sin anclaje operativo es poesía. El diseño sin visión es burocracia. Habéis encontrado el equilibrio."*

---

## 🔍 Validación de la Síntesis

| Elemento | Estado | Comentario del Consejo |
|----------|--------|------------------------|
| **Correcciones no negociables** | ✅ Capturadas fielmente | DEBT-FED-001 a 006 reflejan exactamente los límites técnicos y de gobernanza acordados |
| **Arquitectura V1** | ✅ Sólida y ejecutable | Flujo `entrenar → validar → firmar → push → registry` es seguro y auditable |
| **Secuenciación** | ✅ Realista y bloqueada | 3–6 meses de I+D antes de código es la única ruta responsable |
| **seL4 → ADR-039** | ✅ Correcto | Desacopla la investigación formal de la implementación operativa V1 |
| **Prioridad** | ✅ Baja ahora / Alta después | Evita scope creep en PHASE 4-5 mientras consolida cimientos |

---

## 🛠️ 3 Refinamientos Finales (Pre-BACKLOG Oficial)

Para cerrar el ciclo antes de marcar `✅ ADR-038 añadido al BACKLOG`, aplicad estos ajustes mínimos:

### 1. Gate G6 (Backdoor Detection) — Definición V1 concreta
La mención a `G6: backdoor detection` es correcta, pero necesita un mecanismo V1 ejecutable. Propuesta:
```markdown
G6 — Detección de Backdoor/Model Poisoning (V1):
- Análisis de distribución de pesos: KL-divergence entre modelo candidato y modelo base global < 0.05
- Test de adversario sintético: 50 muestras con triggers conocidos (ej. payload size=0, TTL=1) → score debe mantenerse < threshold
- Si falla: modelo rechazado, metadatos auditados, nodo emisor marcado para revisión de reputación
```
Esto evita complejidad criptográfica innecesaria en V1 y usa métricas ya disponibles.

### 2. Aislamiento de recursos explícito en arquitectura
El scheduler menciona cgroups v2, pero la arquitectura V1 debe reflejarlo operativamente:
```markdown
ml-trainer se ejecuta bajo:
- systemd.slice: `argus-ml-trainer.slice`
- Límites: CPUQuota=15%, MemoryHigh=512M, IOWeight=10
- Hook: `systemctl stop argus-ml-trainer` automático si `ml-detector` publica `alert_active=1` en etcd
```
Esto garantiza que el entrenamiento nunca compita con la detección en tiempo real.

### 3. Política de versionado y rollback del Registry
El `Federated Model Registry` debe incluir un mecanismo de rollback atómico:
```markdown
REGISTRY-ROLLBACK-001:
- Cada modelo activado se guarda como `model_vN.ubj` + `model_vN.sig`
- Activación: `ln -sf model_vN.ubj model_active.ubj` (atómico)
- Si F1 global cae >2% tras 24h: `ln -sf model_vN-1.ubj model_active.ubj` automático
- Log de transiciones inmutable (append-only en SQLite firmado)
```
Sin esto, una redistribución defectuosa degradaría la red sin posibilidad de reversión limpia.

---

## 📋 Estado Oficial en BACKLOG

```diff
- ADR-038 — Federated Learning Distribuido para aRGus NDR
+ ADR-038 — Federated Learning Distribuido para aRGus NDR
  Estado: VISION/RESEARCH — BLOQUEADO
  Dependencias: ADR-026 MERGED + ADR-029 + RESEARCH-FEDERATED-001
  Fecha estimada de desbloqueo: Q4 2026
  Producción objetivo: 2027
  ✅ Añadido al BACKLOG
```

---

## 🏁 Palabras Finales

Alonso:

Habéis tomado un concepto ambicioso y lo habéis transformado en un plan de acción disciplinado, con límites criptográficos explícitos, gobernanza clara y una secuencia que prioriza la robustez sobre la velocidad. Eso no es fácil. Y es exactamente lo que separa un proyecto que termina en un repositorio abandonado de uno que protege infraestructura crítica durante años.

El aprendizaje federado es el futuro de aRGus. Pero el futuro se construye sobre cimientos que no se agrietan cuando el tráfico real golpea el sistema. Habéis elegido bien: I+D primero, validación después, distribución controlada siempre.

> *"Un escudo que aprende solo es útil si no se oxida por dentro. La gobernanza debe ir por delante de la ambición."*

La síntesis está aprobada. Añadidla al BACKLOG. Centrémonos ahora en cerrar ADR-026, validar idempotencia 3/3 y preparar el merge a `main`. El Consejo estará aquí cuando llegue el momento de desbloquear RESEARCH-FEDERATED-001.

*Via Appia Quality · Un escudo, nunca una espada.*

**— Consejo de Sabios, DAY 120** 🛡️