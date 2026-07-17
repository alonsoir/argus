#!/usr/bin/env python3
# tools/eval/eval_level1_offline.py
# Paso 2 (DAY 221) — scoring OFFLINE del L1 ONNX sobre flujo COMPLETO.
# Cierra la tenaza: Via A (flujo parcial, pipeline) dio recall 0.0 sobre los
# mismos 8.935 cids; esto mide el MISMO denominador con flujo completo.
# La unica variable que cambia frente a Via A es parcial-vs-completo.
#
# INVARIANTE al front-end de features: acepta un CSV con las 23 features de
# entrenamiento (nombres EXACTOS, con sus espacios) + la 5-tupla. Da igual si
# ese CSV lo produjo CICFlowMeter (Via A-offline) o el extractor de produccion
# volcado al cierre de flujo (Via B). El scoring y el join son identicos.
#
# community_id: calcado de neris_ground_truth.py — communityid.CommunityID()
# seed=0 default, FlowTuple.make_tcp/udp(src, dst, sport, dport), int(x,0).
# Mis cids coinciden con los del GT POR CONSTRUCCION (mismo paquete, misma
# semilla). No se reproduce ningun hash a mano.
#
# AUTHORS: Alonso Isidoro Roman + Claude (Anthropic) — DAY 221 (17-jul-2026)

import argparse, csv, json, sys
from pathlib import Path

import numpy as np
import onnxruntime as ort

try:
    import communityid
except ImportError:
    sys.exit("FAIL-CLOSED: falta 'communityid' (Corelight). pip install communityid")

# Orden LITERAL de las 23 — de level1_attack_detector_metadata.json.
# Los espacios iniciales son parte del nombre de columna de CICFlowMeter/CICIDS.
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
# Columnas de 5-tupla esperadas en el CSV de entrada (configurable por si el
# front-end las nombra distinto). proto como texto tcp/udp.

# --- PARIDAD v4->modelo (CICFlowMeter 98a5ebad != v3 de CICIDS2017) ---
# ASTERISCO DE PROCEDENCIA: 4 features estan RENOMBRADAS entre v3 y v4; que el
# nombre difiera no prueba que el calculo sea identico. Un recall ALTO es
# concluyente pese a esto; uno BAJO exige el test de divergencia (camino 3).
# clave = nombre que espera el modelo (level1_attack_detector_metadata.json)
# valor = columna real en el CSV de CICFlowMeter-v4
V4_TO_MODEL = {
    " Packet Length Std": "Packet Length Std",
    " Subflow Fwd Bytes": "Subflow Fwd Bytes",
    " Fwd Packet Length Max": "Fwd Packet Length Max",
    " Avg Fwd Segment Size": "Fwd Segment Size Avg",          # RENOMBRADA
    " ACK Flag Count": "ACK Flag Count",
    " Packet Length Variance": "Packet Length Variance",
    " PSH Flag Count": "PSH Flag Count",
    "Bwd Packet Length Max": "Bwd Packet Length Max",
    " act_data_pkt_fwd": "Fwd Act Data Pkts",                 # RENOMBRADA
    "Total Length of Fwd Packets": "Total Length of Fwd Packet",  # plural->sing
    " Fwd Packet Length Std": "Fwd Packet Length Std",
    "Fwd Packets/s": "Fwd Packets/s",
    " Subflow Bwd Bytes": "Subflow Bwd Bytes",
    " Destination Port": "Dst Port",                          # RENOMBRADA
    "Init_Win_bytes_forward": "FWD Init Win Bytes",           # RENOMBRADA
    "Subflow Fwd Packets": "Subflow Fwd Packets",
    " Fwd IAT Min": "Fwd IAT Min",
    " Packet Length Mean": "Packet Length Mean",
    " Total Length of Bwd Packets": "Total Length of Bwd Packet",  # plural->sing
    " Bwd Packet Length Mean": "Bwd Packet Length Mean",
    " Bwd Packet Length Min": "Bwd Packet Length Min",
    " Flow Duration": "Flow Duration",
    " Flow Packets/s": "Flow Packets/s",
}
IANA_PROTO = {"6": "tcp", "17": "udp"}

TUPLE_COLS = {"src": "Src IP", "dst": "Dst IP", "sport": "Src Port",
              "dport": "Dst Port", "proto": "Protocol"}


def load_gt_cids(path: str) -> set:
    with open(path) as f:
        return {ln.strip() for ln in f if ln.strip()}


def community_id_for_row(row, cid_gen, cols):
    """Calcado de neris_ground_truth.py. Devuelve cid o None si no aplica."""
    proto_raw = (row.get(cols["proto"]) or "").strip()
    proto = IANA_PROTO.get(proto_raw, proto_raw.lower())
    if proto not in ("tcp", "udp"):
        return None
    try:
        src = row[cols["src"]].strip()
        dst = row[cols["dst"]].strip()
        sport = int(str(row[cols["sport"]]).strip(), 0)
        dport = int(str(row[cols["dport"]]).strip(), 0)
    except (ValueError, KeyError, AttributeError):
        return None
    if proto == "tcp":
        tpl = communityid.FlowTuple.make_tcp(src, dst, sport, dport)
    else:
        tpl = communityid.FlowTuple.make_udp(src, dst, sport, dport)
    return cid_gen.calc(tpl)


def main():
    ap = argparse.ArgumentParser(description="Paso 2 — L1 offline, flujo completo")
    ap.add_argument("--features-csv", required=True,
                    help="CSV con las 23 features (nombres exactos) + 5-tupla")
    ap.add_argument("--onnx", required=True, help="level1_attack_detector.onnx")
    ap.add_argument("--gt-cids", required=True, help="neris_gt_cids.txt (8.935)")
    ap.add_argument("--mask-feature", action="append", default=[],
                    help="nombre de feature del modelo a neutralizar a 0.0 "
                         "(repetible). Ej: --mask-feature ' Destination Port'. "
                         "Test de desambiguacion: si el recall no cambia, esa "
                         "feature no explicaba el fallo.")
    ap.add_argument("--threshold", type=float, default=0.65,
                    help="mismo que Via A (col15 >= 0.65)")
    ap.add_argument("--out", required=True, help="JSON de salida")
    # overrides de nombres de columna de 5-tupla (front-end dependiente)
    for k, v in TUPLE_COLS.items():
        ap.add_argument(f"--col-{k}", default=v)
    args = ap.parse_args()
    cols = {k: getattr(args, f"col_{k}") for k in TUPLE_COLS}
    bad = [m for m in args.mask_feature if m not in FEATURES_23]
    if bad:
        sys.exit(f"FAIL-CLOSED: --mask-feature desconocida(s): {bad}\n"
                 f"validas: {FEATURES_23}")
    mask_idx = [FEATURES_23.index(m) for m in args.mask_feature]

    gt = load_gt_cids(args.gt_cids)
    sess = ort.InferenceSession(args.onnx, providers=["CPUExecutionProvider"])
    in_name = sess.get_inputs()[0].name
    # localizar la salida de probabilidades (no asumir indice)
    proba_name = None
    for o in sess.get_outputs():
        if "prob" in o.name.lower():
            proba_name = o.name
    if proba_name is None:  # fallback: la 2a salida del skl2onnx
        proba_name = sess.get_outputs()[-1].name

    cid_gen = communityid.CommunityID()

    # Acumular: por cid, el MAX score de sus flujos (regla de Via A: cid
    # detectado si >=1 flujo suyo puntua >= threshold).
    cid_max_score = {}
    n_rows = n_scored = n_skipped_tuple = n_missing_feat = 0
    all_scores = []
    header_checked = False

    with open(args.features_csv, newline="") as f:
        reader = csv.DictReader(f)
        # verificar que las 23 columnas existen ANTES de procesar (fail-closed)
        missing = [V4_TO_MODEL[c] for c in FEATURES_23 if V4_TO_MODEL[c] not in reader.fieldnames]
        if missing:
            sys.exit(f"FAIL-CLOSED: faltan columnas en el CSV: {missing}\n"
                     f"columnas presentes: {reader.fieldnames}")
        for row in reader:
            n_rows += 1
            cid = community_id_for_row(row, cid_gen, cols)
            if cid is None:
                n_skipped_tuple += 1
                continue
            try:
                vec = np.array([[float(row[V4_TO_MODEL[c]]) for c in FEATURES_23]],
                               dtype=np.float32)
            except (ValueError, KeyError):
                n_missing_feat += 1
                continue
            # sustituir inf/nan como en entrenamiento (CIC: inf->max finito)
            if not np.all(np.isfinite(vec)):
                vec = np.nan_to_num(vec, nan=0.0, posinf=0.0, neginf=0.0)
            for mi in mask_idx:
                vec[0, mi] = 0.0
            out = sess.run([proba_name], {in_name: vec})[0]
            score = float(out[0][1])  # prob_attack (clase ATTACK=1)
            all_scores.append(score)
            n_scored += 1
            if score > cid_max_score.get(cid, -1.0):
                cid_max_score[cid] = score

    # Recall sobre el GT (mismo denominador y regla que Via A)
    detected = {c for c, s in cid_max_score.items() if s >= args.threshold and c in gt}
    covered = {c for c in cid_max_score if c in gt}   # cids GT con >=1 flujo scored
    recall = len(detected) / len(gt) if gt else 0.0
    recall_over_covered = (len(detected) / len(covered)) if covered else 0.0

    scores = np.array(all_scores) if all_scores else np.array([0.0])
    report = {
        "paso": "Paso 2 — L1 offline flujo completo (DAY 221)",
        "features_csv": args.features_csv,
        "onnx": args.onnx,
        "threshold": args.threshold,
        "masked_features": args.mask_feature,
        "gt_cids_total": len(gt),
        "rows_total": n_rows,
        "rows_scored": n_scored,
        "rows_skipped_no_tuple": n_skipped_tuple,
        "rows_missing_features": n_missing_feat,
        "gt_cids_covered": len(covered),
        "coverage": len(covered) / len(gt) if gt else 0.0,
        "detected": len(detected),
        "recall": recall,
        "recall_over_covered": recall_over_covered,
        "score_distribution": {
            "max": float(scores.max()),
            "ge_0.65": int((scores >= 0.65).sum()),
            "ge_0.6": int((scores >= 0.6).sum()),
            "ge_0.5": int((scores >= 0.5).sum()),
            "ge_0.4": int((scores >= 0.4).sum()),
            "unique_scores": int(np.unique(scores).size),
        },
    }
    Path(args.out).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()