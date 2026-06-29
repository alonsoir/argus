Estimado Alonso, el **Consejo de Sabios** se congrega en este **DAY 176** para revisar el avance del cableado E2E del bronce y dar respuesta firme a las cuestiones planteadas para el diseño y ejecución del **DAY 177**.

Ante todo, felicitamos la rigurosidad de la jornada: tres cambios compilando bajo `-Werror`, paridad matemática estricta por reutilización directa de la unidad de traducción (`community_id.cpp`), y la inyección limpia del comportamiento *fail-closed* en las variables de entorno. Evitar la reescritura del parser posicional rígido mediante una variable `ARGUS_CID_MODE` ha sido una decisión impecable de radio mínimo de impacto.

A continuación, emitimos nuestro dictamen técnico unificado sobre los dilemas de arquitectura y el orden de operaciones.

---

## 1. Respuestas del Consejo a las Preguntas Lanzadas

### Q1 — node_id sintético: ¿qué valor?

**Dictamen:** El `node_id` debe seguir **exactamente el mismo eje de simetría** que el `community_id`. No debemos acoplar el injector al `config.json` de producción (opción B), ya que rompería su aislamiento como herramienta autónoma de CI.

* **Si `ARGUS_CID_MODE=isomorphic`:** `node_id` debe ser un identificador sintético fijo y válido (ej. `synth-node-00`). Esto permite que el cálculo aguas arriba del `flow_uid` en Kuzu (`hash(node_id ‖ community_id ‖ flow_start_window)`) sea **estructuralmente idéntico al real**, sin colapsar ni degenerar por campos vacíos.
* **Si `ARGUS_CID_MODE=mock`:** `node_id` debe mutar a `synth:node:<event_id>` o un valor marcado equivalente. De este modo, todo el registro de bronce queda auto-identificado como traza sintética y facilita su filtrado inmediato en tests de integración.

### Q2 — El gap de filas: ¿lo perseguimos antes de confiar en el bronce sintético para CI?

**Dictamen:** **Sí, es imperativo investigarlo antes de construir las aserciones del CI.** El ml-detector reporta `received=50, processed=50`, lo que significa que el problema no es de ingesta ni de descarte interno del motor, sino del pipeline de evacuación hacia el bronce.

Descartamos el threshold del `CorrelationWriter` como causa de no-determinismo (si fuera por buffer/threshold, las filas acabarían llegando al cerrar el proceso). El principal sospechoso es el flag sin bloqueo de ZeroMQ:

```cpp
publisher_.send(msg, zmq::send_flags::dontwait);

```

Bajo ráfagas (incluso a 25 ev/s si los hilos se alinean), si el High Water Mark (HWM) interno de ZMQ se satura momentáneamente, `dontwait` descarta paquetes silenciosamente retornando `EAGAIN`.

* **Solución para el injector:** En entornos sintéticos/CI, el injector *debe* garantizar la entrega. Cambiar el flag a envío bloqueante (o incrementar sustancialmente el `ZMQ_SNDHWM`) en la herramienta de test garantizará la contabilidad exacta ($50 = 50$). No podemos basar un CI determinista en un transporte que sufre *drops* silenciosos.

### Q3 — Orden DAY 177: ¿(B) col 17 primero, o estabilizar (A) primero?

**Dictamen:** **Estabilizar (A) primero (reparar `node_id` y resolver el gap de filas) ANTES de atacar el cambio de formato de la columna 17.**

* **Argumento técnico:** Si modificas la columna 17 (`STRING` simbólico) y simultáneamente alteras los bytes que cubre el HMAC mientras sufres una pérdida indeterminada de filas (~42 de 50), aislar un fallo de verificación en el *golden test* `test_correlation_roundtrip` se volverá un infierno matemático.
* Al resolver el gap primero, garantizas un flujo de datos 100% predecible y estables. Una vez que el injector es un reloj suizo, rompes el contrato del bronce (columna 17) con la absoluta certeza de que cualquier discrepancia subsiguiente se debe únicamente al cambio de tipo de datos y al cálculo del HMAC.

### Q4 — Concurrencia del bronce: ¿basta el mutex o queremos una prueba de estrés?

**Dictamen:** **El mutex en el patrón `CsvEventWriter` es suficiente para la seguridad de memoria inmediata, pero se recomienda delegar una prueba de estrés formal a una subtarea no bloqueante.**

Verificar que no hay entrelazado de bytes a 50 eventos es una condición necesaria pero no suficiente para sistemas de alta tasa. El mutex garantiza atomicidad por fila, pero bajo contención severa de *multi-threading* puede convertirse en el cuello de botella del `ml-detector`. No detengas el avance del DAY 177 para esto, pero añade una deuda técnica (`DEBT-STRESS-BRONZE-001`) para estresar el writer con $N$ threads y miles de filas/s antes de congelar la release v0.8.0.

### Q5 — Fuente compartida injector<->sniffer: ¿acoplamiento aceptable o frontera a formalizar?

**Dictamen:** Es un acoplamiento aceptable para el estado actual de la rama (`feature/day170...`), pero **exige la creación de una librería interna a corto plazo (`libs/flow-identity`).**

Haber incluido la unidad de traducción física directamente en el `CMakeLists.txt` de `tools/` es una solución pragmática de "radio mínimo" excelente para el día de hoy. Sin embargo, violar los límites del layout de `sniffer/` desde `tools/` apunta a un síntoma claro: `community_id` ha dejado de ser un componente exclusivo del sniffer. Dado que el ecosistema se expandirá hacia los adaptadores de Zeek/Suricata y verificadores políglotas, extraer la función pura a `libs/flow-identity/` (con su propio set de *unit tests* aislados) limpiará la arquitectura y prevendrá dependencias circulares en el futuro.

---

## 2. Hoja de Ruta Propuesta para el DAY 177 (Orden Reorganizado)

Basándonos en los dictámenes anteriores, sugerimos al Árbitro Final reordenar las prioridades de mañana de la siguiente manera:

```
[Fase 1: Estabilización de Inyección (A)]
   ├── 1. Solucionar DEBT-INJECTOR-ROWGAP-001 (Cambiar a send bloqueante o ajustar HWM en ZMQ)
   └── 2. Solucionar DEBT-INJECTOR-NODEID-001 (Inyectar node_id sintético según modo de simulación)
                               │
            [Verificación: Contabilidad 50/50 lograda]
                               │
                               ▼
[Fase 2: Cambio de Contrato de Bronce (B)]
   └── 3. Modificar Columna 17 -> DetectorSource_Name() (String simbólico) y actualizar HMAC en bloque

```

### Plan de acción inmediato para el código de mañana:

1. **En `tools/synthetic_sniffer_injector.cpp`:**
* Modificar el método de envío para asegurar que no se descartan eventos por presión de tráfico.
* Implementar la lógica del `node_id`:
```cpp
std::string node_id = (cid_mode == CidMode::Isomorphic) ? "synth-node-00" : "synth:node:00";

```




2. **En `sniffer/src/correlation/correlation_writer.cpp` (Fase 2):**
* Sustituir el `static_cast<int>(event.source())` por `event.source().Name()` (o la función correspondiente del wrapper de Protobuf).
* Actualizar `test_correlation_roundtrip` asegurando que el validador de firmas asimile el cambio posicional de la columna de texto.



---

## 3. Notas del Cuaderno de Bitácora (Validación de Lecciones)

El Consejo toma nota y archiva de forma estricta las tres lecciones operativas del día:

* La advertencia sobre los **inodes huérfanos** al borrar el bronce en caliente con el `ml-detector` activo es un hallazgo crítico. Se integrará directamente como pre-condición en los scripts de limpieza del CI (`cleanup_bronze_unsafe`).
* La necesidad de `sudo` combinada con la exportación explícita de `LD_LIBRARY_PATH=/usr/local/lib` para la lectura de la `seed.bin` (permisos `0400`) queda documentada en la guía de *troubleshooting* interno de herramientas de desarrollo.

Quedamos a la espera de tu orden para proceder con el diseño de las estructuras del DAY 177, Alonso. El plan es sólido; el control de la paridad cruzada está blindado por el isomorfismo determinista.

fdo
gemini