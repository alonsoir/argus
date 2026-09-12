#!/usr/bin/env python3
"""
train_ddos_head.py

Harness HONESTO para medir el techo de una cabeza detectora DDoS sobre features REALES de
CICDDoS2019. No es aún la cabeza de producción: es la medición que decide si Path B
(nativas + extractor base) vale la pena antes de cablear nada.

Disciplina anti-autoengaño (en este dataset es trivial sacar 0.99 por leakage):
  - Split CRUZADO por día: entrena en 01-12, evalúa en 03-11. Nada de split aleatorio
    dentro de un ataque puro (fugaría el tipo de ataque).
  - Portmap = held-out REAL (genuinamente test-only). Se reporta su recall aparte.
  - El benigno es ~0.1%: la métrica que manda es el FPR sobre benigno (un NDR que inunda
    de falsos positivos es inútil), no el accuracy. Se reportan PR-AUC y recall por ataque.
  - Se entrena SIEMPRE dos veces: con y sin `Inbound`, para descontar el leakage de entorno
    (todo el ataque va a una víctima fija -> "inbound=ataque" es casi circular).

Features = las TRANSFERIBLES del barrido cross-ataque (sep_min alto en auc_matrix_summary).
Se leen del CSV resumen por umbral, así el conjunto es reproducible y no elegido a mano.
RandomForest class_weight='balanced', random_state=42 (convención del repo). NUNCA usa grep.

  python3 train_ddos_head.py ../../datasets/CICDDoS2019 --summary auc_matrix_summary.csv
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (average_precision_score, roc_auc_score,
                             precision_recall_fscore_support)

CHUNK = 2_000_000
SEED = 42
# Nunca features de identidad/atajo, aunque el umbral las dejara pasar:
HARD_EXCLUDE = {
    "Unnamed: 0", "Flow ID", "Source IP", "Destination IP", "Source Port",
    "Destination Port", "Timestamp", "Label", "Protocol",
    "Min Packet Length", "Fwd Packet Length Min",
}


def find_label_col(columns):
    return {c.strip(): c for c in columns}.get("Label")


def pick_features(summary_csv: Path, sep_min: float):
    s = pd.read_csv(summary_csv, index_col=0)
    if "sep_min" not in s.columns:
        sys.exit(f"[FATAL] {summary_csv} no tiene columna sep_min")
    feats = [f for f in s.index[s["sep_min"] >= sep_min] if f not in HARD_EXCLUDE]
    if not feats:
        sys.exit(f"[FATAL] 0 features con sep_min>={sep_min}")
    return feats


def load_day(root: Path, sub: str, feats, sample_attack: int, rng):
    d = root / sub
    files = sorted(d.glob("*.csv"))
    if not files:
        sys.exit(f"[FATAL] sin CSV en {d}")
    Xs, ys, tags = [], [], []
    head = pd.read_csv(files[0], nrows=0)
    raw = {c.strip(): c for c in head.columns}
    lab_raw = find_label_col(head.columns)
    use = [raw[f] for f in feats if f in raw] + [lab_raw]
    missing = [f for f in feats if f not in raw]
    if missing:
        print(f"  [WARN] {sub}: features ausentes en cabecera: {missing}")
    for path in files:
        for chunk in pd.read_csv(path, usecols=use, chunksize=CHUNK, low_memory=False):
            lab = chunk[lab_raw].astype(str).str.strip()
            is_atk = (lab != "BENIGN").to_numpy()
            mask = ~is_atk
            p = min(1.0, sample_attack / max(1, is_atk.sum()))
            if p < 1.0:
                mask = mask | (is_atk & (rng.random(len(chunk)) < p))
            else:
                mask = mask | is_atk
            if not mask.any():
                continue
            sub_df = chunk.loc[mask, [raw[f] for f in feats if f in raw]]
            sub_df.columns = [f for f in feats if f in raw]
            Xs.append(sub_df)
            ys.append(is_atk[mask].astype("int8"))
            tags.append(lab[mask].to_numpy())
    X = pd.concat(Xs, ignore_index=True)
    y = np.concatenate(ys)
    tag = np.concatenate(tags)
    # Inf (solo Flow Bytes/s / Flow Packets/s) -> NaN -> imputa por mediana de TRAIN.
    X = X.replace([np.inf, -np.inf], np.nan)
    return X, y, tag


def evaluate(model, X, y, tag, medians, label):
    Xi = X.fillna(medians)
    proba = model.predict_proba(Xi)[:, 1]
    pred = (proba >= 0.5).astype("int8")
    ap = average_precision_score(y, proba)
    roc = roc_auc_score(y, proba)
    # FPR sobre benigno = benigno marcado como ataque.
    benign = (y == 0)
    fpr = float(pred[benign].mean()) if benign.any() else float("nan")
    pr, rc, f1, _ = precision_recall_fscore_support(y, pred, average="binary",
                                                    zero_division=0)
    print(f"\n  [{label}]  PR-AUC={ap:.4f}  ROC-AUC={roc:.4f}  "
          f"precision={pr:.4f} recall={rc:.4f} f1={f1:.4f}")
    print(f"           FPR benigno={fpr:.4f}  ({int(pred[benign].sum())}/{int(benign.sum())} "
          f"benignos marcados ataque)")
    # Recall por tipo de ataque en test (Portmap = held-out real).
    print("           recall por ataque:")
    for name in sorted(set(tag[y == 1])):
        m = (tag == name) & (y == 1)
        rec = float(pred[m].mean())
        star = "  <- HELD-OUT" if name.lower() == "portmap" else ""
        print(f"             {name:14s} {rec:.4f}  (n={int(m.sum()):>7,}){star}")
    return ap, roc, fpr


def run(root, feats, sample_train, sample_test, label):
    rng = np.random.default_rng(SEED)
    print(f"\n########## MODELO: {label}  ({len(feats)} features) ##########")
    print("  features:", feats)
    Xtr, ytr, _ = load_day(root, "01-12", feats, sample_train, rng)
    Xte, yte, tag = load_day(root, "03-11", feats, sample_test, rng)
    medians = Xtr.median(numeric_only=True)
    Xtr_i = Xtr.fillna(medians)
    print(f"  train: {len(ytr):,} filas ({int(ytr.sum()):,} ataque / {int((ytr==0).sum()):,} benigno)")
    print(f"  test : {len(yte):,} filas ({int(yte.sum()):,} ataque / {int((yte==0).sum()):,} benigno)")
    model = RandomForestClassifier(n_estimators=200, class_weight="balanced",
                                   random_state=SEED, n_jobs=-1, max_depth=None)
    model.fit(Xtr_i, ytr)
    imp = sorted(zip(feats, model.feature_importances_), key=lambda t: -t[1])
    print("  importancias top-10:", [(f, round(v, 3)) for f, v in imp[:10]])
    return evaluate(model, Xte, yte, tag, medians, label)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", type=Path)
    ap.add_argument("--summary", type=Path, required=True,
                    help="auc_matrix_summary.csv del barrido cross-ataque")
    ap.add_argument("--sep-min", type=float, default=0.60)
    ap.add_argument("--sample-attack-train", type=int, default=80_000)
    ap.add_argument("--sample-attack-test", type=int, default=80_000)
    args = ap.parse_args()

    feats = pick_features(args.summary, args.sep_min)
    print(f"[features] {len(feats)} transferibles con sep_min>={args.sep_min}")

    # Modelo A: conjunto completo transferible.
    a = run(args.root, feats, args.sample_attack_train, args.sample_attack_test,
            "CON Inbound")
    # Modelo B: sin Inbound (descuenta leakage de entorno).
    feats_no_in = [f for f in feats if f != "Inbound"]
    if len(feats_no_in) < len(feats):
        b = run(args.root, feats_no_in, args.sample_attack_train, args.sample_attack_test,
                "SIN Inbound")
        print("\n########## VEREDICTO ##########")
        print(f"  PR-AUC  con Inbound={a[0]:.4f}  sin={b[0]:.4f}  (delta={a[0]-b[0]:+.4f})")
        print(f"  FPR ben con Inbound={a[2]:.4f}  sin={b[2]:.4f}")
        print("  Si el rendimiento se desploma sin Inbound, gran parte era leakage de entorno.")
    else:
        print("\n[nota] Inbound no estaba en el conjunto; sin ablación de entorno.")


if __name__ == "__main__":
    main()