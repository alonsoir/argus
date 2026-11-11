#!/usr/bin/env bash
# scripts/vigilancia/wazuh_manager_desplegar.sh — [VIGILANCIA-D321] ADR-060 8e.4d: la vigilancia de aRGus en el manager.
# Se ejecuta EN la VM wazuh como root: aprovisionador "argus-vigilancia" del Vagrantfile (run: always) y
# make vigilancia-manager-deploy desde el Mac. Todo sale de provisioning/wazuh/ (nada en el código):
#   VERSION                       versión exacta del manager y de los agentes (4.14.10-1)
#   argus/decoders/*.xml          -> /var/ossec/etc/decoders/
#   argus/rules/*.xml             -> /var/ossec/etc/rules/
#   argus/shared/<grupo>/agent.conf -> /var/ossec/etc/shared/<grupo>/agent.conf (el manager lo reparte)
#   argus/grupos.tsv              agente -> grupo
# Pasos: 1 la versión instalada es la de VERSION; 2 copia lo que cambie (con copia de lo anterior), verify-agent-conf de
# cada grupo y wazuh-analysisd -t; si algo no valida, se restaura lo anterior y rc 1 (todo o nada). Medido DAY321:
# verify-agent-conf rechaza un agent.conf mal formado, pero NO una opción desconocida dentro de <syscheck>; eso solo lo
# ve el agente al recibirla (lo comprueba el E2E de la vigilancia); 3 reinicia el manager
# solo si algo cambió y espera a analysisd; 4 asigna cada agente registrado a su grupo (los que aún no están registrados
# se avisan y se asignan en el siguiente despliegue); 5 test de las reglas (test_reglas_wazuh.sh).
# agent_groups devuelve rc 0 aunque falle (medido DAY321: "Internal error: Error 1017" con rc 0): cada paso suyo se
# comprueba por su resultado (el directorio del grupo existe, el agente sale en su grupo), no por el código de salida.
# Variable de entorno solo para el banco de Claude (chroot sin systemd): WAZUH_REINICIO, orden de reinicio del manager.
set -u
LC_ALL=C; export LC_ALL
SRC=${VIGILANCIA_SRC:-/vagrant/provisioning/wazuh}
O=/var/ossec
REINICIO=${WAZUH_REINICIO:-systemctl restart wazuh-manager}
log() { echo "[VIGILANCIA-MANAGER] $*"; }
fallo() { echo "[VIGILANCIA-MANAGER] FALLA: $*"; exit 1; }

# 1 versión
[ -r "$SRC/VERSION" ] || fallo "no leo $SRC/VERSION"
QUIERO=$(tr -d '[:space:]' < "$SRC/VERSION")
[[ "$QUIERO" =~ ^[0-9]+\.[0-9]+\.[0-9]+-[0-9]+$ ]] || fallo "$SRC/VERSION mal formado ('$QUIERO'; formato X.Y.Z-N)"
TENGO=$(dpkg-query -W -f='${Version}' wazuh-manager 2>/dev/null)
[ "$TENGO" = "$QUIERO" ] || fallo "wazuh-manager instalado '$TENGO', se exige '$QUIERO' ($SRC/VERSION). Desde el Mac: vagrant provision wazuh --provision-with install-wazuh"
log "wazuh-manager $TENGO (= $SRC/VERSION)"

# 2 copiar con respaldo, validar; si no valida, restaurar
BK=$(mktemp -d /tmp/argus_vigilancia_bk.XXXXXX)
CAMBIOS=0
declare -a PUESTOS=()
poner() {  # origen destino
  local o=$1 d=$2
  if [ -f "$d" ] && cmp -s "$o" "$d"; then return 0; fi
  mkdir -p "$BK$(dirname "$d")"
  if [ -f "$d" ]; then cp -p "$d" "$BK$d"; else : > "$BK$d.nuevo"; fi
  PUESTOS+=("$d")
  install -m 0660 -o wazuh -g wazuh "$o" "$d" || { restaurar; fallo "no se pudo poner $d: restaurado lo anterior"; }
  CAMBIOS=$((CAMBIOS + 1)); log "puesto $d"
}
restaurar() {
  local d
  for d in "${PUESTOS[@]}"; do
    if [ -f "$BK$d" ]; then cp -p "$BK$d" "$d"; else rm -f "$d"; fi
    log "restaurado $d"
  done
}
for f in "$SRC"/argus/decoders/*.xml; do poner "$f" "$O/etc/decoders/$(basename "$f")"; done
for f in "$SRC"/argus/rules/*.xml; do poner "$f" "$O/etc/rules/$(basename "$f")"; done
GRUPOS=$(awk -F'\t' '!/^#/ && NF == 2 {print $2}' "$SRC/argus/grupos.tsv" | sort -u)
[ -n "$GRUPOS" ] || fallo "$SRC/argus/grupos.tsv sin grupos (formato: agente<TAB>grupo)"
for g in $GRUPOS; do
  [[ "$g" =~ ^[a-z0-9-]{1,64}$ ]] || fallo "grupo '$g' mal formado en grupos.tsv ([a-z0-9-], de 1 a 64)"
  [ -r "$SRC/argus/shared/$g/agent.conf" ] || fallo "falta $SRC/argus/shared/$g/agent.conf"
  if [ ! -d "$O/etc/shared/$g" ]; then
    "$O/bin/agent_groups" -a -g "$g" -q > /tmp/argus_grupo_$g.txt 2>&1
    [ -d "$O/etc/shared/$g" ] || { cat /tmp/argus_grupo_$g.txt; restaurar; fallo "no se pudo crear el grupo $g (agent_groups)"; }
    log "grupo $g creado"
  fi
  poner "$SRC/argus/shared/$g/agent.conf" "$O/etc/shared/$g/agent.conf"
  "$O/bin/verify-agent-conf" -f "$O/etc/shared/$g/agent.conf" > /tmp/argus_verify_$g.txt 2>&1 \
    || { cat /tmp/argus_verify_$g.txt; restaurar; fallo "verify-agent-conf rechaza el agent.conf de $g: restaurado lo anterior"; }
done
if ! "$O/bin/wazuh-analysisd" -t > /tmp/argus_analysisd_t.txt 2>&1; then
  grep -E "ERROR|CRITICAL" /tmp/argus_analysisd_t.txt | grep -v "resource limit" | head -n 5
  restaurar; fallo "wazuh-analysisd -t no valida decoders/reglas: restaurado lo anterior"
fi
log "validado: verify-agent-conf de $(echo $GRUPOS | wc -w) grupos y wazuh-analysisd -t; $CAMBIOS ficheros cambiados"

# 3 reinicio solo si algo cambió
if [ "$CAMBIOS" -gt 0 ]; then
  $REINICIO || fallo "no se pudo reiniciar el manager ($REINICIO)"
  ok=0
  for i in $(seq 1 60); do [ -S "$O/queue/sockets/logtest" ] && pgrep -f "$O/bin/wazuh-analysisd" > /dev/null && { ok=1; break; }; sleep 2; done
  [ "$ok" = 1 ] || fallo "wazuh-analysisd no está arriba 120 s después de reiniciar"
  log "manager reiniciado"
else
  log "sin cambios: no se reinicia"
fi

# 4 agentes -> grupos
LISTA=$("$O/bin/manage_agents" -l 2>/dev/null)
while IFS=$'\t' read -r agente grupo; do
  case "$agente" in ''|'#'*) continue;; esac
  id=$(printf '%s\n' "$LISTA" | sed -n "s/^ *ID: \([0-9]*\), Name: $agente, .*/\1/p" | head -n 1)
  if [ -z "$id" ]; then
    log "AVISO agente '$agente' sin registrar todavía en el manager: se asignará a $grupo en el siguiente despliegue"
    continue
  fi
  if "$O/bin/agent_groups" -s -i "$id" 2>/dev/null | grep -qw -- "$grupo"; then
    log "agente $agente ($id) ya en $grupo"
  else
    "$O/bin/agent_groups" -a -i "$id" -g "$grupo" -q > /tmp/argus_asigna.txt 2>&1
    "$O/bin/agent_groups" -s -i "$id" 2>/dev/null | grep -qw -- "$grupo" \
      || { cat /tmp/argus_asigna.txt; fallo "no se pudo asignar $agente ($id) a $grupo (agent_groups)"; }
    log "agente $agente ($id) asignado a $grupo"
  fi
done < "$SRC/argus/grupos.tsv"

# 5 test de las reglas: forma parte del todo o nada. Medido DAY321: unas reglas con un if_sid que no existe pasan
# wazuh-analysisd -t y solo las caza el test; si no pasa, se restaura lo anterior y se reinicia otra vez.
if ! bash "$(dirname "$0")/test_reglas_wazuh.sh" "$SRC/argus/tests/casos_reglas.tsv"; then
  restaurar
  if [ "$CAMBIOS" -gt 0 ]; then $REINICIO || log "AVISO no se pudo reiniciar tras restaurar ($REINICIO)"; fi
  fallo "el test de las reglas no pasa: restaurado lo anterior y reiniciado el manager"
fi
rm -rf "$BK"
log "HECHO"
