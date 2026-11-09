#!/usr/bin/env bash
# scripts/vigilancia/wazuh_agente_instalar.sh — [VIGILANCIA-D321] ADR-060 8e.4d: el agente de Wazuh, desde el repositorio
# apt firmado de Wazuh y en la versión fija de provisioning/wazuh/VERSION (la misma que el manager). Sustituye a la
# instalación por dpkg de un .deb guardado en el repo (DAY321: su origen no constaba; un hospital exige que todo el
# software de terceros venga de su mantenedor, con su firma).
# Se ejecuta EN cada VM con agente, como root: aprovisionador "wazuh-agent" del Vagrantfile (run: always), con
# AGENT_NAME (nombre con el que se registra; su grupo sale de provisioning/wazuh/argus/grupos.tsv en el manager).
# Lee de provisioning/wazuh/ (nada en el código):
#   VERSION   versión exacta (X.Y.Z-N)
#   MANAGER   IPv4 del manager
#   CLAVE     huella de la clave de firma de Wazuh (lib_apt_oficial.sh)
# Pasos: 1 si ya está esa versión, fijada, apuntando a MANAGER y en marcha, nada que hacer (rc 0); 2 repo oficial con la
# clave comprobada; 3 instala (o actualiza/baja) a VERSION y hold; 4 el agente apunta a MANAGER y está en marcha; 5 espera
# a que conecte con el manager (hasta ESPERA_S, 120 s por defecto: medido DAY321, al actualizar el manager los agentes
# tardaron ~80 s en volver). Que no conecte se avisa pero no es fallo: la VM wazuh es autostart: false y puede estar
# parada; el agente se conecta solo cuando el manager vuelve.
# Una actualización conserva client.keys y ossec.conf (el registro sigue siendo el mismo agente).
set -u
LC_ALL=C; export LC_ALL
SRC=${VIGILANCIA_SRC:-/vagrant/provisioning/wazuh}
LIB=$(dirname "$0")/lib_apt_oficial.sh
O=/var/ossec
ESPERA_S=${ESPERA_S:-120}
log() { echo "[VIGILANCIA-AGENTE] $*"; }
fallo() { echo "[VIGILANCIA-AGENTE] FALLA: $*"; exit 1; }

[ "$(id -u)" = 0 ] || fallo "hay que ejecutarlo como root"
NOMBRE=${AGENT_NAME:-}
[[ "$NOMBRE" =~ ^[a-z0-9-]{1,64}$ ]] || fallo "AGENT_NAME '$NOMBRE' ausente o mal formado ([a-z0-9-], de 1 a 64)"
[[ "$ESPERA_S" =~ ^[0-9]+$ ]] && [ "$ESPERA_S" -le 600 ] || fallo "ESPERA_S '$ESPERA_S' fuera de rango [0, 600]"
for f in VERSION MANAGER CLAVE; do [ -r "$SRC/$f" ] || fallo "no leo $SRC/$f"; done
V=$(tr -d '[:space:]' < "$SRC/VERSION")
[[ "$V" =~ ^[0-9]+\.[0-9]+\.[0-9]+-[0-9]+$ ]] || fallo "$SRC/VERSION mal formado ('$V'; formato X.Y.Z-N)"
M=$(tr -d '[:space:]' < "$SRC/MANAGER")
[[ "$M" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] || fallo "$SRC/MANAGER mal formado ('$M'; una IPv4)"
# shellcheck source=lib_apt_oficial.sh
. "$LIB" || fallo "no cargo $LIB"
log "agente '$NOMBRE', versión $V ($SRC/VERSION), manager $M ($SRC/MANAGER)"

apunta() { grep -q "<address>$M</address>" "$O/etc/ossec.conf" 2>/dev/null; }
en_marcha() { systemctl is-active --quiet wazuh-agent; }

# 1 nada que hacer
TENGO=$(dpkg-query -W -f='${Version}' wazuh-agent 2>/dev/null || true)
FIJADO=$(apt-mark showhold wazuh-agent 2>/dev/null)
if [ "$TENGO" = "$V" ] && [ "$FIJADO" = wazuh-agent ] && apunta && en_marcha; then
  log "OK: wazuh-agent $V ya instalado, fijado, apuntando a $M y en marcha; nada que hacer"
  exit 0
fi
log "estado: instalado '${TENGO:-ninguno}', hold '${FIJADO:-no}'"

# 2 y 3 repo oficial e instalación fijada
repo_oficial wazuh https://packages.wazuh.com/key/GPG-KEY-WAZUH "$SRC/CLAVE" \
  https://packages.wazuh.com/4.x/apt/ "stable main" || fallo "repositorio de Wazuh"
apt-get update -qq || fallo "apt-get update"
# WAZUH_MANAGER/WAZUH_AGENT_NAME solo los usa una instalación nueva; una actualización conserva ossec.conf.
WAZUH_MANAGER="$M" WAZUH_AGENT_NAME="$NOMBRE" instalar_fijado wazuh-agent "$V" || fallo "instalación de wazuh-agent $V"

# 4 apunta a MANAGER y en marcha
apunta || fallo "$O/etc/ossec.conf no apunta a $M (¿agente registrado antes con otro manager? revisar <client><server>)"
systemctl daemon-reload
systemctl enable wazuh-agent >/dev/null 2>&1 || fallo "systemctl enable wazuh-agent"
systemctl restart wazuh-agent || fallo "systemctl restart wazuh-agent"
en_marcha || fallo "wazuh-agent no queda en marcha (journalctl -u wazuh-agent)"

# 5 conexión con el manager (aviso, no fallo)
EST=$O/var/run/wazuh-agentd.state
for ((i = 0; i < ESPERA_S; i += 5)); do
  grep -q "^status='connected'" "$EST" 2>/dev/null && break
  sleep 5
done
if grep -q "^status='connected'" "$EST" 2>/dev/null; then
  log "OK: wazuh-agent $V en marcha y conectado a $M"
else
  log "AVISO: wazuh-agent $V en marcha pero sin conectar con $M en ${ESPERA_S} s ($(grep '^status=' "$EST" 2>/dev/null || echo "sin $EST")); ¿VM wazuh parada?"
fi
exit 0
