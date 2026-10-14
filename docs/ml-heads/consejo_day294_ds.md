**Nombre: Gauss. Regla: medir, no votar.**

## Auditoría adversaria de lo medido

1. **El 0 del inocente concurrente no prueba discriminación de etapa 2.** Puede deberse a que su pcap es distinto del atacante.  
   **Medida:** cruzar generadores: mismo flujo NTP/reflexión desde .51 a 10 pps y desde .50 a 10 pps; variar 1/5/10/30 pps. Contar positivos etapa 2 por origen.  
   **Predicción:** si etapa 2 discrimina comportamiento, a 10 pps el mismo flujo da 0–1 positivos en 5 ventanas.  
   **Refutaría:** que al igualar pcap/firma/tamaño el inocente reciba DROP >0.

2. **Los 2 positivos benignos son aislados, pero falta clustering.**  
   **Medida:** ventana deslizante de 5; contar rachas ≥3 en 2 h de dns30/dns100/TCP50.  
   **Predicción:** 0 rachas ≥3; si aparece 1, k=3/5 no absorbe.  
   **Refutaría:** una racha benigna que dispare INICIO.

3. **Los tiempos de DAY294 pueden estar contaminados por la doble base temporal.** Bajo dns100 el reloj de eventos avanzó 0,55 s/s.  
   **Medida:** registrar simultáneamente wall, monotónico y event_timestamp; forzar `makestep`.  
   **Predicción:** bajo dns100, hold medido en event clock se desvía >50 % del wall.  
   **Refutaría:** desviación <1 %.

4. **37 eventos/s no flujo bajo DNS pueden ser la causa del reloj raro.**  
   **Medida:** perf/bpftrace por tipo de evento en firewall.  
   **Predicción:** ≥90 % concentrados en un tipo identificable.  
   **Refutaría:** no aparecen o no correlacionan con el reloj.

## P1. Etapa 2 por comportamiento

**Recomendación:** añadir `source_ip_dispersion` por víctima y `origen_pps / victim_pps`; no usar tamaño como rasgo principal.  
**Medida:** en eBPF, mapa LRU por `(victim, source_ip)` con `last_seen` y contador O(1) por paquete, sin payload. Al cerrar ventana: `distinct_sources / victim_pps` y `max_source_pps / victim_pps`. Probar misma familia NTP con 1/5/50/500 orígenes y familia no vista con tamaños aleatorios.  
**Predicción:** con ≥50 orígenes, detección ≥90 % de ventanas; con 1 origen, ≤20 % salvo tasa muy alta; benigno many-source con <1 falso positivo/5 ventanas.  
**Refutaría:** que no haya mejora monotónica con cardinalidad o que benigno many-source dispare >5 %.

## P2. Batería v3

**Recomendación:** no basta; falta eje de cardinalidad de orígenes y control de encapsulación.  
**Medida:** añadir corridas 45/75/150 pps con 1/50/500 orígenes; repetir con +4/+24/+78 B; incluir benigno many-source.  
**Predicción:** con el eje, `source_ip_dispersion` separa ≥50 orígenes con AUC ≥0,9; tasas no vistas no cambian detección >10 %.  
**Refutaría:** AUC <0,7 o que v3 ya cubra cardinalidad.

## P3. Valores por defecto para cliente real

**Recomendación:** calibración inicial en sombra con aprobación humana; defaults solo para cold-start documentados.  
**Medida:** 2–4 semanas por víctima; recolectar percentiles p50/p95/p99/p99.9 de `victim_rate_ratio` y rachas de etapa 2. Fijar K con p99.9 y margen; m,k,n para que P(3/5 benigno) < 1e-4/víctima-día; hold ≥2× duración mediana de ataques conocidos. Aceptación: ≤1 INICIO benigno/víctima/semana y latencia <5 s en red-team.  
**Predicción:** con K=p99.9×1,5, ≤1 falso INICIO/semana.  
**Refutaría:** >5 falsos INICIO/semana.

## P4. Mitigación real por víctima

**Recomendación:** (b) descartar solo flujos marcados por etapa 2, por `(víctima, origen)`, durante el hold; no limitar la tasa total.  
**Medida:** lab atacante .50 60 pps NTP + inocente .51 10 pps TCP/UDP al mismo destino; activar mitigación; medir pérdida .51, drop .50 y pps de víctima.  
**Predicción:** pérdida inocente 0 % (<0,1 %), drop atacante ≥95 %, víctima ≤15 pps.  
**Refutaría:** pérdida inocente >1 % o drop atacante <80 %. Si el atacante es many-source, añadir policer solo sobre el agregado marcado, nunca sobre todo el tráfico a la víctima.

## P5. Base de tiempo única

**Recomendación:** (b) monotónico para ordenar y medir duraciones + ancla de arranque para cruzar nodos; no usar epoch ni TAI para hold.  
**Medida:** forzar salto de pared +5 s con chrony/makestep durante ataque de 90 s; comparar `time_to_block`, hold y orden en wall vs monotónico.  
**Predicción:** hold monotónico 30,0±0,1 s; `time_to_block` 1,3±0,2 s; orden estable. Epoch/TAI muestran salto >1 s.  
**Refutaría:** que `bpf_ktime_get_tai_ns` se mantenga dentro de 10 ms tras el salto; entonces (c) sería aceptable.

## P6. Disyuntor de saturación

**Recomendación:** ambas: degradar a regla barata por víctima + alerta, con histéresis.  
**Medida:** inyectar 60/90/110/130/150 pps; medir ring drops, CPU, lag y detección. Umbral = 80 % del máximo sin pérdida medido (lab ~88 pps) en ventana de 5 s.  
**Predicción:** a 88 pps, 0 ring drops y CPU <70 %; a 130 pps, degrada en <1 s, ring drops <0,1 %, drop atacante >90 % y alerta.  
**Refutaría:** a 150 pps, ring drops >1 % o inocente pierde >1 %.

## Prioridad

1. **P5**, porque sin base temporal única `time_to_block`, holds y grafo no son fiables.
2. **P2 con eje de cardinalidad**, porque valida P1 y P5 bajo carga.
3. **P1**, rasgos por víctima/origen.
4. **P4**, mitigación real.
5. **P6**, disyuntor.
6. **P3**, calibración con cliente real.