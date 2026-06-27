## Consejo de Sabios — ADR-040 (ML Plugin Retraining Contract)

Evaluación bajo criterios de: **validez científica, reproducibilidad, robustez frente a deriva y adversarios**.

---

# Veredicto general

* El ADR está **bien fundamentado** y alineado con buenas prácticas reales de ML en producción.
* No hay errores conceptuales graves.
* Sí hay **dos mejoras estructurales necesarias**:

    1. Separación estricta entre evaluación y runtime
    2. Formalización experimental (no solo reglas, también métricas longitudinales)

---

# Respuesta a la pregunta clave

## ¿Pipeline de evaluación interno o CI/CD externo?

### Veredicto del Consejo: **Opción híbrida obligatoria**

Ni A ni B por sí solas son suficientes.

---

## Arquitectura recomendada

### 1. Núcleo reproducible (interno a aRGus)

✔ Debe existir **dentro del repositorio**

Incluye:

* script walk-forward
* evaluación golden set
* cálculo métricas
* guardrail logic

Ejemplo:

```bash
make eval-plugin MODEL=xgboost_v3
```

---

### 2. Orquestación (externa, CI/CD)

✔ Debe ejecutarse en:

* GitHub Actions o equivalente

Responsabilidades:

* ejecutar evaluación
* registrar resultados
* decidir:

    * PROMOTE / HOLD / REJECT
* bloquear firma si falla

---

## Justificación científica

Separar:

| Nivel   | Función                       |
| ------- | ----------------------------- |
| Interno | reproducibilidad experimental |
| Externo | gobernanza y trazabilidad     |

Si no separas:

* pierdes auditabilidad
* introduces sesgos manuales

---

## Riesgo si eliges solo una opción

### Solo A (interno)

* ❌ sin histórico verificable
* ❌ fácil bypass manual

### Solo B (CI)

* ❌ pérdida de reproducibilidad local
* ❌ dependencia de infraestructura externa

---

## Test mínimo reproducible

```bash
# local
make eval-plugin MODEL=candidate

# CI (automático)
on push:
  run eval
  if fail → block signing
```

---

# Evaluación de las reglas del ADR

---

## Regla 1 — Walk-forward

### Veredicto: 🟢 Correcta y crítica

### Mejora recomendada

Añadir:

* **múltiples cortes temporales**, no solo uno

```text
T1, T2, T3...
```

---

### Riesgo actual

* un único split → varianza alta

---

### Test reproducible

```bash
--split-date 2024-01-01
--split-date 2024-03-01
--split-date 2024-06-01
```

Promediar métricas.

---

## Regla 2 — Golden Set

### Veredicto: 🟢 Excelente, pero incompleta

---

### Mejora crítica

Dividir en dos:

| Tipo                       | Uso            |
| -------------------------- | -------------- |
| Golden set (fijo)          | regresión      |
| Evaluation set (evolutivo) | generalización |

---

### Riesgo actual

* overfitting al golden set

---

### Test

* evaluar ambos sets
* comparar drift

---

## Regla 3 — Guardrail −2%

### Veredicto: 🟢 Correcto, pero incompleto

---

### Mejora obligatoria

Añadir:

### ➤ Métrica adicional:

```text
Precision ≥ −2 pp
```

---

### ➤ Regla crítica nueva:

**“No regression on rare classes”**

Ejemplo:

* ataques poco frecuentes
* no deben degradarse aunque F1 global suba

---

### Riesgo actual

* modelo mejora global → empeora casos raros

---

## Regla 4 — IPW + exploración

### Veredicto: 🟢 Muy sólido (nivel producción real)

---

### Mejora

Formalizar:

```text
Exploration ratio ∈ [3%, 10%]
```

Adaptativo según:

* drift detectado

---

### Añadir métrica nueva

```text
Data diversity index (Shannon entropy o similar)
```

---

### Riesgo

* etiquetado manual insuficiente
* sesgo humano

---

## Regla 5 — Competición de algoritmos

### Veredicto: 🟢 Correcto y científicamente obligatorio

---

### Mejora

Añadir criterio explícito:

| Métrica  | Peso |
| -------- | ---- |
| Recall   | 40%  |
| F1       | 30%  |
| Latencia | 20%  |
| RAM      | 10%  |

---

### Riesgo

* elegir modelo por F1 → ignorar latencia

---

# Mejora crítica faltante (no incluida en ADR)

## 🔴 Regla 6 — Dataset lineage obligatorio

Todo modelo debe registrar:

```text
- dataset hash
- features version
- preprocessing version
- training code commit
```

---

### Justificación

Sin esto:

* no hay reproducibilidad científica real

---

# Mejora crítica 2

## 🔴 Regla 7 — Canary deployment

Antes de producción:

* desplegar modelo en:

    * 5–10% del tráfico

Comparar:

* decisiones vs modelo anterior

---

### Riesgo actual

* salto directo a producción

---

# Evaluación global ADR-040

| Área                   | Estado       |
| ---------------------- | ------------ |
| Fundamento científico  | ✔ sólido     |
| Reproducibilidad       | ✔ alta       |
| Robustez ML            | ✔ alta       |
| Seguridad operativa    | ⚠ mejorable  |
| Preparación para paper | ✔ publicable |

---

# Recomendación final del Consejo

Adoptar ADR-040 con estas modificaciones:

1. Arquitectura híbrida (interno + CI)
2. Multi-split walk-forward
3. Golden set + evaluation set
4. Guardrail ampliado (precision + rare classes)
5. Dataset lineage obligatorio
6. Canary deployment antes de producción

---

# Veredicto

El ADR está en el **nivel correcto para sistemas críticos reales**.

Con los ajustes propuestos:

* pasa de “buen diseño”
  a
* **sistema científicamente defendible y auditable**

---

Esto no es solo ML en producción.
Es ML tratado como infraestructura crítica, que es exactamente lo que necesitas.
