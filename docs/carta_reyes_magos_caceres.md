# La carta de los Reyes Magos de Cáceres

**aRGus NDR — qué equipo hace falta para seguir investigando, y por qué**

Fecha: 2026-10-14 (DAY297). Autor: Alonso (desarrollador de aRGus NDR, arXiv:2604.04952).

Este documento explica qué preguntas de investigación sobre aRGus no se pueden responder con el laboratorio actual,
qué equipo las desbloquearía y qué resultado concreto entregaría cada pieza. Si la financiación llega, es una lista
de compra justificada. Si no llega nunca, queda por escrito qué haría falta para avanzar, para que otros puedan
hacerlo y para que el paper declare honestamente el alcance de lo medido.

## 1. Punto de partida: lo que ya está medido

aRGus es un NDR de código abierto en C++20 para infraestructuras críticas (el caso de referencia es un hospital):
sniffer eBPF/XDP, detección con modelos embebidos (RandomForest), agente de firewall y grafo de correlación
multi-sensor (aRGus, Suricata, Zeek, Wazuh). Todo lo siguiente se ha medido con predicción escrita antes de medir,
en un laboratorio de máquinas virtuales (VirtualBox, Vagrant) sobre un portátil:

- Primer descarte de un ataque volumétrico de reflexión NTP: entre 0,8 y 1,8 s después de empezar.
- Latencia de extremo a extremo sniffer -> firewall en reposo: media de 3 a 6 ms, partida en tramos medidos.
- Contabilidad exacta: cada paquete del ataque visto en el cable produce un evento; 0 eventos perdidos y 0
  duplicados entre sniffer y firewall en corridas de 15.262, 17.129 y 26.110 eventos (secuencia por productor).
- Robustez temporal: saltos de reloj de +-5 s en mitad de un ataque sin efecto en la lógica de detección.
- Límites encontrados (y publicados como tales): la cabeza DDoS discrimina el tipo de tráfico, no el comportamiento
  del origen (un gemelo inocente con los mismos paquetes recibe el mismo descarte, 99,2-99,6 %); y con los
  parámetros actuales deja de marcar un ataque sostenido a los 15-25 minutos (medido contra el código de producción).

Esto demuestra que la lógica funciona. No demuestra cuánto aguanta. Eso es lo que este laboratorio no puede medir.

## 2. Por qué el laboratorio actual no basta

- **XDP genérico, no nativo.** Las tarjetas de red de VirtualBox no ejecutan XDP en el controlador: el programa corre
  después de que el núcleo haya asignado memoria para cada paquete. Sirve para validar la lógica; no dice nada del
  rendimiento real de un descarte en el kernel, que es la base de la defensa rápida.
- **Tasas de juguete.** El anillo del sniffer se saturó en torno a 1.000 paquetes/s en la VM (DAY274). Un DDoS real
  contra un hospital se mide en cientos de miles o millones de paquetes/s.
- **Recursos compartidos.** CPU, memoria y disco son los del portátil; la carpeta compartida (vboxsf) añade
  latencias que no existirían en producción (medido: escribir logs ahí multiplicaba la latencia por 4-6).
- **No es continuo.** El portátil se suspende; al despertar, los relojes de las VM saltan (medido: 134 s). Una
  captura de 14 días en sombra, que es el método de calibración previsto (D22), es imposible así.
- **Sin aguas arriba.** No hay router de operador ni enlace que saturar: no se puede ensayar la defensa del ancho de
  banda (FlowSpec, blackhole RTBH), que es la única que protege el enlace frente a un ataque volumétrico.

## 3. Preguntas de investigación que necesitan equipo

Cada una: qué se pregunta, por qué importa en un hospital y qué medida la responde.

| # | Pregunta | Por qué importa | Medida |
|---|---|---|---|
| H1 | ¿Cuántos paquetes/s descarta la vía rápida en XDP nativo, por núcleo, antes de saturar? | La vía rápida tira el ataque claro en el kernel, antes de clasificación, firewall y grafo. Si no aguanta la tasa real, no protege. | Mpps por núcleo con XDP nativo frente a genérico; CPU y latencia de lo legítimo bajo ataque. |
| H2 | ¿A qué carga se satura el anillo del sniffer y qué se pierde primero? | Fija el umbral del modo degradado (D21): degradar y avisar antes de quedarse ciego, no después. | Escalera de carga: pérdida del anillo, retraso de cola y huecos de secuencia por escalón. |
| H3 | ¿Sobrevive la detección de ransomware a un DDoS real? | El DDoS se usa como cortina de humo para mover ransomware lateralmente. Es el riesgo principal. | Ransomware simulado dentro de la red durante un DDoS a tasa real: ¿se detecta, con qué retraso? |
| H4 | ¿Funciona "respuestas sin pregunta" a tasa de línea? | Descartar respuestas NTP/DNS/memcached/SSDP sin consulta previa no tiene falsos positivos por construcción y no se puede usar en nuestra contra falsificando orígenes. | Ataques de reflexión a tasa real: descartado frente a legítimo, coste del estado de consultas. |
| H5 | ¿Qué falsos positivos da la cabeza DDoS con bases calientes reales? | El lab solo mide víctimas con 10 paquetes/s de base. Un servidor real tiene miles (A6). | Tráfico legítimo de varios miles de paquetes/s por víctima, días seguidos, en sombra. |
| H6 | ¿Cómo pide aRGus ayuda aguas arriba, y en cuánto tiempo? | El descarte local protege el host y lo que hay detrás; el enlace solo se salva en el operador. | Ensayo de FlowSpec y RTBH con un router real o simulado: tiempo desde la detección hasta la regla activa. |
| H7 | ¿Cuánto pierden Suricata y Zeek a tasa real, y converge el grafo? | La correlación multi-sensor es la base del grafo y de la evidencia. | Pérdida por sensor en el puerto espejo y convergencia de identidades de flujo bajo carga. |
| H8 | ¿Cómo se calibra la cabeza DDoS con 14 días de tráfico real en sombra? | Es el método acordado (D22): umbral por víctima desde el percentil 99,9 y revisión humana. Nada cambia solo en producción. | Captura continua de 14 días, umbrales por víctima, repetición con adjudicación humana. |

## 4. Equipo

### 4.1 Configuración mínima (desbloquea H1, H2, H3, H4 y H7)

- **Tres servidores físicos**: generador de tráfico, defender (gateway con aRGus) y víctima o servicios. CPU de
  varios núcleos, memoria suficiente para el grafo y disco SSD para capturas.
- **Tarjetas de red con XDP nativo y DPDK**, a 10 o 25 GbE: familias Intel ixgbe/i40e/ice (X520, X710, E810) o
  NVIDIA/Mellanox mlx5 (ConnectX-4 y posteriores). Dos puertos en el defender (entrada y salida).
- **Switch gestionable con puerto espejo (SPAN)**, para que Suricata, Zeek y Wazuh vean el cable sin pasar por el
  defender, como en el lab actual.
- **Software abierto, ya existente**: TRex como generador de tráfico (sobre DPDK), los propios scripts de aRGus.

### 4.2 Configuración recomendable (añade H5, H6 y H8)

- **Un cuarto servidor de sensores** (Suricata, Zeek, Wazuh) con su propia tarjeta de captura.
- **Router Linux con FRR o BIRD** para ensayar FlowSpec y RTBH sin depender de un operador; idealmente, acceso a un
  entorno de pruebas de un operador real.
- **Funcionamiento continuo**: alimentación ininterrumpida (SAI) y alojamiento estable (no un portátil), para las
  capturas de días y semanas.
- **Almacenamiento** para 14 días de capturas y datasets (varios TB).

Precios por cotizar. Todo el software es abierto: el coste es solo el equipo y el alojamiento.

## 5. Qué entrega cada pieza

| Equipo | Resultado comprometido |
|---|---|
| NIC con XDP nativo + generador | H1: cifra de descarte por núcleo; H4: vía rápida "respuestas sin pregunta" validada a tasa real. |
| Defender físico | H2: escalera de carga y umbral del modo degradado medidos, no supuestos. |
| Víctima con servicios reales | H3: detección de ransomware bajo DDoS, con retraso medido; H5: falsos positivos con bases calientes. |
| Switch con espejo + servidor de sensores | H7: pérdidas por sensor y convergencia del grafo bajo carga. |
| Router FRR/BIRD | H6: tiempo desde la detección hasta la regla aguas arriba. |
| Funcionamiento continuo | H8: calibración con 14 días en sombra. |

## 6. Cómo se trabajaría

Igual que hasta ahora: predicción escrita antes de cada medida, parar si algo no da lo esperado y publicar también
lo que sale mal. El orquestador de corridas (`scripts/timebase/lab_corrida.sh`) y la contabilidad
(`scripts/timebase/a1_contabilidad.sh`) ya existen y se pueden llevar al equipo físico casi sin cambios; lo que
cambia es la escala de las cifras, no el método.

## 7. Si el equipo no llega nunca

Lo medido en el laboratorio virtual valida la lógica (detección, contabilidad, robustez temporal, límites del
modelo), no el rendimiento. El paper y el README deben decirlo así: las cifras de latencia y descarte son de un
laboratorio virtual a decenas o cientos de paquetes por segundo, y las preguntas H1-H8 quedan abiertas con el
protocolo de medida descrito aquí, para quien disponga del equipo.
