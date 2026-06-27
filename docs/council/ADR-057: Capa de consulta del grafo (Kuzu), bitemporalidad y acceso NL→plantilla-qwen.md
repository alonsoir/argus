Sin embargo, bajo el principio rector "medir, no votar", hemos identificado 4 puntos débiles estructurales y 1 riesgo de ejecución que requieren evidencia empírica antes de ser ratificados. A continuación, se detalla el análisis y las pruebas medibles exigidas.
1. Capa de Consulta In-Process (Sección 2.1)

Premisa del ADR: Al ser in-process, se evita el conflicto de locks de Kuzu y se mantiene la regla Falco. Se asume que la concurrencia lectura/escritura en el mismo proceso es viable. Punto Débil: Kuzu utiliza MVCC (Multi-Version Concurrency Control). Aunque permite lecturas y escrituras concurrentes, una carga alta de escritura (ej. ingestión masiva de flujos en el engine) puede causar inanición (starvation) de las consultas de lectura, o viceversa, bloqueando el hilo principal del correlation-engine. El ADR no define límites de QoS (Quality of Service). 📏 Prueba Medible Requerida (Fase 2 ampliada):
Smoke Test de Contención: Ejecutar un script C++ que simule una ingesta continua de 10,000 nodos/segundo (escritura) mientras se ejecutan concurrentemente las plantillas T1 y T2 (lectura).
Métrica de Aceptación: La latencia p95 de las consultas de lectura no debe degradarse más de un 20% respecto a su ejecución en una BD en reposo, y el hilo de escritura no debe bloquearse (>100ms) por las lecturas. Si falla, se requiere un patrón de "réplica de solo lectura" o colas de prioridad, no solo "in-process".
2. Bitemporalidad y Semántica de ingested_at (Sección 2.2)

Premisa del ADR: ingested_at se estampa en ON CREATE SET por el reloj del engine, desacoplándolo del reloj envenenado del sniffer. El histórico vive en el WAL. Punto Débil: El ADR no contempla el escenario de Replay o Backfill. Si el sistema se reinicia o se reprocesan datos del WAL (DEBT-LABEL-WAL-001), el ingested_at reflejará el tiempo del replay, no el tiempo original de conocimiento. Esto corrompe la forense "a fecha de", ya que un evento ocurrido el día 1 y reprocesado el día 5 aparecerá como "conocido" el día 5. 📏 Prueba Medible Requerida:
Test de Replay Temporal: Inyectar un lote de datos con flow_start_window = T0. Estampar ingested_at = T1. Simular un fallo y replay del WAL en T2.
Métrica de Aceptación: El sistema debe ser capaz de distinguir entre ingested_at (primera vez) y replayed_at (última vez). Si el schema actual solo permite un campo ingested_at inmutable, el ADR debe especificar que el WAL es la única fuente de verdad para el tiempo de conocimiento histórico, y que el campo en Kuzu es meramente una optimización del "estado actual". El Consejo debe ratificar esta jerarquía de fuentes.
3. Límites del Modelo NL (TinyLlama) (Sección 2.3)

Premisa del ADR: TinyLlama (1.1B parámetros) clasificará la intención y extraerá parámetros tipados sin alucinar, rechazando si la confianza es baja. Punto Débil: Los modelos de <3B parámetros tienen un rendimiento notablemente bajo en extracción estructurada de entidades (ej. extraer un community_id con formato específico o una ventana temporal compleja de una frase ambigua). Confiar ciegamente en su "umbral de confianza" interno (logprobs) suele generar falsos negativos (rechazo de consultas válidas) o falsos positivos (parámetros mal extraídos que fallan en la validación de tipo posterior). 📏 Prueba Medible Requerida (Fase 3):
Dataset de Evaluación: Crear un conjunto de 100 consultas en lenguaje natural realistas (con ambigüedades, jerga técnica y errores tipográficos).
Métrica de Aceptación: Ejecutar el pipeline TinyLlama + Validación de Tipos. Se exige un F1-Score ≥ 0.85 en la extracción correcta de parámetros. Si el F1 es < 0.85, el ADR debe incluir un fallback obligatorio: pre-procesamiento por expresiones regulares (Regex) para parámetros estrictos (IDs, fechas), usando el LLM solo para la clasificación de la plantilla (T1-T6).
4. Honestidad Arquitectónica: Consultas de Conveniencia (T5, T6)

Premisa del ADR: Se incluyen T5 y T6 (filtros tabulares) en el grafo por "conveniencia", reconociendo que el plano ORO (Parquet) lo hace mejor. Punto Débil: Esto es un anti-patrón de "God Object". Permitir consultas tabulares en un motor de grafos desperdicia CPU/RAM, infla el catálogo de mantenimiento y entrena a los usuarios a usar la herramienta incorrecta. Si ORO es mejor, la capa de consulta debe enrutar estas peticiones a ORO, no ejecutarlas en Kuzu. 📏 Prueba Medible Requerida:
Benchmark Comparativo: Ejecutar T5 y T6 sobre un dataset de 10 millones de registros en Kuzu vs. DuckDB (representando ORO).
Métrica de Aceptación: Si Kuzu es >2x más lento o consume >2x de memoria que DuckDB para estas consultas, T5 y T6 deben ser eliminados del catálogo de Kuzu. La capa NL debe traducir estas intenciones a consultas ORO, manteniendo la honestidad de diseño que el propio ADR proclama.
5. Firma del Catálogo (Fase 4)

Punto Débil: El ADR menciona firma Ed25519 del catálogo, pero no especifica cuándo se verifica. Verificar la firma criptográfica en cada consulta NL añadiría una latencia innecesaria. 📏 Aclaración Requerida: El ADR debe especificar explícitamente que la verificación de la firma Ed25519 ocurre únicamente en el arranque (startup) del correlation-engine o al recargar el catálogo, no por cada query.
🏛️ Dictamen Provisional del Consejo

El ADR-057 es aprobado condicionalmente, sujeto a la resolución de las siguientes acciones medibles antes de pasar a "Estado: Aceptado":
[CONSEJO] Ratifica el default in-process, pero exige el Smoke Test de Contención (Punto 1) para garantizar que la lectura no bloquee la escritura en el hilo principal.
[CONSEJO] Ratifica ingested_at en ON CREATE SET, con la condición explícita de que, en escenarios de replay, el WAL (DEBT-LABEL-WAL-001) prevalece como fuente de verdad del tiempo de conocimiento, y el campo de Kuzu es solo una vista del estado actual.
[CONSEJO] Exige la eliminación de T5 y T6 del catálogo de Kuzu si el benchmark (Punto 4) demuestra una penalización de rendimiento >2x frente a ORO. La honestidad arquitectónica debe prevalecer sobre la "conveniencia".
[CONSEJO] Establece un umbral de F1-Score ≥ 0.85 para la extracción de parámetros con TinyLlama. Si no se alcanza, se debe implementar el fallback de Regex para parámetros tipados antes de aprobar la Fase 3.
Próximo paso para el autor: Ejecutar las pruebas medibles indicadas, adjuntar los resultados (gráficos de latencia, métricas de F1, tiempos de ejecución) al ADR, y volver a convocar al Consejo para la firma final.

Respuesta 2

El Consejo de Sabios revisa el **ADR-057** bajo el principio rector `medir, no votar`. A continuación, se exponen los puntos débiles identificados, sustentados con referencias técnicas comprobables y métricas de validación obligatoria. Se responde explícitamente a cada marcador `[CONSEJO]`.

---

## 🔍 1. Puntos débiles identificados y argumentación medible

### 1.1 Capa in-process (§2.1)
| Afirmación del ADR | Verificación técnica | Punto débil | Métrica de validación |
|---|---|---|---|
| `Kuzu solo permite un dueño del lock de escritura; un segundo proceso lector choca con la concurrencia` | Kuzu (≥v0.6) usa **MVCC** y permite múltiples conexiones `READ_ONLY` concurrentes sobre el mismo directorio `.kuzu`. El lock exclusivo solo aplica a transacciones de escritura. La documentación oficial y el código fuente (`transaction_manager.cpp`) confirman lecturas concurrentes sin bloqueo mutuo. | El argumento de "imposibilidad física" es **prematura optimización defensiva**. Un lector externo *técnicamente* es viable si se abre en modo `READ_ONLY` y se gestiona el `flock` compartido. La decisión in-process es válida por **aislamiento de fallos**, no por limitación de Kuzu. | **Smoke Test (Fase 2):** 1) Abrir `libkuzu` en modo `READ_ONLY` desde proceso hijo mientras el engine mantiene handle `READ_WRITE`. 2) Medir: throughput de queries concurrentes (QPS), latencia p99, y si se dispara `SIGBUS`/corrupción de WAL interno. 3) Si `READ_ONLY` externo funciona, el argumento de Falco pasa de "técnico" a "político". |
| `In-process evita reabrir autenticación y mantiene invariante Falco` | Falco monitoriza `open/read` sobre `*.kuzu`. Un proceso separado requería `ptrace`/`bpf` o reglas `syscall` más granulares. | **Acoplamiento de ciclo de vida:** Un fallo de segmentación en una consulta Cypher mal construida o en `libkuzu` derrumba el `correlation-engine`. No hay aislamiento de memoria ni límites de CPU/RAM por consulta. | **Métrica obligatoria:** Medir `max_rss` y `cpu_throttle` del proceso engine bajo carga de consultas simultáneas (≥50 threads). Definir `thread_pool` dedicado con `cgroups`/`setrlimit`. Si el engine cae por OOM en test de carga, el modelo in-process requiere mitigación de aislamiento (sandboxing ligero o `fork` efímero para lecturas pesadas). |

### 1.2 Bitemporalidad (§2.2)
| Afirmación del ADR | Verificación técnica | Punto débil | Métrica de validación |
|---|---|---|---|
| `ingested_at en ON CREATE SET captura transaction-time inmutable` | `ON CREATE SET` solo se ejecuta la primera vez que el nodo se materializa. Refleja correctamente **"cuándo se supo por primera vez"**. | No captura **tiempo de conocimiento de actualizaciones** (ej. reclasificación de alerta, parche de score). La bitemporalidad completa requiere tracking de estados, no solo de nacimiento. El ADR delega esto al WAL, pero la reconstrucción histórica no tiene métricas de viabilidad aún. | **Métrica obligatoria:** Medir latencia de reconstrucción WAL → grafo histórico para ventanas de 1h, 24h, 7d. Medir inflación de storage (`WAL size / graph size ratio`). Si `>30%` overhead o reconstrucción `>500ms` por query, se requiere índice secundario en WAL o particionamiento temporal. |
| `ingested_at UINT64 con reloj NTP-disciplinado desacopla de CLOCK-INJECTION` | `UINT64` sin especificación de época es ambiguo. NTP puede sufrir *step jumps* (≤1000ms en Linux por defecto) que violan monotonicidad. | `ingested_at` no es estrictamente monótono si hay correcciones NTP negativas. Para forense reproducible, se requiere `CLOCK_MONOTONIC` + offset UTC, o garantía de `time_steering` en el engine. | **Métrica obligatoria:** Inyectar `ntpdate -b -0.5s` y `+0.5s` durante carga. Verificar tasa de `ingested_at[t] < ingested_at[t-1]`. Si `>0%`, aplicar `std::chrono::steady_clock` + sincronización periódica a UTC, o usar `libkuzu`'s `transaction_id` como proxy monótono. |
| `Kuzu no tiene bitemporalidad nativa; se modela a mano` | Correcto. Kuzu sigue el modelo Cypher/property-graph, sin soporte para `SYSTEM_TIME PERIOD` (SQL:2011) ni `valid_from/valid_to` automáticos. | Ninguno técnico. Es una decisión arquitectónica alineada con la realidad del motor. | Validar que el catálogo de plantillas (T4) filtra eficientemente por `ingested_at`. Medir costo de indexar `UINT64` vs filtrado lineal. Si `>5ms` por 10k nodos, declarar índice explícito en `CREATE NODE TABLE`. |

### 1.3 Acceso NL→plantilla (§2.3)
| Afirmación del ADR | Verificación técnica | Punto débil | Métrica de validación |
|---|---|---|---|
| `Validación trivial por construcción; parámetros se validan por TIPO` | TinyLlama (1.1B) genera texto libre. La extracción de `$community_id`, `$n`, ventanas temporales **no es determinista**. Un LLM pequeño puede producir `1:src=10.0.0.1/dst=192.168.1.1` (válido) o `community_42` (inválido). | La validación post-LLM requiere **esquema rígido** (JSON Schema, regex, coerción de tipos). Decir "trivial" subestima la tasa de fallo en dominio operativo. | **Métrica obligatoria:** Construir corpus de 100 consultas operativas reales. Medir: 1) Tasa de mapeo correcto a plantilla (precision@1), 2) Tasa de validación de parámetros post-LLM, 3) Tasa de rechazo por ambigüedad. Si validación `<95%`, implementar parser híbrido (LLM → JSON estructurado → validador determinista). |
| `NL solo selecciona plantilla; nunca genera Cypher` | Arquitectura segura por diseño. Elimina superficie de inyección. | Ninguno técnico. Es la única vía aceptable para sistemas de alta integridad. | Medir latencia del pipeline NL→clasificación→extracción→validación. Si `>800ms` p95, considerar modelo más ligero (ej. `distilbert-base` fine-tuneado) o caching de intents frecuentes. |

---

## 📜 2. Respuesta explícita a marcadores `[CONSEJO]`

| `[CONSEJO]` | Decisión del Consejo (basada en evidencia) | Condición de cierre |
|---|---|---|
| **Default in-process** | ✅ **Aceptado**, pero con mitigación de aislamiento: queries de lectura pesada (`T1` con `$n≥3`) deben ejecutarse en `thread_pool` con `setrlimit(RLIMIT_AS)` y timeout estricto. Falco se mantiene sin excepciones. | Cerrar con métrica de `max_rss` bajo carga y 0 caídas en smoke de 10k queries. |
| **Semántica `ingested_at` (`ON CREATE SET`)** | ✅ **Aceptado**. Es la única forma coherente de capturar "primer conocimiento". Se añade requisito: época `Unix UTC`, monotonicidad garantizada por `steady_clock + offset`, y rechazo de queries si `ingested_at` no es estrictamente creciente en lote. | Cerrar con test de inyección NTP y validación de monotonía. |
| **Catálogo T1–T6** | ✅ **Aceptado con poda explícita**: `T5` y `T6` se marcan como `BRIDGE_ORO` en metadatos. No se optimizan para grafo; se delegan a ORO si el catálogo crece. `T4` es la plantilla canónica que justifica la inversión bitemporal. | Cerrar con benchmark comparativo: T4 en grafo vs T4 en ORO (latencia, precisión, coste). |
| **Firma del catálogo (Ed25519)** | ✅ **Aceptado en Fase 4**. No bloquea el diseño actual. Se requiere rotación de claves y verificación en `cypher_builder.hpp` antes de compilar plantillas en memoria. | Cerrar con métrica de verificación `<50μs` por plantilla y gestión de claves en `vault`/`KMS` existente. |
| **Umbral de confianza NL + ambigüedad** | ✅ **Umbral 0.85**. Comportamiento ante ambigüedad: **devolver top-2 con scores y pedir selección explícita al operador**. Rechazo duro solo si `max_confidence < 0.60`. | Cerrar con evaluación de corpus: medir F1@1, tasa de fallback, y tiempo de resolución operador. |

---

## 📊 3. Protocolo de Medición Obligatorio (antes de promoción a `🟢 APROBADO`)

| Eje | Test | Métrica objetivo | Herramienta |
|---|---|---|---|
| **Concurrencia Kuzu** | 1 proceso `RW` + 5 procesos `RO` ejecutando T1/T2/T3 concurrentemente | `0` errores de lock/corrupción, p99 latencia `<200ms` | `libkuzu` C++ API + `hyperfine` |
| **Bitemporal `ingested_at`** | Ingesta de 10k flujos con NTP step ±1s, query T4 por ventana | Monotonía `100%`, overhead storage `<15%`, reconstrucción WAL `<300ms` | `chronyc`, `bpftrace`, `wal_parser` (DEBT-LABEL-WAL-001) |
| **NL→Plantilla** | Corpus 100 queries operativas, 3 niveles de ambigüedad | Precision@1 `≥92%`, validación parámetros `≥96%`, latencia `<500ms` p95 | `evaluate_nl_classifier.py`, `jsonschema` validador |
| **Aislamiento in-process** | 50 threads concurrentes ejecutando T1 con `$n=4` | `max_rss` estable, 0 `SIGSEGV`, CPU throttle `<10%` | `valgrind massif`, `systemd.slice`, `perf` |

---

## ✅ Veredicto Final

El **ADR-057** es **técnicamente sólido, bien acotado y alineado con principios de seguridad y auditabilidad**. No contiene decisiones erróneas, pero sí **suposiciones no medidas** que deben cerrarse con evidencia antes de la implementación.

El Consejo recomienda:
1. **Promover a `🟢 APROBADO` condicionado** a la ejecución del protocolo de medición anterior.
2. **Mantener `in-process` como default**, pero con aislamiento de recursos explícito.
3. **Validar `ingested_at` con monotonicidad garantizada** y marcar `T5/T6` como `BRIDGE_ORO`.
4. **Cerrar `NL→plantilla` con corpus evaluado y validador determinista**, no solo "confianza por construcción".

El principio `medir, no votar` se ha aplicado. Los puntos débiles son **cuantificables y mitigables**. No se requieren cambios de dirección, solo evidencia de cierre.

**Firmado:** Consejo de Sabios  
`📅 Fecha de revisión: [ACTUAL]`  
`🔍 Estado: CONDICIONALMENTE APROBADO → pendiente de smoke tests (§4)`

FDO 

QWEN