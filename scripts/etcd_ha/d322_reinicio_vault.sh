#!/usr/bin/env bash
# d322_reinicio_vault.sh — DAY322 [VAULT-ARRANQUE-D322], ADR-060 8e.4d: test de cierre del arranque de Vault en la VM
# etcd SIN Vagrant (lo que pasa en un hospital tras un corte de luz o un parche del kernel, y cada vez que Vault se cae).
# Se ejecuta EN EL MAC, desde la raíz del repo, con la VM etcd arriba y aprovisionada (vault-arranque):
#   bash scripts/etcd_ha/d322_reinicio_vault.sh
# Pasos (ayudante en la VM: scripts/etcd_ha/d322_reinicio_vault_vm.sh):
#   1 previa: desellado ligado a vault.service, etcd-server sin Wants del desellado, Vault desellado, Falco en marcha
#   2 deja una rotación de logrotate pendiente (la carrera medida DAY322: SIGHUP a un Vault que arranca)
#   3 `sudo systemctl reboot` de la VM (no `vagrant reload`: ningún aprovisionador corre) y espera al arranque
#   4 R1-R4: logrotate rotó en el arranque, Vault arrancó a la primera, lo desselló SU unidad (sin aprovisionadores),
#     Vault y etcd-server sanos
#   5 R5: SIGKILL a Vault: Restart=on-failure lo levanta y su desellado lo deja desellado
#   6 R6: ni un CRITICAL de Falco desde el arranque (el desellado lee su clave como dueño)
# Trap: si no llegó a reiniciar, deshace el paso 2; en cualquier caso deja Vault desellado (si está en marcha).
# Parámetros (entorno), enteros: D322_ESPERA_ARRANQUE_S [60, 900] defecto 300; D322_ESPERA_VAULT_S [10, 300] defecto 60.
# [C7-LIMITE-D329] DEBT-E2E-VAGRANT-SSH-SIN-LIMITE-001: TODA llamada a la VM lleva tiempo límite (scripts/emecas/con_limite.pl,
# que mata también el ssh hijo de vagrant): argus_lab_llamada_vm_limite_s de ansible/inventory/group_vars/all.yml, más la
# espera propia de la llamada cuando la tiene (systemctl --wait 120 s; R5 D322_ESPERA_VAULT_S). Una VM que no contesta es
# ❌ con el paso, no un silencio (DAY328: control-1 viva para el ping y muerta para el disco, 60 min sin veredicto).
# D322_VAGRANT y D322_ALL_YML: solo para el test (scripts/etcd_ha/test_d322_limite.sh, vagrant falso y su all.yml).
set -u
LC_ALL=C; export LC_ALL
H=/vagrant/scripts/etcd_ha/d322_reinicio_vault_vm.sh
log() { echo "[D322-VAULT] $*"; }
entero() {  # nombre valor defecto min max -> VAL
  local n=$1 v=$2 d=$3 lo=$4 hi=$5
  if [ -z "$v" ]; then VAL=$d; log "$n=$d (defecto: ausente)"; return; fi
  if ! [[ "$v" =~ ^[0-9]+$ ]] || [ "$v" -lt "$lo" ] || [ "$v" -gt "$hi" ]; then
    VAL=$d; log "$n=$d (defecto: '$v' mal formado; entero en [$lo, $hi])"; return
  fi
  VAL=$v; log "$n=$v (entorno)"
}
entero D322_ESPERA_ARRANQUE_S "${D322_ESPERA_ARRANQUE_S:-}" 300 60 900; ESPERA_ARRANQUE=$VAL
entero D322_ESPERA_VAULT_S "${D322_ESPERA_VAULT_S:-}" 60 10 300; ESPERA_VAULT=$VAL
Y=${D322_ALL_YML:-ansible/inventory/group_vars/all.yml}
VAGRANT=${D322_VAGRANT:-vagrant}
LIM=$(ruby scripts/emecas/lab_comun.rb limite "$Y") || { log "❌ sin límite de llamada a la VM ($Y)"; exit 1; }
log "límite por llamada a control-1: ${LIM} s (argus_lab_llamada_vm_limite_s, $Y)"
T=$(mktemp /tmp/d322_vault.XXXXXX)
V() {  # límite_s orden...: la salida va a stdout; rc 142 si la VM no contesta en el límite
  local lim=$1; shift
  perl scripts/emecas/con_limite.pl "$lim" "$VAGRANT" ssh control-1 -c "$*" 2>/dev/null | tr -d '\r'
  return "${PIPESTATUS[0]}"
}
VM() {  # paso límite_s orden... -> $T; si la VM no contesta: ❌ con el paso y fuera (el trap deja todo como estaba)
  local paso=$1 lim=$2; shift 2
  V "$lim" "$@" > "$T"
  [ $? = 142 ] && { log "❌ $paso: control-1 no contesta en $lim s (cortado por el límite)"; exit 1; }
  return 0
}
FALLOS=0; PREPARADO=no; REINICIADO=no
pinta() {  # lee $T: muestra las líneas D322 y cuenta las FALLA
  local l
  while IFS= read -r l; do
    case "$l" in
      D322\|FALLA\|*) echo "  ❌ ${l#D322|FALLA|}"; FALLOS=$((FALLOS + 1));;
      D322\|OK\|*)    echo "  ✅ ${l#D322|OK|}";;
      D322\|*)        echo "     ${l#D322|}";;
    esac
  done < "$T"
}
valor() { sed -n "s/^D322|$1|//p" "$T" | head -n 1; }
fin() {
  if [ "$PREPARADO" = si ] && [ "$REINICIADO" = no ]; then V "$LIM" "bash $H restaurar" > "$T"; pinta; fi
  V "$LIM" "systemctl is-active --quiet vault.service && sudo systemctl start argus-vault-unseal.service" > /dev/null
  rm -f "$T"
}
trap fin EXIT

log "predicción: R1-R6 en ✅ (logrotate rota al arrancar, Vault arranca a la primera, lo dessella su unidad sin"
log "            aprovisionadores, sano tras un SIGKILL, 0 CRITICAL de Falco)"
log "1 previa"
VM "1 previa" "$LIM" "bash $H previa"; pinta
BOOT0=$(valor BOOT)
[ "$FALLOS" = 0 ] && [ -n "$BOOT0" ] || { log "❌ la previa falla: no se reinicia nada"; exit 1; }

log "2 rotación pendiente"
VM "2 rotación pendiente" "$LIM" "bash $H preparar"; pinta
[ "$FALLOS" = 0 ] || { log "❌ no se pudo preparar la rotación pendiente"; exit 1; }
PREPARADO=si

log "3 sudo systemctl reboot (sin Vagrant; boot_id anterior $BOOT0)"
V "$LIM" "sudo systemctl reboot" > /dev/null 2>&1 || true
T0=$SECONDS; B=""
while [ $(( SECONDS - T0 )) -lt "$ESPERA_ARRANQUE" ]; do
  sleep 5
  B=$(V "$LIM" "cat /proc/sys/kernel/random/boot_id" | grep -E '^[0-9a-f-]{36}$' | head -n 1)
  [ -n "$B" ] && [ "$B" != "$BOOT0" ] && break
done
[ -n "$B" ] && [ "$B" != "$BOOT0" ] || { log "❌ la VM etcd no volvió en $ESPERA_ARRANQUE s (boot_id '$B')"; exit 1; }
REINICIADO=si
VM "3 systemd tras el arranque" $((120 + LIM)) "timeout 120 systemctl is-system-running --wait"
log "   VM de vuelta en $(( SECONDS - T0 )) s (boot_id $B); systemd: $(tail -n 1 "$T")"
VM "3 unidades fallidas" "$LIM" "systemctl --failed --no-legend --plain"
grep -q '[^[:space:]]' "$T" && { log "   unidades fallidas:"; grep '[^[:space:]]' "$T" | sed 's/^/     /'; }

log "4 arranque (R1-R4)"
VM "4 arranque" "$LIM" "bash $H arranque"; pinta
EPOCH=$(valor EPOCH)
log "5 SIGKILL a Vault (R5)"
VM "5 SIGKILL a Vault" $((ESPERA_VAULT + LIM)) "bash $H matar $ESPERA_VAULT"; pinta
log "6 Falco desde el arranque (R6)"
if [[ "$EPOCH" =~ ^[0-9]+$ ]]; then VM "6 Falco" "$LIM" "bash $H falco $EPOCH"; pinta
else log "  ❌ R6 sin hora de arranque ('$EPOCH')"; FALLOS=$((FALLOS + 1)); fi

if [ "$FALLOS" = 0 ]; then log "✅ PASA: Vault arranca y se dessella solo, sin Vagrant, y Falco no ve ninguna lectura ajena"; exit 0
else log "❌ NO PASA: $FALLOS criterio(s) en ❌"; exit 1; fi
