Estimados miembros del Consejo de Sabios,

El borrador de la **ADR-051** es extraordinariamente maduro. Tras el amargo aprendizaje de las discrepancias del DAY 171/172, asentar la soberanía del **data-plane** sobre las declaraciones del control-plane no es solo una buena práctica de ingeniería; en infraestructura hospitalaria, es un imperativo ético. La falsa sensación de seguridad es, en efecto, nuestro peor enemigo.

A continuación, aporto mi perspectiva y deliberación sobre el diseño técnico y las tres preguntas abiertas planteadas:

---

## Análisis del Core de la ADR-051

### El acierto del enfoque *Per-Sensor* vs. *Global*

La decisión de computar el `orphan_rate` por cada sensor es la única que sobrevive al fuego de la operación real. En un entorno crítico, saber que "la correlación global ha bajado un 14%" genera parálisis por análisis. Saber que `suricata-core-01` tiene un `orphan_rate` del 99% mientras los demás están a < 1% automatiza la mitigación y el guiado del operador en segundos.

### El factor del Wall-Clock como salvavidas temporal

El hallazgo del DAY 172 respecto a los timestamps internos (el abismo de ~116 segundos entre el inicio de Zeek y el fin de flujo por timeout de Suricata) invalida cualquier intento de correlación temporal analizando metadatos nativos en ventanas cortas.
Anclar la distinción huérfano/pendiente al **wall-clock de llegada al correlation-engine (`time.monotonic`)** es la decisión correcta. Protege al health-check de falsos positivos masivos provocados simplemente por la naturaleza arquitectónica de la expiración de flujos de cada sensor.

---

## Respuestas y Votos a las Preguntas Abiertas

### 1. Flujo-diana de referencia: ¿Inyección sintética o escucha pasiva?

* **Voto:** **Inyección sintética activa (Recomendación del borrador ratificada).**
* **Argumentación:** Esperar pasivamente a que circule un flujo exacto introduce un determinismo temporal inaceptable en el arranque del pipeline (un boot que puede tardar 2 segundos o 20 minutos según el tráfico de la red). Dado que el entorno hospitalario exige predictibilidad, el gate debe poseer la capacidad de inyectar de forma segura y controlada el paquete sintético del dataset Neris-diana para evaluar la respuesta del data-plane de inmediato.

### 2. Re-ejecución periódica del gate: ¿Solo arranque o cíclico?

* **Voto:** **Solo en arranque. No se debe re-ejecutar el gate de forma periódica.**
* **Argumentación:** Re-ejecutar el gate de inyección de tráfico sintético en runtime añade ruido artificial innecesario al flujo de datos productivo y penaliza el rendimiento. El `orphan_rate` continuo (gracias a los contadores per-sensor) *ya es* el centinela que detectará si un sensor sufre un drift de seed tras una recarga de configuración en caliente (`SIGHUP`). El gate periódico es redundante; el cinturón y los tirantes ya los llevamos puestos gracias al monitoreo continuo del data-plane real.

### 3. Política de degradación en runtime: ¿Fail-closed total o aislamiento dinámico?

* **Voto:** **Degradación a $N-1$ sensores con anotación explícita de degradación de confianza.**
* **Argumentación:** Si bien en el arranque el *fail-closed* es obligatorio (no se levanta un sistema roto), en runtime la filosofía debe pivotar hacia la resiliencia operativa del hospital. Si el sensor $N$ drifta y lo tiramos todo abajo, dejamos al hospital a ciegas.
  Si aplicamos aislamiento dinámico:

1. El motor de correlación **aísla temporalmente** las alertas/flujos provenientes del sensor degradado para evitar que contaminen el grafo con ruido.
2. Continúa correlacionando con las $N-1$ fuentes sanas.
3. El sistema **anota en el grafo de Neo4j de forma explícita** la pérdida de paridad de dicha fuente y reduce el score de confianza global de los incidentes correlacionados durante esa ventana de tiempo.

---

## Enmiendas Menores y Refinamiento de Dependencias

* **Sobre la dependencia "B" (DEBT-CORRELATION-TIMEOUT-CALIB-001):** Sugiero que la calibración de los `source_wait_timeout` no sea un valor estático a fuego en el código tras el análisis de B, sino una matriz dinámica indexada por el tipo de protocolo/duración estimado (e.g., flujos de larga duración vs. ráfagas UDP).
* **Consensuar prioridades:** Al estar el `orphan_rate` de aRGus bloqueado por `DEBT-ARGUSPP-COUNTER-DUMP-001`, propongo que la fase 1 de la implementación de la ADR-051 despliegue el Gate de Arranque de forma inmediata y deje el Health-Check continuo en estado "Degradado/Pasivo" (midiendo solo Suricata y Zeek) hasta que el volcado de contadores de aRGus esté listo.

El borrador está listo para pasar a **APROBADO** una vez se consoliden los votos sobre estos tres puntos. ¿Coincide el resto de los miembros con este enfoque de degradación dinámica para el runtime?

FDO
GEMINI