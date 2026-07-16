#!/usr/bin/env python3
# tools/eval/eval_level1_model_csv.py
# DEBT-L1-NO-REPRODUCIBLE-HOLDOUT-001 — Vía B (diagnóstico del MODELO aislado).
#
# Mide el ONNX vivo (level1_attack_detector.onnx) sobre el CSV de Wednesday
# (CICIDS2017), con threshold leído del config VIVO y las 23 features tomadas
# POR NOMBRE del oráculo (metadata). Reproduce el eval fósil
# (wednesday_eval_report.json) con el modelo correcto y generador versionado.
#
# ALCANCE (DAY 220): esto NO es un holdout. El entrenador usó split aleatorio
# 80/20 estratificado sobre los 8 días juntos (inferido por aritmética exacta:
# 566149 = 0.2 * 2830743, matriz del metadata). Wednesday está ~80% dentro del
# entrenamiento. Este número es un SANITY CHECK del contrato modelo+features+
# threshold sobre datos reales, mayormente in-sample. La generalización se mide
# aparte (vía A, pipeline vivo sobre CTU-13 Neris).
#
# IMPUTACIÓN: inf→NaN→mediana→fillna(0), réplica del pipeline documentado
# (notebook 02, commit f53c676a), con medianas computadas sobre el CONCAT DE
# LOS 8 DÍAS (universo del entrenador por aritmética), no sobre los 4 días
# del 02. Ver DAY220_FINDINGS.
#
# NO sustituye a `make eval-level1-holdout` (vía A, pipeline vivo).
# AUTHORS: Alonso Isidoro Roman + Claude (Anthropic) — DAY 220 (16-jul-2026)

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import onnxruntime as ort


def md5(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        while b := f.read(chunk):
            h.update(b)
    return h.hexdigest()


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True,
            stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "UNKNOWN"


def find_threshold(cfg: dict, key: str = "level1_attack") -> tuple[float, str]:
    """Busca el threshold vivo en el config sin asumir la ruta exacta.
    Fail-closed: si no hay exactamente UN candidato, aborta listando lo hallado.
    (Regla DAY 219: verificar la ruta antes de concluir sobre el contenido.)"""
    hits: list[tuple[str, float]] = []

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                p = f"{path}.{k}" if path else k
                if k == key and isinstance(v, (int, float)):
                    hits.append((p, float(v)))
                else:
                    walk(v, p)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(cfg, "")
    if len(hits) == 1:
        return hits[0][1], hits[0][0]
    sys.exit(f"FAIL-CLOSED: '{key}' hallado {len(hits)} veces en el config "
             f"(esperado 1): {hits}. Verificar ml_detector_config.json.")


def load_features_csv(path: str, feature_names: list[str],
                      with_label: bool) -> pd.DataFrame:
    """Carga un CSV de CICIDS con encoding latin-1 (paridad notebook 02),
    quedándose solo con las 23 columnas del oráculo (+ Label si procede).
    Fail-closed si falta alguna columna."""
    wanted = {n.strip() for n in feature_names}
    if with_label:
        wanted = wanted | {"Label"}
    df = pd.read_csv(
        path, encoding="latin-1", low_memory=False,
        usecols=lambda c: c.strip() in wanted)
    df.columns = [c.strip() for c in df.columns]
    missing = [n for n in feature_names if n.strip() not in df.columns]
    if missing:
        sys.exit(f"FAIL-CLOSED: columnas ausentes en {path}: {missing}")
    if with_label and "Label" not in df.columns:
        sys.exit(f"FAIL-CLOSED: columna Label ausente en {path}")
    return df


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Vía B — eval del modelo L1 aislado sobre CSV CICIDS")
    ap.add_argument("--model", required=True,
                    help="level1_attack_detector.onnx (el VIVO)")
    ap.add_argument("--metadata", required=True,
                    help="level1_attack_detector_metadata.json (oráculo)")
    ap.add_argument("--config", required=True,
                    help="ml_detector_config.json (threshold VIVO)")
    ap.add_argument("--csv", required=True,
                    help="CSV a evaluar (Wednesday-workingHours.pcap_ISCX.csv)")
    ap.add_argument("--train-universe-csvs", nargs=8, required=True,
                    help="Los 8 CSVs de MachineLearningCVE. Universo del "
                         "entrenador (aritmética 566149 = 0.2*2830743); las "
                         "medianas de imputación se computan sobre su concat.")
    ap.add_argument("--limit", type=int, default=0,
                    help="Smoke test: evaluar solo las N primeras filas "
                         "(0 = todas). Las medianas se computan igual.")
    ap.add_argument("--out", required=True, help="report JSON de salida")
    args = ap.parse_args()

    # ── Oráculo: 23 nombres, en orden ────────────────────────────────────
    meta = json.load(open(args.metadata))
    feature_names: list[str] = meta["feature_names"]
    if len(feature_names) != 23:
        sys.exit(f"FAIL-CLOSED: oráculo declara {len(feature_names)} "
                 f"features, esperadas 23")

    # ── Threshold VIVO (no hardcodear; ruta verificada por walk) ─────────
    cfg = json.load(open(args.config))
    threshold, threshold_path = find_threshold(cfg, "level1_attack")
    print(f"[config] threshold level1_attack = {threshold} "
          f"(en {threshold_path})", file=sys.stderr)

    # ── Medianas del universo del entrenador (8 días) ────────────────────
    print("[imputación] computando medianas sobre 8 CSVs "
          "(universo del entrenador)...", file=sys.stderr)
    universe_md5: dict[str, str] = {}
    frames = []
    for p in args.train_universe_csvs:
        universe_md5[p] = md5(p)
        print(f"  cargando {Path(p).name}...", file=sys.stderr)
        frames.append(load_features_csv(p, feature_names, with_label=False))
    universe = pd.concat(frames, ignore_index=True)
    del frames
    n_universe = len(universe)
    if n_universe != 2_830_743:
        print(f"[AVISO] universo = {n_universe} filas; la aritmética del "
              f"metadata esperaba 2830743. Registrado en el report.",
              file=sys.stderr)
    universe = universe.apply(pd.to_numeric, errors="coerce")
    universe = universe.replace([np.inf, -np.inf], np.nan)
    cols = [n.strip() for n in feature_names]
    medians = universe[cols].median()  # por columna, NaN excluidos
    del universe

    # ── CSV a evaluar: mismo pipeline de imputación ──────────────────────
    df = load_features_csv(args.csv, feature_names, with_label=True)
    if args.limit > 0:
        df = df.head(args.limit)
        print(f"[smoke] limitado a {args.limit} filas", file=sys.stderr)
    y_true = (df["Label"].str.strip() != "BENIGN").astype(int).to_numpy()

    X = df[cols].apply(pd.to_numeric, errors="coerce")
    n_total = len(X)
    n_bad = int((~np.isfinite(
        X.to_numpy(dtype=np.float64)).all(axis=1)).sum())
    X = X.replace([np.inf, -np.inf], np.nan)
    X = X.fillna(medians).fillna(0.0)  # mediana global → 0 residual (02:199)
    X = X.to_numpy(dtype=np.float32)

    # ── Inferencia por lotes ─────────────────────────────────────────────
    sess = ort.InferenceSession(args.model,
                                providers=["CPUExecutionProvider"])
    input_name = sess.get_inputs()[0].name
    output_names = [o.name for o in sess.get_outputs()]
    print(f"[onnx] input='{input_name}' outputs={output_names}",
          file=sys.stderr)

    probs = np.empty(len(X), dtype=np.float64)
    B = 65_536
    proba_shape = None
    for i in range(0, len(X), B):
        outs = sess.run(None, {input_name: X[i:i + B]})
        p = outs[1]  # sklearn-onnx RF: [label, probabilities]
        if isinstance(p, list):  # ZipMap: lista de dicts {clase: prob}
            proba_shape = "zipmap"
            probs[i:i + B] = [d.get(1, d.get("ATTACK", 0.0)) for d in p]
        else:  # tensor (N, 2)
            proba_shape = f"tensor{p.shape[1:]}"
            probs[i:i + B] = p[:, 1]
        done = min(i + B, len(X))
        print(f"\r[onnx] {done}/{len(X)}", end="", file=sys.stderr)
    print("", file=sys.stderr)

    y_pred = (probs >= threshold).astype(int)

    tp = int(((y_pred == 1) & (y_true == 1)).sum())
    fn = int(((y_pred == 0) & (y_true == 1)).sum())
    fp = int(((y_pred == 1) & (y_true == 0)).sum())
    tn = int(((y_pred == 0) & (y_true == 0)).sum())

    report = {
        "eval": "level1_model_csv",
        "scope": ("SANITY CHECK del modelo aislado sobre datos reales, "
                  "mayormente IN-SAMPLE (split 80/20 sobre 8 días, "
                  "DAY220_FINDINGS). NO es holdout. NO es el pipeline."),
        "generated_by": "tools/eval/eval_level1_model_csv.py",
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "model": {"path": args.model, "md5": md5(args.model)},
        "metadata_oracle": {"path": args.metadata,
                            "md5": md5(args.metadata)},
        "threshold": {"value": threshold,
                      "config_path_in_json": threshold_path,
                      "source_file": args.config,
                      "config_md5": md5(args.config)},
        "eval_csv": {"path": args.csv, "md5": md5(args.csv),
                     "rows_evaluated": n_total,
                     "rows_nonfinite_before_imputation": n_bad,
                     "smoke_limit": args.limit},
        "imputation": {
            "policy": "inf->NaN->median(8-day concat)->fillna(0)",
            "rationale": ("universo del entrenador inferido por aritmética "
                          "exacta (566149 = 0.2*2830743); medianas del "
                          "notebook 02 (universo de 4 días) descartadas por "
                          "no corresponder. DAY220_FINDINGS."),
            "universe_rows": n_universe,
            "universe_csvs_md5": universe_md5,
            "medians": {k: float(v) for k, v in medians.items()},
        },
        "onnx_proba_output_shape": proba_shape,
        "confusion": {"tp": tp, "fn": fn, "fp": fp, "tn": tn},
        "recall": tp / (tp + fn) if (tp + fn) else None,
        "precision": tp / (tp + fp) if (tp + fp) else None,
        "fpr": fp / (fp + tn) if (fp + tn) else None,
        "accuracy": (tp + tn) / n_total if n_total else None,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(report, open(args.out, "w"), indent=2)
    print(json.dumps({k: report[k] for k in
                      ("confusion", "recall", "precision", "fpr",
                       "accuracy", "threshold")}, indent=2))
    print(f"\nReport completo: {args.out}")


if __name__ == "__main__":
    main()