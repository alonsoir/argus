#!/usr/bin/env python3
# [CORRELATES-CROSS-SENSOR-D327] DAY327: EMECAS+++ paró en mitre-check porque el poblador de CORRELATES_FLOW de
# scripts/mitre_start.sh emparejaba todos los flujos del mismo community_id (cuadrático; ~8,5 millones de aristas con el
# tráfico Raft de los tres nodos etcd). Ahora solo empareja eventos de sensores distintos (Alert o TelemetryEvent).
# Además correlation-engine/tools/kuzu_query.cpp imprime el mensaje de error de Kuzu ([KUZU-QUERY-ERROR-D327]).
# Dos commits: uno por fichero.
# Uso (raíz del repo): python3 -I scripts/etcd_ha/d327_correlates.py --check | --apply
# Todo o nada: comprueba y calcula todos los ficheros antes de escribir ninguno. Idempotente (YA-APLICADO).
import hashlib, os, sys, tempfile

FICHEROS = [
    {
        'ruta': 'scripts/mitre_start.sh', 'antes': '2398898c411705f78bb74b8ef5a51a20af691affcb4578868dc144eb06359c61', 'despues': '0f6a65f6cd0ad86399f0703974ce9d1c7a060625a5dba3b0ad8f748f238fc588', 'modo': None,
        'nuevo': None,
        'trozos': [
            ('vagrant ssh defender -c "cd $CE && ./kuzu_query $KUZU \\"MATCH (a:NetworkFlow),(b:NetworkFlow) WHERE a.community_id=b.community_id AND a.flow_uid<b.flow_uid MERGE (a)-[e:CORRELATES_FLOW]->(b) ON CREATE SET e.community_id=a.community_id, e.method=\'community_id\', e.confidence=1.0\\"" \\\n',
             '# [CORRELATES-CROSS-SENSOR-D327] solo aristas entre sensores distintos (lo que mide el titular y lo que usa\n# dataset_export.py, con Alert y TelemetryEvent). La versión anterior emparejaba TODOS los flujos del mismo\n# community_id, también los de un mismo sensor: con los tres nodos etcd, aRGus ve cada latido Raft como un flujo\n# nuevo (unos 2000 por 5-tupla en 96 s) y el MERGE quiso crear ~8,5 millones de aristas aRGus-aRGus que nadie\n# usa; Kuzu falló y EMECAS+++ paró en mitre-check (DAY327). Medido sobre esa BD: 6,9 s, 13801 aristas,\n# invariante 0, titular 1213. Sigue siendo cuadrático ENTRE sensores por 5-tupla: DEBT-SNIFFER-FLOW-UID-TCP-LARGA-001.\nvagrant ssh defender -c "cd $CE && ./kuzu_query $KUZU \\"MATCH (ea)-[:ALERT_ABOUT|TELEMETRY_ABOUT]->(a:NetworkFlow), (eb)-[:ALERT_ABOUT|TELEMETRY_ABOUT]->(b:NetworkFlow) WHERE a.community_id=b.community_id AND a.flow_uid<b.flow_uid AND ea.source_sensor<>eb.source_sensor MERGE (a)-[e:CORRELATES_FLOW]->(b) ON CREATE SET e.community_id=a.community_id, e.method=\'community_id\', e.confidence=1.0\\"" \\\n'),
        ],
    },
    {
        'ruta': 'correlation-engine/tools/kuzu_query.cpp', 'antes': '24dad06ccf6929e661881f7fe869c48acf54fd78b84030edf57ff94bc915abc1', 'despues': 'ddfb79b0a120b63b9921347e4b7eb7a490d603b159d4426ae49aaf9e36b892ed', 'modo': None,
        'nuevo': None,
        'trozos': [
            ('            std::cerr << "FATAL: la consulta no tuvo exito\\n";\n',
             '            // [KUZU-QUERY-ERROR-D327] el mensaje de Kuzu: sin él, el fallo del poblador de DAY327 no decía por qué\n            std::cerr << "FATAL: la consulta no tuvo exito: " << result->getErrorMessage() << "\\n";\n'),
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
