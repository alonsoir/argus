# Consejo de Sabios — DAY 118 (15 Abril 2026)

Buenos días Consejo. Soy Alonso (aRGus NDR, ML Defender).

## Lo que hemos completado hoy

### PHASE 3 — CERRADA ✅

- **AppArmor enforce 6/6** — sniffer promovido a enforce con `apparmor-promote.sh`.
  0 denials en 300s de monitorización. `make test-all` verde. `aa-status` confirma
  6/6 componentes en enforce mode.
- **noclobber audit** — auditoría de redirects `>` en `provision.sh` sobre rutas
  críticas (`/etc/`, `.sk`, `seed.bin`, `.sig`). Resultado limpio, sin cambios necesarios.
- **CHANGELOG-v0.4.0.md** — creado y commiteado en `docs/`.
- **`git merge --no-ff` feature/phase3-hardening → main** — trazabilidad científica
  completa. Tag `v0.4.0-phase3-hardening` pusheado.
- **README.md + BACKLOG.md** actualizados. Badge AppArmor → 6/6 enforce.
  ASCII art architecture envuelto en code block (rendering fix).

### PHASE 4 — ABIERTA

- **`feature/adr026-xgboost`** creada y pusheada.
- **`docs/XGBOOST-VALIDATION.md`** — checklist 7 fases, 35 checkboxes, gate médico
  inamovible: Precision ≥ 0.99 + F1 ≥ 0.9985 en CTU-13 Neris (4 runs mínimo).
- **XGBoost 3.2.0 instalado manualmente en VM**:
    - `libxgboost.so` → `/usr/local/lib/` + ldconfig ✅
    - `c_api.h` + `base.h` → `/usr/local/include/xgboost/` ✅
    - Test compilación C con `-lxgboost` → OK ✅
- **DEBT-XGBOOST-PROVISION-001 resuelto en Vagrantfile** — bloque de provisioning
  insertado tras FAISS: `pip3 install xgboost==3.2.0`, curl headers, cp libxgboost.so,
  ldconfig. Reproducible desde `vagrant destroy && vagrant up`.
- **`plugins/xgboost/` creado**:
    - `CMakeLists.txt`: find xgboost headers + libxgboost.so, linkado correcto,
      ruta modelo compilada `MLD_XGBOOST_MODEL_PATH`.
    - `xgboost_plugin.cpp`: skeleton fail-closed. `plugin_init` carga modelo con
      `XGBoosterLoadModel` + `std::terminate()` si falla. `plugin_invoke` y
      `plugin_destroy` implementados. Inferencia real pendiente Fase 3.

---

## Lo que haremos mañana — DAY 119

### PASO 0 especial — prueba Vagrantfile desde cero
```
vagrant destroy -f
vagrant up
# Verificar XGBoost instalado automáticamente
ldconfig -p | grep xgboost        → esperar: /usr/local/lib/libxgboost.so
python3 -c 'import xgboost; print(xgboost.__version__)'  → esperar: 3.2.0
```

### PASO 1 — Compilar plugin_xgboost
```
make pipeline-build    # incluye plugins/xgboost/
make sign-plugins      # firma libplugin_xgboost.so con Ed25519
make test-all          # CI gate completo
```

### PASO 2 — Fase 2: entrenamiento offline XGBoost en CTU-13 Neris
- Localizar el dataset CTU-13 Neris y el feature set exacto del RF baseline
- Script Python de entrenamiento XGBoost con el mismo split train/test
- Exportar modelo a `/etc/ml-defender/models/xgboost_ctu13.json`
- Registrar métricas: F1, Precision, Recall, FPR

### PASO 3 — Fase 3: feature extraction en plugin_invoke
- Implementar extracción de features desde `MessageContext`
- Construir `DMatrix` para inferencia XGBoost C API
- Test de inferencia end-to-end con pipeline 6/6 RUNNING

---

## Preguntas abiertas para el Consejo

### Q1 — Feature set: ¿mismo que RF o recalcular?

El baseline RF usa un feature set específico extraído de CTU-13 Neris.
Para la comparativa RF vs XGBoost sea científicamente válida, ¿debemos:

**Opción A:** Usar exactamente el mismo feature set que el RF (apple to apple).
**Opción B:** Dejar que XGBoost seleccione features óptimas (feature importance)
y documentar el delta como contribución adicional.

Mi intuición: Opción A primero para la comparativa limpia, Opción B como
experimento secundario. ¿El Consejo está de acuerdo?

### Q2 — Formato del modelo: JSON vs binary

XGBoost soporta dos formatos de serialización:
- **JSON** (`model.save_model("model.json")`) — legible, versionable en git,
  pero ~3× más grande que binary.
- **Binary** (`model.save_model("model.ubj")`) — compacto, más rápido de cargar,
  opaco.

Para un sistema open-source con auditoría científica como aRGus NDR,
¿JSON o binary? ¿O ambos (binary en producción, JSON en repo)?

### Q3 — `plugin_invoke` y el MessageContext

El `MessageContext` actual transporta el payload de mensajes ZeroMQ cifrados.
XGBoost necesita un vector de features numéricas (float32).

¿Cómo debe estructurarse la extracción de features desde `MessageContext`?
Opciones:
**Opción A:** El plugin deserializa el payload directamente (acoplamiento fuerte).
**Opción B:** ml-detector pre-procesa y pasa features ya extraídas en el payload
(separación de responsabilidades).
**Opción C:** Nuevo campo `features[]` en `MessageContext` (cambio de API).

¿Cuál preferís arquitectónicamente? Opción B me parece más limpia pero
implica cambiar ml-detector antes del plugin.

### Q4 — Vagrantfile: ¿XGBoost como apt o siempre via pip?

El bloque actual usa `pip3 install xgboost==3.2.0 --break-system-packages`.
Debian Bookworm tiene `python3-xgboost` en apt pero en versión antigua (~1.7).
¿Fijamos versión exacta 3.2.0 via pip (actual) o añadimos fallback apt
para entornos sin acceso a PyPI? Contexto: hospitales con firewalls restrictivos.

---

## Contexto permanente

- arXiv:2604.04952 (Draft v15) — activo
- Pubkey dev: `e51a91e91d72f74fe97e8a4eb883c9c6eb41dd2fc994feaf59d5ba2177720f3d`
- Rama activa: `feature/adr026-xgboost`
- main @ `v0.4.0-phase3-hardening` (da0296cd)
- Pipeline: 6/6 RUNNING · AppArmor 6/6 enforce · make test-all VERDE

*"Via Appia Quality — un escudo, nunca una espada."*

Pregunta para Gemini en segunda ronda:

Gemini, segunda ronda DAY 118 — OBS-4:
Propusiste Soft-Fail en plugin_init: si el modelo XGBoost no carga, ml-detector continúa con RF baseline en lugar de std::terminate().
El resto del Consejo no contradijo fail-closed. Necesito tu posición más desarrollada:

¿El soft-fail es obligatorio para v0.1 o es una mejora post-gate médico?
¿Cómo implementarías el fallback RF en ml-detector sin romper la arquitectura de plugin-loader?
¿El modelo XGBoost sin carga pero con RF activo sigue cumpliendo el gate Precision ≥ 0.99? ¿O ese escenario es simplemente "XGBoost desactivado, RF como único clasificador"?
¿std::terminate() es aceptable en v0.1 si el operador garantiza que el modelo existe antes de arrancar el pipeline (que es lo que hace provision.sh)?

