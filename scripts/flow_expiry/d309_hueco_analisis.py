#!/usr/bin/env python3
"""DAY309 analisis de la corrida "hueco" (d309_hueco_e2e.sh). Uso: d309_hueco_analisis.py DIR_CORRIDA

Lee DIR/dataset.csv (escritor DDoS del ml-detector), DIR/firewall-agent.log, DIR/ml-detector.log y DIR/sniffer.log.
Separa las filas de flujo de .50 -> .1 en los dos ataques por el mayor hueco entre marcas (sin suponer relojes) y
compara flow_packet_count con la prediccion calculada sobre las tuplas reales de los pcaps (DAY309, simulacion de
la tabla con y sin caducidad, sin perdidas). rc 0 = analisis hecho; rc != 0 = faltan datos o no hay hueco.
"""
import collections
import csv
import re
import sys
from pathlib import Path

# Prediccion DAY309 (escrita antes de medir): fraccion de filas con flow_packet_count == k y media, por lado.
PRED = {
    "a1": {"media": 1.027, "dist": {1: 3510, 2: 84, 3: 6}},
    "a2_main": {"media": 2.080, "dist": {2: 3426, 3: 78, 4: 84, 5: 6, 6: 6}},
    "a2_rama": {"media": 1.027, "dist": {1: 3510, 2: 84, 3: 6}},
    "base_main": {"media": 1.026, "dist": {1: 5651, 2: 145, 3: 4}},
    "base_rama": {"media": 1.023, "dist": {1: 5673, 2: 123, 3: 4}},
}
TOL_FRAC = 0.02   # tolerancia en la fraccion de filas con fpk == 1 (perdidas del lab)
TOL_MEDIA = 0.05  # tolerancia relativa en la media de fpk


def stats(rows):
    fpk = [int(round(float(r["flow_packet_count"]))) for r in rows]
    n = len(fpk)
    c = collections.Counter(fpk)
    m = lambda k: sum(float(r[k]) for r in rows) / n
    return {
        "n": n, "media": sum(fpk) / n, "dist": dict(sorted(c.items())), "f1": c.get(1, 0) / n,
        "size": m("mean_packet_size"), "entropia": m("packet_size_entropy"), "completion": m("flow_completion_rate"),
        "ratio_ge3": sum(float(r["victim_rate_ratio"]) >= 3.0 for r in rows) / n, "vpps": m("victim_pps"),
    }


def linea(etq, s):
    print(f"  {etq:10s} n={s['n']:5d} media_fpk={s['media']:.3f} f(fpk=1)={s['f1']:.3f} dist={s['dist']}")
    print(f"  {'':10s} size={s['size']:.1f} entropia={s['entropia']:.4f} completion={s['completion']:.3f} "
          f"ratio>=3={s['ratio_ge3']:.3f} victim_pps={s['vpps']:.1f}")


def contra(etq, s, clave):
    p = PRED[clave]
    pn = sum(p["dist"].values())
    pf1 = p["dist"].get(1, 0) / pn
    ok = abs(s["f1"] - pf1) <= TOL_FRAC and abs(s["media"] - p["media"]) <= TOL_MEDIA * p["media"]
    print(f"  {etq:10s} predicho media={p['media']:.3f} f(fpk=1)={pf1:.3f} -> medido media={s['media']:.3f} "
          f"f(fpk=1)={s['f1']:.3f}: {'COINCIDE' if ok else 'NO COINCIDE'}")
    return ok


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    d = Path(sys.argv[1])
    for f in ("dataset.csv", "firewall-agent.log", "ml-detector.log", "sniffer.log"):
        if not (d / f).is_file():
            print(f"FALTA {d / f}")
            return 3
    sniffer = (d / "sniffer.log").read_text(errors="replace").splitlines()
    ft = [l for l in sniffer if "[FLOW-TABLE] vivos=" in l]
    lado = "rama" if any("[FLOW-TABLE]" in l for l in sniffer) else "main"
    print(f"corrida={d} lado detectado={lado} (por la presencia de [FLOW-TABLE] en sniffer.log)")

    rows = list(csv.DictReader(open(d / "dataset.csv", newline="")))
    flujo = [r for r in rows if r["event_kind"] == "0" and r["dst_ip"] == "192.168.100.1"]
    print(f"filas={len(rows)} de flujo hacia .1={len(flujo)} event_kind={dict(collections.Counter(r['event_kind'] for r in rows))}")
    # v2: solo UDP desde sport 123 (el ataque); el ping de fondo de esperar ESTABLE (ICMP .50 -> .1) quedaba dentro
    otros50 = collections.Counter(r["proto"] for r in flujo if r["src_ip"] == "192.168.100.50"
                                  and not (r["proto"] == "17" and r["src_port"] == "123"))
    print(f"filas de .50 fuera del ataque (descartadas, por proto): {dict(otros50)}")
    atq = sorted((r for r in flujo if r["src_ip"] == "192.168.100.50" and r["proto"] == "17" and r["src_port"] == "123"),
                 key=lambda r: int(r["ts_ns"]))
    base = [r for r in flujo if r["src_ip"] == "192.168.100.51" and r["proto"] == "17"]
    if len(atq) < 2 or not base:
        print("SIN filas suficientes de .50 o de .51")
        return 4
    gaps = [(int(atq[i + 1]["ts_ns"]) - int(atq[i]["ts_ns"]), i) for i in range(len(atq) - 1)]
    g, i = max(gaps)
    print(f"mayor hueco entre filas de .50: {g / 1e9:.1f} s")
    if g < 300e9:
        print("NO HAY HUECO >= 300 s entre los dos ataques: la corrida no mide la caducidad")
        return 5
    a1, a2 = atq[: i + 1], atq[i + 1:]
    for etq, a in (("ataque1", a1), ("ataque2", a2)):
        print(f"  {etq}: {(int(a[-1]['ts_ns']) - int(a[0]['ts_ns'])) / 1e9:.1f} s de filas")

    print("\n== rasgos de flujo (dataset del ml-detector)")
    s1, s2, sb = stats(a1), stats(a2), stats(base)
    linea("ataque1", s1)
    linea("ataque2", s2)
    linea("base .51", sb)
    print("\n== contra la prediccion (escrita antes de medir; tolerancias: fraccion +-0.02, media +-5 %)")
    r = [contra("ataque1", s1, "a1"), contra("ataque2", s2, "a2_" + lado), contra("base .51", sb, "base_" + lado)]
    print(f"  prediccion del lado {lado}: {sum(r)} de 3 coinciden")

    print("\n== sombra del firewall (INICIO/FIN)")
    fw = (d / "firewall-agent.log").read_text(errors="replace").splitlines()
    reg = [l for l in fw if re.search(r"\[SOMBRA-DDOS\] (INICIO|FIN) ", l)]
    for l in reg:
        print("  " + l[l.find("[SOMBRA-DDOS]"):][:300])
    print(f"  INICIO={sum(' INICIO ' in l for l in reg)} FIN={sum(' FIN ' in l for l in reg)}")

    print("\n== resumen periodico de la cabeza ([DDOS-V2] bajo_presion / ataque)")
    ml = (d / "ml-detector.log").read_text(errors="replace").splitlines()
    res = [l for l in ml if "[DDOS-V2] bajo_presion=" in l]
    con = [l for l in res if not re.search(r"ataque=0 ", l)]
    for l in con:
        print("  " + l[l.find("[DDOS-V2]"):][:200])
    tot = [tuple(map(int, re.search(r"bajo_presion=(\d+) ataque=(\d+)", l).groups())) for l in res]
    print(f"  lineas={len(res)} con ataque>0={len(con)} suma bajo_presion={sum(t[0] for t in tot)} "
          f"suma ataque={sum(t[1] for t in tot)}")

    print("\n== tabla de flujos del sniffer ([FLOW-TABLE], solo en la rama)")
    for l in ft:
        print("  " + l[l.find("[FLOW-TABLE]"):][:200])
    cad = sum(int(m.group(1)) for l in ft for m in [re.search(r"caducados=(\d+)", l)] if m)
    if ft:
        print(f"  suma caducados={cad} (prediccion: >= 3510, las tuplas del ataque 1)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
