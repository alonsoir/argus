#!/usr/bin/env python3
# d325_f1_escritor.py — DAY325, F1 del PR2b de DEBT-ETCD-HA-TLS-RAFT-001. Va DESPUÉS de d325_f1_reinicio.py (parte del
# test_etcd_reinicio.sh que dejó aquel, sha256 42d1f8aa...). Solo toca scripts/etcd_ha/test_etcd_reinicio.sh:
#   - Medido DAY325 en el lab: 1 escritura de 86 falló al reiniciar al líder ("etcdserver: request timed out", 5 s): una
#     propuesta en vuelo durante el traspaso del liderazgo. El journal de los tres nodos: nunca dos miembros parados a
#     la vez y líder nuevo en milisegundos. Reproducido en el banco (1 de 2936 con ocho reinicios del líder).
#   - El escritor reintenta en el acto la escritura fallida y guarda duración y error. Criterio: ninguna falla dos veces
#     seguidas, y las fallidas a la primera son como mucho una por reinicio.
#   - Criterio nuevo y directo del quórum: en el journal de etcd de cada nodo, una parada por nodo y ninguna empieza
#     antes de que el miembro anterior vuelva a servir.
# Uso (raíz del repo): python3 -I scripts/etcd_ha/d325_f1_escritor.py --check | --apply
# Todo o nada: sha256 de partida, cada ancla exactamente una vez y sha256 del resultado antes de escribir. Idempotente.
import hashlib, os, sys, tempfile

FICHEROS = [{'ruta': 'scripts/etcd_ha/test_etcd_reinicio.sh',
  'antes': '42d1f8aa8ea219229094eddd858b4796303b7bb412f6a80659e338b618a8e2cc',
  'despues': 'ea08fb9dd8ad03a8b5094956c99d39ea68ce23c7cf7e9adf9163dc35bcc51b47',
  'modo': None,
  'nuevo': None,
  'trozos': [('#   R2 despliegue con otros tiempos de Raft (ETCD_CLUSTER_ARGS, sin tocar el group_vars): los nodos '
              'se reinician de\n'
              '#      uno en uno y en el orden de la lista (reinicio, salud de todos, siguiente), cada etcd tiene '
              'otro PID y su\n'
              '#      etcd.conf.yml lleva los tiempos nuevos.\n'
              '#   R3 vuelta: make etcd-cluster-deploy a secas devuelve los tiempos del group_vars con otro reinicio '
              'de uno en uno;\n'
              '#      una pasada más no cambia nada.\n'
              '#   R4 quórum: un escritor en el primer nodo escribe una clave cada segundo (los tres endpoints) '
              'durante todo el test:\n'
              '#      ninguna escritura falla. Medido en el banco DAY325 (etcd 3.6.16, 3 miembros, mTLS y RBAC): 30 '
              'de 30 con seis\n'
              '#      reinicios, líder incluido; con dos miembros parados la escritura falla (el escritor ve la '
              'pérdida de quórum).\n'
              '#   R5 make etcd-vm-check SANO al acabar.\n'
              '#   R6 Falco: desde el inicio del test, 0 eventos CRITICAL de reglas argus_* en todos los nodos; y en '
              'el primer nodo',
              '#   R2 despliegue con otros tiempos de Raft (ETCD_CLUSTER_ARGS, sin tocar el group_vars): los nodos '
              'se reinician de\n'
              '#      uno en uno y en el orden de la lista (reinicio, salud de todos, siguiente), cada etcd tiene '
              'otro PID y su\n'
              '#      etcd.conf.yml lleva los tiempos nuevos. Y en el reloj de los nodos (journal de etcd de cada '
              'uno): una parada\n'
              '#      por nodo, y ningún miembro se para antes de que el anterior vuelva a servir ("ready to serve '
              'client\n'
              '#      requests"): nunca hay dos miembros parados a la vez, que es lo que perdería el quórum.\n'
              '#   R3 vuelta: make etcd-cluster-deploy a secas devuelve los tiempos del group_vars con otro reinicio '
              'de uno en uno;\n'
              '#      una pasada más no cambia nada.\n'
              '#   R4 servicio: un escritor en el primer nodo escribe una clave cada segundo (los tres endpoints) '
              'durante todo el\n'
              '#      test. Ninguna escritura falla dos veces seguidas (la fallida se reintenta en el acto) y las '
              'fallidas a la\n'
              '#      primera son como mucho una por reinicio. Medido DAY325: al reiniciar al líder etcd le pasa el '
              'liderazgo a otro\n'
              '#      miembro, y una propuesta que va en vuelo en ese instante puede perderse; el cliente solo se '
              'entera por el\n'
              '#      plazo ("etcdserver: request timed out", 5 s). En el lab, 1 de 86 escrituras (journal: los '
              'otros dos miembros\n'
              '#      en marcha y líder nuevo en milisegundos); en el banco, 1 de 2936 con ocho reinicios del líder. '
              'No es pérdida de\n'
              '#      quórum: el reintento entra. Con dos miembros parados (sin quórum) fallan la escritura y su '
              'reintento.\n'
              '#   R5 make etcd-vm-check SANO al acabar.\n'
              '#   R6 Falco: desde el inicio del test, 0 eventos CRITICAL de reglas argus_* en todos los nodos; y en '
              'el primer nodo'),
             ('      echo "EL=$(sudo sed -n \'s/^election-timeout: *//p\' /etc/etcd/etcd.conf.yml 2>/dev/null | head '
              '-n 1)"\n'
              '      echo "FALCO=$(systemctl is-active falco-modern-bpf.service 2>/dev/null)"\n'
              '      echo "LINEAS=$(sudo wc -l "$EVENTOS" 2>/dev/null | awk \'{print $1}\')";;\n'
              '    escritor-bucle)  # ENDPOINTS CLAVE: una escritura por segundo; "epoch rc" por línea\n'
              '      while :; do\n'
              '        t=$(date +%s)\n'
              '        $ETCDCTL --endpoints="$3" put "$4" "$t" > /dev/null 2>&1\n'
              '        echo "$t $?" >> "$ESC_LOG"\n'
              '        sleep 1\n'
              '      done;;\n'
              '    escritor-arrancar)  # ENDPOINTS CLAVE\n'
              '      rm -f "$ESC_LOG" "$ESC_PID"; : > "$ESC_LOG"',
              '      echo "EL=$(sudo sed -n \'s/^election-timeout: *//p\' /etc/etcd/etcd.conf.yml 2>/dev/null | head '
              '-n 1)"\n'
              '      echo "FALCO=$(systemctl is-active falco-modern-bpf.service 2>/dev/null)"\n'
              '      echo "LINEAS=$(sudo wc -l "$EVENTOS" 2>/dev/null | awk \'{print $1}\')"\n'
              '      echo "AHORA=$(date +%s)";;\n'
              '    escritor-bucle)  # ENDPOINTS CLAVE: una escritura por segundo; la fallida se reintenta en el '
              'acto.\n'
              '      # Una línea por escritura: epoch rc rc_del_reintento(- si no hizo falta) segundos error(última '
              'línea)\n'
              '      while :; do\n'
              '        t=$(date +%s); r=-\n'
              '        e=$($ETCDCTL --endpoints="$3" put "$4" "$t" 2>&1 > /dev/null); rc=$?\n'
              '        if [ "$rc" -ne 0 ]; then $ETCDCTL --endpoints="$3" put "$4" "$t" > /dev/null 2>&1; r=$?; fi\n'
              '        echo "$t $rc $r $(( $(date +%s) - t )) $(echo "$e" | tail -n 1 | cut -c1-160)" >> "$ESC_LOG"\n'
              '        sleep 1\n'
              '      done;;\n'
              '    paradas)  # DESDE (epoch): "PARADA parada vuelta" por cada parada de etcd desde entonces (vuelta '
              '= ya sirve; - si no)\n'
              '      sudo journalctl -u etcd --since "@$3" --no-pager -o short-unix 2>/dev/null | awk \'\n'
              '        /Stopping etcd\\.service/ { if (s != "") print "PARADA", s, "-"; s = $1 }\n'
              '        /ready to serve client requests/ { if (s != "") { print "PARADA", s, $1; s = "" } }\n'
              '        END { if (s != "") print "PARADA", s, "-" }\';;\n'
              '    escritor-arrancar)  # ENDPOINTS CLAVE\n'
              '      rm -f "$ESC_LOG" "$ESC_PID"; : > "$ESC_LOG"'),
             ('    return not mal\n'
              '\n'
              'def escritor(f, minimo):\n'
              '    n = fallos = 0; primero = ultimo = None\n'
              '    for l in lineas(f):\n'
              '        p = l.split()\n'
              '        if len(p) != 2 or not p[0].isdigit(): continue\n'
              '        n += 1; ultimo = int(p[0]); primero = primero if primero is not None else ultimo\n'
              '        if p[1] != "0": fallos += 1\n'
              '    bien = fallos == 0 and n >= minimo\n'
              '    print("ESCRITOR %s: %d escrituras, %d fallidas, %s s cubiertos (mínimo %d escrituras)" % (\n'
              '        "BIEN" if bien else "MAL", n, fallos, (ultimo - primero) if n else 0, minimo))\n'
              '    print("ESCRITURAS=%d" % n)\n'
              '    return bien\n'
              '\n'
              'def falco(f):',
              '    return not mal\n'
              '\n'
              'def escritor(f, minimo, max_fallos):\n'
              '    """Ninguna escritura falla dos veces seguidas; las fallidas a la primera, como mucho max_fallos '
              '(una por reinicio)."""\n'
              '    n = fallos = dobles = 0; primero = ultimo = None; det = []\n'
              '    for l in lineas(f):\n'
              '        p = l.split(None, 4)\n'
              '        if len(p) < 4 or not p[0].isdigit(): continue\n'
              '        n += 1; ultimo = int(p[0]); primero = primero if primero is not None else ultimo\n'
              '        if p[1] != "0":\n'
              '            fallos += 1; dobles += p[2] != "0"\n'
              '            det.append("FALLO epoch=%s reintento=%s tras %s s: %s" % (p[0], "entra" if p[2] == "0" '
              'else "FALLA", p[3], p[4] if len(p) > 4 else "?"))\n'
              '    bien = dobles == 0 and fallos <= max_fallos and n >= minimo\n'
              '    print("ESCRITOR %s: %d escrituras en %s s, %d fallidas a la primera (máximo %d), %d fallidas '
              'también al reintentar (mínimo %d escrituras)" % (\n'
              '        "BIEN" if bien else "MAL", n, (ultimo - primero) if n else 0, fallos, max_fallos, dobles, '
              'minimo))\n'
              '    for d in det: print(d)\n'
              '    return bien\n'
              '\n'
              'def paradas(f, nodos):\n'
              '    """Líneas "nodo parada vuelta" (journal de cada nodo): una parada por nodo, en el orden de la '
              'lista, y ninguna\n'
              '    empieza antes de que el miembro anterior vuelva a servir."""\n'
              '    v, mal = {}, []\n'
              '    for l in lineas(f):\n'
              '        p = l.split()\n'
              '        if len(p) == 3: v.setdefault(p[0], []).append((p[1], p[2]))\n'
              '    iv = []\n'
              '    for n in nodos:\n'
              '        ps = v.get(n, [])\n'
              '        if len(ps) != 1: mal.append("%s: %d paradas (esperada 1)" % (n, len(ps))); continue\n'
              '        try: iv.append((n, float(ps[0][0]), float(ps[0][1])))\n'
              '        except ValueError: mal.append("%s: parada sin vuelta (%s %s)" % (n, ps[0][0], ps[0][1]))\n'
              '    txt = []\n'
              '    if not mal:\n'
              '        for k, (n, a, b) in enumerate(iv):\n'
              '            if b < a: mal.append("%s: vuelve antes de pararse" % n)\n'
              '            if k and a <= iv[k - 1][2]:\n'
              '                mal.append("%s se para %.3f s ANTES de que %s vuelva a servir (dos miembros parados a '
              'la vez)" % (n, iv[k - 1][2] - a, iv[k - 1][0]))\n'
              '            if k: txt.append("%.1f s después" % (a - iv[k - 1][2]))\n'
              '            txt.append("%s parado %.1f s" % (n, b - a))\n'
              '    print("PARADAS %s: %s" % ("MAL" if mal else "BIEN", "; ".join(mal or txt)))\n'
              '    return not mal\n'
              '\n'
              'def falco(f):'),
             ('        ("recap con failed=1", recap(f("r5", r([(N[0], 1, 0, 0), (N[1], 1, 0, 1), (N[2], 1, 0, 0)])), '
              '"cambia", N), False),\n'
              '        ("recap sin un nodo", recap(f("r6", r([(N[0], 1, 0, 0), (N[1], 1, 0, 0)])), "cambia", N), '
              'False),\n'
              '        ("escritor bueno", escritor(f("e1", "".join("%d 0\\n" % (1000 + i) for i in range(8))), 5), '
              'True),\n'
              '        ("escritor con un fallo", escritor(f("e2", "1000 0\\n1001 0\\n1002 1\\n1003 0\\n1004 0\\n1005 '
              '0\\n"), 5), False),\n'
              '        ("escritor con pocas escrituras", escritor(f("e3", "1000 0\\n1001 0\\n"), 5), False),\n'
              '    ]\n'
              '    cab = "[D322-FALCO] x: 9 líneas\\n  por regla:\\n"',
              '        ("recap con failed=1", recap(f("r5", r([(N[0], 1, 0, 0), (N[1], 1, 0, 1), (N[2], 1, 0, 0)])), '
              '"cambia", N), False),\n'
              '        ("recap sin un nodo", recap(f("r6", r([(N[0], 1, 0, 0), (N[1], 1, 0, 0)])), "cambia", N), '
              'False),\n'
              '        ("escritor bueno", escritor(f("e1", "".join("%d 0 - 0 \\n" % (1000 + i) for i in range(8))), '
              '5, 3), True),\n'
              '        ("escritor con un fallo que entra al reintentar", escritor(f("e2", "1000 0 - 0 \\n1001 0 - 0 '
              '\\n1002 1 0 5 Error: etcdserver: request timed out\\n1008 0 - 0 \\n1009 0 - 0 \\n1010 0 - 0 \\n"), 5, '
              '3), True),\n'
              '        ("escritor con un fallo que tampoco entra al reintentar", escritor(f("e3", "1000 0 - 0 '
              '\\n1001 0 - 0 \\n1002 1 1 10 Error: context deadline exceeded\\n1013 0 - 0 \\n1014 0 - 0 \\n1015 0 - '
              '0 \\n"), 5, 3), False),\n'
              '        ("escritor con más fallos que reinicios", escritor(f("e4", "".join("%d %s\\n" % (1000 + 6 * '
              'i, "1 0 5 x" if i % 2 else "0 - 0 ") for i in range(10))), 5, 3), False),\n'
              '        ("escritor con pocas escrituras", escritor(f("e5", "1000 0 - 0 \\n1001 0 - 0 \\n"), 5, 3), '
              'False),\n'
              '        ("escritor con el formato viejo (sin medir)", escritor(f("e6", "".join("%d 0\\n" % (1000 + i) '
              'for i in range(8))), 5, 3), False),\n'
              '    ]\n'
              '    P = lambda filas: "".join("%s %s %s\\n" % x for x in filas)\n'
              '    casos += [\n'
              '        ("paradas buenas", paradas(f("p1", P([(N[0], "100.7", "102.3"), (N[1], "103.8", "104.2"), '
              '(N[2], "105.9", "106.3")])), N), True),\n'
              '        ("dos miembros parados a la vez", paradas(f("p2", P([(N[0], "100.7", "102.3"), (N[1], '
              '"102.1", "104.2"), (N[2], "105.9", "106.3")])), N), False),\n'
              '        ("un nodo sin parada", paradas(f("p3", P([(N[0], "100.7", "102.3"), (N[1], "103.8", '
              '"104.2")])), N), False),\n'
              '        ("un nodo con dos paradas", paradas(f("p4", P([(N[0], "100.7", "102.3"), (N[0], "102.9", '
              '"103.3"), (N[1], "103.8", "104.2"), (N[2], "105.9", "106.3")])), N), False),\n'
              '        ("una parada sin vuelta", paradas(f("p5", P([(N[0], "100.7", "102.3"), (N[1], "103.8", "-"), '
              '(N[2], "105.9", "106.3")])), N), False),\n'
              '        ("paradas en otro orden", paradas(f("p6", P([(N[0], "103.8", "104.2"), (N[1], "100.7", '
              '"102.3"), (N[2], "105.9", "106.3")])), N), False),\n'
              '    ]\n'
              '    cab = "[D322-FALCO] x: 9 líneas\\n  por regla:\\n"'),
             ('    if o == "orden": r = orden(a[0], a[1:])\n'
              '    elif o == "recap": r = recap(a[0], a[1], a[2:])\n'
              '    elif o == "escritor": r = escritor(a[0], int(a[1]))\n'
              '    elif o == "falco": r = falco(a[0])\n'
              '    elif o == "autotest": r = autotest(a[0])',
              '    if o == "orden": r = orden(a[0], a[1:])\n'
              '    elif o == "recap": r = recap(a[0], a[1], a[2:])\n'
              '    elif o == "escritor": r = escritor(a[0], int(a[1]), int(a[2]))\n'
              '    elif o == "paradas": r = paradas(a[0], a[1:])\n'
              '    elif o == "falco": r = falco(a[0])\n'
              '    elif o == "autotest": r = autotest(a[0])'),
             ('  else make --no-print-directory etcd-cluster-deploy > "$T/$1.txt" 2>&1; fi\n'
              '}\n'
              'reinicio_bien() {  # etapa salida prefijo_antes prefijo_despues HB EL\n'
              '  local n\n'
              '  A recap "$T/$2.txt" cambia $NODOS > "$T/$2_recap.txt" || { tail -n 30 "$T/$2.txt"; cat '
              '"$T/$2_recap.txt"; falla "$1: el despliegue falló o un nodo no cambió"; }\n'
              '  A orden "$T/$2.txt" $NODOS > "$T/$2_orden.txt" || { cat "$T/$2_orden.txt"; falla "$1: los nodos no '
              'se reinician de uno en uno y en orden"; }',
              '  else make --no-print-directory etcd-cluster-deploy > "$T/$1.txt" 2>&1; fi\n'
              '}\n'
              'reinicio_bien() {  # etapa salida prefijo_antes prefijo_despues HB EL reinicios_acumulados\n'
              '  local n desde\n'
              '  A recap "$T/$2.txt" cambia $NODOS > "$T/$2_recap.txt" || { tail -n 30 "$T/$2.txt"; cat '
              '"$T/$2_recap.txt"; falla "$1: el despliegue falló o un nodo no cambió"; }\n'
              '  A orden "$T/$2.txt" $NODOS > "$T/$2_orden.txt" || { cat "$T/$2_orden.txt"; falla "$1: los nodos no '
              'se reinician de uno en uno y en orden"; }'),
             ('      || falla "$1: $n tiene heartbeat-interval=$(dato "$T/$4_$n.txt" HB) election-timeout=$(dato '
              '"$T/$4_$n.txt" EL), esperado $5 y $6"\n'
              '  done\n'
              '  V "$PRIMERO" "bash $YO --vm escritor-leer" > "$T/$2_esc.txt"\n'
              '  A escritor "$T/$2_esc.txt" 5 > "$T/$2_escr.txt" || { cat "$T/$2_escr.txt"; grep -v \' 0$\' '
              '"$T/$2_esc.txt" | head; falla "$1: el escritor falló durante el reinicio (¿quórum perdido?)"; }\n'
              '  log "$1 PASA: $(sed \'s/^ORDEN BIEN: //\' "$T/$2_orden.txt"); PID nuevo y $5/$6 ms en los $NN '
              'nodos; $(sed -n \'s/^ESCRITOR BIEN: //p\' "$T/$2_escr.txt")"\n'
              '}\n',
              '      || falla "$1: $n tiene heartbeat-interval=$(dato "$T/$4_$n.txt" HB) election-timeout=$(dato '
              '"$T/$4_$n.txt" EL), esperado $5 y $6"\n'
              '  done\n'
              '  : > "$T/$2_paradas.txt"\n'
              '  for n in $NODOS; do  # cada nodo, desde la hora que marcaba ÉL antes del despliegue (un solo reloj: '
              'el del defender)\n'
              '    desde=$(dato "$T/$3_$n.txt" AHORA)\n'
              '    [[ "$desde" =~ ^[0-9]+$ ]] || falla "$1: no leo la hora de $n de antes del despliegue"\n'
              '    V "$n" "bash $YO --vm paradas $desde" | sed -n "s/^PARADA /$n /p" >> "$T/$2_paradas.txt"\n'
              '  done\n'
              '  A paradas "$T/$2_paradas.txt" $NODOS > "$T/$2_paradas_r.txt" || { cat "$T/$2_paradas.txt" '
              '"$T/$2_paradas_r.txt"; falla "$1: las paradas de etcd no van de una en una (journal de los nodos, '
              'arriba)"; }\n'
              '  V "$PRIMERO" "bash $YO --vm escritor-leer" > "$T/$2_esc.txt"\n'
              '  A escritor "$T/$2_esc.txt" 5 "$7" > "$T/$2_escr.txt" || { cat "$T/$2_escr.txt"; falla "$1: el '
              'escritor no pudo escribir durante el reinicio (arriba)"; }\n'
              '  log "$1 PASA: $(sed \'s/^ORDEN BIEN: //\' "$T/$2_orden.txt"); PID nuevo y $5/$6 ms en los $NN '
              'nodos"\n'
              '  log "   journal: $(sed \'s/^PARADAS BIEN: //\' "$T/$2_paradas_r.txt")"\n'
              '  log "   escritor: $(sed -n \'s/^ESCRITOR BIEN: //p\' "$T/$2_escr.txt")"\n'
              '  grep \'^FALLO \' "$T/$2_escr.txt" | sed \'s/^/     /\'\n'
              '}\n'),
             ('DEVOLVER=si\n'
              'despliega r2 "-e etcd_heartbeat_interval_ms=$HBP -e etcd_election_timeout_ms=$ELP"\n'
              'reinicio_bien R2 r2 a b "$HBP" "$ELP"\n'
              '\n'
              '# R3\n'
              'despliega r3\n'
              'reinicio_bien R3 r3 b c "$HB0" "$EL0"\n'
              'DEVOLVER=no\n'
              'despliega r3b',
              'DEVOLVER=si\n'
              'despliega r2 "-e etcd_heartbeat_interval_ms=$HBP -e etcd_election_timeout_ms=$ELP"\n'
              'reinicio_bien R2 r2 a b "$HBP" "$ELP" "$NN"\n'
              '\n'
              '# R3\n'
              'despliega r3\n'
              'reinicio_bien R3 r3 b c "$HB0" "$EL0" "$((2 * NN))"\n'
              'DEVOLVER=no\n'
              'despliega r3b'),
             ('V "$PRIMERO" "bash $YO --vm escritor-leer" > "$T/esc_final.txt"\n'
              'V "$PRIMERO" "bash $YO --vm escritor-parar \'$EPS\' \'$K\'" > /dev/null; ESCRITOR=no\n'
              'A escritor "$T/esc_final.txt" 10 > "$T/esc_final_r.txt" || { cat "$T/esc_final_r.txt"; grep -v \' '
              '0$\' "$T/esc_final.txt" | head; falla "R4: el escritor falló"; }\n'
              'log "R4 PASA: $(sed -n \'s/^ESCRITOR BIEN: //p\' "$T/esc_final_r.txt") con $((2 * NN)) reinicios"\n',
              'V "$PRIMERO" "bash $YO --vm escritor-leer" > "$T/esc_final.txt"\n'
              'V "$PRIMERO" "bash $YO --vm escritor-parar \'$EPS\' \'$K\'" > /dev/null; ESCRITOR=no\n'
              'A escritor "$T/esc_final.txt" 10 "$((2 * NN))" > "$T/esc_final_r.txt" || { cat "$T/esc_final_r.txt"; '
              'falla "R4: el escritor no pudo escribir (arriba)"; }\n'
              'log "R4 PASA: $(sed -n \'s/^ESCRITOR BIEN: //p\' "$T/esc_final_r.txt") con $((2 * NN)) '
              'reinicios"\n')]}]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: python3 -I scripts/etcd_ha/d325_f1_escritor.py --check | --apply"); return 2
    if not (os.path.isfile("Vagrantfile") and os.path.isdir(".git")):
        print("[D325-F1B] PARADA: no estoy en la raíz del repo"); return 1
    plan, errores, ya = [], [], 0
    for f in FICHEROS:
        r = f["ruta"]
        actual = open(r, "rb").read() if os.path.isfile(r) else None
        if actual is not None and sha(actual) == f["despues"]:
            print("[D325-F1B] YA-APLICADO  %s" % r); ya += 1; continue
        if f["nuevo"] is not None:
            if actual is not None:
                errores.append("%s existe con otro contenido (sha256 %s): no se pisa" % (r, sha(actual))); continue
            nuevo = f["nuevo"].encode("utf-8")
        else:
            if actual is None:
                errores.append("%s no existe" % r); continue
            if sha(actual) != f["antes"]:
                errores.append("%s: sha256 de partida %s, se exige %s" % (r, sha(actual), f["antes"])); continue
            t = actual.decode("utf-8")
            mal = False
            for i, (viejo, nuevo_t) in enumerate(f["trozos"], 1):
                c = t.count(viejo)
                if c != 1:
                    errores.append("%s: el ancla %d aparece %d veces (se exige 1)" % (r, i, c)); mal = True; break
                t = t.replace(viejo, nuevo_t)
            if mal: continue
            nuevo = t.encode("utf-8")
        if sha(nuevo) != f["despues"]:
            errores.append("%s: el resultado tendría sha256 %s, se exige %s" % (r, sha(nuevo), f["despues"])); continue
        plan.append((f, nuevo))
    if errores:
        for e in errores: print("[D325-F1B] ERROR  " + e)
        print("[D325-F1B] PARADA: no se escribe nada"); return 1
    if not plan:
        print("[D325-F1B] todo aplicado ya (%d ficheros): nada que hacer" % ya); return 0
    for f, nuevo in plan:
        print("[D325-F1B] %s  %s -> sha256 %s%s" % ("APLICA" if sys.argv[1] == "--apply" else "CHECK ", f["ruta"],
              f["despues"], " (nuevo)" if f["nuevo"] is not None else " (%d anclas)" % len(f["trozos"])))
    if sys.argv[1] == "--check":
        print("[D325-F1B] --check: %d ficheros por cambiar, %d ya aplicados; nada escrito" % (len(plan), ya)); return 0
    for f, nuevo in plan:
        d = os.path.dirname(f["ruta"]) or "."
        modo = f["modo"] if f["modo"] is not None else (os.stat(f["ruta"]).st_mode & 0o777)
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".d325_")
        with os.fdopen(fd, "wb") as h: h.write(nuevo)
        os.chmod(tmp, modo); os.replace(tmp, f["ruta"])
    print("[D325-F1B] aplicado: %d ficheros" % len(plan)); return 0


if __name__ == "__main__":
    sys.exit(main())
