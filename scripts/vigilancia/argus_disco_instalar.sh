#!/usr/bin/env bash
# scripts/vigilancia/argus_disco_instalar.sh — [VIGILANCIA-D321] ADR-060 8e.4d: argus-disco (uso del disco del audit de
# Vault) en la VM etcd. Se ejecuta EN la VM etcd como root: aprovisionador "argus-disco" del Vagrantfile (run: always).
# Del repo (nada en el código):
#   scripts/vigilancia/argus_disco.py            -> /opt/argus/vigilancia/argus_disco.py
#   provisioning/vigilancia/disco.json           -> /etc/argus-vigilancia/disco.json (campos y rangos: argus_disco.py)
#     (o el que diga VIGILANCIA_DISCO_JSON: disco.json o disco-<nombre>.json del mismo directorio [DISCO-RUTAS-D324])
#   provisioning/vigilancia/argus-disco.service  -> /etc/systemd/system/argus-disco.service
# Pasos: 1 pone lo que cambie (con copia de lo anterior); 2 valida: argus_disco.py --una-vez con la configuración puesta
# tiene que dar una medida y ningún ARGUS-DISCO-ERROR; si no, restaura lo anterior y rc 1 (todo o nada); 3 reinicia el
# servicio solo si algo cambió o no está en marcha; 4 comprueba que está en marcha y que su medida llega al journal
# con el identificador argus-disco (lo que lee el agente de Wazuh).
set -u
LC_ALL=C; export LC_ALL
RAIZ=${VIGILANCIA_RAIZ:-/vagrant}
UNIDAD=argus-disco.service
SCRIPT=/opt/argus/vigilancia/argus_disco.py
CONF=/etc/argus-vigilancia/disco.json
UNIT=/etc/systemd/system/$UNIDAD
log() { echo "[VIGILANCIA-DISCO] $*"; }
fallo() { echo "[VIGILANCIA-DISCO] FALLA: $*"; exit 1; }

[ "$(id -u)" = 0 ] || fallo "hay que ejecutarlo como root"
command -v python3 >/dev/null || fallo "falta python3"
# [DISCO-RUTAS-D324] el JSON del repo que va a $CONF: provisioning/vigilancia/$VIGILANCIA_DISCO_JSON, defecto
# disco.json. Lo elige el Vagrantfile por nodo (hasta el PR2c, los nodos sin Vault: disco-sin-vault.json).
DISCO_JSON=${VIGILANCIA_DISCO_JSON:-disco.json}
[[ "$DISCO_JSON" =~ ^disco(-[a-z0-9]+)*\.json$ ]] \
  || fallo "VIGILANCIA_DISCO_JSON='$DISCO_JSON' mal formado (disco.json o disco-<nombre>.json, [a-z0-9-])"
log "configuración: provisioning/vigilancia/$DISCO_JSON ($([ -n "${VIGILANCIA_DISCO_JSON:-}" ] && echo VIGILANCIA_DISCO_JSON || echo 'defecto: VIGILANCIA_DISCO_JSON ausente'))"
for f in scripts/vigilancia/argus_disco.py provisioning/vigilancia/$DISCO_JSON provisioning/vigilancia/argus-disco.service; do
  [ -r "$RAIZ/$f" ] || fallo "no leo $RAIZ/$f"
done

# 1 poner con respaldo
BK=$(mktemp -d /tmp/argus_disco_bk.XXXXXX)
CAMBIOS=0
declare -a PUESTOS=()
poner() {  # origen destino modo
  local o=$1 d=$2 m=$3
  if [ -f "$d" ] && cmp -s "$o" "$d"; then return 0; fi
  mkdir -p "$BK$(dirname "$d")"
  install -d -m 0755 -o root -g root "$(dirname "$d")"
  if [ -f "$d" ]; then cp -p "$d" "$BK$d"; else : > "$BK$d.nuevo"; fi
  PUESTOS+=("$d")
  install -m "$m" -o root -g root "$o" "$d" || { restaurar; fallo "no se pudo poner $d: restaurado lo anterior"; }
  CAMBIOS=$((CAMBIOS + 1)); log "puesto $d"
}
restaurar() {
  local d
  for d in "${PUESTOS[@]}"; do
    if [ -f "$BK$d" ]; then cp -p "$BK$d" "$d"; else rm -f "$d"; fi
    log "restaurado $d"
  done
  systemctl daemon-reload
}
poner "$RAIZ/scripts/vigilancia/argus_disco.py" "$SCRIPT" 0755
poner "$RAIZ/provisioning/vigilancia/$DISCO_JSON" "$CONF" 0644
poner "$RAIZ/provisioning/vigilancia/argus-disco.service" "$UNIT" 0644

# 2 validar
SALIDA=$(cd / && python3 -I "$SCRIPT" "$CONF" --una-vez 2>&1); RC=$?
if [ "$RC" -ne 0 ] || grep -q '^ARGUS-DISCO-ERROR' <<< "$SALIDA" || ! grep -q '^ARGUS-DISCO ruta=' <<< "$SALIDA"; then
  echo "$SALIDA"
  restaurar
  fallo "argus_disco.py --una-vez con $CONF: rc $RC, sin medida o con errores: restaurado lo anterior"
fi
log "validado: $(grep '^ARGUS-DISCO-CONFIG' <<< "$SALIDA"); $(grep '^ARGUS-DISCO ruta=' <<< "$SALIDA")"
systemd-analyze verify "$UNIT" >/dev/null 2>&1 || { restaurar; fallo "systemd-analyze verify rechaza $UNIT: restaurado lo anterior"; }

# 3 servicio
systemctl daemon-reload
systemctl enable "$UNIDAD" >/dev/null 2>&1 || fallo "systemctl enable $UNIDAD"
DESDE=$(date '+%Y-%m-%d %H:%M:%S')
if [ "$CAMBIOS" -gt 0 ] || ! systemctl is-active --quiet "$UNIDAD"; then
  systemctl restart "$UNIDAD" || fallo "systemctl restart $UNIDAD (journalctl -u $UNIDAD)"
else
  DESDE=""
fi

# 4 en marcha y escribiendo al journal como argus-disco
systemctl is-active --quiet "$UNIDAD" || fallo "$UNIDAD no queda en marcha (journalctl -u $UNIDAD)"
if [ -n "$DESDE" ]; then
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    journalctl -t argus-disco --since "$DESDE" -o cat 2>/dev/null | grep -q '^ARGUS-DISCO ruta=' && break
    sleep 1
  done
  ULTIMA=$(journalctl -t argus-disco --since "$DESDE" -o cat 2>/dev/null | grep '^ARGUS-DISCO ruta=' | tail -1)
else
  ULTIMA=$(journalctl -t argus-disco -n 50 -o cat 2>/dev/null | grep '^ARGUS-DISCO ruta=' | tail -1)
fi
[ -n "$ULTIMA" ] || fallo "$UNIDAD en marcha pero sin ninguna medida en el journal con identificador argus-disco"
rm -rf "$BK"
log "OK: $UNIDAD en marcha ($CAMBIOS cambios); última medida: $ULTIMA"
