# aRGus NDR — prompt de continuidad DAY330 (sigue de DAY329)

Responde siempre en español. Alonso es el único desarrollador de aRGus NDR (C++20, NDR para infraestructura crítica,
arXiv:2604.04952). Principio: «medir, no votar». El repo es SOLO LECTURA para Claude: Alonso hace commits, push y PR.
Raíz del repo en el Mac: `~/CLionProjects/test-zeromq-docker`.

## Dónde estamos
- Rama: `feat/etcd-ha-plano-control` (PR2b de **DEBT-ETCD-HA-TLS-RAFT-001**, ADR-048), con los commits de DAY329 y el
  de documentación. **El PR2b está CERTIFICADO: EMECAS+++ desde cero VERDE el 17-nov (08:35-13:10, 4h35m, rc=0)**, con
  todos los pasos, también los de detrás de `mitre-check`, que no se veían desde DAY323.
- **DEBT-LAB-KERNEL-HOMOGENEO-001 CERRADA** (decisión de Alonso: opción (c)). Todas las VMs en la misma fecha de
  Debian: `argus_debian_snapshot: "20261115T000000Z"` en `ansible/inventory/group_vars/all.yml` (fuente única de lo
  común a todas las lentes; validación en `scripts/emecas/lab_comun.rb`; si falta o está mal, Vagrant para: error de
  fabricante). Aprovisionador `debian-fecha` (tras `apt-espera`, en cada up): fuentes a snapshot.debian.org en esa fecha,
  `full-upgrade`, comprobación del kernel de la fecha. EMECAS: `vagrant up --provision-with apt-espera,debian-fecha`,
  `vagrant reload --no-provision`, `vagrant provision`, y `kernel-homogeneo` (8 VMs en `6.1.0-54-amd64`, medido).
- **DEBT-E2E-VAGRANT-SSH-SIN-LIMITE-001 CERRADA en C7**: `d322_reinicio_vault.sh` con tiempo límite en cada llamada
  (`scripts/emecas/con_limite.pl`, mata el grupo de procesos; entrada de terminal → `/dev/null`) y ❌ por paso; C7 deja
  su salida en el log de EMECAS (`c7:`). El resto de E2E con `vagrant ssh` (76 scripts): DEBT-E2E-VAGRANT-SSH-RESTO-001.
- **Bug de Debian #1154153** (oops de ext4 en 6.1.192-1) presentado; otro afectado confirmó la regresión (6.1.190-1 va
  bien) y hay bisección upstream (`29897d75d649`). Decisión de Alonso: hecha nuestra parte; solo pasivo.
- Sin trackear en `scripts/etcd_ha/`: los parcheadores `d324_*` a `d329_*` (aplicados). Se archivan al cerrar el PR2b.
- Lab al cerrar DAY329: arriba y sano tras el EMECAS verde (8 VMs, kernel `6.1.0-54`).

## Lo siguiente, en este orden
1. **Cerrar el PR2b** (Alonso): archivar los parcheadores sin trackear en la rama de archivo
   `archivo/parcheadores-d324-d329` del remoto (lista con `git ls-files --others --exclude-standard scripts/etcd_ha/`,
   nunca con comodines), borrarlos del Mac, push, PR, merge.
2. **Decide Alonso el orden** entre: **PR2c** (Vault en clúster Raft; se borran `disco-sin-vault.json` y
   `VIGILANCIA_DISCO_JSON`) y **DEBT-LAB-VERSIONES-TERCEROS-001** (su propio PR: versiones de terceros por lente).
3. **Documentación** (decidida DAY326, pendiente): ADR-060 sección 7 y el procedimiento de DEBT-VAULT-SELLADO-ALERTA-001
   (clave de desellado: Shamir con `-pgp-keys` y YubiKey, HSM solo Enterprise, KMS de nube, transit desde el Vault de la
   VM admin; nunca en claro en disco), contra la documentación de Vault 2.2.1; ADR-048 (DAY324-329) y ADR-060.
4. **Decidido DAY326, por medir**: suelo del manifiesto (b) (DEBT-PROTEGIDOS-SUELO-REVAULT-001).
5. **Deudas fuera del PR2b**: DEBT-SNIFFER-FLOW-UID-TCP-LARGA-001 (medida barata: `ss -tn` en control-2 contra
   `.20:2382`, dos veces con un minuto), DEBT-CRYPTO-NONCE-REINICIO-001 (medir primero), DEBT-DDOS-COLATERAL-LEGITIMO-001
   (después del PR2, antes de REA; las dos líneas de DAY323 más el arranque en frío), DEBT-EMECAS-PROGRESO-REFERENCIA-001
   (ahora con 35 pasos: el 22 de referencia ya no vale), DEBT-E2E-VAGRANT-SSH-RESTO-001,
   DEBT-LAB-PROVISION-SCRIPT-MUERTO-001 (borrar `scripts/vagrant-provision.sh`).
6. En el defender, borrar `/var/lib/ml-defender/firewall-linaje-anterior/` cuando se decida lo del suelo.
7. **Subir la fecha de Debian**: un commit que cambia `argus_debian_snapshot` y su EMECAS+++ desde cero. No a una
   fecha con el `6.1.0-55` (6.1.192-1) mientras el #1154153 siga abierto.

## Lecciones medidas DAY329
- Lo que no se arranca no está probado: `kernel-homogeneo` mira `uname -r`, no lo instalado.
- El kernel entraba por dos sitios: `unattended-upgrades` (en control-3, el 16-nov a las 06:22, con ~120 paquetes más,
  en plena corrida) y, en defender, el metapaquete `linux-headers-amd64`. Ninguno salía en el log de EMECAS como upgrade.
- En Vagrant, el `name:` de un aprovisionador `shell` es solo su etiqueta: con nombre es
  `config.vm.provision "<nombre>", type: "shell"`. Si no, `--provision-with` responde «is not a known provisioner».
- Un `alarm` sobre `vagrant` no basta: su `ssh` hijo sigue con la salida abierta y quien la lee espera. Hay que matar
  el grupo de procesos. Y en su propio grupo, si la entrada es un terminal, leerlo la detiene (SIGTTIN): `/dev/null`.
- Un test también puede dar verde en falso: el `vagrant` falso dormía menos que el límite. Comprobar que cada caso
  falla con el código viejo (aquí: 0/2, 5/7).
- Hipótesis de Claude que los datos tumbaron hoy: «el kernel entra por un `apt-get upgrade`»; «las control lo instalan
  en otro log»; «`name:` basta para `--provision-with`». Acertadas: snapshot responde rápido (4 s), el `-54` sigue en
  `bookworm-security`, el `reload` arranca el kernel de la fecha.

## Datos útiles
- Nodos: control-1 `192.168.100.20`, control-2 `.21`, control-3 `.22`; 1024 MB, 2 vCPU. etcd 3.6.16 (cliente 2381,
  peers 2382, mTLS, RBAC por CN). Vault 2.2.1 (solo en control-1). Clave transit: huella `a1b73e22cf85899a`.
- VMs en VirtualBox: `ml-defender-gateway-lab`, `ml-defender-client`, `argus-suricata`, `argus-zeek`, `argus-wazuh`,
  `argus-control-1/2/3`. VirtualBox 7.2.10; Guest Additions de la caja 6.0.0.
- Kernels: caja `6.1.0-25-amd64` (6.1.106-3); el del lab, el de la fecha: `6.1.0-54-amd64` (6.1.190-1). En
  bookworm-security ya hay 6.1.192-2 (sin saber si arregla el #1154153).
- Terceros hoy (DEBT-LAB-VERSIONES-TERCEROS-001): Falco 0.43.1 y Wazuh 4.14.10-1 (`provisioning/*/VERSION`), Vault
  `VAULT_PIN`, etcd v3.6.16 y Apache Arrow 24.0.0-1 en el `Vagrantfile`; Zeek y el `.deb` del repositorio de Arrow, sin fijar.
- Llamadas del anfitrión a una VM: `perl scripts/emecas/con_limite.pl <s> vagrant ssh <vm> …`, con
  `argus_lab_llamada_vm_limite_s` (60) de `all.yml`.
- C7: `lab_e2e_vigilancia.sh` guarda su salida en `logs/lab/day303/lab_vigilancia_<marca>/c7_reinicio_vault.txt` y la
  deja en el log de EMECAS con el prefijo `c7:`.
- Parar una corrida de EMECAS: `ps -axo pid,ppid,pgid,command | grep 'make emecas'` para el pgid del `make`, y
  `kill -TERM -<pgid>; sleep 5; kill -KILL -<pgid>`. Vigilar: `bash scripts/emecas/emecas_watch.sh 60`.
- Falco: `provisioning/falco/argus_lab.yaml`; a las VMs con `vagrant provision <vm> --provision-with falco`. Dueño del
  desellado: `argus_lab_es_desellado`. Wazuh: 100551/100552/100553.
- Targets: `kernel-homogeneo`, `test-kernel-homogeneo` (lab_comun, con_limite, kernel_homogeneo, provision_with),
  `test-c7-limite`, `falco-silencio`, `test-falco-silencio`, `anfitrion-recursos` (`RECURSOS_PERFIL=emecas|lab_e2e`),
  `test-anfitrion-recursos`, `etcd-cluster-deploy`, `etcd-vm-deploy`, `test-etcd-cluster`, `test-etcd-reinicio`,
  `test-plano-control`, `etcd-vm-check`, `protegidos-pubkey`, `protegidos-bootstrap`, `test-argus-infra`,
  `test-clave-bronce`, `test-vault-unseal`, `lab-e2e` y sus `lab-e2e-*`, `mitre-check`, `emecas-progreso`.
- Duraciones EMECAS+++ DAY329 (verde, 4h35m): vagrant-up 29m13s + vagrant-reload 6m09s + vagrant-provision 42m08s
  (77 min; antes 53-57 min en un solo up), bootstrap 31m21s, test-all 15m37s, test-etcd-reinicio 4m45s, test-c7-limite
  4m03s, test-e2e-synthetic 6m42s, lab-e2e 1h48m, mitre-check 10m02s. C7: control-1 de vuelta en 44 s; R5 en 6 s.
- Anfitrión (MacBook Pro, 16 hilos, 32 GB): sin lab carga ~2-3, swap 0; lab sano carga 5-8, swap hasta 7,2 GB.

## Forma de trabajar (siguen en vigor)
- Predicción escrita antes de cada medida; si no sale, parar y mirar. Tests que también prueban que fallan cuando
  deben (y que la herramienta no se salte la prueba). Complejidad lineal como mucho. El JSON es la ley; lo importante,
  en un único lugar (JSON, Makefile, protobuf, Ansible, Jinja2).
- Parcheadores: sha256 de partida, cada ancla las veces exactas, nada escrito si algo falla; se copian a
  `scripts/etcd_ha/` y se ejecutan desde ahí, con su sha256. Lo que lleve tabuladores, por parcheador.
- Comandos exactos, en orden, diciendo dónde se ejecutan; salida a `/tmp/…` y `; cat`; no encadenar salidas grandes.
  `git grep`, nunca `grep -rn .` en la raíz. Un commit por cambio lógico, con el mensaje propuesto y `git status`
  antes del `git add`. Nunca reescribir la historia. Software de terceros solo de sus mantenedores. Sin usos nuevos
  de curl. Mientras corre un EMECAS no se aplica nada al repo ni se toca el lab. Toda llamada a una VM, con límite.
- Claves privadas nunca en el repo ni por /vagrant.
