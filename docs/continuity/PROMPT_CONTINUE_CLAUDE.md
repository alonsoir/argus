# Prompt de continuidad — aRGus NDR, DAY290 → DAY291

Reglas de trabajo (sin cambios): medir, no votar; predicción escrita antes de medir; si algo no da lo
esperado, PARAR. Comandos separados o cada salida a su fichero; nunca `grep -rn` desde la raíz (`git grep`
o el fichero concreto); scripts como bloque `cat > f <<'EOF'`; `LC_ALL=C` en todo awk con aritmética;
`set -e` sin `pipefail` junto a `| head`. Comandos EXACTOS y COMPLETOS, en orden, diciendo dónde va cada
uno (Mac / defender / client). Patchers atómicos, todo-o-nada, con `--check` / `--apply` y marca.
Configuración: el JSON es la ley (campo obligatorio ausente, mal formado o fuera de rango ⇒ el proceso NO
arranca y dice campo, formato y límites; nada hardcodeado; defaults del código solo contra basura).

**NUEVO DAY290 — compilar y probar con el MISMO perfil:** `make pipeline-build PROFILE=production` y
`make test-components PROFILE=production`. `PROFILE ?= debug` en el Makefile: sin `PROFILE`, los tests
corren sobre `build-debug` (binario viejo) y el "100 % passed" no prueba nada.

**Foco único: la cabeza DDoS.** Orden: (1) observabilidad ✅, (2) contrato v2 ✅, (3) reentrenar y medir
[provisional DAY289; falta regenerar dataset en régimen CALIENTE], (4) fast-alert como entrada propia
(FUERA del firewall en este PR), (5) fusión + firewall por `final_decision` solo con la cabeza DDoS.

Operativa: targets del Makefile en el **Mac**; scripts en el **defender** desde `/vagrant`; tráfico en el
**client** (`eth1`, .50 → defender .1). Logs `/vagrant/logs/lab/{sniffer,ml-detector}.log` (rotar con
`sudo truncate -s 0`). Escritor de dataset: `python3 /vagrant/day289_dataset_writer.py on|off|estado`
(APAGADO). Arranque de medida: `make pipeline-start PROFILE=production FORCE_ALL_HEADS=1` +
`/vagrant/day288_esperar_estable.sh`. Medidas en segundo plano + `wait` en la misma terminal.

## 0. Estado de git
Rama `feat/ddos-head-contract`, NO mergeada. DAY290 (pusheado):
- `3d48cec0` perf(sniffer) análisis de carga solo con verbosidad BASIC+ [PAYLOAD-VERBOSE-D290]
- `54ff0006` feat(sniffer) foto determinista DDoS v2 en el hilo del anillo [DDOS-SNAP-D290]
- `5fb103f8` tools(day290) paquetes por flujo, perf por hilo, RSS
- + commit de docs de cierre DAY290 (este prompt, BACKLOG DAY290, paper_notes_day290.md)
Comprobar: `git log --oneline -6 origin/feat/ddos-head-contract`.

## 1. Lo que DAY290 dejó MEDIDO

### 1.1 Camino real del sniffer (corrige DAY289)
hilo anillo: handle_event → process_raw_event: fast alert · `add_packet` (FlowStatistics) · [análisis de
carga, ahora solo BASIC+] · plugins ×2 (DUPLICADO, `PLUGIN_LOADER_ENABLED` activo) · ransomware
`process_packet` (alimenta el agregador de ventana) · **foto DDoS v2 (nuevo)** · `add_to_batch`.
hilo rasgos: cola SIN LÍMITE → `populate_protobuf_event` (copia de FlowStatistics + pasada de ventana) →
**`run_ml_detection` (inferencia embebida EN EL SNIFFER)** → serializa → cola SIN LÍMITE → hilos ZMQ.

### 1.2 Unidad de emisión — filas por flujo (consolidado DAY289, `day290_paquetes_por_flujo.sh`)
| familia | filas | flujos | % flujos de 1 fila | reducción si 1 emisión/flujo |
|---|---|---|---|---|
| syn | 9000 | 9000 | 100 | 0 % |
| dns / ntp | 9000 | 8823 | 98,1 | 2 % |
| udpA | 8997 | 198 | 0 | 97,8 % |
| udpB | 3168 | 1581 | 0 (exactamente 2 filas/flujo, sin explicar) | 50 % |
| benigno :9000 | 9266 | 4 | 0 | 100 % |
| ambiente | 10133 | 4222 | 76,8 | 58 % |
⇒ en 3 de 5 familias emitir por flujo no reduce nada (floods de 1 paquete por flujo).
**Decisión: emisión POR PAQUETE en este PR** (revoca DAY289).

### 1.3 El cuello del anillo (perf `1000c` + `/proc`)
- Hilo de rasgos: pasada O(ventana) de `window_stats_30s` (2 `unordered_set`) bajo el mutex del
  `TimeWindowAggregator`. El hilo del anillo se BLOQUEA en `add_event` esperando ese mutex (4,2 %).
- `/proc/PID/task/*/stat` a 1000 pps (60 s, 30 s de tráfico): rasgos 75,9 % de un núcleo (≈100 % durante
  el tráfico), anillo 4,6 %, ZMQ 3,0 + 3,4 %, hilo principal 0,0 %.
- Las 9 llamadas a la ventana: 1 DDoS (`source_ip_dispersion`, FUERA del vector v2), 4 traffic, 4 internal.
  El vector DDoS v2 NO usa el agregador compartido (que es del procesador de ransomware).
- `top -H -p PID` del script DAY289 atribuye al hilo principal 41–67 % que NO existe (kernel: 0,0 %).
  `--sort tid` falla en perf 6.1 (usar `pid`). Los `perf_hilos_*` no valen.

### 1.4 Techo del anillo (`day289_anillo_medir.sh`, ntp, `--loop=3 --limit=30000`)
| corrida | binario | RESERVE_FAIL |
|---|---|---|
| 1000b | antes de la caché | 82,7 % |
| 1000c | caché D289 | 69,0 % |
| 1000d | A + C | 43,3 % |
| 1000e | A + C (mismo binario) | 28,7 % |
| 100c / 100d | — | 0 % / 0 % |
⇒ **15 puntos entre dos corridas idénticas**: cerca de la saturación, una corrida no basta para atribuir
causas. A 100 pps (tasas del dataset) cero pérdidas, dos veces. El techo real se mide en hardware real.

### 1.5 Memoria (`day290_rss_medir.sh`)
syn 5000 flujos: +11,1 MB (~2,2 kB/flujo); ntp ~9800: +16,9 MB (~1,7 kB/flujo); el RSS no baja.
Tabla acotada por LRU (16 shards × 10 000 = 160 000 flujos) ⇒ techo ~270–350 MB. `cleanup_expired_flows`
NO se llama nunca (timeout 120 s letra muerta) y es cuadrático (`list::remove`). Vectores de
FlowStatistics crecen sin límite en flujos largos; `get_flow_stats_copy` los copia en cada evento.

### 1.6 Foto determinista DDoS v2 [DDOS-SNAP-D290]
Problema medido: los rasgos se fotografiaban en el hilo de rasgos, DETRÁS de una cola sin límite ⇒ con
carga, `flow_packet_count` y `victim_*` incluían paquetes posteriores al evento (skew dependiente de la
carga). Ahora: foto en el hilo del anillo tras `add_packet` (`with_flow_stats`, sin copiar): syn_ack_ratio,
flow_completion_rate, flow_packet_count, mean_packet_size (suma incremental), packet_size_entropy
(histograma `std::map` incremental, E1) + consulta de víctima. Viaja en `QueuedEvent`; `populate`
sobrescribe antes de `run_ml_detection`; foto inválida ⇒ centinela + aviso único `[DDOS-SNAP]`.
`test_ddos_flow_snap`: **2135 comparaciones, 0 fallos, igualdad bit a bit** con `extract_ddos_features`.
En corridas: 0 avisos `[DDOS-SNAP]`.

## 2. Decisiones de Alonso DAY290
- Cada cabeza con su propio agregador/mutex SOLO si los datos lo demuestran; compartir es optimización
  prematura hasta que cada cabeza esté arreglada.
- Foto en el instante del paquete (no "leer más tarde"); entropía E1 (bit a bit).
- Emisión por paquete en este PR; emisión por víctima + agregador + techo en hardware real → BACKLOG.
- Configuración de la tabla de flujos (timeout, LRU, barrido) + auditoría de JSON (`_doc` con rango,
  formato y límites) → PR PROPIO justo después de la cabeza DDoS.
- (ii): reiniciar el sniffer antes de CADA corrida de regeneración (tabla de flujos vacía). Al llegar la
  expiración, repetir la batería y comprobar que las predicciones no cambian.
- Config inválida o ausente ⇒ el proceso no arranca (principio general).

## 3. Siguiente (DAY291): regenerar el dataset en régimen CALIENTE
Aceptado (4 puntos):
1. Línea base con la MISMA clave de víctima `{dst .1, proto}`: UDP (`bdns_small`) para familias UDP;
   TCP benigno a :9000 para SYN.
2. 90 s de línea base antes del ataque (EWMA caliente ≥30 ventanas); la línea base sigue durante el ataque.
3. Etiqueta por construcción: línea base con origen **.51** (`tcprewrite` en el client; DAY270), ataque
   desde .50. ABIERTO a resolver primero: el TCP :9000 es tráfico vivo, no pcap ⇒ alias `.51` en eth1 del
   client o pcap TCP benigno. Verificar que el kernel cuenta .51 y .50 en la misma clave.
4. Línea base 10 pps; ataques 30/60/100 pps; reinicio del sniffer por corrida.
**Piloto ANTES de la batería, con predicción:** ntp 30 pps sobre línea base 10 pps ⇒ `victim_rate_ratio`
del ataque ≈ 3–4 (régimen frío daba ≈1,2). Si sale ≈1, PARAR y revisar la EWMA caliente.
Después: familias ntp/dns/syn/udpA/udpB + contrastes bdns_small/bdns_large + pendientes (ráfaga TCP corta
legítima; UDP benigno hacia .1). Reentrenar con la batería: test, familia fuera (¿sube SYN?), tasa
reservada, sonda de victim_pps, caliente, contraste.
Puertas (no se negocian): paridad Python/C++; `.hpp` con umbrales CRUDOS (sin scaler); tamaño del bosque
medido (latencia/tamaño vs acierto); cero bloqueos en corridas benignas E2E. Luego cablear firewall por
`final_decision` (solo DDoS), medir E2E, PR, merge, etiqueta `pre-release-ddos-only-0.0.3`.

## 4. Herramientas DAY290 (raíz, commiteadas)
`day290_patch_payload_verbose.py`, `day290_patch_ddos_snap.py`, `day290_paquetes_por_flujo.sh`,
`day290_perf_por_hilo.sh`, `day290_rss_medir.sh`. Sin commitear aún: `day290_cpu_hilos.sh` (árbitro de CPU
por hilo vía /proc; sustituye al `top` del script DAY289). Evidencia (NO trackear): `/vagrant/logs/lab/day290/`
y `logs/lab/day289/anillo/*d*`, `*e*`.
