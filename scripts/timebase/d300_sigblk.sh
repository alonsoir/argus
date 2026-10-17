#!/usr/bin/env bash
# DAY300 [SIGWAIT-D300]: los hilos del sniffer deben bloquear SIGHUP(1), SIGINT(2) y SIGTERM(15): mascara
# 0x4003 en SigBlk. Excepcion: el hilo principal (tid == pid) esta dentro de sigwait y el kernel le
# desbloquea temporalmente esas senales mientras espera (real_blocked); para el se comprueba que duerme en
# do_sigtimedwait.
set -u
export LC_ALL=C
pid=$(pgrep -x sniffer | head -n 1)
if [ -z "$pid" ]; then echo "sniffer no esta en marcha"; exit 1; fi
total=0; mal=0
for d in /proc/"$pid"/task/*; do
  tid=${d##*/}
  total=$((total + 1))
  blk=$(sudo awk '/^SigBlk:/{print $2}' "$d/status")
  nom=$(sudo awk '/^Name:/{print $2}' "$d/status")
  if [ "$tid" = "$pid" ]; then
    wch=$(sudo cat "$d/wchan")
    echo "hilo principal $tid ($nom): SigBlk=$blk wchan=$wch"
    if [ "$wch" != "do_sigtimedwait" ]; then mal=$((mal + 1)); echo "  ^ el hilo principal NO esta en sigwait"; fi
    continue
  fi
  if (( (16#$blk & 0x4003) != 0x4003 )); then
    mal=$((mal + 1)); echo "SIN BLOQUEO: $d ($nom) SigBlk=$blk"
  fi
done
echo "pid=$pid hilos=$total incidencias=$mal"
