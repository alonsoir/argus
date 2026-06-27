
1. Analizar la compatibilidad de `community_id` como clave primaria única con los eventos de Wazuh, considerando la naturaleza de los eventos de host y la ausencia de 5-tupla en la mayoría de ellos.
2. Evaluar la propuesta de un modelo de dos claves (`community_id` para flujo y `host_key` para host) y su impacto en la arquitectura del correlation-engine y en la máquina de estados de crisis.
3. Examinar la semántica de `source_wait_timeout` y su interacción con las fuentes de eventos, especialmente Wazuh, para evitar esperas innecesarias y latencias excesivas.
4. Definir la cota dura de crisis abiertas y la política de evicción para manejar la backpressure bajo ataque, asegurando la degradación sin bloqueo.
5. Establecer la disciplina de reloj y la tolerancia de tiempo para la correlación de eventos, considerando los diferentes timestamps generados por las fuentes y su impacto en la precisión de la correlación.
6. Decidir si Wazuh debe ingerir `eve.json` de Suricata o si cada motor debe entrar al engine por su propio adapter, para evitar duplicación y eco de eventos.
7. Definir el contrato de ingesta por adapter, incluyendo la persistencia de offset y la deduplicación, para garantizar la resiliencia y la consistencia en la ingesta de eventos.
8. Establecer el alcance de protocolo para `community_id`, considerando la inclusión de TCP/UDP/SCTP y la exclusión de ICMP para FEDER, y su impacto en la correlación de eventos.
# Integración Multi-Motor en aRGus NDR: Análisis Técnico y Recomendaciones para la Correlación de Eventos de Red y Host

> - El uso de `community_id` como clave primaria única es insuficiente para correlacionar eventos de host (Wazuh) y de red (Suricata, Zeek, aRGus) debido a la naturaleza asimétrica de los eventos.
> - Un modelo de dos claves (`community_id` + `host_key`) es recomendable para integrar fuentes heterogéneas, alineado con prácticas de la industria en SIEMs como Elastic y Wazuh.
> - La semántica de `source_wait_timeout` debe ser dinámica y ajustarse al tipo de evento y fuente para evitar latencias innecesarias y mejorar la eficiencia.
> - Estrategias de backpressure, como cotas duras y políticas de evicción (LRU, FIFO), son esenciales para manejar alta carga y evitar bloqueos en la correlación de eventos.
> - La sincronización de relojes mediante NTP y algoritmos como Berkeley o Lamport es crítica para garantizar la consistencia temporal en la correlación de eventos distribuidos.

---

## Introducción

El proyecto aRGus NDR busca integrar cuatro motores de seguridad —aRGus, Suricata, Zeek y Wazuh— para correlacionar eventos de red y host, utilizando `community_id` como identificador clave. Sin embargo, la naturaleza distinta de los eventos generados por Wazuh (HIDS/SIEM basado en host) frente a los sensores de red plantea desafíos técnicos significativos. Este reporte profundiza en las inquietudes técnicas planteadas, analiza la validez de las premisas iniciales y propone soluciones basadas en estándares, buenas prácticas y ejemplos concretos de la industria, con el objetivo de fundamentar las decisiones de diseño para una integración robusta y escalable.

---

## Análisis por Inquietudes Técnicas

### INQ-1: `community_id` como PK única vs. modelo de dos claves

**Contexto:** La premisa inicial propone usar `community_id` como clave primaria única para correlacionar eventos. Sin embargo, Wazuh genera eventos de host que no siempre tienen una 5-tupla clara, lo que dificulta la correlación con eventos de red basados en flujos.

**Hallazgos:**
- En sistemas SIEM como Elastic y Wazuh, es común utilizar modelos de claves múltiples para integrar fuentes heterogéneas (red + host). Por ejemplo, Wazuh puede correlacionar eventos de host mediante un `host_key` (IP, hostname, agent_id) en combinación con identificadores de flujo .
- El uso de `community_id` como única PK puede generar problemas de diseño y deuda técnica en sistemas con fuentes asimétricas, ya que no captura la naturaleza de los eventos de host que no tienen 5-tupla .
- No se encontraron estándares específicos para la correlación de eventos de flujo y host, pero la práctica común es usar claves compuestas que reflejen tanto la identidad del flujo como del host .

**Recomendaciones:**
- Adoptar un modelo de dos claves (`community_id` + `host_key`) para permitir la correlación robusta entre eventos de red y host.
- Validar y actualizar las premisas P1-P5, especialmente el cálculo de `community_id` y la sincronización de relojes, para asegurar alineación con buenas prácticas .

---

### INQ-2: Unión host↔flujo no simétrica

**Contexto:** La correlación entre eventos de host y flujo no es simétrica debido a la diferencia en la naturaleza de los datos (eventos de red basados en flujos vs. eventos de host basados en IPs/agent_id).

**Hallazgos:**
- En soluciones SIEM, la correlación entre eventos de red y host se maneja mediante inventarios de IPs internas y reglas que evitan uniones espurias. Por ejemplo, Wazuh y Elastic correlacionan eventos de host con flujos de red mediante inventarios y políticas de normalización .
- Se utilizan esquemas de datos que relacionan IPs con agent_id y otros identificadores para evitar ambigüedades en la correlación .
- La integración de Wazuh con Suricata mediante agentes que leen `eve.json` permite unificar alertas y correlacionar eventos de host con flujos de red .

**Recomendaciones:**
- Implementar un inventario de IPs internas y reglas de correlación para evitar uniones espurias entre eventos de host y flujo.
- Utilizar esquemas de datos que relacionen IPs, hostnames y agent_id para robustecer la correlación .

---

### INQ-3: Semántica de `source_wait_timeout`

**Contexto:** El tiempo de espera para el cierre de crisis debe ser dinámico y evitar latencias innecesarias, especialmente cuando no todas las fuentes reportan eventos.

**Hallazgos:**
- Sistemas de correlación como Suricata+EveBox y Zeek+Kibana implementan tiempos de espera ajustables según el tipo de evento y fuente, para optimizar la eficiencia .
- Se recomienda computar dinámicamente las fuentes "esperadas" para un evento dado, para evitar que `source_wait_timeout` imponga esperas innecesarias .
- La implementación de tiempos de espera adaptativos mejora la respuesta del sistema y reduce la latencia en la correlación .

**Recomendaciones:**
- Implementar una lógica dinámica para calcular `source_wait_timeout` basada en el tipo de evento y las fuentes involucradas.
- Utilizar algoritmos de ajuste de timeout que consideren la carga del sistema y la criticidad del evento .

---

### INQ-4: Cardinalidad de crisis abiertas y backpressure

**Contexto:** Bajo alta carga (ej. ataques DDoS), el sistema debe limitar el número de crisis abiertas para evitar saturación y bloqueos.

**Hallazgos:**
- Estrategias de backpressure como cotas duras y políticas de evicción (LRU, FIFO) son comunes en sistemas distribuidos para garantizar resiliencia .
- Motores como Suricata y Zeek implementan políticas de evicción y degradación para manejar carga excesiva sin bloquear el sistema .
- La emisión de eventos parciales sin bloqueo es una práctica para mantener la disponibilidad bajo alta carga .

**Recomendaciones:**
- Establecer una cota dura de crisis abiertas y aplicar políticas de evicción (ej. LRU) para manejar backpressure.
- Implementar degradación sin bloqueo mediante la emisión de eventos parciales cuando la carga supere la capacidad de procesamiento .

---

### INQ-5: Disciplina de reloj y timestamps canónicos

**Contexto:** La sincronización de relojes es crítica para la correlación precisa de eventos en sistemas distribuidos.

**Hallazgos:**
- La sincronización de relojes en sistemas distribuidos se logra mediante algoritmos como Berkeley y Lamport, y protocolos como NTP, para garantizar una línea de tiempo consistente .
- El sesgo de reloj (clock skew) debe minimizarse para garantizar el orden correcto de eventos; lo ideal es que sea cero, pero en la práctica se toleran valores pequeños (ej. ≤ 50 ms en laboratorio) .
- La normalización de timestamps a un formato canónico (ej. UTC) y la aplicación de ajustes para compensar diferencias de tiempo entre fuentes son prácticas comunes .
- El monitoreo constante de la derivación de reloj es necesario para detectar y corregir discrepancias que puedan afectar la correlación .

**Recomendaciones:**
- Implementar sincronización de relojes mediante NTP y algoritmos de Berkeley o Lamport.
- Normalizar timestamps a UTC y aplicar ajustes para compensar diferencias entre fuentes.
- Monitorear la derivación de reloj para detectar y corregir discrepancias en tiempo real .

---

### INQ-6: Doble ingesta / eco de eventos

**Contexto:** Evitar la duplicación de eventos en sistemas que integran múltiples fuentes (ej. Wazuh + Suricata).

**Hallazgos:**
- Se utilizan claves de deduplicación como `(source_engine, native_event_id)` para evitar eventos duplicados en sistemas SIEM .
- Es preferible que cada motor ingrese al sistema de correlación por su propio adapter para evitar eco y duplicación de eventos .
- La ingesta de `eve.json` de Suricata por Wazuh puede generar duplicación y eco de eventos, lo que complica la correlación .

**Recomendaciones:**
- Utilizar claves de deduplicación para identificar y filtrar eventos duplicados.
- Preferir que cada motor ingrese al engine mediante su propio adapter en lugar de que Wazuh ingiera logs de Suricata .

---

### INQ-7: Transporte y resiliencia de adapters

**Contexto:** La ingesta de logs en tiempo real desde archivos o sockets debe ser resiliente a fallos de red y rotación de archivos.

**Hallazgos:**
- Herramientas como Filebeat y Logstash son ejemplos de adapters robustos para ingesta de logs en tiempo real .
- La persistencia de offsets y la deduplicación en sistemas como Kafka y Redis son fundamentales para garantizar la consistencia y la resiliencia .
- Se recomienda implementar lógicas de reintento con backoff exponencial para manejar fallos transitorios .
- Patrones de caché como write-through y write-behind son útiles para la persistencia de offsets y deduplicación .

**Recomendaciones:**
- Utilizar librerías y frameworks robustos para la ingesta de logs (ej. Filebeat, Logstash).
- Implementar persistencia de offsets y deduplicación mediante patrones de caché y reintentos con backoff exponencial .

---

### INQ-8: Determinismo vs. realismo en validación

**Contexto:** Validar el sistema de correlación con pruebas deterministas y realistas para garantizar reproducibilidad y cobertura.

**Hallazgos:**
- Se utilizan pcaps fijos como "golden sets" para pruebas deterministas en herramientas como tcpreplay .
- Pruebas con herramientas como nmap o atomic-red-team aportan realismo para evaluar la respuesta del sistema .
- La combinación de pruebas deterministas y realistas es clave para garantizar la robustez y la reproducibilidad en entornos CI/CD .

**Recomendaciones:**
- Utilizar pcaps fijos para pruebas deterministas y herramientas como nmap para pruebas realistas.
- Implementar un pipeline de CI/CD que combine ambas aproximaciones para validar el sistema .

---

### INQ-9: Alcance de protocolo de `community_id`

**Contexto:** Evaluar el soporte de `community_id` para protocolos como ICMP y su impacto en la correlación.

**Hallazgos:**
- `community_id` soporta ICMP en implementaciones como Suricata y Zeek, mapeando type/code a pseudo-puertos .
- La exclusión de ICMP para FEDER puede simplificar la correlación inicial, pero puede limitar la detección de eventos importantes .
- Decisiones de diseño en proyectos similares documentan la exclusión de ICMP para simplificar la correlación .

**Recomendaciones:**
- Incluir TCP/UDP/SCTP en `community_id` y diferir ICMP para FEDER, evaluando su impacto en la correlación.
- Documentar la decisión de diseño y evaluar alternativas para incluir ICMP en el futuro .

---

## Respuestas a las Preguntas al Consejo

### Q1 y Q2: Modelo de claves y grafo de correlación

**Análisis:**
- Un modelo de dos claves (`community_id` + `host_key`) permite representar crisis con dos tipos de aristas (flujo y host), facilitando la correlación de eventos heterogéneos.
- Esto mejora la flexibilidad y robustez del grafo de correlación, especialmente en entornos con múltiples fuentes de datos asimétricas.
- Ejemplos de esquemas de datos en SIEMs muestran que este modelo es más adecuado para representar relaciones complejas entre eventos .

**Recomendación:**
- Adoptar el modelo de dos claves para el grafo de correlación, permitiendo representar crisis con aristas de flujo y host.

---

### Q3: Semántica de cierre de crisis

**Análisis:**
- Computar dinámicamente las fuentes "esperadas" para una crisis permite evitar tiempos de espera innecesarios.
- Implementar una lógica adaptativa para `source_wait_timeout` mejora la eficiencia y reduce la latencia en la correlación.
- Ejemplos en sistemas SIEM muestran que este enfoque optimiza la gestión de eventos y la respuesta a incidentes .

**Recomendación:**
- Implementar un mecanismo dinámico para calcular `source_wait_timeout` basado en el tipo de evento y fuentes involucradas.

---

### Q4: Ingesta de `eve.json` por Wazuh

**Análisis:**
- Que Wazuh ingiera `eve.json` de Suricata puede generar duplicación y eco de eventos, complicando la correlación.
- Es preferible que cada motor ingrese al engine por su propio adapter para evitar redundancia y garantizar la consistencia.
- Esto simplifica la deduplicación y mejora la resiliencia del sistema .

**Recomendación:**
- Evitar que Wazuh ingiera `eve.json` de Suricata; preferir que cada motor entre al engine por su propio adapter.

---

### Q5: Timestamp canónico y tolerancia de reloj

**Análisis:**
- La sincronización de relojes mediante NTP y algoritmos como Berkeley o Lamport es esencial para garantizar la consistencia temporal.
- Se recomienda una tolerancia de reloj ≤ 50 ms en entornos de laboratorio y más estricta en producción.
- El monitoreo constante de la derivación de reloj es clave para detectar y corregir discrepancias .

**Recomendación:**
- Utilizar NTP para sincronización de relojes y monitorear la derivación de reloj en tiempo real.

---

### Q6: Recursos para E2E

**Análisis:**
- Ejecutar 5 VMs simultáneas en un M2 Pro con 32 GB de RAM puede ser viable para pruebas E2E, pero puede requerir optimización.
- Alternativas como perfiles ligeros, arranque secuencial o entornos CI dedicados pueden mejorar la escalabilidad y el rendimiento.
- Es importante evaluar la carga de trabajo y los requisitos de memoria para garantizar la estabilidad .

**Recomendación:**
- Evaluar la viabilidad técnica y considerar alternativas para optimizar el uso de recursos en pruebas E2E.

---

### Q7: Cota de crisis abiertas

**Análisis:**
- Establecer cotas duras y políticas de evicción (ej. LRU) es esencial para manejar alta carga y evitar bloqueos.
- Esto permite garantizar la resiliencia del sistema y la disponibilidad bajo condiciones de ataque.
- Ejemplos en sistemas SIEM muestran que este enfoque mejora la gestión de eventos y la respuesta a incidentes .

**Recomendación:**
- Implementar cotas duras y políticas de evicción para manejar la carga de crisis abiertas.

---

### Q8: Alcance de protocolo

**Análisis:**
- Limitar `community_id` a TCP/UDP/SCTP y diferir ICMP para FEDER simplifica la correlación inicial.
- Sin embargo, ICMP es un protocolo importante para la detección de eventos de red, y su exclusión puede limitar la capacidad de detección.
- Decisiones de diseño en proyectos similares documentan la exclusión de ICMP para simplificar la correlación .

**Recomendación:**
- Incluir TCP/UDP/SCTP en `community_id` y diferir ICMP para FEDER, evaluando su impacto y documentando la decisión.

---

### Q9: Objetivo de FEDER

**Análisis:**
- Enfocar FEDER como un **pipeline vivo** de correlación prioriza la detección en tiempo real y la respuesta rápida.
- Enfocarlo como un **corpus etiquetado y reproducible** prioriza la precisión y la capacidad de análisis forense.
- La elección afecta el orden de las fases de desarrollo: un pipeline vivo requiere optimización de throughput, mientras que un corpus exige reproducibilidad y etiquetado riguroso .

**Recomendación:**
- Evaluar los objetivos de FEDER en función de las prioridades del proyecto: throughput y respuesta rápida vs. precisión y análisis forense.

---

## Orden de Resolución y Dependencias

La investigación sugiere que el orden de fases propuesto (Fase 0 a Fase 6) es técnicamente sólido, pero debe considerarse la prioridad de reproducibilidad si FEDER se enfoca como corpus. En ese caso, se recomienda ajustar las fases para garantizar la calidad y consistencia de los datos antes de escalar la producción.

---

## Conclusiones y Siguientes Pasos

La integración multi-motor en aRGus NDR requiere un modelo de correlación basado en dos claves (`community_id` + `host_key`) para manejar la heterogeneidad de eventos de red y host. La sincronización de relojes, la gestión dinámica de tiempos de espera, y la implementación de estrategias de backpressure son fundamentales para garantizar la robustez y escalabilidad del sistema. Además, se recomienda validar y actualizar las premisas técnicas iniciales para alinearse con estándares y buenas prácticas de la industria.

Como siguientes pasos, se propone:
1. Implementar un modelo de dos claves para la correlación de eventos.
2. Desarrollar un mecanismo dinámico para el cálculo de `source_wait_timeout`.
3. Establecer cotas y políticas de evicción para manejar la carga de crisis abiertas.
4. Implementar sincronización de relojes mediante NTP y monitoreo de derivación.
5. Evaluar la ingesta de eventos mediante adapters independientes para evitar duplicación.
6. Validar el alcance de protocolo para `community_id`, incluyendo TCP/UDP/SCTP y evaluando la exclusión de ICMP.
7. Definir el objetivo de FEDER (pipeline vivo vs. corpus) y ajustar las fases de desarrollo en consecuencia.

---

## Tablas Comparativas

| Aspecto                        | PK Única (`community_id`)                  | Modelo de Dos Claves (`community_id` + `host_key`)           |
|-------------------------------|--------------------------------------------|--------------------------------------------------------------|
| Capacidad de correlación       | Limitada para eventos de host sin 5-tupla | Robusta para eventos de red y host heterogéneos              |
| Complejidad de implementación  | Menor, pero menos flexible                 | Mayor, pero más flexible y escalable                         |
| Ejemplos en la industria       | Poco documentados                          | Común en SIEMs como Elastic, Wazuh                            |
| Impacto en grafo de correlación| Dificulta representación de crisis complejas| Permite representar crisis con aristas de flujo y host       |

| Estrategia de Backpressure       | Descripción                                  | Ventajas                                    | Desventajas                                |
|--------------------------------|----------------------------------------------|---------------------------------------------|--------------------------------------------|
| Cotas duras + evicción LRU     | Límite fijo de crisis abiertas, evicción LRU | Garantiza resiliencia, evita bloqueos      | Puede perder eventos importantes           |
| Emisión de eventos parciales   | Emitir eventos sin bloquear el sistema      | Mantiene disponibilidad bajo alta carga    | Eventos parciales pueden ser menos precisos|

| Opción FEDER                    | Pipeline Vivo                                | Corpus Etiquetado y Reproducible              |
|--------------------------------|----------------------------------------------|---------------------------------------------|
| Prioridad                      | Throughput y respuesta rápida                | Precisión y análisis forense                 |
| Reproducibilidad               | Baja                                        | Alta                                         |
| Escalabilidad                  | Alta                                        | Media                                       |
| Impacto en desarrollo          | Requiere optimización de rendimiento         | Requiere etiquetado y validación rigurosa  |

---

Este reporte proporciona una base técnica sólida para fundamentar las decisiones de diseño en la integración multi-motor de aRGus NDR, considerando las particularidades de Wazuh y los demás motores, y alineándose con las mejores prácticas de la industria en sistemas SIEM y de correlación de eventos de seguridad.

MISTRAL