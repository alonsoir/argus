#!/usr/bin/env python3
"""
parse_results_zeek_v2.py — aRGus NDR DAY 147
Parser mejorado de logs Zeek. Separa correctamente:

  - CaptureLoss notices  → infraestructura, NO son detecciones
  - Detecciones reales   → notice.log filtrado
  - Análisis adicional   → weird.log, http.log, smtp.log, ssl.log

Métricas corregidas:
  TP = notices reales donde src/dst == MALICIOUS_IP
  FP = notices reales donde ni src ni dst == MALICIOUS_IP
  (CaptureLoss excluido del cálculo)

Uso:
    python3 parse_results_zeek_v2.py --logdir /vagrant/logs/experiment/zeek/10mbps
    python3 parse_results_zeek_v2.py --logdir /vagrant/logs/experiment/zeek/10mbps --output metrics.json
"""

import argparse
import json
from pathlib import Path
from collections import defaultdict

MALICIOUS_IP  = "147.32.84.165"
GROUND_TRUTH  = 646
BENIGN_FLOWS  = 12075

# Categorías de notice que son infraestructura/metadatos — excluir de métricas
INFRA_NOTICES = {
    "CaptureLoss::Too_Much_Loss",
    "CaptureLoss::Too_Little_Traffic",
    "CaptureLoss::Packet_Drops",
    "PacketFilter::Dropped_Packets",
}

# ─── Parser genérico Zeek TSV ─────────────────────────────────────────────────

def parse_zeek_log(path: Path) -> list:
    if not path.exists():
        return []
    rows, fields, sep = [], [], "\t"
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("#separator"):
                try:
                    hex_val = line.split()[-1].replace("\\x", "")
                    sep = bytes.fromhex(hex_val).decode()
                except Exception:
                    sep = "\t"
            elif line.startswith("#fields"):
                fields = line.split(sep)[1:]
            elif line.startswith("#"):
                continue
            elif fields:
                values = line.split(sep)
                rows.append(dict(zip(fields, values)))
    return rows

def ip_match(row: dict, ip: str) -> bool:
    for field in ("src", "dst", "id.orig_h", "id.resp_h"):
        if row.get(field) == ip:
            return True
    return False

# ─── notice.log ──────────────────────────────────────────────────────────────

def analyse_notice(logdir: Path) -> dict:
    rows = parse_zeek_log(logdir / "notice.log")

    infra, detections = [], []
    for r in rows:
        note = r.get("note", "")
        if note in INFRA_NOTICES:
            infra.append(r)
        else:
            detections.append(r)

    tp_rows = [r for r in detections if ip_match(r, MALICIOUS_IP)]
    fp_rows = [r for r in detections if not ip_match(r, MALICIOUS_IP)]

    tp = len(tp_rows)
    fp = len(fp_rows)
    fn = GROUND_TRUTH - tp

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / GROUND_TRUTH
    f1        = (2 * precision * recall / (precision + recall)
                 if (precision + recall) > 0 else 0.0)

    # Desglose de tipos reales
    detection_types = defaultdict(int)
    for r in detections:
        detection_types[r.get("note", "Unknown")] += 1

    infra_types = defaultdict(int)
    for r in infra:
        infra_types[r.get("note", "Unknown")] += 1

    # Detalle de TPs
    tp_detail = []
    for r in tp_rows:
        tp_detail.append({
            "note": r.get("note"),
            "src":  r.get("src", r.get("id.orig_h", "-")),
            "dst":  r.get("dst", r.get("id.resp_h", "-")),
            "msg":  r.get("msg", "")[:100],
        })

    return {
        "total_raw_notices":   len(rows),
        "infra_notices":       len(infra),
        "detection_notices":   len(detections),
        "tp": tp, "fp": fp, "fn": fn,
        "precision":  round(precision, 4),
        "recall":     round(recall, 4),
        "f1":         round(f1, 4),
        "detection_types": dict(detection_types),
        "infra_types":     dict(infra_types),
        "tp_detail":       tp_detail,
        "fp_detail": [
            {"note": r.get("note"), "msg": r.get("msg", "")[:80]}
            for r in fp_rows
        ],
    }

# ─── conn.log ────────────────────────────────────────────────────────────────

def analyse_conn(logdir: Path) -> dict:
    rows = parse_zeek_log(logdir / "conn.log")
    mal  = [r for r in rows if ip_match(r, MALICIOUS_IP)]

    services = defaultdict(int)
    for r in mal:
        services[r.get("service", "-")] += 1

    durations = []
    for r in mal:
        try:
            durations.append(float(r.get("duration", "0") or "0"))
        except ValueError:
            pass

    dest_ips = {r.get("id.resp_h") for r in mal
                if r.get("id.orig_h") == MALICIOUS_IP}

    return {
        "total_flows":      len(rows),
        "malicious_flows":  len(mal),
        "unique_dest_ips":  len(dest_ips),
        "services":         dict(services),
        "avg_duration_s":   round(sum(durations)/len(durations), 3) if durations else 0,
        "max_duration_s":   round(max(durations), 3) if durations else 0,
    }

# ─── weird.log ───────────────────────────────────────────────────────────────

def analyse_weird(logdir: Path) -> dict:
    rows = parse_zeek_log(logdir / "weird.log")
    mal  = [r for r in rows if ip_match(r, MALICIOUS_IP)]

    weird_types = defaultdict(int)
    for r in mal:
        weird_types[r.get("name", "unknown")] += 1

    # Top 10
    top = sorted(weird_types.items(), key=lambda x: -x[1])[:10]

    return {
        "total_weird":    len(rows),
        "malicious_weird": len(mal),
        "top_types":      dict(top),
    }

# ─── http.log ────────────────────────────────────────────────────────────────

def analyse_http(logdir: Path) -> dict:
    rows = parse_zeek_log(logdir / "http.log")
    mal  = [r for r in rows
            if r.get("id.orig_h") == MALICIOUS_IP
            or r.get("id.resp_h") == MALICIOUS_IP]

    methods = defaultdict(int)
    status  = defaultdict(int)
    hosts   = defaultdict(int)
    for r in mal:
        methods[r.get("method", "-")] += 1
        status[r.get("status_code", "-")] += 1
        hosts[r.get("host", "-")] += 1

    top_hosts = sorted(hosts.items(), key=lambda x: -x[1])[:10]

    return {
        "total_http":    len(rows),
        "malicious_http": len(mal),
        "methods":  dict(methods),
        "status_codes": dict(status),
        "top_hosts": dict(top_hosts),
    }

# ─── smtp.log ────────────────────────────────────────────────────────────────

def analyse_smtp(logdir: Path) -> dict:
    rows = parse_zeek_log(logdir / "smtp.log")
    mal  = [r for r in rows
            if r.get("id.orig_h") == MALICIOUS_IP]

    domains = defaultdict(int)
    for r in mal:
        domains[r.get("mailfrom", "-")] += 1

    return {
        "total_smtp":    len(rows),
        "malicious_smtp": len(mal),
        "sample_mailfrom": list(domains.keys())[:5],
    }

# ─── ssl.log ─────────────────────────────────────────────────────────────────

def analyse_ssl(logdir: Path) -> dict:
    rows = parse_zeek_log(logdir / "ssl.log")
    mal  = [r for r in rows if ip_match(r, MALICIOUS_IP)]

    invalid = [r for r in mal
               if r.get("validation_status", "") not in ("ok", "-", "")]

    subjects = defaultdict(int)
    for r in invalid:
        subjects[r.get("subject", "-")] += 1

    return {
        "total_ssl":       len(rows),
        "malicious_ssl":   len(mal),
        "invalid_certs":   len(invalid),
        "cert_subjects":   dict(subjects),
    }

# ─── Main ────────────────────────────────────────────────────────────────────

def print_section(title: str):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")

def main():
    parser = argparse.ArgumentParser(
        description="Zeek log analysis v2 — separates infra notices from real detections"
    )
    parser.add_argument("--logdir", required=True,
                        help="Directorio con logs Zeek (e.g. /vagrant/logs/experiment/zeek/10mbps)")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    logdir = Path(args.logdir)
    print(f"\n{'='*60}")
    print(f"  Zeek v2 analysis — {logdir.name}")
    print(f"  Ground truth: {MALICIOUS_IP} ({GROUND_TRUTH} malicious flows)")
    print(f"{'='*60}")

    notice = analyse_notice(logdir)
    conn   = analyse_conn(logdir)
    weird  = analyse_weird(logdir)
    http_  = analyse_http(logdir)
    smtp_  = analyse_smtp(logdir)
    ssl_   = analyse_ssl(logdir)

    # ── notice.log (corregido) ────────────────────────────────────────────────
    print_section("notice.log — CORRECTED METRICS (CaptureLoss excluded)")
    print(f"  Raw notices total   : {notice['total_raw_notices']}")
    print(f"  Infrastructure noise: {notice['infra_notices']}  {notice['infra_types']}")
    print(f"  Real detections     : {notice['detection_notices']}")
    print(f"  TP  : {notice['tp']:4d}  (malicious host detected)")
    print(f"  FP  : {notice['fp']:4d}  (benign host false alarm)")
    print(f"  FN  : {notice['fn']:4d}  (malicious flows missed)")
    print(f"  Precision : {notice['precision']:.4f}")
    print(f"  Recall    : {notice['recall']:.4f}")
    print(f"  F1        : {notice['f1']:.4f}")
    if notice["detection_types"]:
        print(f"\n  Detection types:")
        for k, v in sorted(notice["detection_types"].items(), key=lambda x: -x[1]):
            tag = "  ← TP" if any(d["note"] == k for d in notice["tp_detail"]) else ""
            print(f"    {k}: {v}{tag}")
    if notice["tp_detail"]:
        print(f"\n  TP sample (first 3):")
        for d in notice["tp_detail"][:3]:
            print(f"    [{d['note']}] {d['src']} → {d['dst']}")
            print(f"    msg: {d['msg']}")

    # ── conn.log ──────────────────────────────────────────────────────────────
    print_section("conn.log — behavioral profile of 147.32.84.165")
    print(f"  Total flows         : {conn['total_flows']}")
    print(f"  Malicious flows     : {conn['malicious_flows']}")
    print(f"  Unique dest IPs     : {conn['unique_dest_ips']}")
    print(f"  Services            : {conn['services']}")
    print(f"  Avg duration        : {conn['avg_duration_s']}s")
    print(f"  Max duration        : {conn['max_duration_s']}s  ({conn['max_duration_s']/3600:.2f}h)")

    # ── weird.log ─────────────────────────────────────────────────────────────
    print_section("weird.log — protocol anomalies on malicious host")
    print(f"  Total weird events  : {weird['total_weird']}")
    print(f"  From malicious host : {weird['malicious_weird']}")
    if weird["top_types"]:
        print(f"  Top anomaly types   :")
        for k, v in weird["top_types"].items():
            print(f"    {k}: {v}")
    else:
        print("  (no weird events from malicious host)")

    # ── http.log ──────────────────────────────────────────────────────────────
    print_section("http.log — HTTP C2 / click fraud traffic")
    print(f"  Total HTTP flows    : {http_['total_http']}")
    print(f"  From malicious host : {http_['malicious_http']}")
    print(f"  Methods             : {http_['methods']}")
    print(f"  Status codes        : {http_['status_codes']}")
    if http_["top_hosts"]:
        print(f"  Top contacted hosts :")
        for h, n in list(http_["top_hosts"].items())[:5]:
            print(f"    {h}: {n} requests")

    # ── smtp.log ──────────────────────────────────────────────────────────────
    print_section("smtp.log — spam activity")
    print(f"  Total SMTP sessions : {smtp_['total_smtp']}")
    print(f"  From malicious host : {smtp_['malicious_smtp']}")
    if smtp_["sample_mailfrom"]:
        print(f"  Sample mailfrom     : {smtp_['sample_mailfrom']}")

    # ── ssl.log ───────────────────────────────────────────────────────────────
    print_section("ssl.log — certificate analysis")
    print(f"  Total SSL flows     : {ssl_['total_ssl']}")
    print(f"  From malicious host : {ssl_['malicious_ssl']}")
    print(f"  Invalid certs       : {ssl_['invalid_certs']}  ← origin of SSL::Invalid_Server_Cert notices")

    # ── resumen paradigmas ────────────────────────────────────────────────────
    print_section("PARADIGM COMPARISON SUMMARY")
    print(f"  {'System':<20} {'Paradigm':<25} {'F1':>6} {'Recall':>8} {'TP':>5}")
    print(f"  {'─'*20} {'─'*25} {'─'*6} {'─'*8} {'─'*5}")
    print(f"  {'Suricata 6.0.10':<20} {'Signature (ET Open)':<25} {'0.0000':>6} {'0.0000':>8} {'0':>5}")
    print(f"  {'Zeek 8.1.2 (default)':<20} {'Scripting behavioral':<25} {notice['f1']:>6.4f} {notice['recall']:>8.4f} {notice['tp']:>5}")
    print(f"  {'aRGus NDR':<20} {'ML behavioral':<25} {'0.9985':>6} {'1.0000':>8} {'646':>5}")
    print()

    result = {
        "logdir": str(logdir),
        "ground_truth": {"ip": MALICIOUS_IP, "flows": GROUND_TRUTH},
        "zeek_version": "8.1.2",
        "phase": "1-default-scripts-offline",
        "notice_corrected": notice,
        "conn": conn,
        "weird": weird,
        "http": http_,
        "smtp": smtp_,
        "ssl": ssl_,
    }

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2, ensure_ascii=False))
        print(f"JSON guardado en {out}")

    return result


if __name__ == "__main__":
    main()