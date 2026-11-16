# aRGus NDR — prompt de continuidad DAY329 (sigue de DAY328)

Responde siempre en español. Alonso es el único desarrollador de aRGus NDR (C++20, NDR para infraestructura crítica,
arXiv:2604.04952). Principio: «medir, no votar». El repo es SOLO LECTURA para Claude: Alonso hace commits, push y PR.
Raíz del repo en el Mac: `~/CLionProjects/test-zeromq-docker`.

## Dónde estamos
- Rama: `feat/etcd-ha-plano-control` (PR2b de **DEBT-ETCD-HA-TLS-RAFT-001**, ADR-048), en `19ee5962e` más los dos
  commits de documentación de DAY328. **El PR2b sigue sin la corrida que certifica.**
- **EMECAS+++ desde cero DAY328 (05:03-09:50): verde hasta lab-e2e, colgado en C7 de `lab-e2e-vigilancia`
  (`d322_reinicio_vault.sh`), parado a mano (`rc=143`).** Ningún fallo es del PR2b. Causa, medida:
  - Debian publicó el kernel `6.1.0-55-amd64` (6.1.192-1, del 14-nov) entre la corrida de DAY327 (`-54`) y la de hoy.
  - Al reiniciar control-1 (C7) arranca ese kernel y **sufre un oops en ext4** a los 12 s
    (`ext4_mb_load_buddy_gfp+0xbc`, puntero nulo); el hilo muerto deja una operación de jbd2 abierta y todo lo que
    escribe en disco queda en `D` para siempre: VM viva (ping, saludo de sshd, puerto de etcd) y sin sistema de
    ficheros. Dos arranques de dos en control-1; control-3 arranca sana con el mismo kernel.
  - El examinador no tiene tiempo límite en sus `vagrant ssh` y se quedó mudo 60 minutos en vez de fallar.
- **El lab ejecuta el kernel de la caja** (`6.1.0-25`, de 2024; caja fijada `debian/bookworm64 12.20240905.1`) aunque
  instala el último: lo instalado solo se arranca en C7.
- **Decisión de Alonso (DAY328): todas las imágenes del pipeline iguales, mismo kernel** (homogeneidad en lo que
  podemos controlar). Cómo, sin decidir: DEBT-LAB-KERNEL-HOMOGENEO-001.
- Pruebas fuera del repo: `~/argus-evidencias/d328/` (salidas, capturas, volcado de memoria de control-1 y el borrador
  del informe para Debian, `d328_informe_debian.txt`).
- Sin trackear en `scripts/etcd_ha/` (aplicados; se archivan tras el EMECAS bueno): los `d324_*`, `d325_*`, `d326_*`,
  `d327_*` y `d328_docs.py`.
- Lab al cerrar DAY328: no sirve (control-1 no arranca con el `-55`; control-3 reiniciada). El siguiente EMECAS lo
  destruye; para apagarlo antes, `vagrant halt` y, si control-1 no obedece, `VBoxManage controlvm argus-control-1
  poweroff`.

## Lo siguiente, en este orden
1. **Kernel (DEBT-LAB-KERNEL-HOMOGENEO-001)**. Medir antes de decidir: por dónde llega el kernel nuevo
   (`unattended-upgrades` o un `apt-get`; buscar en `logs/lab/emecas/emecas_20261116_050318.log`), si el `6.1.0-54`
   (6.1.190-1) sigue instalable desde repositorios oficiales (`apt-cache policy linux-image-6.1.0-54-amd64` en una VM;
   si no, snapshot.debian.org) y cuánto cuesta reiniciar las 8 VMs en `vagrant up`. Opciones: (a) versión declarada en
   `group_vars/argus_dev.yml`, paquete retenido, reinicio en el `up` y un paso de EMECAS que compare `uname -r` de
   todas las VMs con la declarada; (b) quedarse en el kernel de la caja; (c) fijar la fecha entera de Debian por
   snapshot. Decide Alonso.
2. **Examinador (DEBT-E2E-VAGRANT-SSH-SIN-LIMITE-001)**: tiempo límite en cada llamada a la VM de
   `d322_reinicio_vault.sh`, veredicto ❌ con el paso, test de que falla cuando la VM no contesta; línea de vida de C7
   en el log de EMECAS.
3. **EMECAS+++ desde cero, el que certifica** (~5 h). CLion cerrado. `nohup bash scripts/emecas/emecas_run.sh emecas+++
   production < /dev/null > /dev/null 2>&1 &` (una sola vez: un segundo lanzamiento sale con 1 sin tocar nada);
   `make emecas-progreso` (su porcentaje no vale: referencia de 22 pasos); terminado cuando existe
   `logs/lab/emecas/emecas_actual.rc`. La parte tras `mitre-check` sigue sin verse desde DAY323.
4. Si verde: archivar los parcheadores en una rama de archivo del remoto, borrarlos del Mac, push, PR, merge. Después,
   **PR2c** (Vault en clúster Raft; se borran `disco-sin-vault.json` y `VIGILANCIA_DISCO_JSON`).
5. **Informe a Debian (DEBT-KERNEL-EXT4-OOPS-6-1-192-001)**: revisar el borrador y enviarlo (`reportbug` o correo a
   `submit@bugs.debian.org`). Antes, si se puede, `dumpe2fs -h` del disco de control-1 arrancándola con el `6.1.0-25`.
6. **Documentación** (decidida DAY326, pendiente): ADR-060 sección 7 y el procedimiento de DEBT-VAULT-SELLADO-ALERTA-001
   (clave de desellado: Shamir con `-pgp-keys` y YubiKey, HSM solo Enterprise, KMS de nube, transit desde el Vault de la
   VM admin; nunca en claro en disco), contra la documentación de Vault 2.2.1; ADR-048 (DAY324-328) y ADR-060.
7. **Decidido DAY326, por medir**: suelo del manifiesto (b) (DEBT-PROTEGIDOS-SUELO-REVAULT-001).
8. **Deudas fuera del PR2b**: DEBT-SNIFFER-FLOW-UID-TCP-LARGA-001 (medida barata pendiente: `ss -tn` en control-2
   contra `.20:2382`, dos veces con un minuto, para confirmar que es una sola conexión), DEBT-CRYPTO-NONCE-REINICIO-001
   (medir primero), DEBT-DDOS-COLATERAL-LEGITIMO-001 (después del PR2, antes de REA; las dos líneas de DAY323 más el
   arranque en frío), DEBT-EMECAS-PROGRESO-REFERENCIA-001.
9. En el defender, borrar `/var/lib/ml-defender/firewall-linaje-anterior/` cuando se decida lo del suelo.

## Lecciones medidas DAY328
- **«Desde cero» no es lo mismo de un día a otro si algo de fuera no está fijado**: el kernel cambió entre dos corridas.
  Y lo que se instala sin arrancarse no está probado.
- **Un examinador sin tiempo límite convierte un rojo en silencio**: toda llamada a una VM lleva límite y veredicto.
- Una VM puede estar viva para el ping y los puertos y muerta para todo lo que escribe: comprobar un puerto no basta
  como prueba de salud.
- Cuando el kernel sufre un oops, el dueño del bloqueo no aparece entre las tareas bloqueadas: está muerto. Buscar
  `BUG:` u `Oops` en el registro del kernel **desde el segundo 0** (un filtro «después del segundo 20» lo escondió).
- Con la VM sorda: consola por `VBoxManage controlvm <vm> screenshotpng`; memoria por `VBoxManage debugvm <vm>
  dumpvmcore` y `strings`; dentro, `/proc/pressure/*`, `/proc/diskstats`, `/proc/[0-9]*/task/*/status` y
  `sudo cat /proc/<pid>/task/<tid>/stack`. `ps` se cuelga; las sondas, con `nohup … &` y salida a fichero.
- Hipótesis de Claude que los datos tumbaron hoy: «falta de memoria en control-1»; «el disco virtual no responde»;
  «`sudo` es lo que cuelga las sesiones»; «la carpeta `/vagrant`»; «el segundo arranque irá bien»; «control-3 fallará
  igual»; «soltar el ssh colgado y seguir la corrida». Acertadas: jbd2 esperando en el commit; control-2 en el kernel
  de la caja; el primer arranque con el mismo oops que el segundo.

## Datos útiles
- Nodos: control-1 `192.168.100.20`, control-2 `.21`, control-3 `.22`; 1024 MB, 2 vCPU. etcd 3.6.16 (cliente 2381,
  peers 2382, mTLS, RBAC por CN). Vault 2.2.1 (solo en control-1). Clave transit: huella `a1b73e22cf85899a`.
- VMs en VirtualBox: `ml-defender-gateway-lab`, `ml-defender-client`, `argus-suricata`, `argus-zeek`, `argus-wazuh`,
  `argus-control-1/2/3`. VirtualBox 7.2.10; Guest Additions de la caja 6.0.0.
- Kernels: caja `6.1.0-25-amd64` (6.1.106-3); DAY327 instaló `6.1.0-54` (6.1.190-1); DAY328 `6.1.0-55` (6.1.192-1).
- C7: `lab_e2e_vigilancia.sh` guarda su salida en `logs/lab/day303/lab_vigilancia_<marca>/c7_reinicio_vault.txt`.
- Parar una corrida de EMECAS: `ps -axo pid,ppid,pgid,command | grep 'make emecas'` para el pgid del `make`, y
  `kill -TERM -<pgid>; sleep 5; kill -KILL -<pgid>`.
- Falco: `provisioning/falco/argus_lab.yaml`; a las VMs con `vagrant provision <vm> --provision-with falco`. Dueño del
  desellado: `argus_lab_es_desellado`. Wazuh: 100551/100552/100553.
- Targets: `falco-silencio`, `test-falco-silencio`, `anfitrion-recursos` (`RECURSOS_PERFIL=emecas|lab_e2e`),
  `test-anfitrion-recursos`, `etcd-cluster-deploy`, `etcd-vm-deploy`, `test-etcd-cluster`, `test-etcd-reinicio`,
  `test-plano-control`, `etcd-vm-check`, `protegidos-pubkey`, `protegidos-bootstrap`, `test-argus-infra`,
  `test-clave-bronce`, `test-vault-unseal`, `lab-e2e` y sus `lab-e2e-*`, `mitre-check`, `emecas-progreso`.
- Duraciones EMECAS+++: DAY327 vagrant-up 1h03m, bootstrap 51m, test-all 18m, lab-e2e 1h51m, emecas++ ~13 min,
  mitre-check 25 min; DAY328 vagrant-up 52m46s, bootstrap 40m17s, test-all 15m37s (C7 empezó a las 3h46m).
- Anfitrión (MacBook Pro, 16 hilos, 32 GB): sin lab carga ~3 (hoy 11,24 al empezar, máximo 12), swap 0,2-1,5 GB; lab
  sano carga 5-8, swap hasta 7,2 GB, nivel ≥ 67, presión 1.

## Forma de trabajar (siguen en vigor)
- Predicción escrita antes de cada medida; si no sale, parar y mirar. Tests que también prueban que fallan cuando
  deben (y que la herramienta no se salte la prueba). Complejidad lineal como mucho. El JSON es la ley.
- Parcheadores: sha256 de partida, cada ancla las veces exactas, nada escrito si algo falla; se copian a
  `scripts/etcd_ha/` y se ejecutan desde ahí, con su sha256. Lo que lleve tabuladores, por parcheador.
- Comandos exactos, en orden, diciendo dónde se ejecutan; salida a `/tmp/…` y `; cat`; no encadenar salidas grandes.
  `git grep`, nunca `grep -rn .` en la raíz. Un commit por cambio lógico, con el mensaje propuesto y `git status`
  antes del `git add`. Nunca reescribir la historia. Software de terceros solo de sus mantenedores. Sin usos nuevos
  de curl. Mientras corre un EMECAS no se aplica nada al repo ni se toca el lab.
- Claves privadas nunca en el repo ni por /vagrant.
