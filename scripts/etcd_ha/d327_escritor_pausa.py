#!/usr/bin/env python3
# [ESCRITOR-PAUSA-D327] DAY327, DEBT-EMECAS-PLANO-CONTROL-001 (PR2b de DEBT-ETCD-HA-TLS-RAFT-001): el escritor de
# scripts/etcd_ha/test_etcd_reinicio.sh deja de escribir cada segundo: pausa entre escrituras en un parámetro,
# ETCD_REINICIO_ESCRITOR_S, entero en [1, 10], defecto 2 (decisión de Alonso DAY326). Menos trazas Notice de Falco.
# Uso (raíz del repo): python3 -I scripts/etcd_ha/d327_escritor_pausa.py --check | --apply
# Todo o nada: comprueba y calcula todos los ficheros antes de escribir ninguno. Idempotente (YA-APLICADO).
import hashlib, os, sys, tempfile

FICHEROS = [
    {
        'ruta': 'scripts/etcd_ha/test_etcd_reinicio.sh', 'antes': 'ea08fb9dd8ad03a8b5094956c99d39ea68ce23c7cf7e9adf9163dc35bcc51b47', 'despues': 'dd1498733ec1ca9454aca80890a115002bde96c65bca30a137f58d64bb93767d', 'modo': None,
        'nuevo': None,
        'trozos': [
            ('#   R4 servicio: un escritor en el primer nodo escribe una clave cada segundo (los tres endpoints) durante todo el\n#      test. Ninguna',
             '#   R4 servicio: un escritor en el primer nodo escribe una clave (los tres endpoints) durante todo el test, con una\n#      pausa de ETCD_REINICIO_ESCRITOR_S segundos entre escrituras [ESCRITOR-PAUSA-D327]. Ninguna'),
            ('# 1500, con EL >= 5 x HB (los rangos del playbook) y distintos de los que tiene el clúster. Ausentes o mal: el defecto,\n# avisando. Trap:',
             '# 1500, con EL >= 5 x HB (los rangos del playbook) y distintos de los que tiene el clúster; ETCD_REINICIO_ESCRITOR_S\n# [1, 10] defecto 2 (DEBT-EMECAS-PLANO-CONTROL-001: cada escritura es un etcdctl con sudo, es decir, trazas Notice de\n# Falco; a 1 s eran el doble). Ausentes o mal: el defecto, avisando. Trap:'),
            ('    escritor-bucle)  # ENDPOINTS CLAVE: una escritura por segundo; la fallida se reintenta en el acto.\n',
             '    escritor-bucle)  # ENDPOINTS CLAVE PAUSA_S: escribe, espera PAUSA_S y vuelve; la fallida se reintenta en el acto.\n'),
            ('        echo "$t $rc $r $(( $(date +%s) - t )) $(echo "$e" | tail -n 1 | cut -c1-160)" >> "$ESC_LOG"\n        sleep 1\n',
             '        echo "$t $rc $r $(( $(date +%s) - t )) $(echo "$e" | tail -n 1 | cut -c1-160)" >> "$ESC_LOG"\n        sleep "${5:-2}"\n'),
            ('    escritor-arrancar)  # ENDPOINTS CLAVE\n',
             '    escritor-arrancar)  # ENDPOINTS CLAVE PAUSA_S\n'),
            ('      setsid nohup bash "$0" --vm escritor-bucle "$3" "$4" > /dev/null 2>&1 < /dev/null &\n',
             '      setsid nohup bash "$0" --vm escritor-bucle "$3" "$4" "${5:-2}" > /dev/null 2>&1 < /dev/null &\n'),
            ('entero ETCD_REINICIO_EL_MS "${ETCD_REINICIO_EL_MS:-}" 1500 500 10000; ELP=$VAL\n',
             'entero ETCD_REINICIO_EL_MS "${ETCD_REINICIO_EL_MS:-}" 1500 500 10000; ELP=$VAL\nentero ETCD_REINICIO_ESCRITOR_S "${ETCD_REINICIO_ESCRITOR_S:-}" 2 1 10; ESCS=$VAL\n'),
            ('V "$PRIMERO" "bash $YO --vm escritor-arrancar \'$EPS\' \'$K\'" > "$T/esc_arranque.txt"\n',
             'V "$PRIMERO" "bash $YO --vm escritor-arrancar \'$EPS\' \'$K\' $ESCS" > "$T/esc_arranque.txt"\n'),
            ('log "nodos: $NODOS; tiempos de prueba: heartbeat $HBP ms, election $ELP ms"\n',
             'log "nodos: $NODOS; tiempos de prueba: heartbeat $HBP ms, election $ELP ms; escritor: pausa de $ESCS s"\n'),
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
