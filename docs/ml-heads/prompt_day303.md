DAY303 — aRGus NDR. Rama: fix/ddos-etapa1-histeresis (sobre main 492580f6). NO mergear hasta EMECAS+++ verde.

REGLAS: medir, no votar; predicción escrita antes de cada medida; si algo no da lo esperado, PARAR. Comandos
completos diciendo dónde (Mac / defender / client); salidas a fichero + "; cat". Scripts como cat > f <<'EOF'
(PYEOF/MDEOF/SHEOF si el texto contiene EOF). Nada de grep -rn desde la raíz: git grep o ruta concreta. Compilar
TODO el pipeline y probar con el mismo perfil: make pipeline-build / test-components PROFILE=production. El JSON
manda: valor correcto se aplica Y se registra ([CONFIG]); ausente o inválido = defecto validado con
[CONFIG-DEFAULT] y el proceso arranca igual. awk con LC_ALL=C. Patchers atómicos --check/--apply con marca.
Al despertar el Mac: make lab-clock-step. Corridas en logs/lab/day303/ (DIA=day303). Tras reiniciar el client:
sudo ip addr add 192.168.100.51/24 dev eth1. Leer un fichero tocado: anclar por nombre (git grep -n -A N),
no por número de línea. Las esperas y marcas de tiempo las hace el script, nunca a mano.
DAY301: arrancar SIEMPRE con PROFILE=production (sin PROFILE se lanza build-debug, anterior a DAY300). El firewall
solo, sin pipeline, muere (sin etcd). Tests con root: make test-firewall-e2e PROFILE=production. Scripts largos:
progreso por pantalla con tee.
NUEVO DAY302:
- Lanzar en segundo plano por vagrant ssh: SIEMPRE "& sleep 2" detrás del &. Sin él el proceso no llega a arrancar
  (medido: ni fichero de salida ni de error).
- Los pcaps del lab llevan MACs ajenas: el kernel del defender los descarta (PACKET_OTHERHOST) ANTES de netfilter;
  el sniffer sí los ve. Para medir aplicación, reescribir MAC destino (vecino 192.168.100.1) y origen (eth1 del
  client), como hace cortar() en scripts/timebase/d302_mitigacion_client.sh.
- E2E de la mitigación real: bash scripts/timebase/d302_mitigacion_e2e.sh NOMBRE 2>&1 | tee /tmp/d303_NOMBRE.txt
  (~12 min; conmutador solo durante la prueba; el trap restaura el JSON con cmp, retira cadena y sets y realinea
  relojes; criterios C1-C5 en d302_mitigacion_analisis.sh).
- logs/ está en .gitignore: las cifras viajan en los commits y en docs/.
- "[CRASH] System State Dump | context=periodic_metrics" NO es un crash (DEBT-FW-LOG-LEVEL-PERIODIC-DUMP-001).
- scripts/timebase/d301_arranque_b1.sh tiene DIA=day301 fijo y solo extrae [CONFIG*]/CRASH/FATAL.

HECHO DAY302 (subido; último 9fe88470 + el commit de cierre):
aa0349f5 b2-1 [DDOS-MITIGACION-B2-D302] [DRYRUN-ADD-BATCH-D302]: BatchProcessor con API por episodio
  (bloquear_episodio = un strike; renovar_episodio = escalón vigente sin strike y refresca last_seen;
  escalon_vigente; timeout fijado al encolar, nunca se acorta), barrera de protegidos en dos puertas (entrada y
  flush_internal), flush_si_toca (latido). add_batch en dry_run valida y simula sin kernel (antes fallaba
  SIEMPRE). Test H6 con fallo provocado (IP inválida). test_batch_processor_episodio (8 casos). 108/108.
36b511c8 b2-2 + b2-2c: cableado en zmq_subscriber (decidir -> bloquear/renovar tras add_drop; latido en
  receive_loop; resumen [DDOS-MITIGACION] con purga y [CONFIG-AVISO] periódico) y main (rangos protegidos al
  procesador; ddos_mitigacion, dry_run y escalones cortos al suscriptor; línea de modo). Pasos 5-8 anotados como
  inalcanzables.
9fe88470 E2E de la mitigación real: RESULTADO PASA (m3).

DECISIONES DE ALONSO DAY302:
- RENOVAR actualiza last_seen: el pipeline ha visto actuar a la IP; la calma cuenta desde su último DROP.
- Registro de TODA acción con set y timeout reales: activo BLOCKED / BLOCK_RENEWED; dry_run DRY_RUN_BLOCK /
  DRY_RUN_RENEW (nunca BLOCKED). Cada RENOVAR alarga la condena sin subir de escalón.
- Log por modo, KISS: dry_run = solo resumen periódico; activo = una línea por acción (se agrupan con
  herramientas Linux). Sin campo detalle_max.
- Escalera de PRUEBA del E2E: [60, 120] s.
- Volumen de log en modo activo: medirlo en despliegue distribuido o hardware real; "menos es más" con el disco.
- PROPUESTA A CONFIRMAR al empezar: los 2 IPSetWrapperTest de rendimiento salen del gate a una etiqueta propia
  "perf" (objetivo test-firewall-perf: imprime números, no bloquea); TestPerformance se rebautiza a lo que mide
  (test() en espacio de usuario, con fork). Umbrales reales en hardware real.

MEDIDO DAY302:
- E2E m3 (2 ataques NTP .50 a 60 pps + .61 protegido a 30 pps, 60 s cada uno, tuplas disjuntas, base .51):
  .50 entra 4,9 / 4,5 s tras el inicio (strikes=1 timeout 60; strikes=2 timeout 120); la regla DROP tira
  3312 / 3348 de 3600 paquetes por ataque (92 %; los ~290 que pasan = 4,8 s de reacción); sale 61,2 / 121,7 s
  tras el fin; .61 y .51 nunca entran (3533 ALERTA_PROTEGIDO); 2 BLOQUEAR, 6701 RENOVAR (el sniffer XDP ve lo que
  netfilter tira); 0 RECHAZADO. La cabeza marcó DROP en el 98 % de los paquetes del ataque.
- Reacción, por tramos (reloj del sniffer): ataque -> 1.er DROP ~1-2 s; -> INICIO ~2 s (k/n 3/5, a propósito);
  -> BLOQUEAR ~1 s (siguiente DROP del origen); -> kernel <= 1-2 s (batch_time_threshold_ms=1000 + latido).
- m2 falló C2 (contador DROP 0) por las MACs de los pcaps; m1 falló por lanzar el muestreo sin sleep.
- Nadie hacía flush por tiempo: should_flush solo se evaluaba al añadir (resuelto con el latido).
- 21 IPSetWrapperTest con root: 19 pasan; fallan BatchAddPerformance (13 ms vs < 10 ms por 1000 IPs, VirtualBox)
  y TestPerformance (3017 µs vs < 1 µs: mide un fork de /sbin/ipset test, umbral imposible). No quedan sets.
- Arranque con el JSON de serie: [DDOS-MITIGACION] modo: DESHABILITADA y resúmenes con modo=deshabilitada a 0.

PENDIENTE, EN ORDEN:
1. Paso 3, gate (a medias):
   - Confirmar la propuesta "perf".
   - Separar IPSetWrapperTest de firewall_tests en su propio ejecutable (gtest_discover_tests registra todo el
     binario de golpe): funcionales con LABELS "e2e;root"; los 2 de rendimiento con LABELS "perf".
   - test-components: el ctest del firewall excluye root y perf (-LE "root|perf"), para que no salgan Skipped.
   - test-firewall-e2e: sudo ctest -L e2e y FALLA si aparece cualquier Skipped / "did not run".
   - Nuevo test-firewall-perf (sudo ctest -L perf, informa, no bloquea).
   - EMECAS (emecas o emecas++) llama a test-firewall-e2e.
   - Inventario ya hecho: logs/lab/day302/inv_gate.txt (Makefile:3074 test-firewall-e2e, :1253 test-components,
     :1319 emecas, :1334 emecas++, :3087 emecas+++; CMake firewall :480-529).
2. E2E de la mitigación como objetivo make con PASA/FALLA (sobre d302_mitigacion_e2e.sh), y los de DAY300
   (d300_reinicio_e2e.sh, d300_protegidos_e2e.sh) también; tests de integración sniffer -> proto -> ml-detector;
   EMECAS+++ desde cero.
3. PR con docs day298_etapa1_resultados, day299_estado_arranque_persistencia, day300_reinicio_e2e,
   day300_parada_y_protegidos, paper_apoyo_day301, paper_apoyo_day302.
4. Tras el merge: interruptor de cabezas (DEBT-HEADS-SWITCH-001) y caducidad de flujos
   (DEBT-SNIFFER-FLOW-EXPIRY-001 + FLOWTABLE-CONFIG-001). Alonso decide el orden. Después, vía rápida XDP.

FICHEROS CLAVE: firewall-acl-agent/include/firewall/batch_processor.hpp/.cpp (ResultadoEpisodio,
encolar_episodio, escalon_vigente, flush_si_toca, barrera en flush_internal), src/core/ipset_wrapper.cpp
(add_batch dry_run), src/api/zmq_subscriber.cpp (latido en receive_loop; mitigación tras add_drop; resumen
[DDOS-MITIGACION]), include/firewall/zmq_subscriber.hpp (Config: ddos_mitigacion, ddos_escalones_cortos, dry_run),
src/main.cpp, tests/unit/test_batch_processor_episodio.cpp, tests/unit/test_ipset_wrapper.cpp (IPSetWrapperTest),
CMakeLists.txt del firewall, Makefile raíz, scripts/timebase/d302_*.
