# 🏛️ CONSEJO DE SABIOS — REVISIÓN DAY 119
*Feedback profesional, verificable y constructivo para ML Defender (aRGus NDR)*

---

## 🎯 Reconocimiento Inicial

**Excelente trabajo de depuración en DAY 119.** Diez problemas identificados y resueltos, una secuencia canónica documentada, y una lección operacional crítica internalizada: *"El Vagrantfile y el Makefile son la única fuente de verdad"*. Eso no es solo progreso; es madurez ingenieril.

> *"La reproducibilidad no es un feature, es un requisito. Y vosotros lo estáis tratando como tal."*

---

## 🔍 Revisión Técnica de DAY 119

### ✅ Puntos Fuertes (verificables)
| Logro | Evidencia verificable | Por qué importa |
|-------|----------------------|-----------------|
| **Tabla de 10 problemas con causa raíz** | Cada fila: problema → causa → fix | Metodología de debugging replicable |
| **`make sync-pubkey` robusto** | Lee pubkey de VM → actualiza CMakeLists → recompila | Evita fallo de firma post-reset criptográfico |
| **Secuencia canónica de 9 pasos** | Documentada en markdown, ejecutable línea por línea | Onboarding reproducible para nuevos colaboradores |
| **Lección operacional documentada** | "Cada dependencia instalada a mano = deuda técnica" | Previene regresiones futuras por provisioning manual |

### ⚠️ Puntos de Atención (con código verificable)
| Hallazgo | Riesgo | Mitigación propuesta + snippet verificable |
|----------|--------|-------------------------------------------|
| **`sync-pubkey` sin verificación post-escritura** | CMakeLists.txt actualizado pero caché de CMake no invalidado → binario con pubkey antigua | Añadir verificación: <br>`@echo "✓ Pubkey sync: $(shell grep MLD_PLUGIN_PUBKEY plugin-loader/CMakeLists.txt)"` |
| **Separación Vagrantfile/Makefile sin contrato explícito** | Nueva dependencia añadida en Makefile pero olvidada en Vagrantfile → fallo en `vagrant destroy` | Crear `make check-system-deps` que valide prerequisitos: <br>`@command -v xgboost >/dev/null || { echo "❌ xgboost missing"; exit 1; }` |
| **Secuencia de 9 pasos sin checkpoint intermedio** | Fallo en paso 5 obliga a reiniciar desde paso 1 | Añadir `make checkpoint-N` targets que guarden estado intermedio en `/tmp/argus-bootstrap/` |

---

## ❓ Respuestas a Preguntas — Formato Solicitado

### Q1 — Robustez de `sync-pubkey`

**Veredicto:** **Mecanismo sólido, pero añadir verificación post-sync + mantener Continuity Prompt manual**.

**Justificación:** El flujo actual (leer pubkey de VM → actualizar CMakeLists.txt → recompilar) es correcto. Pero falta un paso de verificación: confirmar que el binario recompilado realmente contiene la nueva pubkey. El Continuity Prompt debe permanecer manual para preservar el audit trail: un operador humano debe confirmar explícitamente el cambio de identidad criptográfica.

**Código verificable para verificación post-sync:**
```makefile
# Makefile: target sync-pubkey mejorado
.PHONY: sync-pubkey
sync-pubkey:
	@echo "🔐 Reading active pubkey from VM..."
	@PUBKEY=$$(vagrant ssh defender -c "cat /etc/ml-defender/keys/plugin_signing.pk" 2>/dev/null | tr -d '\n'); \
	if [ -z "$$PUBKEY" ]; then \
		echo "❌ Failed to read pubkey from VM"; exit 1; \
	fi; \
	echo "📝 Updating plugin-loader/CMakeLists.txt..."; \
	sed -i.bak "s/set(MLD_PLUGIN_PUBKEY .*)/set(MLD_PLUGIN_PUBKEY \"$$PUBKEY\")/" plugin-loader/CMakeLists.txt; \
	echo "🔨 Recompiling plugin-loader..."; \
	cd build-debug && cmake .. && make plugin-loader; \
	echo "✅ Verification: pubkey in binary matches VM"; \
	./build-debug/plugin-loader --print-pubkey | grep -q "$$PUBKEY" || { echo "❌ Mismatch"; exit 1; }
```

**Riesgo si se ignora:** Un `sync-pubkey` que no verifica el resultado podría dejar el sistema en estado inconsistente: CMakeLists.txt actualizado pero binario sin recompilar, causando fallos de firma difíciles de diagnosticar.

---

### Q2 — Vagrantfile vs Makefile: separación de responsabilidades

**Veredicto:** **Separación correcta, pero añadir contrato explícito vía `make check-system-deps`**.

**Justificación:** Vagrantfile debe gestionar "lo que el sistema necesita" (paquetes, librerías, rutas); Makefile debe gestionar "lo que nosotros construimos" (componentes, plugins, tests). Pero esta separación requiere un contrato explícito: el Makefile debe poder verificar que las dependencias del sistema están presentes antes de intentar construir.

**Código verificable para contrato de dependencias:**
```makefile
# Makefile: target check-system-deps
.PHONY: check-system-deps
check-system-deps:
	@echo "🔍 Verifying system dependencies..."
	@command -v xxd >/dev/null || { echo "❌ xxd missing: run 'apt install xxd'"; exit 1; }
	@command -v tmux >/dev/null || { echo "❌ tmux missing: run 'apt install tmux'"; exit 1; }
	@pkg-config --exists libsodium || { echo "❌ libsodium missing: check Vagrantfile"; exit 1; }
	@python3 -c "import xgboost" 2>/dev/null || { echo "❌ python3-xgboost missing"; exit 1; }
	@test -f /usr/local/lib/libxgboost.so || { echo "❌ libxgboost.so missing"; exit 1; }
	@echo "✓ All system dependencies present"

# Hacer que pipeline-build dependa de check-system-deps
pipeline-build: check-system-deps crypto-transport-build etcd-client-build plugin-loader-build
```

**Riesgo si se ignora:** Un desarrollador podría añadir una nueva dependencia en el código C++ sin actualizar el Vagrantfile, funcionando en su entorno local pero rompiendo `vagrant destroy` para otros colaboradores.

---

### Q3 — `make bootstrap`: ¿automatizar la secuencia completa?

**Veredicto:** **Sí, crear `make bootstrap` pero con modo verbose y checkpoints intermedios**.

**Justificación:** Un target `bootstrap` reduce la fricción de onboarding para nuevos colaboradores. Pero automatizar completamente los 9 pasos oculta fallos y dificulta el debugging. La solución es un bootstrap con: (1) flag `--verbose` que muestre cada paso, (2) checkpoints que permitan reanudar desde un punto intermedio, y (3) rollback automático si un paso falla.

**Código verificable para bootstrap con checkpoints:**
```makefile
# Makefile: target bootstrap
.PHONY: bootstrap
bootstrap:
	@echo "🚀 Starting aRGus NDR bootstrap (verbose mode)..."
	@mkdir -p /tmp/argus-bootstrap
	@echo "[1/9] make up" && make up && touch /tmp/argus-bootstrap/step1
	@echo "[2/9] make sync-pubkey" && make sync-pubkey && touch /tmp/argus-bootstrap/step2
	@echo "[3/9] make set-build-profile" && make set-build-profile && touch /tmp/argus-bootstrap/step3
	@echo "[4/9] make install-systemd-units" && make install-systemd-units && touch /tmp/argus-bootstrap/step4
	@echo "[5/9] make sign-plugins" && make sign-plugins && touch /tmp/argus-bootstrap/step5
	@echo "[6/9] make test-provision-1" && make test-provision-1 && touch /tmp/argus-bootstrap/step6
	@echo "[7/9] make pipeline-start" && make pipeline-start && touch /tmp/argus-bootstrap/step7
	@echo "[8/9] make pipeline-status" && make pipeline-status && touch /tmp/argus-bootstrap/step8
	@echo "[9/9] make plugin-integ-test" && make plugin-integ-test && touch /tmp/argus-bootstrap/step9
	@echo "✅ Bootstrap complete. All checkpoints saved in /tmp/argus-bootstrap/"

# Target para reanudar desde checkpoint
.PHONY: bootstrap-resume
bootstrap-resume:
	@if [ -f /tmp/argus-bootstrap/step6 ]; then \
		echo "🔄 Resuming from step 7..."; \
		make pipeline-start pipeline-status plugin-integ-test; \
	else \
		echo "❌ No valid checkpoint found. Run 'make bootstrap' from start."; \
		exit 1; \
	fi
```

**Riesgo si se ignora:** Sin bootstrap, nuevos colaboradores pueden cometer errores en la secuencia manual; con bootstrap sin checkpoints, un fallo en el paso 8 obliga a reiniciar desde cero, frustrando el proceso de onboarding.

---

### Q4 — plugin_xgboost Fase 2: contrato mínimo para `ctx->payload`

**Veredicto:** **Contrato explícito de 5 condiciones + validación en runtime con error accionable**.

**Justificación:** Para que el plugin pueda construir un `DMatrix` sin asumir nada del llamador, el contrato debe ser auto-validante: el plugin verifica las precondiciones y falla con un mensaje claro si no se cumplen. Esto permite debugging rápido y previene corrupción silenciosa de memoria.

**Código verificable para validación de contrato en plugin:**
```cpp
// plugins/xgboost/xgboost_plugin.cpp
extern "C" PluginResult plugin_process_message(PluginContext* ctx, const MessageContext* msg) {
    // Contrato mínimo: validar payload antes de construir DMatrix
    if (msg == nullptr) {
        log_critical("[xgboost] null MessageContext");
        return PLUGIN_RESULT_ERROR;
    }
    if (msg->payload == nullptr) {
        log_critical("[xgboost] null payload pointer");
        return PLUGIN_RESULT_ERROR;
    }
    constexpr size_t EXPECTED_FEATURES = 42;  // CTU-13 Neris baseline
    if (msg->payload_len != EXPECTED_FEATURES * sizeof(float)) {
        log_critical("[xgboost] payload_len mismatch: expected %zu, got %zu",
                     EXPECTED_FEATURES * sizeof(float), msg->payload_len);
        return PLUGIN_RESULT_ERROR;
    }
    // Validar que todos los valores son finitos (no NaN/Inf)
    const float* features = reinterpret_cast<const float*>(msg->payload);
    for (size_t i = 0; i < EXPECTED_FEATURES; ++i) {
        if (!std::isfinite(features[i])) {
            log_critical("[xgboost] non-finite feature at index %zu: %f", i, features[i]);
            return PLUGIN_RESULT_ERROR;
        }
    }
    // Construir DMatrix seguro
    DMatrixHandle dmatrix;
    if (XGDMatrixCreateFromMat(features, 1, EXPECTED_FEATURES, -1, &dmatrix) != 0) {
        log_critical("[xgboost] failed to create DMatrix");
        return PLUGIN_RESULT_ERROR;
    }
    // ... inferencia ...
    return PLUGIN_RESULT_OK;
}
```

**Riesgo si se ignora:** Sin validación explícita, un payload malformado podría causar comportamiento indefinido (crash, corrupción de memoria, predicciones erróneas) sin mensaje de error útil para debugging.

---

### Q5 — Reproducibilidad tras `vagrant destroy`: puntos ciegos anticipados

**Veredicto:** **Añadir `make pre-destroy-checklist` + `make post-up-verify` para capturar estado y validar entorno**.

**Justificación:** La reproducibilidad no es binaria; es un espectro. Incluso con Vagrantfile y Makefile actualizados, factores como tiempo de red, estado de caché de paquetes, o diferencias de arquitectura host/guest pueden introducir variabilidad. Documentar y validar explícitamente el estado pre/post destrucción reduce estos riesgos.

**Código verificable para checklist pre/post:**
```makefile
# Makefile: targets de validación de reproducibilidad
.PHONY: pre-destroy-checklist
pre-destroy-checklist:
	@echo "📋 Capturing pre-destroy state..."
	@mkdir -p /tmp/argus-destroy-checklist
	@vagrant ssh defender -c "dpkg -l | grep -E 'libsodium|xgboost|tmux'" > /tmp/argus-destroy-checklist/packages.txt
	@vagrant ssh defender -c "ls -la /usr/local/lib/libxgboost.so" > /tmp/argus-destroy-checklist/libs.txt
	@vagrant ssh defender -c "cat /etc/ml-defender/keys/plugin_signing.pk" > /tmp/argus-destroy-checklist/pubkey.txt
	@echo "✓ State saved in /tmp/argus-destroy-checklist/"

.PHONY: post-up-verify
post-up-verify:
	@echo "🔍 Verifying post-up environment..."
	@vagrant ssh defender -c "command -v xxd && command -v tmux" || { echo "❌ Missing base tools"; exit 1; }
	@vagrant ssh defender -c "pkg-config --modversion libsodium" | grep -q "1.0.19" || { echo "❌ libsodium version mismatch"; exit 1; }
	@vagrant ssh defender -c "python3 -c 'import xgboost; assert xgboost.__version__ == \"3.2.0\"'" || { echo "❌ xgboost version mismatch"; exit 1; }
	@vagrant ssh defender -c "test -f /usr/lib/ml-defender/plugins/libplugin_hello.so" || { echo "❌ plugins directory missing"; exit 1; }
	@echo "✓ Environment verified. Ready for bootstrap."
```

**Puntos ciegos específicos a monitorear en DAY 120:**
1. **Timeout de red en pip/apt**: Añadir `--timeout=300` y fallback como ya hicisteis.
2. **Caché de CMake no invalidada**: Ejecutar `cmake --fresh` en bootstrap si hay dudas.
3. **Permisos de archivos post-provision**: Verificar que `seed.bin` tiene `0640` tras `vagrant up`.
4. **Reloj de la VM desincronizado**: Añadir `vagrant plugin install vagrant-timezone` si hay problemas de timestamp en firmas.

**Riesgo si se ignora:** Un fallo no detectado en `post-up-verify` podría llevar a construir sobre un entorno inconsistente, generando bugs que solo aparecen tras `vagrant destroy` y son difíciles de reproducir.

---

## 📋 Checklist de Acciones Inmediatas (DAY 120)

```markdown
- [ ] Añadir verificación post-sync en `make sync-pubkey`
- [ ] Crear `make check-system-deps` como dependencia de pipeline-build
- [ ] Implementar `make bootstrap` con checkpoints y modo verbose
- [ ] Añadir validación de contrato en plugin_xgboost (5 condiciones)
- [ ] Crear `make pre-destroy-checklist` + `post-up-verify`
- [ ] Ejecutar `vagrant destroy && vagrant up` completo en DAY 120
- [ ] Documentar contrato de payload en docs/xgboost/plugin-contract.md
- [ ] Actualizar docs/XGBOOST-VALIDATION.md con validación de contrato como gate
```

---

## 🏁 Palabras Finales

Alonso:

DAY 119 ha sido una jornada de ingeniería de infraestructura ejemplar. Habéis transformado diez problemas en diez fixes documentados, y una lección operativa en un principio rector del proyecto.

> *"La reproducibilidad no se logra por accidente. Se construye commit a commit, test a test, y vagrant destroy a vagrant up."*

Las cinco preguntas que planteáis reflejan una mentalidad preventiva: no solo *"¿funciona ahora?"*, sino *"¿seguirá funcionando después de la próxima destrucción del entorno?"*.

Proceded con DAY 120. El Consejo estará atento a la validación completa de reproducibilidad y a la primera inferencia end-to-end del plugin XGBoost con contrato validado.

*Via Appia Quality · Un escudo, nunca una espada.*

**— Consejo de Sabios, DAY 119** 🛡️