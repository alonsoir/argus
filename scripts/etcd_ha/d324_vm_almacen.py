#!/usr/bin/env python3
# d324_vm_almacen.py — DAY324 [ALMACEN-ESCRIBE-D324]: etcd_vm_estado.sh (make etcd-vm-check) comprueba además que el
# etcd-server ESCRIBE en etcd, con su latido propio (<prefijo>latido/etcd-server) más reciente que
# heartbeat.interval_seconds * timeout_multiplier del JSON. Medido DAY324: con el etcd-server sin alcanzar etcd (503 en
# escrituras), /health daba 200, etcd 3/3 sanos y el check SANO. Añade el target make test-vm-estado-almacen (sin VMs).
# Antes, en su sitio: scripts/etcd_ha/test_vm_estado_almacen.sh. Uso (Mac, raíz del repo): python3 -I scripts/etcd_ha/d324_vm_almacen.py
import hashlib
import os
import sys

EST = "scripts/etcd_ha/etcd_vm_estado.sh"
EST_PARTIDA = "23a9b9dbad14aa4b55c963146a3ca71442d6c12cefa36459b52af275b899ab18"
EST_FINAL = "5d90adc373018600415db994916a91175cc3649ab3f510722858ebb1b484cf17"
MK = "Makefile"
MK_PARTIDA = "eadad9cfa4701f1e86a9a465c60035ba4c6b052f1d2d1956b932d3f78c59bbc5"
TEST = "scripts/etcd_ha/test_vm_estado_almacen.sh"
P = []
P.append(("""#   - etcd: por cada miembro (etcdctl member list: con el PR2 salen todos), sano o no, líder, term y retraso respecto al líder
""","""#   - etcd: por cada miembro (etcdctl member list: con el PR2 salen todos), sano o no, líder, term y retraso respecto al líder
#   - almacén ([ALMACEN-ESCRIBE-D324]): el etcd-server ESCRIBE en etcd. /health solo dice que el proceso responde (da 200
#     aunque no alcance etcd, medido DAY324). Prueba del efecto: su propio latido (<prefijo>latido/etcd-server, que pone al
#     arrancar y cada heartbeat.interval_seconds) tiene como mucho interval_seconds * timeout_multiplier s, el plazo en
#     que él mismo daría por muerto a un componente (del JSON; ausentes o mal: 30 y 3, avisando, como el etcd-server).
"""))
P.append(("""print(t["ca_file"]); print(t["cert_file"]); print(t["key_file"]); print(s["port"]); print(a["prefijo"])
PY
""","""print(t["ca_file"]); print(t["cert_file"]); print(t["key_file"]); print(s["port"]); print(a["prefijo"])
# [ALMACEN-ESCRIBE-D324] plazo del latido propio: los mismos rangos y defectos que el etcd-server (etcd_server_config.hpp)
hb = j.get("heartbeat") if isinstance(j.get("heartbeat"), dict) else {}
def ent(k, d, lo, hi):
    v = hb.get(k)
    if v is None: return d, "%s=%d (defecto: ausente)" % (k, d)
    if not isinstance(v, int) or isinstance(v, bool) or not lo <= v <= hi:
        return d, "%s=%d (defecto: %r mal formado, entero en [%d, %d])" % (k, d, v, lo, hi)
    return v, "%s=%d (JSON)" % (k, v)
i, oi = ent("interval_seconds", 30, 1, 3600); m, om = ent("timeout_multiplier", 3, 2, 10)
print(i * m); print("heartbeat." + oi + " x heartbeat." + om)
PY
"""))
P.append(("""  read -r T_CA; read -r T_CRT; read -r T_KEY; read -r PUERTO; read -r PREFIJO; } <<< "$CFG"
""","""  read -r T_CA; read -r T_CRT; read -r T_KEY; read -r PUERTO; read -r PREFIJO; read -r HB_LIM; read -r O_HB; } <<< "$CFG"
"""))
P.append(("""  [ "$(printf '%s\\n' "$l" | head -n 1)" = SI ] || ok=no
  INFORME+="$(printf '%s\\n' "$l" | tail -n +2)"$'\\n'
  # Vault""","""  [ "$(printf '%s\\n' "$l" | head -n 1)" = SI ] || ok=no
  INFORME+="$(printf '%s\\n' "$l" | tail -n +2)"$'\\n'
  # [ALMACEN-ESCRIBE-D324] el etcd-server escribe en etcd: su latido propio es reciente
  local yo
  yo=$($E get "${PREFIJO}latido/etcd-server" 2>/dev/null)
  l=$(python3 - "$(date +%s)" "$HB_LIM" "$O_HB" "$PREFIJO" "$yo" <<'PY'
import base64, json, sys
ahora, lim, origen, pref = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4]
clave = pref + "latido/etcd-server"
try:
    r = json.loads(sys.argv[5])
except Exception:
    print("NO"); print("  ❌ almacén:       etcd no responde a la lectura de %s" % clave); sys.exit()
kvs = r.get("kvs") or []
if not kvs:
    print("NO"); print("  ❌ almacén:       el etcd-server no ha escrito su latido (%s ausente): no alcanza etcd"
                     " (journalctl -u ml-defender-etcd-server: ETCD-ALMACEN-NO-DISPONIBLE)" % clave); sys.exit()
try:
    ultimo = int(json.loads(base64.b64decode(kvs[0]["value"])).get("ultimo"))
except Exception as e:
    print("NO"); print("  ❌ almacén:       %s ilegible: %s" % (clave, str(e)[:120])); sys.exit()
hace = max(0, ahora - ultimo)
if hace <= lim:
    print("SI"); print("  ✅ almacén:       el etcd-server escribe en etcd (latido propio hace %d s, límite %d s: %s)" % (hace, lim, origen))
else:
    print("NO"); print("  ❌ almacén:       latido propio del etcd-server de hace %d s (límite %d s: %s): no escribe en etcd" % (hace, lim, origen))
PY
)
  [ "$(printf '%s\\n' "$l" | head -n 1)" = SI ] || ok=no
  INFORME+="$(printf '%s\\n' "$l" | tail -n +2)"$'\\n'
  # Vault"""))
MK_P = [("test-etcd-cluster:\n\t@bash scripts/etcd_ha/test_etcd_cluster.sh\n",
         "test-etcd-cluster:\n\t@bash scripts/etcd_ha/test_etcd_cluster.sh\n\n"
         "# [ALMACEN-ESCRIBE-D324] etcd-vm-check da NO SANO si el etcd-server no escribe en etcd (sin VMs: el script de verdad\n"
         "# con sudo/systemctl/curl/etcdctl de mentira; 6 casos de latido fresco, viejo, ausente, sin respuesta y del JSON)\n"
         "test-vm-estado-almacen:\n\t@bash scripts/etcd_ha/test_vm_estado_almacen.sh\n")]


def falla(msg):
    print("[D324-VM-ALMACEN] FALLA: " + msg + " (no se ha escrito nada)")
    sys.exit(1)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def cambia(ruta, partida, pares):
    if not os.path.isfile(ruta):
        falla(ruta + " no existe (¿raíz del repo?)")
    with open(ruta, "rb") as f:
        b = f.read()
    if sha(b) != partida:
        falla(ruta + " no es el de partida: sha256 " + sha(b)[:16] + " (esperado " + partida[:16] + ")")
    t = b.decode("utf-8")
    for viejo, nuevo in pares:
        k = t.count(viejo)
        if k != 1:
            falla("%s: '%s' aparece %d veces (esperada 1)" % (ruta, viejo.strip()[:60], k))
        t = t.replace(viejo, nuevo)
    return t


def main():
    if not os.path.isfile(TEST):
        falla("antes, en su sitio: " + TEST)
    est = cambia(EST, EST_PARTIDA, P)
    if sha(est.encode("utf-8")) != EST_FINAL:
        falla(EST + " no sale con el sha256 esperado (" + sha(est.encode("utf-8"))[:16] + ")")
    mk = cambia(MK, MK_PARTIDA, MK_P)
    for ruta, t in ((EST, est), (MK, mk)):
        st = os.stat(ruta)
        tmp = ruta + ".d324tmp"
        with open(tmp, "wb") as f:
            f.write(t.encode("utf-8"))
        os.chmod(tmp, st.st_mode & 0o7777)
        os.replace(tmp, ruta)
        print("[D324-VM-ALMACEN] %s sha256 %s" % (ruta, sha(t.encode("utf-8"))))
    print("[D324-VM-ALMACEN] RESULTADO PASA: 2 ficheros; ahora: make test-vm-estado-almacen")


if __name__ == "__main__":
    main()
