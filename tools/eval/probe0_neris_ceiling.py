#!/usr/bin/env python3
# tools/eval/probe0_neris_ceiling.py
# PROBE 0 (DAY 221+) — TECHO de separabilidad, la pregunta existencial de L1.
#
# NO produce un modelo desplegable. Entrena sobre Neris MISMO (70/30 estratif.)
# y evalua en el held-out de Neris. Responde: "en el mejor caso imaginable,
# ¿estas 23 features de flujo PUEDEN separar el botnet Neris del fondo?"
#   - Techo ALTO  -> la senal esta en las features; el fallo del Paso 2 es
#                    TRANSFERENCIA CICIDS->Neris (arreglable: reentrenar con
#                    datos representativos).
#   - Techo BAJO  -> las features no llevan la firma; NINGUN reentrenamiento
#                    sobre este espacio de features lo salva. Diagnostico fatal.
#
# SALVAGUARDA: si el pcap Neris es casi todo botnet, no hay negativos con que
# entrenar un discriminador -> el probe es DEGENERADO. El harness lo detecta y
# lo dice ANTES de entrenar (un clasificador "siempre botnet" da recall alto
# trivialmente y mentiria). Ese caso ES un hallazgo: "hace falta trafico benigno
# de otra fuente para medir el techo".
#
# AUTHORS: Alonso Isidoro Roman + Claude (Anthropic) — DAY 221 (17-jul-2026)

import argparse, csv, json, sys
from pathlib import Path
import numpy as np

try:
    import communityid
except ImportError:
    sys.exit("FAIL-CLOSED: falta 'communityid'. pip install communityid")
try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import (recall_score, precision_score, f1_score,
                                 confusion_matrix, roc_auc_score)
except ImportError:
    sys.exit("FAIL-CLOSED: falta scikit-learn. pip install scikit-learn")

FEATURES_23 = [
    " Packet Length Std", " Subflow Fwd Bytes", " Fwd Packet Length Max",
    " Avg Fwd Segment Size", " ACK Flag Count", " Packet Length Variance",
    " PSH Flag Count", "Bwd Packet Length Max", " act_data_pkt_fwd",
    "Total Length of Fwd Packets", " Fwd Packet Length Std", "Fwd Packets/s",
    " Subflow Bwd Bytes", " Destination Port", "Init_Win_bytes_forward",
    "Subflow Fwd Packets", " Fwd IAT Min", " Packet Length Mean",
    " Total Length of Bwd Packets", " Bwd Packet Length Mean",
    " Bwd Packet Length Min", " Flow Duration", " Flow Packets/s",
]
V4_TO_MODEL = {
    " Packet Length Std": "Packet Length Std", " Subflow Fwd Bytes": "Subflow Fwd Bytes",
    " Fwd Packet Length Max": "Fwd Packet Length Max", " Avg Fwd Segment Size": "Fwd Segment Size Avg",
    " ACK Flag Count": "ACK Flag Count", " Packet Length Variance": "Packet Length Variance",
    " PSH Flag Count": "PSH Flag Count", "Bwd Packet Length Max": "Bwd Packet Length Max",
    " act_data_pkt_fwd": "Fwd Act Data Pkts", "Total Length of Fwd Packets": "Total Length of Fwd Packet",
    " Fwd Packet Length Std": "Fwd Packet Length Std", "Fwd Packets/s": "Fwd Packets/s",
    " Subflow Bwd Bytes": "Subflow Bwd Bytes", " Destination Port": "Dst Port",
    "Init_Win_bytes_forward": "FWD Init Win Bytes", "Subflow Fwd Packets": "Subflow Fwd Packets",
    " Fwd IAT Min": "Fwd IAT Min", " Packet Length Mean": "Packet Length Mean",
    " Total Length of Bwd Packets": "Total Length of Bwd Packet",
    " Bwd Packet Length Mean": "Bwd Packet Length Mean", " Bwd Packet Length Min": "Bwd Packet Length Min",
    " Flow Duration": "Flow Duration", " Flow Packets/s": "Flow Packets/s",
}
IANA_PROTO = {"6": "tcp", "17": "udp"}
TUP = {"src": "Src IP", "dst": "Dst IP", "sport": "Src Port", "dport": "Dst Port", "proto": "Protocol"}


def cid_for(row, cg):
    proto = IANA_PROTO.get((row.get(TUP["proto"]) or "").strip(),
                           (row.get(TUP["proto"]) or "").strip().lower())
    if proto not in ("tcp", "udp"):
        return None
    try:
        s, d = row[TUP["src"]].strip(), row[TUP["dst"]].strip()
        sp, dp = int(str(row[TUP["sport"]]).strip(), 0), int(str(row[TUP["dport"]]).strip(), 0)
    except (ValueError, KeyError, AttributeError):
        return None
    t = communityid.FlowTuple.make_tcp(s, d, sp, dp) if proto == "tcp" else communityid.FlowTuple.make_udp(s, d, sp, dp)
    return cg.calc(t)


def main():
    ap = argparse.ArgumentParser(description="Probe 0 — techo de separabilidad Neris")
    ap.add_argument("--features-csv", required=True)
    ap.add_argument("--gt-cids", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--test-size", type=float, default=0.30)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--min-minority", type=int, default=50,
                    help="si la clase minoritaria < este umbral, DEGENERADO")
    args = ap.parse_args()

    gt = {ln.strip() for ln in open(args.gt_cids) if ln.strip()}
    cg = communityid.CommunityID()
    X, ycid, y = [], [], []
    n_rows = n_skip = n_badfeat = 0
    with open(args.features_csv, newline="") as f:
        reader = csv.DictReader(f)
        missing = [V4_TO_MODEL[c] for c in FEATURES_23 if V4_TO_MODEL[c] not in reader.fieldnames]
        if missing:
            sys.exit(f"FAIL-CLOSED: faltan columnas: {missing}")
        for row in reader:
            n_rows += 1
            cid = cid_for(row, cg)
            if cid is None:
                n_skip += 1; continue
            try:
                vec = [float(row[V4_TO_MODEL[c]]) for c in FEATURES_23]
            except (ValueError, KeyError):
                n_badfeat += 1; continue
            X.append(vec); ycid.append(cid); y.append(1 if cid in gt else 0)

    X = np.nan_to_num(np.array(X, dtype=np.float64), posinf=0.0, neginf=0.0)
    y = np.array(y)
    n_pos, n_neg = int((y == 1).sum()), int((y == 0).sum())
    minority = min(n_pos, n_neg)

    balance = {"flows_total": n_rows, "flows_used": len(y), "skipped_no_tuple": n_skip,
               "bad_features": n_badfeat, "positives_botnet": n_pos, "negatives_other": n_neg,
               "minority_class": minority}

    # SALVAGUARDA: probe degenerado si no hay bastante clase minoritaria
    if minority < args.min_minority:
        report = {"probe": "Probe 0 — techo Neris", "VERDICT": "DEGENERADO",
                  "reason": (f"clase minoritaria={minority} < {args.min_minority}. "
                             "El pcap Neris no tiene bastante contraste (casi todo "
                             "una sola clase). No se puede medir el techo con estos "
                             "datos: hace falta trafico benigno de otra fuente. "
                             "Un modelo 'siempre-mayoritaria' daria metricas altas y "
                             "MENTIRIA."), "balance": balance}
        Path(args.out).write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
        return

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=args.test_size,
                                          random_state=args.seed, stratify=y)
    clf = RandomForestClassifier(n_estimators=100, random_state=args.seed,
                                 class_weight="balanced", n_jobs=-1)
    clf.fit(Xtr, ytr)
    proba = clf.predict_proba(Xte)[:, 1]
    pred = (proba >= 0.5).astype(int)

    cm = confusion_matrix(yte, pred).tolist()
    report = {
        "probe": "Probe 0 — techo de separabilidad Neris (in-sample a Neris)",
        "VERDICT": "MEDIDO (interpretar recall/f1 abajo)",
        "features_csv": args.features_csv, "seed": args.seed, "test_size": args.test_size,
        "model": "RandomForest n_estimators=100 class_weight=balanced",
        "balance": balance,
        "test_recall_botnet": float(recall_score(yte, pred, zero_division=0)),
        "test_precision_botnet": float(precision_score(yte, pred, zero_division=0)),
        "test_f1_botnet": float(f1_score(yte, pred, zero_division=0)),
        "test_roc_auc": float(roc_auc_score(yte, proba)) if len(set(yte)) > 1 else None,
        "test_confusion_matrix": cm,
        "feature_importance_top5": sorted(
            [{"f": FEATURES_23[i], "imp": float(v)} for i, v in enumerate(clf.feature_importances_)],
            key=lambda d: -d["imp"])[:5],
    }
    Path(args.out).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()