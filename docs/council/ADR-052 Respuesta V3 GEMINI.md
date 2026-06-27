## Análisis de Viabilidad y Fidelidad de la V3

La versión 3 de este ADR representa un salto cualitativo crítico: abandona la concepción del grafo como un mero "tablón de anuncios de alertas en tiempo real" y lo sitúa correctamente como lo que debe ser en un proyecto de investigación con plazos FEDER rígidos: **el reactor físico que sintetiza el corpus de entrenamiento.**

El arbitraje y las modificaciones introducidas cierran de golpe las brechas que hacían el sistema propenso a fallos catastróficos de diseño en fases avanzadas. A continuación, presento la validación técnica detallada, las respuestas a los interrogantes planteados y los ajustes de ingeniería requeridos.

---

## 1. Respuestas a las Preguntas del Consejo (Segunda Ronda)

### 1.1 Dirimir P2: ¿Existe discrepancia de VALOR legítima a tasa sin pérdida?

**Respuesta:** **NO.** Por diseño y por física de red, bajo una tasa baja sin pérdidas (escenario del Replay #1), **la discrepancia de VALOR es un mito técnico.** * El hash de `community_id` opera exclusivamente sobre la capa 3 (IPs) y la capa 4 (Puertos + Protocolo).

* Si los tres sensores (aRGus, Suricata, Zeek) capturan el flujo íntegro, el orden de llegada de los paquetes, las heurísticas de reensamblado de segmentos TCP o el estado interno del motor de inspección **afectan a qué eventos semánticos se emiten, pero jamás alteran el valor de la 5-tupla original.**

**Conclusión:** El "1% de margen" propuesto por el ala blanda del Consejo es una racionalización de ruidos de integración mal catalogados. **El criterio para el Replay #1 debe ser CERO ESTRICTO en discrepancias de VALOR.** Cualquier desviación es, por definición, un bug de extracción en el parser o un vector de evasión activo.

Se ratifica la **Síntesis de Clasificación Obligatoria** antes del estado VERDE:

1. Discrepancia de **Valor**: Tolerancia cero.
2. Discrepancia de **Presencia** (un sensor no emite): En el Replay #1 debe ser cero debido a la tasa controlada. Si aparece, se cruza con el contador de drop del prerequisito (§1.2).

### 1.2 Decidir el prerrequisito del Drop (P2 / §3.1.4): ¿Bloqueante o Diferible?

**Respuesta:** **BLOQUEANTE, pero de bajo coste (Implementación Inmediata).**
No se puede evaluar la validez del Replay #1 si el entorno de ejecución es ciego a los drops del ring-buffer o de la interfaz virtual. Si un sensor no ve un flujo por pérdida en la tarjeta de red, clasificaríamos el evento erróneamente como un "bug de no-emisión" o una anomalía del motor, envenenando las métricas de calidad de la fase de construcción.

Dado que las herramientas ya exponen estos datos de manera nativa:

* **aRGus:** Contadores en `ring_consumer` y fallos en `libpcap`.
* **Suricata:** `stats.log`
* **Zeek:** `capture_loss.log` / `stats.log`

**Acción:** Es un **prerrequisito bloqueante para mañana**. No requiere escribir código dentro de los sensores; basta con que el script verificador en Python parsee y extraiga estas métricas al finalizar el replay, anexándolas como metadatos del reporte.

### 1.3 Confirmar la separación Valor/Timing

**Respuesta:** **CONFIRMADA.** El Replay #1 debe ejecutarse con la **distribución temporal natural del Neris**.
Inyectar ráfagas artificiales de inactividad introduce artefactos de paridad (fuerza flushes artificiales que alteran la línea temporal del sensor). El Replay #1 busca validar la **integridad del valor**. Los experimentos de estrés de timing, calibración de deltas (`ts_emision_ns`) y fatiga del `source_wait_timeout` pertenecen al Replay #2 y se ejecutarán de forma aislada una vez se congele el core del esquema.

---

## 2. Evaluación de las Decisiones de Arbitraje de Alonso (N5 y N11)

### 2.1 §3.1.1 — Congelación de `H` con Libsodium (`BLAKE2b`)

Esta decisión es impecable desde la perspectiva de la mantenibilidad del software de alta eficiencia. Evita que la infraestructura sufra la clásica fragmentación de librerías donde el backend en Python usa una variante de implementación de SHA3 y el motor en C++20 usa otra que difiere en el padding o el endianness.

Al anclar la función a la interfaz de `crypto_generichash` de la versión de Libsodium compartida:

* El rendimiento de `BLAKE2b` en arquitecturas x86_64/AArch64 es masivo, superando con creces a SHA3 sin necesidad de aceleración de hardware criptográfico específico.
* Se garantiza que el cálculo de `flow_uid` sea determinista y reproducible al 100% de manera offline leyendo directamente desde un pcap con `scapy` o `pypcap` en herramientas de análisis forense.

### 2.2 §3.11 — Inclusión del Vector A Ampliado (Anomalías TCP/TLS)

La anulación del criterio de la mayoría del Consejo es arquitectónicamente correcta. Limitar el Vector A (MITM) a nivel de enlace de datos (L2 - ARP/NDP) ignoraba que en entornos modernos basados en SDN, nubes híbridas y arquitecturas Zero Trust, los ataques de denegación de servicio local o redirección se ejecutan mediante secuestros de sesión L4 o envenenamientos DNS/BGP.

Al incorporar los ganchos para `:HostAnomaly` (como los resets TCP inesperados o los desfases en los números de secuencia del kernel reportados por el agente de host):

* Se dota al grafo de la capacidad de detectar ataques de inyección de tráfico ciegos al `community_id`.
* Se fuerza al pipeline a correlacionar datos de telemetría interna del sistema operativo con eventos de cable en la misma ventana temporal, elevando drásticamente el valor de la muestra en el corpus.

---

## 3. Modelo de Datos de Identidad de Nodo-Flujo

```
flow_uid = base64( H( utf8(node_id) ‖ 0x00 ‖ utf8(community_id) ‖ 0x00 ‖ uint64_be(flow_start_window) [‖ 0x00 ‖ uint32_be(seq_in_window)] ) )

```

### 3.1 Corrección del Conflicto de Ciclo de Vida de Desarrollo (N1)

La disociación entre la identidad del sensor para el corpus (`node_id`) y el par de claves criptográficas efímeras (`Ed25519`) resuelve el problema de la volatilidad del entorno Vagrant. Si el identificador se derivaba del keypair generado en el arranque de la máquina de test, la destrucción del entorno borraba el histórico de enlaces, haciendo inviable la persistencia del dataset en el laboratorio. El uso de un `declared_sensor_id` estático mapeado en el orquestador garantiza la reproducibilidad de los grafos entre ejecuciones.

---

## 4. El Microscopio de Calidad del Corpus: Matriz de Integridad

Para asegurar el cumplimiento de la **Misión Primaria**, cada elemento del esquema se valida bajo tres ejes de estrés de datos:

| Componente | Riesgo en Producción / Ataque | Mitigación Arquitectónica en V3 | Impacto Directo en el Corpus |
| --- | --- | --- | --- |
| **`node_id`** | Inyección de flujos fantasmas por un atacante que compromete la red. | Exige validación en el inventario de endpoints y firma del evento mediante la clave de autenticación viva. | Evita el envenenamiento de datos (*data poisoning*) aislando sensores no autorizados. |
| **`flow_start_window`** | Ataques de denegación de servicio por agotamiento de memoria mediante flujos infinitos. | Uso de ventanas de tiempo deterministas basadas en el *event time* original + aristas tipadas `[:CONTINUES]`. | Preserva la consistencia del grafo sin romper la identidad de conexiones legítimas de larga duración (C2, SSH). |
| **`seq_in_window`** | Reúso masivo e instantáneo de puertos UDP para causar colisiones de hash en el grafo. | Contador monótono inyectado y calculado por el sensor en origen, viajando dentro del Protobuf. | Garantiza la unicidad matemática de cada ráfaga o transacción UDP en ráfagas de alta velocidad. |
| **`provenance_Suspected` vs `Ground_Truth**` | Falsos positivos del motor que sesgan el reentrenamiento del modelo. | Separación estricta de campos. La verdad de escenario proviene del manifiesto MITRE externo; el estado de sospecha es heurístico. | Permite calcular de manera honesta y sin circularidad las métricas de precisión y exhaustividad del pipeline ML. |

---

## 5. Dictamen del Consejo de Sabios

El diseño presentado en la versión 3 del **ADR-052** es **TÉCNICAMENTE SÓLIDO, COHERENTE Y VIABLE PARA RATIFICACIÓN.** Cumple con el doble propósito de actuar como un motor de correlación en tiempo real de alto rendimiento y, de manera prioritaria, como un generador de datasets con integridad garantizada para los contratos de reentrenamiento de modelos de inteligencia artificial (ADR-040).

> **Aprobación de la Mesa:** Se recomienda proceder a la congelación del esquema de la base de datos Neo4j para levantar la deuda técnica `DEBT-NEO4J-FLOW-KEY-001`. El Replay #1 de mañana debe ejecutarse aplicando el criterio de **Cero Estricto en Discrepancias de Valor** y recolectando los contadores de drop por sensor como prerrequisito bloqueante. El pipeline está listo para el despliegue de las pruebas de paridad.
> 
> GEMINI