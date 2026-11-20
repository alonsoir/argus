# aRGus NDR — prompt de continuidad DAY333 (sigue de DAY332)

Responde siempre en español. Alonso es el único desarrollador de aRGus NDR (C++20, NDR para infraestructura crítica,
arXiv:2604.04952). Principio: «medir, no votar». El repo es SOLO LECTURA para Claude: Alonso hace commits, push y PR.
Raíz del repo en el Mac: `~/CLionProjects/test-zeromq-docker`.

## Dónde estamos
- **DAY332** (detalle en `docs/BACKLOG.md`, sección DAY332):
  - **XGBoost retirado** (PR de `fix/xgboost-retirar`, EMECAS+++ desde cero VERDE 4h29m): fuera la instalación del
    `Vagrantfile` (pip sin verificar y dos `curl`), `plugin_xgboost`, su test, sus comprobaciones y targets del
    `Makefile` (`deploy-models`, `sign-models`, `test-integ-xgboost-1`), los cuatro scripts de entrenamiento que lo
    importaban y los `.ubj`. DEBT-XGBOOST-RETIRAR-001 cerrada.
  - Medido: el ml-detector no enlaza XGBoost (`objdump -p` de su binario); sus tres detectores llevan los árboles
    compilados; DDoS v2 no lo necesita ni para entrenar.
- **Decisiones de Alonso DAY332**: retirar XGBoost tras medir que DDoS v2 no lo necesita; las cabezas internal,
  ransomware y traffic (rotas) se repensarán y reentrenarán con la tecnología de DDoS v2.
- Parcheadores d332 en `archivo/parcheadores-d332` (y d331, d330, d324-d329, d313-d323 en las suyas); ninguno en el Mac.
- Lab al cerrar DAY332: EMECAS verde terminado (8 VMs); Alonso lo para al cerrar la sesión.

## Lo siguiente, en este orden (decisión de Alonso DAY331)
1. **Terceros por lente** (DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001): Vault `VAULT_PIN`, etcd, Arrow y su `.deb`,
   libbpf; un PR por lente, cada versión en `provisioning/<producto>/`, como ONNX y libsodium.
2. **DEBT-SNIFFER-FLOW-UID-TCP-LARGA-001**: medir cuántos paquetes lleva cada flujo partido en el bronce (un número fijo
   apunta al tope de DEBT-SNIFFER-FLOW-PACKET-CAP-200; un tiempo fijo, a la caducidad de DAY307).
3. **PR2c** (Vault en clúster Raft; se borran `disco-sin-vault.json` y `VIGILANCIA_DISCO_JSON`): épico, partido si se
   puede. Dos o tres semanas (estimación de Alonso).
4. **Documentación** (decidida DAY326): ADR-060 sección 7 y el procedimiento de DEBT-VAULT-SELLADO-ALERTA-001, contra la
   documentación de Vault 2.2.1; ADR-048 (DAY324-329) y ADR-060; y DEBT-DOCS-XGBOOST-001 (ADR-026 Track 1,
   `docs/XGBOOST-VALIDATION.md`, `docs/xgboost/`, README).
5. Por medir: suelo del manifiesto (b) (DEBT-PROTEGIDOS-SUELO-REVAULT-001); después, borrar en el defender
   `/var/lib/ml-defender/firewall-linaje-anterior/`.
6. Otras: DEBT-REPO-PARCHEADORES-EN-MAIN-001, DEBT-LIBSODIUM-SO-VERSION-CONFLICT-001 (medir antes `/proc/<pid>/maps`),
   DEBT-CRYPTO-NONCE-REINICIO-001 (medir primero), DEBT-DDOS-COLATERAL-LEGITIMO-001 (después del PR2, antes de REA),
   DEBT-EMECAS-PROGRESO-REFERENCIA-001, DEBT-EMECAS-ESPERA-ANFITRION-001, DEBT-E2E-VAGRANT-SSH-RESTO-001,
   DEBT-LAB-PROVISION-SCRIPT-MUERTO-001, DEBT-ONNX-RUNTIME-ORIGEN-001 (seguimiento). Repensar y reentrenar las cabezas
   internal, ransomware y traffic con el método de DDoS v2 (orden sin decidir).
7. **Subir la fecha de Debian**: un commit que cambia `argus_debian_snapshot` y su EMECAS+++. No a una fecha con el
   `6.1.0-55` mientras el #1154153 siga abierto.
8. **2-dic-2026**: caduca la clave de OBS de Zeek; comprobar que OBS la ha prorrogado con la misma huella.

## Lecciones medidas (DAY331-332)
- A las ramas de archivo no se les abre PR: GitHub deja mergearlas con un clic (#171).
- Dos instaladores de lo mismo esconden cuál manda: el que comprobaba nunca instalaba. Lo importante, en un único lugar.
- `ldd` de una biblioteca suelta no dice qué carga un proceso; para eso, `/proc/<pid>/maps`. Si un resultado
  contradice algo que funciona desde hace meses, sospechar primero de la medida.
- `pgrep -f <nombre>` dentro de `vagrant ssh -c` se encuentra a sí mismo: `pgrep -x`.
- `objdump -p` del Mac (Xcode) lee los `NEEDED` de un binario ELF sin levantar el lab.
- Antes de retirar algo, preguntar quién lo va a necesitar; un paquete nombrado en un comentario no es una dependencia.
- El log del EMECAS está en `logs/lab/emecas/emecas_<fecha>.log` (y `emecas_actual.log`).

## Datos útiles
- Nodos: control-1 `192.168.100.20`, control-2 `.21`, control-3 `.22`; 1024 MB, 2 vCPU. etcd 3.6.16 (cliente 2381,
  peers 2382, mTLS, RBAC por CN). Vault 2.2.1 (solo en control-1). Clave transit: huella `a1b73e22cf85899a`.
- VMs en VirtualBox: `ml-defender-gateway-lab`, `ml-defender-client`, `argus-suricata`, `argus-zeek`, `argus-wazuh`,
  `argus-control-1/2/3`; en Vagrant: `defender`, `client`, `suricata`, `zeek`, `wazuh`, `control-1/2/3`. VirtualBox
  7.2.10; Guest Additions de la caja 6.0.0. Caja `debian/bookworm64` 12.20240905.1 en todas.
- Kernels: caja `6.1.0-25-amd64` (6.1.106-3); el del lab, el de la fecha: `6.1.0-54-amd64` (6.1.190-1).
- Terceros en `provisioning/<producto>/`: Falco 0.43.1, Wazuh 4.14.10-1, Zeek serie 9.0 (hoy 9.0.1-0), ONNX Runtime
  1.17.1 (NuGet, SHA512) y libsodium 1.0.19 (minisign + SHA256). En el `Vagrantfile`: Vault `VAULT_PIN`, etcd v3.6.16 y
  Apache Arrow 24.0.0-1; sin fijar: el `.deb` del repositorio de Arrow. XGBoost: retirado DAY332.
- Binario del ml-detector: `ml-detector/build-production/ml-detector` (visible desde el Mac).
- libsodium: bookworm trae la 1.0.18 (`.so.23`), que piden `libzmq5`, `libzmq3-dev` y `vim`; la nuestra, 1.0.19
  (`.so.26`) en `/usr/local`, marca `/usr/local/lib/argus-libsodium.verificado`. download.libsodium.org pasa las
  versiones antiguas a `releases/old/`.
- Llamadas del anfitrión a una VM: `perl scripts/emecas/con_limite.pl <s> vagrant ssh <vm> …`, con
  `argus_lab_llamada_vm_limite_s` (60) de `all.yml`.
- Lanzar EMECAS: `nohup bash scripts/emecas/emecas_run.sh emecas+++ production < /dev/null > /dev/null 2>&1 &`.
  Vigilar: `bash scripts/emecas/emecas_watch.sh 60`. Parar: `ps -axo pid,ppid,pgid,command | grep 'make emecas'`
  para el pgid del `make`, y `kill -TERM -<pgid>; sleep 5; kill -KILL -<pgid>`.
- PRs con `gh` (instalado y con sesión): `gh pr create --base main --head <rama>`, `gh pr diff <rama> --name-only`; el
  merge lo hace Alonso en la web.
- Duraciones EMECAS+++ (verdes): DAY332 XGBoost fuera 4h29m; DAY331 libsodium 4h27m; DAY330 grub + ONNX 4h16m, Zeek
  4h43m. DAY329: 4h35m (vagrant-up 29m, reload 6m, provision 42m, bootstrap 31m, test-all 16m, lab-e2e 1h48m,
  mitre-check 10m).
- Anfitrión (MacBook Pro, 16 hilos, 32 GB): sin lab carga ~2-3, swap 0; lab sano carga 5-8, swap hasta 7,2 GB;
  `anfitrion-recursos` (perfil emecas): carga 12, swap 4096 MB.

## Forma de trabajar (siguen en vigor)
- Predicción escrita antes de cada medida; si no sale, parar y mirar. Tests que también prueban que fallan cuando
  deben (y que la herramienta no se salte la prueba). Complejidad lineal como mucho. El JSON es la ley; lo importante,
  en un único lugar (JSON, Makefile, protobuf, Ansible, Jinja2, `provisioning/<producto>/`).
- Parcheadores: sha256 de partida, cada ancla las veces exactas, nada escrito si algo falla; se copian a
  `scripts/etcd_ha/` y se ejecutan desde ahí, con su sha256 (los de documentación, desde `/tmp`). Lo que lleve
  tabuladores, por parcheador. Al acabar, a la rama de archivo del día, solo con push.
- Comandos exactos, en orden, diciendo dónde se ejecutan; salida a `/tmp/…` y `; cat`; no encadenar salidas grandes.
  `git grep`, nunca `grep -rn .` en la raíz. Un commit por cambio lógico, con el mensaje propuesto y `git status`
  antes del `git add`, y `git log` después. Nunca reescribir la historia. Software de terceros solo de sus
  mantenedores, con su hash o firma. Sin usos nuevos de curl. Mientras corre un EMECAS no se aplica nada al repo ni se
  toca el lab. Toda llamada a una VM, con límite.
- Claves privadas nunca en el repo ni por /vagrant.
- **PRs cortos** (decisión de Alonso DAY329): una deuda o un tema por PR, cada uno con su EMECAS; los gordos, solo si
  son de tipo épico. Dos PRs pueden compartir EMECAS si van apilados. Los de documentación o que no tocan ni el lab ni
  el pipeline, sin EMECAS. La documentación puede ir en español; el README, en inglés.
- **Entorno** (desde DAY329): Alonso trabaja en local con la Terminal de macOS (zsh); Claude, en su cliente de
  escritorio. En zsh, las variables siempre con llaves (`"${C}:refs/…"`), nada que empiece por `=` sin comillas, y lo
  que lleve bucles o aritmética, mejor dentro de `bash -c '…'`.
