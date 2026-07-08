# Nota al Consejo — el porqué de la monocapa: concurrencia, no descuido

**Contexto:** en la primera ronda, el Consejo deliberó sobre la reconexión de las cuatro cabezas sin disponer de un hecho que la auditoría no incluía. Lo aportamos ahora, medido sobre `main`, porque cambia la naturaleza de la precondición del cableado. Esta nota es deliberadamente corta: una sola pregunta nueva, con el hecho técnico que la fundamenta. No adjuntamos la reconciliación de la ronda anterior para no anclar esta deliberación en lo ya dicho.

ficheros relacionados, disponibles solo por el repo.
docs/council/Informe de auditoría del veredicto del ml-detector — para el Consejo de Sabios.md
docs/council/Reconciliación del Consejo de Sabios — auditoría del ml-detector.md
---

## El hecho que faltaba

El estado monocapa **no fue un descuido de secuencia.** En agosto de 2025, el `ml-detector` sufrió una **condición de concurrencia** en la inferencia. La estabilización consistió en **colapsar el procesamiento a un solo hilo**, y nunca se revirtió. Lo que quedó documentado en memoria como "cortar de siete a cuatro modelos" era, en realidad, la serialización del pipeline a un worker único.

Esto está ahora **medido sobre el código actual**, no recordado:

1. **El `ml-detector` es monohilo.** `zmq_handler.hpp:113` declara `std::unique_ptr<std::thread> worker_thread_` — un único hilo, no un pool ni un `std::vector<std::thread>`. `zmq_handler.cpp:217` lo instancia una vez (`make_unique<std::thread>(&ZMQHandler::run, this)`). El bucle `run()` es secuencial: recibe de ZMQ, procesa, repite. El único otro hilo (`memory_monitor_thread_`) vigila memoria, no procesa eventos.

2. **`config.threading.worker_threads` es cosmético.** El JSON anuncia `worker_threads: 2` y `ml_inference_threads: 2`, pero `main.cpp:238` pasa ese número a un `log->info(...)` — se imprime, no instancia nada. La configuración promete una concurrencia que el binario no ejecuta.

3. **El `event` es estado por-invocación.** `zmq_handler.cpp:322` declara `protobuf::NetworkSecurityEvent event;` como variable local dentro de `process_event`, nueva en cada mensaje. No es miembro de clase; no se comparte entre invocaciones.

4. **Los tres writers de persistencia son thread-safe.** `correlation_writer.cpp`, `csv_event_writer.cpp` y `rag_logger.cpp` tienen cada uno su `mutex_` propio, con el patrón explícito `PRECONDITION: mutex_ held by caller` en sus funciones internas. Diseño de locking deliberado, verificado bajo TSAN en su día. Corroborado sobre fichero, no solo recordado.

---

## La consecuencia (medida, no votada)

**Reconectar las cuatro cabezas al veredicto, en el modo actual, es determinista por construcción.** No reabre la carrera de agosto de 2025, porque esa carrera vivía en el paralelismo de inferencia y **hoy no hay segundo hilo** que pueda correr contra el primero. El trabajo de fase 2 (mover el combinador, des-gatear las cabezas, reordenar la persistencia) opera enteramente sobre el `event` local de un worker secuencial. No hay estado de veredicto compartido que una cabeza pueda corromper.

Dicho de otro modo: el precio del determinismo (monohilo) **ya se pagó** en agosto de 2025 y nunca se devolvió. El cableado honesto de la tricapa no lo vuelve a cobrar.

---

## La única pregunta abierta (la honesta, no la que temíamos)

No es "¿cómo reconectamos sin reabrir la carrera?" — eso está resuelto por el monohilo. Es:

> **¿Basta un hilo para el throughput objetivo?**
> Un worker secuencial que corre, por evento: L1 + las 4 cabezas + extracción de features + persistencia (bronce/RAG/CSV) + emisión ZMQ. ¿Sostiene la tasa de línea de los experimentos (10 / 50 / 100 Mbps) dentro del presupuesto de latencia?

Datos de anclaje ya medidos: `Internal::predict` = 0.58 μs; extracción = aritmética escalar (sub-μs); las cuatro cabezas suman ~pocos μs de inferencia. El coste dominante probable no es el cómputo sino la **persistencia por evento** (I/O de disco bajo el `mutex_` de cada writer). Esa es la incógnita a medir.

**Sub-pregunta, solo si un hilo no basta:** si en el futuro se quisiera reintroducir concurrencia, ¿cuál es el patrón seguro? Observamos que la estructura actual **ya lo habilita**: `event` local por worker + writers con `mutex_` propio = un pool de N workers, cada uno con su `event`, escribiendo a writers ya serializados, no comparte estado de procesamiento. La carrera de 2025 pudo deberse a estado mutable *dentro* de los modelos de inferencia (buffers, scalers) compartido entre hilos — no al `event`. Confirmar eso sería la precondición de cualquier retorno a multihilo, pero **no bloquea el cableado monohilo de hoy.**

---

## Lo que pedimos al Consejo

1. **Validar el razonamiento:** ¿coincidís en que, siendo el `ml-detector` monohilo, la reconexión de las cabezas es determinista y no reabre la concurrencia de agosto 2025?
2. **Gate de throughput:** ¿qué medición exigís para dar por bueno que un hilo basta? (Nuestra propuesta: stress a 10/50/100 Mbps con las cuatro cabezas siempre activas, midiendo latencia p99 recepción→emisión y tasa de drop bajo backpressure. Es el Paso 4 del plan.)
3. **Postura para el paper:** si un hilo basta, ¿es defendible presentar el `ml-detector` como *monohilo por decisión de determinismo, con la tricapa completa medida dentro de presupuesto en un solo hilo*? Nuestra lectura es que sí, y que es una posición más fuerte y honesta que prometer una concurrencia que no ejecutamos.

---

*El escudo no solo conoce sus sombras: conoce por qué las proyectó. La monocapa fue una elección de seguridad concurrente, no un olvido. Reconectar la tricapa en monohilo devuelve la señal sin reabrir la herida. Y si un día se quiere multihilo, será una medición nueva, no una deuda vieja.*