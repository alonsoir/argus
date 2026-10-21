#!/usr/bin/env bash
# DAY298 Corrida de ARRANQUE EN FRIO desde el MAC (raiz del repo). A diferencia de lab_corrida.sh, la captura
# en eth2 (filtro: todo lo que va a .1) y el volcado del dataset del ml-detector se activan ANTES de
# pipeline-start, y opcionalmente se lanza trafico del client en segundo plano antes del arranque.
# Para al primer fallo. Resultado en /vagrant/logs/lab/$DIA/NOMBRE/ (DIA del entorno, por defecto day298).
# Uso: bash scripts/timebase/lab_frio.sh NOMBRE ['comando del client en segundo plano'] [segundos_tras_estable]
set -u
N=${1:?nombre de la corrida}
CLI=${2:-}
POST=${3:-120}
DIA=${DIA:-day298}
[[ "$DIA" =~ ^day[0-9]{3}$ ]] || { echo "DIA invalido: '$DIA' (formato dayNNN, p. ej. day298)"; exit 2; }
[[ "$POST" =~ ^[0-9]+$ ]] || { echo "segundos_tras_estable invalido: '$POST'"; exit 2; }
H=/vagrant/scripts/timebase/lab_corrida_defender.sh
D=/vagrant/logs/lab/$DIA/$N
FIL='dst host 192.168.100.1'
paso() { echo; echo "=== [$(date +%T)] $*"; }
falla() { echo; echo "PARADA [$(date +%T)]: $*"; vagrant ssh defender -c "python3 /vagrant/day289_dataset_writer.py off"; exit 1; }
marca() { vagrant ssh defender -c "mkdir -p $D && echo \"$1 \$(date +%s.%N)\" >> $D/tiempos.txt"; }
paso "0 lab-clock-step"
make lab-clock-step || falla "lab-clock-step: relojes no alineados"
paso "1 pipeline-stop"
make pipeline-stop || falla "pipeline-stop"
paso "2 comprobar que no queda nada vivo"
vagrant ssh defender -c "DIA=$DIA bash $H vivos" || falla "quedan procesos del pipeline vivos"
paso "3 logs a cero"
vagrant ssh defender -c "DIA=$DIA bash $H truncar" || falla "truncar logs"
paso "4 volcado del dataset del ml-detector: ON"
vagrant ssh defender -c "python3 /vagrant/day289_dataset_writer.py on" || falla "dataset writer on"
paso "5 captura en eth2 ($FIL)"
vagrant ssh defender -c "DIA=$DIA FILTRO='$FIL' bash $H cap_start $N" || falla "no arranca tcpdump"
if [ -n "$CLI" ]; then
  paso "6 client en segundo plano ANTES del arranque: $CLI"
  # [DAY298-SETSID] setsid: sesion propia, sin la terminal de vagrant ssh (si no, SIGHUP al cerrar la sesion).
  # [DAY299-RETRASO] RETRASO_S opcional: sleep antes del trafico; la comprobacion acepta ese sleep vivo
  CLI_EF="$CLI"; PAT='^(sudo )?tcpreplay'
  if [ -n "${RETRASO_S:-}" ]; then
    case "$RETRASO_S" in ''|*[!0-9]*) falla "RETRASO_S debe ser un entero de segundos (es '$RETRASO_S')";; esac
    CLI_EF="sleep $RETRASO_S; $CLI"; PAT="^(sudo )?tcpreplay|^sleep $RETRASO_S\$"
    echo "RETRASO_S=$RETRASO_S: el trafico del client empieza $RETRASO_S s despues de este paso"
  fi
  vagrant ssh client -c "setsid nohup bash -c '$CLI_EF' > /tmp/$N.client.txt 2>&1 < /dev/null & sleep 2; pgrep -af '$PAT'" || falla "el trafico del client no esta en marcha (no hay tcpreplay ni sleep de RETRASO_S vivo)"
  sleep 5
fi
paso "7 pipeline-start PROFILE=production"
marca inicio_pipeline_start
make pipeline-start PROFILE=production > "/tmp/${N}_start.txt" 2>&1 || { tail -n 20 "/tmp/${N}_start.txt"; falla "pipeline-start rc!=0"; }
marca fin_pipeline_start
tail -n 12 "/tmp/${N}_start.txt"
if grep -E '^[[:space:]]*❌.*STOPPED' "/tmp/${N}_start.txt"; then falla "algun componente STOPPED tras pipeline-start"; fi
paso "8 esperar ESTABLE"
vagrant ssh defender -c "bash /vagrant/day288_esperar_estable.sh" || falla "esperar_estable"
marca estable
paso "9 $POST s tras ESTABLE"
sleep "$POST"
paso "10 fin de captura"
vagrant ssh defender -c "DIA=$DIA bash $H cap_stop $N" || falla "cap_stop"
paso "11 pipeline-stop"
make pipeline-stop || falla "pipeline-stop final"
paso "12 volcado del dataset: OFF y copia"
vagrant ssh defender -c "python3 /vagrant/day289_dataset_writer.py off" || falla "dataset writer off"
vagrant ssh defender -c "f=\$(ls -t /vagrant/logs/lab/ddos_dataset/ddos_dataset_*.csv | head -n 1); cp \"\$f\" $D/ && echo \"dataset: \$f\"" || falla "copia del dataset"
paso "13 contabilidad y copia de resultados"
vagrant ssh defender -c "DIA=$DIA bash $H contar $N" || falla "contabilidad"
if [ -n "$CLI" ]; then vagrant ssh client -c "cat /tmp/$N.client.txt"; fi
echo; echo "=== [$(date +%T)] HECHO: logs/lab/$DIA/$N/"
