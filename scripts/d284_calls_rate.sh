#!/usr/bin/env bash
# DAY284 — serie de [ML-TIME]: calls acumuladas y delta por linea (~10 s). Solo observacion.
# Uso: d284_calls_rate.sh [LOG]
set -euo pipefail
LOG="${1:-/vagrant/logs/lab/sniffer.log}"
grep -n '\[ML-TIME\]' "$LOG" | LC_ALL=C awk -F'[: =]+' '
  { for (i=1;i<=NF;i++) if ($i=="calls") c=$(i+1)+0
    printf "linea=%s calls=%d delta=%d\n", $1, c, (NR>1 ? c-prev : 0); prev=c }'
