# DAY300 — parada inmediata del sniffer, sigwait, reinicio E2E y rangos protegidos

Rama `fix/ddos-etapa1-histeresis`. Commits: b550baf0 (parada inmediata), 8b91651d (sigwait), a9564c7c (E2E del
reinicio, ver `day300_reinicio_e2e.md`), 3c273162 (rangos protegidos 2a), el de la 2b y el de este cierre.

## 1. Parada inmediata (DEBT-SNIFFER-SHUTDOWN-HANG-001, resuelta)

Causa medida: cuatro hilos dormían con `sleep_for(30 s)` no interrumpible y su parada hacía `join()`:
estadísticas y procesador ransomware (ring_consumer), extracción ransomware (RansomwareFeatureProcessor) y
heartbeat (etcd-client, librería compartida; retenía el final de `main`). La parada tardaba 0-30 s según el
instante y `sniffer-stop` (15 s de gracia) acababa en SIGKILL. Arreglo: `condition_variable::wait_for` con
predicado y `notify_all` tras poner la bandera. Medido: 3/3 paradas ordenadas (337, 1086, 448 ms), todas las
marcas; edad de restauración exacta (−0,64 s frente a `volcado_wall_ns`): el «volcado de hace 60 s» de DAY299
era el hueco real del rearranque.

## 2. sigwait (DEBT-SNIFFER-MAIN-LOOP-POLL-001, resuelta)

El hilo principal sondeaba `g_running` con `sleep_for(1 s)` fijo: hasta 1 s de retraso (la dispersión
337-1086 ms). Ahora SIGINT/SIGTERM/SIGHUP se bloquean con `pthread_sigmask` antes de crear hilos y el principal
las espera con `sigwait()`: sin número fijo. Medido: 15/16 hilos con la máscara 0x4003 y el principal en
`do_sigtimedwait` (dentro de sigwait el kernel le desbloquea temporalmente las señales: `/proc` muestra
SigBlk=0 en ese hilo, lo correcto); paradas 4/4 en 123-231 ms.

## 3. Reinicio a mitad de un ataque (persistencia por víctima)

Ver `day300_reinicio_e2e.md`: sin estado, 0 marcados tras el rearranque (razón 0,000); parada ordenada 1,305;
kill -9 1,236 (volcado periódico de hace 34 s). Inocente .51: 0 DROP.

## 4. Rangos protegidos (DEBT-FW-PROTECTED-RANGES-001, sombra hecha)

Decisiones de Alonso: un DROP de la cabeza DDoS cuyo ORIGEN cae en dmz, intranet o externos_criticos es
`ALERTA_PROTEGIDO` y nunca bloqueo automático; sin ningún rango válido (bloque ausente, listas vacías o todo
inválido) el defecto es RFC 1918 + fc00::/7 como intranet (un descuido no puede bloquear la intranet); el JSON
lo dice claramente; los rangos protegidos se reflejarán también en el ipset de whitelist.

- 2a: `ddos_protegidos.hpp` (funciones puras) y `test_ddos_protegidos` (38 comprobaciones).
- 2b: cableado en config y sombra; valores de laboratorio documentados (el client simula Internet, .61 un
  host interno); guía DDOS-PROTEGIDOS.

E2E (`d300_protegidos_e2e.sh`): base .51 a 10 pps; ataque NTP simultáneo desde .50 (60 pps) y .61 protegido
(30 pps) sobre la misma víctima durante 180 s.

| Medida | Resultado |
|---|---|
| Configuración | `[CONFIG] ddos_protegidos.intranet += 192.168.100.61/32 (JSON)`, sin `[CONFIG-DEFAULT]` |
| Episodio (FIN) | solo .50: 10742 DROP de 10800 en el cable (0,995) |
| ALERTA_PROTEGIDO | 5371, todas intranet, `por_defecto=0`; 190 líneas de detalle (tope 10 por periodo) |
| Identidad | DROP de los resúmenes 16113 = FIN 10742 + alertas 5371 (diferencia 0) |
| .61 y .51 | 0 DROP |

Pendiente (2c, con el paso 3b): ipset de whitelist en `hash:net` cargado con los rangos protegidos y barrera
en el camino real de bloqueo.

## 5. Observaciones abiertas (BACKLOG)

ZMQ-DROP al arrancar, líneas de log mezcladas entre hilos, presión sin ataque con bases casi nulas,
4 DROP fuera del episodio en antes2, detectores embebidos ransomware/traffic/internal calculando en cada
evento, defaults silenciosos en config_manager.
