#!/usr/bin/env python3
"""
autopsy_67.py -- DAY 251: autopsia del hueco lens-observable (aRGus)

Localiza por MEDICION donde mueren en el pipeline los flujos botnet del hueco
(true - L, los 67 de STAMP 20260804-080140). Medido en dataset_export.py: el
modo A NO deduplica ni filtra -> L == 5-tuplas de los Parquet de oro. Luego los
del hueco NO estan en el oro; mueren ANTES. Esta autopsia mira la lente decisiva
(zeek, observador 99.9%) en su CONN.LOG CRUDO de la corrida:

  - en conn.log ?  -> zeek los capturo; murieron en zeek->oro (adapter/converter)
  - no en conn.log -> la captura de zeek no los vio (replay/timing, externo)

Y mide el conn_state de los del hueco vs el de los que SI llegaron al oro: si
comparten un estado que los vistos no tienen, ese es el mecanismo (dato, no
conjetura).

FIDELIDAD: reusa canon()/loaders de join_bias_labels.py y load_pcap()/
load_binetflow_botnet_full() de bias_denominator_true.py -> mismo 'blind'.
El conn.log se parsea por su cabecera #fields (sin asumir posiciones).

Uso (desde la raiz del repo):
  python3 scripts/autopsy_67.py 20260804-080140
  python3 scripts/autopsy_67.py --connlog logs/lab/zeek-20260804-080140.conn.log
"""
import argparse
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from join_bias_labels import (
    canon, label_of, load_csv, load_labels, resolve_csv, stamp_of, DEFAULT_BINETFLOW,
)
from bias_denominator_true import load_pcap, load_binetflow_botnet_full, DEFAULT_RAW

LAB = "logs/lab"


# bronce argus correlation_v1: CSV SIN cabecera, posicional. Layout medido de una
# fila real (19 cols): 0 ver, 1 sensor, 2 event_id, 3 node, 4 community_id,
# 5 fstart_sec, 6 fstart_nsec, 7 src_ip, 8 dst_ip, 9 src_port, 10 dst_port,
# 11 protocol, 12 final, 13 cat, 14 fast, 15 ml, 16 overall, 17 auth, 18 hmac.
# canon() colapsa orientacion -> el etiquetado src/dst no afecta a la pertenencia.
AB_SIP, AB_DIP, AB_SP, AB_DP, AB_PROTO = 7, 8, 9, 10, 11
_PROTOS = {"tcp", "udp", "icmp"}


def load_argus_bronce(path):
    """5-tuplas canonicas del bronce CRUDO de argus (eth2, otra pila de captura).
    Parseo POSICIONAL; guard: si la col 11 no parece protocolo, aborta e imprime
    la fila para inspeccion (no inventa columnas)."""
    import csv as _csv
    keys = set()
    with open(path, newline="") as f:
        r = _csv.reader(f)
        first = True
        for row in r:
            if len(row) <= AB_PROTO:
                continue
            if first:
                first = False
                if row[AB_PROTO].strip().lower() not in _PROTOS:
                    return keys, row  # layout inesperado -> devolver fila para inspeccion
            keys.add(canon(row[AB_SIP], row[AB_SP], row[AB_DIP], row[AB_DP], row[AB_PROTO]))
    return keys, None


def parse_zeek_conn(path):
    """Devuelve keys{canon}, states{canon->set(conn_state)}. Parsea por #fields."""
    sep = "\t"
    idx = None
    keys = set()
    states = defaultdict(set)
    with open(path, newline="") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("#separator"):
                v = line.split(None, 1)[1].strip()
                sep = v.encode().decode("unicode_escape") if "\\x" in v or "\\t" in v else v
                continue
            if line.startswith("#fields"):
                names = line.split(sep)[1:]
                idx = {n: i for i, n in enumerate(names)}
                continue
            if line.startswith("#"):
                continue
            if idx is None:
                continue
            p = line.split(sep)
            try:
                oh = p[idx["id.orig_h"]]; op = p[idx["id.orig_p"]]
                rh = p[idx["id.resp_h"]]; rp = p[idx["id.resp_p"]]
                pr = p[idx["proto"]]
                cs = p[idx["conn_state"]] if "conn_state" in idx else "?"
            except (KeyError, IndexError):
                continue
            k = canon(oh, op, rh, rp, pr)
            keys.add(k)
            states[k].add(cs)
    return keys, states, idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stamp", nargs="?", default="")
    ap.add_argument("--csv", default="")
    ap.add_argument("--binetflow", default=DEFAULT_BINETFLOW)
    ap.add_argument("--raw", default=DEFAULT_RAW)
    ap.add_argument("--connlog", default="")
    a = ap.parse_args()

    csv_path = resolve_csv(a.stamp, a.csv)
    stamp = stamp_of(csv_path)
    connlog = a.connlog or os.path.join(LAB, f"zeek-{stamp}.conn.log")
    for p in (csv_path, a.binetflow, a.raw, connlog):
        if not os.path.isfile(p):
            sys.exit(f"[ERROR] no existe {p}")

    # blind = true - L, identico a bias_denominator_true
    rows, keys_union = load_csv(csv_path)
    labels, _ = load_labels(a.binetflow, keys_union)
    L = {k for rs in rows.values() for (k, _f, _c) in rs if label_of(labels, k) == "botnet"}
    B_full, _ = load_binetflow_botnet_full(a.binetflow)
    P, _minlen, _pk, _fwd, n_lines, _ni, _ns, first_idx = load_pcap(a.raw)
    true = P & B_full
    blind = true - L

    # zeek: oro (del CSV, source_sensor==zeek) y conn.log crudo
    zeek_oro = {k for (k, _f, _c) in rows.get("zeek", [])}
    zeek_oro_botnet = zeek_oro & true
    cl_keys, cl_states, idx = parse_zeek_conn(connlog)

    in_cl = blind & cl_keys
    not_cl = blind - cl_keys

    print("=" * 72)
    print("AUTOPSIA del hueco lens-observable  (donde mueren los del hueco)")
    print("=" * 72)
    print(f"STAMP            : {stamp}")
    print(f"conn.log zeek    : {connlog}")
    print(f"campos conn.log  : {'conn_state' in (idx or {})} (conn_state presente)")
    print(f"hueco (blind)    : {len(blind)}")
    print("")
    print("-" * 72)
    print("ETAPA 1 -- ¿estan en el ORO de zeek? (== en el CSV modo A, sensor zeek)")
    print(f"  hueco en oro zeek : {len(blind & zeek_oro)}/{len(blind)}  (esperado 0: por eso son hueco)")
    print("")
    print("ETAPA 2 -- ¿estan en el CONN.LOG CRUDO de zeek?")
    print(f"  hueco en conn.log : {len(in_cl)}/{len(blind)}")
    print(f"  hueco NO en conn.log : {len(not_cl)}/{len(blind)}")
    if in_cl:
        print("")
        print("  -> zeek SI los capturo; mueren en el camino zeek->oro (adapter/converter).")
        cnt = Counter()
        for k in in_cl:
            for s in cl_states[k]:
                cnt[s] += 1
        print("  conn_state de los del hueco que SI estan en conn.log:")
        for s, c in cnt.most_common():
            print(f"      {c:4d}  {s}")
    if not_cl:
        print("")
        print("  -> estos NO estan en el conn.log de zeek (captura no los vio):")
        for k in sorted(not_cl)[:15]:
            print(f"      {k}")
        if len(not_cl) > 15:
            print(f"      ... (+{len(not_cl)-15} mas)")

    # ETAPA 3 -- POSICION TEMPORAL en el pcap (ordinal del primer frame)
    seen = true - blind
    def pos_stats(S):
        v = sorted(first_idx[k] for k in S if k in first_idx)
        if not v:
            return "(vacio)"
        N = n_lines
        q = lambda f: v[int(f * (len(v) - 1))]
        f5, l5 = int(0.05 * N), int(0.95 * N)
        pri = sum(1 for x in v if x <= f5)
        ult = sum(1 for x in v if x >= l5)
        return (f"n={len(v):5d}  pos%: p10={q(0.1)/N*100:5.1f}  p50={q(0.5)/N*100:5.1f}  "
                f"p90={q(0.9)/N*100:5.1f}  | en 1er 5%={pri}  en ultimo 5%={ult}")
    print("")
    print("-" * 72)
    print("ETAPA 3 -- POSICION TEMPORAL en el pcap (%% recorrido; total frames=%d)" % n_lines)
    print(f"  HUECO (blind) : {pos_stats(blind)}")
    print(f"  VISTOS (seen) : {pos_stats(seen)}")
    print("  LECTURA: hueco al INICIO (p*, 1er 5% altos) -> carrera de arming del sensor;")
    print("           al FINAL (ultimo 5% altos) -> corte del drenaje; REPARTIDO como los")
    print("           vistos -> drop de captura por rafaga (no ventana).")

    # ETAPA 4 -- ¿los vio argus por eth2 (otra pila de captura)?
    argus_bronce = os.path.join(LAB, f"argus-{stamp}.bronce.csv")
    print("")
    print("-" * 72)
    print("ETAPA 4 -- ¿estan en el BRONCE CRUDO de argus? (eth2, pila distinta a zeek/eth1)")
    if os.path.isfile(argus_bronce):
        akeys, ahdr = load_argus_bronce(argus_bronce)
        if ahdr is not None:
            print(f"  no localizo columnas 5-tupla; cabecera del bronce = {ahdr}")
        else:
            in_a = blind & akeys
            print(f"  bronce argus: {len(akeys)} 5-tuplas distintas")
            print(f"  hueco en bronce argus : {len(in_a)}/{len(blind)}")
            if not in_a:
                print("  -> argus (eth2) TAMPOCO los vio. Dos pilas de captura independientes,")
                print("     dos interfaces, mismo veredicto: no llegaron a NINGUN cable observado")
                print("     -> perdida de replay (no drop de una pila concreta).")
            else:
                print("  -> argus SI vio algunos que zeek no -> diferencia de pila/interfaz de")
                print("     captura, no perdida de replay pura. Detalle:")
                for k in sorted(in_a)[:15]:
                    print(f"       {k}")
    else:
        print(f"  no existe {argus_bronce}")

    # CONTRASTE: conn_state de los que SI llegaron al oro de zeek
    print("")
    print("-" * 72)
    print("CONTRASTE -- conn_state de los flujos botnet que SI llegaron al oro de zeek")
    seen_cnt = Counter()
    seen_in_cl = 0
    for k in zeek_oro_botnet:
        st = cl_states.get(k)
        if st:
            seen_in_cl += 1
            for s in st:
                seen_cnt[s] += 1
    print(f"  botnet en oro zeek: {len(zeek_oro_botnet)}  (de ellos con linea en conn.log: {seen_in_cl})")
    print("  conn_state de los VISTOS (llegaron al oro):")
    for s, c in seen_cnt.most_common(12):
        print(f"      {c:6d}  {s}")
    print("")
    print("  LECTURA: si los del hueco comparten un conn_state AUSENTE (o raro) entre")
    print("  los vistos, ese estado es el discriminante -> el converter zeek->oro lo")
    print("  descarta. Si comparten estado CON los vistos, el estado NO lo explica.")
    print("=" * 72)


if __name__ == "__main__":
    main()