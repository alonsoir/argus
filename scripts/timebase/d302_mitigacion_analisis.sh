#!/usr/bin/env bash
# DAY302 analisis del E2E de la mitigacion ddos_v2 (Mac). Criterios PASA/FALLA escritos ANTES de la corrida.
# Uso: bash scripts/timebase/d302_mitigacion_analisis.sh logs/lab/day302/NOMBRE ; rc 0 = PASA todo
set -u
export LC_ALL=C
DM=${1:?directorio de la corrida}
F=logs/lab/firewall-agent.log
M=$DM/muestreo.txt
C=$DM/cliente.txt
for f in "$F" "$M" "$C"; do [ -s "$f" ] || { echo "ABORTA: falta o esta vacio $f"; exit 2; }; done
echo "== modo y aviso de escalera de prueba"
grep -m 1 "\[DDOS-MITIGACION\] modo:" "$F"
echo "CONFIG-AVISO ddos_mitigacion (periodico): $(grep -c 'CONFIG-AVISO\] ddos_mitigacion' "$F")"
echo "== INICIO y FIN de la sombra"
grep -e "\[SOMBRA-DDOS\] INICIO" -e "\[SOMBRA-DDOS\] FIN" "$F"
echo "== BLOQUEAR (un strike por episodio)"
grep "\[DDOS-MITIGACION\] BLOQUEAR " "$F"
echo "== acciones por origen (activo: una linea por accion)"
grep -E "\[DDOS-MITIGACION\] (BLOQUEAR|RENOVAR) " "$F" | awk '{for (i = 1; i <= NF; i++) if ($i ~ /^origen=/) print $2, $i}' | sort | uniq -c
echo "RECHAZADO: $(grep -c '\[DDOS-MITIGACION\] RECHAZADO' "$F")"
echo "ALERTA_PROTEGIDO (detalle, con tope): $(grep -c 'ALERTA_PROTEGIDO origen=' "$F")"
grep "\[SOMBRA-DDOS\] protegidos:" "$F" | tail -n 1
echo "== ultimo resumen de la mitigacion"
grep "\[DDOS-MITIGACION\] resumen:" "$F" | tail -n 1
r50=$(grep -c "\[DDOS-MITIGACION\] RENOVAR origen=192.168.100.50 " "$F")
echo "C6 (medida) RENOVAR de .50 = $r50 (> 0: el sniffer sigue viendo el trafico ya bloqueado; XDP va antes que netfilter)"
echo "== criterios"
awk -v ENT_MAX=15 -v SAL1_MIN=55 -v SAL1_MAX=90 -v SAL2_MIN=115 -v SAL2_MAX=150 '
function v(ok) { return ok ? "PASA" : "FALLA" }
FNR == NR { if (NF >= 2 && $2 ~ /^[0-9]+(\.[0-9]+)?$/) mk[$1] = $2 + 0; next }
$1 == "S" {
  t = $2 + 0
  split($3, a, "="); dp = a[2] + 0
  mem = $4; sub(/^miembros=/, "", mem)
  p50 = index(mem, "192.168.100.50:")
  if (index(mem, "192.168.100.61:") > 0) n61++
  if (index(mem, "192.168.100.51:") > 0) n51++
  to50 = ""; co50 = ""
  if (p50) { s = substr(mem, p50); sub(/;.*/, "", s); split(s, b, ":"); to50 = b[2]; co50 = b[3] }
  ns++
  if (t >= mk["inicio_ataque1"] && t < mk["inicio_ataque2"]) {
    if (p50 && !e1) { e1 = t; to_e1 = to50; co_e1 = co50; dp_e1 = dp }
    if (p50 && dp > dpmax1) dpmax1 = dp
    if (e1 && !p50 && !s1) s1 = t
  }
  if (t >= mk["inicio_ataque2"]) {
    if (p50 && !e2) { e2 = t; to_e2 = to50; co_e2 = co50 }
    if (e2 && !p50 && !s2) s2 = t
  }
}
END {
  ia1 = mk["inicio_ataque1"]; fa1 = mk["fin_ataque1"]; ia2 = mk["inicio_ataque2"]; fa2 = mk["fin_ataque2"]
  printf "muestras=%d ataque1=[%.1f, %.1f] ataque2=[%.1f, %.1f]\n", ns, ia1, fa1, ia2, fa2
  c1 = (e1 > 0 && e1 - ia1 <= ENT_MAX)
  printf "C1 %s .50 entra en el set %s s tras inicio_ataque1 (max %d); timeout al entrar=%s comentario=%s\n", v(c1), (e1 ? sprintf("%.1f", e1 - ia1) : "nunca"), ENT_MAX, to_e1, co_e1
  c2 = (e1 > 0 && dpmax1 > dp_e1)
  printf "C2 %s contador de la regla DROP: %d al entrar -> %d max en el ataque 1\n", v(c2), dp_e1, dpmax1
  c3 = (n61 == 0 && n51 == 0)
  printf "C3 %s .61 (protegido) en el set en %d muestras; .51 (base) en %d muestras\n", v(c3), n61, n51
  c4 = (s1 > 0 && s1 - fa1 >= SAL1_MIN && s1 - fa1 <= SAL1_MAX && co_e1 ~ /strikes=1/)
  printf "C4 %s .50 sale %s s tras fin_ataque1 (ventana [%d, %d]; escalon 1 = 60 s; strikes=1 al entrar)\n", v(c4), (s1 ? sprintf("%.1f", s1 - fa1) : "no sale"), SAL1_MIN, SAL1_MAX
  c5 = (e2 > 0 && co_e2 ~ /strikes=2/ && to_e2 + 0 > 60 && to_e2 + 0 <= 120 && s2 > 0 && s2 - fa2 >= SAL2_MIN && s2 - fa2 <= SAL2_MAX)
  printf "C5 %s ataque 2: entra %s s tras inicio_ataque2 con timeout=%s %s; sale %s s tras fin_ataque2 (ventana [%d, %d]; escalon 2 = 120 s)\n", v(c5), (e2 ? sprintf("%.1f", e2 - ia2) : "nunca"), to_e2, co_e2, (s2 ? sprintf("%.1f", s2 - fa2) : "no sale"), SAL2_MIN, SAL2_MAX
  todo = c1 && c2 && c3 && c4 && c5
  printf "RESULTADO %s\n", (todo ? "PASA" : "FALLA")
  exit (todo ? 0 : 1)
}
' "$C" "$M"
