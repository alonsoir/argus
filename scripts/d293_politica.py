#!/usr/bin/env python3
"""DAY293 bloque 1c — simulación offline de la política del firewall POR VÍCTIMA (sombra) sobre las 19 corridas calientes.
Predicción por fila: modelo factorizado (etapa 1 victim_rate_ratio >= K; etapa 2 RF sobre rasgos de flujo, entrenado solo con
filas de train bajo presión), LEAVE-ONE-RUN-OUT (cada corrida predicha por un modelo que no la vio). --delta suma bytes a
mean_packet_size en la entrada de la etapa 2 (sonda de encapsulación).
Víctima = clave {dst_ip, proto}; ventanas de 1 s desde la primera fila de la corrida. Ventana positiva si marcadas >= m.
Bloqueo (sombra) si k positivas en las últimas n; se suelta tras 'hold' ventanas sin positiva.
Evento verdadero: en la clave del atacante y empezando dentro del intervalo del ataque. Cualquier otro evento es FALSO."""
import argparse, itertools
from collections import deque
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

ap = argparse.ArgumentParser()
ap.add_argument("--cons", default="/vagrant/logs/lab/day292/consolidado_caliente.csv")
ap.add_argument("--k-ratio", type=float, default=3.0)
ap.add_argument("--seed", type=int, default=42)
ap.add_argument("--delta", type=float, default=0.0)
ap.add_argument("--m", default="1,2,5,10")
ap.add_argument("--kn", default="1/1,2/3,3/3,3/5,5/5")
ap.add_argument("--hold", default="5,30")
ap.add_argument("--salida", default="/vagrant/logs/lab/day293/politica.tsv")
a = ap.parse_args()

R = "victim_rate_ratio"
F7 = ["syn_ack_ratio", "mean_packet_size", "reflection_signature", "packet_size_entropy",
      "flow_packet_count", "flow_completion_rate", R]
FLUJO = [f for f in F7 if f != R]
ATAQUES = ["ntp", "dns", "syn", "udpA", "udpB"]
STR = {"tasa": str, "fichero": str, "community_id": str, "src_ip": str, "dst_ip": str}


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
X["pred"] = 0
for f in sorted(X.fichero.unique()):
    tr = X[(X.fichero != f) & ~X.arranque]
    tr1 = tr[tr[R] >= a.k_ratio]
    c = RandomForestClassifier(random_state=a.seed, n_jobs=-1)
    c.fit(tr1[FLUJO], tr1.etiqueta, sample_weight=pesos(tr1))
    idx = X.index[X.fichero == f]
    te = X.loc[idx]
    m1 = (te[R] >= a.k_ratio).values
    p = np.zeros(len(te), dtype=int)
    if m1.any():
        Z = te[m1][FLUJO].copy()
        Z["mean_packet_size"] = Z["mean_packet_size"].astype(float) + a.delta
        p[m1] = c.predict(Z)
    X.loc[idx, "pred"] = p
    print("predicha", f, flush=True)

pc = lambda s: "%.2f" % (100 * s.mean()) if len(s) else "n/a"
at = X[X.rol == "atacante"]
ind = X[(X.rol == "inocente") & (X.fase == "durante")]
print("\n# POR FILA (leave-one-run-out, delta=%g): recall fuera %s  recall arranque %s  FP inocente %s  FP inocente durante %s"
      "  FP contraste %s  FP ambiente_victima %s  FP ambiente %s" % (
          a.delta, pc(at[~at.arranque].pred), pc(at[at.arranque].pred), pc(X[X.rol == "inocente"].pred), pc(ind.pred),
          pc(X[X.rol == "contraste"].pred), pc(X[X.rol == "ambiente_victima"].pred), pc(X[X.rol == "ambiente"].pred)))

runs = []
for f, g in X.groupby("fichero"):
    t0 = g.ts_ns.min()
    g = g.assign(w=((g.ts_ns - t0) // 1_000_000_000).astype(int))
    W = int(g.w.max()) + 1
    atg = g[g.rol == "atacante"]
    if len(atg):
        aw0, aw1, akey = int(atg.w.min()), int(atg.w.max()), (atg.dst_ip.iloc[0], atg.proto.iloc[0])
    else:
        aw0 = aw1 = akey = None
    keys = {}
    for k, gk in g.groupby(["dst_ip", "proto"]):
        arr = np.zeros(W, dtype=int)
        cnt = gk[gk.pred == 1].groupby("w").size()
        if len(cnt):
            arr[cnt.index.values] = cnt.values
            keys[k] = arr
    runs.append(dict(f=f, fam=g.familia.iloc[0], tasa=g.tasa.iloc[0], W=W, aw0=aw0, aw1=aw1, akey=akey, keys=keys))


def sim(arr, m, k, n, hold):
    ev, q, blocked, last_pos, start = [], deque(maxlen=n), False, -10 ** 9, None
    for w, c in enumerate(arr):
        pos = c >= m
        q.append(pos)
        if pos:
            last_pos = w
        if not blocked and sum(q) >= k:
            blocked, start = True, w
        elif blocked and w - last_pos >= hold:
            ev.append((start, w)); blocked = False; q.clear()
    if blocked:
        ev.append((start, len(arr)))
    return ev


cols = ["m", "k_n", "hold", "detectados", "ttb_med_s", "ttb_max_s", "cobertura_min", "cobertura_med", "eventos_falsos",
        "falsos_en_contraste", "residual_med_s"]
res = []
for m, kn, hold in itertools.product([int(x) for x in a.m.split(",")], a.kn.split(","), [int(x) for x in a.hold.split(",")]):
    k, n = [int(x) for x in kn.split("/")]
    det, ttb, cob, resid, falsos, falsos_c = 0, [], [], [], 0, 0
    for r in runs:
        tps = []
        for key, arr in r["keys"].items():
            for (s0, s1) in sim(arr, m, k, n, hold):
                if r["akey"] is not None and key == r["akey"] and r["aw0"] <= s0 <= r["aw1"]:
                    tps.append((s0, s1))
                else:
                    falsos += 1
                    if r["fam"] not in ATAQUES:
                        falsos_c += 1
        if r["akey"] is not None:
            if tps:
                det += 1
                ttb.append(min(s0 for s0, _ in tps) - r["aw0"] + 1)
                bl = set()
                for s0, s1 in tps:
                    bl.update(range(s0, s1))
                dur = r["aw1"] - r["aw0"] + 1
                cob.append(100.0 * len([w for w in range(r["aw0"], r["aw1"] + 1) if w in bl]) / dur)
                resid.append(max(s1 for _, s1 in tps) - r["aw1"] - 1)
            else:
                cob.append(0.0)
    natk = sum(1 for r in runs if r["akey"] is not None)
    res.append(dict(m=m, k_n=kn, hold=hold, detectados="%d/%d" % (det, natk),
                    ttb_med_s=float(np.median(ttb)) if ttb else float("nan"), ttb_max_s=max(ttb) if ttb else float("nan"),
                    cobertura_min=min(cob), cobertura_med=float(np.median(cob)), eventos_falsos=falsos,
                    falsos_en_contraste=falsos_c, residual_med_s=float(np.median(resid)) if resid else float("nan")))

D = pd.DataFrame(res)[cols]
D.to_csv(a.salida, sep="\t", index=False)
print("\n# POLÍTICA POR VÍCTIMA (sombra), delta=%g — ttb en s (±1 s por ventana), cobertura en %%" % a.delta)
print(D.to_string(index=False, float_format=lambda v: "%.1f" % v))
