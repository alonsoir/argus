#!/usr/bin/env bash
# DAY301 v2: arranca el PIPELINE con PROFILE=production (etcd + binarios recien compilados), extrae las lineas
# [CONFIG*] del firewall y lo para. Mide tambien que JSON lee el agente. Mac, raiz del repo. Las esperas las hace el script.
set -u
DIA=day301
OUT=logs/lab/$DIA/arranque_b1.txt
LOG=/vagrant/logs/lab/firewall-agent.log
ETC=/etc/ml-defender/firewall-acl-agent/firewall.json
REPO=/vagrant/firewall-acl-agent/config/firewall.json
mkdir -p logs/lab/$DIA
paso() { echo "[$(date +%H:%M:%S)] $*"; }

paso "1/6 comprobando que no hay sesiones tmux en el defender"
ses=$(vagrant ssh -c "tmux ls 2>/dev/null | cut -d: -f1 | tr '\n' ' '" 2>/dev/null | grep -v '^\[argus\]' | tr -d '\r')
if [ -n "$(echo "$ses" | tr -d ' ')" ]; then
    paso "ABORTA: hay sesiones tmux abiertas: $ses (make pipeline-stop antes)"
    exit 1
fi

paso "2/6 midiendo el JSON que lee el agente"
vagrant ssh -c "ls -l $ETC; readlink -f $ETC; cmp $ETC $REPO && echo cmp_rc=0 || echo cmp_rc=\$?" 2>/dev/null \
    | grep -v '^\[argus\]' > "$OUT"
cat "$OUT"

N0=$(vagrant ssh -c "sudo touch $LOG; echo N0=\$(wc -l < $LOG)" 2>/dev/null | grep '^N0=' | cut -d= -f2 | tr -dc '0-9')
[ -n "$N0" ] || { paso "ABORTA: no pude contar las lineas de $LOG"; exit 1; }
paso "3/6 make pipeline-start PROFILE=production (log del firewall desde la linea $((N0 + 1)))"
make pipeline-start PROFILE=production > logs/lab/$DIA/arranque_b1_pipeline_start.txt 2>&1
paso "    pipeline-start rc=$?"

paso "4/6 esperando [CONFIG] recidivism en el log del firewall (maximo 60 s)"
visto=0
t0=$(date +%s)
while [ $(( $(date +%s) - t0 )) -lt 60 ]; do
    if vagrant ssh -c "tail -n +$((N0 + 1)) $LOG | grep -q 'CONFIG\] recidivism'" > /dev/null 2>&1; then
        visto=1
        break
    fi
    sleep 2
done
paso "    visto=$visto tras $(( $(date +%s) - t0 )) s"

paso "5/6 extrayendo lineas [CONFIG*], CRASH y FATAL"
vagrant ssh -c "tail -n +$((N0 + 1)) $LOG" 2>/dev/null | grep -E "\[CONFIG(-DEFAULT|-AVISO)?\]|CRASH|FATAL|ARGUS-CADENA|DRY-RUN\] /usr/sbin/iptables" >> "$OUT"

paso "6/6 make pipeline-stop"
make pipeline-stop > logs/lab/$DIA/arranque_b1_pipeline_stop.txt 2>&1
paso "    pipeline-stop rc=$?"
echo "linea_inicial=$N0 config_recidivism_visto=$visto lineas=$(wc -l < "$OUT")" >> "$OUT"
paso "resultado en $OUT"
