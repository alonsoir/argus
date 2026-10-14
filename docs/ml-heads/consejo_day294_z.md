# Consejo de Sabios — respuesta a DAY294

Firmamos cada bloque; quien firma, responde de la predicción. Somos: **Mireia** (sistemas, relojes, rendimiento), **Bruno** (modelo y estadística), **Yasmin** (tráfico y operadora), **Teo** (despliegue en cliente). Alonso: todo lo de abajo lleva medida, predicción y refutación; lo que no, va marcado como «registrado sin medida».

## 0. Auditoría adversaria de lo medido

**A1 — La contabilidad de paquetes no cierra (Bruno).** 60 pps × 90 s = 5400; el primer DROP llega a 1,3 s, luego lo máximo «dropeable» es 5400 − 78 ≈ 5322. Reportáis 5357: **35 de más**. Un generador a ~60,4 pps cierra la cuenta exacta (5435 − 78 = 5357); si no, hay eventos duplicados. *Medida:* pcap en .1 con hash de 5-tupla+longitud por paquete, cruzado con eventos DROP, 5 corridas. *Predicción:* si el pcap da 60,0 pps exactos, sobran ≥ 20 eventos en ≥ 4 corridas (duplicación; explicaría también parte de los 37 eventos/s). *Refutación:* cierre a ±2 en las 5 corridas.

**A2 — El «0 inocentes» está confundido con la firma (Yasmin).** Es vuestro ejemplo literal: si el tráfico de .51 no comparte tamaño/puertos con la reflexión NTP, la etapa 2 puede discriminar por firma memorizada. *Medida:* corrida **gemelo**: .61 → .1 con paquetes idénticos en tamaño, protocolo y puertos al atacante, a 10 pps, concurrente con el ataque de 60 pps; variante a 60 pps. *Predicción:* gemelo a 10 pps → ≥ 50 % de filas positivas en etapa 2 (apuesto 60-90 %); gemelo a 60 pps → ≥ 95 %. *Refutación:* ≤ 5 % de positivos en el gemelo de 10 pps, en 10 corridas → la etapa 2 discrimina algo más que la firma (identificad qué rasgo: `flow_packet_count` sería «volumen memorizado», mejor que tamaño, pero aún no comportamiento).

**A3 — FIN a 29,3 s con hold=30 (Mireia).** *Mecanismo sospechoso:* si el hold arranca en el **inicio de la ventana** que contiene al último DROP, FIN − último DROP = 30 − (offset dentro de la ventana), media 29,5. Encaja. *Medida:* log de `last_drop_ts`, `fin_ts` e inicio de la última ventana positiva, todo en monotónico, 10 corridas. *Predicción:* distribución 29,0-30,0 con media ≈ 29,5. *Refutación:* 30,0 ± 0,05 estable → el 29,3 era mezcla de relojes al medir.

**A4 — El 0,55x del reloj de la sombra no está explicado y sesga todo lo medido bajo carga (Mireia).** Si es cola, los «2 s hasta INICIO» y los hold bajo dns100 están medidos con un reloj al 55 %; si no, es generación de timestamps. *Medida:* `enq_ts`/`deq_ts` monotónicos en todos los eventos; lag = deq − enq, histograma por segundo; contador de pérdidas del anillo. *Predicción:* bajo dns100 el lag crece ~0,45 s/s hasta decenas de segundos y se drena al terminar (cola); en reposo, lag p99 < 50 ms. *Refutación:* lag < 100 ms durante todo el dns100 → no es cola: es el timestamp. *Y de paso:* histograma por `type` de los 37 eventos/s. *Predicción:* ≥ 80 % de un solo tipo, escala lineal con flujos nuevos/s (pendiente ~0,3-0,4 por flujo: 37/100 encaja). *Refutación:* plano frente a la carga → temporizador, no ciclo de vida de flujos.

**A5 — ¿El EWMA se congela de verdad durante el ataque? (Bruno).** Con τ=3600 y sin congelación, un ataque sostenido se convierte en baseline: a 70 pps sobre suelo 10, la ratio cae por debajo de 3 hacia el minuto ~15 y la sombra haría FIN en mitad del ataque. *Medida:* ataque de 20 min a 60 pps (barato) con la ratio por ventana registrada. *Predicción:* con la histéresis bien cableada, ratio ≥ 6,9 todo el rato; sin congelar, ratio < 3 hacia t ≈ 900 s. *Refutación:* ratio estable sin congelación aparente → identificad qué mantiene el baseline y documentadlo.

**A6 — Todo el lab mide víctimas en el suelo de 10 pps (Teo).** Etapa 1 es relativa: con baseline caliente de 100 pps haría falta un ataque ≥ 300 pps para cruzar K=3 y el anillo muere a ~110. Los «1,3 s» no transfieren como pps absolutos, solo como múltiplo del baseline. *Medida (lo único factible en lab):* víctima caliente a 30 pps (60+ ventanas) + ataque de 80 pps + inocente 10 → ratio 3,0 exacto. *Predicción:* INICIO en ≤ 50 % de corridas (borde). *Refutación:* 10/10 o 0/10 → el borde está más abajo/arriba de lo que el modelo dice.

## P1 — Etapa 2 por comportamiento (Bruno)

**Recomendación:** tres rasgos **por origen**, calculados al cierre de ventana desde la tabla de flujos (cero coste por paquete): `origin_delta_ratio` (pps del origen frente a su propio EWMA por (origen→víctima), suelo 1 pps, τ corto 300-600 s), `share_of_pressure` (delta del origen / suma de deltas positivos de la víctima) y `new_origins_per_victim` (orígenes sin historia previa en la ventana).

**Medida:** ya contáis por flujo; al cierre de ventana, para cada (origen→víctima) activo: pps_o, ewma_o, delta_o = pps_o − ewma_o; los tres números se adjuntan a cada fila de flujo de ese origen. Entrenar con ≥ 2 familias, validar con familia excluida (ICMP o SYN) + subida benigna nunca vista.

**Predicción:** familia excluida: ≥ 70 % de ventanas de ataque marcadas (hoy ~0-1 %), INICIO en ≤ 3 ventanas en ≥ 8/10 corridas; subida TCP benigna: ≤ 5 % de filas positivas y ≤ 2 ventanas consecutivas (absorbida por k/n 3/5).

**Refutación:** familia excluida < 40 % de ventanas (no generaliza) o la subida benigna encadena ≥ 3 ventanas (INICIO falso: castiga a quien crece). Registrado: el delta por origen no cubre distribuido spoofeado (cada origen es nuevo); por eso va junto con `new_origins` y por eso P2 necesita el eje distribuido.

## P2 — Batería v3 (Yasmin)

**Recomendación:** la v3 mide tamaños y volumen, pero faltan tres ejes y un tramo: **gemelo** (A2), **distribuido** (20 orígenes × 3 pps, sin firma NTP), **borde** (A6) y **saturación separada** del eje detección: 150 pps supera el anillo; instrumentar pérdidas y no mezclar esas métricas con detección.

**Medida:** 10 corridas por eje; filas positivas por origen, INICIO/FIN, pérdidas del anillo, lag.

**Predicción:** gemelo 10 pps: ≥ 50 % positivas con el modelo actual; distribuido sin firma: 0/10 INICIO hoy, ≥ 8/10 con `new_origins`; 150 pps: pérdidas del anillo > 0 en < 10 s; borde: INICIO ≤ 50 % de corridas.

**Refutación (la corrida que la refuta):** si el modelo actual ya da ≥ 8/10 en el distribuido sin firma, mi modelo de «memorización de firma» está mal: identificad el rasgo responsable y protegedlo antes de tocar P1.

## P3 — Valores por defecto en cliente (Teo)

**Recomendación:** defectos documentados como arranque + calibración inicial medida con aprobación humana: captura en sombra de **14 días** (dos ciclos semanales) de victim_rate_ratio por víctima; K por víctima = p99.9; aceptación en holdout de 72 h; k/n y hold se negocian con el operativo (minutos de bloqueo falso tolerables por semana), no se miden en su red.

**Medida:** p50/p95/p99/p99.9 por víctima, % de víctimas calientes, ventanas bajo presión/día; replay de los 14 días con el K propuesto, cada INICIO adjudicado por humano; coste de revisión humano ≤ 2 h por despliegue.

**Predicción:** ≥ 80 % de víctimas calientes con p99.9 ≤ 2,0 y ≤ 1 % de ventanas bajo presión al día; K=3 global resistirá sin ajuste para ≥ 70 % de las víctimas (las víctimas de backups nocturnos fallarán: para eso está el K por víctima).

**Refutación:** ≥ 25 % de víctimas con p99.9 > 2,5 → el K global 3 no vale para ese cliente (no refuta el método: exige K por víctima). Criterio de aceptación: 0 INICIO en el holdout de 72 h, ≤ 1 INICIO adjudicado en el replay.

## P4 — Mitigación real por víctima (Yasmin)

**Recomendación:** limitación **jerárquica** durante el estado de la víctima: cupo total ≈ 2× EWMA de la víctima + cupo por origen (máx(c × EWMA del origen, mínimo documentado)); la opción (b) solo como acelerador, nunca decisión única, porque la etapa 2 hoy memoriza firmas (vuestro 99 % de TCP inocente en familia-fuera lo dice). La (c) es la memorización convertida en arma; la (a) sola castiga al inocente proporcionalmente.

**Medida:** PR de mitigación real: ataque 60 pps (.50) + inocente .51 a 10 pps, familia idéntica y gemelo, 90 s; métricas: entrega del inocente (entregado/ofertado), entrega del atacante, latencia INICIO→aplicación, recuperación tras FIN; comparativa con (a) sola.

**Predicción:** jerárquica: inocente ≥ 90 %, atacante ≤ 5 %, recuperación ≤ 2 s; (a) sola: inocente ≤ 35 % (20 pps repartidos 10/70) — ese número descarta (a) como única medida.

**Refutación:** inocente < 80 % o atacante > 15 % con la jerárquica; o memoria por origen > 64 MB con 10 000 orígenes simulados → top-N + bucket por defecto, y medir si el inocente cae al bucket (predigo que no: 10 pps sostenidos rankean alto en top-1024).

## P5 — Base de tiempo única (Mireia) — va primera

**Recomendación:** opción **(b) endurecida**: MONOTÓNICO como única base para ventanas, hold, `time_to_block` y orden del grafo; epoch solo en el borde (Parquet, UI) vía ancla por nodo (arranque + re-anclaje en cada salto detectado) y evento `CLOCK_STEP`. Descartar (c): `bpf_ktime_get_tai_ns` existe en 6.1, pero TAI = realtime − tai_offset, así que **cada makestep salta TAI igual** (solo os salva de leap seconds, no de `makestep 1 -1`).

**Medida:** detector de salto (|Δreal − Δmono| > 10 ms → re-ancla + CLOCK_STEP); suite de inyección: ataque de 90 s con salto de +8 s en t=45 s (`date -s`), FIN medido por observador externo (pcap en otra VM con reloj independiente), % de filas Parquet en rango; contar saltos/día en este VBox.

**Predicción:** con (b): FIN = 30 ± 0,5 s en 20/20 corridas con salto, `time_to_block` cambia < 0,1 s, Parquet 100 %, 1 CLOCK_STEP por salto; con epoch-en-todo: FIN se desvía exactamente el salto (≈ 22 o 38 s) en ≥ 19/20. En VBox espero 0-5 saltos/día en reposo y > 10 bajo carga de CPU.

**Refutación:** una sola corrida con (b) donde FIN se desvíe > 0,5 s o el orden de eventos se rompa → hay epoch filtrado en un temporizador. Nota: el 0,55x no lo arregla P5 (es cola o timestamps: A4); lo arregla el lag de A4 y agregar DROPs por (origen, ventana).

## P6 — Disyuntor de saturación (Mireia)

**Recomendación:** **ambas**: degradar Y avisar, con umbral de **cola** (transfiere entre hardware), no de pps: degradado si lag p99 > 500 ms o pérdidas de anillo > 0 en la ventana; en degradado, etapa 1 + regla barata por víctima (ratio + orígenes nuevos) sostiene la sombra, se suspende la inferencia por flujo, DROPs agregados por (origen, ventana), evento `SATURACION`; salida con lag p99 < 100 ms durante 3 ventanas.

**Medida:** escalera 30/60/80/100/110/150 pps, 120 s por peldaño, con lag y pérdidas instrumentados; más una corrida con degradación forzada (retardo artificial en el consumidor) lanzando un ataque de 60 pps: comprobar INICIO ≤ 5 s por la regla y volumen de eventos plano.

**Predicción:** con eventos por paquete, el cruce de lag p99 > 500 ms está entre 80 y 110 pps (encaja con vuestro ~110 y con dns100); agregando por (origen, ventana) (5357 → ~90 eventos), el cruce baja de la capacidad del anillo: el techo pasa a ser el anillo, no el procesado.

**Refutación:** lag p99 < 100 ms a 110 pps con eventos por paquete → el 0,55x de dns100 no es capacidad y este umbral quedaría calibrado con un confusor; o la regla no da INICIO en la corrida degradada → la regla barata es insuficiente y los rasgos de P1 deben entrar también en ella.

## Prioridad

1. **A1 + A2 hoy mismo** (son corridas, no código): protegen el titular «0 inocentes» y la contabilidad antes de escribir nada encima.
2. **P5 + instrumentación de A4** (la rama ya abierta): sin reloj y cola creíbles, la v3 mediría ruido; makestep y el 0,55x tocan todos los números por tomar.
3. **P1 + P2** con los ejes gemelo/distribuido/borde; la escalera de P6 en la misma semana (mismos instrumentos).
4. **P4 solo cuando familia-fuera ≥ 60 %**: activar mitigación con la etapa 2 actual sería convertir vuestro 99 % de TCP inocente en bloqueos reales.
5. **P3 en paralelo desde ya** si hay cliente: la captura de 14 días cuesta tiempo de pared, no desarrollo; los números se deciden al final.

Registrado como decisiones propuestas (continuando D5-D9): **D10** = P5-(b) + ancla/CLOCK_STEP + inyección de saltos; **D11** = lag enq/deq en todos los eventos; **D12** = corrida gemelo + cierre de contabilidad; **D13** = rasgos por origen de P1; **D14** = v3 + ejes gemelo/distribuido/borde con saturación separada; **D15** = mitigación jerárquica tras P1; **D16** = captura de 14 días en cliente iniciada en paralelo.

— Mireia, Bruno, Yasmin y Teo.