# Apoyo para el paper — base de tiempo única (DAY295)

Material para la sección de método/limitaciones. Todo medido el 2026-10-12 en el lab (VirtualBox sobre macOS).

1. Un único campo de tiempo con dos bases. event_timestamp (google.protobuf.Timestamp, semántica epoch) llevaba
   CLOCK_MONOTONIC del kernel (bpf_ktime_get_ns) en flujos y fast-alert, y epoch (system_clock) en las ventanas de
   ransomware y en la variante libpcap. Consecuencias observadas antes de esta rama: el reloj de la sombra del firewall
   se congeló (DAY293) y un día de Parquet tuvo el 99 % de filas en monotónico (DAY294). Además flow_start_time, que va
   al bronce correlation_v1 y al grafo, iba en monotónico mientras Suricata y Zeek van en epoch.

2. Suspender el anfitrión congela las VMs. REALTIME, MONOTONIC y BOOTTIME pierden exactamente lo mismo (BOOTTIME -
   MONOTONIC cambió 0,000000 s): en una VM no se puede distinguir MONOTONIC de BOOTTIME.

3. La corrección gradual de NTP también acelera el reloj monotónico. Tras despertar, chrony corrigió 257 s
   gradualmente: CLOCK_MONOTONIC y CLOCK_REALTIME corrieron +81300 ppm (8,1 %) frente a CLOCK_MONOTONIC_RAW durante
   unos 45 min. REALTIME - MONOTONIC no cambió: el desvío es invisible para quien compara pared y monotónico; solo lo
   delata MONOTONIC_RAW. Un hold de 30 s habría durado 27,7 s reales. En reposo, MONOTONIC frente a RAW = -1876 ppm
   (corrección de frecuencia de chrony, constante). Un salto forzado (chronyc makestep) movió REALTIME +208,878 s sin
   tocar MONOTONIC ni BOOTTIME.

4. Un servidor chrony sirve su hora corregida, no la de su reloj: el client saltó a la hora real 4 min antes que el
   propio defender. Durante ~4 min las dos VMs discreparon en 210-230 s. Cualquier medida que cruzara horas del client
   (inicio del ataque) con eventos del defender habría salido mal.

5. Lección de diseño: una sola base interna (CLOCK_MONOTONIC, compartida por bpf_ktime_get_ns y steady_clock:
   diferencia medida 56 ns), epoch solo en los bordes (mono + ancla por nodo), detección de saltos por cambio de
   REALTIME - MONOTONIC y detección de corrección gradual por MONOTONIC frente a MONOTONIC_RAW. Cada evento lleva
   boot_id, secuencia por productor, ancla y estado del reloj, para poder auditarlo después.

6. La política por víctima del firewall cuenta ventanas de 1 s: el hold está cuantizado por diseño (FIN a 29,3 s con
   hold de 30 ventanas en DAY294). El criterio honesto es "30 ventanas, inmune a saltos del reloj de pared", no
   "30,0 +- 0,1 s".

7. Retraso sniffer -> firewall con el pipeline en reposo (mismo nodo, mismo boot_id): media 12-26 ms, máximo 22-90 ms
   por periodo de 10 s. Línea base para explicar el reloj de eventos al 0,55x bajo carga DNS (DAY294).

Limitación a declarar: todo esto es un lab virtualizado; en hardware real no hay congelación por suspensión del
anfitrión y la elección MONOTONIC/BOOTTIME solo importaría si se suspende el nodo del pipeline.
