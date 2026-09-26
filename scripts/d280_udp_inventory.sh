#!/usr/bin/env bash
# DAY280 — inventario: servidores UDP escuchando, sincronización de hora y herramientas de carga.
h=$(hostname)
echo "== $h: sockets UDP en escucha"
sudo ss -ulnp
echo "== $h: servicios de DNS/hora activos"
systemctl list-units --type=service --state=running --no-pager | grep -Ei 'unbound|dnsmasq|bind|named|chrony|ntp|timesyncd|resolved' || echo "(ninguno)"
echo "== $h: estado de sincronización de hora"
timedatectl 2>/dev/null | grep -Ei 'synchronized|NTP service' || echo "(timedatectl no disponible)"
echo "== $h: herramientas"
for b in dig dnsperf iperf3 unbound dnsmasq chronyd hping3 nping; do printf '%-8s %s\n' "$b" "$(command -v $b || echo NO)"; done
