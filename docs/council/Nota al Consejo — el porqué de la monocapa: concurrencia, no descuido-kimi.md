# Deliberación del Consejo — Nota aclaratoria: el monohilo como precondición

## Posición general: el hecho técnico aportado **cambia la pregunta** de la primera ronda. La validamos, pero con una advertencia de método que no podemos ignorar.

---

## 1. Validación del razonamiento: ¿monohilo implica determinismo seguro?

**Veredicto: Sí, con una condición de contorno.**

El razonamiento es correcto: si `process_event` opera sobre un `event` local (`zmq_handler.cpp:322`), si el worker es un único hilo (`zmq_handler.cpp:217`), y si los writers tienen `mutex_` propio, entonces:

- No hay carrera de datos sobre el estado del evento durante el procesamiento.
- No hay carrera de datos sobre el veredicto entre cabezas, porque las cabezas se ejecutan secuencialmente dentro del mismo hilo.
- La única concurrencia posible es en los writers (múltiples workers potenciales escribiendo al mismo disco), pero con un solo worker esa concurrencia no existe.

**La condición de contorno:** el hecho de que el `event` sea local no garantiza determinismo si los **modelos de inferencia** (los objetos `level1_model_`, `ddos_model_`, etc.) tienen estado mutable interno. Un modelo XGBoost o Random Forest en C++ puede tener buffers de predicción reutilizados, scalers con estado, o memoria de trabajo que no sea thread-safe. Si en agosto 2025 la carrera ocurrió **dentro** del runtime de inferencia (ej. dos hilos llamando `predict` en el mismo objeto modelo), entonces el monohilo la evita. Si la carrera ocurrió **entre** el modelo y otro componente compartido (ej. un `feature_extractor` singleton), el monohilo también la evita.

**Pero:** si el modelo tiene un `predict` que modifica estado interno (algunos runtimes de ML lo hacen para cachear features), un solo hilo sigue siendo seguro porque las llamadas son secuenciales. La única forma de que el monohilo no sea suficiente es que el modelo tenga un `predict` que dependa de estado global (ej. una variable estática en `feature_extractor.cpp`). Eso sería un bug independiente del hilo, y debería detectarse en la medición de stress.

**Conclusión:** validamos que el monohilo resuelve el problema de concurrencia de agosto 2025 **para el cableado de fase 2**. No reabre la herida.

---

## 2. Gate de throughput: ¿qué medición exigir?

**Veredicto: La propuesta del informe (stress a 10/50/100 Mbps, p99, drops) es necesaria pero insuficiente. Añadimos tres métricas obligatorias.**

La propuesta base es correcta, pero omite algo crítico: **la persistencia por evento es el cuello de botella probable**, no la inferencia. Los modelos suman pocos μs; un `write_record` a CSV/bronce puede costar milésimas de segundo si el disco está bajo presión.

**Métricas obligatorias para el gate:**

| Métrica | Qué mide | Umbral propuesto | Por qué |
|---------|----------|------------------|---------|
| **Latencia p99** recepción ZMQ → emisión ZMQ | Tiempo de procesamiento completo por evento | < 10 ms (presupuesto del sistema) | El paper cita "gate <2μs" para inferencia pura; el sistema entero debe ser <10 ms para no perder paquetes en burst |
| **Tasa de drop** bajo backpressure | Eventos descartados por cola llena | 0% a 10 Mbps, <0.1% a 50 Mbps, <1% a 100 Mbps | En un NDR real, drop = ceguera temporal |
| **Latencia p99 de persistencia** (bronce + RAG + CSV) | Tiempo bajo `mutex_` de cada writer | < 5 ms por writer | Si un writer tarda >5 ms, el worker se bloquea y la cola ZMQ crece |
| **Throughput sostenido** (pps, no solo Mbps) | Paquetes por segundo procesados | ≥ 9,000 pps a 10 Mbps (referencia ADR-029) | El pcap CTU-13 Neris da ~9,000 pps a 10 Mbps; el sistema debe sostenerlo |
| **Uso de CPU** del worker | ¿Un core al 100%? | < 80% a throughput objetivo | Si un core al 100% no alcanza, el monohilo es insostenible |

**Condición de paso:** todas las métricas verdes en **tres corridas consecutivas** de EMECAS (no una sola), con el sniffer reemplazado por el stress test (Paso 4 del plan). Si alguna métrica falla en cualquiera de las tres corridas, el gate no pasa.

**Nota sobre VirtualBox:** las métricas de 10/50/100 Mbps en VM virtio son **límites superiores virtuales**, no representativos de hardware real. El paper debe distinguir: "En VM de desarrollo (VirtualBox virtio), el monohilo sostiene X pps con latencia p99 Y ms. En hardware de producción (especificar), la proyección es Z pps." No afirmar que 100 Mbps en VM = 100 Mbps en hospital.

---

## 3. Postura para el paper: ¿es defendible el monohilo con tricapa?

**Veredicto: Sí, pero con una redacción específica que evite dos trampas.**

### Trampa 1: "Monohilo por decisión de determinismo"
Eso suena a que el equipo **eligió** monohilo como arquitectura óptima. La verdad es más honesta: **"El determinismo se priorizó sobre el paralelismo; el sistema opera secuencialmente por evento, con la tricapa completa ejecutándose en un único worker. La concurrencia fue eliminada en agosto 2025 como estabilización ante una condición de carrera, y no se ha reintroducido porque el throughput de un hilo satisface el presupuesto medido."**

Esto es una posición **más fuerte** porque:
- No oculta la historia (la estabilización de agosto 2025).
- No promete una arquitectura que no se ejecuta (no dice "decidimos monohilo", dice "estabilizamos a monohilo y verificamos que el presupuesto se cumple").
- Deja la puerta abierta a multihilo futuro como **mejora medida**, no como deuda.

### Trampa 2: "Tricapa completa en un solo hilo"
Esto puede leerse como "las cuatro cabezas son fiables". No lo son. La postura correcta es:

> **"La arquitectura tricapa está completamente cableada en el worker secuencial: el veredicto final combina (noisy-OR) las salidas de las cuatro cabezas especializadas. De las cuatro, dos operan con fiabilidad medida > 0 (Internal, DDoS) y dos operan con peso 0 documentado (Ransomware, Traffic) por razones de extractor, no de arquitectura. El sistema es tricapa en estructura y monocapa en peso efectivo hasta que el reentrenamiento eleve las cabezas restantes."**

Esto es **honesto y defendible** ante cualquier revisor:
- La arquitectura está ahí (cableada).
- Los pesos están medidos (no votados).
- Las limitaciones están documentadas (no ocultas).
- El determinismo está garantizado por construcción (monohilo).

### Redacción propuesta para el paper (§Nuevo):

> **"Determinism through sequential execution."** The `ml-detector` processes each event in a single worker thread (`worker_thread_`, §Código). The trilayer architecture (fast path, L1, four specialized heads) executes sequentially per event, with the final verdict computed by a noisy-OR combinator over all head outputs. This sequential design was stabilized in August 2025 after a race condition in concurrent inference; it has not been reverted because measured throughput (§Benchmarks) satisfies the latency budget. The four heads are structurally present; two (Internal, DDoS) carry measured weight > 0, while two (Ransomware, Traffic) carry weight 0 with documented extractor limitations (§Deuda). The architecture is trilayer in wiring and monolayer in effective weight until retraining elevates the remaining heads.

---

## Resumen de la deliberación de esta ronda

| Pregunta | Respuesta del Consejo |
|----------|----------------------|
| ¿Monohilo = determinista para fase 2? | **Sí**, validado. La condición de contorno es estado mutable interno de los modelos, verificable en stress. |
| ¿Qué gate de throughput? | **Cinco métricas**: p99 total, tasa de drop, p99 persistencia, throughput pps, uso CPU. Tres corridas EMECAS consecutivas. |
| ¿Defendible en el paper? | **Sí**, con redacción honesta: "estabilizado a monohilo, tricapa cableada, pesos medidos, dos cabezas activas, dos en peso 0 documentado." |

---

## Advertencia final (modo adversario)

El hecho de que el `config.threading.worker_threads` sea **cosmético** (`main.cpp:238` lo loguea pero no lo usa) es un **bug de configuración**, no una feature. Si el JSON promete 2 workers y el binario ejecuta 1, eso es una **divergencia config→código** que debe documentarse como deuda técnica. No lo oculten en el paper como "decisión arquitectónica"; es una **limitación heredada de la estabilización**. Nombradlo:

> `DEBT-CONFIG-WORKER-THREADS-COSMETIC-001`: `worker_threads` en JSON no instancia workers; el valor es informativo, no operativo. Resuelto en fase 2 si se reintroduce concurrencia medida.

El escudo que conoce sus sombras no solo las conoce; las nombra.

*Deliberación del Consejo de Sabios — Kimi (Moonshot AI), ronda 2*

fdo

kimi