#!/usr/bin/env python3
"""DAY309 analisis de una corrida de la bateria B (d309_corrida_e2e.sh). Uso: d309_bateria_analisis.py DIR_CORRIDA

Lee DIR/tipo.txt, DIR/dataset.csv, DIR/firewall-agent.log, DIR/ml-detector.log y DIR/sniffer.log. Agrupa las filas de
flujo hacia .1 por (origen, protocolo); compara flow_packet_count con la prediccion calculada sobre las tuplas reales de
los pcaps (simulacion de la tabla con y sin caducidad, sin perdidas) y escribe DIR/resumen.json para
d309_comparar.py. rc 0 = analisis hecho; rc != 0 = faltan datos.
"""
import collections
import csv
import json
import re
import sys
from pathlib import Path

ATQ, BASE = "192.168.100.50", "192.168.100.51"
# Prediccion DAY309 (escrita antes de medir): grupo -> lado -> distribucion de flow_packet_count.
_ref = {1: 5200, 2: 189, 3: 11}
_base_bat = {1: 2072, 2: 28}
PRED = {
    "bateria ntp": {"atq udp": {"main": _ref, "rama": _ref}, "base udp": {"main": _base_bat, "rama": _base_bat}},
    "bateria dns": {"atq udp": {"main": _ref, "rama": _ref}, "base udp": {"main": _base_bat, "rama": _base_bat}},
    "bateria syn": {"atq tcp": {"main": {1: 5400}, "rama": {1: 5400}}},
    "benigna": {"base udp": {"main": {1: 4384, 2: 114, 3: 2}, "rama": {1: 4400, 2: 98, 3: 2}}},
}
TOL_FRAC = 0.02   # fraccion de filas con fpk == 1
TOL_MEDIA = 0.05  # media de fpk, relativa
PROTO = {"1": "icmp", "6": "tcp", "17": "udp"}


def stats(rows):
    fpk = [int(round(float(r["flow_packet_count"]))) for r in rows]
    n = len(fpk)
    c = collections.Counter(fpk)
    m = lambda k: sum(float(r[k]) for r in rows) / n
    top = dict(sorted(c.items())[:6])
    return {
        "n": n, "media_fpk": round(sum(fpk) / n, 4), "f1": round(c.get(1, 0) / n, 4), "max_fpk": max(fpk),
        "dist": {str(k): v for k, v in top.items()}, "size": round(m("mean_packet_size"), 2),
        "entropia": round(m("packet_size_entropy"), 4), "syn_ack": round(m("syn_ack_ratio"), 4),
        "completion": round(m("flow_completion_rate"), 4),
        "ratio_ge3": round(sum(float(r["victim_rate_ratio"]) >= 3.0 for r in rows) / n, 4),
        "vpps": round(m("victim_pps"), 2),
    }


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    d = Path(sys.argv[1])
    for f in ("tipo.txt", "dataset.csv", "firewall-agent.log", "ml-detector.log", "sniffer.log"):
        if not (d / f).is_file():
            print(f"FALTA {d / f}")
            return 3
    tipo = (d / "tipo.txt").read_text().strip()
    clave = " ".join(tipo.split()[:2])
    sniffer = (d / "sniffer.log").read_text(errors="replace").splitlines()
    lado = "rama" if any("[FLOW-TABLE]" in l for l in sniffer) else "main"
    print(f"corrida={d} tipo={tipo} lado detectado={lado} (por la presencia de [FLOW-TABLE] en sniffer.log)")
    rows = list(csv.DictReader(open(d / "dataset.csv", newline="")))
    flujo = [r for r in rows if r["event_kind"] == "0" and r["dst_ip"] == "192.168.100.1"]
    print(f"filas={len(rows)} de flujo hacia .1={len(flujo)} event_kind={dict(collections.Counter(r['event_kind'] for r in rows))}")
    grupos = collections.defaultdict(list)
    for r in flujo:
        quien = {ATQ: "atq", BASE: "base"}.get(r["src_ip"], "otro")
        grupos[f"{quien} {PROTO.get(r['proto'], r['proto'])}"].append(r)
    res = {"tipo": tipo, "lado": lado, "grupos": {}, "pred": {}}
    print("\n== rasgos de flujo por grupo (origen, protocolo)")
    for g in sorted(grupos):
        s = stats(grupos[g])
        res["grupos"][g] = s
        print(f"  {g:10s} n={s['n']:5d} media_fpk={s['media_fpk']:.3f} f(fpk=1)={s['f1']:.3f} max={s['max_fpk']} "
              f"dist={s['dist']}")
        print(f"  {'':10s} size={s['size']:.1f} entropia={s['entropia']:.4f} syn_ack={s['syn_ack']:.3f} "
              f"completion={s['completion']:.3f} ratio>=3={s['ratio_ge3']:.3f} victim_pps={s['vpps']:.1f}")
    print("\n== contra la prediccion (escrita antes de medir; tolerancias: fraccion +-0.02, media +-5 %)")
    ok_n = tot = 0
    for g, porlado in PRED.get(clave, {}).items():
        tot += 1
        p = porlado[lado]
        pn = sum(p.values())
        pf1 = p.get(1, 0) / pn
        pm = sum(k * v for k, v in p.items()) / pn
        s = res["grupos"].get(g)
        if not s:
            print(f"  {g:10s} predicho media={pm:.3f}: SIN FILAS")
            res["pred"][g] = False
            continue
        ok = abs(s["f1"] - pf1) <= TOL_FRAC and abs(s["media_fpk"] - pm) <= TOL_MEDIA * pm
        ok_n += ok
        res["pred"][g] = ok
        print(f"  {g:10s} predicho media={pm:.3f} f(fpk=1)={pf1:.3f} -> medido media={s['media_fpk']:.3f} "
              f"f(fpk=1)={s['f1']:.3f}: {'COINCIDE' if ok else 'NO COINCIDE'}")
    print(f"  prediccion del lado {lado}: {ok_n} de {tot} coinciden")

    fw = (d / "firewall-agent.log").read_text(errors="replace").splitlines()
    reg = [l for l in fw if re.search(r"\[SOMBRA-DDOS\] (INICIO|FIN) ", l)]
    print("\n== sombra del firewall (INICIO/FIN)")
    for l in reg:
        print("  " + l[l.find("[SOMBRA-DDOS]"):][:240])
    ini, fin = sum(" INICIO " in l for l in reg), sum(" FIN " in l for l in reg)
    drops = [int(m.group(1)) for l in reg if " FIN " in l for m in [re.search(r"eventos_drop=(\d+)", l)] if m]
    print(f"  INICIO={ini} FIN={fin} eventos_drop en FIN={drops}")
    ml = (d / "ml-detector.log").read_text(errors="replace").splitlines()
    tot2 = [tuple(map(int, m.groups())) for l in ml for m in [re.search(r"\[DDOS-V2\] bajo_presion=(\d+) ataque=(\d+)", l)] if m]
    bp, at = sum(t[0] for t in tot2), sum(t[1] for t in tot2)
    print(f"\n== cabeza: lineas [DDOS-V2]={len(tot2)} suma bajo_presion={bp} suma ataque={at}")
    ft = [l for l in sniffer if "[FLOW-TABLE] vivos=" in l]
    cad = sum(int(m.group(1)) for l in ft for m in [re.search(r"caducados=(\d+)", l)] if m)
    des = sum(int(m.group(1)) for l in ft for m in [re.search(r"desalojos_lru=(\d+)", l)] if m)
    fut = sum(int(m.group(1)) for l in ft for m in [re.search(r"marcas_futuras=(\d+)", l)] if m)
    if ft:
        print(f"== tabla de flujos: lineas={len(ft)} caducados={cad} desalojos_lru={des} marcas_futuras={fut}")
    res["decision"] = {"inicio": ini, "fin": fin, "drops_fin": drops, "bajo_presion": bp, "ataque": at}
    res["flow_table"] = {"lineas": len(ft), "caducados": cad, "desalojos_lru": des, "marcas_futuras": fut}
    (d / "resumen.json").write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
    print(f"\nresumen -> {d / 'resumen.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
