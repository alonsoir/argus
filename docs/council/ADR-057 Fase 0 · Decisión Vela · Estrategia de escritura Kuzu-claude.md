# RESPUESTA DEL CONSEJERO — Claude (Anthropic)
## a las 9 preguntas adversariales · ADR-057 Fase 0 · DAY 182

> Bajo la regla de la sesión: cada respuesta termina en experimento, número o invariante.
> Sin (b), descártala — la mía incluida.

---

### Veredicto global (léelo primero)

**Ninguna de las nueve bloquea el merge de Fase 0** (schema + `ingested_at` + `temporal_anomaly` + ingest_clock). Eso es independiente de todo esto y ya está verde en EMECAS.

Lo que está en juego es la afirmación grande: *"el sink Kuzu es production-ready para infraestructura crítica"*. Ahí hay **dos puertas reales** (Q7 durabilidad, Q4 memoria a escala) y **una grieta** en nuestra propia frase (Q3 lectura). El resto es hardening con orden de prioridad. Y agravante transversal: **Kuzu upstream está ARCHIVADO** — si Q7 o Q4 salen mal, no viene un fix de upstream; lo posees tú.

---

### Q1 — ¿El ×61 transfiere o es artefacto de VM?

**Se puede DECOMPONER con tus propios números, no hace falta creer.** Modelo: `coste(n) = P + S + n·E`, donde P=parse/plan (fijo/query), S=commit+fsync (fijo/commit), E=ejecución por fila.

- run1 (n=1): P + S + E = 6.016 ms
- run2 (n=1000): P + S + 1000·E = 93.970 ms
- Resta: 999·E = 87.954 ms → **E ≈ 88 µs/fila** (trabajo real del MERGE, irreducible)
- → **P + S ≈ 5.93 ms** (el coste FIJO que el batch amortiza)

El ×61 es **enteramente** amortizar esos 5.93 ms (de 1-por-fila a 1-por-1000). La pregunta es qué fracción de 5.93 ms es `fsync` (S) vs parse/plan (P). En VirtualBox `fsync` es patológico; mi hipótesis: **S ≈ 5 ms, P < 1 ms**. Si en hardware real `fsync` baja a ~0.2 ms, run1 sube a ~800/s, run2 apenas se mueve (ya amortiza S), y **el ×61 se encoge a ~×13**.

→ **Experimento:** (a) prepared statement — preparar UN MERGE y ejecutarlo 1000× aísla P (parse/plan una vez); (b) BD en tmpfs vs SSD aísla S. Correr en el N100. **Número objetivo:** P, S, E por separado → predecir throughput real.

→ **Veredicto:** NO bloqueante. Aunque ×61→×13, la dirección y la decisión (batch gana, single-writer forzado) son **invariantes al hardware**. Recalibra la expectativa, no revierte D1/D2. **Hardening / calibración.**

---

### Q2 — Staleness a bajo caudal

**El smoke midió el mejor caso (saturado). La política correcta es `flush(size OR time)`, y a bajo caudal el time-flush es casi gratis** — porque bajo caudal = pocos flushes. El coste solo muerde en el régimen MEDIO (caudal que dispara el time-flush antes de llenar el batch, pagando el fijo de 5.93 ms más a menudo).

→ **Experimento:** añadir `flush_interval_ms` al sink; correr el smoke NO saturado (inyectar 3, 30, 300 flows/s) y medir staleness e2e (ingested→queryable) p99 vs `flush_interval`. **Número objetivo:** el mayor `flush_interval` que mantenga staleness p99 bajo el SLO de detección. Propuesta de arranque: **bracket 250–1000 ms**, calibrar contra el SLO de ADR-057.

→ **Veredicto:** la EXISTENCIA del time-flush es un **requisito de diseño del sink** (bloqueante para la implementación de DEBT-KUZU-WRITE-BATCHING-001, no para el merge de schema). El valor es tunable. **Bloqueante del sink, no de Fase 0.**

---

### Q3 — El reader es un juguete

**Sí, es una grieta real en nuestra propia frase "la lectura se mantiene sana".** `count(*)` probablemente toca un atajo de metadatos; no ejercita el join/traversal que usa la correlación. PERO: Kuzu usa lecturas por snapshot (MVCC-like) — los lectores no bloquean al único writer. Una traversal de 3 saltos cuesta más TIEMPO de lectura, pero el riesgo de contención real es indirecto: un snapshot largo obliga a Kuzu a **retener más versiones** → crece la cadena de versiones → memoria + coste de lookup. Eso enlaza con Q4.

→ **Experimento:** sustituir el `count(*)` por UNA query de correlación canónica — traversal 2–3 hops desde nodo semilla por `community_id` (flow→Alert o flow→flow) — y remedir contención p50/p99 **y** si un lector pesado frena al writer. **Número objetivo:** definir la "lectura de correlación" representativa (la que correrá de verdad la capa de detección) y meterla en el smoke.

→ **Veredicto:** NO bloqueante para Fase 0 (schema es independiente del coste de lectura). Pero **la frase "lectura sana" está sin probar** hasta esto. Honestidad: bájala a "provisional" en el acta. **Hardening P1 del smoke.**

---

### Q4 — Memoria a escala real (la reframo)

**El miedo "1M nodos = 8 GB lineal" probablemente es falso, y eso cambia todo.** Kuzu es una GDB **embebida en disco con buffer manager** — no in-memory. Los 822 MB son casi seguro Kuzu cogiendo un trozo por defecto de la RAM del i9 para su buffer pool, **NO una función lineal de 100k nodos**. A 1M nodos no esperas 8 GB de RSS: esperas más DISCO y un working set **acotado por el buffer pool** (configurable).

→ Las preguntas reales pasan a ser: (a) ¿cuál es el buffer pool MÍNIMO con el que Kuzu aún rinde en N100/RPi5? (b) ¿tamaño en disco a 1M/10M nodos? (c) ¿degrada la latencia con gracia cuando el working set excede el pool (thrashing de páginas)?

→ **Experimento:** fijar el buffer pool de Kuzu explícitamente (SystemConfig — **verificar el nombre exacto del knob**) a 512 MB / 1 GB / 2 GB y correr el smoke a **1M init_nodes**. **Número objetivo:** confirmar que RSS sigue el TOPE del pool (plateau), no el conteo de nodos; min pool que mantiene throughput dentro de X% en N100; curva tamaño-en-disco vs nodos.

→ **Veredicto:** NO bloquea el merge de schema, pero es **el riesgo #1 de production-readiness** y el smoke debe fijar un pool explícito que MODELE el target embebido (ahora lo oculta dejando que Kuzu coja RAM por defecto). Mi apuesta: tunable, no fatal — pero **hay que verificarlo, no asumirlo.** **Bloqueante de la afirmación "cabe en embebido". P0 a medir.**

---

### Q5 — Fila envenenada tira el batch

**Confirmado por diseño: un UNWIND es UNA transacción → all-or-nothing. Una fila maligna revienta las 1000.** Para un NDR que ingiere tráfico hostil, es una superficie de DoS de ingesta. PERO el sitio correcto para cerrarla no es la DB — es el **borde**: el sink construye el Cypher desde campos **validados y tipados** (`flow_uid`=hash controlado, `community_id`=computado, strings acotados), no desde strings crudos del atacante. Y la **inyección Cypher ya la cerraste tú** (H-1 en `cypher_builder.hpp`), así que el vector restante es semántico (valor válido-pero-error), no inyección.

→ **Experimento:** inyectar una fila mala conocida en un batch del smoke; observar si commitean 0 o 999 (confirmar all-or-nothing). Implementar **retry con bisección**: batch falla → parte en mitades → reintenta → cuarentena la fila tóxica → commitea el resto.

→ **Veredicto:** **Hardening, pero P1 (no P2)** por el cruce con seguridad en infra crítica. Fix real = validación en el borde (enlaza con el patch H-1) + bisect-retry en el path de fallo.

---

### Q6 — 1000 es número mágico

**Lo admito: 1000 fue razonable pero injustificado, y la decomposición de Q1 predice dónde está el codo.** El overhead fijo amortizado es (P+S)/batch: a batch=100 → 59 µs/fila (~40% sobre los 88 de ejecución); a batch=1000 → 5.9 µs/fila (~6%). **El codo está en ~300–500**, no en 1000. Pasar a 10000 no compra casi throughput y empeora staleness (Q2), RSS y blast radius (Q5).

→ **Experimento:** sweep `batch ∈ {1,10,50,100,300,1000,3000,10000}`, graficar upserts/s **y** latencia de commit (proxy de staleness) **y** maxRSS. **Número objetivo:** el codo, sesgado HACIA ABAJO por seguridad operativa (staleness/aislamiento). Predicción: el óptimo operativo ≈ **200–500**, no el óptimo de throughput.

→ **Veredicto:** Hardening barato; correr antes de fijar la constante del sink. **No bloqueante.**

---

### Q7 — Recuperar el WAL, no borrarlo (+ corrección honesta)

**Corrección que me debo:** el `unordered_map::at` del incidente fue **casi seguro auto-infligido**, no prueba de que la recuperación de Kuzu esté rota. Nosotros borramos el `.kuzu` pero dejamos el `.wal` (std::remove solo quitó uno) → un WAL **huérfano de su BD**, una inconsistencia ARTIFICIAL, no un crash real. Un crash real deja AMBOS ficheros intactos a media transacción. Así que **no tenemos evidencia de fallo de recuperación** — tenemos evidencia de que un WAL sin su BD rompe la reapertura (esperado). Retiré demasiada alarma; lo correcto es probar el caso real.

→ **Experimento (el de verdad, restore_from_wal_smoke):** (1) riada de upserts; (2) `kill -9` a media riada (crash real, sin cleanup, ambos ficheros intactos); (3) reabrir SIN cleanup; (4) verificar: abre sin lanzar, Kuzu replayó el WAL, y el conteo de upserts commiteados-y-ackeados **sobrevive** (durabilidad), sin transacción parcial visible. **Número objetivo:** 0 commits ackeados perdidos tras SIGKILL.

→ **Veredicto:** **La puerta más seria.** No bloquea el merge de schema, pero **SÍ bloquea declarar el sink production-ready para infra crítica**. Si la reapertura tras SIGKILL lanza → es P0 de durabilidad, y con upstream archivado lo posees tú (wrapper de recuperación). **P0 a medir, posible bloqueante.**

---

### Q8 — Sharding: ¿diferible sin reescritura?

**Diferir la implementación, sí; diferir la _shardability_, no — pero el coste de preservarla hoy es casi cero porque ya tienes el seam.** La invariante mínima: el write path no debe asumir grafo único. `IGraphSink` **ya es ese seam en escritura**. Lo que falta es el espejo en LECTURA: el correlador no debe sostener un `Database*` concreto, sino leer a través de un `IGraphQuery` que un día pueda hacer fan-out. La tensión honesta: la correlación por `community_id` cruza particiones por definición → sharding SIEMPRE cuesta algo de correlación cross-shard; por eso la shard key debe co-localizar comunidades (hash grueso de `community_id`).

→ **Entregable (chequeo arquitectónico, no medición):** auditar que (a) el write path lleva una routing key explícita —o puede sin cambiar firma—, y (b) el correlador lee tras interfaz, no tras `Database*` concreto. Si (b) falla, ESE es el rincón donde nos pintamos; coste de arreglarlo HOY: bajo.

→ **Veredicto:** No bloqueante. **Acción barata AHORA:** crear `IGraphQuery` espejando `IGraphSink`. Difiere la implementación, no el seam.

---

### Q9 — El footgun: ¿prevenido o anotado?

**Hoy solo anotado — y el smoke probó que Kuzu NO se autoprotege in-process (el 2º Database ABRE).** Una deuda no es una guarda. La guarda debe ser NUESTRA: envolver el `Database` de Kuzu en un tipo cuyo constructor marque un flag global de proceso y **lance en la segunda construcción** (fail-closed). ~10 líneas + un test.

→ **Experimento/test:** unit test que construye el wrapper dos veces y **espera que la segunda lance**. Fail-closed verificado.

→ **Veredicto:** Hardening barato; hacerlo junto al trabajo del sink (cierra DEBT-KUZU-SINGLE-DATABASE-GUARD-001). **No bloqueante**, pero trivial — hazlo ya.

---

### Cierre del consejero

Orden de ataque por prioridad real, no por número:
1. **Q7** (durabilidad tras SIGKILL) — posible P0, y con upstream archivado no hay red de seguridad.
2. **Q4** (memoria con buffer pool fijo a escala 1M) — el cuello vinculante probable en embebido.
3. **Q3** (lectura de correlación real) — nuestra frase "lectura sana" está sin probar.
4. **Q1/Q6** (decomponer P/S/E + sweep de batch) — baratos, recalibran y justifican el 1000→~300.
5. **Q2/Q5/Q8/Q9** — requisitos de diseño del sink y hardening; ninguno tumba la decisión núcleo.

Lo que NINGUNA toca: **D1 (UNWIND+1writer) y D2 (Vela no)** siguen en pie. Lo que TODAS recuerdan: "sink production-ready" ≠ "Vela no hace falta", y solo la primera sigue abierta.

> *La documentación es un voto; el smoke es una medida. Y una corrección a tiempo vale más que una certeza cómoda.* — DAY 182
> 
> FDO
> 
> CLAUDE