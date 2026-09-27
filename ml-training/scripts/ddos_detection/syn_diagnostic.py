#!/usr/bin/env python3
"""
syn_diagnostic.py

Por qué los flags no rescatan SYN. Distingue:
  H1: flag counts degenerados (constantes/mal poblados) -> RF los ignora con razón.
  H2: SYN flood es fenómeno de TASA -> el SYN que se escapa es indistinguible del benigno
      en TODO el espacio por-flujo -> solo lo ven features agregadas/ventana (familia de
      source_ip_dispersion). Techo fundamental por-flujo.

Método: entrena el modelo base (23 transferibles) en 01-12, lo aplica a 03-11/Syn.csv,
parte el SYN en CAZADO/ESCAPADO a umbral 0.5, y mide qué separa cada grupo del benigno.
La cifra clave = max AUC de ESCAPADO-vs-benigno: ~0.5 en todo -> H2; algo alto -> señal en
la mesa. Reutiliza train_ddos_head y cross_attack_auc. NUNCA usa grep.

  python3 syn_diagnostic.py ../../datasets/CICDDoS2019 --summary auc_matrix_summary.csv
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

import train_ddos_head as H
from cross_attack_auc import auc_vs_benign

FLAGS = ["SYN Flag Count", "ACK Flag Count", "RST Flag Count", "FIN Flag Count",
         "PSH Flag Count", "URG Flag Count"]


def load_syn_file(root, base, rng, sample_attack=200_000):
    path = root / "03-11" / "Syn.csv"
    head = pd.read_csv(path, nrows=0)
    raw = {c.strip(): c for c in head.columns}
    lab_raw = H.find_label_col(head.columns)
    seen, cols = set(), []
    for c in base + FLAGS:                     # URG Flag Count puede estar en ambos -> dedup
        if c in raw and c not in seen:
            cols.append(c)
            seen.add(c)
    use = [raw[c] for c in cols] + [lab_raw]
    Xs, ys = [], []
    for chunk in pd.read_csv(path, usecols=use, chunksize=H.CHUNK, low_memory=False):
        lab = chunk[lab_raw].astype(str).str.strip()
        is_atk = (lab != "BENIGN").to_numpy()
        p = min(1.0, sample_attack / max(1, is_atk.sum()))
        mask = (~is_atk) | (is_atk & (rng.random(len(chunk)) < p)) if p < 1 else (~is_atk) | is_atk
        if mask.any():
            d = chunk.loc[mask, [raw[c] for c in cols]]
            d.columns = cols
            Xs.append(d)
            ys.append(is_atk[mask].astype("int8"))
    X = pd.concat(Xs, ignore_index=True).replace([np.inf, -np.inf], np.nan)
    if "SYN Flag Count" in X.columns and "ACK Flag Count" in X.columns:
        X["syn_ack_ratio"] = X["SYN Flag Count"] / (X["ACK Flag Count"] + 1.0)
    return X, np.concatenate(ys), cols


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", type=Path)
    ap.add_argument("--summary", type=Path, required=True)
    ap.add_argument("--sep-min", type=float, default=0.60)
    ap.add_argument("--sample-attack-train", type=int, default=80_000)
    args = ap.parse_args()

    base = [f for f in H.pick_features(args.summary, args.sep_min) if f != "Inbound"]
    rng = np.random.default_rng(H.SEED)

    # Modelo base entrenado en 01-12.
    Xtr, ytr, _ = H.load_day(args.root, "01-12", base, args.sample_attack_train, rng)
    med = Xtr.median(numeric_only=True)
    model = RandomForestClassifier(n_estimators=200, class_weight="balanced",
                                   random_state=H.SEED, n_jobs=-1).fit(Xtr.fillna(med), ytr)

    # Fichero SYN con flags.
    X, y, cols = load_syn_file(args.root, base, rng)
    benign = y == 0
    attack = y == 1
    print(f"[syn] test: {int(attack.sum()):,} SYN / {int(benign.sum()):,} benigno")

    # Salud de flags (H1): mediana ataque vs benigno + nunique + %cero.
    print("\n=== SALUD DE FLAGS (H1) ===")
    print(f"  {'columna':22s} {'nuniq':>6} {'%cero':>7} {'med_SYN':>9} {'med_ben':>9}")
    for c in [c for c in FLAGS if c in X.columns] + (["syn_ack_ratio"] if "syn_ack_ratio" in X else []):
        v = X[c].to_numpy()
        fin = v[np.isfinite(v)]
        print(f"  {c:22s} {len(np.unique(fin[:50000])):>6} "
              f"{100*(fin==0).mean():>6.1f}% {np.median(v[attack]):>9.3g} "
              f"{np.median(v[benign]):>9.3g}")

    # Parte SYN en cazado/escapado con el modelo base.
    # Alinea SIEMPRE al orden/nombres que el modelo registró en fit (headers de 01-12 y
    # de Syn.csv pueden diferir en un espacio o en una columna presente/ausente).
    feat_used = list(model.feature_names_in_)
    faltan = [f for f in feat_used if f not in X.columns]
    if faltan:
        print(f"  [aviso] features del fit ausentes en Syn.csv (se imputan a mediana): {faltan}")
    Xp = X.reindex(columns=feat_used)
    proba = model.predict_proba(Xp.fillna(med.reindex(index=feat_used)))[:, 1]
    caught = attack & (proba >= 0.5)
    missed = attack & (proba < 0.5)
    print(f"\n  SYN cazado(>=0.5)={int(caught.sum()):,}  escapado={int(missed.sum()):,} "
          f"({100*missed.sum()/attack.sum():.1f}%)")

    # AUC de CADA feature: todo-SYN vs benigno, y ESCAPADO vs benigno.
    feat_all = cols + (["syn_ack_ratio"] if "syn_ack_ratio" in X.columns else [])
    rows = []
    for c in feat_all:
        x = X[c].to_numpy().astype("float64")
        a_all = auc_vs_benign(np.r_[x[attack], x[benign]],
                              np.r_[np.ones(attack.sum()), np.zeros(benign.sum())])
        a_mis = auc_vs_benign(np.r_[x[missed], x[benign]],
                              np.r_[np.ones(missed.sum()), np.zeros(benign.sum())])
        sep_mis = abs(a_mis - 0.5) + 0.5 if not np.isnan(a_mis) else np.nan
        rows.append((c, a_all, a_mis, sep_mis))
    rows.sort(key=lambda r: -(r[3] if not np.isnan(r[3]) else 0))

    print("\n=== ¿QUÉ SEPARA EL SYN ESCAPADO DEL BENIGNO? (H2) ===")
    print(f"  {'feature':30s} {'AUC_todoSYN':>12} {'AUC_escapado':>13} {'sep_escapado':>13}")
    for c, a_all, a_mis, sep in rows[:15]:
        print(f"  {c:30s} {a_all:>12.4f} {a_mis:>13.4f} {sep:>13.4f}")

    best = max((r[3] for r in rows if not np.isnan(r[3])), default=float("nan"))
    print("\n=== VEREDICTO ===")
    print(f"  Máxima separación ESCAPADO-vs-benigno = {best:.4f}")
    if best < 0.6:
        print("  -> H2: el SYN escapado es INDISTINGUIBLE del benigno por-flujo. Techo "
              "fundamental.\n     Solo features de TASA/ventana (familia source_ip_dispersion) "
              "pueden cazarlo.")
    else:
        print("  -> Hay señal por-flujo en el escapado que el modelo base no explota "
              "(revisar esa feature).")


if __name__ == "__main__":
    main()