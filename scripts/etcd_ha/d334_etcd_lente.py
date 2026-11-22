#!/usr/bin/env python3
# d334_etcd_lente.py — [TERCEROS-ETCD-D334] parcheador DAY334: DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, lente etcd.
# Vagrantfile: el heredoc ETCD_INSTALL (versión y sha256 escritos dentro, descarga con curl) pasa a ser una llamada a
# scripts/terceros/etcd_instalar.sh, que lee provisioning/etcd/{VERSION,SHA256}. Makefile: target test-etcd-instalar y su
# paso en EMECAS, junto a test-arrow-instalar. Se ejecuta desde la raíz del repo:
#   python3 scripts/etcd_ha/d334_etcd_lente.py
# Comprueba el sha256 de partida de los dos ficheros y que cada ancla esté las veces exactas; si algo falla, no escribe
# nada. Al final comprueba el sha256 de llegada.
import hashlib, sys

PARTIDA = {
    "Vagrantfile": "c22ccbe4f9b1c4c6f412f1c90319bfa5f95f74784be7af5f90667769ed6934ba",
    "Makefile": "feb26923f951dc64f3d005cb0a03d14f2a228db6ec6cf779b8a42799f9ff3a96",
}
LLEGADA = {
    "Vagrantfile": "a46b8dcbf2e48514020c3171098c28a8d4925f110aaf1e117cfbd5f495d43499",
    "Makefile": "3491e9215d3897b2268f318e1f8e777a31f049e62891bc287747f64fabd45bea",
}

V_COMENTARIO_VIEJO = """\
    # [ETCD-CLUSTER-D324] etcd en TODOS los nodos (ADR-048, revisión DAY324). Aquí solo el binario oficial (v3.6.16, sha256
    # fijado), el certificado etcd-<nodo> del nodo (d312_pki.sh nodos: su IP en el SAN) y el usuario etcd. etcd.conf.yml,
    # la unidad, el arranque del clúster y el RBAC los hace Ansible desde el defender: make etcd-cluster-deploy.
"""
V_COMENTARIO_NUEVO = """\
    # [ETCD-CLUSTER-D324] etcd en TODOS los nodos (ADR-048, revisión DAY324). Aquí solo el binario oficial, el certificado
    # etcd-<nodo> del nodo (d312_pki.sh nodos: su IP en el SAN) y el usuario etcd. etcd.conf.yml, la unidad, el arranque
    # del clúster y el RBAC los hace Ansible desde el defender: make etcd-cluster-deploy.
    # [TERCEROS-ETCD-D334] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, lente etcd: el binario lo pone
    # scripts/terceros/etcd_instalar.sh, con la versión y el SHA256 (el del SHA256SUMS oficial) de provisioning/etcd/.
    # Antes: los dos escritos aquí y la descarga con curl.
"""

V_INSTALL_VIEJO = """\
    etcd.vm.provision "shell", name: "etcd-install", inline: <<-'ETCD_INSTALL'
  set -e
  ETCD_VER="v3.6.16"
  ETCD_SHA256="c8c0d96d8292ef085deabbf735e9561d3d396768e4d606df005aa25964f21911"
  ETCD_URL="https://github.com/etcd-io/etcd/releases/download/${ETCD_VER}/etcd-${ETCD_VER}-linux-amd64.tar.gz"
  if [ -x /usr/local/bin/etcd ] && /usr/local/bin/etcd --version 2>/dev/null | grep -q "^etcd Version: ${ETCD_VER#v}$"; then
    echo "✅ etcd ${ETCD_VER} ya instalado"; exit 0
  fi
  echo "📦 Instalando etcd ${ETCD_VER} (binario oficial, sha256 fijado)..."
  command -v curl > /dev/null || { apt-get update -qq; apt-get install -y curl; }
  T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
  curl -fsSL "$ETCD_URL" -o "$T/etcd.tgz"
  GOT=$(sha256sum "$T/etcd.tgz" | awk '{print $1}')
  [ "$GOT" = "$ETCD_SHA256" ] || { echo "❌ ETCD_INSTALL: sha256 ${GOT}, se exige ${ETCD_SHA256}"; exit 1; }
  tar xzf "$T/etcd.tgz" -C "$T"
  install -m 0755 "$T/etcd-${ETCD_VER}-linux-amd64/etcd"    /usr/local/bin/etcd
  install -m 0755 "$T/etcd-${ETCD_VER}-linux-amd64/etcdctl" /usr/local/bin/etcdctl
  install -m 0755 "$T/etcd-${ETCD_VER}-linux-amd64/etcdutl" /usr/local/bin/etcdutl
  /usr/local/bin/etcd --version | grep -q "^etcd Version: ${ETCD_VER#v}$" || { echo "❌ ETCD_INSTALL: versión instalada inesperada"; exit 1; }
  echo "✅ etcd $(/usr/local/bin/etcd --version | head -1 | awk '{print $3}') instalado (sha256 verificado)"
    ETCD_INSTALL
"""
V_INSTALL_NUEVO = """\
    etcd.vm.provision "shell", name: "etcd-install",
      inline: "bash /vagrant/scripts/terceros/etcd_instalar.sh || { echo '❌ etcd install failed'; exit 1; }"
"""

M_PASO_VIEJO = "\t@$(EMECAS_PASO) test-arrow-instalar -- $(MAKE) test-arrow-instalar\n"
M_PASO_NUEVO = M_PASO_VIEJO + "\t@$(EMECAS_PASO) test-etcd-instalar -- $(MAKE) test-etcd-instalar\n"

M_TARGET_VIEJO = ".PHONY: test-arrow-instalar\ntest-arrow-instalar:\n\t@bash scripts/terceros/test_arrow_instalar.sh\n"
M_TARGET_NUEVO = M_TARGET_VIEJO + (
    "\n"
    "# [TERCEROS-ETCD-D334] test-etcd-instalar (Mac, sin VMs ni red): las funciones de scripts/terceros/etcd_instalar.sh\n"
    "# (VERSION, SHA256, versión de los tres binarios, qué se saca del tarball y qué no) y provisioning/etcd/{VERSION,SHA256},\n"
    "# también contra funciones que lo aceptan todo.\n"
    ".PHONY: test-etcd-instalar\n"
    "test-etcd-instalar:\n"
    "\t@bash scripts/terceros/test_etcd_instalar.sh\n"
)

CAMBIOS = {
    "Vagrantfile": [(V_COMENTARIO_VIEJO, V_COMENTARIO_NUEVO), (V_INSTALL_VIEJO, V_INSTALL_NUEVO)],
    "Makefile": [(M_PASO_VIEJO, M_PASO_NUEVO), (M_TARGET_VIEJO, M_TARGET_NUEVO)],
}

def sha(b):
    return hashlib.sha256(b).hexdigest()

nuevos = {}
for f, cambios in CAMBIOS.items():
    try:
        datos = open(f, "rb").read()
    except OSError as e:
        sys.exit("❌ no leo %s: %s (¿desde la raíz del repo?). No se ha escrito nada" % (f, e))
    if sha(datos) != PARTIDA[f]:
        sys.exit("❌ %s: sha256 de partida %s, se espera %s. No se ha escrito nada" % (f, sha(datos), PARTIDA[f]))
    texto = datos.decode("utf-8")
    for i, (viejo, nuevo) in enumerate(cambios, 1):
        n = texto.count(viejo)
        if n != 1:
            sys.exit("❌ %s: el ancla %d está %d veces (se espera 1). No se ha escrito nada" % (f, i, n))
        texto = texto.replace(viejo, nuevo)
    b = texto.encode("utf-8")
    if sha(b) != LLEGADA[f]:
        sys.exit("❌ %s: sha256 de llegada %s, se espera %s. No se ha escrito nada" % (f, sha(b), LLEGADA[f]))
    nuevos[f] = b

for f, b in nuevos.items():
    open(f, "wb").write(b)
    print("✅ %s parcheado (sha256 %s)" % (f, LLEGADA[f]))
