#!/usr/bin/env python3
# DAY292 — filas mal clasificadas en test por el modelo caliente: FP de contraste y atacantes no detectados.
import joblib, pandas as pd
D = "/vagrant/logs/lab/day292"
FEATS = ["syn_ack_ratio", "mean_packet_size", "reflection_signature", "packet_size_entropy",
         "flow_packet_count", "flow_completion_rate", "victim_rate_ratio", "victim_pps"]
rf = joblib.load(f"{D}/ddos_v2_rf_caliente.joblib")
X = pd.read_csv(f"{D}/consolidado_caliente.csv", dtype={"tasa": str, "fichero": str, "community_id": str})
te = X[X.split == "test"].copy()
te["pred"] = rf.predict(te[FEATS])
te["prob"] = rf.predict_proba(te[FEATS])[:, 1]
t0 = te[te.rol.isin(["atacante", "contraste"])].groupby("fichero").ts_ns.min()
te["t_s"] = (te.ts_ns - te.fichero.map(t0)) / 1e9
pd.set_option("display.width", 220)
cols = ["familia", "tasa", "t_s", "prob"] + FEATS
fp = te[(te.rol == "contraste") & (te.pred == 1)]
print(f"== FP contraste: {len(fp)}")
print(fp[cols].round(3).to_string(index=False))
fn = te[(te.rol == "atacante") & (te.pred == 0)]
print(f"\n== atacantes no detectados: {len(fn)}  por familia y segundo (t_s redondeado hacia abajo)")
print(fn.groupby(["familia", (fn.t_s // 1).astype(int)]).size().to_string())
print("\n== muestra de no detectados (10 primeros por familia)")
print(fn.groupby("familia").head(10)[cols].round(3).to_string(index=False))
