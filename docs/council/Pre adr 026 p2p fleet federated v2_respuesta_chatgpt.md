Evaluación técnica directa del PRE-ADR-026. El planteamiento es sólido; la asimetría nodo/servidor está bien fundamentada y alineada con el dominio (infraestructura crítica con recursos limitados). A continuación, revisión implacable por puntos.

---

# 🧠 Evaluación global

**Fortalezas claras:**

* Separación correcta:

    * detección → modelos tabulares
    * explicabilidad → LLM
* Asimetría nodo/servidor bien justificada
* Uso de plugins firmados (hereda bien ADR-025)
* BitTorrent bien acotado (solo distribución)

**Riesgo principal:**

> Estás subestimando la complejidad operativa del pipeline de datos (schema, validación, drift, privacidad).
> Ese es el verdadero cuello de botella, no el ML.

---

# 🔎 Respuestas del Consejo

---

## Q1 — Versionado del schema CSV

**Respuesta: SÍ, bloqueante duro.**

Sin esto:

* no puedes reentrenar consistentemente
* no puedes comparar modelos
* no puedes reproducir resultados
* invalidas valor científico del dataset

**Recomendación concreta:**

Definir YA:

```text
schema_version: uint16
feature_set_id: hash
normalization_version: uint8
```

Y añadir:

* compatibilidad hacia atrás (mínimo 2 versiones)
* migradores de schema

👉 Esto no es deuda técnica. Es **infraestructura crítica**.

---

## Q2 — Protocolo nodo → servidor

**Recomendación clara: HTTPS (simple) o gRPC ligero**

### Comparativa real:

| Protocolo | Pros                       | Contras                      | Veredicto |
| --------- | -------------------------- | ---------------------------- | --------- |
| ZeroMQ    | ya lo tienes               | complejo, difícil de auditar | ❌         |
| gRPC      | eficiente, tipado          | overhead + protobuf          | ⚠️        |
| HTTPS     | simple, robusto, auditable | algo más lento               | ✅         |

👉 Para hospitales:

> **menos moving parts > más rendimiento**

**Decisión recomendada:**

* HTTPS + compresión (LZ4/zstd)
* batch uploads (no streaming continuo)

---

## Q3 — Thresholds de validación

**F1 > 0.99 es peligroso como regla fija.**

Problemas:

* datasets desbalanceados → F1 engañoso
* overfitting silencioso
* no captura falsos positivos reales

**Recomendación realista:**

```text
F1 > 0.95
FPR < 0.01
Recall > 0.97
```

Y además:

* validación cruzada multi-dataset
* test en datos “out-of-distribution”

👉 Añadir:

```text
canary deployment obligatorio antes de distribución global
```

---

## Q4 — Privacidad (crítico en hospitales)

**Hash de IP NO es suficiente.**

Porque:

* reidentificable (patrones de tráfico)
* correlación temporal
* ataques de diccionario

**Necesitas mínimo:**

* hashing con salt rotatorio
* truncado de IP (/24 o /16)
* eliminación de payloads
* revisión legal LOPD/GDPR

👉 Esto es **bloqueante antes de producción real**.

---

## Q5 — FT-Transformer vs XGBoost

**Respuesta clara: XGBoost primero.**

FT-Transformer:

* más complejo
* más difícil de explicar
* peor en datasets pequeños/ruidosos

En NDR real:

> XGBoost gana en 80% de escenarios tabulares prácticos

**Recomendación:**

* Año 1: RF + XGBoost
* Año 2: evaluar FT-Transformer con benchmarks reales tuyos

---

## Q6 — Modelo para vLLM

Comparativa práctica:

| Modelo       | Pros       | Contras             | Veredicto |
| ------------ | ---------- | ------------------- | --------- |
| Phi-3 Mini   | ligero     | menos robusto       | ⚠️        |
| Mistral 7B   | equilibrio | requiere GPU seria  | ✅         |
| Llama 3.1 8B | potente    | más pesado/licencia | ⚠️        |

**Recomendación:**

👉 **Mistral 7B fine-tuneado**

Porque:

* buen razonamiento estructurado
* comunidad madura
* encaja con vLLM

---

## Q7 — Ciclo de vida de plugins (CRÍTICO)

Ahora mismo esto está incompleto.

Necesitas:

### 1. Versionado fuerte

```text
plugin_name: rf_wannacry
version: semver
model_hash: sha256
```

### 2. Canary deployment

* 5–10% nodos
* monitorizar métricas reales

### 3. Rollback automático

```text
si FPR ↑ o errores ↑ → revertir versión anterior
```

### 4. TTL de modelos

* invalidación automática tras X días

👉 Sin esto, el sistema no es operativo a escala.

---

# ⚠️ Observaciones críticas adicionales

---

## 1. “Federated learning” está mal planteado (importante)

Lo que describes NO es FL clásico.

Es:

> **centralized learning con data aggregation**

Y eso es correcto para tu caso.

**No intentes meter FL ahora**:

* complejidad enorme
* problemas de privacidad (gradient leakage)
* no encaja con nodos débiles

👉 Decisión correcta: evitar FL en fase inicial.

---

## 2. BitTorrent — cuidado con el threat model

Problema:

* nodo comprometido puede servir binarios corruptos

Mitigación (ya alineada con ADR-025):

* verificación Ed25519 obligatoria
* hash del modelo

👉 Asegúrate de que:

```text
NUNCA se ejecuta nada sin verificación
```

---

## 3. Dataset como activo estratégico (muy acertado)

Esto es clave:

> CTU-13 fue académico → tú puedes tener dataset real moderno

Pero implica:

* responsabilidad legal
* governance del dato
* control de acceso

👉 Esto merece un ADR propio.

---

# 🧭 Conclusión del Consejo

## Decisiones claras

* ✅ Asimetría nodo/servidor → CORRECTA (mantener)
* ✅ RF specialists como plugins → CORRECTO
* ✅ BitTorrent para distribución → CORRECTO (con firma obligatoria)
* ❌ Federated Learning → POSPONER
* ⚠️ LLM → solo capa de explicabilidad

---

## Bloqueantes reales (no negociables)

1. Versionado de schema CSV
2. Política de privacidad (LOPD/GDPR)
3. Lifecycle completo de plugins (canary + rollback)
4. Definición de métricas de validación realistas

---

## Insight final (importante)

El valor de tu sistema no va a venir de:

* LLMs
* FT-Transformers
* arquitecturas sofisticadas

Va a venir de:

> **calidad del pipeline de datos + control del ciclo de vida de modelos**

---

Si quieres, el siguiente paso lógico es diseñar:

👉 **ADR-026b: Model Lifecycle & Telemetry Governance**

Ahí está el verdadero núcleo del sistema que estás construyendo.
