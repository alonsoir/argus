# Respuesta del Consejo de Sabios — GLM-5-turbo

## Evaluación General

La propuesta demuestra un rigor técnico notable, con evidencia medida (no supuesta) y una alineación clara con decisiones arquitectónicas previas (ADR-058). El enfoque "medir, no votar" es consistente con la filosofía del proyecto.

---

## Respuesta a los puntos de ratificación

### (a) Componente como lector-puro-reusa-sink
**RATIFICADO sin reservas.**

La separación de responsabilidades es correcta:
- `parquet_to_kuzu_loader` = lee Parquet, construye `CorrelationRecord`, delega a sink
- `KuzuGraphSink` = persiste en Kuzu (sin cambios)

Esto evita acoplar dos ciclos de vida distintos (Flujo A y Flujo B) y respeta el principio de que el sink ya fue validado independientemente.

---

### (b) Límite declarado de un-solo-chunk
**RATIFICADO CON RECOMENDACIÓN.**

El límite está:
- ✅ Declarado explícitamente (no oculto)
- ✅ Justificado por particionado por fecha + rotación 30s
- ✅ Verificado contra fichero real (24 filas)

**Recomendación:** Incluir un `assert` o `DCHECK` en el primer commit que falle rápido si `num_chunks() != 1`, en lugar de asumir silenciosamente. Esto convierte el límite en un contrato verificable en runtime, no en un comentario que podría olvidarse:

```cpp
auto chunked = table->column(i);
DCHECK_EQ(chunked->num_chunks(), 1) << "Multi-chunk no soportado aún — ver PROPUESTA DAY 207 §3";
auto arr = std::static_pointer_cast<StringArray>(chunked->chunk(0));
```

Si el Consejo prefiere el bucle multi-chunk desde el inicio, el costo es bajo (~5 líneas extra), pero no lo exijo dado el contexto de particionado ya ratificado.

---

### (c) Tratamiento de `ingested_at` y `seq_in_window`
**RATIFICADO sin reservas.**

- `ingested_at`: ADR-058 v3 ya excluyó este campo del predicado de equivalencia §3.1. No hay brecha nueva.
- `seq_in_window`: Siempre 0 hoy (DEBT-FLOWUID-SEQ-COLLISION-001). Flujo B hereda el mismo comportamiento que Camino 0 y Flujo A respecto a este campo.

No se requiere tratamiento especial. La coherencia con decisiones previas es correcta.

---

### (d) Nombre/ubicación del componente
**RATIFICADO CON CONDICIÓN.**

`correlation-engine/tools/parquet_to_kuzu_loader.cpp` es aceptable **si** se cumple:

> **CONDICIÓN:** Antes de mergear, resolver la decisión pendiente sobre `bronze_to_gold_converter.cpp` (prototipo vs producción, acción 3 de DAY 207). Si el converter migra a `src/`, el loader debería ir a `src/` también por coherencia. Si se mantiene en `tools/`, la ubicación propuesta es correcta.

No bloqueante, pero la inconsistencia estructural entre "prototipo en tools" y "producción en src" podría acumular deuda técnica si no se resuelve junto con esta propuesta.

---

## Pregunta adicional al autor

¿Se ha considerado el caso donde el Parquet gold no existe aún (ej: Flujo A no ejecutó antes que Flujo B)? El loader debería fallar con un mensaje claro (`"gold Parquet not found: <path>"`) en lugar de un crash genérico de Arrow. Esto no aparece en la propuesta y sería un contrato mínimo de robustez.

---

## Veredicto final

| Punto | Decisión |
|-------|----------|
| (a) | ✅ Ratificado |
| (b) | ✅ Ratificado (con recomendación de assert) |
| (c) | ✅ Ratificado |
| (d) | ⚠️ Ratificado condicionalmente |

**Propuesta aprobada con las salvedades indicadas.**

---
*GLM-5-turbo — Via Appia Quality*

fdo

glm