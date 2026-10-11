#!/usr/bin/env python3
"""DAY292 — modelo B: como day292_entrenar.py pero SIN las filas de arranque del atacante (D4) en entrenamiento,
y recall informado fuera y dentro del arranque + latencia de detección por corrida de test.
RF random_state=42, sin scaler, pesos jerárquicos (clases 50/50; rol igual; corrida igual)."""
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import joblib, sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance

D = Path("/vagrant/logs/lab/day292")
CONS = D / "consolidado_caliente.csv"
FRIO = Path("/vagrant/logs/lab/day289/consolidado.csv")
MODELO = D / "ddos_v2_rf_caliente_b.joblib"
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
    return f"{100.0 * s.mean():6.2f}%" if len(s) else "   n/a "


X = pd.read_csv(CONS, dtype=STR)
if "arranque" not in X.columns:
    raise SystemExit("PARAR: el consolidado no tiene columna 'arranque' (falta el patch D4)")
X["arranque"] = X.arranque.astype(str) == "True"
tr = X[(X.split == "train") & ~X.arranque]
te = X[X.split == "test"].copy()
print(f"sklearn {sklearn.__version__}  train={len(tr)} (arranque excluido: {int(X[X.split == 'train'].arranque.sum())})  test={len(te)}")
rf = entrenar(tr)
te["pred"] = rf.predict(te[FEATS])

print("\n== PUERTAS sobre test")
a = te[te.rol == "atacante"]
print("  recall atacante FUERA del arranque:", pct(a[~a.arranque].pred),
      {f: round(100 * g.pred.mean(), 2) for f, g in a[~a.arranque].groupby("familia")})
print("  recall atacante EN el arranque:    ", pct(a[a.arranque].pred),
      {f: round(100 * g.pred.mean(), 2) for f, g in a[a.arranque].groupby("familia")}, " n=", int(a.arranque.sum()))
for rol in ["inocente", "contraste", "ambiente_victima", "ambiente"]:
    g = te[te.rol == rol]
    print(f"  FP {rol:17s} total {pct(g.pred)}  durante {pct(g[g.fase == 'durante'].pred)}  n={len(g)}  marcadas={int(g.pred.sum())}")

print("\n== LATENCIA por corrida de test: primer t desde el que las filas del atacante quedan marcadas >= 95 % en ventanas de 0,5 s")
for fich, g in a.groupby("fichero"):
    g = g.sort_values("ts_ns")
    t = (g.ts_ns - g.ts_ns.min()) / 1e9
    b = (t // 0.5)
    m = g.groupby(b).pred.mean()
    ok = m[m >= 0.95]
    lat = None
    for k in sorted(m.index):
        if (m[m.index >= k] >= 0.95).all():
            lat = k * 0.5
            break
    print(f"  {g.familia.iloc[0]:5s} {g.tasa.iloc[0]:>3s}  latencia_sostenida={lat if lat is not None else 'nunca'} s")

print("\n== importancias por impureza")
for f, v in sorted(zip(FEATS, rf.feature_importances_), key=lambda x: -x[1]):
    print(f"  {f:22s} {v:.4f}")
tep = te[~(te.rol.eq("atacante") & te.arranque)]
pi = permutation_importance(rf, tep[FEATS], tep.etiqueta, scoring="balanced_accuracy",
                            n_repeats=5, random_state=SEED, n_jobs=-1)
print("== importancias por permutación (test sin arranque, balanced_accuracy)")
for i in np.argsort(-pi.importances_mean):
    print(f"  {FEATS[i]:22s} {pi.importances_mean[i]:.4f} ± {pi.importances_std[i]:.4f}")

nodos = sum(e.tree_.node_count for e in rf.estimators_)
prof = max(e.tree_.max_depth for e in rf.estimators_)
print(f"\n== tamaño del bosque: árboles={len(rf.estimators_)} nodos_total={nodos} profundidad_max={prof}")

print("\n== FAMILIA FUERA (sin arranque; recall sobre todas las filas atacante de la familia; FP inocente durante)")
for fam in ATAQUES:
    m = entrenar(tr[tr.familia != fam])
    g = X[(X.familia == fam) & ~X.arranque]
    p = pd.Series(m.predict(g[FEATS]), index=g.index)
    at = g.rol == "atacante"
    ino = (g.rol == "inocente") & (g.fase == "durante")
    por = {tt: round(100 * p[at & (g.tasa == tt)].mean(), 2) for tt in ["30", "60", "100"]}
    print(f"  sin {fam:5s} recall={pct(p[at])} {por}  FP inocente durante={pct(p[ino])}")

print("\n== TASA FUERA (train 30/60 + contrastes bdns, sin arranque; test 100 pps sin arranque)")
tr3 = X[(X.tasa.isin(["30", "60"]) | X.familia.str.startswith("bdns")) & ~X.arranque]
te3 = X[(X.tasa == "100") & ~X.arranque]
m = entrenar(tr3)
p = pd.Series(m.predict(te3[FEATS]), index=te3.index)
at = te3.rol == "atacante"
print("  recall 100 pps:", pct(p[at]), {f: round(100 * p[at & (te3.familia == f)].mean(), 2) for f in ATAQUES})
print("  FP inocente durante:", pct(p[(te3.rol == "inocente") & (te3.fase == "durante")]))

print("\n== SONDA sobre test sin arranque (atacante y inocente durante): % marcado ataque")
base = te[((te.rol == "atacante") & ~te.arranque) | ((te.rol == "inocente") & (te.fase == "durante"))]
for nombre, fn in [("original", lambda z: z),
                   ("victim_pps x0.1", lambda z: z.assign(victim_pps=z.victim_pps * 0.1)),
                   ("victim_pps x0.25", lambda z: z.assign(victim_pps=z.victim_pps * 0.25)),
                   ("victim_pps x0.5", lambda z: z.assign(victim_pps=z.victim_pps * 0.5)),
                   ("victim_pps x2", lambda z: z.assign(victim_pps=z.victim_pps * 2)),
                   ("victim_pps x4", lambda z: z.assign(victim_pps=z.victim_pps * 4)),
                   ("ratio=1 (víctima fría)", lambda z: z.assign(victim_rate_ratio=1.0)),
                   ("ratio=1 y pps=10 (sin ataque)", lambda z: z.assign(victim_rate_ratio=1.0, victim_pps=10.0))]:
    z = fn(base.copy())
    p = pd.Series(rf.predict(z[FEATS]), index=z.index)
    r = {f: round(100 * p[(z.rol == "atacante") & (z.familia == f)].mean(), 1) for f in ATAQUES}
    print(f"  {nombre:30s} atacante {r}  inocente {pct(p[z.rol == 'inocente'])}")

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
