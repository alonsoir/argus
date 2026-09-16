# CONTINUIDAD DAY271 — El veredicto de DAY270 está MEDIDO: level1 clasifica el flood DDoS real como BENIGN (13567 BENIGN / 1 ATTACK, recall≈0). La cascada mata el recall DDoS. Mañana: medir B (¿la cabeza DDoS aislada también dice benigno?) abriendo la compuerta a la fuerza, y con ese dato decidir el rediseño paralelo-fusión + unidad agregada.

## EL VEREDICTO (medido, no re-litigar)
Sometido a un flood UDP real de CICDDoS2019 a través del pipeline íntegro (sniffer→extractor→level1),
**level1 clasificó 13567 flujos del flood como BENIGN y 1 como ATTACK** → recall ≈ 0.007%. Ceguera casi total.

Traza real de la decisión (el vocabulario del log — mis contadores `Running Level 2 DDoS`/`DDoS: class=1`
de DAY270 eran cadenas FANTASMA, no existen):
```
🤖 Level 1: label=0 (BENIGN), confidence=0.8999
[DUAL-SCORE] fast=0.0000, ml=0.1001, final=0.1001, source=DETECTOR_SOURCE_ML_PRIORITY
```
Reparto correcto con: `grep 'Level 1:' <log> | grep -oE 'label=[01] \((BENIGN|ATTACK)\)' | sort | uniq -c`

### Mecanismo (hallazgo arquitectónico, material de paper)
- El flood son flujos de **1 paquete** (`1 fwd, 0 bwd`, ~482 bytes, UDP puerto alto). A nivel de flujo aislado
  es indistinguible de un datagrama UDP legítimo: todas las features Std/Var/IAT/Bwd colapsan a 0.
- **La firma DDoS NO vive en el flujo, vive en el AGREGADO** (miles de flujos, misma víctima, alta tasa).
  level1 clasifica flujo-a-flujo → estructuralmente ciego. No es peso mal entrenado; es **desajuste entre la
  unidad de decisión (flujo) y la unidad del ataque (conjunto)**.
- El 1 ATTACK de 13568 era idéntico al resto (1 fwd, 482 bytes): ruido de frontera, sin señal que perseguir.

## DECISIÓN DE ARQUITECTURA — ya no está abierta
DAY269 dejó el fork cascada-veto vs paralelo-fusión ATADO a este número. El número llegó:
**level1 BLOQUEA los DDoS reales → la cascada mata recall → el paralelo-fusión pasa a NECESARIO, no opcional.**
(ver [[reparacion-cabeza-ddos]] y la política de respuesta graduada/reversible de DAY269).

Corrección al modelo mental de Alonso (DAY270, con el HECHO delante): el cuello **NO es "las cabezas
interfieren entre sí"**. El flujo ni siquiera LLEGA a la cabeza DDoS — muere en `Level 1: BENIGN` y la
compuerta `zmq_handler.cpp:549` no se abre. El problema es (1) la compuerta level1 con poder de veto +
(2) la unidad-flujo. Separar cabezas es correcto pero INSUFICIENTE: ninguna cabeza que mire UN flujo
detecta el DDoS. La vía DDoS necesita **unidad de decisión AGREGADA (ventana por víctima)** y que
**level1 NO vetee**.

## PENDIENTE DAY271 (en orden, despacito) — MEDIR B ANTES DE REDISEÑAR
La discrepancia a dirimir con un número: Alonso apuesta "la cabeza DDoS funciona bien sola, las otras
interfieren"; Claude apuesta "la cabeza DDoS con unidad-flujo tampoco puede, el problema es la agregación".
**B lo dirime.**

1. **Abrir la compuerta a la fuerza (cambio mínimo, reversible).** En `ml-detector/src/zmq_handler.cpp`
   alrededor de la línea 549, el guard exacto:
   ```cpp
   if (label_l1 == 1 && confidence_l1 >= config_.ml.thresholds.level1_attack) { ... level2 DDoS ... }
   ```
   Cortocircuitar con un flag debug `force_all_heads` para que level2 DDoS corra SIEMPRE, sea cual sea
   el veredicto de level1. NO reescribir arquitectura; solo abrir la compuerta para observar.
   INVARIANTE: flag por Makefile, NUNCA JSON a mano (muere en destroy→up).
   ANTES de tocar: `sed -n '540,575p' ml-detector/src/zmq_handler.cpp` (ver el if completo y qué llama dentro).

2. **Correr el flood a 100pps con la compuerta abierta** (ver artefacto y método abajo). Ahora la cabeza
   DDoS SÍ se ejecuta sobre cada flujo del flood.

3. **Medir B: ¿qué dice `DDoSDetector::predict` (ddos_detector.cpp:11) sobre los flujos de 1 paquete?**
    - Predicción de Claude a contrastar: también BENIGN → confirmaría que el problema es unidad de agregación,
      no la cabeza. Fija esta expectativa ANTES de correr, o malinterpretarás el resultado como "la cabeza
      tampoco sirve" cuando la lectura correcta es "la cabeza sobre unidad-flujo no sirve, necesita agregada".
    - Si la cabeza DDoS SÍ marca estos flujos como ataque → gana Alonso (la interferencia entre cabezas era
      real), y el diagnóstico cambia. Ese sería un hallazgo CONTRA la hipótesis de Claude — lo que queremos.

4. **Con B medido, decidir la forma del rediseño:**
    - Si la cabeza necesita unidad AGREGADA (apuesta Claude): el trabajo es construir la ventana por víctima
      que la alimente (recordar: `source_ip_dispersion` ya es feature de ventana 30s desde el TimeWindowAggregator
      del processor de ransomware, ver [[grieta-b-source-ip-dispersion]]).
    - Si la cabeza ya discrimina por flujo (apuesta Alonso): el trabajo es solo quitar el veto de level1.
    - Probablemente ambos, pero el orden importa y B lo fija.

5. **Backlog de cabezas (Alonso, no perseguir aún):** revisar level1 (ataque global) e INTERNO. Deudas
   estructurales conocidas: `num_features()` hardcodeado a 10 en detectores Traffic e Internal (DDoS ya a 9);
   level1 arrastra su P0 = `Init_Win_bytes_forward` hardcodeado a 0.0f en serve (visto vivo en el flood:
   Feature[14]=0; OJO es UDP sin ventana TCP, así que 0 podría ser legítimo aquí — ambiguo, resolver mirando
   el código de serve antes de afirmar bug).

## MÉTODO DE REPLAY (ya resuelto DAY270 — reusar, no re-descubrir)
5 supuestos ocultos del harness Neris, todos medidos y superados:
1. Los chunks del PCAP CICDDoS2019 son por TAMAÑO (tcpdump rota a 191MB), no por ataque. El reloj interno
   NO cuadra con el CSV → identificar el ataque por CONTENIDO (`tshark -z io,phs`, `-z endpoints,ip`), no por hora.
2. DLT: cosmético (el warning de tcpreplay `unsupported DLT Ethernet 0x1` es ruido; ambos pcap son Ethernet).
3. El sniffer XDP en **eth1 es HOST-BASED** (solo tráfico destinado al host). El canal bueno es **eth2 GATEWAY
   (defender, 192.168.100.1)** que captura tránsito. Config en sniffer.json (host_interface eth1 mode1,
   gateway_interface eth2 mode2).
4. Reescribir IP+MAC del flood a la topología del lab. Corre EN el guest client (tiene tcprewrite; el Mac no):
   ```
   vagrant ssh client -c "tcprewrite \
     --infile=/vagrant/datasets/cicddos2019/_0125_50k.pcap \
     --outfile=/vagrant/datasets/cicddos2019/_0125_50k_lab.pcap \
     --dstipmap=0.0.0.0/0:192.168.100.1 --srcipmap=0.0.0.0/0:192.168.100.50 \
     --enet-smac=<MAC client eth1> --enet-dmac=<MAC defender eth2> --fixcsum"
   ```
   (MACs DAY270: client eth1 = 08:00:27:07:8c:2f ; defender eth2 = 08:00:27:6f:63:da — reconfirmar, cambian en destroy→up)
5. El ring buffer XDP→consumer se SATURA por pps: a 1000pps captura ~14%, a **100pps ~95%**. Medir con
   `bpftool map dump name stats` (delta antes/después del replay). **Replicar SIEMPRE a `--pps=100`.**
   El filtro de puertos del sniffer NO fue causa (default_action=capture, included_ports=[], excluded_ports=[22]).

### Artefacto listo y receta de corrida limpia
- PCAP reescrito: `datasets/cicddos2019/_0125_50k_lab.pcap` (50k pkts, src 192.168.100.50 → dst 192.168.100.1, UDP).
- Log del ml-detector: `defender:/vagrant/logs/lab/ml-detector.log`. ml-detector corre en `defender`.
- Arranque con verbose (imprescindible o no hay trazas de decisión): `make pipeline-stop && make pipeline-start VERBOSE=1`
  (VERBOSE en MAYÚSCULAS; confirmar `pgrep -af ml-detector` termina en `--verbose`; confirmar que un
  `grep -c 'Feature Extraction' <log>` sube con tráfico de ambiente antes de replicar).
- Receta:
  ```
  vagrant ssh defender -c "truncate -s 0 /vagrant/logs/lab/ml-detector.log"   # rotación in situ (fd O_APPEND vivo), NUNCA logs-lab-clean
  vagrant ssh client   -c "sudo tcpreplay -i eth1 --pps=100 /vagrant/datasets/cicddos2019/_0125_50k_lab.pcap"  # ~8 min
  vagrant ssh defender -c "grep 'Level 1:' /vagrant/logs/lab/ml-detector.log | grep -oE 'label=[01] \((BENIGN|ATTACK)\)' | sort | uniq -c"
  ```
- Ground-truth (clock-independiente): flood = src 192.168.100.50 → dst 192.168.100.1 (tras reescritura).

## INVARIANTES
`main` protegida (PR only). Rama de trabajo = `docs/ml-heads-grieta-b`. El Makefile es la verdad (nivel de
log y flags por Makefile, NUNCA JSON a mano — muere en destroy→up). `git grep`/fichero concreto, NUNCA
`grep -rn` desde raíz. NO encadenar salidas grandes. Rotar el log con `truncate -s 0` ANTES de cada replay
que vaya a medir (pipeline vivo). El compilador/parser/mapa es el árbitro. HECHO ≠ SOSPECHADO.

## BACKLOG (anotar, NO perseguir)
- `_0125_50k_lab.pcap` colapsa la dispersión de origen a 1 (src único). Para estresar `source_ip_dispersion`
  (grieta B) haría falta mapear a un RANGO de orígenes, no a uno. Otro experimento.
- Deuda de método para el paper: el ring consumer pierde el 86% de un flood a 1000pps → el throughput del
  consumer, no el modelo, acota la detección DDoS. Línea de i+d real (¿un solo hilo? ¿parseo por evento caro?
  ¿ring pequeño?).
- Herramientas sin commitear: `fpr_neris_A.py` (parser+buckets+eval candidato), `ddos_gate_start.sh`/target
  `ddos-gate-start` (driver de medición de compuerta; sus contadores GATE/FLAG apuntan a cadenas fantasma,
  arreglar con el vocabulario real `Level 1: label=...` antes de trackear).
- `ddos_head_A` (candidato offline) sigue sin cablear al pipeline; su relación con el fork Path A/Path B de
  Fase 2 sigue pendiente de aclarar. Recall Syn 0.577 (débil) — NO es "la cabeza funciona bien sola" sin medir.
- Warning GPG apt HashiCorp (`NO_PUBKEY FC9CA96ACA026560`) en provisión — no bloquea.