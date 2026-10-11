#!/usr/bin/env python3
"""DAY293 — riesgo de redondeo %.6g del consolidado frente a los umbrales del .hpp generado (cabeza DDoS v2 factorizada).
(1) Parsea el .hpp desde el TEXTO y lo evalúa (numpy, orden de árbol 0..n-1); exige igualdad exacta con p1/clase del CSV.
(2) Para cada fila de la etapa 1 y cada rasgo: intervalo del valor verdadero = texto ± 0,5·10^(e-5) (6 cifras significativas;
    0 exacto si el texto es 0) + margen float32. En riesgo si algún umbral del rasgo cae dentro.
(3) Para las filas en riesgo: lleva cada rasgo en riesgo a los dos extremos de su intervalo y cuenta si la CLASE cambia."""
import argparse, re
import numpy as np
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--hpp", default="/vagrant/logs/lab/day293/ddos_v2_forest_inline.hpp")
ap.add_argument("--paridad", default="/vagrant/logs/lab/day293/ddos_v2_paridad.csv")
a = ap.parse_args()
FLUJO = ["syn_ack_ratio", "mean_packet_size", "reflection_signature", "packet_size_entropy",
         "flow_packet_count", "flow_completion_rate"]

txt = open(a.hpp).read()
trees = []
for m in re.finditer(r"inline constexpr Node tree_(\d+)\[\] = \{\n(.*?)\n\};", txt, re.S):
    rows = re.findall(r"\{(-?\d+), ([^,]+), (-?\d+), (-?\d+), ([^,]+), ([^}]+)\}", m.group(2))
    f, t, l, r, p0, p1 = zip(*rows)
    trees.append(dict(f=np.array(f, int), t=np.array(t, float), l=np.array(l, int), r=np.array(r, int),
                      p0=np.array(p0, float), p1=np.array(p1, float)))
print("árboles parseados %d, nodos %d" % (len(trees), sum(len(t["f"]) for t in trees)))


def evalua(X):
    s0 = np.zeros(len(X)); s1 = np.zeros(len(X))
    rows = np.arange(len(X))
    for T in trees:
        idx = np.zeros(len(X), dtype=int)
        while True:
            internos = T["f"][idx] >= 0
            if not internos.any():
                break
            f = np.where(internos, T["f"][idx], 0)
            izq = X[rows, f] <= T["t"][idx]
            idx = np.where(internos, np.where(izq, T["l"][idx], T["r"][idx]), idx)
        s0 += T["p0"][idx]; s1 += T["p1"][idx]
    n = len(trees)
    return s0 / n, s1 / n


P = pd.read_csv(a.paridad, dtype=str)
e1 = P.etapa1.astype(int).values == 1
D = P[e1].reset_index(drop=True)
txtv = D[FLUJO].values
X = np.column_stack([D[c].astype(np.float32).values.astype(np.float64) for c in FLUJO])
p0, p1 = evalua(X)
clase = (p1 > p0).astype(int)
print("Y1 p1 exacta: %d/%d   clase igual: %d/%d" % (int((p1 == D.p1.astype(float).values).sum()), len(D),
                                                    int((clase == D.clase.astype(int).values).sum()), len(D)))

V = np.column_stack([D[c].astype(np.float64).values for c in FLUJO])
with np.errstate(divide="ignore"):
    e = np.floor(np.log10(np.abs(V)))
half = np.where(V == 0, 0.0, 0.5 * 10.0 ** (e - 5)) + np.abs(V) * 6e-8
riesgo = np.zeros(V.shape, dtype=bool)
for j in range(len(FLUJO)):
    ths = np.unique(np.concatenate([T["t"][T["f"] == j] for T in trees]))
    if not len(ths):
        continue
    i = np.clip(np.searchsorted(ths, V[:, j]), 1, len(ths) - 1)
    d = np.minimum(np.abs(V[:, j] - ths[i - 1]), np.abs(V[:, j] - ths[i]))
    riesgo[:, j] = d <= half[:, j]
fil = riesgo.any(axis=1)
print("Y2 filas en riesgo (intervalo preciso): %d de %d en etapa 1;  por rasgo: %s" % (
    int(fil.sum()), len(D), ", ".join("%s=%d" % (c, int(riesgo[:, j].sum())) for j, c in enumerate(FLUJO))))

cambia = np.zeros(len(D), dtype=bool)
for j in range(len(FLUJO)):
    sel = np.where(riesgo[:, j])[0]
    if not len(sel):
        continue
    for signo in (-1.0, 1.0):
        Xv = X[sel].copy()
        Xv[:, j] = (V[sel, j] + signo * half[sel, j]).astype(np.float32).astype(np.float64)
        q0, q1 = evalua(Xv)
        cambia[sel] |= ((q1 > q0).astype(int) != clase[sel])
print("Y3 filas cuya clase CAMBIA en algún extremo: %d" % int(cambia.sum()))
if cambia.any():
    print(D[cambia].head(20).to_string())
