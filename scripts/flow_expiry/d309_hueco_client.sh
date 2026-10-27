#!/usr/bin/env bash
# DAY309 corrida "hueco" (CLIENT): mide lo que cambia la caducidad de flujos (idle_timeout_s 300) en ddos_v2.
# Base .51 a 10 pps durante 580 s. Ataque NTP desde .50 a 60 pps, 60 s, a los 60 s; 330 s de silencio del atacante;
# el MISMO tramo de tuplas otra vez a los 450 s. Sin caducidad (main) los flujos del ataque 2 heredan los del 1;
# con ella (rama) han caducado y empiezan de cero. Mismo recorte y reescritura de MACs que d302_mitigacion_client.sh
# ([LAB-PCAP-MAC-D302]: sin ello el kernel del defender descarta las tramas antes de netfilter).
# Uso (lo lanza d309_hueco_e2e.sh): bash /vagrant/logs/lab/day309/tools/d309_hueco_client.sh
set -eu
trap 'echo "PARADA linea $LINENO"' ERR
BASE=/vagrant/datasets/lab/benign_dns_ntp_17k_disjunto_src51.pcap
A50=/vagrant/datasets/lab/ntp_reflex_63k_disjunto_lab.pcap
SHA_BASE=5badabb15c30d019b0cb98c3128e44b4c9aaf9d6f456932c81050466b823b0ea
SHA_A50=f3732ea337b8d50e0e67fe9a09ce234065304328c5c1188ab1e5f32b9d2272d0
T=/tmp/d309h
mkdir -p "$T"
echo "$SHA_BASE  $BASE" > "$T/sha.txt"
echo "$SHA_A50  $A50" >> "$T/sha.txt"
sha256sum -c "$T/sha.txt" || { echo "PARADA sha256 de los pcaps distinto del MANIFEST"; exit 1; }
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
cortar "$BASE" "$T/base.pcap" 0 5800
cortar "$A50" "$T/a50.pcap" 0 3600
T0=$(date +%s.%N)
hasta() { python3 -c "import time; time.sleep(max(0.0, $T0 + $1 - time.time()))"; }
ataque() {
  echo "inicio_ataque$1 $(date +%s.%N)"
  sudo tcpreplay -i eth1 --pps=60 "$T/a50.pcap" > "/tmp/d309h_a50_$1.txt" 2>&1
  echo "fin_ataque$1 $(date +%s.%N)"
}
echo "inicio_base $T0"
sudo tcpreplay -i eth1 --pps=10 "$T/base.pcap" > /tmp/d309h_base.txt 2>&1 &
PB=$!
hasta 60
ataque 1
hasta 450
ataque 2
wait "$PB"
echo "fin_base $(date +%s.%N)"
for f in /tmp/d309h_base.txt /tmp/d309h_a50_1.txt /tmp/d309h_a50_2.txt; do
  echo "--- $f"
  grep -E 'Actual|Failed' "$f" || true
done
