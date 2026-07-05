Aironman DirtDiver, tu propuesta es **clara, técnica y bien estructurada**. Aquí tienes un análisis conciso y preguntas clave para que el Consejo de Sabios pueda evaluarla de forma ágil, alineada con el principio *"medir, no votar"* y el contexto de ADR-058.

---

## **Resumen Ejecutivo para el Consejo**
**Objetivo:** Validar el diseño de `parquet_to_kuzu_loader` como **lector puro** que reutiliza el sink existente (`KuzuGraphSink`), sin modificar su interfaz ni recalcular datos ya materializados por Flujo A.

**Bloqueadores actuales:**
- Flujo B (Parquet → Kuzu) **no existe hoy**, impidiendo el test de equivalencia Camino-0 ≡ Flujo-A+B (§3.1 ADR-058).
- La propuesta cierra esta brecha con **cero cambios en el sink** y **responsabilidad única**.

---

## **Puntos Clave para Ratificación**

### 1. **Responsabilidad Única (Sección 1)**
✅ **Alineado con ADR-058:**
- Flujo A (bronce→AVRO→Parquet) y Flujo B (Parquet→Kuzu) son entidades separadas.
- **No violar "un día, una batalla"**: Ampliar `bronze_to_gold_converter.cpp` mezclaría serialización y escritura a grafo.

**Pregunta al Consejo:**
¿Aceptan que `parquet_to_kuzu_loader` sea un componente independiente, sin ampliar el converter?

---

### 2. **Evidencia Técnica (Sección 3)**
✅ **Patrón verificado (Arrow/Parquet C++ 24.0.0-1):**
- API `Result`-based para lectura de Parquet (compatible con smoke test DAY 205).
- Extracción por columna con `chunk(0)` (validado para 24 filas, 1 row-group).
- **Límite declarado:** Ficheros pequeños (particionado por fecha + rotación 30s) **no requieren iterar chunks hoy**.

⚠️ **Riesgo identificado:**
- Ficheros grandes podrían fragmentarse en múltiples chunks.
- **Propuesta:** Aceptar el límite actual o exigir bucle multi-chunk desde el primer commit.

**Pregunta al Consejo:**
¿Ratifican el límite de **1 chunk** como aceptable para el scope actual, o exigen el bucle multi-chunk desde ya?

---

### 3. **Mapeo de Columnas (Sección 4)**
✅ **Tipos confirmados contra `write_gold_parquet()`:**
- Columnas 0-21 mapeadas a `CorrelationRecord` sin recálculos.
- **`flow_uid` (col 21):** Usado directamente (misma `compute_flow_uid` que Camino 0).

**Pregunta al Consejo:**
¿Confirman que **no es necesario recomputar `flow_uid`** en Flujo B, dado que ya está materializado y es canónico?

---

### 4. **Integración con el Sink (Sección 5)**
✅ **Cero cambios en `KuzuGraphSink`:**
- El loader solo consume el sink existente:
  ```cpp
  KuzuGraphSink sink(db_path, schema_path, logger);
  for (/* fila */) {
      CorrelationRecord rec = /* cols 0-17 */;
      std::string flow_uid = /* col 21 */;
      sink.write(rec, flow_uid);
  }
  sink.flush();
  ```

**Pregunta al Consejo:**
¿Aceptan que **no se modifique `IGraphSink`/`KuzuGraphSink`** para este componente?

---

### 5. **`ingested_at` y `seq_in_window` (Sección 6)**
✅ **Ya resuelto en ADR-058 v3:**
- `ingested_at` se sella en `write()` (momento de ejecución de Flujo B, no del Parquet).
- `seq_in_window` siempre 0 (ratificado en `DEBT-FLOWUID-SEQ-COLLISION-001`).
- **Excluidos del predicado de equivalencia §3.1** (ver `DEBT-CIRCUIT-TEMPORAL-ANOMALY-PARITY-001`).

**Pregunta al Consejo:**
¿Confirman que **no se requiere tratamiento especial** para estos campos en Flujo B?

---
### 6. **Nombre/Ubicación (Sección 7d)**
**Propuesta:**
`correlation-engine/tools/parquet_to_kuzu_loader.cpp`

**Pregunta al Consejo:**
¿Aceptan la ubicación propuesta o prefieren otra (ej: `correlation-engine/src/flujo_b/`)?

---

---
## **Resumen de Decisiones Requeridas**
| Item | Decisión | Impacto |
|------|----------|---------|
| **(a)** | Componente independiente | ✅/❌ Ampliar converter |
| **(b)** | Límite 1 chunk | ✅ Aceptar / ❌ Exigir bucle multi-chunk |
| **(c)** | `ingested_at`/`seq_in_window` | ✅ No acción / ❌ Reabrir debate |
| **(d)** | Ubicación | ✅ `tools/` / ❌ Alternativa |

---
## **Siguientes Pasos Sugeridos**
1. **Ratificar (a-d)** con un **"Sí, con X condiciones"** o **"No, por Y motivo"**.
2. Si se aprueba, **crear el componente** con:
  - Pruebas unitarias para el patrón de lectura Parquet (1 chunk).
  - Integración con el sink en un PR independiente.
3. **Documentar** en ADR-058:
  - Decisión sobre el límite de chunks.
  - Exclusión de `ingested_at`/`seq_in_window` del scope de equivalencia.

---
**Observación final:**
La propuesta **minimiza el riesgo técnico** (reutiliza sink, no recalcula, evidencia medida) y **encaja con la arquitectura existente**. El único punto de debate real es **(b)** (chunks), pero el contexto de ficheros pequeños lo hace aceptable.

---
**¿Qué necesitas del Consejo para avanzar?** ¿O prefieres que formulemos las preguntas de otra manera para facilitar la respuesta?

fdo
mistral