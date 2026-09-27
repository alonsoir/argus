#!/usr/bin/env python3
"""
fpr_head_A.py — Especificidad (FPR) de la cabeza DDoS A sobre Neris.

DAY269 — esqueleto de apoyo. Parser OFFLINE del log verboso de ml-detector.
Neris NO tiene DDoS → todo flujo que A puntúe > umbral es un FALSO POSITIVO.
Mide FPR a 0.5 (entrenamiento de A) Y 0.7 (umbral de despliegue real, config L149).

Uso:
    # 1) Traer el log limpio desde la VM al host (o parsear en la VM)
    vagrant ssh -c "cat /vagrant/logs/lab/ml-detector.log" > ml-detector.log
    # 2) Correr
    python3 fpr_head_A.py --log ml-detector.log --model ddos_head_A.pkl

Prerrequisito de dataset LIMPIO: rotar el log (make logs-lab-clean) JUSTO antes
del replay, para que contenga SOLO Neris. Si el log está mezclado, el denominador
no vale (lección DAY268).

INCOMPLETO A PROPÓSITO: los TODO marcan las 3 decisiones que exigen tener el
feature_names.json de A y el .pkl delante. No inventar el orden de las 9.
"""

import argparse
import re
import sys
from dataclasses import dataclass, field

# ── Formato del bloque (capturado DAY268, paso 3) ────────────────────────────
# [ts] [ml-detector] [debug] Feature Extraction:
# [ts] [ml-detector] [debug]   Flow: 147.32.84.165:2343 -> 213.246.53.125:5296 (TCP)
# [ts] [ml-detector] [debug]   Duration: 0.000s
# [ts] [ml-detector] [debug]   Packets: 1 fwd, 0 bwd, 1 total
# [ts] [ml-detector] [debug]   Bytes: 86 fwd, 0 bwd, 86 total
# [ts] [ml-detector] [debug]   Feature[ 0] Packet Length Std             :     0.000000
# ... 23 líneas Feature[0..22] ...

RE_BLOCK_START = re.compile(r'\[debug\]\s+Feature Extraction:')
RE_FLOW        = re.compile(r'\[debug\]\s+Flow:\s+(\S+)\s+->\s+(\S+)\s+\((\w+)\)')
RE_PACKETS     = re.compile(r'\[debug\]\s+Packets:\s+(\d+)\s+fwd,\s+(\d+)\s+bwd,\s+(\d+)\s+total')
RE_FEATURE     = re.compile(r'\[debug\]\s+Feature\[\s*(\d+)\]\s+(.+?)\s*:\s*([\d.eE+-]+)\s*$')

N_LEVEL1 = 23  # el vector volcado

# Centinela de flujo de 1 paquete (DAY267): Fwd IAT Min ≈ 3.00e10
IAT_SENTINEL = 3.0e10


@dataclass
class Flow:
    src: str
    dst: str
    proto: str
    pkts_fwd: int = 0
    pkts_bwd: int = 0
    pkts_total: int = 0
    feats: dict = field(default_factory=dict)  # idx -> (nombre, valor)

    @property
    def is_empty(self) -> bool:
        return self.pkts_total == 0

    @property
    def is_degenerate(self) -> bool:
        # 1 paquete y/o centinela IAT. bwd=0 SOLO no basta (A lo trata como señal;
        # es justo lo que queremos medir, no descartar).
        f16 = self.feats.get(16, ("", 0.0))[1]
        return self.pkts_total <= 1 or f16 >= IAT_SENTINEL

    @property
    def is_good(self) -> bool:
        return (not self.is_empty) and (not self.is_degenerate)


def parse_log(path):
    """Devuelve lista de Flow. Un bloque = de 'Feature Extraction:' hasta el siguiente
    (o hasta reunir 23 features). Robusto ante líneas intercaladas (warnings, etc.)."""
    flows = []
    cur = None
    n_feats = 0
    with open(path, 'r', errors='replace') as fh:
        for line in fh:
            if RE_BLOCK_START.search(line):
                if cur is not None:
                    flows.append(cur)
                cur = None
                n_feats = 0
                cur = Flow(src="?", dst="?", proto="?")
                continue
            if cur is None:
                continue
            m = RE_FLOW.search(line)
            if m:
                cur.src, cur.dst, cur.proto = m.group(1), m.group(2), m.group(3)
                continue
            m = RE_PACKETS.search(line)
            if m:
                cur.pkts_fwd  = int(m.group(1))
                cur.pkts_bwd  = int(m.group(2))
                cur.pkts_total = int(m.group(3))
                continue
            m = RE_FEATURE.search(line)
            if m:
                idx = int(m.group(1))
                cur.feats[idx] = (m.group(2).strip(), float(m.group(3)))
                n_feats += 1
                if n_feats == N_LEVEL1:
                    flows.append(cur)
                    cur = None
                    n_feats = 0
                continue
    if cur is not None:
        flows.append(cur)
    return flows


# ── TODO(1): mapa A→índice level1 (de DAY267). Confirmar contra feature_names.json ──
# Orden de las 9 de A, cada una como índice en el vector level1 de 23:
#   A#0 Total Length of Fwd Packets = level1[9]
#   A#1 Total Length of Bwd Packets = level1[18]
#   A#2 Fwd Packet Length Max       = level1[2]
#   A#3 Bwd Packet Length Max       = level1[7]
#   A#4 Bwd Packet Length Mean      = level1[19]
#   A#5 Packet Length Mean          = level1[17]
#   A#6 Avg Fwd Segment Size        = level1[3]
#   A#7 Subflow Fwd Bytes  (ALIAS de A#0) = level1[1]
#   A#8 Subflow Bwd Bytes  (ALIAS de A#1) = level1[12]
# OJO: verificar el ORDEN EXACTO que espera el .pkl con feature_names.json antes de fiarse.
A_TO_LEVEL1 = [9, 18, 2, 7, 19, 17, 3, 1, 12]  # TODO: confirmar contra artifacts_ddos_A/feature_names.json


def build_A_vector(flow: Flow):
    """Reconstruye el vector de 9 de A en su orden, desde los 23 de level1."""
    vec = []
    for a_idx, l1_idx in enumerate(A_TO_LEVEL1):
        if l1_idx not in flow.feats:
            return None  # bloque incompleto → descartar
        vec.append(flow.feats[l1_idx][1])
    return vec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--log', required=True, help='ml-detector.log (limpio, solo Neris)')
    ap.add_argument('--model', default='ddos_head_A.pkl', help='pickle de la cabeza A')
    ap.add_argument('--thresholds', default='0.5,0.7')
    args = ap.parse_args()

    flows = parse_log(args.log)
    total = len(flows)
    empty = sum(1 for f in flows if f.is_empty)
    degen = sum(1 for f in flows if (not f.is_empty) and f.is_degenerate)
    good  = [f for f in flows if f.is_good]

    print(f"── Censo de flujos (auditable) ──")
    print(f"  Total bloques parseados : {total}")
    print(f"  Vacíos (0 paquetes)     : {empty}")
    print(f"  Degenerados (1pkt/IAT)  : {degen}")
    print(f"  Buenos (aptos para A)   : {len(good)}")
    print()

    if not good:
        print("✗ Sin flujos buenos. Revisar calidad del replay antes de medir A.")
        sys.exit(1)

    # ── TODO(2): cargar el modelo. Formato del .pkl a confirmar (sklearn? xgboost?) ──
    # import pickle
    # with open(args.model, 'rb') as fh:
    #     model = pickle.load(fh)
    #
    # X = [build_A_vector(f) for f in good]
    # X = [v for v in X if v is not None]
    # proba = model.predict_proba(X)[:, 1]   # TODO: confirmar índice de la clase positiva
    #
    # ── TODO(3): contar FP a cada umbral ──
    # Neris NO tiene DDoS → cualquier proba > umbral es un FP.
    # for thr in [float(t) for t in args.thresholds.split(',')]:
    #     fp = int((proba > thr).sum())
    #     fpr = fp / len(proba)
    #     print(f"  FPR @ {thr}: {fp}/{len(proba)} = {fpr:.4%}")

    print("TODO(2)/(3): descomentar carga de modelo + conteo FP cuando ddos_head_A.pkl esté a mano.")
    print(f"Listo para puntuar {len(good)} vectores de 9. Confirmar A_TO_LEVEL1 contra feature_names.json primero.")


if __name__ == '__main__':
    main()