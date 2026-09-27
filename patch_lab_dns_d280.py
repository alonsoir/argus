#!/usr/bin/env python3
"""DAY280 — añade al Vagrantfile raíz la provisión del lab DNS benigno:
  defender: unbound en 192.168.100.1:53 con zona local lab.argus (provisión 'lab-dns-resolver')
  client:   dnsperf (provisión 'lab-dns-load')
Idempotente (marcador LAB-DNS-D280), atómico (si un ancla no casa exactamente 1 vez, no escribe nada).
Uso: python3 patch_lab_dns_d280.py [--check] [ruta_Vagrantfile]
No hace commit."""
import sys, pathlib

MARK = "LAB-DNS-D280"

DEFENDER_BLOCK = r'''
    # ════════════════════════════════════════════════════════════════════════
    # Provisioning: resolver DNS BENIGNO del lab (LAB-DNS-D280)
    # ════════════════════════════════════════════════════════════════════════
    # unbound en 192.168.100.1:53 (misma víctima que el flood CICDDoS2019) con
    # zona local estática lab.argus (h1..h20 → 192.168.100.201..220). Respuestas
    # deterministas, sin depender de internet. Uso: medir el FP de la señal
    # DDoS del kernel con UDP legítimo de alta tasa (dnsperf desde el client).
    # NO toca la resolución del propio defender (/etc/resolv.conf intacto).
    # Verifica POR INVOCACIÓN (dig), no por test -f.
    defender.vm.provision "shell", name: "lab-dns-resolver", inline: <<-'LAB_DNS_RESOLVER'
      set -e
      export DEBIAN_FRONTEND=noninteractive
      echo "🧪 LAB-DNS-D280 — unbound en 192.168.100.1:53 (zona lab.argus)"
      RESOLV_SHA_BEFORE=$(sha256sum /etc/resolv.conf | awk '{print $1}')

      apt-get update -qq
      apt-get install -y unbound
      systemctl disable --now unbound-resolvconf.service 2>/dev/null || true

      CONF=/etc/unbound/unbound.conf.d/argus-lab.conf
      {
        printf '%s\n' '# LAB-DNS-D280 — generado por el Vagrantfile; no editar a mano'
        printf '%s\n' 'server:'
        printf '%s\n' '    interface: 127.0.0.1'
        printf '%s\n' '    interface: 192.168.100.1'
        printf '%s\n' '    ip-freebind: yes'
        printf '%s\n' '    access-control: 127.0.0.0/8 allow'
        printf '%s\n' '    access-control: 192.168.100.0/24 allow'
        printf '%s\n' '    num-threads: 1'
        printf '%s\n' '    local-zone: "lab.argus." static'
        for i in $(seq 1 20); do
          printf '    local-data: "h%d.lab.argus. 60 IN A 192.168.100.%d"\n' "$i" "$((200 + i))"
        done
      } > "$CONF"

      unbound-checkconf
      systemctl enable unbound
      systemctl restart unbound
      sleep 1

      echo "── verificando (por invocación) ──"
      GOT_LAN=$(dig @192.168.100.1 h1.lab.argus A +short +time=2 +tries=1)
      GOT_LO=$(dig @127.0.0.1 h20.lab.argus A +short +time=2 +tries=1)
      [ "$GOT_LAN" = "192.168.100.201" ] || { echo "❌ dig @192.168.100.1 h1 -> '$GOT_LAN'"; exit 1; }
      [ "$GOT_LO" = "192.168.100.220" ]  || { echo "❌ dig @127.0.0.1 h20 -> '$GOT_LO'"; exit 1; }
      RESOLV_SHA_AFTER=$(sha256sum /etc/resolv.conf | awk '{print $1}')
      [ "$RESOLV_SHA_BEFORE" = "$RESOLV_SHA_AFTER" ] || { echo "❌ /etc/resolv.conf cambió al instalar unbound"; exit 1; }
      ss -ulnp | grep -E '192\.168\.100\.1:53 ' >/dev/null || { echo "❌ unbound no escucha en 192.168.100.1:53"; exit 1; }
      echo "✅ LAB-DNS-D280 resolver OK (h1 -> $GOT_LAN, h20 -> $GOT_LO, resolv.conf intacto)"
    LAB_DNS_RESOLVER
'''

CLIENT_BLOCK = r'''
    # LAB-DNS-D280 — generador de carga DNS legítima (dnsperf) contra el resolver
    # del defender. Solo instala y verifica que el binario ejecuta; la prueba
    # contra 192.168.100.1 la hace el script de medida (el defender puede no estar arriba).
    client.vm.provision "shell", name: "lab-dns-load", inline: <<-'LAB_DNS_LOAD'
      set -e
      export DEBIAN_FRONTEND=noninteractive
      echo "🧪 LAB-DNS-D280 — dnsperf en el client"
      apt-get update -qq
      apt-get install -y --no-install-recommends dnsperf
      command -v dnsperf
      dnsperf -h 2>&1 | head -2 || true
      echo "✅ LAB-DNS-D280 dnsperf instalado"
    LAB_DNS_LOAD
'''

ANCHOR_DEF = "\n    NTP_SYNC\n"
ANCHOR_CLI = "\n        CLIENT\n\n  end  # End client VM"

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check = "--check" in sys.argv
    path = pathlib.Path(args[0] if args else "Vagrantfile")
    src = path.read_text()
    if MARK in src:
        print(f"✅ ya aplicado ({MARK} presente en {path}); nada que hacer")
        return 0
    for anchor in (ANCHOR_DEF, ANCHOR_CLI):
        n = src.count(anchor)
        if n != 1:
            print(f"❌ ancla encontrada {n} veces (se esperaba 1): {anchor!r}")
            print("   NO se ha escrito nada.")
            return 2
    out = src.replace(ANCHOR_DEF, ANCHOR_DEF + DEFENDER_BLOCK, 1)
    out = out.replace(ANCHOR_CLI, "\n        CLIENT\n" + CLIENT_BLOCK + "\n  end  # End client VM", 1)
    added = out.count("\n") - src.count("\n")
    if check:
        print(f"🔎 --check: aplicaría el parche (+{added} líneas) a {path}")
        return 0
    path.write_text(out)
    print(f"✅ parche aplicado a {path} (+{added} líneas). Siguiente: 'vagrant validate' en el Mac")
    return 0

if __name__ == "__main__":
    sys.exit(main())
