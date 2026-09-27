# Grieta B — `source_ip_dispersion` de la cabeza DDoS

**Investigación medida (DAY263+).** Definición operacional del lado *serve*, acople
estructural con la ruta ransomware, dataset CICDDoS2019 validado y plan del análogo
offline. Toda afirmación de abajo está MEDIDA sobre el código, no supuesta.

Contexto: grieta A (geo) fue refutada como fantasma en DAY261-262. Queda grieta B —
la de diseño, la única de las 9 features que el bosque SÍ consume.

---

## 1. Definición operacional del lado serve (MEDIDA)

- `source_ip_dispersion` se computa en `sniffer/src/userspace/ml_defender_features.cpp:64-73`
  (`extract_ddos_source_ip_dispersion`). El parámetro `flow` va comentado → **NO es
  función del flujo**; sale del `aggregator_`.
- **Fórmula:** `min( log2(unique_ips + 1) / log2(event_count + 2), 1.0 )`.
    - `event_count == 0` → `0.0f`
    - `!aggregator_` → `MISSING_FEATURE_SENTINEL` (`-9999.0f`)
    - Es una normalización logarítmica de la fracción de endpoints únicos, NO una cuenta.
      Pocas IPs sobre muchos eventos → ~0 (una fuente martilleando = flood clásico);
      tantas IPs como eventos → ~1 (DDoS distribuido).
- **Ventana:** 30 s exactos (`now - 30'000'000'000ULL`), **sliding** (recalculada por
  flujo con `TimeWindowAggregator::get_current_time_ns()`). No tumbling.
- **Clave de agrupación:** NINGUNA. `get_window_stats(start, now)` toma la ventana
  global, sin trocear por IP destino ni 5-tupla.
- **TRAMPA CAZADA — el estadístico NO cuenta IPs origen pese al nombre.**
  `time_window_aggregator.cpp:60-61` mete `event.src_ip` **y** `event.dst_ip` en el
  MISMO `unordered_set unique_ips`. Cuenta endpoints únicos (origen ∪ destino).
  Construir el análogo offline sobre `Source IP` a secas —lo que el nombre empuja a
  hacer— mediría otra magnitud → espejismo con dos etiquetas iguales (mismo género que
  la grieta A homónima).
- **Sin filtro:** `add_event` (`time_window_aggregator.cpp:28`) = solo `push_back` al
  ring buffer + `pop_front` si excede `max_events`. NO usa la `IPWhitelist`/`DNSAnalyzer`
  que recibe el constructor. → el offline NO replica ningún filtro de whitelist.
- **Cap del ring buffer:** `max_events = 10000` (confirmado en ambos lados: default del
  ctor y valor explícito en `ransomware_feature_processor.cpp:26-30`). Bajo flood
  (CICDDoS2019 = ataque casi puro, densidad altísima) el cap MUERDE: 10000 eventos
  entran en < 30 s → la ventana efectiva es "últimos 10000 eventos", NO 30 s de reloj, y
  `event_count` se satura en 10000. **El offline debe aplicar ventana =
  `[t-30s, t] ∩ últimos 10000 eventos`.**

## 2. Acople estructural (hallazgo fuerte, material de paper/Consejo)

- `MLDefenderExtractor` NO posee aggregator: ctor `= default`, `aggregator_ = nullptr`
  (`ml_defender_features.hpp:239`). Lo recibe por inyección vía
  `set_aggregator(TimeWindowAggregator*)` (`hpp:47`, idempotente por `if(!aggregator_)`).
- El ÚNICO `add_event` del repo (fuera de la def) está en la ruta **ransomware**
  (`ransomware_feature_processor.cpp:130` y `:134`). El lado DDoS solo LEE de la ventana;
  nadie la alimenta desde DDoS.
- **Cableado (`ring_consumer.cpp:819`):**
  `ml_extractor_.set_aggregator(ransomware_processor_->get_aggregator())`.
  `get_aggregator()` devuelve `aggregator_.get()` (`ransomware_feature_processor.hpp:35`)
  = puntero crudo al `make_unique` que POSEE el processor de ransomware → **MISMA
  INSTANCIA, sin copia**. Inyección lazy, una vez:
  `if(!ml_extractor_.has_aggregator() && ransomware_processor_)`. NO está detrás de flag
  de ransomware → acople PERMANENTE y estructural mientras exista `ransomware_processor_`.
- **Consecuencia:** la feature DDoS `source_ip_dispersion` NO tiene ventana propia; vive
  de la ventana que llena la ruta ransomware (su granularidad, su cap, su condición de
  estar viva y alimentando). Si esa ruta no corre, la feature se mueve por razones
  ajenas a DDoS. Mismo patrón "dos decisiones razonables por separado, colectivamente
  incoherentes" de grieta A, ahora en el **cableado de alimentación**, no en el orden de
  features. **CAVEAT obligado en paper:** la feature solo lleva señal viva si la ruta
  ransomware está construida y alimentando.
- **El patrón GENERALIZA:** `get_window_stats` aparece en ~12 features DDoS de
  `ml_defender_features.cpp` (líneas 68, 375, 411, 433, 446, 498, 507, 552, 565…) → la
  dependencia de la ventana (y el acople con ransomware) afecta a toda la familia que
  sale del aggregator, no solo a `source_ip_dispersion`.

## 3. Granularidad del evento (casi cerrado)

- `ring_consumer.cpp:621` = `ransomware_processor_->process_packet(event)` alimenta el
  aggregator. Nombre `process_packet` + `tw_event` sellado con `bytes = event.packet_len`
  (`ransomware_feature_processor.cpp:121-129`, `packet_len` es campo por-paquete) ⇒
  **EVENTO = PAQUETE**, no flujo. Descartada la hipótesis previa "evento = flujo".
- La LECTURA DDoS cuelga de flujo: `process_event_features` (`ring_consumer.cpp:642+`)
  hace `ShardedFlowManager::get_flow_stats_copy(flow_key)` y extrae sobre
  `FlowStatistics` (`:819+`). Cuadro final: **aggregator alimentado por paquete, feature
  leída por flujo.**
- **RESIDUAL sin ojear (SOSPECHADO, no HECHO):** confirmar que `process_packet` se llama
  1×/paquete en el mismo dispatch (ver `ring_consumer.cpp` 615-645). Solo importa si el
  factor paquetes/flujo se vuelve load-bearing.

## 4. Plan del análogo offline sobre CICDDoS2019 (pendiente de construir)

- Por cada flujo a `t` (su `Timestamp` de fin): ventana global
  `[t-30s, t] ∩ últimos 10000 eventos`, meter `Source IP ∪ Destination IP` en un set
  (`uniq`), `event_count` = eventos en ventana, aplicar
  `min(log2(uniq+1)/log2(ev+2), 1)`.
- Serve cuenta eventos por PAQUETE; un CSV es por-flujo → expandir cada fila a sus
  `Total Fwd + Bwd Packets` para que `event_count` case, o declarar sesgo acotado.
- **Parser de fecha OBLIGATORIO explícito:**
  `pd.to_datetime(col, format='%Y-%d-%m %H:%M:%S.%f')` (pandas por defecto asume mes-día
  e invertiría fechas como `2018-12-05`).
- Test de "misma distribución" offline vs serve: KS, o histogramas + percentiles. El
  número decide la horquilla.
- **Horquilla de decisión (DAY263):** (a) replicar la ventana offline / (b) sacarla del
  contrato train+serve como se hizo con geo — PERO geo no la comía el modelo y esta SÍ
  (cuidado) / (c) reformular como función del flujo — **casi MUERTA por construcción**:
  una dispersión necesita un conjunto y un flujo tiene 1 IP origen. Fork vivo = (a) vs
  (b). Consejo de Sabios + paper.
- **Asimetría a ETIQUETAR (Consejo/paper):** cada CSV de CICDDoS2019 es un ataque casi
  puro (p.ej. `Portmap` = 186960 ataque / 4734 benigno) → el offline es "ventana dentro
  de un ataque puro", no "ventana de producción mezclada". Válido para comparar la FORMA
  del sentinel-vs-vivo, pero no es el régimen de serve.

## 5. Dataset CICDDoS2019 — VALIDADO y caracterizado (reusable para el paso 2 "las 9")

- **Ubicación:** `ml-training/datasets/CICDDoS2019/` (descargado de cicresearch.ca).
  Estructura: `01-12/` (día ENTRENAMIENTO, 12 ataques, 11 CSV, ~22 GB, **50 063 112
  filas**) + `03-11/` (día TEST, 7 ataques, 7 CSV, ~8.7 GB, **20 364 525 filas**).
  Recuentos cuadran fila a fila con lo publicado por CIC (`wc -l` menos cabeceras).
- WebDDoS NO es fichero propio (~439 paquetes embebidos en otro CSV; las fuentes
  discrepan UDPLag vs DrDoS_UDP → localizar por la columna `Label` si importa).
  PortScan/Portmap solo en test (ataque no visto en train, a propósito).
- 88 columnas CICFlowMeter-V3, mismo hash de cabecera `46e0bdae` en los 18 ficheros.
  Col 1 `Unnamed: 0` = índice pandas (tirar). Col 63 `Fwd Header Length.1` = duplicado
  de la 42 (bug CICFlowMeter). Col 86 `SimillarHTTP` (errata) suele venir vacía.
- Columnas que grieta B necesita, presentes: 3 `Source IP`, 5 `Destination IP`,
  8 `Timestamp`, 7 `Protocol`, 2 `Flow ID` (5-tupla ya lista). OJO nombres con espacio de
  relleno a la izquierda.
- **Timestamp:** formato ÚNICO en los 18 = `AAAA-DD-MM HH:MM:SS.ffffff` (24h, µs). Es
  día-mes (mes=12 en 01-12, mes=03 en 03-11). El año dice 2018 (desfase conocido de la
  captura, irrelevante para ventanear).
- `Infinity`/`NaN` confinados a cols 22-23 (`Flow Bytes/s`, `Flow Packets/s`) en flujos
  con `Flow Duration = 0` (n/0). El guard del loader debe esperarlos ahí; no contaminan
  las columnas de grieta B.
- **Categorías (para interpretar la dispersión):** reflexión (MSSQL, SSDP, NTP, TFTP,
  DNS, LDAP, NetBIOS, SNMP) → origen = reflectores (muchos); explotación (SYN, UDP,
  UDP-lag) → origen a menudo spoofeado. Ambas empujan la dispersión arriba por motivos
  distintos; como el estadístico serve cuenta origen∪destino, el spoofing de origen no lo
  domina solo.
- Col 74 `Init_Win_bytes_forward` presente → este dataset sirve para medir el skew P0 del
  level1 (hardcodeado a `0.0f` en serve, no está en el protobuf `NetworkFeatures`) cuando
  le toque a level1. NO es la batalla DDoS.

## 6. Deudas / higiene afloradas (BACKLOG, no hoy)

- `sniffer/src/userspace/ml_defender_features.cpp.bak.day79` está TRACKEADO (ensucia
  cada `git grep`). Higiene: `git rm` cuando toque.
- Dos formas de contar IPs conviven en `TimeWindowAggregator`: la global src∪dst
  (`cpp:60-61`, la que come grieta B) y la selectiva `count_unique_ips` (`cpp:445`, con
  flag `true` = solo destino, usada p.ej. por SMB diversity en `:240`). No mezclar; para
  grieta B manda 60-61.