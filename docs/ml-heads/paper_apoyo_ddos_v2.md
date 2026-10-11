# Apoyo para reescribir el paper — cabeza DDoS v2 (DAY255-DAY294)

Uso: material de partida para la revisión de arXiv:2604.04952. Cada afirmación lleva su origen (DAYNNN y documento).
Esto NO es el texto del paper. Antes de escribir, cruzar con la respuesta del Consejo a consejo_day294.md.

## 1. Tesis propuesta

Un detector DDoS embebido en un NDR no falla por el modelo, sino por los contratos que lo rodean: entre entrenamiento y
servicio, entre la unidad de decisión y la unidad del ataque, entre cabezas que se vetan entre sí, y entre relojes. Al
hacer explícitos y medibles esos contratos, una cabeza pequeña (etapa 1 relativa por víctima + bosque de 100 árboles
solo bajo presión) detecta en vivo sin castigar al tráfico benigno concurrente, en modo sombra.

## 2. Arco, con los hallazgos medidos

| DAY | Hallazgo | Doc / memoria |
|---|---|---|
| 255 | Skew train/serve: geo servido como centinela fijo y entrenado con valores sintéticos informativos. Dos decisiones correctas por separado e incoherentes juntas. | reparación cabeza DDoS |
| 269-270 | Compuerta en cascada: la cabeza DDoS solo corría si level1 decía ATTACK. Sobre CICDDoS2019 por el pipeline: level1 13567 BENIGN / 1 ATTACK -> recall ~0. | BACKLOG DAY270 |
| 270 | La firma DDoS no vive en el flujo (1 paquete, 0 bwd), sino en el agregado por víctima. | BACKLOG DAY270 |
| 270 | Replicar un dataset de flujo en un NDR vivo exige alinear DLT, IP destino, subred, entrega L2 al hook y tasa bajo la saturación del anillo (1000 pps: ~14 % capturado; 100 pps: ~95 %). | BACKLOG DAY270 |
| 272 | Con la compuerta forzada, la cabeza vieja ya detectaba ~21 % (988/4661): el veto de level1 mataba detecciones posibles. Paralelo-fusión necesario. | BACKLOG DAY272 |
| 281 | El ml-detector recalculaba los rasgos; train y serve en espacios distintos (MinMax frente a crudo). Bosque viejo: 100 % de FP sobre una subida TCP legítima de 50 KB/s. | BACKLOG DAY281 |
| 286 | Contrato v2 de 8 rasgos calculados una vez en el sniffer, solo tráfico entrante. | ddos-contract-v2-day286.md |
| 287 | El sniffer leía la carga de los fragmentos IP como puertos: 63 % de filas basura en un bloque de CICDDoS2019. Corregido en XDP y libpcap. | paper_notes_day287.md |
| 288-291 | victim_rate_ratio depende de la historia de la víctima: régimen frío frente a caliente; EWMA con histéresis (K_in=3, K_out=1,5, τ=3600 s). | paper_notes_day288-291 |
| 292 | Batería caliente: 19 corridas, 0 pérdidas hasta 110 pps. Con familia fuera, los modelos fallan: aprenden firmas de generador. | paper_notes_day292.md |
| 293 | Modelo factorizado elegido por medida; política por víctima k-de-n simulada offline; paridad Python/C++ 127930/127930. | bloque1_day293.md |
| 293-294 | En vivo, en sombra: 1 INICIO / 1 FIN, solo el atacante, 0 del inocente; benigna presionada: 0 INICIO. | bloque2_day294.md |

## 3. Resultados citables (en vivo, DAY294)

- Latencia: primer DROP ~1,3 s tras el inicio del ataque; INICIO 2 s después (k=3 ventanas); FIN 29,3 s tras el último DROP.
- Especificidad con inocente concurrente hacia la misma víctima: 0 de sus eventos marcados; 5357 DROP, todos del atacante.
- Benigno fuera de distribución que activa la etapa 1 (dnsperf real 30 y 100 q/s, TCP 50 KB/s): 2 positivos en ~18000
  filas bajo presión (~0,01 %), absorbidos por k=3/5; 0 INICIO.
- Coste del modelo: 100 árboles, 6 rasgos de flujo, umbrales crudos inline en C++.

## 4. Método que merece sección propia

- Contrato único de rasgos: se calculan una vez (sniffer); el servicio solo lee; la paridad Python/C++ es una puerta.
- Unidad de decisión = víctima (etapa 1) + flujo (etapa 2): factorizar separa "hay presión" de "qué tipo de tráfico es".
- Régimen de datos: entrenamiento caliente; arranque del atacante fuera del entrenamiento y medido como latencia (D4).
- Política fuera del modelo: k-de-n ventanas por víctima con hold. Un paquete aislado nunca dispara.
- Despliegue en sombra antes de bloquear: el firewall registra lo que haría.
- "Medir, no votar" con un consejo multi-LLM y un árbitro humano; predicción escrita antes de cada medida.

## 5. Lecciones de ingeniería (bugs encontrados por medir, no por revisar)

- Dos bases de tiempo en event_timestamp (monotónico en flujos, epoch en otros eventos): congelaba el reloj de la sombra;
  99 % de un día de filas fuera de rango en Parquet. Abierto como PR propio.
- dry_run del firewall moría al arrancar en un kernel sin ipsets (solo visible tras rearrancar la VM).
- El client del lab no tenía Internet por diseño y perdía NTP: derivaba ~1,6 ms/s (14 s en horas). Arreglado
  sirviendo la hora desde el defender. Sin relojes comunes no se puede medir la latencia entre nodos.
- El validador de Parquet solo miraba la primera fila de cada fichero.
- make pipeline-start no falla si un componente queda caído.

## 6. Límites y amenazas a la validez (escribirlos tal cual)

- Generalización: la etapa 2 aprende firmas de nuestros generadores. Familia fuera: ~0 % (ntp) o ~99 % de FP (syn).
- Laboratorio: VirtualBox en un portátil, una víctima, <= ~110 pps sin pérdidas. Sin hardware real, sin multi-víctima.
- Pocas familias de ataque (reflexión NTP/DNS, SYN, dos bloques UDP de CICDDoS2019) y tasas bajas.
- Víctima fría: el modelo no bloquea; sin defensa automática hasta acumular historia.
- Defectos (K, m, k/n, hold) de laboratorio, no calibrados en una red real.
- Sombra: no hay medida de mitigación real ni de su daño colateral.
- La fast-alert está fuera de la decisión.

## 7. Lo que NO se debe afirmar

- Que aRGus "detecta DDoS" en general: se ha medido una cabeza, unas familias, un laboratorio.
- Tasas de detección sin decir régimen (caliente/frío), familias y tasa.
- Que el firewall bloquea: en esta versión solo registra.
- Comparaciones con otros NDR o con CICIDS: no hay experimento comparable.

## 8. Figuras y tablas sugeridas

1. Diagrama del flujo de decisión: sniffer (rasgos v2, EWMA por víctima) -> etapa 1 -> etapa 2 -> final_decision ->
   política por víctima (sombra).
2. Línea temporal del E2E: base, inicio del ataque, primer DROP, INICIO, último DROP, FIN (relojes alineados por NTP).
3. Tabla antes/después: bosque viejo frente a ddos_v2 en la subida TCP legítima y en el inocente concurrente.
4. Tabla de la corrida benigna presionada (filas bajo presión frente a positivos por tramo).
5. Tabla de "familia fuera" (límite principal), del bloque 1.
6. Cronología de bugs encontrados por medida (sección 5) como evidencia del método.

## 9. Pendiente antes de reescribir

- Respuesta del Consejo a consejo_day294.md y decisiones del árbitro.
- PR de la base de tiempo única (fix/event-timestamp-timebase): las latencias citables deben medirse después.
- Batería v3 y, si es posible, una medida en hardware real.
- Intervalos por corrida (bloque1_day293.md) para todas las cifras que se citen.
