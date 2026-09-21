# CONTINUIDAD DAY275 → DAY276

Rama `docs/ml-heads-grieta-b`. Principios: "medir, no votar" / Via Appia Quality.
Tema: pérdida del ring medida al paquete; el contador del kernel (mapa `ddos_victims`) como métrica DDoS.

## 1. Estado al cerrar DAY275

Hecho y verificado:

- **Punto 2 (cerrado):** pcap completo a 1000 pps (`_full2`). tcpreplay: 50.000 pkts / 23.999.270 B en 49,99 s, 0 fallos, 0 reintentos. `.1/17` = 49.997 pkts / 23.998.186 B; `.1/1` (ICMP) = 2 pkts; no contado = 1 pkt / 64 B (el PVST+). La suma del CSV del lector (`ts_ms >= T0`) da 49.997 / 23.998.186: el lector escribe exactamente lo que cuenta el kernel. Los 3.777 paquetes "que faltaban" en DAY274 **no se reprodujeron**: probablemente aquella corrida estuvo incompleta (no se guardó su línea `Actual:`, así que no está demostrado).
- **Punto 3 (cerrado):** `patch_ring_loss_counters.py` instrumenta `sniffer/src/kernel/sniffer.bpf.c`: `stats` pasa de 1 a 3 entradas. `stats[0]` = eventos enviados al ring (intacto), `stats[1]` = `bpf_ringbuf_reserve` fallido (ring lleno), `stats[2]` = los seis `bpf_ringbuf_discard` (puertos excluidos / L4 truncada). Verificador OK (`make sniffer-ddos-agg-bpf-test` → RESULTADO OK), build debug OK con `-Werror`. `patch_snap_delta_ring.py` extiende `snap_delta.py`: imprime s1, s2, el residuo `B − (A + s1 + s2)` y el % A/B.
- **Identidad del kernel:** `B (suma del mapa) = A (stats[0]) + s1 + s2`. Residuo = 0 en las dos corridas medidas con los contadores nuevos.
- **Capacidad del ring:** `sizeof(struct simple_event)` = 566 B (packed, calculado a mano; el BTF del objeto no traía el struct). Registro = 566 + 8 de cabecera, redondeado a 8 = 576 B. Ring `1 << 20` = 1 MiB → **1.820 eventos**.

- **Punto 4 (hecho hasta donde llega el laboratorio):** el contador del kernel es exacto respecto a lo que la NIC entrega, hasta ~5.9k pps efectivos (ver sección 2 y hallazgos 10-12). Sin probar `--topspeed`: tcpreplay en la VM no pasa de ~5.9k pps, así que no aportaría tasas mayores.

Commits hechos: `1131df9c` (`sniffer.bpf.c` + `patch_ring_loss_counters.py`) y `601048c8` (`snap_delta.py` + `patch_snap_delta_ring.py`). Pendiente de commit: este documento (colocar en `docs/continuity/`). `docs/continuity/PROMPT_CONTINUE_CLAUDE.md` aparece modificado y no es de DAY275. Trampa: los patchers se añadieron al índice vacíos (`AM`); repetir `git add` tras cualquier re-descarga.

## 2. Evidencia medida en DAY275

Todas: replay desde `client`, XDP genérico en eth1/eth2 de `defender`, pcap `_0125_50k_lab.pcap`, build debug, `FORCE_ALL_HEADS=1`, VirtualBox (6 vCPU).

| Corrida | Enviado | B (mapa) | A `stats[0]` | s1 reserve | s2 filtro | A/B | Residuo |
|---|---|---|---|---|---|---|---|
| `_full2` (sin contadores nuevos) | 50.000 @ 1000 pps | 50.318 | 7.547 | n/d | n/d | 15,0 % | n/d (A−B = −42.771) |
| `_ring1` | 50.000 @ 1000 pps | 50.124 | 6.725 | 43.399 | 0 | 13,4 % | **0** |
| `_p300` | 6.000 @ 300 pps (19,99 s) | 6.240 | 4.522 | 1.718 | 0 | 72,5 % | **0** |

| `_p5000` | 50.000 @ 5000 pps (9,99 s) | 49.423 | 2.334 | 47.089 | 0 | 4,7 % | **0** |
| `_p10000` (pedido) | 50.000 @ 5.947 pps reales (8,40 s) | 47.493 | 2.219 | 45.274 | 0 | 4,7 % | **0** |

- El contador del kernel es exacto en las tres primeras: `.1/17` = 49.997 / 23.998.186 (`_full2`, `_ring1`) y 5.999 / 2.867.902 (`_p300`). No contado = 1 pkt / 64 B (PVST+) en todas. Diferencia cable − mapa de +5 a +44 pkts: tráfico de fondo (8.8.8.8, 1.1.1.1, TCP del laboratorio).
- `_p5000`: `.1/17` = 49.368 / 23.695.008 B (faltan **629 UDP, 1,26 %** frente a lo enviado); cable − mapa = +11 pkts / +484 B (tramas de ~44 B, no IPv4); eth2 RX +49.432, `missed` 0; ICMP completo (2 pkts).
- `_p10000`: tcpreplay pidió 10.000 pps y logró **5.947** (50.000 en 8,40 s, 0 fallos). `.1/17` = 47.445 / 22.768.770 B (faltan **2.552 UDP, 5,1 %**); cable − mapa = +2 pkts / +106 B; eth2 RX +47.494, `missed` 0. TX de eth1 en el cliente: 180.432 → 230.452 = **+50.020** (50.000 + 20 de fondo): los paquetes salieron del cliente y se perdieron **antes** de que eth2 los contase.
- A 300 y 1000 pps no hay faltante frente a lo enviado.
- Hubo además un replay de 20.000 pkts @ 1000 pps lanzado solo para mirar `top` (sin fotos): no cuenta como medida.

## 3. Hallazgos y decisiones

1. **A−B = −s1 exacto.** Toda la pérdida del ring en estas corridas es `reserve` fallido. `stats[2]` = 0 durante las corridas (3 en el arranque, tráfico ajeno con puerto excluido). El hallazgo 2 de DAY274 (por eliminación de caminos) queda medido.
2. **Modelo `A ≈ 1.820 + r·T`** (r = ritmo de drenaje del consumidor): r ≈ 98–114 ev/s a 1000 pps y ≈ 135 a 300 pps. **La predicción hecha a 300 pps (A ≈ 3.800 ± 10 %) falló** (salió 4.522). El ruido entre dos corridas idénticas a 1000 pps es ~16 %. El "consumidor a ritmo constante" no se sostiene tal cual.
3. **Sniffer:** su CPU sigue al tráfico (dos hilos al ~99 % y ~91 % bajo carga, ~1 % en reposo). Hace trabajo real por evento (~7–10 ms de un hilo, inferido de reparto de CPU, no perfilado).
4. **ml-detector:** cuatro hilos al 100 % incluso ~8 min después del replay; escribe ~100 KB/s de log en nivel debug (volcado por feature, una línea cada una) en `/vagrant/logs/lab/ml-detector.log` (~790 MB). Es **cola atrasada**, no bucle. Consecuencia metodológica: **las corridas no son independientes**, cada una deja un atraso que consume ~4 núcleos en la siguiente. Puede explicar parte del ruido del hallazgo 2.
5. `VERBOSE` **no llega al sniffer** (`sniffer-start` no pasa `--verbose`); solo afecta al ml-detector.
6. **Todas las cifras de ring son de este laboratorio:** VirtualBox, 6 vCPU compartidos por todos los componentes, XDP genérico, build debug -O0, `FORCE_ALL_HEADS=1`, ml-detector con atraso en paralelo. No se trasladan a un despliegue real.
7. **Sin medir:** el tramo ring → consumidor → ml-detector (cuántos eventos aceptados por el ring llegan al ml-detector).
8. **Decisión:** no seguir persiguiendo la causa del ritmo del consumidor en el laboratorio (deriva del foco). El foco pasa al contador del kernel.
9. Vigentes de DAY274: lector nace desactivado en código y activado en `sniffer.json`; ventana tumbling = delta entre lecturas; usar `d_pkts / window_ms`; la fila `window_ms = 0` es el baseline (filtrar en el harness); CSV append con flush por ventana.

## 4. Trampas de entorno

- `bpftool` solo funciona con `sudo` (no está en el PATH del usuario `vagrant`).
- Los `make` de build y tests (`make sniffer`, `make sniffer-ddos-agg-bpf-test`) usan `vagrant ssh` y se lanzan **desde el Mac**, no desde `defender`. `PROFILE ?= debug` → `/vagrant/sniffer/build-debug`.
- `--sent PKTS BYTES` de `snap_delta.py`: sustituir por los números de la línea `Actual:` de tcpreplay de esa corrida.
- `top` en batch: usar `-n 2 -d 3` y quedarse con la segunda muestra (la primera da porcentajes acumulados).
- Antes de una corrida, mirar si el ml-detector aún tiene atraso (`top`), o anotarlo: contamina.
- Descargar ficheros puede dejar un espacio final en el nombre. `ls -l` antes de ejecutar en la VM.
- `pgrep -a sniffer` vacío = sniffer caído. Arranque: `make pipeline-start VERBOSE=1 FORCE_ALL_HEADS=1` (Mac). `make pipeline-stop` mata el sniffer sin pasar por el cleanup; parada limpia: `sudo kill -INT $(pgrep -x sniffer)`.
- Logs enormes (`sniffer.log` ~95 MB, `ml-detector.log` ~790 MB): nunca `cat`; `tail -n N | cut -c1-220` o `grep | tail`.
- El Mac no tiene libbpf: lo que compila BPF va en la VM. Patchers con `--dry`/`--apply`/`--check`; nunca commitean.
- Comandos de uno en uno; salidas grandes a fichero; `git grep`, nunca `grep -rn` desde la raíz.

## 5. Procedimiento de medida (E2E con `snap_delta.py` ya extendido)

1. `defender`: `pgrep -a sniffer` (no vacío) y `sudo bash /vagrant/snap_ddos.sh > ~/antes_X.txt`
2. `client`: `sudo tcpreplay --pps=N [--limit=M] --intf1=eth1 /vagrant/datasets/cicddos2019/_0125_50k_lab.pcap 2>&1 | tee ~/tcpreplay_X.txt`
3. `defender`: `sudo bash /vagrant/snap_ddos.sh > ~/despues_X.txt`
4. `defender`: `python3 /vagrant/snap_delta.py ~/antes_X.txt ~/despues_X.txt --sent PKTS BYTES` (números de `Actual:`). Leer: `.1/17`, "no contado", `B − (A + s1 + s2)` = 0.
5. Cruce con el CSV: `awk -F, -v t0=$(head -1 ~/antes_X.txt | cut -d. -f1)000 '$2>=t0 && $4=="192.168.100.1" && $5==17 {p+=$6;b+=$7} END{print p+0,b+0}' /vagrant/logs/lab/ddos_windows.csv`

## 6. Pendiente, en orden propuesto

1. `git status --short` y los dos commits de la sección 1.
2. **Punto 4 (foco):** subir la tasa (5000, 10000, `--topspeed`) con el pcap completo y comprobar que el contador del kernel sigue exacto (`.1/17` = 49.997 / 23.998.186, no contado = 1 pkt / 64 B, residuo = 0). Mirar `missed`/`dropped` de eth2 y hasta dónde llega. Anotar el estado del ml-detector en cada corrida.
3. **Diseño de la cabeza DDoS (ideas a evaluar, ninguna adoptada).** El mapa da la **víctima (destino) y su tasa, exactas**; no da las IP de origen. La dispersión de fuentes (grieta B, `source_ip_dispersion`) hoy sale de los eventos del ring, que pierde ~87 % a 1000 pps en el laboratorio y no es una muestra aleatoria. Nota: el nivel de tasa al que el ring empieza a perder depende de la configuración del laboratorio, pero **bajo un flood real el ring siempre se saturará** (ningún consumidor en userspace sigue un flood), así que los contadores del kernel son estructurales y no un apaño del laboratorio. Ideas, en el orden en que se aplicarían:
   1. Proteger a la víctima: limitar la tasa hacia esa IP (por protocolo/puerto), con histéresis para no oscilar.
   2. Filtrar por **firma del ataque** (protocolo, puerto origen, tamaño), no por IP: en reflexión/amplificación (UDP con puerto origen 53/123/389/1900…) las "IP de origen" son reflectores legítimos, y bloquearlas puede romper DNS/NTP del hospital (en el laboratorio ya aparecen 8.8.8.8 y 1.1.1.1).
   3. Segunda etapa en el kernel, armada solo cuando una víctima supera el umbral: mapa `(víctima, origen)` con LRU y lectura de los top-N desde userspace; el coste solo se paga durante el ataque.
   4. Bloqueo temporal de orígenes con TTL escalonado y **lista de permitidos** (DNS, NTP, actualizaciones, VPN de proveedores, sistemas clínicos), con tope de tamaño y aprobación humana para acciones de gran alcance. Aplicarlo con XDP (mapa de bloqueo consultado antes del resto) sería mucho más barato que reglas en el firewall de userspace.
   5. Limitar por origen o por prefijo /24 (token bucket) en vez de bloquear duro: deja pasar a los legítimos y frena a los pesados.
   6. Un volumétrico satura el enlace antes de que aRGus lo vea: escalar aguas arriba (operador, blackhole/FlowSpec, CERT, servicio de limpieza de tráfico).
   7. Registrar orígenes, tasas y marcas de tiempo como evidencia para informes y correlación posterior, con política de retención (las IP son datos personales).
      Qué acción toma el firewall actual (limitar hacia la víctima, bloquear orígenes) es una decisión de diseño aún abierta.
4. **Paso 4:** harness para la fórmula de `escalation` (tumbling frente a EWMA por shift) sobre el CSV, con `d_pkts/window_ms` y sin las filas `window_ms = 0`.
5. Batalla aparte: medir el tramo ring → ml-detector (contador de entrada del ml-detector frente a `stats[0]`).
6. Nota de honestidad: revisar si el paper (arXiv:2604.04952) o el README afirman algo sobre completitud de captura a alta tasa; estos resultados lo matizarían.
7. Opcional: `make test-components > /tmp/test-components.log 2>&1` y `grep -n test_ddos_kernel_reader /tmp/test-components.log`.

Sin probar todavía: XDP nativo, pcap único, build release, ring saturado de forma controlada más allá de lo medido.

## 7. Prompt de arranque para DAY276

> Continuamos aRGus NDR, rama `docs/ml-heads-grieta-b`, "medir, no votar". Lee `CONTINUIDAD_DAY275_a_276.md`. Reglas: comandos de uno en uno, `git grep` (nunca `grep -rn` desde la raíz), salidas grandes a fichero, los ficheros que generas los ejecuto yo en mi VM y los commits los hago yo. Empieza comprobando `git status --short` y los commits pendientes; después el punto 4: subir la tasa y comprobar que el contador del kernel sigue exacto. No persigas la causa del ritmo del consumidor en el laboratorio. Respuestas en español y concisas.