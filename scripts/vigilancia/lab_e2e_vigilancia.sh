#!/usr/bin/env bash
# scripts/vigilancia/lab_e2e_vigilancia.sh — [VIGILANCIA-E2E-D322] ADR-060 8e.4d-3: E2E de la vigilancia de aRGus.
# Cada caso provoca algo en el lab y exige su alerta en el alerts.json del manager de Wazuh (VM wazuh), escrita después
# del inicio del caso (scripts/vigilancia/alertas_wazuh.sh). Decisiones de Alonso: dentro de lab-e2e (DAY321); C4
# provoca su propia divergencia y C8 solo mide en su primera corrida (DAY322).
# Se ejecuta EN EL MAC, desde la raíz del repo, con las VMs defender, client, control-1 y wazuh arriba:
#   DIA=dayNNN bash scripts/vigilancia/lab_e2e_vigilancia.sh NOMBRE        (make lab-e2e-vigilancia)
#
# PREDICCIÓN (escrita antes de la primera corrida, DAY322):
#   C1 FIM: crear un fichero en /etc/argus-pki da la 554 y borrarlo la 553 (agente control-1), cada una en < 30 s.
#   C2 disco: umbral_pct=1 da la 100541 (estado=ALTO) en < periodo_s + 30 s; restaurado con cmp.
#   C3 audit de Vault: chattr +i en audit.log y un login: HTTP 200 (sigue el device de syslog) y la 100520 en < 30 s.
#   C5 Falco: copiar la clave del desellado da la 100551 (argus_lab_clave_leida_ajeno) en < 30 s.
#   C6 Falco: leerla como nobody da la 100552 (argus_lab_clave_intento_fallido) en < 30 s.
#   C8 MEDIDA (sin PASA/FALLA): etcd parado durante un etcd-vm-check (--esperar 30) deja unas 15 x 17 = 255 trazas
#      NOTICE en Falco y otras tantas 100553 en el manager.
#      MEDIDO DAY322 (primera corrida): 14 trazas en Falco y 14 alertas 100553 (cada etcdctl espera su timeout: caben
#      un par de vueltas en 36 s, no 15). Desde entonces es criterio (decisión de Alonso): trazas de Falco <=
#      VIG_C8_MAX_TRAZAS y todas llegan al manager (alertas 100553 = trazas).
#   C7 d322_reinicio_vault.sh PASA (R1-R6).
#   C4 vigía: una divergencia (E1 de d320_vigia_e2e.sh) da la 100511 y luego la 100512 del agente defender.
# Trap: deshace todo lo de la VM etcd (lab_e2e_vigilancia_etcd.sh restaurar); C4 y C7 llevan su propio trap. El
# pipeline queda PARADO, como los demás E2E con la mitigación real (lab-e2e lo vuelve a arrancar al final).
# Parámetros (entorno), enteros: VIG_ESPERA_S [10, 600] defecto 45 (espera de cada alerta); VIG_ESPERA_DISCO_S
# [30, 900] defecto 120; VIG_ESPERA_ETCD_S [5, 300] defecto 30 (lo que espera el etcd-vm-check de C8);
# VIG_C8_MAX_TRAZAS [1, 100000] defecto 60 (unas 4 veces lo medido DAY322: 14; otro despliegue puede necesitar más).
set -u
LC_ALL=C; export LC_ALL
N=${1:?nombre de la corrida}
export DIA=${DIA:-day322}
DM=logs/lab/$DIA/$N
HW=/vagrant/scripts/vigilancia/alertas_wazuh.sh
HE=/vagrant/scripts/vigilancia/lab_e2e_vigilancia_etcd.sh
log() { echo "[VIG-E2E] $*"; }
entero() {  # nombre valor defecto min max -> VAL
  local n=$1 v=$2 d=$3 lo=$4 hi=$5
  if [ -z "$v" ]; then VAL=$d; log "$n=$d (defecto: ausente)"; return; fi
  if ! [[ "$v" =~ ^[0-9]+$ ]] || [ "$v" -lt "$lo" ] || [ "$v" -gt "$hi" ]; then
    VAL=$d; log "$n=$d (defecto: '$v' mal formado; entero en [$lo, $hi])"; return
  fi
  VAL=$v; log "$n=$v (entorno)"
}
entero VIG_ESPERA_S "${VIG_ESPERA_S:-}" 45 10 600; ESPERA=$VAL
entero VIG_ESPERA_DISCO_S "${VIG_ESPERA_DISCO_S:-}" 120 30 900; ESPERA_DISCO=$VAL
entero VIG_ESPERA_ETCD_S "${VIG_ESPERA_ETCD_S:-}" 30 5 300; ESPERA_ETCD=$VAL
entero VIG_C8_MAX_TRAZAS "${VIG_C8_MAX_TRAZAS:-}" 60 1 100000; C8_MAX=$VAL
mkdir -p "$DM"
T=$(mktemp /tmp/vig_e2e.XXXXXX)
FALLOS=0
V() { local m=$1; shift; vagrant ssh "$m" -c "$*" 2>/dev/null | tr -d '\r' | grep -v '^\[argus\]'; }
pinta() {  # lee $T: muestra las líneas E2E y cuenta las FALLA
  local l
  while IFS= read -r l; do
    case "$l" in
      E2E\|FALLA\|*) echo "  ❌ ${l#E2E|FALLA|}"; FALLOS=$((FALLOS + 1));;
      E2E\|OK\|*)    echo "  ✅ ${l#E2E|OK|}";;
      E2E\|*)        echo "     ${l#E2E|}";;
    esac
  done < "$T"
  cat "$T" >> "$DM/salida.txt"
}
valor() { sed -n "s/^E2E|$1|//p" "$T" | head -n 1; }
DESDE=""; INODO=""
marca() {  # punto de partida de un caso en el alerts.json
  V wazuh "bash $HW posicion" > "$T"; DESDE=$(valor DESDE); INODO=$(valor INODO)
  [[ "$DESDE" =~ ^[0-9]+$ ]] && [[ "$INODO" =~ ^[0-9]+$ ]] || { pinta; log "❌ no leo la posición de alerts.json"; exit 1; }
}
alerta() {  # agente espera_s regla [texto]
  V wazuh "bash $HW esperar $DESDE $INODO $2 $1 $3 '${4:-}'" > "$T"; pinta
}
etcd() { V control-1 "bash $HE $*" > "$T"; pinta; }
fin() {
  log "TRAP: restaurando la VM etcd"
  V control-1 "bash $HE restaurar" > "$T"; pinta
  rm -f "$T"
}
trap fin EXIT
trap 'exit 130' INT TERM

log "0 VMs y manager"
for m in defender client control-1 wazuh; do
  V "$m" "echo vivo" | grep -qx vivo || { log "❌ la VM $m no responde: vagrant up $m (lab-e2e-vigilancia la necesita)"; exit 1; }
done
V wazuh "systemctl is-active wazuh-manager; sudo /var/ossec/bin/agent_control -l" > "$T"
grep -qx active "$T" || { cat "$T"; log "❌ wazuh-manager no está en marcha en la VM wazuh"; exit 1; }
for a in control-1 defender; do
  grep -E "Name: $a, .*Active" "$T" > /dev/null || { cat "$T"; log "❌ el agente $a no está Active en el manager"; exit 1; }
done
log "   wazuh-manager en marcha; agentes control-1 y defender Active"

log "C1 FIM en /etc/argus-pki"
marca; etcd fim-crear; alerta control-1 "$ESPERA" 554 vigilancia-e2e.prueba
marca; etcd fim-borrar; alerta control-1 "$ESPERA" 553 vigilancia-e2e.prueba

log "C2 umbral del disco bajado"
marca; etcd disco-bajar; alerta control-1 "$ESPERA_DISCO" 100541 'estado=ALTO'
etcd disco-restaurar

log "C3 audit de fichero de Vault inmutable"
marca; etcd audit-romper; alerta control-1 "$ESPERA" 100520
etcd audit-restaurar

log "C5 lectura ajena de una clave (Falco CRITICAL)"
marca; etcd clave-copiar; alerta control-1 "$ESPERA" 100551 argus_lab_clave_leida_ajeno

log "C6 intento fallido de leer una clave (Falco WARNING)"
marca; etcd clave-intento; alerta control-1 "$ESPERA" 100552 argus_lab_clave_intento_fallido

log "C8 trazas de un etcd-vm-check con etcd parado (máximo $C8_MAX, y todas en el manager)"
marca; D8=$DESDE; I8=$INODO
V control-1 "bash $HE falco-lineas" > "$T"; pinta; L8=$(valor LINEAS)
if ! [[ "$L8" =~ ^[0-9]+$ ]]; then
  echo "  ❌ C8 sin el nº de líneas de partida de Falco: no se mide"; FALLOS=$((FALLOS + 1))
else
  etcd etcd-parar
  t0=$SECONDS
  V control-1 "bash /vagrant/scripts/etcd_ha/etcd_vm_estado.sh --estricto --esperar $ESPERA_ETCD" > "$DM/c8_etcd_vm_check.txt"
  log "   etcd-vm-check con etcd parado: $(( SECONDS - t0 )) s ($DM/c8_etcd_vm_check.txt)"
  etcd etcd-arrancar
  V control-1 "bash /vagrant/scripts/etcd_ha/d322_medir_falco_admin.sh $L8" > "$DM/c8_falco.txt"
  log "   Falco (VM etcd), eventos desde la línea $L8:"; grep -E '^ +[0-9]+ ' "$DM/c8_falco.txt" | sed 's/^/     /'
  F8=$(grep -E '^ +[0-9]+  argus_lab_clave_leida_admin \(Notice\)$' "$DM/c8_falco.txt" | awk '{print $1}' | head -n 1)
  F8=${F8:-0}
  W8=""; t0=$SECONDS   # que el agente mande lo último: hasta ESPERA s a que el manager tenga las F8
  while :; do
    V wazuh "bash $HW contar $D8 $I8 control-1 100553" > "$T"; W8=$(valor CUENTA)
    [[ "$W8" =~ ^[0-9]+$ ]] && [ "$W8" -ge "$F8" ] && break
    [ $(( SECONDS - t0 )) -ge "$ESPERA" ] && break
    sleep 3
  done
  echo "C8 trazas_falco=$F8 alertas_100553=${W8:-?} maximo=$C8_MAX espera_s=$ESPERA_ETCD" >> "$DM/medidas.txt"
  if [ "$F8" -le "$C8_MAX" ] && [ "${W8:-x}" = "$F8" ]; then
    echo "  ✅ C8 $F8 trazas NOTICE en Falco (máximo $C8_MAX) y las $W8 en el manager (100553)"
  else
    echo "  ❌ C8 $F8 trazas en Falco (máximo $C8_MAX), ${W8:-?} alertas 100553 en el manager (tienen que ser las mismas)"
    FALLOS=$((FALLOS + 1))
  fi
fi

log "C7 reinicio de Vault sin Vagrant (d322_reinicio_vault.sh)"
bash scripts/etcd_ha/d322_reinicio_vault.sh > "$DM/c7_reinicio_vault.txt" 2>&1; r=$?
grep -E '✅|❌' "$DM/c7_reinicio_vault.txt" | sed 's/^/  /'
[ "$r" = 0 ] && echo "  ✅ C7 d322_reinicio_vault.sh PASA" || { echo "  ❌ C7 d322_reinicio_vault.sh rc=$r ($DM/c7_reinicio_vault.txt)"; FALLOS=$((FALLOS + 1)); }

log "C4 divergencia del vigía (d320_vigia_e2e.sh solo con E1; arranca y para el pipeline)"
marca
D320_EVENTOS=E1 bash scripts/etcd_ha/d320_vigia_e2e.sh "${N}_vigia" > "$DM/c4_vigia.txt" 2>&1; r=$?
grep -E '^(PASA|FALLA|PARADA)' "$DM/c4_vigia.txt" | sed 's/^/     d320: /'
[ "$r" = 0 ] || { echo "  ❌ C4 d320_vigia_e2e.sh rc=$r ($DM/c4_vigia.txt)"; FALLOS=$((FALLOS + 1)); }
alerta defender "$ESPERA" 100511 PROTEGIDOS-DIVERGENCIA
alerta defender "$ESPERA" 100512 PROTEGIDOS-RECONCILIADO

echo
if [ "$FALLOS" = 0 ]; then log "✅ PASA lab-e2e-vigilancia — $DM/"; exit 0
else log "❌ NO PASA: $FALLOS fallo(s) — $DM/"; exit 1; fi
