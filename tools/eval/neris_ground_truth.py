#!/usr/bin/env python3
# tools/eval/neris_ground_truth.py
# DEBT-L1-NO-REPRODUCIBLE-HOLDOUT-001 (mitad generalizacion) — Via A, Fase 1.
# DEBT-NERIS-GT646-UNPROVENANCED-001 — arqueologia del 646 (subproducto).
#
# Deriva la verdad terreno del eval Neris desde el binetflow de CTU-13:
#   flujos From-Botnet-* (dentro de la ventana del pcap, tcp/udp)
#   -> community_id -> dedupe.
# La unidad de medida del recall es "community_id botnet UNICO" (el cid no
# lleva tiempo; el join del bronce es por cid — dedupe DECLARADO, no implicito).
#
# community_id: paquete `communityid` (Corelight, implementacion de REFERENCIA
# de la spec — la misma que Zeek). La paridad C++<->Zeek de aRGus (DAY 171/172)
# la valida transitivamente. Seed=0 (default, igual que Zeek y que el sniffer).
#
# Arqueologia del 646: GT_TP=646 en parse_results.py es una constante sin
# derivacion. Este script cuenta bajo varios criterios y reporta si alguno
# reproduce 646. Si ninguno: irreconstruible, documentado.
#
# AUTHORS: Alonso Isidoro Roman + Claude (Anthropic) — DAY 220 (16-jul-2026)

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import communityid
except ImportError:
    sys.exit("FAIL-CLOSED: falta el paquete 'communityid' (Corelight). "
             "pip install communityid")


def md5(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        while b := f.read(chunk):
            h.update(b)
    return h.hexdigest()


def parse_ts(raw: str) -> datetime:
    # binetflow: "2011/08/10 09:46:53.047277" (hora local CTU; el pcap es de
    # la misma captura/origen — comparacion naive, misma zona horaria).
    return datetime.strptime(raw.strip(), "%Y/%m/%d %H:%M:%S.%f")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Via A Fase 1 — GT Neris desde binetflow")
    ap.add_argument("--binetflow", required=True)
    ap.add_argument("--window-start", required=True,
                    help='Primer paquete del pcap, ej "2011/08/10 09:01:40.475792"'
                         " (de capinfos; fijar explicito, no asumir)")
    ap.add_argument("--window-end", required=True,
                    help='Ultimo paquete del pcap, ej "2011/08/10 13:49:29.289628"')
    ap.add_argument("--out-cids", required=True,
                    help="salida: un community_id por linea (el GT)")
    ap.add_argument("--out-meta", required=True,
                    help="salida: JSON con criterios, conteos y arqueologia 646")
    args = ap.parse_args()

    w_start = parse_ts(args.window_start)
    w_end = parse_ts(args.window_end)
    cid_gen = communityid.CommunityID()  # seed=0, base64 — paridad Zeek/aRGus

    # Contadores por criterio (arqueologia del 646 incluida)
    n_total = 0
    n_botnet = 0                    # From-Botnet-*, sin mas filtros
    n_botnet_window = 0             # + ventana del pcap
    n_botnet_window_l4 = 0          # + proto in {tcp,udp}
    n_botnet_window_tcp = 0         # variante: solo tcp
    n_unparsable = 0                # puertos/campos no parseables (contados)
    label_breakdown = {}
    cids = set()
    cids_tcp = set()
    tuples_seen = set()             # dedupe por 5-tupla dirigida (otra vara)

    with open(args.binetflow, newline="") as f:
        # El fichero arranca con linea(s) en blanco antes del header en algunas
        # distribuciones — filtramos lineas vacias antes del DictReader.
        reader = csv.DictReader(
            (line for line in f if line.strip()), skipinitialspace=True)
        for row in reader:
            n_total += 1
            label = (row.get("Label") or "").strip()
            if not label.startswith("flow=From-Botnet"):
                continue
            n_botnet += 1
            label_breakdown[label] = label_breakdown.get(label, 0) + 1

            try:
                ts = parse_ts(row["StartTime"])
            except (ValueError, KeyError):
                n_unparsable += 1
                continue
            if not (w_start <= ts <= w_end):
                continue
            n_botnet_window += 1

            proto = (row.get("Proto") or "").strip().lower()
            if proto not in ("tcp", "udp"):
                continue  # sin community_id posible (D-F: SKIP legitimo)
            n_botnet_window_l4 += 1
            if proto == "tcp":
                n_botnet_window_tcp += 1

            try:
                src, dst = row["SrcAddr"].strip(), row["DstAddr"].strip()
                sport = int(row["Sport"].strip(), 0)   # base 0: acepta 0x...
                dport = int(row["Dport"].strip(), 0)
            except (ValueError, KeyError, AttributeError):
                n_unparsable += 1
                continue

            tuples_seen.add((src, sport, dst, dport, proto))
            if proto == "tcp":
                tpl = communityid.FlowTuple.make_tcp(src, dst, sport, dport)
            else:
                tpl = communityid.FlowTuple.make_udp(src, dst, sport, dport)
            cid = cid_gen.calc(tpl)
            cids.add(cid)
            if proto == "tcp":
                cids_tcp.add(cid)

    counts = {
        "binetflow_rows_total": n_total,
        "from_botnet_all": n_botnet,
        "from_botnet_in_pcap_window": n_botnet_window,
        "from_botnet_window_tcp_udp": n_botnet_window_l4,
        "from_botnet_window_tcp_only": n_botnet_window_tcp,
        "unique_directed_5tuples": len(tuples_seen),
        "unique_community_ids_tcp_udp": len(cids),   # <- EL DENOMINADOR DEL EVAL
        "unique_community_ids_tcp_only": len(cids_tcp),
        "rows_unparsable_skipped": n_unparsable,
    }
    hit_646 = {k: v for k, v in counts.items() if v == 646}

    meta = {
        "generated_by": "tools/eval/neris_ground_truth.py",
        "binetflow": {"path": args.binetflow, "md5": md5(args.binetflow)},
        "window": {"start": args.window_start, "end": args.window_end,
                   "source": "capinfos first/last packet time del pcap "
                             "(md5 172c6b4eb9be9a14fb5703a83f747a6c)"},
        "criteria": ("Label startswith 'flow=From-Botnet' AND StartTime en "
                     "ventana AND proto in {tcp,udp}; unidad = community_id "
                     "unico (dedupe declarado; el cid no lleva tiempo)"),
        "community_id": {"impl": "communityid (PyPI, Corelight — referencia)",
                         "seed": 0,
                         "parity": "C++<->Zeek probada DAY 171/172; "
                                   "Zeek usa la implementacion de referencia"},
        "counts": counts,
        "label_breakdown_top": dict(sorted(label_breakdown.items(),
                                           key=lambda kv: -kv[1])[:15]),
        "gt646_archaeology": {
            "constant_location": "experiments/suricata-comparative/parse_results.py:14",
            "criteria_matching_646": hit_646 if hit_646 else
            "NINGUNO — 646 no reconstruible bajo estos criterios "
            "(DEBT-NERIS-GT646-UNPROVENANCED-001 sigue abierta)",
        },
    }

    Path(args.out_cids).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out_cids, "w") as f:
        for cid in sorted(cids):
            f.write(cid + "\n")
    json.dump(meta, open(args.out_meta, "w"), indent=2)
    print(json.dumps({"counts": counts,
                      "gt646": meta["gt646_archaeology"]["criteria_matching_646"]},
                     indent=2))
    print(f"\nGT: {len(cids)} cids -> {args.out_cids}\nMeta: {args.out_meta}")


if __name__ == "__main__":
    main()