#!/usr/bin/env bash
# scripts/vigilancia/falco_instalar.sh — [VIGILANCIA-D321] ADR-060 8e.4d: Falco y las reglas de aRGus, desde el repositorio
# apt firmado de Falco (download.falco.org) y en la versión fija de provisioning/falco/VERSION.
# Se ejecuta EN la VM etcd y en el defender, como root: aprovisionador "falco" del Vagrantfile (run: always).
# Lee de provisioning/falco/ (nada en el código):
#   VERSION            versión exacta del paquete falco
#   CLAVE              huella de la clave de firma de Falco (lib_apt_oficial.sh)
#   argus_lab.yaml     reglas de aRGus           -> /etc/falco/rules.d/argus_lab.yaml
#   argus_salida.yaml  motor, salida y reglas activas -> /etc/falco/config.d/argus_salida.yaml
# Driver modern_ebpf (medido DAY321 en las dos VMs: BTF presente) y SIN falcoctl-artifact-follow: las reglas solo cambian
# con un despliegue (el paquete lo enmascara con FALCOCTL_ENABLED=no; aquí se comprueba). Servicio: falco-modern-bpf.
# Pasos: 1 instala (o actualiza/baja) a VERSION y hold, solo si hace falta; 2 pone los dos ficheros si cambian (con copia
# de lo anterior) y valida con falco --dry-run: tiene que cargar argus_lab.yaml UNA vez y quedar activas exactamente sus
# reglas (las "- rule:" del fichero); si no, se restaura lo anterior y rc 1 (todo o nada); 3 /var/log/falco, el fichero
# de eventos (lo lee el agente de Wazuh: sin él, el agente da ERROR 1103 hasta el primer evento) y su logrotate;
# 4 reinicia falco-modern-bpf solo si algo cambió o no está en marcha, y comprueba que queda en marcha.
set -u
LC_ALL=C; export LC_ALL
SRC=${VIGILANCIA_FALCO_SRC:-/vagrant/provisioning/falco}
LIB=$(dirname "$0")/lib_apt_oficial.sh
UNIDAD=falco-modern-bpf.service
REGLAS=/etc/falco/rules.d/argus_lab.yaml
SALIDA=/etc/falco/config.d/argus_salida.yaml
EVENTOS=/var/log/falco/eventos.json
ROTA=/etc/logrotate.d/argus-falco
log() { echo "[VIGILANCIA-FALCO] $*"; }
fallo() { echo "[VIGILANCIA-FALCO] FALLA: $*"; exit 1; }

[ "$(id -u)" = 0 ] || fallo "hay que ejecutarlo como root"
for f in VERSION CLAVE argus_lab.yaml argus_salida.yaml; do [ -r "$SRC/$f" ] || fallo "no leo $SRC/$f"; done
V=$(tr -d '[:space:]' < "$SRC/VERSION")
[[ "$V" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || fallo "$SRC/VERSION mal formado ('$V'; formato X.Y.Z)"
N_REGLAS=$(grep -c '^- rule:' "$SRC/argus_lab.yaml")
[ "$N_REGLAS" -ge 1 ] || fallo "$SRC/argus_lab.yaml sin reglas"
# shellcheck source=lib_apt_oficial.sh
. "$LIB" || fallo "no cargo $LIB"
CAMBIOS=0

# 1 paquete
TENGO=$(dpkg-query -W -f='${Version}' falco 2>/dev/null || true)
FIJADO=$(apt-mark showhold falco 2>/dev/null)
if [ "$TENGO" = "$V" ] && [ "$FIJADO" = falco ]; then
  log "falco $V ya instalado y fijado"
else
  log "estado: instalado '${TENGO:-ninguno}', hold '${FIJADO:-no}'; se instala falco $V"
  repo_oficial falcosecurity https://falco.org/repo/falcosecurity-packages.asc "$SRC/CLAVE" \
    https://download.falco.org/packages/deb "stable main" || fallo "repositorio de Falco"
  apt-get update -qq || fallo "apt-get update"
  # Sin diálogos: driver modern_ebpf y sin seguimiento automático de reglas (postinst del paquete 0.43.1).
  FALCO_FRONTEND=noninteractive FALCO_DRIVER_CHOICE=modern_ebpf FALCOCTL_ENABLED=no \
    instalar_fijado falco "$V" || fallo "instalación de falco $V"
  CAMBIOS=$((CAMBIOS + 1))
fi
[ "$(systemctl is-enabled falcoctl-artifact-follow.service 2>/dev/null)" = masked ] \
  || fallo "falcoctl-artifact-follow no está enmascarado: las reglas se actualizarían solas desde Internet"

# 2 ficheros, con respaldo y validación
BK=$(mktemp -d /tmp/argus_falco_bk.XXXXXX)
declare -a PUESTOS=()
poner() {  # origen destino
  local o=$1 d=$2
  if [ -f "$d" ] && cmp -s "$o" "$d"; then return 0; fi
  mkdir -p "$BK$(dirname "$d")" "$(dirname "$d")"
  if [ -f "$d" ]; then cp -p "$d" "$BK$d"; else : > "$BK$d.nuevo"; fi
  PUESTOS+=("$d")
  install -m 0644 -o root -g root "$o" "$d" || { restaurar; fallo "no se pudo poner $d: restaurado lo anterior"; }
  CAMBIOS=$((CAMBIOS + 1)); log "puesto $d"
}
restaurar() {
  local d
  for d in "${PUESTOS[@]}"; do
    if [ -f "$BK$d" ]; then cp -p "$BK$d" "$d"; else rm -f "$d"; fi
    log "restaurado $d"
  done
}
poner "$SRC/argus_lab.yaml" "$REGLAS"
poner "$SRC/argus_salida.yaml" "$SALIDA"
SECO=$(falco -c /etc/falco/falco.yaml --dry-run -o log_level=debug 2>&1); RC=$?
CARGAS=$(grep -cF "$REGLAS |" <<< "$SECO")
ACTIVAS=$(sed -n 's/.*: (\([0-9]*\)) enabled rules in total.*/\1/p' <<< "$SECO" | tail -1)
if [ "$RC" -ne 0 ] || [ "$CARGAS" != 1 ] || [ "$ACTIVAS" != "$N_REGLAS" ]; then
  echo "$SECO" | tail -20
  restaurar
  fallo "falco --dry-run: rc $RC, $REGLAS cargado $CARGAS veces (se exige 1), ${ACTIVAS:-?} reglas activas (se exigen $N_REGLAS): restaurado lo anterior"
fi
log "falco --dry-run OK: $REGLAS cargado una vez, $ACTIVAS reglas activas ($(sed -n 's/.*: (\([0-9]*\)) syscalls in rules: \(.*\)/\1 syscalls: \2/p' <<< "$SECO" | tail -1))"

# 3 eventos y su rotación (UMask=0077 de la unidad: Falco los crea 0600; el agente de Wazuh lee como root)
install -d -m 0750 -o root -g root /var/log/falco
[ -f "$EVENTOS" ] || install -m 0600 -o root -g root /dev/null "$EVENTOS"
cat > "$BK/rota" <<'LOGROTATE'
# [VIGILANCIA-D321] generado por scripts/vigilancia/falco_instalar.sh; no editar a mano
# Falco abre y cierra el fichero en cada evento (file_output.keep_alive: false): basta con renombrarlo.
/var/log/falco/eventos.json {
  daily
  rotate 14
  missingok
  notifempty
  compress
  delaycompress
  create 0600 root root
}
LOGROTATE
if ! cmp -s "$BK/rota" "$ROTA"; then
  install -m 0644 -o root -g root "$BK/rota" "$ROTA"; log "puesto $ROTA"
fi
command -v logrotate >/dev/null || apt-get install -y logrotate >/dev/null
logrotate -d "$ROTA" >/dev/null 2>&1 || fallo "logrotate rechaza $ROTA"

# 4 servicio (una sola unidad de Falco: dos a la vez cargarían dos sondas y duplicarían cada evento)
for u in falco-kmod falco-bpf falco-custom; do
  ! systemctl is-active --quiet "$u.service" || fallo "$u.service está en marcha: solo debe correr $UNIDAD"
done
systemctl enable "$UNIDAD" >/dev/null 2>&1 || fallo "systemctl enable $UNIDAD"
if [ "$CAMBIOS" -gt 0 ] || ! systemctl is-active --quiet "$UNIDAD"; then
  systemctl restart "$UNIDAD" || fallo "systemctl restart $UNIDAD (journalctl -u $UNIDAD)"
  sleep 5
fi
systemctl is-active --quiet "$UNIDAD" || fallo "$UNIDAD no queda en marcha (journalctl -u $UNIDAD)"
rm -rf "$BK"
log "OK: falco $V, $UNIDAD en marcha, $N_REGLAS reglas de aRGus, eventos en $EVENTOS ($CAMBIOS cambios)"
