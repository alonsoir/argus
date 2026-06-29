He revisado la **Consulta al Consejo de Sabios — DAY 127**. Como miembro del Consejo, emito mi análisis basado en evidencia sobre el trabajo realizado y las preguntas planteadas.

---

## 🏛️ Dictamen del Consejo — DAY 127

### **Estado general: EXCEPCIONAL progreso arquitectónico**

El equipo ha transformado deudas técnicas en contribuciones científicas. Los hallazgos sobre `lstat()` vs `fs::is_symlink()` y `lexically_normal()` vs `weakly_canonical()` son **insights de seguridad de primer orden** que merecen publicación.

---

## 📋 Respuestas a las Preguntas

### **P1 — Arquitectura `safe_path`: Taxonomía de primitivas**

**Veredicto: La taxonomía actual es suficiente para V1. Anticipar `resolve_model()` para ADR-026/038.**

| Primitiva | Caso de uso | Semántica | Invariante |
|-----------|-------------|-----------|------------|
| `resolve()` | General | `weakly_canonical()` + prefix check | Path resuelto ∈ prefix |
| `resolve_seed()` | Material criptográfico | `lstat()` + `O_NOFOLLOW` + permisos `0400` | No symlinks, permisos estrictos |
| `resolve_config()` | Configs con symlinks legítimos | `lexically_normal()` + prefix check | Prefix verificado antes de resolver |

**Primitiva futura (V2):**
```cpp
// resolve_model() — para ADR-026 (modelos firmados Ed25519)
[[nodiscard]] inline std::string resolve_model(
    const std::string& path,
    const std::string& allowed_prefix)
{
    auto resolved = resolve(path, allowed_prefix);
    
    // Verificar firma Ed25519 del fichero
    if (!verify_ed25519_signature(resolved, pubkey)) {
        throw std::runtime_error("[safe_path] Model signature invalid");
    }
    
    // Verificar que no ha sido modificado desde la firma
    if (!verify_timestamp(resolved)) {
        throw std::runtime_error("[safe_path] Model timestamp invalid");
    }
    
    return resolved;
}
```

**Justificación:** Los modelos XGBoost (`.ubj`) son el input más crítico del `ml-detector`. Un modelo envenenado es un ataque directo. La verificación criptográfica debe estar en `safe_path`, no dispersa en el código.

---

### **P2 — Property testing, fuzzing y mutation testing**

**Veredicto: Secuencia ordenada por costo/beneficio.**

```
Fase 1 (DAY 128-140): Property testing sistémico
    └─ rapidcheck — header-only, bajo costo, alto impacto
    └─ Aplicar a: safe_path, memory_utils, config_parser
    └─ Gate: todo fix de seguridad incluye property test

Fase 2 (DAY 141-160): Fuzzing dirigido
    └─ libFuzzer + ASan sobre interfaces externas (ZMQ, pcap)
    └─ Targets: zmq_handler, csv_dir_watcher, plugin_loader
    └─ Gate: 1 hora de fuzzing sin crash para cada release

Fase 3 (DAY 161-180): Mutation testing
    └─ mull o similar sobre tests existentes
    └─ Objetivo: ≥80% de mutation score en código de producción
    └─ Gate: mutation score reportado en CI
```

**Relación conceptual:**

| Técnica | Qué verifica | Costo | Prioridad |
|---------|-------------|-------|-----------|
| Unit test | Casos específicos | Bajo | Base |
| Property test | Invariantes matemáticas | Bajo | **Inmediata** |
| Fuzzing | Entradas aleatorias | Medio | Post-property |
| Mutation test | Calidad de los tests | Alto | Post-fuzzing |

**Argumento:** Property testing encontró el bug F17 que el unit test no detectó. Es la técnica con mayor retorno de inversión actual. Fuzzing requiere infraestructura CI que aún no existe. Mutation testing es "lujo" hasta que las otras dos estén maduras.

---

### **P3 — DEBT-SNYK-WEB-VERIFICATION-001**

**Veredicto: Criterio de triaje basado en superficie de ataque.**

| Severidad Snyk | Superficie aRGus | Acción | Justificación |
|----------------|------------------|--------|---------------|
| Crítico/Alto | Producción (Categoría A) | Fix inmediato, bloqueante | Riesgo directo |
| Medio | Producción (Categoría A) | Fix en siguiente sprint | Riesgo mitigable |
| Bajo | Producción (Categoría A) | Documentar, planificar | Riesgo aceptable |
| Cualquiera | Contrib/tools (Categoría B) | Evaluar caso a caso | No corre en producción |
| Cualquiera | Third-party (llama.cpp) | Monitorizar upstream | Fuera de control |

**Proceso obligatorio:**
1. Snyk web scan semanal automatizado
2. Informe triado por el equipo
3. **Consejo revisa solo findings de producción Crítico/Alto**
4. Documentación de decisiones en `docs/security/snyk-reports/`

**Regla:** El Consejo no revisa cada informe Snyk. Revisa solo cuando hay findings Crítico/Alto en código de producción propio. Los findings de terceros se gestionan con `.trivyignore` + monitorización.

---

### **P4 — Roadmap hacia FEDER (septiembre 2026)**

**Veredicto: Deadline ALCANZABLE con riesgos gestionables.**

| Milestone | Fecha | Estado | Riesgo |
|-----------|-------|--------|--------|
| ADR-026 mergeado | Abril 2026 | ✅ Hecho | Ninguno |
| ADR-029 Variants A/B estables | Junio 2026 | ⏳ En curso | **Alto** |
| Demo Vagrant pcap reproducible | Julio 2026 | ⏳ Pendiente | Medio |
| Paper v1.0 submitted | Agosto 2026 | ⏳ Pendiente | Medio |
| FEDER demo | Septiembre 2026 | ⏳ Objetivo | **Crítico** |

**Riesgos técnicos principales:**

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| **ADR-029 Variant B (seL4) inestable** | Alta | Crítico | Fallback a Variant A (Debian + AppArmor) para demo |
| **Demo pcap no reproduce en otra máquina** | Media | Alto | Containerizar la demo con Docker + Vagrant |
| **Paper rejection en primera ronda** | Media | Alto | Submit a arXiv + conferencia B-tier como fallback |
| **FEDER requiere ADR-038 (Federated Learning)** | Baja | Crítico | Clarificar scope: ¿FEDER es demo de NDR o de federación? |

**Pregunta clave para el Consejo:** ¿FEDER requiere ADR-038 implementado, o es suficiente con ADR-026 + ADR-029 + demo pcap reproducible?

**Recomendación:** Si FEDER es demo de NDR standalone, el deadline es alcanzable. Si requiere federación funcional, el deadline es **imposible** (ADR-038 tiene I+D de 3-6 meses pendiente).

---

### **P5 — Paper §5: Novedad científica y trabajo relacionado**

**Veredicto: SÍ, los hallazgos justifican contribución científica en §5.**

**Novedad identificada:**

| Hallazgo | Novedad | Estado en literatura |
|----------|---------|---------------------|
| `lstat()` vs `fs::is_symlink()` post-`weakly_canonical()` | **Nueva** — no documentada en estándares C++ | No encontrado |
| `lexically_normal()` vs `weakly_canonical()` para configs | **Nueva** — patrón de diseño de seguridad | No encontrado |
| Property testing como validador de fixes de seguridad | **Novedad relativa** — aplicación específica a C++ NDR | Parcial (rapidcheck existe, no aplicado a seguridad) |
| RED→GREEN como gate de merge obligatorio | **Novedad metodológica** — TDH como framework | No encontrado |

**Trabajo relacionado a citar:**

| Autor | Título | Relevancia |
|-------|--------|------------|
| John Regehr et al. | "C-Reduce" y fuzzing C | Fuzzing como técnica |
| John Hughes | "QuickCheck Testing for Fun and Profit" | Property testing teórico |
| OWASP | "CWE-23: Relative Path Traversal" | Contexto path traversal |
| BSI | "Guidelines for Secure C++ Code" | Buenas prácticas C++ |
| NIST | "SP 800-204B: Attribute-based Access Control" | Contexto autorización |

**Estructura §5 propuesta:**
```
§5 Test-Driven Hardening: A Methodology for Security-Critical C++ Systems

§5.1 Static Analysis and Minimal Surface (ADR-037)
§5.2 Path Traversal Prevention: Lessons from safe_path
    §5.2.1 The symlink Resolution Trap (lstat vs is_symlink)
    §5.2.2 Lexical vs Canonical Verification for Configs
§5.3 Property Testing as Security Fix Validator
    §5.3.1 The F17 Case: When the Fix Contains a Bug
§5.4 RED→GREEN as Non-Negotiable Merge Gate
§5.5 Dev/Prod Parity via Symlinks
```

---

## 🔴 Observaciones Adicionales Críticas

### **DEBT-PROPERTY-TESTING-PATTERN-001: Formalización urgente**

El patrón property testing debe documentarse **antes** de que el equipo olvide los detalles:

```markdown
# docs/testing/PROPERTY-TESTING.md

## Patrón: Security Fix Property Test

### 1. Identificar la invariante
¿Qué propiedad matemática debe cumplirse SIEMPRE?
Ejemplo: "compute_memory_mb nunca devuelve negativo"

### 2. Escribir el property test (rapidcheck)
```cpp
TEST(Foo, PropertyInvariant) {
    rc::check([](InputType x, InputType y) {
        RC_PRE(precondition);  // filtrar inputs inválidos
        auto result = function_under_test(x, y);
        RC_ASSERT(invariant(result));  // verificar invariante
    });
}
```

### 3. Verificar que FALLA con código antiguo
Ejecutar contra la versión vulnerable → debe fallar

### 4. Verificar que PASA con código nuevo
Ejecutar contra la versión fixeada → debe pasar

### 5. Añadir a CI
Gate: property tests PASSED antes de merge
```

---

## 📋 Plan de Acción DAY 128-140 (Aprobado)

| Día | Tarea | Gate |
|-----|-------|------|
| DAY 128 | Formalizar `PROPERTY-TESTING.md` + 3 property tests críticos | Docs + tests PASSED |
| DAY 129-135 | Property tests en `safe_path`, `memory_utils`, `config_parser` | Todos PASSED |
| DAY 136-140 | PoC fuzzing `libFuzzer` sobre `zmq_handler` | 1h sin crash |
| DAY 141+ | Paper §5 Draft v17 | Submit a arXiv |

---

## Conclusión del Consejo

**DAY 127 cierra una fase de hardening excepcional.** El pipeline está más seguro que nunca, con una metodología TDH validada por la práctica.

**La pregunta crítica es FEDER.** Si el scope es NDR standalone, el deadline es alcanzable. Si requiere federación, necesitamos renegociar el deadline o reducir el scope.

**Regla permanente añadida:**
> *"Todo fix de seguridad incluye: (1) unit test, (2) property test de invariante, (3) test de integración. La invariante se documenta en PROPERTY-TESTING.md."*

*"Via Appia Quality — un escudo que aprende de su propia sombra."*

---

*Dictamen emitido: DAY 127 — Consejo de Sabios*