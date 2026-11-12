
## DAY322 — 8e.5 hecho: bootstrap del manifiesto y P1-P6; EMECAS+++ desde cero, cuatro paradas [PROTEGIDOS-BOOTSTRAP-D322]

Commits: `aae32596d` (8e.5), `b8831bcb9` (antispoof desde el manifiesto), `c772cb27b` (avance y resumen de EMECAS),
`bd3f8bb18` (R3 por flujo), `218e0aaea` (grupo del agente de Wazuh; C7 en una VM nueva). Documentados el DAY323.

### Decisiones de Alonso (DAY322)
- `argus-infra init`: rc 4 propio (`SALIDA_YA_HAY`) si ya hay un manifiesto publicado; el bootstrap da por buenos 0 y 4.
- Avance y resumen de EMECAS: un log por paso; se guardan todas las corridas.
- El agente de Wazuh pide su grupo al registrarse (`WAZUH_AGENT_GROUP`); `provisioning/wazuh/argus/grupos.tsv` es la
  única fuente.
- «No revocamos nada»: el pipeline arranca con el etcd-server ya desplegado (orden normal); sigue la decisión DAY316
  (si al arrancar no responde ninguno, los componentes protegen sin firmar).

### EMECAS+++ desde cero: cuatro corridas, cada parada con su causa medida y su arreglo
1. `lab-e2e-antispoof`: esperaba `ips_mac=1 mac=1`, escritos a mano con la v11 del lab; con la v1 de la plantilla, .20
   lleva su MAC (`08:00:27:a2:00:20`): `redes=3 ips_mac=2 mac=2`. Lo esperado sale ahora del manifiesto publicado
   (`b8831bcb9`).
2. `lab-e2e-reinicio-antes`, R3: 3 marcas tras el reinicio que eran AISLADO de 192.168.100.12 (manager de Wazuh) -> .1
   por TCP, no del ataque (UDP). R3 cuenta solo el flujo del ataque (`bd3f8bb18`).
3. `vagrant-up`: el wheel de pandas 3.0.5 llegó corrupto. El hash fijado es el oficial de PyPI (`2c0cf1dd…c78a`,
   11 323 634 bytes): pasajero. Si se repite, reintentar la descarga hasta 3 veces sin aflojar el hash.
4. `lab-e2e-vigilancia` (6 fallos): la VM etcd nace después que la wazuh y su agente se quedaba en `default`
   (`agent.conf` de 76 bytes), y C7 exigía una entrada de logrotate que una VM nueva no tiene (`218e0aaea`).
En la 4.ª pasaron vagrant-up (55 min), bootstrap (38 min), test-all, test-argus-infra, test-vigilancia-*, firewall,
synthetic y lab-e2e hasta vigilancia.

### Hallazgos DAY322 (8e.5 y EMECAS)
- Ninguna de las cuatro paradas era del producto: eran de los tests o del orden en que nacen las VMs, y tres solo se
  ven desde cero (la plantilla v1, la VM etcd después que la wazuh, una VM sin historia de logrotate).
- `make emecas-progreso`: con un paso fallido, el reloj de la cabecera seguía contando hasta ahora (arreglado DAY323).

## DAY323 — EMECAS+++ desde cero en verde: Suricata ciego, un reloj por sensor, una ventana MITRE que mezclaba días, Jenkins sin clave y el NTP de los sensores en el episodio DDoS [SURICATA-ARRANQUE-D323] [LAB-NTP-SENSORES-D323] [MITRE-VENTANA-D323] [JENKINS-CLAVE-D323] [PROTEGIDOS-SENSORES-D323]

Commits: `d44e0a2d0` (Suricata), `6387cfd75` (un solo reloj), `2fcac3ce9` (ventana MITRE), `2f74f5047` (Jenkins),
`95d349c89` (sensores en la plantilla), `443fffb96` (veredicto de protegidos), el de `[EMECAS-PROGRESO-D323]` y este de
documentación.

### Las corridas
1.ª EMECAS+++ desde cero sobre `218e0aaea` (06:39-11:02 hora de Madrid, 4h23m): pasaron los 21 primeros pasos, también
lo que el DAY322 quedó sin probar en esta configuración (lab-kernel-limpio, restore, reinicio del etcd-server, los
actos de emecas++). Paró en mitre-check: `suricata: eventos en el grafo > 0 (0)`. Arreglos: Suricata, el reloj y la
ventana MITRE (abajo).
2.ª (13:36): paró en vagrant-up a los 18 min: `NO_PUBKEY 7198F4B714ABFC68` del repositorio de Jenkins en el
`apt-get update` de `vault-install`. Arreglo: Jenkins.
3.ª (14:23): paró en lab-e2e, P2 de protegidos: `origenes=192.168.100.50:10783,192.168.100.10:1,192.168.100.11:1,
192.168.100.12:1`. Arreglo: los sensores en la plantilla y el veredicto.
4.ª (18:10, sobre `443fffb96`): ver «EMECAS+++ desde cero con los arreglos».

### Medido en el lab (horas UTC)
- Suricata: el adapter leyó 1982 eventos y los descartó todos (solo guarda `alert`; hubo 0). El log decía
  `0 signatures processed` y captura en eth0, la NAT (solo 10.0.2.15). El proceso era de las 06:11:50 (lo arranca
  `apt-get install` con la configuración de fábrica); las reglas son de las 06:12:15 y el yaml de las 06:12:58, y nadie
  lo reiniciaba. Tras `systemctl restart`: 53 345 firmas, eth1, mitre-check PASA. El 3-nov funcionó en una VM que se
  había reiniciado.
- Lo que el veredicto daba por bueno: los bronces de Suricata del 04-nov empiezan con las mismas alertas, del 3-nov a
  las 10:51; `mitre_start.sh` copiaba el eve.json entero. Hoy, en la misma VM, 32 → 64 eventos de una corrida a otra.
- Zeek: 8 filas (7 de .1 → .20:2379 y un NTP), ninguna del barrido. A las 10:00:00 zeekctl rotó el conn.log a mitad
  de la corrida: el barrido (1072 líneas de .50) quedó en `conn.09:59:34-10:00:00.log.gz` y la cosecha copiaba solo el
  del spool. La corrida de las 10:33, sin hora en punto, dio 1077.
- `zeekctl stop` vuelve en el acto y el archivado sigue en segundo plano: `post-terminate` y un `archive-log` por
  fichero, en serie, unos 55 s cada uno; 121 s para dos ficheros.
- Relojes: suricata (162.159.200.1), zeek y wazuh (195.95.153.59) tomaban la hora del pool de Debian por la NAT, cada
  uno con su referencia; client y etcd, del defender. Las VMs derivan de 2000 a 4600 ppm (de 3 a 7 minutos al día sin
  NTP).
- Un FATAL del loader (`gold Parquet not found`) acabó en `mitre_start.sh rc=0`.
- Jenkins: la clave del repositorio se pedía a keyserver.ubuntu.com con los errores a `/dev/null`. No respondió, el
  anillo quedó vacío, apt rechazó el repositorio, el bloque dijo «✅ Jenkins instalado (puerto 8080)» sin Jenkins y el
  repositorio roto tumbó el `apt-get update` de `vault-install`, tres aprovisionadores después. La descarga oficial
  (`https://pkg.jenkins.io/debian-stable/jenkins.io-2026.key`) trae `5E386EADB55F01504CAE8BCF7198F4B714ABFC68`, la
  publicada en el changelog 2.543. Al reinstalar en el defender roto, dpkg se quedó preguntando qué hacer con el
  `/etc/default/jenkins` que el bloque viejo había escrito sin Jenkins.
- El NTP de los sensores: con la hora del defender, suricata, zeek y wazuh mandan UDP/123 a .1 (31, 22 y 34 consultas
  en la corrida; ningún otro UDP suyo a .1). Las que caen dentro del ataque UDP a .1 entraron en el episodio de la
  cabeza DDoS, un evento por sensor. .20 (etcd, protegido) ya iba al defender: sus consultas dan alerta, no bloqueo.

### Decisiones de Alonso (DAY323)
- Un solo reloj para el lab, el del defender. Si un sensor no va con él es un bug operacional, y la prueba falla
  diciéndolo; no se compensa.
- El grafo del día lleva solo los datos de esa sesión: los de otro día, mezclados, son datos sucios.
- Se arregla todo; cada arreglo se prueba aparte y, con todos probados, EMECAS+++ otra vez desde cero.
- Jenkins se arregla ya, con la clave del mantenedor comprobada por huella. Si no se puede instalar, el up sigue
  (EMECAS no usa Jenkins; las claves del lab las crean los aprovisionadores de Vagrant, no Jenkins), pero sin dejar un
  repositorio roto.
- Los sensores del lab son infraestructura del NDR: entran en la plantilla del manifiesto, con MAC vacía.
- El problema de fondo (tráfico legítimo hacia la víctima dentro del episodio) es deuda; al afrontarla, primero se mide
  qué ve el modelo. Alonso: «van a ser las dos cosas, como mínimo; no descartemos alguna sorpresa».

### Los arreglos, cada uno probado aparte antes de EMECAS
- `d44e0a2d0`: la provisión reinicia Suricata con las reglas y el yaml ya escritos y comprueba, en las líneas del log
  con el pid nuevo, `Engine started`, `eth1: creating` y firmas > 0; si no, falla. `suricata-update` con 3 intentos
  (antes `|| true`). Probado: 6 casos con los logs medidos; `vagrant destroy -f suricata` y `vagrant up suricata`: eth1
  y 53 345 firmas; mitre-check PASA sin tocar nada a mano.
- `6387cfd75`: provisión `lab-ntp` (run: always) en suricata, zeek y wazuh: hora del defender o la provisión falla;
  `lab-clock-step` recorre `LAB_CLOCK_VMS` (por defecto `client`, como hasta ahora) y mitre-check lo pasa primero con
  client suricata zeek. Probado: las tres VMs con `C0A86401 (192.168.100.1)`; con chrony del defender parado, ❌ y rc 1;
  lab-clock-step con cinco VMs < 1 ms.
- `2fcac3ce9`: una ventana [T0, T1] del reloj del defender para los tres sensores: `scripts/mitre_ventana.py` filtra
  cada bronce (fila a fila, byte a byte: el HMAC sigue valiendo) y cuenta las filas del ataque (.50 ↔ .1). Zeek se
  cosecha tras el stop y su archivado (`scripts/mitre_zeek_cosecha.sh`, `MITRE_ZEEK_ARCHIVO_MAX_S` = 300 s), también lo
  que una rotación archivó. Adapter, converter (sin filas es fallo), loader y consultas comprueban su resultado. El
  veredicto exige filas del ataque por sensor. `test-mitre-ventana` (15 casos; 7 mutaciones cazadas) va antes de
  mitre-check. Medido en el lab: archivado en 114 s; 13 ficheros conn del día, de los que la ventana dejó 1093 filas
  (1069 del ataque); Suricata `dentro=33 fuera=64`; argus, 541 filas anteriores a T0 fuera.
- `2f74f5047`: `scripts/jenkins/jenkins_instalar.sh` con `repo_oficial` (como Wazuh y Falco) y
  `provisioning/jenkins/CLAVE`; «✅» solo si dpkg lo da por instalado; si no, rc 3, aviso y repositorio retirado, y el up
  sigue. Nunca una pregunta de dpkg: fuera el `/etc/default/jenkins` de un intento fallido, y `confdef`/`confold` sin
  terminal. Probado en el defender roto: clave falsa → rechazo con la huella real y rc 3, apt sano después; caso bueno →
  Jenkins 2.580.2; reinstalación con un `/etc/default/jenkins` suelto → sin pregunta; idempotente.
- `95d349c89`: .10, .11 y .12 como `infraestructura` en `tools/argus-infra/plantillas/hospital-lab.json` y las tres
  aserciones de `test_argus_infra.py` que fijaban la plantilla (22 tests). Probado publicándolos en el manifiesto vivo
  (`argus-infra add`, v2-v4) y repitiendo lab-e2e-protegidos: P2 = solo .50.
- `443fffb96`: el veredicto de protegidos saca la infraestructura de la línea «rangos protegidos» que escribe el
  firewall (lo que aplica) y P1 exige todas las entradas de la plantilla; antes, .20 escrita a mano y P3 contaba como
  «de otro origen» las alertas de los sensores. Probado con logs sintéticos (lo de hoy PASA; un sensor en `origenes=`,
  una alerta de una IP fuera del manifiesto o un manifiesto sin una entrada de la plantilla FALLAN) y con la corrida
  real: P1-P6 PASA.
- `[EMECAS-PROGRESO-D323]`: `make emecas-progreso` para el reloj de la cabecera en el fallo (test nuevo; sin el
  arreglo, falla).

### EMECAS+++ desde cero con los arreglos
**PASA, rc=0, en 4h02m** (18:10-22:13 hora de Madrid, sobre `443fffb96`): la primera emecas+++ verde desde cero del
PR1. mitre-check con los criterios nuevos: argus 1777 eventos en el grafo (1253 del ataque en la ventana), Suricata
31 (31), Zeek 1114 (1068), invariante 0, 1080 flujos corroborados. Los tiempos de cada paso quedan en
`logs/lab/emecas_tiempos_emecas+++.tsv` (dan el porcentaje de `make emecas-progreso` desde ahora).

### Hallazgos DAY323
- Tests que no podían fallar por la razón correcta: (1) provisión que no comprueba su efecto (Suricata instalado sin
  mirar si captura; `|| true`); (2) aserciones débiles («> 0» pasaba con alertas del día anterior y con NTP y etcd);
  (3) resultados que dependen del reloj o del estado (la rotación a la hora en punto, el eve.json acumulado, un reloj
  por sensor). Solo los destapa una corrida desde cero. Regla para lo nuevo: cada operación comprueba su efecto
  concreto, sobre estado nuevo, y se prueba también que falla cuando debe.
- Dos predicciones fallidas de Claude, paradas a medir: que el barrido de Zeek seguía en memoria (era la rotación: lo
  dijeron los nombres de los archivados) y que los 1076 de Zeek del 04-nov eran acumulados (el `deploy` empieza un log
  nuevo en cada corrida; en Suricata sí lo eran).
- Un arreglo puede destapar otro problema: «un solo reloj» hizo que el NTP de los sensores fuera a la víctima del
  ataque del lab y destapó que la cabeza DDoS mete tráfico legítimo en el episodio. Y dos tests tenían listas escritas
  a mano (el veredicto de protegidos y `test_argus_infra.py`): lo esperado tiene que salir de la fuente (el manifiesto,
  la plantilla), como ya se hizo con antispoof el DAY322.

### DEBT-CTU-START-VENTANA-001 — ABIERTA (nueva DAY323)
`scripts/ctu_start.sh` tiene los patrones que tenía `mitre_start.sh`: el eve.json entero, `ls -t … | head -1` para la
salida de cada adapter, Zeek copiado del spool y pasos sin comprobar. No está en EMECAS. Arreglo: lo mismo que
`mitre_start.sh` (`mitre_ventana.py`, `mitre_zeek_cosecha.sh` y las comprobaciones de cada paso).
**Test de cierre:** ctu-start en una VM con corridas anteriores deja en el grafo solo las filas de su ventana, y falla
si un paso falla.

### DEBT-DDOS-COLATERAL-LEGITIMO-001 — ABIERTA (nueva DAY323, Alonso)
Durante un ataque contra una víctima, la cabeza DDoS mete en el episodio el tráfico legítimo de un paquete que llega a
esa víctima (medido DAY323: NTP de los sensores a .1, un evento por sensor en `origenes=`). Fuera del modo sombra se
bloquearía a quien solo pidió la hora o un nombre. En un hospital: cualquier equipo que consulte NTP o DNS a un
servidor atacado; y, al revés, las respuestas legítimas a lo que la DMZ pregunta fuera (53/123 → puerto alto) se
parecen a una reflexión. Primer paso: medir qué ve el modelo en esos eventos (escritor del dataset DDoS v2 o
`[HEAD-SCORES]` en verbose). Dos líneas, probablemente las dos: (1) benigno de servicio en el entrenamiento, en los dos
sentidos (consultas a la víctima y respuestas a lo que pregunta la DMZ), sin que el puerto solo decida, porque los
floods y amplificaciones van precisamente a 53 y 123; (2) un umbral de evidencia por origen en la atribución del
episodio, configurable en el JSON (DAY323: .50 con 10 783 eventos, cada sensor con 1). Va con los rasgos por origen.
**Test de cierre:** un cliente no protegido que consulta NTP y DNS a la víctima durante el ataque no aparece en
`origenes=`, y el atacante sí.

### Pendiente (por orden)
Cierre del PR1 (README del etcd-server, push, PR). Después, PR2 (HA): ≥3 nodos etcd (caída de uno, reelección, cuánto
tardan en sincronizar; apagar todos y encender uno a uno), Vault en HA y su Ansible, nº de nodos en el inventario y
plantilla Jinja2 de `etcd.conf.yml`, en PRs pequeños. Después del PR2, la «dieta de adelgazamiento» (código deprecado
fuera; Trivy). Más tarde (toca Jenkins y exige otro EMECAS): DEBT-SUPPLY-CHAIN-ORIGEN-OFICIAL-001. Sin orden decidido:
DEBT-ARGUS-INFRA-MOD-001, DEBT-SNIFFER-SYSTEM-SYSCTL-001, DEBT-LAB-ZONA-HORARIA-001, DEBT-HARDENED-FALCO-RUTAS-001,
DEBT-VAULT-SELLADO-ALERTA-001, DEBT-CTU-START-VENTANA-001, DEBT-DDOS-COLATERAL-LEGITIMO-001.
