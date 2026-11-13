#!/usr/bin/env bash
# test_etcd_reinicio.sh — DAY325, F1 del PR2b de DEBT-ETCD-HA-TLS-RAFT-001 [ETCD-REINICIO-D325] [FALCO-SILENCIO-D325]:
# el reinicio de uno en uno de ansible/playbooks/etcd_cluster.yml, de verdad (VMs arriba: defender y los nodos del plano
# de control). Mac, raíz del repo: make test-etcd-reinicio. Los nodos salen de argus_control_nodos (nodos_control.rb).
#   R0 (sin VMs) los analizadores detectan: cada uno tiene que FALLAR con una muestra mala (dos reinicios seguidos sin
#      salud entre medias, un nodo sin reiniciar, un failed=1, una escritura fallida, una CRITICAL de Falco) y pasar
#      con la buena. Si no, el test falla sin tocar el laboratorio: un analizador ciego daría un verde falso.
#   R1 punto de partida: make etcd-cluster-deploy no cambia nada (el clúster está en la configuración del group_vars)
#      y Falco está en marcha en todos los nodos.
#   R2 despliegue con otros tiempos de Raft (ETCD_CLUSTER_ARGS, sin tocar el group_vars): los nodos se reinician de
#      uno en uno y en el orden de la lista (reinicio, salud de todos, siguiente), cada etcd tiene otro PID y su
#      etcd.conf.yml lleva los tiempos nuevos. Y en el reloj de los nodos (journal de etcd de cada uno): una parada
#      por nodo, y ningún miembro se para antes de que el anterior vuelva a servir ("ready to serve client
#      requests"): nunca hay dos miembros parados a la vez, que es lo que perdería el quórum.
#   R3 vuelta: make etcd-cluster-deploy a secas devuelve los tiempos del group_vars con otro reinicio de uno en uno;
#      una pasada más no cambia nada.
#   R4 servicio: un escritor en el primer nodo escribe una clave cada segundo (los tres endpoints) durante todo el
#      test. Ninguna escritura falla dos veces seguidas (la fallida se reintenta en el acto) y las fallidas a la
#      primera son como mucho una por reinicio. Medido DAY325: al reiniciar al líder etcd le pasa el liderazgo a otro
#      miembro, y una propuesta que va en vuelo en ese instante puede perderse; el cliente solo se entera por el
#      plazo ("etcdserver: request timed out", 5 s). En el lab, 1 de 86 escrituras (journal: los otros dos miembros
#      en marcha y líder nuevo en milisegundos); en el banco, 1 de 2936 con ocho reinicios del líder. No es pérdida de
#      quórum: el reintento entra. Con dos miembros parados (sin quórum) fallan la escritura y su reintento.
#   R5 make etcd-vm-check SANO al acabar.
#   R6 Falco: desde el inicio del test, 0 eventos CRITICAL de reglas argus_* en todos los nodos; y en el primer nodo
#      hay trazas argus_lab_clave_leida_admin (Notice): Falco estaba mirando y etcdctl va con sudo.
# Parámetros (entorno), enteros: ETCD_REINICIO_HB_MS [50, 1000] defecto 150 y ETCD_REINICIO_EL_MS [500, 10000] defecto
# 1500, con EL >= 5 x HB (los rangos del playbook) y distintos de los que tiene el clúster. Ausentes o mal: el defecto,
# avisando. Trap: para el escritor, borra su clave y, si el clúster quedó con los tiempos de prueba, lanza
# make etcd-cluster-deploy para devolverlo al group_vars.
# Coste: lineal en la salida de Ansible y en los eventos de Falco posteriores al inicio.
set -u
LC_ALL=C; export LC_ALL
EVENTOS=/var/log/falco/eventos.json
ESC_LOG=/tmp/argus_test_reinicio_escritor.txt
ESC_PID=/tmp/argus_test_reinicio_escritor.pid
ETCDCTL="sudo etcdctl --cacert=/etc/etcd/tls/ca.crt --cert=/etc/argus-pki/etcd-server.crt --key=/etc/argus-pki/etcd-server.key --command-timeout=5s"

# ── Parte que corre EN UN NODO (vagrant): bash /vagrant/scripts/etcd_ha/test_etcd_reinicio.sh --vm ORDEN ... ─────────
if [ "${1:-}" = "--vm" ]; then
  case "${2:-}" in
    estado)  # una línea CLAVE=valor por dato; wc con la ruta como argumento (la redirección la abriría vagrant)
      echo "PID=$(systemctl show etcd -p MainPID --value 2>/dev/null)"
      echo "HB=$(sudo sed -n 's/^heartbeat-interval: *//p' /etc/etcd/etcd.conf.yml 2>/dev/null | head -n 1)"
      echo "EL=$(sudo sed -n 's/^election-timeout: *//p' /etc/etcd/etcd.conf.yml 2>/dev/null | head -n 1)"
      echo "FALCO=$(systemctl is-active falco-modern-bpf.service 2>/dev/null)"
      echo "LINEAS=$(sudo wc -l "$EVENTOS" 2>/dev/null | awk '{print $1}')"
      echo "AHORA=$(date +%s)";;
    escritor-bucle)  # ENDPOINTS CLAVE: una escritura por segundo; la fallida se reintenta en el acto.
      # Una línea por escritura: epoch rc rc_del_reintento(- si no hizo falta) segundos error(última línea)
      while :; do
        t=$(date +%s); r=-
        e=$($ETCDCTL --endpoints="$3" put "$4" "$t" 2>&1 > /dev/null); rc=$?
        if [ "$rc" -ne 0 ]; then $ETCDCTL --endpoints="$3" put "$4" "$t" > /dev/null 2>&1; r=$?; fi
        echo "$t $rc $r $(( $(date +%s) - t )) $(echo "$e" | tail -n 1 | cut -c1-160)" >> "$ESC_LOG"
        sleep 1
      done;;
    paradas)  # DESDE (epoch): "PARADA parada vuelta" por cada parada de etcd desde entonces (vuelta = ya sirve; - si no)
      sudo journalctl -u etcd --since "@$3" --no-pager -o short-unix 2>/dev/null | awk '
        /Stopping etcd\.service/ { if (s != "") print "PARADA", s, "-"; s = $1 }
        /ready to serve client requests/ { if (s != "") { print "PARADA", s, $1; s = "" } }
        END { if (s != "") print "PARADA", s, "-" }';;
    escritor-arrancar)  # ENDPOINTS CLAVE
      rm -f "$ESC_LOG" "$ESC_PID"; : > "$ESC_LOG"
      setsid nohup bash "$0" --vm escritor-bucle "$3" "$4" > /dev/null 2>&1 < /dev/null &
      echo $! > "$ESC_PID"; sleep 1
      kill -0 "$(cat "$ESC_PID")" 2>/dev/null && echo "ESCRITOR=$(cat "$ESC_PID")" || echo "ESCRITOR=";;
    escritor-leer) cat "$ESC_LOG" 2>/dev/null;;
    escritor-parar)  # ENDPOINTS CLAVE: para el bucle (su grupo), espera a la última escritura y borra la clave
      if [ -f "$ESC_PID" ]; then
        p=$(cat "$ESC_PID"); kill -TERM -- "-$p" 2>/dev/null; kill -TERM "$p" 2>/dev/null
        for _ in 1 2 3 4 5 6 7 8; do kill -0 "$p" 2>/dev/null || break; sleep 1; done
        rm -f "$ESC_PID"
      fi
      sleep 1; $ETCDCTL --endpoints="$3" del "$4" > /dev/null 2>&1; echo "PARADO=si";;
    *) echo "[TEST-ETCD-REINICIO] --vm: orden desconocida '${2:-}'"; exit 2;;
  esac
  exit 0
fi

# ── Parte del Mac ──────────────────────────────────────────────────────────────────────────────────────────────────
NODOS_RB=scripts/etcd_ha/nodos_control.rb
GV=ansible/inventory/group_vars/argus_dev.yml
YO=/vagrant/scripts/etcd_ha/test_etcd_reinicio.sh
MEDIR=/vagrant/scripts/etcd_ha/d322_medir_falco_admin.sh
log()   { echo "[TEST-ETCD-REINICIO] $*"; }
falla() { echo "[TEST-ETCD-REINICIO] FALLA: $*"; exit 1; }
[ -f "$NODOS_RB" ] && [ -f Vagrantfile ] || falla "no estoy en la raíz del repo"
command -v ruby >/dev/null || falla "falta ruby"
T=$(mktemp -d /tmp/argus_test_reinicio.XXXXXX) || falla "mktemp"
# < /dev/null: vagrant ssh lee la entrada estándar; dentro de un 'while read' se comería el resto de la lista
V() { local m=$1; shift; vagrant ssh "$m" -c "$*" < /dev/null 2>/dev/null | tr -d '\r' | grep -v '^\[argus\]'; }
dato() { sed -n "s/^$2=//p" "$1" | head -n 1; }

cat > "$T/analiza.py" <<'PY'
# Analizadores de test_etcd_reinicio.sh. Una pasada por cada fichero: O(n).
import re, sys
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
T_REINICIO = "reinicio de etcd en este miembro"
T_SALUD = "salud de todos los miembros desde el primer nodo"

def lineas(f):
    with open(f, encoding="utf-8", errors="replace") as h:
        for l in h:
            yield ANSI.sub("", l).replace("\r", "").rstrip("\n")

def orden(f, nodos):
    """Reinicio de uno en uno y en el orden de la lista: (reinicio n, salud n) por cada nodo, sin nada más."""
    tarea, ev = "", []
    for l in lineas(f):
        if l.startswith("TASK ["):
            tarea = l; continue
        m = re.match(r"(ok|changed|fatal|failed): \[([a-z0-9-]+)", l)
        if not m: continue
        if T_REINICIO in tarea and m.group(1) == "changed": ev.append("reinicio " + m.group(2))
        elif T_SALUD in tarea: ev.append(("salud " if m.group(1) == "ok" else "SALUD-MAL ") + m.group(2))
    esperado = [x for n in nodos for x in ("reinicio " + n, "salud " + n)]
    print("ORDEN %s: %s" % ("BIEN" if ev == esperado else "MAL", "; ".join(ev) or "(ningún reinicio)"))
    return ev == esperado

def recap(f, modo, nodos):
    """modo=igual: nadie cambia nada. modo=cambia: cada nodo cambia algo. En los dos: failed=0 y unreachable=0."""
    vistos, mal = {}, []
    for l in lineas(f):
        m = re.match(r"([a-z0-9-]+) +: ok=(\d+) +changed=(\d+) +unreachable=(\d+) +failed=(\d+)", l)
        if m: vistos[m.group(1)] = tuple(int(x) for x in m.groups()[1:])
    for n in nodos:
        if n not in vistos: mal.append("%s sin línea en el PLAY RECAP" % n)
    for n, (ok, ch, un, fa) in sorted(vistos.items()):
        if un or fa: mal.append("%s unreachable=%d failed=%d" % (n, un, fa))
        if modo == "igual" and ch: mal.append("%s changed=%d (esperado 0)" % (n, ch))
        if modo == "cambia" and n in nodos and not ch: mal.append("%s changed=0 (esperado > 0)" % n)
    print("RECAP %s (%s): %s" % ("MAL" if mal else "BIEN", modo, "; ".join(mal) or
          ", ".join("%s changed=%d" % (n, v[1]) for n, v in sorted(vistos.items()))))
    return not mal

def escritor(f, minimo, max_fallos):
    """Ninguna escritura falla dos veces seguidas; las fallidas a la primera, como mucho max_fallos (una por reinicio)."""
    n = fallos = dobles = 0; primero = ultimo = None; det = []
    for l in lineas(f):
        p = l.split(None, 4)
        if len(p) < 4 or not p[0].isdigit(): continue
        n += 1; ultimo = int(p[0]); primero = primero if primero is not None else ultimo
        if p[1] != "0":
            fallos += 1; dobles += p[2] != "0"
            det.append("FALLO epoch=%s reintento=%s tras %s s: %s" % (p[0], "entra" if p[2] == "0" else "FALLA", p[3], p[4] if len(p) > 4 else "?"))
    bien = dobles == 0 and fallos <= max_fallos and n >= minimo
    print("ESCRITOR %s: %d escrituras en %s s, %d fallidas a la primera (máximo %d), %d fallidas también al reintentar (mínimo %d escrituras)" % (
        "BIEN" if bien else "MAL", n, (ultimo - primero) if n else 0, fallos, max_fallos, dobles, minimo))
    for d in det: print(d)
    return bien

def paradas(f, nodos):
    """Líneas "nodo parada vuelta" (journal de cada nodo): una parada por nodo, en el orden de la lista, y ninguna
    empieza antes de que el miembro anterior vuelva a servir."""
    v, mal = {}, []
    for l in lineas(f):
        p = l.split()
        if len(p) == 3: v.setdefault(p[0], []).append((p[1], p[2]))
    iv = []
    for n in nodos:
        ps = v.get(n, [])
        if len(ps) != 1: mal.append("%s: %d paradas (esperada 1)" % (n, len(ps))); continue
        try: iv.append((n, float(ps[0][0]), float(ps[0][1])))
        except ValueError: mal.append("%s: parada sin vuelta (%s %s)" % (n, ps[0][0], ps[0][1]))
    txt = []
    if not mal:
        for k, (n, a, b) in enumerate(iv):
            if b < a: mal.append("%s: vuelve antes de pararse" % n)
            if k and a <= iv[k - 1][2]:
                mal.append("%s se para %.3f s ANTES de que %s vuelva a servir (dos miembros parados a la vez)" % (n, iv[k - 1][2] - a, iv[k - 1][0]))
            if k: txt.append("%.1f s después" % (a - iv[k - 1][2]))
            txt.append("%s parado %.1f s" % (n, b - a))
    print("PARADAS %s: %s" % ("MAL" if mal else "BIEN", "; ".join(mal or txt)))
    return not mal

def falco(f):
    """Salida de d322_medir_falco_admin.sh: CRITICAL de reglas argus_* y trazas Notice de administración."""
    crit = notice = 0; medido = aviso = False
    for l in lineas(f):
        if l.startswith("LINEAS="): medido = True
        if "AVISO:" in l: aviso = True
        m = re.match(r" +(\d+)  (argus_\S+) \((\w+)\)$", l)
        if not m: continue
        if m.group(3).lower() == "critical": crit += int(m.group(1))
        if m.group(2) == "argus_lab_clave_leida_admin" and m.group(3).lower() == "notice": notice += int(m.group(1))
    if not medido or aviso:
        print("FALCO NO-MEDIDO: %s" % ("fichero rotado durante el test" if aviso else "sin LINEAS= en la salida")); return None
    print("CRITICAL=%d" % crit); print("NOTICE_ADMIN=%d" % notice)
    return crit == 0

def autotest(d):
    import os
    def f(nombre, texto):
        p = os.path.join(d, nombre); open(p, "w", encoding="utf-8").write(texto); return p
    def pasada(pasos):  # [(tarea, estado, nodo)]
        return "".join("TASK [[ETCD-REINICIO] %s] ****\n\x1b[0;33m%s: [%s%s]\x1b[0m\r\n\n" % (
            T_REINICIO + " (x)" if t == "R" else T_SALUD, e, n, "" if n == "control-1" or t == "R" else " -> control-1")
            for t, e, n in pasos)
    N = ["control-1", "control-2", "control-3"]
    buena = pasada([(t, e, n) for n in N for t, e in (("R", "changed"), ("S", "ok"))])
    casos = [
        ("orden bueno", orden(f("o1", buena), N), True),
        ("dos reinicios seguidos", orden(f("o2", pasada([("R", "changed", N[0]), ("R", "changed", N[1]), ("S", "ok", N[0]),
                                                         ("S", "ok", N[1]), ("R", "changed", N[2]), ("S", "ok", N[2])])), N), False),
        ("un nodo sin reiniciar", orden(f("o3", pasada([(t, e, n) for n in N[:2] for t, e in (("R", "changed"), ("S", "ok"))])), N), False),
        ("salud fallida", orden(f("o4", pasada([("R", "changed", N[0]), ("S", "ok", N[0]), ("R", "changed", N[1]), ("S", "fatal", N[1])])), N), False),
        ("ningún reinicio", orden(f("o5", "TASK [otra] ***\nok: [control-1]\n"), N), False),
        ("orden distinto de la lista", orden(f("o6", buena), [N[1], N[0], N[2]]), False),
    ]
    r = lambda filas: "PLAY RECAP ****\n" + "".join("%-26s : ok=9    changed=%d    unreachable=%d    failed=%d    skipped=2\n" % x for x in filas)
    casos += [
        ("recap igual", recap(f("r1", r([(n, 0, 0, 0) for n in N + ["localhost"]])), "igual", N), True),
        ("recap igual con un cambio", recap(f("r2", r([(N[0], 0, 0, 0), (N[1], 1, 0, 0), (N[2], 0, 0, 0)])), "igual", N), False),
        ("recap cambia", recap(f("r3", r([(n, 1, 0, 0) for n in N] + [("localhost", 0, 0, 0)])), "cambia", N), True),
        ("recap cambia con un nodo sin cambio", recap(f("r4", r([(N[0], 1, 0, 0), (N[1], 0, 0, 0), (N[2], 1, 0, 0)])), "cambia", N), False),
        ("recap con failed=1", recap(f("r5", r([(N[0], 1, 0, 0), (N[1], 1, 0, 1), (N[2], 1, 0, 0)])), "cambia", N), False),
        ("recap sin un nodo", recap(f("r6", r([(N[0], 1, 0, 0), (N[1], 1, 0, 0)])), "cambia", N), False),
        ("escritor bueno", escritor(f("e1", "".join("%d 0 - 0 \n" % (1000 + i) for i in range(8))), 5, 3), True),
        ("escritor con un fallo que entra al reintentar", escritor(f("e2", "1000 0 - 0 \n1001 0 - 0 \n1002 1 0 5 Error: etcdserver: request timed out\n1008 0 - 0 \n1009 0 - 0 \n1010 0 - 0 \n"), 5, 3), True),
        ("escritor con un fallo que tampoco entra al reintentar", escritor(f("e3", "1000 0 - 0 \n1001 0 - 0 \n1002 1 1 10 Error: context deadline exceeded\n1013 0 - 0 \n1014 0 - 0 \n1015 0 - 0 \n"), 5, 3), False),
        ("escritor con más fallos que reinicios", escritor(f("e4", "".join("%d %s\n" % (1000 + 6 * i, "1 0 5 x" if i % 2 else "0 - 0 ") for i in range(10))), 5, 3), False),
        ("escritor con pocas escrituras", escritor(f("e5", "1000 0 - 0 \n1001 0 - 0 \n"), 5, 3), False),
        ("escritor con el formato viejo (sin medir)", escritor(f("e6", "".join("%d 0\n" % (1000 + i) for i in range(8))), 5, 3), False),
    ]
    P = lambda filas: "".join("%s %s %s\n" % x for x in filas)
    casos += [
        ("paradas buenas", paradas(f("p1", P([(N[0], "100.7", "102.3"), (N[1], "103.8", "104.2"), (N[2], "105.9", "106.3")])), N), True),
        ("dos miembros parados a la vez", paradas(f("p2", P([(N[0], "100.7", "102.3"), (N[1], "102.1", "104.2"), (N[2], "105.9", "106.3")])), N), False),
        ("un nodo sin parada", paradas(f("p3", P([(N[0], "100.7", "102.3"), (N[1], "103.8", "104.2")])), N), False),
        ("un nodo con dos paradas", paradas(f("p4", P([(N[0], "100.7", "102.3"), (N[0], "102.9", "103.3"), (N[1], "103.8", "104.2"), (N[2], "105.9", "106.3")])), N), False),
        ("una parada sin vuelta", paradas(f("p5", P([(N[0], "100.7", "102.3"), (N[1], "103.8", "-"), (N[2], "105.9", "106.3")])), N), False),
        ("paradas en otro orden", paradas(f("p6", P([(N[0], "103.8", "104.2"), (N[1], "100.7", "102.3"), (N[2], "105.9", "106.3")])), N), False),
    ]
    cab = "[D322-FALCO] x: 9 líneas\n  por regla:\n"
    casos += [
        ("falco sin critical", falco(f("f1", cab + "        6  argus_lab_clave_leida_admin (Notice)\n  por minuto (UTC):\nLINEAS=9\n")), True),
        ("falco con critical", falco(f("f2", cab + "        3  argus_lab_clave_leida_ajeno (Critical)\n        6  argus_lab_clave_leida_admin (Notice)\nLINEAS=9\n")), False),
        ("falco con otra critical argus", falco(f("f3", cab + "        1  argus_lab_hijo_inesperado (Critical)\nLINEAS=9\n")), False),
        ("falco rotado", falco(f("f4", cab + "  AVISO: el fichero tiene menos líneas que DESDE\nLINEAS=2\n")), None),
        ("falco sin salida", falco(f("f5", "")), None),
    ]
    mal = [n for n, real, esperado in casos if real is not esperado]
    print("AUTOTEST %s: %d casos%s" % ("MAL" if mal else "BIEN", len(casos), (", fallan: " + ", ".join(mal)) if mal else ""))
    return not mal

if __name__ == "__main__":
    o, a = sys.argv[1], sys.argv[2:]
    if o == "orden": r = orden(a[0], a[1:])
    elif o == "recap": r = recap(a[0], a[1], a[2:])
    elif o == "escritor": r = escritor(a[0], int(a[1]), int(a[2]))
    elif o == "paradas": r = paradas(a[0], a[1:])
    elif o == "falco": r = falco(a[0])
    elif o == "autotest": r = autotest(a[0])
    else: sys.exit(2)
    sys.exit(0 if r else 1)
PY
A() { python3 -I "$T/analiza.py" "$@"; }

# R0
mkdir "$T/auto"
A autotest "$T/auto" > "$T/auto.txt" 2>&1 || { cat "$T/auto.txt"; rm -rf "$T"; falla "R0: un analizador no detecta lo que debe (arriba): no se toca el laboratorio"; }
log "R0 PASA: $(grep '^AUTOTEST' "$T/auto.txt" | sed 's/^AUTOTEST BIEN: //') de los analizadores (cada uno falla con su muestra mala)"

# Nodos y parámetros
ruby "$NODOS_RB" nodos "$GV" Vagrantfile > "$T/lista.txt" 2>&1 || { cat "$T/lista.txt"; rm -rf "$T"; falla "la lista de nodos no vale"; }
NODOS=$(awk -F'\t' '$1 == "nodo" {printf "%s%s", (n++ ? " " : ""), $2}' "$T/lista.txt")
NN=$(echo "$NODOS" | wc -w | tr -d ' ')
EPS=$(awk -F'\t' '$1 == "nodo" {printf "%shttps://%s:2381", (n++ ? "," : ""), $3}' "$T/lista.txt")
PRIMERO=${NODOS%% *}
[ "$NN" -ge 3 ] || { rm -rf "$T"; falla "$NN nodos: con menos de 3 un reinicio pierde el quórum (no hay nada que probar)"; }
entero() {  # nombre valor defecto min max -> VAL
  local n=$1 v=$2 d=$3 lo=$4 hi=$5
  if [ -z "$v" ]; then VAL=$d; log "$n=$d (defecto: ausente)"; return; fi
  if ! [[ "$v" =~ ^[0-9]+$ ]] || [ "$v" -lt "$lo" ] || [ "$v" -gt "$hi" ]; then
    VAL=$d; log "$n=$d (defecto: '$v' mal formado; entero en [$lo, $hi])"; return
  fi
  VAL=$v; log "$n=$v (entorno)"
}
entero ETCD_REINICIO_HB_MS "${ETCD_REINICIO_HB_MS:-}" 150 50 1000; HBP=$VAL
entero ETCD_REINICIO_EL_MS "${ETCD_REINICIO_EL_MS:-}" 1500 500 10000; ELP=$VAL
if [ "$ELP" -lt $((5 * HBP)) ]; then HBP=150; ELP=1500; log "tiempos de prueba 150 y 1500 (defecto: EL tiene que ser >= 5 x HB)"; fi
K="/argus/test-etcd-reinicio/$(date -u +%Y%m%dT%H%M%SZ)"
ESCRITOR=no; DEVOLVER=no
fin() {
  local rc=$?
  if [ "$ESCRITOR" = si ]; then V "$PRIMERO" "bash $YO --vm escritor-parar '$EPS' '$K'" > /dev/null; fi
  if [ "$DEVOLVER" = si ]; then
    log "TRAP: el clúster pudo quedar con los tiempos de prueba; make etcd-cluster-deploy para devolverlo al group_vars"
    make --no-print-directory etcd-cluster-deploy > "$T/trap.txt" 2>&1
    log "TRAP: $(perl -pe 's/\e\[[0-9;]*[A-Za-z]//g; s/\r//g' "$T/trap.txt" | grep -aE '^[a-z0-9-]+ +: ok=' | tr -s ' ' | tr '\n' ';')"
  fi
  if [ "$rc" -ne 0 ]; then log "salidas en $T (no se borran al fallar)"; else rm -rf "$T"; fi
}
trap fin EXIT
trap 'exit 130' INT TERM
estado() {  # prefijo: deja $T/<prefijo>_<nodo>.txt por nodo; falla si un nodo no contesta
  local n
  for n in $NODOS; do
    V "$n" "bash $YO --vm estado" > "$T/$1_$n.txt"
    [[ "$(dato "$T/$1_$n.txt" PID)" =~ ^[1-9][0-9]*$ ]] || { cat "$T/$1_$n.txt"; falla "$n: no leo el PID de etcd (¿VM parada o etcd parado?)"; }
  done
}
despliega() {  # nombre [argumentos de ETCD_CLUSTER_ARGS]
  if [ -n "${2:-}" ]; then make --no-print-directory etcd-cluster-deploy ETCD_CLUSTER_ARGS="$2" > "$T/$1.txt" 2>&1
  else make --no-print-directory etcd-cluster-deploy > "$T/$1.txt" 2>&1; fi
}
reinicio_bien() {  # etapa salida prefijo_antes prefijo_despues HB EL reinicios_acumulados
  local n desde
  A recap "$T/$2.txt" cambia $NODOS > "$T/$2_recap.txt" || { tail -n 30 "$T/$2.txt"; cat "$T/$2_recap.txt"; falla "$1: el despliegue falló o un nodo no cambió"; }
  A orden "$T/$2.txt" $NODOS > "$T/$2_orden.txt" || { cat "$T/$2_orden.txt"; falla "$1: los nodos no se reinician de uno en uno y en orden"; }
  estado "$4"
  for n in $NODOS; do
    [ "$(dato "$T/$3_$n.txt" PID)" != "$(dato "$T/$4_$n.txt" PID)" ] || falla "$1: etcd de $n tiene el mismo PID ($(dato "$T/$4_$n.txt" PID)): no se reinició"
    [ "$(dato "$T/$4_$n.txt" HB)" = "$5" ] && [ "$(dato "$T/$4_$n.txt" EL)" = "$6" ] \
      || falla "$1: $n tiene heartbeat-interval=$(dato "$T/$4_$n.txt" HB) election-timeout=$(dato "$T/$4_$n.txt" EL), esperado $5 y $6"
  done
  : > "$T/$2_paradas.txt"
  for n in $NODOS; do  # cada nodo, desde la hora que marcaba ÉL antes del despliegue (un solo reloj: el del defender)
    desde=$(dato "$T/$3_$n.txt" AHORA)
    [[ "$desde" =~ ^[0-9]+$ ]] || falla "$1: no leo la hora de $n de antes del despliegue"
    V "$n" "bash $YO --vm paradas $desde" | sed -n "s/^PARADA /$n /p" >> "$T/$2_paradas.txt"
  done
  A paradas "$T/$2_paradas.txt" $NODOS > "$T/$2_paradas_r.txt" || { cat "$T/$2_paradas.txt" "$T/$2_paradas_r.txt"; falla "$1: las paradas de etcd no van de una en una (journal de los nodos, arriba)"; }
  V "$PRIMERO" "bash $YO --vm escritor-leer" > "$T/$2_esc.txt"
  A escritor "$T/$2_esc.txt" 5 "$7" > "$T/$2_escr.txt" || { cat "$T/$2_escr.txt"; falla "$1: el escritor no pudo escribir durante el reinicio (arriba)"; }
  log "$1 PASA: $(sed 's/^ORDEN BIEN: //' "$T/$2_orden.txt"); PID nuevo y $5/$6 ms en los $NN nodos"
  log "   journal: $(sed 's/^PARADAS BIEN: //' "$T/$2_paradas_r.txt")"
  log "   escritor: $(sed -n 's/^ESCRITOR BIEN: //p' "$T/$2_escr.txt")"
  grep '^FALLO ' "$T/$2_escr.txt" | sed 's/^/     /'
}

# R1
log "nodos: $NODOS; tiempos de prueba: heartbeat $HBP ms, election $ELP ms"
despliega r1
A recap "$T/r1.txt" igual $NODOS > "$T/r1_recap.txt" || { tail -n 20 "$T/r1.txt"; cat "$T/r1_recap.txt"; falla "R1: make etcd-cluster-deploy falla o cambia algo: el clúster no está en la configuración del group_vars; no se empieza"; }
estado a
HB0=$(dato "$T/a_$PRIMERO.txt" HB); EL0=$(dato "$T/a_$PRIMERO.txt" EL)
[[ "$HB0" =~ ^[0-9]+$ ]] && [[ "$EL0" =~ ^[0-9]+$ ]] || falla "R1: no leo los tiempos de Raft de $PRIMERO (HB='$HB0' EL='$EL0')"
for n in $NODOS; do
  [ "$(dato "$T/a_$n.txt" HB)" = "$HB0" ] && [ "$(dato "$T/a_$n.txt" EL)" = "$EL0" ] || falla "R1: $n no tiene los mismos tiempos que $PRIMERO ($HB0/$EL0)"
  [ "$(dato "$T/a_$n.txt" FALCO)" = active ] || falla "R1: Falco no está en marcha en $n (sin él, 0 CRITICAL no dice nada)"
  [[ "$(dato "$T/a_$n.txt" LINEAS)" =~ ^[0-9]+$ ]] || falla "R1: no leo el nº de líneas de $EVENTOS en $n"
done
[ "$HBP" != "$HB0" ] || [ "$ELP" != "$EL0" ] || falla "R1: los tiempos de prueba ($HBP/$ELP) son los que ya tiene el clúster: elegir otros con ETCD_REINICIO_HB_MS y ETCD_REINICIO_EL_MS"
log "R1 PASA: sin cambios; el clúster está en $HB0/$EL0 ms; Falco en marcha en los $NN nodos"

# Escritor (R4)
V "$PRIMERO" "bash $YO --vm escritor-arrancar '$EPS' '$K'" > "$T/esc_arranque.txt"
[[ "$(dato "$T/esc_arranque.txt" ESCRITOR)" =~ ^[0-9]+$ ]] || { cat "$T/esc_arranque.txt"; falla "R4: el escritor no arranca en $PRIMERO"; }
ESCRITOR=si
sleep 4

# R2
DEVOLVER=si
despliega r2 "-e etcd_heartbeat_interval_ms=$HBP -e etcd_election_timeout_ms=$ELP"
reinicio_bien R2 r2 a b "$HBP" "$ELP" "$NN"

# R3
despliega r3
reinicio_bien R3 r3 b c "$HB0" "$EL0" "$((2 * NN))"
DEVOLVER=no
despliega r3b
A recap "$T/r3b.txt" igual $NODOS > "$T/r3b_recap.txt" || { tail -n 20 "$T/r3b.txt"; cat "$T/r3b_recap.txt"; falla "R3: tras volver, otra pasada todavía cambia algo"; }
log "R3 PASA también la pasada de después: sin cambios"

# R4
sleep 3
V "$PRIMERO" "bash $YO --vm escritor-leer" > "$T/esc_final.txt"
V "$PRIMERO" "bash $YO --vm escritor-parar '$EPS' '$K'" > /dev/null; ESCRITOR=no
A escritor "$T/esc_final.txt" 10 "$((2 * NN))" > "$T/esc_final_r.txt" || { cat "$T/esc_final_r.txt"; falla "R4: el escritor no pudo escribir (arriba)"; }
log "R4 PASA: $(sed -n 's/^ESCRITOR BIEN: //p' "$T/esc_final_r.txt") con $((2 * NN)) reinicios"

# R5
make --no-print-directory etcd-vm-check > "$T/check.txt" 2>&1 || { tail -n 15 "$T/check.txt"; falla "R5: etcd-vm-check no da SANO tras los reinicios"; }
log "R5 PASA: etcd-vm-check SANO"

# R6
sleep 5
CRIT_TOTAL=0
for n in $NODOS; do
  V "$n" "bash $MEDIR $(dato "$T/a_$n.txt" LINEAS)" > "$T/falco_$n.txt"
  A falco "$T/falco_$n.txt" > "$T/falco_${n}_r.txt"; rc=$?
  grep -q '^CRITICAL=' "$T/falco_${n}_r.txt" || { cat "$T/falco_$n.txt" "$T/falco_${n}_r.txt"; falla "R6: Falco no medido en $n"; }
  c=$(dato "$T/falco_${n}_r.txt" CRITICAL); CRIT_TOTAL=$((CRIT_TOTAL + c))
  echo "  $n: CRITICAL argus_*=$c, trazas Notice de administración=$(dato "$T/falco_${n}_r.txt" NOTICE_ADMIN)"
  [ "$rc" -eq 0 ] || grep -E '^ +[0-9]+  argus_' "$T/falco_$n.txt" | sed 's/^/    /'
done
[ "$CRIT_TOTAL" -eq 0 ] || falla "R6: $CRIT_TOTAL eventos CRITICAL de reglas argus_* durante el test (arriba, por regla; detalle en $T/falco_<nodo>.txt)"
[ "$(dato "$T/falco_${PRIMERO}_r.txt" NOTICE_ADMIN)" -ge 1 ] || falla "R6: ninguna traza Notice de administración en $PRIMERO: Falco no vio los etcdctl con sudo (0 CRITICAL no dice nada)"
log "R6 PASA: 0 CRITICAL de reglas argus_* en los $NN nodos; Falco estaba mirando (trazas Notice de etcdctl con sudo en $PRIMERO)"
log "RESULTADO PASA"
