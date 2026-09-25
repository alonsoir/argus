# Prompt de continuidad — aRGus NDR, DAY279 → DAY280

Reglas de trabajo (sin cambios): medir, no votar; predicción escrita antes de medir; comandos
separados o cada salida a su fichero; nunca `grep -rn` desde la raíz (usar `git grep` o el fichero
concreto); los scripts los ejecuta Alonso en su VM; scripts como bloque `cat > f <<'EOF'`; si algo
no da lo esperado, parar.
Nuevas DAY279:
- No reinventar lo que ya existe en el Makefile raíz (regenerar protobuf = `make proto`; los targets
  de componente copian el .pb a `build-$(PROFILE)/proto` SIEMPRE; `make pipeline-build` recompila todo).
- Los scripts de medida con aritmética en awk van con `LC_ALL=C` (la VM está en es_ES: "0.75"+0 = 0).
- Las líneas "Event received", "Flow:", "DDoS: class=" son DEBUG: sin `VERBOSE=1` no existen y no
  se puede cruzar nada por evento. Para medir cabezas: `make pipeline-start FORCE_ALL_HEADS=1 VERBOSE=1`.
- `proto-verify` tarda ~40 min (find sobre /vagrant entero). No usarlo para el día a día; basta
  `grep -c victim_window <build-debug>/proto/network_security.pb.h`.

Foco: la cabeza DDoS por separado. Las demás cabezas fuera de foco.

## 1. Re-análisis de cic2 (DAY278) sobre el log guardado

Log intacto en `/vagrant/logs/lab/d278_ml-detector.log.bak` (ventana cic2 03:12:49–03:21:09).
- El flood es un único grupo: 192.168.100.50 → 192.168.100.1 UDP. .50 genera además tráfico normal
  (DNS a 8.8.8.8/1.1.1.1, TCP 1514 a Wazuh .12): contar "por IP" mezcla flood y fondo.
- Eventos del flood en REPLAY = 2250: **1596 fast-alert** (71 %) + 654 normales.
    - Los fast-alert llevan los 23 rasgos a CERO (`Packets: 0`): la cabeza DDoS devuelve 0.4717
      (= nota del vector vacío) → class=0 siempre.
    - En los normales la cabeza acierta 512/654 = **78,3 %**.
    - DNS de .50: class=1 en 24/83 = **28,9 %** (FP ≥ recall). TCP nunca dispara.
    - Con datos, la cabeza dispara por "UDP de 1 paquete sin vuelta" (`symmetry=1.0`); `entropy=0.000`
      y `disp=0.100` en todos los eventos inspeccionados.
- Los 1596 fast-alert salen del ml-detector con `final=0.75 ≥ malicious_threshold=0.7` ⇒
  `final_classification=MALICIOUS` y `final_decision=DROP`. **El ml-detector SÍ recomendó bloquear .50.**
  El log `✅ BENIGN` (zmq_handler.cpp L864–870) imprime la etiqueta de level1, no final_classification.
- **El firewall no obedece al ml-detector**: `firewall-acl-agent/src/api/zmq_subscriber.cpp:583`
  `if (!ml.attack_detected_level1()) return;` (debug, silencioso) y usa `level1_confidence` como
  confidence. Ignora final_decision / final_classification / overall_threat_score.
  Explica: .50 nunca bloqueado (level1 BENIGN) y Neris bloqueado con threat_category=NORMAL.
  El veto de level1 existe DOS veces: ml-detector L549 y firewall L583.
- El fast-alert es la heurística de RANSOMWARE (ring_consumer.cpp `send_fast_alert`, llamada en L530;
  reason "high_external_ips" hardcodeado; threat_category RANSOMWARE_FAST_DETECTION; score =
  `fast_detector_config_.ransomware.scores.alert` = 0.75). No es señal DDoS.
- Corrección de DAY278 §2: para .50 el final no era 0.10 sino 0.75 en los fast-alert.

## 2. Implementado y commiteado: la señal del kernel llega al ml-detector (opción a)

Commit `e2cac4b0` en `docs/ml-heads-grieta-b` (14 ficheros; patcher `patch_victim_window_d279.py`).
- proto: `message VictimWindow {victim_ip, protocol, d_pkts, d_bytes, window_ms, window_seq,
  snapshot_age_ms}` + `NetworkSecurityEvent.victim_window = 36`.
- `sniffer/include/ddos_victim_board.hpp` (nuevo): snapshot inmutable por ventana, shared_ptr
  compartido lector→consumer creado en main (sin punteros colgantes). Guarda TODAS las víctimas
  (el tope kDdosMaxRowsPerWindow es solo del CSV). No publica la baseline (t_start_ns==0).
- Lector: `set_board()`, publica en `poll_once()`; **el CSV pasa a ser opcional** (antes, sin ruta
  CSV el lector no arrancaba, ni en main.cpp ni en start()).
- RingBufferConsumer: `set_victim_board()` + `stamp_victim_window()` en los DOS sitios donde nace
  un evento (camino normal y fast-alert).
- ml-detector: línea INFO `[VICTIM-WINDOW] event=…, victim=…, proto=…, d_pkts=…, d_bytes=…,
  window_ms=…, seq=…, age_ms=…` (o `absent`) tras `[DUAL-SCORE]`. SOLO observación: no entra en
  ninguna cabeza ni en final_score.
- Semántica: sin campo = lector apagado / sin snapshot; con campo y d_pkts=0 = víctima sin tráfico.
  El evento lleva la ÚLTIMA ventana CERRADA ⇒ la señal va hasta 1 ventana (~1 s) por detrás.
- Test: `make sniffer-ddos-board-test` (verde).

## 3. Medido con la señal nueva

- cic3 (FORCE_ALL_HEADS=1, sin VERBOSE, 06:04:04–06:12:27): eventos del flood con
  `d_pkts=100, d_bytes=48200 (=100×482 B exacto), window_ms≈1000, age_ms<1000`. 9 `absent` (arranque).
  Serie del ml-detector con picos de 458 en ventanas de ~1000 ms (hipótesis: ráfagas de recuperación
  de tcpreplay en VirtualBox + sesgo de muestreo; NO verificada).
- cic4 (FORCE_ALL_HEADS=1 VERBOSE=1, 06:33:10–06:41:30), cruce por evento, `id_mismatch=0`:

| Detector | Recall sobre el flood (por evento) | FP sobre el resto |
|---|---|---|
| Cabeza DDoS actual | 3033 / 20 679 = 14,7 % | 110 / 553 = 19,9 % |
| Señal kernel, umbral vpps ≥ 50 | 20 463 / 20 679 = 99,0 % | 0 / 553 = 0 % |

Fast-alert del flood: la cabeza 0 %, la señal 50+ en 16 178/16 349.
CAVEATS: el 0 % FP es contra el ambiente de ESTE lab (nadie más recibe UDP > 10 pps); un servidor
legítimo cargado (resolver DNS, NTP) tendría vpps alto. El umbral 50 es de cubos, no calibrado.
La señal describe a la VÍCTIMA; el origen a bloquear lo pone el evento.
- CSV del lector, cic4 (sin sesgo): 493 ventanas, **suma 49 121** (esperado ≈ 49 999), max 202,
  2 ventanas < 60. Predicción FALLIDA: **faltan 879 paquetes (1,76 %)**. ABIERTO: ¿pérdida antes del
  hook (VirtualBox/eth2) o ventanas fuera del filtro de tiempo? Coherente con DAY274 (eth2 recibió
  46 595 de 50 000 una vez, sin explicar).

## 4. Deuda (registrar en BACKLOG)

Nueva DAY279:
- DEBT-FIREWALL-GATES-ON-LEVEL1-001 (**P0**): zmq_subscriber.cpp:583 filtra por
  attack_detected_level1 e ignora final_decision. Sustituye a DEBT-FIREWALL-BLOCKS-NORMAL-CATEGORY-001.
- DEBT-ML-DETECTOR-VERDICT-LOG-IS-L1-001: L864–870 loguea ATTACK/BENIGN por level1.
- DEBT-FAST-ALERT-EMPTY-FEATURES-001: fast-alert llega con 23 rasgos a 0; las cabezas evalúan un
  vector vacío (71 % de los eventos del flood).
- DEBT-DDOS-HEAD-UNIDIRECTIONAL-UDP-001: con datos, dispara con cualquier UDP de 1 pkt sin vuelta.
- DEBT-FAST-DETECTOR-REASON-MISMATCH-001: la heurística ransomware dispara sobre flood y ambiente.
- DEBT-LAB-AWK-LOCALE-001: LC_ALL=C en scripts de medida.
- DEBT-VERIFY-PROTOBUF-FIND-SLOW-001: verify_protobuf.sh recorre /vagrant entero por vboxsf.
- DEBT-PROTO-DISTRIBUTE-PROFILES-001: generate.sh distribuye a build/, no a build-$(PROFILE).
- DEBT-KERNEL-COUNT-GAP-CIC4-001: 879 paquetes sin contar en cic4 (abierto, ver §3).
- Cosmético: comentario "10 features" en `message DDoSFeatures` (son 9).
  Siguen abiertas de DAY278: DEBT-ML-DETECTOR-L2-NOT-IN-FINAL-SCORE-001, DEBT-RECIDIVISM-SAME-EPISODE-001,
  DEBT-FIREWALL-IPTABLES-RULES-NOT-IDEMPOTENT-001, DEBT-FORCE-ALL-HEADS-MISLABELS-ATTACK-001; y las de
  DAY277 (H3 overflow retry, stale binary, comment flag, autonomy whitelist H7, procedencia _lab.pcap,
  higiene .old/.orig).

## 5. Artefactos DAY279

- Scripts (sin commitear): `scripts/d279_ddos_by_ip.sh`, `d279_flood_by_evtype.sh` (lanzar con
  LC_ALL=C), `d279_vw_series.sh HH:MM:SS HH:MM:SS [victim] [proto]`, `d279_vw_x_ddos.sh HH:MM:SS HH:MM:SS`.
- Horas y salida tcpreplay: `/vagrant/logs/lab/d279_cic3_times.txt`, `d279_cic4_times.txt`,
  `d279_cic3_tcpreplay.txt`, `d279_cic4_tcpreplay.txt` (50 000 pkts, 100,00 pps, 0 fallidos, 766 flows).
- Replay (VM client, eth1 = 192.168.100.50):
  `sudo tcpreplay -i eth1 --pps=100 /vagrant/datasets/cicddos2019/_0125_50k_lab.pcap`
- El log actual del ml-detector contiene cic4 (VERBOSE). Rotar con `truncate -s 0`, nunca logs-lab-clean.

## 6. Siguiente sesión (orden propuesto)

1. Cerrar el hueco de 879 paquetes: mismo cálculo sobre el CSV en la ventana de cic3; contadores de
   `ip -s link` de eth2 (defender) antes/después del replay; comparar con los 50 000 enviados.
2. Medir el FP de la señal con tráfico UDP BENIGNO de alta tasa (p. ej. carga DNS contra un resolver
   del lab) antes de dejar que la señal influya en nada.
3. Decidir cómo entra la señal en la cabeza DDoS: vpps absoluto vs relativo a la línea base de cada
   víctima (escalation / EWMA, Paso 4 del harness de DAY274). Contrato de la cabeza antes de la
   fusión: probabilidad calibrada + FP medido sobre fondo + recall sobre etiquetado.
4. Decidir qué hace la cabeza con los fast-alert sin rasgos (no evaluarlos como flujo).
5. Después de las cabezas: fórmula de fusión (L411) y que el firewall obedezca final_decision (L583).