#!/usr/bin/env python3
"""
cross_attack_auc.py

Matriz AUC (ataque-vs-benigno) de CADA feature nativa a través de CADA fichero/ataque de
CICDDoS2019. El objetivo NO es el AUC de un fichero (en este dataset roza lo perfecto por
puro shortcut), sino la ESTABILIDAD del AUC entre tipos de ataque:

  - feature TRANSFERIBLE  = separación alta y estable en MUCHOS ataques (señal DDoS real).
  - feature ATAJO         = separación alta en 1-2 ataques y ~0.5 en el resto (no generaliza).

Muestreo ESTRATIFICADO por fichero: se queda TODO el benigno (que es escaso, ~0.1%) + una
muestra Bernoulli del ataque hasta ~--sample-attack filas, para que el AUC sea estable y la
memoria acotada sobre 70M filas. Dos pasadas: (1) contar Label -barato-, (2) leer features.

AUC por rangos (Mann-Whitney), sin sklearn/scipy. NUNCA usa grep.

  python3 cross_attack_auc.py ../../datasets/CICDDoS2019 --out auc_matrix.csv
  python3 cross_attack_auc.py ../../datasets/CICDDoS2019 --only 03-11   # solo un día
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

CHUNK = 2_000_000
# Columnas de identidad / basura conocida: fuera del AUC (no son features del modelo).
EXCLUDE = {
    "Unnamed: 0", "Flow ID", "Source IP", "Destination IP", "Source Port",
    "Destination Port", "Timestamp", "Label", "SimillarHTTP", "Fwd Header Length.1",
}


def find_label_col(columns):
    stripped = {c.strip(): c for c in columns}
    return stripped.get("Label")


def average_ranks(sorted_vals):
    n = len(sorted_vals)
    ranks = np.empty(n, dtype="float64")
    i = 0
    while i < n:
        j = i + 1
        while j < n and sorted_vals[j] == sorted_vals[i]:
            j += 1
        ranks[i:j] = (i + j + 1) / 2.0
        i = j
    return ranks


def auc_vs_benign(x, y):
    finite = np.isfinite(x)
    x, y = x[finite], y[finite]
    n_pos = int(y.sum())
    n_neg = len(y) - n_pos
    if n_pos == 0 or n_neg == 0:
        return np.nan
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty(len(x), dtype="float64")
    ranks[order] = average_ranks(x[order])
    sum_pos = ranks[y == 1].sum()
    return (sum_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def count_labels(path, lab_raw):
    n_attack = n_benign = 0
    for chunk in pd.read_csv(path, usecols=[lab_raw], chunksize=CHUNK, low_memory=False):
        lab = chunk[lab_raw].astype(str).str.strip()
        b = int((lab == "BENIGN").sum())
        n_benign += b
        n_attack += len(lab) - b
    return n_attack, n_benign


def sample_file(path, lab_raw, feat_raw, p_attack, rng):
    """Devuelve (DataFrame features, y) con todo el benigno + Bernoulli(p) del ataque."""
    keep = []
    ys = []
    for chunk in pd.read_csv(path, usecols=feat_raw + [lab_raw], chunksize=CHUNK,
                             low_memory=False):
        lab = chunk[lab_raw].astype(str).str.strip()
        is_atk = (lab != "BENIGN").to_numpy()
        mask = ~is_atk                                   # todo el benigno
        if p_attack < 1.0:
            r = rng.random(len(chunk)) < p_attack
            mask = mask | (is_atk & r)
        else:
            mask = mask | is_atk
        if mask.any():
            keep.append(chunk.loc[mask, feat_raw])
            ys.append(is_atk[mask])
    if not keep:
        return None, None
    X = pd.concat(keep, ignore_index=True)
    y = np.concatenate(ys).astype("int8")
    return X, y


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--sample-attack", type=int, default=200_000)
    ap.add_argument("--only", default=None, help="limitar a un subdir (01-12 o 03-11)")
    args = ap.parse_args()

    subs = [args.only] if args.only else ["01-12", "03-11"]
    files = []
    for sub in subs:
        d = args.root / sub
        if d.is_dir():
            files += [(sub, p) for p in sorted(d.glob("*.csv"))]
    if not files:
        sys.exit(f"[FATAL] sin CSV bajo {args.root}/{subs}")

    # Columnas-feature = intersección: numéricas y no excluidas, según cabecera del 1er fichero.
    head = pd.read_csv(files[0][1], nrows=0)
    stripped = [c.strip() for c in head.columns]
    raw_by_strip = {c.strip(): c for c in head.columns}
    lab_raw = find_label_col(head.columns)
    feat_strip = [c for c in stripped if c not in EXCLUDE]
    feat_raw = [raw_by_strip[c] for c in feat_strip]

    rng = np.random.default_rng(42)
    matrix = {}          # file_tag -> {feature: auc}
    order_tags = []
    for sub, path in files:
        tag = f"{sub}/{path.stem}"
        order_tags.append(tag)
        lr = find_label_col(pd.read_csv(path, nrows=0).columns)
        n_atk, n_ben = count_labels(path, lr)
        if n_ben == 0 or n_atk == 0:
            print(f"  [skip] {tag}: benigno={n_ben} ataque={n_atk}")
            matrix[tag] = {}
            continue
        p = min(1.0, args.sample_attack / n_atk)
        X, y = sample_file(path, lr, feat_raw, p, rng)
        aucs = {}
        for c in feat_strip:
            col = X[c] if c in X.columns else X[raw_by_strip.get(c, c)]
            aucs[c] = auc_vs_benign(pd.to_numeric(col, errors="coerce").to_numpy("float64"), y)
        matrix[tag] = aucs
        print(f"  [ok] {tag:22s} ataque~{min(n_atk, args.sample_attack):>7,}/"
              f"{n_atk:<10,} benigno={n_ben:>6,} p={p:.4f}")

    # Ensambla tabla feature x fichero de SEPARACIÓN = |AUC-0.5|+0.5 (0.5=nula, 1=perfecta).
    df = pd.DataFrame(matrix)                             # index=feature, cols=file tags
    sep = (df - 0.5).abs() + 0.5

    attack_tags = order_tags                             # todos son ficheros de ataque
    summary = pd.DataFrame({
        "sep_min": sep.min(axis=1),
        "sep_mean": sep.mean(axis=1),
        "sep_max": sep.max(axis=1),
        "n_files": sep.notna().sum(axis=1),
    })
    portmap_col = next((t for t in order_tags if t.endswith("Portmap")), None)
    if portmap_col:
        summary["sep_portmap"] = sep[portmap_col]        # held-out real

    print("\n=== TRANSFERIBLES: separación ALTA y ESTABLE en todos los ataques "
          "(orden por sep_min) ===")
    top_stable = summary.sort_values("sep_min", ascending=False).head(20)
    for feat, r in top_stable.iterrows():
        pm = f" portmap={r['sep_portmap']:.3f}" if portmap_col else ""
        print(f"   {feat:34s} min={r['sep_min']:.3f} mean={r['sep_mean']:.3f} "
              f"max={r['sep_max']:.3f} n={int(r['n_files'])}{pm}")

    print("\n=== ATAJOS: brillan en algún ataque pero colapsan en otro "
          "(sep_max alto, sep_min ~0.5) ===")
    shortcut = summary[(summary["sep_max"] >= 0.9) & (summary["sep_min"] <= 0.6)]
    shortcut = shortcut.sort_values("sep_max", ascending=False).head(20)
    for feat, r in shortcut.iterrows():
        pm = f" portmap={r['sep_portmap']:.3f}" if portmap_col else ""
        print(f"   {feat:34s} min={r['sep_min']:.3f} max={r['sep_max']:.3f} "
              f"n={int(r['n_files'])}{pm}")

    if args.out:
        sep.round(4).to_csv(args.out)
        summary.round(4).to_csv(str(args.out).replace(".csv", "_summary.csv"))
        print(f"\n[out] matriz -> {args.out}   resumen -> "
              f"{str(args.out).replace('.csv', '_summary.csv')}")


if __name__ == "__main__":
    main()