#!/usr/bin/env bash
# DAY302 E2E de la mitigacion ddos_v2 (client). Base .51 a 10 pps durante 450 s. Ataque 1 a los 60 s y ataque 2 a
# los 240 s, 60 s cada uno: NTP desde .50 a 60 pps y desde .61 (protegido) a 30 pps. Cada ataque con tuplas
# DISJUNTAS (tramos distintos del pcap): la tabla de flujos del sniffer no caduca (DEBT-SNIFFER-FLOW-EXPIRY-001).
# [LAB-PCAP-MAC-D302] medido DAY302: los pcaps del lab llevan MACs ajenas -> el kernel del defender descarta las
# tramas (PACKET_OTHERHOST) antes de netfilter. Al cortar, se reescriben MAC destino (la de 192.168.100.1 en la
# tabla de vecinos) y MAC origen (eth1 del client). Nada escrito a mano.
set -eu
trap 'echo "PARADA linea $LINENO"' ERR
BASE=/vagrant/datasets/lab/benign_dns_ntp_17k_disjunto_src51.pcap
A50=/vagrant/datasets/lab/ntp_reflex_63k_disjunto_lab.pcap
A61=/vagrant/datasets/lab/ntp_reflex_10k_lab_src61.pcap
T=/tmp/d302m
mkdir -p "$T"
DMAC=$(ip neigh show 192.168.100.1 dev eth1 | awk '{for (i = 1; i < NF; i++) if ($i == "lladdr") print $(i + 1)}')
if [ -z "$DMAC" ]; then
  ping -c 1 -W 1 192.168.100.1 > /dev/null 2>&1 || true
  DMAC=$(ip neigh show 192.168.100.1 dev eth1 | awk '{for (i = 1; i < NF; i++) if ($i == "lladdr") print $(i + 1)}')
fi
[ -n "$DMAC" ] || { echo "PARADA sin MAC de 192.168.100.1 en la tabla de vecinos de eth1"; exit 1; }
SMAC=$(cat /sys/class/net/eth1/address)
echo "mac destino=$DMAC origen=$SMAC"
export DMAC SMAC
cortar() {
python3 - "$1" "$2" "$3" "$4" <<'PYEOF'
import os, struct, sys
src, dst, skip, take = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
dmac = bytes.fromhex(os.environ["DMAC"].replace(":", ""))
smac = bytes.fromhex(os.environ["SMAC"].replace(":", ""))
f = open(src, "rb")
gh = f.read(24)
magic = struct.unpack("<I", gh[:4])[0]
if magic in (0xA1B2C3D4, 0xA1B23C4D):
    e = "<"
elif magic in (0xD4C3B2A1, 0x4D3CB2A1):
    e = ">"
else:
    sys.exit(f"{src}: no es pcap clasico (magic {magic:#x})")
linktype = struct.unpack(e + "I", gh[20:24])[0]
if linktype != 1:
    sys.exit(f"{src}: linktype {linktype} no es Ethernet (1)")
o = open(dst, "wb")
o.write(gh)
n = i = 0
while n < take:
    h = f.read(16)
    if len(h) < 16:
        break
    incl = struct.unpack(e + "I", h[8:12])[0]
    data = f.read(incl)
    if i >= skip:
        if len(data) < 12:
            sys.exit(f"{src}: trama {i} de {len(data)} bytes, sin cabecera Ethernet")
        o.write(h + dmac + smac + data[12:])
        n += 1
    i += 1
o.close()
print(f"tramo {dst} {n} paquetes desde {skip} (MACs reescritas)")
if n < take:
    sys.exit(f"faltan paquetes en {src}: {n} < {take}")
PYEOF
}
cortar "$BASE" "$T/base.pcap" 0 4500
cortar "$A50" "$T/a50_1.pcap" 0 3600
cortar "$A50" "$T/a50_2.pcap" 3600 3600
cortar "$A61" "$T/a61_1.pcap" 0 1800
cortar "$A61" "$T/a61_2.pcap" 1800 1800
T0=$(date +%s.%N)
hasta() { python3 -c "import time; time.sleep(max(0.0, $T0 + $1 - time.time()))"; }
ataque() {
  echo "inicio_ataque$1 $(date +%s.%N)"
  sudo tcpreplay -i eth1 --pps=30 "$T/a61_$1.pcap" > "/tmp/d302m_a61_$1.txt" 2>&1 &
  local p=$!
  sudo tcpreplay -i eth1 --pps=60 "$T/a50_$1.pcap" > "/tmp/d302m_a50_$1.txt" 2>&1
  wait "$p"
  echo "fin_ataque$1 $(date +%s.%N)"
}
echo "inicio_base $T0"
sudo tcpreplay -i eth1 --pps=10 "$T/base.pcap" > /tmp/d302m_base.txt 2>&1 &
PB=$!
hasta 60
ataque 1
hasta 240
ataque 2
wait "$PB"
echo "fin_base $(date +%s.%N)"
for f in /tmp/d302m_base.txt /tmp/d302m_a50_1.txt /tmp/d302m_a61_1.txt /tmp/d302m_a50_2.txt /tmp/d302m_a61_2.txt; do
  echo "--- $f"
  grep -E 'Actual|Failed' "$f" || true
done
