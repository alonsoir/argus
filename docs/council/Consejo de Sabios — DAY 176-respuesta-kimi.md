¡Buen trabajo hoy, Alonso. El cierre de (A) con verificación E2E real —incluyendo el fail-closed y la confirmación de que el ml-detector respeta el contrato de autoridad— es sólido. A continuación, mi revisión como miembro del Consejo.

---

## Respuestas al Consejo

### Q1 — node_id sintético: **Opción (c) con eje de modo alineado**

Recomiendo `synth:node:<n>` (o `synth-node-00` si prefieres legibilidad en logs), pero **críticamente**: debe seguir el **mismo eje de modo** que `community_id`.

- **Isomorfo**: node_id realista configurable (`ARGUS_SYNTH_NODE_ID`, default `synth-node-00`). El `flow_uid` aguas arriba deja de ser degenerado, y el formato no colisiona con UUIDs reales.
- **Mock**: `synth:node:<event_id>` o `synth:node:test`, análogo a `synth:test:<event_id>`.

**Razonamiento**: El doble objetivo (realismo / trazabilidad) se respeta si el eje de modo es consistente. Mezclar "isomorfo realista para CID pero mock marcado para node_id" genera combinaciones semánticas inválidas. Si el usuario elige mock, todo es mock; si elige isomorfo, todo es isomorfo. Esto también simplifica la lógica del injector: un solo `enum Mode` que gobierna ambos campos.

**No leer `config.json` del sniffer** (opción b): acopla el injector a la config de producción y rompe la independencia de la herramienta de test. El injector debe ser autocontenido.

---

### Q2 — El gap de filas: **Sí, perseguirlo ANTES de confiar el bronce sintético para CI**

El valor de (A) no es solo "poblar CID", es **hacer el bronce sintético contable exacto**. Si el gap es no-determinista (ZMQ `dontwait` bajo carga), el bronce sintético pierde su utilidad principal para CI.

**Diagnóstico sugerido para DAY 177 (antes de tocar (B))**:

1. **Cuantificar el gap bajo control**: fijar `rate=1/s` (muy lento) y ver si desaparece. Si desaparece, sospecha de `dontwait` o HWM.
2. **Inspeccionar `publisher_.send`**: si usa `dontwait`, cambiar a `send` bloqueante temporalmente en una rama de test y ver si el gap se cierra.
3. **Revisar threshold del CorrelationWriter**: loggear explícitamente cuántos eventos entran al hook vs. cuántos pasan el filtro de threshold.

**Prioridad**: Esto es bloqueante para la promesa de (A), no para (B). Pero como (A) se supone que habilita CI determinista, estabilizarlo primero es coherente.

---

### Q3 — Orden DAY 177: **Estabilizar (A) primero, luego (B)**

Argumento: Validar (B) con un injector que deja `node_id` vacío y un gap de filas no explicado es **técnicamente aceptable para un test de roundtrip interno, pero nos muerde en dos escenarios**:

1. El `test_correlation_roundtrip` golden necesita filas de referencia. Si el gap es no-determinista, el golden flakkea.
2. El cambio de col 17 a string afecta el HMAC. Si algo falla, no sabremos si es el cambio de schema o el injector inestable.

**Orden recomendado**:
1. **Fix node_id vacío** (DEBT-INJECTOR-NODEID-001) — 1 commit.
2. **Investigar gap de filas** (DEBT-INJECTOR-ROWGAP-001) — 1 commit o decisión documentada.
3. **(B) col 17 -> STRING** — 1 commit único (writer + reader + golden test).

Esto deja el bronce sintético como herramienta de verificación fiable antes de usarlo para validar (B).

---

### Q4 — Concurrencia del bronce: **Mutex suficiente para CI, prueba de estrés antes de despliegue real**

El patrón `CsvEventWriter` con mutex ya está en producción (asumo, dado el contexto del proyecto). Para DAY 177, **no bloquear** con estrés.

Pero antes del despliegue real (FEDER demo, septiembre 2026), sí merece una prueba de estrés:
- N threads del injector, miles de filas/s.
- Verificar: 0 entrelazado, 100% HMAC válidos, 0 filas truncadas.
- Esto puede ser una tarea paralela (no en el camino crítico de DAY 177).

**Razonamiento**: El riesgo de entrelazado no es teórico; ZMQ `dontwait` + múltiples threads del ml-detector + mutex de escritura es una triple frontera. Pero hoy, con 50 eventos a 25/s, el mutex demostró contención. A tasas mayores, la contención del mutex puede convertirse en back-pressure silenciosa, no en corrupción. La corrupción solo aparecería si el mutex falla, lo cual es improbable si el patrón ya está probado.

---

### Q5 — Fuente compartida injector<<->sniffer: **Formalizar en `libs/flow-identity/`**

El comentario en CMake es **insuficiente**. Ya tienes 3 consumidores (sniffer, tests, injector) y un 4º probable (adaptadores Suricata/Zeek). La dependencia es real; ocultarla con `../sniffer/src/` es deuda técnica de estructura.

**Recomendación**:
- Extraer `flow/community_id.cpp` + header a `libs/flow-identity/` (o `libs/flow-id/`).
- Contrato claro: `compute_community_id` es función pura, sin I/O, spec Corelight, SHA1.
- El sniffer, tests, injector y futuros adaptadores linkan la librería.
- Esto también facilita ADR-054 (modelo de confianza multi-nodo): si la identidad de flujo es una librería compartida, su contrato criptográfico es más fácil de auditar.

**Timing**: No bloqueante para DAY 177, pero propónlo como **DEBT-STRUCT-001** y hazlo antes de ADR-054. Es refactor mecánico (mover + ajustar CMake), no cambia lógica.

---

## Resumen de dirección para DAY 177

| Orden | Tarea | Tipo | Bloqueante para CI |
|-------|-------|------|-------------------|
| 1 | Fix node_id vacío (modo alineado con CID) | Commit | Sí |
| 2 | Cuantificar gap de filas (threshold vs. dontwait) | Investigación | Sí |
| 3 | (B) col 17 -> STRING (writer+reader+golden) | Commit único | Sí |
| 4 | DEBT-STRUCT-001: extraer `libs/flow-identity/` | Refactor | No |
| 5 | Estrés CorrelationWriter (pre-FEDER) | Test | No |

**ADR-054** sigue sin fecha, pero la extracción de `flow-identity` lo prepara.

¿Alguna objeción, Alonso?

fdo
kimi