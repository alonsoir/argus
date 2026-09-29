# Prompt de continuidad — aRGus NDR, DAY283 → DAY284

Reglas de trabajo (sin cambios): medir, no votar; prediccion escrita antes de medir; comandos
separados o cada salida a su fichero; nunca `grep -rn` desde la raiz (usar `git grep` o el fichero
concreto); los scripts los ejecuta Alonso en su VM; scripts como bloque `cat > f <<'EOF'`; si algo
no da lo esperado, parar; `LC_ALL=C` en todo script con aritmetica en awk. Tras un cambio, compilar
TODO el pipeline (`make pipeline-build`), no un componente. Dar comandos exactos, en orden, con donde
se ejecuta cada uno.

Operativa: targets del Makefile raiz en el **Mac**; scripts y patchers en el **defender** desde `/vagrant`;
trafico en el **client** (interfaz del lab `eth1`). Logs: `/vagrant/logs/lab/ml-detector.log` y
`/vagrant/logs/lab/sniffer.log` (rotar con `truncate -s 0`, con el pipeline parado si se quiere limpio).
`make pipeline-start FORCE_ALL_HEADS=1` para que todas las cabezas puntuen.

**Perfil production (DAY283):** `make pipeline-build PROFILE=production` (~1 h) y
`make pipeline-start PROFILE=production FORCE_ALL_HEADS=1`. Todos los componentes usan
`build-$(PROFILE)`. Comprobar el binario vivo con `sudo readlink -e /proc/$(pgrep -o -x sniffer)/cwd`
(sin sudo, readlink falla en silencio porque el sniffer corre como root).

## 0. Estado de git

Rama `feat/ddos-head-contract` (desde main 83f93ca8). Commits DAY283: fix del golden vector (perfil
production), instrumentacion `[ML-TIME]`/`[ML-PHASE]` + scripts, docs (BACKLOG + este prompt).
Comprobar con `git fetch` y `git log --oneline -6 origin/feat/ddos-head-contract`. NO mergeada.

## 1. Lo que DAY283 dejo medido (detalle en `docs/BACKLOG.md`, seccion DAY283)

- `[ML-TIME]` y `[ML-PHASE]` en `sniffer.log` cada 10 s (acumulados; bucket b = [2^b, 2^(b+1)) ns).
  Delta entre dos lineas: `scripts/d283_phase_delta.sh ANTES DESPUES`.
- Coste de `run_ml_detection` en production: 51 µs/llamada en ambiente, 95 µs bajo subida TCP 50 KB/s.
  Cabeza DDoS: 6 µs de media (mediana 2–4 µs) en ambiente, 12,8 µs bajo carga. Ransomware = 47 % del coste.
  Extraccion desde el proto ≈ 100 ns. Debug solo ~2× mas lento que production.
- **D2 respondido:** inferir DDoS en el sniffer es asumible. El cuello real es otro:
  **el consumidor del ring saca ~40–90 eventos/s** (una inferencia por evento, `calls` ≈ `Paquetes
  procesados`). Un flood de 12 000 pkts a 100 pps se drena 3–4 min despues de acabar. El ML es < 1 % del
  presupuesto por evento (~10–25 ms). DEBT-SNIFFER-CONSUMER-THROUGHPUT-001.
- Perfil production estaba podrido (arreglado un `assert` que ademas pasaba en vacio con NDEBUG).
- `Paquetes enviados` clavado en 25 000 (sin investigar).

## 2. Orden propuesto para DAY284

1. **Caudal del consumidor del ring.** Primero mirar lo que ya existe: `process_raw_event`
   (ring_consumer.cpp ~524–640) cronometra con `start_time`/`end_time` → `update_processing_time`
   (~1169) → `total_processing_time_us`. Ver si se imprime y que abarca. Luego cronometrar el camino
   completo por evento (sondeo del ring → `handle_event` → populate → serializacion → ZMQ) con el mismo
   estilo de histograma. Prediccion antes de medir. Confirmar tambien si la cola esta en el ring
   (progresion completa de `Paquetes procesados` durante un drenaje).
2. **Repetir la carga 2** (CICDDoS2019, `sudo tcpreplay --intf1=eth1 --pps=100 --limit=12000
   /vagrant/datasets/cicddos2019/_0125_50k_lab.pcap` en el client). Foto de "despues" SOLO cuando
   `calls` vuelva al goteo del ambiente.
3. Mirar el 25 000 de `Paquetes enviados`.
4. Despues, el orden DAY283 sigue: D1 (definicion unica rasgo a rasgo, H1/H2/H3; recordar DAY255: cambiar
   la definicion en serve sin reentrenar crea skew), dataset por el mismo codigo, fast-alert como entrada
   propia a la fusion, fusion + firewall obedeciendo final_decision.

Contexto de Alonso: solo la cabeza DDoS esta en foco; ransomware, traffic e internal no son fiables
todavia y NO se desactivan (no seria realista). Lab mononucleo emulado en su portatil.

Siguen abiertas: DEBT-FIREWALL-GATES-ON-LEVEL1-001 (P0), DEBT-ML-DETECTOR-VERDICT-LOG-IS-L1-001,
DEBT-ML-DETECTOR-LAG-UNDER-LOAD-001, DEBT-ML-DETECTOR-EVENT-PER-PACKET-001, DEBT-DDOS-HEAD-* de DAY281,
y las nuevas de DAY283.