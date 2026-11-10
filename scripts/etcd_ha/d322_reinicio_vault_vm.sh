#!/usr/bin/env bash
# d322_reinicio_vault_vm.sh — DAY322 [VAULT-ARRANQUE-D322]: ayudante EN LA VM etcd de d322_reinicio_vault.sh (Mac).
# Como vagrant (hace sudo dentro). Salida legible por máquina: líneas "D322|<CLAVE>|<valor>" y "D322|OK|…"/"D322|FALLA|…".
#   previa                 desellado en vault.service.wants y no en multi-user; etcd-server sin Wants del desellado;
#                          Vault desellado (etcd_vm_estado.sh); Falco y logrotate.timer en marcha; boot_id
#   preparar               deja una rotación de logrotate PENDIENTE para el próximo arranque (copia de lo tocado en
#                          /root/d322_bk/): el sello de logrotate.timer y la fecha de audit.log en el estado de logrotate
#   restaurar              deshace "preparar" (si no hubo reinicio)
#   arranque               veredicto del arranque actual (R1-R4)
#   matar ESPERA_S         SIGKILL a Vault y espera hasta ESPERA_S a que Restart=on-failure lo levante y su desellado
#                          acabe (R5)
#   falco DESDE_EPOCH      eventos de Falco desde DESDE_EPOCH (s UTC): ni un CRITICAL de aRGus (R6)
set -u
LC_ALL=C; export LC_ALL
ESTADO=/vagrant/scripts/etcd_ha/etcd_vm_estado.sh
U=argus-vault-unseal.service
ST=/var/lib/logrotate/status
SELLO=/var/lib/systemd/timers/stamp-logrotate.timer
BK=/root/d322_bk
ok()    { echo "D322|OK|$*"; }
falla() { echo "D322|FALLA|$*"; MAL=$((MAL + 1)); }
MAL=0
vault_hmac() { bash "$ESTADO" 2>/dev/null | grep -E '^  (✅|❌|⚠️)  ?(vault-hmac|etcd-server):' ; }
desellados() { sudo journalctl -b -u "$U" -o cat --no-pager 2>/dev/null | grep -cF '[VAULT-UNSEAL] Vault desellado'; }

case "${1:-}" in
previa)
  echo "D322|BOOT|$(cat /proc/sys/kernel/random/boot_id)"
  [ -L /etc/systemd/system/vault.service.wants/$U ] && ok "$U en vault.service.wants" || falla "$U NO está en vault.service.wants (¿corrió vault-arranque?)"
  [ ! -e /etc/systemd/system/multi-user.target.wants/$U ] && ok "$U fuera de multi-user.target.wants" || falla "$U sigue en multi-user.target.wants"
  W=$(systemctl show -p Wants --value ml-defender-etcd-server.service)
  case " $W " in *" $U "*) falla "ml-defender-etcd-server sigue con Wants=$U";; *) ok "ml-defender-etcd-server sin Wants del desellado";; esac
  L=$(vault_hmac); echo "$L" | sed 's/^/D322|ESTADO|/'
  echo "$L" | grep -q '✅ vault-hmac' && ok "Vault desellado antes del reinicio" || falla "Vault no está desellado antes del reinicio"
  systemctl is-active --quiet falco-modern-bpf.service && ok "Falco en marcha" || falla "Falco no está en marcha"
  systemctl is-enabled --quiet logrotate.timer && ok "logrotate.timer habilitado" || falla "logrotate.timer no está habilitado"
  ;;
preparar)
  sudo grep -q '^"/var/log/vault/audit.log" ' "$ST" || { falla "$ST sin entrada de /var/log/vault/audit.log (sin ella logrotate no rota la primera vez)"; exit 1; }
  sudo test -s /var/log/vault/audit.log || { falla "/var/log/vault/audit.log vacío (notifempty: no rotaría)"; exit 1; }
  sudo install -d -m 0700 "$BK"; sudo cp -p "$ST" "$BK/status"; sudo cp -p "$SELLO" "$BK/sello" 2>/dev/null || sudo touch "$BK/sin_sello"
  sudo sed -i 's#^"/var/log/vault/audit.log" .*#"/var/log/vault/audit.log" 2000-1-1-0:0:0#' "$ST"
  sudo touch -d '2 days ago' "$SELLO"
  ok "rotación pendiente: audit.log con última rotación 2000-1-1 y sello de logrotate.timer de hace 2 días (copia en $BK)"
  ;;
restaurar)
  sudo test -d "$BK" || { ok "nada que restaurar"; exit 0; }
  sudo cp -p "$BK/status" "$ST"
  if sudo test -f "$BK/sello"; then sudo cp -p "$BK/sello" "$SELLO"; else sudo rm -f "$SELLO"; fi
  sudo rm -rf "$BK"; ok "restaurado el estado de logrotate y el sello del timer"
  ;;
arranque)
  sudo rm -rf "$BK"   # el reinicio ya consumió la rotación pendiente
  echo "D322|EPOCH|$(date -u -d "$(uptime -s)" +%s)"
  HOY=$(date -u +%Y-%-m-%-d)
  F=$(sudo sed -n 's#^"/var/log/vault/audit.log" \([0-9-]*\)-.*#\1#p' "$ST")
  NL=$(sudo journalctl -b -u logrotate.service -o cat --no-pager | grep -c '^Finished logrotate.service')
  [ "$NL" -ge 1 ] && [ "$F" = "$HOY" ] && ok "R1 logrotate corrió en este arranque y rotó audit.log (fecha $F)" \
    || falla "R1 logrotate en este arranque: $NL ejecuciones, audit.log rotado el '$F' (se esperaba $HOY): la prueba no probó la carrera"
  FV=$(sudo journalctl -b -u vault.service -o cat --no-pager | grep -c "Failed with result")
  NR=$(systemctl show -p NRestarts --value vault.service)
  [ "$FV" = 0 ] && [ "$NR" = 0 ] && ok "R2 vault.service arrancó a la primera (0 fallos, NRestarts=0)" \
    || falla "R2 vault.service: $FV fallos y NRestarts=$NR en este arranque (journalctl -b -u vault)"
  ND=$(desellados); NDF=$(sudo journalctl -b -u "$U" -o cat --no-pager | grep -c 'Dependency failed')
  NP=$(sudo journalctl -b _COMM=sudo -o cat --no-pager | grep -c 'COMMAND=/usr/bin/bash -l')
  [ "$ND" -ge 1 ] && [ "$NDF" = 0 ] && [ "$NP" = 0 ] \
    && ok "R3 desellado por su unidad ($ND vez/veces), sin 'Dependency failed' y sin ningún aprovisionador de Vagrant" \
    || falla "R3 desellado: $ND veces, $NDF 'Dependency failed', $NP aprovisionadores (sudo bash -l) en este arranque"
  L=$(vault_hmac); echo "$L" | sed 's/^/D322|ESTADO|/'
  echo "$L" | grep -q '✅ vault-hmac' && echo "$L" | grep -q '✅ etcd-server' \
    && ok "R4 Vault desellado y etcd-server sano tras el reinicio" || falla "R4 Vault o etcd-server no sanos tras el reinicio"
  ;;
matar)
  E=${2:-}; [[ "$E" =~ ^[0-9]+$ ]] && [ "$E" -ge 10 ] && [ "$E" -le 300 ] || { falla "ESPERA_S '$E' mal formado: entero [10, 300]"; exit 1; }
  N0=$(desellados); R0=$(systemctl show -p NRestarts --value vault.service)
  sudo systemctl kill -s KILL vault.service; T0=$(date +%s)
  while :; do
    N=$(desellados); R=$(systemctl show -p NRestarts --value vault.service)
    [ "$N" -gt "$N0" ] && systemctl is-active --quiet vault.service && break
    [ $(( $(date +%s) - T0 )) -ge "$E" ] && break
    sleep 1
  done
  T=$(( $(date +%s) - T0 ))
  L=$(vault_hmac); echo "$L" | sed 's/^/D322|ESTADO|/'
  [ "$R" -gt "$R0" ] && [ "$N" -gt "$N0" ] && echo "$L" | grep -q '✅ vault-hmac' \
    && ok "R5 tras SIGKILL, Restart=on-failure levantó Vault (NRestarts $R0 -> $R) y su desellado lo dejó desellado en $T s" \
    || falla "R5 tras SIGKILL en $T s: NRestarts $R0 -> $R, desellados $N0 -> $N, $(echo "$L" | grep vault-hmac)"
  ;;
falco)
  D=${2:-}; [[ "$D" =~ ^[0-9]+$ ]] || { falla "DESDE_EPOCH '$D' mal formado"; exit 1; }
  sudo python3 - "$D" <<'PY'
import collections, datetime, glob, json, sys
desde = int(sys.argv[1]); c = collections.Counter(); crit = []
for f in sorted(glob.glob("/var/log/falco/eventos.json*")):
    if f.endswith(".gz"): continue
    for linea in open(f, errors="replace"):
        try: e = json.loads(linea)
        except Exception: continue
        t = datetime.datetime.fromisoformat(e.get("time", "")[:19]).replace(tzinfo=datetime.timezone.utc).timestamp()
        if t < desde: continue
        c[(e.get("rule"), e.get("priority"))] += 1
        if e.get("priority") == "Critical": crit.append(e.get("output", "")[:300])
for (r, p), n in sorted(c.items()): print("D322|FALCO|%d %s (%s)" % (n, r, p))
for x in crit: print("D322|CRITICAL|%s" % x)
print("D322|%s|R6 Falco desde el reinicio: %d CRITICAL de aRGus" % ("OK" if not crit else "FALLA", len(crit)))
PY
  exit 0
  ;;
*) echo "uso: $0 previa | preparar | restaurar | arranque | matar ESPERA_S | falco DESDE_EPOCH"; exit 2;;
esac
[ "$MAL" = 0 ]
