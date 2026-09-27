#!/usr/bin/env python3
"""
train_ddos_head_v2.py — comparacion A vs B de la cabeza DDoS, con decision por IC.

NO reimplementa carga ni split: HEREDA load_day / pick_features / SEED del
train_ddos_head.py original (disciplina de leakage ya PROBADA: parser %Y-%d-%m,
Inf en cols 22-23, benigno = todo != BENIGN, split cruzado 01-12 -> 03-11,
Portmap held-out, imputacion por mediana de TRAIN). Reescribir ese core de memoria
seria la leccion Init_Win otra vez (reescribir != preservar); por eso se importa.

Lo UNICO nuevo es la capa de decision que el original no tiene:
  - umbral a FPR benigno FIJO (no 0.5): compara A y B al MISMO coste de FP.
  - recall por tipo de ataque a ese umbral.
  - IC por bootstrap sobre TIPOS DE ATAQUE (no flujos): la unidad de
    generalizacion es el ataque; remuestrear flujos daria un IC falsamente
    estrecho (el 0.99 mentiroso en version estadistica).

A  = features transferibles que el detector level1 (rf_23) YA sirve hoy.
B  = techo transferible completo (todas las de sep_min alto), cablee o no.
B-A = lo que habria que cablear proto->cabeza para desplegar B.

Regla de decision (la fija la medicion, NO un umbral inventado):
  - IC de (recall_B - recall_A) CRUZA CERO  -> no cablear B-A: la ganancia no se
    separa de la varianza entre ataques.
  - IC limpio SOBRE cero -> decision de ingenieria: ese Delta medido vale las N
    features de B-A que hay que cablear? Con los dos numeros delante.
  - IC limpio BAJO cero -> B es peor; quedate con A.

AVISO honesto que este harness NO puede quitar: el benigno es escaso y homogeneo
(misma captura) -> numeros TECHO, no garantia de despliegue. La generalizacion
solo se prueba dentro de reflexion/amplificacion. Huella dominante = tamano de
paquete, evadible.

  python3 train_ddos_head_v2.py ../../datasets/CICDDoS2019 \
      --summary auc_matrix_summary.csv --sep-min 0.60 --target-fpr 0.0095
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier

# --- HERENCIA del core probado; si falla, paramos en vez de seguir a ciegas ---
try:
    from train_ddos_head import load_day, pick_features, SEED
except ImportError as e:
    sys.exit(f"[FATAL] no importo el core original (train_ddos_head.py en el CWD): {e}")

# rf_23: lo que el detector level1 YA computa y sirve hoy (nombres stripped).
# Fuente: sniffer/config/features/rf_23_features.json (los 23 'name').
RF23_SERVED = {
    "Packet Length Std", "Subflow Fwd Bytes", "Fwd Packet Length Max",
    "Avg Fwd Segment Size", "ACK Flag Count", "Packet Length Variance",
    "PSH Flag Count", "Bwd Packet Length Max", "act_data_pkt_fwd",
    "Total Length of Fwd Packets", "Fwd Packet Length Std", "Fwd Packets/s",
    "Subflow Bwd Bytes", "Destination Port", "Init_Win_bytes_forward",
    "Subflow Fwd Packets", "Fwd IAT Min", "Packet Length Mean",
    "Total Length of Bwd Packets", "Bwd Packet Length Mean",
    "Bwd Packet Length Min", "Flow Duration", "Flow Packets/s",
}

# Serve-invalidas MEDIDAS. Fuera SIEMPRE, aunque el sep_min las dejara pasar:
# el sep_min es una metrica de separabilidad en el dataset y NO ve estos defectos
# de serve/captura. Se codifican a mano, cada una con su razon medida.
EXCLUDE_MEASURED = {
    "ACK Flag Count":         "DAY265: espuria+invertida (ACK=1 en 99.94% de flujos sin retorno; serve contaria 0 -> clasificaria al reves)",
    "PSH Flag Count":         "DAY265: mismo subsistema de flags binario del dataset (SYN=0 en Syn.csv lo delata)",
    "Init_Win_bytes_forward": "DAY264: serve la hardcodea a 0.0f -> offline mediria un fantasma no desplegable",
    "Inbound":                "leakage de entorno (victima fija); ya ablacionado en el harness original",
}


def fixed_fpr_threshold(benign_scores, target_fpr):
    """Umbral que produce ~target_fpr sobre el benigno. El benigno FIJA el coste;
    el recall se lee luego a ese umbral -> A y B se comparan al MISMO FPR, no al
    mismo umbral (que tendrian escalas distintas y harian injusta la comparacion)."""
    s = np.sort(benign_scores)[::-1]
    if len(s) == 0:
        return 0.5
    k = int(np.floor(target_fpr * len(s)))
    return float(s[0] + 1e-9) if k == 0 else float(s[k - 1])


def recall_by_attack(scores, y, tag, thr):
    """Recall a umbral fijo, por tipo de ataque -> dict tipo->recall.
    Portmap entra como una clave mas (es held-out; se lee aparte al reportar)."""
    out = {}
    for t in sorted(set(tag[y == 1])):
        m = (tag == t) & (y == 1)
        out[t] = float((scores[m] >= thr).mean()) if m.any() else float("nan")
    return out


def paired_bootstrap_delta(rA, rB, n_boot=5000, seed=SEED):
    """IC de (recall_B - recall_A) remuestreando TIPOS DE ATAQUE (macro).
    Pareado: el MISMO sorteo de ataques para A y B (reduce varianza del sorteo
    compartido). Devuelve (delta, lo, hi, n_tipos)."""
    types = sorted(set(rA) & set(rB))
    a = np.array([rA[t] for t in types])
    b = np.array([rB[t] for t in types])
    n = len(types)
    if n == 0:
        return float("nan"), float("nan"), float("nan"), 0
    rng = np.random.default_rng(seed)
    deltas = np.empty(n_boot)
    for j in range(n_boot):
        idx = rng.integers(0, n, n)
        deltas[j] = b[idx].mean() - a[idx].mean()
    lo, hi = np.percentile(deltas, [2.5, 97.5])
    return float(b.mean() - a.mean()), float(lo), float(hi), n


def train_score(Xtr, ytr, Xte, cols, medians):
    """RF sobre las columnas `cols` (mismas FILAS para A y B, subset de columnas).
    Imputa con la mediana de TRAIN (heredada). Devuelve (scores_test, modelo)."""
    m = RandomForestClassifier(n_estimators=200, class_weight="balanced",
                               random_state=SEED, n_jobs=-1)
    m.fit(Xtr[cols].fillna(medians[cols]), ytr)
    return m.predict_proba(Xte[cols].fillna(medians[cols]))[:, 1], m


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", type=Path)
    ap.add_argument("--summary", type=Path, required=True,
                    help="auc_matrix_summary.csv del barrido cross-ataque")
    ap.add_argument("--sep-min", type=float, default=0.60)
    ap.add_argument("--target-fpr", type=float, default=0.0095,
                    help="FPR benigno al que se comparan A y B (default 0.95%%)")
    ap.add_argument("--sample-attack-train", type=int, default=80_000)
    ap.add_argument("--sample-attack-test", type=int, default=80_000)
    ap.add_argument("--n-boot", type=int, default=5000)
    args = ap.parse_args()

    selected = pick_features(args.summary, args.sep_min)
    B = [f for f in selected if f not in EXCLUDE_MEASURED]
    A = [f for f in B if f in RF23_SERVED]
    only_B = [f for f in B if f not in RF23_SERVED]        # <- lo que hay que CABLEAR
    excluded = [f for f in selected if f in EXCLUDE_MEASURED]

    if not A:
        sys.exit("[FATAL] A vacio: ninguna transferible es servible por rf_23. Baja --sep-min.")
    print(f"[A]   servible-hoy         ({len(A):2d}): {A}")
    print(f"[B]   techo transferible   ({len(B):2d}): {B}")
    print(f"[B-A] a cablear a serve    ({len(only_B):2d}): {only_B}")
    if excluded:
        print(f"[excluidas por medicion]      : {excluded}")
    if not only_B:
        print("[nota] B == A: no hay nada nuevo que cablear; el veredicto sera Delta~0 por construccion.")

    # Carga UNA vez con B (superconjunto); A y B ven EXACTAMENTE las mismas filas.
    rng = np.random.default_rng(SEED)
    Xtr, ytr, _ = load_day(args.root, "01-12", B, args.sample_attack_train, rng)
    Xte, yte, tag = load_day(args.root, "03-11", B, args.sample_attack_test, rng)
    medians = Xtr.median(numeric_only=True)

    present = list(Xtr.columns)
    Acols = [c for c in A if c in present]
    Bcols = [c for c in B if c in present]
    dropped = [c for c in B if c not in present]
    if dropped:
        print(f"[WARN] features ausentes en cabecera, excluidas de facto: {dropped}")
    print(f"\ntrain: {len(ytr):,} filas ({int(ytr.sum()):,} atk / {int((ytr==0).sum()):,} ben)"
          f"  |  test: {len(yte):,} filas ({int(yte.sum()):,} atk / {int((yte==0).sum()):,} ben)")

    sA, _ = train_score(Xtr, ytr, Xte, Acols, medians)
    sB, _ = train_score(Xtr, ytr, Xte, Bcols, medians)

    benign = (yte == 0)
    thrA = fixed_fpr_threshold(sA[benign], args.target_fpr)
    thrB = fixed_fpr_threshold(sB[benign], args.target_fpr)
    fprA = float((sA[benign] >= thrA).mean())
    fprB = float((sB[benign] >= thrB).mean())

    rA = recall_by_attack(sA, yte, tag, thrA)
    rB = recall_by_attack(sB, yte, tag, thrB)

    print(f"\n=== recall por ataque a FPR benigno ~{args.target_fpr:.4f} "
          f"(A real={fprA:.4f} / B real={fprB:.4f}) ===")
    print(f"{'ataque':16s} {'A':>8s} {'B':>8s} {'B-A':>9s}")
    for t in sorted(set(rA) | set(rB)):
        va, vb = rA.get(t, float("nan")), rB.get(t, float("nan"))
        star = "  <- HELD-OUT" if t.lower() == "portmap" else ""
        print(f"{t:16s} {va:8.4f} {vb:8.4f} {vb - va:+9.4f}{star}")

    d, lo, hi, n = paired_bootstrap_delta(rA, rB, args.n_boot)
    macroA = float(np.nanmean(list(rA.values())))
    macroB = float(np.nanmean(list(rB.values())))
    print(f"\n=== VEREDICTO (macro sobre {n} tipos de ataque) ===")
    print(f"  recall_A(macro)={macroA:.4f}   recall_B(macro)={macroB:.4f}")
    print(f"  Delta(B-A) = {d:+.4f}   IC95% bootstrap = [{lo:+.4f}, {hi:+.4f}]")
    if n < 10:
        print(f"  [aviso] n={n} tipos: IC crudo. Leelo JUNTO a la tabla de arriba, "
              f"no solo el numero (con pocos tipos, un ataque manda mucho).")
    if np.isnan(d):
        print("  -> sin tipos comunes; revisa los datos.")
    elif lo <= 0 <= hi:
        print("  -> EL IC CRUZA CERO: NO cablear B-A. La ganancia no se separa de "
              "la varianza entre ataques. La cabeza desplegable es A.")
    elif lo > 0:
        print(f"  -> IC LIMPIO SOBRE CERO. Decision de ingenieria: Delta={d:+.4f} "
              f"vale cablear {len(only_B)} features?  ->  {only_B}")
    else:
        print("  -> IC LIMPIO BAJO CERO: B es PEOR que A. Quedate con A "
              "(mas features metieron ruido, no senal).")


if __name__ == "__main__":
    main()