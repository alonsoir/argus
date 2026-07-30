#!/usr/bin/env python3
"""
add_wazuh_agents.py — inserta el agente Wazuh en las 4 VMs de agente del Vagrantfile.

Espejo de mitre_start_add_zeek.py: anclado, idempotente, all-or-nothing, con backup.
- Define WAZUH_AGENT_INSTALL (heredoc Ruby QUOTED <<-'...', sin interpolacion) tras el
  cierre de ADAPTER_TOOLCHAIN.
- Anade un provision "wazuh-agent" a defender, client, suricata, zeek (NO a wazuh = manager).
  El nombre del agente por VM viaja en env AGENT_NAME.
- Instala por dpkg del .deb cacheado en /vagrant -> sin apt/DNS/gnupg.

Uso:  python3 add_wazuh_agents.py [ruta_al_Vagrantfile]   (por defecto ./Vagrantfile)
"""
import sys, os, time, re

PATH = sys.argv[1] if len(sys.argv) > 1 else "Vagrantfile"

CONST_BLOCK = '''
# WAZUH_AGENT_INSTALL — instala el agente Wazuh por dpkg del .deb cacheado en /vagrant.
# dpkg NO necesita repo/apt/DNS/gnupg (a diferencia de la via apt). El nombre del agente
# llega por env AGENT_NAME (fijado en cada provision). Version clavada = la del manager.
WAZUH_AGENT_INSTALL = <<-'WAZUH_AGENT_INSTALL_SHELL'
  set -e
  MANAGER_IP="192.168.100.12"
  DEB="/vagrant/provisioning/wazuh/wazuh-agent_4.14.7-1_amd64.deb"
  echo "🛡️  WAZUH_AGENT_INSTALL — agente '${AGENT_NAME}' -> manager ${MANAGER_IP}"
  if /var/ossec/bin/wazuh-control info >/dev/null 2>&1; then
    echo "✅ agente ya instalado, nada que hacer"; exit 0
  fi
  if [ ! -f "$DEB" ]; then
    echo "❌ no encuentro el .deb en $DEB"
    echo "   cachealo antes del up:  mkdir -p provisioning/wazuh && cp logs/wazuh-agent_4.14.7-1_amd64.deb provisioning/wazuh/"
    exit 1
  fi
  WAZUH_MANAGER="$MANAGER_IP" WAZUH_AGENT_NAME="$AGENT_NAME" dpkg -i "$DEB"
  systemctl daemon-reload
  systemctl enable --now wazuh-agent
  echo "✅ WAZUH_AGENT_INSTALL — '${AGENT_NAME}' instalado y arrancado"
WAZUH_AGENT_INSTALL_SHELL
'''

AGENTS = ["defender", "client", "suricata", "zeek"]   # NO wazuh (manager)

def provision_line(var):
    return ('    %s.vm.provision "shell", name: "wazuh-agent", '
            'env: {"AGENT_NAME" => "%s"}, inline: WAZUH_AGENT_INSTALL\n' % (var, var))

def die(msg):
    sys.stderr.write("ABORTA (no se ha escrito nada): %s\n" % msg); sys.exit(1)

with open(PATH, encoding="utf-8") as f:
    original = f.read()
lines = original.splitlines(keepends=True)

# idempotencia
if "WAZUH_AGENT_INSTALL" in original:
    print("Ya aplicado (WAZUH_AGENT_INSTALL presente). Nada que hacer."); sys.exit(0)

# cierre de ADAPTER_TOOLCHAIN (delimitador a solas, exactamente 1)
close_idx = [i for i, ln in enumerate(lines) if ln.strip() == "ADAPTER_TOOLCHAIN_SHELL"]
if len(close_idx) != 1:
    die("esperaba 1 cierre 'ADAPTER_TOOLCHAIN_SHELL', encontre %d" % len(close_idx))

# cada define de agente (exactamente 1 c/u) + variable de bloque
define_at = {}
for name in AGENTS:
    pat = 'config.vm.define "%s"' % name
    idxs = [i for i, ln in enumerate(lines) if pat in ln]
    if len(idxs) != 1:
        die("esperaba 1 define de '%s', encontre %d" % (name, len(idxs)))
    m = re.search(r"do\s*\|\s*(\w+)\s*\|", lines[idxs[0]])
    if not m:
        die("no pude leer la variable de bloque de '%s': %s" % (name, lines[idxs[0]].rstrip()))
    define_at[name] = (idxs[0], m.group(1))

# inserciones (indice, texto); aplicar de atras a delante para no desplazar
inserts = [(close_idx[0] + 1, CONST_BLOCK)]
for name in AGENTS:
    idx, var = define_at[name]
    inserts.append((idx + 1, provision_line(var)))

for pos, text in sorted(inserts, key=lambda t: t[0], reverse=True):
    lines[pos:pos] = [text]

# backup del ORIGINAL (contenido intacto capturado antes de mutar) + escritura all-or-nothing
bak = PATH + ".bak-" + time.strftime("%Y%m%d-%H%M%S")
with open(bak, "w", encoding="utf-8") as f:
    f.write(original)
with open(PATH, "w", encoding="utf-8") as f:
    f.write("".join(lines))

print("OK. Backup en %s" % bak)
print("Insertado: constante WAZUH_AGENT_INSTALL + provision en %s" % ", ".join(AGENTS))
print("Recuerda: 1) cachear el .deb en provisioning/wazuh/  2) ruby -c Vagrantfile")