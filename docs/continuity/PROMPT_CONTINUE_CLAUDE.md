DAY301 — aRGus NDR. Rama: fix/ddos-etapa1-histeresis (sobre main 492580f6). NO mergear hasta EMECAS+++ verde.

REGLAS: medir, no votar; predicción escrita antes de cada medida; si algo no da lo esperado, PARAR. Comandos
completos diciendo dónde (Mac / defender / client); salidas a fichero + "; cat". Scripts como cat > f <<'EOF'
(PYEOF/MDEOF si el texto contiene EOF). Nada de grep -rn desde la raíz: git grep o ruta concreta. Compilar TODO
el pipeline y probar con el mismo perfil: make pipeline-build / test-components PROFILE=production. El JSON
manda: valor correcto se aplica Y se registra ([CONFIG]); ausente o inválido = defecto validado con
[CONFIG-DEFAULT] y el proceso arranca igual. awk con LC_ALL=C. Patchers atómicos --check/--apply con marca.
Al despertar el Mac: make lab-clock-step. Corridas en logs/lab/day301/ (DIA=day301). Tras reiniciar el client:
sudo ip addr add 192.168.100.51/24 dev eth1. Leer un fichero tocado: anclar por nombre (git grep -n -A N),
no por número de línea. Las esperas y marcas de tiempo las hace el script, nunca a mano.
d300_parada.sh y d300_sigblk.sh se ejecutan en el DEFENDER.

HECHO DAY300 (subido): b550baf0 parada inmediata (4 hilos con sleep_for(30 s) -> condition_variable; heartbeat
de etcd-client; 3/3 paradas ordenadas) | 8b91651d sigwait en el hilo principal (sin sondeo; paradas 123-231 ms;
15/16 hilos con máscara y el principal en do_sigtimedwait) | a9564c7c E2E del reinicio a mitad de un ataque
de 60 pps: sin estado 0,000; ordenada 1,305; kill -9 1,236 (docs/ml-heads/day300_reinicio_e2e.md) |
3c273162 + commit 2b: rangos protegidos en SOMBRA (ddos_protegidos.hpp, ALERTA_PROTEGIDO, defecto RFC 1918 +
fc00::/7, JSON de lab documentado, guía DDOS-PROTEGIDOS); E2E .50 + .61 protegido: 16113 = 10742 + 5371 |
cierre: day300_parada_y_protegidos.md, paper_apoyo_day300.md, BACKLOG, este prompt.

PENDIENTE, EN ORDEN:
1. Paso 3b: drop temporal real E2E con dry_run apagado solo durante el test (decisión de Alonso DAY299): IP
   entra en el ipset con timeout calculado (reincidencia, RECIDIVISM-D276) y sale al vencer. OJO, medido
   DAY300: la sombra de ddos_v2 hace return antes de cualquier bloqueo (zmq_subscriber.cpp, comentario
   [DDOS-SHADOW-D293]: "la mitigación real será por víctima", DEBT-FIREWALL-PER-VICTIM-001): HOY NO EXISTE el
   camino ddos_v2 -> ipset. Primero DISEÑO con Alonso (qué se bloquea: origen con drop temporal y escalado; con
   qué condición: episodio INICIO; conmutador en el JSON), después medir soporte ipset del kernel del defender.
   Con él, la tanda 2c de rangos protegidos: ipset de whitelist en hash:net (hoy hash:ip, whitelist.json vacío)
   cargado con los rangos protegidos, y barrera en batch_processor (un origen protegido nunca entra en la lista
   negra). Y los tests del ipset con root dentro del gate (DEBT-FW-IPSET-TESTS-SIN-ROOT-001; 21 se saltan).
2. Tests de integración sniffer -> proto -> ml-detector en test-components; objetivos make de los E2E del lab
   con PASA/FALLA automáticos (base: d300_reinicio_e2e.sh y d300_protegidos_e2e.sh, cuyas predicciones ya son
   criterios numéricos); EMECAS+++ desde cero.
3. PR con docs/ml-heads/day298_etapa1_resultados.md, day299_estado_arranque_persistencia.md,
   day300_reinicio_e2e.md, day300_parada_y_protegidos.md.
4. Después del merge, dos ramas que Alonso dio ambas como "justo después": interruptor de cabezas
   (DEBT-HEADS-SWITCH-001, decisiones DAY300) y caducidad de flujos (DEBT-SNIFFER-FLOW-EXPIRY-001 +
   FLOWTABLE-CONFIG-001, decisión DAY298). Alonso decide el orden.

FICHEROS CLAVE: sniffer/src/userspace/main.cpp (sigwait), ring_consumer.cpp/.hpp (espera_o_parada),
ransomware_feature_processor.cpp/.hpp, etcd-client/src/etcd_client.cpp (heartbeat), Makefile (sniffer-stop),
firewall-acl-agent/include/firewall/ddos_protegidos.hpp, config_loader.cpp (bloque ddos_protegidos),
zmq_subscriber.cpp (ALERTA_PROTEGIDO antes de add_drop; return de la sombra), batch_processor.cpp (2c),
firewall.json (ddos_protegidos, ipsets.whitelist hash:ip), scripts/timebase/d300_*.sh.
