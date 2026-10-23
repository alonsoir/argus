# DAY305 — Interruptor de cabezas (DEBT-HEADS-SWITCH-001)

Rama `feat/heads-switch` (desde main `a0ba1d62`). Decisiones de Alonso: DAY300 (BACKLOG) y DAY305.

## Decisiones DAY305 (Alonso)

- UNA sola PR: cada cabeza se enciende o apaga según su JSON, de verdad, leído al arrancar. "Nice and easy".
- La administración remota de la instalación a través de etcd-server (admin autorizado → etcd-server modifica esa
  parte del JSON del componente y le avisa) SALE de esta rama: es un diseño propio, que va más allá de las cabezas
  (primer caso de uso de la administración remota) y se hace bien, no con prisa. Va al BACKLOG.
- Modelo de autoridad (para ese diseño futuro): el JSON de cada componente da los valores por defecto; quien manda
  es el mensaje del etcd-server de la instalación, que conoce todos sus componentes. Un proceso superior podría
  hablar con varias instalaciones. Apagar cabezas es una acción de seguridad crítica: mensaje firmado, registrado
  en el log del receptor y visible en el resumen [HEADS].
- Laboratorio (decisión DAY300): mientras se trabaja DDoS, todo lo que no sea DDoS apagado en el JSON del lab
  (ddos_v2 ON; level1, ransomware, traffic, internal y fast-path OFF). Defecto en el código si falta el campo: ON
  con [CONFIG-DEFAULT], para que un JSON incompleto no apague nada en silencio.
- El DDoS viejo (`level2.ddos`, `DDoSDetector`, `ddos_trees_inline.hpp`) se RETIRA en su propia rama, sin mezclar.
  En el bloque A no se toca su flag (`level2.ddos.enabled` ya funciona).

## Inventario medido (DAY305, main a0ba1d62)

| Cabeza | Proceso | Flag hoy | ¿Funciona? | Lectura |
|---|---|---|---|---|
| fast-path (FastDetector) | sniffer | `fast_detector.enabled` | NO: `ring_consumer.cpp:620` ingiere siempre | arranque |
| ransomware (procesador + agregador) | sniffer | ninguno | `ring_consumer.cpp:202` se inicializa siempre | — |
| rasgos embebidos ddos/ransomware/traffic/internal | sniffer | ninguno | `populate_ml_defender_features` los calcula siempre | — |
| level1 | ml-detector | `level1.enabled` | apagarlo hace `return 1` (`main.cpp` ~275) | arranque |
| DDoS viejo | ml-detector | `level2.ddos.enabled` | sí (se retira en otra rama) | arranque |
| ransomware | ml-detector | `level2.ransomware.enabled` | sí | arranque |
| traffic | ml-detector | `level3.web.enabled` | sí | arranque |
| internal | ml-detector | `level3.internal.enabled` | sí | arranque |
| ddos_v2 | ml-detector | `ml.ddos_v2.enabled` | sí | CADA evento (`zmq_handler.cpp:488`) |

- Firewall: solo actúa con `final_decision == "DROP"` (`zmq_subscriber.cpp:716`) + `ddos_shadow.enabled` + evento
  de flujo; la mitigación real tiene doble llave (`dry_run` + `ddos_mitigacion.habilitada`).
  `final_decision = ddos_v2_attack ? DROP : ALLOW` (`zmq_handler.cpp:623`). Con ddos_v2 apagada, el firewall no hace nada.
- ddos_v2 NO depende del agregador de ransomware: sus rasgos salen de la foto del anillo (`ring_consumer.cpp:937,
  962-966`) y del kernel (`1417-1438`).
- Dependen del agregador de ransomware: `source_ip_dispersion` (DDoS viejo), 4 rasgos de traffic y 4 de internal.
  Los 9 llamadores de `window_stats_30s()` están protegidos por `if (!aggregator_)`. La función no lo está.

## Lista de cierre (cada punto con su predicción ANTES de medir)

**A1. Sniffer: interruptores reales.**
`fast_detector.enabled` corta de verdad la línea 620. Flags nuevos para ransomware, ddos, traffic e internal en
sniffer.json, cada uno con `_doc`, defecto validado, `[CONFIG-DEFAULT]` si falta o es inválido, y registro del
valor efectivo. Con ransomware apagado no se crea el procesador ni el agregador. `populate` se salta los
extractores de las cabezas apagadas y deja en sus campos el centinela, nunca un 0 ambiguo.
Si traffic o internal van encendidas con ransomware apagado, aviso `[HEADS-DEP]` (4 rasgos irán a centinela).
`window_stats_30s()` lleva la guardia dentro, con prueba unitaria sobre el agregador nulo.
Predicción: los rasgos base (PARTE 2, 102+ campos) y la foto DDoS v2 no dependen de ningún extractor apagado.
El bronce y el grafo reciben lo mismo que hoy.

**A2. ml-detector: level1 apagada no mata el proceso.**
MEDIDO: `zmq_handler.cpp:454` solo comprueba `is_flow_event` y llama a `level1_model_->predict(...)` sin mirar si
el modelo existe → quitar el `return 1` haría caer el proceso en el primer evento de flujo. Además, sin inferencia
`label_l1` queda en -1, y las líneas 476 y 593 (`label_l1 == 0 ? BENIGN : ATTACK`) lo publicarían como "ATTACK".
Hoy NO pasa: esas líneas ya van dentro de `if (is_flow_event)` (corregido tras leer el fichero entero; la primera
lectura DAY305 lo daba por ocurrido). Pasaría con level1 apagada si solo se quitara el `return 1`.
Solución (`d305_mld_heads.py`): `l1_on = is_flow_event && level1_model_` gobierna extracción, inferencia,
predicción y veredicto de level1, `ml_score` y la fuente de autoridad. Los 5 `enabled` de cabeza pasan de
obligatorios a defecto true + [CONFIG-DEFAULT]. Línea `[HEADS]` con el estado EFECTIVO al arrancar y en cada
informe de estadísticas. Con level1 apagada, ddos_v1/ransomware/traffic/internal no se evalúan (siguen detrás de
la compuerta de level1, salvo FORCE_ALL_HEADS); `[HEADS]` lo avisa.
Con TODAS las cabezas apagadas: cero inferencias, el bronce correlation_v1 se sigue escribiendo, `final_decision`
siempre ALLOW y `overall_threat_score` 0.

**A3. Estado en el log, siempre visible (sin verbose).**
Línea `[HEADS]` por proceso al arrancar, con el estado efectivo de cada cabeza, y repetida en el resumen
periódico. Se corrige el «Ransomware Detection: DISABLED» que hoy no dice la verdad.

**A4. Ransomware (asignado a esta rama en DAY300).**
Los intervalos fijos (30 s) pasan al JSON del bloque de la cabeza, con la constante como respaldo y
`[CONFIG-DEFAULT]`. Se arregla DEBT-SNIFFER-RANSOMWARE-STOP-RACE-001.

**A5. Pruebas: la PR se explica con tests.**
- Unitarias: lectura de flags (falta, tipo erróneo → defecto + aviso) y agregador nulo.
- E2E-1, todo apagado: el sniffer captura, el bronce crece, el ml-detector hace 0 inferencias y el firewall 0 DROP.
- E2E-2, solo ddos_v2: flood ntp 60 pps → INICIO y FIN de la sombra como en DAY294, 0 del inocente .51.
- Medida de herramienta: CPU de sniffer y ml-detector con todo apagado / solo ddos_v2 / todo encendido (línea base).

**A6. EMECAS+++ production desde cero → PR.**

## Deudas a registrar en el BACKLOG (fuera de esta rama)

- DEBT-ETCD-REMOTE-ADMIN-001 (diseño): administración remota de una instalación a través de etcd-server. Primer
  caso de uso: encender/apagar cabezas. Hoy etcd-server es propio (httplib: /register, /unregister, /components,
  /seed, /validate, /health, /info, /secrets/keys; config bajo /config/<componente>), sin *watch*, y los
  componentes no vuelven a leer su config tras registrarse. Abierto: canal de aviso (consulta larga desde el
  componente, sin puertos de escucha), firma y autorización del admin, registro, interfaz (junto a la del grafo).

- DEBT-DDOS-V1-RETIRE-001: retirar el DDoS viejo (detector, header, flag, rasgos viejos del sniffer y bloque
  `level2.ddos` del JSON, que aún declara 10 rasgos con geo).
- DEBT-FW-MITIGACION-ATADA-A-SOMBRA-001: la mitigación real solo corre con `ddos_shadow.enabled`; apagar la sombra
  apaga la mitigación.
- DEBT-REPO-RESIDUOS-001 (ampliar): `etcd-server/src/*.backup*` (4), `sniffer/src/userspace/ml_defender_features.cpp.bak.day79`,
  `sniffer/include/payload_analyzer.hpp.v1.0`.
