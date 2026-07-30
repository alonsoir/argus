#!/usr/bin/env python3
"""
add_authd_force_provision.py — inserta un provision `authd-force` en el bloque wazuh
del Vagrantfile raíz, JUSTO DESPUÉS del provision `adapter-toolchain` del manager.

El provision corre tools/fix_authd_force.py (force = reemplazar-siempre) + reinicia el
manager, y verifica fail-loud UNA cosa determinista: que el marcador de <force> quedó en
el ossec.conf. La liveness de authd NO se sondea aquí (wazuh-control status devuelve !=0
por daemons opcionales caídos → falso negativo); que authd levanta con esta config lo
prueba E2E la prueba de enroll (destroy&up de un agente). Cierra
DEBT-WAZUH-AUTHD-FORCE-NOT-PROVISIONED-001.

Anclado / idempotente / all-or-nothing / backup. Uso: python3 add_authd_force_provision.py [Vagrantfile]
"""
import sys, time

PATH = sys.argv[1] if len(sys.argv) > 1 else "Vagrantfile"

ANCHOR = '    wazuh.vm.provision "shell", name: "adapter-toolchain", inline: ADAPTER_TOOLCHAIN\n'

BLOCK = (
    '\n'
    '    wazuh.vm.provision "shell", name: "authd-force", inline: <<-\'AUTHD_FORCE_SHELL\'\n'
    '      set -eu\n'
    '      echo "=== authd-force: force=reemplazar-siempre (DEBT-WAZUH-AUTHD-FORCE-NOT-PROVISIONED-001) ==="\n'
    '      OSSEC_CONF=/var/ossec/etc/ossec.conf\n'
    '      [ -f "$OSSEC_CONF" ] || { echo "ERROR: no existe $OSSEC_CONF (install-wazuh no corrio?)"; exit 1; }\n'
    '      command -v python3 >/dev/null 2>&1 || apt-get install -y python3\n'
    '      python3 /vagrant/tools/fix_authd_force.py\n'
    '      systemctl restart wazuh-manager\n'
    '      # Verificacion determinista: el marcador de force quedo en la config. La liveness de\n'
    '      # authd NO se sondea (wazuh-control status sale !=0 por daemons opcionales -> falso\n'
    '      # negativo); el enroll de un agente (destroy&up) es la prueba E2E de que authd levanta.\n'
    '      grep -q \'<disconnected_time enabled="no">0</disconnected_time>\' "$OSSEC_CONF" \\\n'
    '        || { echo "ERROR: <force> no quedo en reemplazar-siempre en ossec.conf"; exit 1; }\n'
    '      echo "=== authd-force OK (force codificada; el enroll de zeek lo prueba E2E) ==="\n'
    '    AUTHD_FORCE_SHELL\n'
)

MARKER = 'name: "authd-force"'

with open(PATH, encoding="utf-8") as f:
    original = f.read()

if MARKER in original:
    print("Ya aplicado (existe un provision authd-force). Nada que hacer.")
    sys.exit(0)

n = original.count(ANCHOR)
if n != 1:
    sys.stderr.write(
        "ABORTA: el ancla adapter-toolchain del bloque wazuh aparece %d veces "
        "(esperaba 1). No toco nada.\n" % n
    )
    sys.exit(1)

new = original.replace(ANCHOR, ANCHOR + BLOCK, 1)
if new == original:
    sys.stderr.write("ABORTA: no se pudo insertar el bloque.\n")
    sys.exit(1)

bak = PATH + ".bak-" + time.strftime("%Y%m%d-%H%M%S")
with open(bak, "w", encoding="utf-8") as f:
    f.write(original)
with open(PATH, "w", encoding="utf-8") as f:
    f.write(new)

print("OK: provision authd-force insertado tras adapter-toolchain del bloque wazuh.")
print("Backup en %s" % bak)
print("Verifica:  ruby -c %s  &&  vagrant validate" % PATH)