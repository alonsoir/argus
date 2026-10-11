#!/usr/bin/env python3
"""DAY293 bloque 1b-i — forma del modelo sobre los MISMOS splits por corrida que d293_intervalos.py (mismo generador y semilla).
Salud: AUC de cada rasgo solo (max(auc, 1-auc)) sobre el consolidado fuera del arranque.
Formas: plano_rf (= B-sinpps), plano_arbol_dD, regla (victim_rate_ratio >= K), fact_rf, fact_arbol_dD.
Factorizado: etapa 1 = victim_rate_ratio >= K (K = K_in de la histéresis, global y declarado); etapa 2 = clasificador entrenado
SOLO con las filas de train que pasan la etapa 1, con los rasgos de flujo (sin el ratio). Arranque del atacante fuera del train;
en test se mide fuera y dentro del arranque. Puerta: recall fuera >= 99 % y FP inocente/contraste = 0 en el split."""
import argparse, time
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import roc_auc_score

ap = argparse.ArgumentParser()
ap.add_argument("--cons", default="/vagrant/logs/lab/day292/consolidado_caliente.csv")
ap.add_argument("--n-splits", type=int, default=60)
ap.add_argument("--seed-splits", type=int, default=2026)
ap.add_argument("--rf-seeds", default="42,7,1234")
ap.add_argument("--k", type=float, default=3.0)
ap.add_argument("--profundidades", default="2,3,4")
ap.add_argument("--salida", default="/vagrant/logs/lab/day293/formas.tsv")
a = ap.parse_args()

R = "victim_rate_ratio"
F7 = ["syn_ack_ratio", "mean_packet_size", "reflection_signature", "packet_size_entropy",
      "flow_packet_count", "flow_completion_rate", R]
FLUJO = [f for f in F7 if f != R]
ATAQUES = ["ntp", "dns", "syn", "udpA", "udpB"]
STR = {"tasa": str, "fichero": str, "community_id": str, "src_ip": str, "dst_ip": str}
ROLES_FP = ["inocente", "contraste", "ambiente_victima", "ambiente"]
PROF = [int(x) for x in a.profundidades.split(",")]
SEEDS = [int(x) for x in a.rf_seeds.split(",")]


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


def nodos(c):
    return sum(e.tree_.node_count for e in c.estimators_) if hasattr(c, "estimators_") else c.tree_.node_count


X = pd.read_csv(a.cons, dtype=STR)
X["arranque"] = X.arranque.astype(str) == "True"

print("# SALUD: AUC de un rasgo solo (max(auc,1-auc)), consolidado fuera del arranque")
base = X[~X.arranque]
for f in F7 + ["victim_pps"]:
    auc = roc_auc_score(base.etiqueta.astype(int), base[f].astype(float))
    print("   %-22s %.4f%s" % (f, max(auc, 1 - auc), "   <-- > 0,9" if max(auc, 1 - auc) > 0.9 else ""))

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


def desc(t):
    r = runs[runs.fichero.isin(t)]
    return " ".join("%s%s" % (f, ta) for f, ta in sorted(zip(r.familia, r.tasa)))


FORMAS = [("plano_rf", SEEDS)] + [("plano_arbol_d%d" % d, [42]) for d in PROF] + [("regla", [0])] + \
         [("fact_rf", SEEDS)] + [("fact_arbol_d%d" % d, [42]) for d in PROF]


def clf_de(forma, s):
    if forma.endswith("_rf"):
        return RandomForestClassifier(random_state=s, n_jobs=-1)
    return DecisionTreeClassifier(max_depth=int(forma.rsplit("_d", 1)[1]), random_state=s)


cols = ["split", "test", "forma", "seed", "recall_fuera", "recall_arranque", "fp_inocente", "fp_inocente_durante",
        "fp_contraste", "fp_ambiente_victima", "fp_ambiente", "nodos", "fit_s"]
filas = []
with open(a.salida, "w") as out:
    out.write("\t".join(cols) + "\n")
    for sid, tset in splits:
        te = X[X.fichero.isin(tset)]
        tr = X[~X.fichero.isin(tset) & ~X.arranque]
        tr1 = tr[tr[R] >= a.k]
        w_tr, w_tr1 = pesos(tr), pesos(tr1)
        m1 = (te[R] >= a.k).values
        for forma, seeds in FORMAS:
            for s in seeds:
                t0 = time.time()
                if forma == "regla":
                    pred, nn = m1.astype(int), 0
                elif forma.startswith("plano"):
                    c = clf_de(forma, s); c.fit(tr[F7], tr.etiqueta, sample_weight=w_tr)
                    pred, nn = c.predict(te[F7]), nodos(c)
                else:
                    c = clf_de(forma, s); c.fit(tr1[FLUJO], tr1.etiqueta, sample_weight=w_tr1)
                    pred = np.zeros(len(te), dtype=int)
                    if m1.any():
                        pred[m1] = c.predict(te[m1][FLUJO])
                    nn = nodos(c)
                r = medir(te, pred)
                r.update(split=sid, test=desc(tset), forma=forma, seed=s, nodos=nn, fit_s=round(time.time() - t0, 1))
                filas.append(r)
                out.write("\t".join(("%.4f" % r[c]) if isinstance(r[c], float) else str(r[c]) for c in cols) + "\n")
        out.flush()
        print("hecho", sid, flush=True)

D = pd.DataFrame(filas)
D["puerta"] = (D.recall_fuera >= 0.99) & (D.fp_inocente == 0) & (D.fp_contraste == 0)
print("\n# RESUMEN (61 splits, todas las semillas): min / mediana / max en %; puerta = recall fuera >= 99 % y FP inocente/contraste = 0")
met = ["recall_fuera", "recall_arranque", "fp_inocente", "fp_inocente_durante", "fp_contraste", "fp_ambiente_victima", "fp_ambiente"]
for forma, _ in FORMAS:
    g = D[D.forma == forma]
    print("%s  filas=%d  pasan_puerta=%d/%d  nodos %d/%d/%d" % (forma, len(g), int(g.puerta.sum()), len(g),
          g.nodos.min(), int(g.nodos.median()), g.nodos.max()))
    for c in met:
        v = 100 * g[c].dropna()
        print("   %-20s %7.2f %7.2f %7.2f" % (c, v.min(), v.median(), v.max()))
