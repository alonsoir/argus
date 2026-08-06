#!/usr/bin/env python3
"""
join_bias_labels.py -- DAY 250 (+DAY 252): join bias-vs-ground-truth (aRGus)

Cruza el dataset modo A (las 3 lentes: argus/suricata/zeek) contra las labels
por-flujo del binetflow del CTU-13 (escenario 1), por 5-TUPLA CANONICALIZADA.
SIN ventana temporal: el replay --mbps=10 reescribio el reloj, asi que el
StartTime del binetflow (wall-clock 2011) no casa con nuestros timestamps.

Filosofia (Alonso, DAY 250): NO se funden las lentes a un estandar comun.
Cada lente reporta lo SUYO; el valor esta en la DIVERGENCIA entre lentes:
  - argus    : clasificador ML con veredicto binario -> matriz de confusion.
  - suricata : solo deja fila cuando emitio algo (alerta) -> precision de
               alertas + recall; el silencio no deja fila, FN por ausencia.
  - zeek     : telemetria pura, sin veredicto -> solo cobertura/visibilidad.

DAY 252 (aditivo, sin tocar la API que importan bias_denominator_true.py /
autopsy_67.py): emite ademas, para cada lente, la GRANULARIDAD (5-tuplas
distintas / filas) y, para argus, el SPLIT fast/ml de sus filas MALICIOUS y la
concentracion de peers -> respalda con comando los caveats de granularidad,
ML-ciego y FP de fondo de lab. load_csv() se mantiene INTACTA; lo nuevo vive en
load_argus_extra() para no romper a los importadores.

Contrato de STAMP identico a dataset_export.py: STAMP posicional opcional;
vacio -> autodetecta el CSV modo A mas reciente. Consume la SALIDA de
dataset-export (logs/datasets/dataset-modeA-$STAMP.csv) y escribe su propio
artefacto (logs/datasets/bias-report-$STAMP.txt), ademas de stdout.

Uso:
  python3 scripts/join_bias_labels.py                 # ultimo modo A
  python3 scripts/join_bias_labels.py 20260804-080140 # STAMP concreto
  python3 scripts/join_bias_labels.py --csv X.csv --binetflow Y.binetflow
"""
import argparse
import csv
import glob
import os
import re
import sys
from collections import defaultdict, Counter

DEFAULT_BINETFLOW = "datasets/ctu13/capture20110810.binetflow"
CSV_GLOB = "logs/datasets/dataset-modeA-*.csv"
REPORT_DIR = "logs/datasets"

# --- columnas (0-indexed) ---
# CSV modo A: source_sensor,event_id,community_id,src_ip,dst_ip,src_port,
#             dst_port,protocol,flow_start_sec,final_classification,threat_category,
#             fast_detector_score,ml_detector_score,overall_threat_score,...
C_SENSOR, C_SIP, C_DIP, C_SP, C_DP, C_PROTO, C_FINAL, C_CAT = 0, 3, 4, 5, 6, 7, 9, 10
C_FAST, C_ML, C_OVERALL = 11, 12, 13  # DAY 252: scores para el split del caveat ML-ciego
# binetflow: StartTime,Dur,Proto,SrcAddr,Sport,Dir,DstAddr,Dport,State,sTos,dTos,
#            TotPkts,TotBytes,SrcBytes,Label
B_PROTO, B_SIP, B_SP, B_DIP, B_DP, B_LABEL = 2, 3, 4, 6, 7, 14


def canon(ip1, p1, ip2, p2, proto):
    """Clave 5-tupla independiente de orientacion. proto en minuscula; par
    (ip,port) ordenado -> colapsa el <-> del binetflow y cualquier inversion
    src/dst entre lentes (imprescindible: proto viene TCP en argus/suricata,
    tcp en zeek y en el binetflow)."""
    a = (ip1.strip(), p1.strip())
    b = (ip2.strip(), p2.strip())
    lo, hi = sorted((a, b))
    return (proto.strip().lower(), lo[0], lo[1], hi[0], hi[1])


def is_botnet(label):
    return "botnet" in label.strip().lower()


def resolve_csv(stamp, csv_override):
    """Contrato STAMP igual a dataset-export: override explicito > STAMP
    posicional > autodeteccion del modo A mas reciente."""
    if csv_override:
        return csv_override
    if stamp:
        return os.path.join(REPORT_DIR, f"dataset-modeA-{stamp}.csv")
    cands = sorted(glob.glob(CSV_GLOB), key=os.path.getmtime)
    if not cands:
        sys.exit(f"[ERROR] no hay ningun {CSV_GLOB}; corre antes `make dataset-export`.")
    return cands[-1]


def stamp_of(csv_path):
    m = re.search(r"dataset-modeA-(.+)\.csv$", os.path.basename(csv_path))
    return m.group(1) if m else os.path.splitext(os.path.basename(csv_path))[0]


def load_csv(path):
    rows = defaultdict(list)
    keys_union = set()
    with open(path, newline="") as f:
        r = csv.reader(f)
        next(r)
        for row in r:
            if len(row) <= C_CAT:
                continue
            sensor = row[C_SENSOR].strip()
            k = canon(row[C_SIP], row[C_SP], row[C_DIP], row[C_DP], row[C_PROTO])
            rows[sensor].append((k, row[C_FINAL].strip(), row[C_CAT].strip()))
            keys_union.add(k)
    return rows, keys_union


def load_labels(path, keys_union):
    labels = defaultdict(set)
    n = 0
    with open(path, newline="") as f:
        r = csv.reader(f)
        next(r)
        for row in r:
            n += 1
            if len(row) <= B_LABEL:
                continue
            k = canon(row[B_SIP], row[B_SP], row[B_DIP], row[B_DP], row[B_PROTO])
            if k in keys_union:
                labels[k].add(row[B_LABEL].strip())
    return labels, n


def label_of(labels, k):
    lset = labels.get(k)
    if not lset:
        return None
    if any(is_botnet(x) for x in lset):
        return "botnet"
    return "clean"


# --- DAY 252: extra SOLO para argus, en pasada aparte (no toca load_csv) ---
def _to_f(x):
    try:
        return float(x)
    except (ValueError, TypeError):
        return float("nan")


def _avg(xs):
    xs = [x for x in xs if x == x]  # descarta NaN
    return sum(xs) / len(xs) if xs else 0.0


def load_argus_extra(path):
    """Segunda pasada, SOLO argus: scores de las filas MALICIOUS (para el split
    fast/ml del caveat ML-ciego) y concentracion de filas por IP destino (para
    el caveat de granularidad = flujos gruesos persistentes). Separada de
    load_csv() a proposito: su firma la importan bias_denominator_true.py y
    autopsy_67.py, y NO debe cambiar."""
    mal = []            # (k, fast, ml, overall) de filas MALICIOUS de argus
    peers = Counter()   # dst_ip -> nº de filas de argus (todas, no solo MALICIOUS)
    with open(path, newline="") as f:
        r = csv.reader(f)
        next(r)
        for row in r:
            if len(row) <= C_OVERALL:
                continue
            if row[C_SENSOR].strip() != "argus":
                continue
            peers[row[C_DIP].strip()] += 1
            if row[C_FINAL].strip().upper() == "MALICIOUS":
                k = canon(row[C_SIP], row[C_SP], row[C_DIP], row[C_DP], row[C_PROTO])
                mal.append((k, _to_f(row[C_FAST]), _to_f(row[C_ML]), _to_f(row[C_OVERALL])))
    return mal, peers


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stamp", nargs="?", default="", help="STAMP del modo A (vacio = autodetecta el mas reciente)")
    ap.add_argument("--csv", default="", help="override del CSV modo A")
    ap.add_argument("--binetflow", default=DEFAULT_BINETFLOW)
    ap.add_argument("--out", default="", help="override del fichero de reporte")
    args = ap.parse_args()

    csv_path = resolve_csv(args.stamp, args.csv)
    if not os.path.isfile(csv_path):
        sys.exit(f"[ERROR] no existe {csv_path}; corre antes `make dataset-export` (o pasa STAMP=).")
    if not os.path.isfile(args.binetflow):
        sys.exit(f"[ERROR] no existe {args.binetflow}; corre `make fetch-neris-labels`.")

    stamp = stamp_of(csv_path)
    out_path = args.out or os.path.join(REPORT_DIR, f"bias-report-{stamp}.txt")

    buf = []

    def emit(line=""):
        buf.append(line)
        print(line)

    rows, keys_union = load_csv(csv_path)
    labels, n_binetflow = load_labels(args.binetflow, keys_union)
    argus_mal, argus_peers = load_argus_extra(csv_path)  # DAY 252

    emit("=" * 72)
    emit("JOIN bias-vs-ground-truth  (5-tupla canonica, sin ventana temporal)")
    emit("=" * 72)
    emit(f"csv modo A          : {csv_path}")
    emit(f"binetflow (labels)  : {args.binetflow}")
    emit(f"STAMP               : {stamp}")
    emit(f"binetflow escaneado : {n_binetflow} filas")
    emit(f"5-tuplas replay     : {len(keys_union)} distintas (union de las 3 lentes)")
    matched = len(labels)
    pct = matched / len(keys_union) * 100 if keys_union else 0.0
    emit(f"5-tuplas con label  : {matched}  ({pct:.1f}% de las nuestras casan en el binetflow)")

    ambiguous = []
    for k, lset in labels.items():
        if any(is_botnet(x) for x in lset) and any(not is_botnet(x) for x in lset):
            ambiguous.append((k, lset))
    emit("")
    emit(f"[VALIDACION CLAVE] 5-tuplas a la vez botnet Y clean en el binetflow: {len(ambiguous)}")
    if ambiguous:
        emit("  -> la 5-tupla NO desambigua estas; 'botnet si cualquiera' las cuenta botnet (declarar).")
        for k, lset in ambiguous[:10]:
            emit(f"     {k} :: {sorted(lset)}")
        if len(ambiguous) > 10:
            emit(f"     ... (+{len(ambiguous) - 10} mas)")
    else:
        emit("  -> clave LIMPIA: ninguna 5-tupla replayada mezcla botnet y clean. Seguro.")

    gt_botnet = set()
    for rs in rows.values():
        for k, _f, _c in rs:
            if label_of(labels, k) == "botnet":
                gt_botnet.add(k)
    emit("")
    emit(f"[DENOMINADOR] flujos botnet (5-tupla) vistos por >=1 lente: {len(gt_botnet)}")
    emit("  CAVEAT: denominador LENS-OBSERVABLE. Un flujo botnet que NINGUNA lente")
    emit("  capturo no deja fila -> no cuenta. Denominador VERDADERO = extraer las")
    emit("  5-tuplas del pcap replayado (tshark) -> `make bias-denominator-true`.")

    for sensor in ("argus", "suricata", "zeek"):
        rs = rows.get(sensor, [])
        emit("")
        emit("-" * 72)
        emit(f"LENTE: {sensor}   (filas en el dataset: {len(rs)})")
        emit("-" * 72)

        seen_keys = {k for k, _f, _c in rs}
        seen_botnet = {k for k in seen_keys if k in gt_botnet}
        cov = len(seen_botnet) / len(gt_botnet) * 100 if gt_botnet else 0.0
        emit(f"  VISIBILIDAD: ve {len(seen_botnet)}/{len(gt_botnet)} flujos botnet del denominador ({cov:.1f}%)")

        # DAY 252: granularidad por-lente (distintas totales vs filas)
        n_distinct = len(seen_keys)
        gran = f"{len(rs) / n_distinct:.1f}" if n_distinct else "n/a"
        emit(f"  GRANULARIDAD: {n_distinct} 5-tuplas distintas en {len(rs)} filas (filas/5-tupla={gran})")

        gt_counts = Counter(label_of(labels, k) for k, _f, _c in rs)
        emit(f"  filas por ground-truth: botnet={gt_counts.get('botnet', 0)}  "
             f"clean={gt_counts.get('clean', 0)}  sin-label={gt_counts.get(None, 0)}")

        if sensor == "argus":
            tp = fp = fn = tn = 0
            for k, final, _c in rs:
                gt = label_of(labels, k)
                if gt is None:
                    continue
                pred_mal = (final.upper() == "MALICIOUS")
                if gt == "botnet" and pred_mal:
                    tp += 1
                elif gt != "botnet" and pred_mal:
                    fp += 1
                elif gt == "botnet" and not pred_mal:
                    fn += 1
                else:
                    tn += 1
            prec = tp / (tp + fp) if (tp + fp) else 0.0
            rec = tp / (tp + fn) if (tp + fn) else 0.0
            emit("  DETECCION (final_classification==MALICIOUS vs label botnet; solo filas con label):")
            emit(f"    TP={tp}  FP={fp}  FN={fn}  TN={tn}")
            emit(f"    precision={prec:.3f}  recall={rec:.3f}")
            emit("    NOTA: precision alta puede ser trivial si clean==0 (sin poblacion negativa).")

            # DAY 252: split fast/ml de las filas MALICIOUS (caveat ML-ciego)
            mal_by_gt = Counter(label_of(labels, k) for k, _fa, _ml, _ov in argus_mal)
            n_mal = len(argus_mal)
            m_over = _avg([ov for _k, _fa, _ml, ov in argus_mal])
            m_fast = _avg([fa for _k, fa, _ml, _ov in argus_mal])
            m_ml = _avg([ml for _k, _fa, ml, _ov in argus_mal])
            emit(f"  SPLIT fast/ml de las {n_mal} filas MALICIOUS (caveat: ML ciego, el heuristico lleva la deteccion):")
            emit(f"    por ground-truth: botnet={mal_by_gt.get('botnet', 0)}  "
                 f"clean={mal_by_gt.get('clean', 0)}  sin-label={mal_by_gt.get(None, 0)}")
            emit(f"    score medio: overall={m_over:.4f}  fast={m_fast:.4f}  ml={m_ml:.4f}")
            emit("    -> overall==fast y ml<<overall => el fast-path decide, el ML esta ciego sobre este trafico.")
            emit("    -> las MALICIOUS sin-label son FP contra el fondo de lab (no etiquetado): la precision 1.000 es solo vs CTU.")

            # DAY 252: concentracion de peers por filas (granularidad = flujo grueso persistente)
            emit("  TOP IPs destino por nº de filas de argus (concentracion / flujo grueso persistente):")
            for dip, n in argus_peers.most_common(5):
                emit(f"    {n:6d}  {dip}")

        elif sensor == "suricata":
            alert_botnet = gt_counts.get("botnet", 0)
            alert_clean = gt_counts.get("clean", 0)
            alert_nolabel = gt_counts.get(None, 0)
            total = len(rs)
            prec = alert_botnet / total if total else 0.0
            rec = len(seen_botnet) / len(gt_botnet) if gt_botnet else 0.0
            emit("  DETECCION (cada fila = un evento emitido por suricata; el silencio no deja fila):")
            emit(f"    sobre botnet={alert_botnet}  sobre clean={alert_clean}  sin-label={alert_nolabel}")
            emit(f"    precision (botnet/total emitidas)={prec:.3f}   "
                 f"recall (flujos botnet vistos/denominador)={rec:.3f}")
            cats = Counter(c for k, _f, c in rs if label_of(labels, k) == "botnet")
            if cats:
                emit("    TIPO de evento sobre flujos botnet (firma de botnet vs anomalia de protocolo):")
                for c, n in cats.most_common(10):
                    emit(f"      {n:6d}  {c}")

        else:  # zeek
            emit("  (telemetria pura, sin veredicto -> sin matriz de deteccion; solo visibilidad)")

    emit("")
    emit("=" * 72)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        f.write("\n".join(buf) + "\n")
    print(f"\n[artefacto] reporte escrito en {out_path}")


if __name__ == "__main__":
    main()