#!/usr/bin/env python3
"""DAY289 — primer entrenamiento (PROVISIONAL) de la cabeza DDoS sobre el contrato v2.
Solo lectura de consolidado.csv y de los CSV calientes. RF random_state=42, sin scaler.
Balance por pesos: cada celda (etiqueta, familia, tasa) pesa igual dentro de su clase y las dos
clases pesan igual. Split 70/30 por ts_ns dentro de cada (fichero, familia).
Salidas en /vagrant/logs/lab/day289/: ddos_v2_rf_provisional.joblib + modelo.sha256."""
import hashlib, re, sys
from pathlib import Path
import numpy as np
import pandas as pd
import joblib, sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance

OUT = Path("/vagrant/logs/lab/day289")
CONS = OUT / "consolidado.csv"
CAL_RUNS = Path("/vagrant/logs/lab/day288/runs_caliente.tsv")
DSDIR = Path("/vagrant/logs/lab/ddos_dataset")
MODELO = OUT / "ddos_v2_rf_provisional.joblib"
FEATS = ["syn_ack_ratio", "mean_packet_size", "reflection_signature", "packet_size_entropy",
         "flow_packet_count", "flow_completion_rate", "victim_rate_ratio", "victim_pps"]
ATAQUES = ["ntp", "dns", "syn", "udpA", "udpB"]
STR = {"tasa": str, "fichero": str, "community_id": str, "src_ip": str, "dst_ip": str}
SEED = 42


def parar(msg):
    print("PARAR:", msg)
    sys.exit(1)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


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
        print(f"  {r.etiqueta:8s} {r.familia:9s} {r.tasa:>4s} n={r.n:5d}  "
              f"nuevo={100*r.nuevo:6.2f}%  viejo={100*r.viejo:6.2f}%")


print(f"versiones: sklearn {sklearn.__version__} pandas {pd.__version__} numpy {np.__version__}")
df = pd.read_csv(CONS, dtype=STR)
if df[FEATS].isna().any().any():
    parar("NaN en rasgos")
cnt = {k: int(v) for k, v in df["etiqueta"].value_counts().items()}
if cnt != {"ataque": 39165, "benigno": 19399}:
    parar(f"conteos inesperados {cnt}")
df["y"] = (df["etiqueta"] == "ataque").astype(int)

# --- split temporal 70/30 dentro de cada (fichero, familia)
df = df.sort_values(["fichero", "familia", "ts_ns"], kind="mergesort").reset_index(drop=True)
g = df.groupby(["fichero", "familia"])
df["train"] = g.cumcount() < np.floor(0.7 * g["ts_ns"].transform("size"))
tr, te = df[df["train"]], df[~df["train"]]
print(f"split: train={len(tr)} (ataque {int(tr.y.sum())})  test={len(te)} (ataque {int(te.y.sum())})")

# --- riesgo de extrapolación de flow_packet_count (test por encima del máximo de train)
print("\n== extrapolación flow_packet_count: % de test > máx de train en su grupo (solo >0) ==")
mx = tr.groupby(["fichero", "familia"])["flow_packet_count"].max().rename("mx")
ex = te.join(mx, on=["fichero", "familia"])
ex = ex.assign(fuera=ex["flow_packet_count"] > ex["mx"]).groupby(["familia", "fichero"])["fuera"].mean()
for (fam, fic), v in ex[ex > 0].items():
    print(f"  {fam:9s} {fic}  {100*v:6.2f}%")

# --- modelo principal
rf = entrenar(tr)
nodos = sum(e.tree_.node_count for e in rf.estimators_)
prof = max(e.tree_.max_depth for e in rf.estimators_)
print(f"\nbosque: {len(rf.estimators_)} árboles, {nodos} nodos, profundidad máx {prof}")

pred = rf.predict(te[FEATS])
print("\n== TEST: % marcado ataque (ataque = recall; benigno = FP) — nuevo vs old_ddos_class ==")
tabla(te, pred)
pa = te["y"] == 1
print(f"  GLOBAL recall nuevo={100*pred[pa.values].mean():.2f}% viejo={100*(te.loc[pa,'old_ddos_class']==1).mean():.2f}%")
print(f"  GLOBAL FP     nuevo={100*pred[~pa.values].mean():.2f}% viejo={100*(te.loc[~pa,'old_ddos_class']==1).mean():.2f}%")

print("\n== importancias por impureza ==")
for f, v in pd.Series(rf.feature_importances_, FEATS).sort_values(ascending=False).items():
    print(f"  {f:22s} {v:.4f}")
pi = permutation_importance(rf, te[FEATS], te["y"], scoring="balanced_accuracy",
                            n_repeats=5, random_state=SEED, n_jobs=-1)
print("\n== importancias por permutación (test, balanced_accuracy; media ± std) ==")
for i in np.argsort(-pi.importances_mean):
    print(f"  {FEATS[i]:22s} {pi.importances_mean[i]:.4f} ± {pi.importances_std[i]:.4f}")

# --- dejar una familia fuera
print("\n== dejar una familia fuera: recall sobre TODAS sus filas; FP sobre el benigno de test ==")
for f in ATAQUES:
    m = entrenar(tr[tr["familia"] != f])
    df_f = df[df["familia"] == f]
    p = m.predict(df_f[FEATS])
    fp = m.predict(te.loc[te["etiqueta"] == "benigno", FEATS]).mean()
    por_tasa = "  ".join(f"{t}:{100*p[(df_f['tasa'] == t).values].mean():.1f}%"
                         for t in sorted(df_f["tasa"].unique(), key=int))
    print(f"  sin {f:5s} recall={100*p.mean():6.2f}%  [{por_tasa}]  FP benigno={100*fp:.2f}%")

# --- evaluación en caliente (desplazamiento), aparte
print("\n== CALIENTE (no entrenado): % marcado ataque, total y por tercio temporal ==")
if not CAL_RUNS.is_file():
    parar(f"falta {CAL_RUNS}")
for linea in CAL_RUNS.read_text().splitlines():
    st = re.findall(r"\b\d{6}\b", linea)
    if not st:
        continue
    fam, tasa = linea.split()[:2]
    f = DSDIR / f"ddos_dataset_20261005-{st[0]}.csv"
    if not f.is_file():
        parar(f"falta {f}")
    c = pd.read_csv(f, dtype=STR)
    c = c[(c.src_ip == "192.168.100.50") & (c.dst_ip == "192.168.100.1") &
          (c.event_kind == 0) & (c.syn_ack_ratio > -9000) & (c.proto == 6)]
    if fam == "benignhot":
        c = c[c.dst_port == 9000]
    elif fam != "syn":
        parar(f"familia caliente desconocida: {linea}")
    c = c.sort_values("ts_ns")
    p = rf.predict(c[FEATS])
    ter = np.array_split(p, 3)
    print(f"  {fam:9s} {tasa:>4s} {st[0]} n={len(c)}  nuevo={100*p.mean():6.2f}%  "
          f"viejo={100*(c.old_ddos_class == 1).mean():6.2f}%  tercios="
          + "/".join(f"{100*x.mean():.1f}%" for x in ter))

joblib.dump(rf, MODELO)
(OUT / "modelo.sha256").write_text(f"{sha256(MODELO)}  {MODELO}\n{sha256(CONS)}  {CONS}\n")
print(f"\nmodelo: {MODELO}\n" + (OUT / "modelo.sha256").read_text())
