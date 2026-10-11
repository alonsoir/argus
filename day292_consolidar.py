#!/usr/bin/env python3
"""DAY292 — consolidación de la batería CALIENTE para el reentrenamiento de la cabeza DDoS v2.
Solo lectura sobre las fuentes. Decisiones en logs/lab/day292/decisiones_entrenamiento.txt (D1-D3).
Salidas: consolidado_caliente.csv + manifiesto_caliente.sha256 en logs/lab/day292/."""
import hashlib, os, sys
from pathlib import Path
import pandas as pd

D = Path("/vagrant/logs/lab/day292")
DS = Path("/vagrant/logs/lab/ddos_dataset")
RUNS = D / "runs_caliente.tsv"
OUT = D / "consolidado_caliente.csv"
MAN = D / "manifiesto_caliente.sha256"
FEATS = ["syn_ack_ratio", "mean_packet_size", "reflection_signature", "packet_size_entropy",
         "flow_packet_count", "flow_completion_rate", "victim_rate_ratio", "victim_pps"]
PROTO = {"ntp": 17, "dns": 17, "udpA": 17, "udpB": 17, "syn": 6, "bdns_small": 17, "bdns_large": 17}
ATAQUES = {"ntp", "dns", "udpA", "udpB", "syn"}
TEST = {("ntp", "60"), ("dns", "60"), ("udpA", "60"), ("udpB", "60"), ("syn", "60"), ("bdns_large", "10")}
L, C = "/vagrant/datasets/lab", "/vagrant/datasets/cicddos2019"
PCAPS = [f"{L}/ntp_reflex_10k_lab.pcap", f"{L}/dns_reflex_10k_lab.pcap", f"{L}/syn_flood_10k_lab.pcap",
         f"{C}/_0125_50k_lab.pcap", f"{C}/_0220_50k_lab.pcap", f"{L}/benign_dns_ntp_small_5k_lab_src51.pcap",
         f"{L}/benign_dns_ntp_small_5k_lab.pcap", f"{L}/benign_dns_large_5k_lab.pcap"]
ATQ, INO, VIC = "192.168.100.50", "192.168.100.51", "192.168.100.1"
# D4: segundos de arranque del atacante fuera del entrenamiento. argv[1], defecto 2.0, rango [0, 10].
ARRANQUE_S = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
if not 0.0 <= ARRANQUE_S <= 10.0:
    print(f"PARAR: ARRANQUE_S={ARRANQUE_S} fuera de rango [0, 10] s (defecto 2.0)")
    sys.exit(1)


def parar(m):
    print("PARAR:", m)
    sys.exit(1)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


runs = pd.read_csv(RUNS, sep="\t", header=None, names=["familia", "tasa", "fichero"], dtype=str)
if len(runs) != 19:
    parar(f"runs_caliente.tsv tiene {len(runs)} corridas, se esperaban 19")
if runs.fichero.duplicated().any():
    parar("fichero repetido en runs_caliente.tsv")
for fam in runs.familia:
    if fam not in PROTO:
        parar(f"familia desconocida {fam}")

hdr0, partes, info = None, [], []
for _, r in runs.iterrows():
    p = DS / r.fichero
    if not p.exists():
        parar(f"falta {p}")
    hdr = p.open().readline().strip()
    if hdr0 is None:
        hdr0 = hdr
    elif hdr != hdr0:
        parar(f"cabecera distinta en {r.fichero}")
    d = pd.read_csv(p, dtype={"community_id": str, "src_ip": str, "dst_ip": str})
    d = d[d.event_kind == 0]
    n0 = len(d)
    d = d[(d[FEATS] > -9000).all(axis=1)].copy()
    centinela = n0 - len(d)
    a = (d.src_ip == ATQ) & (d.dst_ip == VIC)
    ap = a & (d.proto == PROTO[r.familia])
    if not ap.any():
        parar(f"{r.fichero} ({r.familia} {r.tasa}): sin filas .50->.1 de su protocolo")
    t0, t1 = d.ts_ns[ap].min(), d.ts_ns[ap].max()
    i = (d.src_ip == INO) & (d.dst_ip == VIC)
    rol = pd.Series("ambiente", index=d.index)
    rol[(d.dst_ip == VIC) & ~a & ~i] = "ambiente_victima"
    rol[i] = "inocente"
    rol[a & ~ap] = "descartado_proto"
    rol[ap] = "atacante" if r.familia in ATAQUES else "contraste"
    fase = pd.Series("durante", index=d.index)
    fase[d.ts_ns < t0] = "pre"
    fase[d.ts_ns > t1] = "post"
    d = d.assign(rol=rol, fase=fase, etiqueta=(rol == "atacante").astype(int),
                 arranque=(rol == "atacante") & (d.ts_ns < t0 + int(ARRANQUE_S * 1e9)),
                 familia=r.familia, tasa=r.tasa, fichero=r.fichero,
                 split="test" if (r.familia, r.tasa) in TEST else "train")
    info.append((r.familia, r.tasa, r.fichero, n0, centinela, int((rol == "descartado_proto").sum()),
                 round((t1 - t0) / 1e9, 1)))
    partes.append(d[d.rol != "descartado_proto"])

X = pd.concat(partes, ignore_index=True)
tmp = OUT.with_suffix(".csv.tmp")
X.to_csv(tmp, index=False)
os.replace(tmp, OUT)

print("== por corrida: familia tasa fichero kind0 centinela descartado_proto duracion_ataque_s")
for t in info:
    print("  ", *t)
print("== filas por rol / familia / tasa / split")
print(X.groupby(["rol", "familia", "tasa", "split"]).size().to_string())
print("== inocente por fase")
print(X[X.rol == "inocente"].groupby(["familia", "tasa", "fase"]).size().unstack(fill_value=0).to_string())
print(f"== arranque del atacante (primeros {ARRANQUE_S} s) por corrida")
print(X[X.arranque].groupby(["familia", "tasa"]).size().to_string())
print("== totales")
print(X.groupby(["split", "etiqueta"]).size().to_string())
print(X.groupby("rol").size().to_string())

lineas = [f"{sha(DS / f)}  {DS / f}" for f in runs.fichero]
lineas += [f"{sha(RUNS)}  {RUNS}"]
for p in PCAPS:
    lineas.append(f"{sha(p)}  {p}" if Path(p).exists() else f"FALTA  {p}")
lineas.append(f"{sha(OUT)}  {OUT}")
tmp = MAN.with_suffix(".tmp")
tmp.write_text("\n".join(lineas) + "\n")
os.replace(tmp, MAN)
print("== manifiesto:", MAN, " entradas FALTA:", sum(l.startswith("FALTA") for l in lineas))
