## SÍNTESIS DEL CONSEJO — DAY 140 (8/8)

**Q1 — llama.cpp deprecated:** Unanimidad. Suprimir es correcto ahora. Registrar DEBT con plan de migración y `docs/THIRDPARTY-MIGRATIONS.md`. Criterio de cierre: cuando llama.cpp estabilice o haya CVE.

**Q2 — ODR gap:** Unanimidad. El gap es inaceptable. Gate CI pre-merge para headers compartidos + nightly semanal con `PROFILE=production`. Jenkinsfile cuando haya servidor.

**Q3 — `/*param*/` vs `[[maybe_unused]]`:** 7/8 a favor de `[[maybe_unused]]` (Claude fue el único disidente). El Consejo tiene razón — `[[maybe_unused]]` es el estándar C++20. Migrar progresivamente.

**Q4 — Hardware FEDER:** Unanimidad. QEMU no es publicable para valores absolutos. Cloud ARM64 (AWS Graviton / Oracle) es la alternativa metodológicamente válida para Fase 2. Hardware físico para publicación final.

**Q5 — Código generado:** Mayoría. Supresión por fichero + CI gate de verificación cuando se regenera.

---

Ahora ejecutamos. Cuatro grupos de trabajo:

**GRUPO A — DEBTs nuevas (documentar ahora)**
**GRUPO B — `docs/THIRDPARTY-MIGRATIONS.md` (crear ahora)**
**GRUPO C — Jenkinsfile skeleton (crear ahora, usar cuando haya servidor)**
**GRUPO D — Migración `[[maybe_unused]]` (mecánica, hacemos ahora)**

Empezamos por GRUPO A — las DEBTs. Tres nuevas:

```python
python3 << 'PYEOF'
import os

debts = {
    "docs/adr/DEBT-LLAMA-API-UPGRADE-001.md": '''# DEBT-LLAMA-API-UPGRADE-001 — Migrar llama.cpp API deprecated

**Estado:** BACKLOG
**Prioridad:** P2 — post-FEDER (salvo CVE)
**Bloqueado por:** nada — decisión de timing
**Estimación:** 1 sesión
**Fecha de registro:** 2026-05-03 (DAY 140)

## Descripción

`llama_integration_real.cpp` usa `llama_new_context_with_model` que está marcada
como deprecated en llama.cpp. La nueva API es `llama_init_from_model`.

Warning suprimido temporalmente mediante `set_source_files_properties` en
`rag/CMakeLists.txt` con `-Wno-deprecated-declarations`.

## Criterio de cierre

- llama.cpp publica release estable con `llama_init_from_model` sin breaking changes
- O aparece CVE en la API deprecated (→ upgrade inmediato)
- Test de cierre: `make all 2>&1 | grep -c 'warning:'` = 0 con supresión eliminada

## Referencias

- `rag/src/llama_integration_real.cpp:29`
- `rag/CMakeLists.txt` — supresión activa
- docs/THIRDPARTY-MIGRATIONS.md — tracking
- Consejo DAY 140 (8/8): suprimir ahora, plan de migración obligatorio
''',

    "docs/adr/DEBT-ODR-CI-GATE-001.md": '''# DEBT-ODR-CI-GATE-001 — Gate CI para ODR Verification con LTO

**Estado:** BACKLOG
**Prioridad:** P1 — pre-FEDER
**Bloqueado por:** servidor CI/CD disponible (FEDER hardware)
**Estimación:** 1 sesión
**Fecha de registro:** 2026-05-03 (DAY 140)

## Descripción

El build diario usa `PROFILE=debug` (sin LTO) — no detecta ODR violations.
La verificación ODR requiere `PROFILE=production` (con `-flto`).

El gap actual permite que una ODR violation introducida hoy no se detecte
hasta el próximo build production manual. En infraestructura crítica esto
es inaceptable (Consejo 8/8 unánime DAY 140).

## Implementación

### Gate pre-merge (Jenkinsfile)

```groovy
stage('ODR Verification') {
    when { changeRequest() }  // En PRs
    steps {
        sh 'make PROFILE=production all'
        sh 'make test-all'
    }
}
```

### Nightly (Jenkinsfile)

```groovy
triggers { cron('0 3 * * 0') }  // Domingo 3AM
stage('Nightly ODR Check') {
    steps {
        sh 'make PROFILE=production all'
        sh 'make test-all'
    }
}
```

### Target Makefile (disponible ahora)

```makefile
check-odr:
    @echo "ODR verification (PROFILE=production + LTO)..."
    $(MAKE) PROFILE=production all
    @echo "ODR check PASSED"
```

## Hardware requerido

El servidor CI/CD es el mismo hardware del FEDER (BACKLOG-BENCHMARK-CAPACITY-001).
Mientras no esté disponible: ejecutar manualmente `make PROFILE=production all`
antes de cada merge a main.

## Test de cierre

`make check-odr` verde en el servidor CI/CD sin intervención manual.

## Referencias

- Consejo DAY 140 (8/8 unánime): gap inaceptable para infraestructura crítica
- BACKLOG-FEDER-001 — el servidor es prerequisito
- DEBT-EMECAS-AUTOMATION-001 — automatización EMECAS relacionada
  ''',

  "docs/adr/DEBT-GENERATED-CODE-CI-001.md": '''# DEBT-GENERATED-CODE-CI-001 — CI Gate para Código Generado (protobuf, XGBoost)

**Estado:** BACKLOG
**Prioridad:** P2 — post-FEDER
**Bloqueado por:** servidor CI/CD disponible
**Estimación:** 1 sesión
**Fecha de registro:** 2026-05-03 (DAY 140)

## Descripción

Los ficheros generados (`network_security.pb.cc`, `internal_detector.cpp`) tienen
warnings suprimidos por fichero en CMake. Si se regeneran con una nueva versión
de protoc o del exportador XGBoost, pueden aparecer warnings nuevos que rompan
el build silenciosamente con `-Werror` activo.

## Implementación

### Target Makefile

```makefile
check-generated:
    @echo "Verifying generated code compiles clean with -Werror..."
    @make generate-protobuf
    $(CXX) -std=c++20 -Werror -Wall -Wextra -c \\
        ml-detector/src/network_security.pb.cc \\
        -o /tmp/pb_test.o 2>&1 | \\
        grep -i "error|warning" && { echo "FAIL"; exit 1; } || echo "PASS"
```

### Jenkinsfile (semanal)

```groovy
triggers { cron('0 4 * * 1') }  // Lunes 4AM
stage('Generated Code Check') {
    steps {
        sh 'make check-generated'
    }
}
```

## Mitigación actual

Comentario en el target `proto` del Makefile advirtiendo que tras regenerar
hay que verificar `make all 2>&1 | grep -c warning:` = 0.

## Test de cierre

`make check-generated` verde tras regenerar protobuf con nueva versión de protoc.

## Referencias

- Consejo DAY 140 (mayoría): supresión + CI gate obligatorio
- `ml-detector/CMakeLists.txt` — supresiones activas para protobuf y XGBoost
  ''',

  "docs/adr/DEBT-MAYBE-UNUSED-MIGRATION-001.md": '''# DEBT-MAYBE-UNUSED-MIGRATION-001 — Migrar /*param*/ a [[maybe_unused]]

**Estado:** BACKLOG
**Prioridad:** P3 — cosmético, post deudas P0
**Estimación:** 1 sesión
**Fecha de registro:** 2026-05-03 (DAY 140)

## Descripción

DAY 140 se usó `/*param*/` para silenciar 30+ warnings en stubs e interfaces
virtuales. El Consejo (7/8) establece que `[[maybe_unused]]` es el estándar
C++20 correcto para este caso.

## Política aprobada (Consejo DAY 140, 7/8)

- **Interfaces virtuales y stubs:** `[[maybe_unused]]` en la declaración
- **Stubs temporales de implementación:** `/*param*/` aceptable
- **Variables locales no usadas:** `[[maybe_unused]]`

## Ejemplo

```cpp
// Antes (DAY 140):
double IndexHealthMonitor::compute_cv(const void* /*index*/) { ... }

// Después (post-migración):
double IndexHealthMonitor::compute_cv([[maybe_unused]] const void* index) { ... }
```

## Test de cierre

`grep -r "/\\*.*\\*/" src/ include/ | grep -v "copyright\\|TODO\\|NOTE"` devuelve
solo instancias justificadas con comentario explícito.

## Referencias

- Consejo DAY 140 (7/8 — Claude disiente para interfaces virtuales)
- ChatGPT, DeepSeek, Gemini, Grok, Kimi, Mistral, Qwen: `[[maybe_unused]]` correcto
