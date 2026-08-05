#!/usr/bin/env python3
"""
bias_denominator_true.py -- DAY 251: denominador VERDADERO (aRGus)

Cierra el CAVEAT del denominador lens-observable de join_bias_labels.py
(DEBT-BIAS-DENOMINATOR-LENS-OBSERVABLE-001). El bias-report cuenta los flujos
botnet vistos por >=1 lente (14188); un flujo botnet que NINGUNA lente capturo
no deja fila y no cuenta. Este script mide el suelo real: las 5-tuplas botnet
que FISICAMENTE estuvieron en el pcap replayado (tshark), independientemente de
las lentes -> el punto ciego COMPARTIDO del banco de sensores.

FIDELIDAD: reutiliza canon()/is_botnet()/label_of()/load_csv()/load_labels() de
join_bias_labels.py -> MISMA canonicalizacion (par ordenado, proto minuscula)
que el join. No se reimplementa nada; si canon() cambiase, este script cambia
con el.

Conjuntos:
  P        = 5-tuplas canonicas del pcap replayado (tshark raw).
  B_full   = 5-tuplas canonicas etiquetadas botnet en el binetflow ENTERO
             (SIN restringir a lo que vieron las lentes).
  L        = 5-tuplas botnet vistas por >=1 lente (== gt_botnet del join, 14188).
  true     = P & B_full   -> denominador VERDADERO de NUESTRA corrida (acotado
             por el pcap: la NIC del host infectado, no todo CTU-13).
  blind    = true - L      -> botnet en el cable que NINGUNA lente vio.
  health   = L - P         -> deberia ser vacio (mismatch de canon; declarar).

SPLIT GSO (si el raw trae 8a columna frame.len): separa los 'blind' GSO-only
(todos sus frames > MTU, no replayables, explicados por el 0.81%) del HUECO REAL
(algun frame <= MTU: llego al cable y ninguna lente lo vio).

CARACTERIZACION del hueco real (con el raw por-paquete): por cada 5-tupla,
paquetes totales y direccionalidad (fwd = desde el endpoint 'lo' de la clave;
bwd = respuesta). bwd==0 -> intento sin respuesta capturada (tipo S0), pista de
por que las lentes de flujo no lo emiten como oro. Ademas concentracion de peers.

Entrada tshark (occurrence=f, separador coma, SIN cabecera):
  7 campos: ip.proto,ip.src,ip.dst,tcp.srcport,tcp.dstport,udp.srcport,udp.dstport
  8 campos: ... + frame.len   (activa split GSO + minlen)

Uso (desde la raiz del repo):
  python3 scripts/bias_denominator_true.py                    # ultimo modo A
  python3 scripts/bias_denominator_true.py 20260804-080140    # STAMP concreto
  python3 scripts/bias_denominator_true.py --mtu 1514
"""
import argparse
import csv
import os
import sys
import statistics as st
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from join_bias_labels import (
    canon, is_botnet, label_of, load_csv, load_labels,
    resolve_csv, stamp_of, DEFAULT_BINETFLOW,
    B_PROTO, B_SIP, B_SP, B_DIP, B_DP, B_LABEL,
)

DEFAULT_RAW = "logs/datasets/neris-pcap-5tuples-raw.csv"
REPORT_DIR = "logs/datasets"
HOST = "147.32.84.165"  # SARUMAN, el host infectado del escenario
PROTO_NUM = {"6": "tcp", "17": "udp", "1": "icmp"}


def load_pcap(path):
    """P + estadistica por 5-tupla desde el raw POR-PAQUETE (una fila = un frame).
    Devuelve: P, minlen{key->min frame.len} (o None), pkts{key->n}, fwd{key->n lo->hi},
    n_lines, n_ip, n_skip."""
    P = set()
    minlen = {}
    pkts = Counter()
    fwd = Counter()
    first_idx = {}
    has_fl = False
    n_lines = n_ip = n_skip = 0
    with open(path, newline="") as f:
        r = csv.reader(f)
        for row in r:
            n_lines += 1
            if len(row) < 7:
                continue
            pnum, sip, dip, t_sp, t_dp, u_sp, u_dp = (c.strip() for c in row[:7])
            if not sip or not dip:
                continue  # frame no-IP (ARP, etc.)
            n_ip += 1
            proto = PROTO_NUM.get(pnum)
            if proto == "tcp":
                sp, dp = t_sp, t_dp
            elif proto == "udp":
                sp, dp = u_sp, u_dp
            elif proto == "icmp":
                sp, dp = "", ""
            else:
                n_skip += 1
                continue
            key = canon(sip, sp, dip, dp, proto)
            P.add(key)
            if key not in first_idx:
                first_idx[key] = n_lines  # ordinal del frame en el pcap (linea del raw)
            pkts[key] += 1
            if (sip, sp) == (key[1], key[2]):  # este frame va de 'lo' -> 'hi'
                fwd[key] += 1
            fl = row[7].strip() if len(row) >= 8 else ""
            if fl.isdigit():
                has_fl = True
                v = int(fl)
                if key not in minlen or v < minlen[key]:
                    minlen[key] = v
    return P, (minlen if has_fl else None), pkts, fwd, n_lines, n_ip, n_skip, first_idx


def load_binetflow_botnet_full(path):
    B = set()
    n = 0
    with open(path, newline="") as f:
        r = csv.reader(f)
        next(r)
        for row in r:
            n += 1
            if len(row) <= B_LABEL:
                continue
            if not is_botnet(row[B_LABEL]):
                continue
            B.add(canon(row[B_SIP], row[B_SP], row[B_DIP], row[B_DP], row[B_PROTO]))
    return B, n


def peer_of(key):
    """endpoint que NO es el host infectado -> 'ip:port'."""
    lo = (key[1], key[2]); hi = (key[3], key[4])
    peer = hi if lo[0] == HOST else lo
    return f"{peer[0]}:{peer[1]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stamp", nargs="?", default="")
    ap.add_argument("--csv", default="")
    ap.add_argument("--binetflow", default=DEFAULT_BINETFLOW)
    ap.add_argument("--raw", default=DEFAULT_RAW, help="tshark raw del pcap (7 u 8 campos)")
    ap.add_argument("--mtu", type=int, default=1514, help="umbral frame.len para GSO-only")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    csv_path = resolve_csv(args.stamp, args.csv)
    for p, hint in ((csv_path, "make dataset-export"),
                    (args.binetflow, "make fetch-neris-labels"),
                    (args.raw, "tshark -r <pcap> ... > " + DEFAULT_RAW)):
        if not os.path.isfile(p):
            sys.exit(f"[ERROR] no existe {p}; corre antes `{hint}`.")

    stamp = stamp_of(csv_path)
    out_path = args.out or os.path.join(REPORT_DIR, f"bias-denominator-true-{stamp}.txt")

    buf = []

    def emit(line=""):
        buf.append(line)
        print(line)

    rows, keys_union = load_csv(csv_path)
    labels, n_binetflow = load_labels(args.binetflow, keys_union)
    L = set()
    for rs in rows.values():
        for k, _f, _c in rs:
            if label_of(labels, k) == "botnet":
                L.add(k)

    B_full, _ = load_binetflow_botnet_full(args.binetflow)
    P, minlen, pkts, fwd, n_lines, n_ip, n_skip, _first = load_pcap(args.raw)

    true = P & B_full
    blind = true - L
    health = L - P

    emit("=" * 72)
    emit("DENOMINADOR VERDADERO  (5-tupla canonica del pcap vs lens-observable)")
    emit("=" * 72)
    emit(f"csv modo A          : {csv_path}")
    emit(f"binetflow (labels)  : {args.binetflow}  ({n_binetflow} filas)")
    emit(f"pcap raw (tshark)   : {args.raw}  ({'con' if minlen is not None else 'sin'} frame.len)")
    emit(f"STAMP               : {stamp}")
    emit("")
    emit(f"pcap: lineas={n_lines}  con-IP={n_ip}  proto-sin-match={n_skip}")
    emit(f"P  (5-tuplas distintas en el pcap)             : {len(P)}")
    emit(f"B_full (5-tuplas botnet en el binetflow entero) : {len(B_full)}")
    emit(f"L  (botnet vistas por >=1 lente == gt_botnet)   : {len(L)}")
    emit("")
    emit("-" * 72)
    emit(f"[DENOMINADOR VERDADERO]  P & B_full = {len(true)}")
    emit("  = 5-tuplas botnet que FISICAMENTE estuvieron en NUESTRO replay.")
    emit("  ACOTADO por el pcap (NIC del host infectado), NO por todo CTU-13.")
    emit("")
    emit(f"[PUNTO CIEGO COMPARTIDO]  true - L = {len(blind)}")
    if true:
        emit(f"  = {len(blind) / len(true) * 100:.2f}% del denominador verdadero que NINGUNA lente vio.")

    if len(blind) == 0:
        emit("  -> el banco vio TODO el botnet replayado. El caveat se DISUELVE.")
    else:
        if minlen is None:
            gap = sorted(blind)
            emit("  (sin frame.len: no puedo separar GSO; re-genera el raw con -e frame.len)")
        else:
            gso_only = sorted(k for k in blind if minlen.get(k, 0) > args.mtu)
            gap = sorted(k for k in blind if minlen.get(k, 10 ** 9) <= args.mtu)
            emit(f"  SPLIT GSO (umbral frame.len > {args.mtu}):")
            emit(f"    GSO-only (no replayables, explicados por el 0.81%) : {len(gso_only)}")
            emit(f"    HUECO REAL (algun frame <= MTU, llego al cable)     : {len(gap)}")

        # TEST de la hipotesis "cola larga": ¿los ciegos son los flujos GRANDES?
        # (flush de conn.log: conexiones largas aun abiertas al cosechar no dejan fila)
        seen_true = true - blind
        def dist(sset):
            v = sorted(pkts[k] for k in sset)
            if not v:
                return "(vacio)"
            return (f"n={len(v):5d}  min={v[0]:<4d} p50={int(st.median(v)):<5d} "
                    f"media={sum(v)/len(v):<6.0f} p90={v[int(0.9*(len(v)-1))]:<5d} max={v[-1]}")
        emit("")
        emit("  DISTRIBUCION de paquetes/flujo (hipotesis: los ciegos son la cola larga):")
        emit(f"    CIEGOS (blind) : {dist(blind)}")
        emit(f"    VISTOS (seen)  : {dist(seen_true)}")
        ranked = sorted(true, key=lambda k: pkts[k], reverse=True)
        topN = set(ranked[:len(blind)])
        emit(f"    de los {len(blind)} flujos MAS GRUESOS de 'true', son ciegos: {len(topN & blind)}/{len(blind)}")

        if gap:
            # caracterizacion del hueco real
            unanswered = [k for k in gap if (pkts[k] - fwd[k]) == 0]
            answered = [k for k in gap if (pkts[k] - fwd[k]) > 0]
            tiny = [k for k in gap if pkts[k] <= 2]
            emit("")
            emit(f"  CARACTERIZACION del hueco real ({len(gap)} flujos):")
            emit(f"    sin respuesta capturada (bwd==0, tipo S0/intento) : {len(unanswered)}")
            emit(f"    con respuesta (bwd>0, handshake/datos)            : {len(answered)}")
            emit(f"    triviales (<=2 paquetes en todo el pcap)          : {len(tiny)}")
            peers = Counter(peer_of(k) for k in gap)
            emit(f"    peers distintos                                   : {len(peers)}")
            emit("    top peers del hueco (ip:port  ->  n flujos):")
            for pr, c in peers.most_common(8):
                emit(f"      {c:4d}  {pr}")
            emit("")
            emit("    detalle (min frame.len | pkts fwd/bwd | 5-tupla):")
            for k in gap:
                b = pkts[k] - fwd[k]
                ml = minlen.get(k, "?") if minlen is not None else "?"
                emit(f"      len={ml:>5}  pkts={pkts[k]:>3} ({fwd[k]}/{b})  {k}")

    emit("")
    emit(f"[SALUD DE LA CLAVE]  L - P = {len(health)}  (deberia ser 0)")
    if health:
        emit("  -> una lente vio botnet en 5-tuplas que NO estan en el pcap: DECLARAR.")
        for k in sorted(health)[:15]:
            emit(f"       {k}")
    else:
        emit("  -> limpio: todo lo que las lentes vieron como botnet esta en el pcap.")
    emit("")
    emit("=" * 72)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        f.write("\n".join(buf) + "\n")
    print(f"\n[artefacto] reporte escrito en {out_path}")


if __name__ == "__main__":
    main()