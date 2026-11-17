#!/usr/bin/env python3
# d324_etcd_cluster.py — DAY324, PR2b paso 4 de DEBT-ETCD-HA-TLS-RAFT-001 [ETCD-CLUSTER-D324]: etcd en clúster en los
# nodos del plano de control (ADR-048, revisión DAY324). Cambia:
#   Vagrantfile: etcd-install y los certificados etcd-<nodo> en TODOS los nodos (salen del 'if primero'); el heredoc
#     etcd-local (etcd de un nodo, configuración y RBAC) se sustituye por etcd-tls (usuario etcd y certificado del
#     nodo, verificado contra la CA y con su IP en el SAN); etcd-base abre 2381/2382 solo a los otros nodos.
#   Makefile: CONTROL_NODOS (de nodos_control.rb) en los up/halt de todas las VMs; etcd-cluster-deploy (Ansible) y
#     test-etcd-cluster; etcd-vm-deploy despliega primero el clúster.
#   Inventario: grupo etcd_members (los nodos del plano de control).
#   group_vars: etcd_almacen_endpoints sale de argus_control_nodos; tiempos de Raft.
#   nodos_control.rb: modos 'nombres' (para el Makefile) y 'grupo'; test_plano_control.py: C2 exige etcd_members.
# Los ficheros nuevos (playbook, plantilla, test) se dejan antes en su sitio con su sha256. Uso (Mac, raíz del repo): python3 -I scripts/etcd_ha/d324_etcd_cluster.py
import hashlib
import os
import sys

GV = "ansible/inventory/group_vars/argus_dev.yml"
INV = "ansible/inventory/dev.yml"
PARTIDA = {
    "Vagrantfile": "f6403ac67210dff8d833527e4e2f99680669ea0efdac5350903ce1ff36e7bb3a",
    "Makefile": "db81ac55ffaf5243635894ce5610ad9cf92b304ec03b9edd0938fc3bb703c7c4",
    INV: "701920b006f9c911f3d01a8318d7a46c4bb3e1de79fa4eae83481cf4cea0fc3c",
    GV: "955b5fc62a0a33d3e9fd39b1c1dc755b70e0bf49918c7ab5eeb53c53b555446f",
    "scripts/etcd_ha/nodos_control.rb": "e2fbfe05563df494c40fd47e3ebd4980a3f2572e21da38c09a6963dc9f16cad4",
    "scripts/etcd_ha/test_plano_control.py": "50fd6ce357e68d4327e63e3cc92f8eb5c41d0dbed8030d6f61b864913757b81c",
}
NUEVOS = ["ansible/playbooks/etcd_cluster.yml", "ansible/playbooks/templates/etcd.conf.yml.j2",
          "scripts/etcd_ha/test_etcd_cluster.sh"]
RB = "scripts/etcd_ha/nodos_control.rb"
TPC = "scripts/etcd_ha/test_plano_control.py"

ETCD_BASE_PEERS = r'''      # [ETCD-CLUSTER-D324] etcd entre nodos del plano de control: clientes (2381) y peers (2382), solo desde los otros
      # nodos (ARGUS_PEERS, del Vagrantfile: argus_control_nodos menos este). Con un solo nodo no hay regla.
      if [ -n "${ARGUS_PEERS:-}" ]; then
        [[ "$ARGUS_PEERS" =~ ^192\.168\.100\.[0-9]{1,3}(,\ 192\.168\.100\.[0-9]{1,3})*$ ]] \
          || { echo "❌ etcd-base: ARGUS_PEERS='$ARGUS_PEERS' mal formado"; exit 1; }
        sed -i "s|^    ip saddr 192.168.100.1 tcp dport 2379 accept\$|&\n    ip saddr { $ARGUS_PEERS } tcp dport { 2381, 2382 } accept|" /etc/nftables.conf
      fi
      nft -c -f /etc/nftables.conf
'''
ETCD_BASE_VERIF = r'''        || { echo "❌ etcd-base: la regla del 2379 no quedó cargada"; exit 1; }
      if [ -n "${ARGUS_PEERS:-}" ]; then
        nft list chain inet argus_etcd input | grep -q "ip saddr { $ARGUS_PEERS } tcp dport { 2381, 2382 } accept" \
          || { echo "❌ etcd-base: la regla de etcd entre nodos ($ARGUS_PEERS) no quedó cargada"; exit 1; }
      fi
'''
PKI_ETCD = '''    end  # if primero

    # [ETCD-CLUSTER-D324] etcd en TODOS los nodos (ADR-048, revisión DAY324). Aquí solo el binario oficial (v3.6.16, sha256
    # fijado), el certificado etcd-<nodo> del nodo (d312_pki.sh nodos: su IP en el SAN) y el usuario etcd. etcd.conf.yml,
    # la unidad, el arranque del clúster y el RBAC los hace Ansible desde el defender: make etcd-cluster-deploy.
    etcd.vm.provision "shell", name: "pki-etcd-dir", inline: "install -d -m 0700 -o vagrant -g vagrant /tmp/argus-pki-etcd"
    ["ca.crt", "etcd-#{nodo["nombre"]}.crt", "etcd-#{nodo["nombre"]}.key"].each do |f|
'''
ETCD_TLS = r'''    etcd.vm.provision "shell", name: "etcd-tls",
      env: { "ARGUS_NODO" => nodo["nombre"], "ARGUS_NODO_IP" => nodo["ip"] }, inline: <<-'ETCD_TLS'
      set -e
      umask 077
      [[ "${ARGUS_NODO:-}" =~ ^[a-z0-9-]{1,32}$ ]] && [[ "${ARGUS_NODO_IP:-}" =~ ^192\.168\.100\.[0-9]{1,3}$ ]] \
        || { echo "❌ etcd-tls: ARGUS_NODO='${ARGUS_NODO:-}' / ARGUS_NODO_IP='${ARGUS_NODO_IP:-}' ausentes o mal formados"; exit 1; }
      echo "=== $ARGUS_NODO: usuario y TLS de etcd [ETCD-CLUSTER-D324] (configuración y arranque: make etcd-cluster-deploy) ==="
      id etcd > /dev/null 2>&1 || useradd --system --home-dir /var/lib/etcd --shell /usr/sbin/nologin etcd
      install -d -m 0700 -o etcd -g etcd /var/lib/etcd
      install -d -m 0755 -o root -g root /etc/etcd
      PKI_IN=/tmp/argus-pki-etcd
      if [ -d "$PKI_IN" ]; then
        install -d -m 0750 -o etcd -g etcd /etc/etcd/tls
        install -m 0644 -o etcd -g etcd "$PKI_IN/ca.crt"                /etc/etcd/tls/ca.crt
        install -m 0644 -o etcd -g etcd "$PKI_IN/etcd-$ARGUS_NODO.crt" /etc/etcd/tls/etcd.crt
        install -m 0600 -o etcd -g etcd "$PKI_IN/etcd-$ARGUS_NODO.key" /etc/etcd/tls/etcd.key
        rm -rf "$PKI_IN"
      fi
      for f in /etc/etcd/tls/ca.crt /etc/etcd/tls/etcd.crt /etc/etcd/tls/etcd.key; do
        [ -s "$f" ] || { echo "❌ etcd-tls: falta $f (en el Mac: bash scripts/etcd_ha/d312_pki.sh nodos \$ARGUS_PKI_DIR; vagrant provision $ARGUS_NODO)"; exit 1; }
      done
      command -v openssl > /dev/null || { apt-get update -qq; apt-get install -y -qq openssl > /dev/null; }
      openssl verify -CAfile /etc/etcd/tls/ca.crt /etc/etcd/tls/etcd.crt > /dev/null \
        || { echo "❌ etcd-tls: /etc/etcd/tls/etcd.crt no lo firmó la CA del laboratorio"; exit 1; }
      openssl x509 -in /etc/etcd/tls/etcd.crt -noout -text | grep -qF "IP Address:$ARGUS_NODO_IP" \
        || { echo "❌ etcd-tls: /etc/etcd/tls/etcd.crt sin IP:$ARGUS_NODO_IP en el SAN (¿el certificado de otro nodo?)"; exit 1; }
      echo "✅ etcd-tls: etcd-$ARGUS_NODO (IP:$ARGUS_NODO_IP, firmado por la CA) en /etc/etcd/tls; etcd sin configurar hasta make etcd-cluster-deploy"
    ETCD_TLS
'''
MK_VAR = '''ETCD_VM_ESPERA_S ?= 30
# [PLANO-CONTROL-D324] nodos del plano de control: argus_control_nodos del group_vars, validados por nodos_control.rb
# (la misma validación que el Vagrantfile). Sin lista válida, el target que los use para aquí diciéndolo.
CONTROL_NODOS = $(or $(shell ruby scripts/etcd_ha/nodos_control.rb nombres ansible/inventory/group_vars/argus_dev.yml Vagrantfile),$(error [PLANO-CONTROL-D324] sin nodos de control: ruby scripts/etcd_ha/nodos_control.rb nodos ansible/inventory/group_vars/argus_dev.yml Vagrantfile))
'''
MK_DEPLOY = '''etcd-vm-deploy:
\t@$(MAKE) --no-print-directory etcd-cluster-deploy  # [ETCD-CLUSTER-D324] el etcd-server necesita el clúster antes
\t@bash scripts/etcd_ha/d312_etcd_vm_deploy.sh $(PROFILE)
'''
MK_TARGETS = '''# [ETCD-CLUSTER-D324] etcd en clúster en los nodos del plano de control (Ansible desde el defender, como deploy-configs):
# ansible/playbooks/etcd_cluster.yml. Arranque estático; con datos solo reinicia si cambió la configuración.
etcd-cluster-deploy:
\t@vagrant ssh defender -- -t "cd /vagrant && sudo ansible-playbook -i ansible/inventory/dev.yml ansible/playbooks/etcd_cluster.yml --diff"

# [ETCD-CLUSTER-D324] el clúster de verdad (VMs arriba): idempotencia, miembros de la lista, replicación, TLS, hashkv
test-etcd-cluster:
\t@bash scripts/etcd_ha/test_etcd_cluster.sh

# Informe (rc 0 siempre)
'''
RB_PARES = [
    ("#   ruby scripts/etcd_ha/nodos_control.rb inventario INVENTARIO          -> host<TAB>ansible_host de argus_dev, uno por línea\n",
     "#   ruby scripts/etcd_ha/nodos_control.rb inventario INVENTARIO          -> host<TAB>ansible_host de argus_dev, uno por línea\n"
     "#   ruby scripts/etcd_ha/nodos_control.rb grupo INVENTARIO GRUPO         -> los hosts del grupo, uno por línea\n"
     "#   ruby scripts/etcd_ha/nodos_control.rb nombres GROUP_VARS VAGRANTFILE -> los nombres en una línea (el Makefile: CONTROL_NODOS)\n"),
    ('    h.map { |nombre, v| [nombre, (v || {})["ansible_host"].to_s] }\n  end\nend\n',
     '    h.map { |nombre, v| [nombre, (v || {})["ansible_host"].to_s] }\n  end\n\n'
     '  def self.hosts_grupo(inventario, grupo)\n'
     '    d = YAML.safe_load(File.read(inventario, encoding: "UTF-8")) || {}\n'
     '    ((((d["all"] || {})["children"] || {})[grupo] || {})["hosts"] || {}).keys\n'
     '  end\nend\n'),
    ('  when "inventario"\n',
     '  when "nombres"\n'
     '    abort "uso: ruby #{$PROGRAM_NAME} nombres GROUP_VARS VAGRANTFILE" unless ARGV.size == 3\n'
     '    cfg, errores, avisos = ArgusNodosControl.cargar(ARGV[1], ARGV[2])\n'
     '    avisos.each { |a| warn "[PLANO-CONTROL] AVISO #{a}" }\n'
     '    unless errores.empty?\n'
     '      errores.each { |e| warn "[PLANO-CONTROL] ERROR #{e}" }\n'
     '      exit 1\n'
     '    end\n'
     '    puts cfg["nodos"].map { |n| n["nombre"] }.join(" ")\n'
     '  when "grupo"\n'
     '    abort "uso: ruby #{$PROGRAM_NAME} grupo INVENTARIO GRUPO" unless ARGV.size == 3\n'
     '    puts ArgusNodosControl.hosts_grupo(ARGV[1], ARGV[2])\n'
     '  when "inventario"\n'),
    ('    abort "uso: ruby #{$PROGRAM_NAME} nodos GROUP_VARS VAGRANTFILE | inventario INVENTARIO"',
     '    abort "uso: ruby #{$PROGRAM_NAME} nodos|nombres GROUP_VARS VAGRANTFILE | inventario INVENTARIO | grupo INVENTARIO GRUPO"'),
]
TPC_PARES = [
    ("#      el group_vars real, y el inventario lleva exactamente esos nodos con su IP (ningún control-N de más ni de menos).\n",
     "#      el group_vars real, y el inventario lleva exactamente esos nodos con su IP (ningún control-N de más ni de menos),\n"
     "#      y su grupo etcd_members (el que despliega ansible/playbooks/etcd_cluster.yml) es exactamente esa lista.\n"),
    ('    with open(GV, encoding="utf-8") as f:\n        real = f.read()\n',
     '    rc, g = ruby("grupo", INV, "etcd_members")\n'
     '    miembros = sorted(l.strip() for l in g.splitlines() if l.strip())\n'
     '    if rc != 0 or miembros != sorted(n for n, _ in nodos):\n'
     '        falla("C2: el grupo etcd_members del inventario (%s) no es la lista de nodos (%s)"\n'
     '              % (", ".join(miembros), ", ".join(n for n, _ in nodos)))\n'
     '    with open(GV, encoding="utf-8") as f:\n        real = f.read()\n'),
    ('    print("[PLANO-CONTROL] C2 PASA: %d nodos (%s) iguales en group_vars e inventario; %d copias estropeadas rechazadas"',
     '    print("[PLANO-CONTROL] C2 PASA: %d nodos (%s) iguales en group_vars, inventario y etcd_members; %d copias estropeadas rechazadas"'),
]
CAMBIOS = {
    "Vagrantfile": [
        ("etcd.vm.provision \"shell\", name: \"etcd-base\", run: \"always\", inline: <<-'ETCD_BASE'",
         "etcd.vm.provision \"shell\", name: \"etcd-base\", run: \"always\",\n"
         "      env: { \"ARGUS_PEERS\" => ARGUS_CONTROL[\"nodos\"].map { |n| n[\"ip\"] }.reject { |ip| ip == nodo[\"ip\"] }.join(\", \") },\n"
         "      inline: <<-'ETCD_BASE'"),
        ("      nft -c -f /etc/nftables.conf\n", ETCD_BASE_PEERS),
        ('        || { echo "❌ etcd-base: la regla del 2379 no quedó cargada"; exit 1; }\n', ETCD_BASE_VERIF),
        ("    # [ETCD-LOCAL-D312] etcd real de 1 nodo (binario oficial v3.6.16, sha256 fijado, como Kuzu), solo 127.0.0.1:2381/2382,\n"
         "    # TLS de cliente obligatorio y RBAC por CN (etcd-server: readwrite /argus/). El PR2 añade los peers (HA Raft).\n"
         "    etcd.vm.provision \"shell\", name: \"pki-etcd-dir\", inline: \"install -d -m 0700 -o vagrant -g vagrant /tmp/argus-pki-etcd\"\n"
         "    %w[ca.crt etcd.crt etcd.key].each do |f|\n", PKI_ETCD),
        ("    end  # if primero\n\n    # [DEPLOY-SSH-D315] DEBT-ANSIBLE-DEPLOY-CONFIGS-001 paso 2a: usuario argus-deploy",
         "\n    # [DEPLOY-SSH-D315] DEBT-ANSIBLE-DEPLOY-CONFIGS-001 paso 2a: usuario argus-deploy"),
    ],
    "Makefile": [
        ("ETCD_VM_ESPERA_S ?= 30\n", MK_VAR),
        ("vagrant up defender client control-1\n", "vagrant up defender client $(CONTROL_NODOS)\n"),
        ("vagrant halt defender client control-1\n", "vagrant halt defender client $(CONTROL_NODOS)\n"),
        ("@vagrant up defender client suricata zeek wazuh control-1\n", "@vagrant up defender client suricata zeek wazuh $(CONTROL_NODOS)\n"),
        ("@vagrant halt defender client suricata zeek wazuh control-1\n", "@vagrant halt defender client suricata zeek wazuh $(CONTROL_NODOS)\n"),
        ("vagrant-up -- vagrant up defender client suricata zeek wazuh control-1\n",
         "vagrant-up -- vagrant up defender client suricata zeek wazuh $(CONTROL_NODOS)\n"),
        ("etcd-vm-deploy:\n\t@bash scripts/etcd_ha/d312_etcd_vm_deploy.sh $(PROFILE)\n", MK_DEPLOY),
        ("# Informe (rc 0 siempre)\n", MK_TARGETS),
    ],
    RB: RB_PARES,
    TPC: TPC_PARES,
    INV: [
        ("    etcd_servers:\n      hosts:\n        control-1:\n",
         "    etcd_servers:\n      hosts:\n        control-1:\n"
         "    # [ETCD-CLUSTER-D324] miembros del clúster etcd (ansible/playbooks/etcd_cluster.yml): los nodos de\n"
         "    # argus_control_nodos (make test-plano-control y el propio playbook exigen que coincidan)\n"
         "    etcd_members:\n      hosts:\n        control-1:\n        control-2:\n        control-3:\n"),
    ],
    GV: [
        ("# Lab: un único miembro, elegido a mano (el etcd local de la VM etcd).\n"
         "etcd_almacen_endpoints:\n  - \"https://127.0.0.1:2381\"\n",
         "# Lab [ETCD-CLUSTER-D324]: los miembros salen de argus_control_nodos (abajo), no de una lista escrita a mano.\n"
         "etcd_almacen_endpoints: \"{{ argus_control_nodos | map(attribute='ip') | map('regex_replace', '^(.*)$', 'https://\\\\1:2381') | list }}\"\n"),
        ("argus_control_cpus: 2\n",
         "argus_control_cpus: 2\n\n"
         "# [ETCD-CLUSTER-D324] tiempos de Raft de etcd en ms (ansible/playbooks/etcd_cluster.yml). heartbeat: entero [50, 1000];\n"
         "# election: entero [500, 10000] y >= 5 x heartbeat. Ausentes o mal: 100 y 1000 (los de etcd), avisando con\n"
         "# [ETCD-CLUSTER-DEFAULT]. Se miden en el PR2e (reelección y cambios de líder durante un EMECAS+++).\n"
         "etcd_heartbeat_interval_ms: 100\n"
         "etcd_election_timeout_ms: 1000\n"),
    ],
}


def falla(msg):
    print("[D324-ETCD-CLUSTER] FALLA: " + msg + " (no se ha escrito nada)")
    sys.exit(1)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    faltan = [f for f in NUEVOS if not os.path.isfile(f)]
    if faltan:
        falla("antes, en su sitio: " + ", ".join(faltan))
    nuevos = []
    for ruta, pares in CAMBIOS.items():
        if not os.path.isfile(ruta):
            falla(ruta + " no existe (¿raíz del repo?)")
        with open(ruta, "rb") as f:
            b = f.read()
        if sha(b) != PARTIDA[ruta]:
            falla(ruta + " no es el de partida: sha256 " + sha(b)[:16] + " (esperado " + PARTIDA[ruta][:16] + ")")
        t = b.decode("utf-8")
        for viejo, nuevo in pares:
            k = t.count(viejo)
            if k != 1:
                falla("%s: '%s' aparece %d veces (esperada 1)" % (ruta, viejo.strip()[:60], k))
            t = t.replace(viejo, nuevo)
        nuevos.append((ruta, t))
    vf = dict(nuevos)["Vagrantfile"]
    i = vf.index("    etcd.vm.provision \"shell\", name: \"etcd-local\", inline: <<-'ETCD_LOCAL'\n")
    j = vf.index("    ETCD_LOCAL\n", i) + len("    ETCD_LOCAL\n")
    if vf.count("name: \"etcd-local\"") != 1:
        falla("Vagrantfile: el aprovisionador etcd-local no aparece exactamente una vez")
    vf = vf[:i] + ETCD_TLS + vf[j:]
    nuevos = [(r, vf if r == "Vagrantfile" else t) for r, t in nuevos]
    for ruta, t in nuevos:
        tmp = ruta + ".d324tmp"
        st = os.stat(ruta)
        with open(tmp, "wb") as f:
            f.write(t.encode("utf-8"))
        os.chmod(tmp, st.st_mode & 0o7777)
        os.replace(tmp, ruta)
        print("[D324-ETCD-CLUSTER] %s sha256 %s" % (ruta, sha(t.encode("utf-8"))))
    print("[D324-ETCD-CLUSTER] RESULTADO PASA: %d ficheros; ahora: make test-plano-control" % len(nuevos))


if __name__ == "__main__":
    main()
