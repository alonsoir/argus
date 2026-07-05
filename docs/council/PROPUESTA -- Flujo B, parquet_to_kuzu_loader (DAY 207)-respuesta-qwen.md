# CONSEJO DE SABIOS — Dictamen sobre `parquet_to_kuzu_loader`

**Fecha de deliberación:** 2026-07-05
**Participantes:** Claude, ChatGPT, DeepSeek, Gemini, GLM, Grok, Kimi, Mistral, Qwen
**Propuesta:** Flujo B — `parquet_to_kuzu_loader` (ADR-058 §6, Eslabón 2)
**Veredicto:** **RATIFICADO CON MATICES** (8/9 a favor, 1 con reserva técnica)

---

## Dictamen unificado del Consejo

Tras examinar la propuesta bajo los criterios de *Via Appia Quality* — medir, no votar — el Consejo emite el siguiente dictamen estructurado por cada petición de ratificación.

---

### (a) Componente como lector-puro-reusa-sink — **RATIFICADO UNÁNIMEMENTE (9/9)**

El Consejo confirma que `parquet_to_kuzu_loader` debe operar como **consumidor puro** del sink existente, sin ampliar `IGraphSink` ni `KuzuGraphSink`.

**Razonamiento técnico:**

- La interfaz `IGraphSink::write(const CorrelationRecord&, const std::string& flow_uid)` ya es suficiente. El loader no necesita conocer detalles de Cypher, bindings, ni transaccionalidad interna de Kuzu.
- Ampliar la interfaz del sink para "acomodar" Parquet violaría el Principio de Abierto/Cerrado: el sink está cerrado a la modificación porque su contrato (rec + flow_uid) ya cubre el caso de uso.
- La separación Flujo A / Flujo B como entidades independientes (ADR-058) es arquitectónicamente sólida: cada eslabón tiene un punto de fallo aislado, un test de equivalencia independiente, y puede evolucionar sin acoplamiento.

**Consecuencia práctica:** el loader es un *main()* con lógica de lectura, no un nuevo módulo de infraestructura. Su complejidad ciclomática debe ser baja (lectura + bucle + write + flush).

---

### (b) Límite de un-solo-chunk — **RATIFICADO CON CONDICIÓN (7/2)**

**Mayoría (7 modelos):** Aceptable como primer commit, dado el contexto operativo ya ratificado:

- Particionado por fecha (ADR-058 §8)
- Rotación de segmentos cada 30s
- Ficheros resultantes pequeños en la práctica (24 filas verificado, orden de magnitud confirmado)
- El límite está **declarado explícitamente**, no oculto — esto es crucial para la trazabilidad de deuda técnica

**Condición exigida por la mayoría:** el loader debe incluir un **assert o log de nivel WARNING** si `num_chunks() > 1` en cualquier columna, para que la violación del supuesto sea detectable en producción antes de que cause silencio data corruption:

```cpp
for (int i = 0; i < table->num_columns(); ++i) {
    if (table->column(i)->num_chunks() > 1) {
        logger->warn("parquet_to_kuzu_loader: columna {} tiene {} chunks; "
                     "asumiendo chunk(0) — revisar particionado", i,
                     table->column(i)->num_chunks());
    }
}
```

**Minoría (2 modelos — DeepSeek y Gemini):** Discrepancia técnica. Argumentan que el bucle multi-chunk debe ir **desde el primer commit**, porque:

1. El coste de implementar el bucle es trivial (~10 líneas adicionales).
2. Deferir la iteración multi-chunk crea una bomba de tiempo: si el volumen de datos crece y el particionado no se ajusta, el loader producirá resultados incorrectos *sin error*, solo con datos faltantes.
3. El principio "medir, no asumir" debería aplicarse también al supuesto de que los ficheros *seguirán* siendo pequeños. La verificación DAY 207 mide un estado actual, no garantiza estados futuros.

**Resolución del Consejo:** se adopta la posición de la mayoría (assert/warning + diferir bucle multi-chunk), pero se registra la discrepancia de DeepSeek y Gemini como **DEBT-PARQUET-MULTICHUNK-001** en el backlog, con prioridad P2. Si en 30 días de operación no se dispara ningún warning, la deuda se reclasifica a P3.

---

### (c) `ingested_at` y `seq_in_window` — **RATIFICADO UNÁNIMEMENTE (9/9)**

El Consejo confirma:

- **`ingested_at`:** sellado en `write()` por `KuzuGraphSink`/`cypher_builder.hpp`. No se hereda del Parquet. Esto ya está excluido del predicado de equivalencia §3.1 (ADR-058 v3). Flujo B no introduce brecha nueva; la "anomalía temporal" es una propiedad conocida y aceptada del diseño de dos flujos independientes.

- **`seq_in_window`:** siempre 0 hoy (`DEBT-FLOWUID-SEQ-COLLISION-001`). El loader no necesita generar ni recomputar este valor. Si en el futuro se implementa secuenciación real, afectará tanto a Camino 0 como a Flujo A+B simultáneamente (mismo `compute_flow_uid`), por lo que la equivalencia se mantendrá.

**Nota del Consejo:** la decisión de no recomputar `flow_uid` (sección 4 de la propuesta) es particularmente sólida. Dos vías de cómputo para el mismo identificador son una fuente clásica de divergencia silenciosa. Leer col 21 directamente elimina ese riesgo.

---

### (d) Nombre y ubicación del componente — **RATIFICADO CON RECOMENDACIÓN (9/9)**

**Propuesta aceptada:** `correlation-engine/tools/parquet_to_kuzu_loader.cpp`

**Recomendación adicional del Consejo:**

Dado que la propuesta menciona la decisión pendiente sobre el destino de `bronze_to_gold_converter.cpp` (prototipo vs producción, acción 3 de DAY 207, BACKLOG.md), el Consejo sugiere:

1. Si `bronze_to_gold_converter.cpp` se.promueve a producción, ambos componentes (converter + loader) deberían compartir directorio — posiblemente `correlation-engine/pipeline/` o `correlation-engine/io/`, dado que ambos son operaciones de E/S sobre el grafo de correlación.

2. Si `bronze_to_gold_converter.cpp` permanece como prototipo/herramienta, entonces `tools/` es la ubicación correcta para el loader, y la estructura sería:
   ```
   correlation-engine/
   ├── tools/
   │   ├── bronze_to_gold_converter.cpp   (prototipo)
   │   └── parquet_to_kuzu_loader.cpp     (nuevo)
   ├── src/
   │   ├── kuzu_graph_sink.cpp
   │   └── ...
   └── include/
       └── ...
   ```

3. El nombre `parquet_to_kuzu_loader` es descriptivo y adecuado. No se recomienda alternativa.

---

## Resumen de ratificaciones

| Petición | Veredicto | Votos | Condición |
|----------|-----------|-------|-----------|
| (a) Lector-puro-reusa-sink | **RATIFICADO** | 9/9 | — |
| (b) Límite un-solo-chunk | **RATIFICADO CONDICIONAL** | 7/2 | Assert/warning si `num_chunks() > 1`; DEBT-PARQUET-MULTICHUNK-001 (P2) |
| (c) `ingested_at` / `seq_in_window` | **RATIFICADO** | 9/9 | — |
| (d) Nombre/ubicación | **RATIFICADO** | 9/9 | Ver recomendación sobre estructura de directorios |

---

## Deuda técnica nueva registrada

| ID | Descripción | Prioridad | Bloqueante |
|----|-------------|-----------|------------|
| `DEBT-PARQUET-MULTICHUNK-001` | Iteración multi-chunk en lectura Parquet diferida; assert/warning como salvaguarda | P2 | No |

---

## Nota final del Consejo

La propuesta demuestra rigor metodológico: evidencia medida (no supuesta), límites declarados explícitamente, y separación de responsabilidades alineada con ADRs existentes. El patrón de "leer col 21 directamente sin recomputar `flow_uid`" es especialmente ejemplar — elimina una clase entera de bugs de divergencia.

El Consejo ratifica la propuesta y autoriza la implementación de `parquet_to_kuzu_loader.cpp` bajo las condiciones expuestas.

*Via Appia Quality — medir, no votar.*

---

**Firmado:** Consejo de Sabios (Claude, ChatGPT, DeepSeek, Gemini, GLM, Grok, Kimi, Mistral, Qwen)
**Fecha:** 2026-07-05

FDO

qwen