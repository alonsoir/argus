#!/usr/bin/env bash
# [LATIDO-DATOS-D321] DAY321 E2E de 8e.4c (ADR-060 H-H y H-F) con el pipeline vivo: la versión del manifiesto que manda
# el firewall en su latido (protegidos_version) frente a la publicada, tal como la enseña pipeline-status
# (scripts/etcd_ha/etcd_vm_estado.sh en la VM etcd), y la línea [PROTEGIDOS-RP-FILTER] del agente.
# Para provocar un firewall DESFASADO de verdad (decisión de Alonso DAY321): protegidos.consulta_sec=3600 SOLO durante la
# prueba (el JSON se restaura con cmp, como d302/d320), se publica N+1 con argus-infra y el firewall no la recoge.
# La entrada de prueba (192.168.100.63/32 por eth2, intranet) se quita al acabar (N+2), también desde el trap.
# No toca dry_run ni la mitigación. Necesita la VM etcd arriba. Deja el pipeline PARADO, como los demás E2E. ~8 min.
# Uso (raíz del repo, Mac): DIA=day321 bash scripts/etcd_ha/d321_latido_e2e.sh NOMBRE
#
# PREDICCIÓN (escrita antes de la corrida; HB = etcd.heartbeat_interval_seconds del firewall.json, 30):
#  L0 al arrancar: en el log del firewall '[ETCD-CLIENTE-LATIDO-DATO] firewall-acl-agent: protegidos_version=N (nuevo)'
#     y '[PROTEGIDOS-RP-FILTER]' con rp_filter 0 en todas las interfaces del manifiesto (medido DAY320); en <= HB + 15 s
#     etcd_vm_estado.sh dice '✅ protegidos:     vN publicada; 1 componente al día'.
#  L1 consulta_sec=3600 y N+1 publicada: en <= HB + 15 s '⚠️  protegidos:     v(N+1) publicada; 1 componente:
#     1 DESFASADO' y '- firewall-acl-agent vN DESFASADO (activo, ...'; el veredicto de la VM etcd ([ETCD-VM-ESTADO]
#     SANO / NO SANO) es el mismo que en L0 (la línea solo informa).
#  L2 JSON restaurado (cmp) y pipeline rearrancado: en <= HB + 15 s '✅ ... v(N+1) publicada; 1 componente al día'.
#  L3 sin la entrada de prueba (N+2): en <= consulta_sec + HB + 15 s '✅ ... v(N+2) publicada; 1 componente al día'.
#  L4 en todo el log del firewall, 0 líneas de rechazo de datos del latido (ni del cliente ni devueltas por el
#     etcd-server) y, en el journal del etcd-server desde el principio de la prueba, 0 [ETCD-LATIDO-DATOS-RECHAZADOS].
set -u
N=${1:?nombre de la corrida}
export DIA=${DIA:-day321}
H=/vagrant/scripts/timebase/lab_corrida_defender.sh
DM=logs/lab/$DIA/$N
JSON=firewall-acl-agent/config/firewall.json
BAK=/tmp/$N.firewall.json.orig
F=logs/lab/firewall-agent.log
EST=/vagrant/scripts/etcd_ha/etcd_vm_estado.sh
IP63=192.168.100.63
UNIDAD=ml-defender-etcd-server.service
JSON_TOCADO=0; RESTAURADO=0; FALLOS=0; ENTRADA63=0; HB=30; CS=30
paso()  { echo; echo "=== [$(date +%T)] $*"; }
falla() { echo; echo "PARADA [$(date +%T)]: $*"; exit 1; }
pasa()  { echo "PASA  $*"; }
mal()   { echo "FALLA $*"; FALLOS=$((FALLOS + 1)); }
# vm VM ORDEN: salida sin la línea [argus] de vagrant y con el código del comando remoto (patrón de d320_antispoof)
vm()    { local out rc; out=$(vagrant ssh "$1" -c "$2" 2>/dev/null); rc=$?
          [ -n "$out" ] && printf '%s\n' "$out" | tr -d '\r' | grep -v '^\[argus\]'; return $rc; }
infra() { vm etcd "sudo /usr/local/sbin/argus-infra $1"; }
estado(){ vm etcd "bash $EST" > "$DM/estado_$1.txt" 2>&1; grep -E '^  (✅ |⚠️  |❌ )protegidos:|^       - [a-z].* v[0-9]+ ' "$DM/estado_$1.txt"; }
veredicto() { grep -oE '^\[ETCD-VM-ESTADO\] (SANO|NO SANO)' "$DM/estado_$1.txt" | head -n 1; }
publicada() { sed -nE 's/^  (✅ |⚠️  )protegidos:     v([0-9]+) publicada.*/\2/p' "$DM/estado_$1.txt" | head -n 1; }
# espera_linea ETIQUETA SEGUNDOS PATRÓN: repite etcd_vm_estado.sh cada 5 s hasta que la línea case; deja T (segundos)
espera_linea() {
  local et=$1 lim=$2 pat=$3 t0; t0=$(date +%s)
  while :; do
    estado "$et" > /dev/null
    grep -qE "$pat" "$DM/estado_$et.txt" && { T=$(( $(date +%s) - t0 )); return 0; }
    [ $(( $(date +%s) - t0 )) -ge "$lim" ] && { T=$(( $(date +%s) - t0 )); return 1; }
    sleep 5
  done
}
restaurar() {
  [ "$RESTAURADO" = 1 ] && return 0
  RESTAURADO=1
  echo; echo "=== [$(date +%T)] TRAP: restaurando el lab"
  if [ "$ENTRADA63" = 1 ]; then
    infra "del --planta lab-vagrant --cidr $IP63/32 --interfaz eth2 --motivo 'fin de la prueba del latido DAY321 (trap)' --si" | tail -n 3
  fi
  make pipeline-stop > "/tmp/${N}_stop_trap.txt" 2>&1
  echo "    pipeline-stop rc=$?"
  if [ "$JSON_TOCADO" = 1 ] && [ -f "$BAK" ]; then
    cp "$BAK" "$JSON"
    if cmp -s "$BAK" "$JSON"; then echo "    JSON restaurado (cmp 0)"; else echo "    ERROR: el JSON NO coincide con $BAK"; fi
  fi
  echo "    el pipeline queda PARADO (como d302/d320); make pipeline-start PROFILE=production para levantarlo"
}
trap restaurar EXIT
trap 'exit 130' INT TERM

paso "1 comprobaciones previas y ritmos del JSON"
git diff --quiet -- "$JSON" || falla "$JSON tiene cambios sin commit: no se toca"
vagrant status etcd 2>/dev/null | grep -qE "^etcd +running" || falla "la VM etcd no está arriba (vagrant up etcd)"
read -r HB CS < <(python3 - "$JSON" <<'PYEOF'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
print(d["etcd"].get("heartbeat_interval_seconds", 30), d.get("protegidos", {}).get("consulta_sec", 30))
PYEOF
) || falla "no leo el JSON"
LIM=$((HB + 15)); LIM3=$((CS + HB + 15))
INICIO=$(vm etcd "date +%s")
[[ "$INICIO" =~ ^[0-9]+$ ]] || falla "no leo la hora de la VM etcd"
echo "    heartbeat_interval_seconds=$HB consulta_sec=$CS (límites: $LIM s y $LIM3 s); journal del etcd-server desde @$INICIO"
mkdir -p "$DM"

paso "2 L0 pipeline-stop, logs a cero y pipeline-start PROFILE=production"
make pipeline-stop > "/tmp/${N}_stop0.txt" 2>&1 || falla "pipeline-stop"
vm defender "DIA=$DIA bash $H truncar" > /dev/null || falla "truncar"
make pipeline-start PROFILE=production > "/tmp/${N}_start0.txt" 2>&1 || { tail -n 20 "/tmp/${N}_start0.txt"; falla "pipeline-start rc!=0"; }
ok=0
for i in $(seq 1 90); do grep -q "\[ETCD-CLIENTE-LATIDO-DATO\] firewall-acl-agent: protegidos_version=" "$F" 2>/dev/null && ok=1 && break; sleep 1; done
[ "$ok" = 1 ] || falla "no aparece '[ETCD-CLIENTE-LATIDO-DATO] firewall-acl-agent: protegidos_version=' en $F"
grep -m 1 "\[ETCD-CLIENTE-LATIDO-DATO\] firewall-acl-agent: protegidos_version=" "$F" | sed 's/^/    /'
RPF=$(grep -m 1 "\[PROTEGIDOS-RP-FILTER\]" "$F")
echo "    $RPF" | cut -c1-240
if [ -n "$RPF" ] && echo "$RPF" | grep -qE '=[0-9] \(all=' && ! echo "$RPF" | grep -qE '=[12?] \(all='; then
  pasa "L0 [PROTEGIDOS-RP-FILTER] al arrancar, 0 en todas las interfaces del manifiesto"
else
  mal "L0 [PROTEGIDOS-RP-FILTER] ausente o con valores distintos de 0 (medido DAY320: 0 en todas)"
fi
if espera_linea l0 "$LIM" '^  ✅ protegidos:     v[0-9]+ publicada; 1 componente al día'; then
  NV=$(publicada l0); V0=$(veredicto l0)
  grep -E 'protegidos:|firewall-acl-agent v' "$DM/estado_l0.txt" | sed 's/^/    /'
  grep -q "protegidos_version=$NV " "$F" && pasa "L0 firewall al día con v$NV en $T s (límite $LIM)" || mal "L0 pipeline-status dice v$NV pero el log del firewall no"
else
  estado l0; falla "L0 en $LIM s pipeline-status no dice '✅ ... 1 componente al día' (ver $DM/estado_l0.txt)"
fi
echo "    veredicto de la VM etcd en L0: $V0"

paso "3 L1 pipeline-stop y protegidos.consulta_sec=3600 SOLO para la prueba (copia exacta en $BAK)"
make pipeline-stop > "/tmp/${N}_stop1.txt" 2>&1 || falla "pipeline-stop"
rm -f "$BAK"; cp "$JSON" "$BAK" || falla "copia del JSON"
JSON_TOCADO=1
python3 - "$JSON" <<'PYEOF' || falla "no se pudo conmutar el JSON"
import json, sys
p = sys.argv[1]
d = json.load(open(p, encoding="utf-8"))
antes = d["protegidos"]["consulta_sec"]
d["protegidos"]["consulta_sec"] = 3600
with open(p, "w", encoding="utf-8") as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
    f.write("\n")
print(f"    antes: consulta_sec={antes}; ahora: consulta_sec=3600 (PRUEBA)")
PYEOF
make pipeline-start PROFILE=production > "/tmp/${N}_start1.txt" 2>&1 || { tail -n 20 "/tmp/${N}_start1.txt"; falla "pipeline-start rc!=0"; }
espera_linea l1a "$LIM" "^  ✅ protegidos:     v$NV publicada; 1 componente al día" || falla "tras rearrancar con consulta_sec=3600 el firewall no vuelve al día con v$NV"
paso "3b publicar v$((NV + 1)) con la entrada de prueba $IP63/32 por eth2 (argus-infra, VM etcd)"
infra "add --planta lab-vagrant --categoria intranet --cidr $IP63/32 --interfaz eth2 --motivo-entrada 'prueba latido DAY321' --motivo 'prueba del latido DAY321 (se quita al acabar)' --si" | tail -n 4
infra "list" | grep -q "$IP63/32" || falla "argus-infra no publicó $IP63"
ENTRADA63=1
if espera_linea l1 "$LIM" "^  ⚠️  protegidos:     v$((NV + 1)) publicada; 1 componente: 1 DESFASADO"; then
  grep -E 'protegidos:|firewall-acl-agent v' "$DM/estado_l1.txt" | sed 's/^/    /'
  if grep -qE "^       - firewall-acl-agent v$NV DESFASADO \(activo, latido hace [0-9]+ s\)" "$DM/estado_l1.txt"; then
    pasa "L1 firewall DESFASADO (v$NV con v$((NV + 1)) publicada) en $T s (límite $LIM)"
  else
    mal "L1 la línea de detalle no dice 'firewall-acl-agent v$NV DESFASADO (activo, ...'"
  fi
  [ "$(veredicto l1)" = "$V0" ] && pasa "L1 el desfase no cambia el veredicto de la VM etcd ($V0)" || mal "L1 veredicto $(veredicto l1) distinto del de L0 ($V0)"
else
  estado l1; mal "L1 en $LIM s pipeline-status no dice '⚠️  ... v$((NV + 1)) publicada; 1 componente: 1 DESFASADO'"
fi

paso "4 L2 pipeline-stop, JSON restaurado (cmp) y pipeline-start"
make pipeline-stop > "/tmp/${N}_stop2.txt" 2>&1 || falla "pipeline-stop"
cp "$BAK" "$JSON"; cmp -s "$BAK" "$JSON" || falla "el JSON NO coincide con $BAK"
JSON_TOCADO=0; echo "    JSON restaurado (cmp 0)"
make pipeline-start PROFILE=production > "/tmp/${N}_start2.txt" 2>&1 || { tail -n 20 "/tmp/${N}_start2.txt"; falla "pipeline-start rc!=0"; }
if espera_linea l2 "$LIM" "^  ✅ protegidos:     v$((NV + 1)) publicada; 1 componente al día"; then
  pasa "L2 al rearrancar recoge v$((NV + 1)) y queda al día en $T s (límite $LIM)"
else
  estado l2; mal "L2 en $LIM s no está al día con v$((NV + 1))"
fi

paso "5 L3 quitar la entrada de prueba (v$((NV + 2))) con el pipeline vivo"
infra "del --planta lab-vagrant --cidr $IP63/32 --interfaz eth2 --motivo 'fin de la prueba del latido DAY321' --si" | tail -n 3
infra "list" | grep -q "$IP63/32" && falla "argus-infra no quitó $IP63"
ENTRADA63=0
if espera_linea l3 "$LIM3" "^  ✅ protegidos:     v$((NV + 2)) publicada; 1 componente al día"; then
  grep -E 'protegidos:|firewall-acl-agent v' "$DM/estado_l3.txt" | sed 's/^/    /'
  pasa "L3 v$((NV + 2)) recogida por la consulta periódica y al día en $T s (límite $LIM3)"
else
  estado l3; mal "L3 en $LIM3 s no está al día con v$((NV + 2))"
fi

paso "6 L4 sin rechazos de datos del latido"
r1=$(grep -cE "\[ETCD-CLIENTE-LATIDO-DATOS-RECHAZADOS\]|no se guarda \(datos del latido" "$F")
r2=$(vm etcd "sudo journalctl -u $UNIDAD --since @$INICIO --no-pager | grep -c '\[ETCD-LATIDO-DATOS-RECHAZADOS\]'")
[ "$r1" = 0 ] && pasa "L4 0 rechazos en el log del firewall" || mal "L4 $r1 rechazos en el log del firewall"
[ "${r2:-x}" = 0 ] && pasa "L4 0 [ETCD-LATIDO-DATOS-RECHAZADOS] en el journal del etcd-server" || mal "L4 ${r2:-sin respuesta} rechazos en el journal del etcd-server"
grep -E "\[ETCD-CLIENTE-LATIDO-DATO\]|\[PROTEGIDOS-RP-FILTER\]" "$F" | cut -c1-200 > "$DM/latido_firewall.txt"
cp "$F" "$DM/firewall-agent.log" 2>/dev/null
echo; echo "=== RESULTADO $([ "$FALLOS" = 0 ] && echo PASA || echo "FALLA ($FALLOS)") — $DM/"
[ "$FALLOS" = 0 ]
