#!/usr/bin/env python3
"""DAY292 — reentrenamiento de la cabeza DDoS v2 en régimen CALIENTE (decisiones D1-D3).
RF random_state=42, sin scaler. Pesos jerárquicos: clases 50/50; dentro de cada clase cada rol igual;
dentro de cada rol cada corrida (familia, tasa) igual. Salidas en logs/lab/day292/."""
import hashlib, sys
from pathlib import Path
import numpy as np
import pandas as pd
import joblib, sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance

D = Path("/vagrant/logs/lab/day292")
CONS = D / "consolidado_caliente.csv"
FRIO = Path("/vagrant/logs/lab/day289/consolidado.csv")
MODELO = D / "ddos_v2_rf_caliente.joblib"
FEATS = ["syn_ack_ratio", "mean_packet_size", "reflection_signature", "packet_size_entropy",
         "flow_packet_count", "flow_completion_rate", "victim_rate_ratio", "victim_pps"]
ATAQUES = ["ntp", "dns", "syn", "udpA", "udpB"]
STR = {"tasa": str, "fichero": str, "community_id": str, "src_ip": str, "dst_ip": str}
SEED = 42


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


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


def entrenar(d):
    rf = RandomForestClassifier(random_state=SEED, n_jobs=-1)
    rf.fit(d[FEATS], d.etiqueta, sample_weight=pesos(d))
    return rf


def pct(s):
    return f"{100.0 * s.mean():6.2f}%"


X = pd.read_csv(CONS, dtype=STR)
tr, te = X[X.split == "train"], X[X.split == "test"]
print(f"sklearn {sklearn.__version__}  train={len(tr)}  test={len(te)}")
rf = entrenar(tr)
te = te.assign(pred=rf.predict(te[FEATS]))

print("\n== TEST (60 pps + bdns_large_10): % marcado ataque por rol / familia / fase")
t = te.groupby(["rol", "familia", "tasa", "fase"]).pred.agg(["size", "mean"])
t["mean"] = (100 * t["mean"]).round(2)
print(t.to_string())

print("\n== PUERTAS sobre test")
a = te[te.rol == "atacante"]
print("  recall atacante:", pct(a.pred), " por familia:",
      {f: round(100 * g.pred.mean(), 2) for f, g in a.groupby("familia")})
for rol in ["inocente", "contraste", "ambiente_victima", "ambiente"]:
    g = te[te.rol == rol]
    print(f"  FP {rol:17s} total {pct(g.pred)}  durante {pct(g[g.fase == 'durante'].pred)}  n={len(g)}")

print("\n== importancias por impureza")
for f, v in sorted(zip(FEATS, rf.feature_importances_), key=lambda x: -x[1]):
    print(f"  {f:22s} {v:.4f}")
pi = permutation_importance(rf, te[FEATS], te.etiqueta, scoring="balanced_accuracy",
                            n_repeats=5, random_state=SEED, n_jobs=-1)
print("== importancias por permutación (test, balanced_accuracy)")
for i in np.argsort(-pi.importances_mean):
    print(f"  {FEATS[i]:22s} {pi.importances_mean[i]:.4f} ± {pi.importances_std[i]:.4f}")

nodos = sum(e.tree_.node_count for e in rf.estimators_)
prof = max(e.tree_.max_depth for e in rf.estimators_)
print(f"\n== tamaño del bosque: árboles={len(rf.estimators_)} nodos_total={nodos} profundidad_max={prof}")

print("\n== FAMILIA FUERA (train sin esa familia; recall sobre TODAS sus filas atacante; FP inocente durante)")
for fam in ATAQUES:
    m = entrenar(tr[tr.familia != fam])
    g = X[X.familia == fam]
    p = pd.Series(m.predict(g[FEATS]), index=g.index)
    at = g.rol == "atacante"
    ino = (g.rol == "inocente") & (g.fase == "durante")
    por = {tt: round(100 * p[at & (g.tasa == tt)].mean(), 2) for tt in ["30", "60", "100"]}
    print(f"  sin {fam:5s} recall={pct(p[at])} {por}  FP inocente durante={pct(p[ino])}")

print("\n== TASA FUERA (train 30/60 + contrastes bdns; test 100 pps)")
tr3 = X[X.tasa.isin(["30", "60"]) | X.familia.str.startswith("bdns")]
te3 = X[X.tasa == "100"]
m = entrenar(tr3)
p = pd.Series(m.predict(te3[FEATS]), index=te3.index)
at = te3.rol == "atacante"
print("  recall 100 pps:", pct(p[at]), {f: round(100 * p[at & (te3.familia == f)].mean(), 2) for f in ATAQUES})
ino = (te3.rol == "inocente") & (te3.fase == "durante")
print("  FP inocente durante:", pct(p[ino]))

print("\n== SONDA sobre test (atacante y inocente durante): % marcado ataque")
base = te[(te.rol == "atacante") | ((te.rol == "inocente") & (te.fase == "durante"))]
for nombre, fn in [("original", lambda z: z),
                   ("victim_pps x0.1", lambda z: z.assign(victim_pps=z.victim_pps * 0.1)),
                   ("victim_pps x0.25", lambda z: z.assign(victim_pps=z.victim_pps * 0.25)),
                   ("victim_pps x0.5", lambda z: z.assign(victim_pps=z.victim_pps * 0.5)),
                   ("victim_pps x2", lambda z: z.assign(victim_pps=z.victim_pps * 2)),
                   ("victim_pps x4", lambda z: z.assign(victim_pps=z.victim_pps * 4)),
                   ("ratio=1 (víctima fría)", lambda z: z.assign(victim_rate_ratio=1.0))]:
    z = fn(base.copy())
    p = pd.Series(rf.predict(z[FEATS]), index=z.index)
    r = {f: round(100 * p[(z.rol == "atacante") & (z.familia == f)].mean(), 1) for f in ATAQUES}
    print(f"  {nombre:24s} atacante {r}  inocente {pct(p[z.rol == 'inocente'])}")

print("\n== FRÍO DAY288/289 (solo evaluación, D1)")
if FRIO.exists():
    F = pd.read_csv(FRIO, dtype=STR)
    F = F[(F[FEATS] > -9000).all(axis=1)]
    F = F.assign(pred=rf.predict(F[FEATS]))
    t = F.groupby(["etiqueta", "familia", "tasa"]).pred.agg(["size", "mean"])
    t["mean"] = (100 * t["mean"]).round(2)
    print(t.to_string())
else:
    print("  FALTA", FRIO)

joblib.dump(rf, MODELO)
print(f"\nmodelo: {MODELO}\n{sha(MODELO)}  {MODELO}\n{sha(CONS)}  {CONS}")
