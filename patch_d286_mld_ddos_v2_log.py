#!/usr/bin/env python3
"""DAY286: linea de observacion [DDOS-V2] en el ml-detector (debug, sin coste sin verbose).
Imprime ddos_embedded tal como llega del sniffer. Solo observacion.
Atomico, idempotente (marca [DDOS-V2-D286]). Uso: --check | --apply."""
import sys

PATH = "/vagrant/ml-detector/src/zmq_handler.cpp"
MARK = "[DDOS-V2-D286]"
ANCHOR = "// ADR-012 PHASE 2d — invoke plugins post-inferencia (Consejo DAY 111)"
BLOCK = [
    f"if (logger_->should_log(spdlog::level::debug)) {{  // {MARK} contrato v2 tal como llega del sniffer (observacion)",
    "    const auto& dv = event.network_features().ddos_embedded();",
    '    logger_->debug("[DDOS-V2] event={}, src={}:{}, dst={}:{}, syn_ack={:.3f}, mean_size={:.1f}, refl={:.0f}, entropy={:.3f}, pkts={:.0f}, completion={:.2f}, vratio={:.3f}, vpps={:.1f}",',
    "                   event.event_id(),",
    "                   event.network_features().source_ip(), event.network_features().source_port(),",
    "                   event.network_features().destination_ip(), event.network_features().destination_port(),",
    "                   dv.syn_ack_ratio(), dv.mean_packet_size(), dv.reflection_signature(),",
    "                   dv.packet_size_entropy(), dv.flow_packet_count(), dv.flow_completion_rate(),",
    "                   dv.victim_rate_ratio(), dv.victim_pps());",
    "}",
]

def die(m):
    print(f"ABORTO: {m}")
    sys.exit(1)

mode = sys.argv[1] if len(sys.argv) > 1 else ""
if mode not in ("--check", "--apply"):
    die("uso: --check | --apply")
ls = open(PATH).read().split("\n")
if any(MARK in l for l in ls):
    print("YA APLICADO. Nada que hacer.")
    sys.exit(0)
hits = [i for i, l in enumerate(ls) if l.strip() == ANCHOR]
if len(hits) != 1:
    die(f"ancla: {len(hits)} coincidencias (esperado 1)")
i = hits[0]
indent = ls[i][:len(ls[i]) - len(ls[i].lstrip())]
new = [indent + b for b in BLOCK]
print(f"Plan: insertar {len(new)} lineas ANTES de {PATH}:{i+1}")
for n in new:
    print(f"  + {n}")
if mode == "--check":
    print("\n--check: no se escribe nada.")
    sys.exit(0)
ls[i:i] = new
open(PATH, "w").write("\n".join(ls))
print(f"\nAPLICADO. marcas={open(PATH).read().count(MARK)}")
