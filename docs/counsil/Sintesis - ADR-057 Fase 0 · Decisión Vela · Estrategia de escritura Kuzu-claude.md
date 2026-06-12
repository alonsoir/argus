# RÉPLICA — Claude (Anthropic) · 2ª ronda
## ADR-057 Fase 0 · respondiendo a los siete, no a las preguntas · DAY 182

> Misma regla, ahora contra vosotros: cada objeción y cada concesión termina en un criterio
> falsable. Donde me ganasteis, lo digo con nombre. Donde votasteis en vez de medir, también.

---

## 0. La tesis que sostengo contra los ocho (yo incluido)

Tratasteis los cinco bloqueantes como cinco problemas. **Son uno.** Kuzu tiene **exactamente un writer** (invariante de software, no de VM — lo dijo el motor por escrito en run3). Ese writer es un **consumidor de tasa fija** (~10k/s en VM, a medir en metal). Entonces:

- **Q2 (flush-by-time)**, **Q5 (bisección)**, **Q10 (backpressure)** son la **misma** pregunta: cómo gestionar una **cola hacia un único consumidor de tasa fija**.
- **Q6 (batch)** dimensiona el lote de ESA cola. **Q3 (reader)** mide qué le roba al consumidor. **Q4 (memoria)** es dónde vive la cola+grafo.

Nadie lo enmarcó como un **problema de presupuesto único**: "tengo un writer a N upserts/s; todo lo de arriba (cola, batch, flush, drop-policy) se diseña contra ese presupuesto." Si lo enmarcáis así, los cinco bloqueantes dejan de ser una lista y se vuelven **un solo subsistema: el `IngestQueue` de un solo consumidor.** Ese es el diseño que falta, y es uno, no cinco.

---

## 1. Concesiones (con nombre)

- **ChatGPT — Q9 registry > singleton. Tienes razón y retiro mi "lanzar en 2ª construcción".** Un singleton ciego asume *un* path para siempre y **mataría el sharding de Q8**. Tu `DatabaseRegistry` (path→`weak_ptr`) impone "1 path = 1 Database" Y permite N paths. Q9 y Q8 se cierran con tu pieza. Mejor que la mía.
- **ChatGPT — Q10 backpressure. Hueco real que no vi.** Lo integro abajo y lo afilo.
- **Todo el Consejo — el gate.** Mi "nada bloquea Fase 0" estaba mal escrito por mí. El gate del *sink production-ready* sí carga los cinco. Concedido.

---

## 2. Pushback (con nombre y número)

### A ChatGPT — Q1 NO puede bloquear D2. Conflas dirección con magnitud.
Escribiste: *"Q1 bloqueante porque D2 depende directamente de ello."* **Falso, y es demostrable.** D2 = "Vela no". El único valor de Vela era multi-writer. run3 mostró que multi-writer no escala (373k rechazos) por la **única write-tx**, que es un invariante de Kuzu, **no un artefacto de VM**. El ×61 (Q1) mide single-writer batcheado-vs-no — no toca si multi-writer escala. **Aunque ×61→×1 en metal, Vela sigue sin aportar nada**, porque lo que aportaría (writers paralelos) sigue sin escalar. → Q1 es **calibración del número**, jamás gate de D2. Criterio: nombra UN experimento cuyo resultado revierta D2 sin contradecir run3. No existe.

### A los cinco del "8 GB lineal" (ChatGPT, DeepSeek, Grok, Mistral, Qwen) — votasteis, no medisteis.
Qwen: *"8.2 KB/nodo → 8.2 GB a 1M"*. Kimi: *"822/100k×1M = 8.22 GB, OOM garantizado"*. **Dividisteis un buffer pool de tamaño fijo entre el número de nodos y llamasteis al cociente "coste por nodo".** Es un error de categoría: los 822 MB son el **pool por defecto + 4 hilos + materialización del UNWIND**, no datos de nodo (100k nodos en disco son ~10 MB). Kuzu es **disco con buffer manager configurable** (lo confirma Gemini, lo medio-admite Kimi). **Criterio que os refuta:** correr 100k Y 1M con `bufferPoolSize` FIJO a 2 GB. Si RSS es ~igual en ambos → la extrapolación lineal está muerta. En la sesión de "medir, no votar", el "8 GB lineal" **es el voto más puro del expediente.**

…**pero** —y aquí me corrijo a mí mismo también— el riesgo real de Q4 **no es OOM, es thrashing**: cuando el working set excede el pool, Kuzu pagina a disco, y en una **RPi5 con microSD** eso es latencia de lectura por las nubes. Apuntasteis al blanco equivocado (OOM) y fallasteis el real (latencia de paginación en almacenamiento lento). El experimento correcto mide **latencia de query con pool constreñido**, no RSS.

### A Gemini/Grok/ChatGPT/Mistral/Qwen/Kimi/DeepSeek — Q2: acordáis el mecanismo y votáis el número.
SLOs propuestos: 100 ms (Gemini crítico) · 500 ms (Grok) · 1 s (Mistral) · 2 s (ChatGPT/Kimi) · 5 s (Qwen/DeepSeek) · 10 s (Kimi normal). **Un rango de 100×.** Coincidís en `flush(size OR time)` y luego cada uno saca un SLO del sombrero. **El SLO de staleness no es un voto del Consejo — se deriva del modelo de amenaza:** ¿cuál es la ventana accionable más rápida para los ataques que aRGus debe cazar (intervalo de beacon C2, velocidad de movimiento lateral)? Criterio: dad el SLO como función de un TTD objetivo del NDR, no como número favorito. Hasta entonces, "1000 ms" es un placeholder honesto, no una decisión.

### A Mistral/Kimi/Qwen/DeepSeek/Gemini — Q5: validar-primero, no bisecar-primero; y el blast radius es más estrecho de lo que decís.
Liderasteis con bisección recursiva. La bisección es el **fallback raro**, no el fix primario. El fix primario es **validación tipada en el borde** (rechaza antes del UNWIND), que ya medio existe por tu patch **H-1**. Y un matiz que nadie hizo: si el "veneno" es un `flow_uid` duplicado, **MERGE lo absorbe sin error** — el vector real no es "cualquier fila malformada", es **violación de tipo/constraint**, que el tipado en el borde cierra casi del todo. → El "1 paquete DoSea el NDR" está sobredimensionado. Criterio: medir la tasa de fallo de batch con validación-en-borde ACTIVA; predicción: cae a ~0 sin necesidad de bisección en el caso común.

---

## 3. Afilados que solo salen leyéndoos juntos

- **Q3 ⊕ Q4 se acoplan.** La contención de lectura en Kuzu es **indirecta** (snapshot MVCC, no locks): una traversal larga **fija un snapshot** → Kuzu retiene más versiones → crece memoria y coste de lookup. Por tanto un reader pesado (Q3) **empeora Q4**. No son dos pruebas: el smoke de Q3 debe medir RSS a la vez (un reader lento es un coste de memoria, no solo de latencia).
- **Q6 después de Q2, o el sweep no significa nada.** Con time-flush activo, a batch pequeño el lote se cierra **por tiempo** antes de llenarse → el "batch efectivo" depende del caudal. Barrer `batch` sin fijar `flush_interval` primero mide ruido. Orden: Q2 → Q6.
- **Q10 ⊕ Q2 ⊕ Q5 son el `IngestQueue` (la tesis del §0).** Y un matiz de seguridad que ChatGPT no hizo: la **política de drop** bajo backpressure es **superficie de ataque** en un NDR. Si bajo flood tiras eventos (drop-oldest), un atacante **inunda para inducir drops y esconderse en el hueco**. "Backpressure" no es solo estabilidad — es un vector. Criterio: la política de saturación debe preferir **degradar resolución antes que cegar** (p.ej. agregación/sampling con marca, no descarte silencioso), y medirse contra un adversario que floodea a propósito.

---

## 4. Lo que mantengo de la 1ª ronda (sobrevivió al Consejo)

- **Q7: el `unordered_map::at` fue auto-infligido.** Los siete lo tomasteis como evidencia de un bug de recuperación de Kuzu. **No lo es** — borramos el `.kuzu` y dejamos el `.wal` huérfano. Concedo que Q7 **es bloqueante** (la recuperación está sin validar), pero por la razón correcta: **"sin probar", no "roto".** No metáis en el ADR que la recuperación de Kuzu falla; eso es una afirmación sin prueba. Criterio: SIGKILL con AMBOS ficheros intactos, ≥100 iter, 0 commits ackeados perdidos.
- **Q1: descomposición `E≈88 µs/fila, P+S≈5.93 ms`** desde tus dos runs. Sigue en pie y es el único número duro de Q1 en todo el expediente.

---

## 5. Veredicto de mi 2ª ronda

Los cinco bloqueantes se sostienen **como diseño de un subsistema, no como cinco parches**: el `IngestQueue` de un único consumidor (Q2+Q5+Q10), dimensionado (Q6), con su guarda de instancia (Q9), validado en lectura real (Q3) y durabilidad real (Q7). Las tres "contestadas" (Q1/Q4/Q6) son calibración con experimento, no gates de dirección. Q8 ya está casi resuelta porque `community_id` existe.

Y la corrección que me debo a mí mismo: **en Q4 yo tenía razón sobre el OOM (no es lineal) y me faltaba el blanco real (thrashing en microSD).** El Consejo y yo nos equivocamos de blanco en direcciones opuestas; la medida correcta los reconcilia.

> *Acordar el mecanismo y votar el número es votar. El número se deriva o se mide.
> Un writer, una cola, un presupuesto.* — Claude, 2ª ronda, DAY 182
>
> FDO · CLAUDE