#!/usr/bin/env python3
"""
parse_results.py — Suricata eve.json → métricas paper v19
Compara con Table 3 (detección) y Table 11 (throughput) de aRGus DAY 145

Usage: python3 parse_results.py <eve.json> <malicious_ip>
"""
import sys
import json
from collections import defaultdict

EVE_FILE   = sys.argv[1] if len(sys.argv) > 1 else "/var/log/suricata/eve.json"
MALICIOUS  = sys.argv[2] if len(sys.argv) > 2 else "147.32.84.165"
GT_TP      = 646    # flows maliciosos ground truth (Neris)
GT_BENIGN  = 12075  # flows benignos ground truth (Neris)

alerts = []
try:
    with open(EVE_FILE) as f:
        for line in f:
            try:
                e = json.loads(line)
                if e.get("event_type") == "alert":
                    alerts.append(e)
            except:
                pass
except FileNotFoundError:
    print(f"❌ {EVE_FILE} no encontrado")
    sys.exit(1)

# Flows únicos por src_ip
tp_flows = set()
fp_flows = set()

for a in alerts:
    src = a.get("src_ip", "")
    key = (src, a.get("dest_ip",""), a.get("src_port",0),
           a.get("dest_port",0), a.get("proto",""))
    if src == MALICIOUS:
        tp_flows.add(key)
    else:
        fp_flows.add(key)

TP = len(tp_flows)
FP = len(fp_flows)
FN = max(0, GT_TP - TP)
TN = max(0, GT_BENIGN - FP)

precision = TP/(TP+FP) if (TP+FP) > 0 else 0
recall    = TP/GT_TP   if GT_TP > 0 else 0
f1        = 2*precision*recall/(precision+recall) if (precision+recall) > 0 else 0
fpr       = FP/GT_BENIGN if GT_BENIGN > 0 else 0

# Reglas más disparadas
rules = defaultdict(int)
for a in alerts:
    sig = a.get("alert", {}).get("signature", "unknown")
    rules[sig] += 1
top_rules = sorted(rules.items(), key=lambda x: -x[1])[:5]

print()
print("╔════════════════════════════════════════════════════════════╗")
print("║  Suricata 6.0.10 — CTU-13 Neris — Métricas Comparativas  ║")
print("╠════════════════════════════════════════════════════════════╣")
print(f"║  Total alertas:        {len(alerts):<35}║")
print(f"║  TP flows:             {TP:<35}║")
print(f"║  FP flows:             {FP:<35}║")
print(f"║  FN:                   {FN:<35}║")
print(f"║  TN:                   {TN:<35}║")
print(f"║  Precision:            {precision:.4f}{'':<30}║")
print(f"║  Recall:               {recall:.4f}{'':<30}║")
print(f"║  F1:                   {f1:.4f}{'':<30}║")
print(f"║  FPR:                  {fpr:.6f}{'':<28}║")
print("╠════════════════════════════════════════════════════════════╣")
print("║  Comparativa aRGus DAY 145 (Table 3 paper v19):           ║")
print("║  F1=0.9985  Prec=0.9969  Rec=1.0000  FPR=0.0002%         ║")
print("╠════════════════════════════════════════════════════════════╣")
print("║  Top 5 reglas disparadas:                                 ║")
for sig, cnt in top_rules:
    line = f"  {cnt:>5}x  {sig[:48]}"
    print(f"║  {line:<58}║")
print("╚════════════════════════════════════════════════════════════╝")
print()

# JSON para el paper
result = {
    "system": "Suricata",
    "version": "6.0.10",
    "dataset": "CTU-13 Neris",
    "ground_truth_ip": MALICIOUS,
    "total_alerts": len(alerts),
    "TP": TP, "FP": FP, "FN": FN, "TN": TN,
    "precision": round(precision, 4),
    "recall": round(recall, 4),
    "f1": round(f1, 4),
    "fpr": round(fpr, 6),
    "top_rules": [{"rule": r, "count": c} for r,c in top_rules]
}
out = f"/vagrant/logs/experiment/suricata_metrics_final.json"
try:
    with open(out, "w") as f:
        json.dump(result, f, indent=2)
    print(f"✅ Métricas guardadas en {out}")
except:
    print(json.dumps(result, indent=2))
