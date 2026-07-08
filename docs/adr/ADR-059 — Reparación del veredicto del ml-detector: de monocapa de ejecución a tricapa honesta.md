# ADR-059 — Reparación del veredicto del `ml-detector`: de monocapa de ejecución a tricapa honesta

**Estado:** PROPUESTO · pendiente de arbitraje final de Alonso en 2 decisiones abiertas (§7) y de mediciones-gate (§6)
**Fecha:** DAY 212
**Contexto de decisión:** auditoría DAY 209–212 + dos rondas del Consejo de Sabios (9 modelos) + reconciliación
**Repositorio:** todo lo afirmado es corroborable en `main`; los números de línea son de DAY 212 (re-grepear si hay deriva)
**Reemplaza/deriva de:** `DEBT-VERDICT-MONOCAPA-001`

---

## 0. Marco (innegociable)

El fin de este ADR **no es una fecha**. Es dejar el `ml-detector` **fiable y determinista**, o saber con prueba técnica medida qué parte no puede quedar bien todavía y por qué. Dos sentidos de "arreglar", que este documento mantiene separados en todo momento:

- **(A) Cablear bien** — que la arquitectura de ejecución coincida con la que el diseño promete, y que la señal llegue correcta aguas abajo hasta el grafo. **En nuestras manos, medible ahora.**
- **(B) Cabezas fiables** — que cada clasificador discrimine de verdad sobre tráfico real. **Depende de datos** (algunos aún no generados). No se promete por decreto.

Cada afirmación se etiqueta: **[MEDIDO]** (verificado sobre fichero), **[PENDIENTE]** (requiere medición nombrada), **[ARBITRIO]** (decisión de Alonso). Nada de "por diseño" donde la verdad es "estabilizado tras una crisis".

---

## 1. Contexto — qué está roto y por qué (medido)

El veredicto del `ml-detector` (`final_classification`) es, en ejecución, **monocapa** (`max(fast_path, L1)`), pese a que el paper (arXiv:2604.04952) dibuja una tricapa. Tres defectos apilados, todos **[MEDIDO]**:

- **Defecto A (secuencia):** el veredicto se sella (`set_overall_threat_score`, L402) **antes** de que corran las 4 cabezas (L558–819).
- **Defecto B (gate L1) — causa raíz:** las cabezas solo corren si `label_l1 == 1` (L552). L1 es portero, no compañero de ensemble. Un flujo de exfiltración interna que L1 marca BENIGN nunca activa al Internal.
- **Defecto C (persistencia pre-cabezas):** bronce/RAG/CSV se escriben (L525–542) **antes** del gate y las cabezas. El grafo ingiere estado pre-inferencia. Prueba cruda: fila de bronce con `threat_category = RAW_CAPTURE` (etiqueta del sniffer, no del ml-detector).

**Origen de la monocapa — no fue descuido [MEDIDO]:** en agosto de 2025 se produjo una **condición de concurrencia** en la inferencia; la estabilización fue **colapsar el procesamiento a un solo hilo**, nunca revertido. Hoy: `worker_thread_` es un único `std::unique_ptr<std::thread>` (`zmq_handler.hpp:113`); el `event` es local a `process_event` (L322); `config.threading.worker_threads: 2` es **cosmético** (`main.cpp:238` solo lo imprime). El `ml-detector` es **estrictamente monohilo**. La monocapa es una **cicatriz de estabilización**, no chapuza.

---

## 2. Decisión — resumen ejecutivo

Reconectar la tricapa **en modo monohilo**, con honestidad de pesos: cada cabeza entra al veredicto según su **fiabilidad medida**, y el paper lo declara. El cableado (A) se hace ahora; la fiabilidad de las cabezas (B) se persigue con datos, declarando cada límite con su razón técnica. Dos cabezas entran con **peso 0 documentado** por razones de extractor, no de arquitectura.

Esto es **determinista por construcción [MEDIDO, ratificado 8/8 por el Consejo]**: un único hilo, `event` local, writers ya serializados → cero *interleaving*. Reconectar las cabezas **no reabre la carrera de agosto 2025**, porque esa carrera vivía en el paralelismo de inferencia y hoy no hay segundo hilo.

---

## 3. Decisiones ratificadas por el Consejo (cerradas)

Consenso de las 9 voces; van al plan sin más discusión.

1. **Monohilo confirmado como base del cableado.** El determinismo ya está pagado; reconectar no lo vuelve a cobrar. *(8/8)*
2. **Operador de combinación: noisy-OR** `P = 1 − ∏(1 − pᵢ)`, `pᵢ = clip(fiabilidad_i, ε, 1−ε) · score_calibrado_i`, ε≈0.01. Monótono, con corroboración, no diluye, siempre ≥ max. *(7/8 ratifican; refinamientos de clip [kimi], calibración [deepseek], tabla de saturación [glm] incorporados.)*
3. **Inyección en `provenance` (ADR-002) como N veredictos homogéneos.** Cada cabeza → `add_verdicts()`; el combinador itera `provenance->verdicts()`; `provenance->set_final_decision()` es el punto único de decisión. `authoritative_source` se conserva por compatibilidad del wire, redefinido a `ENSEMBLE_NOISY_OR`. `discrepancy_score` recalculado como desv. típica de scores activos (señal para el SOC). *(8/8)*
4. **Matar la cascada Traffic→Internal (L748).** El Internal corre siempre, desacoplado. El dominio (interno/internet) se resuelve por **lookup determinista** (RFC1918 + subredes configuradas), no por ML. *(8/8)*
5. **`fast_score` NO entra en el noisy-OR.** Es un heurístico del sniffer sin fiabilidad medible; se mantiene como circuit-breaker: `final = max(fast_score, P_noisy_or)`. *(glm GAP-002, aceptado.)*
6. **Traffic FUERA del noisy-OR aunque se repare.** Estima P(dominio interno), no P(malicioso) — variable distinta; agregarla con noisy-OR sería type-incorrecto. Aporta contexto de dominio, no un voto de amenaza. *(chatgpt, disidencia de raíz aceptada como refinamiento.)*
7. **Poblar `ml_context` desde las cabezas** (post-inferencia). Elimina `DEBT-RAG-ATTACKFAMILY-HARDCODED-001` como efecto colateral (`attack_family` derivado de la cabeza dominante, ya no hardcodeado). *(8/8)*
8. **Regenerar golden vectors como `correlation_v2`** (post-cabezas); congelar `correlation_v1` como regresión del fast-path. Contrato invariante en esquema, no en contenido. *(8/8)*

---

## 4. Destino de las cuatro cabezas (medido DAY 212)

Ninguna se maquilla. Cada una entra al veredicto según su fiabilidad medida, con pronóstico de recuperación **distinto** — el ADR no las trata igual.

| Cabeza | Salud extractor [MEDIDO] | Peso inicial | Pronóstico de recuperación |
|--------|--------------------------|:---:|----------------------------|
| **Internal (L3)** | 7/10 features reales [MEDIDO, y REFORZADO DAY 212]. En el ml-detector: `[5]` lateral, `[7]` exfil, etc. Y en el sniffer, sus features multi-flujo (`lateral_movement_score`, `service_discovery_patterns`) YA leen `unique_ips_count`/`unique_ports_count` de un agregado poblado con IPs/puertos reales — no son cascarón. | **Provisional 0.3** | **Mejor candidato, con más base de la que creíamos.** El cable no solo está verificado poblado: las features de ventana están *implementadas y vivas* leyendo el agregado real. Sube a F1-medido tras pulso MITRE (§6, Paso 3). Sigue sin ascender por vectores de juguete — la calidad discriminante sobre tráfico real es lo pendiente, no la existencia del dato. |
| **DDoS (L2)** | 6/10 honesto, features de peso reales | **F1-medido** | Degradado pero vivo. Peso = su F1 medido. |
| **Traffic (L3)** | **Doble extractor [MEDIDO — corrige el diagnóstico previo].** El del `ml-detector` (`feature_extractor.cpp`) es 5/10 constante. Pero el del **sniffer** (`ml_defender_features.cpp`) tiene varias features de ventana YA VIVAS leyendo un agregado real. | **0** de momento (y fuera del noisy-OR, §3.6) | **Más recuperable de lo que el diagnóstico inicial afirmó.** El `TimeWindowAggregator` existe, se alimenta con IPs/puertos reales (`TimeWindowEvent{src_ip,dst_ip,src_port,dst_port,protocol,bytes}`), y expone `unique_ips_count`/`unique_ports_count` sobre ventana de 30s. `dst_ip_concentration` ya está implementada y leyendo ese agregado. Solo `protocol_variety` queda en `SENTINEL` — y su arreglo es añadir `unique_protocols_count` a `WindowStats` (el dato ya está en `TimeWindowEvent.protocol`). Horas, no rediseño. Pendientes reales: (a) reparentar el agregador (§4.1), (b) transportar estas features al ml-detector (hoy el `ml-detector` usa su propio extractor 5/10, no el del sniffer). |
| **Ransomware (L2)** | 1/10 real. `entropy` = varianza de longitud de paquete ÷ 100.000, no Shannon. | **0** | **La más profunda.** La señal (entropía de *payload*) NO está en `NetworkFeatures` en ninguna granularidad (el sniffer no captura payload, quizá no debe por privacidad). Recuperación = rediseño de features de flujo (volumen a SMB/445, ratios asimétricos) o fuente nueva. No es "corregir la fórmula". |

**Hallazgo de granularidad [MEDIDO, con un matiz honesto]:** `NetworkFeatures` es un **flujo individual** (`source_ip`/`destination_ip` escalares, no `repeated`; contadores de un `flow`). Esto confirma a glm/qwen: las features de distribución (entropía IPs, concentración destino, variedad protocolo) son imposibles a esta granularidad. **Pero** el sniffer tiene un `TimeWindowAggregator` (`ml_defender_features.cpp`, ~12 sitios) y esas features están marcadas como Phase-2-pendiente, no como imposibles. La reconciliación: Traffic no es "irrecuperable" ni "reescribir el extractor del ml-detector" — es **completar la Phase 2 del sniffer y transportar las features de ventana**.

### 4.1 Acoplamiento oculto Traffic↔Ransomware [MEDIDO DAY 212] — hallazgo nuevo

Al medir si el `TimeWindowAggregator` respira, se destapó un acoplamiento que ni la auditoría ni el Consejo habían visto:

- El agregador **se alimenta** — no es un cascarón: `ransomware_feature_processor.cpp:134` llama `aggregator_->add_event(tw_event)`.
- Pero el agregador **lo posee el procesador de ransomware** (`ransomware_feature_processor.cpp:26` lo instancia).
- El extractor de features de ML (que calcula Traffic vía `get_window_stats`) **no tiene agregador propio: lo toma prestado** — `ring_consumer.cpp:817-818`: `if (!ml_extractor_.has_aggregator() && ransomware_processor_) ml_extractor_.set_aggregator(ransomware_processor_->get_aggregator())`.

**Consecuencia:** las features de ventana de Traffic solo funcionan si el **procesador de ransomware está activo**. Si ransomware se desactiva (y es la cabeza que el ADR pone a peso 0), Traffic se queda sin agregador → sus features de ventana devuelven `MISSING_FEATURE_SENTINEL`. Dos cabezas que creíamos independientes están acopladas por una fuente de datos compartida. → nota `NOTA-ACOPLAMIENTO-TRAFFIC-RANSOMWARE-001` (§8).

Además, `ring_consumer.cpp:1345` menciona un **`FlowAggregator`** pendiente (`// Phase 2: replace with real values once FlowAggregator is available`), distinto del `TimeWindowAggregator` temporal. Es posible que las features de distribución de Traffic (entropía de IPs, variedad de protocolo) necesiten ese agregador por-flujo, no el temporal de ransomware que hoy toman prestado.

> **[MEDIDO — tercera medición, CERRADA DAY 212]:** el agregado NO es un cascarón ni respira aire equivocado. `TimeWindowEvent` lleva `src_ip`, `dst_ip`, `src_port`, `dst_port`, `protocol`, `bytes`; el procesador de ransomware lo puebla con los valores reales del evento; `WindowStats` expone `unique_ips_count` y `unique_ports_count` sobre ventana de 30s. Es **exactamente** el dato que las features de distribución de dominio necesitan, y el extractor del Internal en el sniffer YA lo usa (`lateral_movement_score` = `unique_ips/event_count`; `service_discovery` = `unique_ports/event_count`). **Corrección honesta del ADR:** la afirmación previa "las features de distribución son imposibles a granularidad de flujo" era cierta para `NetworkFeatures` (un flujo) pero FALSA para el sniffer, que tiene una segunda vía (el `TimeWindowAggregator`) ya construida y poblada. El diagnóstico inicial midió el extractor roto del `ml-detector` sin ver el extractor más sano del `sniffer`. Traffic es más recuperable de lo afirmado.

**Reencuadre del acoplamiento (§4.1 sigue en pie, con marco corregido):** no es "Traffic depende de una cabeza muerta para un dato que quizá no sirve". Es "Traffic y el Internal comparten un agregado **sano y poblado** que hoy cuelga del ciclo de vida del procesador de ransomware. Hay que **reparentarlo** (darle vida propia, independiente de que ransomware esté activo), no construirlo de cero." Trabajo menor, no proyecto.

---

## 5. El problema de rendimiento — monohilo vs sniffer multihilo

Consecuencia directa del monohilo, y el riesgo real que el Consejo (glm, gemini, qwen, deepseek, kimi) marca por encima de la concurrencia:

**El desajuste de impedancia.** El sniffer es multihilo (múltiples workers publicando datagramas por ZMQ) contra un `input_socket_` PULL monohilo del ml-detector (`high_water_mark: 1000`, `mode: connect`). Más productores contra un consumidor único = la cola se llena más rápido.

**La regla que gobierna el afinado [derivada, a validar por medición]:** el paralelismo del productor está limitado por el serialismo del consumidor. **Si el ml-detector monohilo es el cuello de botella, subir los hilos del sniffer lo empeora, no lo mejora.** El número óptimo de hilos del sniffer no es "los más posibles" — es "los que el ml-detector puede drenar sin dropear". Ese número es un **resultado** del stress test, no un parámetro a priori.

**El peligro concreto [Consejo, unánime en el mecanismo]:** no es que el sistema "vaya lento". Es que una escritura síncrona a disco (bronce/RAG/CSV bajo `mutex_`) **bloquee el event loop** → ZMQ acumula → se alcanza el HWM → el sniffer eBPF **descarta tráfico**. Un NDR que dropea bajo carga no es lento: está **ciego**. El benchmark de inferencia (0.58 μs) se vuelve irrelevante si la persistencia añade milisegundos de cola de I/O por evento.

**Orden de trabajo [decisión, ratificada implícitamente]:** primero el ml-detector correcto y monohilo; luego se mide qué tasa drena; luego se afina el sniffer contra esa tasa. Afinar los hilos del sniffer contra un consumidor sin su tricapa cableada no tiene sentido — cambiaría el perfil de carga a mitad de camino. **Si ni afinando ZMQ el sniffer deja de ahogar al ml-detector, se baja también la config multihilo del sniffer** (cada componente con su hilo de trabajo, y el estudio de la verdadera config multihilo por componente queda para post-reparación). Hipótesis abierta a post-ADR: el único componente genuinamente multihilo podría ser el `firewall-agent` (I/O-bound, no compute-bound con dependencia estricta por evento).

---

## 6. Plan de trabajo accionable (TDH — cada paso con gate de medición)

Sin fechas. Cada paso tiene un gate; nada sube al veredicto sin su pulso medido. Orden por dependencia, no por preferencia.

### PRECONDICIÓN — Concurrencia (RESUELTA, §1)
Monohilo confirmado y validado 8/8. Reconectar es determinista por construcción. Si en el futuro se toca la concurrencia, es un gate de TSAN — pero **no bloquea el cableado monohilo de hoy**.

### PASO 0 — Fix del detonador latente (BLOQUEANTE, antes del des-gateo)
`DEBT-RING-CONSUMER-BACKWARD-ZERO-001` (P1, glm+qwen). Hoy `ring_consumer.cpp:908` hace `set_total_backward_bytes(0)` en fast-path; inofensivo porque el Internal no corre ahí. **El des-gateo del Paso 2 lo detonaría:** cada flujo fast-path tendría `backward=0` → la feature `[7]` del Internal (exfil: `forward/backward > 2.0`) dispararía con ratio infinito → falso positivo sistemático de exfiltración.
**Fix:** usar `flow.dbytes` real, o tratar `backward=0` como dato ausente (skip feature, no ratio infinito).
**Gate:** fix en `main` + test que verifique que `[7]` no dispara con backward ausente.

### PASO 1 — Decisiones de cabezas (medición de granularidad: HECHA, §4)
- Internal: cablear, peso provisional **0.3** declarado.
- DDoS: cablear, peso = F1 medido.
- Traffic: peso **0**, fuera del noisy-OR. Recuperación = Phase-2 sniffer (proyecto aparte).
- Ransomware: peso **0**, `status: DISABLED_UNRELIABLE`, score suprimido en provenance. Recuperación = rediseño de features (proyecto aparte).
  **Gate:** decisión documentada por cabeza con su razón técnica (hecho en §4).

### PASO 2 — Cableado (Defectos A+B+C), secuencia de PRs de glm (§7-D2)
1. **Mover** el bloque combinador (399–416) **y** las tres escrituras de persistencia (525–542) a **después** de las cabezas (post-819), antes de `send_enriched_event` (850).
2. **Sacar Internal del gate de L1** — corre siempre. (Traffic también corre, pero para dominio determinista, no para el noisy-OR.)
3. **Sustituir `max` por noisy-OR** sobre `provenance->verdicts()` poblado con las cabezas de peso > 0.
4. **Poblar `ml_context`** con la salida de las cabezas (mata DEBT-RAG-4).
5. **Internal con peso modulado por dominio** (glm): `peso = peso_base × factor_dominio` (1.0 interno / 0.3 externo), NO gateado — evita FP de exfil en tráfico de internet.
6. **Relajar gate B:** si `fast_score > malicious_threshold`, las cabezas corren aunque L1 diga BENIGN (qwen — evita FP de fast-path sin corroboración).
   **Tests del combinador (TDH):** (a) una dispara→sube; (b) dos corroboran→refuerzo; (c) fiabilidad-0 no envenena; (d) golden v2 verdes; (e) saturación dentro de tabla.
   **Gate:** tests verdes.

### PASO 3 — Pulso del Internal sobre datos etiquetados (5.2b-i)
F1 real del Internal sobre MITRE ATT&CK / Atomic Red Team en entorno controlado (lateral/exfil). No unos `curl` — señal suficiente y etiquetada para que el pipeline la recoja.
**Gate:** F1 medido existe → ajustar peso 0.3 → F1 (si F1>0.7 sube; si <0.5 baja o se reconsidera).

### PASO 4 — Gate de throughput (REDEFINIDO por el Consejo — el propuesto era insuficiente)
No basta latencia global. Se exige **descomposición por fase** + medición de ceguera:
- **Desglose de latencia por etapa** (chatgpt/glm/qwen): t_extract, t_predict×cabeza, t_proto, t_bronce, t_rag, t_csv, t_zmq. Sin esto se optimiza a ciegas.
- **Latencia p50/p99/p99.9** recepción→emisión. Umbral: p99 < 10ms (deepseek propone escalonado: 5/10/20ms a 10/50/100 Mbps).
- **Tasa de drop del socket ZMQ del ml-detector** (no solo del pipeline): profundidad de cola, HWM alcanzado, mensajes perdidos. **Umbral: 0 a tasa objetivo.** Un drop aquí = ceguera.
- **Throughput sostenido en pps** (no solo Mbps): ref ~9.000 pps a 10 Mbps (CTU-13 Neris). **10 minutos continuos**, no ráfagas (kimi — el I/O degrada con el tiempo).
- **CPU del worker** < 80% de un core.
- **Perfil de estrés hacia el peor caso** (gemini): small packets (64B) + ráfaga de ataque (DDoS/escaneo), NO flujos limpios de descargas.
- **Distinguir VM de hardware** (kimi): 100 Mbps en VirtualBox virtio es límite virtual; el paper dice "en VM X pps; proyección hardware Z", no equipara.
  **Gate:** todos los umbrales verdes en 3 corridas EMECAS consecutivas. Si la persistencia síncrona rompe el presupuesto → refactor a I/O asíncrono (ring buffer lock-free worker↔I/O) ANTES de reclamar tasa de línea en el paper.

### PASO 5 — Des-gateo del firewall (PR2, §7-D2) + pcap relay e2e en hardware propio
Relajar `attack_detected_level1()` del firewall a `ensemble || L1`. TTL real recepción→clasificación→firewall. Número de "hardware suelo" para el paper.
**Gate:** sin sobre-bloqueo masivo; TTL medido.

### PASO 6 — PR3: eliminar fallback a L1 en el firewall (tras validar N días)

### PASO 7 — Números al paper (config honesta)
Qué cabeza pesa cuánto; Ransomware/Traffic declaradas con su razón técnica. Limitación = **hueco de cobertura** ("aún no tenemos estas cabezas fiables"), NO divergencia predicha. Threading = **"estabilizado a monohilo, no elegido"** (§7-D3).

---

## 7. Decisiones abiertas — ARBITRIO de Alonso

### D1 [ARBITRIO] — Peso 0 vs. cabeza ausente
**Recomendación (síntesis glm):** peso 0 **con `status: DISABLED_UNRELIABLE` en provenance y score crudo suprimido (o −1)**. La cabeza figura (arquitectura tricapa honesta) pero NO escribe un score basura que un analista malinterprete. Reconcilia los dos bandos del Consejo (weight-0: deepseek/kimi/mistral // ausente: gemini/grok/qwen).

### D2 [ARBITRIO] — PR atómico vs. secuenciado
**Recomendación (glm, secuenciado-aditivo):** PR1 añade campo NUEVO `attack_detected_ensemble()` sin tocar el viejo → firewall sigue leyendo L1 → nada aguas abajo cambia. PR2 cambia el gate del firewall a `ensemble || L1` (cinturón y tirantes). PR3 elimina el fallback tras N días. Desarma la objeción del bando atómico (consistencia) sin su riesgo (rollback dual). Bando atómico: deepseek/gemini/mistral. Bando secuenciado: grok/kimi/glm/qwen.

### D3 [ARBITRIO — ya inclinado] — Redacción del monohilo en el paper
chatgpt y kimi frenan "monohilo por decisión de determinismo" como demasiado fuerte. **Recomendación aceptada por Alonso:** *"El determinismo se priorizó sobre el paralelismo; la concurrencia se eliminó en agosto 2025 como estabilización ante una condición de carrera, y no se ha reintroducido porque un hilo satisface el presupuesto medido."* Describe el hecho sin presuponer que fue la única decisión correcta.

---

## 8. Deudas técnicas (a `docs/BACKLOG.md`)

| ID | P | Descripción |
|----|---|-------------|
| `DEBT-VERDICT-MONOCAPA-001` | P0 | El defecto padre. Se cierra al completar este ADR. |
| `DEBT-BRONZE-WRITTEN-PRE-HEADS-001` | P1 | Persistencia pre-cabezas. Cierra en Paso 2. |
| `DEBT-RING-CONSUMER-BACKWARD-ZERO-001` | P1 | `backward_bytes=0` en fast-path. Detonador del des-gateo. Paso 0. |
| `DEBT-CONFIG-COSMETIC-THREADS-001` | **P0-paper** | `worker_threads: 2` miente sobre la arquitectura. Eliminar o `=1` con comentario, y quitar el `log->info` de `main.cpp:238`, ANTES de publicar. Un revisor que vea "2" y lea "monohilo" rompe la credibilidad del paper. |
| `DEBT-PERSISTENCE-SYNC-BLOCKING-001` | P1 | ¿La persistencia síncrona bloquea el event loop bajo carga? Medir en Paso 4; si sí, I/O asíncrono. |
| `DEBT-SNIFFER-WINDOW-FEATURES-PHASE2-001` | P2 | Alcance real [MEDIDO, menor de lo pensado]: (a) añadir `unique_protocols_count` a `WindowStats` para `protocol_variety` (el dato ya está en `TimeWindowEvent.protocol`); (b) transportar las features de ventana del sniffer al ml-detector (hoy el ml-detector usa su propio extractor 5/10, no el sano del sniffer). NO es rediseño: el agregado ya existe, se alimenta con IPs reales, y varias features ya están vivas. |
| `NOTA-ACOPLAMIENTO-TRAFFIC-RANSOMWARE-001` | P2 | El agregado (sano y poblado) lo posee el procesador de ransomware; Traffic y el Internal lo heredan condicionalmente (`ring_consumer.cpp:817`). **Reparentar**, no reconstruir: darle vida propia independiente de que ransomware esté activo. Trabajo menor. |
| `DEBT-TRAFFIC-EXTRACTOR-CONSTANTS-001` | P2-alto | Traffic 5/10 constante. Depende de la deuda anterior. |
| `DEBT-RANSOMWARE-ML-HEAD-INERT-001` | P2 | `entropy` no-Shannon; señal de payload ausente del contrato. Recuperación profunda. |
| `DEBT-MODEL-THREADSAFETY-001` | P3 | Modelos de inferencia asumidos thread-safe, sin verificar. Solo importa si se reintroduce multihilo. |
| `DEBT-ML-SCORE-FIELD-L1-ONLY-001` | P3 | `ml_detector_score` = solo L1. Semántico. |
| `DEBT-BACKPRESSURE-DOCUMENTATION-001` | P3 | Comportamiento de backpressure ZMQ sin documentar. |

**Housekeeping:** `git rm` de `proto_aligned`; corregir narrativa tricapa→realidad en el paper; `README.md` + `docs/BACKLOG.md`.

---

## 9. Consecuencias

**Positivas:** el veredicto pasa a ser lo que el paper dice; el grafo ingiere estado post-inferencia; la señal interna llega al firewall; cada cabeza pesa según su fiabilidad medida; el determinismo se preserva (monohilo); el paper gana una posición honesta e inatacable sobre threading.

**Negativas / costes:** fase 2 es cirugía del camino más caliente (mitigada por monohilo determinista + PRs aditivos secuenciados); el throughput monohilo puede resultar insuficiente y forzar I/O asíncrono o bajar los hilos del sniffer (medible en Paso 4); dos cabezas quedan a peso 0 con recuperación diferida y honestamente declarada.

**Lo que NO hace este ADR:** no promete cuatro cabezas fiables (dos necesitan datos/rediseño); no resuelve la config multihilo por componente (estudio post-reparación); no afina los hilos del sniffer (resultado del Paso 4, no de este ADR).

---

## 10. Cierre

El `ml-detector` tiene defectos, algunos serios, todos medidos y corroborables en `main`. Este ADR los repara con honestidad: cablea la tricapa en monohilo determinista, mete cada cabeza según su fiabilidad medida, y declara con razón técnica las dos que no pueden quedar bien todavía. No baja el listón: un escudo que hace lo que dice que hace, para hospitales que no pueden pagar otro.

*Via Appia Quality — medir quién clasifica, no solo cómo de bien. El escudo conoce sus sombras, incluida la fecha en que las proyectó: agosto de 2025. Repararlo no es borrar la cicatriz; es entender por qué se hizo y devolver la señal sin reabrir la herida.*