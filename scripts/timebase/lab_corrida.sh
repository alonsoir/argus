#!/usr/bin/env bash
# DAY297 Orquesta una corrida del lab desde el MAC (raiz del repo): relojes, parada, nada vivo, logs a cero, arranque
# production, espera ESTABLE, captura en eth2 del defender, trafico del client, fin de captura, parada y contabilidad.
# Para al primer fallo. Resultado en /vagrant/logs/lab/day297/NOMBRE/.
# Uso: bash scripts/timebase/lab_corrida.sh NOMBRE 'comando del client'
set -u
N=${1:?nombre de la corrida}
CLI=${2:?comando del client}
H=/vagrant/scripts/timebase/lab_corrida_defender.sh
paso() { echo; echo "=== [$(date +%T)] $*"; }
falla() { echo; echo "PARADA [$(date +%T)]: $*"; exit 1; }
paso "0 lab-clock-step"
make lab-clock-step || falla "lab-clock-step: relojes no alineados"
paso "1 pipeline-stop"
make pipeline-stop || falla "pipeline-stop"
paso "2 comprobar que no queda nada vivo"
vagrant ssh defender -c "bash $H vivos" || falla "quedan procesos del pipeline vivos"
paso "3 logs a cero"
vagrant ssh defender -c "bash $H truncar" || falla "truncar logs"
paso "4 pipeline-start PROFILE=production"
make pipeline-start PROFILE=production > "/tmp/${N}_start.txt" 2>&1 || { tail -n 20 "/tmp/${N}_start.txt"; falla "pipeline-start rc!=0"; }
tail -n 12 "/tmp/${N}_start.txt"
# Solo lineas de estado que EMPIEZAN por la cruz: el eco del comando de comprobacion de etcd contiene
# "echo '... STOPPED'" y no debe contar (falso positivo medido DAY297).
if grep -E '^[[:space:]]*❌.*STOPPED' "/tmp/${N}_start.txt"; then falla "algun componente STOPPED tras pipeline-start"; fi
paso "5 esperar ESTABLE"
vagrant ssh defender -c "bash /vagrant/day288_esperar_estable.sh" || falla "esperar_estable"
paso "6 captura en eth2"
vagrant ssh defender -c "bash $H cap_start $N" || falla "no arranca tcpdump"
paso "7 client: $CLI ; sleep 30"
if ! vagrant ssh client -c "$CLI; sleep 30"; then
  vagrant ssh defender -c "bash $H cap_stop $N"
  make pipeline-stop
  falla "el comando del client fallo"
fi
paso "8 fin de captura"
vagrant ssh defender -c "bash $H cap_stop $N" || falla "cap_stop"
paso "9 pipeline-stop"
make pipeline-stop || falla "pipeline-stop final"
paso "10 contabilidad y copia de resultados"
vagrant ssh defender -c "bash $H contar $N" || falla "contabilidad"
echo; echo "=== [$(date +%T)] HECHO: logs/lab/day297/$N/"
