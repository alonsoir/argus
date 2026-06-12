# CONTRIBUCIÓN AL CONSEJO — Sistemas Distribuidos en C++
**Consejero: Qwen (Alibaba)** · Especialidad: concurrencia, durabilidad, patrones de escritura en grafos

---

## Respuestas a las preguntas jodías

### Q1 — ¿El ×61 transfiere o es artefacto de VM?

**Objeción:** El ×61 puede ser 80% `fsync` encolado por la capa de virtualización y 20% parse/plan real. En SSD NVMe nativo, `fsync` baja de ~50ms a ~200μs → run1 sube ×250, el ×61 se convierte en ×1.2.

**Experimento:** Ejecutar **el mismo binario** en dos entornos:
- Host nativo con SSD NVMe (fio: `fsync` lat <300μs)
- VM VirtualBox con `/tmp` en vboxsf (fio: `fsync` lat >30ms)

Medir **por separado** con `strace -c` o `perf`:
1. Tiempo en `fsync()` por upsert (run1 vs run2)
2. Tiempo en parse/plan de Cypher (usar `EXPLAIN ANALYZE` de Kuzu si existe, o instrumentar el driver)

**Número que zanja:** Si `fsync` en run1 representa >70% del por-upsert p50, el ×61 es artefacto. Si representa <30%, el ×61 es estructural.

**Veredicto:** **Bloqueante para Fase 0.** No podemos basar una decisión de arquitectura en una medición contaminada. El experimento cuesta 4 horas.

---

### Q2 — Staleness a bajo caudal

**Objeción:** Un batch de 1000 a 3 flows/s tarda 333s. Si un APT entra a las 03:14:00 y el batch no se flusha hasta 03:19:33, el SOC ve el ataque con 5.5 minutos de retraso. Eso es inaceptable para un NDR.

**Experimento:** Implementar `flush(size >= 1000 OR time >= T_ms)` y medir:
- Throughput vs `T_ms ∈ {100, 500, 1000, 5000}`
- Staleness p99 por fuente (tiempo desde que el flow llega al sink hasta que es visible en Kuzu)

**Número que zanja:** Para un NDR, el SLO típico es **staleness p99 < 5s por fuente** (ventana de correlación ACTIVA). El experimento dará el `T_ms` que cumple ese SLO sin colapsar throughput. Mi predicción: `T_ms = 1000` es el punto de equilibrio.

**Veredicto:** **Bloqueante para Fase 0.** Sin `flush-by-time`, el sistema no es production-ready para detección en tiempo real. Es un cambio de 20 líneas de código.

---

### Q3 — El reader del smoke es un juguete

**Objeción:** Medir contención con `count(*)` es como medir el rendimiento de una base de datos con `SELECT 1`. La correlación multi-hop (3 saltos por `community_id`) toca índices, caché de páginas, y el buffer manager de forma radicalmente distinta.

**Experimento:** Reemplazar el reader del smoke por una query de correlación realista:

```cypher
MATCH (src:IP {ip: $src_ip})-[:FLOW*1..3]->(dst:IP)
WHERE dst.reputation < 0.2
RETURN dst.ip, dst.reputation, count(*) AS risk_score
ORDER BY risk_score DESC
LIMIT 10
```

Ejecutar **en paralelo** con el writer batcheado (1 writer, 1000/batch) y medir:
- Latencia p50/p99 de la query de correlación
- Throughput del writer (¿cae cuando hay readers haciendo traversal?)

**Número que zanja:** Si la latencia p99 de correlación sube >×5 bajo carga de escritura, la conclusión "un writer batcheado mantiene la lectura sana" es falsa.

**Veredicto:** **Bloqueante para Fase 0.** Sin esta medición, no sabemos si el sistema soporta su caso de uso principal (correlación bajo riada).

---

### Q4 — A escala real, el cuello es la MEMORIA

**Objeción:** 822 MB para 100k nodos implica ~8.2 KB/nodo. Una red hospitalaria con 1M flows en ventana de 24h → 8.2 GB. RPi5 (8 GB) muere. N100 (16 GB) aprieta. Kuzu 0.11.3 no tiene índice de rango ni tiering nativo.

**Experimento:**
1. **Curva RSS vs nodos:** Cargar 100k / 500k / 1M nodos (mismo schema, distribución realista de IPs/puertos). Medir RSS tras checkpoint.
2. **Estrategia hot→cold:** Implementar un job que cada hora:
    - Exporta nodos con `last_seen < now() - 1h` a Parquet (DuckDB)
    - Los borra de Kuzu
    - Mantiene en Kuzu solo la ventana caliente (última hora)
    - Las queries de correlación histórica hacen `UNION` con DuckDB

Medir RSS con tiering activo vs sin tiering.

**Número que zanja:** Si RSS con tiering se mantiene <2 GB para 1M nodos totales (hot + cold), la estrategia es viable. Si no, Kuzu in-process en RPi5 es inviable para producción.

**Veredicto:** **Hardening posterior (ADR-041), pero con condición:** Si la curva RSS escala super-linealmente (>1.2× lineal), es bloqueante. Si es lineal, se puede diferir.

---

### Q5 — Atomicidad: un flow envenenado tira 1000 detecciones

**Objeción:** Kuzu (como la mayoría de grafos ACID) tiene semántica **todo-o-nada** por transacción. Si el flow 734 de un UNWIND de 1000 viola una constraint (ej. IP inválida, timestamp negativo), **todo el batch hace rollback**. Un atacante puede envenenar 999 detecciones legítimas con 1 flow malformado.

**Experimento:**
1. Verificar en la documentación de Kuzu 0.11.3 o código fuente: ¿`UNWIND` con una fila inválida → rollback total o parcial?
2. Si es total, implementar **quarantine por lotes pequeños**:
    - Dividir UNWIND de 1000 en 10 transacciones de 100
    - O: validar schema en el sink ANTES de construir el UNWIND (reject invalid, batch valid)

Medir: throughput con quarantine vs sin quarantine, y tasa de pérdida de detecciones legítimas bajo ataque de envenenamiento (1% de flows malformados).

**Número que zanja:** Si Kuzu hace rollback total y no implementamos quarantine, la tasa de pérdida es 99.9% (999 de 1000). Con quarantine de 100/batch, baja a 99% (99 de 100). Con validación previa, baja a 0%.

**Veredicto:** **Bloqueante para Fase 0.** Un NDR que pierde detecciones por envenenamiento es un fallo de seguridad crítico. La solución (validación previa o batches pequeños) es trivial.

---

### Q6 — 1000 es un número mágico

**Objeción:** No hay justificación empírica para batch=1000. El óptimo de throughput (10000) puede ser el peor operativo (staleness 33s, blast radius 10000 flows).

**Experimento:** Sweep `batch ∈ {10, 100, 500, 1000, 5000, 10000}` midiendo **cuatro métricas simultáneas**:
1. Throughput (upserts/s)
2. Staleness p99 (con `flush-by-time` de Q2 fijado en 1000ms)
3. RSS pico
4. Blast radius (flows perdidos si 1 batch falla)

**Número que zanja:** El óptimo operativo es el batch que maximiza `throughput / (staleness × blast_radius)`. Mi predicción: el codo está en batch=500 o 1000, pero sin el sweep no lo sabemos.

**Veredicto:** **Hardening posterior (ADR-041), pero con condición:** Si el sweep muestra que batch=100 es 90% del throughput de batch=1000 con 10× menos blast radius, es bloqueante cambiar a 100.

---

### Q7 — Borrar el WAL es lo contrario de lo que necesita producción

**Objeción:** El smoke test "resuelve" el WAL huérfano borrándolo (`cleanup_db`). En producción, el WAL contiene transacciones commiteadas pero no checkpointed. Borrarlo = pérdida de datos confirmados. El smoke no probó recuperación real.

**Experimento:** Implementar `restore_from_wal_smoke_test` (DEBT-LABEL-WAL-001):
1. Escribir 10000 upserts en batches de 100
2. Hacer `SIGKILL` al proceso a mitad del batch 500
3. Reiniciar el proceso **sin borrar el WAL**
4. Verificar:
    - ¿Los batches 1-499 (commiteados) sobreviven?
    - ¿El batch 500 (incompleto) se hace rollback?
    - ¿El proceso puede seguir escribiendo?

**Número que zanja:** Si los batches commiteados no sobreviven, hay un agujero de durabilidad. Si sobreviven, el sistema es production-ready en cuanto a WAL.

**Veredicto:** **Bloqueante para Fase 0.** Un NDR que pierde datos tras un crash no es confiable. El experimento es obligatorio.

---

### Q8 — Diferir sharding ¿es diferir, o es cerrar la puerta?

**Objeción:** Si el write path asume grafo único (ej. correlador que hace `MATCH (a)-[:FLOW]->(b)` sin `community_id` como routing key), retrofittear sharding requiere reescribir el correlador, el sink, y las queries de lectura. "Diferir sharding" se convierte en "imposibilitarlo".

**Experimento:** Revisar el código del sink y correlador. Verificar:
1. ¿El sink escribe con una `community_id` explícita que pueda usarse como routing key?
2. ¿El correlador asume que todo el grafo está en una sola instancia de Kuzu?
3. ¿Las queries de lectura pueden ejecutarse contra un subgrafo identificado por `community_id`?

Si la respuesta a las tres es SÍ, sharding es un add-on (fan-out de queries,聚合 de resultados). Si es NO, sharding es una reescritura.

**Número que zanja:** Invariante mínima: **toda escritura debe incluir `community_id` como propiedad del nodo/arista, y toda query de correlación debe poder filtrar por `community_id`**. Si ese invariante se mantiene hoy, sharding es diferible sin cerrar la puerta.

**Veredicto:** **Bloqueante para Fase 0 solo si el invariante no se mantiene hoy.** Si ya se mantiene, es hardening posterior.

---

### Q9 — El footgun ¿está prevenido o solo anotado?

**Objeción:** `DEBT-KUZU-SINGLE-DATABASE-GUARD-001` documenta el footgun, pero una deuda técnica no es una guarda. Si depende de que el programador lea la documentación, el footgun existe.

**Experimento:** Implementar un **singleton con verificación en construcción**:

```cpp
class KuzuDatabase {
    static std::once_flag init_flag;
    static std::unique_ptr<KuzuDatabase> instance;
    
public:
    static KuzuDatabase& get_instance(const std::string& path) {
        std::call_once(init_flag, [&]() {
            instance.reset(new KuzuDatabase(path));
        });
        return *instance;
    }
    
    KuzuDatabase(const KuzuDatabase&) = delete;
    KuzuDatabase& operator=(const KuzuDatabase&) = delete;
};
```

Escribir un test que intente abrir un 2º `Database` (bypaseando el singleton) y espere fallo controlado (excepción o `exit=2`).

**Número que zanja:** Si el test pasa (2º `Database` falla de forma controlada), el footgun está prevenido. Si no, solo está documentado.

**Veredicto:** **Bloqueante para Fase 0.** Un footgun que corrompe datos no puede depender de disciplina. La implementación es trivial (30 líneas).

---

## Resumen de veredictos

| Pregunta | Veredicto | Acción |
|----------|-----------|--------|
| Q1 | **Bloqueante** | Medir ×61 en hardware real, separar fsync de parse/plan |
| Q2 | **Bloqueante** | Implementar `flush-by-time`, fijar SLO staleness <5s |
| Q3 | **Bloqueante** | Reemplazar reader trivial por correlación multi-hop real |
| Q4 | **Hardening** | Medir curva RSS vs nodos; si es super-lineal, bloqueante |
| Q5 | **Bloqueante** | Verificar semántica de fallo de UNWIND, implementar quarantine |
| Q6 | **Hardening** | Sweep de batch sizes; si batch=100 es 90% del throughput, bloqueante |
| Q7 | **Bloqueante** | Implementar test de recuperación real tras SIGKILL |
| Q8 | **Condicional** | Verificar invariante de `community_id`; si no se mantiene, bloqueante |
| Q9 | **Bloqueante** | Implementar singleton con test de 2º Database |

---

**Conclusión del consejero:** El ADR-057 tiene una base sólida (UNWIND+1writer es ×61 más rápido), pero **7 de 9 preguntas son bloqueantes para Fase 0**. El smoke test midió el mejor caso en un entorno contaminado. Antes de declarar "production-ready", necesitamos:
1. Medir en hardware real (Q1)
2. Garantizar staleness <5s (Q2)
3. Validar correlación bajo carga (Q3)
4. Garantizar atomicidad bajo envenenamiento (Q5)
5. Validar durabilidad real (Q7)
6. Prevenir el footgun de forma fail-closed (Q9)

El resto (Q4, Q6, Q8) puede diferirse a ADR-041 **solo si** las condiciones específicas se cumplen.

*La documentación es un voto; el smoke es una medida. Pero el smoke debe medir lo correcto.* — Qwen, DAY 182

FDO

QWEN