# aRGus NDR — prompt de continuidad DAY338 (sigue de DAY337)

Responde siempre en español. Alonso es el único desarrollador de aRGus NDR (C++20, NDR para infraestructura crítica,
arXiv:2604.04952). Principio: «medir, no votar». El repo es SOLO LECTURA para Claude: Alonso hace commits, push y PR.
Claude no ejecuta en el repo ningún `git` que escriba, ni siquiera `fetch` (DAY333 dejó un `.lock`), ni nada en el Mac.
Raíz del repo en el Mac: `~/CLionProjects/test-zeromq-docker` (remoto `github.com/alonsoir/argus`, público: Claude
puede clonarlo en su entorno para leer y probar, nunca en el Mac).

**Ningún número inventado, jamás** (DAY337): todo sha256, conteo, duración o cifra que se presente como medida sale de
una herramienta ejecutada en la sesión sobre los mismos bytes que se entregan. Si no se ha calculado, se dice («sin
sha256: no lo he calculado»). Un script escrito directamente en el mensaje se guarda y se mide antes de dar su sha256.

## Dónde estamos
- **DAY337** (detalle en `docs/BACKLOG.md`, sección DAY337): main en `e0b36abf2`. Entraron:
  - **#192** (A de DAY336): jinja2 y cryptography de Debian, sin pip.
  - **#195** (B′ de DAY336): `apt-get update` de los repositorios oficiales con `--error-on=any` y reintentos; cierra
    DEBT-APT-OFICIAL-UPDATE-SIN-REINTENTO-001. El #193 se mergeó en la rama de A, no en main.
  - **#196**: `validate_roundtrip.py` sin numpy (`scripts/parquet/filas_ts.py`, `test_filas_ts.py` con numpy
    bloqueado, en `make test-parquet`).
  - **#198**: el entorno de entrenamiento ML sale de la base a un venv opcional (`make ml-entreno`,
    `/opt/argus/ml-entreno`, `provisioning/ml-entreno/requirements.txt` con el cierre entero de 10 paquetes y sus
    hashes); `test-ml-entreno` en el EMECAS. Cierra DEBT-DDOS-V2-PINNED-ENV-001. El #197 se mergeó en la rama del #196.
  - **#194**: docs de DAY336. Y el PR de docs de DAY337.
- EMECAS+++ desde cero de #196 y #198 apilados: **VERDE en 5h08m** (`emecas_20261125_094402.log`); los 41 min de más
  frente a DAY336 son de red (apt bajó los mismos 3747 MB en 2331 s, frente a 671 s).
- Defender recién provisionado (DAY337): `import numpy` da `ModuleNotFoundError`; de los paquetes del entorno ML
  (y pyarrow), en `pip3 list` solo pyarrow 26.0.1, en `~vagrant/.local`. semgrep no se miró.
- Lab al cerrar DAY337: el del EMECAS verde, encendido (8 VMs).
- Parcheadores aplicados y aún en el Mac: `/tmp` (d336: `medir_pip_d336.sh`, `d336_python_apt.py`,
  `d336_apt_reintento.py`, `d336_docs.py`; d337: `d337_docs.py`) y `scripts/etcd_ha/` (sin trackear:
  `d337_parquet_sin_numpy.py`, `d337_ml_entreno.py`). A `archivo/parcheadores-d336` y `archivo/parcheadores-d337`.
- Pendiente de Alonso (DAY336): revocar sesiones y claves en OpenAI y en el proveedor de opencode; vaciar la Papelera.

## Lo siguiente, en este orden (decisiones de Alonso DAY331, DAY336 y DAY337)
1. **Archivo**: los parcheadores de DAY336 y DAY337 a sus ramas de archivo (solo push, sin PR) y fuera del disco.
   Borrar en GitHub las ramas ya mergeadas `terceros/d336-*` y `terceros/d337-*`.
2. **Resto de la lente pip** (DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001), un PR cada una, con su EMECAS: **C**
   pyarrow 26.0.1 (wheel cp311 manylinux_2_28, sha256 `39cb0f24…548c`, medido DAY336), instalada por la provisión como
   root con `--require-hashes --no-deps` (hoy `parquet-convert` hace `pip3 install --upgrade pyarrow` como `vagrant` en
   cada corrida: baja la última que haya); `parquet-convert` solo comprueba. Antes, medir su cierre (`Requires:` vacío
   en PyPI para la 26.0.1). **D** semgrep fuera de la base, a un target opcional con venv y lock de hashes, como
   `ml-entreno` (después, medir a qué resuelven urllib3 y protobuf).
3. **DEBT-LAB-TERCEROS-CACHE-CORRIDA-001**: caché de descargas opcional (apagada por defecto), autoridad el hash del
   repo, por producto empezando por Falco; partir de `dist/vendor/` (su `CHECKSUMS` hoy es circular). DAY337 midió lo
   que cuesta no tenerla: 28 min de apt más lento en una corrida.
4. Menores: DEBT-EMECAS-RESUMEN-APT-001 (nueva DAY337), DEBT-FIREWALL-ANTISPOOF-A8-INTERMITENTE-001 (partir el CHECK
   de la línea 158), DEBT-LAB-APT-DEBIAN-UPDATE-SIN-COMPROBAR-001, DEBT-LAB-PROVISION-SCRIPT-MUERTO-001,
   DEBT-TERCEROS-DESCARGA-COMUN-001, DEBT-LAB-CURL-NODOS-001, DEBT-LAB-HARDENED-VAULT-CLAVE-001,
   DEBT-MAKE-CHECK-LIBBPF-001, DEBT-SNIFFER-LIBBPF-ORDEN-LDCONFIG-001 (RUNPATH o `libbpf.a`; medir con
   `/proc/<pid>/maps`).
5. **DEBT-SNIFFER-FLOW-UID-TCP-LARGA-001**: medir cuántos paquetes lleva cada flujo partido en el bronce (un número fijo
   apunta al tope de DEBT-SNIFFER-FLOW-PACKET-CAP-200; un tiempo fijo, a la caducidad de DAY307).
6. **PR2c** (Vault en clúster Raft; se borran `disco-sin-vault.json` y `VIGILANCIA_DISCO_JSON`): épico, partido si se
   puede. Dos o tres semanas (estimación de Alonso).
7. **Documentación** (decidida DAY326): ADR-060 sección 7 y el procedimiento de DEBT-VAULT-SELLADO-ALERTA-001, contra la
   documentación de Vault 2.2.1; ADR-048 (DAY324-329) y ADR-060; y DEBT-DOCS-XGBOOST-001 (ADR-026 Track 1,
   `docs/XGBOOST-VALIDATION.md`, `docs/xgboost/`, README). La frase del README (línea 87) «All third-party software
   (Wazuh, Falco, Jenkins) is installed from its maintainer's signed apt repository…» se queda corta y dice «All» antes
   de tiempo: se corrige en un PR de README cuando se cierre la lente pip (C y D).
8. Por medir: suelo del manifiesto (b) (DEBT-PROTEGIDOS-SUELO-REVAULT-001); después, borrar en el defender
   `/var/lib/ml-defender/firewall-linaje-anterior/`.
9. Otras: DEBT-REPO-PARCHEADORES-EN-MAIN-001 (con `tools/fix_vagrantfile_day160.py` y `fix_firewall_odr.py`),
   DEBT-LIBSODIUM-SO-VERSION-CONFLICT-001 (medir antes `/proc/<pid>/maps`), DEBT-CRYPTO-NONCE-REINICIO-001 (medir
   primero), DEBT-DDOS-COLATERAL-LEGITIMO-001 (después del PR2, antes de REA), DEBT-EMECAS-PROGRESO-REFERENCIA-001,
   DEBT-EMECAS-ESPERA-ANFITRION-001, DEBT-E2E-VAGRANT-SSH-RESTO-001, DEBT-ONNX-RUNTIME-ORIGEN-001 (seguimiento),
   subir de versión etcd-cpp-apiv3 (v0.15.4) y Temurin 21 (DEBT-LAB-VERSIONES-TERCEROS-001, cada una con su EMECAS).
   Repensar y reentrenar las cabezas internal, ransomware y traffic con el método de DDoS v2 (orden sin decidir; Atomic
   Red Team entra, con su commit fijado, con RESEARCH-MITRE-ATTACK-RANSOMWARE-001); el entorno, `make ml-entreno`.
   `fix/lab-terceros-vault` tiene dos commits locales sin subir (`bee01c358`, `2ea109691`, lente Arrow de DAY333):
   comprobar con `git diff --stat fix/lab-terceros-vault main -- scripts/terceros/arrow_instalar.sh provisioning/arrow`
   que ya están en main y borrar la rama local.
10. **Subir la fecha de Debian**: un commit que cambia `argus_debian_snapshot` y su EMECAS+++. No a una fecha con el
    `6.1.0-55` mientras el #1154153 siga abierto.
11. **2-dic-2026**: caduca la clave de OBS de Zeek; comprobar que OBS la ha prorrogado con la misma huella.

## Lecciones medidas (DAY334-337)
- **Pilas de PRs** (DAY335 #184-#189, DAY336 #193, DAY337 #197: tres veces): mergear un PR cuya base no es main no lo
  lleva a main, y avisar de cambiar la base antes de pulsar no ha bastado. Método desde DAY337: el EMECAS se corre
  sobre la punta de la pila; se abre y mergea el primer PR contra main; el siguiente se abre **después**, ya contra
  main. Al final, `git diff --stat <commit del EMECAS> main` vacío.
- Ningún número sin su medida (ver arriba). Un sha256 que no coincide es motivo para no ejecutar, aunque luego resulte
  que el error estaba en el número.
- Antes de quitar algo de la base, buscar quién lo usa también por debajo: `to_numpy()` de pyarrow necesita numpy
  aunque pyarrow no lo declare. Mejor quitar la dependencia que verificarla.
- `sys.modules['x'] = None` en un test prueba que el código no usa `x` aunque `x` siga instalado.
- Un EMECAS lento: sumar los `Fetched <MB> in <tiempo>` de apt por VM y paso antes de sospechar del PR (DAY337: los
  mismos MB, 3,5 veces más lento).
- En zsh, nada de `<…>` en un comando (lo toma por redirección): escribir el valor; `gh pr view|diff|edit` aceptan el
  nombre de la rama.
- Al aplicar dos piezas seguidas, commitear cada una antes de empezar la siguiente.
- `git grep -e wget -e curl` no ve los `git clone` ni los `pip install`: también son descargas.
- Antes de fijar algo, preguntar quién lo usa (Atomic Red Team, CMake y Crypto++, semgrep: solo `make audit`; el
  entorno ML: nadie del pipeline ni del EMECAS).
- Un `pip install` sin `--upgrade` da por bueno lo de apt: ver a qué fichero resuelve el `import` antes de fijar.
- `--require-hashes` pide el cierre entero: medir el árbol (`pip3 show`, `Requires:`), no solo las versiones (DAY337:
  `six`, que llegaba por apt).
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
  `logs/lab/emecas/<fecha>T<hora>_emecas+++/resumen.md` (`sed -n '/^## Falló/,$p'`), con un log por paso.
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
  `e31ac4d4…`), Kuzu 0.11.3 (SHA256 `e99f9671…`), Temurin `21.0.7.0.0+6-0` (clave `3B04D753…F8F04B`) y el entorno de
  entrenamiento ML (`provisioning/ml-entreno/requirements.txt`, 10 wheels cp311 con sha256). Los de git, con
  `scripts/terceros/lib_git_fijado.sh`; los de apt, con `scripts/vigilancia/lib_apt_oficial.sh` (`repo_oficial`,
  `actualizar_indices`, `instalar_fijado`; usa `curl` para la clave). Esperas de apt en `provisioning/apt-oficial/`.
- Python del defender (Python 3.11.2, `python3-venv` en el `apt-get` de Python del `Vagrantfile`): jinja2,
  cryptography y six de apt; de pip, el inventario de DAY336 menos el entorno ML: pyarrow 26.0.1 en `~vagrant/.local`
  (`parquet-convert`) y semgrep 1.186.0 con 57 dependencias (urllib3 2.8.0 y protobuf 6.33.6 tapan a los de apt).
  numpy, pandas y scikit-learn, solo en el venv opcional `/opt/argus/ml-entreno` (`make ml-entreno`; pip 23.0.1 de
  Debian; uso: `/opt/argus/ml-entreno/bin/python3 <script>`). La v2 de DDoS se entrenó con sklearn 1.9.0
  (`ddos_v2_fact_rf@day293-f3d6b261`); su consolidado está en `logs/lab/day292/`, fuera del repo (en el Mac).
  `download.falco.org` falla de vez en cuando (503/504).
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
  `gh pr view <rama> --json number,baseRefName,state`, `gh pr diff <rama> --name-only`; el merge lo hace Alonso en la
  web, con «Create a merge commit». CodeRabbit comenta en cada PR pero no revisa (menos de 10 estrellas).
- Duraciones EMECAS+++ (verdes): DAY337 #196+#198 5h08m (red lenta: vagrant-up 44m20s, provision 56m23s); DAY336 A+B′
  4h27m; DAY335 siete lentes 4h30m; DAY334 etcd 4h52m, libbpf 4h33m; DAY333 Vault 4h25m, Arrow 4h37m; DAY332 4h29m;
  DAY331 4h27m. DAY336 por pasos: vagrant-up 27m, reload 6m, provision 43m, bootstrap 29m, test-all 14m, lab-e2e 1h48m,
  mitre-check 10m.
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
  son de tipo épico. Dos PRs pueden compartir EMECAS si van apilados (y se abren uno tras otro, ver lecciones). Los de
  documentación o que no tocan ni el lab ni el pipeline, sin EMECAS. La documentación puede ir en español; el README,
  en inglés.
- **Entorno** (desde DAY329): Alonso trabaja en local con la Terminal de macOS (zsh); Claude, en su cliente de
  escritorio. En zsh, las variables siempre con llaves (`"${C}:refs/…"`), nada que empiece por `=` sin comillas, y lo
  que lleve bucles o aritmética, mejor dentro de `bash -c '…'`.
