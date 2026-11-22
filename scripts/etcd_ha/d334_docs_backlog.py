#!/usr/bin/env python3
# d334_docs_backlog.py — [DOCS-D334] parcheador de documentación DAY334: docs/BACKLOG.md, sección DAY334 al final y los
# títulos de DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001 y DEBT-LAB-VERSIONES-TERCEROS-001. Se copia a /tmp y se
# ejecuta desde la raíz del repo:
#   python3 /tmp/d334_docs_backlog.py
# Comprueba el sha256 de partida y que cada ancla esté una vez; si algo falla, no escribe nada. Comprueba el de llegada.
import hashlib, sys
F = "docs/BACKLOG.md"
PARTIDA = '62c21b8397f1afd72c9cfd5d263c4f73a06e6a3db39eaf7a936b290c44f430fc'
LLEGADA = '460689f813e53d0bb18107ce2830bf2a0f4fc32689a256f81d9f0c4ec84a9015'
T1_VIEJO = '### DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001 — ABIERTA (nueva DAY330; hechos ONNX Runtime #168, libsodium DAY331, Vault #177 y Arrow #178 DAY333; quedan etcd, solo orden, y libbpf; ver DAY333)\n'
T1_NUEVO = '### DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001 — ABIERTA (nueva DAY330; hechos ONNX Runtime #168, libsodium DAY331, Vault #177 y Arrow #178 DAY333, etcd #180 y libbpf #181 DAY334; queda el inventario con `git grep`; ver DAY334)\n'
T2_VIEJO = '### DEBT-LAB-VERSIONES-TERCEROS-001 — sigue ABIERTA (avance DAY330; Vault y Arrow a `provisioning/<producto>/` DAY333)\n'
T2_NUEVO = '### DEBT-LAB-VERSIONES-TERCEROS-001 — sigue ABIERTA (avance DAY330; Vault y Arrow a `provisioning/<producto>/` DAY333; etcd y libbpf DAY334)\n'
SECCION = """
## DAY334 — etcd y libbpf desde su mantenedor, con su hash o su commit fijado [TERCEROS-ETCD-D334] [TERCEROS-LIBBPF-D334]

### Hecho DAY334
- **#180, `fix/lab-terceros-etcd`** (merge `0e8668946`), EMECAS+++ production desde cero **VERDE en 4h52m**
  (`logs/lab/emecas/emecas_20261122_074159.log`). Dos commits:
  - `0a8a001fb`: `provisioning/etcd/{VERSION,SHA256}` (3.6.16 y el SHA256 del `SHA256SUMS` oficial) y
    `scripts/terceros/etcd_instalar.sh` con su test (`test-etcd-instalar`, también en el EMECAS: 33 casos; los 23
    rechazos fallan contra funciones que lo aceptan todo). Baja con `wget --https-only`, saca del tarball solo `etcd`,
    `etcdctl` y `etcdutl` por nombre exacto, comprueba que los tres dicen la versión y deja la marca
    `/usr/local/lib/argus-etcd.sha256`.
  - `558adf090`: el aprovisionador `etcd-install` llama al instalador; fuera la versión y el sha256 escritos en el
    heredoc `ETCD_INSTALL` y la descarga con `curl`.
  - Comprobado en el log: en control-1, control-2 y control-3, tarball de 25263894 bytes con el SHA256 de
    `provisioning/etcd/SHA256` y `etcd Version: 3.6.16`.
- **#181, `fix/lab-terceros-libbpf`** (merge `4d6f00313`), EMECAS+++ production desde cero **VERDE en 4h33m**
  (`logs/lab/emecas/emecas_20261122_132014.log`). Dos commits:
  - `ce8d1f738`: `provisioning/libbpf/{VERSION,COMMIT}` (1.4.6 y `fdf402b384cc42ce29bb9e27011633be3cbafe1e`) y
    `scripts/terceros/libbpf_instalar.sh` con su test (`test-libbpf-instalar`: 27 casos, 18 rechazos; el tag se prueba
    con un repositorio git de juguete, sin red). Clona el tag y para si no apunta al commit fijado; compila la estática
    y la compartida; al final comprueba que `libbpf.so.1` resuelve a `/usr/lib64/libbpf.so.<VERSION>` y deja la marca
    `/usr/local/lib/argus-libbpf.commit`.
  - `24e8ee484`: el bloque «CRITICAL: libbpf 1.4.6» de `all-dependencies` pasa a ser la llamada al instalador.
  - Comprobado en el log: en el defender, desde cero, tag `v1.4.6` clonado y comprobado contra `fdf402b3…`, y
    `libbpf.so.1 -> /usr/lib64/libbpf.so.1.4.6`.
- Parcheadores d334 (`d334_etcd_lente.py`, `d334_libbpf_lente.py`) en la rama de archivo `archivo/parcheadores-d334`,
  **solo con push, sin PR**.

### Medido DAY334
- **etcd**: el tarball oficial de v3.6.16 se bajó de nuevo y su sha256 sigue siendo `c8c0d96d…`, el de su
  `SHA256SUMS`. Las primeras líneas de versión son `etcd Version: 3.6.16`, `etcdctl version: 3.6.16` y
  `etcdutl version: 3.6.16` (antes solo se comprobaba `etcd`).
- **libbpf no publica ni firma ni hash.** El tag `v1.4.6` es ligero (sin objeto tag) y apunta a `fdf402b3…`
  («libbpf: bump version to v1.4.6», Andrii Nakryiko), commit sin firma; `git ls-remote` da el mismo. Contra el
  repositorio real, el instalador rechaza el `v1.4.7` (`ca72d073…`). Hay también 1.4.7 y 1.8.0: no se sube.
- **El sniffer enlaza `libbpf.so.1` dinámica** (`objdump -p sniffer/build-production/sniffer`), aunque el
  `Vagrantfile` compilaba con `BUILD_STATIC_ONLY=y`: en el `src/Makefile` de la v1.4.6, `install` depende de `all`,
  y en esa segunda llamada, sin la variable, se construía también la compartida.
- **En el defender hay dos `libbpf.so.1` con el mismo SONAME**: la 1.4.6 en `/usr/lib64` y la 1.1.2 de bookworm
  (`libbpf1 1:1.1.2-0+deb12u1`) en `/usr/lib/x86_64-linux-gnu`. El sniffer en marcha carga la 1.4.6
  (`/proc/<pid>/maps`), pero solo porque `/etc/ld.so.conf.d/libbpf.conf` va antes que `x86_64-linux-gnu.conf` en la
  caché de ldconfig. Desde #181, el aprovisionamiento lo comprueba; al arrancar el proceso, sigue dependiendo de ese
  orden (deuda abajo).
- **La 1.1.2 no se puede quitar**: `apt-get -s remove libbpf1` se lleva también iproute2, chrony, ifupdown e
  isc-dhcp-client.
- **`curl` sigue en los nodos de control**: lo instala `etcd-base` (`apt-get install -y nftables chrony curl`) y lo usa
  `scripts/vigilancia/lib_apt_oficial.sh` para bajar las claves apt (Vault, Falco, Wazuh, Zeek, Arrow).
- **Avance del inventario de descargas del `Vagrantfile`** (`git grep -e wget -e curl -- Vagrantfile`, sin terminar):
  CMake 3.25.0 (`wget`, sin hash, solo si la instalada es < 3.20), Crypto++ 8.7.0 (`wget` del zip, sin hash, solo si
  falla apt), SDKMAN (`curl -s https://get.sdkman.io | bash`, sin comprobar nada, como root) y Kuzu v0.11.3 (`curl`,
  con un sha256 fijado tras la primera descarga, sin contrastar con el mantenedor).

### Decisiones de Alonso DAY334
- **libbpf, opción (a)**: dejar el `git clone` del tag y fijar el commit (no el tarball que genera GitHub ni el paquete
  de Debian).
- La 1.1.2 de bookworm se queda: la necesitan binarios nativos de bookworm.
- Lo del `Makefile` (`status`, `check-libbpf`) y la determinación del cargador van en PRs aparte.

### Deudas
- **DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001**: avanza (título arriba). Queda el inventario con `git grep` de lo
  que se baje con `wget`/`curl` (primeros candidatos, arriba), un PR por lente.
- **DEBT-LAB-CURL-NODOS-001 — ABIERTA (nueva DAY334)**: `curl` en las VMs del lab por `etcd-base` y por
  `lib_apt_oficial.sh`. Las lentes etcd y libbpf no lo añaden, pero tampoco lo quitan. Arreglo: que
  `lib_apt_oficial.sh` baje las claves con `wget` (o con lo que ya haya) y que `etcd-base` no instale `curl`; medir
  antes quién más lo usa en cada VM.
- **DEBT-MAKE-CHECK-LIBBPF-001 — ABIERTA (nueva DAY334, menor)**: `make status` (compara versiones como texto con awk)
  y `make check-libbpf` dan por buena cualquier libbpf ≥ 1.2.0, usan `vagrant ssh` sin límite y no miran qué
  `libbpf.so.1` se carga. Reescribirlos contra `provisioning/libbpf/VERSION`, con `con_limite.pl`; no borrarlos.
- **DEBT-SNIFFER-LIBBPF-ORDEN-LDCONFIG-001 — ABIERTA (nueva DAY334)**: al arrancar, el sniffer carga la 1.4.6 solo por
  el orden de ldconfig. Que no dependa de él: RUNPATH a `/usr/lib64` en el binario o enlazar `libbpf.a`. Medir con
  `/proc/<pid>/maps` y `objdump -p`.
- **DEBT-LAB-PROVISION-SCRIPT-MUERTO-001**: se añade que `scripts/install-sniffer-deps.sh`, `scripts/vagrant-provision.sh`
  y `ml-training/scripts/Vagrantfile_optimized` instalan `libbpf-dev` de apt (la 1.1.2 con sus cabeceras); no los
  llama nadie.
- **DEBT-LAB-VERSIONES-TERCEROS-001**: etcd y libbpf ya están en `provisioning/<producto>/`.

### Lecciones DAY334
- Leer antes de predecir: la descarga de etcd era con `curl`, no con `wget`.
- `objdump -p` dice si una biblioteca se enlaza dinámica; un `BUILD_STATIC_ONLY=y` en una llamada a `make` no dice
  nada de la siguiente.
- Con dos bibliotecas del mismo SONAME, cuál carga un proceso lo decide el orden del cargador: medir con
  `/proc/<pid>/maps`, y que el instalador compruebe a qué resuelve (`ldconfig -p`) en vez de suponerlo.
- Antes de quitar un paquete de la distribución, simular: `apt-get -s remove` dice qué más se llevaría.
- Un tag ligero no lleva firma y se puede mover: se fija el commit, y el test lo prueba con un repositorio git de
  juguete (`file://`), sin red.
- Los `.py` y `.sh` que se pasan como fichero pueden no llegar a Descargas: entregarlos como bloque `cat > f <<'EOF'`
  y comprobar el sha256 en el sitio.
"""
datos = open(F, "rb").read()
sha = lambda b: hashlib.sha256(b).hexdigest()
if sha(datos) != PARTIDA:
    sys.exit("❌ %s: sha256 de partida %s, se espera %s. No se ha escrito nada" % (F, sha(datos), PARTIDA))
t = datos.decode("utf-8")
for i, v in enumerate((T1_VIEJO, T2_VIEJO), 1):
    if t.count(v) != 1:
        sys.exit("❌ %s: el ancla %d está %d veces (se espera 1). No se ha escrito nada" % (F, i, t.count(v)))
t = t.replace(T1_VIEJO, T1_NUEVO).replace(T2_VIEJO, T2_NUEVO) + SECCION
b = t.encode("utf-8")
if sha(b) != LLEGADA:
    sys.exit("❌ %s: sha256 de llegada %s, se espera %s. No se ha escrito nada" % (F, sha(b), LLEGADA))
open(F, "wb").write(b)
print("✅ %s parcheado (sha256 %s)" % (F, LLEGADA))
