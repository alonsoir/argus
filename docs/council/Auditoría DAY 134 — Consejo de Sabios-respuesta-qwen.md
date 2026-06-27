# 🏛️ CONSEJO DE SABIOS — REVISIÓN DAY 134 & PREPARACIÓN DAY 135
*Feedback basado en ingeniería de sistemas reproducibles, principios de seguridad y metodología científica*

---

## 🎉 Reconocimiento Inicial

**Feliz cumpleaños, Alonso.** DAY 134 es un testimonio de disciplina técnica: dos ADRs estructurales, primer pipeline E2E en entorno hardened, 15 incidencias de integración diagnosticadas y resueltas, y un paper que ahora contiene métricas reales de fuzzing. La madurez del proyecto es visible en cada fix y en cada decisión documentada.

> *"La seguridad no se improvisa. Se construye, se verifica y se reproduce."*

---

## ❓ Respuestas a Preguntas — Formato Científico

### Q1 — Atomicidad vs Checkpoints para `make hardened-full`

**Recomendación concreta:** **Pasos idempotentes con tracking de estado explícito (`.hardened-state/`), pero fail-fast en gates de seguridad. No rollback automático total.**

**Justificación técnica:**
- **Reproducibilidad**: Un archivo de estado que registra `step_name`, `timestamp`, y `artifact_hash` permite reanudar sin recompilar, manteniendo trazabilidad.
- **Seguridad**: Los gates (`check-prod-all`) deben ejecutarse **siempre**, sin caché. Un estado seguro no se asume; se verifica en cada ejecución.
- **Eficiencia vs Rigor**: Fallar en un paso intermedio y limpiar solo ese artefacto evita 30 min de build innecesario, pero garantiza que no quede un estado parcialmente parcheado considerado "válido".

**Riesgo identificado:** Corrupción o desincronización del archivo de estado si un script falla entre el check y la escritura del hash.
**Mitigación:** Usar operaciones atómicas (`mv tmp.state hardened.state`) y verificar hashes de artefactos antes de saltar pasos.

**Verificación mínima:**
```makefile
# Makefile fragmento
HARDENED_STATE := .hardened-state/manifest.json
.PHONY: hardened-full
hardened-full:
	@mkdir -p $(HARDENED_STATE)
	@./scripts/hardened-run.sh --step build --state $(HARDENED_STATE)
	@./scripts/hardened-run.sh --step sign --state $(HARDENED_STATE)
	@./scripts/hardened-run.sh --step deploy --state $(HARDENED_STATE)
	@make check-prod-all  # ← SIEMPRE se ejecuta completo
```

---

### Q2 — Semillas en la hardened VM

**Recomendación concreta:** **La hardened VM DEBE estar sin semillas por defecto. El warning es una señal de seguridad correcta, no un bug.**

**Justificación técnica:**
- El axioma BSR (Build/Runtime Separation) exige que el entorno de runtime no contenga secretos de build/provisioning.
- Las seeds son **configuración de despliegue**, no artefactos de compilación. Inyectarlas durante el build viola el principio de mínimos privilegios y crea imágenes no portables.
- El pipeline hardened debe producir una **imagen estéril**: lista para recibir seeds solo bajo control explícito del operador.

**Riesgo identificado:** Si los tests de integración requieren seeds, podría haber tentación de hardcodearlas o dejarlas en la imagen.
**Mitigación:** Usar `seed.test.bin` (valores dummy, documentados como no-crypto) para pruebas de parsing/permisos. La verificación real de seeds solo ocurre en `provision.sh --inject-seeds`, que requiere interacción manual o secreto externo (Vault/Pass).

**Verificación mínima:**
```bash
# check-prod-permissions debe tratar la ausencia de seed como EXPECTADO en fase build
# Solo en fase runtime se ejecuta:
test -f /etc/ml-defender/<component>/seed.bin || echo "ℹ️ Seed not injected (expected post-build)"
```

---

### Q3 — Idempotencia del procedimiento EMECAS hardened

**Recomendación concreta:** **Idempotencia por defecto para desarrollo iterativo; `vagrant destroy` como único camino para reproducibilidad científica/FEDER.**

**Justificación técnica:**
- **Idempotencia** es estándar en IaC (Ansible, Terraform): permite ajustar AppArmor, Falco o permisos sin destruir la VM.
- **Destrucción** es el único método que garantiza *estado inicial idéntico*, requisito para papers, auditorías y demos FEDER.
- Ambas son válidas; sirven propósitos distintos. Documentar explícitamente cuándo usar cada una evita ambigüedad metodológica.

**Riesgo identificado:** La idempotencia puede enmascarar "drift" si un paso falla silenciosamente y el siguiente asume estado previo.
**Mitigación:** Cada step idempotente debe verificar condiciones post-ejecución, no solo existencia de archivos. Incluir `make hardened-clean` que resetea estado sin destruir VM.

**Verificación mínima:**
```bash
# docs/REPRODUCIBILITY.md
## When to use what
- `make hardened-full` (idempotent): Iterative hardening, AppArmor/Falco tuning
- `vagrant destroy -f && vagrant up && make hardened-full`: FEDER demo, paper reproducibility, security audit
```

---

### Q4 — Falco .deb como artefacto versionado

**Recomendación concreta:** **Mantener en `dist/` (gitignored), pero fijar por SHA-256 + URL en un manifiesto. Nunca commitear binarios ni usar Git LFS.**

**Justificación técnica:**
- **Repositorio limpio**: Git no está diseñado para binarios de 50 MB. LFS añade complejidad de cuotas, mirroring y revisión de seguridad.
- **Supply chain security**: Descargar en cada provision sin verificación hash es vulnerable a tampering. Verificar SHA-256 antes de `dpkg -i` mitiga esto.
- **Reproducibilidad**: Un manifiesto `dist/falco-manifest.json` con `version`, `url`, `sha256`, y `date` permite trazabilidad completa sin inflar el repo.

**Riesgo identificado:** La URL de descarga puede volverse inaccesible o cambiar el binario sin cambiar versión.
**Mitigación:** Script de provision debe hacer: `curl -fsSL $URL | sha256sum -c manifest.json && dpkg -i falco.deb`. Si falla hash, abortar inmediatamente.

**Verificación mínima:**
```json
// dist/falco-manifest.json
{
  "version": "0.43.1",
  "url": "https://download.falco.org/packages/deb-amd64/falco_0.43.1_amd64.deb",
  "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "verified_by": "make check-falco-manifest"
}
```

---

### Q5 — Prerequisito `confidence_score` en ml-detector

**Recomendación concreta:** **Verificación en dos capas: inspección estática del esquema ZMQ + test de integración con input determinista.**

**Justificación técnica:**
- **Inspección de código/schema**: Confirma que el campo existe en la definición del mensaje (FlatBuffers/Protobuf/struct C++). Sin esto, el test de integración podría estar capturando un campo añadido accidentalmente o mal serializado.
- **Test de integración con golden input**: Confirma que el campo se emite en runtime, está en `[0.0, 1.0]`, y es correlacionado con la predicción. Usar un flujo de red determinista (mismo pcap, misma semilla) elimina flakiness.
- Juntas, satisfacen el principio de *verificación independiente* requerido para contratos ML (ADR-040).

**Riesgo identificado:** Si el test de integración depende de estado global del modelo, puede fallar intermitentemente en CI.
**Mitigación:** Cargar un modelo estático de prueba (`test_model.onnx`) y enviar un único flujo pre-generado. Asserts estrictos sobre formato y rango.

**Verificación mínima:**
```python
# tests/test_ml_confidence_score.py
def test_confidence_score_emitted():
    # 1. Static schema check
    schema = load_zmq_schema("ml_detector_output.fbs")
    assert "confidence_score" in schema.fields, "Schema missing confidence_score"
    
    # 2. Runtime integration test
    msg = run_ml_detector_on_golden_flow("data/golden_flow_001.pcap")
    assert 0.0 <= msg.confidence_score <= 1.0
    assert (msg.prediction == 1) == (msg.confidence_score > 0.5)  # Consistency check
```

---

## 📋 Checklist de Acciones Inmediatas (DAY 135)

```markdown
- [ ] Implementar `make hardened-full` con tracking de estado `.hardened-state/` + gates siempre completos
- [ ] Convertir warning de `seed.bin` a mensaje informativo en build; añadir step explícito `seed-inject` para runtime
- [ ] Documentar uso idempotente vs destructivo en `docs/REPRODUCIBILITY.md`
- [ ] Crear `dist/falco-manifest.json` + verificación SHA-256 en provision
- [ ] Implementar verificación dual (schema + runtime) para `confidence_score` en ml-detector
- [ ] Añadir `make hardened-clean` para resetear estado sin `vagrant destroy`
- [ ] Preparar script `scripts/hardened-run.sh` con manejo de errores atómicos por step
```

---

## 🏁 Palabras Finales

Alonso:

DAY 134 cerró un ciclo crítico: la transición de arquitectura teórica a sistema operativo verificado. Las 15 incidencias resueltas no son ruido; son la fricción inevitable de hacer que la teoría colisione con la realidad del kernel, el filesystem y el toolchain. Cada fix fortalece la reproducibilidad del pipeline.

Las preguntas que planteáis para DAY 135 tocan la esencia de la ingeniería de sistemas seguros: cómo equilibrar eficiencia, trazabilidad y pureza de estado sin sacrificar ninguno. Las respuestas propuestas siguen un principio rector: **lo que no se puede verificar de forma independiente, no se puede confiar**.

> *"La reproducibilidad no es un lujo académico. Es la única garantía de que un escudo funcionará cuando se necesite."*

Descansad hoy. Mañana, con energía renovada, cerrad el EMECAS hardened y dejad que el pipeline hable por sí mismo. El Consejo revisará los resultados con el mismo rigor con el que acompaña cada commit.

*Via Appia Quality · Un escudo, nunca una espada.*

**— Consejo de Sabios, DAY 134** 🏛️