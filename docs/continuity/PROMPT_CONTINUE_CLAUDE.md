# Prompt de continuidad — aRGus NDR, DAY286 → DAY287

Reglas de trabajo (sin cambios): medir, no votar; predicción escrita antes de medir; comandos
separados o cada salida a su fichero; nunca `grep -rn` desde la raíz (usar `git grep` o el fichero
concreto); los scripts los ejecuta Alonso en su VM; scripts como bloque `cat > f <<'EOF'`; si algo no
da lo esperado, parar; `LC_ALL=C` en todo script con aritmética en awk. Tras un cambio, compilar TODO
el pipeline (`make pipeline-build PROFILE=production`, ~25–60 min). Dar comandos exactos y completos, en
orden, con dónde se ejecuta cada uno (Mac / defender / client). Patchers atómicos e idempotentes con
`--check` / `--apply`.

**Foco único: la cabeza DDoS.** Lo demás va al backlog (ver sección DAY286 de `docs/BACKLOG.md`).

Operativa: targets del Makefile raíz en el **Mac**; scripts y patchers en el **defender** desde
`/vagrant` (rutas absolutas); tráfico en el **client** (`eth1`). Arranque:
`make pipeline-stop` y `make pipeline-start PROFILE=production FORCE_ALL_HEADS=1` (`VERBOSE=1` para las
líneas por evento: `[DDOS-V2]`, `[VICTIM-WINDOW]`, `[HEAD-SCORES]`; con VERBOSE el drenado es lento).
Logs: `/vagrant/logs/lab/{sniffer,ml-detector}.log` (rotar con `sudo truncate -s 0`). Ventanas por
víctima del kernel: `/vagrant/logs/lab/ddos_windows.csv`. Replay:
`sudo tcpreplay --intf1=eth1 --pps=100 --limit=N /vagrant/datasets/cicddos2019/_0125_50k_lab.pcap`.

## 0. Estado de git

Rama `feat/ddos-head-contract`, NO mergeada. Commits DAY286: `d9901d67` (contrato v2 en el sniffer,
campos 11–15) y el commit de H2 (campo 14 + definición única de `ddos_window_ms`). Pendiente de commit:
la sección DAY286 de `docs/BACKLOG.md` y este prompt. Comprobar con `git fetch` y
`git log --oneline -5 origin/feat/ddos-head-contract`.

## 1. Lo que DAY286 dejó medido

- **Contrato DDoS v2 (8 rasgos, solo tráfico entrante)** calculado una vez en el sniffer y verificado E2E:
  `syn_ack_ratio`, `mean_packet_size`, `reflection_signature`, `packet_size_entropy`, `flow_packet_count`,
  `flow_completion_rate`, `victim_rate_ratio`, `victim_pps`. Flood: 482 B, entropía 0, 100 pps. Subida
  legítima: 1090 B, entropía 0,9, completion 0,5, 50 pps. Reflexión: `refl = 1`.
- `victim_rate_ratio` = EWMA por víctima con dos alfas (α = 0,1; α/60 si clave caliente ≥ 30 ventanas y
  ratio ≥ 5; suelo 10 pps). Equivalencia offline ↔ implementación: 0 discrepancias.
- El ml-detector **todavía no come** el contrato v2: sigue con `extract_level2_ddos_features` (viejo) y el
  bosque sintético. Solo lo observa con `[DDOS-V2]`.
- Corrección DAY270: el flood NO son flujos de 1 paquete (la línea `Packets:` del ml-detector engaña).
- La captura no ve la vuelta en tráfico que termina en el defender, y el código de flujos parte cada
  sentido en dos flujos (DEBT-SNIFFER-FLOW-UNIDIRECTIONAL-001, backlog; no bloquea DDoS).

## 2. Siguiente: paso 2 — dataset por el mismo código

Diseñar antes de escribir nada (predicción por decisión):

1. **Cómo recoger `ddos_embedded` v2 sin VERBOSE** (la línea `[DDOS-V2]` es debug y frena el drenado):
   ¿el CSV o el bronce del ml-detector ya serializan `ddos_embedded`? Medir antes de crear nada.
2. **Qué pcaps etiquetados**: CICDDoS2019 (varios tipos: SYN, UDP, reflexión DNS/NTP/LDAP…) reescritos a la
   topología del lab (método DAY270) + benigno real (ambiente, subida TCP, DNS). Cuidado con el colapso de
   orígenes de `tcprewrite` (H1) y con el tope de 200 paquetes por flujo (DEBT-SNIFFER-FLOW-PACKET-CAP-200).
3. **Etiquetado** por 5-tupla / ventana de replay, sin depender de columnas de CIC.
4. Entrenar **sin scaler** (bosque invariante a escala), medir importancias, y solo entonces quitar rasgos.
5. Después: el ml-detector lee `ddos_embedded` v2 (lista de rasgos de `ml_detector_config.json` L179–187
   actualizada en el mismo commit) y el nuevo `.hpp`.

Medidas a incluir: FP sobre ambiente y sobre la subida TCP legítima de 50 KB/s (hoy 100 % class=1 con el
bosque viejo).

Después de la cabeza: fusión + firewall obedeciendo `final_decision` (DEBT-FIREWALL-GATES-ON-LEVEL1-001, P0),
con lista explícita de señales habilitadas (al principio solo DDoS). Luego, actualización del paper.

Siguen abiertas: las de DAY281–285 y las nuevas de DAY286 (backlog).