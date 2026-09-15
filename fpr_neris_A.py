#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fpr_neris_A.py (v2) — FPR (especificidad) de la cabeza DDoS "A" sobre replay Neris.

Neris NO tiene DDoS -> cualquier positivo de A es FALSO POSITIVO.
Referencia del entrenamiento (metadata.json): fp_benign_cic = 0.0878 (~8.8% sobre
benigno del CIC). Lo de hoy es la validacion out-of-distribution de ese numero.

Arbitros (medido, no recordado):
  - feature_names.json / metadata.json -> las 9 features de A, en orden, SIN alias.
  - el .pkl (RandomForestClassifier, classes_=[0,1], n_features_in_=9) -> clase 1 = DDoS.
  - el log -> que IPs emiten y con que forma de flujo.

OJO nivel-1 vs A: en el log, 'Level 1: label=0 (BENIGN)' es el clasificador GENERAL,
no A. A es esta cabeza DDoS y se puntua aparte con las 9 features de abajo.

Ejes:
  DENOMINADOR: D1 (solo .165) | D2 (IPs Botnet del binetflow) | D_all (todas 147.32.x)
  POBLACION:   bueno (bwd>=1) | fwd_only (bwd=0,>=2pkt) | un_paquete (total==1) | no_vacio
"""

import argparse
import re
import sys
from collections import defaultdict, Counter

# -- Mapeo A: los 9 de metadata.json, en orden. SIN duplicar (la teoria del alias
#    de DAY267 la desmiente el metadata: son 9 features independientes). ----------
A_FEATURE_ORDER = [
    "Total Length of Fwd Packets",
    "Total Length of Bwd Packets",
    "Fwd Packet Length Max",
    "Bwd Packet Length Max",
    "Bwd Packet Length Mean",
    "Packet Length Mean",
    "Avg Fwd Segment Size",
    "Subflow Fwd Bytes",
    "Subflow Bwd Bytes",
]
# median_impute de metadata.json (relleno de ausentes como en entrenamiento)
MEDIAN_IMPUTE = {
    "Total Length of Fwd Packets": 1438.0,
    "Total Length of Bwd Packets": 0.0,
    "Fwd Packet Length Max": 516.0,
    "Bwd Packet Length Max": 0.0,
    "Bwd Packet Length Mean": 0.0,
    "Packet Length Mean": 516.0,
    "Avg Fwd Segment Size": 516.0,
    "Subflow Fwd Bytes": 1438.0,
    "Subflow Bwd Bytes": 0.0,
}

IP_NERIS_CONFIRMED = "147.32.84.165"
NERIS_PREFIX = "147.32."
# Umbrales: 0.5 (train), 0.6 (sep_min del metadata), 0.7 (despliegue, config L149)
THRESHOLDS = (0.5, 0.6, 0.7)

# -- Parser. Bloque = desde 'Feature Extraction:' hasta 'Level 1:'/'Event received'.
RE_FLOW = re.compile(r"Flow:\s*([\d.]*):(\d*)\s*->\s*([\d.]*):(\d*)\s*\(([^)]*)\)")
RE_PKTS = re.compile(r"Packets:\s*(\d+)\s*fwd,\s*(\d+)\s*bwd,\s*(\d+)\s*total")
RE_FEAT = re.compile(r"Feature\[\s*(\d+)\]\s+(.+?)\s*:\s*([-+0-9.eE]+)\s*$")
MARK_BLOCK = "Feature Extraction:"
MARK_END = ("Level 1:", "Event received", "Event sent", "Fast Detector")


def parse_blocks(logpath):
    block = None

    def new():
        return {"src_ip": "", "dst_ip": "", "src_port": "", "dst_port": "",
                "proto": "", "fwd": 0, "bwd": 0, "total": 0,
                "features": {}, "flow_seen": False}

    def valid(b):
        return b is not None and b["flow_seen"] and len(b["features"]) >= 1

    with open(logpath, "r", errors="replace") as fh:
        for line in fh:
            if MARK_BLOCK in line:
                if valid(block):
                    yield block
                block = new()
                continue
            if block is None:
                continue
            if any(m in line for m in MARK_END):
                if valid(block):
                    yield block
                block = None
                continue
            m = RE_FLOW.search(line)
            if m:
                block["src_ip"], block["src_port"] = m.group(1), m.group(2)
                block["dst_ip"], block["dst_port"] = m.group(3), m.group(4)
                block["proto"] = m.group(5)
                block["flow_seen"] = True
                continue
            m = RE_PKTS.search(line)
            if m:
                block["fwd"], block["bwd"], block["total"] = (
                    int(m.group(1)), int(m.group(2)), int(m.group(3)))
                continue
            m = RE_FEAT.search(line)
            if m:
                try:
                    block["features"][m.group(2).strip()] = float(m.group(3))
                except ValueError:
                    pass
    if valid(block):
        yield block


def bucket(b):
    if not b["src_ip"] or b["total"] == 0:
        return "vacio"
    if b["total"] == 1:
        return "un_paquete"
    if b["bwd"] == 0:
        return "fwd_only"
    return "bueno"


POPULATIONS = {
    "bueno": lambda bk: bk == "bueno",
    "fwd_only": lambda bk: bk == "fwd_only",
    "un_paquete": lambda bk: bk == "un_paquete",
    "no_vacio": lambda bk: bk != "vacio",
}


def make_denominators(botnet_ips):
    d = {
        "D1_solo_165": lambda ip: ip == IP_NERIS_CONFIRMED,
        "D_all_147_32": lambda ip: ip.startswith(NERIS_PREFIX),
    }
    if botnet_ips:
        d["D2_botnet_label"] = lambda ip: ip in botnet_ips
    return d


def build_vector(block):
    """Vector de 9 en orden de A; rellena ausentes con median_impute (como train)."""
    return [block["features"].get(name, MEDIAN_IMPUTE[name]) for name in A_FEATURE_ORDER]


def load_model(path):
    import joblib
    return joblib.load(path)


def load_botnet_ips_from_grep(grep_path):
    """
    Lee un fichero pequeno (salida de un grep previo del binetflow) con lineas que
    contengan ip y label; devuelve IPs 147.32.x con >=1 flujo Botnet.
    Evita arrastrar los 386MB por Python.
    """
    botnet, seen = set(), Counter()
    with open(grep_path, "r", errors="replace") as fh:
        for line in fh:
            low = line.lower()
            for tok in re.findall(r"147\.32\.\d+\.\d+", line):
                seen[tok] += 1
                if "botnet" in low:
                    botnet.add(tok)
    print("-- Labels binetflow (IPs 147.32.x) --")
    for ip, c in sorted(seen.items()):
        print(f"  {ip:18s} apariciones={c:<6d} -> {'BOTNET' if ip in botnet else 'normal/bg'}")
    return botnet


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log")
    ap.add_argument("--model")
    ap.add_argument("--labels", help="fichero pequeno con lineas del binetflow (grep previo)")
    ap.add_argument("--dump-features", action="store_true")
    ap.add_argument("--sample", type=int, default=0, help="imprime N bloques de muestra")
    args = ap.parse_args()

    if not args.log:
        ap.error("hace falta --log")
    blocks = list(parse_blocks(args.log))
    print(f"Bloques parseados: {len(blocks)}")

    if args.dump_features:
        names = set()
        for b in blocks:
            names |= set(b["features"])
        print(f"\n-- {len(names)} nombres de feature vistos --")
        for nm in sorted(names):
            in_a = " [A]" if nm in A_FEATURE_ORDER else ""
            print(f"  {nm}{in_a}")
        missing = [n for n in A_FEATURE_ORDER if n not in names]
        if missing:
            print(f"\n[!] features de A NO vistas en el log: {missing}")
        else:
            print("\n[ok] las 9 features de A estan presentes en el log")
        return

    # censo por IP x bucket
    by_ip = defaultdict(Counter)
    for b in blocks:
        if b["src_ip"].startswith(NERIS_PREFIX):
            by_ip[b["src_ip"]][bucket(b)] += 1
    print("\n-- Censo por IP origen 147.32.x x bucket --")
    print(f"{'IP':18s} {'vacio':>6s} {'1pkt':>6s} {'fwd_only':>9s} {'bueno':>6s} {'TOT':>6s}")
    for ip in sorted(by_ip):
        c = by_ip[ip]
        print(f"{ip:18s} {c['vacio']:>6d} {c['un_paquete']:>6d} "
              f"{c['fwd_only']:>9d} {c['bueno']:>6d} {sum(c.values()):>6d}")

    if args.sample:
        print(f"\n-- {args.sample} bloques de muestra (147.32.x) --")
        shown = 0
        for b in blocks:
            if b["src_ip"].startswith(NERIS_PREFIX):
                print(f"  {b['src_ip']}->{b['dst_ip']} {b['fwd']}f/{b['bwd']}b "
                      f"[{bucket(b)}] vec={[round(v,1) for v in build_vector(b)]}")
                shown += 1
                if shown >= args.sample:
                    break

    botnet = load_botnet_ips_from_grep(args.labels) if args.labels else set()
    denoms = make_denominators(botnet)

    if not args.model:
        print("\n(Sin --model: censo listo. Cablea el pkl para el FPR.)")
        return

    model = load_model(args.model)
    n_exp = getattr(model, "n_features_in_", None)
    if n_exp != len(A_FEATURE_ORDER):
        sys.exit(f"[X] modelo espera {n_exp}, A_FEATURE_ORDER tiene {len(A_FEATURE_ORDER)}")
    classes = list(getattr(model, "classes_", [0, 1]))
    pos = classes.index(1) if 1 in classes else len(classes) - 1
    print(f"\nModelo OK: {type(model).__name__}, classes_={classes}, col positiva={pos}")

    scorable, X = [], []
    for b in blocks:
        if bucket(b) == "vacio":
            continue
        scorable.append(b)
        X.append(build_vector(b))
    if not scorable:
        sys.exit("[X] nada puntuable")
    proba = model.predict_proba(X)[:, pos]

    print("\n-- FPR (Neris = todo positivo es FP) --")
    print(f"   Referencia entrenamiento fp_benign_cic = 0.0878 (8.8%)")
    for dname, dfn in denoms.items():
        print(f"\n[{dname}]")
        head = f"  {'poblacion':11s} {'N':>6s}"
        for t in THRESHOLDS:
            head += f" {'FP@'+str(t):>7s} {'rate':>7s}"
        print(head)
        for pname, pfn in POPULATIONS.items():
            idx = [i for i, b in enumerate(scorable) if dfn(b["src_ip"]) and pfn(bucket(b))]
            n = len(idx)
            row = f"  {pname:11s} {n:>6d}"
            if n == 0:
                for _ in THRESHOLDS:
                    row += f" {'-':>7s} {'-':>7s}"
            else:
                for t in THRESHOLDS:
                    fp = sum(1 for i in idx if proba[i] > t)
                    row += f" {fp:>7d} {fp/n:>7.1%}"
            print(row)

    print("\nLectura: compara 'bueno' vs 'un_paquete'/'fwd_only'. Si estos disparan mas "
          "FP, medir solo sobre 'bueno' es optimista. El numero del paper debe ser la "
          "poblacion que A puntua DE VERDAD en serve (filtra 1-paquete antes de A?).")


if __name__ == "__main__":
    main()