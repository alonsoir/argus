#!/usr/bin/env bash
# scripts/vigilancia/test_reglas_wazuh.sh — [VIGILANCIA-D321] ADR-060 8e.4d: test de cada regla de aRGus en el manager.
# Se ejecuta EN la VM wazuh como root (make test-vigilancia-reglas desde el Mac), con las reglas ya instaladas por
# wazuh_manager_desplegar.sh. Por cada caso de provisioning/wazuh/argus/tests/casos_reglas.tsv pasa la línea por
# wazuh-logtest y compara la regla y el nivel que salen con los esperados. Esperado "-": no debe saltar ninguna regla
# de aRGus (100500-100599). rc 0 solo si pasan todos. LC_ALL=C para que nada dependa del idioma de la VM.
set -u
LC_ALL=C; export LC_ALL
CASOS=${1:-/vagrant/provisioning/wazuh/argus/tests/casos_reglas.tsv}
LT=/var/ossec/bin/wazuh-logtest
[ -r "$CASOS" ] || { echo "[TEST-REGLAS] FALLA: no leo $CASOS"; exit 1; }
[ -x "$LT" ] || { echo "[TEST-REGLAS] FALLA: no existe $LT (¿es la VM del manager?)"; exit 1; }
pasa=0; falla=0
while IFS=$'\t' read -r nombre id nivel linea; do
  case "$nombre" in ''|'#'*) continue;; esac
  salida=$(printf '%s\n' "$linea" | timeout 30 "$LT" 2>&1)
  fase3=$(printf '%s\n' "$salida" | sed -n '/Phase 3/,$p')
  got_id=$(printf '%s\n' "$fase3" | sed -n "s/^[[:space:]]*id: '\([0-9]*\)'.*/\1/p" | head -n 1)
  got_lv=$(printf '%s\n' "$fase3" | sed -n "s/^[[:space:]]*level: '\([0-9]*\)'.*/\1/p" | head -n 1)
  if [ "$id" = "-" ]; then
    if [[ "${got_id:-0}" =~ ^1005[0-9][0-9]$ ]]; then ok=no; else ok=si; fi
  else
    if [ "$got_id" = "$id" ] && [ "$got_lv" = "$nivel" ]; then ok=si; else ok=no; fi
  fi
  if [ "$ok" = si ]; then
    pasa=$((pasa + 1)); echo "PASA  $nombre: regla ${got_id:-ninguna} nivel ${got_lv:--}"
  else
    falla=$((falla + 1)); echo "FALLA $nombre: esperada $id nivel $nivel, sale ${got_id:-ninguna} nivel ${got_lv:--}"
    printf '%s\n' "$salida" | sed -n '/Phase 2/,$p' | head -n 12 | sed 's/^/      | /'
  fi
done < "$CASOS"
echo "[TEST-REGLAS] $pasa PASA, $falla FALLA (wazuh-manager $(/var/ossec/bin/wazuh-control info 2>/dev/null | sed -n 's/^WAZUH_VERSION="\(.*\)"/\1/p'))"
[ "$falla" = 0 ]
