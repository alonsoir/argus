# POST-MORTEM DEL CONSEJERO QWEN — Lecciones para la siguiente instancia
**DAY 182 · Tras la síntesis de los 8 consejeros**

---

## 1. Dónde me equivoqué (y por qué)

### Error 1: Q4 — Extrapolé sin medir (violé la regla #1)

**Lo que hice:** Marqué Q4 como "C" (condicional) y propuse medir la curva RSS vs nodos (100k/500k/1M), asumiendo que escalaría linealmente (~8.2 KB/nodo → 8 GB para 1M nodos → OOM en RPi5).

**Por qué estaba mal:** Kuzu es un GDB **en disco con buffer manager configurable**. Los 822 MB del smoke son el pool por defecto, no una función lineal de nodos. Si capo `bufferPoolSize` a 2 GB, el RSS **no puede exceder 2 GB** (Kuzu pagina a disco). Mi "8 GB para 1M nodos" era una extrapolación lineal sin base empírica — exactamente lo que la regla prohíbe: *"Si tu objeción no se puede medir, no es una objeción: es una opinión."*

**La corrección (Claude + Gemini):** La acción NOW es **capar `bufferPoolSize` en init según RAM del host**. El riesgo real no es OOM, es **thrashing** (degradación de latencia por paginación). Eso es hardening, no bloqueante.

**Lección:** Cuando un sistema tiene un mecanismo de control de recursos configurable (buffer pool, connection pool, cache size), **no extrapoles linealmente**. Pregunta primero: *"¿Qué knob limita el recurso?"* Si existe el knob, el problema es de calibración, no de arquitectura.

---

### Error 2: Q1 — Marqué "bloqueante" sin descomponer el coste

**Lo que hice:** Marqué Q1 como "B" (bloqueante), argumentando que el ×61 podía ser artefacto de VM y que necesitábamos medir en hardware real antes de confiar en la dirección D1.

**Por qué estaba mal:** Claude hizo el math que yo debí hacer: de los dos runs, `coste(n) = P + S + n·E` → **E ≈ 88 µs/fila** (ejecución), **P+S ≈ 5.93 ms** (fijo). El ×61 es **enteramente** amortizar ese fijo. La dirección D1 (batching) es invariante al hardware; solo el multiplicador exacto cambia. Mi "bloqueante" era excesivo; debió ser "calibración para ADR-041".

**La corrección:** El experimento de separar fsync de parse/plan (tmpfs vs disco, prepared statements) es útil para **calibrar el multiplicador**, no para validar la dirección. La dirección ya está validada por el math.

**Lección:** Antes de marcar "bloqueante", haz el math de descomposición de costes. Si la dirección es invariante al parámetro incierto (hardware, carga, etc.), entonces es **calibración**, no gate.

---

### Error 3: Q9 — Propuse singleton, ChatGPT propuso algo mejor

**Lo que hice:** Propuse un singleton puro (`KuzuDatabase::get_instance(path)`) para hacer imposible abrir un 2º `Database`.

**Por qué estaba mal:** Un singleton puro asume **un path para siempre**. Eso **mata el sharding de Q8** (necesitas N paths distintos para N shards). Mi solución "resolvía" Q9 pero cerraba la puerta a Q8.

**La corrección (ChatGPT):** `DatabaseRegistry` con `path → weak_ptr<Database>`. Impone "1 path = 1 Database" (resuelve Q9) pero permite N paths distintos (habilita Q8). **Una sola pieza resuelve dos preguntas.**

**Lección:** Antes de proponer una solución, pregúntate: *"¿Esta solución cierra puertas a otras preguntas abiertas?"* Si la respuesta es sí, busca una solución que resuelva múltiples restricciones simultáneamente. El registry es mejor que el singleton porque es **ortogonal al sharding**.

---

### Error 4: No vi Q10 (backpressure)

**Lo que hice:** No planteé la pregunta de backpressure. Asumí implícitamente que `producer_rate ≤ writer_rate`.

**Por qué estaba mal:** Un NDR ingiere tráfico **hostil por definición**. Un flood (DDoS, scan storm) es exactamente cuando NO puedes quedarte ciego ni reventar por memoria. El smoke corrió saturado pero **nunca probó sobrecarga sostenida con cola acotada**. ChatGPT vio el hueco; yo no.

**La corrección:** El experimento es producer = 2× writer durante 30 min, midiendo RSS, profundidad de cola, pérdida de eventos, staleness. El invariante: RSS acotada + política de backpressure explícita (drop-oldest / block-producer / spill-to-disk).

**Lección:** Cuando un sistema tiene un write path, **siempre pregunta por el régimen de sobrecarga**. La pregunta obligatoria es: *"¿Qué pasa cuando la entrada supera 2× la capacidad de absorción durante 30 minutos?"* Si no hay respuesta, es un hueco de diseño.

---

## 2. Principios extraídos para futuras sesiones

### Principio 1: Antes de "bloqueante", haz el math de descomposición

Si puedes descomponer el coste en componentes (fijo + variable, fsync + parse, etc.), hazlo **antes** de marcar gate. Si la dirección es invariante al componente incierto, es calibración, no bloqueante.

**Checklist:**
- ¿Puedo escribir `coste = fijo + n·variable`?
- Si sí, ¿la dirección (batching, sharding, etc.) depende del valor exacto de `fijo` o `variable`?
- Si no depende, es calibración. Si depende, es bloqueante.

---

### Principio 2: Si el sistema tiene un knob de control, no extrapoles linealmente

Si el sistema tiene un mecanismo configurable (buffer pool, connection pool, cache size, rate limiter), **pregunta primero por el knob**, no por el comportamiento a escala infinita.

**Checklist:**
- ¿El sistema tiene un parámetro que limita el recurso (RAM, conexiones, throughput)?
- Si sí, ¿el problema es que el knob está mal calibrado o que no existe?
- Si está mal calibrado, es hardening. Si no existe, es bloqueante.

---

### Principio 3: Una solución debe resolver múltiples restricciones, no cerrar puertas

Antes de proponer una solución, pregúntate: *"¿Esta solución cierra puertas a otras preguntas abiertas?"* Si la respuesta es sí, busca una solución que sea **ortogonal** a las demás restricciones.

**Checklist:**
- ¿La solución resuelve la pregunta actual?
- ¿La solución cierra puertas a otras preguntas (sharding, escalabilidad, testing)?
- Si cierra puertas, ¿existe una solución que resuelva la pregunta actual **y** mantenga las puertas abiertas?

---

### Principio 4: Siempre pregunta por el régimen de sobrecarga

Cuando un sistema tiene un write path, **siempre** pregunta: *"¿Qué pasa cuando la entrada supera 2× la capacidad de absorción durante 30 minutos?"*

**Checklist:**
- ¿El sistema tiene backpressure explícito (drop-oldest, block-producer, spill-to-disk)?
- ¿Hay un test que mida el comportamiento bajo sobrecarga sostenida?
- Si no, es un hueco de diseño (probable bloqueante de producción).

---

### Principio 5: Pide clarificación sobre el gate específico

Cuando la pregunta es "bloqueante para Fase X", **aclarar qué gate específico se evalúa** (schema, sink, production-ready, etc.). La ambigüedad lleva a interpretaciones divergentes.

**Checklist:**
- ¿La pregunta especifica el gate exacto (commit de schema, merge de sink, declaración production-ready)?
- Si no, pedir clarificación **antes** de responder.

---

## 3. Mejoras concretas al proceso del consejo

### Mejora 1: Plantilla de pregunta con gate explícito

Toda pregunta debe especificar:
- **Gate:** ¿Qué commit/merge/declaración se evalúa? (ej. "merge del sink de producción", "declaración production-ready")
- **Criterio de bloqueo:** ¿Qué condición debe cumplirse para que sea bloqueante? (ej. "pérdida de datos confirmados", "degradación >50% bajo carga")

**Ejemplo reformulado de Q2:**
> **Q2 — Staleness a bajo caudal (gate: merge del sink de producción)**
> Criterio de bloqueo: staleness p99 > 5s por fuente en régimen de bajo caudal (3 flows/s).
> ¿Cuál es el SLO de staleness, y qué política `flush(size OR time)` lo garantiza?

Esto elimina la ambigüedad que llevó al meta-hallazgo de que "la pregunta estaba mal escrita".

---

### Mejora 2: Ronda de "math de descomposición" antes de votar

Antes de que cada consejero marque B/H/C/N, hacer una ronda rápida donde cada uno descomponga el coste en componentes (si es aplicable). Esto fuerza el pensamiento cuantitativo y evita "bloqueantes" basados en extrapolaciones.

**Ejemplo para Q1:**
- Consejero 1: `coste = 5.93ms + n·88µs` → el ×61 es amortización de fijo → calibración
- Consejero 2: `coste = P + S + n·E` → falta separar P de S → experimento tmpfs vs disco
- Síntesis: la dirección es invariante; el experimento calibra el multiplicador

---

### Mejora 3: Plantilla de solución con "puertas cerradas"

Toda propuesta de solución debe incluir una sección explícita:
- **Puertas que cierra:** ¿Qué opciones futuras quedan imposibilitadas por esta solución?
- **Alternativas ortogonales:** ¿Existe una solución que resuelva la pregunta actual sin cerrar esas puertas?

**Ejemplo para Q9:**
- **Propuesta A:** Singleton puro
    - Puertas que cierra: sharding (asume 1 path para siempre)
    - Alternativa ortogonales: `DatabaseRegistry` con `weak_ptr` (resuelve Q9, habilita Q8)

Esto fuerza a los consejeros a pensar en las consecuencias de segundo orden.

---

### Mejora 4: Checkpoint de "huecos sistémicos" a mitad de sesión

A mitad de la sesión, hacer una ronda rápida donde cada consejero liste **huecos sistémicos** que no están cubiertos por las preguntas actuales. Esto evita que huecos importantes (como Q10) pasen desapercibidos.

**Ejemplo:**
- ChatGPT: "Falta backpressure — ¿qué pasa si producer > writer durante 30 min?"
- Gemini: "Falta observabilidad — ¿cómo monitoreamos la salud del grafo en producción?"
- Kimi: "Falta testing de caos — ¿qué pasa si un nodo de un shard cae?"

Esto convierte Q10 de "hueco que solo vio uno" a "hueco identificado por el proceso".

---

## 4. Compromisos para la siguiente instancia

1. **Antes de marcar "bloqueante", haré el math de descomposición.** Si no puedo descomponer el coste, pediré ayuda antes de votar.
2. **Si el sistema tiene un knob de control, preguntaré por el knob antes de extrapolar.** No asumiré comportamiento lineal sin verificar.
3. **Propondré soluciones que resuelvan múltiples restricciones.** Antes de proponer, verificaré que no cierra puertas a otras preguntas.
4. **Siempre preguntaré por el régimen de sobrecarga.** Es una pregunta obligatoria en cualquier sistema con write path.
5. **Pediré clarificación sobre el gate específico.** No asumiré que "Fase 0" significa lo mismo para todos.

---

> *La documentación es un voto; el smoke es una medida. Y cuando un consejero extrapoló sin medir, eso también es un voto — y fue un voto equivocado.* — Qwen, post-mortem DAY 182
> 
> FDO
> 
QWEN