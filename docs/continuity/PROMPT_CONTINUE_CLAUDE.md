# Prompt de continuidad — aRGus NDR, DAY288 → DAY289

Reglas de trabajo (sin cambios): medir, no votar; predicción escrita antes de medir; comandos
separados o cada salida a su fichero; nunca `grep -rn` desde la raíz (usar `git grep` o el fichero
concreto); los scripts/patchers los ejecuta Alonso en su VM; scripts como bloque `cat > f <<'EOF'`;
si algo no da lo esperado, parar; `LC_ALL=C` en todo script con aritmética en awk; en scripts con
`set -e` NO usar `pipefail` junto a `| head` (SIGPIPE aborta el script en silencio, pasó DAY288).
Tras un cambio, compilar TODO el pipeline (`make pipeline-build PROFILE=production`). Dar comandos
EXACTOS y COMPLETOS, uno a uno, en orden, diciendo dónde se ejecuta cada uno (Mac / defender /
client), sin nada que el usuario tenga que sustituir a mano. Patchers atómicos e idempotentes con
`--check` / `--apply`.

**Foco único: la cabeza DDoS.** Orden de trabajo (decidido DAY281): (1) observabilidad por cabeza ✅,
(2) contrato único de rasgos train/serve ✅ (contrato v2 + escritor de dataset + fix de fragmentos),
(3) reentrenar y medir importancias antes de quitar rasgos [EN CURSO: dataset COMPLETO DAY288,
falta consolidar y entrenar], (4) fast-alert como entrada propia a la fusión, (5) fusión + firewall
por `final_decision` (DEBT-FIREWALL-GATES-ON-LEVEL1-001, P0).

Operativa: targets del Makefile raíz en el **Mac**; scripts en el **defender** desde `/vagrant`
(rutas absolutas); tráfico en el **client** (`eth1`, 192.168.100.50 → defender 192.168.100.1).
Logs: `/vagrant/logs/lab/{sniffer,ml-detector}.log` (rotar SIEMPRE con `sudo truncate -s 0` en
sitio). El escritor de dataset (`ddos_dataset_writer.enabled` en `ml_detector_config.json`) quedó
APAGADO al cerrar DAY288.

## 0. Estado de git

Rama `feat/ddos-head-contract`, NO mergeada. Commits DAY288: `938705f4` (generadores de pcaps en
`scripts/dataset_lab/` + MANIFEST.md) y el commit de los 9 scripts `day288_*.sh` (comprobar hash con
`git log --oneline -4 origin/feat/ddos-head-contract`). Pendiente de commit: este prompt, el BACKLOG
DAY288 y `docs/ml-heads/paper_notes_day288.md`.

## 1. Lo que DAY288 dejó MEDIDO y CERRADO

### 1.1 Pcaps de ataque del lab, reproducibles byte a byte
- `scripts/dataset_lab/gen_syn_flood.py` y `gen_reflection.py` (stdlib, seed 42, MACs del lab, sin
  tcprewrite). Los pcaps viven en `datasets/lab/` (ignorado por `.gitignore:169 datasets/`).
  Regenerados a /tmp: sha256 idéntico en los tres. `MANIFEST.md` con comandos y sha256.
- nping queda DESCARTADO para el dataset (no respeta `-c`, no varía el puerto origen).

### 1.2 Protocolo de corridas (scripts en la raíz, commiteados)
Una corrida = un arranque del pipeline = un fichero `ddos_dataset_<arranque>.csv`. Secuencia:
1. Defender `/vagrant/day288_pre.sh TAG` (trunca logs, graba vmstat y top).
2. Mac `make pipeline-start PROFILE=production FORCE_ALL_HEADS=1`.
3. Defender `/vagrant/day288_esperar_estable.sh` (compuerta: ≥10 sondeos del lector en 30 s, todos
   ≤1200 ms; guarda la MARCA en `logs/lab/day288/marca.txt`).
4. Client `sudo tcpreplay --intf1=eth1 --pps=R --limit=3000 <pcap>` EN CUANTO salga ESTABLE.
5. Client `sleep 30`. 6. Mac `make pipeline-stop`.
7. Defender `/vagrant/day288_post.sh FAM R PROTO` (QA sobre `ddos_windows.csv`: ventanas de ataque
   con pps en [0,5R, 1,5R] y ningún sondeo >1500 ms; mide `ventanas_previas` de la clave
   `.1/PROTO`; registra en `runs.tsv` si FRIO (<30), en `runs_caliente.tsv` si CALIENTE, en
   `runs_descartadas.tsv` si RECHAZADA; mide la corrida).
- Medida por corrida: `day288_medir_corrida.sh`; por deciles de víctima: `day288_victima_deciles.sh`.

### 1.3 Registro de corridas (`/vagrant/logs/lab/day288/`)
`runs.tsv` (ENTRENAMIENTO, todo régimen frío; 4.ª col = ventanas previas, vacía en las 8 primeras):
| fam | R | fichero | kind0 | notas |
|---|---|---|---|---|
| ntp | 30 / 60 / 100 | 053850 / 055341 / 055914 | 3000 c/u | refl=1, 482 B |
| dns | 30 / 60 / 100 | 060630 / 061741 / 062421 | 3000 c/u | refl=1, 1442 B |
| syn | 30 / 100 / 60 | 063035 / 070634 / 071539 | 3000 c/u | syn_ack=1, 54 B, 3000 flujos |
| udpA | 30 / 60 / 100 | 072033 / 072623 / 073207 | 2999 c/u | 66 flujos, flow_pkts≈51 |
| udpB | 30 / 60 / 100 | 075033 / 075634 / 080144 | 1056 c/u | 527 flujos, 1457,6 B |
| benign | 2 / 20 / 50 / 100 KB/s | 081423 / 082436 / 083143 / 083642 | 603 / 2948 / 2915 / 2800 | 1 flujo TCP→:9000 |
(prefijo de fichero `ddos_dataset_20261005-`). benign_2 aceptada a mano: el QA de banda de pps no
aplica a 2 pps (se colaban ventanas de ambiente); su `max_window_ms` = 1039, OK.
`runs_caliente.tsv` (EVALUACIÓN de desplazamiento, NO entrenar): syn 60 `063628` (137 ventanas
previas), benignhot 100 `085803` (66 previas; 60 s a 2 KB/s + 120 s a 100 KB/s).
`runs_descartadas.tsv`: ntp 30 `051444` (ráfaga de laboratorio, ver 1.5).
Ficheros de DAY287 (20261004-*) NO entran: nping de tamaño arbitrario, bloque B pre-fix con flujos
fantasma, bloque A a otra tasa. Se conservan como evidencia.

### 1.4 Hechos medidos que condicionan el entrenamiento
- **kind=1 (fast alert) no lleva rasgos**: los 8 a centinela en el 100 % de las filas. Entrenar con
  `kind=0` y `syn_ack_ratio > -9000` (excluye las filas sin estado de flujo).
- **Línea base del bosque viejo** (`old_ddos_class`): SYN 0 %; NTP/DNS 0–0,1 %; udpA 36 / 57 / 72 %
  a 30 / 60 / 100 pps (depende del caudal, no de la firma); udpB 87–92 % plano; benigno TCP
  0,5 % a 2 KB/s y **99,97–100 % de FP a ≥20 KB/s**; benignhot 98 %.
- **`victim_rate_ratio` depende de la HISTORIA de la clave de víctima** (`hot = seen ≥ 30 && ratio
  ≥ 5`, α/60 si hot). Clave fría → α rápido → el ratio decae a ~1 en ~10–20 ventanas (punto ciego).
  En régimen frío y misma tasa, todas las familias dan el mismo ratio medio (1,18 / 1,54 / 2,1 a
  30 / 60 / 100). Cuando la línea base está bajo el suelo de 10 pps, ratio = victim_pps/10 exacto.
- **FP de clave caliente ACOTADO, no permanente** (benignhot): ratio ~9 → 5,4 en 120 s; sale de ≥5
  tras ≈ −ln(0,8)/(0,1/60) ≈ 134 ventanas ≈ 2,2 min, independiente de la carga si la línea base
  previa ≪ carga.
- **Fast alert**: ~1 por flujo nuevo en reflexión UDP; 2–5 en SYN frío frente a 80 en SYN caliente.
- **Las tasas de ataque (30–100 pps) y benignas (2–100 pps) se solapan por diseño**: `victim_pps` no
  puede separar las clases por sí solo. Comprobarlo en las importancias.

### 1.5 Laboratorio
- Episodios de parón de la VM (lector con ventanas de hasta 16 s; paquetes entregados en ráfaga:
  434 pkts en 981 ms a "30 pps"). El kernel mide bien la llegada real; es artefacto de lab.
  Mitigado con compuerta + QA. Causa sin medir (VirtualBox no informa `st` de forma fiable).
- Coste del pipeline a 100 pps UDP (~200 ev/s con FORCE_ALL_HEADS): ml-detector ~320 % CPU,
  sniffer hasta ~110 %, firewall-acl-agent 30–50 % sin actuar. No afecta al dataset (QA, filas y
  huecos perfectos).

## 2. Siguiente (DAY289): consolidar y entrenar (punto 3)

Diseñar antes de escribir, predicción por decisión:
1. **Consolidación** (script nuevo, solo lectura de los CSV): leer `runs.tsv`, filtrar `.50→.1`,
   `kind=0`, `syn_ack_ratio > -9000`, proto según familia (udpA/udpB/ntp/dns 17, syn 6; benign 6
   con dport 9000). Etiqueta binaria (ataque/benigno) + columna `familia` + `tasa` + `fichero`.
   Ambiente (filas que NO son .50→.1) como benigno adicional, etiquetado `ambiente`. Manifiesto con
   sha256 de cada CSV fuente y de los pcaps (MANIFEST.md + sha256 de `_0125_50k_lab.pcap` y
   `_0220_50k_lab.pcap`). Rellenar la 4.ª columna de las 8 primeras líneas de `runs.tsv` (ventanas
   previas) con un backfill medido.
2. **Balance**: decidir N por familia (udpB solo tiene 3168 filas). Predecir el balance.
3. **Split temporal 70/30 dentro de cada corrida** (por `ts_ns`), NUNCA por filas al azar ni por
   `community_id` (udpA son 66 flujos; los rasgos de víctima son estado compartido en el tiempo).
4. **Entrenar SIN scaler** (bosque), medir: recall por familia y tasa, FP sobre benigno por tasa y
   sobre ambiente, importancias de los 8 rasgos. Comparar SIEMPRE con `old_ddos_class`.
5. **Evaluación de desplazamiento**: aplicar el modelo a `runs_caliente.tsv` (syn caliente,
   benignhot) y reportar aparte.
6. SOLO después decidir si se quita algún rasgo (`victim_rate_ratio` es el candidato a vigilar).

Recordatorio de alcance: entrenar es el paso 3 de 5. Después hay que cablear el modelo nuevo en
serve (el ml-detector debe consumir `ddos_embedded` v2), sacar la fast alert como entrada propia y
hacer que el firewall obedezca `final_decision` con lista explícita de señales habilitadas (al
principio solo DDoS). Luego, actualización del paper.

## 3. Herramientas DAY288
- `scripts/dataset_lab/` (commiteado): generadores + MANIFEST.md.
- Raíz: `day288_inventario_dataset.sh`, `day288_huecos_flujo.sh`, `day288_medir_corrida.sh`,
  `day288_victima_deciles.sh`, `day288_ventanas_corrida.sh`, `day288_esperar_estable.sh`,
  `day288_qa_corrida.sh`, `day288_pre.sh`, `day288_post.sh`.
- Receptor/emisor TCP benigno: `scripts/d281_tcp_sink.py`, `scripts/d281_tcp_upload.py`.
- Evidencia (NO trackear): `/vagrant/logs/lab/day288/` (runs*.tsv, medida_*, vmstat_*, top_*,
  tcpreplay_*, sink.txt) y `/vagrant/logs/lab/ddos_dataset/`.
### 4.4 ORDEN ACORDADO (Alonso, cierre DAY288)
1. DAY289: consolidar + PRIMER entrenamiento (pregunta: ¿separa el contrato v2 las familias donde el
   bosque viejo fallaba?). Vale con cualquier modelo de emisión.
2. Justo después: paso 0 del anillo (§4.2): contador de `reserve` fallidos + `perf` del sniffer a
   100 pps. Sin tocar comportamiento.
3. Decidir con esos datos si se cambia la emisión (por flujo en vez de por paquete):
   - SI se cambia: regenerar las 19 corridas con el mismo protocolo (pcaps reproducibles +
     scripts day288_*, ~2 h mecánicas) y reentrenar ANTES de cablear. Motivo: cambiar la emisión
     cambia filas por flujo y momento de cada foto; cablear antes reabriría el skew train/serve de
     DAY255.
   - NO se cambia: cablear el modelo (pasos 4-5) y el anillo vuelve al BACKLOG.

### 4.1 Primer punto de la consolidación: benigno con reflection_signature=1
Antes de entrenar, contar las filas de AMBIENTE (no .50→.1, kind=0, con rasgos) con
`reflection_signature = 1` (respuestas DNS/NTP legítimas que recibe el propio defender).
Predicción a escribir antes de medir. Si hay suficientes, sirven de benigno con refl=1. Si no hay,
el modelo aprenderá "refl=1 ⇒ ataque" y hay que generar respuestas DNS/NTP legítimas (pcap del lado
entrante) ANTES de dar el entrenamiento por bueno.

### 4.2 Rendimiento del consumidor del anillo (requisito para validar a tasas reales)
Pista medida DAY288: a 100 pps el sniffer consume ~1 núcleo (hasta 112 %) ≈ 10 ms de CPU por
paquete; un ringbuf eBPF soporta millones de eventos/s. Hipótesis: el cuello es el trabajo por
evento del consumidor (protobuf + >100 rasgos + ddos_embedded + ZMQ, una vez por paquete), no el
anillo.
- Paso 0 (medida barata): contador de `bpf_ringbuf_reserve` fallidos en el mapa `stats` (hoy no
  instrumentado) + `perf record -g` del sniffer durante una corrida a 100 pps.
- Palancas (por impacto esperado): (1) emitir por flujo y no por paquete (al nacer, cada N
  paquetes o T ms, al cerrar; = DEBT-ML-DETECTOR-EVENT-PER-PACKET-001 desde el sniffer);
  (2) contadores por flujo en el kernel, como ddos_victims; (3) consumidor desacoplado: hilo que
  vacía el anillo a cola sin bloqueos + hilos de construcción + envío por lotes; (4) degradación
  con muestreo bajo presión, contadores del kernel exactos y aviso en log; (5) XDP nativo frente a
  genérico (depende del hardware).
- Orden: paso 0 → palanca 1 → solo si no basta, 2 y 3. Cuándo: ver §4.4.

### 4.3 Hoja de ruta de familias DDoS (después del primer entrenamiento)
- Volumétricas L3/L4 (floods UDP/SYN/ACK/RST/ICMP, reflexiones, multi-origen, pulsos): un solo
  modelo, preferiblemente multiclase. Generadores de pcap ampliables; el sniffer solo ve el
  entrante, así que un pcap del lado cliente (incluida una avalancha legítima de miles de clientes)
  es realista para él.
- Otra unidad de observación ⇒ otras cabezas, no la DDoS: ataques lentos (estado de conexión),
  repartidos entre muchas víctimas (agregar por /24), capa de aplicación (peticiones).
- Predicción para el primer entrenamiento: con un modelo binario único, recall alto y parejo en las
  5 familias volumétricas. Si una queda claramente por debajo o el multiclase la confunde con el
  benigno, es evidencia para separarla.
- Muro: tasas >100 pps bloqueadas por el consumidor del anillo (§4.2). Un bosque no extrapola: por
  encima de 100 pps el comportamiento del modelo está sin definir.
