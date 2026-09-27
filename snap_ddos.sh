#!/usr/bin/env bash
# snap_ddos.sh Foto de contadores para medir deltas ANTES/DESPUES. Uso: sudo bash /vagrant/snap_ddos.sh > ~/fichero.txt
date +%s.%N
ip -s link show eth1
ip -s link show eth2
bpftool -j map dump name stats
bpftool -j map dump name ddos_victims
