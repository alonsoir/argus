Evaluación directa y accionable del DAY 118 y de las decisiones abiertas.

---

# Evaluación general (DAY 118)

**Fortalezas claras**

1. **Cierre de PHASE 3 sólido y verificable**

  * AppArmor 6/6 enforce sin denials + rollback probado → estado de producción realista.
  * `TEST-PROVISION-1` + invariantes → ya es un **sistema operable**, no solo código.
  * `noclobber` + audit → evita clase entera de errores silenciosos (muy buen movimiento).

2. **Disciplina de seguridad coherente**

  * Fail-closed consistente (plugins, reset, loader).
  * Separación dev/prod ya interiorizada (clave para futuro mantenimiento).

3. **Entrada en PHASE 4 bien estructurada**

  * Checklist XGBoost con gates cuantitativos estrictos → enfoque científico correcto.
  * Instalación reproducible en Vagrant → evita “works on my machine”.

---

**Debilidades / Riesgos**

1. **Complejidad operativa creciente**

  * Ya tienes: Ed25519 + AppArmor + provision + invariantes + plugins + ahora ML.
  * Sin control, el sistema puede volverse difícil de mantener para terceros.

2. **Acoplamiento potencial ML ↔ pipeline**

  * Riesgo en `plugin_invoke` + extracción de features.
  * Si se hace mal, rompe la modularidad lograda en PHASE 2–3.

3. **Dependencia externa (XGBoost runtime)**

  * `pip --break-system-packages` no es aceptable en producción hospitalaria.
  * Necesitas estrategia de distribución más robusta.

---

# Respuestas a las preguntas

---

## Q1 — Feature set

**Veredicto: ACEPTAR A → luego B como experimento separado**

**Justificación**

* Necesitas comparabilidad científica directa con el baseline RF.
* Cambiar features invalida la comparación.
* XGBoost ya optimiza internamente (boosting), no necesitas cambiar features inicialmente.

**Riesgo si ignoras esto**

* Resultados no publicables / no defendibles académicamente.

**Recomendación concreta**

```text
FASE 1 (obligatoria):
- Mismo dataset
- Mismo split
- Mismas features

FASE 2 (opcional, paper v2):
- Feature importance XGBoost
- Ablation study
```

---

## Q2 — Formato del modelo

**Veredicto: CONDICIONAL → ambos (JSON + binary)**

**Recomendación técnica**

* Repo:

  * JSON (auditable, versionable)
* Producción:

  * Binary (`.ubj`) firmado con Ed25519

**Patrón recomendado**

```
model/
 ├── xgboost_ctu13.json   (audit / git)
 ├── xgboost_ctu13.ubj    (runtime)
 └── xgboost_ctu13.sig
```

**Código ejemplo (C API)**

```c
// Prefer binary en runtime
if (XGBoosterLoadModel(booster, "model.ubj") != 0) {
    fprintf(stderr, "Failed to load binary model\n");
    exit(1);
}
```

**Riesgo si usas solo JSON**

* Mayor latencia de carga
* Mayor superficie de parsing

---

## Q3 — MessageContext / extracción de features

**Veredicto: ACEPTAR B (ml-detector preprocesa)**

**Esta decisión es crítica.**

---

### Por qué B es correcta

* Mantiene **single responsibility**
* Evita duplicación de lógica de features
* Permite:

  * RF
  * XGBoost
  * futuros modelos

---

### Diseño recomendado (con código)

**Extensión de MessageContext (NO romper API existente):**

```cpp
struct FeatureVector {
    std::vector<float> values;
    uint32_t version;  // importante para compatibilidad
};

struct MessageContext {
    // existente
    std::vector<uint8_t> payload;

    // nuevo (opcional)
    std::optional<FeatureVector> features;
};
```

---

### ml-detector

```cpp
FeatureVector extract_features(const PacketBatch& batch) {
    FeatureVector fv;
    fv.version = 1;

    fv.values = {
        batch.packet_count,
        batch.avg_packet_size,
        batch.syn_ratio,
        batch.udp_ratio,
        // mismas features que RF
    };

    return fv;
}
```

---

### plugin_xgboost

```cpp
extern "C" int plugin_invoke(MessageContext* ctx) {
    if (!ctx->features.has_value()) {
        // fail-closed
        return -1;
    }

    const auto& f = ctx->features.value().values;

    DMatrixHandle dmat;
    XGDMatrixCreateFromMat(f.data(), 1, f.size(), -1, &dmat);

    bst_ulong out_len;
    const float* out_result;

    XGBoosterPredict(booster, dmat, 0, 0, &out_len, &out_result);

    // usar resultado
    return 0;
}
```

---

**Riesgo si eliges A**

* Acoplamiento fuerte
* Bugs duplicados
* Imposible evolucionar features sin romper plugins

---

## Q4 — Vagrantfile / instalación XGBoost

**Veredicto: CONDICIONAL → evitar pip en producción**

---

### Problema actual

```bash
pip3 install xgboost --break-system-packages
```

Esto es:

* No reproducible a largo plazo
* Problemático en entornos restringidos
* Riesgo de supply chain

---

### Estrategia recomendada

**Nivel 1 — desarrollo (OK actual)**

* pip → válido

**Nivel 2 — staging/producción**

Opción recomendada:

```
vendor/xgboost/
 ├── libxgboost.so
 ├── headers/
 └── VERSION
```

Y en provisioning:

```bash
cp vendor/xgboost/libxgboost.so /usr/local/lib/
ldconfig
```

---

### Alternativa robusta

* Construir `.deb` interno:

```bash
dpkg-deb --build xgboost_3.2.0/
```

---

**Riesgo si mantienes pip**

* Entornos hospitalarios sin internet → fallo de despliegue
* No reproducibilidad exacta

---

# Observaciones adicionales importantes

---

## 1. plugin_xgboost fail-closed — correcto, pero incompleto

Añade logging estructurado:

```cpp
if (XGBoosterLoadModel(...) != 0) {
    log_critical("xgboost: model load failed");
    std::terminate();
}
```

---

## 2. Falta: TEST-INTEG-XGBOOST-1

Debes añadir YA:

```
Caso:
- features válidas
- modelo cargado

Esperado:
- inferencia correcta
- no crash
```

---

## 3. Latencia

XGBoost en CPU ARM puede ser cuello de botella.

Añade métrica desde el inicio:

```cpp
auto start = std::chrono::high_resolution_clock::now();
// predict
auto end = ...
```

---

## 4. Firma del modelo (CRÍTICO)

El modelo es código ejecutable en la práctica.

Debe seguir mismo esquema que plugins:

```
xgboost_ctu13.ubj
xgboost_ctu13.ubj.sig
```

Y verificación antes de cargar.

---

# Conclusión clara

Estás en un punto muy sólido:

* PHASE 3 → sistema seguro y operable
* PHASE 4 → riesgo principal = complejidad, no seguridad

Las decisiones correctas ahora son:

1. **Mantener simplicidad (no romper arquitectura)**
2. **Separar ML de transporte**
3. **Controlar dependencias externas**
4. **Preservar comparabilidad científica**

Si mantienes eso, el proyecto sigue en trayectoria excelente.

---

Si quieres, en el siguiente paso puedo diseñarte:

* el contrato exacto `FeatureVector v1`
* el test de validación científica RF vs XGBoost
* o el flujo completo de firma/verificación de modelos (igual que plugins)

sin añadir complejidad innecesaria.
