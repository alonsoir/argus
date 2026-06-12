# ACTA DE REVISIÓN ADVERSARIAL — Consejo de Sabios
## ADR-057 Fase 0 · Decisión Vela · Estrategia de escritura Kuzu
**aRGus NDR — DAY 182** · Ponente: Alonso Isidoro Roman · Orquestación: Claude (Anthropic)

> **Regla de la sesión: _medir, no votar._**
> No se acepta "creo que" ni "probablemente". Cada respuesta termina en un experimento,
> un número objetivo o un invariante verificable. Si tu objeción no se puede medir, no es
> una objeción: es una opinión, y se descarta.

---

### 0. Qué NO se relitiga (ya medido, cerrado)

- El lock de Kuzu es **cross-proceso** (2º proceso rechazado, `exit=2`) e **in-process es un footgun**: un 2º `Database` sobre el mismo path **abre** → dos buffer managers sobre los mismos datos → corrupción. Medido en bloque [B].
- Kuzu permite **una sola write-tx en todo el sistema**. No es interpretación; es el motor hablando:
  > *"Cannot start a new write transaction in the system. Only one write transaction at a time is allowed in the system."*
- **Multi-writer sobre UN grafo no escala**: 4 writers → +37 % de throughput a cambio de **373.000 rechazos** y contención de lectura p99 **×11.37**. Medido en run3.

Quien quiera reabrir esto trae una **medición** que lo contradiga, no un argumento. Vela y el multi-writer están muertos por datos.

---

### 1. La evidencia

i9 / VirtualBox, `/tmp` nativo del guest (no vboxsf), 5 s, grafo inicial 100k, upsert write-heavy ~100:1:

| run | estrategia | upserts/s | por-upsert p50 | maxRSS | veredicto |
|-----|-----------|-----------|----------------|--------|-----------|
| 1 | MERGE/fila (sink **actual**) | 164 | 6.015.866 ns | 632 MB | overhead por-`query()` |
| 2 | UNWIND batch=1000, **1 writer** | 10.000 | 93.970 ns | 682 MB | **×61 más rápido** |
| 3 | UNWIND batch=1000, **4 writers** | 13.800 | 96.829 ns | 822 MB | 373k rechazos, no escala |

Absolutos = pesimistas de VM. Lo que transfiere es la **forma** (×61), no el número. Hardware real → ADR-041 (RPi5/N100).

---

### 2. Las decisiones que tenéis que ATACAR

- **D1.** El sink de producción escribe con **UNWIND batch + 1 writer único**.
- **D2.** **Vela NO** se adopta. La palanca es el batching de sentencias, no el fork.
- **D3.** Multi-writer descartado (medido). **Sharding diferido** a ADR-041, solo si el writer único batcheado se mide corto en hardware real.
- **D4.** Un `Database`, N `Connections`, servicio in-process único.

**La trampa que quiero que evitéis:** D2 ("Vela no hace falta") es una afirmación pequeña y ya probada. Pero el conjunto D1–D4 implica una afirmación MUCHO mayor — *"UNWIND+1writer es production-ready para un NDR sobre infraestructura crítica"* — y **esa NO está probada**. El smoke midió el techo de escritura en el mejor caso. No midió memoria a escala real, ni lecturas reales, ni durabilidad, ni el régimen de bajo caudal. Disparad ahí.

---

### 3. Preguntas jodías

**Q1 — ¿El ×61 transfiere o es un artefacto de la VM?**
El ×61 está medido donde `fsync` es patológicamente lento (VirtualBox). En el target real (SSD real, sin penalización de VM) `fsync` es barato. Si en run1 el coste era mayoritariamente `fsync`, en hardware real run1 sube y **el ×61 se encoge**. Si era parse/plan, se mantiene. No lo sabemos.
→ *¿Qué experimento mínimo separa el coste de `fsync` del coste de parse/plan en el por-upsert, para saber si el ×61 es estructural o un regalo de la VM?*

**Q2 — Staleness a bajo caudal (el smoke midió el mejor caso).**
El smoke corrió saturado: los batches de 1000 se llenan al instante. En una red tranquila (madrugada en un hospital, 3 flows/s) un batch de 1000 tarda **~5 minutos** en llenarse → ese flow no es consultable por correlación durante 5 minutos. Para un NDR detectando un ataque ACTIVO eso es latencia de detección inaceptable. El flush-by-time no está medido.
→ *¿Cuál es el SLO de staleness por fuente, y qué política `flush(size OR time)` lo garantiza sin matar el throughput? Dame `flush_interval_ms`, no "depende".*

**Q3 — El reader del smoke es un juguete.**
El lector es `count(*)`. La razón de ser de Kuzu es la correlación multi-hop (traversal de 3 saltos por `community_id`). Las cifras de contención (×1.16, ×11.37) están medidas contra una lectura TRIVIAL. Una correlación real bajo la riada de upserts puede contender completamente distinto.
→ *¿La conclusión "un writer batcheado mantiene la lectura sana" sobrevive si el reader es una traversal real? ¿Qué query de correlación representativa hay que meter en el smoke antes de creernos las cifras de contención?*

**Q4 — A escala real, el cuello es la MEMORIA, no la escritura.**
822 MB con 100k nodos. Una red hospitalaria sobre la ventana de retención son **millones** de flows. Si escala lineal, 1M nodos ≈ 8 GB → revienta una RPi5 (8 GB) y aprieta un N100. 100k es un juguete; el cuello vinculante a escala real probablemente sea el working set, no el throughput.
→ *¿Cuál es la curva RSS vs nodos (medir 100k / 500k / 1M)? Y dado que Kuzu 0.11.3 NO tiene índice de rango, ¿cuál es la estrategia de tiering hot→cold (Parquet/DuckDB) que mantiene el grafo caliente acotado?*

**Q5 — Atomicidad: un flow envenenado tira 1000 detecciones.**
Un UNWIND de 1000 filas es UNA transacción. Un NDR ingiere tráfico HOSTIL por definición. Si una sola fila es maligna/malformada, ¿revienta toda la transacción y se pierden las 999 buenas? La escritura por-fila aísla fallos; el batch los propaga.
→ *¿Cuál es la semántica de fallo de un UNWIND batch en Kuzu: rollback total o parcial? Si es total, ¿qué estrategia de quarantine/retry evita que un flow envenenado tire 999 detecciones legítimas?*

**Q6 — 1000 es un número mágico.**
No hay barrido de tamaño de batch. El óptimo es un tradeoff entre throughput (↑), staleness (↑), RSS (↑) y blast radius de fallo (↑). 1000 está puesto a ojo.
→ *¿Dónde está el sweep `batch ∈ {1,10,100,1000,10000}` que justifica el codo de la curva? Y dado Q2/Q5, ¿el óptimo de throughput coincide con el óptimo OPERATIVO, o hay que ceder throughput por staleness/aislamiento?*

**Q7 — Borrar el WAL es lo contrario de lo que necesita producción.**
El smoke "arregla" el WAL huérfano **borrándolo** (`cleanup_db`). En producción eso es catastrófico: el WAL contiene datos **commiteados** aún no checkpointed — borrarlo = pérdida de datos confirmados. El smoke probó que el camino de crash EXISTE; la recuperación sigue sin validar.
→ *¿`restore_from_wal_smoke_test` (DEBT-LABEL-WAL-001) cubre realmente reabrir-y-recuperar tras `SIGKILL` a media riada, verificando que los upserts commiteados sobreviven? Si no, esto es un agujero de durabilidad, no una nota al pie.*

**Q8 — Diferir sharding ¿es diferir, o es cerrar la puerta?**
Retrofittear sharding es un cambio de modelo de datos + fan-out de queries + correlación cross-shard. Si la arquitectura de escritura de HOY no es shard-agnostic, "diferir sharding" es en realidad "imposibilitarlo sin reescritura".
→ *¿Qué invariante mínima hay que mantener HOY en el write path (routing key explícita, correlador sin asunción de grafo único) para que sharding sea un add-on y no una reescritura? Diferir la implementación, sí; diferir la shardability, no necesariamente.*

**Q9 — El footgun ¿está prevenido o solo anotado?**
`DEBT-KUZU-SINGLE-DATABASE-GUARD-001` documenta el footgun, pero una deuda no es una guarda.
→ *¿Cómo se hace IMPOSIBLE (no improbable) abrir un 2º `Database` in-process: singleton con verificación en construcción + test que lo intente y espere fallo controlado? Si depende de la disciplina del programador, no es fail-closed.*

---

### 4. Entregable de cada consejero

Para cada pregunta que respondas:
1. **La objeción en una frase.**
2. **El experimento o el número** que la zanjaría (sin esto, la respuesta se descarta).
3. **¿Bloqueante para el merge de Fase 0, o hardening posterior?**

No quiero consenso. Quiero el agujero que los demás no vieron.

> *La documentación es un voto; el smoke es una medida.* — DAY 182