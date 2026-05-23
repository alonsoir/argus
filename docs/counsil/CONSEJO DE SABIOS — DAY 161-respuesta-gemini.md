¡Gran jornada de consolidación para el proyecto, colega! Cerrar la deuda técnica del protocolo binario (`DEBT-WIRE-PROTOCOL-TEST-001`) y blindar el test de integración E2E frente a regresiones son dos victorias estructurales brutales para la estabilidad de *Argus*.

Como miembros del consejo (y compañeros de autoría de este pipeline), aquí tienes nuestro dictamen técnico sobre las encrucijadas de hoy:

---

## Q1 — Wire Protocol Test: ¿Capa limpia o CryptoTransport completo?

**Mantén los tests desacoplados a nivel unitario, pero exige su coexistencia.**

La separación de responsabilidades (*Separation of Concerns*) es sagrada aquí. El test actual de `test_wire_protocol.cpp` debe validar **únicamente** la corrección de la serialización, el *endianness* (LE) y la descompresión LZ4. Mezclar cifrado ahí volvería el test frágil y dificultaría el diagnóstico cuando algo falle (¿ha fallado el vector de inicialización del AES o un byte corrupto del LZ4?).

> **El veredicto:** No dupliques la lógica de CryptoTransport en este test. La seguridad de que ambas piezas encajan bien debe recaer en los tests de integración superiores (o en el propio EMECAS++). Si los tests existentes de `crypto-transport` ya inyectan payloads estructurados y pasan por la capa binaria, estás cubierto.

---

## Q2 — Jenkinsfile.dev vs Jenkinsfile.prod

**El diseño actual es pragmático y totalmente correcto para la fase actual.**

No caigas en la trampa de la sobreingeniería temprana. Que `Jenkinsfile.dev` use `agent any` y asuma la cohabitación con Vagrant en tu máquina local es la forma más eficiente de mantener el bucle de *feedback* corto mientras seas el principal desarrollador en local.

¿Cuándo tendrá sentido cambiar a `agent { label 'argus-server' }`?

* **Inmediatamente cuando el hardware físico de la UEx entre en juego:** En ese momento, las pruebas sobre arquitectura real requerirán agentes Jenkins dedicados (`argus-server` o nodos específicos para RPi5/N100).
* **Concurrencia:** Cuando más miembros del equipo empiecen a pushear ramas de características de forma simultánea y tu Mac se convierta en el cuello de botella de la compilación.

---

## Q3 — DEBT-CONFIG-JINJA2-PIPELINE-001: ¿Cálculo en runtime o perfiles fijos?

**Rotundamente: Perfiles fijos determinados en tiempo de despliegue/construcción.**

Hacer que un script calcule y modifique parámetros críticos de configuración al vuelo en *runtime* basándose en la detección de hardware es un antipatrón peligroso en sistemas embebidos y de infraestructura crítica. Introduce un determinismo nulo: dos máquinas teóricamente idénticas podrían acabar con configs distintas por fluctuaciones en la detección, haciendo que la depuración en producción sea una pesadilla.

| Enfoque | Ventajas | Desventajas |
| --- | --- | --- |
| **Cálculo en Runtime** | Flexibilidad total ante hardware desconocido. | Cero predictibilidad, riesgo de fallos catastróficos en arranque, auditoría imposible. |
| **Perfiles Fijos (Jinja2)** | **Predecible, auditable, almacenable en Git (GitOps).** | Requiere definir explícitamente los perfiles de antemano. |

Los JSONs originales son sagrados. Tu pipeline Jinja2 debe compilar la configuración final aplicando el set de valores del perfil correspondiente (`edge-low`, `edge-medium`, `edge-high`, `server-feder`) antes de empaquetar el `.deb`. Si el sistema corre en una RPi5, el paquete instalado debe contener la configuración explícita para RPi5, sin magia en caliente.

---

## Q4 — EMECAS++ y el fix del delta E2E

**Inyecta tráfico sintético mínimo de manera determinista.**

Depender exclusivamente de tráfico orgánico en un entorno de integración continua (y más dentro de una VM Vagrant ejecutada en un entorno de escritorio) es la receta perfecta para tener *flaky tests* (tests intermitentes). Si tu Mac entra en reposo, o las interfaces virtuales suspenden el tráfico un instante, el delta dará 0 y romperá el pipeline sin que exista un bug real.

El `test-e2e-live` debe ser autónomo. Como parte del *setup* del propio test, dispara un script ligero (un *pcap replay* vía `tcpreplay` o un generador sintético mínimo) que garantice la inyección de, al menos, un puñado de eventos conocidos durante esa ventana de 60 segundos. Así mides que el sniffer realmente procesa las deltas, pero controlas el entorno.

---

## Q5 — Prioridad DAY 162: El siguiente hito

El consejo vota de manera unánime por la **Opción A: DEBT-ARGUSPP-SURICATA-001 (ADR-048 F2)**.

**¿Por qué?** Tras varias jornadas de fontanería interna, infraestructura, crypto y pipelines, el proyecto necesita "oxígeno funcional". Integrar la primera señal externa (Suricata) validará el pipeline completo que acabas de refactorizar bajo fuego real. Es el hito que demuestra el valor del core de Argus hacia el exterior.

*Nota de advertencia:* La opción B (NTP) debe ser obligatoriamente la siguiente para evitar que la correlación temporal de esas alertas de Suricata se vuelva loca en entornos multi-nodo.