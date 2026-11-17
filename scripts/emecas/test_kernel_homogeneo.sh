#!/bin/bash
# [KERNEL-HOMOGENEO-D329] test de kernel_homogeneo.sh (anfitrión) con un vagrant falso: cada VM responde lo que diga su
# fichero en el directorio temporal, o se cuelga. Comprueba el código de salida, el veredicto de cada VM y, en la VM
# colgada, que el límite la corta (un examinador sin límite convierte un rojo en silencio: DAY328).
set -u
D=$(cd "$(dirname "$0")" && pwd)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
F=20261115T000000Z
K=6.1.0-54-amd64
LIM=10   # el mínimo de all.yml: la VM colgada cuesta 10 s

cat > "$T/vagrant" <<'FALSO'
#!/bin/bash
# vagrant falso: "ssh <vm> -- bash -s"; responde con $KH_DIR/vm_<vm>, o se cuelga si contiene "colgar"
cat > /dev/null
r="$KH_DIR/vm_$2"
[ -f "$r" ] || exit 1
if grep -qx colgar "$r"; then sleep 60; exit 0; fi
cat "$r"
FALSO
chmod +x "$T/vagrant"
export KH_DIR="$T" KERNEL_HOMOGENEO_VAGRANT="$T/vagrant"

printf 'argus_debian_snapshot: "%s"\nargus_lab_llamada_vm_limite_s: %s\n' "$F" "$LIM" > "$T/all.yml"
printf 'argus_lab_llamada_vm_limite_s: %s\n' "$LIM" > "$T/sin_fecha.yml"
bien() { printf 'uname=%s\nfecha=%s\nkernel_fecha=%s\n' "${1:-$K}" "${2:-$F}" "${3:-$K}" > "$T/vm_$4"; }

fallos=0
casos=0
comprobar() {  # nombre rc_esperado patrón_obligatorio n_ok_esperado -- args
  local nombre=$1 rc_esp=$2 patron=$3 nok=$4; shift 5
  local s rc n
  s=$(bash "$D/kernel_homogeneo.sh" "$@" 2>&1); rc=$?
  n=$(printf '%s\n' "$s" | grep -c '^  ✅')
  casos=$((casos + 1))
  if [ "$rc" -eq "$rc_esp" ] && printf '%s\n' "$s" | grep -q -- "$patron" && [ "$n" -eq "$nok" ]; then
    echo "✅ $nombre"
  else
    echo "❌ $nombre (rc=$rc, esperado $rc_esp; ✅ por VM=$n, esperado $nok; patrón '$patron')"
    printf '%s\n' "$s" | sed 's/^/     | /'
    fallos=$((fallos + 1))
  fi
}

bien "" "" "" a; bien "" "" "" b; bien "" "" "" c
comprobar "tres VMs iguales y en la fecha" 0 "✅ kernel-homogeneo: 3 VMs" 3 -- "$T/all.yml" a b c

bien 6.1.0-25-amd64 "" "" b
comprobar "una VM con el kernel de la caja (instalado el de la fecha, sin arrancar)" 1 "❌ b: uname=6.1.0-25-amd64 no es el kernel de la fecha" 2 -- "$T/all.yml" a b c

bien "" 20261116T000000Z "" b
comprobar "una VM con otra fecha" 1 "❌ b: fecha=20261116T000000Z" 2 -- "$T/all.yml" a b c

bien "" "" "" b; bien 6.1.0-55-amd64 "" 6.1.0-55-amd64 c
comprobar "una VM coherente consigo misma pero con otro kernel que las demás" 1 "distinto del de las demás" 2 -- "$T/all.yml" a b c

bien "" "" "" c; echo colgar > "$T/vm_b"
t0=$(date +%s)
comprobar "una VM que no contesta" 1 "❌ b: no contesta en ${LIM} s" 2 -- "$T/all.yml" a b c
dt=$(( $(date +%s) - t0 )); casos=$((casos + 1))
if [ "$dt" -lt $((LIM + 15)) ]; then echo "✅ el límite la corta (${dt} s)"; else echo "❌ el límite no la corta (${dt} s)"; fallos=$((fallos + 1)); fi

bien "" "" "" b
comprobar "sin fecha declarada: para y no consulta ninguna VM" 1 "ERROR DE FABRICANTE" 0 -- "$T/sin_fecha.yml" a b c

comprobar "una VM que no existe" 1 "❌ z: la consulta falló" 1 -- "$T/all.yml" a z

echo "$((casos - fallos))/$casos casos"
[ "$fallos" -eq 0 ]
