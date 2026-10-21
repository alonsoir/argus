#!/usr/bin/env bash
# DAY303 [ARGUS-ESTABLE-LAB-D303]: paso "esperar ESTABLE" de los E2E del lab, con fondo CONTROLADO.
# Medido DAY303 (K13-K15): day288_esperar_estable.sh exige >=10 sondeos del lector del kernel en 30 s
# (ddos_windows.csv), y el lector solo escribe claves con paquetes en la ventana. Con las 5 VMs (make up) el
# fondo lo daban Wazuh/Zeek sin que nadie lo supiera; en EMECAS (3 VMs) el lab esta mudo: 6 filas en 120 s.
# Ahora el fondo es explicito: ping 2 pps client -> 192.168.100.1 SOLO durante la espera (victima {.1, ICMP},
# no la del ataque {.1, UDP}; a 2 pps no hay presion). El criterio de day288 no se toca.
# K15: con el ping, sondeos_30s=28 max_window_ms=1005 -> ESTABLE a la primera.
# Se para el ping al salir (tambien por trap) y se dejan 3 s para que su ultima ventana quede atras.
# Uso (Mac, raiz del repo; lo llaman d300_reinicio_e2e.sh, d300_protegidos_e2e.sh y d302_mitigacion_e2e.sh)
set -u
PID=/tmp/d303_fondo_ping.pid
parar() {
  vagrant ssh client -c "if [ -f $PID ]; then kill \$(cat $PID) 2>/dev/null; rm -f $PID; fi; sleep 1; if pgrep -x ping > /dev/null; then echo '[ESTABLE-LAB] AVISO: queda un ping vivo en el client'; else echo '[ESTABLE-LAB] fondo parado'; fi" 2>/dev/null | tr -d '\r' | grep -v '^\[argus\]'
}
trap parar EXIT
vagrant ssh client -c "setsid bash -c 'ping -q -i 0.5 -I eth1 192.168.100.1 > /dev/null 2>&1 & echo \$! > $PID' < /dev/null > /dev/null 2>&1; sleep 1; kill -0 \$(cat $PID)" > /dev/null 2>&1 \
  || { echo "[ESTABLE-LAB] FALLA: no arranca el ping de fondo en el client"; exit 1; }
echo "[ESTABLE-LAB] fondo: ping 2 pps client -> 192.168.100.1 (ICMP, victima {.1,1}; el ataque va a {.1,17})"
vagrant ssh defender -c "bash /vagrant/day288_esperar_estable.sh"
rc=$?
parar
trap - EXIT
sleep 3
exit "$rc"
