# Consejo de Sabios — DAY 118 — Síntesis de Veredictos

*5/7 modelos respondieron. Parallel.ai sin respuesta (patrón habitual).*
*Nota: archivo qwen responde como "DeepSeek" — patrón consolidado.*

---

## Q1 — Feature set: ¿mismo que RF o recalcular?

**UNANIMIDAD (5/5): Opción A primero.**

Mismo feature set que el RF baseline. La única variable que cambia es el
algoritmo. Si cambian los features, el delta de métricas no es atribuible
al modelo → no publicable.

Opción B (XGBoost feature importance) como experimento secundario,
documentado en ablation study. No bloquea el gate médico.

**Acción DAY 119:** localizar el feature extractor exacto del RF baseline
en ml-detector y replicarlo en el script Python de entrenamiento.

---

## Q2 — Formato del modelo: JSON vs binary

**UNANIMIDAD (5/5): JSON en repo, .ubj en producción.**

- `xgboost_ctu13.json` → git, auditoría científica, diff-friendly
- `xgboost_ctu13.ubj` → runtime C API, ~3× más rápido de cargar
- `xgboost_ctu13.ubj.sig` → firma Ed25519 (ver observación adicional #2)

DeepSeek propone fallback en plugin_init: intentar .ubj primero, JSON si
no existe.

```cpp
if (access((model_path + ".ubj").c_str(), F_OK) == 0)
    XGBoosterLoadModel(booster, (model_path + ".ubj").c_str());
else
    XGBoosterLoadModel(booster, (model_path + ".json").c_str());
```

---

## Q3 — plugin_invoke y MessageContext

**UNANIMIDAD (5/5): Opción B — ml-detector pre-procesa.**

ml-detector extrae features (mismas que RF) y las serializa como
`float32[]` en el payload. El plugin XGBoost recibe el vector,
construye DMatrix y llama XGBoosterPredict. Plugin agnóstico al
formato del mensaje ZeroMQ.

ChatGPT5 propone `std::optional<FeatureVector>` en MessageContext
sin romper API existente. DeepSeek y Qwen proponen serialización
directa como `float*` en payload. Grok: campo opcional en
MessageContext.

**Decisión del árbitro (Alonso):** pendiente — discutir DAY 119.
Punto de debate: modificar MessageContext (struct) vs usar payload
como canal de features.

---

## Q4 — Vagrantfile: pip vs apt

**Mayoría (4/5): pip 3.2.0 primero + fallback apt + documentación offline.**

ChatGPT5 es el más estricto: propone vendorizar libxgboost.so en el
repo para hospitales air-gapped.

**Consenso práctico:**
1. pip install xgboost==3.2.0 --break-system-packages (primero)
2. Fallback: apt-get install python3-xgboost (con WARNING de versión)
3. Documentar en docs/OFFLINE-DEPLOYMENT.md cómo precargar el .whl
4. Para producción hospitalaria real: compilar desde fuente en build
   pipeline controlada y distribuir solo el .so firmado

**Acción DAY 119:** añadir fallback apt al bloque Vagrantfile.

---

## Observaciones adicionales — Items mandatorios

### OBS-1 — Firma del modelo (ChatGPT5, CRÍTICO)
El modelo XGBoost es código ejecutable en la práctica. Debe seguir el
mismo esquema que los plugins:
```
xgboost_ctu13.ubj
xgboost_ctu13.ubj.sig  (Ed25519, mismo esquema ADR-025)
```
Verificación antes de XGBoosterLoadModel. **Bloqueante para merge.**

### OBS-2 — TEST-INTEG-XGBOOST-1 (ChatGPT5 + DeepSeek)
Añadir test en `make test-all`:
- Cargar modelo (juguete en CI, real en validación)
- Llamar plugin_invoke con MessageContext sintético
- Verificar que salida ∈ [0,1] y no NaN
  **Bloqueante para merge.**

### OBS-3 — Latencia desde el primer día (ChatGPT5)
```cpp
auto start = std::chrono::high_resolution_clock::now();
// predict
auto end = std::chrono::high_resolution_clock::now();
```
Métricas de latencia en cada inferencia desde Fase 3. Para la
tabla comparativa RF vs XGBoost en el paper.

### OBS-4 — std::terminate() en plugin_init: DEBATE ABIERTO
**Gemini (único):** propone Soft-Fail — si modelo no carga, plugin
devuelve error, ml-detector continúa con RF baseline en lugar de
terminar. Más resiliente para sistema crítico.

**ChatGPT5, DeepSeek, Grok, Qwen:** no contradicen fail-closed.
El Consejo no alcanza unanimidad en este punto.

**Posición actual (fail-closed):** `std::terminate()` es consistente
con ADR-025 y el diseño del sistema. Soft-Fail requiere que ml-detector
tenga lógica de fallback RF → mayor complejidad.

**Decisión del árbitro (Alonso):** pendiente. Preguntar al Consejo
DAY 119 si fail-closed es aceptable para v0.1 y soft-fail va a backlog.

### OBS-5 — Contratos informales para ADR-036 (Grok)
Añadir ya en xgboost_plugin.cpp:
```cpp
// @requires: ctx != nullptr && ctx->payload != nullptr
// @ensures: return_value == PLUGIN_OK || PLUGIN_FAIL_CLOSED
// @invariant: no side effects on MessageContext si falla
```
No bloqueante. Coste cero. Prepara ADR-036 formal verification.

### OBS-6 — Cache del modelo en plugin_init (Qwen)
```cpp
static std::unique_ptr<BoosterHandle> cached_model;
if (!cached_model) { XGBoosterLoadModel(...); }
```
Evitar reload en cada invocación. No bloqueante para Fase 1.

---

## Items mandatorios para merge a main (actualizados)

| Gate | Umbral | Estado |
|------|--------|--------|
| F1-score CTU-13 Neris | ≥ 0.9985 | ⏳ |
| Precision | ≥ 0.99 | ⏳ |
| Recall | ≥ 0.99 | ⏳ |
| FPR | ≤ 0.001 | ⏳ |
| Latencia por inferencia | ≤ 2× baseline RF | ⏳ |
| Plugin firmado Ed25519 | obligatorio | ⏳ |
| **Modelo firmado Ed25519** | **obligatorio (OBS-1)** | ⏳ |
| TEST-INTEG-XGBOOST-1 | obligatorio (OBS-2) | ⏳ |
| make test-all verde | obligatorio | ⏳ |
| Revisión Consejo | unanimidad/mayoría | ⏳ |

---

---

# ML Defender (aRGus NDR) — DAY 119 Continuity Prompt

Buenos días Claude. Soy Alonso (aRGus NDR, ML Defender).

## POLÍTICA DE DEUDA TÉCNICA

- **Bloqueante:** debe cerrarse en esta feature. No hay merge a main sin test verde.
- **No bloqueante:** asignada a feature destino en BACKLOG. No toca esta feature.
- **Toda deuda tiene test de cierre.**

---

## Estado al cierre de DAY 118

### Hitos completados
- PHASE 3 CERRADA ✅ — `git merge --no-ff` + tag `v0.4.0-phase3-hardening` (da0296cd)
- AppArmor 6/6 enforce (0 denials) ✅ · make test-all VERDE ✅
- CHANGELOG-v0.4.0.md ✅ · README + BACKLOG actualizados ✅
- `feature/adr026-xgboost` abierta ✅
- `docs/XGBOOST-VALIDATION.md` creado ✅
- XGBoost 3.2.0 instalado manualmente en VM ✅
  - `/usr/local/lib/libxgboost.so` + `/usr/local/include/xgboost/` ✅
  - Compilación C con `-lxgboost` OK ✅
- DEBT-XGBOOST-PROVISION-001 en Vagrantfile (bloque tras FAISS, líneas 327-348) ✅
- `plugins/xgboost/CMakeLists.txt` + `xgboost_plugin.cpp` skeleton ✅
  - Commit: `9500300a` en `feature/adr026-xgboost`

### Consejo DAY 118 — Veredictos (5/7 respondieron)
- Q1 feature set: **UNANIMIDAD Opción A** — mismo feature set que RF baseline
- Q2 formato modelo: **UNANIMIDAD** — JSON en repo, .ubj en producción
- Q3 plugin_invoke: **UNANIMIDAD Opción B** — ml-detector pre-procesa features
- Q4 Vagrantfile: **Mayoría** — pip 3.2.0 + fallback apt + docs offline

### Items mandatorios añadidos por el Consejo
- OBS-1: Firma Ed25519 del modelo (.ubj.sig) — bloqueante para merge
- OBS-2: TEST-INTEG-XGBOOST-1 — bloqueante para merge
- OBS-3: latencia desde Fase 3
- OBS-4: std::terminate() vs soft-fail — DEBATE ABIERTO (solo Gemini propone soft-fail)
- OBS-5: contratos informales ADR-036 en código
- OBS-6: cache modelo en plugin_init

---

## PASO 0 — Verificación de estabilidad (SIEMPRE PRIMERO)

```bash
cd /Users/aironman/CLionProjects/test-zeromq-docker
git checkout feature/adr026-xgboost
git pull origin feature/adr026-xgboost
make pipeline-stop
make pipeline-build 2>&1 | tail -5
vagrant ssh -c "sudo bash /vagrant/etcd-server/config/set-build-profile.sh debug"
make sign-plugins
make test-provision-1
make pipeline-start && make pipeline-status
# Esperar: 6/6 RUNNING
make plugin-integ-test 2>&1 | grep -E "PASSED|FAILED"
# Esperar: 6/6 PASSED
```

**Solo si 6/6 RUNNING y 6/6 PASSED se continúa.**

---

## PASO 0b — ESPECIAL DAY 119: prueba Vagrantfile desde cero

**ANTES del PASO 0 habitual:**

```bash
vagrant destroy -f
vagrant up
# Esperar ~20-30 minutos
vagrant ssh -c "sudo ldconfig -p | grep xgboost"
# Esperar: libxgboost.so (libc6,x86-64) => /usr/local/lib/libxgboost.so
vagrant ssh -c "python3 -c 'import xgboost; print(xgboost.__version__)'"
# Esperar: 3.2.0
vagrant ssh -c "ls /usr/local/include/xgboost/"
# Esperar: base.h  c_api.h
```

Si el PASO 0b falla → diagnosticar y arreglar el bloque Vagrantfile antes de continuar.

---

## Orden DAY 119

### PASO 1 — Fallback apt en Vagrantfile (Q4 Consejo)
Actualizar el bloque XGBoost del Vagrantfile para añadir fallback:
```bash
pip3 install xgboost==3.2.0 --break-system-packages || {
    echo "⚠️  PyPI inaccesible, fallback a apt (versión desactualizada)"
    apt-get install -y python3-xgboost
    echo "❗ WARNING: xgboost $(python3 -c 'import xgboost; print(xgboost.__version__)')"
    echo "❗ Para reproducibilidad científica, usar xgboost==3.2.0"
}
```

### PASO 2 — Compilar plugin_xgboost
```bash
make pipeline-build 2>&1 | grep -E "plugin_xgboost|PASSED|FAILED|error"
make sign-plugins
make test-all 2>&1 | grep -E "PASSED|FAILED|ALL TESTS"
```

### PASO 3 — Localizar feature set RF baseline
```bash
find /vagrant/ml-detector -name "*.h" -o -name "*.cpp" | xargs grep -l "feature" 2>/dev/null
```
Identificar el feature extractor exacto: columnas, orden, normalización.
Documentar en `docs/xgboost/features.md`.

### PASO 4 — Script entrenamiento XGBoost (Opción A)
Crear `scripts/train_xgboost_baseline.py`:
- Mismo feature set que RF
- `random_state=42` para reproducibilidad
- Guardar `xgboost_ctu13.json` + `xgboost_ctu13.ubj`
- Registrar: F1, Precision, Recall, FPR, latencia
- Gate: Precision ≥ 0.99 + F1 ≥ 0.9985

### PASO 5 — Firma modelo (OBS-1 Consejo — bloqueante)
Extender `make sign-plugins` o crear `make sign-models` para firmar
`xgboost_ctu13.ubj` con la keypair Ed25519 (mismo esquema ADR-025).

### PASO 6 — Decisión OBS-4 (std::terminate vs soft-fail)
Consultar Consejo con pregunta específica si no se decide en sesión.

---

## Contexto permanente

### ADR-025 keypair dev (post-reset DAY 117)
MLD_PLUGIN_PUBKEY_HEX: `e51a91e91d72f74fe97e8a4eb883c9c6eb41dd2fc994feaf59d5ba2177720f3d`

### seed_family post-reset DAY 117
Seed compartido: `75deaca96768b5d973a4339faf2325c058969bf93c00c0d21eef703a2ab91360`
INVARIANTE-SEED-001: todos los seed.bin DEBEN ser idénticos.

### Lección operacional crítica
`provision.sh --reset` rota keypair. Siempre post-reset:
`make pipeline-build` + `make sign-plugins` + `make test-all`

### Regla de oro
6/6 RUNNING + make test-all VERDE

### Patrón robusto para scripts en VM
```bash
cat > /tmp/script.py << 'PYEOF'
...
PYEOF
vagrant upload /tmp/script.py /tmp/script.py
vagrant ssh -c "sudo python3 /tmp/script.py"
```
NUNCA sed -i sin -e '' en macOS. NUNCA Python inline con paréntesis en zsh.

### DEBTs no bloqueantes (NO tocar en esta feature)
- DEBT-CRYPTO-003a → feature/crypto-hardening
- DEBT-OPS-001/002 → feature/ops-tooling
- DEBT-SNIFFER-SEED → feature/crypto-hardening
- DEBT-INFRA-001 → feature/bare-metal
- DEBT-CLI-001 → feature/adr032-hsm
- ADR-033 TPM → post-PHASE 4

### feature/adr026-xgboost — estado
- `plugins/xgboost/CMakeLists.txt` ✅
- `plugins/xgboost/xgboost_plugin.cpp` (skeleton) ✅
- `docs/XGBOOST-VALIDATION.md` ✅
- Vagrantfile bloque XGBoost (líneas 327-348) ✅
- Commit: `9500300a`
- Feature set: Opción A (mismo que RF) — UNANIMIDAD Consejo
- Formato modelo: JSON repo + .ubj producción — UNANIMIDAD Consejo
- plugin_invoke: Opción B (ml-detector pre-procesa) — UNANIMIDAD Consejo
- OBS-1 firma modelo: BLOQUEANTE — pendiente implementar
- OBS-4 std::terminate vs soft-fail: DEBATE ABIERTO

### Paper arXiv
arXiv:2604.04952 — Draft v15. Tabla RF vs XGBoost irá en §4.