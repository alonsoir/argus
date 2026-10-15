#!/usr/bin/env python3
# DAY298 paso 1: estado de la victima en el evento (DDoSFeatures.victim_state = 16, enum VictimState).
# 0 = UNKNOWN porque en proto3 un campo ausente vale 0: eventos sin el campo (sniffer antiguo o sin snapshot)
# se leen como desconocido y el ml-detector aplica la etapa 1 antigua con aviso. Diseno:
# docs/ml-heads/diseno_etapa1_histeresis_day298.md, apartado 1. Atomico. Uso: --check | --apply
import os, sys

F = "protobuf/network_security.proto"
MARCA = "DAY298-VICTIM-STATE"
A_MSG = "// 🛡️ LEVEL 2 - DDoS Detection Features (10 features)\nmessage DDoSFeatures {\n"
ENUM = """// [DAY298-VICTIM-STATE] Estado de la victima (dst_ip, proto) en la ventana del agregador del kernel, segun la
// histeresis del sniffer. 0 = UNKNOWN a proposito (campo ausente en proto3): evento sin estado (sniffer antiguo
// o sin snapshot del lector) -> el ml-detector aplica la etapa 1 antigua (ratio >= k_ratio) con aviso.
enum VictimState {
  VICTIM_STATE_UNKNOWN        = 0;  // sin estado (campo ausente o sin snapshot)
  VICTIM_STATE_COLD           = 1;  // clave sin historia suficiente (seen < warm_windows); el ratio no significa nada
  VICTIM_STATE_NORMAL         = 2;  // caliente, sin presion: la etapa 1 usa ratio >= k_ratio
  VICTIM_STATE_UNDER_PRESSURE = 3;  // bajo_presion (entrada por k_in en caliente o por P_abs en frio); EWMA congelada
}

"""
A_FLD = "    float victim_pps = 15;  // d_pkts/window_ms de la ventana del kernel (dst_ip, proto). Sustituye a 10\n"
FLD = "    VictimState victim_state = 16;  // [DAY298-VICTIM-STATE] estado de la victima en esta ventana (ver enum)\n"

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        sys.exit("uso: d298_patch_proto.py --check | --apply")
    txt = open(F).read()
    if MARCA in txt:
        sys.exit(f"NO APLICABLE: {F} ya lleva {MARCA}")
    errores = []
    for nombre, ancla in (("cabecera de DDoSFeatures", A_MSG), ("campo victim_pps = 15", A_FLD)):
        if txt.count(ancla) != 1:
            errores.append(f"{nombre} aparece {txt.count(ancla)} veces, se esperaba 1")
    if "VictimState" in txt or "victim_state" in txt:
        errores.append("ya existe VictimState o victim_state en el proto")
    if errores:
        sys.exit("NO APLICABLE:\n  " + "\n  ".join(errores))
    nuevo = txt.replace(A_MSG, ENUM + A_MSG).replace(A_FLD, A_FLD + FLD)
    if sys.argv[1] == "--check":
        print("CHECK OK: enum VictimState antes de DDoSFeatures y campo victim_state = 16 tras victim_pps")
        return
    with open(F + ".tmp", "w") as o:
        o.write(nuevo)
    os.replace(F + ".tmp", F)
    print("APLICADO [DAY298-VICTIM-STATE]")

main()
