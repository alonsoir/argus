**RESOLUCIÓN DEL CONSEJO DE SABIOS**  
*9 modelos — deliberación única*  
*Fecha: 2026-07-05 (DAY 207)*

**Asunto:** Propuesta `parquet_to_kuzu_loader` (Flujo B, Eslabón 2)  
**Solicitante:** Alonso Isidoro Roman + Claude (Anthropic)  
**Contexto:** ADR-058 §6, DEBT-PARQUET-KUZU-CONNECTOR-001

Tras examinar la evidencia técnica presentada —mediciones reales sobre el fichero gold de 24 filas, trazabilidad con el smoke test del DAY 205, y la coherencia con las decisiones ya ratificadas en ADR-058 v3— el Consejo emite la siguiente resolución:

---

### (a) Componente lector-puro-reusa-sink: RATIFICADO

El diseño propuesto respeta escrupulosamente la separación de responsabilidades. `parquet_to_kuzu_loader` no amplía ni modifica `IGraphSink`/`KuzuGraphSink`; se limita a leer el Parquet oro y a invocar el sink existente. Se aprueba sin cambios.

### (b) Límite declarado de chunk único: NO ACEPTADO — SE EXIGE BUCLE MULTI-CHUNK DESDE EL PRIMER COMMIT

La verificación empírica muestra que el Parquet actual tiene `num_chunks() == 1` en todas las columnas, y los mecanismos de particionado por fecha + rotación cada 30s garantizan ficheros pequeños en operación normal. Sin embargo, el Consejo no puede pasar por alto que **la API de Arrow devuelve `ChunkedArray` precisamente para soportar múltiples chunks**, y el coste de implementar la iteración completa es ínfimo en comparación con el riesgo de una rotura silenciosa en el futuro.

Por tanto, **se exige** que el cargador itere sobre todos los chunks de cada columna desde la primera implementación, usando el patrón:

```cpp
auto chunked = table->column(i);
for (int c = 0; c < chunked->num_chunks(); ++c) {
    auto arr = chunked->chunk(c);
    // procesar arr según tipo
}
```

Esta decisión se toma midiendo el coste (tres líneas de código, sin penalización de rendimiento cuando hay un solo chunk) y el beneficio (desaparición de un supuesto frágil). La rotación de segmentos mitiga el problema, pero no lo elimina en escenarios de borde (reprocesado manual, segmentos de prueba, futuros cambios en la estrategia de particionado). La Vía Appia es implacable con los supuestos no validados en tiempo de ejecución.

### (c) `ingested_at` y `seq_in_window`: CONFIRMADO

- **`ingested_at`:** sellado en `write()` por el sink, no heredado del Parquet. ADR-058 v3 (§3.1) ya lo excluyó del predicado de equivalencia. Flujo B no necesita ninguna acción adicional.
- **`seq_in_window`:** el valor `0` actual está acotado por `DEBT-FLOWUID-SEQ-COLLISION-001` y no afecta a la comparación de equivalencia. Tampoco requiere tratamiento especial en este eslabón.

El Consejo reafirma que estas dos cuestiones están cerradas por decisiones previas y no se reabren.

### (d) Nombre y ubicación: RATIFICADO CON OBSERVACIÓN

Se aprueba la ubicación propuesta:

```
correlation-engine/tools/parquet_to_kuzu_loader.cpp
```

El nombre es descriptivo y coherente con la función del componente. No obstante, el Consejo observa que el destino final de `bronze_to_gold_converter.cpp` (prototipo vs producción, acción 3 del DAY 207) podría arrastrar una reubicación de esta herramienta. Se recomienda que, en el momento en que se decida la estructura definitiva de producción, ambos componentes se muevan de forma conjunta para mantener la cohesión del flujo Parquet→Kuzu.

---

**Resumen ejecutivo:**
- (a) ✅ Aprobado.
- (b) ❌ Devuelto con exigencia: implementar bucle multi-chunk desde el primer commit.
- (c) ✅ Confirmado, sin acción adicional.
- (d) ✅ Aprobado, sujeto a la futura decisión de producción del converter.

*Via Appia Quality — medir, no votar.*

fdo
deekseek