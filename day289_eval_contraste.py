#!/usr/bin/env python3
"""DAY289 — aplica el modelo PROVISIONAL (sin reentrenar) a las corridas de contraste.
Comprueba el sha256 del modelo, filtra igual que el consolidador (.50→.1, kind=0, rasgos, UDP),
reporta % marcado ataque (aquí = FP), distribución de probabilidad, por tercio temporal, y una sonda
de sensibilidad: mismas filas con victim_pps fijado a valores de benigno y de ataque."""
import hashlib, sys
from pathlib import Path
import numpy as np
import pandas as pd
import joblib

OUT = Path("/vagrant/logs/lab/day289")
MODELO = OUT / "ddos_v2_rf_provisional.joblib"
REG = Path("/vagrant/logs/lab/day288/contraste.tsv")
DSDIR = Path("/vagrant/logs/lab/ddos_dataset")
FEATS = ["syn_ack_ratio", "mean_packet_size", "reflection_signature", "packet_size_entropy",
         "flow_packet_count", "flow_completion_rate", "victim_rate_ratio", "victim_pps"]
STR = {"community_id": str, "src_ip": str, "dst_ip": str}
SONDA = [2, 5, 10, 30, 60, 100]


def parar(msg):
    print("PARAR:", msg)
    sys.exit(1)


h = hashlib.sha256(MODELO.read_bytes()).hexdigest()
esperado = (OUT / "modelo.sha256").read_text().split()[0]
if h != esperado:
    parar(f"sha256 del modelo {h} != {esperado}")
rf = joblib.load(MODELO)
print(f"modelo OK sha256={h[:12]}…")
if not REG.is_file():
    parar(f"falta {REG}")

for linea in REG.read_text().splitlines():
    c = linea.split("\t")
    if len(c) < 3:
        continue
    fam, tasa, fic = c[0], c[1], c[2]
    f = DSDIR / fic
    if not f.is_file():
        parar(f"falta {f}")
    d = pd.read_csv(f, dtype=STR)
    d = d[(d.src_ip == "192.168.100.50") & (d.dst_ip == "192.168.100.1") &
          (d.event_kind == 0) & (d.syn_ack_ratio > -9000) & (d.proto == 17)].sort_values("ts_ns")
    if d.empty:
        parar(f"sin filas tras filtrar en {fic}")
    X = d[FEATS]
    p = rf.predict_proba(X)[:, 1]
    marca = p >= 0.5
    q = np.percentile(p, [5, 50, 95])
    ter = "/".join(f"{100*x.mean():.1f}%" for x in np.array_split(marca, 3))
    print(f"\n{fam:10s} {tasa:>3s} pps  {fic}  n={len(d)}")
    print(f"  FP nuevo={100*marca.mean():6.2f}%  viejo={100*(d.old_ddos_class == 1).mean():6.2f}%  "
          f"prob p5/p50/p95={q[0]:.3f}/{q[1]:.3f}/{q[2]:.3f}  tercios={ter}")
    print(f"  medias: mean_size={d.mean_packet_size.mean():.1f} refl={d.reflection_signature.mean():.2f} "
          f"flow_pkts={d.flow_packet_count.mean():.2f} ratio={d.victim_rate_ratio.mean():.3f} "
          f"victim_pps={d.victim_pps.mean():.1f}")
    sonda = []
    for v in SONDA:
        Xs = X.copy()
        Xs["victim_pps"] = float(v)
        sonda.append(f"{v}:{100*(rf.predict_proba(Xs)[:, 1] >= 0.5).mean():.1f}%")
    print("  sonda victim_pps→ % ataque  " + "  ".join(sonda))
