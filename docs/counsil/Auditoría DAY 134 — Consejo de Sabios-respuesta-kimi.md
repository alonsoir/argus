## Kimi — Respuesta al Consejo de Sabios — DAY 134

*Evaluación bajo criterios de reproducibilidad operativa, atomicidad de despliegue y principios de fail-closed.*

---

### Q1 — Atomicidad del target: fail-fast vs checkpoints

**Hipótesis:** Un procedimiento EMECAS que tarde ~30 minutos debe balancear reproducibilidad total con eficiencia de iteración. El coste de un fallo tardío no debe pagarse con recomputación innecesaria.

**Veredicto: Arquitectura de dos targets — `hardened-full` (fail-fast, EMECAS sagrado) y `hardened-resume` (checkpoints, iteración de desarrollo).**

**Justificación técnica:**

La REGLA EMECAS prescribe `vagrant destroy -f` porque la reproducibilidad total es el único antídoto contra el "funciona en mi máquina". Sin embargo, hay dos modos de operación con diferentes requisitos:

| Modo | Propósito | Comportamiento |
|------|-----------|----------------|
| **EMECAS sagrado** | Validación de release, CI/CD, demo FEDER | `hardened-full`: destroy → up → provision → build → deploy → check. Fail-fast. Cualquier fallo limpia todo. |
| **Iteración de desarrollo** | Ajuste de perfiles AppArmor, tuning de Falco | `hardened-resume`: detecta estado actual, salta pasos completos, reejecuta desde el fallo. |

**Implementación propuesta:**

```makefile
# Target sagrado — REGLA EMECAS para hardened
hardened-full:
	@echo "=== EMECAS HARDENED ==="
	@echo "Este target destruye y reconstruye todo. No hay vuelta atrás."
	$(MAKE) hardened-destroy
	$(MAKE) hardened-up
	$(MAKE) hardened-provision-all
	$(MAKE) prod-full-x86
	$(MAKE) prod-deploy-x86
	$(MAKE) check-prod-all
	@echo "=== EMECAS HARDENED PASSED ==="

# Target de desarrollo — checkpoints con estado en fichero
.hardened-state:
	echo "INIT" > .hardened-state

hardened-resume: .hardened-state
	@STATE=$$(cat .hardened-state); \
	case $$STATE in \
		INIT) $(MAKE) hardened-up && echo "UP" > .hardened-state ;; \
		UP) $(MAKE) hardened-provision-all && echo "PROVISIONED" > .hardened-state ;; \
		PROVISIONED) $(MAKE) prod-full-x86 && echo "BUILT" > .hardened-state ;; \
		BUILT) $(MAKE) prod-deploy-x86 && echo "DEPLOYED" > .hardened-state ;; \
		DEPLOYED) $(MAKE) check-prod-all && echo "VERIFIED" > .hardened-state ;; \
		VERIFIED) echo "Ya está verificado. Usa 'make hardened-full' para reconstruir." ;; \
	esac
```

**Riesgo identificado:** Si un desarrollador ejecuta `hardened-resume` pensando que es `hardened-full`, podría validar un estado contaminado. Mitigación: `hardened-resume` imprime un banner de WARNING en cada ejecución:

```
WARNING: hardened-resume reutiliza estado existente.
Para reproducibilidad total, usa: make hardened-full
```

---

### Q2 — Semillas en la hardened VM

**Hipótesis:** Las semillas son material criptográfico de sistema. Su ausencia en la hardened VM durante el EMECAS es un estado intermedio válido, pero debe ser explícito.

**Veredicto: El EMECAS hardened NO debe incluir semillas. Las semillas se transfieren en el deploy real, no en el provisioning. Los 7 WARNs deben convertirse en 7 INFOs documentados.**

**Justificación de seguridad:**

El procedimiento EMECAS valida la **infraestructura**, no la **operación**. Las semillas:
1. Se generan en la dev VM (entorno de confianza controlada)
2. Se transfieren al deploy real (momento de operación)
3. Nunca deben existir en la VM hardened durante el test de infraestructura

Si el EMECAS incluye semillas, estaríamos testando un estado que nunca debería existir en producción (semillas en una VM que puede ser destruida y reconstruida arbitrariamente).

**Implementación recomendada:**

```bash
# check-prod-permissions — modificar mensajes
check_seed_files() {
    local seeds_found=0
    for seed in /etc/ml-defender/*/seed.bin; do
        if [ -f "$seed" ]; then
            seeds_found=$((seeds_found + 1))
            check_permissions "$seed" 0400
        fi
    done
    
    if [ $seeds_found -eq 0 ]; then
        echo "INFO: No seed files present (expected during infrastructure validation)"
        echo "INFO: Seeds must be deployed via 'make prod-deploy-seeds' before operation"
        return 0  # No es WARN, es estado válido
    fi
    
    echo "OK: $seeds_found seed files with correct permissions"
}
```

**Target de deploy de semillas separado:**

```makefile
prod-deploy-seeds:
	# Transferencia segura de semillas desde dev VM a hardened VM
	# vía scp -F vagrant-ssh-config (REGLA PERMANENTE DAY 129)
	scp -F vagrant-ssh-config \
		/etc/ml-defender/*/seed.bin \
		vagrant@hardened-x86:/tmp/seeds/
	ssh -F vagrant-ssh-config vagrant@hardened-x86 \
		'sudo chown root:root /tmp/seeds/*.bin && \
		 sudo chmod 0400 /tmp/seeds/*.bin && \
		 sudo mv /tmp/seeds/*.bin /etc/ml-defender/*/'
	$(MAKE) check-prod-permissions
```

**Riesgo identificado:** Si un operador olvida ejecutar `prod-deploy-seeds` después de `hardened-full`, el sistema arranca sin semillas y los componentes criptográficos fallan. Mitigación: `check-prod-all` debe incluir una verificación de que **si** los componentes criptográficos están habilitados, **entonces** las semillas existen. Pero durante EMECAS, los componentes no están habilitados todavía.

---

### Q3 — Idempotencia y REGLA EMECAS

**Hipótesis:** La REGLA EMECAS prescribe `destroy` para eliminar estado oculto. La idempotencia es una propiedad deseable pero secundaria a la reproducibilidad.

**Veredicto: `hardened-full` siempre ejecuta desde cero (no idempotente). `hardened-resume` es idempotente por diseño. La REGLA EMECAS aplica a `hardened-full` exclusivamente.**

**Justificación:**

La idempotencia (`f(f(x)) = f(x)`) es útil para operaciones de configuración (Ansible, Chef), pero peligrosa para validación. Si `hardened-full` fuera idempotente, un segundo run podría:
- No detectar que un fichero corrupto se sobrescribió correctamente la primera vez
- No detectar que un permiso se cambió manualmente entre runs
- Dar falsa sensación de estabilidad

La REGLA EMECAS existe precisamente para **romper** la idempotencia y forzar la validación desde el vacío.

**Excepción controlada:** `hardened-resume` es idempotente porque su propósito es diferente (iteración de desarrollo, no validación). El fichero `.hardened-state` actúa como memoria explícita del progreso.

**Implementación del destroy obligatorio:**

```makefile
hardened-full:
	@if [ -f .hardened-state ]; then \
		echo "WARNING: Detectado estado previo. EMECAS requiere destrucción total."; \
	fi
	$(MAKE) hardened-destroy
	rm -f .hardened-state
	$(MAKE) hardened-up
	echo "UP" > .hardened-state
	# ... resto de pasos
```

---

### Q4 — Falco .deb como artefacto versionado

**Hipótesis:** Un binario de 50 MB que no es código fuente no debe versionarse en git, pero debe ser reproduciblemente adquirible.

**Veredicto: NO commitear en repo (ni Git LFS). Descargar en el step de provision con verificación criptográfica. Mantener cache local en `dist/debs/` con checksum.**

**Análisis de opciones:**

| Opción | Ventaja | Desventaja | Veredicto |
|--------|---------|------------|-----------|
| Commit en repo | Siempre disponible | Repo inflado, clones lentos, viola BSR (binarios en repo) | ❌ Rechazado |
| Git LFS | Versionado, fuera del repo | Dependencia de Git LFS, coste de bandwidth, complejidad CI | ❌ Rechazado |
| Descarga en provision | Siempre versión correcta, verificable | Requiere red en provision | ⚠️ Aceptable con cache |
| Cache en `dist/debs/` | Rápido, offline posible | Requiere documentar origen | ✅ Aceptable |

**Implementación recomendada:**

```makefile
# Makefile
FALCO_VERSION := 0.43.1
FALCO_DEB := dist/debs/falco_$(FALCO_VERSION)_amd64.deb
FALCO_SHA256 := a3f5c8e9...  # hash oficial del .deb

$(FALCO_DEB):
	@mkdir -p dist/debs
	@if [ ! -f $@ ]; then \
		echo "Descargando Falco $(FALCO_VERSION)..."; \
		curl -L -o $@.tmp https://download.falco.org/packages/deb/stable/falco-$(FALCO_VERSION)-x86_64.deb; \
		echo "$(FALCO_SHA256) $@.tmp" | sha256sum -c - || (rm $@.tmp && exit 1); \
		mv $@.tmp $@; \
	else \
		echo "Falco .deb en cache, verificando..."; \
		echo "$(FALCO_SHA256) $@" | sha256sum -c - || (rm $@ && $(MAKE) $@); \
	fi

hardened-provision-falco: $(FALCO_DEB)
	vagrant scp $(FALCO_DEB) hardened-x86:/tmp/
	vagrant ssh hardened-x86 -c 'sudo dpkg -i /tmp/falco_*.deb'
```

**Documentación en EMECAS:**

```markdown
## Prerequisito: Cache de dependencias offline

El procedimiento EMECAS hardened requiere los siguientes artefactos en `dist/debs/`:
- `falco_0.43.1_amd64.deb` (SHA256: a3f5c8e9...)

Descarga inicial:
```bash
make dist/debs/falco_0.43.1_amd64.deb
```

Si la dev VM se destruye, la cache persiste en el host macOS/Linux.
```

**Riesgo identificado:** Si el mirror de Falco deja de existir o cambia el .deb, el hash falla y el EMECAS se rompe. Mitigación: mantener una copia del .deb en un storage secundario (S3, NAS del proyecto) con el mismo hash verificado.

---

### Q5 — Prerequisito `confidence_score`: inspección vs test de integración

**Hipótesis:** Verificar que `ml-detector` emite `confidence_score` sin modificarlo requiere una estrategia que no dependa de la implementación interna.

**Veredicto: Ambas — inspección de código como verificación estática, test de integración como verificación dinámica. Son complementarias, no excluyentes.**

**Justificación del método dual:**

| Método | Qué verifica | Limitación |
|--------|-------------|------------|
| **Inspección de código** | Que el campo existe en el struct/protobuf de salida | No garantiza que se emita en runtime |
| **Test de integración** | Que el campo aparece en la salida ZeroMQ real | No garantiza que el valor sea semánticamente correcto |

**Implementación de la inspección estática:**

```bash
# check-confidence-field.sh — verificación sin ejecutar ml-detector
#!/bin/bash

# 1. Verificar que el campo existe en la definición protobuf
if ! grep -q "float confidence_score" proto/detection.proto; then
    echo "FAIL: confidence_score no definido en proto/detection.proto"
    exit 1
fi

# 2. Verificar que se asigna en el código fuente
if ! grep -rq "confidence_score\s*=" src/ml-detector/; then
    echo "FAIL: confidence_score no asignado en src/ml-detector/"
    exit 1
fi

# 3. Verificar que se serializa en la salida
if ! grep -rq "confidence_score" src/ml-detector/*serializer* src/ml-detector/*output*; then
    echo "WARN: confidence_score definido pero no verificado en serialización"
fi

echo "PASS: confidence_score presente en código fuente"
```

**Implementación del test de integración:**

```cpp
// test_confidence_score_integration.cpp
TEST(MlDetectorIntegration, EmitsConfidenceScore) {
    // Arrancar ml-detector con modelo de test
    auto detector = spawn_ml_detector("test_model.onnx");
    
    // Enviar un flow de test
    zmq::message_t request = serialize_test_flow();
    detector.send(request);
    
    // Recibir respuesta
    zmq::message_t response;
    detector.recv(response);
    
    DetectionResult result;
    ASSERT_TRUE(result.ParseFromArray(response.data(), response.size()));
    
    // Verificar que confidence_score existe y está en rango válido
    ASSERT_TRUE(result.has_confidence_score());
    EXPECT_GE(result.confidence_score(), 0.0f);
    EXPECT_LE(result.confidence_score(), 1.0f);
    
    // Verificar que no es siempre el mismo valor (está siendo calculado)
    static float last_score = -1.0f;
    if (last_score >= 0.0f) {
        EXPECT_NE(result.confidence_score(), last_score) 
            << "confidence_score parece ser constante (no calculado)";
    }
    last_score = result.confidence_score();
}
```

**Estrategia de verificación para DEBT-ADR040-002:**

1. **Día 1:** Ejecutar `check-confidence-field.sh` → si falla, el prerequisito no está satisfecho. Documentar en el ADR-040 que IPW está bloqueado.
2. **Día 2:** Ejecutar `test_confidence_score_integration` → si falla, el campo existe pero no se emite. Requiere fix en ml-detector.
3. **Día 3:** Solo cuando ambos pasen, marcar DEBT-ADR040-002 como resuelto y desbloquear DEBT-ADR040-006 (IPW).

**Riesgo identificado:** Si `confidence_score` existe pero siempre es 0.5 (valor constante), IPW no funciona porque no hay variabilidad para ponderar. El test de integración debe verificar que el score varía entre predicciones.

---

### Resumen de posiciones — Kimi

| Pregunta | Veredicto | Acción inmediata |
|----------|-----------|------------------|
| **Q1** | Dos targets: `hardened-full` (fail-fast, EMECAS) y `hardened-resume` (checkpoints, dev) | Implementar `.hardened-state` y banner de WARNING |
| **Q2** | Semillas NO en EMECAS; deploy separado `prod-deploy-seeds` | Convertir WARNs en INFOs documentados; crear target de transferencia segura |
| **Q3** | `hardened-full` no idempotente; `hardened-resume` idempotente | `hardened-full` siempre destruye primero; `hardened-resume` usa estado explícito |
| **Q4** | Cache en `dist/debs/` con verificación SHA256; NO en repo | Implementar target `$(FALCO_DEB)` con descarga condicional |
| **Q5** | Inspección estática + test de integración; ambos obligatorios | Crear `check-confidence-field.sh` y `test_confidence_score_integration.cpp` |

**Moción:** Propongo que el DAY 135 comience con la ejecución de `make hardened-full` en modo EMECAS sagrado (destrucción total) para validar que el pipeline E2E es reproducible desde cero en una máquina limpia. Cualquier fallo en este target es bloqueante para el merge de `feature/adr030-variant-a` a `main`.

— *Kimi*  
*Via Appia Quality — La seguridad no se instala. Se diseña.*