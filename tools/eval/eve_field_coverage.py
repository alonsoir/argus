#!/usr/bin/env python3
"""eve_field_coverage.py — cobertura de campos de identidad en un eve.json de Suricata.

Reproduce, en una sola pasada, las cuatro medidas que sostienen la puerta de diseño
multi-sensor (docs/design/multisensor-graph-identity/puerta-diseno-multisensor.md, DAY 225):

  1. Tabla event_type x {community_id, flow.start, flow_id}  -> secciones §1.3
  2. Alertas sin community_id, agrupadas por firma               -> §1.3, D5
  3. Colapso de community_id por protocolo (eventos `flow`)      -> §1.6, D1
  4. Reutilizacion de 5-tupla: repetidos y separacion temporal   -> §1.6

Uso:
    python3 tools/eval/eve_field_coverage.py <ruta-eve.json> [--diana <community_id>]

Sin dependencias externas. Salida determinista (ordenada), apta para redirigir a
un fichero de evidencia y commitear junto al documento que cita los numeros.

medir, no votar.
"""

import argparse
import json
import sys
from collections import Counter, defaultdict

DIANA_POR_DEFECTO = "1:IN7uqVpMWxpmuhQTowSQB2XEe0E="


def analizar(ruta, diana):
    total = Counter()
    con_cid = Counter()
    con_fstart = Counter()
    con_fid = Counter()

    ilegibles = 0
    diana_hits = 0

    # alertas sin community_id, por firma
    alertas_sin_cid = Counter()

    # eventos `flow`: cid distintos por protocolo
    flow_eventos = Counter()
    flow_cids = defaultdict(set)

    # reutilizacion: cid -> [(timestamp_inicio, sport, dport, proto)]
    repeticiones = defaultdict(list)

    with open(ruta, errors="replace") as fh:
        for linea in fh:
            linea = linea.strip()
            if not linea:
                continue
            try:
                e = json.loads(linea)
            except Exception:
                ilegibles += 1
                continue

            tipo = e.get("event_type", "<none>")
            total[tipo] += 1

            cid = e.get("community_id")
            if cid is not None:
                con_cid[tipo] += 1
                if cid == diana:
                    diana_hits += 1

            flujo = e.get("flow")
            tiene_start = isinstance(flujo, dict) and "start" in flujo
            if tiene_start:
                con_fstart[tipo] += 1
            if "flow_id" in e:
                con_fid[tipo] += 1

            if tipo == "alert" and cid is None:
                firma = e.get("alert", {})
                alertas_sin_cid[
                    "gid={} sid={} rev={} {!r}".format(
                        firma.get("gid"),
                        firma.get("signature_id"),
                        firma.get("rev"),
                        firma.get("signature"),
                    )
                ] += 1

            if tipo == "flow" and cid is not None:
                proto = e.get("proto", "?")
                flow_eventos[proto] += 1
                flow_cids[proto].add(cid)
                repeticiones[cid].append(
                    (flujo.get("start") if tiene_start else None,
                     e.get("src_port"), e.get("dest_port"), proto)
                )

    return dict(
        total=total, con_cid=con_cid, con_fstart=con_fstart, con_fid=con_fid,
        ilegibles=ilegibles, diana_hits=diana_hits, alertas_sin_cid=alertas_sin_cid,
        flow_eventos=flow_eventos, flow_cids=flow_cids, repeticiones=repeticiones,
    )


def informe(r, ruta, diana, top):
    p = print
    p("=" * 78)
    p("eve_field_coverage — {}".format(ruta))
    p("=" * 78)
    p("lineas ilegibles : {}".format(r["ilegibles"]))
    p("eventos totales  : {}".format(sum(r["total"].values())))
    p("diana {}: {} ocurrencias".format(diana, r["diana_hits"]))
    p("")

    p("[1] Cobertura de campos por event_type")
    p("{:<12} {:>9} {:>14} {:>12} {:>9}".format(
        "event_type", "total", "community_id", "flow.start", "flow_id"))
    for tipo, n in sorted(r["total"].items(), key=lambda x: (-x[1], x[0])):
        p("{:<12} {:>9} {:>14} {:>12} {:>9}".format(
            tipo, n, r["con_cid"][tipo], r["con_fstart"][tipo], r["con_fid"][tipo]))
    p("")

    p("[2] Alertas sin community_id, por firma")
    if not r["alertas_sin_cid"]:
        p("    (ninguna)")
    for firma, n in sorted(r["alertas_sin_cid"].items(), key=lambda x: (-x[1], x[0])):
        p("    {:>6}  {}".format(n, firma))
    p("")

    p("[3] Colapso de community_id por protocolo (solo eventos `flow`)")
    p("{:<8} {:>9} {:>11} {:>9} {:>8}".format(
        "proto", "eventos", "distintos", "colapso", "%"))
    tot_ev = tot_uniq = 0
    for proto, n in sorted(r["flow_eventos"].items(), key=lambda x: (-x[1], x[0])):
        u = len(r["flow_cids"][proto])
        tot_ev += n
        tot_uniq += u
        pct = (n - u) / n * 100 if n else 0.0
        p("{:<8} {:>9} {:>11} {:>9} {:>7.1f}%".format(proto, n, u, n - u, pct))
    if tot_ev:
        pct = (tot_ev - tot_uniq) / tot_ev * 100
        p("{:<8} {:>9} {:>11} {:>9} {:>7.1f}%".format(
            "TOTAL", tot_ev, tot_uniq, tot_ev - tot_uniq, pct))
    p("")

    p("[4] Top {} community_id reutilizados (separacion temporal)".format(top))
    rep = [(len(v), k, v) for k, v in r["repeticiones"].items() if len(v) > 1]
    rep.sort(key=lambda x: (-x[0], x[1]))
    for n, cid, filas in rep[:top]:
        filas = sorted(filas, key=lambda f: (f[0] or ""))
        _, sport, dport, proto = filas[0]
        p("    {:>4}x  {}  proto={} sport={} dport={}".format(n, cid, proto, sport, dport))
        for inicio, _, _, _ in filas[:4]:
            p("            {}".format(inicio))
        if n > 4:
            p("            ... ({} mas)".format(n - 4))
    p("")
    p("=" * 78)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ruta", help="ruta al eve.json")
    ap.add_argument("--diana", default=DIANA_POR_DEFECTO,
                    help="community_id a contar (default: diana E2E del flujo Neris)")
    ap.add_argument("--top", type=int, default=5, help="cuantos reutilizados mostrar")
    args = ap.parse_args()

    try:
        r = analizar(args.ruta, args.diana)
    except FileNotFoundError:
        sys.exit("no existe: {}".format(args.ruta))

    informe(r, args.ruta, args.diana, args.top)


if __name__ == "__main__":
    main()