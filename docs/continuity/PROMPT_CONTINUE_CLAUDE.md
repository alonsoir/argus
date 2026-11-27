# aRGus NDR — prompt de continuidad DAY340 (sigue de DAY339)

Responde siempre en español. Alonso es el único desarrollador de aRGus NDR (C++20, NDR para infraestructura crítica,
arXiv:2604.04952). Principio: «medir, no votar». El repo es SOLO LECTURA para Claude: Alonso hace commits, push y PR.
Claude no ejecuta en el repo ningún `git` que escriba, ni siquiera `fetch` (DAY333 dejó un `.lock`), ni nada en el Mac.
Raíz del repo en el Mac: `~/CLionProjects/test-zeromq-docker` (remoto `github.com/alonsoir/argus`, público: Claude
puede clonarlo en su entorno para leer y probar, nunca en el Mac).

**Ningún número inventado, jamás** (DAY337): todo sha256, conteo, duración o cifra que se presente como medida sale de
una herramienta ejecutada en la sesión sobre los mismos bytes que se entregan. Si no se ha calculado, se dice («sin
sha256: no lo he calculado»). Un script escrito directamente en el mensaje se guarda y se mide antes de dar su sha256.
**También las cuentas** (DAY339: una resta hecha de cabeza salió 2 millones mal): se ejecutan, no se calculan a ojo.

## Dónde estamos
- **DAY339** (detalle en `docs/BACKLOG.md`, sección DAY339): main en `30d6603c`. Entraron:
  - **#202** (DEBT-SNIFFER-IS-EXTERNAL-IP-BYTE-ORDER-001, CERRADA): medido en el bronce que `evt.dst_ip` llega a
    `is_external_ip` en el orden que espera (el del eBPF, `sniffer.bpf.c:315`); sin cambio de lógica, comentario
    corregido y `sniffer/tests/test_is_external_ip.cpp` (oráculo externo y control de que discrimina el orden).
  - **#203** (DEBT-SNIFFER-IS-EXTERNAL-IP-MULTICAST-001, nueva y CERRADA): `224.0.0.0/4` y `255.255.255.255` ya no
    cuentan como IP externa (opción (a) de Alonso: solo lo medido; 111 259 filas `argus` a `224.0.x.x` lo eran).
  - El PR de docs de DAY339.
- EMECAS+++ desde cero de la pila #202+#203: **VERDE en 4h16m** (`emecas_20261127_090132.log`); `git diff --stat` entre
  su punta y main, vacío.
- Deudas nuevas abiertas DAY339 (aviso de datos): DEBT-BRONCE-ANTERIOR-D229-IPS-INVERTIDAS-001 (el bronce modificado
  antes del 24-jul tiene parte de las IPs invertidas en el texto) y DEBT-BRONCE-SINTETICO-EN-LAB-001 (una fila
  `synthetic-97` en `logs/correlation/argus-2026-09-04-062100.csv.tmp`; no se sabe qué la escribió).
- Ramas: `fix/d339-*` borradas. Archivo: `archivo/parcheadores-d339` (parcheadores, scripts de medida y el de docs).
- Lab al cerrar DAY339: el del EMECAS verde.
- Pendiente de Alonso (DAY336): revocar sesiones y claves en OpenAI y en el proveedor de opencode; vaciar la Papelera.

## Lo siguiente, en este orden (decisiones de Alonso DAY331, DAY336, DAY337, DAY338 y DAY339)
1. **Lente pip D** (lo último de DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001): semgrep 1.186.0 fuera de la base, a un
   target opcional con venv y lock de hashes, como `ml-entreno` (solo lo usa `make audit`). Antes, medir su cierre
   entero (57 dependencias en DAY336) y, después, a qué resuelven urllib3 y protobuf en el Python del sistema. Con D, el
   PR de README de la línea 87 («All third-party software…»).
2. **DEBT-LAB-TERCEROS-CACHE-CORRIDA-001**: caché de descargas opcional (apagada por defecto), autoridad el hash del
   repo, por producto empezando por Falco; partir de `dist/vendor/` (su `CHECKSUMS` hoy es circular). DAY337 midió lo
   que cuesta no tenerla: 28 min de apt más lento en una corrida.
3. Menores: DEBT-EMECAS-RESUMEN-APT-001, DEBT-FIREWALL-ANTISPOOF-A8-INTERMITENTE-001 (partir el CHECK de la línea 158),
   DEBT-LAB-APT-DEBIAN-UPDATE-SIN-COMPROBAR-001, DEBT-LAB-PROVISION-SCRIPT-MUERTO-001, DEBT-TERCEROS-DESCARGA-COMUN-001,
   DEBT-LAB-CURL-NODOS-001, DEBT-LAB-HARDENED-VAULT-CLAVE-001, DEBT-MAKE-CHECK-LIBBPF-001,
   DEBT-SNIFFER-LIBBPF-ORDEN-LDCONFIG-001 (RUNPATH o `libbpf.a`; medir con `/proc/<pid>/maps`),
   DEBT-BRONCE-SINTETICO-EN-LAB-001 (medir qué generador escribe `synthetic-*` en el bronce real).
4. **DEBT-SNIFFER-FLOW-UID-TCP-LARGA-001**: medir cuántos paquetes lleva cada flujo partido en el bronce (un número fijo
   apunta al tope de DEBT-SNIFFER-FLOW-PACKET-CAP-200; un tiempo fijo, a la caducidad de DAY307).
5. **PR2c** (Vault en clúster Raft; se borran `disco-sin-vault.json` y `VIGILANCIA_DISCO_JSON`): épico, partido si se
   puede. Dos o tres semanas (estimación de Alonso).
6. **Cabezas** (decisión de Alonso DAY337): la siguiente es **ransomware**. Su ruta llena la ventana que lee DDoS
   (`ring_consumer.cpp`: `set_aggregator(ransomware_processor_->get_aggregator())`, el único `add_event`), así que se
   mide que DDoS v2 y ransomware funcionan bien a la par. Justo antes de empezarla, un **inventario por cabeza** (DDoS
   v2, ransomware, internal, traffic): qué features consume, de dónde sale cada una (ventana del aggregator,
   estadísticas del flujo u otro sitio) y con qué ventana; después, antes la que comparta ruta y features con las ya
   hechas. La v1 de ransomware no vale (DEBT-RANSOMWARE-ML-HEAD-INERT-001); datos reales en red (DAY195, DAY316): el lab
   no tiene VMs Windows y Atomic Red Team entra con su commit fijado (RESEARCH-MITRE-ATTACK-RANSOMWARE-001). El
   entorno, `make ml-entreno`. `new_external_ips_30s` ya sale con `is_external_ip` medido y sin multicast (DAY339). El
   bronce anterior al 24-jul tiene IPs invertidas en el texto (DEBT-BRONCE-ANTERIOR-D229-IPS-INVERTIDAS-001): no usarlo
   para entrenar sin tratarlo. Después de la v2 de ransomware, investigación: CPU por etapa (captura, extracción, cada
   cabeza) a varias tasas, para decidir entre un ml-detector con todas las cabezas o varios (repartir por flujo, no por
   cabeza; las ventanas compartidas, en un único sniffer).
7. **Documentación** (decidida DAY326): ADR-060 sección 7 y el procedimiento de DEBT-VAULT-SELLADO-ALERTA-001, contra la
   documentación de Vault 2.2.1; ADR-048 (DAY324-329) y ADR-060; y DEBT-DOCS-XGBOOST-001 (ADR-026 Track 1,
   `docs/XGBOOST-VALIDATION.md`, `docs/xgboost/`, README).
8. Por medir: suelo del manifiesto (b) (DEBT-PROTEGIDOS-SUELO-REVAULT-001); después, borrar en el defender
   `/var/lib/ml-defender/firewall-linaje-anterior/`.
9. Otras: DEBT-REPO-PARCHEADORES-EN-MAIN-001 (con `tools/fix_vagrantfile_day160.py` y `fix_firewall_odr.py`),
   DEBT-LIBSODIUM-SO-VERSION-CONFLICT-001 (medir antes `/proc/<pid>/maps`), DEBT-CRYPTO-NONCE-REINICIO-001 (medir
   primero), DEBT-DDOS-COLATERAL-LEGITIMO-001 (después del PR2, antes de REA; para dar por buena la v2),
   DEBT-EMECAS-PROGRESO-REFERENCIA-001, DEBT-EMECAS-ESPERA-ANFITRION-001, DEBT-E2E-VAGRANT-SSH-RESTO-001,
   DEBT-ONNX-RUNTIME-ORIGEN-001 (seguimiento), DEBT-BRONCE-ANTERIOR-D229-IPS-INVERTIDAS-001 (marcar, apartar o
   reescribir, nunca en silencio), subir de versión etcd-cpp-apiv3 (v0.15.4) y Temurin 21
   (DEBT-LAB-VERSIONES-TERCEROS-001, cada una con su EMECAS). Ramas locales del Mac con el remoto `gone` (24 en el
   `git branch -vv` de DAY338, de DAY202 a DAY337): revisar y borrar con `git branch -d`.
10. **Subir la fecha de Debian**: un commit que cambia `argus_debian_snapshot` y su EMECAS+++. No a una fecha con el
    `6.1.0-55` mientras el #1154153 siga abierto.
11. **2-dic-2026**: caduca la clave de OBS de Zeek; comprobar que OBS la ha prorrogado con la misma huella.

## Lecciones medidas (DAY334-339)
- **Las cuentas se ejecutan** (DAY339): una resta de cabeza dio 41 430 272 donde eran 39 430 272.
- **Un criterio de «sospechoso» ancho da cifras sin significado** (DAY339: toda IP acabada en `.10` o `.127` contaba
  como «privada al revés»). Antes de contar, calcular lo que daría el azar.
- **`sort | head` con `pipefail` sale con 141** (SIGPIPE): `sed -n '1,Np'`.
- **Mirar el valor tal cual antes de agrupar**: `int(x/86400)` mete en el «día 0» vacíos, negativos y segundos desde
  el arranque. La fecha de modificación de los ficheros fecha lo que la columna no puede.
- **Un parcheador que sustituye un fichero conserva su modo** (`os.replace` dejaba `100644` un `100755`):
  `git diff --summary` vacío antes del `git add`.
- **Antes del EMECAS, `make pipeline-build` y `make test-components` en el defender**: el CMake entero con los flags de
  production; un fallo ahí no cuesta una corrida de 4 h.
- **`gh pr create` siempre con `--title` y `--body-file`**, y con la rama ya en GitHub («Head ref must be a branch» es
  que falta el push); sin `--title` entra en modo interactivo y «Continue in browser» no crea nada.
- **En el Mac, un fichero descargado con el mismo nombre sustituye al anterior** en Descargas (sin `(1)`): el nombre,
  con `shasum`, no supuesto.
- **Un test se prueba también contra el código roto a propósito** (DAY339: con la IP invertida, 9 y 13 fallos; contra
  el código anterior, exactamente los casos nuevos).
- **`/tmp` del Mac no es archivo** (DAY338: se perdieron los parcheadores de DAY336 con un reinicio): todo
  parcheador, también los de documentación, a `scripts/etcd_ha/` y desde ahí, hasta su rama de archivo.
- Un parcheador con ficheros enteros dentro (líneas de miles de caracteres) se entrega como fichero, no con
  `cat <<'EOF'`; Alonso comprueba su sha256 en el Mac antes de ejecutarlo.
- Lo que no se ha medido se dice como predicción; el EMECAS la convierte en medida (DAY338: pip como root en
  `/usr/local`, comprobado en el log).
- Antes de borrar una rama con commits propios: `git merge-base --is-ancestor <commit> main`. Un `git diff` no vacío
  puede ser main por delante (`fix/lab-terceros-vault`, DAY338).
- **Pilas de PRs** (DAY335 #184-#189, DAY336 #193, DAY337 #197: tres veces): mergear un PR cuya base no es main no lo
  lleva a main, y avisar de cambiar la base antes de pulsar no ha bastado. Método desde DAY337 (DAY339 #202+#203: bien):
  el EMECAS se corre sobre la punta de la pila; se abre y mergea el primer PR contra main; el siguiente se abre
  **después**, ya contra main. Al final, `git diff --stat <commit del EMECAS> main` vacío.
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
- **Orden de bytes de las IPs del sniffer** (medido DAY339): el eBPF ensambla `src_ip`/`dst_ip` como número de host
  (`a<<24|b<<16|c<<8|d`, `sniffer.bpf.c:314-315`); a texto, solo con `ip_host_to_buffer` (`sniffer/include/ip_format.hpp`,
  `htonl` + `inet_ntop`). `is_external_ip` no excluye la clase E ni los demás rangos especiales de IANA (solo RFC 1918,
  loopback, link-local, multicast y broadcast limitado).
- **Bronce del lab**: `/vagrant/logs/correlation` (en el Mac, `logs/correlation`; 38 814 ficheros en DAY339), CSV de 19
  columnas: `source_sensor` 2, `flow_start_sec` 6, `src_ip` 8, `dst_ip` 9 (contadas desde 1). Leerlo entero con perl
  tarda unos 2-3 min en el Mac.
- Llamadas del anfitrión a una VM: `perl scripts/emecas/con_limite.pl <s> vagrant ssh <vm> …`, con
  `argus_lab_llamada_vm_limite_s` (60) de `all.yml`.
- Lanzar EMECAS: con el lab encendido, `vagrant destroy -f` y esperar a que la carga a 5 min baje de 6
  (`sysctl -n vm.loadavg`); después `nohup bash scripts/emecas/emecas_run.sh emecas+++ production < /dev/null > /dev/null
  2>&1 &`. Vigilar: `bash scripts/emecas/emecas_watch.sh 60`. Parar: `ps -axo pid,ppid,pgid,command | grep 'make
  emecas'` para el pgid del `make`, y `kill -TERM -<pgid>; sleep 5; kill -KILL -<pgid>`.
- PRs con `gh` (instalado y con sesión; 2.96.0): `gh pr create --base main --head <rama> --title "<t>" --body-file <f>`
  (rama ya subida), `gh pr view <rama> --json number,baseRefName,state`, `gh pr diff <rama> --name-only`; el merge lo
  hace Alonso en la web, con «Create a merge commit». CodeRabbit comenta en cada PR pero no revisa (menos de 10
  estrellas).
- Duraciones EMECAS+++ (verdes): DAY339 #202+#203 4h16m; DAY338 #200 4h09m; DAY337 #196+#198 5h08m (red lenta:
  vagrant-up 44m20s, provision 56m23s); DAY336 A+B′ 4h27m; DAY335 siete lentes 4h30m; DAY334 etcd 4h52m, libbpf 4h33m;
  DAY333 Vault 4h25m, Arrow 4h37m; DAY332 4h29m; DAY331 4h27m. DAY336 por pasos: vagrant-up 27m, reload 6m, provision
  43m, bootstrap 29m, test-all 14m, lab-e2e 1h48m, mitre-check 10m.
- Anfitrión (MacBook Pro, 16 hilos, 32 GB): sin lab carga ~2-3, swap 0; lab sano carga 5-8, swap hasta 7,2 GB;
  `anfitrion-recursos` (perfil emecas): carga 12, swap 4096 MB.

## Forma de trabajar (siguen en vigor)
- Predicción escrita antes de cada medida; si no sale, parar y mirar. Tests que también prueban que fallan cuando
  deben (y que la herramienta no se salte la prueba). Complejidad lineal como mucho. El JSON es la ley; lo importante,
  en un único lugar (JSON, Makefile, protobuf, Ansible, Jinja2, `provisioning/<producto>/`).
- Parcheadores: sha256 de partida, cada ancla las veces exactas, nada escrito si algo falla, sha256 de llegada,
  conservan el modo; se copian a `scripts/etcd_ha/` y se ejecutan desde ahí, con su sha256 (también los de
  documentación). Lo que lleve tabuladores, por parcheador. Claude los prueba antes en su copia del repo. Al acabar, a
  la rama de archivo del día, solo con push.
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
