#!/usr/bin/env python3
"""
syn_rescue.py

Mide si añadir señal de FLAGS (SYN/ACK/RST counts + syn_ack_ratio derivada) rescata el
punto ciego de SYN sin ensuciar el resto ni el FPR. Entrena DOS modelos sobre las MISMAS
filas (baseline transferible vs aumentado) y compara al punto de operación FPR<=1%.

Tesis a contrastar: un SYN flood es mudo en backward -> las transferibles no lo ven; una
feature de flags (atajo por-ataque en la métrica cross-ataque) es el complemento dirigido
que lo rescata. Atajo como ÚNICA señal = malo; como señal complementaria a la clase que el
general no ve = rescate.

Reutiliza pick_features/find_label_col de train_ddos_head. NUNCA usa grep.

  python3 syn_rescue.py ../../datasets/CICDDoS2019 --summary auc_matrix_summary.csv
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

import train_ddos_head as H

FLAG_COLS = ["SYN Flag Count", "ACK Flag Count", "RST Flag Count"]


def load_day(root, sub, feats, extra, sample_attack, rng):
    d = root / sub
    files = sorted(d.glob("*.csv"))
    head = pd.read_csv(files[0], nrows=0)
    raw = {c.strip(): c for c in head.columns}
    lab_raw = H.find_label_col(head.columns)
    cols = feats + [c for c in extra if c in raw]
    use = [raw[c] for c in cols] + [lab_raw]
    Xs, ys, tags = [], [], []
    for path in files:
        for chunk in pd.read_csv(path, usecols=use, chunksize=H.CHUNK, low_memory=False):
            lab = chunk[lab_raw].astype(str).str.strip()
            is_atk = (lab != "BENIGN").to_numpy()
            p = min(1.0, sample_attack / max(1, is_atk.sum()))
            mask = ~is_atk if p >= 1.0 else (~is_atk) | (is_atk & (rng.random(len(chunk)) < p))
            mask = mask | is_atk if p >= 1.0 else mask
            if not mask.any():
                continue
            sub_df = chunk.loc[mask, [raw[c] for c in cols]]
            sub_df.columns = cols
            Xs.append(sub_df)
            ys.append(is_atk[mask].astype("int8"))
            tags.append(lab[mask].to_numpy())
    X = pd.concat(Xs, ignore_index=True).replace([np.inf, -np.inf], np.nan)
    return X, np.concatenate(ys), np.concatenate(tags)


def derive(X):
    if "SYN Flag Count" in X.columns and "ACK Flag Count" in X.columns:
        X = X.copy()
        X["syn_ack_ratio"] = X["SYN Flag Count"] / (X["ACK Flag Count"] + 1.0)
    return X


def op_point(model, Xte, yte, medians, fpr_target):
    proba = model.predict_proba(Xte.fillna(medians))[:, 1]
    benign = yte == 0
    grid = np.linspace(0.5, 0.999, 500)
    fprs = np.array([(proba[benign] >= t).mean() for t in grid])
    ok = np.where(fprs <= fpr_target)[0]
    return proba, (grid[ok[0]] if len(ok) else 0.5)


def evalu(proba, thr, yte, tag, label):
    pred = proba >= thr
    benign = yte == 0
    attack = yte == 1
    print(f"\n  [{label}] umbral={thr:.3f}  FPR_ben={pred[benign].mean():.4f}  "
          f"recall_atk={pred[attack].mean():.4f}")
    recs = {}
    for name in sorted(set(tag[attack])):
        m = (tag == name) & attack
        recs[name] = pred[m].mean()
        star = " <- SYN" if name.lower() == "syn" else (" <- held-out" if name.lower()=="portmap" else "")
        print(f"      {name:14s} {recs[name]:.4f}  (n={int(m.sum()):>7,}){star}")
    return recs


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", type=Path)
    ap.add_argument("--summary", type=Path, required=True)
    ap.add_argument("--sep-min", type=float, default=0.60)
    ap.add_argument("--sample-attack-train", type=int, default=80_000)
    ap.add_argument("--sample-attack-test", type=int, default=80_000)
    ap.add_argument("--fpr-target", type=float, default=0.01)
    args = ap.parse_args()

    base = [f for f in H.pick_features(args.summary, args.sep_min) if f != "Inbound"]
    rng = np.random.default_rng(H.SEED)
    print(f"[carga] base={len(base)} features + flags {FLAG_COLS}")
    Xtr, ytr, _ = load_day(args.root, "01-12", base, FLAG_COLS, args.sample_attack_train, rng)
    Xte, yte, tag = load_day(args.root, "03-11", base, FLAG_COLS, args.sample_attack_test, rng)
    Xtr, Xte = derive(Xtr), derive(Xte)

    aug = base + [c for c in FLAG_COLS if c in Xtr.columns]
    if "syn_ack_ratio" in Xtr.columns:
        aug = aug + ["syn_ack_ratio"]

    med = Xtr.median(numeric_only=True)
    print(f"  train={len(ytr):,}  test={len(yte):,}  "
          f"(SYN test n={int(((tag=='Syn')&(yte==1)).sum()):,})")

    results = {}
    for label, feats in [("BASELINE", base), ("AUMENTADO+flags", aug)]:
        m = RandomForestClassifier(n_estimators=200, class_weight="balanced",
                                   random_state=H.SEED, n_jobs=-1)
        m.fit(Xtr[feats].fillna(med[feats]), ytr)
        proba, thr = op_point(m, Xte[feats], yte, med[feats], args.fpr_target)
        results[label] = evalu(proba, thr, yte, tag, label)
        if label == "AUMENTADO+flags":
            imp = sorted(zip(feats, m.feature_importances_), key=lambda t: -t[1])[:8]
            print("      importancias:", [(f, round(v, 3)) for f, v in imp])

    print("\n=== VEREDICTO SYN ===")
    b = results["BASELINE"].get("Syn", float("nan"))
    a = results["AUMENTADO+flags"].get("Syn", float("nan"))
    print(f"  recall SYN  baseline={b:.4f}  aumentado={a:.4f}  (delta={a-b:+.4f})")
    print("  Comprueba que Portmap y el FPR NO empeoran: rescate limpio vs a costa de otros.")


if __name__ == "__main__":
    main()