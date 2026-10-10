#!/usr/bin/env python3
"""DAY293 — exportador de la cabeza DDoS v2 FACTORIZADA (etapa 1: victim_rate_ratio >= K; etapa 2: RandomForest sobre los
6 rasgos de flujo, entrenado SOLO con filas bajo presión; arranque del atacante fuera; pesos jerárquicos de DAY292).
Salidas:
  --hpp     cabecera C++ con los árboles: umbrales y probabilidades de hoja en double (%.17g), SIN escalado (rasgos crudos).
  --paridad CSV para el test C++: los 7 valores de entrada TAL COMO están en el consolidado, etapa 1, p0, p1 y clase de Python.
Convención de paridad (igual que sklearn): el rasgo se convierte a float32 y se compara, promovido a double, contra el umbral
double (x <= t va a la izquierda); p = suma en orden de árbol (0..n-1) de las probabilidades de hoja / n_árboles; clase = 1 si
p1 > p0 (empate -> 0). La etapa 1 compara el ratio en float32 promovido a double con K.
Además cuenta las filas en riesgo de redondeo: el consolidado guarda los rasgos con %.6g (ddos_dataset_writer.hpp)."""
import argparse, hashlib, datetime
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier

ap = argparse.ArgumentParser()
ap.add_argument("--cons", default="/vagrant/logs/lab/day292/consolidado_caliente.csv")
ap.add_argument("--k", type=float, default=3.0)
ap.add_argument("--seed", type=int, default=42)
ap.add_argument("--hpp", default="/vagrant/logs/lab/day293/ddos_v2_forest_inline.hpp")
ap.add_argument("--paridad", default="/vagrant/logs/lab/day293/ddos_v2_paridad.csv")
ap.add_argument("--rel-tol", type=float, default=5e-6)
a = ap.parse_args()

R = "victim_rate_ratio"
FLUJO = ["syn_ack_ratio", "mean_packet_size", "reflection_signature", "packet_size_entropy",
         "flow_packet_count", "flow_completion_rate"]
STR = {"tasa": str, "fichero": str, "community_id": str, "src_ip": str, "dst_ip": str}
STR.update({c: str for c in FLUJO + [R]})


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


X = pd.read_csv(a.cons, dtype=STR)
X["arranque"] = X.arranque.astype(str) == "True"
F32 = {c: X[c].astype(np.float32) for c in FLUJO + [R]}
X1 = (F32[R].astype(np.float64) >= a.k).values
tr = X[X1 & ~X.arranque.values]
Xtr = np.column_stack([F32[c][tr.index].values for c in FLUJO])
rf = RandomForestClassifier(random_state=a.seed, n_jobs=-1)
rf.fit(Xtr, tr.etiqueta.values, sample_weight=pesos(tr).values)
rf.n_jobs = 1
print("sklearn %s  consolidado sha %s  train (bajo presión, sin arranque) = %d filas" % (sklearn.__version__, sha(a.cons)[:8], len(tr)))

# predicción propia (orden de árbol fijo) sobre TODAS las filas
Xall = np.column_stack([F32[c].values for c in FLUJO])
p = np.zeros((len(X), 2))
for est in rf.estimators_:
    t = est.tree_
    leaf = est.apply(Xall)
    v = t.value[leaf, 0, :]
    p += v / v.sum(axis=1, keepdims=True)
p /= len(rf.estimators_)
clase = np.where(X1, (p[:, 1] > p[:, 0]).astype(int), 0)
ref = np.zeros(len(X), dtype=int)
ref[X1] = rf.predict(Xall[X1])
print("X2 autoconsistencia (propia vs rf.predict, filas etapa 1): %d/%d iguales" % (int((clase[X1] == ref[X1]).sum()), int(X1.sum())))

# riesgo de redondeo
riesgo = np.zeros(len(X), dtype=bool)
usados = {}
for est in rf.estimators_:
    t = est.tree_
    for f, thr in zip(t.feature, t.threshold):
        if f >= 0:
            usados.setdefault(int(f), set()).add(float(thr))
for f, ths in usados.items():
    x = Xall[:, f].astype(np.float64)
    ths = np.array(sorted(ths))
    i = np.clip(np.searchsorted(ths, x), 1, len(ths) - 1)
    d = np.minimum(np.abs(x - ths[i - 1]), np.abs(x - ths[i]))
    riesgo |= X1 & (d <= a.rel_tol * np.maximum(np.abs(x), 1.0))
rr = F32[R].values.astype(np.float64)
riesgo_k = np.abs(rr - a.k) <= a.rel_tol * max(abs(a.k), 1.0)
print("X3 filas en riesgo de redondeo: etapa 2 %d, etapa 1 (ratio ~ K) %d, de %d filas (%d en etapa 1)" % (
    int(riesgo.sum()), int(riesgo_k.sum()), len(X), int(X1.sum())))

# cabecera C++
nodos = sum(e.tree_.node_count for e in rf.estimators_)
L = ["// AUTO-GENERATED por ml-training/scripts/ddos_detection/export_ddos_v2_fact_rf.py — NO EDITAR A MANO",
     "// Cabeza DDoS v2 FACTORIZADA, etapa 2 (RandomForest). Etapa 1 (victim_rate_ratio >= K) fuera de este fichero.",
     "// Consolidado sha256 %s; sklearn %s; random_state %d; K de entrenamiento %.17g; %s" % (
         sha(a.cons), sklearn.__version__, a.seed, a.k, datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")),
     "// Árboles %d, nodos %d. Rasgos CRUDOS (sin escalado), en este orden: %s" % (len(rf.estimators_), nodos, ", ".join(FLUJO)),
     "// Paridad con sklearn: x -> float -> double; x <= threshold va a left; p = suma en orden de árbol / kNumTrees; clase 1 si p1 > p0.",
     "#pragma once", "", "#include <cstdint>", "#include <cstddef>", "",
     "namespace ml_defender::ddos_v2 {", "",
     "inline constexpr std::size_t kNumFeatures = %d;" % len(FLUJO),
     "inline constexpr const char* kFeatureNames[kNumFeatures] = {%s};" % ", ".join('"%s"' % f for f in FLUJO),
     "inline constexpr double kTrainK = %.17g;" % a.k, "",
     "struct Node {", "    int16_t feature;   // -2 = hoja", "    double threshold;", "    int32_t left;", "    int32_t right;",
     "    double p0;", "    double p1;", "};", ""]
for i, est in enumerate(rf.estimators_):
    t = est.tree_
    L.append("inline constexpr Node tree_%d[] = {" % i)
    rows = []
    for n in range(t.node_count):
        v = t.value[n, 0, :]
        s = v.sum()
        p0, p1 = (v[0] / s, v[1] / s) if t.children_left[n] == -1 else (0.0, 0.0)
        if t.children_left[n] == -1:
            rows.append("    {-2, 0.0, -1, -1, %.17g, %.17g}" % (p0, p1))
        else:
            rows.append("    {%d, %.17g, %d, %d, 0.0, 0.0}" % (t.feature[n], t.threshold[n], t.children_left[n], t.children_right[n]))
    L.append(",\n".join(rows))
    L.append("};")
L.append("")
L.append("inline constexpr std::size_t kNumTrees = %d;" % len(rf.estimators_))
L.append("inline constexpr const Node* kTrees[kNumTrees] = {%s};" % ", ".join("tree_%d" % i for i in range(len(rf.estimators_))))
L.append("")
L.append("}  // namespace ml_defender::ddos_v2")
with open(a.hpp, "w") as f:
    f.write("\n".join(L) + "\n")
print("X1 hpp %s: %d árboles, %d nodos" % (a.hpp, len(rf.estimators_), nodos))

out = pd.DataFrame({c: X[c] for c in FLUJO + [R]})
out["etapa1"] = X1.astype(int)
out["p0"] = ["%.17g" % v for v in p[:, 0]]
out["p1"] = ["%.17g" % v for v in p[:, 1]]
out["clase"] = clase
out.to_csv(a.paridad, index=False)
print("paridad %s: %d filas (sha %s)" % (a.paridad, len(out), sha(a.paridad)[:8]))
