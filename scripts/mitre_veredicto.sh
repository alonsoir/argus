#!/usr/bin/env bash
# mitre_veredicto.sh — DAY317 [MITRE-VEREDICTO-D317]: corre scripts/mitre_start.sh (nmap del client por aRGus, Suricata y
# Zeek hasta el grafo) y da un veredicto PASA/FALLA para EMECAS+++ (Acto IV): mitre_start.sh rc 0; los tres sensores con
# eventos en el grafo; invariante (CORRELATES_FLOW entre community_id distintos) = 0; flujos corroborados cross-sensor > 0.
# Uso (Mac, raíz del repo):  bash scripts/mitre_veredicto.sh            (corre mitre_start.sh y evalúa su salida)
#                            bash scripts/mitre_veredicto.sh --solo F    (evalúa una salida ya guardada)
# La salida completa queda en logs/lab/mitre-veredicto-<fecha>.txt.
# [MITRE-VENTANA-D323] además, cada sensor debe tener filas del ataque (atacante <-> víctima) en la ventana [T0, T1]
# de la corrida: líneas «[MITRE-VENTANA] sensor=S ... ataque=K» de mitre_start.sh. Medido DAY323: con «eventos > 0»
# pasaban Suricata con alertas de otro día y Zeek con solo etcd y NTP.
set -u
export LC_ALL=C
TAG=MITRE-VEREDICTO
if [ "${1:-}" = "--solo" ]; then
  F=${2:?fichero con la salida de mitre_start.sh}; RC=0
  [ -f "$F" ] || { echo "[$TAG] FALLA: no existe $F"; exit 1; }
else
  [ -f Vagrantfile ] && [ -d .git ] || { echo "[$TAG] FALLA: no estoy en la raíz del repo"; exit 1; }
  mkdir -p logs/lab; F=logs/lab/mitre-veredicto-$(date -u +%Y%m%dT%H%M%SZ).txt
  # [MITRE-VEREDICTO-D317b] por pantalla y al fichero a la vez (DAY317: en silencio, mitre-check parecía colgado)
  bash scripts/mitre_start.sh 2>&1 | tee "$F"; RC=${PIPESTATUS[0]}
  echo "[$TAG] salida de mitre_start.sh en $F (rc=$RC)"
fi
# Formato de kuzu_query (medido DAY317): «sensor|n» por fila; los recuentos sueltos, un número solo en su línea.
tr -d '\r' < "$F" | awk -v rc="$RC" -v tag="$TAG" '
  /^-- sensores en el grafo --/        { s = "sens"; next }
  /^-- invariante/                     { s = "inv";  next }
  /^-- flujos corroborados/            { s = "corr"; next }
  /^\([0-9]+ filas\)/                  { s = ""; next }
  /^\[MITRE-VENTANA\] sensor=/         { sn = ""; ak = -1
                                         for (i = 2; i <= NF; i++) { split($i, kv, "=")
                                           if (kv[1] == "sensor") sn = kv[2]; else if (kv[1] == "ataque") ak = kv[2] + 0 }
                                         if (sn != "") { at[sn] = ak; va[sn] = 1 }; next }
  s == "sens" && /^[a-z_-]+\|[0-9]+$/  { split($0, a, "|"); n[a[1]] = a[2] + 0; next }
  s == "inv"  && /^[0-9]+$/            { inv = $0 + 0; vi = 1; next }
  s == "corr" && /^[0-9]+$/            { corr = $0 + 0; vc = 1; next }
  END {
    ok = 1
    c = (rc == 0); printf "  %s  mitre_start.sh rc=%d\n", (c ? "OK   " : "FALLA"), rc; ok = ok && c
    split("argus suricata zeek", ss, " ")
    for (i = 1; i <= 3; i++) { v = n[ss[i]] + 0; c = (v > 0); printf "  %s  %s: eventos en el grafo > 0 (%d)\n", (c ? "OK   " : "FALLA"), ss[i], v; ok = ok && c }
    for (i = 1; i <= 3; i++) { c = (va[ss[i]] && at[ss[i]] > 0); printf "  %s  %s: filas del ataque en la ventana > 0 (%s)\n", (c ? "OK   " : "FALLA"), ss[i], (va[ss[i]] ? at[ss[i]] : "sin dato"); ok = ok && c }
    c = (vi && inv == 0); printf "  %s  invariante = 0 (%s)\n", (c ? "OK   " : "FALLA"), (vi ? inv : "sin dato"); ok = ok && c
    c = (vc && corr > 0); printf "  %s  flujos corroborados cross-sensor > 0 (%s)\n", (c ? "OK   " : "FALLA"), (vc ? corr : "sin dato"); ok = ok && c
    printf "[%s] VEREDICTO %s\n", tag, (ok ? "PASA" : "FALLA")
    exit (ok ? 0 : 1)
  }'
