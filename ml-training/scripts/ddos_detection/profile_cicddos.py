#!/usr/bin/env python3
"""
profile_cicddos.py

Perfila CICDDoS2019 (CICFlowMeter-V3, 88 cols) para decidir features de una cabeza
detectora DDoS entrenada sobre datos REALES. Dos modos:

  1) CENSO (barato, todo el dataset):
       python3 profile_cicddos.py --census ../../datasets/CICDDoS2019
     Lee SOLO la columna Label de cada CSV bajo {01-12,03-11}. Tabula labels x fichero,
     totales ataque/benigno, y qué ataques están en train (01-12) vs test (03-11).

  2) PERFIL (un CSV, salud + poder discriminante):
       python3 profile_cicddos.py ../../datasets/CICDDoS2019/03-11/Portmap.csv --out stats.csv
     Por cada columna: dtype, %missing, %inf, %zero, nunique (capado), min/max/mean/std,
     constante?, y AUC ataque-vs-benigno (Mann-Whitney por rangos, SIN sklearn/scipy).
     El AUC dice cuánto separa CADA feature nativa por sí sola: base para seleccionar.

Notas medidas (DAY263): col 1 'Unnamed: 0'=índice pandas (tirar); col 63
'Fwd Header Length.1'=dup de la 42; col 86 'SimillarHTTP' suele vacía; Infinity/NaN
confinados a cols 22-23 ('Flow Bytes/s','Flow Packets/s'). AUC ~1.0 = separador casi
perfecto -> sospechar leakage/atajo, no celebrar. NUNCA usa grep.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

NUNIQUE_CAP = 50_000          # tope del set de únicos (acota memoria en cols alta-card)
LABEL_CANDIDATES = ["Label", "label", " Label"]


def find_label_col(columns):
    stripped = {c.strip(): c for c in columns}
    for cand in ("Label",):
        if cand in stripped:
            return stripped[cand]
    return None


# ---------------------------------------------------------------- CENSO ----
def census(root: Path):
    files = []
    for sub in ("01-12", "03-11"):
        d = root / sub
        if d.is_dir():
            files += sorted((sub, p) for p in d.glob("*.csv"))
    if not files:
        sys.exit(f"[FATAL] sin CSV bajo {root}/01-12 o /03-11")

    per_file = {}          # (sub, name) -> {label: count}
    label_split = {}       # label -> {'01-12': n, '03-11': n}
    for sub, path in files:
        head = pd.read_csv(path, nrows=0)
        lab = find_label_col(head.columns)
        if lab is None:
            print(f"  [WARN] {sub}/{path.name}: sin columna Label")
            continue
        # Solo la columna Label, por chunks, para no cargar GB.
        vc = pd.Series(dtype="int64")
        for chunk in pd.read_csv(path, usecols=[lab], chunksize=2_000_000, low_memory=False):
            c = chunk[lab].astype(str).str.strip().value_counts()
            vc = vc.add(c, fill_value=0)
        per_file[(sub, path.name)] = vc.astype("int64").to_dict()
        for label, n in vc.items():
            label_split.setdefault(label, {"01-12": 0, "03-11": 0})
            label_split[label][sub] += int(n)

    print("\n=== CENSO por fichero ===")
    for (sub, name), d in per_file.items():
        tot = sum(d.values())
        benign = d.get("BENIGN", 0)
        atk = tot - benign
        dominant = max(((k, v) for k, v in d.items() if k != "BENIGN"),
                       key=lambda kv: kv[1], default=("-", 0))
        print(f"  {sub}/{name:22s} filas={tot:>9,} benign={benign:>8,} "
              f"ataque={atk:>9,} dominante={dominant[0]}({dominant[1]:,})")

    print("\n=== Labels: train(01-12) vs test(03-11) ===")
    all_train = all_test = 0
    for label in sorted(label_split):
        tr = label_split[label]["01-12"]
        te = label_split[label]["03-11"]
        all_train += tr
        all_test += te
        flag = ""
        if label != "BENIGN":
            if tr and not te:
                flag = "  <- solo TRAIN"
            elif te and not tr:
                flag = "  <- solo TEST (ataque no visto)"
        print(f"  {label:16s} train={tr:>11,}  test={te:>11,}{flag}")
    print(f"  {'TOTAL':16s} train={all_train:>11,}  test={all_test:>11,}")


# --------------------------------------------------------------- AUC ------
def average_ranks(sorted_vals):
    """Rangos 1..n con promedio en empates, sobre un array YA ordenado."""
    n = len(sorted_vals)
    ranks = np.empty(n, dtype="float64")
    i = 0
    while i < n:
        j = i + 1
        while j < n and sorted_vals[j] == sorted_vals[i]:
            j += 1
        ranks[i:j] = (i + j + 1) / 2.0     # promedio de posiciones (1-based) i+1..j
        i = j
    return ranks


def auc_vs_benign(x: np.ndarray, y: np.ndarray):
    """AUC (attack=1) por Mann-Whitney. x finito, y en {0,1}. NaN -> filtrado fuera."""
    finite = np.isfinite(x)
    x = x[finite]
    y = y[finite]
    n_pos = int(y.sum())
    n_neg = len(y) - n_pos
    if n_pos == 0 or n_neg == 0:
        return np.nan, len(y)
    order = np.argsort(x, kind="mergesort")
    ranks_sorted = average_ranks(x[order])
    ranks = np.empty(len(x), dtype="float64")
    ranks[order] = ranks_sorted
    sum_pos = ranks[y == 1].sum()
    auc = (sum_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    return auc, len(y)      # AUC>0.5: valores altos -> ataque; <0.5: altos -> benigno


# -------------------------------------------------------------- PERFIL ----
def profile_file(csv_path: Path, out: Path, sample: int):
    head = pd.read_csv(csv_path, nrows=0)
    lab_col = find_label_col(head.columns)
    if lab_col is None:
        sys.exit("[FATAL] sin columna Label.")
    df = pd.read_csv(csv_path, low_memory=False)
    df.columns = [c.strip() for c in df.columns]
    lab_col = lab_col.strip()

    n = len(df)
    y = (df[lab_col].astype(str).str.strip() != "BENIGN").to_numpy().astype("int8")
    print(f"[perfil] {csv_path.name}  filas={n:,}  ataque={int(y.sum()):,}  "
          f"benigno={int((y==0).sum()):,}")

    if sample and n > sample:
        idx = np.random.default_rng(42).choice(n, size=sample, replace=False)
        idx.sort()
        df_s = df.iloc[idx]
        y_s = y[idx]
        print(f"[perfil] AUC sobre muestra de {sample:,} filas (rng=42)")
    else:
        df_s, y_s = df, y

    known_junk = {"Unnamed: 0", "Fwd Header Length.1", "SimillarHTTP", "Flow ID",
                  "Source IP", "Destination IP", "Timestamp", lab_col}
    rows = []
    for col in df.columns:
        s = df[col]
        n_missing = int(s.isna().sum())
        if pd.api.types.is_numeric_dtype(s):
            arr = s.to_numpy()
            n_inf = int(np.isinf(arr).sum())
            finite = arr[np.isfinite(arr)]
            n_zero = int((finite == 0).sum())
            cmin = float(finite.min()) if finite.size else np.nan
            cmax = float(finite.max()) if finite.size else np.nan
            cmean = float(finite.mean()) if finite.size else np.nan
            cstd = float(finite.std()) if finite.size else np.nan
            nuniq = int(np.unique(finite[:NUNIQUE_CAP]).size) if finite.size else 0
            if col not in known_junk:
                a, _ = auc_vs_benign(df_s[col].to_numpy().astype("float64"), y_s)
            else:
                a = np.nan
        else:
            n_inf = 0
            n_zero = 0
            cmin = cmax = cmean = cstd = np.nan
            vals = s.dropna().astype(str)
            nuniq = int(vals.iloc[:NUNIQUE_CAP].nunique())
            a = np.nan
        constant = (nuniq <= 1)
        rows.append({
            "column": col, "dtype": str(s.dtype),
            "pct_missing": round(100 * n_missing / n, 3),
            "pct_inf": round(100 * n_inf / n, 3),
            "pct_zero": round(100 * n_zero / n, 3),
            "nunique": nuniq, "constant": constant,
            "min": cmin, "max": cmax, "mean": cmean, "std": cstd,
            "auc_attack": None if np.isnan(a) else round(a, 4),
            "auc_sep": None if np.isnan(a) else round(abs(a - 0.5) + 0.5, 4),  # |AUC-.5|+.5
            "known_junk": col in known_junk,
        })
    stats = pd.DataFrame(rows)

    dead = stats[stats["constant"]]["column"].tolist()
    inf_cols = stats[stats["pct_inf"] > 0]["column"].tolist()
    scored = stats[stats["auc_sep"].notna()].sort_values("auc_sep", ascending=False)

    print(f"\n  columnas CONSTANTES ({len(dead)}): {dead}")
    print(f"  columnas con Inf ({len(inf_cols)}): {inf_cols}")
    print(f"\n  TOP-15 features por separación |AUC-0.5| (AUC ataque=1):")
    for _, r in scored.head(15).iterrows():
        arrow = ">benigno" if r["auc_attack"] < 0.5 else ">ataque "
        leak = "  [~perfecto: sospechar leakage]" if r["auc_sep"] >= 0.99 else ""
        print(f"   {r['column']:34s} AUC={r['auc_attack']:.4f} ({arrow}) sep={r['auc_sep']:.4f}{leak}")
    print(f"\n  features sin señal (AUC en 0.45-0.55): "
          f"{int(((stats['auc_sep']>=0.5)&(stats['auc_sep']<0.55)).sum())}")

    if out:
        stats.to_csv(out, index=False)
        print(f"\n[out] tabla completa -> {out}  ({len(stats)} columnas)")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="?", type=Path, help="CSV a perfilar")
    ap.add_argument("--census", type=Path, help="raíz CICDDoS2019 (modo censo, solo Label)")
    ap.add_argument("--out", type=Path, default=None, help="CSV con la tabla de stats")
    ap.add_argument("--sample", type=int, default=None,
                    help="submuestreo de filas para el AUC (ficheros enormes)")
    args = ap.parse_args()

    if args.census:
        census(args.census)
    elif args.csv:
        profile_file(args.csv, args.out, args.sample)
    else:
        ap.error("da un CSV a perfilar o --census DIR")


if __name__ == "__main__":
    main()