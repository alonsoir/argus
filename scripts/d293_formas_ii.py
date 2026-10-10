#!/usr/bin/env python3
"""DAY293 bloque 1b-ii — (1) árboles factorizados del split D2 en texto; (2) familia fuera (train sin las 3 corridas de la
familia, test = esas 3 corridas enteras) para plano_rf, fact_rf y fact_arbol_dD; (3) sonda de encapsulación sobre D2
(mean_packet_size + delta en TODO el test). Etapa 1 = victim_rate_ratio >= K; etapa 2 sin el ratio. Arranque fuera del train."""
import argparse
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier, export_text

ap = argparse.ArgumentParser()
ap.add_argument("--cons", default="/vagrant/logs/lab/day292/consolidado_caliente.csv")
ap.add_argument("--k", type=float, default=3.0)
ap.add_argument("--profundidades", default="2,3,4")
ap.add_argument("--rf-seeds", default="42,7,1234")
ap.add_argument("--deltas", default="0,4,24,78")
a = ap.parse_args()

R = "victim_rate_ratio"
F7 = ["syn_ack_ratio", "mean_packet_size", "reflection_signature", "packet_size_entropy",
      "flow_packet_count", "flow_completion_rate", R]
FLUJO = [f for f in F7 if f != R]
ATAQUES = ["ntp", "dns", "syn", "udpA", "udpB"]
STR = {"tasa": str, "fichero": str, "community_id": str, "src_ip": str, "dst_ip": str}
PROF = [int(x) for x in a.profundidades.split(",")]
SEEDS = [int(x) for x in a.rf_seeds.split(",")]
FORMAS = [("plano_rf", SEEDS), ("fact_rf", SEEDS)] + [("fact_arbol_d%d" % d, [42]) for d in PROF]


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


def entrenar(forma, s, tr):
    c = RandomForestClassifier(random_state=s, n_jobs=-1) if forma.endswith("_rf") else \
        DecisionTreeClassifier(max_depth=int(forma.rsplit("_d", 1)[1]), random_state=s)
    if forma.startswith("plano"):
        c.fit(tr[F7], tr.etiqueta, sample_weight=pesos(tr)); return ("plano", c)
    tr1 = tr[tr[R] >= a.k]
    c.fit(tr1[FLUJO], tr1.etiqueta, sample_weight=pesos(tr1)); return ("fact", c)


def predecir(mod, te):
    kind, c = mod
    if kind == "plano":
        return c.predict(te[F7])
    pred = np.zeros(len(te), dtype=int)
    m1 = (te[R] >= a.k).values
    if m1.any():
        pred[m1] = c.predict(te[m1][FLUJO])
    return pred


def linea(te, pred):
    te = te.assign(pred=pred)
    at = te[te.rol == "atacante"]
    ino = te[te.rol == "inocente"]
    ind = ino[ino.fase == "durante"]
    av = te[te.rol == "ambiente_victima"]
    f = lambda s: "%7.2f" % (100 * s.mean()) if len(s) else "    n/a"
    return "%s %s %s %s %s" % (f(at[~at.arranque].pred), f(at[at.arranque].pred), f(ino.pred), f(ind.pred), f(av.pred))


X = pd.read_csv(a.cons, dtype=STR)
X["arranque"] = X.arranque.astype(str) == "True"
trD2 = X[(X.split == "train") & ~X.arranque]
teD2 = X[X.split == "test"]

print("# (1) ÁRBOLES FACTORIZADOS (split D2, etapa 2 entrenada con ratio >= %.2f)" % a.k)
for d in PROF:
    kind, c = entrenar("fact_arbol_d%d" % d, 42, trD2)
    print("\n--- fact_arbol_d%d (%d nodos)" % (d, c.tree_.node_count))
    print(export_text(c, feature_names=FLUJO, decimals=3))

HDR = "recall_fuera recall_arranque fp_inocente fp_inocente_durante fp_ambiente_victima (en %)"
print("\n# (2) FAMILIA FUERA: train sin la familia; test = sus 3 corridas enteras\n   familia forma semilla | " + HDR)
for fam in ATAQUES:
    tr = X[(X.familia != fam) & ~X.arranque]
    te = X[X.familia == fam]
    for forma, seeds in FORMAS:
        for s in seeds:
            print("   %-5s %-15s %5d | %s" % (fam, forma, s, linea(te, predecir(entrenar(forma, s, tr), te))), flush=True)

print("\n# (3) ENCAPSULACIÓN sobre D2: mean_packet_size + delta en todo el test\n   forma semilla delta | " + HDR)
for forma, seeds in FORMAS:
    mod = entrenar(forma, seeds[0], trD2)
    for dl in [int(x) for x in a.deltas.split(",")]:
        te = teD2.copy()
        te["mean_packet_size"] = te["mean_packet_size"].astype(float) + dl
        print("   %-15s %5d %4d | %s" % (forma, seeds[0], dl, linea(te, predecir(mod, te))), flush=True)
