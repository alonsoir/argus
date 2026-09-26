# Prompt de continuidad — aRGus NDR, DAY280 → DAY281

Reglas de trabajo (sin cambios): medir, no votar; predicción escrita antes de medir; comandos
separados o cada salida a su fichero; nunca `grep -rn` desde la raíz (usar `git grep` o el fichero
concreto); los scripts los ejecuta Alonso en su VM; scripts como bloque `cat > f <<'EOF'`; si algo
no da lo esperado, parar; `LC_ALL=C` en todo script con aritmética en awk.

Nuevas DAY280:
- Los targets del Makefile raíz (`make pipeline-start`, etc.) se lanzan en el **Mac** (llaman a
  `vagrant ssh`). Los scripts de medida, en el **defender** desde `/vagrant`. El tráfico, en el **client**.
- Log del ml-detector: `/vagrant/logs/lab/ml-detector.log` (rotar con `truncate -s 0`).
- **Todo cruce por evento se hace por `seq` de la ventana estampada, NUNCA por hora del log.**
  El ml-detector procesa con retraso (ver §3). `seq` de `[VICTIM-WINDOW]` == `win` del CSV (verificado).
- Antes de cruzar, esperar a que la última `seq` del log alcance el `win_fin` del episodio.
- En bash interactivo, `!!` dentro de `echo "..."` expande el historial.

Foco: la cabeza DDoS por separado. Las demás cabezas fuera de foco.

## 1. Cerrado: el contador del kernel es exacto

- DEBT-KERNEL-COUNT-GAP-CIC4-001 **CERRADA**: los 879 paquetes "perdidos" de cic4 eran el filtro
  horario de d279 (bordes + desfase de reloj client/defender), no pérdida.
- Esperado correcto por replay del pcap `_0125_50k_lab.pcap` en la clave `{192.168.100.1, UDP}`:
  **49 997** = 50 000 − 1 PVST+ (no IPv4) − 2 ICMP (proto 1). Medido 49 997 exactos en 7 replays
  completos (cic3 troceado en 3 episodios por parones de tcpreplay, cic4, y 5 de DAY274–278).
- Con DNS benigno: 6 001 / 12 000 / 24 000 exactos a 50/100/200 qps.
- Método que no depende de relojes: episodios por hueco de tiempo en el CSV
  (`scripts/d280_kernel_gap.sh`, `scripts/d280_episodes.py`).
- Abierto menor: EP17 (cic2, DAY278) suma 51 308 (+1 311), 520 s.

## 2. Lab DNS benigno (Vagrantfile)

- Defender: provisión `lab-dns-resolver` = unbound en 192.168.100.1:53 + zona local `lab.argus`
  (h1..h20 → .201..220), `ip-freebind`, verificado por `dig`, resolv.conf intacto.
- Client: `dnsperf` (2.10.0-2) añadido a la lista apt de `client-setup` (un bloque aparte no puede
  instalar: tras `client-setup` el client no tiene salida a internet).
- Patchers: `patch_lab_dns_d280.py` + `patch_lab_dns_d280_v2.py`. **Verificar que el commit está hecho.**
- Carga: `scripts/d280_dns_load.sh` (vars `LEVELS`, `DUR`, `PAUSE`, `CLIENTS`).

## 3. Retraso sniffer → ml-detector (medido)

- Con `VERBOSE=1`: el ml-detector trabaja a ~1/3 del tiempo real con ~30 eventos/s de entrada;
  retraso creciente hasta **~12 min** (último evento procesado 12 min después del fin del tráfico).
- Sin VERBOSE (`FORCE_ALL_HEADS=1`, 100 qps): una sola joroba, máx **22,8 s**, causada por una
  ráfaga de entrada al inicio de la carga (~55 ev/s los primeros 20 s frente a ~18 ev/s estables);
  después se pone al día hasta ~1 s. No es prioridad (fase funcional, no de rendimiento).
- `age_ms` bajo y 0 discrepancias con el CSV: el dato se estampa bien en el sniffer; solo llega tarde.
- Consecuencia: las tablas por evento de DAY279 (cic4) cruzadas por hora son **parciales** en
  totales; las proporciones se mantienen (FLOOD se define por 5-tupla).

## 4. Tráfico benigno: DNS .50 → .1 (por seq, con VERBOSE)

| Carga | Eventos | Señal kernel vpps ≥ 50 | Cabeza DDoS dispara |
|---|---|---|---|
| 50 qps, 4 clientes | 2 524 | 95,8 % | 0 |
| 100 qps, 4 clientes | 1 200 | 96,7 % | 0 |
| 200 qps, 4 clientes | 1 590 | 96,0 % | 0 |
| 100 qps, 200 clientes | 2 316 | 97,5 % | 0 |

- La señal en valor absoluto = volumen puro: FP ≈ 96 % sobre DNS legítimo ≥ 50 qps. Sola no sirve.
- **XDP en eth2 solo ve ingreso**: las respuestas del resolver (salida por eth2) no se cuentan;
  `{192.168.100.50, UDP}` tiene 0 filas en todo el histórico. La simetría no sale del hook actual.
- dnsperf 0 consultas perdidas: el firewall no bloqueó .50 en ninguna carga.
- REFUTADO "la cabeza dispara con flujos de 1 paquete": los eventos DNS también llegan como
  `Packets: 1 fwd, 0 bwd`.

## 5. Qué hace disparar a la cabeza (mini flood, 6 000 pkts, seq 4814–4874)

`scripts/d280_ddos_feat_tab.sh` sobre la línea `DDoS Features:` completa:
- **El discriminador es `escalation` (traffic_escalation_rate)**: todos los `class=1` visibles tienen
  escalation 0,006–0,042; los `class=0` con rasgos, 0,001–0,006 (solape en ~0,006, lo decide
  entropy u otra). En DNS, escalation = **0,000** en los 2 316 eventos → nunca dispara.
  Misma víctima, mismo origen y misma tasa por víctima (100 pps) que el flood ⇒ escalation NO es la
  tasa por víctima; mide otra cosa (pendiente leer la fórmula).
- 4 653 eventos `class=0` con **symmetry=0 y todo a 0** = casi seguro los fast-alert de vector vacío
  (DEBT-FAST-ALERT-EMPTY-FEATURES-001). Sin verificar: la tabla no separa FAST/NORM.
- Cota de recall sobre eventos CON rasgos (solo top-12 filas de cada clase): 891 disparan frente a
  ≥ 429 que no ⇒ ≲ 67 %. Hay que calcularlo completo.
- Hallazgo aparte: DNS con `Packets: 1` pero `Duration: 50 s` y `Flow Packets/s 0,52` (~26 pkts):
  conteo y duración de alcances distintos → DEBT-FLOW-COUNTS-SCOPE-MISMATCH-001.

## 6. Deuda (registrar en BACKLOG)

Nueva DAY280:
- DEBT-KERNEL-COUNT-GAP-CIC4-001 → **CERRADA** (artefacto del filtro horario).
- DEBT-LAB-VM-CLOCK-DRIFT-001: ~62–67 s de desfase client/defender en DAY279 con chrony activo;
  hoy ±2 s. Causa desconocida. Método: horas en el defender o episodios por CSV.
- DEBT-ML-DETECTOR-LAG-UNDER-LOAD-001: ver §3 (VERBOSE ≈ 1/3 tiempo real; sin él, joroba de 22 s).
- DEBT-XDP-INGRESS-ONLY-NO-SYMMETRY-001: el hook solo ve ingreso en eth2; sin simetría víctima↔origen.
- DEBT-FLOW-COUNTS-SCOPE-MISMATCH-001: ver §5.
- DEBT-LAB-CLIENT-NO-EGRESS-001: tras `client-setup` el client no tiene internet (MASQUERADE solo a eth1).
- DEBT-VAGRANT-HASHICORP-APT-KEY-001: `NO_PUBKEY FC9CA96ACA026560` en el repo de HashiCorp.
- Fuera de foco: nº de eventos no escala con qps (2 524 / 1 200 / 1 590).
  Siguen abiertas DAY279: DEBT-FIREWALL-GATES-ON-LEVEL1-001 (P0), DEBT-ML-DETECTOR-VERDICT-LOG-IS-L1-001,
  DEBT-FAST-ALERT-EMPTY-FEATURES-001, DEBT-DDOS-HEAD-UNIDIRECTIONAL-UDP-001 (reformular: el disparo va
  por escalation, no por 1 paquete), DEBT-FAST-DETECTOR-REASON-MISMATCH-001, DEBT-VERIFY-PROTOBUF-FIND-SLOW-001,
  DEBT-PROTO-DISTRIBUTE-PROFILES-001, comentario "10 features" en DDoSFeatures; y las de DAY277–278.

## 7. Artefactos DAY280 (sin commitear salvo Vagrantfile + patchers)

`scripts/`: `d280_kernel_gap.sh` (episodios por tiempo), `d280_episodes.py` (episodios + rango win,
último arranque), `d280_vm_clock.sh` (desfase VM↔host, en el Mac), `d280_udp_inventory.sh`,
`d280_dns_load.sh`, `d280_vw_raw.sh`, `d280_vw_lag.py` (retraso por ventana), `d280_vw_x_ddos.sh`
(cruce señal×cabeza por seq), `d280_event_blocks.sh` (bloques de log completos),
`d280_ddos_feat_tab.sh` (clase × rasgos DDoS).
Logs: `/vagrant/logs/lab/d280_*.txt`, `d279_ddos_windows.csv.bak`. El log actual del ml-detector
(VERBOSE) contiene: DNS 50/100/200 (seq 191–671), DNS 200 clientes (2127–2247), mini flood (4814–4874).

## 8. Siguiente sesión (orden propuesto)

1. **Leer la fórmula de serve de `traffic_escalation_rate`** (y `resource_saturation_score`) en el
   productor: `git grep -n "escalation" -- sniffer/ ml-detector/` (ml_defender_features.cpp,
   ring_consumer.cpp). Predicción escrita antes: qué mide y por qué da 0,000 en DNS y 0,01–0,04 en
   el flood con la misma tasa por víctima. Es el rasgo de mayor importancia del bosque (0,33, DAY255).
2. Tabla completa (no top-12) del mini flood separando FAST/NORM → recall real de la cabeza sobre
   eventos con rasgos, y confirmar que los 4 653 de vector vacío son los fast-alert.
3. FP de la cabeza sobre el ambiente (DAY279: 110/553 = 19,9 %): qué tráfico dispara y con qué escalation.
4. Decidir qué hace la cabeza con los fast-alert sin rasgos (no evaluarlos como flujo).
5. Diseño: ¿alimentar el concepto "escalation" desde la ventana por víctima del kernel (relativo a su
   línea base)? CUIDADO lección DAY255 (geo): cambiar la definición en serve sin cambiarla en train
   crea skew. Exige definición única train/serve o reentrenar.
6. Después de las cabezas: fusión (L411) y que el firewall obedezca `final_decision` (L583).