## Kimi — Respuesta al Consejo de Sabios — DAY 140

*Evaluación bajo criterios de pragmatismo en dependencias de terceros, cobertura de verificación ODR, y rigor metodológico para benchmarks empíricos.*

---

### Q1 — `-Werror` en código de terceros: suprimir vs actualizar

**Hipótesis:** La decisión entre suprimir warnings en código de terceros y actualizar la API depende de la estabilidad de la dependencia, el riesgo de la nueva API, y el coste del cambio.

**Veredicto: Política de dos niveles — "update-if-stable, suppress-if-experimental".**

**Criterio de decisión:**

| Factor | Actualizar API | Suprimir warning |
|--------|---------------|------------------|
| **API nueva estable** | ✅ Sí | ❌ No |
| **API nueva experimental** | ❌ No | ✅ Sí |
| **Cambio requiere refactor mayor** | ❌ No (post-FEDER) | ✅ Sí (ahora) |
| **Seguridad afectada** | ✅ Sí (inmediato) | ❌ No |
| **Build roto sin el cambio** | ✅ Sí | ❌ No |

**Aplicación a `llama.cpp`:**

`llama_init_from_model` reemplaza a `llama_new_context_with_model`. La API de llama.cpp es **experimental por diseño** — cambia entre releases menores. Actualizar ahora introduce riesgo de que la próxima versión de llama.cpp rompa el build de nuevo.

**Política recomendada:**

```cmake
# CMakeLists.txt — código de terceros experimental
set_source_files_properties(
    src/rag-security/llama_integration_real.cpp
    PROPERTIES COMPILE_FLAGS "-Wno-deprecated-declarations"
)

# Documentar en KNOWN-DEBTS con fecha de revisión
# DEBT-LLAMA-API-UPDATE-001: Revisar en próxima release estable de llama.cpp
# Fecha de revisión: 2026-06-01 o cuando llama.cpp llegue a v1.0
```

**Regla permanente propuesta:**

> **RULE-THIRDPARTY-WARNINGS-001:** Para código de terceros, la supresión de warnings está permitida si y solo si: (a) la API deprecada no tiene CVEs conocidos, (b) la API nueva es experimental o no estable, (c) existe un DEBT con fecha de revisión programada, (d) la supresión es por fichero, no global.

**Acción inmediata:** Añadir `DEBT-LLAMA-API-UPDATE-001` a `KNOWN-DEBTS-v0.6.md` con fecha de revisión. No actualizar la API de llama.cpp antes de FEDER salvo que haya un CVE que lo obligue.

---

### Q2 — ODR verification scope: debug vs production gap

**Hipótesis:** Un gap entre el build diario (debug) y el build de verificación (production+LTO) permite que las ODR violations se introduzcan y permanezcan latentes.

**Veredicto: El gap es inaceptable para infraestructura crítica. Añadir gate CI `PROFILE=production all` pre-merge obligatorio.**

**Análisis del riesgo:**

| Escenario | Probabilidad | Impacto |
|-----------|-------------|---------|
| Developer introduce ODR en debug build | Alta (debug es el flujo diario) | Silencioso hasta production |
| ODR se manifiesta como corrupción en production | Media | Crítico — falsos negativos en detección |
| ODR detectada en pre-merge production gate | Baja si el gate existe | Cero — se rechaza el merge |

**La verificación ODR requiere LTO porque:**
- LTO unifica la visión global del linker sobre todos los símbolos
- Sin LTO, cada translation unit tiene su propia copia de símbolos inline
- El linker no detecta violaciones porque no compara definiciones entre TUs

**Implementación del gate:**

```bash
# .github/workflows/ci.yml o Makefile target
pre-merge-check:
    $(MAKE) clean
    $(MAKE) PROFILE=debug all test-all        # Build rápido + tests
    $(MAKE) clean
    $(MAKE) PROFILE=production all            # ODR verification + LTO
    $(MAKE) check-prod-all                    # Si hardened VM disponible
```

**Alternativa si CI no tiene VM hardened:** Al menos ejecutar `PROFILE=production all` en el runner. La verificación ODR no requiere la VM, solo requiere LTO.

**Frecuencia recomendada:**
- **Pre-merge:** Obligatorio. Cada PR que toca headers compartidos debe pasar production+LTO.
- **Nightly:** Obligatorio. `make PROFILE=production all` en CI cada noche para detectar acumulación.
- **Debug build:** No requiere ODR check (LTO en debug es lento y no representativo).

**Coste:** `PROFILE=production all` tarda ~10-15 minutos vs ~3 minutos de debug. Aceptable para pre-merge.

---

### Q3 — Stubs: `/*param*/` vs `[[maybe_unused]]`

**Hipótesis:** La elección entre comentar el nombre del parámetro y usar `[[maybe_unused]]` afecta la legibilidad, la mantenibilidad, y la semántica de "intención de implementación futura".

**Veredicto: `[[maybe_unused]]` para interfaces virtuales planificadas; `/*param*/` para stubs temporales.**

**Análisis comparativo:**

| Aspecto | `/*param*/` | `[[maybe_unused]]` |
|---------|------------|-------------------|
| **Semántica** | "Este parámetro no se usa *aún*" | "Este parámetro puede no usarse *intencionalmente*" |
| **Legibilidad** | Clara en definición | Clara en declaración |
| **Herramientas** | Compilador lo ignora | Compilador verifica que realmente no se usa |
| **Refactor** | Fácil de revertir (descomentar) | Requiere eliminar atributo al usar |
| **C++20 idiomático** | Estilo C legacy | Estilo moderno |

**Política recomendada:**

```cpp
// Caso A: Interfaz virtual que se implementará en el futuro
// Usar [[maybe_unused]] en la DECLARACIÓN (header)
class CaptureBackend {
public:
    virtual bool open(
        const std::string& iface,
        [[maybe_unused]] PacketCallback cb,   // Será usado en PcapBackend v2
        [[maybe_unused]] void* ctx            // Será usado en PcapBackend v2
    ) = 0;
};

// Caso B: Stub temporal que se eliminará pronto
// Usar /*param*/ en la DEFINICIÓN (cpp)
void TemporaryStub::placeholder(int /*will_be_removed_in_DAY_142*/) {
    // Empty by design — DEBT-TEMP-001
}
```

**Regla permanente propuesta:**

> **RULE-STUB-PARAMETERS-001:** En interfaces virtuales públicas, usar `[[maybe_unused]]` para documentar parámetros reservados. En implementaciones temporales o stubs de test, usar `/*param*/` para indicar eliminación inminente. Nunca mezclar ambos estilos en el mismo fichero.

**Acción inmediata:** Refactorizar los 30+ stubs actuales:
1. Identificar cuáles son interfaces virtuales (mover `[[maybe_unused]]` al header)
2. Identificar cuáles son stubs temporales (mantener `/*param*/`, añadir DEBT)
3. Eliminar stubs que ya no son necesarios (posiblemente algunos de los 30)

---

### Q4 — Gap hardware FEDER: emulación QEMU vs hardware físico

**Hipótesis:** El benchmark empírico requiere hardware real para ser publicable, pero el riesgo de no tener hardware a tiempo debe mitigarse con alternativas metodológicamente válidas.

**Veredicto: Estrategia de tres niveles — emulación para desarrollo, cloud ARM para validación, hardware físico para publicación final.**

**Análisis de alternativas:**

| Alternativa | Validez científica | Coste | Timeline | Recomendación |
|-------------|-------------------|-------|----------|---------------|
| **QEMU user-mode ARM64** | Baja — no emula caché, no emula NIC real, no emula thermal | Bajo | Inmediato | Solo para desarrollo funcional |
| **QEMU system-mode ARM64 + virtio-net** | Media — emula sistema completo pero NIC es virtual | Bajo | 1-2 días | Para validación de arquitectura |
| **AWS Graviton / Oracle Cloud ARM** | **Alta** — hardware ARM64 real, NIC real, kernel real | Medio (~50€/mes) | Inmediato | **Para benchmark publicable** |
| **RPi5 físico** | Máxima — hardware target real | Alto (depende aprobación) | Incierto | Para validación final |

**Recomendación para FEDER:**

1. **Fase 1 (ahora — 15 Junio):** Desarrollar y testear en QEMU system-mode ARM64 con virtio-net. Esto valida que el código compila y funciona en ARM64.

2. **Fase 2 (15 Junio — 1 Agosto):** Alquilar instancia ARM64 en cloud (AWS t4g.large o Oracle Cloud A1) para ejecutar el benchmark empírico. Los números son publicables porque el hardware es real, aunque no sea el hardware target final.

3. **Fase 3 (post-FEDER):** Validar en RPi5 físico cuando llegue. Publicar una nota de errata o addendum si los números difieren significativamente.

**Justificación metodológica:**

Un benchmark en cloud ARM64 es **publicable** si se documenta:
- Instancia exacta (AWS t4g.large, 2 vCPU ARM Graviton2, 8 GB RAM)
- Kernel exacto (`uname -a`)
- NIC exacta (ENA driver en AWS, o virtio-net en QEMU)
- Configuración de red (no tuning especial)

La diferencia con RPi5 (Cortex-A76 @ 2.4 GHz, 4 GB RAM LPDDR4X) es conocida y documentable: *"Los resultados en cloud ARM64 representan un límite superior al rendimiento en RPi5 debido a mayor RAM y CPU más rápida. Los resultados en RPi5 se reportan en [referencia post-FEDER]."*

**Riesgo de QEMU puro:** Los números de QEMU no son publicables en revisión por pares porque:
- No emula la caché L2/L3 de ARM64 correctamente
- No emula el bus USB3-to-Ethernet del RPi4/5
- No emula thermal throttling (crítico para el gate de 75°C de ADR-041)

**Acción inmediata:** Abrir cuenta AWS u Oracle Cloud, lanzar instancia ARM64, y ejecutar `make build-production-arm64` + benchmark de throughput. Coste: ~20€ para un mes de uso intensivo.

---

### Q5 — `-Werror` y código generado: supresión vs CI verification

**Hipótesis:** La supresión por fichero de código generado es pragmática pero oculta warnings que podrían indicar problemas reales (generador de código obsoleto, incompatibilidad de versiones).

**Veredicto: Supresión por fichero + CI gate que regenera y verifica.**

**Análisis de riesgo:**

| Escenario | Con supresión por fichero | Con CI regeneration |
|-----------|--------------------------|---------------------|
| `protoc` nuevo genera warnings diferentes | Build roto silenciosamente en próximo `make all` | Detectado inmediatamente en CI |
| XGBoost cambia estructura de trees | Warnings nuevos ocultos | Detectado en CI |
| Upgrade de dependencia | Necesita revisión manual de supresiones | CI falla, obliga a revisión |

**Implementación recomendada:**

```cmake
# CMakeLists.txt — código generado
set_source_files_properties(
    ${PROTOBUF_GENERATED}
    PROPERTIES COMPILE_FLAGS "-Wno-all"
)

# PERO: añadir target de verificación explícito
add_custom_target(verify-generated-clean
    COMMAND ${CMAKE_COMMAND} -E echo "Regenerating protobuf..."
    COMMAND protoc --cpp_out=. network_security.proto
    COMMAND ${CMAKE_COMMAND} -E echo "Building with -Werror..."
    COMMAND ${CMAKE_CXX_COMPILER} -c -Werror -Wall -Wextra 
            network_security.pb.cc -o /tmp/verify.pb.o
    COMMENT "Verifying generated code compiles clean with -Werror"
)
```

**CI gate:**

```yaml
# .github/workflows/ci.yml
verify-generated:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Regenerate protobuf
      run: |
        protoc --version
        protoc --cpp_out=./tmp network_security.proto
    - name: Compile generated code with -Werror
      run: |
        g++ -std=c++20 -Werror -Wall -Wextra -c ./tmp/network_security.pb.cc
    - name: Regenerate XGBoost stubs
      run: |
        # Script que regenera internal_detector.cpp
        ./scripts/regenerate-xgboost-stubs.sh
    - name: Compile generated code
      run: |
        g++ -std=c++20 -Werror -Wall -Wextra -c ./tmp/internal_detector.cpp
```

**Frecuencia:** Semanal es suficiente. Los generadores de código no cambian diariamente.

**Regla permanente propuesta:**

> **RULE-GENERATED-CODE-001:** Todo código generado por herramientas externas (protoc, XGBoost, etc.) se suprime por fichero en el build diario. Un gate CI semanal regenera el código y verifica que compila con `-Werror` sin supresiones. Si falla, se crea un DEBT para actualizar el generador o la supresión.

---

### Resumen de posiciones — Kimi

| Pregunta | Veredicto | Acción inmediata |
|----------|-----------|------------------|
| **Q1** | Suprimir llama.cpp; actualizar solo si CVE o API estable | Añadir `DEBT-LLAMA-API-UPDATE-001` con fecha de revisión |
| **Q2** | Gate `PROFILE=production all` pre-merge obligatorio | Añadir target `pre-merge-check` al Makefile; configurar CI nightly |
| **Q3** | `[[maybe_unused]]` para interfaces virtuales; `/*param*/` para stubs temporales | Refactorizar 30+ stubs según clasificación |
| **Q4** | Cloud ARM64 (AWS/Oracle) para benchmark publicable; QEMU solo para desarrollo | Abrir cuenta cloud ARM64; ejecutar benchmark esta semana |
| **Q5** | Supresión por fichero + CI semanal de regeneración | Añadir target `verify-generated-clean`; configurar CI semanal |

**Moción:** Propongo que el DAY 141 comience con la ejecución del benchmark en cloud ARM64 (Fase 2 de Q4) como acción prioritaria. El hardware físico es incierto; el cloud ARM64 es controlable y los resultados son publicables. Paralelamente, implementar el gate `pre-merge-check` (Q2) para cerrar el gap ODR.

— *Kimi*  
*Via Appia Quality — La seguridad no se instala. Se diseña.*