#!/bin/bash
# [KERNEL-HOMOGENEO-D329] (anfitrión) DEBT-LAB-KERNEL-HOMOGENEO-001: todas las VMs del laboratorio en el mismo Debian
# y ejecutando su kernel. Para cada VM, con el tiempo límite de all.yml en cada llamada (una VM que no contesta es ❌, no
# un cuelgue: lección DAY328; con_limite.pl mata también los hijos de vagrant):
#   - fecha: sus fuentes de Debian apuntan a argus_debian_snapshot;
#   - kernel: uname -r es el kernel que pide linux-image-amd64 en esa fecha (instalado y ADEMÁS arrancado);
#   - el mismo kernel en todas las VMs.
# Uso: kernel_homogeneo.sh <all.yml> <vm>...   rc 0 solo si todas cumplen. Coste lineal en el número de VMs.
# KERNEL_HOMOGENEO_VAGRANT: el vagrant a usar (por defecto, vagrant; el test pone uno falso).
set -u
D=$(cd "$(dirname "$0")" && pwd)
Y=${1:?uso: kernel_homogeneo.sh <all.yml> <vm>...}
shift
[ "$#" -ge 1 ] || { echo "❌ kernel-homogeneo: sin VMs que comprobar"; exit 1; }
VAGRANT=${KERNEL_HOMOGENEO_VAGRANT:-vagrant}

FECHA=$(ruby "$D/lab_comun.rb" fecha "$Y") || { echo "❌ kernel-homogeneo: sin argus_debian_snapshot válido en $Y"; exit 1; }
LIM=$(ruby "$D/lab_comun.rb" limite "$Y") || { echo "❌ kernel-homogeneo: no se puede leer el límite de $Y"; exit 1; }
echo "[KERNEL-HOMOGENEO-D329] fecha declarada $FECHA; límite por llamada ${LIM} s; $# VMs"

malas=0
primero=""
for vm in "$@"; do
  T0=$(date +%s)
  salida=$(perl "$D/con_limite.pl" "$LIM" "$VAGRANT" ssh "$vm" -- 'bash -s' < "$D/kernel_homogeneo_vm.sh" 2>/dev/null)
  rc=$?
  dt=$(( $(date +%s) - T0 ))
  if [ "$rc" -eq 142 ]; then
    echo "  ❌ $vm: no contesta en ${LIM} s (cortado por el límite)"; malas=$((malas + 1)); continue
  fi
  u=$(printf '%s\n' "$salida" | sed -n 's/^uname=//p' | head -n 1)
  f=$(printf '%s\n' "$salida" | sed -n 's/^fecha=//p' | head -n 1)
  k=$(printf '%s\n' "$salida" | sed -n 's/^kernel_fecha=//p' | head -n 1)
  if [ "$rc" -ne 0 ] || [ -z "$u" ]; then
    echo "  ❌ $vm: la consulta falló (rc=$rc, ${dt} s)"; malas=$((malas + 1)); continue
  fi
  fallos=""
  [ "$f" = "$FECHA" ] || fallos="$fallos fecha=${f:-<ninguna>} (declarada $FECHA);"
  [ "$u" = "$k" ] || fallos="$fallos uname=$u no es el kernel de la fecha (${k:-<ninguno>});"
  [ -z "$primero" ] && primero="$u"
  [ "$u" = "$primero" ] || fallos="$fallos uname=$u distinto del de las demás ($primero);"
  if [ -z "$fallos" ]; then
    echo "  ✅ $vm: $u, fecha $f (${dt} s)"
  else
    echo "  ❌ $vm:$fallos"; malas=$((malas + 1))
  fi
done

if [ "$malas" -eq 0 ]; then
  echo "✅ kernel-homogeneo: $# VMs en $FECHA con el kernel $primero"
  exit 0
fi
echo "❌ kernel-homogeneo: $malas de $# VMs no cumplen"
exit 1
