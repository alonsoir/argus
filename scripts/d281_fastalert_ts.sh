#!/usr/bin/env bash
# Por CSV de eventos del ml-detector (sin cabecera): filas fast-alert y cuantas con timestamp no-epoch (< 1.7e18 ns).
set -uo pipefail
for f in /vagrant/logs/ml-detector/events/*.csv; do
  LC_ALL=C awk -F, -v f="$(basename "$f")" '
    $2 ~ /^fast-alert-/ { fa++; if (($1+0) < 1.7e18) bad++ }
    END { if (fa>0) printf "%s fast_alert=%d ts_no_epoch=%d\n", f, fa, bad+0 }' "$f"
done
