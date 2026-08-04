#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# dataset_export.py  --  aRGus NDR  --  dataset-export MODOS A / B / C
# ---------------------------------------------------------------------------
# Todos: UNA fila por evento del ORO. Identidad + 5-tupla SIEMPRE del ORO
# (el grafo no las tiene: NetworkFlow es identidad pura). Difieren en el
# VEREDICTO y en el proposito:
#
#   MODO A (el mas honesto): veredicto del ORO Parquet HMAC-sellado
#     + topologia del grafo (cross_sensor_corroborations, reuse_degree).
#     -> logs/datasets/dataset-modeA-$STAMP.csv
#
#   MODO B (lo que el pipeline materializo): veredicto LEIDO del grafo Kuzu
#     por event_id, en vez del ORO. Identidad+topologia igual que A.
#     Si el loader es fiel, B == A. Solo difiere donde el loader mangono algo.
#     -> logs/datasets/dataset-modeB-$STAMP.csv
#
#   MODO C (validador del loader, NO es dataset): compara ORO vs grafo por
#     event_id, campo a campo del veredicto. Toda discrepancia = bug de carga.
#     Resumen a stdout + CSV de filas discrepantes.
#     -> logs/datasets/dataset-modeC-diff-$STAMP.csv
#
# Uso:  python3 dataset_export.py [--mode A|B|C] [STAMP]
#   sin STAMP -> ultima corrida en logs/lab/. Corre en el HOST (.venv con
#   pyarrow) y despacha kuzu_query dentro de defender via `vagrant ssh`.
# ---------------------------------------------------------------------------
import sys, os, subprocess, csv, glob, argparse
import pyarrow.parquet as pq

LAB          = "logs/lab"
KUZU_DIR     = "logs/day234-kuzu"
OUT_DIR      = "logs/datasets"
KUZU_BIN     = "/vagrant/correlation-engine/build/kuzu_query"
KUZU_DB_TMPL = "/vagrant/{kdir}/mitre-{stamp}.kuzu"
SENSORS      = ["argus", "suricata", "zeek"]

COLS_ORO = [
    "source_sensor", "event_id", "community_id",
    "src_ip", "dst_ip", "src_port", "dst_port", "protocol",
    "flow_start_sec",
    "final_classification", "threat_category",
    "fast_detector_score", "ml_detector_score", "overall_threat_score",
    "authoritative_source", "flow_uid",
]
VERDICT_STR = ["final_classification", "threat_category", "authoritative_source"]
VERDICT_NUM = ["fast_detector_score", "ml_detector_score", "overall_threat_score"]
NUM_TOL     = 1e-6   # los scores del grafo salen "0.750000"; comparar como float


def run_kuzu(db_vagrant, q, label):
    """Devuelve lista de filas [campo,...] (sin el pie '(N filas)')."""
    cmd = ["vagrant", "ssh", "defender", "-c", '%s %s "%s"' % (KUZU_BIN, db_vagrant, q)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write("AVISO: kuzu_query (%s) rc=%s\n%s\n" % (label, r.returncode, r.stderr[-400:]))
    out = []
    for line in r.stdout.splitlines():
        if "|" not in line or line.lstrip().startswith("("):
            continue
        out.append([p.strip() for p in line.split("|")])
    return out


def latest_stamp():
    ps = sorted(glob.glob(os.path.join(LAB, "argus-*.parquet")))
    if not ps:
        sys.exit("ERROR: no hay ORO de argus en %s" % LAB)
    b = os.path.basename(ps[-1])
    return b[len("argus-"):-len(".parquet")]


def topo_maps(db_vagrant):
    base = ("MATCH (e)-[:ALERT_ABOUT|TELEMETRY_ABOUT]->(f:NetworkFlow)"
            "-[:CORRELATES_FLOW]-(g:NetworkFlow)<-[:ALERT_ABOUT|TELEMETRY_ABOUT]-(e2) "
            "WHERE e.source_sensor %s e2.source_sensor "
            "RETURN f.flow_uid, e.source_sensor, count(DISTINCT g)")
    def collect(op, label):
        m = {}
        for p in run_kuzu(db_vagrant, base % op, label):
            if len(p) == 3:
                try: m[(p[0], p[1])] = int(p[2])
                except ValueError: pass
        return m
    return collect("<>", "cross"), collect("=", "reuse")


def graph_verdict(db_vagrant):
    """{event_id: {campo_veredicto: valor}} (scores como float)."""
    q = ("MATCH (e:%s) RETURN e.event_id, e.final_classification, e.threat_category, "
         "e.fast_detector_score, e.ml_detector_score, e.overall_threat_score, e.authoritative_source")
    m = {}
    for label in ("Alert", "TelemetryEvent"):
        for p in run_kuzu(db_vagrant, q % label, label):
            if len(p) != 7:
                continue
            eid, fc, tc, fs, ml, ov, au = p
            try:
                m[eid] = {"final_classification": fc, "threat_category": tc,
                          "authoritative_source": au,
                          "fast_detector_score": float(fs),
                          "ml_detector_score": float(ml),
                          "overall_threat_score": float(ov)}
            except ValueError:
                continue
    return m


def iter_oro(stamp):
    for sensor in SENSORS:
        p = os.path.join(LAB, "%s-%s.parquet" % (sensor, stamp))
        if not os.path.exists(p):
            sys.stderr.write("AVISO: falta %s -> sensor '%s' omitido\n" % (p, sensor))
            continue
        yield sensor, pq.read_table(p, columns=COLS_ORO).to_pydict()


def export_dataset(stamp, db, mode):
    cross, reuse = topo_maps(db)
    gv = graph_verdict(db) if mode == "B" else None
    out = os.path.join(OUT_DIR, "dataset-mode%s-%s.csv" % (mode, stamp))
    header = COLS_ORO + ["cross_sensor_corroborations", "reuse_degree"]
    n = 0; per = {}; b_missing = 0
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(header)
        for sensor, d in iter_oro(stamp):
            for i in range(len(d["flow_uid"])):
                row = [d[c][i] for c in COLS_ORO]
                if mode == "B":
                    g = gv.get(d["event_id"][i])
                    if g is None:
                        b_missing += 1          # loader dropo este evento; se deja el del ORO
                    else:
                        for c in VERDICT_STR + VERDICT_NUM:
                            row[COLS_ORO.index(c)] = g[c]
                key = (d["flow_uid"][i], d["source_sensor"][i])
                row += [cross.get(key, 0), reuse.get(key, 0)]
                w.writerow(row); n += 1
            per[sensor] = per.get(sensor, 0) + len(d["flow_uid"])
    print("OK -- modo %s -- %d filas -> %s" % (mode, n, out))
    print("  por sensor: %s" % ", ".join("%s=%d" % (s, c) for s, c in per.items()))
    if mode == "B" and b_missing:
        print("  AVISO: %d eventos del ORO sin nodo en el grafo (ver modo C)" % b_missing)


def validate_loader(stamp, db):
    gv = graph_verdict(db)
    out = os.path.join(OUT_DIR, "dataset-modeC-diff-%s.csv" % stamp)
    matched = 0; oro_only = 0
    field_mismatch = {f: 0 for f in VERDICT_STR + VERDICT_NUM}
    seen = set()
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["event_id", "source_sensor", "field", "oro", "graph"])
        for sensor, d in iter_oro(stamp):
            for i in range(len(d["event_id"])):
                eid = d["event_id"][i]; seen.add(eid)
                g = gv.get(eid)
                if g is None:
                    oro_only += 1
                    w.writerow([eid, d["source_sensor"][i], "__MISSING_IN_GRAPH__", "", ""])
                    continue
                ok = True
                for f in VERDICT_STR:
                    if str(d[f][i]) != g[f]:
                        field_mismatch[f] += 1; ok = False
                        w.writerow([eid, d["source_sensor"][i], f, d[f][i], g[f]])
                for f in VERDICT_NUM:
                    if abs(float(d[f][i]) - g[f]) > NUM_TOL:
                        field_mismatch[f] += 1; ok = False
                        w.writerow([eid, d["source_sensor"][i], f, d[f][i], g[f]])
                if ok:
                    matched += 1
    graph_only = sum(1 for e in gv if e not in seen)
    print("MODO C -- validador del loader (ORO vs grafo por event_id)")
    print("  eventos ORO: %d | nodos evento en grafo: %d" % (len(seen), len(gv)))
    print("  coinciden 100%%: %d" % matched)
    print("  ORO sin nodo en grafo (loader dropo): %d" % oro_only)
    print("  nodos en grafo sin fila ORO: %d" % graph_only)
    dirty = {f: c for f, c in field_mismatch.items() if c}
    print("  mismatches de veredicto por campo: %s" % (dirty if dirty else "NINGUNO"))
    if oro_only == 0 and graph_only == 0 and not dirty:
        print("  ==> LOADER FIEL: el grafo es proyeccion bit-a-bit del ORO sellado.")
    else:
        print("  ==> DIVERGENCIAS: ver detalle -> %s" % out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stamp", nargs="?", default=None)
    ap.add_argument("--mode", choices=["A", "B", "C"], default="A")
    a = ap.parse_args()
    stamp = a.stamp or latest_stamp()
    db = KUZU_DB_TMPL.format(kdir=KUZU_DIR, stamp=stamp)
    os.makedirs(OUT_DIR, exist_ok=True)
    print("[dataset-export modo %s] stamp=%s  grafo=%s" % (a.mode, stamp, db))
    if a.mode in ("A", "B"):
        export_dataset(stamp, db, a.mode)
    else:
        validate_loader(stamp, db)


if __name__ == "__main__":
    main()