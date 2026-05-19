# Consejo de Sabios — Respuesta a las Preguntas Abiertas del ADR-046 v2

Revisado el borrador v2. El documento ha madurado considerablemente desde la última sesión. La integración de Wazuh como cuarto plano ortogonal es correcta arquitectónicamente y la decisión de no tocar el protobuf hasta tener evidencia empírica es la única postura defendible. A continuación, el dictamen del Consejo sobre las seis preguntas abiertas.

---

## 1. Timeout de espera (60s) — Configurabilidad por tipo de disparador

**Dictamen: 60s como default global, con timeouts específicos por fuente.**

El 60s es razonable como *default* porque cubre el peor caso (Wazuh asíncrono), pero no debe ser un valor rígido. La arquitectura event-driven gana robustez cuando cada fuente declara su propio SLA de entrega. Propuesta:

| Fuente | Timeout recomendado | Justificación |
|---|---|---|
| aRGus | 2s | El flujo ya está en memoria en el edge; el CSV se genera en tiempo real. |
| Suricata | 5s | eve.json se escribe síncronamente tras el match de la regla. |
| Zeek | 10s | Los logs se escriben al cierre de la conexión; conexiones largas pueden demorar. |
| Wazuh | 60s | OSSEC protocol + manager queue + decoders. El peor caso justifica el default global. |

**Implementación sugerida:** el `CrisisWindow` debe llevar un mapa `std::unordered_map<CrisisSource, std::chrono::seconds> source_timeouts`, configurable vía JSON en el servidor. El hilo de limpieza evalúa cada ventana contra el timeout del disparador que la originó, no contra un valor único.

**Escenario crítico:** si el disparador es Wazuh (FIM) y el ataque incluye un C2 beacon, aRGus y Zeek pueden tener la señal de red *antes* de que Wazuh dispare. En ese caso, la ventana ya está abierta por Wazuh y los 60s son correctos. Si el disparador es aRGus, esperar 60s por Wazuh es razonable; si no llega, se registra como `wazuh: null` en el Parquet — el dataset sigue siendo válido, solo incompleto en ese plano.

---

## 2. Orden de integración en Vagrantfile — Suricata primero

**Dictamen: Suricata primero, Zeek segundo.**

**Argumentos:**
- **Suricata aporta ground truth inmediato.** Una vez integrado, cada alerta de ET Open etiqueta automáticamente flujos como maliciosos. Esto desbloquea el flywheel de reentrenamiento (ADR-040) sin esperar a que Zeek o Wazuh estén listos.
- **Suricata es más fácil de integrar.** Es un único proceso con un único output (`eve.json`). Zeek requiere gestionar múltiples logs (`conn.log`, `dns.log`, `ssl.log`, `files.log`) y su política de rotación.
- **Validación temprana del pipeline de correlación.** Con aRGus + Suricata ya tienes dos fuentes. Puedes prototipar el `correlation-engine` v1 (ver pregunta 4) con solo dos planos, reduciendo la complejidad del debugging.
- **Zeek depende de decisiones de política.** ¿Activamos `files.log`? ¿A qué nivel de TLS fingerprinting? Esas decisiones son más fáciles de tomar cuando ya tienes Suricata corriendo y puedes comparar cobertura.

**Contra-argumento Zeek-primero:** Zeek aporta contexto de protocolo que enriquece el grafo Neo4j. Pero el grafo no es necesario para validar la hipótesis científica central (F1 ensemble > F1 aRGus solo). El grafo es valor añadido; Suricata es prerequisito metodológico.

---

## 3. Wazuh en el edge — P2, post-validación de recursos

**Dictamen: Wazuh agent es P2, no P1.**

**Argumentos:**
- **Incertidumbre de consumo.** El documento reconoce explícitamente que el consumo del pipeline completo es *desconocido* (DEBT-ARGUSPP-RESOURCE-001). Añadir Wazuh agent (que incluye syscheckd, rootcheck, wazuh-modulesd) a un RPi5 que ya corre aRGus + Suricata + Zeek es arriesgado sin medición previa.
- **Wazuh es el plano más diferente.** aRGus, Suricata y Zeek comparten la misma interfaz de red y el mismo paradigma de captura pasiva. Wazuh introduce un canal de transporte completamente diferente (OSSEC TCP/1514) y un manager centralizado. Su integración es un proyecto de infraestructura, no solo un paquete más en el Vagrantfile.
- **Validación incremental.** Si aRGus + Suricata + Zeek ya no caben en el RPi5, sabes que necesitas redefinir el Tier 2 antes de siquiera considerar Wazuh. Si caben, entonces mides Wazuh en aislamiento y decides si va al mismo nodo o requiere un N100 dedicado.
- **El pipeline funciona sin Wazuh.** Los tres planos de red (aRGus, Suricata, Zeek) ya cubren la mayoría de las técnicas MITRE ATT&CK de red. Wazuh aporta host integrity, que es crítico para la *completitud* del grafo, pero no bloquea la validación de la hipótesis científica.

**Excepción:** si el hardware físico ya está disponible y las mediciones de DEBT-ARGUSPP-RESOURCE-001 muestran capacidad sobrante, Wazuh puede subir a P1. Pero no antes de esos datos.

---

## 4. `correlation-engine` v1 scope mínimo — Acuerdo, con matiz

**Dictamen: Acuerdo, pero v1 debe incluir *buffer temporal* para las dos fuentes de red, no solo aRGus.**

La propuesta original del ADR es conservadora: v1 solo disparador aRGus + buffer + flush a Parquet sin join completo. El Consejo acepta el espíritu (minimizar scope), pero sugiere un escalón intermedio:

**v1.0 (inmediato):** Disparador aRGus únicamente. Buffer circular local por nodo. Al dispararse, flush del propio buffer aRGus a Parquet. Sin join, sin Neo4j. Esto valida la infraestructura de ventanas temporales y el formato Parquet enriquecido.

**v1.1 (post-Suricata):** Añadir Suricata como segunda fuente. Join temporal aRGus ↔ Suricata. Esto ya permite etiquetado automático (Suricata alerta → flujo aRGus etiquetado) y es el mínimo viable para el flywheel de reentrenamiento.

**v1.2 (post-Zeek):** Añadir Zeek. Join tri-fuente.

**v2.0 (post-Wazuh):** Join cuatro fuentes + Neo4j.

**Justificación:** El join aRGus + Suricata es conceptualmente idéntico al join cuatro fuentes, pero con la mitad de la complejidad de integración. Si v1 solo hace aRGus, no estás validando el *core* del correlation-engine (el join temporal multi-fuente). v1.1 es el verdadero MVP.

---

## 5. `mitre-generator` — ADR-047 independiente

**Dictamen: ADR-047 independiente.**

**Argumentos:**
- **Complejidad suficiente.** El `mitre-generator` no es un script simple. Es un orquestador C++20 que debe: (a) parsear JSON de configuración de técnicas, (b) lanzar Atomic Red Team (o Caldera/Metasploit) de forma no-interactiva, (c) capturar timestamps con precisión de milisegundos, (d) manejar fallos parciales de técnicas, (e) producir un manifiesto JSON estandarizado, (f) sincronizar con el servidor de correlación. Eso es arquitectura, no documentación.
- **Interfaz de contrato.** El manifiesto JSON es un contrato formal entre dos componentes (`mitre-generator` y `correlation-engine`). Los contratos entre componentes son el territorio natural de los ADRs.
- **Ciclo de vida separado.** El `mitre-generator` se usa en pentesting controlado, no en producción. Tiene requisitos de seguridad diferentes (¿se instala en la misma máquina víctima? ¿en una máquina de ataque separada? ¿cómo se aísla para evitar daño colateral?). Esos son decisiones arquitectónicas propias.
- **Precedente.** ADR-045 (VaultClient) y ADR-040 (ML Plugin Retraining) son componentes aislados con ADR propio. `mitre-generator` tiene similar complejidad y aislamiento funcional.

**Contenido de ADR-047:** Alcance, herramienta candidata final (Atomic Red Team vs Caldera), modelo de aislamiento de la máquina víctima, formato del manifiesto JSON, sincronización de reloj con el servidor (prerrequisito de DEBT-ARGUSPP-NTP-001), y política de rollback si una técnica deja el sistema inestable.

---

## 6. Experimento de mezcla datasets — Recuperabilidad

**Dictamen: Los datos existen, pero requieren arqueología. El paper v24 no debe depender de su recuperación completa.**

**Análisis:**
El documento describe tres estrategias evaluadas (100% académico, mezcla, 100% sintético) con un resultado sorprendente: el extremo puro sintético fue el óptimo. Para la sección del paper, se necesita:
1. La curva F1 vs ratio académico/sintético.
2. Los hiperparámetros exactos de cada punto de la curva.
3. La descripción del generador sintético (distribuciones estadísticas de comportamiento).

**Riesgo:** si el experimento fue ejecutado en un entorno de desarrollo efímero (Vagrant VM destruida, logs en `/tmp`), los artefactos pueden haberse perdido. El Consejo recomienda:

- **P0:** Reconstruir la curva con una ejecución *nueva* y controlada. Usar el pipeline actual (aRGus v0.9.2-day157) con los datasets académicos disponibles (CIC-IDS-2017, CTU-13) y el generador sintético actual. Esto garantiza reproducibilidad y elimina la duda de "¿los datos antiguos eran correctos?".
- **P1:** Arqueología de logs. Buscar en el repositorio `test-zeromq-docker` (o en el paper v3, §8.13) si existen resultados intermedios guardados. Si existen, incluirlos como *validación histórica*; si no, la nueva ejecución es suficiente.

**Nota metodológica para el paper:** La sección debe enfatizar que el resultado es *counter-intuitive* (la mezcla degrada) y conectarlo con la literatura de *dataset shift* y *domain adaptation*. La referencia a Sommer & Paxson [2010] es correcta pero insuficiente; añadir también:
- **Arp et al. [2022]** — "Dos and Don'ts of Machine Learning in Computer Security" (USENIX Security) para el argumento de que los datasets académicos inducen overfitting a artefactos de captura.
- **Wagner et al. [2022]** — "SoK: The Problem of Dataset Shift in Machine-Learning-Based Network Intrusion Detection" para el marco teórico de *dataset shift*.

---

## Resumen ejecutivo del Consejo

| Pregunta | Dictamen | Prioridad |
|---|---|---|
| 1. Timeout | Default 60s, configurable por fuente (2s/5s/10s/60s) | P0 |
| 2. Orden integración | Suricata primero, Zeek segundo | P1 |
| 3. Wazuh en edge | P2, post-medición de recursos | P2 |
| 4. correlation-engine v1 | Acuerdo, pero v1.1 debe incluir join aRGus+Suricata | P1 |
| 5. mitre-generator | ADR-047 independiente | P1 |
| 6. Datasets experimento | Re-ejecutar controladamente; no depender de arqueología | P1 |

**Próximo paso recomendado:** Alonso y el equipo cierran el ADR-046 v2 con estos dictámenes, abren inmediatamente ADR-047 (`mitre-generator`), y priorizan DEBT-ARGUSPP-SURICATA-001 para desbloquear v1.1 del correlation-engine.

*Dictamen emitido. Que la calidad prevalezca.*