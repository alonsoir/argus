# Prompt de continuidad — aRGus NDR, DAY284 → DAY285

Reglas de trabajo (sin cambios): medir, no votar; predicción escrita antes de medir; comandos
separados o cada salida a su fichero; nunca `grep -rn` desde la raíz (usar `git grep` o el fichero
concreto); los scripts los ejecuta Alonso en su VM; scripts como bloque `cat > f <<'EOF'`; si algo no
da lo esperado, parar; `LC_ALL=C` en todo script con aritmética en awk. Tras un cambio, compilar TODO
el pipeline (`make pipeline-build PROFILE=production`, ~1 h), no un componente. Dar comandos exactos,
en orden, con dónde se ejecuta cada uno.

Operativa: targets del Makefile raíz en el **Mac**; scripts y patchers en el **defender** desde
`/vagrant`; tráfico en el **client** (`eth1`). Arranque:
`make pipeline-start PROFILE=production FORCE_ALL_HEADS=1` (opcional `SNIFFER_LOG=` y
`ML_DETECTOR_LOG=` para mandar un log a `/tmp/argus-lab/`). Comprobar binario vivo y destino del log:
`sudo readlink -e /proc/$(pgrep -o -x sniffer)/cwd` y `sudo ls -l /proc/$(pgrep -o -x sniffer)/fd/1`.
Protocolo de corrida: `sudo truncate -s 0` del log JUSTO antes de `d284_sampler.sh 480 5 SALIDA`
(acepta `LOG=`); replay ~1 min después:
`sudo tcpreplay --intf1=eth1 --pps=100 --limit=12000 /vagrant/datasets/cicddos2019/_0125_50k_lab.pcap`.
Usar el reloj del defender (el del client no sirve para tiempos).
`make up` en macOS 15.8.1+ depende de `vagrant_port_check_fix.rb` (imprime `[argus] port-check fix ACTIVO`).

## 0. Estado de git

Rama `feat/ddos-head-contract`, NO mergeada, working tree limpio al cerrar DAY284 (antes del commit
de docs). Comprobar con `git fetch` y `git log --oneline -10 origin/feat/ddos-head-contract`.

## 1. Lo que DAY284 dejó medido (detalle en `docs/BACKLOG.md`, sección DAY284)

- DEBT-SNIFFER-CONSUMER-THROUGHPUT-001 CERRADA: era log síncrono por evento sobre vboxsf que
  serializaba tres hilos en `std::cout`. Arreglado tras `g_verbosity`: 40 → 101 ev/s, cola 110 s → <10 s.
- El defender tiene 6 vCPUs (no mononúcleo).
- Descartes ZMQ: `dontwait` + `rcvhwm` 1000 del ml-detector → miles de mensajes perdidos cuando el
  ml-detector se satura. `send_timeout_ms` es config muerta.
- ml-detector: más lento que la llegada (6,5 min para 120 s de replay); **52 % de sus inferencias son
  fast alerts** (13 611/26 182) que pasan por todas las cabezas sobre un vector constante. No existe
  desvío para ellas en `ml-detector/src`.

## 2. Orden propuesto para DAY285

1. **Fast alert fuera de las cabezas (decisión DAY281 punto 4, ahora con beneficio medido).**
   Primero leer: `ml-detector/src/zmq_handler.cpp` alrededor de L400–440 (fusión `[DUAL-SCORE]`) y el
   punto de entrada del mensaje (dónde se decide level1/level2). Hoy la alerta solo se distingue por
   el prefijo `fast-alert-` del `event_id` (sniffer L1252): valorar un campo explícito en el proto antes
   que depender del prefijo. Diseño objetivo: la fast alert no pasa por las cabezas; entra a la fusión
   como señal propia y se correlaciona con los eventos de flujo de la misma víctima/5-tupla.
   Predicción escrita antes de medir; criterio de hecho: con el mismo replay, 0 inferencias de cabeza
   sobre `fast-alert-*` y menos descartes ZMQ.
2. **`[ZMQ-DROP] descartados=N en los últimos 10 s`** en el sniffer, siempre visible (sin verbose),
   sustituyendo a la línea `[ERROR]` por mensaje.
3. **`[VICTIM-WINDOW]`, `[HEAD-SCORES]`, `[DUAL-SCORE]` tras `--verbose`** en el ml-detector
   (`VERBOSE=1` para el trabajo de las cabezas).
4. **Re-medir** con 1–3 aplicados, log del ml-detector en `/vagrant`: descartes ZMQ y tasa del
   ml-detector durante la llegada.
5. **A/B de contención del host**: `vagrant halt suricata zeek` y repetir la corrida.
6. Después sigue el orden DAY283: D1 (definición única rasgo a rasgo, H1/H2/H3; recordar DAY255:
   cambiar la definición en serve sin reentrenar crea skew), dataset por el mismo código, fusión +
   firewall obedeciendo final_decision.

Contexto de Alonso: solo la cabeza DDoS está en foco; ransomware, traffic e internal no son fiables
todavía y NO se desactivan. La heurística rápida de ransomware se dispara con el flood DDoS (anotado,
fuera de foco).

Siguen abiertas: DEBT-FIREWALL-GATES-ON-LEVEL1-001 (P0), DEBT-ML-DETECTOR-VERDICT-LOG-IS-L1-001,
DEBT-ML-DETECTOR-LAG-UNDER-LOAD-001 (ahora con causas medidas: log por evento + fast alerts),
DEBT-ML-DETECTOR-EVENT-PER-PACKET-001, DEBT-DDOS-HEAD-* de DAY281, DEBT-SNIFFER-ZMQ-SILENT-DROP,
DEBT-VAGRANT-PORT-CHECK-MACOS-001, y las de DAY283.