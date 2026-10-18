DAY302 — aRGus NDR. Rama: fix/ddos-etapa1-histeresis (sobre main 492580f6). NO mergear hasta EMECAS+++ verde.

REGLAS: medir, no votar; predicción escrita antes de cada medida; si algo no da lo esperado, PARAR. Comandos
completos diciendo dónde (Mac / defender / client); salidas a fichero + "; cat". Scripts como cat > f <<'EOF'
(PYEOF/MDEOF si el texto contiene EOF). Nada de grep -rn desde la raíz: git grep o ruta concreta. Compilar TODO
el pipeline y probar con el mismo perfil: make pipeline-build / test-components PROFILE=production. El JSON
manda: valor correcto se aplica Y se registra ([CONFIG]); ausente o inválido = defecto validado con
[CONFIG-DEFAULT] y el proceso arranca igual. awk con LC_ALL=C. Patchers atómicos --check/--apply con marca.
Al despertar el Mac: make lab-clock-step. Corridas en logs/lab/day302/ (DIA=day302). Tras reiniciar el client:
sudo ip addr add 192.168.100.51/24 dev eth1. Leer un fichero tocado: anclar por nombre (git grep -n -A N),
no por número de línea. Las esperas y marcas de tiempo las hace el script, nunca a mano.
NUEVO DAY301: arrancar SIEMPRE con PROFILE=production (firewall-start/pipeline-start sin PROFILE lanzan
build-debug, un binario anterior a DAY300; medido). El firewall solo, sin pipeline, muere (sin etcd).
Arranque con verificación: bash scripts/timebase/d301_arranque_b1.sh 2>&1 | tee /tmp/f.txt (pipeline-start/stop
PROFILE=production, ~3,5 min, progreso por pantalla). Tests con root: make test-firewall-e2e PROFILE=production.
Scripts largos: progreso por pantalla con tee, nunca solo a fichero.

HECHO DAY301 (subido, último 91cb3fe6), paso 3b preparado por tandas:
baa8bfbf 3b-a: ddos_mitigacion.hpp (DdosMitigacion: NADA/ESPERAR/BLOQUEAR/RENOVAR por origen; solo con la
víctima en episodio; un episodio = un strike; RENOVAR sin strike; desborde por max_origenes sin strike; purgar;
escalones_cortos) + DdosShadowPolicy::en_episodio() + test_ddos_mitigacion (coherencia con INICIO/FIN medida)
b68d81e6 b1: bloque ddos_mitigacion en firewall.json y config ([CONFIG]/[CONFIG-DEFAULT]); escalera de producción
[3600, 86400, 604800, 2073600] (código x2 structs + JSON, validada en parse_recidivism); [CONFIG] de la escalera
efectiva y [CONFIG-AVISO] de escalones cortos; set_type del ipset leído del JSON; whitelist hash:net
98d730b1 arranque b1 verificado en real (PROFILE=production)
5e4e272a c1 [ARGUS-CADENA-D301]: setup_base_rules reescrita: INPUT -I 1 -j ML_DEFENDER_TEST (único salto,
idempotente); dentro whitelist RETURN y blacklist DROP (nunca ACCEPT); sin rate limiting (solo aviso);
netmask solo en hash:ip; dry_run simula todas las órdenes
91cb3fe6 c2 [ARGUS-WHITELIST-D301]: la whitelist se vacía y carga con los rangos protegidos IPv4 al arrancar;
test_argus_cadena_root contra el kernel (32/32; sin root sale 77 = Skipped honesto). test-components 100/100;
test-firewall-e2e con root 4/4 (los 3 antiguos corren de verdad por primera vez)

DECISIONES DE ALONSO DAY301:
- Se bloquea la IP de ORIGEN de los DROP de ddos_v2 solo con su víctima en episodio; nunca la víctima ni un
  origen protegido. El origen se bloquea en su siguiente DROP dentro del episodio (no la lista del INICIO).
- FIN no desbloquea: manda el timeout. Un episodio = un strike; mientras siga atacando se renueva sin strike;
  tras su último DROP corre el escalón entero; reincidencia solo por episodio nuevo.
- Escalera de producción 1 h / 1 d / 7 d / 24 d, nunca permanente; castigos cortos solo para pruebas, con aviso.
- Doble llave: dry_run + ddos_mitigacion.habilitada (defecto false). min_drops_origen defecto 1, techo con medida.
- "Protegido" = aRGus nunca lo bloquea, no que el host lo acepte todo: cadena propia, whitelist RETURN.
- Tests con root: que pasen todos; primero los de esta feature, después los antiguos.

MEDIDO DAY301: la víctima del lab es el propio defender (eth2 = 192.168.100.1) y el client enruta por él
(default via .1): INPUT basta; FORWARD medible en el futuro sin cambiar topología. Kernel 6.1.0-53: ip_set,
hash_ip, hash_net y xt_set cargables. ipset 7.17 rechaza netmask en hash:net (rc 2). /etc/ml-defender/
firewall-acl-agent/firewall.json es enlace al JSON del repo. Hoy no existe ningún set ni regla en el defender.

PENDIENTE, EN ORDEN:
1. Tanda b2, cableado:
   - batch_processor: API por episodio. BLOQUEAR -> compute_penalty_timeout (strike+1). RENOVAR -> escalón
     vigente SIN strike (función nueva; sin estado = escalón 0). Ojo con pending_penalty_ (H6) y la dedup de
     pending_ips_.
   - Barrera: un origen en rangos protegidos nunca entra en la blacklist.
   - zmq_subscriber, tras add_drop: decidir(dst, proto, src, ddos_shadow_.en_episodio(dst, proto)) ->
     processor_; líneas [DDOS-MITIGACION] (detalle limitado) y contadores en el resumen; purgar en cada resumen;
     [CONFIG-AVISO] periódico de escalones cortos.
   - Config del suscriptor: ddos_mitigacion + escalones cortos; main los copia.
   - Pasos 5-8 viejos (inalcanzables; timeout_sec 300/600/3600 e ipset_name fijos): retirar o anotar.
   - Tests unitarios de batch_processor en dry_run: strike por episodio, renovar sin strike, barrera.
2. E2E real, con conmutador solo durante el test (dry_run false, habilitada true, escalera corta) y trap que
   restaura y verifica. Criterios PASA/FALLA:
   - .50 entra en el ipset a pocos s del INICIO;
   - sube el contador de la regla DROP (iptables -L ML_DEFENDER_TEST -v -n);
   - .61 nunca entra;
   - .50 sale tras su último DROP + escalón;
   - en un 2.º ataque, el escalón sube;
   - medir si el sniffer sigue viendo el tráfico bloqueado (XDP antes que netfilter);
   - distribución de DROP por origen para fijar el techo de min_drops_origen.
3. Gate: test-firewall-e2e dentro de EMECAS, fallando si hay Skipped. Después los 21 IPSetWrapperTest antiguos.
4. Tests de integración sniffer -> proto -> ml-detector; objetivos make E2E con PASA/FALLA; EMECAS+++ desde cero.
5. PR con docs day298_etapa1_resultados, day299_estado_arranque_persistencia, day300_reinicio_e2e,
   day300_parada_y_protegidos, paper_apoyo_day301.
6. Tras el merge: interruptor de cabezas (DEBT-HEADS-SWITCH-001) y caducidad de flujos
   (DEBT-SNIFFER-FLOW-EXPIRY-001 + FLOWTABLE-CONFIG-001). Alonso decide el orden.

FICHEROS CLAVE: firewall-acl-agent/include/firewall/ddos_mitigacion.hpp, ddos_shadow_policy.hpp (en_episodio),
ddos_protegidos.hpp (categoria_de; saneado vive en detalle_protegidos), batch_processor.hpp/.cpp
(flush_internal, compute_penalty_timeout, pending_penalty_), src/api/zmq_subscriber.cpp (add_drop y return de la
sombra; resumen [SOMBRA-DDOS]), include/firewall/zmq_subscriber.hpp (Config), src/main.cpp (zmq_config.ddos_*,
whitelist, recidivism), src/core/iptables_wrapper.cpp (setup_base_rules), config/firewall.json
(ddos_mitigacion, recidivism, ipsets), tests/unit/test_argus_cadena_root.cpp, scripts/timebase/d301_*.
