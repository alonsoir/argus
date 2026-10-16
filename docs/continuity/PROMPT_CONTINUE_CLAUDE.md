DAY300 — aRGus NDR. Rama: fix/ddos-etapa1-histeresis (sobre main 492580f6). NO mergear hasta EMECAS+++ verde.

REGLAS: medir, no votar; predicción escrita antes de cada medida; si algo no da lo esperado, PARAR. Comandos
completos diciendo dónde (Mac / defender / client); salidas a fichero + "; cat". Scripts como cat > f <<'EOF'
(PYEOF/MDEOF si el texto contiene EOF). Nada de grep -rn desde la raíz: git grep o ruta concreta. Compilar TODO
el pipeline y probar con el mismo perfil: make pipeline-build / test-components PROFILE=production. El JSON
manda: defecto validado + [CONFIG-DEFAULT], el proceso arranca igual. awk con LC_ALL=C. Patchers atómicos
--check/--apply con marca. Al despertar el Mac: make lab-clock-step. Corridas: logs/lab/day300/ (DIA=day300).
Tras reiniciar el client: sudo ip addr add 192.168.100.51/24 dev eth1. Leer un fichero tocado hoy: anclar por
nombre (git grep -n -A N "nombre"), no por número de línea (los parches desplazan las líneas).

HECHO DAY299 (subido): 83f99b16 generados de protobuf/ que faltaban en 2085d708 | b05f880c ESTADO-ARRANQUE:
plazo ddos_victim_arranque_ventanas (5), sin foto en plazo = FRIO, fuera = [DDOS-ARRANQUE] ERROR +
[DDOS-V2-ANOMALIA] estado_victima_ausente; nace docs/operaciones/GUIA_OPERACIONES.md | e586aa31 medida +
lab_frio.sh RETRASO_S | 004e3c8b [DDOS-ARRANQUE] AVISO con agregador apagado + MANIFEST + BACKLOG | 5caf4735
paso 4 persistencia (volcado cada 60 ventanas y en la parada, restauración con caducidad 86400 ventanas,
rebase de last_seq, CSV v1 600, tests 15a-15f) | commit de cierre: sniffer-stop (SIGTERM, 15 s, SIGKILL) usado
por pipeline-stop, SIGHUP = parada ordenada, docs day299 + paper_apoyo_day299 + BACKLOG.
Medido: frío 300 pps: estado_victima_ausente 298 -> 0, primera foto ~1,0 s, pases = marcados 51655;
agregador apagado: [DDOS-V2-ANOMALIA] cada 10 s, 0 DROP; parada: [Cleanup] + volcado de parada (10
víctimas) + restauración (10 víctimas) medidos.

PENDIENTE, EN ORDEN:
0. DEBT-SNIFFER-SHUTDOWN-HANG-001: tras el volcado de parada el sniffer no termina en 15 s (SIGKILL 2/2).
   Medir la última línea del sniffer.log antes del SIGKILL (anillo, thread manager, ZMQ linger, loader eBPF).
   Corregir el aviso de sniffer-stop ("sin volcado de parada" es falso si ya volcó). Medir por qué la
   restauración dijo "volcado de hace 60 s" con rearranque inmediato. Mirar permisos del fichero:
   sudo ls -l /var/lib/argus/sniffer/ (esperado -rw-------).
1. E2E del reinicio a mitad de un ataque de 60 pps (por debajo de abs_pps): cliente corto
   (d299_reinicio_client.sh: base .51 10 pps; a los 90 s ataque 60 pps 360 s; 60 s de base al final) y
   script de reinicio en una segunda terminal del Mac (espera inicio_ataque en tiempos.txt, +120 s,
   sniffer-stop, borra el fichero solo en "antes", sniffer-start). Tres corridas: antes (fichero borrado),
   después con parada ordenada, después con pkill -9. Predicción: antes 0 marcados tras el reinicio;
   después "restauradas ... (1 bajo presion)" y ataque marcado tras ~1 s.
2. Paso 5 DEBT-FW-PROTECTED-RANGES-001 en el firewall (sombra: ALERTA_PROTEGIDO).
3b. Drop temporal real E2E con dry_run apagado solo durante el test (decisión de Alonso): IP entra en el
   ipset con timeout calculado y sale al vencer. Antes, medir: soporte ipset del kernel del defender, camino
   de un DROP ddos_v2 con dry_run=false, conmutador del JSON del firewall. Con él, los tests del ipset con
   root dentro del gate (DEBT-FW-IPSET-TESTS-SIN-ROOT-001; make test-firewall-e2e no está en ningún gate).
4. Tests de integración sniffer -> proto -> ml-detector en test-components; objetivo make del E2E del lab con
   PASA/FALLA automáticos; EMECAS+++ desde cero.
5. PR con docs/ml-heads/day298_etapa1_resultados.md + day299_estado_arranque_persistencia.md.
   Después del merge: rama DEBT-SNIFFER-FLOW-EXPIRY-001 + DEBT-SNIFFER-FLOWTABLE-CONFIG-001.
   Más adelante: DEBT-PIPELINE-STOP-GRACEFUL-001 (resto de componentes), DEBT-HEADS-VENTANA-BASE-ARRANQUE-001.

FICHEROS CLAVE: sniffer/include/ddos_victim_board.hpp (lookup con plazo, sello_estado_victima, volcar_estado,
restaurar_estado, aplicar_rebase_si_pendiente, volcado_periodico, volcar_parada), sniffer/include/
ddos_contract_v2.hpp (VictimEwmaParams con arranque_ventanas y estado_*), sniffer/src/userspace/main.cpp
(marcar/borrar plazo antes de ring_consumer.start, restaurar tras set_ewma_params, volcar_parada tras parar el
lector, SIGHUP), ring_consumer.cpp (stamp_victim_window_from), config_manager.cpp (parse_victim_ewma),
sniffer.json (bloque kernel_space), ml-detector/src/zmq_handler.cpp ([DDOS-V2-ANOMALIA]), Makefile
(sniffer-stop, pipeline-stop), docs/operaciones/GUIA_OPERACIONES.md, scripts/timebase/lab_frio.sh (RETRASO_S),
d298_etapa1_resumen.sh, d299_agg_conmutador.py.
