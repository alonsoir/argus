# Prompt de continuidad — aRGus NDR, DAY287 → DAY288

Reglas de trabajo (sin cambios): medir, no votar; predicción escrita antes de medir; comandos
separados o cada salida a su fichero; nunca `grep -rn` desde la raíz (usar `git grep` o el fichero
concreto); los scripts/patchers los ejecuta Alonso en su VM; scripts como bloque `cat > f <<'EOF'`;
si algo no da lo esperado, parar; `LC_ALL=C` en todo script con aritmética en awk. Tras un cambio,
compilar TODO el pipeline (`make pipeline-build PROFILE=production`, ~25–60 min). Dar comandos exactos
y completos, en orden, con dónde se ejecuta cada uno (Mac / defender / client). Patchers atómicos e
idempotentes con `--check` / `--apply`.

**Foco único: la cabeza DDoS.** Orden de trabajo (decidido DAY281): (1) observabilidad por cabeza ✅,
(2) contrato único de rasgos train/serve [EN CURSO], (3) reentrenar y medir importancias antes de
quitar rasgos, (4) fast-alert como entrada propia a la fusión, (5) fusión + firewall por `final_decision`.

Operativa: targets del Makefile raíz en el **Mac**; scripts y patchers en el **defender** desde
`/vagrant` (rutas absolutas); tráfico en el **client** (`eth1`, 192.168.100.50 → defender 192.168.100.1).
Arranque: `make pipeline-stop` y `make pipeline-start PROFILE=production FORCE_ALL_HEADS=1`. Logs:
`/vagrant/logs/lab/{sniffer,ml-detector}.log` (rotar SIEMPRE con `sudo truncate -s 0` en sitio, NUNCA
`logs-lab-clean` con el pipeline vivo). Dataset DDoS de laboratorio en
`/vagrant/logs/lab/ddos_dataset/ddos_dataset_<arranque>.csv` (apagado por defecto; se activa con el
`sed` sobre `ddos_dataset_writer.enabled` en `ml_detector_config.json`).

## 0. Estado de git

Rama `feat/ddos-head-contract`, NO mergeada. Último commit en el momento de escribir esto: `c60c25ba`.
Commits DAY287: `c7293346` (escritor de dataset v2), `c60c25ba` (fix de fragmentos IP). Pendiente de
commit: este prompt, el BACKLOG DAY287 y los scripts de medida del día (ver DAY288 paso 0).
Comprobar con `git fetch && git log --oneline -6 origin/feat/ddos-head-contract`.

## 1. Lo que DAY287 dejó MEDIDO y CERRADO

### 1.1 Escritor de dataset DDoS v2 (punto 2 del plan, CERRADO, commit c7293346)
- Clase header-only `ml-detector/include/ddos_dataset_writer.hpp`. Escribe en el mismo punto que la
  línea `[DDOS-V2]` del `zmq_handler.cpp` (tras `[HEAD-SCORES]`, fuera del `if(should_log(debug))`),
  así que NO depende de VERBOSE. Un fichero por arranque, apagado por defecto, flush por fila.
- 18 columnas: `ts_ns, community_id, src_ip, dst_ip, src_port, dst_port, proto, event_kind` + los 8
  rasgos del contrato v2 (`syn_ack_ratio, mean_packet_size, reflection_signature, packet_size_entropy,
  flow_packet_count, flow_completion_rate, victim_rate_ratio, victim_pps`) + `old_ddos_prob, old_ddos_class`
  (veredicto del bosque viejo; -1 = cabeza no evaluada en ese evento).
- CSV plano, sin HMAC: integridad por sha256 en el manifiesto del entrenamiento.
- VERIFICADO E2E: cruce 1:1 con el bronce `correlation_v1` por `community_id`+`ts` salvo la cola de
  cada corrida que `pipeline-stop` mata (deuda aparte, backlog).

### 1.2 Fix de fragmentos IP (CERRADO, commit c60c25ba, DEBT-SNIFFER-IP-FRAGMENT)
- HALLAZGO: el sniffer NO trataba los fragmentos IPv4 no-primeros. Parseaba bytes de la carga como
  puertos TCP/UDP → flujos fantasma. Medido en el bloque B de CICDDoS2019: de 4990 filas UDP, 3144
  (63 %) eran basura.
- Arreglado en el kernel (`sniffer.bpf.c`): si offset != 0, se cuenta en `ddos_victims` (va antes del
  reserve) pero NO se parsean puertos ni va al ring. Contador nuevo `STAT_FRAG_SKIPPED` = stats[3];
  identidad ahora B = A + s1 + s2 + s3. También en Variant B (`main_libpcap.cpp`): mismo criterio,
  no emite evento. `snap_delta.py` lee stats[3].
- VERIFICADO: bloque B pasa de 4990 a 1770 filas reales; stats[3]=3224; victim_pps 82,5 → 97,9.
- Por qué no se vio antes: nunca había entrado tráfico fragmentado al pipeline (TCP con MSS no
  fragmenta, el bloque A es de 440 B, Neris llegaba recortado por MTU de VirtualBox).

### 1.3 Dataset CICDDoS2019: qué hay de verdad (MEDIDO, índices 15 y 16 en logs/lab/day287/)
- Solo tenemos el día de ENTRENAMIENTO (01-12 = 1 de diciembre), 250 chunks `SAT-01-12-2018_0*`
  (191 MB cada uno) + el zip `PCAP-01-12_0-0249.zip`. NO está el día de test (11 de marzo).
- AppArmor: `tcpdump` no abre ficheros sin extensión `.pcap`. Se lee por stdin: `tcpdump -r - ... < fichero`.
- Los chunks van 13:17–15:09 UTC (solo ~2 h de las ~6,75 del día). Orden por nº de chunk = orden
  temporal (sin retrocesos).
- SOLO DOS familias de ataque en lo disponible, las dos UDP volumétricas:
    * BLOQUE A (chunks 1–196): UDP 440 B, sport aleatorio 512–1023, dport alto. Es el flood del
      `_0125_50k_lab.pcap` que usamos siempre.
    * BLOQUE B (chunks 197–249): UDP ~3964/3995 B, FRAGMENTADO en IP, sport ~564.
- CLAVE PARA EL PAPER: en CIC el tráfico de ataque NO lleva el puerto de servicio como origen, así que
  `reflection_signature` NO puede dispararse nunca con CIC. En una reflexión real (NTP/DNS) sí lleva
  123/53. Hallazgo sobre el realismo del dataset.
- El horario de CIC NO sirve para etiquetar tipos (el desfase UTC no casa); etiquetar por firma medida.

### 1.4 Ataques generados en el lab (punto 2 opción b, MEDIDO; cada familia con su firma)
Herramienta: `nping` (0.7.93, ya instalado en el client). AVISO FUERTE: `nping` NO respeta `-c N`
(se queda enviando hasta Ctrl-C) y NO sabe variar el puerto origen en una ejecución. Para el dataset
DEFINITIVO hay que generar pcaps y reproducir con `tcpreplay --limit` (que sí respeta el tope). Hoy se
cortó a mano. SYN flood ya se generó como pcap a mano (ver abajo).

Firmas medidas (todas 192.168.100.50 → 192.168.100.1, replay/envío a 100 pps):

| Familia | Origen | sport | refl | mean_size | syn_ack | flow_pkts | class1 viejo |
|---------|--------|-------|------|-----------|---------|-----------|--------------|
| UDP flood 440 | CIC bloque A | aleatorio | 0 | 482 | 0 | ~2 | 72–75 % |
| UDP frag 4K | CIC bloque B | aleatorio | 0 | ~1441 | 0 | ~2 | ~92 % |
| SYN flood | lab (pcap) | efímero | 0 | 54 | 1.000 | 1.00 | 0 % |
| NTP reflex | lab (nping -g 123) | 123 | 1.000 | 482 | 0 | 1–2 | ~35 % |
| DNS reflex | lab (nping -g 53, len 1400) | 53 | 1.000 | 1442 | 0 | 1.04 | 3,6 % |

- SYN flood pcap: `/vagrant/datasets/lab/syn_flood_5k_lab.pcap`, generado con
  `/vagrant/datasets/lab/gen_syn_flood.py` (stdlib, checksums IP+TCP correctos, 5000 SYN con puerto
  origen distinto por paquete, MACs del lab ya puestas → NO necesita tcprewrite).
- RESULTADO DE PAPER: el bosque viejo (sin contrato v2) marca class=1 en apenas 0–5 % de SYN y
  reflexiones. NO ve casi ningún ataque que no sea el flood UDP volumétrico que fue casi su único
  patrón de entrenamiento. Evidencia de que el contrato v2 (reflection_signature, syn_ack_ratio,
  victim_pps/victim_rate_ratio del kernel) es NECESARIO.
- NOTA SESGO: la corrida NTP quedó enorme (696877 filas, 64504 flujos reales = 64504 community_id =
  64504 puertos destino, flow_pkts ≤ 5, sin acumulación ni tope-200; muchas filas = muchas
  observaciones a lo largo del tiempo, no un bug). Hay que SUBMUESTREAR NTP o aplastará al resto.

## 2. Siguiente: punto 3 — consolidar el dataset y entrenar

Diseñar antes de escribir (predicción por decisión):

1. **Consolidar**: reunir los ficheros `ddos_dataset_*.csv` de las corridas de hoy en un dataset
   único etiquetado por familia. Etiqueta = por construcción (qué corrida/qué firma), no por columnas
   de CIC. Guardar el manifiesto con sha256 de cada fichero fuente.
2. **Submuestreo equilibrado por familia**: NTP tiene 696877 filas frente a ~5000 del SYN. Decidir N
   por familia (p. ej. 5000) y muestrear de forma reproducible (seed). Predecir el balance antes.
3. **Benigno**: ambiente + subida TCP 50 KB/s + DNS/HTTP legítimos del lab, por construcción.
4. **SPLIT CRÍTICO**: el sniffer emite una fila POR PAQUETE (foto acumulada del flujo), así que las
   filas de un mismo flujo están correladas. El split train/test DEBE ser por flujo (community_id) o
   por ventana temporal, NUNCA por filas al azar, o se filtra información del test al train.
5. **Entrenar SIN scaler** (bosque invariante a escala), medir importancias, y SOLO entonces decidir
   si se quita algún rasgo. Punto 3 del orden DAY281.
6. **Reemplazar nping por pcaps**: generar NTP y DNS como pcap (igual que el SYN flood, con un
   `gen_reflection.py` análogo a `gen_syn_flood.py`) y reproducir con `tcpreplay --limit N`, para
   corridas reproducibles de tamaño fijo. Backlog inmediato de DAY288.

Medidas a incluir en el entrenamiento: FP sobre ambiente y sobre la subida TCP legítima de 50 KB/s;
recall por familia; importancias de los 8 rasgos. Comparar SIEMPRE contra la línea base del bosque
viejo (`old_ddos_class`) que ya va en el dataset.

Después de la cabeza: fusión + firewall obedeciendo `final_decision`
(DEBT-FIREWALL-GATES-ON-LEVEL1-001, P0), con lista explícita de señales habilitadas (al principio solo
DDoS). Luego, actualización del paper (sección de método de dataset + hallazgos de realismo).

## 3. Scripts y herramientas de DAY287 (en la raíz del repo salvo nota)
- `patch_d287_ddos_dataset_writer.py` — escritor de dataset (ya aplicado y commiteado).
- `patch_d287_ip_frag.py` / `patch_d287_ip_frag_userspace.py` — fix de fragmentos (ya aplicados y
  commiteados).
- `day287_medir_sumidero.sh`, `day287_medir_dataset.sh`, `day287_cruce_p11.sh`,
  `day287_cruce_p11_ds.sh`, `day287_indice_cicddos.sh`, `day287_indice2_cicddos.sh`,
  `day287_medir_bloqueB.sh` — commiteados.
- `day287_medir_syn.sh`, `day287_medir_reflex.sh` — PENDIENTES de commit (DAY288 paso 0).
- `/vagrant/datasets/lab/gen_syn_flood.py` + `/vagrant/datasets/lab/syn_flood_5k_lab.pcap` — pendientes
  de decidir si se trackean (el pcap es regenerable; preferible trackear solo el .py + manifiesto).
- Salidas de medida en `/vagrant/logs/lab/day287/` (NO trackear; son evidencia de laboratorio).