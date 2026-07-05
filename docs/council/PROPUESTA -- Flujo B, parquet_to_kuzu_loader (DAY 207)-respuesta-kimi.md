

---

# RESPUESTA DEL CONSEJO — `parquet_to_kuzu_loader`

**Fecha:** 2026-07-05 (DAY 207)  
**Voz del Consejo:** Kimi (Moonshot AI)  
**Estado:** **RATIFICADO con condiciones** — 4/4 puntos aprobados, 2 advertencias técnicas.

---

## (a) ✅ RATIFICADO — Lector-puro-reusa-sink

El diseño de `parquet_to_kuzu_loader` como consumidor pasivo de `IGraphSink`/`KuzuGraphSink` es correcto. La separación de responsabilidades sigue el principio "un día, una batalla" y evita la contaminación del `bronze_to_gold_converter.cpp`. No se toca la interfaz del sink.

**Argumento de cierre:** El Flujo B no tiene por qué saber cómo se escribe a Kuzu; solo debe saber qué escribir. Que el sink sepa de Cypher, transacciones y sellado de `ingested_at` es su responsabilidad, no del loader.

---

## (b) ⚠️ RATIFICADO CON ADVERTENCIA — Límite de single-chunk

El Consejo **acepta el límite declarado** como razonable dado el contexto operativo (particionado por fecha + rotación de 30s). Sin embargo, **exige una guarda defensiva en el código desde el primer commit**, no como TODO futuro.

```cpp
// Patrón obligatorio — no asumir, verificar:
for (int col = 0; col < table->num_columns(); ++col) {
    auto chunked = table->column(col);
    if (chunked->num_chunks() != 1) {
        // LOG_FATAL o throw con mensaje explícito que cite ADR-058 §3.1
        // y el nombre del fichero que violó la suposición
    }
}
```

**Razón:** Un `chunk(0)` silencioso en un fichero multi-chunk no falla — trunca datos. Es un bug de corrupción silenciosa, el peor tipo. La guarda convierte una suposición en un contrato verificable en runtime. Cuando el día llegue de soportar multi-chunk, el `LOG_FATAL` te dirá exactamente qué fichero y qué columna rompieron el contrato.

La iteración multi-chunk puede diferirse, pero **la verificación no**.

---

## (c) ✅ RATIFICADO — `ingested_at` y `seq_in_window` no requieren tratamiento especial

Confirmado. ADR-058 v3 ya excluyó ambos del predicado de equivalencia §3.1. El sellado de `ingested_at` en `write()` es consistente con el diseño del sink y no introduce brecha nueva. `seq_in_window` siendo 0 en todos los flujos hoy es un invariante conocido (`DEBT-FLOWUID-SEQ-COLLISION-001`).

**No se reabre.**

---

## (d) ✅ RATIFICADO — Nombre y ubicación propuestos

`correlation-engine/tools/parquet_to_kuzu_loader.cpp` es aceptable. El Consejo sugiere considerar, en la decisión pendiente sobre `bronze_to_gold_converter.cpp` (acción 3 DAY 207), si `tools/` es el destino final o si ambos componentes deberían migrar a `correlation-engine/pipeline/` una vez el prototipo se consolide. Eso es **fuera de alcance de esta propuesta** y correctamente dejado para el BACKLOG.

---

## Advertencia adicional del Consejo: estado de Kuzu

Un miembro del Consejo (Grok, vía búsqueda web) reporta que **KuzuDB ha sido archivado** — el equipo original está en Apple y el proyecto ya no recibe mantenimiento activo . Esto no bloquea la propuesta hoy (el código del sink ya existe y funciona), pero el Consejo insta a que el BACKLOG.md incluya una **deuda de arquitectura** para evaluar migración a Neo4j, DuckDB con extensión de grafo, o alternativa activa antes del demo FEDER (septiembre 2026). No es acción inmediata, pero es riesgo conocido que debe estar documentado.

---

## Resumen de ratificación

| Punto | Estado | Nota |
|-------|--------|------|
| (a) Lector-puro-reusa-sink | ✅ Ratificado | Sin cambios en interfaz |
| (b) Límite single-chunk | ⚠️ Ratificado con guarda defensiva | `num_chunks() == 1` obligatorio en código |
| (c) `ingested_at`/`seq_in_window` | ✅ Ratificado | Sin tratamiento especial |
| (d) Ubicación | ✅ Ratificado | `tools/` aceptado; revisar al consolidar pipeline |

---

*Via Appia Quality — medir, no votar.*  
*El Consejo ha hablado.*

fdo
kimi