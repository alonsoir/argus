#!/usr/bin/env bash
# DAY290 — suma de overhead por hilo (pid) en un perf report --sort pid,symbol. SOLO LECTURA.
# Uso: bash day290_perf_por_hilo.sh <perf_pid_sym_*.txt>
set -eu
IN="$1"
LC_ALL=C awk '
/^ +[0-9.]+% +[0-9]+:/ {
  pct = $1; sub(/%/, "", pct); pct += 0
  pid = $2
  sym = ""
  for (i = 4; i <= NF; i++) sym = sym (i > 4 ? " " : "") $i
  if (length(sym) > 90) sym = substr(sym, 1, 90) "..."
  tot[pid] += pct
  if (pct > best[pid]) { best[pid] = pct; bsym[pid] = $3 " " sym }
  all += pct
}
END {
  printf "%-22s %8s   %s\n", "pid:comm", "pct", "simbolo principal (pct)"
  for (p in tot) printf "%-22s %7.2f%%   %s (%.2f%%)\n", p, tot[p], bsym[p], best[p]
  printf "TOTAL sumado: %.2f%%\n", all
}' "$IN" | sort -t'%' -k1,1 -r
