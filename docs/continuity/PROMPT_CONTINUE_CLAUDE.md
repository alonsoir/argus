# aRGus NDR — prompt de continuidad DAY331 (sigue de DAY330)

Responde siempre en español. Alonso es el único desarrollador de aRGus NDR (C++20, NDR para infraestructura crítica,
arXiv:2604.04952). Principio: «medir, no votar». El repo es SOLO LECTURA para Claude: Alonso hace commits, push y PR.
Raíz del repo en el Mac: `~/CLionProjects/test-zeromq-docker`.

## Dónde estamos
- **DAY330: tres PRs cortos, cada uno con su EMECAS+++ desde cero VERDE** (detalle en `docs/BACKLOG.md`, sección DAY330):
  - **#167** grub: `debian-fecha` fija `grub-pc/install_devices` al disco de `/boot` antes del `full-upgrade` (la caja
    lo trae sin valor y el postinst paraba; DEBT-LAB-GRUB-INSTALL-DEVICES-001 CERRADA).
  - **#168** ONNX Runtime 1.17.1 del paquete **NuGet** oficial de Microsoft con su SHA512
    (`provisioning/onnxruntime/`, `scripts/terceros/onnxruntime_instalar.sh`): `github.com/microsoft/onnxruntime` da
    404 desde el 17-nov-2026.
  - **Zeek** con la serie 9.0 fijada y la clave de OBS comprobada por huella (`provisioning/zeek/`,
    `scripts/vigilancia/zeek_instalar.sh`). Si al leer esto su PR no está en `main`, es lo primero.
- Parcheadores `d330_*` en la rama de archivo `archivo/parcheadores-d330`, que no se mergea ni se borra; ninguno en el Mac.
- **Pendiente de decisión de Alonso**: las versiones de Zeek y ONNX se pusieron en `provisioning/<producto>/` como Falco
  y Wazuh, no en el group_vars de cada lente que él decidió el DAY329 (ver DEBT-LAB-VERSIONES-TERCEROS-001, DAY330).
- Cuota de Claude justa hasta el viernes 21-nov a las 11:00: económicos en mensajes y lecturas.
- Lab al cerrar DAY330: arriba y sano tras el EMECAS verde de Zeek (8 VMs, kernel `6.1.0-54`).

## Lo siguiente, en este orden (decisión de Alonso DAY330)
1. Cerrar lo de Zeek si falta, y la decisión de dónde viven las versiones de terceros.
2. **Terceros por lente** (DEBT-LAB-VERSIONES-TERCEROS-001 y DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001): libsodium y
   XGBoost (mismo bloque que ONNX), Vault `VAULT_PIN`, etcd, Arrow y su `.deb`, libbpf; un PR por lente.
3. **DEBT-SNIFFER-FLOW-UID-TCP-LARGA-001**: medido DAY330 que las 13 conexiones Raft de control-2 son largas (iguales en
   60 s): el sniffer parte una conexión. Siguiente medida, barata: cuántos paquetes lleva cada flujo partido en el
   bronce (un número fijo apunta al tope de DEBT-SNIFFER-FLOW-PACKET-CAP-200; un tiempo fijo, a la caducidad de DAY307).
4. **PR2c** (Vault en clúster Raft; se borran `disco-sin-vault.json` y `VIGILANCIA_DISCO_JSON`): épico, partido si se
   puede. Dos o tres semanas (estimación de Alonso).
5. **Documentación** (decidida DAY326): ADR-060 sección 7 y el procedimiento de DEBT-VAULT-SELLADO-ALERTA-001, contra la
   documentación de Vault 2.2.1; ADR-048 (DAY324-329) y ADR-060.
6. Por medir: suelo del manifiesto (b) (DEBT-PROTEGIDOS-SUELO-REVAULT-001); después, borrar en el defender
   `/var/lib/ml-defender/firewall-linaje-anterior/`.
7. Otras: DEBT-CRYPTO-NONCE-REINICIO-001 (medir primero), DEBT-DDOS-COLATERAL-LEGITIMO-001 (después del PR2, antes de
   REA), DEBT-EMECAS-PROGRESO-REFERENCIA-001, DEBT-EMECAS-ESPERA-ANFITRION-001, DEBT-E2E-VAGRANT-SSH-RESTO-001,
   DEBT-LAB-PROVISION-SCRIPT-MUERTO-001, DEBT-ONNX-RUNTIME-ORIGEN-001 (seguimiento).
8. **Subir la fecha de Debian**: un commit que cambia `argus_debian_snapshot` y su EMECAS+++. No a una fecha con el
   `6.1.0-55` mientras el #1154153 siga abierto.
9. **2-dic-2026**: caduca la clave de OBS de Zeek; comprobar que OBS la ha prorrogado con la misma huella.

## Lecciones medidas DAY330
- Lo que se baja de fuera puede desaparecer de un día para otro (ONNX Runtime): todo tercero, con el hash de su
  mantenedor, y que el aprovisionamiento pare si la descarga falla. Un `wget -q` sin comprobar tapó el fallo 1h40m.
- Misma caja, misma fecha y mismo paquete no bastan: un valor de debconf que no fijamos decidió si grub se instalaba.
  Lo que no se fija, se juega a la lotería.
- OBS guarda una sola versión por paquete: allí se fija la serie, no la versión.
- Después de los `git commit`, `git log` para ver que entraron: en la rama de grub se quedó sin hacer el commit de la
  implementación.
- En zsh, una palabra que empieza por `=` se expande (`echo ===` falla): entrecomillar.
- Tras un `destroy` con el lab lleno, uno o dos minutos antes de lanzar EMECAS, y sin vídeos abiertos (swap).
- Hipótesis de Claude que los datos tumbaron hoy: cinco (ver BACKLOG, DAY330). Parar y medir funcionó cada vez.

## Datos útiles
- Nodos: control-1 `192.168.100.20`, control-2 `.21`, control-3 `.22`; 1024 MB, 2 vCPU. etcd 3.6.16 (cliente 2381,
  peers 2382, mTLS, RBAC por CN). Vault 2.2.1 (solo en control-1). Clave transit: huella `a1b73e22cf85899a`.
- VMs en VirtualBox: `ml-defender-gateway-lab`, `ml-defender-client`, `argus-suricata`, `argus-zeek`, `argus-wazuh`,
  `argus-control-1/2/3`; en Vagrant: `defender`, `client`, `suricata`, `zeek`, `wazuh`, `control-1/2/3`. VirtualBox
  7.2.10; Guest Additions de la caja 6.0.0. Caja `debian/bookworm64` 12.20240905.1 en todas.
- Kernels: caja `6.1.0-25-amd64` (6.1.106-3); el del lab, el de la fecha: `6.1.0-54-amd64` (6.1.190-1).
- Terceros: Falco 0.43.1, Wazuh 4.14.10-1, Zeek serie 9.0 (hoy 9.0.1-0) y ONNX Runtime 1.17.1 en
  `provisioning/<producto>/`; Vault `VAULT_PIN`, etcd v3.6.16 y Apache Arrow 24.0.0-1 en el `Vagrantfile`; sin fijar:
  el `.deb` del repositorio de Arrow; sin verificar: libsodium 1.0.19 y XGBoost 3.2.0.
- Llamadas del anfitrión a una VM: `perl scripts/emecas/con_limite.pl <s> vagrant ssh <vm> …`, con
  `argus_lab_llamada_vm_limite_s` (60) de `all.yml`.
- Lanzar EMECAS: `nohup bash scripts/emecas/emecas_run.sh emecas+++ production < /dev/null > /dev/null 2>&1 &`.
  Vigilar: `bash scripts/emecas/emecas_watch.sh 60`. Parar: `ps -axo pid,ppid,pgid,command | grep 'make emecas'`
  para el pgid del `make`, y `kill -TERM -<pgid>; sleep 5; kill -KILL -<pgid>`.
- PRs con `gh` (instalado y con sesión): `gh pr create --base main --head <rama>`, `gh pr diff <rama> --name-only`,
  `gh pr merge <rama> --merge`.
- Duraciones EMECAS+++ DAY330 (verdes): grub + ONNX 4h16m; Zeek 4h43m. DAY329: 4h35m (vagrant-up 29m, reload 6m,
  provision 42m, bootstrap 31m, test-all 16m, lab-e2e 1h48m, mitre-check 10m).
- Anfitrión (MacBook Pro, 16 hilos, 32 GB): sin lab carga ~2-3, swap 0; lab sano carga 5-8, swap hasta 7,2 GB;
  `anfitrion-recursos` (perfil emecas): carga 12, swap 4096 MB.

## Forma de trabajar (siguen en vigor)
- Predicción escrita antes de cada medida; si no sale, parar y mirar. Tests que también prueban que fallan cuando
  deben (y que la herramienta no se salte la prueba). Complejidad lineal como mucho. El JSON es la ley; lo importante,
  en un único lugar (JSON, Makefile, protobuf, Ansible, Jinja2).
- Parcheadores: sha256 de partida, cada ancla las veces exactas, nada escrito si algo falla; se copian a
  `scripts/etcd_ha/` y se ejecutan desde ahí, con su sha256 (los de documentación, desde `/tmp`). Lo que lleve
  tabuladores, por parcheador.
- Comandos exactos, en orden, diciendo dónde se ejecutan; salida a `/tmp/…` y `; cat`; no encadenar salidas grandes.
  `git grep`, nunca `grep -rn .` en la raíz. Un commit por cambio lógico, con el mensaje propuesto y `git status`
  antes del `git add`, y `git log` después. Nunca reescribir la historia. Software de terceros solo de sus
  mantenedores, con su hash o firma. Sin usos nuevos de curl. Mientras corre un EMECAS no se aplica nada al repo ni se
  toca el lab. Toda llamada a una VM, con límite.
- Claves privadas nunca en el repo ni por /vagrant.
- **PRs cortos** (decisión de Alonso DAY329): una deuda o un tema por PR, cada uno con su EMECAS; los gordos, solo si
  son de tipo épico. Dos PRs pueden compartir EMECAS si van apilados (DAY330: grub y ONNX). La documentación puede ir
  en español; el README, en inglés.
- **Entorno** (desde DAY329): Alonso trabaja en local con la Terminal de macOS (zsh); Claude, en su cliente de
  escritorio. En zsh, las variables siempre con llaves (`"${C}:refs/…"`), nada que empiece por `=` sin comillas, y lo
  que lleve bucles o aritmética, mejor dentro de `bash -c '…'`.
