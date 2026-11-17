#!/usr/bin/env python3
# [REINICIO-R3-PROTEGIDO-D327] DAY327: el criterio R3 (modo antes) de scripts/timebase/d303_veredicto_reinicio.sh cuenta
# tambien las marcas de origen protegido. EMECAS+++ de DAY327 paro en lab-e2e-reinicio-antes: 4 marcas del ml-detector
# tras el reinicio y 0 AISLADO; el firewall las habia tratado como manda el diseno (ALERTA_PROTEGIDO, sin bloquear) y
# el veredicto de DAY322 no conocia esa linea. Ahora: marcas tras el corte = AISLADO de otros flujos + ALERTA_PROTEGIDO.
# Uso (raiz del repo): python3 -I scripts/etcd_ha/d327_r3_protegido.py --check | --apply
# Todo o nada: comprueba y calcula todos los ficheros antes de escribir ninguno. Idempotente (YA-APLICADO).
import hashlib, os, sys, tempfile

FICHEROS = [
    {
        'ruta': 'scripts/timebase/d303_veredicto_reinicio.sh', 'antes': '109c9a2247aef5b3d9b8bbd3b56a75ffefdbd873dd2739fb186be6d89465b036', 'despues': 'f7c46647dba541dd55568c832f7fdf0f2a2634b574baa5882b9ee67a595cbe43', 'modo': None,
        'nuevo': None,
        'trozos': [
            ('#               antes del reinicio, puede imprimirse despues del corte con los eventos de antes.\n',
             '#               antes del reinicio, puede imprimirse despues del corte con los eventos de antes.\n#               [REINICIO-R3-PROTEGIDO-D327] Medido DAY327 en EMECAS+++: 4 marcas tres minutos despues del reinicio\n#               y ningun AISLADO; el R3 de DAY322 fallo. Una marca cuyo ORIGEN esta en el manifiesto de protegidos\n#               (desde DAY323 los sensores y desde DAY324 los nodos de control son infraestructura) no entra en\n#               episodio ni en AISLADO: el firewall escribe [SOMBRA-DDOS] ALERTA_PROTEGIDO y no bloquea\n#               (zmq_subscriber.cpp, [PROTEGIDOS-D300]). Tambien esta explicada: marcas del ml-detector tras el\n#               corte = eventos AISLADO de los demas flujos + lineas ALERTA_PROTEGIDO tras linea_fw_parado.\n'),
            ('      AI=${1:-0}; AA=${2:-0}; AJ=${3:-0}\n      if [ "$AI" -eq 0 ] && [ "$AA" -eq 0 ] && [ "$MD" -eq "$AJ" ]; then\n        ok "R3 marcado: antes=$MA; tras el reinicio 0 del ataque ($VICT proto $PROTO, en frio) y $MD marcas, todas aislados de otros flujos ($AJ)"\n      else\n        ko "R3 marcado: tras el reinicio el ataque ($VICT proto $PROTO) tiene $AI INICIO y $AA eventos aislados (esperado 0 y 0); marcas del ml-detector $MD, aislados de otros flujos $AJ (tienen que ser iguales); antes=$MA"\n      fi\n',
             '      AI=${1:-0}; AA=${2:-0}; AJ=${3:-0}\n      # [REINICIO-R3-PROTEGIDO-D327] una linea ALERTA_PROTEGIDO = un evento marcado de origen protegido (no se bloquea)\n      AP=$(awk -v L="$LF" \'NR > L && /\\[SOMBRA-DDOS\\] ALERTA_PROTEGIDO / { n++ } END { printf "%d\\n", n }\' "$F")\n      if [ "$AI" -eq 0 ] && [ "$AA" -eq 0 ] && [ "$MD" -eq $((AJ + AP)) ]; then\n        ok "R3 marcado: antes=$MA; tras el reinicio 0 del ataque ($VICT proto $PROTO, en frio) y $MD marcas, todas explicadas: $AJ aislados de otros flujos + $AP de origen protegido (ALERTA_PROTEGIDO, no se bloquea)"\n      else\n        ko "R3 marcado: tras el reinicio el ataque ($VICT proto $PROTO) tiene $AI INICIO y $AA eventos aislados (esperado 0 y 0); marcas del ml-detector $MD, aislados de otros flujos $AJ + de origen protegido $AP = $((AJ + AP)) (tienen que ser iguales); antes=$MA"\n      fi\n      awk -v L="$LF" \'NR > L && /\\[SOMBRA-DDOS\\] ALERTA_PROTEGIDO / {\n          o = ""; c = ""; v = ""; p = ""\n          for (i = 1; i <= NF; i++) { split($i, a, "=")\n            if (a[1] == "origen") o = a[2]; if (a[1] == "categoria") c = a[2]; if (a[1] == "victima") v = a[2]; if (a[1] == "proto") p = a[2] }\n          n[o " categoria=" c " victima=" v " proto=" p]++ }\n        END { for (k in n) printf "[VEREDICTO] dato (no decide): tras el reinicio, %d marcas de origen protegido origen=%s\\n", n[k], k }\' "$F"\n'),
        ],
    },
]


def sha(b): return hashlib.sha256(b).hexdigest()

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: --check | --apply"); return 2
    aplicar = sys.argv[1] == "--apply"
    if not os.path.isdir(".git"):
        print("[ERROR] ejecutar desde la raíz del repo (no veo .git)"); return 2
    plan, ya, errores = [], 0, 0
    for f in FICHEROS:
        r = f["ruta"]
        if os.path.exists(r):
            actual = open(r, "rb").read()
            h = sha(actual)
            if h == f["despues"]:
                print(f"[YA-APLICADO] {r} {h[:16]}"); ya += 1; continue
            if f["antes"] == "nuevo":
                print(f"[ERROR] {r} existe con otro contenido ({h[:16]}); se esperaba que no existiera"); errores += 1; continue
            if h != f["antes"]:
                print(f"[ERROR] {r} sha256 {h[:16]}, se esperaba {f['antes'][:16]} (antes) o {f['despues'][:16]} (después)"); errores += 1; continue
            t = actual.decode("utf-8")
            for i, (v, n) in enumerate(f["trozos"]):
                if t.count(v) != 1:
                    print(f"[ERROR] {r}: trozo {i + 1} aparece {t.count(v)} veces"); errores += 1; break
                t = t.replace(v, n)
            nb = t.encode("utf-8")
            modo = os.stat(r).st_mode & 0o777
        else:
            if f["antes"] != "nuevo":
                print(f"[ERROR] {r} no existe"); errores += 1; continue
            nb = f["nuevo"].encode("utf-8"); modo = int(f["modo"], 8)
        if sha(nb) != f["despues"]:
            print(f"[ERROR] {r}: el resultado no da el sha256 esperado"); errores += 1; continue
        plan.append((r, nb, modo, f))
        print(f"[APLICABLE] {r} {f['antes'][:16]} -> {f['despues'][:16]} ({len(f['trozos']) if f['nuevo'] is None else 'fichero nuevo'}{' bloques' if f['nuevo'] is None else ''})")
    if errores:
        print(f"[ERROR] {errores} problemas: no se escribe nada"); return 1
    if not plan:
        print(f"[CHECK] todo ya aplicado ({ya} ficheros)"); return 0
    if not aplicar:
        print(f"[CHECK] todo aplicable ({len(plan)} ficheros, {ya} ya aplicados); nada escrito"); return 0
    for r, nb, modo, f in plan:
        d = os.path.dirname(r) or "."
        os.makedirs(d, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".parche_")
        with os.fdopen(fd, "wb") as o: o.write(nb)
        os.chmod(tmp, modo)
        os.replace(tmp, r)
        print(f"[APLICADO] {r} sha256={f['despues']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
