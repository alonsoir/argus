# CONTINUIDAD DAY269 — Paso 1 (palanca VERBOSE) CERRADO y MEDIDO. El FPR de A queda para hoy: dataset LIMPIO (logs-lab-clean ANTES del replay) + script parser. El log de DAY268 está contaminado (Neris + ambiente) — descartarlo, no rescatarlo a grep.

## Estado del commit (LISTO para entrar, independiente del FPR)
Edit del Makefile HECHO y verificado en runtime:
- Declarada `VERBOSE ?=` bajo `PROFILE ?= debug` / `CMAKE_FLAGS := ...`.
- `ml-detector-start`: `cd /vagrant/ml-detector/build-debug` → `cd $(ML_DETECTOR_BUILD_DIR)`
  (usa la var canónica profile-aware ya existente) + `./ml-detector` →
  `./ml-detector $(if $(VERBOSE),--verbose,)`.
- `firewall-start`: NO tocado (opción C quedó opcional; decidir si entra por simetría).
- `rag-ingester-start`: NO tocado A PROPÓSITO (se depreca; no invertir en él).
  Commit sugerido:
  *"feat(makefile): palanca VERBOSE + build-$(PROFILE) en ml-detector-start (cierra arranque mudo del log en debug)"*
  PENDIENTE mañana: `git add Makefile && git commit` + PR a main (main protegida).

## HECHOS DAY268 (medidos, no re-litigar)
- **Palanca VERBOSE funciona**: `pgrep -af ml-detector` → `5080 ./ml-detector --verbose`.
  El binario recibe el flag; spdlog baja a debug; volcado L185-189 VIVO.
  `grep -m5 '[debug].*Feature['` → salen las 23 features con nombre y valor. Arranque
  mudo CERRADO (en debug, que es el default y lo que se corre). **Paso 1 = HECHO.**
- **Herencia de VERBOSE por command-line: automática.** `make pipeline-start VERBOSE=1`
  propaga el flag hasta `ml-detector-start` SIN tocar `pipeline-start` (make exporta las
  vars de command-line a los $(MAKE) hijos). Verificado por pgrep. **NO hace falta** la
  línea `VERBOSE=$(VERBOSE)` en pipeline-start. Backlog cerrado antes de abrirlo.
- **Formato del bloque de features (paso 3, capturado):** cada bloque abre con
  `📦 Event received: id=...` → `Feature Extraction:` → `Flow: <ip:port> -> <ip:port> (PROTO)`
  → `Duration:` → `Packets: N fwd, M bwd, T total` → `Bytes: ...` → 23 líneas `Feature[N] <nombre> : <valor>`.
  Clave de agrupación robusta = línea `Flow:` (5-tupla). Delimitador de bloque = `Feature Extraction:`.
- **El replay SÍ llega al extractor por eth1** (descartado el miedo eth1/eth2): los bloques
  traen `Flow: 147.32.84.165:...` = IP maliciosa del ground-truth CTU. Camino
  sniffer→ml-detector OK.
- **Replay Neris terminó**: `Actual: 320524 packets in 67.44s`, `5.24 Mbps` (pediste 10; el
  techo real lo pone el artefacto MTU de VirtualBox — `Message too long errno=90`, HECHO
  conocido de DAY145, NO es error del pipeline), `19135 flows`, `Failed: 2630 (~0.8%)`.
- **Hay dataset utilizable, NO es un fantasma total**: `grep -c 'bwd, [1-9]'` = 7756 (tráfico
  bidireccional abundante); centinela de 1-paquete `Fwd IAT Min : 30000...` = solo **17**
  ocurrencias (residual, NO el patrón). El susto de "todo son flujos degenerados" fue un
  `tail` desafortunado + lectura precipitada; corregido por medición.

## CONTAMINACIÓN del log DAY268 (por esto NO se midió el FPR hoy)
- El log `ml-detector.log` MEZCLA Neris (03:37+) con tráfico ambiente (03:09-03:10) porque
  NO se rotó antes del replay. Conteos crudos a grep son AMBIGUOS:
  2998 bloques vs 3425 `Packets: 0...0` vs 7756 `bwd,[1-9]` NO cuadran → multi-match por
  bloque (líneas Packets Y Bytes casan patrones) + mezcla temporal. **Ninguno es el número
  que importa.** El número real (flujos de Neris bien formados aptos para A) solo lo da el
  PARSER leyendo bloques completos, no grep.
- **Decisión: descartar este log.** No rescatar a grep. Mañana, dataset limpio de cero.

## PENDIENTE DAY269 (en orden, despacito)
1. **Commit + PR del Makefile** (arriba). Cierra el trabajo ya medido antes de abrir frente nuevo.
2. **Dataset LIMPIO**: pipeline arriba con verbose + rotar log JUSTO antes del replay:
    - `make pipeline-start VERBOSE=1`
    - `vagrant ssh -c "pgrep -af ml-detector"` → confirmar `./ml-detector --verbose`
    - `make logs-lab-clean`  ← INMEDIATAMENTE antes del replay (log = solo Neris)
    - `make test-replay-neris`
    - OJO recursos host: client+suricata cayeron `aborted` a la vez en DAY268 (host corto de
      RAM/CPU). Si vuelve a caer a mitad de Neris → problema del Mac, no de aRGus.
3. **Script FPR** (Python, offline, esqueleto en fichero de apoyo): parsear bloques por
   `Feature Extraction:` / clave `Flow:` (5-tupla) → clasificar cada bloque en
   {vacío: Packets 0/0/0 | degenerado: 1-paquete/centinela | bueno: bwd≥1} → sobre los BUENOS
   seleccionar los 7 índices distintos de A del vector de 23 → reconstruir vector de 9 en
   orden de A (duplicar los 2 pares alias) → `predict_proba` con `ddos_head_A.pkl` →
   contar `>0.5` Y `>0.7`. **Neris no tiene DDoS → todo positivo = FP (especificidad).**
   Reportar: FP a ambos umbrales, y desglose {buenos / vacíos / degenerados} para que el
   número sea auditable.
4. Con el FPR de A medido: decidir cableado (PENDIENTE 3 de DAY268) A sola / A+regla Syn /
   cabeza nueva con flags.

## Mapa A→índice level1 (de DAY267, para el script — no re-derivar)
Las 9 de A salen del vector level1 de 23 (`feature_extractor.cpp::extract_level1_features`).
7 señales independientes (2 pares alias: A#0≡A#7 total_forward_bytes; A#1≡A#8 total_backward_bytes,
medido INOCUO — mismas medianas train). A trata bwd=0 como firma de ataque (medianas bwd de
train todas 0) → los flujos fwd-solo son los sospechosos nº1 de FP. Umbral despliegue real
= 0.7 (config L149), A se entrenó/midió a 0.5 → medir AMBOS.

## Invariantes
`main` protegida (PR only). El Makefile es la verdad — nivel de log por Makefile, NUNCA el
JSON sellado a mano (muere en destroy→up: pasó en DAY268, `vagrant up` reprovisó y borró el
estado). `git grep`/fichero concreto, NUNCA `grep -rn` desde raíz. NO encadenar salidas
grandes. Compilador/medición = árbitro. HECHO ≠ SOSPECHADO. **Rotar el log ANTES de cada
replay que vaya a medir** (lección DAY268).

## Backlog afloradas DAY268 (anotar, NO perseguir)
- `ml-detector-start` no fue idempotente en una corrida (`duplicate session` pese al
  `kill-session` previo) → sesión tmux colgada tras la caída. Se resolvió con
  `pipeline-stop` + verificar `tmux ls` sin sesiones. Vigilar si reaparece.
- Warning GPG apt en provisión: `NO_PUBKEY FC9CA96ACA026560` (repo HashiCorp). No bloquea
  (bootstrap enterprise termina OK), pero se vuelve fallo duro si HashiCorp rota claves.
- `test-replay-neris` sobre VirtualBox mide throughput bien (uso DAY145) pero el artefacto
  MTU degrada la calidad de flujo — ~0.8% failed. Suficiente para FPR (7756 flujos bwd),
  pero si el FPR sale raro, sospechar calidad de replay antes que A.
- Propagar `--verbose` a otros componentes (sniffer/firewall/etcd/rag): SOSPECHADO que sus
  parsers acepten el flag (solo medido en ml-detector). Medir parser de args de cada uno
  ANTES de cablear, o un `pipeline-start VERBOSE=1` podría tumbar un componente con getopt
  estricto.