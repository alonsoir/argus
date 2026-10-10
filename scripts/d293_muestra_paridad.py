#!/usr/bin/env python3
"""DAY293 — muestra fija del CSV de paridad para el ctest: filas de etapa 1 cerca de la frontera (|p1-p0| < 0,3),
3000 de etapa 1 al azar y 1000 sin etapa 1 (random_state=42)."""
import pandas as pd
P = pd.read_csv("/vagrant/logs/lab/day293/ddos_v2_paridad.csv", dtype=str)
e1 = P.etapa1 == "1"
d = (P.p1.astype(float) - P.p0.astype(float)).abs()
cerca = P[e1 & (d < 0.3)]
resto = P[e1].drop(cerca.index)
M = pd.concat([cerca, resto.sample(n=min(3000, len(resto)), random_state=42),
               P[~e1].sample(n=min(1000, int((~e1).sum())), random_state=42)]).sort_index()
out = "/vagrant/ml-detector/tests/data/ddos_v2_paridad_muestra.csv"
M.to_csv(out, index=False)
print("muestra %s: %d filas (cerca de la frontera %d)" % (out, len(M), len(cerca)))
