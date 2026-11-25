#!/usr/bin/env python3
# d337_docs.py — [DOCS-D337] sección DAY337 del BACKLOG, cabeceras de DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001 y
# DEBT-DDOS-V2-PINNED-ENV-001, el #195 en la línea de B′ de DAY336, y el prompt de continuidad DAY338. Se ejecuta desde
# la raíz del repo, en la rama docs/d337 recién salida de main (e0b36abf2). Comprueba el sha256 de partida de cada
# fichero, cada ancla las veces exactas y no escribe nada si algo falla; al final, el sha256 de llegada.
import hashlib, sys

def sha(b): return hashlib.sha256(b).hexdigest()

SECCION = '''
## DAY337 — merge de A y B′; lente pip B: validate_roundtrip.py sin numpy y el entorno de entrenamiento ML a un venv opcional con hashes [PARQUET-SIN-NUMPY-D337] [ML-ENTRENO-D337]

### Hecho DAY337
- **Merge de DAY336**: A entró por el **#192** (`fb2d636ee`). El **#193** (B′) se mergeó con su base de partida,
  `terceros/d336-python-apt` (`67447f2ba`), y no llegó a main; B′ entró por el **#195** (`f1a902246`), el mismo
  `b9e19ed17`, sin EMECAS nuevo: `git diff --stat b9e19ed17 main` solo dio los dos ficheros de docs del **#194**
  (`159d6987c`). DEBT-APT-OFICIAL-UPDATE-SIN-REINTENTO-001 queda cerrada en main por el #195.
- **#196, `terceros/d337-parquet-sin-numpy`** (`797f5547d`, merge `b2b0ab384`): la comprobación de `timestamp_utc_ns`
  en todas las filas pasa a `scripts/parquet/filas_ts.py` (`fallos_ts`: nulos, `< TS_MIN_NS`, del futuro, no múltiplo
  de 1 ms), solo con `pyarrow.compute`, lineal; `validate_roundtrip.py` la usa y ya no importa numpy. Mismos mensajes
  que la función de antes: 0 diferencias en 20000 columnas aleatorias (nulos, varios trozos, negativos, extremos de
  int64, valores en el límite); el validador entero, igual con un Parquet bueno (`ROUNDTRIP PASSED`) y con uno malo (los
  mismos 3 `FAIL`). `scripts/parquet/test_filas_ts.py`, en el defender con numpy bloqueado
  (`sys.modules['numpy'] = None`): 15 casos, 9 rechazos contra una función que lo acepta todo; contra el validador de
  antes, 2 fallos. En `make test-parquet`, antes del roundtrip.
- **#198, `terceros/d337-ml-entreno`** (`59a8d32bd`, merge `e0b36abf2`): el entorno de entrenamiento ML sale de la
  provisión base. `provisioning/ml-entreno/requirements.txt`: el cierre entero, 10 paquetes, cada uno con el sha256 de
  su wheel cp311 (los 8 de `requirements-ddos-pinned.txt`, más narwhals 2.29.0 y six 1.17.0).
  `scripts/terceros/ml_entreno_instalar.sh`: como root, venv `/opt/argus/ml-entreno`, `--require-hashes --no-deps
  --only-binary=:all:`, `pip check` y `pip freeze` exactamente igual al lock; si ya lo es, no baja nada. `make
  ml-entreno`, opcional y fuera del EMECAS. Fuera del `Vagrantfile` el `pip3 install -r requirements-ddos-pinned.txt` y
  fuera el fichero. `test-ml-entreno` en el Mac (35 casos, 23 rechazos contra funciones que lo aceptan todo; contra el
  `Vagrantfile` de antes, 1 fallo), en el EMECAS tras `test-apt-oficial-reintento`. El **#197** se mergeó con su base de
  partida, `terceros/d337-parquet-sin-numpy` (`c52f487a1`), y no llegó a main: tercera vez (DAY335, #193, #197); el
  #198 lleva el mismo `59a8d32bd`, y `git diff --stat 59a8d32bd main` sale vacío.
- **EMECAS+++ production desde cero de #196 y #198 apilados**: **VERDE en 5h08m**
  (`logs/lab/emecas/emecas_20261125_094402.log`). `✅ test-parquet-filas`, `ROUNDTRIP PASSED` y `✅ test-ml-entreno`.

### Medido DAY337
- **Quién usa el entorno ML**: de los 28 `.py` que nombra el Makefile, solo `validate_roundtrip.py` importa algo de él
  (numpy). 40 `.py` importan pandas, sklearn, scipy, joblib, dateutil, pytz o narwhals: ninguno lo llama el Makefile,
  el `Vagrantfile`, un `.sh` o un `.yml` (solo los nombra, para renombrarlos, `scripts/cleanup_scripts.sh`, que no llama
  nadie); los que se llaman entre sí son de análisis o entrenamiento. El sha `56f0c5ae` (`.hpp` v1) y `ddos-regen` se
  borraron DAY306: ya no hay nada que comprobar con él.
- **La v2 de DDoS**: cabecera de `ddos_v2_forest_inline.hpp`: `sklearn 1.9.0; random_state 42; K de entrenamiento 3;
  2026-10-10T04:20:04Z` (consolidado `f3d6b261…`, `logs/lab/day292/`, fuera del repo). Del resto de versiones no quedó
  registro.
- **pyarrow 26.0.1 sin numpy**: `requires_dist` vacío en PyPI; en un venv sin numpy, `import pyarrow` y
  `pyarrow.compute` funcionan y `to_numpy()` da `ImportError`; el validador de antes, `ModuleNotFoundError`.
- **Los 10 sha256 del lock**, iguales por tres caminos: `pip download` en el defender, `pip download` fuera del lab y
  la API JSON de PyPI.
- **El defender (lab de DAY336)**: Python 3.11.2; las 8 versiones fijadas y narwhals ya en la 2.29.0 (la última, sin
  fijar); six 1.16.0 de apt (`/usr/lib/python3/dist-packages`); numpy de pip (`/usr/local`); `python3-venv` instalado
  (está en el `apt-get` de Python del `Vagrantfile`). `make ml-entreno` en ese lab: los 10 instalados (8 desde la caché
  de pip de root, pytz y six bajados), `No broken requirements found`; la segunda y la tercera, sin descargas; sklearn
  1.9.0, pandas 3.0.5, scipy 1.17.1, pip 23.0.1.
- **El defender recién provisionado (tras el EMECAS)**: `import numpy` da `ModuleNotFoundError`; de numpy,
  scikit-learn, pandas, scipy, joblib, threadpoolctl, narwhals y pyarrow, `pip3 list` solo muestra pyarrow 26.0.1;
  `/opt/argus/ml-entreno` no existe.
- **Los 41 min de más del EMECAS frente a DAY336 son de red**: vagrant-up 44m20s (+17m25s) y vagrant-provision 56m23s
  (+13m20s). Suma de los `Fetched … in …` de apt por paso: los mismos 1318,4 MB en vagrant-up, en 1143 s frente a 251 s,
  y 2429,1 MB en vagrant-provision, en 1188 s frente a 420 s (+1660 s, unos 28 min). Todas las VMs, más lentas (control-2,
  317 s frente a 40 s en vagrant-up). 0 reintentos de `apt-get update` en las dos corridas. El resto, unos 10 min
  repartidos entre los pasos de las VMs.

### Decisiones de Alonso DAY337
- Lente pip B como **B2**: el entorno de entrenamiento ML fuera de la base, a un target opcional con venv y lock de
  hashes (como D, semgrep); en un venv, no en el Python del sistema.
- `validate_roundtrip.py` sin numpy: «eliminar superficie de contacto innecesaria; menos a verificar».
- DEBT-DDOS-V2-PINNED-ENV-001, cerrada con lo medido (solo la versión de sklearn).
- La frase del README sobre terceros (línea 87: «All third-party software…»), se corrige en un PR de README al cerrar
  la lente pip.
- Pilas de PRs: el segundo se abre cuando el primero ya está en main, contra main.

### Deudas
- **DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001**: avanza. Lente pip: **A** (#192) y **B** (#196 y #198) hechos.
  Quedan **C** pyarrow 26.0.1 y **D** semgrep.
- **DEBT-DDOS-V2-PINNED-ENV-001 — CERRADA DAY337 (#198)**.
- **DEBT-APT-OFICIAL-UPDATE-SIN-REINTENTO-001 — CERRADA DAY337 (#195)**.
- **DEBT-EMECAS-RESUMEN-APT-001 — ABIERTA (nueva DAY337, menor)**: que `resumen.md` muestre, al lado de cada paso, la
  suma de los `Fetched <MB> in <tiempo>` de apt (MB y segundos), para que una corrida lenta por la red se explique
  sola.
- **DEBT-LAB-TERCEROS-CACHE-CORRIDA-001**: se añade lo medido hoy (28 min de apt más lento en una corrida).

### Lecciones DAY337
- **Pilas de PRs**: tres veces se ha mergeado un PR con base distinta de main (DAY335, #193, #197); avisar de cambiar
  la base antes de pulsar no basta. El EMECAS se corre sobre la punta de la pila; el segundo PR se abre después del
  merge del primero, ya contra main.
- **Ningún número sin su medida**: Claude dio el sha256 de un script como calculado sin haberlo calculado. El script
  llegó entero; el número era inventado. Todo sha256 o cifra que se presente como medida sale de una herramienta
  ejecutada en la sesión, sobre los mismos bytes.
- Antes de quitar algo de la base, buscar quién lo usa por debajo (`to_numpy()`); mejor quitar la dependencia que
  verificarla.
- `sys.modules['x'] = None` en un test prueba que el código no usa `x` aunque siga instalado.
- Un EMECAS lento: sumar los `Fetched` de apt por VM antes de sospechar del PR.
- En zsh, nada de `<…>` en un comando: lo toma por redirección.
'''

PROMPT = '''# aRGus NDR — prompt de continuidad DAY338 (sigue de DAY337)

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
'''

BL_DESCARGA_VIEJO = "### DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001 — ABIERTA (nueva DAY330; hechos ONNX Runtime #168, libsodium DAY331, Vault #177 y Arrow #178 DAY333, etcd #180 y libbpf #181 DAY334; inventario y siete lentes DAY335, #183 y #190: el Vagrantfile, sin descargas sin verificar; lente pip partida en A-D DAY336, A hecho (jinja2 y cryptography de Debian), quedan B entorno ML, C pyarrow y D semgrep; ver DAY336)\n"
BL_DESCARGA_NUEVO = "### DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001 — ABIERTA (nueva DAY330; hechos ONNX Runtime #168, libsodium DAY331, Vault #177 y Arrow #178 DAY333, etcd #180 y libbpf #181 DAY334; inventario y siete lentes DAY335, #183 y #190: el Vagrantfile, sin descargas sin verificar; lente pip partida en A-D DAY336: A hecho (#192, jinja2 y cryptography de Debian), B hecho DAY337 (#196 validate_roundtrip.py sin numpy y #198 el entorno de entrenamiento ML a un venv opcional con hashes), quedan C pyarrow y D semgrep; ver DAY336 y DAY337)\n"
BL_V2_VIEJO = """### DEBT-DDOS-V2-PINNED-ENV-001 — ABIERTA
ml-training/requirements-ddos-pinned.txt lo instala el Vagrantfile (linea 417), pero su comentario documenta el
entorno de la manivela v1 (sha 56f0c5ae, DAY256). Medir con que entorno se entrena la v2
(export_ddos_v2_fact_rf.py) y reescribir el comentario o el pin.
"""
BL_V2_NUEVO = """### DEBT-DDOS-V2-PINNED-ENV-001 — CERRADA DAY337 (#198)
ml-training/requirements-ddos-pinned.txt lo instala el Vagrantfile (linea 417), pero su comentario documenta el
entorno de la manivela v1 (sha 56f0c5ae, DAY256). Medir con que entorno se entrena la v2
(export_ddos_v2_fact_rf.py) y reescribir el comentario o el pin.
Cerrada DAY337: la v2 se entrenó con sklearn 1.9.0 (cabecera de ddos_v2_forest_inline.hpp); del resto de versiones no
quedó registro. El fichero y su comentario salen del repo; el entorno, con su cierre entero y sus hashes, está en
provisioning/ml-entreno/requirements.txt (make ml-entreno). Ver DAY337.
"""
BL_APT_VIEJO = "- **DEBT-APT-OFICIAL-UPDATE-SIN-REINTENTO-001 — nueva y hecha DAY336** (B′, pendiente de merge).\n"
BL_APT_NUEVO = "- **DEBT-APT-OFICIAL-UPDATE-SIN-REINTENTO-001 — nueva y hecha DAY336** (B′; en main por el #195, DAY337: el #193\n  se mergeó en la rama de A).\n"
BL_FIN = "  `~/Library`, llavero, repo) y fuera. Al mover a la Papelera varias rutas que acaban igual, un destino por ruta.\n"

errores = []
f = "docs/BACKLOG.md"
b = open(f, "rb").read()
if sha(b) != "c7dfd1e17b183feb3bfa0264a4eb4931bb69960d217a17dc3402d85f47cdc962":
    errores.append(f"{f}: sha256 de partida {sha(b)}")
t = b.decode("utf-8")
for viejo, nuevo in ((BL_DESCARGA_VIEJO, BL_DESCARGA_NUEVO), (BL_V2_VIEJO, BL_V2_NUEVO), (BL_APT_VIEJO, BL_APT_NUEVO)):
    n = t.count(viejo)
    if n != 1:
        errores.append(f"{f}: ancla encontrada {n} veces, se esperaba 1: {viejo.splitlines()[0][:80]!r}")
    else:
        t = t.replace(viejo, nuevo)
if not t.endswith(BL_FIN) or t.count(BL_FIN) != 1:
    errores.append(f"{f}: no acaba en la última línea de las lecciones de DAY336")
t += SECCION
bl = t.encode("utf-8")

g = "docs/continuity/PROMPT_CONTINUE_CLAUDE.md"
c = open(g, "rb").read()
if sha(c) != "e936166ece41b87a2ee1c095222c9c2d1ea228699cf53f34a234c9802ce391a6":
    errores.append(f"{g}: sha256 de partida {sha(c)}")
pc = PROMPT.encode("utf-8")

if errores:
    print("❌ no se escribe nada:")
    for e in errores: print("   " + e)
    sys.exit(1)
open(f, "wb").write(bl)
open(g, "wb").write(pc)
print(f"✅ {f}  sha256 de llegada {sha(bl)}")
print(f"✅ {g}  sha256 de llegada {sha(pc)}")
