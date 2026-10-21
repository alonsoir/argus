# DAY299 — estado de la víctima en el arranque, persistencia y parada ordenada

Rama `fix/ddos-etapa1-histeresis`. Commits: 83f99b16 (generados del proto que faltaban en 2085d708),
b05f880c (ESTADO-ARRANQUE), e586aa31 (medida + RETRASO_S), 004e3c8b (AVISO + documentación),
5caf4735 (persistencia, paso 4) y el commit de sniffer-stop de cierre del día.

## 1. Estado de la víctima en la ventana de arranque (DEBT-DDOS-ESTADO-ARRANQUE-001, resuelta)

Causa medida: sin foto del agregador (`have_snapshot=false`, porque la baseline no se publica) el evento
salía sin `victim_state`. Además, el consumidor del anillo arranca antes que el lector (main.cpp). El
diagnóstico de DAY298 (`window_ms==0`) era incorrecto.

Arreglo: plazo de arranque `ddos_victim_arranque_ventanas` (defecto 5, rango [2,60]):
- sin foto y dentro del plazo: FRIO;
- fuera del plazo o sin lector: sin estado, `[DDOS-ARRANQUE] ERROR` en el sniffer y
  `[DDOS-V2-ANOMALIA] estado_victima_ausente` en el ml-detector;
- agregador apagado: `[DDOS-ARRANQUE] AVISO` al arrancar.

| Escenario | Antes (DAY298) | Después (DAY299) |
|---|---|---|
| Frío, ataque de 300 pps presente en el arranque | 298 eventos sin estado | **0**; 648 sellados FRIO (fast alerts incluidas) |
| Primera foto del agregador | sin medir | **1015 / 1035 ms** (≈1 ventana) |
| Pases = marcados | 13 373 | **51 655 = 51 655**; DROP solo .50 desde la primera ventana con foto |
| Paquetes no marcados | — | 11 345 = 37 s antes del sniffer + ~1 s de ceguera física (0,6 % de error) |
| Agregador apagado, 60 s a 300 pps | — | 12 avisos `[DDOS-V2-ANOMALIA]`, ~3000 por 10 s (~17 900 de 18 000 paquetes), **0 DROP**, una línea AVISO |

La alarma está medida en los dos sentidos: calla en un arranque normal y salta cuando la cabeza queda ciega.

## 2. Persistencia del estado por víctima (DEBT-DDOS-STATE-PERSIST-001, código hecho; E2E pendiente)

- Volcado cada `ddos_victim_estado_volcado_ventanas` (60), en el hilo del lector, sin cerrojos.
- Volcado en la parada, tras parar el lector.
- Restauración al arrancar, antes del lector, con caducidad `ddos_victim_estado_max_edad_ventanas` (86 400).
- Las víctimas restauradas cuentan como calientes y conservan `bajo_presion` con la EWMA congelada.
- Rebase de `last_seq` en la primera ventana publicada. Sin él, un ataque **moderado** (en la banda de
  histéresis, 20 pps sobre base 10,5) perdería la presión tras el reinicio; uno fuerte reentra solo.
- CSV v1, tmp + rename, permisos 600, restauración atómica. Se descarta si está caducado, tiene fecha
  futura, otro `interval_ms` o una fila mal formada.
- Tests: `test_ddos_victim_board` 15a-15f.

Verificación corta (DAY299): `sin estado previo` → `primer volcado: 9 víctimas` → SIGTERM →
`[Cleanup]` → `volcado de parada: 10 víctimas` → rearranque → `restauradas 10 víctimas, volcado de hace 60 s`.

## 3. Parada ordenada del sniffer

Medido: `pipeline-stop` hacía `tmux kill-session` (SIGHUP) y ningún componente lo trataba, así que nunca
ejecutaban su limpieza (0 líneas `[Cleanup]` en sniffer.log).

Hecho:
- target `sniffer-stop` (SIGTERM, espera `SNIFFER_STOP_GRACE_S`=15, SIGKILL de último recurso), usado por
  `pipeline-stop`;
- el sniffer trata SIGHUP como parada ordenada.

Abierto: el proceso hace la limpieza hasta el volcado y después **no termina en 15 s** (SIGKILL en las dos
paradas medidas). El aviso «sin volcado de parada» es falso en ese caso.

## Pendiente (DAY300)

1. Colgado de la parada del sniffer después del volcado; corregir el aviso; edad de 60 s en la restauración.
2. E2E del reinicio a mitad de un ataque de 60 pps: antes (fichero borrado), después (parada ordenada) y
   después (kill -9).
3. Rangos protegidos en el firewall (paso 5).
4. Drop temporal real de punta a punta con dry_run apagado, y los tests del ipset con root dentro del gate.
5. Tests de integración, objetivo make del E2E con PASA/FALLA, EMECAS+++ y PR.
