# ADR-003: ML Autonomous Evolution System

**Date:** November 6, 2025
**Status:** ✅ APPROVED — actualizado DAY 94 (22 marzo 2026)
**Participants:** Alonso (Human/Vision), Claude (AI/Implementation), DeepSeek (AI/Prototyping)

> **Nota de actualización DAY 94:**
> Este ADR ha sido actualizado para incorporar las decisiones de ADR-017
> (Plugin Interface Hierarchy). Los nuevos modelos RF reentrenados se
> despliegan como plugins `InferencePlugin` (`libmodel_*.so`), no como
> ficheros `.hpp` compilados en el core. El core legacy (modelos RF
> embebidos actuales) permanece FROZEN — Strangler Fig Pattern.
> Los validadores de ADR-003 (verify_A..F) son herramientas de CI,
> **no plugins de producción** — fuera del scope de ADR-017.

---

## Context

We have successfully implemented a synthetic data retraining pipeline that
demonstrates measurable improvement (F1: 0.98 → 1.00). Now we need to design
the system for autonomous model evolution — how new models are discovered,
validated, and deployed to production.

---

## Decision Drivers

1. **Life-Critical Infrastructure:** System protects healthcare and critical
   systems where false negatives are unacceptable
2. **Scientific Method:** Embrace experimentation, document failures, learn iteratively
3. **Human-AI Collaboration:** Balance autonomy with human oversight
4. **Open Source Legacy:** Build for future generations to improve upon
5. **Pragmatic Implementation:** See it work first (Phase 0), then make it safe (Phase 1+)

---

## Decisions Made

### 1. Plugin-based Model Deployment

> **Nota crítica DAY 94 — sin recompilación para nuevos modelos:**
> Añadir `libmodel_neris_v2.so` a ml-detector **no requiere recompilar
> ml-detector**. El binario del componente no cambia. Solo se actualiza
> `ml_detector_config.json` con el nuevo plugin en `plugins.enabled`
> y se reprovisiona el par ml-detector↔plugin_nuevo. El canal ZeroMQ
> sniffer↔ml-detector no se ve afectado. Esto es exactamente el valor
> de ADR-017: el sistema crece sin recompilar el core.

 ✅ (actualizado DAY 94)

**Decisión original (DAY 1–88):** Los modelos reentrenados se compilaban
como ficheros `model_*.hpp` integrados en el binario de `ml-detector`.

**Decisión actualizada (DAY 94, ADR-017):** Los nuevos modelos RF reentrenados
se despliegan como plugins `InferencePlugin` siguiendo ADR-017:

```
libmodel_neris_v1.so      ← primer modelo reentrenado (post SYN-5)
libmodel_neris_v2.so      ← iteración siguiente
libmodel_wannacry_v1.so   ← tras FEAT-RANSOM-1
libmodel_ryuk_v1.so       ← tras FEAT-RANSOM-4
```

**Invariante:** El core legacy (modelos RF embebidos actuales) es **FROZEN**.
No se migra. No se toca. Los nuevos modelos extienden el sistema via plugins.
Strangler Fig Pattern.

**Contrato del plugin de modelo (ADR-017):**
```c
// plugin_component_type() = "ml-detector"
// plugin_subtype()        = "inference"

PluginResult plugin_predict(MlDetectorContext* ctx);
// ctx->features    = vector 40 floats
// ctx->scores_out  = vector M scores por clase (write)
// ctx->n_classes   = número de clases
```

El plugin predice. El core del ml-detector decide qué hacer con los scores
según ADR-007 (AND-consensus). Un plugin nunca bloquea directamente.

**JSON is the law — también para plugins de modelo:**
Cada `libmodel_*.so` tiene su fichero JSON de contrato. Si falta cualquier
clave requerida, el plugin falla en carga con error explícito. Sin valores
por defecto silenciosos.

---

### 2. Folder Watching Architecture ✅ (sin cambios)

**Decision:** Use external drop folders (outside build) with file system
watching, rather than hardcoded model paths.

**Actualización DAY 94:** Los drop folders ahora contienen `.so` y sus
ficheros JSON de contrato, no `.hpp` ni `.json` de XGBoost.

```
/usr/lib/ml-defender/plugins/
├── libmodel_neris_v1.so
├── libmodel_neris_v1.json       ← contrato JSON del plugin
├── libmodel_wannacry_v1.so
├── libmodel_wannacry_v1.json
└── ...
```

`ModelWatcher` detecta nuevos `.so` en el directorio. Los carga solo si:
1. El fichero JSON de contrato existe y está completo
2. El HMAC del `.so` es válido (ADR-013, DAY 95-96)
3. El plugin está listado en `ml_detector_config.json` → `plugins.enabled`

---

### 3. Model Specialization Over Replacement ✅ (sin cambios)

**Decision:** Maintain multiple models in ensemble with specialization roles,
rather than replacing old models with new ones.

**Actualización DAY 94:** El ensemble ahora combina:
- Core legacy (FROZEN): RF embebidos compilados — siempre activos
- Plugins (nuevos): `libmodel_*.so` — opcionales, declarados en JSON

El core siempre vota. Los plugins añaden votos adicionales. La lógica
AND-consensus de ADR-007 aplica sobre todos los votos combinados.

---

### 4. Phased Autonomy Approach ✅ (sin cambios estructurales)

**Phases:**
```
Phase 0 (DAY 1–88):  Modelos .hpp compilados en core — validado ✅
Phase 1 (DAY 94+):   Modelos como plugins .so — human-approved promotion
Phase 2 (Q3 2026):   Watchdog + automatic rollback
Phase 3 (Q4 2026):   Advanced validation pipeline
Phase 4 (2027):      Full autonomy
```

**Actualización:** Phase 0 está completa. Phase 1 arranca con ADR-017
implementado — los primeros modelos como plugins serán los reentrenados
tras SYN-5 (FEAT-RANSOM-1, post bare-metal stress test).

---

### 5. Modular Validation Pipeline ✅ (sin cambios — fuera de scope ADR-017)

**Decision:** Validation as pluggable components (verify_A..F).

**Aclaración DAY 94 (ADR-017):** Los validadores verify_A..F son
**herramientas de CI/CD**, no plugins de producción en el sentido de
ADR-017. Se ejecutan en el pipeline de CI antes de promover un modelo.
No se cargan vía `dlopen` en producción. No tienen keypairs ni HMAC de
autenticación de plugin.

```
Pipeline de validación (CI):
    retrain → verify_A → verify_B → verify_C → verify_D → verify_E → promote

Promotion = copiar libmodel_*.so a /usr/lib/ml-defender/plugins/
            + actualizar plugins.enabled en ml_detector_config.json
            + re-provisioning de keypairs (ADR-013)
```

---

### 6. etcd as Orchestration Brain ✅ (actualizado — ADR-013)

**Actualización DAY 94:** etcd-server tiene **responsabilidad única** tras
ADR-013 — gestión del ciclo de vida de componentes y configuración en runtime.
La distribución de seeds criptográficos fue eliminada de etcd-server en ADR-013.

La metadata de modelos (especialización, versión activa, performance) sigue
en etcd, pero las claves criptográficas de los plugins no:

```yaml
# etcd — modelo metadata (sin claves criptográficas)
/ml/models/ml-detector/inference/neris_v1/metadata:
  version: "1.0.0"
  plugin_path: "/usr/lib/ml-defender/plugins/libmodel_neris_v1.so"
  f1_score: 0.9985
  trained_on: "CTU-13 Neris DAY 86"
  status: "active"

# etcd — ensemble config
/ml/ensemble/ml-detector/config:
  active_plugins: ["libmodel_neris_v1.so"]
  voting_strategy: "AND_consensus"    # ADR-007
```

---

### 7. Watchdog for Automatic Rollback ✅ (sin cambios estructurales)

**Actualización DAY 94:** El watchdog opera sobre los plugins cargados.
Un rollback consiste en:
1. Desactivar el plugin degradado en `plugins.enabled`
2. Hacer `dlclose` del `.so`
3. Activar la versión anterior (`libmodel_neris_v1.so` si falló `_v2.so`)
4. No se requiere recompilación — es un cambio de configuración JSON

---

### 8. XGBoost JSON Format Strategy (actualizado DAY 94)

**Decisión original:** Soporte para ONNX y XGBoost JSON en producción.

**Actualización DAY 94:** Los nuevos modelos se despliegan como plugins `.so`
que internamente pueden usar cualquier formato de modelo (ONNX, XGBoost JSON,
sklearn serializado). El formato interno del modelo es un detalle de
implementación del plugin — el contrato externo es siempre:

```c
PluginResult plugin_predict(MlDetectorContext* ctx);
```

El `ml-detector` core no necesita saber si el plugin usa ONNX o XGBoost
internamente. Esta separación elimina la dependencia de versiones específicas
de librerías de ML en el core del pipeline.

---

### 9. Ethical Foundation ✅ (sin cambios — permanente)

**Decision:** Design system with explicit ethical considerations for
life-critical infrastructure.

Este principio es inmutable. Ninguna decisión de ADR posterior puede
comprometer la seguridad de los usuarios finales (pacientes de hospital,
alumnos, empleados de pymes) en nombre de la conveniencia técnica.

**Manifestación en ADR-017/018/019:**
- Type-safety en el hot path (ADR-017) — previene SIGSEGV que tumba el NDR
- AppArmor por plugin (ADR-019) — un plugin comprometido no puede escalar
- Fallo explícito si falta configuración (ADR-017) — sin comportamientos
  silenciosos que comprometan la detección

---

## Validation — estado actualizado DAY 94

**Phase 0 (DAY 1–88) — COMPLETADA ✅**
- Modelo RF embebido → pipeline → clasificación de tráfico ✅
- F1=0.9985, Recall=1.0000 en CTU-13 Neris ✅

**Phase 1 (DAY 94+) — EN CURSO**
- [ ] ADR-017 plugin interface hierarchy — DONE DAY 94
- [ ] Primer plugin de modelo: `libmodel_neris_v2.so` (post SYN-5)
- [ ] Human-approved promotion pipeline

**Phase 2 (Q3 2026) — PENDIENTE**
- [ ] Watchdog + rollback automático sobre plugins
- [ ] Shadow mode testing de nuevos modelos

---

## Open Questions — estado actualizado DAY 94

1. **¿Cuánto tiempo en shadow mode antes de promover a activo?**
   - Pendiente: depende de los datos de SYN-3/SYN-4 — respuesta empírica

2. **¿Cómo detectar modelos maliciosos en un plugin?**
   - Parcialmente resuelto: HMAC + keypairs (ADR-013) + AppArmor (ADR-019)
   - Pendiente: análisis comportamental en shadow mode (verify_D)

3. **¿Cómo explicar decisiones del ensemble cuando votan core + plugins?**
   - ADR-002 (DetectionProvenance) — cada engine vota con su engine_name
   - `libmodel_neris_v1` aparece como `engine_name` en el protobuf

4. **¿Proporciones correctas en el ensemble multi-familia?**
   - Consulta pendiente al Consejo antes de ENT-MODEL-1

---

## References

- ADR-002: Multi-Engine Provenance — DetectionProvenance para plugins
- ADR-007: AND-consensus scoring — aplica a votos de plugins
- ADR-013: Seed Distribution — autenticación de plugins .so
- ADR-017: Plugin Interface Hierarchy — contrato InferencePlugin
- ADR-018: eBPF Kernel Plugin Loader — plugins de kernel-telemetry
- ADR-019: OS Hardening — AppArmor por plugin
- `docs/experiments/f1_replay_log.csv` — source of truth de métricas
- `docs/design/synthetic_data_wannacry_spec.md` — spec SYN-3

---

## Sign-off

**Alonso (Human):** ✅ Approved
**Claude (AI):** ✅ Updated DAY 94
**DeepSeek (AI):** ✅ Original prototyping

**Status:** APPROVED — Phase 1 in progress (plugin-based model deployment)

**Last Review:** DAY 94 — 22 marzo 2026

---

*Co-authored-by: Alonso Isidoro Román + Claude (Anthropic)*
*Consejo de Sabios — ML Defender (aRGus NDR)*
*Original: November 6, 2025 — Actualizado: DAY 94, 22 marzo 2026*