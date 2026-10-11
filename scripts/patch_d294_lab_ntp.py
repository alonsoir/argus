#!/usr/bin/env python3
"""DAY294 — patcher atómico (todo o nada) [ARGUS-LAB-NTP-D294] sobre el Vagrantfile raíz (DEBT-LAB-VM-NTP-001).
Medido DAY294: el client NO tiene salida a Internet (ruta por defecto via 192.168.100.1; diseño del lab) y pierde sus
fuentes NTP -> su reloj deriva ~1,6 ms/s (los ~14 s de DAY293). Arreglo:
 - defender (provisioner ntp-sync, run always): chrony sirve la hora a 192.168.100.0/24, local stratum 10,
   makestep 1 -1 (salto si desfase > 1 s, p. ej. tras suspender el portátil). Reinicia chrony solo si cambia algo.
 - client (provisioner NUEVO client-ntp, run always, tras client-setup): server 192.168.100.1 iburst, pool comentado,
   makestep 1 -1, waitsync.
Uso: --check | --apply. Idempotente por la marca. No commitea."""
import sys
from pathlib import Path

MARK = "[ARGUS-LAB-NTP-D294]"
VF = Path("/vagrant/Vagrantfile")


def fail(m):
    print("ABORTA:", m); sys.exit(1)


def before(t, anchor, block, name):
    c = t.count(anchor)
    if c != 1:
        fail("%s: ancla encontrada %d veces" % (name, c))
    return t.replace(anchor, block + anchor)


DEF_ANCHOR = "      # Forzar sync inmediato (especialmente útil tras vagrant up en frío)\n"
DEF_BLOCK = (
    "      # [ARGUS-LAB-NTP-D294] el defender sirve la hora a la red interna (el client no tiene salida a Internet)\n"
    "      # y salta el reloj siempre que el desfase pase de 1 s (suspensiones del portátil). Idempotente.\n"
    "      CHRONY_CONF=/etc/chrony/chrony.conf\n"
    "      CHRONY_CAMBIO=0\n"
    "      if grep -q '^makestep 1 3$' \"$CHRONY_CONF\"; then\n"
    "        sed -i 's/^makestep 1 3$/makestep 1 -1/' \"$CHRONY_CONF\"; CHRONY_CAMBIO=1\n"
    "      fi\n"
    "      if ! grep -q '^allow 192.168.100.0/24' \"$CHRONY_CONF\"; then\n"
    "        echo 'allow 192.168.100.0/24' >> \"$CHRONY_CONF\"; CHRONY_CAMBIO=1\n"
    "      fi\n"
    "      if ! grep -q '^local stratum 10' \"$CHRONY_CONF\"; then\n"
    "        echo 'local stratum 10' >> \"$CHRONY_CONF\"; CHRONY_CAMBIO=1\n"
    "      fi\n"
    "      if [ \"$CHRONY_CAMBIO\" = \"1\" ]; then systemctl restart chrony; sleep 3; echo \"⏱️  chrony reconfigurado (servidor de la red interna)\"; fi\n"
    "\n"
)

CLI_ANCHOR = "  end  # End client VM\n"
CLI_BLOCK = (
    "    # [ARGUS-LAB-NTP-D294] el client toma la hora del defender, su pasarela (el client no tiene salida a Internet\n"
    "    # tras el cambio de ruta de client-setup). makestep 1 -1: salta el reloj siempre que el desfase pase de 1 s.\n"
    "    client.vm.provision \"shell\", name: \"client-ntp\", run: \"always\", inline: <<-'CLIENT_NTP'\n"
    "      CHRONY_CONF=/etc/chrony/chrony.conf\n"
    "      sed -i 's/^pool /#pool /' \"$CHRONY_CONF\"\n"
    "      sed -i 's/^makestep 1 3$/makestep 1 -1/' \"$CHRONY_CONF\"\n"
    "      grep -q '^server 192.168.100.1 iburst' \"$CHRONY_CONF\" || echo 'server 192.168.100.1 iburst' >> \"$CHRONY_CONF\"\n"
    "      systemctl restart chrony\n"
    "      chronyc waitsync 30 0.1 0 1 || echo \"⚠️  client-ntp: sin sincronizar con 192.168.100.1 en 30 s\"\n"
    "      chronyc tracking | grep -E \"Reference ID|System time|Leap status\" || true\n"
    "      chronyc -n sources || true\n"
    "    CLIENT_NTP\n"
    "\n"
)


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        fail("uso: --check | --apply")
    t = VF.read_text(encoding="utf-8")
    if MARK in t:
        print("YA APLICADO (marca %s presente). Nada que hacer." % MARK); return
    n = before(t, DEF_ANCHOR, DEF_BLOCK, "defender ntp-sync")
    n = before(n, CLI_ANCHOR, CLI_BLOCK, "client fin de VM")
    if n.count(MARK) != 2:
        fail("marca esperada 2 veces, hay %d" % n.count(MARK))
    if sys.argv[1] == "--check":
        print("CHECK OK: anclas únicas; se insertarían %d líneas." % (n.count("\n") - t.count("\n"))); return
    tmp = VF.with_name(VF.name + ".d294tmp")
    tmp.write_text(n, encoding="utf-8")
    tmp.replace(VF)
    print("APLICADO %s: +%d líneas en %s" % (MARK, n.count("\n") - t.count("\n"), VF))


if __name__ == "__main__":
    main()
