# CONTINUIDAD DAY273 → DAY274 — agregador DDoS por víctima en el kernel (eBPF/XDP)

Rama de trabajo: `docs/ml-heads-grieta-b`. Principios: "medir, no votar" · Via Appia Quality.
Sole developer: Alonso. C++20, flags `-std=c++20 -Wall -Wextra -Wpedantic -Werror`.

## 1. Estado en una frase

El contador por víctima dentro del kernel está construido, verificado en el kernel real 6.1 y medido E2E
a 100 pps: cuenta exacto y no pierde nada entre el contador y el ring. **NO detecta ataques todavía**:
es la capa de medición sobre la que se ajustará la fórmula de `escalation` (Paso 4).

## 2. Decisiones fijas (no reabrir)

- (a) Clave = `dst_ip + protocolo`; mapa `LRU_HASH` de 65536 entradas.
- (b) El kernel cuenta de forma monótona por víctima. Userspace lee cada T segundos y
  `delta = ventana tumbling`. Sin lógica de ventana, reset, float ni división en el kernel.
- (c) Se cuentan paquetes Y bytes.

## 3. Qué existe (evidencia)

Mapa `ddos_victims`: key `{u32 dst_ip; u32 proto}` (8 B), value `{u64 pkts; u64 bytes}` (16 B), max 65536.
`dst_ip` es el valor numérico `a<<24|b<<16|c<<8|d` (192.168.100.1 = 3232261121 = 0xC0A86401).
El bloque de conteo va tras el chequeo IPv4 y antes de `bpf_ringbuf_reserve`. Altas nuevas con
`bpf_map_update_elem(..., BPF_NOEXIST)` + nueva búsqueda; contadores con `__sync_fetch_and_add`.

Ficheros en el commit de la rama:
- `sniffer/src/kernel/sniffer.bpf.c` (parche `patch_ddos_kernel_agg.py`, marcadores `DDOS-KAGG-D273:*`)
- `sniffer/include/ddos_kernel_agg.hpp` — `sniffer::DdosKernelAggregator` (header-only, `poll()`, `compute_delta` puro,
  lectura por `bpf_map_lookup_batch`)
- `sniffer/tests/test_ddos_kernel_agg.cpp` — tests puros + modo `--bpf <obj>` con `BPF_PROG_TEST_RUN`
- `sniffer/CMakeLists.txt` y `Makefile` (parche `patch_ddos_build_wiring.py` v2)

Verificado:
- El verificador de 6.1 acepta el programa; el `.bpf.o` recompilado contiene el mapa; el sniffer en ejecución lo tiene
  (`lru_hash`, key 8, value 16, max 65536).
- `make sniffer-ddos-agg-test` (ctest, sin root, entra en `make test-components`): Passed bajo `-Werror`.
- `make sniffer-ddos-agg-bpf-test` (root): OK; ventana de 5000 paquetes → `d_pkts=5000 d_bytes=2410000`.

## 4. Medición E2E (DAY273) — números

Replay de `datasets/cicddos2019/_0125_50k_lab.pcap` a `--pps=100` (499.99 s, 50000 paquetes, 23 999 270 B)
desde la VM `client` hacia la `defender` (XDP generic en eth1 y eth2, kernel 6.1.0-53, Debian bookworm).

| Magnitud | Valor |
|---|---|
| Víctima 192.168.100.1/UDP, delta | +49 997 pkts, +23 998 186 B |
| Víctima 192.168.100.1/ICMP, delta (clave nueva) | +2 pkts, +1 020 B |
| Total víctima | 49 999 pkts, 23 999 206 B |
| Enviado por tcpreplay | 50 000 pkts, 23 999 270 B |
| No contado | 1 paquete, 64 B (hipótesis: trama no IPv4; SIN VERIFICAR) |
| Delta `stats[0]` (eventos al ring) | 50 599 |
| Suma de deltas de todo el mapa | 50 599 (A−B = 0: sin pérdida kernel→ring a 100 pps) |
| Prueba corta (500 pkts) | 500 pkts y 239 848 B, idénticos a lo enviado |
| Detector: líneas de flujo UDP a la víctima | 790 (flujos, NO paquetes; pcap 766 + 17 de la prueba corta) |

## 5. Trampas de entorno (leer antes de ejecutar nada)

- `make`, `patch_*.py` y `git` corren en el **Mac**. `readelf`, `bpftool` (necesita `sudo`), `pgrep`, `tcpreplay` y
  `g++` con libbpf corren en las **VMs**. En la VM no existe `vagrant`; el Mac no tiene eBPF ni libbpf.
- El replay se lanza desde la VM **`client`** (`vagrant ssh client`). Lanzarlo desde `defender` da A=0: los paquetes
  salen por TX y nunca pasan por el hook XDP de RX. (Error real cometido en DAY273.)
- El XDP está en **eth1 y eth2**. Al comparar contadores de interfaz mirar las dos (el tráfico del cliente entra por eth2).
- `BPF_PROG_TEST_RUN` sin contexto entrega los paquetes como recibidos por `lo` (ifindex 1): hay que poblar
  `iface_configs[if_nametoindex("lo")]` y `filter_settings` (default 0 = DROP), o el programa sale sin contar.
- El sniffer carga `sniffer.bpf.o` por ruta relativa (cwd `/vagrant/sniffer/build-debug`); el binario no lo embebe.
- `cmake --build --target <nuevo>` no reconfigura: las recetas ejecutan `cmake .` antes.
- `LIBBPF_OPTS` usa extensiones GNU y falla con `-Wpedantic -Werror` en C++: struct explícito.
- Un `grep "192.168.100.1"` casa también con `.10`/`.11`/`.12`. Usar regex anclada.
- Snapshot ANTES/DESPUÉS con un solo comando (`/tmp/snap.sh`: fecha, `ip -s link` eth1/eth2, `bpftool -j map dump`
  de `stats` y `ddos_victims`) para evitar desfases entre mapas.
- Preferencias de trabajo: `git grep`, nunca `grep -rn` en la raíz; comandos de salida grande por separado o a fichero;
  los ficheros generados por Claude los ejecuta Alonso en su VM.

## 6. Pendiente, en orden

1. Verificar la hipótesis de la trama de 64 B: `tcpdump -nr datasets/cicddos2019/_0125_50k_lab.pcap not ip -c 5`
   y contar ICMP del pcap. Cierra el cabo suelto antes de publicar.
2. Aplicar `patch_ebpf_loader_ddos.py` (NO aplicado; solo verificado su `--dry`). Comprobar apply, idempotencia y
   caminos de fallo. Requiere `sniffer/include/ddos_kernel_agg.hpp` presente.
3. Hilo lector en el proceso del sniffer que llame a `poll()` cada T.
4. Repetir el E2E a más pps: ahí A−B puede dejar de ser 0 y la confusión de DAY272 se hace visible. Probar también
   la carrera multi-CPU de la inserción `BPF_NOEXIST` (solo un flood real la muestra).
5. Paso 4: harness de ajuste de fórmula para `escalation` (tumbling vs EWMA por shift) sobre los conteos limpios.
6. Restos en la rama: `join_flood_escalation*.py`, `profile_flood_pcap.py` (sin trackear).

## 7. Lo que NO está demostrado

- Ninguna detección: no se ha medido cuántos ataques marca el detector con esta capa.
- Comportamiento por encima de 100 pps y con el ring saturado.
- Carrera multi-CPU en el alta de víctimas nuevas.
- XDP en modo nativo (todo se ha medido en generic/SKB sobre VirtualBox).
- Un solo pcap (un corte de CICDDoS2019).

## 8. Prompt de arranque para la próxima sesión

> Continuamos DAY274 de aRGus NDR (C++20, rama `docs/ml-heads-grieta-b`). Lee `CONTINUIDAD_DAY273_a_274.md`.
> Estado: el agregador por víctima en kernel (`ddos_victims`, LRU_HASH 65536, key dst_ip+proto, contadores monótonos
> pkts+bytes) está verificado y medido a 100 pps (49 999/50 000 paquetes IPv4 contados, A−B=0). No detecta nada aún.
> Empieza por el punto 1 del pendiente (tcpdump de la trama no IPv4) y luego el punto 2 (aplicar el patcher del loader).
> Reglas: comandos separados, `git grep`, los ficheros los ejecuto yo en la VM Vagrant, make/git en el Mac.