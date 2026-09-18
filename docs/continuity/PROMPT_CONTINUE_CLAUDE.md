# CONTINUIDAD DAY273 — Agregador DDoS en el kernel eBPF (pre-ring). El confound de la cola de DAY272 quedó RESUELTO: el decaimiento era PÉRDIDA DE RING userspace, no la feature. Hoy se cerraron paso 1+2, se fijó el diseño del agregador en-kernel y se midió el punto de integración exacto en `sniffer.bpf.c`. Mañana: escribir el patcher del eBPF + tests. Rama `docs/ml-heads-grieta-b`.

## LO MEDIDO Y CERRADO (no re-litigar)

### Paso 1 — discriminador (CERRADO)
De las 9 features DDoS, bajo flood sobre el flood limpio: **`escalation` (traffic_escalation_rate) VARÍA y DOMINA** → la cabeza esencialmente umbraliza `escalation` (`class ≈ umbral(escalation)`, corte ~0.005). Cuadra con su importancia 0.33 en el RF post-geo (DAY255). `entropy` varía pero sucia (a 0.000 hay 58 DDOS mezclados con 78 NORMAL). `symmetry` binaria (0/1). `protocol`, `completion`, `disp` CLAVADAS; `saturation` casi.
**CORRECCIÓN a DAY272:** lo muerto es el eje **ESPACIAL** (`source_ip_dispersion`, porque `_lab.pcap` colapsa origen a 1 IP → cap satura). El eje **TEMPORAL** (`escalation`) está VIVO y mandando. La cabeza SÍ usa agregación; el eje que funciona en este flood es el del tiempo, no el del origen.

### Paso 2 — recall limpio (CERRADO)
**149/193 = 0.772** sobre el flood (`plm=482`) en el snapshot congelado `/tmp/detector-day272.log`. Endurecer por puerto NO cambió nada (todo puerto alto; el puerto resultó proxy del tiempo, no discriminador — cada puerto salió 100% de una clase por el orden de envío del pcap). Onset DETECTADO (warmup REFUTADO: primer tramo temporal ya 95.8% DDOS). Los fallos se concentran en la COLA (último tercio 54→46→36% DDOS).

### Confound de la cola — RESUELTO (artefacto 0, `profile_flood_pcap.py`)
La tasa real del flood es **PLANA**: 100 pps exactos a la víctima durante los 500s enteros, cero decaimiento (medido sobre el pcap SIN ring: 49999 pkts, 1 víctima real 192.168.100.1/UDP, 482B = 99%). El detector, en cambio, solo vio 151.7s truncados y decayendo. Las dos cosas juntas ⟹ **(b) PÉRDIDA DE RING userspace bajo carga CONFIRMADA; (a) la feature decae REFUTADA.** El "decaimiento de escalation" era artefacto del ring, no de la feature.

### Material de paper (nuevo)
> El decaimiento aparente de una feature agregada en la cola de un flood es artefacto de la pérdida del ring buffer userspace bajo carga, no de la feature. La tasa real es constante; el detector solo ve una fracción truncada. Agregar en XDP —antes del ring— recupera la señal sin pérdida, y la ganancia crece con la severidad del ataque.

### Marcador de apuestas (medir, no votar)
Claude perdió DOS: `escalation`-clavada → falsa; warmup → falso. Alonso ganó: "la cabeza funciona sobre agregación (temporal)". La P0 del pipeline queda diagnosticada con dato duro: **el ring userspace es el techo de detección**, no el modelo.

## DECISIONES DE ARQUITECTURA FIJADAS (a/b/c) — agregador en-kernel
- **(a) Clave** = `dst_ip + protocol`. KISS. Cada víctima nueva = entrada nueva. Mapa `LRU_HASH`, `max_entries=65536` (~6MB). La memoria NO es la restricción (memcg en 6.1, NO `RLIMIT_MEMLOCK` desde 5.11); la restricción real es el desalojo LRU, benigno (una víctima fría no está bajo flood). Complicar la clave solo si un test lo exige.
- **(b) Semántica** = el kernel cuenta MONÓTONO por víctima; userspace lee cada T segundos y el **delta** = ventana tumbling. Cero lógica de ventana en kernel, cero reset, cero float, cero división. **EWMA-por-shift** (`val -= val>>k; val += muestra`) queda como RETADOR para la iteración offline.
- **(c) Qué se cuenta** = paquetes + bytes por víctima. Exacto (enteros), barato (dos `add`). Dispersión/unique-IPs APLAZADAS (caras en kernel, muertas en flood de origen único).

## TOOLKIT eBPF VERIFICADO (defender, kernel 6.1.0-53-amd64, Debian bookworm)
- `percpu_hash`, `lru_hash`, `lru_percpu_hash` disponibles. `bpf_loop` y `bpf_ktime_get_ns` presentes. BTF `/sys/kernel/btf/vmlinux` existe (4.3MB) → **CO-RE viable**.
- `BPF_SDIV` (división con signo, ISA v4) NO garantizada en 6.1 (es 6.6+). El diseño EWMA-por-shift NO divide → esquivado por diseño, no por suerte.

## CONTRATO DEL AGREGADOR ACTUAL (medido, `sniffer/include/time_window_aggregator.hpp`)
- El **cap-10000 es `max_events`** del constructor = tamaño del ALMACÉN de eventos (`vector<TimeWindowEvent>`, 1 evento/paquete). Flood > 10000 eventos/ventana → almacén lleno → `event_count` clavado a 10000 → fórmula log constante. La muerte de DAY272 con nombre y línea.
- `escalation` NO se calcula en este header; se deriva aguas abajo en el extractor DDoS del ml-detector. Como NO la portamos (diseño de cero), no hace falta tocarla ahora.
- **Insight**: el fallo no es el número 10000, es **CONTAR POR EVENTO**. Contar POR VÍCTIMA (clave=víctima) mata el cap por construcción: el flood martillea 1 contador (`u32/u64`), no llena un almacén de 10000.

## PUNTO DE INTEGRACIÓN eBPF — MEDIDO (`sniffer/src/kernel/sniffer.bpf.c`)
- **UN solo** programa XDP propio: `xdp_sniffer_enhanced` (`SEC("xdp")`, L194). Loader = `sniffer/src/userspace/ebpf_loader.cpp`. NO hay que encadenar/xdp-dispatcher → se **extiende el programa existente**.
- Guard de bounds L213 `if (ip_start + 20 > data_end) return XDP_PASS;` YA cubre los 20B de IP → `daddr` (`ip[16..19]`) dentro de bounds. Sin guard nuevo.
- Nombres verbatim: `data`, `data_end` (L195-196), `ip` (`__u8*`, L216), `packet_len = data_end - data` (L240).
- L233-236 YA extraen `event->dst_ip`, `event->src_ip`, `event->protocol`, `event->packet_len` **en HOST order** (shifts). El contador REUSA esos campos. **OJO byte order**: host order, hereda `DEBT-SNIFFER-IP-BYTE-ORDER-001`; userspace DEBE leer la clave en host order (mismo orden los dos lados = no repetir aquella batalla).
- **DECISIÓN ABIERTA (la central del ejercicio):** contar ANTES o DESPUÉS del `bpf_ringbuf_reserve` (L223). Después = solo cuenta lo que reservó ring → contamina con la pérdida que queremos evitar. **ANTES, con variables locales = conteo independiente del ring = el objetivo.** Recomendación firme: ANTES.

### Boceto del contador (revisado, cuadra con el fichero real; NO aplicado)
```c
/* define junto a L31-33 */
#define BPF_MAP_TYPE_LRU_HASH 9

/* mapa junto a `stats` ~L149.
   OJO: dst_ip en HOST order (hereda shifts L234). Userspace lee host order. */
struct ddos_key { __u32 dst_ip; __u8 proto; };
struct ddos_val { __u64 pkts; __u64 bytes; };
struct {
    __uint(type, BPF_MAP_TYPE_LRU_HASH);
    __uint(max_entries, 65536);
    __type(key, struct ddos_key);
    __type(value, struct ddos_val);
} ddos_victims SEC(".maps");

/* bloque de conteo — versión ANTES-DEL-RESERVE con locales (recomendada):
   extraer dst_ip/proto/len a locales tras el guard L213-216 y contar aquí,
   ANTES del bpf_ringbuf_reserve de L223, para no heredar la pérdida del ring. */
struct ddos_key dk = {};
dk.dst_ip = (ip[16]<<24)|(ip[17]<<16)|(ip[18]<<8)|ip[19];  /* host order */
dk.proto  = ip[9];
__u64 wlen = (__u64)(data_end - data);
struct ddos_val *dv = bpf_map_lookup_elem(&ddos_victims, &dk);
if (dv) { __sync_fetch_and_add(&dv->pkts, 1); __sync_fetch_and_add(&dv->bytes, wlen); }
else { struct ddos_val nv = { .pkts = 1, .bytes = wlen }; bpf_map_update_elem(&ddos_victims, &dk, &nv, BPF_ANY); }
```

## PENDIENTE DAY273 (en orden, ACORDADO)
1. **Script Python que MODIFICA `sniffer.bpf.c`** (patcher estilo `patch_force_all_heads.py`: idempotente, atómico, **--dry/--apply/--check**, verifica que compila, NO commitea). Inserta: el `#define`, el `struct`+mapa `ddos_victims`, y el bloque de conteo **ANTES del reserve con locales**.
2. **`ebpf_loader.cpp`**: exponer el mapa `ddos_victims` a userspace por nombre, leerlo cada T.
3. **Tests de INTEGRACIÓN + E2E** (como hasta ahora): flood por el pipeline → verificar que el conteo en-kernel == ~50000 SIN pérdida, contra el 77% que dejó pasar el ring. Este es el criterio de HECHO del ejercicio.
4. **Harness de fitting de fórmulas** de `escalation` sobre los conteos LIMPIOS (tumbling vs EWMA-por-shift), elegir la que mejor separe. SOLO entonces decidir qué baja al kernel como punto fijo.

## FICHEROS DE HOY (pendientes de commitear a `docs/ml-heads-grieta-b`)
- `zmq_handler.cpp` — log de 9 features DDoS. **APLICADO, compila, SIN commitear.** Patcher: `patch_log_all_features.py`.
- `join_flood_escalation.py` (v1), `_v2.py`, `_v3.py` — parsers de análisis (untracked).
- `profile_flood_pcap.py` — profiler sin pérdida del pcap (untracked; requiere `pip install dpkt`).

## INVARIANTES
`main` protegida (PR only). Rama = `docs/ml-heads-grieta-b`. Flags por Makefile, NUNCA JSON a mano. `git grep`/fichero concreto, NUNCA `grep -rn` desde raíz. No encadenar salidas grandes. El compilador/verificador es el árbitro. HECHO ≠ SOSPECHADO.

## MÉTODO DE REPLAY (reusar)
`_0125_50k_lab.pcap` a `--pps=100` desde el guest client: `sudo tcpreplay --intf1=eth1 /vagrant/datasets/cicddos2019/_0125_50k_lab.pcap`. Rehacer `tcprewrite` SOLO si hubo `destroy→up` (las MACs cambian). `truncate -s 0 logs/lab/detector.log` con el pipeline VIVO (NUNCA `logs-lab-clean`, mueve el inodo). `make pipeline-start VERBOSE=1 FORCE_ALL_HEADS=1` fuerza la compuerta level1. Log del detector: `logs/lab/detector.log` (host) = `/vagrant/logs/lab/detector.log` (VM). Congelar a `/tmp` para análisis. Ring stats en el defender: `sudo bpftool map dump name stats`.