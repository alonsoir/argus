#!/usr/bin/env python3
"""
retrain_ddos_head_A.py — reentrena la cabeza DDoS sobre el feature set A
(servible-hoy) con labels REALES de CICDDoS2019, y PERSISTE el artefacto
(modelo + feature_names) para cableado C++ y para el test de especificidad
sobre Neris (Camino 1).

NO reimplementa carga/split/seed: HEREDA el core probado de train_ddos_head.py
(igual que train_ddos_head_v2.py). A se DERIVA con el mismo mecanismo que v2
(pick_features ∩ RF23_SERVED − EXCLUDE_MEASURED); NO se teclea a mano.

Lo NUEVO frente a los dos harness (que solo miden y tiran el modelo):
  - persiste model.pkl (joblib) + scaler si aplica
  - persiste feature_names.json (ORDEN exacto = contrato del cableado C++)
  - persiste metadata.json (seed, sep_min, filas, sha del summary, recall)
"""
import argparse, json, sys, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib

# --- HERENCIA del core probado (mismo patrón que v2) ---
try:
    from train_ddos_head import load_day, pick_features, SEED
except ImportError as e:
    sys.exit(f"[FATAL] no importo el core original (train_ddos_head.py en el CWD): {e}")
try:
    from train_ddos_head_v2 import RF23_SERVED, EXCLUDE_MEASURED
except ImportError as e:
    sys.exit(f"[FATAL] no importo RF23_SERVED/EXCLUDE_MEASURED de v2: {e}")

# Contrato duro: features de la cabeza VIEJA que NO deben aparecer en A.
# No se "matan" con código: mueren por ausencia (no están en RF23_SERVED ni en
# el summary de CIC). El assert lo CONVIERTE EN GARANTÍA MEDIDA, no suposición.
FORBIDDEN_OLD = {"syn_ack_ratio", "geographical_concentration",
                 "packet_symmetry", "protocol_anomaly_score",
                 "traffic_amplification_factor", "flow_completion_rate",
                 "traffic_escalation_rate", "resource_saturation_score",
                 "packet_size_entropy"}  # el "sintético-9" del generador de Betas


def derive_A(summary_csv: Path, sep_min: float):
    """A = pick_features ∩ RF23_SERVED − EXCLUDE_MEASURED. Mismo mecanismo que v2."""
    selected = pick_features(summary_csv, sep_min)
    A = [f for f in selected if f in RF23_SERVED and f not in EXCLUDE_MEASURED]
    if not A:
        sys.exit("[FATAL] A vacío tras intersección con RF23_SERVED")
    intruso = [f for f in A if f in FORBIDDEN_OLD]
    if intruso:
        sys.exit(f"[FATAL] feature de la cabeza vieja en A: {intruso} (no debería ocurrir)")
    return A


def sha256_head(path: Path, n=1_000_000):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read(n))
    return h.hexdigest()[:12]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", type=Path)
    ap.add_argument("--summary", type=Path, required=True)
    ap.add_argument("--sep-min", type=float, default=0.60)
    ap.add_argument("--sample-attack-train", type=int, default=80_000)
    ap.add_argument("--sample-attack-test", type=int, default=80_000)
    ap.add_argument("--out", type=Path, default=Path("artifacts_ddos_A"))
    args = ap.parse_args()

    A = derive_A(args.summary, args.sep_min)
    print(f"[A] feature set ({len(A)}): {A}")

    rng = np.random.default_rng(SEED)
    Xtr, ytr, _   = load_day(args.root, "01-12", A, args.sample_attack_train, rng)
    Xte, yte, tag = load_day(args.root, "03-11", A, args.sample_attack_test, rng)

    # Orden de columnas = contrato. Fijar EXPLÍCITO, no confiar en el de load_day.
    Xtr = Xtr[A]; Xte = Xte[A]
    print(f"train: {len(Xtr):,} filas ({int(ytr.sum()):,} atk / {int((1-ytr).sum()):,} ben)")
    print(f"test : {len(Xte):,} filas ({int(yte.sum()):,} atk / {int((1-yte).sum()):,} ben)")

    # Imputación por mediana de TRAIN (misma disciplina del core; explícita aquí)
    med = Xtr.median(numeric_only=True)
    Xtr = Xtr.fillna(med); Xte = Xte.fillna(med)

    model = RandomForestClassifier(n_estimators=200, class_weight="balanced",
                                   random_state=SEED, n_jobs=-1)
    model.fit(Xtr, ytr)

    # Recall por ataque a umbral 0.5 (baseline honesto; el punto de operación de
    # despliegue lo fija operating_point.py, NO este script — misma nota que v2).
    proba = model.predict_proba(Xte)[:, 1]
    pred = (proba >= 0.5).astype(int)
    print("\n=== recall por ataque (umbral 0.5) ===")
    per = {}
    for t in sorted(set(tag[yte == 1])):
        m = (tag == t) & (yte == 1)
        r = float(pred[m].mean()) if m.sum() else float("nan")
        per[t] = r
        print(f"  {t:20s} {r:.4f}  (n={int(m.sum())})")
    # Especificidad: FP sobre el benigno held-out de CIC
    benmask = (yte == 0)
    fp = float(pred[benmask].mean())
    print(f"\n  FP benigno CIC held-out (umbral 0.5): {fp:.4f}  (n={int(benmask.sum())})")

    # --- PERSISTENCIA: lo único nuevo. Modelo + contrato de features + metadata ---
    out = args.out; out.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out / "ddos_head_A.pkl")
    (out / "feature_names.json").write_text(json.dumps(A, indent=2))
    meta = {"seed": SEED, "sep_min": args.sep_min, "features": A,
            "n_features": len(A), "summary_sha": sha256_head(args.summary),
            "train_rows": int(len(Xtr)), "test_rows": int(len(Xte)),
            "recall_per_attack": per, "fp_benign_cic": fp,
            "median_impute": {k: float(v) for k, v in med.items()}}
    (out / "metadata.json").write_text(json.dumps(meta, indent=2))
    print(f"\n[persistido] {out}/ddos_head_A.pkl + feature_names.json + metadata.json")
    print("  feature_names.json ES EL CONTRATO que el cableado C++ debe respetar (orden incluido).")

if __name__ == "__main__":
    main()
