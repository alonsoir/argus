#!/usr/bin/env python3
"""DAY293 bloque 1a — intervalos de A, B y B-sinpps con varios splits POR CORRIDA (fichero) y varias semillas del bosque.
Split 0 = el D2 de DAY292 (columna split del consolidado): debe reproducir DAY292 (paridad); si no, PARAR.
Splits 1..N: por cada familia de ataque UNA tasa al azar a test y UNA corrida de contraste al azar a test; el resto a train.
Mismo RF que day292_entrenar*.py (por defecto de sklearn, sin scaler, pesos jerárquicos). B y B-sinpps sin el arranque del
atacante en train (D4); en test siempre se mide fuera y dentro del arranque."""
import argparse, time, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier

ap = argparse.ArgumentParser()
ap.add_argument("--cons", default="/vagrant/logs/lab/day292/consolidado_caliente.csv")
ap.add_argument("--n-splits", type=int, default=12)
ap.add_argument("--seed-splits", type=int, default=2026)
ap.add_argument("--rf-seeds", default="42")
ap.add_argument("--modelos", default="A,B,Bsinpps")
ap.add_argument("--salida", default="/vagrant/logs/lab/day293/intervalos.tsv")
a = ap.parse_args()

F7 = ["syn_ack_ratio", "mean_packet_size", "reflection_signature", "packet_size_entropy",
      "flow_packet_count", "flow_completion_rate", "victim_rate_ratio"]
MODELOS = {"A": (F7 + ["victim_pps"], False), "B": (F7 + ["victim_pps"], True), "Bsinpps": (F7, True)}
ATAQUES = ["ntp", "dns", "syn", "udpA", "udpB"]
STR = {"tasa": str, "fichero": str, "community_id": str, "src_ip": str, "dst_ip": str}
ROLES_FP = ["inocente", "contraste", "ambiente_victima", "ambiente"]


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


def medir(te, pred):
    te = te.assign(pred=pred)
    at = te[te.rol == "atacante"]
    r = {"recall_fuera": at[~at.arranque].pred.mean(),
         "recall_arranque": at[at.arranque].pred.mean() if at.arranque.any() else float("nan")}
    for rol in ROLES_FP:
        g = te[te.rol == rol]
        r["fp_" + rol] = g.pred.mean() if len(g) else float("nan")
    g = te[(te.rol == "inocente") & (te.fase == "durante")]
    r["fp_inocente_durante"] = g.pred.mean() if len(g) else float("nan")
    return r


print("sklearn", sklearn.__version__, " sha consolidado", sha(a.cons)[:8])
X = pd.read_csv(a.cons, dtype=STR)
if "arranque" not in X.columns:
    raise SystemExit("PARAR: el consolidado no tiene columna 'arranque'")
X["arranque"] = X.arranque.astype(str) == "True"

for col in ["familia", "tasa", "split"]:
    n = X.groupby("fichero")[col].nunique()
    if (n > 1).any():
        raise SystemExit("PARAR: %s no es único por fichero: %s" % (col, list(n[n > 1].index)))
runs = X.groupby("fichero")[["familia", "tasa", "split"]].first().reset_index()
print("\n# CORRIDAS (fichero, familia, tasa, split D2)")
print(runs.to_string(index=False))
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


def desc(t):
    r = runs[runs.fichero.isin(t)]
    return " ".join("%s%s" % (f, ta) for f, ta in sorted(zip(r.familia, r.tasa)))


cols = ["split", "test", "modelo", "rf_seed", "recall_fuera", "recall_arranque", "fp_inocente", "fp_inocente_durante",
        "fp_contraste", "fp_ambiente_victima", "fp_ambiente", "nodos", "fit_s"]
filas = []
with open(a.salida, "w") as out:
    out.write("\t".join(cols) + "\n")
    print("\n# RESULTADOS POR SPLIT\n" + "\t".join(cols), flush=True)
    for sid, tset in splits:
        te = X[X.fichero.isin(tset)]
        trall = X[~X.fichero.isin(tset)]
        for m in a.modelos.split(","):
            feats, sin_arr = MODELOS[m]
            tr = trall[~trall.arranque] if sin_arr else trall
            for s in [int(x) for x in a.rf_seeds.split(",")]:
                t0 = time.time()
                rf = RandomForestClassifier(random_state=s, n_jobs=-1)
                rf.fit(tr[feats], tr.etiqueta, sample_weight=pesos(tr))
                r = medir(te, rf.predict(te[feats]))
                r.update(split=sid, test=desc(tset), modelo=m, rf_seed=s,
                         nodos=sum(e.tree_.node_count for e in rf.estimators_), fit_s=round(time.time() - t0, 1))
                filas.append(r)
                line = "\t".join(("%.4f" % r[c]) if isinstance(r[c], float) else str(r[c]) for c in cols)
                out.write(line + "\n"); out.flush(); print(line, flush=True)

R = pd.DataFrame(filas)
print("\n# RESUMEN sobre splits aleatorios (sin D2): min / mediana / max  (en %)")
met = ["recall_fuera", "recall_arranque", "fp_inocente", "fp_inocente_durante", "fp_contraste", "fp_ambiente_victima", "fp_ambiente"]
for m, g in R[R.split != "D2"].groupby("modelo"):
    print(m, " n=%d" % len(g))
    for c in met:
        v = 100 * g[c].dropna()
        if len(v):
            print("   %-20s %7.2f %7.2f %7.2f" % (c, v.min(), v.median(), v.max()))
    print("   %-20s %7d %7d %7d" % ("nodos", g.nodos.min(), int(g.nodos.median()), g.nodos.max()))
