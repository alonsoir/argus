#!/usr/bin/env bash
# DAY309 corrida "hueco" (MAC): antes/despues de la caducidad de flujos en ddos_v2. Esqueleto de
# d302_mitigacion_e2e.sh SIN tocar el firewall (queda de serie: dry_run, sombra). Conmutador SOLO durante la prueba:
# ddos_dataset_writer.enabled=true en ml_detector_config.json (con day289_dataset_writer.py). trap: restaura el JSON
# byte a byte (cmp), para el pipeline y realinea relojes. Vive en logs/lab/day309/tools (ignorado por git) para
# poder correr igual con main (57d1d400) y con la rama.
# Uso (raiz del repo, Mac): bash logs/lab/day309/tools/d309_hueco_e2e.sh NOMBRE > /tmp/d309_NOMBRE.txt 2>&1
set -u
N=${1:?nombre de la corrida}
export DIA=day309
H=/vagrant/scripts/timebase/lab_corrida_defender.sh
D=/vagrant/logs/lab/$DIA/$N
DM=logs/lab/$DIA/$N
TOOLS=logs/lab/$DIA/tools
CSV=/var/lib/argus/sniffer/ddos_victim_estado.csv
CLI=/tmp/$N.client.txt
FIL='dst host 192.168.100.1'
JSON=ml-detector/config/ml_detector_config.json
BAK=/tmp/$N.ml_detector_config.json.orig
DS=/vagrant/logs/lab/ddos_dataset
JSON_TOCADO=0
RESTAURADO=0
paso()  { echo; echo "=== [$(date +%T)] $*"; }
falla() { echo; echo "PARADA [$(date +%T)]: $*"; exit 1; }
marca() { vagrant ssh defender -c "mkdir -p $D && echo \"$1 \$(date +%s.%N)\" >> $D/tiempos.txt" > /dev/null 2>&1; }
restaurar() {
  [ "$RESTAURADO" = 1 ] && return 0
  RESTAURADO=1
  echo; echo "=== [$(date +%T)] TRAP: restaurando el lab"
  make pipeline-stop > "/tmp/${N}_stop_trap.txt" 2>&1
  echo "    pipeline-stop rc=$?"
  if [ "$JSON_TOCADO" = 1 ] && [ -f "$BAK" ]; then
    cp "$BAK" "$JSON"
    if cmp -s "$BAK" "$JSON"; then echo "    JSON restaurado (cmp 0)"; else echo "    ERROR: el JSON NO coincide con $BAK"; fi
  fi
  make lab-clock-step > "/tmp/${N}_clock_trap.txt" 2>&1
  echo "    lab-clock-step rc=$?"
}
trap restaurar EXIT
trap 'exit 130' INT TERM

paso "0 comprobaciones previas"
[ -f "$TOOLS/d309_hueco_client.sh" ] && [ -f "$TOOLS/d309_hueco_analisis.py" ] || falla "faltan las herramientas en $TOOLS"
[ -e "$DM" ] && falla "$DM ya existe: elegir otro nombre (no se mezclan corridas)"
echo "    rama/commit: $(git rev-parse --short HEAD) $(git branch --show-current)"
git diff --quiet -- "$JSON" || falla "$JSON tiene cambios sin commit: no se toca"
make lab-clock-step || falla "relojes no alineados"
make lab-e2e-prep || falla "lab-e2e-prep"
paso "1 pipeline-stop y comprobacion"
make pipeline-stop > "/tmp/${N}_stop0.txt" 2>&1 || falla "pipeline-stop"
vagrant ssh defender -c "DIA=$DIA bash $H vivos" || falla "quedan procesos vivos"
paso "2 escritor del dataset encendido SOLO para la prueba (copia exacta en $BAK)"
rm -f "$BAK"
cp "$JSON" "$BAK" || falla "copia del JSON"
JSON_TOCADO=1
vagrant ssh defender -c "python3 /vagrant/day289_dataset_writer.py on" || falla "no se pudo encender el escritor"
vagrant ssh defender -c "python3 /vagrant/day289_dataset_writer.py estado" | grep -q "enabled = true" || falla "el escritor no quedo encendido"
paso "3 logs a cero, CSV de estado borrado, ficheros del dataset previos"
vagrant ssh defender -c "DIA=$DIA bash $H truncar" || falla "truncar"
vagrant ssh defender -c "sudo rm -f $CSV && mkdir -p $D $DS && : > $D/tiempos.txt && ls $DS > $D/dataset_previos.txt" || falla "preparar"
paso "4 pipeline-start PROFILE=production"
make pipeline-start PROFILE=production > "/tmp/${N}_start.txt" 2>&1 || { tail -n 20 "/tmp/${N}_start.txt"; falla "pipeline-start rc!=0"; }
if grep -E '^[[:space:]]*❌.*STOPPED' "/tmp/${N}_start.txt"; then falla "algun componente STOPPED"; fi
paso "5 esperar ESTABLE"
bash scripts/timebase/d303_esperar_estable_lab.sh || falla "esperar_estable"
marca estable
paso "6 captura en eth2 ($FIL)"
vagrant ssh defender -c "DIA=$DIA FILTRO='$FIL' bash $H cap_start $N" || falla "no arranca tcpdump"
paso "7 client en segundo plano (base 580 s; ataque a los 60 s y el MISMO tramo a los 450 s, 60 s cada uno)"
vagrant ssh client -c "setsid nohup bash /vagrant/$TOOLS/d309_hueco_client.sh > $CLI 2>&1 < /dev/null & sleep 15; pgrep -af '^(sudo )?tcpreplay'" || { vagrant ssh client -c "cat $CLI"; falla "el trafico del client no esta en marcha"; }
marca inicio_cliente
paso "8 esperando fin_base (hasta 800 s); progreso cada ~60 s"
ok=0
t0=$(date +%s)
ult=0
while [ $(( $(date +%s) - t0 )) -lt 800 ]; do
  if vagrant ssh client -c "grep -q fin_base $CLI" 2>/dev/null; then ok=1; break; fi
  if vagrant ssh client -c "grep -q PARADA $CLI" 2>/dev/null; then break; fi
  ahora=$(date +%s)
  if [ $((ahora - ult)) -ge 60 ]; then
    ult=$ahora
    echo "    [$(date +%T)] $(vagrant ssh client -c "tail -n 1 $CLI" 2>/dev/null | tr -d '\r' | cut -c1-120)"
  fi
  sleep 5
done
[ "$ok" = 1 ] || { vagrant ssh client -c "cat $CLI"; falla "no aparece fin_base en $CLI"; }
marca fin_cliente
sleep 15
paso "9 fin de la captura y pipeline-stop"
vagrant ssh defender -c "DIA=$DIA bash $H cap_stop $N" || falla "cap_stop"
make pipeline-stop > "/tmp/${N}_stop1.txt" 2>&1 || falla "pipeline-stop final"
paso "10 contabilidad, logs y dataset de la corrida"
vagrant ssh defender -c "DIA=$DIA bash $H contar $N" || falla "contar"
vagrant ssh defender -c "cd $DS && ls > /tmp/$N.ds_ahora.txt && nuevos=\$(comm -13 $D/dataset_previos.txt /tmp/$N.ds_ahora.txt) && n=\$(echo \"\$nuevos\" | grep -c . || true) && echo \"    ficheros nuevos del dataset: \$n\" && [ \"\$n\" = 1 ] && cp \"$DS/\$nuevos\" $D/dataset.csv && echo \"    dataset: \$nuevos -> $D/dataset.csv\"" || falla "no hay exactamente un fichero nuevo en $DS"
vagrant ssh client -c "cat $CLI" 2>/dev/null | tr -d '\r' | grep -v '^\[argus\]' > "$DM/cliente.txt"
git rev-parse HEAD > "$DM/commit.txt"
cat "$DM/cliente.txt"
paso "11 analisis"
python3 "$TOOLS/d309_hueco_analisis.py" "$DM" | tee "$DM/analisis.txt"
rc=${PIPESTATUS[0]}
echo; echo "=== [$(date +%T)] HECHO: $DM/ (analisis rc=$rc)"
exit $rc
