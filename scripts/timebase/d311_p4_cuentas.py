#!/usr/bin/env python3
# DAY311 [P4-D311]: descompone la identidad P4 del E2E de protegidos (DROP_resumenes = DROP_FIN + alertas).
# Instrumento de medida (se commitea). Solo lee; no escribe nada.
#   fw LOG                    firewall-agent.log de una corrida: totales, comprobacion de formato, intervalos con DROP,
#                             DROP no protegidos por intervalo situados respecto al episodio (reloj monotono).
#   bronce TIEMPOS DIR [S]    segmentos argus-*.csv de DIR con mtime en [estable, fin_cliente + S] (S=120):
#                             filas DROP (col 16 overall_threat_score = p1 de ddos_v2 si pasa la etapa 1; DROP <=> p1 > 0.5)
#                             por (src_ip, dst_ip, protocol). El bronce NO lleva ICMP (community_id vacio).
# Lectura del codigo (DAY311): el resumen cuenta todo final_decision DROP (zmq_subscriber.cpp:606); el FIN solo los de
# SU victima {dst, proto} (ddos_shadow_policy.hpp add_drop); los protegidos van a alertas antes de add_drop.
import csv
import os
import re
import sys
from collections import Counter

RE_RES = re.compile(r"\[SOMBRA-DDOS\] resumen: habilitada=(\d+) eventos=(\d+) flujo=(\d+) final_decision DROP=(\d+) "
                    r"ALLOW=(\d+) otro_o_vacio=(\d+) ts_evento_min=(-?\d+) ts_evento_max=(-?\d+) victimas_activas=(\d+)\s*$")
RE_PROT = re.compile(r"\[SOMBRA-DDOS\] protegidos: alertas=(\d+) dmz=(\d+) intranet=(\d+) externos_criticos=(\d+) "
                     r"por_defecto=(\d+)\s*$")
RE_MIT = re.compile(r"\[DDOS-MITIGACION\] resumen: modo=(\S+) bloquear=(\d+) renovar=(\d+) esperar=(\d+) "
                    r"rechazo_protegido=(\d+) rechazo_ip_invalida=(\d+) ")
RE_REG = re.compile(r"\[SOMBRA-DDOS\] (INICIO|FIN) victima=(\S+) proto=(\d+) inicio_s=(-?\d+)(?: fin_s=(-?\d+))?.* "
                    r"eventos_drop=(\d+) .*origenes=(\S*) primer_evento=")


def fw(path):
    res, prot, mit, regs = [], [], [], []
    malas = Counter()
    otros = Counter()
    with open(path, errors="replace") as f:
        for n, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if "[SOMBRA-DDOS] resumen:" in line:
                m = RE_RES.search(line)
                if m:
                    res.append((n, [int(x) for x in m.groups()]))
                else:
                    malas["resumen"] += 1
                    print(f"[MAL-FORMADA] resumen linea {n}: {line[:200]}")
            elif "[SOMBRA-DDOS] protegidos:" in line:
                m = RE_PROT.search(line)
                if m:
                    prot.append((n, int(m.group(1))))
                else:
                    malas["protegidos"] += 1
                    print(f"[MAL-FORMADA] protegidos linea {n}: {line[:200]}")
            elif "[DDOS-MITIGACION] resumen:" in line:
                m = RE_MIT.search(line)
                if m:
                    mit.append((n, m.group(1), [int(x) for x in m.groups()[1:]]))
                else:
                    malas["mitigacion"] += 1
            elif re.search(r"\[SOMBRA-DDOS\] (INICIO|FIN) ", line):
                m = RE_REG.search(line)
                if m:
                    regs.append((n, m.group(1), m.group(2), int(m.group(3)), int(m.group(4)),
                                 int(m.group(5)) if m.group(5) else None, int(m.group(6)), m.group(7)))
                else:
                    malas["registro"] += 1
                    print(f"[MAL-FORMADA] registro linea {n}: {line[:200]}")
            for k in ("FIN victima=", "INICIO victima=", "primer DROP recibido", "ALERTA_PROTEGIDO",
                      "evento DROP sin network_features", "[TIMEBASE-ANOMALIA]"):
                if k in line:
                    otros[k] += 1
    RES = sum(r[1][3] for r in res)
    AL = prot[-1][1] if prot else 0
    FIN = sum(r[6] for r in regs if r[1] == "FIN")
    print(f"[P4] fichero={path}")
    print(f"[P4] lineas resumen={len(res)} protegidos={len(prot)} mitigacion={len(mit)} registros={len(regs)} "
          f"mal_formadas={dict(malas) if malas else 0}")
    print("[P4] apariciones: " + " ".join(f"'{k}'={otros[k]}" for k in (
        "FIN victima=", "INICIO victima=", "primer DROP recibido", "ALERTA_PROTEGIDO",
        "evento DROP sin network_features", "[TIMEBASE-ANOMALIA]")))
    print(f"[P4] DROP_resumenes={RES} DROP_FIN={FIN} alertas={AL} diferencia={RES - FIN - AL}")
    for r in regs:
        orig = r[7]
        suma = sum(int(x.rsplit(":", 1)[1]) for x in orig.split(",") if ":" in x)
        print(f"[P4] {r[1]} linea={r[0]} victima={r[2]}/{r[3]} inicio_s={r[4]} fin_s={r[5]} eventos_drop={r[6]} "
              f"origenes={orig} suma_origenes={suma}")
    ini = [r for r in regs if r[1] == "INICIO"]
    fin = [r for r in regs if r[1] == "FIN"]
    e0 = ini[0][4] if ini else None
    e1 = fin[-1][5] if fin else None
    # alertas acumuladas -> incremento por intervalo (la linea protegidos va justo detras de su resumen)
    al_por_res = {}
    j, prev = 0, 0
    for i, (n, _) in enumerate(res):
        nxt = res[i + 1][0] if i + 1 < len(res) else float("inf")
        cur = prev
        while j < len(prot) and prot[j][0] < nxt:
            if prot[j][0] > n:
                cur = prot[j][1]
            j += 1
        al_por_res[i] = cur - prev
        prev = cur
    mit_por_res = {}
    k = 0
    for i, (n, _) in enumerate(res):
        nxt = res[i + 1][0] if i + 1 < len(res) else float("inf")
        s = 0
        while k < len(mit) and mit[k][0] < nxt:
            if mit[k][0] > n:
                s += mit[k][2][0] + mit[k][2][1] + mit[k][2][2]
            k += 1
        mit_por_res[i] = s
    print(f"[P4] episodio (reloj monotono, s): inicio_s={e0} fin_s={e1}")
    print("[P4] intervalos con DROP>0 o victimas_activas>1:")
    print("[P4]   idx linea ts_min ts_max DROP d_alertas no_protegidos victimas_activas mitig(b+r+e) no_prot-mitig posicion")
    pos_sum = Counter()
    fuera_sum = Counter()  # no protegidos que NO pasaron por decidir con victima en episodio
    vmax = 0
    for i, (n, v) in enumerate(res):
        drop, tmin, tmax, vict = v[3], v[6], v[7], v[8]
        vmax = max(vmax, vict)
        nop = drop - al_por_res[i]
        if e0 is None:
            pos = "sin_episodio"
        elif tmax < e0:
            pos = "antes"
        elif e1 is not None and tmin > e1:
            pos = "despues"
        elif tmin >= e0 and (e1 is None or tmax <= e1):
            pos = "dentro"
        else:
            pos = "borde"
        if drop > 0 or vict > 1:
            pos_sum[pos] += nop
            fuera_sum[pos] += nop - mit_por_res[i]
            print(f"[P4]   {i} {n} {tmin} {tmax} {drop} {al_por_res[i]} {nop} {vict} {mit_por_res[i]} "
                  f"{nop - mit_por_res[i]} {pos}")
    print(f"[P4] no_protegidos por posicion: {dict(pos_sum)} total={sum(pos_sum.values())} "
          f"(= DROP_resumenes - alertas = {RES - AL}); victimas_activas_max={vmax}")
    print(f"[P4] no_protegidos - mitig por posicion: {dict(fuera_sum)} (modo mitigacion: "
          f"{sorted(set(m[1] for m in mit))}; solo discrimina si no es deshabilitada)")
    return 0 if not malas else 1


def bronce(tiempos, d, margen):
    t = {}
    with open(tiempos) as f:
        for line in f:
            p = line.split()
            if len(p) == 2:
                t[p[0]] = float(p[1])
    if "estable" not in t or "fin_cliente" not in t:
        print(f"[P4-BRONCE] FALLA: faltan marcas estable/fin_cliente en {tiempos}: {t}")
        return 1
    t0, t1 = t["estable"], t["fin_cliente"] + margen
    fich = sorted(x for x in os.listdir(d) if x.startswith("argus-") and x.endswith(".csv"))
    sel = [x for x in fich if t0 <= os.stat(os.path.join(d, x)).st_mtime <= t1]
    print(f"[P4-BRONCE] dir={d} segmentos_argus={len(fich)} en_ventana={len(sel)} ventana=[{t0:.0f}, {t1:.0f}]")
    drop, filas, malas, borde = Counter(), 0, 0, 0
    fs_min, fs_max = None, None
    for x in sel:
        with open(os.path.join(d, x), newline="") as f:
            for row in csv.reader(f):
                if len(row) != 19:
                    malas += 1
                    continue
                filas += 1
                try:
                    p1 = float(row[16])
                    fs = int(row[5])
                except ValueError:
                    malas += 1
                    continue
                fs_min = fs if fs_min is None else min(fs_min, fs)
                fs_max = fs if fs_max is None else max(fs_max, fs)
                if p1 == 0.5:
                    borde += 1
                if p1 > 0.5:
                    drop[(row[7], row[8], row[11])] += 1
    print(f"[P4-BRONCE] filas={filas} mal_formadas={malas} p1_igual_0.5={borde} flow_start_sec=[{fs_min}, {fs_max}]")
    print(f"[P4-BRONCE] filas DROP (p1 > 0.5) = {sum(drop.values())} por (src, dst, protocol):")
    for (s, dd, pr), c in sorted(drop.items(), key=lambda kv: -kv[1]):
        print(f"[P4-BRONCE]   {s} -> {dd} {pr} {c}")
    return 0


def main():
    a = sys.argv[1:]
    if len(a) == 2 and a[0] == "fw":
        return fw(a[1])
    if len(a) in (3, 4) and a[0] == "bronce":
        return bronce(a[1], a[2], float(a[3]) if len(a) == 4 else 120.0)
    print("uso: d311_p4_cuentas.py fw LOG | bronce TIEMPOS DIR [MARGEN_S]")
    return 2


if __name__ == "__main__":
    sys.exit(main())
