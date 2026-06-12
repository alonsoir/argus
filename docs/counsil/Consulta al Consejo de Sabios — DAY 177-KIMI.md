**Asiento Claude — Respuesta al Consejo de Sabios, DAY 177**

---

### Q1. Dirección del fix de ROWGAP-001

**Posición: (b) + (d) combinados, con preferencia por (b) como mínimo viable.**

El reencuadre es correcto: el síntoma es bidireccional (pérdida *o* reenvío), la causa es la misma (`dontwait` sin control de retorno). Para una herramienta de test, no necesitamos "exactly once" de producción, pero sí **determinismo de CI**.

- **(b)** `send()` bloqueante con timeout es el cambio más barato y semánticamente correcto: reemplaza `dontwait` por `zmq::send_flags::none` con un `setsockopt(ZMQ_SNDTIMEO, ...)` razonable (p. ej. 1 s). Eso elimina tanto la pérdida por HWM como el reenvío accidental, sin reescribir la arquitectura.
- **(d)** es defendible *solo si* el dedup aguas arriba fuera real. Pero hoy los reenvíos generan `community_id` distinto → `flow_uid` distinto → **no son deduplicables**. Aceptar (d) puro invalidaría la métrica de filas en CI.
- **(a)** está bien, pero añade lógica de reintento innecesaria; el bloqueo con timeout es más simple y suficiente para un injector local.

**Recomendación:** implementar (b) en el injector; si en algún escenario remoto el timeout sigue siendo problemático, entonces añadir (a) como retry de 1 intento. No tocar el patrón PUSH/PULL — (c) es overkill para una herramienta de test.

---

### Q2. Realismo del benigno vs cobertura del discard path

**Posición: dos perillas, con valor por defecto determinista.**

La disyuntiva es falsa si separamos **modo CI** de **modo fuzz**:

- **Modo `deterministic` (default en CI):** 100 % TCP/UDP coherente. Garantiza conteos estables y bronce predecible.
- **Modo `realistic`:** 5 % ICMP (o cualquier proto sin puertos) + 95 % TCP/UDP. Ejercita el `nullopt` → descarte.

Esto se implementa con un parámetro de configuración del injector (`--realistic-protocol-mix` o similar). El CI corre el determinista; un test nocturno o manual puede activar el realista.

**Beneficio:** no perdemos cobertura del discard path, pero el build de integración permanece estable. Coste: una bifurcación más en el injector, trivial frente al valor.

---

### Q3. ¿Alimenta ADR-055?

**Posición: Sí, ADR-055 absorbe todo, con secciones diferenciadas.**

ADR-055 = *decisiones de injectors / golden / lib*. Los tres temas (node_id, proto benigno, ROWGAP) son decisiones de diseño del injector, no del pipeline de producción. Encajan naturalmente en ADR-055:

- **Sección "Injector sintético — identidad"**: node_id isomorfo fijo, justificación (unicidad por community_id).
- **Sección "Injector sintético — realismo del tráfico benigno"**: protocolo coherente, modos determinista/realista.
- **Sección "Injector sintético — semántica de entrega"**: reencuadre de ROWGAP, elección de `send()` bloqueante con timeout, explícita renuncia a "exactly once" en favor de "at most one por event_id en la ventana de test".

El reencuadre de ROWGAP no merece ADR propio; es una nota de diseño dentro del ADR del injector. Si en el futuro el patrón PUSH/Pull se eleva a producción, entonces sí se escribe ADR de mensajería separado.

---

### Q4. DEBT id para el hallazgo de proto

**Posición: No se abre DEBT nuevo. Se cierra como "completar A".**

El hallazgo era un **bug del injector**, no una deuda del sistema objetivo. La deuda original (poblar community_id) era del lado bronce/ingesta; el injector era el medio, no el fin. Al arreglar la coherencia proto/nombre, simplemente se completó el objetivo A.

**Registro aceptable:** el comentario `DAY 177 (A)` en el código + una línea en el log de DAY 177 que diga "Objetivo A cerrado: community_id 100 % poblado; fix de coherencia protocol_number/protocol_name en injector". Eso es suficiente trazabilidad sin inflar el registro de deudas.

---

### Q5. Oracle Divergence en bronce

**Posición: Registro y aplazamiento.**

El bronce está haciendo exactamente lo correcto: **preservar la procedencia real** (`DETECTOR_SOURCE_DIVERGENCE` vs `DETECTOR_SOURCE_ML_PRIORITY`). Eso es coherente con ADR-051 y no debe normalizarse a un valor fijo.

**No fijar ahora** cómo propaga hacia Kuzu o decisión gold porque:
1. El consumidor no está cableado; cualquier regla que fijemos hoy será especulativa.
2. La divergencia es una señal de calidad; su tratamiento depende de la lógica de "decisión gold" que aún no existe.

**Acción:** registrar en el ADR-055 (o en notas del DAY) que el bronce preserva la fuente divergente y que el mapeo a confianza/veredicto es *pending* hasta el cableado del consumidor. Nada más.

---

### Resumen de voto

| Q | Posición |
|---|----------|
| Q1 | (b) bloqueante con timeout; (d) solo si el dedup fuera real (hoy no lo es) |
| Q2 | Dos perillas: modo determinista (default CI) y modo realista (5 % descarte) |
| Q3 | Absorber en ADR-055, tres subsecciones |
| Q4 | Ratificación: no DEBT nuevo, cerrar como "completar A" |
| Q5 | Aplazamiento, preservar procedencia, decidir al cablear consumidor |

**Convergencia buscada:** 8/8 en Q1–Q3; ratificación en Q4; registro en Q5.

FDO
KIMI