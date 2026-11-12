#!/usr/bin/env python3
# test_plano_control.py — DAY324, PR2b de DEBT-ETCD-HA-TLS-RAFT-001 [PLANO-CONTROL-D324]. Comprobaciones estáticas del
# plano de control del laboratorio (sin VMs; se lanza en el Mac, raíz del repo: make test-plano-control).
#   C1 (paso 1, renombrado etcd -> control-1): ningún fichero VIVO nombra todavía a la VM 'etcd' (vagrant ssh/up/halt/
#      status/destroy/ssh-config etcd, S/V etcd "...", known_hosts_etcd, AGENT_NAME etcd, el grupo de Wazuh argus-etcd,
#      la máquina "etcd" del Vagrantfile o del inventario). VIVO no es una lista escrita a mano: se parte del Makefile,
#      el Vagrantfile, ansible/ y provisioning/, y se añade todo script de scripts/ o tools/ cuya ruta aparezca en un
#      fichero vivo, hasta que no entra ninguno más. Un parcheador de un día que nadie llama no es vivo. Este test
#      no se mira a sí mismo (sus muestras de C0 llevan el nombre viejo a propósito).
#   C0 (el detector detecta): antes de mirar el repo, el detector tiene que cazar cada línea de una muestra con el
#      nombre viejo y dejar pasar cada línea de una muestra legítima (etcd.service, etcd-server, /etc/etcd...). Si no,
#      el test falla sin mirar nada: un detector ciego daría un verde falso.
# Coste: lineal en el tamaño de los ficheros vivos.
import os
import re
import subprocess
import sys

VIEJO = re.compile(
    r"vagrant (?:ssh|up|halt|provision|ssh-config|status|destroy|reload)(?: -f)?(?: (?:defender|client|suricata|zeek|wazuh))*"
    r" etcd(?![\w/.-])"
    r"|(?:^|[\s;(|&])[SV] etcd \""
    r"|known_hosts_etcd"
    r"|argus-etcd(?![\w-])"
    r"|\"AGENT_NAME\" => \"etcd\""
    r"|config\.vm\.define \"etcd\""
    r"|^\s+etcd:\s*$"
    r"|\^etcd \+running"
    r"|^etcd\targus-")
DEBE_CAZAR = [
    'vagrant ssh etcd -c "bash x"',
    'vagrant up defender client suricata zeek wazuh etcd',
    'vagrant halt defender client etcd',
    'vagrant status etcd 2>/dev/null | grep -qE "^etcd +running"',
    'vagrant ssh-config etcd >> "$CFG"',
    'echo "VM parada: vagrant up etcd"',
    'vagrant destroy -f etcd && vagrant up etcd',
    'PB=$(S defender "x" | S etcd "sha256sum")',
    '  V etcd "bash $HE restaurar" > "$T"',
    '-o UserKnownHostsFile=/vagrant/dist/deploy/known_hosts_etcd',
    'el agente de Wazuh (grupo argus-etcd: lo asigna',
    'env: {"AGENT_NAME" => "etcd"},',
    '  config.vm.define "etcd", autostart: false do |etcd|',
    '        etcd:',
    'etcd\targus-etcd',
]
DEBE_PASAR = [
    'vagrant ssh control-1 -c "sudo systemctl restart etcd.service"',
    'vagrant ssh -c "cd /vagrant/etcd-server && make"',
    'vagrant ssh control-1 -c "etcdctl --endpoints=https://127.0.0.1:2381 member list"',
    'echo "firman bronce hasta que vuelvan etcd-server, etcd y Vault. VM parada: vagrant up control-1"',
    'install -d -m 0750 -o etcd -g etcd /etc/etcd/tls',
    'profile argus-etcd-server /opt/argus/bin/etcd-server {',
    '    etcd_servers:',
    'etcd() { V control-1 "bash $HE $*" > "$T"; pinta; }',
    'BIN=/vagrant/etcd-server/build-$PROFILE/etcd-server',
    'vagrant ssh defender -c "ipset save" || falla "el manifiesto vigente no protege la VM etcd"',
    'vagrant ssh control-1 -c "systemctl stop x; echo \\"etcd-server de la VM etcd: activo\\""',
]
RAICES = ("Makefile", "Vagrantfile")
DIRS_RAIZ = ("ansible/", "provisioning/")
DIRS_SCRIPTS = ("scripts/", "tools/")


def falla(msg):
    print("[PLANO-CONTROL] FALLA: " + msg)
    sys.exit(1)


def c0():
    ciegas = [m for m in DEBE_CAZAR if not VIEJO.search(m)]
    falsas = [m for m in DEBE_PASAR if VIEJO.search(m)]
    if ciegas or falsas:
        falla("C0 detector: no caza " + repr(ciegas) + "; caza de más " + repr(falsas))
    print("[PLANO-CONTROL] C0 PASA: el detector caza %d de %d líneas viejas y deja pasar %d de %d legítimas"
          % (len(DEBE_CAZAR), len(DEBE_CAZAR), len(DEBE_PASAR), len(DEBE_PASAR)))


def vivos():
    todos = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout.split("\n")
    todos = [f for f in todos if f]
    vivo = {f for f in todos if f in RAICES or f.startswith(DIRS_RAIZ)}
    candidatos = [f for f in todos if f.startswith(DIRS_SCRIPTS)]
    texto = {}

    def leer(f):
        if f not in texto:
            try:
                with open(f, encoding="utf-8", errors="replace") as h:
                    texto[f] = h.read()
            except (IsADirectoryError, FileNotFoundError):
                texto[f] = ""
        return texto[f]

    nuevos = set(vivo)
    while nuevos:
        corpus = "\n".join(leer(f) for f in nuevos)
        nuevos = {c for c in candidatos if c not in vivo and c in corpus}
        vivo |= nuevos
    return sorted(vivo), leer


def c1():
    vivo, leer = vivos()
    hits = []
    yo = os.path.relpath(os.path.abspath(__file__))
    for f in vivo:
        if f == yo:
            continue
        for i, linea in enumerate(leer(f).split("\n"), 1):
            if VIEJO.search(linea):
                hits.append("%s:%d: %s" % (f, i, linea.strip()[:120]))
    if hits:
        print("\n".join(hits))
        falla("C1: %d líneas vivas nombran todavía a la VM 'etcd' (arriba)" % len(hits))
    print("[PLANO-CONTROL] C1 PASA: %d ficheros vivos, ninguno nombra a la VM 'etcd'" % len(vivo))


if __name__ == "__main__":
    c0()
    c1()
    print("[PLANO-CONTROL] RESULTADO PASA")
