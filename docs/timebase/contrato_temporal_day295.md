# Contrato temporal de aRGus — DAY295 (rama fix/event-timestamp-timebase)

Árbitro: Alonso. Origen: D16 y D17 (consejo_day294_sintesis.md); aceptación D15.
Decisiones DAY295: T1 base MONOTONIC; T2 detector [CLOCK-SLEW] + regla del lab; T3 target `lab-clock-step` en esta rama.

## 1. Inventario medido (DAY295, git grep)

| Dónde | Reloj | Destino |
|---|---|---|
| Flujo Variant A (`ring_consumer.cpp:939`) | `bpf_ktime_get_ns` (`sniffer.bpf.c:328`) = CLOCK_MONOTONIC | `event_timestamp` |
| Fast-alert (`ring_consumer.cpp:1340`) | idem (event.timestamp del kernel) | `event_timestamp` |
| Ventana ransomware (`ring_consumer.cpp:1446`) | `system_clock` (epoch) | `event_timestamp` |
| Flujo Variant B (`main_libpcap.cpp:160`) | `system_clock` al EMITIR (no al capturar) | `event_timestamp` |
| `event_id` (`:927`, `:1337`) | monotónico + `src^dst` | PK del grafo (fuera de alcance, §6) |
| Ventanas DDoS kernel, tablero de víctimas | CLOCK_MONOTONIC / `steady_clock` | internos |
| `ddos_windows.csv` (`ddos_kernel_reader.hpp:222`) | `system_clock` | sello epoch |
| CSV ml-detector (`csv_event_writer.cpp:221`) | copia `event_timestamp` sin mirar la base | Parquet `timestamp_utc_ns` (`generate_parquet.py:33`) |
| CSV firewall (`logger.cpp:267/313`) | `system_clock` (ms) | Parquet firewall (`generate_parquet.py:65`) |
| Reloj de la sombra (`zmq_subscriber.cpp:588`) | `event_timestamp` (solo eventos de flujo, parche D293) | hold, INICIO/FIN |
| `detection.set_timestamp` (`zmq_subscriber.cpp:712`) | `event_timestamp.seconds()` — TRUNCA los ns | detección del firewall |
| Validador Parquet (`validate_roundtrip.py:30/40`) | lee solo la fila `[0]` | EMECAS |

Hoy `event_timestamp` (un único `google.protobuf.Timestamp`, `network_security.proto:592`) mezcla dos bases:
flujo y fast-alert en monotónico; ventana ransomware y Variant B en epoch. Origen del 99 % monotónico del Parquet
2026-10-01 y de la congelación de la sombra en DAY293.

## 2. Medidas DAY295 (scripts/d295_suspension.py, scripts/d295_slew_rate.py)

- M1 Suspensión del Mac ~4 min: la VM se CONGELA. REALTIME, MONOTONIC y BOOTTIME pierden lo mismo (B−M cambia
  0,000000 s). El lab no distingue MONOTONIC de BOOTTIME.
- M2 Tras despertar, chrony (defender) detecta 257,6 s y CORRIGE GRADUALMENTE pese a `makestep 1 -1`: MONOTONIC y
  REALTIME corren +81 300 ppm (8,1 %) frente a MONOTONIC_RAW durante ~45 min. R−M no cambia: la corrección
  gradual es INVISIBLE a R−M. Un hold de 30 s dura 27,7 s reales.
- M3 `chronyc makestep` manual: REALTIME salta +208,878 s; MONOTONIC y BOOTTIME no (un par: dR 209,4 s, dM 0,547 s).
  Firma de CLOCK_STEP = cambio brusco de R−M. Tras el salto, MONOTONIC frente a RAW = −1875,5 ppm (corrección de
  frecuencia de base de chrony, constante).
- M4 El client saltó solo (+257,7 s, 4 min después de detectarlo) ANTES que el defender: chrony sirve su hora
  corregida, no su reloj. Durante ~4 min client y defender discreparon en ~210-230 s.

## 3. Contrato (versión 1)

C1. Base interna única: CLOCK_MONOTONIC. Kernel `bpf_ktime_get_ns`; espacio de usuario `std::chrono::steady_clock`
    (libstdc++ en Linux = CLOCK_MONOTONIC; un test lo comprueba). Ventanas, hold, time_to_block, retrasos y orden se
    calculan SOLO en esta base, y solo entre eventos con el mismo `boot_id`.
C2. Campos nuevos en el evento (nombres provisionales; números al leer el .proto; `schema_version` sube):
    - `mono_ns` (uint64): instante del evento en CLOCK_MONOTONIC.
    - `boot_id` (string, /proc/sys/kernel/random/boot_id). `originating_node_id` ya existe.
    - `producer_start_mono_ns` (uint64) + `producer_seq` (uint64, +1 por evento): orden total y duplicados (A1).
      La clave (node_id, boot_id, producer_start_mono_ns, producer_seq) es única.
    - `wall_anchor_ns` (int64): REALTIME − MONOTONIC vigente al emitir. Epoch = mono_ns + wall_anchor_ns.
    - `clock_state` (enum): OK / SLEWING / STEPPED (último salto hace menos de N s, N en el JSON).
    - `time_contract_version` (uint32) = 1.
    - Retraso por salto (D17): `sniffer_send_mono_ns`, `mld_recv_mono_ns`, `mld_send_mono_ns`; el firewall calcula
      el suyo al recibir. Mismo nodo y mismo boot_id → restas válidas.
C3. `event_timestamp` vuelve a significar SIEMPRE epoch (semántica de google.protobuf.Timestamp) = mono_ns +
    wall_anchor_ns, en todos los tipos de evento y en las dos variantes. Nadie calcula duraciones con él.
C4. Ancla por proceso productor: muestrea REALTIME − MONOTONIC cada `anchor_period_s`; si cambia más de
    `step_threshold_s` → nueva ancla, log `[CLOCK-STEP] delta=… s` y contador. Medido: en reposo R−M varía
    < 0,00001 s en 720 s.
C5. Detector `[CLOCK-SLEW]` (uno por nodo, en el sniffer): ppm de MONOTONIC frente a MONOTONIC_RAW por ventana de
    `slew_window_s`; si |ppm| > `slew_ppm_threshold` → aviso periódico y `clock_state = SLEWING`. Medido: base
    −1876 ppm, corrección gradual +81 300 ppm. RAW no se usa para medir (el XDP no tiene RAW).
C6. Bordes: CSV del ml-detector, dataset DDoS, Parquet y logs escriben epoch derivado (C3) y, además, mono_ns,
    boot_id, producer_seq y clock_state. El firewall deja de truncar (`:712`) y su sombra usa mono_ns.
C7. Parámetros en el JSON (el JSON manda; defecto validado + `[CONFIG-DEFAULT]`; valores de LABORATORIO):
    anchor_period_s=1 [0,1–60], step_threshold_s=0,05 [0,001–10], slew_window_s=10 [1–300],
    slew_ppm_threshold=10000 [1000–500000], stepped_recent_s=60 [1–3600].
C8. Regla del lab: tras suspender el Mac, `make lab-clock-step` (defender y después client: `chronyc makestep`;
    verificación DENTRO de las VMs con chronyc, desfase < 1 ms) antes de cualquier medida.

## 4. Aceptación

- Salto inyectado `sudo date -s "+5 seconds"` y `-5` en mitad de un ataque: hold 30 ± 0,1 s (en mono_ns), orden
  intacto por (boot_id, producer_seq), `[CLOCK-STEP]` registrado, Parquet 100 % en rango.
- Corrección gradual real (suspensión de ~3 min SIN lab-clock-step): `[CLOCK-SLEW]` y `clock_state = SLEWING`
  mientras dure; después, `lab-clock-step` y vuelta a OK.
- Validador de Parquet sobre TODAS las filas (epoch entre 2020-01-01 y ahora + 1 día).
- Test: steady_clock y clock_gettime(CLOCK_MONOTONIC) difieren < 1 ms.
- D15 (A1 contabilidad con producer_seq, A2 gemelo .61, A5 ataque largo) con los relojes ya fiables.

## 5. Orden de los patchers (atómicos, --check / --apply, marca [TIMEBASE-D295])

1 proto + `make proto` → 2 sniffer (flujo, fast-alert, ventana ransomware, Variant B, ancla, CLOCK-STEP, CLOCK-SLEW)
→ 3 ml-detector (recepción/envío, CSV, dataset DDoS) → 4 firewall (sombra en mono_ns, `:712`, retraso)
→ 5 Parquet (esquemas, generate_parquet, validador sobre todas las filas) → 6 Makefile `lab-clock-step`
→ 7 pruebas. Compilar y probar con PROFILE=production.

## 6. Fuera de alcance

- `event_id` y `community_id` no cambian. `community_id` es el estándar compartido con Suricata y Zeek;
  `event_id` es propio de cada sensor (adapters: `suricata:`, `zeek:`, `wz1:` deterministas). La colisión
  (DEBT-EVENT-ID-COLLISION-001) y la reproducibilidad entre replays (consulta al Consejo DAY180) van en un diseño
  propio: reacuñar con boot_id/seq resolvería la colisión pero empeoraría la reproducibilidad.
- BOOTTIME (no distinguible en el lab; solo importa si se suspende el nodo del pipeline). TAI (descartado D16).
- Sincronización entre nodos físicos (boot_id y node_id dejan el sitio preparado).
- DEBT-LAB-CHRONY-NO-AUTOSTEP-001: el defender no saltó en 14 min con `makestep 1 -1`; el client sí (4 min).
  Evidencia: journals de chrony DAY295. Mitigado por C8.

## 7. Anexo DAY295 (tarde): lo implementado y lo que no estaba en el inventario de la mañana

Implementado y verificado E2E (commits 1e285785, ad439698, 82e99666, a8bdb27b, df376a42):
- Proto: enum ClockState, message TimeContext, NetworkSecurityEvent.time_context = 38 (solo añade campos).
- Sniffer Variant A: timebase.hpp (lógica pura, test_timebase 33/33); sección "timebase" en sniffer.json con
  [CONFIG-DEFAULT]; hilo del reloj ([CLOCK-STEP], [CLOCK-SLEW]); stamp_time_context en flujo, fast-alert y ventana
  ransomware; event_timestamp = mono_ns + ancla en los tres; schema_version 32. Log de arranque:
  "[TIMEBASE] contrato v1 activos: ..." con los valores que llegan al consumidor.
- Firewall: sombra DDoS sobre time_context.mono_ns; validación de time_context; retraso sniffer->firewall.

Correcciones al inventario (§1):
- Faltaban DOS tiempos más del sniffer, ambos monotónicos: NetworkFeatures.flow_start_time (campo 11) y
  TimeWindow.window_start (ring_consumer.cpp populate_protobuf_event). flow_start_time es el que el ml-detector
  copia al bronce correlation_v1 (columnas 5-6) -> el bronce de aRGus iba en segundos desde el arranque (~10427)
  mientras Suricata, Zeek, los tests del bronce, flow_uid y ADR-057 esperan epoch. Arreglado [TIMEBASE-D295:FLOWSTART]:
  ambos en epoch derivado. Verificado: flow_start_sec 1791786093,530362835 = mono 12865,876550181 + ancla (dif 23 ns).
  TimeWindow.sequence_number sigue siendo event.timestamp (es un contador, no un instante).
- csv_writer del ml-detector está APAGADO desde DAY285 (único consumidor: el Parquet antiguo de parquet-convert).
  La ruta "CSV ml-detector -> Parquet timestamp_utc_ns" no está viva; el borde vivo hacia el grafo es
  correlation_writer (bronce). El validador de Parquet sigue mirando solo la fila [0] (pendiente).
- Detection.timestamp (firewall :712): sin consumidores en todo el repo; se queda en segundos epoch.
- sniffer_send_mono_ns = instante de SERIALIZACIÓN (entrada en send_queue_), no el envío por socket.
- Cadena de configuración del sniffer: sniffer.json -> ConfigManager (SnifferConfig) -> config_types.cpp copia a
  g_config (StrictSnifferConfig) -> main.cpp copia campo a campo a un SnifferConfig nuevo -> RingBufferConsumer.
  Un eslabón olvidado = defectos en silencio; la línea [TIMEBASE] del arranque es la prueba de que llegó.

Decisiones del árbitro (DAY295):
- La sombra cuenta VENTANAS, no segundos: hold_s -> hold_windows en firewall.json (un JSON antiguo con hold_s avisa
  y se ignora). 1 ventana = 1 s de CLOCK_MONOTONIC del sniffer (mono_ns / 1e9, entero); es la única constante fija
  (window_ms configurable exigiría recalibrar m, k/n y hold: BACKLOG).
- Criterio de aceptación de D16 REFORMULADO: el hold dura exactamente hold_windows ventanas (29-30 s medidos en
  mono_ns, cuantizado por diseño; explica el FIN a 29,3 s de DAY294) y un salto de +-5 s del reloj de pared en mitad de
  un ataque no lo cambia.
- time_context con formato inusual: se registra y se marca para estudio, nunca se usa para procesar el evento ni se
  castiga a la IP del paquete (no es quien lo rompió: el time_context lo escribe nuestro sniffer y viaja por el ZMQ
  interno; una anomalía apunta a un fallo nuestro, a un productor sin contrato o a un componente comprometido).
  8 causas: sin_time_context, version, mono_cero, boot_id, futuro, retraso_otro_boot, retraso_negativo,
  retraso_absurdo. Detalle [TIMEBASE-ANOMALIA] limitado por causa y periodo (anomalias_detalle_max) + recuento en el
  resumen [TIMEBASE]; si hubo anomalías, también por stderr.
- Supuesto de la v1: sniffer y firewall en el MISMO nodo (retraso_otro_boot = anomalía). Multinodo: BACKLOG.

Medido con el pipeline en reposo (DAY295 09:57): retraso sniffer->firewall media 12-26 ms, máximo 22-90 ms por
periodo de 10 s; 0 anomalías en las 8 causas. Línea base para el 0,55x bajo dns100.

Pendiente en esta rama: lab-clock-step; sellos mld_recv/mld_send del ml-detector (D17, partir el retraso en dos
tramos); validador de Parquet sobre todas las filas; aceptación (saltos +-5 s, corrección gradual real, D15 A1/A2/A5);
EMECAS+++, PR, merge.

## 8. Anexo DAY296 — medido (rama fix/event-timestamp-timebase)

### 8.1 Perfil del lab
- El lab ejecutaba binarios de DEBUG (-O0) desde el 2026-10-11: pipeline-start usa build-$(PROFILE) (PROFILE ?= debug), no
  build-active. Las medidas en reposo del DAY295 (12-26 ms) son de debug. Regla nueva: compilar, probar Y ARRANCAR con
  PROFILE=production. set-build-profile.sh aceptaba debug|release (build-release no existia); ahora debug|production|tsan|asan.

### 8.2 D17: retraso partido en tramos (mismo nodo, CLOCK_MONOTONIC)
- ml-detector sella mld_recv_mono_ns (tras el recv, antes de descifrar) y mld_send_mono_ns (antes de serializar), solo si el
  evento trae time_context. El firewall parte el retraso: sniffer_mld / mld_interno / mld_fw. Causas de anomalia nuevas:
  8 mld_sin_sello, 9 mld_orden (sniffer_send <= mld_recv <= mld_send <= ahora). Identidad de tramos exacta (<= 0,0001 ms).
- Hallazgo: el firewall escribia ~25 lineas DEBUG por evento a vboxsf con doble vaciado; logging.level del JSON se leia y no se
  usaba. Arreglado ([LOG-LEVEL-D296], defecto info). Retraso sniffer->firewall en reposo, production:
  log debug: media 14-39 ms, max 85 ms (mld_fw 8-25 ms)  ->  log info: media 3,3-5,9 ms, max <= 11 ms (mld_fw 0,3-2,4 ms).
  Bajo ataque ntp 60 pps: media 2,2-7,6 ms, max <= 18,5 ms. Tramo dominante ahora: sniffer_mld (1,4-4,3 ms).

### 8.3 Saltos de pared de +-5 s en mitad de un ataque (chrony parado)
- Ataque ntp 60 pps (.50 -> .1) sobre base .51 10 pps; +5 s a los 43 s del ataque; -5 s a los 27,6 s del hold.
- Sniffer: [CLOCK-STEP] +4,9986 s y -5,0001 s.
- Sombra: primer DROP ventana 14399 (~1,7 s tras el inicio), INICIO 14401 (k=3), ultimo DROP 14489, FIN 14519 = 14489 + 30
  (hold_windows exacto, sin efecto del salto de -5 s); 5364 DROP, todos de .50; 0 del inocente; 0 anomalias.
- Bronce: inicios de flujo del atacante con hueco de 5,015 s (5 s + 1/60 s), es decir sigue al reloj de pared. El hueco
  aparece 0,20 s despues del salto: anchor_period_s = 1,0, asi que tras un salto hasta 1 s de flujos lleva el ancla vieja.
- El FIN se emitio 5,6 s de pared despues de su ventana: la sombra decide al llegar eventos y la base acababa justo en la
  ventana 14519. El reloj de pared no gobierna la exportacion de flujos del sniffer (revisado en el codigo).

### 8.4 Correccion gradual provocada (adjtimex, chrony parado)
- tick 10030 (el de chrony) -> 10530 durante 90 s de monotonico (85,50 s de RAW): [CLOCK-SLEW] 52993,7 ppm (esperado 53000),
  sin [CLOCK-STEP]; al restaurar, [CLOCK-SLEW] FIN ppm=2993,71 (la base del tick de chrony). Vuelta: un unico [CLOCK-STEP]
  -4,27485 s = 90,0346 x (1 - 10030/10530), aplicado por chrony al arrancar. 0 anomalias.

### 8.5 Suspension real del Mac
- Mac dormido 118 s (pmset); la VM quedo 134 s atrasada. chrony lo detecto ~2 min despues de despertar y SALTO +133,994 s
  (en DAY295 corrigio gradualmente 14 min: no siempre igual). Durante esos ~2 min la epoca del defender va 134 s atrasada.
  Regla del lab: make lab-clock-step justo al despertar.

### 8.6 Parquet y bronce
- validate_roundtrip.py comprobaba solo la fila [0]: 32 ficheros del ml-detector (691461 de 774069 filas, 89 %) llevaban
  timestamp_utc_ns monotonico desde 2026-03-08. Ahora se comprueban todas las filas; datos borrados. csv_writer esta
  apagado desde DAY285: ese gate vigila un camino historico. El camino vivo es el bronce correlation_v1.
- Bronce: 48 % de las filas eran fast-alerts con flow_start = 0 (sin tiempo). Fuera del bronce hasta que sean fiables
  (correlation_writer.include_fast_alerts = false). Bajo replay DNS hay ~1 fast-alert por paquete.

### 8.7 No verificado
- Orden por (boot_id, producer_seq): ningun log ni el bronce llevan producer_seq.
- El salto de -5 s en el bronce (cayo en el hold, solo con la base .51).

## 9. Anexo DAY297 — aceptacion D15 (A1, A2, A5) y secuencia por productor

### 9.1 Orquestador de corridas
- scripts/timebase/lab_corrida.sh (Mac) + lab_corrida_defender.sh: lab-clock-step, parada, nada vivo, logs a cero,
  arranque PROFILE=production, ESTABLE, tcpdump en eth2 del defender, client, parada y contabilidad
  (a1_contabilidad.sh). Para al primer fallo. ~7 min por corrida; resultados en logs/lab/day297/<nombre>/.
- Falso positivo corregido el mismo dia: el eco del comando de comprobacion de etcd en pipeline-start contiene
  "STOPPED"; solo cuentan las lineas de estado que empiezan por la cruz.
- Entorno DAY297: las cinco VMs levantadas (defender, client, suricata, zeek, wazuh). El agente Wazuh del client habla
  con el manager .12:1514 por el intnet: aparece en el cable y en el sniffer.

### 9.2 A1 contabilidad (ntp 60 pps desde .50 + base .51 a 10 pps)
- Cable (tcpdump en eth2, 0 descartados por el kernel): ataque de .50 = 5400 exactos (udp src port 123); .50 lleva
  ademas 69-72 paquetes legitimos (agente Wazuh -> .12:1514, NTP de chrony a .1, ARP). .51 = 2100.
- DROP de los resumenes [SOMBRA-DDOS] = eventos_drop del registro de la sombra, al evento (5350 y 5360).
- Un evento de flujo por paquete del cliente (diferencia explicada por el reposo, ~1-2 flujos/s). Los eventos no-flujo
  van ~1 a 1 con los paquetes UDP del client (fast-alerts; DEBT-FIREWALL-NONFLOW-EVENTS-001).
- event_id del flujo = event.timestamp (ns, bpf_ktime_get_ns) + "_" + (src_ip XOR dst_ip): no es una identidad (XOR
  simetrico y sin puertos; en el ataque solo la marca de tiempo distingue eventos) ni distingue duplicado de colision.
  DEBT-SNIFFER-EVENT-ID-NOT-UNIQUE-001.
- Contadores [TIMEBASE-SEQ-D297] en el firewall (clave nodo|boot_id|producer_start_mono_ns, acumulados, linea propia
  "[TIMEBASE] secuencia"): seq_dup = 0 y seq_hueco = 0 en 15262, 17129 y 26110 eventos; seq_recibidos = suma de
  "eventos" de los resumenes, diferencia 0 en las tres corridas. Ningun evento perdido ni duplicado entre sniffer y
  firewall, a 70, 80 y 130 pps hacia la victima.
- Los 5357 DROP de DAY294 frente al maximo de 5292-5352 (Consejo, A1) no se pueden reconstruir (sin producer_seq
  visible entonces); con el binario actual hay 0 duplicados medidos.

### 9.3 Orden de entrega (corrige el "orden intacto" de 8.7, no verificable en DAY296)
- producer_seq garantiza unicidad y deteccion de perdidas; NO garantiza orden de entrega.
- seq_desorden: 1 (60 pps), 0 (70 pps) y 12 (120 pps). Los detallados ([TIMEBASE-SEQ-DET-D297]): siempre un flujo
  (kind 0) adelantado por la fast-alert siguiente (kind 1), distancia 1. El sniffer numera en orden; la inversion
  ocurre despues del sellado. Hipotesis sin medir: ml-detector (2 hilos de trabajo; la fast-alert no pasa por los
  modelos desde DAY285). Las ventanas de la sombra avanzan solo con flujos; los casos vistos no las afectan.
- Siguiente paso: mld_recv_mono_ns / mld_send_mono_ns en la linea de detalle. DEBT-TIMEBASE-SEQ-DELIVERY-ORDER-001.

### 9.4 Arranque en frio de la etapa 1
- Primera corrida: 32 DROP en el primer segundo tras arrancar el pipeline (primer origen 192.168.100.12, manager Wazuh,
  -> .1 TCP, ratio = 14, p1 = 0,86); sin INICIO (k/n los absorbio). No se repitio en las tres corridas siguientes:
  depende de que haya trafico hacia una victima en los primeros segundos.
- Causa en el codigo: warm_windows solo condiciona la ENTRADA en bajo_presion (ddos_contract_v2.hpp:103); la etapa 1
  del ml-detector compara el ratio crudo con K = 3 (ddos_v2_head.hpp:39) y nadie consume bajo_presion.
  DEBT-DDOS-COLDSTART-ETAPA1-001 (siguiente rama, decision de Alonso).

### 9.5 A2 gemelo .61 (mismos paquetes que el ataque, otra IP; tcprewrite --srcipmap, --fixcsum)
| Gemelo | DROP .50 | DROP .61 | ratio_max | NTP legitimo de .51 (446 paquetes, src port 123) |
|---|---|---|---|---|
| 10 pps | 5381/5400 = 0,9965 | 896/900 = 0,9956 | 8,00 | 0 DROP |
| 60 pps | 5356/5400 = 0,9919 | 5355/5400 = 0,9917 | 13,07 | 0 DROP |
- Afirmacion correcta: la cabeza discrimina el TIPO de trafico (NTP de reflexion frente a NTP legitimo pequeno), no el
  comportamiento del origen. Base de D19 (rasgos por origen) y de aplazar la mitigacion real (D20).

### 9.6 A5 ataque largo (offline contra la funcion de produccion)
- scripts/timebase/a5_ataque_largo.cpp incluye sniffer/include/ddos_contract_v2.hpp y llama a victim_ewma_step con sus
  parametros por defecto (alpha 0,1; alpha_lento 1/3600; k_in 3; k_out 1,5; warm 30; floor 10). 10 min de base y
  2 h de base + ataque.
- La etapa 1 (ratio >= 3) deja de pasar a los 905-1459 s y la sombra daria FIN a los 15,6-24,8 min de un ataque
  sostenido (antes cuanto mas debil); la salida de bajo_presion (k_out = 1,5) llega a los 3400-3954 s. Todas las
  celdas a +-1 ventana de la prediccion analitica t = tau * ln((P - e0) / (P - P/K)); el ratio inicial coincide con el
  medido en vivo (6,99 / 8,00 / 13,07).
- Causa comun con 9.4: la etapa 1 no consume el estado de histeresis. Con bajo_presion el corte pasaria a 57-66 min;
  cuanto debe durar es calibracion (D22). DEBT-DDOS-V2-LONG-ATTACK-001 confirmada offline; la corrida en vivo (~20 min,
  necesita --loop) va a la siguiente rama como prueba de antes y despues (decision de Alonso).

### 9.7 No verificado
- Origen de los ~140 pps hacia .1 en el primer segundo de la primera corrida (ratio 14).
- Los 2 desordenes no detallados de la corrida a 120 pps (tope de detalle por periodo).
- En que etapa ocurre el desorden (cola de envio del sniffer, ml-detector o transporte).
