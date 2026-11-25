# aRGus NDR — prompt de continuidad DAY337 (sigue de DAY336)

Responde siempre en español. Alonso es el único desarrollador de aRGus NDR (C++20, NDR para infraestructura crítica,
arXiv:2604.04952). Principio: «medir, no votar». El repo es SOLO LECTURA para Claude: Alonso hace commits, push y PR.
Claude no ejecuta en el repo ningún `git` que escriba, ni siquiera `fetch` (DAY333 dejó un `.lock`), ni nada en el Mac.
Raíz del repo en el Mac: `~/CLionProjects/test-zeromq-docker` (remoto `github.com/alonsoir/argus`, público: Claude
puede clonarlo en su entorno para leer y probar, nunca en el Mac).

## Dónde estamos
- **DAY336** (detalle en `docs/BACKLOG.md`, sección DAY336): EMECAS+++ desde cero **VERDE en 4h27m**
  (`emecas_20261124_190219.log`) con dos PRs apilados, **sin abrir todavía**:
  - **A** `terceros/d336-python-apt` (`d96372349`): jinja2 y cryptography de Debian, sin pip;
    `scripts/terceros/python_apt.sh`; `test-python-apt`.
  - **B′** `terceros/d336-apt-reintento` (sobre A): `actualizar_indices` y `ao_version_visible` en
    `scripts/vigilancia/lib_apt_oficial.sh`, `provisioning/apt-oficial/ESPERAS_S` (30 60); la usan los 7 instaladores de
    apt y dos bloques del `Vagrantfile`; `test-apt-oficial-reintento`. Cierra DEBT-APT-OFICIAL-UPDATE-SIN-REINTENTO-001.
  - Docs del día: `docs/d336`, desde main, sin EMECAS.
- Parcheadores d336 en `/tmp` del Mac (`medir_pip_d336.sh`, `d336_python_apt.py`, `d336_apt_reintento.py`,
  `d336_docs.py`): a `archivo/parcheadores-d336`, solo con push.
- Lab al cerrar DAY336: EMECAS verde terminado (8 VMs).
- Fuera del Mac DAY336: Orca, Codex y opencode. Pendiente de Alonso: revocar sesiones y claves en OpenAI y en el
  proveedor de opencode; vaciar la Papelera.

## Lo siguiente, en este orden (decisiones de Alonso DAY331 y DAY336)
1. **Merge a main**: abrir A con base main y B′ con base `terceros/d336-python-apt`; mergear A borrando su rama (GitHub
   pasa B′ a main) o cambiar la base de B′ a main antes de pulsar; después B′. Comprobar `git diff --stat <commit de B′>
   main` vacío. Luego el PR de docs.
2. **Resto de la lente pip** (DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001), un PR cada una, con su EMECAS (pueden ir
   apiladas): **B** entorno ML (`narwhals==2.29.0` y `--hash` en los 9, `--require-hashes --no-deps`, `pip3 check`;
   hashes de `pip3 download` en el defender contra PyPI; test también del sha `56f0c5ae` del `.hpp`); **C** pyarrow
   26.0.1 (wheel cp311 manylinux_2_28, sha256 `39cb0f24…548c`), instalada por la provisión como root y `parquet-convert`
   solo comprueba; **D** semgrep fuera de la base, a un target opcional con venv y lock de hashes (después, medir a qué
   resuelven urllib3 y protobuf).
3. **DEBT-LAB-TERCEROS-CACHE-CORRIDA-001**: caché de descargas opcional (apagada por defecto), autoridad el hash del
   repo, por producto empezando por Falco; partir de `dist/vendor/` (su `CHECKSUMS` hoy es circular).
4. Menores: DEBT-FIREWALL-ANTISPOOF-A8-INTERMITENTE-001 (partir el CHECK de la línea 158),
   DEBT-LAB-APT-DEBIAN-UPDATE-SIN-COMPROBAR-001, DEBT-LAB-PROVISION-SCRIPT-MUERTO-001, DEBT-TERCEROS-DESCARGA-COMUN-001,
   DEBT-LAB-CURL-NODOS-001, DEBT-LAB-HARDENED-VAULT-CLAVE-001, DEBT-MAKE-CHECK-LIBBPF-001,
   DEBT-SNIFFER-LIBBPF-ORDEN-LDCONFIG-001 (RUNPATH o `libbpf.a`; medir con `/proc/<pid>/maps`).
5. **DEBT-SNIFFER-FLOW-UID-TCP-LARGA-001**: medir cuántos paquetes lleva cada flujo partido en el bronce (un número fijo
   apunta al tope de DEBT-SNIFFER-FLOW-PACKET-CAP-200; un tiempo fijo, a la caducidad de DAY307).
6. **PR2c** (Vault en clúster Raft; se borran `disco-sin-vault.json` y `VIGILANCIA_DISCO_JSON`): épico, partido si se
   puede. Dos o tres semanas (estimación de Alonso).
7. **Documentación** (decidida DAY326): ADR-060 sección 7 y el procedimiento de DEBT-VAULT-SELLADO-ALERTA-001, contra la
   documentación de Vault 2.2.1; ADR-048 (DAY324-329) y ADR-060; y DEBT-DOCS-XGBOOST-001 (ADR-026 Track 1,
   `docs/XGBOOST-VALIDATION.md`, `docs/xgboost/`, README).
8. Por medir: suelo del manifiesto (b) (DEBT-PROTEGIDOS-SUELO-REVAULT-001); después, borrar en el defender
   `/var/lib/ml-defender/firewall-linaje-anterior/`.
9. Otras: DEBT-REPO-PARCHEADORES-EN-MAIN-001 (con `tools/fix_vagrantfile_day160.py` y `fix_firewall_odr.py`),
   DEBT-LIBSODIUM-SO-VERSION-CONFLICT-001 (medir antes `/proc/<pid>/maps`), DEBT-CRYPTO-NONCE-REINICIO-001 (medir
   primero), DEBT-DDOS-COLATERAL-LEGITIMO-001 (después del PR2, antes de REA), DEBT-EMECAS-PROGRESO-REFERENCIA-001,
   DEBT-EMECAS-ESPERA-ANFITRION-001, DEBT-E2E-VAGRANT-SSH-RESTO-001, DEBT-ONNX-RUNTIME-ORIGEN-001 (seguimiento),
   subir de versión etcd-cpp-apiv3 (v0.15.4) y Temurin 21 (DEBT-LAB-VERSIONES-TERCEROS-001, cada una con su EMECAS).
   Repensar y reentrenar las cabezas internal, ransomware y traffic con el método de DDoS v2 (orden sin decidir; Atomic
   Red Team entra, con su commit fijado, con RESEARCH-MITRE-ATTACK-RANSOMWARE-001).
10. **Subir la fecha de Debian**: un commit que cambia `argus_debian_snapshot` y su EMECAS+++. No a una fecha con el
    `6.1.0-55` mientras el #1154153 siga abierto.
11. **2-dic-2026**: caduca la clave de OBS de Zeek; comprobar que OBS la ha prorrogado con la misma huella.

## Lecciones medidas (DAY333-336)
- En una pila de PRs, mergear uno cuya base no es main no lo lleva a main (DAY335: #184-#189). O se borra la rama al
  mergear, o se cambia la base del siguiente a main antes de pulsar; al final, `git diff --stat <commit del EMECAS>
  main` vacío.
- Al aplicar dos piezas seguidas, commitear cada una antes de empezar la siguiente.
- `git grep -e wget -e curl` no ve los `git clone` ni los `pip install`: también son descargas.
- Antes de fijar algo, preguntar quién lo usa (Atomic Red Team, CMake y Crypto++, semgrep: solo `make audit`).
- Un `pip install` sin `--upgrade` da por bueno lo de apt: ver a qué fichero resuelve el `import` antes de fijar.
- `--require-hashes` pide el cierre entero: medir el árbol (`pip3 show`, `Requires:`), no solo las versiones.
- `vagrant ssh -c` corre como `vagrant`: un `pip install` sin root acaba en `~/.local`.
- `apt-get update` sale con 0 con un repositorio caído: `--error-on=any` (apt 2.6.2 la tiene).
- Un servidor intermitente no deja patrón: contar en los logs por VM y corrida antes de construir hipótesis.
- Un test que falla una vez: repetirlo y contar en los logs antiguos antes de culpar al PR (antispoof A8: 1 de 36).
- Tras destruir el lab, esperar a que la carga a 5 min baje de 6 antes de lanzar (el EMECAS mide en el paso 3).
- El sha256 de algo compilado no es una referencia (etcd-cpp-apiv3 no es reproducible): se contrasta el commit.
- Con dos alternativas de igual prioridad, `update-alternatives` mantiene la que estaba: rutas explícitas.
- Antes del EMECAS, `git status`.
- A las ramas de archivo no se les abre PR: GitHub deja mergearlas con un clic (#171).
- Dos instaladores de lo mismo esconden cuál manda. Lo importante, en un único lugar.
- `ldd` de una biblioteca suelta no dice qué carga un proceso; para eso, `/proc/<pid>/maps`. Si un resultado
  contradice algo que funciona desde hace meses, sospechar primero de la medida.
- `pgrep -f <nombre>` dentro de `vagrant ssh -c` se encuentra a sí mismo: `pgrep -x`.
- Una clave de repositorio sin comprobar se cambia sin que nadie lo vea: huella en `provisioning/<producto>/CLAVE`,
  contrastada con el mantenedor por otro canal. Si el mantenedor no firma, su hash o el commit del tag.
- Antes de afirmar qué hace un `.deb`, abrirlo (`dpkg-deb -e`/`-c`). Antes de predecir, leer el bloque.
- En awk, nada de intervalos `{n}`; los tests del Mac, también con `mawk`.
- Tras cambiar de rama, `git log --oneline -3` antes de commitear; si los commits caen en otra rama,
  `git merge --ff-only`, sin reescribir.
- El log del EMECAS está en `logs/lab/emecas/emecas_<fecha>.log` (y `emecas_actual.log`); el resumen, en
  `logs/lab/emecas/<fecha>_emecas+++/resumen.md` (`sed -n '/^## Falló/,$p'`).
- Los `.py`/`.sh` se entregan como bloque `cat > f <<'EOF'`, con su sha256 comprobado en el sitio.
- Un programa que da a un agente el teclado de tus terminales es un shell remoto: no en el Mac del lab.

## Datos útiles
- Nodos: control-1 `192.168.100.20`, control-2 `.21`, control-3 `.22`; 1024 MB, 2 vCPU. etcd 3.6.16 (cliente 2381,
  peers 2382, mTLS, RBAC por CN). Vault 2.2.1 (solo en control-1). Clave transit: huella `a1b73e22cf85899a`.
- VMs en VirtualBox: `ml-defender-gateway-lab`, `ml-defender-client`, `argus-suricata`, `argus-zeek`, `argus-wazuh`,
  `argus-control-1/2/3`; en Vagrant: `defender`, `client`, `suricata`, `zeek`, `wazuh`, `control-1/2/3`. VirtualBox
  7.2.10; Guest Additions de la caja 6.0.0. Caja `debian/bookworm64` 12.20240905.1 en todas. apt 2.6.2.
- Kernels: caja `6.1.0-25-amd64` (6.1.106-3); el del lab, el de la fecha: `6.1.0-54-amd64` (6.1.190-1).
- Terceros en `provisioning/<producto>/`: Falco 0.43.1, Wazuh 4.14.10-1, Zeek serie 9.0 (hoy 9.0.1-0), ONNX Runtime
  1.17.1 (NuGet, SHA512), libsodium 1.0.19 (minisign + SHA256), Vault 2.2.1-1 (clave apt `D55C0D1A…CA026560`),
  Arrow/Parquet 24.0.0-1 (las 25 claves de `downloads.apache.org/arrow/KEYS`), etcd 3.6.16 (SHA256 `c8c0d96d…`),
  libbpf 1.4.6 (commit `fdf402b3…`), cpp-httplib 0.67.0 (commit `7800c3dc…`), etcd-cpp-apiv3 0.15.3 (commit
  `e31ac4d4…`), Kuzu 0.11.3 (SHA256 `e99f9671…`) y Temurin `21.0.7.0.0+6-0` (clave `3B04D753…F8F04B`). Los de git, con
  `scripts/terceros/lib_git_fijado.sh`; los de apt, con `scripts/vigilancia/lib_apt_oficial.sh` (`repo_oficial`,
  `actualizar_indices`, `instalar_fijado`; usa `curl` para la clave). Esperas de apt en `provisioning/apt-oficial/`.
- Python del defender: jinja2 y cryptography de apt (`python_apt.sh`); de pip, el entorno ML (8 fijados + `narwhals`),
  pyarrow 26.0.1 en `~vagrant/.local` y semgrep 1.186.0 con 57 dependencias (urllib3 2.8.0 y protobuf 6.33.6 tapan a
  los de apt). `download.falco.org` falla de vez en cuando (503/504).
- Binarios visibles desde el Mac: `ml-detector/build-production/ml-detector`, `sniffer/build-production/sniffer`.
- libsodium: bookworm trae la 1.0.18 (`.so.23`); la nuestra, 1.0.19 (`.so.26`) en `/usr/local`, marca
  `/usr/local/lib/argus-libsodium.verificado`. libbpf: bookworm trae la 1.1.2; la nuestra, 1.4.6 en `/usr/lib64`, marca
  `/usr/local/lib/argus-libbpf.commit`.
- Llamadas del anfitrión a una VM: `perl scripts/emecas/con_limite.pl <s> vagrant ssh <vm> …`, con
  `argus_lab_llamada_vm_limite_s` (60) de `all.yml`.
- Lanzar EMECAS: con el lab encendido, `vagrant destroy -f` y esperar a que la carga a 5 min baje de 6
  (`sysctl -n vm.loadavg`); después `nohup bash scripts/emecas/emecas_run.sh emecas+++ production < /dev/null > /dev/null
  2>&1 &`. Vigilar: `bash scripts/emecas/emecas_watch.sh 60`. Parar: `ps -axo pid,ppid,pgid,command | grep 'make
  emecas'` para el pgid del `make`, y `kill -TERM -<pgid>; sleep 5; kill -KILL -<pgid>`.
- PRs con `gh` (instalado y con sesión): `gh pr create --base main --head <rama> --body-file <f>`,
  `gh pr diff <rama> --name-only`; el merge lo hace Alonso en la web, con «Create a merge commit».
- Duraciones EMECAS+++ (verdes): DAY336 A+B′ 4h27m; DAY335 siete lentes 4h30m; DAY334 etcd 4h52m, libbpf 4h33m;
  DAY333 Vault 4h25m, Arrow 4h37m; DAY332 4h29m; DAY331 4h27m. DAY329: 4h35m (vagrant-up 29m, reload 6m, provision 42m,
  bootstrap 31m, test-all 16m, lab-e2e 1h48m, mitre-check 10m).
- Anfitrión (MacBook Pro, 16 hilos, 32 GB): sin lab carga ~2-3, swap 0; lab sano carga 5-8, swap hasta 7,2 GB;
  `anfitrion-recursos` (perfil emecas): carga 12, swap 4096 MB.

## Forma de trabajar (siguen en vigor)
- Predicción escrita antes de cada medida; si no sale, parar y mirar. Tests que también prueban que fallan cuando
  deben (y que la herramienta no se salte la prueba). Complejidad lineal como mucho. El JSON es la ley; lo importante,
  en un único lugar (JSON, Makefile, protobuf, Ansible, Jinja2, `provisioning/<producto>/`).
- Parcheadores: sha256 de partida, cada ancla las veces exactas, nada escrito si algo falla, sha256 de llegada; se
  copian a `scripts/etcd_ha/` y se ejecutan desde ahí, con su sha256 (los de documentación, desde `/tmp`). Lo que
  lleve tabuladores, por parcheador. Claude los prueba antes en su copia del repo. Al acabar, a la rama de archivo
  del día, solo con push.
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
