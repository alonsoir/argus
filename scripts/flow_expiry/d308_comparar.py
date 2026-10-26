#!/usr/bin/env python3
# DAY308 — comparador de paridad con tolerancia del paso 1 (estadisticos incrementales en FlowStatistics).
# SOLO MEDIDA. Criterios escritos antes de medir en docs/ml-heads/day308_paso1_diseno.md, seccion 3.
#
# Uso: d308_comparar.py REFERENCIA.tsv NUEVO.tsv ORACULO.tsv
#   REFERENCIA = logs/lab/day307/paridad/antes.tsv (codigo de antes del paso 1)
#   NUEVO      = salida principal de d308_paridad_tolerancia (codigo a comprobar)
#   ORACULO    = segunda salida de d308_paridad_tolerancia (misma corrida que NUEVO)
#
# Clases (seccion 2 del doc):
#   E: todo campo que no este en V ni en D -> NUEVO identico a REFERENCIA, texto exacto.
#   V: desviaciones y derivados -> NUEVO dentro de tolerancia del ORACULO. Se informa tambien REFERENCIA
#      contra ORACULO (el error del calculo viejo), por tramo de tamano del flujo. Esto ultimo no es criterio.
#   D: escalones sobre el cv -> NUEVO igual al ORACULO; se cuentan y listan los cambios REFERENCIA -> NUEVO.
# Un campo ausente vale 0 (proto3 no escribe ceros).
# Tolerancias (2 ulp de float = 2^-23 relativo; los derivados heredan el error de lo que derivan):
#   desviaciones: |a-b| <= 2^-23 * max(|a|,|b|)
#   packet_length_variance (std*std): |a-b| <= 2^-22 * max(|a|,|b|)
#   consistencias (1 - cociente, valores en [0,1] o centinela): |a-b| <= 2^-22, centinela exacto
# Salida: un informe y codigo 0 solo si E, V y D cumplen.
import sys

STD = ["forward_packet_length_std", "backward_packet_length_std", "flow_inter_arrival_time_std",
       "forward_inter_arrival_time_std", "backward_inter_arrival_time_std", "packet_length_std"]
VAR = ["packet_length_variance"]
CONS = ["ransomware_embedded.behavior_consistency", "traffic_classification.temporal_consistency",
        "internal_anomaly.protocol_regularity", "internal_anomaly.packet_size_consistency"]
D = ["ransomware_embedded.temporal_pattern", "internal_anomaly.temporal_anomaly_score"]
V = STD + VAR + CONS
NO_E = set(V + D)
CENTINELA = -9999.0
TRAMOS = ["1-20", "21-500", "501+"]


def tramo(n):
    return 0 if n <= 20 else (1 if n <= 500 else 2)


def campos(resto):
    d = {}
    for par in resto.rstrip(";").split(";"):
        if par:
            k, v = par.split("=", 1)
            d[k] = v
    return d


def tol(nombre, a, b):
    if nombre in CONS:
        if a == CENTINELA or b == CENTINELA:
            return a == b
        return abs(a - b) <= 2.0 ** -22
    escala = max(abs(a), abs(b))
    f = 2.0 ** -22 if nombre in VAR else 2.0 ** -23
    return abs(a - b) <= f * escala


def rel(a, b):
    escala = max(abs(a), abs(b))
    return 0.0 if escala == 0 else abs(a - b) / escala


def main():
    if len(sys.argv) != 4:
        print("uso: d308_comparar.py REFERENCIA.tsv NUEVO.tsv ORACULO.tsv")
        return 2
    fr, fn, fo = (open(p, encoding="ascii") for p in sys.argv[1:])
    cab = [fr.readline(), fn.readline(), fo.readline()]
    if cab[0] != cab[1]:
        print("ABORTA: cabeceras distintas REFERENCIA/NUEVO:", cab[0].strip(), "|", cab[1].strip())
        return 2
    e_mal, e_ej = 0, []
    v_mal = {k: [0, 0, 0] for k in V}            # NUEVO fuera de tolerancia, por tramo
    v_ref_mal = {k: [0, 0, 0] for k in V}        # REFERENCIA fuera de tolerancia (informativo)
    v_ref_max = {k: [0.0, 0.0, 0.0] for k in V}  # error relativo maximo REFERENCIA vs ORACULO
    v_new_max = {k: [0.0, 0.0, 0.0] for k in V}
    v_ej = []
    d_mal, d_cambios, d_ej = {k: 0 for k in D}, {k: 0 for k in D}, []
    ev_tramo = [0, 0, 0]
    total = 0
    for lr, ln, lo in zip(fr, fn, fo):
        ir, rr = lr.rstrip("\n").split("\t", 1)
        i_n, rn = ln.rstrip("\n").split("\t", 1)
        io, nflujo, ro = lo.rstrip("\n").split("\t", 2)
        if not (ir == i_n == io):
            print("ABORTA: eventos desalineados", ir, i_n, io)
            return 2
        total += 1
        t = tramo(int(nflujo))
        ev_tramo[t] += 1
        cr, cn, co = campos(rr), campos(rn), campos(ro)
        er = {k: v for k, v in cr.items() if k not in NO_E}
        en = {k: v for k, v in cn.items() if k not in NO_E}
        if er != en:
            e_mal += 1
            if len(e_ej) < 5:
                dif = sorted(k for k in set(er) | set(en) if er.get(k) != en.get(k))
                e_ej.append((ir, [(k, er.get(k), en.get(k)) for k in dif[:4]]))
        for k in V:
            a_n, a_r, a_o = float(cn.get(k, 0)), float(cr.get(k, 0)), float(co[k])
            if not tol(k, a_n, a_o):
                v_mal[k][t] += 1
                if len(v_ej) < 10:
                    v_ej.append((ir, nflujo, k, a_n, a_o))
            if not tol(k, a_r, a_o):
                v_ref_mal[k][t] += 1
            if a_o != CENTINELA and a_r != CENTINELA:
                v_ref_max[k][t] = max(v_ref_max[k][t], rel(a_r, a_o))
            if a_o != CENTINELA and a_n != CENTINELA:
                v_new_max[k][t] = max(v_new_max[k][t], rel(a_n, a_o))
        for k in D:
            a_n, a_r, a_o = float(cn.get(k, 0)), float(cr.get(k, 0)), float(co[k])
            if a_n != a_o:
                d_mal[k] += 1
            if a_n != a_r:
                d_cambios[k] += 1
                if len(d_ej) < 20:
                    d_ej.append((ir, nflujo, k, a_r, a_n, co["cv_iat"]))
    sobra = [f.readline() for f in (fr, fn, fo)]
    if any(sobra):
        print("ABORTA: ficheros de distinta longitud")
        return 2

    print(f"eventos={total} por_tramo " + " ".join(f"{TRAMOS[j]}={ev_tramo[j]}" for j in range(3)))
    ok_e = e_mal == 0
    print(f"[E] eventos con algun campo E distinto: {e_mal}  -> {'CUMPLE' if ok_e else 'FALLA'}")
    for ej in e_ej:
        print("    ej evento", ej[0], ej[1])
    ok_v = all(sum(v) == 0 for v in v_mal.values())
    print(f"[V] NUEVO fuera de tolerancia del ORACULO: {sum(sum(v) for v in v_mal.values())}  -> "
          f"{'CUMPLE' if ok_v else 'FALLA'}")
    print("    campo | NUEVO fuera (1-20/21-500/501+) | NUEVO err_rel_max | REFERENCIA fuera | REFERENCIA err_rel_max")
    for k in V:
        print(f"    {k} | {'/'.join(map(str, v_mal[k]))} | "
              f"{'/'.join(f'{x:.2e}' for x in v_new_max[k])} | {'/'.join(map(str, v_ref_mal[k]))} | "
              f"{'/'.join(f'{x:.2e}' for x in v_ref_max[k])}")
    for ej in v_ej:
        print("    ej NUEVO fuera: evento=%s n_flujo=%s %s nuevo=%r oraculo=%r" % ej)
    ok_d = all(v == 0 for v in d_mal.values())
    print(f"[D] NUEVO distinto del escalon del ORACULO: {sum(d_mal.values())}  -> {'CUMPLE' if ok_d else 'FALLA'}")
    for k in D:
        print(f"    {k}: cambios REFERENCIA->NUEVO={d_cambios[k]} NUEVO!=ORACULO={d_mal[k]}")
    for ej in d_ej:
        print("    ej cambio: evento=%s n_flujo=%s %s referencia=%s nuevo=%s cv_oraculo=%s" % ej)
    ok = ok_e and ok_v and ok_d
    print("VEREDICTO:", "CUMPLE" if ok else "FALLA")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
