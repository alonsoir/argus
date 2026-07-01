Excelente ejercicio de rigor. El ADR está excepcionalmente trazado y el invariantismo ("medir, no votar") se respeta en casi todo el documento. Sin embargo, al someterlo a la misma lente de inspección que usáis para el binario, saltan **tres defectos lógicos bloqueantes** (contradicciones internas que harán fallar el predicado §3.1 por diseño) y **dos riesgos de implementación** que conviene sellar antes del primer `commit`.

Aquí tenéis el dictamen del Consejo, categorizado por severidad.

---

### 🔴 BLOQUEANTES (Rompen el predicado §3.1 o la lógica interna)

#### 1. Paradoja de `flow_start_window` (V1 vs §3.1 vs §7)
* **Dónde falla:** Hay una contradicción directa entre la evidencia V1, el predicado de equivalencia y las consecuencias.
* **El problema:** V1 demuestra medido que `flow_start_window` **no existe** en bronce. §7 dictamina que el contrato bronce **no se modifica**. Sin embargo, V1 decide materializar `flow_start_window` como columna del oro. El predicado §3.1 exige: `∀ uid: props_identidad(uid)_C0 == props_identidad(uid)_AB` (donde incluye explícitamente `flow_start_window`).
* **Por qué rompe:** Camino-0 lee bronce. Si bronce no tiene `flow_start_window`, Camino-0 **no puede** poner esa propiedad en el nodo de Kuzu. Flujo-A+B sí la pondrá (porque la calcula en el converter y la escribe en el Parquet oro). Resultado: el predicado fallará siempre en esta columna.
* **Resolución obligada antes de implementar:** Elegid una:
    - **Opción A (Recomendada, limpia):** Actualizar Camino-0 (`main.cpp`) para que compute `window_micros()` en *read-time* (como ya hace para el hash, línea 117) y lo inyecte en el `MERGE ... ON CREATE SET flow_start_window = $window`. Así ambas ramas lo calculan independientemente y el predicado se sostiene.
    - **Opción B:** Excluir explícitamente `flow_start_window` del predicado §3.1 para Camino-0, limitando la equivalencia de esta columna a "Flujo-A la calcula y la guarda en oro, Camino-0 no la usa en el grafo pero comparte el mismo `flow_uid`". (Más débil, vulnera el principio de "oro como ledger verificable" para C0).

#### 2. El vacío de determinismo de `event_id` (§3.1)
* **Dónde falla:** En la definición del predicado: `set(event_id)_C0 == set(event_id)_AB`.
* **El problema:** El ADR congela y traza la generación de `flow_uid` hasta el último bit (V9). Pero **no dice una sola palabra** sobre cómo se genera `event_id` en Camino-0 ni cómo se generará en Flujo-A.
* **Por qué rompe:** Si `event_id` es un UUID v4 (aleatorio), el set de C0 y el set de AB serán distintos aunque la fila sea la misma. Si es un hash de las columnas, ¿cuáles? ¿Incluye timestamp? Si el converter de Flujo-A (greenfield) implementa `event_id` distinto que el reader C++, el predicado falla al 100%.
* **Resolución obligada:** Añadir al ADR el algoritmo exacto de `event_id` (o trazarlo a `fichero:línea` en C++ y dictar que el converter Flujo-A debe invocar el mismo algoritmo o leerlo del bronce si ya viene generado).

#### 3. La trampa del *fallback* en `flow_uid` para Flujo-A (V9)
* **Dónde falla:** En la nota final de V9: *"(o, si es Python, los vectores golden congelados)"*.
* **El problema:** Los "vectores golden congelados" solo sirven para pasar el test de laboratorio. En producción, Flujo-A procesará tráfico real que no está en los vectores golden. Si el converter de Flujo-A es Python y **no** tiene la implementación de `encode_flow_input` (length-prefixed, BE, tag), el circuito fallará en producción el día 1.
* **Resolución obligada:** Corregir la redacción. No es un "o". El decreto es: *El converter Flujo-A (sea C++ o Python) DEBE portar `encode_flow_input` 1:1. Los vectores golden son el test de no-regresión de ese port, no un sustituto del algoritmo.*

---

### 🟡 RIESGOS DE IMPLEMENTACIÓN (Alta probabilidad de fuego en el Eslabón 0)

#### 4. Condición de carrera en `inotify` + Rename (§5)
* **El problema:** El Eslabón 0 propone `inotify`/`IN_CLOSE_WRITE` + escritura atómica `.tmp` → rename. Es el patrón estándar, pero tiene una trampa conocida en Linux: `IN_CLOSE_WRITE` salta cuando el *writer* cierra el fd. Si el writer hace `close()` y luego `rename()`, el watcher verá el cierre del `.tmp`, no del `.csv` final. Si hace `rename()` y luego `close()`, el watcher podría ver el `CLOSE_WRITE` sobre el path *ya renombrado*, pero si el reader levanta el `ifstream` antes de que el kernel termine de vaciar los buffers del filesystem al disco (dirty pages), el reader leerá un fichero truncado o con EOF prematuro.
* **Prevención medible:** El writer **debe** llamar a `fsync(fd)` antes de `close()`. El ADR debería imponer `fsync` como parte del contrato atómico del Eslabón 0 para garantizar que el `ifstream` del reader no sufre partial reads.

#### 5. Idempotencia ZMQ (PUSH/PULL) vs Grafo Kuzu (§2.5 y §3.1)
* **El problema:** Aceptáis at-least-once en ZMQ. Kuzu usa `MERGE` con `ON CREATE SET` (V7), lo que lo hace idempotente para la *creación* de nodos.
* **El riesgo oculto:** ¿Qué pasa con las relaciones (`ALERT_ABOUT`, etc.)? Si un mensaje se duplica en ZMQ, se ejecutará `MERGE (a:Alert)-[:ALERT_ABOUT]->(f:NetworkFlow)` dos veces. Kuzu maneja esto sin error, pero si en el futuro añadís un contador o propiedad en la creación del `MERGE` de la relación, el at-least-once la duplicará. Por ahora es seguro, pero queda como mina terrestre.
* **Acción (P2, no bloquea):** Anotar en el ADR que las relaciones de Kuzu en este circuito son estrictamente stateless (sin contadores) *porque* el nivel de transporte es at-least-once.

---

### 🟢 OBSERVACIONES MENORES (Higiene del ADR)

* **Alcance de "Circuito Completo" (§2.3):** El título dice "Circuito completo aguas abajo", pero se excluye Wazuh (host↔red) y se difiere la ML head. Para evitar que alguien del equipo lea el título y asuma que el dashboard verá hosts, sugiero cambiar el título a: *"ADR-058 — Circuito aguas abajo de RED (medallón: adapters → bronce → LZ → Kuzu → dashboard)"*.
* **HMAC en el predicado (§3.1):** Dice `∀ fila: hmac_row preservado de bronce`. Esto implica que la columna `hmac_row` viaja de bronce a oro, y de oro a Kuzu como una propiedad del nodo. Confirmad que el schema de Kuzu (`schema.cypher`) tiene previsto un string de 64 chars hex para esta columna, o el test fallará por schema mismatch.

---

### Veredicto del Consejo

**NO RATIFICADO** hasta que se subsanen los 3 bloqueantes (especialmente la Paradoja de `flow_start_window` y el vacío de `event_id`). Son defectos de especificación, no de código; arreglarlos en el ADR hoy cuesta 10 minutos. Descubrirlos el viernes al ejecutar el predicado `EQUIV(Camino0, FlujoA+B)` costará días de depuración.

Una vez corregidos esos tres puntos, el diseño es sólido y listo para el `commit` del Eslabón 0.

FDO

GLM