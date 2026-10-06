#!/usr/bin/env python3
"""DAY289 — reentreno con el contraste benigno (bdns_small / bdns_large) como MEDIDA, no detector.
A: consolidado + contraste, split 70/30 temporal por (fichero, familia), pesos por celda.
B: tasa reservada — bdns_large 20 fuera de train; test = todas sus filas.
C: tasa reservada — bdns_large 5 fuera de train; test = todas sus filas.
Sonda victim_pps (modelo A) sobre bdns_large y sobre dns de ataque. Caliente con el modelo A."""
import hashlib, re, sys
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance

OUT = Path("/vagrant/logs/lab/day289")
CONS = OUT / "consolidado.csv"
REG = Path("/vagrant/logs/lab/day288/contraste.tsv")
CAL_RUNS = Path("/vagrant/logs/lab/day288/runs_caliente.tsv")
DSDIR = Path("/vagrant/logs/lab/ddos_dataset")
MODELO = OUT / "ddos_v2_rf_contraste.joblib"
FEATS = ["syn_ack_ratio", "mean_packet_size", "reflection_signature", "packet_size_entropy",
         "flow_packet_count", "flow_completion_rate", "victim_rate_ratio", "victim_pps"]
STR = {"tasa": str, "fichero": str, "community_id": str, "src_ip": str, "dst_ip": str}
GRID = [2, 5, 10, 15, 20, 25, 30, 40, 60, 100]
SEED = 42


def parar(msg):
    print("PARAR:", msg)
    sys.exit(1)


def pesos(d):
    w = pd.Series(0.0, index=d.index)
    for etq, dc in d.groupby("etiqueta"):
        celdas = dc.groupby(["familia", "tasa"]).size()
        for (fam, tasa), n in celdas.items():
            m = (d["etiqueta"] == etq) & (d["familia"] == fam) & (d["tasa"] == tasa)
            w[m] = 1.0 / (len(celdas) * n)
    return w * (len(d) / w.sum())


def entrenar(d):
    rf = RandomForestClassifier(random_state=SEED, n_jobs=-1)
    rf.fit(d[FEATS], d["y"], sample_weight=pesos(d))
    return rf


def tabla(d, pred):
    t = (d.assign(nuevo=pred)
          .groupby(["etiqueta", "familia", "tasa"])
          .agg(n=("nuevo", "size"), nuevo=("nuevo", "mean"),
               viejo=("old_ddos_class", lambda s: float((s == 1).mean())))
          .reset_index())
    t["tn"] = pd.to_numeric(t["tasa"], errors="coerce")
    for r in t.sort_values(["etiqueta", "familia", "tn"]).itertuples():
        print(f"  {r.etiqueta:8s} {r.familia:10s} {r.tasa:>4s} n={r.n:5d}  "
              f"nuevo={100*r.nuevo:6.2f}%  viejo={100*r.viejo:6.2f}%")


def sonda(m, X):
    out = []
    for v in GRID:
        Xs = X.copy()
        Xs["victim_pps"] = float(v)
        out.append(f"{v}:{100*(m.predict(Xs[FEATS])).mean():.0f}%")
    return "  ".join(out)


# --- carga
cons = pd.read_csv(CONS, dtype=STR)
partes = []
for linea in REG.read_text().splitlines():
    c = linea.split("\t")
    if len(c) < 3:
        continue
    fam, tasa, fic = c[0], c[1], c[2]
    d = pd.read_csv(DSDIR / fic, dtype=STR)
    d = d[(d.src_ip == "192.168.100.50") & (d.dst_ip == "192.168.100.1") &
          (d.event_kind == 0) & (d.syn_ack_ratio > -9000) & (d.proto == 17)]
    partes.append(d.assign(etiqueta="benigno", familia=fam, tasa=tasa,
                           fichero=fic.replace("ddos_dataset_", "").replace(".csv", "")))
con = pd.concat(partes, ignore_index=True)
if len(cons) != 58564 or len(con) != 6000:
    parar(f"conteos inesperados: consolidado={len(cons)} contraste={len(con)}")
if list(con.columns) != list(cons.columns):
    parar("columnas distintas entre consolidado y contraste")
df = pd.concat([cons, con], ignore_index=True)
if df[FEATS].isna().any().any():
    parar("NaN en rasgos")
df["y"] = (df["etiqueta"] == "ataque").astype(int)
df = df.sort_values(["fichero", "familia", "ts_ns"], kind="mergesort").reset_index(drop=True)
g = df.groupby(["fichero", "familia"])
df["train"] = g.cumcount() < np.floor(0.7 * g["ts_ns"].transform("size"))
tr, te = df[df["train"]], df[~df["train"]]
print(f"A: train={len(tr)} test={len(te)}  (contraste en train={int(tr.familia.str.startswith('bdns').sum())})")

# --- A
rfA = entrenar(tr)
print(f"bosque A: {sum(e.tree_.node_count for e in rfA.estimators_)} nodos, "
      f"profundidad máx {max(e.tree_.max_depth for e in rfA.estimators_)}")
pA = rfA.predict(te[FEATS])
print("\n== A TEST: % marcado ataque (ataque = recall; benigno = FP) ==")
tabla(te, pA)
pa = (te["y"] == 1).values
print(f"  GLOBAL recall={100*pA[pa].mean():.2f}%  FP={100*pA[~pa].mean():.2f}%")
print("\n== A importancias por impureza ==")
for f, v in pd.Series(rfA.feature_importances_, FEATS).sort_values(ascending=False).items():
    print(f"  {f:22s} {v:.4f}")
pi = permutation_importance(rfA, te[FEATS], te["y"], scoring="balanced_accuracy",
                            n_repeats=5, random_state=SEED, n_jobs=-1)
print("\n== A importancias por permutación (test, balanced_accuracy) ==")
for i in np.argsort(-pi.importances_mean):
    print(f"  {FEATS[i]:22s} {pi.importances_mean[i]:.4f} ± {pi.importances_std[i]:.4f}")
print("\n== A sonda victim_pps → % marcado ataque (filas de test) ==")
for fam, tasa in [("bdns_large", "5"), ("bdns_large", "10"), ("bdns_large", "20"),
                  ("bdns_small", "10"), ("dns", "30"), ("dns", "100"), ("ntp", "30")]:
    X = te[(te.familia == fam) & (te.tasa == tasa)]
    print(f"  {fam:10s} {tasa:>3s}  {sonda(rfA, X)}")

# --- B y C: tasa reservada
for etiqueta, reservada in [("B", "20"), ("C", "5")]:
    fuera = (df.familia == "bdns_large") & (df.tasa == reservada)
    m = entrenar(tr[~fuera[tr.index]])
    Xh = df[fuera]
    ph = m.predict(Xh[FEATS])
    pr = m.predict(te[~fuera[te.index]][FEATS])
    yr = (te[~fuera[te.index]]["y"] == 1).values
    print(f"\n== {etiqueta}: bdns_large {reservada} pps fuera de train ==")
    print(f"  FP sobre sus {len(Xh)} filas = {100*ph.mean():.2f}%   resto del test: "
          f"recall={100*pr[yr].mean():.2f}% FP={100*pr[~yr].mean():.2f}%")
    print(f"  sonda sobre sus filas: {sonda(m, Xh)}")

# --- caliente con A
print("\n== A CALIENTE: % marcado ataque, total y por tercio ==")
for linea in CAL_RUNS.read_text().splitlines():
    st = re.findall(r"\b\d{6}\b", linea)
    if not st:
        continue
    fam, tasa = linea.split()[:2]
    c = pd.read_csv(DSDIR / f"ddos_dataset_20261005-{st[0]}.csv", dtype=STR)
    c = c[(c.src_ip == "192.168.100.50") & (c.dst_ip == "192.168.100.1") &
          (c.event_kind == 0) & (c.syn_ack_ratio > -9000) & (c.proto == 6)]
    if fam == "benignhot":
        c = c[c.dst_port == 9000]
    c = c.sort_values("ts_ns")
    p = rfA.predict(c[FEATS])
    print(f"  {fam:9s} {tasa:>4s} n={len(c)}  nuevo={100*p.mean():6.2f}%  tercios="
          + "/".join(f"{100*x.mean():.1f}%" for x in np.array_split(p, 3)))

joblib.dump(rfA, MODELO)
h = hashlib.sha256(MODELO.read_bytes()).hexdigest()
(OUT / "modelo_contraste.sha256").write_text(f"{h}  {MODELO}\n")
print(f"\nmodelo A: {MODELO}\n{h}")
