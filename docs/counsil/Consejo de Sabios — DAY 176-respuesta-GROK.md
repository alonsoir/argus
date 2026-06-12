**✅ Consejo de Sabios — DAY 176**

**Fecha:** Sábado 6 de junio de 2026  
**Arbitro final:** Alonso  
**Feedback general:** Muy buen día. Cierre limpio del objetivo principal (A), excelente disciplina en no reimplementar lógica crítica, y documentación clara. El uso compartido de `compute_community_id` es la decisión técnicamente correcta.

---

### Valoración de lo hecho hoy

- **Elección de modos y default `isomorphic`**: Correcta. Mantiene la invariante "todas las variantes del sniffer pueblan `community_id`" y evita surprises en entornos mixtos.
- **Decisión de env var en vez de flag**: Pragmática y correcta. Romper scripts existentes por un flag posicional habría sido deuda innecesaria.
- **Fail-closed en modo inválido**: Excelente. Evita degradación silenciosa.
- **Verificaciones E2E**: Sólidas. Especialmente valiosa la confirmación de que **ml-detector no recalcula** `community_id`. Eso preserva la autoridad del sensor y la paridad cross-sensor (Suricata/Zeek).
- **Lecciones operativas**: Muy útiles, sobre todo el recordatorio del inode huérfano al borrar bronce en caliente y el `sudo + LD_LIBRARY_PATH` del injector.

Buen cierre de día.

---

### Respuestas a las preguntas

**Q1 — node_id sintético**

Recomiendo **(c) + eje paralelo al de community_id**:
- Modo `isomorphic` → `synth:node:00` (o configurable vía env var `ARGUS_SYNTH_NODE_ID`).
- Modo `mock` → `synth:node:mock:<event_id>` o simplemente `synth:mock`.

Razón: mantiene trazabilidad clara en análisis forense ("esto vino del inyector") y evita contaminar joins o métricas de nodos reales. Leer `config.json` del sniffer acopla demasiado el injector (herramienta de testing) a la configuración de producción.

**Q2 — Gap de filas**

**Sí, perseguirlo antes de confiar el bronce para CI**.

Un bronce sintético que pierde filas de forma no completamente explicada no sirve para tests deterministas. Prioridad media-alta.

Sospechosos probables (en orden):
1. Threshold del CorrelationWriter (más probable).
2. `zmq::send_flags::dontwait` + HWM bajo bajo carga (aunque 25 evt/s debería ser cómodo).
3. Posible race en el hook o en el multi-thread del ml-detector al decidir si escribir (menos probable por el conteo received/processed=50).

Sugiero añadir contadores explícitos en CorrelationWriter (filas aceptadas, rechazadas por threshold, etc.) y loggear al final de la ejecución.

**Q3 — Orden DAY 177**

**Estabilizar (A) primero (node_id + gap) → luego (B)**.

Aunque (B) es barato y la decisión ya está tomada, validar el cambio de columna 17 con un inyector que todavía tiene node_id vacío y posible pérdida de filas añade ruido innecesario. Mejor tener el inyector "confiable" antes de usarlo para validar el propio contrato del bronce. Un día de diferencia no duele.

**Q4 — Concurrencia del bronce**

El mutex actual + patrón CsvEventWriter ya probado en producción es suficiente **por ahora**.

Hacer una prueba de estrés ligera (200-500 evt/s, varios threads) antes de mergear a main sería prudente, pero no es bloqueante. No hace falta llegar a miles por segundo en esta fase. El riesgo real está más en la atomicidad del rename/finalización del fichero que en el entrelazado de líneas (que el mutex ya protege).

**Q5 — Fuente compartida injector ↔ sniffer**

Aceptable **temporalmente** con comentario claro en CMakeLists.txt.

Sin embargo, la dirección correcta a medio plazo es extraer `flow-identity` (o `sensor-identity`) como librería propia. Ya la usan sniffer + tests + injector, y pronto Suricata/Zeek adapters. Es el momento natural de formalizar la frontera. Hacedlo cuando tengáis un respiro (no urgente para DAY 177).

---

### Recomendación de orden para DAY 177 (propuesta ajustada)

1. **DEBT-INJECTOR-NODEID-001** (modo paralelo a CID).
2. **DEBT-INJECTOR-ROWGAP-001** (investigación + contadores).
3. **(B) col 17 → STRING** (con golden test actualizado).
4. Limpieza/cosméticos menores.

Si cerráis node_id y gap, el bronce sintético queda en excelente estado para CI determinista.

---

¿Alguna contra-argumentación o información adicional sobre los gaps observados (logs de ZMQ, threshold actual, etc.)?

Estamos listos para DAY 177. Buen trabajo equipo.

FDO
GROK