# Consejo de Sabios — DAY 102
## Solicitud de feedback — 30 marzo 2026

---

## Contexto

DAY 102 de ML Defender (aRGus NDR). Se ha completado **ADR-012 PHASE 1b**
en su totalidad: plugin-loader integrado en los 5 componentes restantes del
pipeline (firewall-acl-agent, rag-ingester, rag-security), precedido por
TEST-PLUGIN-INVOKE-1 (unanimidad del Consejo DAY 101).

Tests: **25/25 ✅** (nuevo récord — TEST-PLUGIN-INVOKE-1 añadido hoy).

---

## Lo realizado en DAY 102

### TEST-PLUGIN-INVOKE-1 (prerequisito unánime del Consejo)

Test unitario en `plugin-loader/tests/test_invoke_all.cpp`:
- `PacketContext` sintético → `invoke_all()` → asserts sobre contadores
- Resultado: `invocations=1, errors=0, overruns=0` ✅
- Valida el hot path completo: load → init → invoke → shutdown
- CTest: `100% tests passed, 0 tests failed out of 1`

### ADR-012 PHASE 1b — 5/5 componentes

| Componente | Estado | Smoke test |
|------------|--------|-----------|
| sniffer | ✅ DAY 101 | 1 plugin cargado |
| ml-detector | ✅ DAY 101 | 1 plugin cargado |
| firewall-acl-agent | ✅ DAY 102 | 1 plugin cargado, shutdown OK |
| rag-ingester | ✅ DAY 102 | 1 plugin cargado |
| rag-security | ✅ DAY 102 | 1 plugin cargado |

**Patrón replicado en todos:**
- `CMakeLists.txt`: `find_library` + `find_path` + `PLUGIN_LOADER_ENABLED`
- `main.cpp`: `#ifdef` guards + `unique_ptr<PluginLoader>` + `load_plugins()` + `shutdown()`
- `config/*.json`: sección `plugins` con hello plugin

**Nota de implementación:** `rag-security` requirió `g_plugin_loader` como
variable global (el signal handler `signalHandler()` necesita acceso).
Resto de componentes: `unique_ptr` local en scope de `main()`.

---

## Preguntas al Consejo

### Q1 — Makefile rag alignment

El Makefile tiene una inconsistencia detectada en DAY 102:

```makefile
# rag-build actual — delega a Makefile interno
rag-build:
    @vagrant ssh -c "cd /vagrant/rag && make build"  # siempre Release

# Patrón del resto de componentes
firewall: proto etcd-client-build
    @vagrant ssh -c 'cd /vagrant/firewall-acl-agent && \
        mkdir -p $(FIREWALL_BUILD_DIR) && \
        cd $(FIREWALL_BUILD_DIR) && \
        cmake $(CMAKE_FLAGS) .. && \   # respeta PROFILE
        make -j4'
```

Adicionalmente:
- `pipeline-start` arranca rag-security vía tmux pero no hay `rag-attach`
- `test-components` no incluye los tests del rag (test_faiss_basic, test_embedder, test_onnx_basic)
- `build-unified` no incluye `rag-build`

**Pregunta:** ¿Refactorizamos `rag-build` al patrón estándar (cmake directo con
`$(CMAKE_FLAGS)`) en DAY 103? ¿O lo dejamos como deuda técnica documentada
dado que el componente funciona y el foco es arXiv?

### Q2 — PAPER-ADR022 §6: estructura de la subsección

El Consejo acordó en DAY 101 que el caso de estudio HKDF Context Symmetry
pertenece a §6 (metodológico) como subsección independiente.

Propuesta de estructura:

```
§6.X HKDF Context Symmetry: A Pedagogical Case Study in Test-Driven Hardening

6.X.1 The Error
  - Contexto HKDF definido por componente en lugar de por canal
  - Consecuencia: TX y RX derivan la misma clave → MAC failures silenciosas

6.X.2 Why the Type-Checker Cannot Help
  - Ambos contextos son std::string — sin distinción semántica en el tipo
  - El error es un modelo mental incorrecto, no un error de sintaxis
  - Ejemplo concreto: "ml-defender:sniffer:v1" vs
    "ml-defender:sniffer-to-ml-detector:v1:tx"

6.X.3 Detection via Intentional Regression (TEST-INTEG-3)
  - Descripción del test: introducir asimetría deliberada → verificar MAC failure
  - Por qué un test unitario de cifrado no lo detectaría
  - El test como especificación ejecutable del protocolo

6.X.4 Lesson
  - Cryptographic correctness requires E2E protocol tests, not just API tests
  - TDH como metodología: el test define el contrato del sistema, no solo la API
```

**Pregunta:** ¿Es correcta esta estructura para §6? ¿Falta algo o sobra algo?
¿El título "Pedagogical Case Study" es el correcto o sugeriríais otro?

### Q3 — Orden de prioridades DAY 103+

Con ADR-012 PHASE 1b completada, el camino crítico hacia arXiv tiene estas
tareas pendientes P1:

| Tarea | Esfuerzo estimado |
|-------|-------------------|
| Makefile rag alignment | 1-2 horas |
| PAPER-ADR022 §6 | 2-3 horas |
| BARE-METAL stress test (≥100 Mbps) | 1 día |
| PAPER-FINAL métricas DAY 102 | 1 hora |
| DOCS-APPARMOR (6 perfiles) | 2-3 días |

**Pregunta:** ¿Es correcto priorizar Makefile + Paper §6 en DAY 103 antes
de BARE-METAL? ¿O el stress test debería subir en prioridad dado que es
el único resultado empírico que falta para la submission?

---

## Para responder

Por favor responded con:
1. Vuestra posición sobre Q1 (refactorizar ahora vs deuda)
2. Feedback sobre la estructura de §6.X (Q2)
3. Recomendación de orden de prioridades P1 (Q3)

Formato sugerido: respuesta estructurada por pregunta, con
razonamiento explícito si hay divergencia entre revisores.

---

*Proyecto: ML Defender (aRGus NDR)*
*Rama: feature/bare-metal-arxiv*
*Tests: 25/25 ✅ · ADR-012 PHASE 1b: 5/5 COMPLETA*
*Co-authored-by: Alonso Isidoro Roman + Claude (Anthropic)*