#!/bin/bash
# d322_medir_falco_admin.sh — DAY322, ADR-060 8e.4d: de dónde salen los eventos de Falco de /var/log/falco/eventos.json.
# Se ejecuta EN LA VM etcd (o en el defender) como vagrant; hace sudo para leer el fichero (root).
#   bash /vagrant/scripts/etcd_ha/d322_medir_falco_admin.sh [DESDE]
#   DESDE: nº de línea ya visto (entero >= 0, defecto 0 = todo el fichero). Resume solo las líneas posteriores.
# Saca, para esas líneas: eventos por regla; por (regla, proceso, padre, fichero, usuario); y por minuto (UTC).
# Al final, LINEAS=N: el nº de líneas actual, para pasarlo como DESDE en la siguiente medida.
# Una sola pasada por el fichero: O(n) en líneas.
set -u
LC_ALL=C; export LC_ALL
F=/var/log/falco/eventos.json
DESDE=${1:-0}
if ! [[ "$DESDE" =~ ^[0-9]+$ ]]; then
  echo "[D322-FALCO] DESDE='$DESDE' mal formado: entero >= 0 (nº de línea ya visto; 0 = todo el fichero)"; exit 2
fi
if ! sudo test -f "$F"; then echo "[D322-FALCO] falta $F (¿Falco instalado en $(hostname)?)"; exit 1; fi
sudo python3 - "$F" "$DESDE" "$(hostname)" <<'PY'
import collections, json, sys
f, desde, host = sys.argv[1], int(sys.argv[2]), sys.argv[3]
por_regla, grupos, minutos = collections.Counter(), collections.Counter(), collections.Counter()
n = malas = 0
with open(f, errors="replace") as fh:
    for n, linea in enumerate(fh, 1):
        if n <= desde: continue
        try:
            e = json.loads(linea)
        except Exception:
            malas += 1; continue
        of = e.get("output_fields") or {}
        r = e.get("rule", "?")
        por_regla[(r, e.get("priority", "?"))] += 1
        grupos[(r, of.get("proc.exepath", "?"), of.get("proc.pexepath", "?"), of.get("fd.name", "-"),
                of.get("user.name", "?"))] += 1
        minutos[(r, str(e.get("time", "?"))[:16])] += 1
print("[D322-FALCO] %s %s: %d líneas en total; resumen de las %d posteriores a la %d%s" % (
    host, f, n, max(n - desde, 0), desde, (", %d sin JSON válido" % malas) if malas else ""))
if n < desde:
    print("  AVISO: el fichero tiene menos líneas que DESDE (¿rotado por logrotate?): vuelve a medir con DESDE=0")
print("  por regla:")
for (r, p), c in sorted(por_regla.items()): print("    %5d  %s (%s)" % (c, r, p))
print("  por regla, proceso, padre, fichero, usuario:")
for (r, pr, pa, fi, us), c in sorted(grupos.items()): print("    %5d  %s proc=%s padre=%s fichero=%s usuario=%s" % (c, r, pr, pa, fi, us))
print("  por minuto (UTC):")
for (r, m), c in sorted(minutos.items(), key=lambda kv: (kv[0][1], kv[0][0])): print("    %5d  %s %s" % (c, m, r))
print("LINEAS=%d" % n)
PY
