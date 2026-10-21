# DAY300 — E2E del reinicio del sniffer a mitad de un ataque (persistencia del estado por víctima)

Rama `fix/ddos-etapa1-histeresis`. Commits del día: b550baf0 (parada inmediata), 8b91651d (sigwait) y el
de este documento.

## Montaje

- Base benigna desde .51 a 10 pps durante 510 s (`benign_dns_ntp_17k_disjunto_src51.pcap`, sin tuplas repetidas).
- A los 90 s, ataque NTP desde .50 a 60 pps durante 360 s (`ntp_reflex_63k_disjunto_lab.pcap`).
  70 pps sobre la víctima {.1, udp}: razón ~7 frente a la base (> K_in = 3), pero < abs_pps = 200 (en frío no entra).
- A los 120 s de ataque detectado, reinicio del sniffer de tres formas. Las tres corridas empiezan sin CSV de estado.
- Orquestador `scripts/timebase/d300_reinicio_e2e.sh` (espera y anota instantes él mismo), cliente
  `d300_reinicio_client.sh`, análisis `d300_reinicio_analisis.sh` (corta el ml-detector.log con el sniffer ya
  parado). Captura en eth2 para contar el cable.

## Resultados

| Modo | Restauración | Marcados antes / después | Razón | DROP / ataque en cable | Sombra |
|---|---|---|---|---|---|
| antes (CSV borrado) | sin estado previo | 8980 / 0 | 0,000 | 8976 / 21600 = 0,416 | FIN a mitad (177 s) |
| ordenada (sniffer-stop) | 10 víctimas (1 bajo presión), volcado de hace 25 s | 8663 / 11304 | 1,305 | 19967 / 21600 = 0,924 | un episodio de 387 s |
| kill9 (pkill -KILL) | 10 víctimas (1 bajo presión), volcado periódico de hace 34 s | 8882 / 10982 | 1,236 | 19864 / 21600 = 0,920 | un episodio de 386 s |

Predicción escrita antes de medir: razón ≈ 0 en `antes` y 1,15-1,40 en `ordenada` y `kill9`
(≈ 189 s de ataque tras el rearranque frente a ≈ 145 s antes de la parada). Cumplida en las tres.

- Origen inocente .51: 0 DROP en las tres (su base incluye 1015 paquetes NTP).
- ml-detector y firewall cuadran: marcados = DROP (19967 y 19864); seq_recibidos = suma de eventos.
- Con estado restaurado, lo único sin marcar es el tiempo de sniffer caído (~25-30 s) y el primer segundo del
  ataque: ceguera física, no fallo de la restauración. Sin estado, el ataque bajo abs_pps se aprende como base y
  no se vuelve a marcar (0 DROP en ~190 s).
- `kill9` reproduce un corte de luz: sin volcado de parada, se restaura el último volcado periódico (≤ 60 ventanas).

Primera medida (`d300_reinicio_antes`) descartada para la tabla: el corte del log se tomó antes de lanzar
sniffer-stop (17 s de `vagrant ssh`), y 997 marcados del sniffer viejo cayeron del lado "después". El firewall,
con marcas de tiempo, ya mostraba 0 DROP tras el rearranque. Se corrigió el orquestador (`linea_ml_parado`) y se
repitió (`d300_reinicio_antes2`).

## Observaciones abiertas

- `[ZMQ-DROP]` en los primeros 10 s tras cada rearranque con tráfico (15 y 4 eventos medidos).
- Líneas de log mezcladas entre hilos (`[ZMQ-DROP]` y `[ML-PHASE]` en la misma línea).
- `[ML-PHASE]` muestra que los detectores embebidos ransomware/traffic/internal calculan en cada evento: evidencia
  para el interruptor de cabezas.
- antes2: resúmenes 8980 DROP frente a 8976 del FIN (4 DROP de una ventana anterior al INICIO).
