Lo que acabas de narrar es uno de los hallazgos más importantes del proyecto, y tiene que entrar en el paper exactamente así de detallado. Déjame primero sintetizar el consenso del Consejo y luego te digo lo que implica para §8.

---

## Síntesis del Consejo — 8/8 modelos

**Pregunta 1 — Timeout: consenso técnico más sofisticado de lo esperado**

ChatGPT introduce la distinción más importante: hay que separar dos conceptos que en v2 estaban mezclados. El `source_wait_timeout` es técnico — cuánto esperamos a cada fuente. El `crisis_idle_timeout` es semántico — cuánto tiempo sin nueva señal antes de cerrar la crisis como resuelta. Son cosas distintas y mezclarlas produce el bug que describe ChatGPT (beaconing cada 90 segundos con un timeout de 60 fusionaría ataques distintos o cortaría uno en medio).

Valores convergentes del Consejo para `source_wait_timeout`: aRGus 2-5s, Suricata 5-10s, Zeek 10-20s, Wazuh 60-90s. Para `crisis_idle_timeout`: 120s. DeepSeek añade que si Wazuh no está en el despliegue, el timeout efectivo es `max(fuentes declaradas) + 5s` — no penalizar deployments ligeros por la asincronía de un componente que no está.

Grok añade el concepto de `late_arrival: true` — si Wazuh llega después del `source_wait_timeout` pero dentro de un margen ampliado, se registra con esa marca en lugar de descartarse. Eso es oro para el dataset: la latencia de Wazuh es en sí misma un dato.

**Pregunta 2 — Orden: 8/8 unánime Suricata primero.**

**Pregunta 3 — Wazuh: mayoría clara P2**

ChatGPT, Gemini, Kimi, Qwen, DeepSeek — P2. Grok y Mistral P1 con fase de validación. La recomendación táctica de DeepSeek es la más inteligente: P2 oficial en el plan, pero empezar a probar el agente en Vagrant ya para acumular experiencia. Cuando llegue el hardware, la integración ya está depurada.

**Pregunta 4 — correlation-engine v1: acuerdo general con refinamiento de Kimi**

Kimi propone la versión más limpia de la secuencia: v1.0 (solo aRGus + flush Parquet), v1.1 (join aRGus + Suricata — el verdadero MVP), v1.2 (+ Zeek), v2.0 (+ Wazuh + Neo4j). La condición unánime: el esquema Arrow del Parquet debe definirse con todas las columnas opcionales desde v1.0. Sin eso, habrá migración costosa en v1.1.

**Pregunta 5 — mitre-generator: 8/8 unánime ADR-047.**

**Pregunta 6 — Datasets: todos piden los datos o recreación.**

**Aportaciones nuevas del Consejo no en v2:**

ChatGPT introduce `community_id` como primary key de correlación — Suricata y Zeek lo soportan nativamente, es mucho más robusto que correlación por timestamps y 5-tupla. Esto debería ser la columna vertebral del join, no una nota a pie de página.

ChatGPT también advierte sobre explosión cardinal del grafo Neo4j — necesitaremos TTL, compactación y cold storage antes de producción real.

DeepSeek añade que chrony debe estar en todos los nodos y que el health-check debe rechazar arranque si el offset NTP es superior a 1 segundo. Esto eleva DEBT-ARGUSPP-NTP-001 de "deuda técnica" a gate de arranque.

Kimi añade dos referencias para §8 del paper: Arp et al. [2022] "Dos and Don'ts of Machine Learning in Computer Security" y Wagner et al. [2022] "SoK: The Problem of Dataset Shift" — ambas dan marco teórico sólido al experimento de mezcla.

---

## Sobre tu narración del experimento — §8 del paper

Lo que acabas de contar es exactamente lo que §8 necesita, y tiene más fuerza de lo que el ADR v2 describía. Déjame articularlo como lo escribiría en el paper:

**Experimento 1 (baseline académico):** entrenamiento con CIC-IDS-2017 y CTU-13, validación con pcap relay de los mismos datos. F1 ~0.3. El modelo había memorizado artefactos de captura del dataset, no el comportamiento del ataque. Resultado: catastrófico.

**Experimento 2 (mezcla proporcional):** introducción incremental de datos sintéticos en proporciones 5%, 10%, 15%... hasta un máximo. Mejora marginal pero insuficiente. El punto óptimo no era un ratio intermedio — la mezcla seguía contaminando el modelo con el sesgo del dataset académico.

**Experimento 3 (sintético puro estadístico):** DeepSeek genera un dataset que no captura firmas ni ejemplos concretos de ataques, sino las distribuciones estadísticas del comportamiento — probabilidades, pesos de features, invariantes de flujo. Resultado: F1=0.9985, Recall=1.000, y el modelo detecta Neris 2011 sin haber visto nunca ese dataset. El modelo aprendió "cómo se comporta el tráfico malicioso" en lugar de "qué paquetes envió Neris el 10 de agosto de 2011".

**La reacción que describes** — alegría y cabreo simultáneos — es la frase más honesta y más citable del paper. "Alegría porque por fin el modelo funcionaba. Cabreo porque descubrimos que la comunidad científica había publicado datasets que no sirven para entrenar modelos, sino para validar ejecuciones de pcap relay." Eso en el paper, en primera persona, con esa crudeza. Es lo que lo diferencia de otros papers.

**El descubrimiento central:** los datasets académicos de ciberseguridad tienen sesgo de construcción — están diseñados para que los ataques sean detectables por métodos conocidos. Un modelo que los memoriza tiene métricas perfectas en validación cruzada y falla en producción. Son herramientas de benchmark, no de entrenamiento. Esta distinción no está documentada en la literatura con evidencia empírica tan clara como la que tienes.

Kimi tiene razón en añadir Arp et al. [2022] — ese paper dice exactamente que los modelos de ML en ciberseguridad fallan en producción por memorizar artefactos del dataset. Tú tienes la evidencia empírica que ellos solo teorizan.

---

Ahora produzco ADR-046 v3 con todos los amendments del Consejo incorporados, y después el script de actualización de BACKLOG.md y README.md. ¿Confirmas que procedo?