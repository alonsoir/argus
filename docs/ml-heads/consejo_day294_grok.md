**Nombre: Grok**

Auditoría adversaria breve de lo medido (antes de P1-P6):  
El 0 del inocente concurrente (.51) y los 5357 DROP solo de .50 pueden deberse a que la etapa 2 memoriza firmas de tamaño/reflexión del generador NTP (límite ya reconocido), no a discriminación comportamental pura. El pcap del inocente es “demasiado distinto” en mean_packet_size y reflection_signature. Confirmarlo: re-ejecutar el E2E idéntico pero forzando al inocente a usar el mismo tamaño medio ±5 B y la misma firma de reflexión (o al revés: atacante con tamaños aleatorios). Si el inocente empieza a generar DROP o el atacante pierde detección, el confusor es la firma, no la etapa 1.  
Bajo dns100 el reloj de eventos avanzó ~0,55 s/s y recuperó de golpe: posible cola de eventos no-flujo (~37/s) o semántica de timestamp. Medir: correlacionar contador de eventos no-flujo vs. desfase monotónico-pared en la misma corrida.  
Paridad 127930/127930 es fuerte, pero solo sobre el conjunto de entrenamiento; no prueba generalización.  
Todo el lab está acotado a ≤110 pps sin pérdida de anillo → cualquier predicción de latencia o k/n debe llevar el caveat de saturación.

---

**P1. Etapa 2 por comportamiento**  
Recomendación: priorizar `source_ip_dispersion_victim` (nº de orígenes distintos por víctima en la ventana de 1 s) + `origin_share` (tasa del origen / tasa de la víctima).

Medida: añadir ambos rasgos en el sniffer (mapa eBPF por víctima, actualización O(1) por paquete con bitmap o contador + set limitado a 64 orígenes; sin coste extra por paquete más allá del hash). Re-entrenar etapa 2 solo con filas bajo presión, excluyendo arranque. Luego batería “familia fuera”: reflexión NTP con tamaños aleatorios uniformes [40-1400] y SYN-flood con tamaños aleatorios; inocente TCP/UDP legítimo concurrente.

Predicción numérica: con los dos rasgos, detección de familia fuera ≥ 85 % (TPR) a FP ≤ 0,5 % en inocente concurrente (k=3/5 absorbe los aislados).

Qué la refutaría: TPR < 60 % en familia fuera o FP > 2 % en inocente → los rasgos siguen siendo insuficientes o el entrenamiento aún memoriza.

---

**P2. Batería v3**  
Recomendación: la propuesta es casi suficiente; falta un eje explícito de “origen legítimo que de repente concentra >30 % de la tasa de la víctima”.

Medida: ejecutar exactamente `bateria_v3_propuesta.md` + una corrida extra: base mixta + un único origen legítimo (dnsperf o TCP) que suba a 40-50 % de la tasa de la víctima durante 60 s mientras el resto es ataque de familia fuera.

Predicción: con tamaños aleatorios + tasas 45/75/150, etapa 2 (tras P1) da TPR ≥ 80 % y 0 INICIO falsos en bases mixtas.

Qué la refutaría: cualquier corrida de familia fuera con TPR < 50 % o un INICIO en la base mixta de volumen alto → falta eje de concentración de origen o de volume-skew.

---

**P3. Valores por defecto para cliente real**  
Recomendación: calibración inicial automática con aprobación humana (no defectos fijos).

Medida: 7-14 días de tráfico real en sombra (solo logging de victim_rate_ratio y decisiones etapa 1/2). Calcular percentiles 95/99/99,9 de victim_rate_ratio por víctima crítica; proponer K = p99 × 1,5 (o el valor que deje FP < 0,1 % en el histórico). Para m/k/n/hold: simular offline las políticas sobre el log y elegir la que maximice TPR histórico de incidentes conocidos con FP=0. Presentar tabla al personal; ellos aprueban o ajustan.

Predicción: en un hospital típico K quedará entre 4-8; hold 60-180 s.

Qué la refutaría: si tras 14 días el p99 de victim_rate_ratio es <2 o >20 de forma estable → la histéresis o el EWMA necesitan retuning previo.

---

**P4. Mitigación real por víctima**  
Recomendación: (b) descartar solo los flujos que la etapa 2 marca, por origen, durante el hold.

Medida: implementar en lab el drop selectivo por (víctima, origen) cuando final_decision=ataque; medir throughput del inocente .51 (10 pps) y del atacante durante 90 s de ataque + 30 s hold.

Predicción: inocente .51 mantiene ≥ 98 % de sus paquetes; atacante pierde ≥ 95 % de los suyos una vez en hold.

Qué la refutaría: pérdida > 5 % del inocente o < 80 % del atacante → hay fuga de clasificación o el hold es demasiado corto/largo.

---

**P5. Base de tiempo única (siguiente PR)**  
Recomendación: (b) monotónico para ordenar y medir duraciones + ancla de arranque (realtime-monotonic) escrita una vez al inicio y actualizada solo en arranque/reinicio.

Medida: tras el cambio, forzar un `makestep` artificial de ±5 s en el host mientras corre un ataque E2E + hold; comprobar que time_to_block, duración de hold y grafo de eventos siguen siendo correctos (±100 ms).

Predicción: con ancla + monotónico, hold medido = 30,0 ± 0,2 s incluso con salto de pared; time_to_block no se altera.

Qué la refutaría: hold desviado > 1 s o time_to_block negativo/erróneo tras el salto → la ancla no se está aplicando correctamente a todos los eventos.

---

**P6. Disyuntor de saturación**  
Recomendación: ambas: degradar a regla barata por víctima (solo victim_rate_ratio ≥ K → sombra/alerta) + avisar.

Medida: inyectar tráfico sintético a 150, 200, 300 pps en el anillo; medir pérdida de eventos de flujo, latencia de decisión y tasa de falsos. Umbral de activación: pérdida de anillo > 0,1 % o cola de eventos > 2× la media de 10 s.

Predicción: a 150 pps ya aparece pérdida > 0,5 %; el disyuntor debe saltar antes de 110-120 pps sostenidos.

Qué la refutaría: si a 200 pps no hay pérdida medible en el anillo actual → el umbral lab es demasiado conservador y hay que re-medirlo en hardware real.

---

**Prioridad**  
1º P5 (base de tiempo única) — ya es la siguiente rama abierta y ha mordido tres veces; sin reloj fiable el resto de medidas de latencia/hold son sospechosas.  
2º P1 + batería v3 (generalización).  
3º P4 (mitigación selectiva).  
4º P6 (disyuntor).  
5º P3 (calibración cliente) — se hace cuando haya un cliente real y logs de sombra limpios.