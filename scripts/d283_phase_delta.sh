#!/usr/bin/env bash
# DAY283 — delta de [ML-PHASE] entre dos lineas (antes/despues de una carga).
# Uso: d283_phase_delta.sh FICHERO_ANTES FICHERO_DESPUES  (cada uno con una linea [ML-PHASE])
set -euo pipefail
B=${1:?antes}; A=${2:?despues}
LC_ALL=C awk '
function parse(line, tag,   n,f,i,name,rest,p,sum,h,m,j,bc,hh) {
  n = split(line, f, " ")
  for (i = 1; i <= n; i++) {
    if (f[i] ~ /^calls=/) { sub(/^calls=/, "", f[i]); calls[tag] = f[i] + 0; continue }
    if (index(f[i], "=") == 0 || index(f[i], "|") == 0) continue
    name = f[i]; sub(/=.*/, "", name)
    rest = f[i]; sub(/^[^=]*=/, "", rest)
    p = index(rest, "|"); sum = substr(rest, 1, p - 1); h = substr(rest, p + 1)
    S[tag, name] = sum + 0; names[name] = 1
    m = split(h, hh, ",")
    for (j = 1; j <= m; j++) { if (hh[j] == "") continue; split(hh[j], bc, ":"); H[tag, name, bc[1] + 0] = bc[2] + 0 }
  }
}
NR == 1 { parse($0, "B"); next }
NR == 2 { parse($0, "A"); next }
END {
  dc = calls["A"] - calls["B"]
  printf "calls=%d\n", dc
  if (dc <= 0) { print "PARAR: sin llamadas nuevas entre las dos lineas"; exit 1 }
  tot = 0
  for (k in names) { ds[k] = S["A", k] - S["B", k]; tot += ds[k] }
  printf "%-9s %7s %10s %6s %6s\n", "fase", "%suma", "media_us", "med_b", "p99_b"
  split("extract ddos ransom traffic internal post", ord, " ")
  for (o = 1; o <= 6; o++) {
    k = ord[o]; med = -1; p99 = -1; c = 0
    for (b = 0; b < 40; b++) {
      c += H["A", k, b] - H["B", k, b]
      if (med < 0 && c >= dc * 0.5)  med = b
      if (p99 < 0 && c >= dc * 0.99) p99 = b
    }
    printf "%-9s %6.1f%% %10.2f %6d %6d\n", k, 100 * ds[k] / tot, ds[k] / dc / 1000, med, p99
  }
  printf "total_media_us=%.2f\n", tot / dc / 1000
}' "$B" "$A"
