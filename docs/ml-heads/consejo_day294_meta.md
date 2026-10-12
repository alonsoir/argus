Hola Alonso, soy **Meta AI** — uno de los sabios del Consejo.

No tengo los 4 adjuntos en el chat (bloque1_day293, bloque2_day294, bateria_v3_propuesta, consejo_day292). Para la auditoría fina que pides los necesito. Súbelos aquí si puedes y re-audito línea por línea.

Te dejo igualmente el dictamen DAY294 con lo que me has dado, en tu formato: **medida + predicción + refutación**. Todo lo que digo es falsable.

### 0. Auditoría adversaria de lo medido en DAY294

**Lo que está bien medido:** el merge con firewall en SOMBRA, paridad Python/C++ 127930/127930, y la corrida benigna que no dispara INICIO son la prueba de que el bosque nuevo ya no memoriza TCP 50KB/s. Es un avance real respecto al 100% de FP anterior.

**Dónde está mal medido o va más allá del dato:**

1.  **El 0 del inocente concurrente (.51 -> .1 a 10 pps) no prueba inocencia.** Tu pcap del inocente es demasiado distinto del atacante (.50 NTP reflexión 60 pps). El bosque aprende `mean_packet_size + reflection_signature`, no comportamiento. Por tanto el 0 puede deberse a distancia de firma, no a discriminación.
    *Cómo lo mediría:* Mismo generador que el atacante pero con IP .51 y tasa 10 pps, tamaños aleatorios del atacante, y origen con puerto NTP legítimo. Si entonces el inocente sí dispara DROP, tu 0 actual queda refutado.

2.  **Relojes mezclados invalidan duraciones.** `time_to_block ~1.3s` y `hold 29.3s` están medidos con relojes distintos (monotónico en flujos vs epoch en otros). Con `makestep 1 -1` activado, cualquier salto de pared rompe el grafo. Las 37 eventos/s no-flujo bajo DNS100 y el avance 0.55s/s del reloj de eventos apuntan a cola en usuario.
    *Cómo lo mediría:* Traza de `event_timestamp` fuente (bpf_ktime vs clock_gettime) por tipo de evento, y prueba de salto: `chronyc makestep` forzado durante ataque. Si `time_to_block` o `hold` cambia >0.5s, la medida actual es inválida.

3.  **Dos filas aisladas absorvidas por k/n no es robustez.** En dns 30 y 100 q/s tienes 1 positivo cada ~3600 y ~9900 filas. Con k=3/5 lo absorbes, pero no has medido ráfaga de falsos.
    *Cómo lo mediría:* Ventana deslizante de 5s con 3+ positivos correlados temporalmente. Predicción: bajo dns100 con jitter aparecerán ráfagas.

### P1. Etapa 2 por comportamiento

**Recomendación en una línea:** Cambiar de firma de paquete a cardinalidad y cuota por víctima.

**Medida propuesta:** Nuevos rasgos calculados UNA vez en sniffer, sin coste por paquete (estructuras por ventana de 1s por víctima):
- `victim_src_cardinality`: nº IPs origen distintas / víctima en ventana. Implementación: HyperLogLog de 256 bytes por víctima, update O(1).
- `src_quota`: max_pps_de_un_origen / victim_pps. Implementación: Count-Min Sketch por víctima + top-1.
- `victim_entropy_src`: entropía de distribución de orígenes por víctima.

**Predicción:** Con estos 3 rasgos, entrenando solo con NTP reflexión, en familia fuera (SYN flood 100 pps desde 50 IPs aleatorias, tamaño fijo 60B) la etapa 2 marcará >85% de flujos atacantes y <1% de TCP 50KB/s inocente.
**Qué la refutaría:** Si `src_quota` del TCP legítimo desde 1 IP hacia víctima bajo presión supera 0.7 y dispara >5% FP, el rasgo no generaliza.

### P2. Batería v3

**Recomendación:** No basta. Falta eje de dispersión de orígenes y eje de mezcla benigno+ataque simultáneo.

**Medida:** Añadir a tu batería: (a) ataque distribuido 20-100 orígenes, (b) ataque + dnsperf 30q/s simultáneo sobre misma víctima, (c) tamaños intra-flujo variables (no solo inter-flujo).

**Predicción:** Tu batería actual pasará con 0% detección en (a) porque el bosque espera un origen.
**Refutación:** Si con (a) detecta >70% sin haber entrenado dispersión, tu modelo ya generaliza y mi crítica cae.

### P3. Valores por defecto para cliente real

**Recomendación:** Defectos fijos documentados + calibración inicial obligatoria de 14 días con aprobación humana, nunca auto-calibración silenciosa.

**Método de calibración:**
1. Medir `victim_rate_ratio` por víctima durante 14 días, ventanas de 1s, con suelo 10 pps. Sacar p99, p99.9, max.
2. K = max(3, p99.9 * 1.5). m=5, k/n=3/5, hold=30s como defecto de lab, no se toca sin segunda medida.
3. Criterio aceptación: 0 INICIO en 14 días de histórico + inyección sintética de 60 pps 90s debe disparar INICIO en <3s.

**Predicción:** En hospital, p99.9 de resolver DNS interno estará en 2.1-2.8, por lo que K=3 seguirá sin disparar falsos, pero K=3 en PACS o backup nocturno disparará.
**Refutación:** Si en 14 días p99.9 >4 en >20% de víctimas, K global no sirve: hace falta K por tipo de víctima.

### P4. Mitigación real por víctima

**Recomendación:** Opción (b) descartar solo flujos que etapa 2 marca, por origen y durante hold, con contador por víctima.

**Medida:** Cuando SOMBRA dice INICIO víctima V, firewall pasa a DROP solo si `final_decision=ataque` AND `dst==V`. Medir en lab: ataque .50 60pps + inocente .51 10pps + dnsperf 30q/s sobre .1, 90s. Métrica: pps del inocente que llega a app vs pps del atacante que llega.

**Predicción:** Inocente .51 mantiene >95% pps, atacante <5% pps durante hold.
**Refutación:** Si inocente cae <80% por colisión en tabla de flujos o por evicción, la mitigación (b) no aísla.

### P5. Base de tiempo única

**Recomendación:** (b) monotónico para ordenar y medir duraciones + ancla de arranque epoch para cruzar nodos. Nunca epoch en todo con `makestep 1 -1`.

**Medida:** Todo evento lleva `bpf_ktime_get_boot_ns()` + una sola vez al arrancar `boot_to_epoch_anchor = epoch - monotonic`. En usuario conviertes solo para logs. Hold y `time_to_block` se calculan siempre en monotónico.

**Prueba:** Lanzar ataque 90s y en t=30s forzar `chronyc -a makestep`. Predicción con (b): `time_to_block` y `FIN-INICIO` varían <50ms. Con (a) epoch: varían >1s y grafo se rompe.
**Refutación:** Si (c) TAI en eBPF 6.1 no salta con makestep y da cross-nodo sin ancla, elijo (c).

### P6. Disyuntor de saturación

**Recomendación:** Degradar a regla barata por víctima + avisar, nunca solo avisar.

**Medida:** Medir pérdidas de anillo: `ring_lost` / `ring_total` por segundo. Umbral: si `loss >1%` durante 2 ventanas o `events/s > 200` (doble de tu 110 pps sin pérdida), pasar a modo DEGRADADO: etapa 1 solo con `victim_rate_ratio`, etapa 2 = 1 (todo bajo presión se marca), pero mitigación sigue por víctima con rate-limit.

**Predicción:** A 200 pps sostenidos el modo degradado mantiene 0% pérdida de anillo y detecta INICIO en <4s, a costa de FP 5-10% que k/n 3/5 absorbe.
**Refutación:** Si en degradado el FP sube >20% y dispara INICIO en benigna dns100, el umbral está bajo: subir a 300 pps.

Si me subes los md, te devuelvo la auditoría línea por línea de intervalos, política DdosShadow y sensibilidad +4/+24/+78B que mencionas.

Soy **Meta AI**.