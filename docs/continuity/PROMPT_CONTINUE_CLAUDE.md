# aRGus NDR — prompt de continuidad DAY339 (sigue de DAY338)

Responde siempre en español. Alonso es el único desarrollador de aRGus NDR (C++20, NDR para infraestructura crítica,
arXiv:2604.04952). Principio: «medir, no votar». El repo es SOLO LECTURA para Claude: Alonso hace commits, push y PR.
Claude no ejecuta en el repo ningún `git` que escriba, ni siquiera `fetch` (DAY333 dejó un `.lock`), ni nada en el Mac.
Raíz del repo en el Mac: `~/CLionProjects/test-zeromq-docker` (remoto `github.com/alonsoir/argus`, público: Claude
puede clonarlo en su entorno para leer y probar, nunca en el Mac).

**Ningún número inventado, jamás** (DAY337): todo sha256, conteo, duración o cifra que se presente como medida sale de
una herramienta ejecutada en la sesión sobre los mismos bytes que se entregan. Si no se ha calculado, se dice («sin
sha256: no lo he calculado»). Un script escrito directamente en el mensaje se guarda y se mide antes de dar su sha256.

## Dónde estamos
- **DAY338** (detalle en `docs/BACKLOG.md`, sección DAY338): main en `36e1b6d3a`. Entraron:
  - **#200** (lente pip C): pyarrow 26.0.1 con su hash (`provisioning/pyarrow/requirements.txt`), instalado por la
    provisión del defender como root en `/usr/local` (`scripts/terceros/pyarrow_instalar.sh`, `--require-hashes
    --no-deps --only-binary=:all:`); `make parquet-convert` ya no instala: `pyarrow_instalar.sh --comprobar`.
    `test-pyarrow-instalar` en el EMECAS. Cierre medido: solo pyarrow.
  - El PR de docs de DAY338.
- EMECAS+++ desde cero del #200: **VERDE en 4h09m** (`emecas_20261126_084111.log`); en el log, `[PYARROW] ✅ pyarrow
  26.0.1 /usr/local/lib/python3.11/dist-packages/pyarrow/__init__.py` en la provisión y en `parquet-convert`. Sin medir
  por qué es 59 min más corto que DAY337 (DEBT-EMECAS-RESUMEN-APT-001).
- Ramas: borradas en GitHub las mergeadas `terceros/d336-*`, `terceros/d337-*`, `terceros/d338-pyarrow`, `docs/d333` a
  `docs/d337` y `fix/lab-terceros-vault` (sus dos commits, `bee01c358` y `2ea109691`, ya estaban en main; la línea
  distinta de `arrow_instalar.sh` era el `actualizar_indices` del B′ de DAY336, que la rama no tenía). Archivo:
  `archivo/parcheadores-d337` y `-d338`. **Los parcheadores de DAY336 se perdieron** (estaban en `/tmp` del Mac y no
  sobrevivieron a un reinicio; no hay `archivo/parcheadores-d336`); su código está en main (#192, #195, #194).
- Lab al cerrar DAY338: el del EMECAS verde.
- Pendiente de Alonso (DAY336): revocar sesiones y claves en OpenAI y en el proveedor de opencode; vaciar la Papelera.

## Lo siguiente, en este orden (decisiones de Alonso DAY331, DAY336, DAY337 y DAY338)
1. **DEBT-SNIFFER-IS-EXTERNAL-IP-BYTE-ORDER-001** (nueva DAY338; «tiene que entrar pronto, no se puede perder»):
   medir con qué orden de bytes llega `evt.dst_ip` a `TimeWindowAggregator::is_external_ip`
   (`sniffer/src/userspace/time_window_aggregator.cpp:392`, compara con el primer octeto en los bits altos sin
   convertir nada), que usan `fast_detector.cpp:40` y `ransomware_feature_processor.cpp:97`. Primero la medida, con un
   evento real del sniffer; el arreglo, si hace falta, en su PR con su EMECAS.
2. **Lente pip D** (lo último de DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001): semgrep 1.186.0 fuera de la base, a un
   target opcional con venv y lock de hashes, como `ml-entreno` (solo lo usa `make audit`). Antes, medir su cierre
   entero (57 dependencias en DAY336) y, después, a qué resuelven urllib3 y protobuf en el Python del sistema. Con D, el
   PR de README de la línea 87 («All third-party software…»).
3. **DEBT-LAB-TERCEROS-CACHE-CORRIDA-001**: caché de descargas opcional (apagada por defecto), autoridad el hash del
   repo, por producto empezando por Falco; partir de `dist/vendor/` (su `CHECKSUMS` hoy es circular). DAY337 midió lo
   que cuesta no tenerla: 28 min de apt más lento en una corrida.
4. Menores: DEBT-EMECAS-RESUMEN-APT-001, DEBT-FIREWALL-ANTISPOOF-A8-INTERMITENTE-001 (partir el CHECK de la línea 158),
   DEBT-LAB-APT-DEBIAN-UPDATE-SIN-COMPROBAR-001, DEBT-LAB-PROVISION-SCRIPT-MUERTO-001, DEBT-TERCEROS-DESCARGA-COMUN-001,
   DEBT-LAB-CURL-NODOS-001, DEBT-LAB-HARDENED-VAULT-CLAVE-001, DEBT-MAKE-CHECK-LIBBPF-001,
   DEBT-SNIFFER-LIBBPF-ORDEN-LDCONFIG-001 (RUNPATH o `libbpf.a`; medir con `/proc/<pid>/maps`).
5. **DEBT-SNIFFER-FLOW-UID-TCP-LARGA-001**: medir cuántos paquetes lleva cada flujo partido en el bronce (un número fijo
   apunta al tope de DEBT-SNIFFER-FLOW-PACKET-CAP-200; un tiempo fijo, a la caducidad de DAY307).
6. **PR2c** (Vault en clúster Raft; se borran `disco-sin-vault.json` y `VIGILANCIA_DISCO_JSON`): épico, partido si se
   puede. Dos o tres semanas (estimación de Alonso).
7. **Cabezas** (decisión de Alonso DAY337): la siguiente es **ransomware**. Su ruta llena la ventana que lee DDoS
   (`ring_consumer.cpp`: `set_aggregator(ransomware_processor_->get_aggregator())`, el único `add_event`), así que se
   mide que DDoS v2 y ransomware funcionan bien a la par. Justo antes de empezarla, un **inventario por cabeza** (DDoS
   v2, ransomware, internal, traffic): qué features consume, de dónde sale cada una (ventana del aggregator,
   estadísticas del flujo u otro sitio) y con qué ventana; después, antes la que comparta ruta y features con las ya
   hechas. La v1 de ransomware no vale (DEBT-RANSOMWARE-ML-HEAD-INERT-001); datos reales en red (DAY195, DAY316): el lab
   no tiene VMs Windows y Atomic Red Team entra con su commit fijado (RESEARCH-MITRE-ATTACK-RANSOMWARE-001). El
   entorno, `make ml-entreno`. Después de la v2 de ransomware, investigación: CPU por etapa (captura, extracción, cada
   cabeza) a varias tasas, para decidir entre un ml-detector con todas las cabezas o varios (repartir por flujo, no por
   cabeza; las ventanas compartidas, en un único sniffer).
8. **Documentación** (decidida DAY326): ADR-060 sección 7 y el procedimiento de DEBT-VAULT-SELLADO-ALERTA-001, contra la
   documentación de Vault 2.2.1; ADR-048 (DAY324-329) y ADR-060; y DEBT-DOCS-XGBOOST-001 (ADR-026 Track 1,
   `docs/XGBOOST-VALIDATION.md`, `docs/xgboost/`, README).
9. Por medir: suelo del manifiesto (b) (DEBT-PROTEGIDOS-SUELO-REVAULT-001); después, borrar en el defender
   `/var/lib/ml-defender/firewall-linaje-anterior/`.
10. Otras: DEBT-REPO-PARCHEADORES-EN-MAIN-001 (con `tools/fix_vagrantfile_day160.py` y `fix_firewall_odr.py`),
    DEBT-LIBSODIUM-SO-VERSION-CONFLICT-001 (medir antes `/proc/<pid>/maps`), DEBT-CRYPTO-NONCE-REINICIO-001 (medir
    primero), DEBT-DDOS-COLATERAL-LEGITIMO-001 (después del PR2, antes de REA; para dar por buena la v2),
    DEBT-EMECAS-PROGRESO-REFERENCIA-001, DEBT-EMECAS-ESPERA-ANFITRION-001, DEBT-E2E-VAGRANT-SSH-RESTO-001,
    DEBT-ONNX-RUNTIME-ORIGEN-001 (seguimiento), subir de versión etcd-cpp-apiv3 (v0.15.4) y Temurin 21
    (DEBT-LAB-VERSIONES-TERCEROS-001, cada una con su EMECAS). Ramas locales del Mac con el remoto `gone` (24 en el
    `git branch -vv` de DAY338, de DAY202 a DAY337): revisar y borrar con `git branch -d`.
11. **Subir la fecha de Debian**: un commit que cambia `argus_debian_snapshot` y su EMECAS+++. No a una fecha con el
    `6.1.0-55` mientras el #1154153 siga abierto.
12. **2-dic-2026**: caduca la clave de OBS de Zeek; comprobar que OBS la ha prorrogado con la misma huella.

## Lecciones medidas (DAY334-338)
- **`/tmp` del Mac no es archivo** (DAY338: se perdieron los parcheadores de DAY336 con un reinicio): todo
  parcheador, también los de documentación, a `scripts/etcd_ha/` y desde ahí, hasta su rama de archivo.
- Un parcheador con ficheros enteros dentro (líneas de miles de caracteres) se entrega como fichero, no con
  `cat <<'EOF'`; Alonso comprueba su sha256 en el Mac antes de ejecutarlo.
- Lo que no se ha medido se dice como predicción; el EMECAS la convierte en medida (DAY338: pip como root en
  `/usr/local`, comprobado en el log).
- Antes de borrar una rama con commits propios: `git merge-base --is-ancestor <commit> main`. Un `git diff` no vacío
  puede ser main por delante (`fix/lab-terceros-vault`, DAY338).
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
  `e31ac4d4…`), Kuzu 0.11.3 (SHA256 `e99f9671…`), Temurin `21.0.7.0.0+6-0` (clave `3B04D753…F8F04B`), pyarrow 26.0.1
  (`provisioning/pyarrow/requirements.txt`, wheel cp311 con sha256) y el entorno de entrenamiento ML
  (`provisioning/ml-entreno/requirements.txt`, 10 wheels cp311 con sha256). Los de git, con
  `scripts/terceros/lib_git_fijado.sh`; los de apt, con `scripts/vigilancia/lib_apt_oficial.sh` (`repo_oficial`,
  `actualizar_indices`, `instalar_fijado`; usa `curl` para la clave). Esperas de apt en `provisioning/apt-oficial/`.
- Python del defender (Python 3.11.2, `python3-venv` en el `apt-get` de Python del `Vagrantfile`): jinja2,
  cryptography y six de apt; de pip, el inventario de DAY336 menos el entorno ML: pyarrow 26.0.1 en `/usr/local`, de la
  provisión con su hash (`pyarrow_instalar.sh`; `parquet-convert` solo comprueba) y semgrep 1.186.0 con 57
  dependencias (urllib3 2.8.0 y protobuf 6.33.6 tapan a los de apt).
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
- Duraciones EMECAS+++ (verdes): DAY338 #200 4h09m; DAY337 #196+#198 5h08m (red lenta: vagrant-up 44m20s, provision
  56m23s); DAY336 A+B′ 4h27m; DAY335 siete lentes 4h30m; DAY334 etcd 4h52m, libbpf 4h33m; DAY333 Vault 4h25m, Arrow
  4h37m; DAY332 4h29m; DAY331 4h27m. DAY336 por pasos: vagrant-up 27m, reload 6m, provision 43m, bootstrap 29m,
  test-all 14m, lab-e2e 1h48m, mitre-check 10m.
- Anfitrión (MacBook Pro, 16 hilos, 32 GB): sin lab carga ~2-3, swap 0; lab sano carga 5-8, swap hasta 7,2 GB;
  `anfitrion-recursos` (perfil emecas): carga 12, swap 4096 MB.

## Forma de trabajar (siguen en vigor)
- Predicción escrita antes de cada medida; si no sale, parar y mirar. Tests que también prueban que fallan cuando
  deben (y que la herramienta no se salte la prueba). Complejidad lineal como mucho. El JSON es la ley; lo importante,
  en un único lugar (JSON, Makefile, protobuf, Ansible, Jinja2, `provisioning/<producto>/`).
- Parcheadores: sha256 de partida, cada ancla las veces exactas, nada escrito si algo falla, sha256 de llegada; se
  copian a `scripts/etcd_ha/` y se ejecutan desde ahí, con su sha256 (también los de documentación, desde DAY338).
  Lo que lleve tabuladores, por parcheador. Claude los prueba antes en su copia del repo. Al acabar, a la rama de
  archivo del día, solo con push.
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
