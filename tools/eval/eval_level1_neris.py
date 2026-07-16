#!/usr/bin/env python3
# tools/eval/eval_level1_neris.py
# DEBT-L1-NO-REPRODUCIBLE-HOLDOUT-001 (mitad generalizacion) — Via A, Fase 4.
#
# Cruza el bronce correlation_v1 (producido por el pipeline VIVO durante el
# replay del pcap Neris) contra la verdad terreno derivada del binetflow
# (neris_ground_truth.py). Reporta DOS numeros separados:
#
#   coverage = |GT ∩ cids_bronce| / |GT|
#       — mide sniffer + formacion de flujo + SKIPs. Un cid ausente del bronce
#         es perdida rio-arriba, NO un fallo del modelo.
#   recall   = |GT detectados como ataque| / |GT|
#       — el numero del paper (alcance: cross-dataset, botnet Neris).
#   recall_over_covered = detectados / cubiertos
#       — aisla el modelo de las perdidas del sniffer.
#
# Predicado "detectado": col 15 (ml_detector_score) >= threshold vivo.
# Equivalencia con el gate de zmq_handler.cpp:722 probada en DAY220:
#   ml_score = label==1 ? conf : 1-conf  (linea 550). Si conf es la confianza
#   de la clase predicha (>0.5), ml_score = P(ATTACK) siempre, y
#   col15 >= 0.65 <=> (label==1 AND conf >= 0.65). VERIFICAR en el smoke que
#   predict() devuelve confianza-de-la-clase-predicha.
#
# Columnas del bronce (correlation_v1.hpp, CorrelationV1Row):
#   4=community_id  12=final_classification  14=fast_detector_score
#   15=ml_detector_score  16=overall_threat_score(=max, MONOCAPA-001)
#   17=authoritative_source  18=HMAC (ignorado aqui; verificacion aparte)
#
# AUTHORS: Alonso Isidoro Roman + Claude (Anthropic) — DAY 220 (16-jul-2026)

import argparse
import csv
import glob
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

COL_CID = 4
COL_FINAL_CLASS = 12
COL_FAST = 14
COL_ML = 15
COL_OVERALL = 16
COL_AUTH = 17
MIN_COLS = 19  # 0-18 (incluye HMAC)


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


def find_threshold(cfg: dict, key: str = "level1_attack"):
    hits = []

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
             f"(esperado 1): {hits}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Via A Fase 4 — cruce bronce vs GT Neris")
    ap.add_argument("--bronze-glob", required=True,
                    help="glob de segmentos bronce del run, "
                         "ej '/vagrant/.../bronze/*.csv'")
    ap.add_argument("--gt-cids", required=True,
                    help="salida de neris_ground_truth.py (un cid/linea)")
    ap.add_argument("--gt-meta", required=True,
                    help="meta JSON de neris_ground_truth.py (se embebe)")
    ap.add_argument("--config", required=True,
                    help="ml_detector_config.json (threshold VIVO)")
    ap.add_argument("--replay-note", default="",
                    help="nota libre: settings de tcpreplay, PROFILE, etc.")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    gt = set(l.strip() for l in open(args.gt_cids) if l.strip())
    if not gt:
        sys.exit("FAIL-CLOSED: GT vacio — correr neris_ground_truth.py antes")
    gt_meta = json.load(open(args.gt_meta))

    cfg = json.load(open(args.config))
    threshold, threshold_path = find_threshold(cfg)

    files = sorted(glob.glob(args.bronze_glob))
    if not files:
        sys.exit(f"FAIL-CLOSED: ningun fichero bronce casa con "
                 f"'{args.bronze_glob}' — el replay no produjo bronce o el "
                 f"glob es incorrecto (verificar la RUTA antes de concluir).")

    # Agregacion por cid: max ml_score visto, n registros, clases vistas.
    seen = {}          # cid -> dict(max_ml, max_fast, n, classes)
    n_rows = 0
    n_short = 0        # lineas con menos columnas de las esperadas (contadas)
    bronze_md5 = {}
    for path in files:
        bronze_md5[path] = md5(path)
        with open(path, newline="") as f:
            for cols in csv.reader(f):
                if len(cols) < MIN_COLS:
                    n_short += 1
                    continue
                n_rows += 1
                cid = cols[COL_CID]
                try:
                    ml = float(cols[COL_ML])
                    fast = float(cols[COL_FAST])
                except ValueError:
                    n_short += 1
                    continue
                s = seen.setdefault(cid, {"max_ml": 0.0, "max_fast": 0.0,
                                          "n": 0, "classes": set()})
                s["max_ml"] = max(s["max_ml"], ml)
                s["max_fast"] = max(s["max_fast"], fast)
                s["n"] += 1
                s["classes"].add(cols[COL_FINAL_CLASS])

    covered = gt & set(seen)
    detected = {c for c in covered if seen[c]["max_ml"] >= threshold}
    missed_covered = covered - detected          # el modelo los vio y dijo no
    missed_uncovered = gt - covered              # nunca llegaron al bronce

    n_gt = len(gt)
    report = {
        "eval": "level1_neris (via A — pipeline VIVO, cross-dataset)",
        "scope": ("Generalizacion cross-dataset a trafico BOTNET (CTU-13 "
                  "Neris). Solo RECALL: el pcap es la captura filtrada al "
                  "host infectado — sin universo benigno, FPR no medible "
                  "aqui. DAY220_FINDINGS §6."),
        "generated_by": "tools/eval/eval_level1_neris.py",
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "replay_note": args.replay_note,
        "threshold": {"value": threshold,
                      "config_path_in_json": threshold_path,
                      "source_file": args.config,
                      "config_md5": md5(args.config)},
        "detected_predicate": ("max(col15 ml_detector_score por cid) >= "
                               "threshold — equivalente al gate "
                               "zmq_handler.cpp:722 (ver cabecera)"),
        "ground_truth": {"cids": n_gt, "meta": gt_meta},
        "bronze": {"files": len(files), "md5": bronze_md5,
                   "rows": n_rows, "rows_malformed_skipped": n_short,
                   "unique_cids_total": len(seen)},
        "results": {
            "gt_cids": n_gt,
            "covered": len(covered),
            "detected": len(detected),
            "missed_covered_by_model": len(missed_covered),
            "missed_uncovered_upstream": len(missed_uncovered),
            "coverage": len(covered) / n_gt,
            "recall": len(detected) / n_gt,
            "recall_over_covered": (len(detected) / len(covered))
            if covered else None,
        },
        # Muestras para diagnostico (no exhaustivas, 20 cada una)
        "samples": {
            "missed_covered": sorted(missed_covered)[:20],
            "missed_uncovered": sorted(missed_uncovered)[:20],
        },
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(report, open(args.out, "w"), indent=2, default=str)
    print(json.dumps(report["results"], indent=2))
    print(f"\nReport completo: {args.out}")


if __name__ == "__main__":
    main()