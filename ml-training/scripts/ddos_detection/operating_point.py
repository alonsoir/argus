#!/usr/bin/env python3
"""
operating_point.py

Convierte el "FPR=7.86% a umbral 0.5" en una curva de punto de operación, y autopsia el
benigno mal clasificado. Reutiliza la carga y selección de features de train_ddos_head.py.

  - Barrido de umbral: para cada threshold, FPR sobre benigno, recall global de ataque, y
    recall de los dos ataques que importan (Portmap held-out, Syn punto ciego). Responde:
    ¿existe un punto con FPR<=target que aún caza?
  - Autopsia de falsos positivos: ¿el benigno marcado ataque es un clúster coherente
    (mediana de features desplazada HACIA ataque -> benigno atacante-símil, addressable)
    o difuso (mediana ~ benigno correcto -> ruido del modelo)?

Modelo = SIN Inbound por defecto (el honesto, sin crutch de entorno). NUNCA usa grep.

  python3 operating_point.py ../../datasets/CICDDoS2019 --summary auc_matrix_summary.csv
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

import train_ddos_head as H     # co-localizado en ddos_detection/


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", type=Path)
    ap.add_argument("--summary", type=Path, required=True)
    ap.add_argument("--sep-min", type=float, default=0.60)
    ap.add_argument("--sample-attack-train", type=int, default=80_000)
    ap.add_argument("--sample-attack-test", type=int, default=80_000)
    ap.add_argument("--keep-inbound", action="store_true",
                    help="incluir Inbound (por defecto se quita: modelo honesto)")
    ap.add_argument("--fpr-target", type=float, default=0.01)
    args = ap.parse_args()

    feats = H.pick_features(args.summary, args.sep_min)
    if not args.keep_inbound:
        feats = [f for f in feats if f != "Inbound"]
    print(f"[features] {len(feats)}  (Inbound {'DENTRO' if 'Inbound' in feats else 'FUERA'})")

    rng = np.random.default_rng(H.SEED)
    Xtr, ytr, _ = H.load_day(args.root, "01-12", feats, args.sample_attack_train, rng)
    Xte, yte, tag = H.load_day(args.root, "03-11", feats, args.sample_attack_test, rng)
    medians = Xtr.median(numeric_only=True)
    model = RandomForestClassifier(n_estimators=200, class_weight="balanced",
                                   random_state=H.SEED, n_jobs=-1)
    model.fit(Xtr.fillna(medians), ytr)

    Xte_i = Xte.fillna(medians)
    proba = model.predict_proba(Xte_i)[:, 1]
    benign = (yte == 0)
    attack = (yte == 1)
    is_portmap = np.array([t.lower() == "portmap" for t in tag]) & attack
    is_syn = np.array([t.lower() == "syn" for t in tag]) & attack

    print("\n=== BARRIDO DE UMBRAL (modelo honesto) ===")
    print(f"  {'thr':>5} {'FPR_ben':>9} {'recall_atk':>11} {'rec_Portmap':>12} {'rec_Syn':>9}")
    thresholds = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.97, 0.99]
    for thr in thresholds:
        pred = proba >= thr
        fpr = pred[benign].mean()
        rec = pred[attack].mean()
        rpm = pred[is_portmap].mean() if is_portmap.any() else float("nan")
        rsy = pred[is_syn].mean() if is_syn.any() else float("nan")
        print(f"  {thr:>5.2f} {fpr:>9.4f} {rec:>11.4f} {rpm:>12.4f} {rsy:>9.4f}")

    # Punto de operación: umbral MÁS BAJO con FPR<=target (maximiza recall bajo la restricción).
    grid = np.linspace(0.5, 0.999, 500)
    fprs = np.array([(proba[benign] >= t).mean() for t in grid])
    ok = np.where(fprs <= args.fpr_target)[0]
    if len(ok):
        t_op = grid[ok[0]]
        pred = proba >= t_op
        print(f"\n=== PUNTO DE OPERACIÓN  (FPR<={args.fpr_target}) ===")
        print(f"  umbral={t_op:.3f}  FPR_ben={pred[benign].mean():.4f}  "
              f"recall_atk={pred[attack].mean():.4f}  "
              f"Portmap={pred[is_portmap].mean():.4f}  Syn={pred[is_syn].mean():.4f}")
    else:
        t_op = 0.5
        print(f"\n=== PUNTO DE OPERACIÓN ===\n  NINGÚN umbral logra FPR<={args.fpr_target}. "
              f"El benigno de este testbed no se separa limpio -> flanco duro, no de tuning.")

    # Autopsia del benigno mal clasificado a umbral 0.5.
    pred05 = proba >= 0.5
    fp = benign & pred05           # benigno marcado ataque
    tn = benign & ~pred05          # benigno correcto
    print(f"\n=== AUTOPSIA FALSOS POSITIVOS (umbral 0.5)  FP={int(fp.sum())} de {int(benign.sum())} benignos ===")
    imp = sorted(zip(feats, model.feature_importances_), key=lambda t: -t[1])[:8]
    print(f"  {'feature':30s} {'ben_correcto':>13} {'ben_FP':>12} {'ataque':>12}  lectura")
    for f, _ in imp:
        med_tn = Xte_i.loc[tn, f].median()
        med_fp = Xte_i.loc[fp, f].median()
        med_at = Xte_i.loc[attack, f].median()
        # ¿El FP está desplazado hacia ataque respecto al benigno correcto?
        toward = ""
        span = abs(med_at - med_tn)
        if span > 0:
            frac = (med_fp - med_tn) / (med_at - med_tn)
            if frac > 0.5:
                toward = "-> como ATAQUE"
            elif frac < 0.1:
                toward = "~ benigno"
        print(f"  {f:30s} {med_tn:>13.3g} {med_fp:>12.3g} {med_at:>12.3g}  {toward}")
    print("\n  Si la mayoría de features del FP están '-> como ATAQUE', el benigno mal "
          "clasificado es\n  atacante-símil (addressable con una feature que los distinga). "
          "Si están '~ benigno',\n  el modelo dispara sobre benigno normal -> problema de fondo.")


if __name__ == "__main__":
    main()