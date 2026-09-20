# CONTINUIDAD DAY274 → DAY275

Rama `docs/ml-heads-grieta-b`. Principios: "medir, no votar" / Via Appia Quality.
Tema: agregador DDoS por víctima en el kernel (eBPF/XDP) y su lector en el sniffer.

## 1. Estado al cerrar DAY274

Hecho y verificado:

- **Punto 1 (cerrado):** el frame que no cuenta el kernel es un PVST+ de Cisco (SNAP/802.3, 64 B, no IPv4). Está en la posición 1066 del pcap; los 2 ICMP en la 6730 y 6731 (posiciones reales del fichero, no los números `-#` de tcpdump con filtro). No existe un "paquete nº 1".
- **Punto 2 (cerrado):** `patch_ebpf_loader_ddos.py` aplicado, commit `0e5fc58d`. El loader encuentra el mapa `ddos_victims` (FD 5, max 65536, layout 8 B/16 B comprobado).
- **Punto 3 (hecho, sin commit del usuario aún salvo comprobación):** `patch_ddos_reader.py` crea `sniffer/include/ddos_kernel_reader.hpp` y `sniffer/tests/test_ddos_kernel_reader.cpp`, y toca `config_manager.*`, `config_types.*`, `main.cpp` y `sniffer/config/sniffer.json`. Compilado con `-Werror` (solo build-debug verificado), test unitario pasado, apagado limpio verificado con SIGINT (reader parado antes de borrar el loader).
- **Cableado del test (hecho):** `patch_ddos_reader_wiring.py` añade el bloque CMake y el target `make sniffer-ddos-reader-test`. Pasa desde la VM (ctest) y desde el Mac.
- **`snap_ddos.sh`** (commit `96052bd4`) y **`snap_delta.py`** (nuevo, calibrado al byte con la pareja `antes1070/despues1070`).

Commits pendientes del usuario (comprobar con `git status --short`):

1. Lector: `patch_ddos_reader.py`, `ddos_kernel_reader.hpp`, `test_ddos_kernel_reader.cpp`, `config_manager.hpp`, `config_types.h`, `config_manager.cpp`, `config_types.cpp`, `main.cpp`, `sniffer.json`. El patcher salía como `AM`: hay que hacer `git add` otra vez.
2. Cableado: `patch_ddos_reader_wiring.py`, `Makefile`, `sniffer/CMakeLists.txt`.
3. `snap_delta.py` (renombrar antes si sigue con espacio final: `mv "snap_delta.py " snap_delta.py`).

## 2. Evidencia medida en DAY274

Todas las corridas: replay desde `client` (hostname `ml-client`, `--intf1=eth1`), XDP genérico (SKB) en eth1/eth2 de `defender`, pcap `_0125_50k_lab.pcap` (50.000 pkts / 23.999.270 B = 49.997 UDP + 2 ICMP + 1 PVST+).

| Corrida | eth2 RX | mapa (suma) | `.1/17` (pkts / B) | `stats[0]` | A−B | cable − mapa |
|---|---|---|---|---|---|---|
| 1070 pkts (ritmo bajo) | +1100 | +1099 / 518.118 B | +1069 / 512.810 | +1099 | 0 | +2 pkts / +106 B |
| 5000 pkts @ 100 pps (50 s) | +5064 | +5059 / 2.398.202 B | +4999 / 2.389.358 | +5059 | **0** | +9 / +465 B |
| 5000 pkts @ 1000 pps (5 s) | +5031 | +5032 / 2.394.502 B | +4999 / 2.389.358 | **+2320** | **−2712** | +4 / +432 B |
| pcap completo @ 1000 pps (ventana 326 s) | +46.595 | +46.602 / 22.235.868 B | +46.221 / 22.181.682 | **+4788** | **−41.814** | +19 / +1.347 B |

- tcpreplay de las dos corridas de 5000: 5000 pkts / 2.389.422 B, `Failed packets: 0`, 0 reintentos. Enviado − contado en `.1/17` = 1 pkt / 64 B (el PVST+), en ambas.
- Corrida completa: la suma del CSV con `ts_ms >= T0` coincide con el delta de `.1/17` (46.221 pkts / 22.181.682 B). El lector escribe exactamente lo que cuenta el kernel.
- **Falta la línea `Actual:` de tcpreplay de la corrida completa**: no se guardó.

## 3. Hallazgos y decisiones

1. **A−B no es "pérdida del ring" a secas.** `stats[0]` se incrementa al final del camino (línea ~414 de `sniffer/src/kernel/sniffer.bpf.c`), después del `bpf_ringbuf_reserve` y de los filtros de puerto. Lo que no incrementa: `reserve` fallido (`return XDP_PASS` sin contador) y los seis `bpf_ringbuf_discard` (puerto origen/destino no capturable, cabecera L4 truncada). El mapa `ddos_victims` se cuenta antes del `reserve` (marcador `DDOS-KAGG-D273:COUNT`), independiente de ring y filtros.
2. **En esta configuración A−B ≈ eventos que no llegan al ring por saturación.** `sniffer.json`: `excluded_ports: [22]`, `included_ports: []`, `default_action: capture`. Los descartes por filtro son despreciables. El test A/B con los mismos 5000 paquetes lo demuestra: A−B = 0 a 100 pps y −2712 a 1000 pps. Como el contenido es idéntico, la causa depende de la tasa; el único camino del código que depende de la tasa es el `reserve` fallido (ring lleno). Conclusión por eliminación de caminos de código; no se ha instrumentado el `reserve` fallido directamente.
3. **El agregador en el kernel resiste lo que el ring no.** A 1000 pps el mapa contó 4999/4999 UDP y 2.389.358 B exactos mientras al ring llegaba el 46 % de los eventos (2320 de 5032; en la corrida larga solo el 10,3 %: 4788 de 46.602). El mapa no perdió nada.
4. **Consecuencia abierta para aRGus (medida solo en este laboratorio):** en el build debug, con `FORCE_ALL_HEADS=1`, VirtualBox y XDP genérico, el camino ring → consumidor userspace → cabezas ML satura a 1000 pps y ve una fracción del tráfico. **Confirma lo ya medido en DAY270** (ring ~14 % a 1000 pps, ~95 % a 100 pps; aquí 46 % en ráfaga de 5 s y 10,3 % en la corrida larga; el filtro de puertos ya se había descartado entonces como causa). Novedad de DAY274: el contador del kernel no se ve afectado. No sabemos aún si el cuello es el tamaño del ring, el ritmo del consumidor o el build -O0.
5. **Sobre el pcap:** unos 250 flujos de 200 paquetes; los primeros pares (src, dst) vistos tienen puerto origen 800–999 y destino alto aleatorio. Los primeros ~1070 paquetes pasan todos por el filtro.
6. **Los 3.777 paquetes que faltan en la corrida completa siguen sin explicar.** eth2 recibió +46.595 y el pcap tiene 50.000. `missed` = 0 y `dropped` = +1 (el PVST+), así que la pérdida ocurre antes de la NIC de `defender` o tcpreplay no terminó. Las dos corridas de 5000 llegaron completas, luego a 1000 pps no hay pérdida sistemática en el envío. Hipótesis sin comprobar: envío interrumpido o incompleto.
7. Otras decisiones vigentes: el lector nace desactivado en código y activado en `sniffer.json`; ventana tumbling en userspace = delta entre lecturas; usar `d_pkts / window_ms` (jitter ±5 %); la fila `window_ms=0` es el baseline (filtrar en el harness); el CSV es append con flush por ventana.

## 4. Trampas de entorno

- Descargar ficheros puede dejar un espacio final en el nombre (`snap_delta.py `). Comprobar con `ls -l` antes de ejecutar en la VM.
- `pgrep -a sniffer` vacío = sniffer caído. Comprobarlo antes de cada foto ANTES. Arranque: `make pipeline-start VERBOSE=1 FORCE_ALL_HEADS=1` (Mac).
- `make pipeline-stop` mata el sniffer sin pasar por el cleanup (se pierden <1 s de cola; el CSV se vuelca por ventana). Parada limpia: `sudo kill -INT $(pgrep -x sniffer)`.
- El log `/vagrant/logs/lab/sniffer.log` pesa ~80 MB (más de 1,78 M líneas): nunca `cat`, solo `grep | tail`.
- El Mac no tiene libbpf: los patchers con compilación se ejecutan en la VM `defender`. Los patchers exigen `--dry`, `--apply` o `--check`; nunca commitean.
- El build sniffer usa `-Werror` (`flags.make`); solo se ha verificado build-debug (-O0).
- El replay se lanza solo desde `client`; el tráfico entra por eth2 de `defender`. bpftool y `snap_ddos.sh` necesitan `sudo`.
- Comandos de uno en uno; salidas grandes a fichero; `git grep`, nunca `grep -rn` desde la raíz.

## 5. Procedimiento de medida (E2E con `snap_delta.py`)

1. `defender`: `sudo bash /vagrant/snap_ddos.sh > ~/antes_X.txt`
2. `client`: `sudo tcpreplay --pps=N [--limit=M] --intf1=eth1 /vagrant/datasets/cicddos2019/_0125_50k_lab.pcap 2>&1 | tee ~/tcpreplay_X.txt` (guardar la salida).
3. `defender`: `sudo bash /vagrant/snap_ddos.sh > ~/despues_X.txt`
4. `defender`: `python3 /vagrant/snap_delta.py ~/antes_X.txt ~/despues_X.txt --sent PKTS BYTES`
5. Cruce con el CSV: `T0=$(head -1 ~/antes_X.txt | cut -d. -f1)000`, luego `awk -F, -v t0=$T0 '$2>=t0 && $4=="192.168.100.1" && $5==17 {p+=$6;b+=$7} END{print p+0,b+0}' /vagrant/logs/lab/ddos_windows.csv` (esperar un par de segundos tras la foto DESPUÉS).

## 6. Pendiente, en orden propuesto

1. Comprobar `git status --short` y hacer los tres commits de la sección 1.
2. **Repetir el pcap completo a 1000 pps guardando la salida de tcpreplay** para explicar los 3.777 paquetes. Esperado si todo va bien: `.1/17` = 49.997, ICMP = 2, no contado = 1 pkt / 64 B.
3. **Cuantificar la pérdida del ring.** Antes de tocar el BPF, mirar la definición del mapa `stats` (sniffer.bpf.c ~línea 152, `max_entries`) y decidir cómo contar el `reserve` fallido por separado (otra clave de `stats` o mapa nuevo). Con eso, A−B se descompone en `reserve` fallido y descartes por filtro. Medir también el ritmo real del consumidor y el tamaño del ring.
4. **Subir la tasa** (5000, 10000, `--topspeed`) para comprobar que el contador del kernel sigue exacto y ver hasta dónde llega eth2 sin `missed`/`dropped`. La carrera con varios CPU en los `BPF_NOEXIST` es difícil de reproducir con una sola cola en VirtualBox.
5. **Paso 4:** harness para la fórmula de `escalation` (tumbling frente a EWMA por shift) sobre el CSV, con tasas `d_pkts/window_ms` y sin las filas `window_ms=0`.
6. Actualizar los documentos de continuidad anteriores: punto 1 cerrado, puntos 2 y 3 hechos, los ficheros `join_flood_escalation*.py` y `profile_flood_pcap.py` ya no están sin trackear.
7. Opcional: `make test-components > /tmp/test-components.log 2>&1` y `grep -n test_ddos_kernel_reader /tmp/test-components.log`, para confirmar que el test entra en la batería general.

Sin probar todavía (arrastrado de DAY273): modo XDP nativo, ring saturado de forma controlada (ahora hay datos de que ya ocurre), pcap único, build release.

## 7. Prompt de arranque para DAY275

> Continuamos aRGus NDR, rama `docs/ml-heads-grieta-b`, "medir, no votar". Lee `CONTINUIDAD_DAY274_a_275.md`. Reglas: comandos de uno en uno, `git grep` (nunca `grep -rn` desde la raíz), salidas grandes a fichero, los ficheros que generas los ejecuto yo en mi VM y los commits los hago yo. Empieza por el punto 2 de la sección 6: repetir el pcap completo a 1000 pps guardando la salida de tcpreplay, con `snap_delta.py`. Después, el punto 3: cuantificar la pérdida del ring separando `reserve` fallido de descartes por filtro. Respuestas en español y concisas.