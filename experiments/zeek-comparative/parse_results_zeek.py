#!/usr/bin/env python3
"""
parse_results_zeek.py — aRGus NDR DAY 147
Parsea notice.log y conn.log de Zeek para calcular TP/FP/FN/F1/Recall
contra el ground truth CTU-13 Neris (147.32.84.165, 646 flujos maliciosos).

Uso:
    python3 parse_results_zeek.py \
        --notice /vagrant/logs/experiment/zeek/notice.log \
        --conn   /vagrant/logs/experiment/zeek/conn.log \
        --speed  50Mbps

Métricas:
    notice.log → TP/FP/FN/F1/Recall (detección primaria, equivalente a eve.json)
    conn.log   → análisis behavioral complementario del ground truth IP
"""

import argparse
import json
from pathlib import Path

MALICIOUS_IP  = "147.32.84.165"
GROUND_TRUTH  = 646          # flujos maliciosos conocidos
BENIGN_FLOWS  = 12075        # flujos benignos en el corpus Neris

# ─── Parser de logs Zeek (formato TSV con cabeceras #fields) ─────────────────

def parse_zeek_log(path: Path) -> list[dict]:
    """Lee un fichero de log Zeek TSV y devuelve lista de dicts."""
    if not path.exists():
        return []
    rows = []
    fields = []
    sep = "\t"
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("#separator"):
                sep_hex = line.split()[-1]
                sep = bytes.fromhex(sep_hex.replace("\\x", "")).decode()
            elif line.startswith("#fields"):
                fields = line.split(sep)[1:]
            elif line.startswith("#"):
                continue
            elif fields:
                values = line.split(sep)
                rows.append(dict(zip(fields, values)))
    return rows

# ─── Análisis de notice.log ───────────────────────────────────────────────────

def analyse_notice(notice_path: Path) -> dict:
    rows = parse_zeek_log(notice_path)
    total_notices = len(rows)

    tp_rows, fp_rows = [], []
    for r in rows:
        src = r.get("src", r.get("id.orig_h", "-"))
        dst = r.get("dst", r.get("id.resp_h", "-"))
        if src == MALICIOUS_IP or dst == MALICIOUS_IP:
            tp_rows.append(r)
        else:
            fp_rows.append(r)

    tp = len(tp_rows)
    fp = len(fp_rows)
    fn = GROUND_TRUTH - tp  # malicious flows with no notice

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / GROUND_TRUTH
    f1        = (2 * precision * recall / (precision + recall)
                 if (precision + recall) > 0 else 0.0)

    # Notice types breakdown
    note_counts = {}
    for r in rows:
        note = r.get("note", "Unknown")
        note_counts[note] = note_counts.get(note, 0) + 1

    return {
        "total_notices": total_notices,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 4),
        "recall":    round(recall, 4),
        "f1":        round(f1, 4),
        "notice_types": note_counts,
        "tp_sample": [
            {"note": r.get("note"), "msg": r.get("msg", "")[:80]}
            for r in tp_rows[:5]
        ],
    }

# ─── Análisis de conn.log ─────────────────────────────────────────────────────

def analyse_conn(conn_path: Path) -> dict:
    rows = parse_zeek_log(conn_path)
    malicious_rows = [
        r for r in rows
        if r.get("id.orig_h") == MALICIOUS_IP or r.get("id.resp_h") == MALICIOUS_IP
    ]

    # Service breakdown
    services = {}
    for r in malicious_rows:
        svc = r.get("service", "-")
        services[svc] = services.get(svc, 0) + 1

    # Duration stats
    durations = []
    for r in malicious_rows:
        try:
            durations.append(float(r.get("duration", "0") or "0"))
        except ValueError:
            pass

    avg_dur = sum(durations) / len(durations) if durations else 0.0
    max_dur = max(durations) if durations else 0.0

    # Unique dest IPs
    dest_ips = {r.get("id.resp_h") for r in malicious_rows
                if r.get("id.orig_h") == MALICIOUS_IP}

    return {
        "total_flows_in_log": len(rows),
        "malicious_ip_flows": len(malicious_rows),
        "unique_dest_ips": len(dest_ips),
        "services": services,
        "avg_duration_s": round(avg_dur, 3),
        "max_duration_s": round(max_dur, 3),
    }

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Parse Zeek notice.log + conn.log → TP/FP/FN/F1 vs CTU-13 Neris"
    )
    parser.add_argument("--notice", required=True)
    parser.add_argument("--conn",   required=True)
    parser.add_argument("--speed",  default="unknown")
    parser.add_argument("--output", default=None,
                        help="Guardar JSON en fichero")
    args = parser.parse_args()

    notice_path = Path(args.notice)
    conn_path   = Path(args.conn)

    notice_stats = analyse_notice(notice_path)
    conn_stats   = analyse_conn(conn_path)

    result = {
        "speed":         args.speed,
        "ground_truth":  {"malicious_ip": MALICIOUS_IP,
                          "malicious_flows": GROUND_TRUTH,
                          "benign_flows": BENIGN_FLOWS},
        "notice_log":    notice_stats,
        "conn_log":      conn_stats,
        "zeek_phase":    "1-default-scripts",
    }

    print("=" * 60)
    print(f"Zeek experiment results — {args.speed}")
    print("=" * 60)
    print(f"\n[notice.log — primary detection]")
    print(f"  Total notices : {notice_stats['total_notices']}")
    print(f"  TP (malicious): {notice_stats['tp']}")
    print(f"  FP (benign)   : {notice_stats['fp']}")
    print(f"  FN (missed)   : {notice_stats['fn']}")
    print(f"  Precision     : {notice_stats['precision']:.4f}")
    print(f"  Recall        : {notice_stats['recall']:.4f}")
    print(f"  F1            : {notice_stats['f1']:.4f}")
    if notice_stats["notice_types"]:
        print(f"\n  Notice types  :")
        for k, v in sorted(notice_stats["notice_types"].items(),
                            key=lambda x: -x[1]):
            print(f"    {k}: {v}")
    else:
        print("\n  ⚠️  notice.log vacío — 0 alertas generadas")

    print(f"\n[conn.log — behavioral analysis of {MALICIOUS_IP}]")
    print(f"  Total flows    : {conn_stats['total_flows_in_log']}")
    print(f"  Malicious flows: {conn_stats['malicious_ip_flows']}")
    print(f"  Unique dest IPs: {conn_stats['unique_dest_ips']}")
    print(f"  Services       : {conn_stats['services']}")
    print(f"  Avg duration   : {conn_stats['avg_duration_s']}s")
    print(f"  Max duration   : {conn_stats['max_duration_s']}s")
    print("=" * 60)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2))
        print(f"\n✅ JSON guardado en {out}")

    return result


if __name__ == "__main__":
    main()
