#!/usr/bin/env python3
"""DAY293 1a — detalle de casos (split:modelo:semilla): recall por familia/tasa del atacante fuera del arranque, victim_rate_ratio
de los fallos frente al de los benignos (test y train) e importancias. Regenera los splits con el MISMO generador que
d293_intervalos.py: --seed-splits y --n-splits deben coincidir con la corrida que se analiza."""
import argparse
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

ap = argparse.ArgumentParser()
ap.add_argument("--cons", default="/vagrant/logs/lab/day292/consolidado_caliente.csv")
ap.add_argument("--n-splits", type=int, default=60)
ap.add_argument("--seed-splits", type=int, default=2026)
ap.add_argument("--casos", default="S7:Bsinpps:7,S7:Bsinpps:42,S52:B:42,S52:Bsinpps:42")
a = ap.parse_args()

F7 = ["syn_ack_ratio", "mean_packet_size", "reflection_signature", "packet_size_entropy",
      "flow_packet_count", "flow_completion_rate", "victim_rate_ratio"]
MODELOS = {"A": (F7 + ["victim_pps"], False), "B": (F7 + ["victim_pps"], True), "Bsinpps": (F7, True)}
ATAQUES = ["ntp", "dns", "syn", "udpA", "udpB"]
STR = {"tasa": str, "fichero": str, "community_id": str, "src_ip": str, "dst_ip": str}
R = "victim_rate_ratio"


def pesos(d):
    w = pd.Series(0.0, index=d.index)
    for y, dy in d.groupby("etiqueta"):
        nroles = dy.rol.nunique()
        for rol, dr in dy.groupby("rol"):
            celdas = dr.groupby(["familia", "tasa"]).size()
            for (f, t), n in celdas.items():
                m = (d.etiqueta == y) & (d.rol == rol) & (d.familia == f) & (d.tasa == t)
                w[m] = 1.0 / (nroles * len(celdas) * n)
    return w * (len(d) / w.sum())


def q(s):
    s = s.astype(float)
    if not len(s):
        return "n/a"
    return "%.2f/%.2f/%.2f/%.2f" % (s.min(), s.quantile(0.05), s.quantile(0.5), s.quantile(0.95))


X = pd.read_csv(a.cons, dtype=STR)
X["arranque"] = X.arranque.astype(str) == "True"
runs = X.groupby("fichero")[["familia", "tasa", "split"]].first().reset_index()
contr = sorted(runs[~runs.familia.isin(ATAQUES)].fichero)
splits = [("D2", set(runs[runs.split == "test"].fichero))]
rng = np.random.default_rng(a.seed_splits)
vistos, intentos = {frozenset(splits[0][1])}, 0
while len(splits) < a.n_splits + 1 and intentos < 10000:
    intentos += 1
    t = set()
    for fam in ATAQUES:
        t.add(rng.choice(sorted(runs[runs.familia == fam].fichero)))
    t.add(rng.choice(contr))
    if frozenset(t) not in vistos:
        vistos.add(frozenset(t)); splits.append(("S%d" % len(splits), t))
S = dict(splits)

print("ratio = min/p05/p50/p95")
for caso in a.casos.split(","):
    sid, m, s = caso.split(":"); s = int(s)
    feats, sin_arr = MODELOS[m]
    te = X[X.fichero.isin(S[sid])].copy()
    tr = X[~X.fichero.isin(S[sid])]
    if sin_arr:
        tr = tr[~tr.arranque]
    rf = RandomForestClassifier(random_state=s, n_jobs=-1)
    rf.fit(tr[feats], tr.etiqueta, sample_weight=pesos(tr))
    te["pred"] = rf.predict(te[feats])
    tdesc = " ".join("%s%s" % (f, t) for f, t in sorted(zip(runs[runs.fichero.isin(S[sid])].familia, runs[runs.fichero.isin(S[sid])].tasa)))
    print("\n=== %s %s semilla %d  test: %s" % (sid, m, s, tdesc))
    at = te[(te.rol == "atacante") & ~te.arranque]
    print("  ATACANTE TEST fuera del arranque: familia tasa n recall | ratio todas | ratio FN")
    for (f, t), g in at.groupby(["familia", "tasa"]):
        fn = g[g.pred == 0]
        print("   %-5s %4s %6d %7.2f%% | %s | %s (n=%d)" % (f, t, len(g), 100 * g.pred.mean(), q(g[R]), q(fn[R]), len(fn)))
    for rol in ["contraste", "inocente"]:
        g = te[(te.rol == rol) & (te.fase == "durante")]
        print("  %s TEST durante: n=%d marcadas=%d ratio %s" % (rol.upper(), len(g), int(g.pred.sum()), q(g[R])))
    g = tr[(tr.rol == "contraste") & (tr.fase == "durante")]
    print("  CONTRASTE TRAIN durante: ratio %s  max=%.2f" % (q(g[R]), g[R].astype(float).max() if len(g) else float("nan")))
    g = tr[(tr.rol == "atacante") & (tr.tasa == "30")]
    print("  ATACANTE TRAIN a 30 pps: ratio %s" % q(g[R]))
    imp = sorted(zip(rf.feature_importances_, feats), reverse=True)
    print("  importancias: " + "  ".join("%s=%.3f" % (n, v) for v, n in imp))
