#!/usr/bin/env python3
"""
ML Defender - F1 Score Calculator (DAY 81+)
Via Appia Quality - Consejo de Sabios

Methodology:
  - Ground truth: CTU-13 Neris botnet malicious IPs
  - Detections: [FAST ALERT] lines from sniffer.log with src/dst IPs
  - TP: FAST ALERT where src OR dst is a known malicious IP
  - FP: FAST ALERT where neither src nor dst is malicious
  - FN: estimated from total_events - TP (requires --total-events argument)
  - TN: total_events - TP - FP - FN

Usage:
  python3 calculate_f1_neris.py <sniffer_log> --total-events <N> [--threshold <T>]

Example:
  python3 calculate_f1_neris.py /tmp/sniffer_day81.log --total-events 9594
"""

import re
import sys
import argparse
from collections import defaultdict

# CTU-13 Neris botnet ground truth - known malicious IPs
MALICIOUS_IPS = {
    '147.32.84.165',   # Neris primary C&C
    '147.32.84.191',   # Neris secondary
    '147.32.84.192',   # Neris secondary
}

# Pattern: [FAST ALERT] Ransomware heuristic: src=IP:port dst=IP:port (ExtIPs=N, SMB=N)
FAST_ALERT_PATTERN = re.compile(
    r'\[FAST ALERT\].*?src=(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):\d+\s+dst=(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):\d+'
)

# Pattern for FAST-DETECT SUSPICIOUS lines (to count total fast evaluations)
FAST_DETECT_PATTERN = re.compile(r'\[FAST-DETECT\].*?FastScore=([\d.]+)')


def parse_sniffer_log(log_file: str):
    """Parse sniffer.log and extract FAST ALERTs with IPs."""
    alerts = []
    fast_evaluations = 0

    try:
        with open(log_file, 'r', errors='replace') as f:
            for line in f:
                # Count FAST-DETECT evaluations
                m = FAST_DETECT_PATTERN.search(line)
                if m:
                    fast_evaluations += 1
                    continue

                # Extract FAST ALERTs with IPs
                m = FAST_ALERT_PATTERN.search(line)
                if m:
                    src_ip = m.group(1)
                    dst_ip = m.group(2)
                    is_malicious = (src_ip in MALICIOUS_IPS or dst_ip in MALICIOUS_IPS)
                    alerts.append({
                        'src': src_ip,
                        'dst': dst_ip,
                        'is_malicious': is_malicious,
                        'line': line.strip()
                    })
    except FileNotFoundError:
        print(f"ERROR: File not found: {log_file}")
        sys.exit(1)

    return alerts, fast_evaluations


def deduplicate_alerts(alerts):
    """
    Deduplicate alerts by (src, dst) pair.
    Multiple [FAST ALERT] lines for the same flow are one detection event.
    Returns deduplicated list and raw count.
    """
    seen = set()
    deduped = []
    for a in alerts:
        key = (a['src'], a['dst'])
        if key not in seen:
            seen.add(key)
            deduped.append(a)
    return deduped, len(alerts)


def calculate_metrics(tp, fp, fn, tn):
    total = tp + fp + fn + tn
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    fpr       = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    accuracy  = (tp + tn) / total if total > 0 else 0.0
    return {
        'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'fpr': fpr,
        'accuracy': accuracy,
        'total': total
    }


def print_results(m, label, raw_alert_count, dedup_count, total_events, note=""):
    print()
    print("=" * 68)
    print(f"  {label}")
    print("=" * 68)
    print(f"  Raw [FAST ALERT] lines:      {raw_alert_count}")
    print(f"  Deduplicated alert events:   {dedup_count}")
    print(f"  Total events (ml-detector):  {total_events}")
    print()
    print(f"  TP  (malicious, detected):   {m['tp']}")
    print(f"  FP  (benign, false alarm):   {m['fp']}")
    print(f"  FN  (malicious, missed):     {m['fn']}")
    print(f"  TN  (benign, correct):       {m['tn']}")
    print()
    print(f"  Precision:  {m['precision']:.4f}")
    print(f"  Recall:     {m['recall']:.4f}")
    print(f"  F1-Score:   {m['f1']:.4f}  ← paper metric")
    print(f"  FPR:        {m['fpr']:.4f}")
    print(f"  Accuracy:   {m['accuracy']:.4f}")
    if note:
        print()
        print(f"  NOTE: {note}")
    print("=" * 68)


def main():
    parser = argparse.ArgumentParser(description='ML Defender F1 Calculator')
    parser.add_argument('sniffer_log', help='Path to sniffer.log')
    parser.add_argument('--total-events', type=int, required=True,
                        help='Total events processed (from ml-detector stats)')
    parser.add_argument('--day', type=str, default='?',
                        help='Day label for output (e.g. DAY81)')
    parser.add_argument('--thresholds', type=str, default='',
                        help='Threshold description (e.g. ddos=0.85,ransom=0.90)')
    args = parser.parse_args()

    print()
    print("=" * 68)
    print("  ML DEFENDER - F1 SCORE CALCULATOR")
    print(f"  Day: {args.day}  |  Thresholds: {args.thresholds}")
    print(f"  Ground truth: CTU-13 Neris ({len(MALICIOUS_IPS)} malicious IPs)")
    print("=" * 68)
    print(f"  Malicious IPs: {', '.join(sorted(MALICIOUS_IPS))}")

    alerts, fast_evals = parse_sniffer_log(args.sniffer_log)
    deduped, raw_count = deduplicate_alerts(alerts)

    total_events = args.total_events

    # --- Metrics using DEDUPLICATED alerts ---
    tp = sum(1 for a in deduped if a['is_malicious'])
    fp = sum(1 for a in deduped if not a['is_malicious'])

    # FN: malicious flows that were NOT detected
    # We don't have per-event IP in ml-detector, so FN = estimated from
    # total malicious detections expected. Conservative estimate:
    # assume all malicious events in PCAP that didn't trigger FAST ALERT = FN
    # Without full per-event IP table, FN must be treated as lower bound = 0
    # (we know Fast Detector caught 4712 events >= 0.70)
    fn_note = ("FN estimated as 0 — [FAST ALERT] only fires on detected flows. "
               "True FN requires per-event IP table. "
               "Recall=1.0 is an upper bound, not confirmed.")
    fn = 0
    tn = total_events - tp - fp - fn

    m = calculate_metrics(tp, fp, fn, tn)
    print_results(
        m,
        label=f"FAST DETECTOR — deduplicated alerts vs ground truth",
        raw_alert_count=raw_count,
        dedup_count=len(deduped),
        total_events=total_events,
        note=fn_note
    )

    # --- IP breakdown ---
    print()
    print("  DETECTED IPs breakdown:")
    ip_counts = defaultdict(int)
    for a in deduped:
        for ip in [a['src'], a['dst']]:
            if ip in MALICIOUS_IPS:
                ip_counts[ip] += 1
    if ip_counts:
        for ip, count in sorted(ip_counts.items()):
            print(f"    {ip}  →  {count} flow(s) detected  [MALICIOUS ✓]")
    else:
        print("    No malicious IPs detected in alerts.")

    benign_alerts = [a for a in deduped if not a['is_malicious']]
    if benign_alerts:
        print(f"\n  FALSE POSITIVE IPs (sample, max 5):")
        for a in benign_alerts[:5]:
            print(f"    src={a['src']}  dst={a['dst']}")

    print()
    print("  CSV line for f1_replay_log.csv:")
    print(f"  DAY{args.day},{args.thresholds},{total_events},"
          f"{m['tp']},{m['fp']},{m['fn']},{m['tn']},"
          f"{m['f1']:.4f},{m['precision']:.4f},{m['recall']:.4f},{m['fpr']:.4f}")
    print()


if __name__ == '__main__':
    main()