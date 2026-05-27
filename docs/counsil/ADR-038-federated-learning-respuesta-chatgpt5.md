Evaluación directa y exigente del ADR-038.

---

# **ADR-038 — Evaluación del Consejo**

## **Veredicto global**

**CONDICIONAL — NO IMPLEMENTAR todavía.**
Mantener como **línea estratégica + sección de paper**, pero **bloquear implementación** hasta cerrar tres riesgos estructurales: *privacidad, seguridad de agregación y complejidad operativa*.

---

# **Puntos fuertes (bien hechos, mantener)**

### 1. Arquitectura desacoplada (acierto crítico)

* `ml-trainer` es **asíncrono y no bloqueante**
* Scheduler protege misión crítica (muy bien definido)

✔ Esto respeta el principio más importante del sistema:
**el pipeline defensivo nunca puede degradarse por ML**

---

### 2. Fail-gate antes de distribución (G1–G5)

Excelente diseño defensivo:

* Firma Ed25519
* Sandbox 24h
* Rollback automático

✔ Esto evita uno de los mayores riesgos del federated learning:
**propagar modelos malos o maliciosos**

---

### 3. Metadatos aunque falle el modelo

Esto es especialmente sólido:

> separar conocimiento estadístico de modelo entrenado

✔ Muy buena intuición:
permite inteligencia colectiva sin riesgo directo de poisoning.

---

### 4. Scheduler operativo realista

Las condiciones:

```
CPU < 20%
RAM > 512MB
NO_ALERTS
ventana horaria
cooldown días
```

✔ Esto está alineado con entornos hospitalarios reales
✔ No introduce interferencia operacional

---

# **Puntos débiles (críticos)**

## 1. ❌ Riesgo de poisoning federado (GRAVE)

El sistema actual permite:

* Nodo comprometido
* Genera dataset "válido"
* Pasa G2/G3 (estadística plausible)
* Inserta backdoor en modelo

**Problema:**
Los gates actuales **no detectan ataques dirigidos (model poisoning)**.

---

### Ejemplo realista

Un atacante introduce:

```
if dst_port == 104 && payload_signature == X:
    return benign
```

→ comportamiento oculto
→ no afecta métricas globales
→ pasa validaciones
→ backdoor activo

---

### Solución mínima obligatoria

Añadir:

```text
G6: Backdoor detection gate
- Trigger set tests (inputs adversariales conocidos)
- Randomized input probing
- SHAP/feature importance anomaly check
```

---

## 2. ❌ Web-of-trust es insuficiente

> “similar a PGP”

Esto **no escala ni es seguro** en este contexto.

Problemas:

* Difícil revocación
* Confianza subjetiva
* Vulnerable a infiltración progresiva

---

### Recomendación clara

**NO usar web-of-trust**

Usar:

```text
Trust Anchor central (mínimo viable):
- Root public key hardcodeada
- Nodos firmados por esa root
- Rotación vía ADR-024 mechanism
```

✔ Simple
✔ Revocable
✔ Compatible con tu arquitectura actual

---

## 3. ❌ Privacidad diferencial mal definida

Decir:

> ε-differential privacy

sin especificar:

* epsilon
* mecanismo (Laplace / Gaussian)
* sensibilidad

→ es **teóricamente vacío**

---

### Riesgo real

Incluso con hash + agregación:

* dispositivos médicos únicos
* patrones temporales
* correlación externa

→ **re-identificación posible**

---

### Recomendación

Para v1:

```text
NO usar differential privacy aún
```

Usar:

* agregación fuerte (k-anonymity ≥ 20)
* eliminación de outliers únicos
* bucketización agresiva

DP se introduce **solo con experto**.

---

## 4. ❌ Complejidad operacional (tu preocupación — correcta)

Este ADR introduce:

* nuevo componente
* scheduler
* pipeline paralelo
* cifrado adicional
* distribución tipo BitTorrent
* nodos centrales
* validación multi-gate

→ **esto es otro sistema entero dentro del sistema**

---

### Impacto real

Para un operador hospitalario:

* imposible de entender
* difícil de depurar
* alto coste cognitivo

---

### Regla que estás rompiendo

> “El sistema debe ser mantenible por personal no experto”

---

## 5. ❌ BitTorrent como transporte (mala elección aquí)

Problemas:

* puertos bloqueados en hospitales
* comportamiento sospechoso en firewalls
* difícil trazabilidad
* complejidad innecesaria

---

### Sustituto recomendado

```text
HTTPS pull model (simple):
- nodo consulta endpoint central
- descarga modelo firmado
```

✔ auditabilidad
✔ firewall-friendly
✔ simple

---

# **Respuestas a preguntas clave**

## **P1 — Anonimización**

**Respuesta:**
CONDICIONAL — requiere rediseño

* No usar DP en v1
* Usar agregación + bucketización
* DPIA obligatoria antes de producción

---

## **P2 — Web-of-trust**

**Respuesta:**
RECHAZAR

* Sustituir por root trust central
* Integrar con seed_family / ADR-024

---

## **P3 — Agregación federada**

**Respuesta:**
Para XGBoost:

* ❌ FedAvg (no aplica bien)
* ❌ merge de árboles directo

✔ Recomendado:

```text
Model selection:
- entrenar múltiples modelos
- seleccionar mejor en nodo central
```

o:

```text
Dataset aggregation (preferido):
- combinar datasets anonimizados
- reentrenar modelo global
```

---

## **P4 — Scheduler hospitalario**

**Respuesta:**
Lo actual es suficiente para v1

No integrar HIS/RIS aún → complejidad innecesaria

---

## **P5 — Incentivos**

**Respuesta práctica:**

```text
Acceso a modelo global mejorado
```

No compliques esto más en v1.

---

# **Recomendación estructural (clave)**

Dividir ADR-038 en **3 fases reales**:

---

## **FASE 1 (implementable)**

* Solo recolección de metadatos
* Sin modelos
* Sin federated learning real

✔ Bajo riesgo
✔ Alto valor

---

## **FASE 2**

* Dataset sharing anonimizado
* Nodo central entrena modelo

✔ Control total
✔ Sin poisoning distribuido

---

## **FASE 3 (investigación)**

* Federated learning real

✔ Solo cuando todo lo anterior esté probado

---

# **Código orientativo (contrato mínimo seguro)**

```cpp
struct FederatedMetadata {
    uint32_t feature_id;
    float mean;
    float stddev;
    uint32_t count;
};

struct FederatedPayload {
    uint32_t version;
    uint32_t k_anonymity; // >= 20
    std::vector
```
