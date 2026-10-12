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
