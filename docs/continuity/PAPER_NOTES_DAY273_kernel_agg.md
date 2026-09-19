# Notas para el paper — agregación por víctima en el kernel (DAY273)

Estado: material para una sección/apéndice de aRGus NDR (arXiv:2604.04952) y para el post técnico.
Regla de redacción: solo afirmar lo medido; los límites van en el mismo párrafo que la afirmación.

## 1. Claim candidato (una frase, con cautela)

Contar tráfico por víctima dentro del kernel, antes del ring buffer, da una señal de entrada para la cabeza DDoS que
no depende de que el userspace consuma a tiempo; a 100 pps el conteo fue exacto sobre IPv4 y no hubo pérdida
entre el contador y el ring.

## 2. Motivación (el confound de DAY272)

Cuando las características de detección se calculan en userspace a partir de eventos del ring buffer, cualquier pérdida
del ring sesga en silencio justo la señal que se quiere evaluar. No se puede separar "el detector falló" de
"el paquete nunca llegó al detector". La medición de DAY272 estaba confundida por eso.

## 3. Diseño

- Programa XDP `xdp_sniffer_enhanced`; bloque de conteo tras el chequeo IPv4 y antes de `bpf_ringbuf_reserve`.
- Mapa `LRU_HASH`, 65 536 entradas; clave `(dst_ip, proto)` = 8 B; valor `(pkts, bytes)` = 16 B.
- Contadores monótonos con `__sync_fetch_and_add`; alta con `BPF_NOEXIST` + relectura.
- Sin ventanas, resets, float ni división en el kernel. Userspace lee por `bpf_map_lookup_batch` cada T y la ventana
  tumbling es el delta entre lecturas (contadores que retroceden = reinserción tras desalojo; se detectan y se tratan).
- El desalojo LRU (de 128 en 128) es benigno para una víctima bajo flood: es la entrada más caliente.

## 4. Método

- Entorno: VM Debian bookworm, kernel 6.1.0-53, XDP generic (SKB) en eth1 y eth2 sobre VirtualBox; libbpf 1.4.6.
- Tráfico: `tcpreplay --pps=100` de `_0125_50k_lab.pcap` (corte de CICDDoS2019, 50 000 paquetes, 23 999 270 B,
  499.99 s) desde una VM cliente.
- Medida: snapshot antes/después con un solo comando (mapas `stats` y `ddos_victims`, contadores de interfaz).
- Tests previos: `BPF_PROG_TEST_RUN` con 5000 paquetes → `d_pkts=5000`, `d_bytes=2 410 000`; el verificador de 6.1 acepta el programa.

## 5. Resultados

| Magnitud | Valor |
|---|---|
| Víctima 192.168.100.1/UDP | +49 997 pkts, +23 998 186 B |
| Víctima 192.168.100.1/ICMP | +2 pkts, +1 020 B |
| Total víctima | 49 999 pkts, 23 999 206 B |
| Enviado | 50 000 pkts, 23 999 270 B |
| Diferencia | 1 paquete, 64 B (hipótesis: trama no IPv4; pendiente de verificar con tcpdump) |
| Delta `stats[0]` (eventos al ring) | 50 599 |
| Suma de deltas del mapa | 50 599 → pérdida kernel→ring = 0 a 100 pps |
| Prueba corta | 500 pkts y 239 848 B, idénticos a lo enviado |

El total del mapa incluye tráfico de fondo (Wazuh, DNS, mDNS): 662 paquetes en unos 11 minutos en el primer intento,
en el que el replay no llegó a la NIC de entrada (ver sección 6). Da una idea de la línea base.

## 6. Dos falsos negativos de medición (material metodológico)

Ambos produjeron "0 paquetes" y ambos eran errores del experimento, no del código. Encajan con "medir, no votar":
un 0 medido correctamente sobre lo equivocado sigue siendo un 0 inválido.
1. `BPF_PROG_TEST_RUN` sin contexto entrega los paquetes como recibidos por `lo`; sin entrada en `iface_configs` para
   ese ifindex el programa sale antes de contar. Se detectó porque `stats[0]` también era 0.
2. El primer replay se lanzó desde la propia VM defensora: los paquetes salen por TX y no atraviesan el hook XDP de RX
   (`ip -s link` mostró TX +50 017 y RX casi sin cambio). Se detectó con `pgrep` y con los contadores de interfaz.

## 7. Amenazas a la validez / límites

- Una sola tasa (100 pps): es el régimen donde el ring no pierde; no se ha mostrado el caso con pérdida.
- La carrera multi-CPU del alta con `BPF_NOEXIST` no se ha ejercitado: 100 pps no genera concurrencia real y
  `BPF_PROG_TEST_RUN` corre en una CPU.
- XDP generic sobre VirtualBox, no nativo; un solo pcap.
- El contador cuenta también paquetes que el filtro de puertos descartaría: mide "llegó a la NIC como IPv4", no "se capturó".
- La trama de 64 B no contada y los 2 ICMP no se han verificado contra el pcap.
- El número C del detector (790 líneas de flujo) es de flujos, no de paquetes; no mide pérdida aguas abajo.
- No hay resultado de detección: esto es la capa de medición, no el detector.

## 8. Qué habilita

El Paso 4: ajustar la fórmula de `escalation` (ventana tumbling frente a EWMA por shift) sobre conteos limpios y
comprobar cuánto cambia el resultado cuando el ring pierde (a más pps).

## 9. Reproducibilidad

- Test puro: `make sniffer-ddos-agg-test` (Mac). Integración contra el kernel real: `make sniffer-ddos-agg-bpf-test` (Mac; llama a la VM, pide root).
- E2E: `/tmp/snap.sh` antes → `sudo tcpreplay --pps=100 --intf1=eth1 datasets/cicddos2019/_0125_50k_lab.pcap` en la VM `client`
  → `/tmp/snap.sh` después. Comparar deltas de `ddos_victims` y `stats[0]`.
- Revisión de cifras: todas recalculadas a partir de los volcados JSON de `bpftool` (antes/después).

## 10. Párrafo borrador (inglés, para el paper)

> To decouple detection quality from userspace consumption, we moved per-victim accounting into the XDP program,
> upstream of the ring buffer. A `BPF_MAP_TYPE_LRU_HASH` keyed by `(dst_ip, proto)` holds monotonic packet and byte
> counters; userspace samples the map every T seconds and takes the difference between samples as a tumbling window,
> so the kernel side needs no windowing, resets, floating point or division. Replaying a 50,000-packet CICDDoS2019
> slice at 100 pps, the kernel counted 49,999 IPv4 packets (23,999,206 B) for the victim against 50,000 packets
> (23,999,270 B) sent; the single unaccounted 64-byte frame is consistent with a non-IPv4 frame [to be verified].
> The number of events submitted to the ring buffer equalled the sum of the per-victim counters (50,599), i.e. no
> loss between counter and ring at this rate. We have not yet evaluated higher rates, multi-CPU insertion races, or
> native-mode XDP, and no detection result is claimed here: this layer provides the loss-independent input on which
> the escalation formula will be fitted.

## 11. Figura/tabla sugerida

Una tabla "enviado vs contado en kernel vs entrado al ring" a 100 pps, y (cuando exista) la misma a 1×, 10× y 50× de
esa tasa, donde A−B debería dejar de ser 0. Es la figura que responde al confound de DAY272.

## 12. Antes de publicar

1. `tcpdump -nr datasets/cicddos2019/_0125_50k_lab.pcap not ip -c 5` y contar ICMP: cierra las dos incógnitas de la sección 7.
2. Repetir a más pps (punto 4 de la continuidad) si se quiere afirmar algo sobre pérdida.