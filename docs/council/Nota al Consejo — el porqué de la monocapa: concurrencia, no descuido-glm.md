# Dictamen del Consejo — Modo Adversario (Adenda de Concurrencia)

**Postura:** El hecho aportado cambia el contexto del defecto. La monocapa deja de ser "sloppy coding" (código descuidado) y pasa a ser "cicatriz de estabilización" (arquitectura congelada tras una crisis). El Consejo valida el razonamiento de seguridad, pero tensa las consecuencias que el informe asume sobre el rendimiento y expone un riesgo de integridad para el paper.

---

## Respuesta 1 — Validez del razonamiento: SÍ, es determinista por construcción

El Consejo coincide plenamente. La prueba es matemática, no empírica:

Si el grafo de estado de `process_event` se ejecuta sobre una variable local (`NetworkSecurityEvent event;` en el stack de L322) dentro de un único hilo de ejecución secuencial, entonces no existe interleaving posible con otra invocación de `process_event`.

La condición de carrera de agosto de 2025 requería (casi con certeza) estado mutable compartido entre los modelos de inferencia (buffers internos de ONNX/Runtime, scalers reutilizados, o estado del modelo estático). Al colapsar a un solo hilo, ese estado dejó de ser concurrente.

**Consecuencia para Fase 2:** El Defecto B (gate de L1) y el Defecto A (secuencia del veredicto) pueden reescribirse con la garantía absoluta de que reordenar líneas dentro de `process_event` no introduce data races. No necesitamos `std::atomic`, no necesitamos `std::mutex` en el combinador, no necesitamos memory barriers. El determinismo es gratis porque el архитектура ya pagó el precio de la serialización.

**Nota menor de higiene (no bloqueante):** Los `mutex_` en `correlation_writer`, `csv_event_writer` y `rag_logger` son hoy **cerrojos muertos** (*dead locks* en el sentido de que nunca esperan, no en el sentido de *deadlock*). Si solo un hilo llama a `write_record()`, el `std::lock_guard` adquiere el mutex sin contención y lo libera inmediatamente. Es sobrecarga de microsegundos inútil. No hay que quitarlos ahora (no hay ganancia real), pero documentar que son reliquias del diseño previo a agosto de 2025.

---

## Respuesta 2 — Gate de Throughput: La propuesta es necesaria pero INSUFICIENTE

El informe asume: *"El coste dominante probable no es el cómputo sino la persistencia por evento (I/O de disco bajo el mutex_)"*.

El Consejo valida la intuición, pero **rechaza el gate propuesto** tal como está formulado. Medir solo latencia p99 y tasa de drop bajo backpressure a 10/50/100 Mbps no basta porque no aísla la variable de peligro.

### El peligro real: I/O Síncrono Bloqueante en el Event Loop

Hoy, `process_event` hace esto en el hilo único:
```
recv_zmq() → inferencia (~2μs) → correlation_writer_->write_record() → rag_logger_->log_event() → csv_writer_->write_event() → send_zmq()
```

Si `write_record()` hace `std::ofstream::write()` síncrono (sin `O_DIRECT`, sin buffer asíncrono), el hilo se bloquea en la syscall `write()` del kernel. Si el disco (o el sistema de ficheros virtual de la VM) tarda 5ms en vaciar el buffer, **el event loop entero se para 5ms**. Durante esos 5ms, no se leen mensajes de ZMQ. Si el sniffer inunda el socket ZMQ a 50 Mbps, el buffer del socket ZMQ se llena. El sniffer hace drop o backpressure.

**El benchmark de inferencia (0.58 μs) se vuelve irrelevante** si la persistencia añade 5ms de cola de I/O por evento.

### Gate revisado que el Consejo exige (Paso 4 del plan):

No basta con "stress a X Mbps y ver si aguenta". Se requiere **descomposición de latencia por fase**:

1. **Medición de persistencia aislada:** Bench de `correlation_writer_->write_record()` sobre N eventos con el disco real de producción. ¿Cuál es la latencia p50, p99, p99.9 de *solo* la escritura?
2. **Medición de bloqueo del event loop:** En el stress test a 10/50/100 Mbps, instrumentar el bucle `run()` para medir el tiempo entre `recv_zmq()` return y el siguiente `recv_zmq()` call. Si ese tiempo > (inferencia + persistencia_nominal), hay contención de I/O.
3. **Medición de profundidad de cola ZMQ:** Exponer `ZMQ_RCVHWM` (High Water Mark) y contar mensajes perdidos en el socket del ml-detector. Si el ml-detector pierde mensajes del sniffer bajo carga, el sistema no "va lento" — está ciego a paquetes.

**Condición de pase del gate:** La latencia p99 del event loop completo (recv→process→send) debe ser < 10ms al 90% de la tasa de línea objetivo, **y** la tasa de drop del socket ZMQ del ml-detector debe ser exactamente 0. Si la persistencia síncrona rompe esto, el gate *no pasa*, y la fase 2 requiere mover la persistencia a un hilo dedicado (productor-consumidor con ring buffer lock-free entre el worker de inferencia y el worker de I/O) *antes* de declarar el sistema listo.

Esto no bloquea el cableado lógico (Paso 1 del plan reordenado), pero **sí bloquea la reclamación de "sostiene X Mbps"** en el paper.

---

## Respuesta 3 — Postura para el paper: SÍ, pero con una trampa que desactivar

Presentar el `ml-detector` como *monohilo por decisión de determinismo* es una posición **académicamente más fuerte** que prometer concurrencia falsa. La literatura de sistemas de red está llena de arquitecturas "run-to-completion" de un solo hilo (ej: early DPDK, algunos NIDS legacy) que justifican la elección por eliminación de locks y cache coherence costs.

**Cómo formularlo (aprobado):**
> "To guarantee strict determinism in verdict assembly and eliminate shared-state synchronization overhead during inference, the pipeline operates on a single-threaded run-to-completion event loop. We demonstrate that the computational cost of the full three-layer ensemble (X μs per flow) fits within the latency budget of a single thread at line rates up to Y Mbps."

**La trampa que hay que desactivar (GAP-ADVERSARIO-003, elevado a DEBT P0 para el paper):**

El informe dice: *"El JSON anuncia `worker_threads: 2`... se imprime, no instancia nada. La configuración promete una concurrencia que el binario no ejecuta."*

Si el paper dice "single-threaded by design" y un revisor baja al repo y ve `config.json` con `worker_threads: 2`, **la credibilidad se rompe**. El revisor asume que o bien el paper miente, o bien los autores no saben lo que su propio código hace.

**Acción obligatoria antes del paper:**
- Eliminar `worker_threads` y `ml_inference_threads` del JSON de configuración.
- O cambiarlos a `worker_threads: 1` con un comentario: `// Single-threaded by design for deterministic inference (see Section X.Y)`.
- Eliminar el `log->info(...)` de `main.cpp:238` que imprime un número que no se usa.

No se puede publicar "diseño monohilo determinista" dejando en el repo un config que dice "2 hilos". Es una contradicción trivial que invalidaría el trabajo ante cualquier revisor riguroso.

---

## Resumen de la Adenda

| Pregunta | Veredicto del Consejo |
|----------|----------------------|
| **¿Reconexión segura de la carrera?** | **SÍ.** Determinismo por construcción. Variable local + hilo único = cero interleaving. |
| **¿Gate de throughput?** | **Rechazado el propuesto, sustituido.** No basta con medir latencia global. Se exige descomposición (inferencia vs persistencia) y medición de drop en socket ZMQ. El I/O síncrono es el riesgo, no la inferencia. |
| **¿Postura para el paper?** | **SÍ, defendible y fuerte.** Pero condicionada a eliminar la mentira del `config.json` (GAP-ADVERSARIO-003). |

**Deuda nueva salida de esta adenda:**

| ID | P | Descripción |
|----|---|-------------|
| `DEBT-CONFIG-COSMETIC-THREADS-001` | **P0-paper** | `worker_threads: 2` en config y `main.cpp:238` mienten sobre la arquitectura real. Eliminar o corregir a `1` antes de publicación. |
| `DEBT-PERSISTENCE-SYNC-BLOCKING-001` | **P1** | Medir si la persistencia síncrona (bronce/RAG/CSV) bloquea el event loop bajo carga. Si sí, requiere refactor a I/O asíncrono antes de reclamar tasas de línea. |

---

*El Consejo nota con aprobación que la sombra tiene nombre y fecha: agosto de 2025. Un sistema que congela su arquitectura para sobrevivir no es un sistema roto — es un sistema que aprendió. Pero un sistema que dice haber aprendido mientras deja la configuración vieja en el cajón, ese sí está roto. Arreglad el config. Medid el I/O. Lo demás, va bien.*

fdo

glm