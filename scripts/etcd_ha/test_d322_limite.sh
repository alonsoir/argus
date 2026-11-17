#!/bin/bash
# [C7-LIMITE-D329] test de d322_reinicio_vault.sh (Mac, raíz del repo) con un vagrant falso que contesta como la VM
# control-1 o se cuelga en el paso que se le diga. Comprueba que un paso colgado da ❌ con el paso, en el límite y no en
# una hora (DAY328), que no reinicia nada si la previa no contesta, y que con la VM sana el examinador PASA.
set -u
R=scripts/etcd_ha/d322_reinicio_vault.sh
[ -f "$R" ] || { echo "❌ ejecutar desde la raíz del repo"; exit 1; }
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
LIM=10   # el mínimo de all.yml
printf 'argus_debian_snapshot: "20261115T000000Z"\nargus_lab_llamada_vm_limite_s: %s\n' "$LIM" > "$T/all.yml"

cat > "$T/vagrant" <<'FALSO'
#!/bin/bash
# vagrant falso: "ssh control-1 -c <orden>". $C7_DIR/colgar dice qué orden se cuelga (subcadena); llamadas a $C7_DIR/llamadas
c=$4
echo "$c" >> "$C7_DIR/llamadas"
if [ -s "$C7_DIR/colgar" ] && [[ "$c" == *"$(cat "$C7_DIR/colgar")"* ]]; then sleep 600; exit 0; fi   # más que cualquier límite del examinador
case "$c" in
  *" previa")     echo "D322|OK|previa"; echo "D322|BOOT|11111111-1111-1111-1111-111111111111" ;;
  *" preparar")   echo "D322|OK|rotación pendiente" ;;
  *"systemctl reboot"*) touch "$C7_DIR/reiniciado" ;;
  *boot_id*)      if [ -f "$C7_DIR/reiniciado" ]; then echo 22222222-2222-2222-2222-222222222222; \
                  else echo 11111111-1111-1111-1111-111111111111; fi ;;
  *"is-system-running"*) echo running ;;
  *"--failed"*)   ;;
  *" arranque")   echo "D322|OK|R1-R4"; echo "D322|EPOCH|1763355600" ;;
  *" matar "*)    echo "D322|OK|R5" ;;
  *" falco "*)    echo "D322|OK|R6" ;;
esac
exit 0
FALSO
chmod +x "$T/vagrant"
export C7_DIR="$T" D322_VAGRANT="$T/vagrant" D322_ALL_YML="$T/all.yml" D322_ESPERA_ARRANQUE_S=60

fallos=0; casos=0
comprobar() {  # nombre colgar rc_esperado patrón máx_s reinicio_esperado(si|no)
  local nombre=$1 colgar=$2 rc_esp=$3 patron=$4 max=$5 rein=$6 s rc t0 dt r
  rm -f "$T/llamadas" "$T/reiniciado"; printf '%s' "$colgar" > "$T/colgar"
  t0=$(date +%s); s=$(bash "$R" 2>&1); rc=$?; dt=$(( $(date +%s) - t0 ))
  r=no; grep -q 'systemctl reboot' "$T/llamadas" 2>/dev/null && r=si
  casos=$((casos + 1))
  if [ "$rc" -eq "$rc_esp" ] && printf '%s\n' "$s" | grep -q -- "$patron" && [ "$dt" -le "$max" ] && [ "$r" = "$rein" ]; then
    echo "✅ $nombre (${dt} s)"
  else
    echo "❌ $nombre (rc=$rc/$rc_esp, ${dt} s/máx $max, reinicio=$r/$rein, patrón '$patron')"
    printf '%s\n' "$s" | sed 's/^/     | /'
    fallos=$((fallos + 1))
  fi
}

comprobar "VM sana: PASA" "" 0 "✅ PASA" 30 si
comprobar "la previa no contesta: ❌ en el límite y sin reiniciar" " previa" 1 "❌ 1 previa: control-1 no contesta en ${LIM} s" $((LIM + 15)) no
comprobar "el arranque no contesta tras el reinicio: ❌ con el paso" " arranque" 1 "❌ 4 arranque: control-1 no contesta en ${LIM} s" $((LIM + 25)) si
comprobar "systemd no contesta tras el reinicio: ❌ en su límite (120 s + el de all.yml)" "is-system-running" 1 "❌ 3 systemd tras el arranque: control-1 no contesta en $((120 + LIM)) s" $((120 + LIM + 25)) si
comprobar "la VM no vuelve (boot_id no contesta): ❌ acotado por D322_ESPERA_ARRANQUE_S" "boot_id" 1 "no volvió en 60 s" $((60 + LIM + 25)) si

echo "$((casos - fallos))/$casos casos"
[ "$fallos" -eq 0 ]
