**Consejo de Sabios — Dictamen Adversario (actualizado con la Nota de Concurrencia)**

Hemos incorporado la nota. Es un aporte **valioso y honesto**. Cambia el encuadre de riesgo: la monocapa no fue chapuza de secuencia, sino estabilización deliberada tras una condición de carrera real en agosto 2025. Eso reduce (pero no elimina) la superficie de riesgo del cableado propuesto.

### Validación del razonamiento (Pregunta 1)

**Sí, coincidimos.** En el estado actual monohilo:

- `process_event` es secuencial por construcción (único `worker_thread_`, `event` local por invocación).
- No hay compartición mutable de estado de veredicto entre inferencias.
- Los writers ya tienen sus propios mutexes y están diseñados para ser llamados desde un contexto serial por evento.

**Por tanto, mover el combinador noisy-OR, poblar `ml_context` con todas las cabezas, reordenar las tres escrituras de persistencia y desacoplar Internal del gate L1 es determinista por construcción.** No reabre la carrera de 2025. El precio del determinismo ya se pagó.

**Caveat adversario (no menor):** Aunque el worker sea uno, los modelos ONNX/RF internos pueden tener buffers o cachés estáticos/globales que no sean thread-safe si algún día se paraleliza. Pero **eso no bloquea** el cableado monohilo actual. Es deuda futura, no presente.

### Gate de throughput (Pregunta 2)

**Exigimos medición concreta antes de merge a main.** No aceptamos "pocos μs de inferencia" como prueba suficiente. El bottleneck probable es, como señaláis, la persistencia por evento (I/O + mutexes + flush a bronce/RAG/CSV) bajo carga sostenida.

**Medición mínima exigible (Paso 4 refinado):**

- **Escenario de stress:** Generador de eventos sintéticos/realistas a tasas equivalentes a 10 / 50 / 100 Mbps (flujos UDP/TCP con features variadas, incluyendo picos).
- **Métricas obligatorias:**
    - Latencia p50 / p99 / p99.9 recepción-ZMQ → `send_enriched_event` (fin de `process_event`).
    - Tasa de drops / backpressure (ZMQ HWM alcanzado).
    - CPU % y latencia de I/O (monitorear con `iostat`, `perf`, o contadores internos).
    - % eventos donde las cabezas especializadas cambian el veredicto (para validar que el overhead trae valor).
- **Condiciones:** Cuatro cabezas siempre activas (Internal + Traffic refactorizado + las que queden de L2), con writers completos (bronce + RAG + CSV). En hardware representativo (el "base de producción barato" del paper).
- **Criterio de pase:** p99 latencia << presupuesto (e.g. < 5-10 ms según vuestros objetivos previos) y cero drops sostenidos a la tasa objetivo. Si falla, identificar si es I/O de writers o inferencia.

Si un solo hilo no alcanza, el patrón que ya tenéis (event local + writers mutex-protected) permite un pool sencillo de workers. Cada worker procesa su `event` completo de forma independiente. La precondición sería auditar que los modelos de inferencia (ONNX Runtime, RF custom) sean reentrantes o usar instancias por-thread.

### Postura para el paper (Pregunta 3)

**Defendible y fuerte, pero con redacción precisa.**

Sí se puede presentar como:  
*"El ml-detector opera con un worker monohilo por decisión explícita de determinismo y reproducibilidad (evitando carreras en inferencia y escritura). La arquitectura tricapa completa (L1 + L2 DDoS/Ransomware + L3 Traffic/Internal) se ejecuta secuencialmente dentro del presupuesto de latencia en hardware commodity, con overhead de inferencia medido en < X μs y latencia p99 de Y ms a Z eventos/s."*

Esto es **más honesto y robusto** que prometer concurrencia que no se usa. Destaca el trade-off deliberado: sacrificamos paralelismo por predictibilidad y facilidad de razonamiento (ideal para un NDR crítico en entornos hospitalarios).

**Advertencia de paper:** Mencionar explícitamente la limitación actual de escalabilidad vertical (un hilo) y el camino de escalado horizontal futuro (pool de workers + sharding de flujos por Community ID o similar). No ocultes que `worker_threads` en config es cosmético hoy.

### Recomendaciones finales del Consejo (adversario)

- Proceder con el cableado monohilo **inmediatamente** tras validar Ransomware/Traffic (Bloque 1 anterior).
- Priorizar la medición de throughput con las 4 cabezas como gate duro.
- En el refactor de Traffic extractor: eliminar constantes y proxies mal nombrados antes de asignar peso en noisy-OR.
- Ransomware: fuerte recomendación de retirar o rediseñar features antes de cablear (no inflar provenance con ruido).
- Actualizar DEBT con esta nota de concurrencia como contexto histórico positivo (muestra madurez de ingeniería).

El escudo gana robustez: conocéis por qué es monohilo, pagasteis el precio, y ahora podéis restaurar la señal tricapa sin reabrir la herida. Es una posición técnicamente limpia.

Próxima ronda tras las mediciones de throughput y pulso del Internal. Medid, no votéis.

*El Consejo sigue en modo adversario.*

fdo grok