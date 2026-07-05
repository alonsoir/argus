# PROPUESTA AL CONSEJO DE SABIOS — Flujo B: parquet_to_kuzu_loader

**Fecha:** 2026-07-05 (DAY 207)
**Autor:** Alonso Isidoro Roman + Claude (Anthropic)
**Contexto:** ADR-058 §6 — `DEBT-PARQUET-KUZU-CONNECTOR-001` (greenfield, Flujo B:
Parquet → Kuzu, Eslabón 2). Necesario para que el criterio de cierre del medallón
(test de equivalencia Camino-0 ≡ Flujo-A+B, §3.1) sea ejecutable — hoy solo existe
un lado de la comparación (Camino 0 vive; Flujo A vive; Flujo B no).
**Consejo:** Claude, ChatGPT, DeepSeek, Gemini, GLM, Grok, Kimi, Mistral, Qwen (9 modelos).

---

## 1. Responsabilidad única

`parquet_to_kuzu_loader` lee el Parquet oro (cols 0-21, ya materializado por Flujo A
— `bronze_to_gold_converter.cpp`) y lo escribe a Kuzu **reusando el sink existente
sin ningún cambio en `KuzuGraphSink`/`IGraphSink`**. No recalcula nada que Flujo A
ya materializó.

## 2. Por qué separado del converter (no ampliar `bronze_to_gold_converter.cpp`)

- El propio ADR-058 ya distingue Flujo A (bronce→AVRO→Parquet) de Flujo B
  (Parquet→Kuzu) como entidades separadas ("Flujo B — Parquet → Kuzu. Greenfield
  (Eslabón 2)").
- Ampliar el converter mezclaría dos responsabilidades (serializar a Parquet +
  escribir a un grafo), violando "un día, una batalla", y obligaría a reescribir
  la cabecera del `.cpp`, que hoy dice explícitamente "fuera de alcance": test de
  equivalencia completo y conexión a Kuzu.

## 3. Evidencia técnica (medido, no supuesto — DAY 207)

**Patrón de lectura Parquet con Arrow/Parquet C++ 24.0.0-1**, verificado dos veces
contra fichero real:
- API `Result`-based (misma que descubrió el smoke test DAY 205 para
  `parquet::arrow::OpenFile`/`FileReader::ReadTable`, que cambiaron de
  output-parameter a `arrow::Result<T>` en esta versión):
  ```cpp
  auto infile = arrow::io::ReadableFile::Open(path).ValueOrDie();
  auto reader = parquet::arrow::OpenFile(infile, arrow::default_memory_pool()).ValueOrDie();
  auto table = reader->ReadTable().ValueOrDie();
  ```
- Extracción por columna: cast a tipo concreto de Arrow, `std::static_pointer_cast<TipoArray>(
  table->column(i)->chunk(0))`, patrón ya verificado en `eslabon1_smoke.cpp`
  (round-trip AVRO→Parquet, 3 casos: fila normal, NaN, -0.0 — los 3 con `chunk(0)`
  sin iterar).
- **Verificación propia DAY 207** contra el Parquet gold real de 24 filas
  (`/tmp/gold_out.parquet`, generado por el converter tras retirar la copia local
  de `canonicalize_double`, ver `DEBT-CIRCUIT-CANONICALIZE-PARITY-001`):
  `table->column(0)->num_chunks() == 1` y `table->column(21)->num_chunks() == 1`.

**Límite declarado (no oculto):** esta verificación cubre un Parquet de un único
row-group (24 filas). Ficheros mucho mayores podrían fragmentar en varios chunks
por columna, lo que exigiría iterar `for (c = 0; c < chunked_array->num_chunks(); ++c)`
en vez de asumir `chunk(0)`. No bloqueante hoy dado el particionado por fecha +
rotación de segmentos cada 30s ya ratificados (ADR-058 §8) — los ficheros
resultantes seguirán siendo pequeños en la práctica. Se deja explícito para que
el Consejo lo evalúe, no se asume sin más.

## 4. Mapeo de columnas Parquet → `CorrelationRecord` (cols 0-17)

Tipos confirmados contra `write_gold_parquet()` en `bronze_to_gold_converter.cpp`:

| col | campo | tipo Arrow |
|---|---|---|
| 0-4, 7-8, 11-13, 17 | strings (schema_version…authoritative_source) | `StringArray` |
| 5 | flow_start_sec | `Int64Array` |
| 6 | flow_start_nano | `Int32Array` |
| 9-10 | src_port / dst_port | `Int32Array` (asimetría con `uint32_t` del proto, ya ratificada 9/9 DAY 205) |
| 14-16 | fast/ml/overall_threat_score | `DoubleArray` (ya canónicos desde origen — DAY 207, `DEBT-CIRCUIT-CANONICALIZE-PARITY-001`) |
| 21 | flow_uid | `StringArray` — **usado directamente, sin recomputar** |

**Por qué no se recomputa `flow_uid`:** ya está materializado en col 21 por Flujo A,
calculado con la misma `compute_flow_uid` (`flow_uid.hpp`) que usa Camino 0 — mismo
punto único. Recomputarlo sería trabajo redundante y una segunda vía por la que dos
implementaciones podrían divergir con el tiempo.

## 5. Integración con el sink existente — cero cambios en `kuzu_graph_sink.hpp`/`.cpp`

```cpp
KuzuGraphSink sink(db_path, schema_path, logger);
for (/* fila en Parquet */) {
    CorrelationRecord rec = /* reconstruida de cols 0-17 */;
    std::string flow_uid = /* col 21, leída directa */;
    sink.write(rec, flow_uid);
}
sink.flush();
```

## 6. Nota sobre `ingested_at` — ya resuelta por ADR-058 v3, no se reabre hoy

`KuzuGraphSink`/`cypher_builder.hpp::make_bindings` sellan `ingested_at` internamente
al momento de `write()` (comentario propio del header: "ingest_now_ns() sellado a la
ENTRADA, per-fila"), no desde un dato persistido en el Parquet. Para filas que pasan
por Flujo B, `ingested_at` reflejará el momento de ejecución de Flujo B, no el
momento original de Camino 0. **Esto no es una brecha nueva**: ADR-058 v3 ya excluyó
`ingested_at`/`temporal_anomaly` del predicado de equivalencia §3.1 por esta misma
razón (ver `DEBT-CIRCUIT-TEMPORAL-ANOMALY-PARITY-001`, P1, alcance ampliado a
"procedencia de `ingested_at`" en la revisión v2→v3).

## 7. Petición concreta al Consejo

Ratificar:

- **(a)** El componente como lector-puro-reusa-sink: `parquet_to_kuzu_loader` no
  amplía `IGraphSink` ni `KuzuGraphSink`, solo los consume.
- **(b)** El límite declarado de un-solo-chunk (sección 3) como aceptable dado el
  particionado por fecha + rotación de 30s ya ratificados — o, si el Consejo lo
  considera insuficiente, exigir el bucle multi-chunk desde el primer commit en
  vez de diferirlo.
- **(c)** Confirmar que `ingested_at` (sellado en `write()`, no heredado del
  Parquet) y `seq_in_window` (siempre 0 hoy, `DEBT-FLOWUID-SEQ-COLLISION-001`) no
  necesitan tratamiento especial en Flujo B más allá de lo ya decidido en
  ADR-058 v3.
- **(d)** Nombre/ubicación del componente nuevo: propuesta
  `correlation-engine/tools/parquet_to_kuzu_loader.cpp` (o alternativa que el
  Consejo prefiera) — pendiente también de la decisión más amplia sobre destino
  de `bronze_to_gold_converter.cpp` (prototipo vs producción, acción 3 de DAY 207,
  BACKLOG.md).

---

*Via Appia Quality — medir, no votar.*


---

## RESOLUCIÓN FINAL (Alonso, DAY 207)

Tras la ronda de 9 respuestas del Consejo de Sabios, se resuelve:

### (a) Lector-puro-reusa-sink
**Ratificado, sin cambios.** Consenso unánime del Consejo (9/9).

### (b) Chunking — DESVIACIÓN DELIBERADA de la mayoría del Consejo
**Decisión: bucle multi-chunk completo desde el primer commit** (alineado con
la postura minoritaria de DeepSeek, no con la mayoría que proponía
assert-y-diferir).

**Matiz añadido, no propuesto por ningún miembro del Consejo tal cual:** el
bucle procesa TODOS los chunks con normalidad (dato correcto siempre, cero
pérdida silenciosa) — pero se emite un `WARNING` (no excepción, no fail-fast)
cuando `num_chunks() > 1`, únicamente para visibilidad/monitorización de
cuándo el supuesto de "ficheros pequeños, particionado por fecha" empieza a
dejar de cumplirse en la práctica. Razón explícita: un fail-fast (excepción)
puede impedir ver algo importante que sí se podría procesar correctamente;
mejor un WARNING que deja avanzar y avisa, que un corte que oculta el dato.

```cpp
for (int i = 0; i < table->num_columns(); ++i) {
    auto chunked = table->column(i);
    if (chunked->num_chunks() > 1) {
        logger->warn("parquet_to_kuzu_loader: columna {} tiene {} chunks "
                     "(esperado 1 dado el particionado actual) — procesando "
                     "todos, sin pérdida de datos", i, chunked->num_chunks());
    }
    for (int c = 0; c < chunked->num_chunks(); ++c) {
        auto arr = chunked->chunk(c);
        // procesar arr según tipo, fila a fila
    }
}
```

No se abre `DEBT-PARQUET-MULTICHUNK-001` (la propuesta de Qwen) porque la
implementación completa desde el día 1 hace innecesaria esa deuda.

### (c) `ingested_at` / `seq_in_window`
**Ratificado, sin cambios.** Consenso unánime (9/9). No se reabre.

### (d) Nombre/ubicación
**Ratificado, condicionado** a la decisión pendiente de la acción 3 de DAY 207
(destino de `bronze_to_gold_converter.cpp`, prototipo vs producción). Se
mantiene `correlation-engine/tools/parquet_to_kuzu_loader.cpp` como ubicación
provisional; si el converter migra a producción, ambos componentes se mueven
juntos (recomendación coincidente de DeepSeek/GLM/Kimi/Qwen).

### Hallazgos del Consejo incorporados al diseño (no estaban en la propuesta original)

1. **Manejo de error — Parquet gold ausente** (GLM): si Flujo B corre antes de
   que Flujo A haya producido el fichero, debe fallar con mensaje explícito
   (`"gold Parquet not found: <path>"`), no con un crash genérico de Arrow.
   **Incorporado al diseño.**
2. **Nota de punto único de verdad** (ChatGPT): se añade explícitamente —
   "el loader no genera Cypher ni conoce el esquema de Kuzu; toda la lógica
   de persistencia permanece encapsulada en `KuzuGraphSink`". **Incorporado.**
3. **Continuidad de KuzuDB como producto** (Kimi, verificado independientemente
   por Claude vía búsqueda web — ver `DEBT-KUZU-CONTINUITY-001` en BACKLOG.md):
   confirmado con fuentes reales (GitHub, PyPI, The Register, EU DMA filing)
   que KuzuDB fue archivado el 10 de octubre de 2025 tras adquisición de
   Kùzu Inc. por Apple (revelada en filing de febrero 2026). **Decisión de
   Alonso: NO depreciar hoy.** El objetivo actual es demostrar la hipótesis
   de que los datasets generados por el pipeline vía grafo son de calidad
   suficiente para inferir datasets comportamentales académicos — no entregar
   una demo funcional. La evaluación de migración se difiere a: (i) la
   hipótesis queda demostrada → estudio de alternativas post-FEDER (fondos ya
   asegurados), o (ii) aparece un impedimento técnico real en Kuzu 0.11.3 que
   bloquee la demostración de la hipótesis. Documentado como deuda de
   arquitectura, no como acción inmediata.

### Cuestión NO resuelta por esta ronda del Consejo — requiere ronda propia

**El esquema Parquet gold multi-sensor** (aRGus + Suricata + Zeek + Wazuh, con
activación configurable por señal — necesario para el método científico:
poder aislar el efecto de activar/desactivar cada señal) **no estaba en el
documento enviado al Consejo** y por tanto su ratificación de hoy cubre
**únicamente el esquema mono-fuente `correlation_v1`**. Ver
`DEBT-PARQUET-GOLD-SCHEMA-MULTISENSOR-001` en BACKLOG.md — diseño pendiente,
su propia ronda de Consejo antes de que `parquet_to_kuzu_loader` esté completo
para el caso multi-sensor. La v1 del loader se construye contra el esquema
mono-fuente ya ratificado (coherente con "un día, una batalla").

### Cuestión que sigue abierta, sin resolver por nadie todavía

Integridad del Parquet gold en sí (¿un atacante con acceso de escritura al
directorio gold, sin acceso al bronce, podría inyectar filas falsas sin que
Flujo B lo detecte?) — no la abordó ningún miembro del Consejo. No bloqueante
para la v1, pero pendiente de decidir si es alcance de este componente o de
otra capa (permisos de filesystem).
