#!/usr/bin/env bash
# scripts/emecas/test_lab_parar.sh — [LAB-PARAR-D331] (anfitrión) prueba scripts/emecas/lab_parar.sh con un vagrant y un
# make falsos (no toca el lab): orden de parada, pipeline-stop solo con el defender en marcha, VMs ya paradas o sin
# crear, halt colgado -> --force tras el límite, pipeline-stop que falla -> sigue, VM que no para -> rc 1, sin VMs ->
# rc 2. Tarda unos 15 s (el caso del halt colgado espera el límite mínimo, 10 s). rc 0 solo si pasan todos.
set -u
LC_ALL=C; export LC_ALL
D=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
ok=0; mal=0
bien() { ok=$((ok + 1)); }
falla() { mal=$((mal + 1)); echo "FALLO: $*"; }

cat > "$T/vagrant" <<'V'
#!/usr/bin/env bash
E="$LP_T/estado"; R="$LP_T/registro"
case "$1" in
  status) echo "1,$2,state,$(cat "$E/$2" 2>/dev/null || echo not_created)" ;;
  halt)
    if [ "$2" = --force ]; then echo "halt --force $3" >> "$R"; echo poweroff > "$E/$3"; exit 0; fi
    echo "halt $2" >> "$R"
    [ -e "$LP_T/cuelga/$2" ] && sleep 30
    [ -e "$LP_T/nopara/$2" ] && exit 0
    [ -e "$LP_T/falla/$2" ] && exit 1
    echo poweroff > "$E/$2" ;;
  *) exit 9 ;;
esac
V
cat > "$T/make" <<'M'
#!/usr/bin/env bash
echo "make $*" >> "$LP_T/registro"; exit "${LP_MAKE_RC:-0}"
M
chmod +x "$T/vagrant" "$T/make"
printf 'argus_debian_snapshot: "20261115T000000Z"\nargus_lab_llamada_vm_limite_s: 10\n' > "$T/all.yml"
export LP_T="$T" LAB_PARAR_VAGRANT="$T/vagrant" LAB_PARAR_MAKE="$T/make" LAB_PARAR_ALLYML="$T/all.yml"
VMS="client suricata zeek wazuh defender control-3 control-2 control-1"

# prepara ESTADO [VM=estado...]: todas las VMS con ESTADO y las excepciones; limpia registro y marcas
prepara() {
  rm -rf "$T/estado" "$T/cuelga" "$T/nopara" "$T/falla"; mkdir -p "$T/estado" "$T/cuelga" "$T/nopara" "$T/falla"
  : > "$T/registro"; local v; for v in $VMS; do echo "$1" > "$T/estado/$v"; done; shift
  for v in "$@"; do echo "${v#*=}" > "$T/estado/${v%%=*}"; done
}
corre() { bash "$D/lab_parar.sh" "$@" > "$T/salida" 2>&1; echo $?; }
reg() { tr '\n' '|' < "$T/registro"; }

# 1. todo en marcha: pipeline-stop y después los halt en el orden dado, rc 0
prepara running
rc=$(corre $VMS)
esperado="make --no-print-directory pipeline-stop|halt client|halt suricata|halt zeek|halt wazuh|halt defender|halt control-3|halt control-2|halt control-1|"
[ "$rc" = 0 ] && bien || falla "1: rc=$rc"
[ "$(reg)" = "$esperado" ] && bien || falla "1: registro $(reg)"
grep -q '✅ laboratorio parado en orden: 8 VMs' "$T/salida" && bien || falla "1: sin la línea final"

# 2. todo parado ya: ni pipeline-stop ni halt, rc 0
prepara poweroff
rc=$(corre $VMS)
[ "$rc" = 0 ] && bien || falla "2: rc=$rc"
[ -z "$(reg)" ] && bien || falla "2: registro $(reg)"
grep -q 'no hay pipeline que parar' "$T/salida" && bien || falla "2: sin el aviso del pipeline"

# 3. defender parado, client en marcha y una VM sin crear: sin pipeline-stop, solo halt client
prepara poweroff client=running
rm -f "$T/estado/wazuh"
rc=$(corre $VMS)
[ "$rc" = 0 ] && bien || falla "3: rc=$rc"
[ "$(reg)" = "halt client|" ] && bien || falla "3: registro $(reg)"
grep -q 'wazuh: ya en not_created' "$T/salida" && bien || falla "3: wazuh sin crear no se salta"

# 4. halt de zeek colgado: vence el límite, --force de zeek y sigue con wazuh, rc 0
prepara running; : > "$T/cuelga/zeek"
rc=$(corre $VMS)
[ "$rc" = 0 ] && bien || falla "4: rc=$rc"
case "$(reg)" in *"halt zeek|halt --force zeek|halt wazuh|"*) bien ;; *) falla "4: registro $(reg)" ;; esac
grep -q 'AVISO vagrant halt zeek rc=142 (venció el límite de 10 s)' "$T/salida" && bien || falla "4: sin el aviso del límite"

# 5. halt de suricata que falla: --force y sigue
prepara running; : > "$T/falla/suricata"
rc=$(corre $VMS)
[ "$rc" = 0 ] && bien || falla "5: rc=$rc"
case "$(reg)" in *"halt suricata|halt --force suricata|halt zeek|"*) bien ;; *) falla "5: registro $(reg)" ;; esac

# 6. pipeline-stop falla: aviso, y los halt se hacen igual
prepara running
rc=$(LP_MAKE_RC=3 corre $VMS)
[ "$rc" = 0 ] && bien || falla "6: rc=$rc"
grep -q 'AVISO pipeline-stop rc=3' "$T/salida" && bien || falla "6: sin el aviso de pipeline-stop"
[ "$(reg)" = "$esperado" ] && bien || falla "6: registro $(reg)"

# 7. wazuh dice que para pero sigue en marcha (también tras --force no se mira: el halt dio 0): rc 1 nombrándola
prepara running; : > "$T/nopara/wazuh"
rc=$(corre $VMS)
[ "$rc" = 1 ] && bien || falla "7: rc=$rc"
grep -q '❌ wazuh queda en running' "$T/salida" && bien || falla "7: no nombra wazuh"
grep -q '1 de 8 VMs sin parar' "$T/salida" && bien || falla "7: sin el recuento"

# 8. sin VMs: rc 2
prepara running
rc=$(corre)
[ "$rc" = 2 ] && bien || falla "8: rc=$rc"
[ -z "$(reg)" ] && bien || falla "8: registro $(reg)"

echo "[TEST-LAB-PARAR] $ok bien, $mal mal"
[ "$mal" = 0 ]
