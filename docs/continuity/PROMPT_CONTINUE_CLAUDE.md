# aRGus NDR — continuidad para DAY324

**PR1 de DEBT-ETCD-HA-TLS-RAFT-001 cerrado**: `feat/etcd-mtls-vault` mergeada a main (PR #153, `0479e69d9`), con
**EMECAS+++ PROFILE=production desde cero en verde** (DAY323, 4h02m, sobre `443fffb96`). ADR-060 (manifiesto firmado de
rangos protegidos) y BACKLOG al día. Etiqueta `pre-release-etcd-mtls-vault-0.0.10` sobre el merge. README de la
portada actualizado en `docs/readme-etcd-mtls-vault` (PR aparte, solo documentación).

## Dónde lo dejamos (DAY323, miércoles 11 de noviembre, 06:38-22:30)
Commits del DAY323, todos subidos:
- `d44e0a2d0` Suricata: la provisión lo reinicia con reglas y yaml ya escritos y comprueba eth1 y firmas > 0 [SURICATA-ARRANQUE-D323]
- `6387cfd75` un solo reloj: suricata, zeek y wazuh toman la hora del defender (provisión lab-ntp); lab-clock-step
  recorre LAB_CLOCK_VMS y mitre-check lo exige [LAB-NTP-SENSORES-D323]
- `2fcac3ce9` mitre-check: una ventana [T0,T1] del reloj del defender para los tres sensores (scripts/mitre_ventana.py),
  Zeek a prueba de rotación (scripts/mitre_zeek_cosecha.sh), el veredicto exige el ataque por sensor, ningún FATAL en
  silencio; test-mitre-ventana (15 casos) [MITRE-VENTANA-D323]
- `2f74f5047` Jenkins: clave del repositorio desde pkg.jenkins.io por huella (scripts/jenkins/jenkins_instalar.sh,
  provisioning/jenkins/CLAVE); si no se instala, rc 3, aviso, repositorio retirado y el up sigue [JENKINS-CLAVE-D323]
- `95d349c89` los sensores .10 .11 .12 como infraestructura en la plantilla del manifiesto [PROTEGIDOS-SENSORES-D323]
- `443fffb96` el veredicto de protegidos saca la infraestructura del manifiesto que aplica el firewall [PROTEGIDOS-SENSORES-D323]
- `2859bed0a` `[EMECAS-PROGRESO-D323]` (la cabecera de emecas-progreso para su reloj en el fallo) y `e9eb4581e` el de
  documentación (DAY322 y DAY323 en BACKLOG; 8e.5 en ADR-060)
- `0479e69d9` merge del PR #153 a main; etiqueta `pre-release-etcd-mtls-vault-0.0.10` sobre él (como las anteriores,
  cada una en el merge de su PR)
- README de la portada (DAY323, al final del día): tabla de etiquetas desde el paper, sección «Control plane», puerta de
  calidad con seis VMs y el resultado del DAY323, límites y «What comes next» al día; prompt de continuidad corregido

Cuatro corridas de EMECAS+++ desde cero el DAY323, cada parada con su causa medida, su arreglo probado aparte y su commit:
1. mitre-check: Suricata con 0 alertas (corría con la config de fábrica: eth0, 0 firmas); además el eve.json se leía
   entero (el 04-nov pasó con alertas del 3-nov), la rotación horaria de Zeek se comía el barrido y un FATAL del loader
   acababa en rc 0. Y cada sensor con su propio reloj de Internet.
2. vagrant-up: el keyserver de la clave de Jenkins no respondió (errores a /dev/null, «✅ Jenkins instalado» falso).
3. lab-e2e-protegidos P2: con la hora del defender, el NTP de los sensores a .1 entraba en el episodio DDoS.
4. PASA: mitre-check con argus 1777 (1253 del ataque), Suricata 31 (31), Zeek 1114 (1068), 1080 corroborados.

## Primero, DAY324
1. `git status -sb`, `git log -3 --oneline` y `git tag --sort=-creatordate | head -3` (Mac): main al día con origin;
   el PR del README mergeado (si no, revisarlo y mergearlo); la etiqueta 0.0.10 en `0479e69d9`. Siguen sin commit los
   parcheadores de `scripts/etcd_ha/d3*` y `scripts/d31*` y dos `__pycache__/`. Borrar la rama vieja
   (`git branch -d feat/etcd-mtls-vault`, `git push origin --delete feat/etcd-mtls-vault`) si sigue.
2. Pendiente del PR1 que no entró: el README del etcd-server (`etcd-server/README.md` no existe): qué hace (mTLS,
   autorización por OU/CN, registro y latidos en etcd, claves HMAC en Vault, rutas del manifiesto), cómo se despliega en
   la VM etcd y qué hace si etcd o Vault caen. Leer antes el JSON del etcd-server y el ADR-060. PR pequeño de
   documentación.
3. Empezar el PR2 (abajo): primero medir; diseño antes de código.

## Después (en este orden, decidido por Alonso)
1. PR2 (HA): ≥3 nodos etcd (caída de uno, reelección, cuánto tardan en sincronizar; apagar todos y encender uno a uno),
   Vault en HA y su Ansible, nº de nodos en el inventario + plantilla Jinja2 de etcd.conf.yml. En PRs pequeños.
2. Después del PR2: la «dieta de adelgazamiento» (código deprecado fuera; Trivy).
   Más tarde (toca Jenkins y exige otro EMECAS): DEBT-SUPPLY-CHAIN-ORIGEN-OFICIAL-001 (queda el JDK de Jenkins por
   SDKMAN sin verificar, libsodium, el origen del sha de etcd, la huella de Wazuh sin publicar).
   Deudas sin orden: DEBT-ARGUS-INFRA-MOD-001, DEBT-SNIFFER-SYSTEM-SYSCTL-001, DEBT-LAB-ZONA-HORARIA-001,
   DEBT-HARDENED-FALCO-RUTAS-001, DEBT-VAULT-SELLADO-ALERTA-001, DEBT-CTU-START-VENTANA-001 (nueva),
   DEBT-DDOS-COLATERAL-LEGITIMO-001 (nueva).

## Decisiones de Alonso del DAY323
- Un solo reloj para el lab, el del defender: si un sensor no va con él es un bug operacional y la prueba falla
  diciéndolo, no lo compensa. El grafo del día lleva solo datos de esa sesión.
- Se arregla todo lo que para EMECAS; cada arreglo se prueba aparte y, con todos probados, EMECAS+++ desde cero.
- Jenkins se arregla con la clave del mantenedor por huella; si no se instala, el up sigue (EMECAS no usa Jenkins; las
  claves del lab las crean los aprovisionadores de Vagrant) sin dejar un repositorio roto.
- Los sensores del lab son infraestructura del NDR (plantilla del manifiesto, MAC vacía).
- DEBT-DDOS-COLATERAL-LEGITIMO-001: al afrontarla, primero medir qué ve el modelo; «van a ser las dos cosas, como
  mínimo» (benigno de servicio en el entrenamiento, en los dos sentidos, sin que el puerto solo decida; umbral de
  evidencia por origen en la atribución del episodio). «No descartemos alguna sorpresa».

## A tener presente
- Regla del DAY323 para lo nuevo: cada operación comprueba su efecto concreto, sobre estado nuevo, y se prueba también
  que falla cuando debe. Lo esperado en un test sale de la fuente (manifiesto, plantilla), nunca de una lista a mano.
- Claude: entregar siempre los ficheros COMPLETOS en el `cat > f <<'EOF'`, nunca un marcador (DAY323 se colaron dos).
  Si un fichero empieza por línea en blanco, decirlo (cuenta en el sha256).
- Propuesta sin decidir (de Claude, DAY323): poder reanudar EMECAS desde un hito con instantáneas de Vagrant, solo para
  probar arreglos; el cierre siempre desde cero.
- mitre-check tarda ahora ~14 min (espera ~2 min al archivado de Zeek, tests y relojes). EMECAS+++ entera ~4 h; con
  tiempos guardados, `make emecas-progreso` ya da porcentaje.
- Horas de las VMs en UTC (Alonso en Europe/Madrid, UTC+1): decirlo al mostrarlas.
- RAM: las seis VMs ocupan ~19 GB de RSS de 32; la swap va justa en EMECAS.
- git en el Mac con `core.fileMode=false` (los scripts nuevos quedan 100644; se lanzan con bash/python3).
- El banco de Claude es nuevo en cada sesión: Falco 0.43.1, Vault 2.2.1 y la clave de Jenkins
  (5E386EAD…7198F4B714ABFC68) se descargan y verifican en el lab, nunca los pasa Claude.
