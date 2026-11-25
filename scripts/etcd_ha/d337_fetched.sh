#!/usr/bin/env bash
# Suma, por VM, las líneas "Fetched <tamaño> in <tiempo> (<velocidad>)" de apt en los logs de los pasos 4 y 6 de dos
# corridas del EMECAS: cuántas descargas, cuántos MB y cuántos segundos. Solo lee.
set -u
LC_ALL=C; export LC_ALL
for d in "logs/lab/emecas/20261124T190220_emecas+++" "logs/lab/emecas/20261125T094402_emecas+++"; do
  for p in 04_vagrant-up.log 06_vagrant-provision.log; do
    f="$d/$p"
    echo "== $f"
    [ -f "$f" ] || { echo "   (no existe)"; continue; }
    grep -E "Fetched [0-9.,]+ [kMG]?B in " "$f" | awk '
      {
        vm = "?"
        if (match($0, /^ *[a-z0-9-]+: /)) { vm = substr($0, RSTART, RLENGTH); gsub(/[ :]/, "", vm) }
        linea = $0; sub(/.*Fetched /, "", linea)
        split(linea, a, " "); n = a[1]; gsub(/,/, "", n); u = a[2]
        mb = n + 0
        if (u == "B") mb = mb / 1e6; else if (u == "kB") mb = mb / 1e3; else if (u == "GB") mb = mb * 1e3
        t = linea; sub(/^[^ ]+ [^ ]+ in /, "", t); sub(/ \(.*/, "", t)
        s = 0; m = split(t, b, " ")
        for (i = 1; i <= m; i++) {
          v = b[i]; x = v + 0
          if (v ~ /h$/) s += x * 3600; else if (v ~ /min$/) s += x * 60; else if (v ~ /s$/) s += x
        }
        nd[vm]++; tmb[vm] += mb; ts[vm] += s; TMB += mb; TS += s
      }
      END {
        for (vm in nd) printf "   %-10s %3d descargas %8.1f MB %6d s\n", vm, nd[vm], tmb[vm], ts[vm]
        printf "   %-10s %3s            %8.1f MB %6d s\n", "TOTAL", "", TMB, TS
      }' | sort
  done
done
