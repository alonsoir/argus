#!/usr/bin/env python3
# d334_libbpf_lente.py — [TERCEROS-LIBBPF-D334] parcheador DAY334: DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, lente
# libbpf. Vagrantfile: el bloque "CRITICAL: libbpf 1.4.6" de all-dependencies (git clone del tag sin comprobar, solo si
# la instalada era < 1.2.0) pasa a ser una llamada a scripts/terceros/libbpf_instalar.sh, que lee
# provisioning/libbpf/{VERSION,COMMIT}; los dos export se quedan para el resto del aprovisionador. Makefile: target
# test-libbpf-instalar y su paso en EMECAS, junto a test-etcd-instalar. Se ejecuta desde la raíz del repo:
#   python3 scripts/etcd_ha/d334_libbpf_lente.py
# Comprueba el sha256 de partida de los dos ficheros y que cada ancla esté las veces exactas; si algo falla, no escribe
# nada. Al final comprueba el sha256 de llegada.
import hashlib, sys

PARTIDA = {"Vagrantfile": 'a46b8dcbf2e48514020c3171098c28a8d4925f110aaf1e117cfbd5f495d43499', "Makefile": '3491e9215d3897b2268f318e1f8e777a31f049e62891bc287747f64fabd45bea'}
LLEGADA = {"Vagrantfile": '3f69ef0b5052a0ca6c4e47b607922d8a55c0465492cff8a750921850300a2cc1', "Makefile": '69a3ba9ecc89a9831fd5c32b001ede8a07f1b5679e9dc497651d3fef04497047'}

V_VIEJO = '      # CRITICAL: libbpf 1.4.6 (FIX PERMANENTE)\n      CURRENT_LIBBPF_VERSION=$(PKG_CONFIG_PATH="/usr/lib64/pkgconfig:/usr/local/lib/pkgconfig:${PKG_CONFIG_PATH}" pkg-config --modversion libbpf 2>/dev/null || echo "0.0.0")\n      if [ "$(printf \'%s\\n\' "1.2.0" "$CURRENT_LIBBPF_VERSION" | sort -V | head -n1)" != "1.2.0" ]; then\n        echo "🔧 Upgrading libbpf to 1.4.6..."\n        apt-get install -y libelf-dev zlib1g-dev pkg-config\n        cd /tmp && rm -rf libbpf\n        git clone --depth 1 --branch v1.4.6 https://github.com/libbpf/libbpf.git\n        cd libbpf/src\n        make -j$(nproc) BUILD_STATIC_ONLY=y\n        make install install_headers\n        ldconfig\n\n        if ! grep -q "PKG_CONFIG_PATH.*usr/lib64/pkgconfig" /etc/environment 2>/dev/null; then\n          echo \'PKG_CONFIG_PATH="/usr/lib64/pkgconfig:/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH"\' >> /etc/environment\n        fi\n\n        cat > /etc/profile.d/libbpf.sh << \'LIBBPF_PROFILE\'\nexport PKG_CONFIG_PATH="/usr/lib64/pkgconfig:/usr/local/lib/pkgconfig:${PKG_CONFIG_PATH}"\nexport LD_LIBRARY_PATH="/usr/lib64:/usr/local/lib:${LD_LIBRARY_PATH}"\nLIBBPF_PROFILE\n        chmod +x /etc/profile.d/libbpf.sh\n        export PKG_CONFIG_PATH="/usr/lib64/pkgconfig:/usr/local/lib/pkgconfig:${PKG_CONFIG_PATH}"\n        export LD_LIBRARY_PATH="/usr/lib64:/usr/local/lib:${LD_LIBRARY_PATH}"\n        echo "/usr/lib64" > /etc/ld.so.conf.d/libbpf.conf\n        ldconfig\n        cd /tmp && rm -rf libbpf\n      fi\n'
V_NUEVO = '      # [TERCEROS-LIBBPF-D334] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, lente libbpf: libbpf del repositorio oficial\n      # (github.com/libbpf/libbpf) en el tag de provisioning/libbpf/VERSION, comprobado contra el commit de\n      # provisioning/libbpf/COMMIT (scripts/terceros/libbpf_instalar.sh). Antes: git clone del tag sin comprobar a qué\n      # apuntaba, y solo si la instalada era < 1.2.0. El script comprueba también que libbpf.so.1 se resuelve a la nuestra\n      # (/usr/lib64) y no a la 1.1.2 de bookworm, que pide iproute2 (medido DAY334). Si falla, para aquí.\n      bash /vagrant/scripts/terceros/libbpf_instalar.sh || { echo "❌ libbpf"; exit 1; }\n      export PKG_CONFIG_PATH="/usr/lib64/pkgconfig:/usr/local/lib/pkgconfig:${PKG_CONFIG_PATH}"\n      export LD_LIBRARY_PATH="/usr/lib64:/usr/local/lib:${LD_LIBRARY_PATH}"\n'
M_PASO_VIEJO = '\t@$(EMECAS_PASO) test-etcd-instalar -- $(MAKE) test-etcd-instalar\n'
M_PASO_NUEVO = '\t@$(EMECAS_PASO) test-etcd-instalar -- $(MAKE) test-etcd-instalar\n\t@$(EMECAS_PASO) test-libbpf-instalar -- $(MAKE) test-libbpf-instalar\n'
M_TARGET_VIEJO = '.PHONY: test-etcd-instalar\ntest-etcd-instalar:\n\t@bash scripts/terceros/test_etcd_instalar.sh\n'
M_TARGET_NUEVO = '.PHONY: test-etcd-instalar\ntest-etcd-instalar:\n\t@bash scripts/terceros/test_etcd_instalar.sh\n\n# [TERCEROS-LIBBPF-D334] test-libbpf-instalar (Mac, sin VMs ni red): las funciones de scripts/terceros/libbpf_instalar.sh\n# (VERSION, COMMIT, el tag contra el commit fijado con un repositorio git de juguete, y a qué libbpf.so.1 resuelve\n# ldconfig) y provisioning/libbpf/{VERSION,COMMIT}, también contra funciones que lo aceptan todo.\n.PHONY: test-libbpf-instalar\ntest-libbpf-instalar:\n\t@bash scripts/terceros/test_libbpf_instalar.sh\n'

CAMBIOS = {
    "Vagrantfile": [(V_VIEJO, V_NUEVO)],
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
