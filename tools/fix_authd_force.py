#!/usr/bin/env python3
"""
fix_authd_force.py — pone la politica <force> del authd del manager en "reemplazar SIEMPRE"
(re-enrollment de un agente re-imaginado sustituye al registro viejo, sin esperar 1h).
Idempotente, con backup. Uso:  sudo python3 fix_authd_force.py [/var/ossec/etc/ossec.conf]
"""
import sys, re, time, os
PATH = sys.argv[1] if len(sys.argv) > 1 else "/var/ossec/etc/ossec.conf"

FORCE = (
    "<force>\n"
    "      <enabled>yes</enabled>\n"
    "      <key_mismatch>yes</key_mismatch>\n"
    "      <disconnected_time enabled=\"no\">0</disconnected_time>\n"
    "      <after_registration_time>0</after_registration_time>\n"
    "    </force>"
)

with open(PATH, encoding="utf-8") as f:
    original = f.read()

if '<disconnected_time enabled="no">0</disconnected_time>' in original and \
        "<after_registration_time>0</after_registration_time>" in original:
    print("Ya aplicado (force = reemplazar siempre). Nada que hacer."); sys.exit(0)

if "<auth>" not in original:
    sys.stderr.write("ABORTA: no hay bloque <auth> en %s\n" % PATH); sys.exit(1)

new = original
if re.search(r"<force>.*?</force>", original, flags=re.DOTALL):
    new = re.sub(r"<force>.*?</force>", FORCE, original, count=1, flags=re.DOTALL)
    how = "reemplazado bloque <force> existente"
else:
    # insertar antes de </auth>
    new = re.sub(r"</auth>", "  " + FORCE + "\n  </auth>", original, count=1)
    how = "insertado bloque <force> nuevo"

if new == original:
    sys.stderr.write("ABORTA: no se pudo aplicar el cambio\n"); sys.exit(1)

bak = PATH + ".bak-" + time.strftime("%Y%m%d-%H%M%S")
with open(bak, "w", encoding="utf-8") as f:
    f.write(original)
with open(PATH, "w", encoding="utf-8") as f:
    f.write(new)
print("OK (%s). Backup en %s" % (how, bak))
print("Reinicia el manager:  sudo systemctl restart wazuh-manager")