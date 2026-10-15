#!/usr/bin/env bash
# DAY297 Ayudante en el DEFENDER de scripts/timebase/lab_corrida.sh (se invoca por vagrant ssh desde el Mac).
# Subcomandos: vivos | truncar | cap_start NOMBRE | cap_stop NOMBRE | contar NOMBRE
set -u
DIA=${DIA:-day297}  # [DAY298-DIA]
[[ "$DIA" =~ ^day[0-9]{3}$ ]] || { echo "DIA invalido: '$DIA' (formato dayNNN, p. ej. day298)"; exit 2; }
D=/vagrant/logs/lab/$DIA
PAT='/(sniffer|ml-detector|firewall-acl-agent)( |$)'
FILTRO=${FILTRO:-src host 192.168.100.50 or src host 192.168.100.51 or src host 192.168.100.61}  # [DAY298-FILTRO] cambiable desde el entorno
case "${1:-}" in
  vivos)
    n=$(pgrep -c -f "$PAT" || true)
    echo "vivos=$n"
    pgrep -a -f "$PAT" || true
    [ "$n" = "0" ]
    ;;
  truncar)
    sudo truncate -s 0 /vagrant/logs/lab/sniffer.log /vagrant/logs/lab/ml-detector.log /vagrant/logs/lab/firewall-agent.log
    echo "logs a cero"
    ;;
  cap_start)
    N=${2:?nombre}
    sudo rm -f "/tmp/$N.pcap" "/tmp/$N.tcpdump.txt"
    sudo setsid nohup tcpdump -i eth2 -n -s 96 -w "/tmp/$N.pcap" "$FILTRO" > "/tmp/$N.tcpdump.txt" 2>&1 < /dev/null &
    sleep 3
    if pgrep -f "tcpdump -i eth2 .*/tmp/$N.pcap" > /dev/null; then echo "tcpdump en marcha: /tmp/$N.pcap"; else cat "/tmp/$N.tcpdump.txt"; exit 1; fi
    ;;
  cap_stop)
    N=${2:?nombre}
    sudo pkill -INT -f "tcpdump -i eth2 .*/tmp/$N.pcap" || true
    for _ in 1 2 3 4 5 6 7 8 9 10; do pgrep -f "tcpdump -i eth2 .*/tmp/$N.pcap" > /dev/null || break; sleep 1; done
    if pgrep -f "tcpdump -i eth2 .*/tmp/$N.pcap" > /dev/null; then echo "tcpdump no termina"; exit 1; fi
    cat "/tmp/$N.tcpdump.txt"
    ;;
  contar)
    N=${2:?nombre}
    mkdir -p "$D/$N"
    sudo cp "/tmp/$N.pcap" "/tmp/$N.tcpdump.txt" "$D/$N/"
    cp /vagrant/logs/lab/firewall-agent.log "$D/$N/firewall-agent.log"
    sudo bash /vagrant/scripts/timebase/a1_contabilidad.sh "/tmp/$N.pcap" > "$D/$N/contabilidad.txt" 2>&1
    cat "$D/$N/tcpdump.txt" 2>/dev/null || cat "$D/$N/$N.tcpdump.txt"
    cat "$D/$N/contabilidad.txt"
    ;;
  *)
    echo "uso: $0 vivos | truncar | cap_start NOMBRE | cap_stop NOMBRE | contar NOMBRE"
    exit 2
    ;;
esac
