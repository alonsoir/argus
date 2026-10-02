# Prompt de continuidad — aRGus NDR, DAY285 → DAY286

Reglas de trabajo (sin cambios): medir, no votar; predicción escrita antes de medir; comandos
separados o cada salida a su fichero; nunca `grep -rn` desde la raíz (usar `git grep` o el fichero
concreto); los scripts los ejecuta Alonso en su VM; scripts como bloque `cat > f <<'EOF'`; si algo no
da lo esperado, parar; `LC_ALL=C` en todo script con aritmética en awk. Tras un cambio, compilar TODO
el pipeline (`make pipeline-build PROFILE=production`, ~25–60 min), no un componente. Dar comandos
exactos, en orden, con dónde se ejecuta cada uno.

**Foco único: arreglar las cabezas de detección, empezando por DDoS.** Las deudas y diseños nuevos de
DAY285 (sección DAY285 de `docs/BACKLOG.md`) son backlog: no se abren ahora. Después de las cabezas
viene la actualización del paper.

Operativa: targets del Makefile raíz en el **Mac**; scripts y patchers en el **defender** desde
`/vagrant`; tráfico en el **client** (`eth1`). Arranque:
`make pipeline-stop` y `make pipeline-start PROFILE=production FORCE_ALL_HEADS=1` (`VERBOSE=1` para
ver las líneas por evento: `[HEAD-SCORES]`, `[DUAL-SCORE]`, `[VICTIM-WINDOW]`, detecciones). Logs en
`/vagrant/logs/lab/sniffer.log` y `/vagrant/logs/lab/ml-detector.log`; comprobar con
`sudo readlink -e /proc/$(pgrep -o -x ml-detector)/exe` y `sudo ls -l /proc/$(pgrep -o -x ml-detector)/fd/1`.
El ml-detector arranca sin `-c`: usa `../config/ml_detector_config.json` relativo a `build-production`.
Protocolo de corrida: `sudo truncate -s 0` de los dos logs, ~1 min, `date` en el defender,
`sudo tcpreplay --intf1=eth1 --pps=100 --limit=12000 /vagrant/datasets/cicddos2019/_0125_50k_lab.pcap`
en el client, `date` al acabar. El `📊 Stats` del ml-detector sale **cada 60 s**: drenado = dos líneas
seguidas con el mismo `processed` (más allá del ambiente, ~1 msg/s). Usar el reloj del defender.

## 0. Estado de git

Rama `feat/ddos-head-contract`, NO mergeada. Commits DAY285: `829267e4` (EventKind, [ZMQ-DROP],
logs a debug, resúmenes) y `perf(ml-detector)` (rag_logger/csv_writer apagados, guarda de plugins),
más el commit de docs. Comprobar con `git fetch` y `git log --oneline -10 origin/feat/ddos-head-contract`.

## 1. Lo que DAY285 dejó medido (detalle en `docs/BACKLOG.md`, sección DAY285)

- Fast alert y ventana ransomware fuera de level1 y de las cabezas (`event_kind = 37`); decisión
  aguas abajo neutra (`final = fast`).
- Logs mínimos por defecto; resúmenes cada 10 s siempre visibles: `[ZMQ-DROP]` (sniffer),
  `[ZMQ-DROP-OUT]` y `[DETECCIONES]` (ml-detector).
- El ml-detector va al ritmo de llegada a 100 pps: drena <20 s tras el replay (antes 6,5 min). Causa
  dominante: el RAG Logger creaba 2 ficheros cifrados por evento sobre vboxsf. 0 descartes.
- Bajo el flood el firewall no actúa (decide por level1, que dice BENIGN); la cabeza DDoS marca el
  flujo y su veredicto no llega a nada.

## 2. Orden para DAY286 (el de DAY283, ahora sin ruido de rendimiento)

1. **D1 — definición única rasgo a rasgo de la cabeza DDoS** (H1/H2/H3 del inventario DAY282/DAY283;
   leer esas secciones del BACKLOG antes de proponer nada). Recordar DAY255: cambiar la definición en
   serve sin reentrenar crea skew; el contrato de rasgos debe ser único y compartido train/serve.
   Recordar DAY281: el ml-detector recalcula los 9 rasgos en
   `feature_extractor.cpp::extract_level2_ddos_features(nf)`; `disp=0,100` y `protocol=0` están
   hardcodeados; `escalation` serve = bytes/s por flujo /1e6 frente a "tasa de crecimiento" sintética.
   Preferencia de Alonso: calcular los rasgos en el sniffer si es factible al 100 % con lo que tiene.
2. **Dataset por el mismo código** que sirve (no por un generador aparte).
3. **Fusión + firewall obedeciendo `final_decision`**: lista explícita de señales habilitadas en el
   JSON del ml-detector, al principio solo la cabeza DDoS; level1 y el fast de ransomware observados y
   registrados pero fuera de la decisión. Cierra DEBT-FIREWALL-GATES-ON-LEVEL1-001 (P0). Política de
   respuesta graduada y reversible (DAY269).

Medida a incluir en el trabajo de la cabeza: falsos positivos sobre ambiente (tras el replay, ~4
`[DETECCIONES] ddos` cada 10–40 s) y la subida TCP legítima de 50 KB/s (DAY281: 100 % class=1).

Contexto de Alonso: ransomware, traffic e internal no son fiables todavía y NO se desactivan. La
heurística rápida de ransomware se dispara con el flood DDoS (anotado, fuera de foco).

Siguen abiertas: DEBT-FIREWALL-GATES-ON-LEVEL1-001 (P0), DEBT-ML-DETECTOR-VERDICT-LOG-IS-L1-001,
DEBT-ML-DETECTOR-EVENT-PER-PACKET-001, DEBT-DDOS-HEAD-* de DAY281, las de DAY283,
DEBT-VAGRANT-PORT-CHECK-MACOS-001, y las nuevas de DAY285 (backlog). Antes del merge a main:
decidir DEBT-TEST-PARQUET-LEFTOVER-LOGS-001.