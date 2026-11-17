#!/usr/bin/env python3
# d324_nodos.py — DAY324, PR2b paso 2 de DEBT-ETCD-HA-TLS-RAFT-001 [PLANO-CONTROL-D324]: la lista de nodos del plano de
# control en el group_vars (argus_control_nodos, memoria y CPU), el Vagrantfile define una VM por nodo con
# scripts/etcd_ha/nodos_control.rb, y el inventario lleva los nodos nuevos en argus_dev (aún no en etcd_servers: PR2d).
# control-1 sigue con todo lo de hoy; control-2 y control-3, de momento, la base (reloj del defender, nftables) y el
# acceso de despliegue. El bloque de la VM no se reindenta: sus heredocs llevan ficheros cuyo sangrado importa.
# Antes: scripts/etcd_ha/nodos_control.rb en su sitio (el Vagrantfile lo carga).
# Uso (Mac, raíz del repo): python3 -I scripts/etcd_ha/d324_nodos.py
# Exige el sha256 de partida de cada fichero (rama en 542e02bf7), cambia cada ancla exactamente una vez y no escribe
# nada si algo no cuadra.
import hashlib
import os
import sys

GV = "ansible/inventory/group_vars/argus_dev.yml"
INV = "ansible/inventory/dev.yml"
PARTIDA = {
    "Vagrantfile": "070813f3aacb167bf9a2424fd8394bb33f6785dde116b66962b2dad12ad00d74",
    INV: "0ab4fa478cd28ccd74a96636302435afbb08395c89f598f910d685722029bb86",
    GV: "cf61098ddd83b46a67cfc4392aa974891e9a85daec76187b56b32dc31f7880e1",
}
CARGA = '''p. ej. hospital-lab)"
end

# [PLANO-CONTROL-D324] nodos del plano de control (etcd + Vault + etcd-server; ADR-048/049, revisión DAY324), del mismo
# group_vars: scripts/etcd_ha/nodos_control.rb los valida (formato y límites en su cabecera). Sin lista válida Vagrant
# para aquí: es la identidad de la infraestructura del laboratorio y no tiene defecto sano.
require File.join(__dir__, "scripts", "etcd_ha", "nodos_control")
ARGUS_CONTROL, errores_control, avisos_control = ArgusNodosControl.cargar(ARGUS_GROUP_VARS, File.join(__dir__, "Vagrantfile"))
avisos_control.each { |a| warn "[PLANO-CONTROL-D324] AVISO #{a}" }
unless errores_control.empty?
  abort "[PLANO-CONTROL-D324] #{ARGUS_GROUP_VARS}:\\n  " + errores_control.join("\\n  ")
end
'''
VAGRANT = [
    ('p. ej. hospital-lab)"\nend\n', CARGA),
    ('  config.vm.define "control-1", autostart: false do |etcd|\n',
     '  # [PLANO-CONTROL-D324] una VM por nodo de ARGUS_CONTROL (sin reindentar el bloque: sus heredocs llevan ficheros\n'
     '  # cuyo sangrado importa). El primero (control-1) lleva todo lo de hoy; los demás, de momento, la base (reloj,\n'
     '  # nftables) y el acceso de despliegue: etcd en clúster (paso 4), Vault (PR2c), etcd-server (PR2d), vigilancia (paso 6).\n'
     '  ARGUS_CONTROL["nodos"].each_with_index do |nodo, i_nodo|\n'
     '  primero = i_nodo.zero?\n'
     '  config.vm.define nodo["nombre"], autostart: false do |etcd|\n'),
    ('etcd.vm.hostname    = "argus-control-1"', 'etcd.vm.hostname    = "argus-#{nodo["nombre"]}"'),
    ('vb.name   = "argus-control-1"', 'vb.name   = "argus-#{nodo["nombre"]}"'),
    ('      vb.memory = "1536"  # [VIGILANCIA-D321] +512: Falco (medido DAY321: 114-149 MB de RSS) y el agente de Wazuh\n'
     '      vb.cpus   = 2\n',
     '      vb.memory = ARGUS_CONTROL["memoria_mb"].to_s  # [PLANO-CONTROL-D324] del group_vars (DAY324: ~510 MB de picos)\n'
     '      vb.cpus   = ARGUS_CONTROL["cpus"]\n'),
    ('      ip: "192.168.100.20",\n      mac: "080027A20020",', '      ip: nodo["ip"],\n      mac: nodo["mac"],'),
    ('    # [VAULT-SERVER-D312] PKI: directorio de entrada 0700',
     '    if primero  # [PLANO-CONTROL-D324] PKI, Vault y etcd de un nodo: solo control-1 (etcd en clúster: paso 4; Vault: PR2c)\n'
     '    # [VAULT-SERVER-D312] PKI: directorio de entrada 0700'),
    ('    # [DEPLOY-SSH-D315] DEBT-ANSIBLE-DEPLOY-CONFIGS-001 paso 2a: usuario argus-deploy',
     '    end  # if primero\n\n'
     '    # [DEPLOY-SSH-D315] DEBT-ANSIBLE-DEPLOY-CONFIGS-001 paso 2a: usuario argus-deploy'),
    ("etcd.vm.provision \"shell\", name: \"deploy-access\", run: \"always\", inline: <<-'DEPLOY_ACCESS'",
     "etcd.vm.provision \"shell\", name: \"deploy-access\", run: \"always\",\n"
     "      env: { \"ARGUS_NODO\" => nodo[\"nombre\"], \"ARGUS_NODO_IP\" => nodo[\"ip\"] }, inline: <<-'DEPLOY_ACCESS'"),
    ('      set -e\n      PUB=/vagrant/dist/deploy/argus_deploy_ed25519.pub\n',
     '      set -e\n'
     '      [[ "${ARGUS_NODO:-}" =~ ^[a-z0-9-]{1,32}$ ]] && [[ "${ARGUS_NODO_IP:-}" =~ ^192\\.168\\.100\\.[0-9]{1,3}$ ]] \\\n'
     '        || { echo "❌ deploy-access: ARGUS_NODO=\'${ARGUS_NODO:-}\' / ARGUS_NODO_IP=\'${ARGUS_NODO_IP:-}\' ausentes o mal formados"; exit 1; }\n'
     '      PUB=/vagrant/dist/deploy/argus_deploy_ed25519.pub\n'),
    ("echo \"192.168.100.20 $(cut -d' ' -f1,2 /etc/ssh/ssh_host_ed25519_key.pub)\" > /vagrant/dist/deploy/known_hosts_control-1",
     "echo \"$ARGUS_NODO_IP $(cut -d' ' -f1,2 /etc/ssh/ssh_host_ed25519_key.pub)\" > \"/vagrant/dist/deploy/known_hosts_$ARGUS_NODO\""),
    ('en /vagrant/dist/deploy/known_hosts_control-1"', 'en /vagrant/dist/deploy/known_hosts_$ARGUS_NODO"'),
    ('    # [ETCD-SERVER-UNIT-D317] DEBT-ETCD-HA-TLS-RAFT-001 paso 6a',
     '    if primero  # [PLANO-CONTROL-D324] etcd-server, argus-infra y vigilancia: solo control-1 (PR2d y paso 6)\n'
     '    # [ETCD-SERVER-UNIT-D317] DEBT-ETCD-HA-TLS-RAFT-001 paso 6a'),
    ('  end  # End etcd VM\n',
     '    end  # if primero\n  end  # End VM del nodo de control\n  end  # each ARGUS_CONTROL [PLANO-CONTROL-D324]\n'),
]
NODO_INV = '''        {n}:
          ansible_host: {ip}
          ansible_user: argus-deploy
          ansible_ssh_private_key_file: /root/.ssh/argus_deploy_ed25519
          ansible_host_key_checking: true
          ansible_ssh_common_args: "-o UserKnownHostsFile=/vagrant/dist/deploy/known_hosts_{n} -o StrictHostKeyChecking=yes"
'''
INVENTARIO = [
    ('-o UserKnownHostsFile=/vagrant/dist/deploy/known_hosts_control-1 -o StrictHostKeyChecking=yes"\n    etcd_servers:\n',
     '-o UserKnownHostsFile=/vagrant/dist/deploy/known_hosts_control-1 -o StrictHostKeyChecking=yes"\n'
     '        # [PLANO-CONTROL-D324] los demás nodos del plano de control (argus_control_nodos del group_vars; el test\n'
     '        # make test-plano-control exige que coincidan). Aún no están en etcd_servers: su etcd-server llega en el PR2d.\n'
     + NODO_INV.format(n="control-2", ip="192.168.100.21") + NODO_INV.format(n="control-3", ip="192.168.100.22")
     + '    etcd_servers:\n'),
]
GRUPO = '''argus_hospital_id: "hospital-lab"
'''
GRUPO_NUEVO = '''argus_hospital_id: "hospital-lab"

# [PLANO-CONTROL-D324] nodos del plano de control del laboratorio (ADR-048/049, revisión DAY324): una VM por nodo con
# etcd + Vault + etcd-server. La única fuente: la leen el Vagrantfile y el inventario (make test-plano-control comprueba
# que coinciden), con la validación de scripts/etcd_ha/nodos_control.rb (formato y límites en su cabecera). Sin
# defecto: una lista ausente o mal formada para Vagrant. El primero es control-1 en .20 (el resto del laboratorio lo da
# por hecho hasta el PR2d). MAC fija: el manifiesto de protegidos ata cada IP de infraestructura a su MAC.
argus_control_nodos:
  - { nombre: control-1, ip: 192.168.100.20, mac: "080027A20020" }
  - { nombre: control-2, ip: 192.168.100.21, mac: "080027A20021" }
  - { nombre: control-3, ip: 192.168.100.22, mac: "080027A20022" }
# Memoria y CPU de cada nodo. memoria_mb: entero [768, 4096]; medido DAY324 en la VM etcd: picos de los servicios
# ~510 MB (vault 234, falco 121, etcd 64, wazuh-agent 58, etcd-server 30); 1024 hasta medir el pico del
# aprovisionamiento y de un EMECAS+++. cpus: entero [1, 4].
argus_control_memoria_mb: 1024
argus_control_cpus: 2
'''
CAMBIOS = {"Vagrantfile": VAGRANT, INV: INVENTARIO, GV: [(GRUPO, GRUPO_NUEVO)]}


def falla(msg):
    print("[D324-NODOS] FALLA: " + msg + " (no se ha escrito nada)")
    sys.exit(1)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    if not os.path.isfile("scripts/etcd_ha/nodos_control.rb"):
        falla("falta scripts/etcd_ha/nodos_control.rb (el Vagrantfile lo carga)")
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
    for ruta, t in nuevos:
        tmp = ruta + ".d324tmp"
        st = os.stat(ruta)
        with open(tmp, "wb") as f:
            f.write(t.encode("utf-8"))
        os.chmod(tmp, st.st_mode & 0o7777)
        os.replace(tmp, ruta)
        print("[D324-NODOS] %s sha256 %s" % (ruta, sha(t.encode("utf-8"))))
    print("[D324-NODOS] RESULTADO PASA: %d ficheros; ahora: make test-plano-control" % len(nuevos))


if __name__ == "__main__":
    main()
