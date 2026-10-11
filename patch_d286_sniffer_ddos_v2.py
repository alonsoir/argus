#!/usr/bin/env python3
"""DAY286: el sniffer rellena el contrato DDoS v2 (campos 11,12,13,15) + centinelas 11-15.
Crea sniffer/include/ddos_contract_v2.hpp (funciones puras constexpr + static_assert).
Atomico (comprueba todas las anclas antes de escribir), idempotente (marca [DDOS-V2-D286]).
Uso: --check | --apply. No compila, no commitea."""
import os, sys

ROOT = "/vagrant/sniffer"
MARK = "[DDOS-V2-D286]"
HDR = f"{ROOT}/include/ddos_contract_v2.hpp"
HDR_TXT = """// sniffer/include/ddos_contract_v2.hpp
// [DDOS-V2-D286] Contrato DDoS v2: funciones puras, sin dependencias.
// Rasgos que dependen del paquete o de la ventana del kernel (no de FlowStatistics).
#pragma once
#include <cstdint>

namespace argus::ddos {

// Puertos de servicio UDP explotados en reflexion/amplificacion.
inline constexpr bool is_reflection_service_port(uint16_t p) noexcept {
    switch (p) {
        case 17: case 19: case 53: case 69: case 111: case 123: case 137: case 138:
        case 161: case 389: case 1434: case 1900: case 3702: case 5683: case 11211:
            return true;
        default:
            return false;
    }
}

// 1 si el paquete es UDP desde un puerto de servicio reflejable hacia un puerto alto.
inline constexpr float reflection_signature(uint8_t proto, uint16_t sport, uint16_t dport) noexcept {
    return (proto == 17 && is_reflection_service_port(sport) && dport >= 1024) ? 1.0f : 0.0f;
}

// Paquetes por segundo de la victima en la ventana del kernel. window_ms debe ser > 0.
inline constexpr float victim_pps(uint64_t d_pkts, uint64_t window_ms) noexcept {
    return static_cast<float>(static_cast<double>(d_pkts) * 1000.0 / static_cast<double>(window_ms));
}

// Tests en compilacion.
static_assert(reflection_signature(17, 53, 40000) == 1.0f, "DNS reflejado");
static_assert(reflection_signature(17, 123, 1024) == 1.0f, "NTP reflejado, limite 1024");
static_assert(reflection_signature(17, 40000, 53) == 0.0f, "consulta DNS legitima");
static_assert(reflection_signature(6, 53, 40000) == 0.0f, "TCP no cuenta");
static_assert(reflection_signature(17, 53, 1023) == 0.0f, "destino no alto");
static_assert(reflection_signature(17, 8080, 40000) == 0.0f, "puerto no reflejable");
static_assert(victim_pps(100, 1000) == 100.0f, "100 pkts en 1 s");
static_assert(victim_pps(50, 500) == 100.0f, "50 pkts en 0,5 s");

}  // namespace argus::ddos
"""

def die(m):
    print(f"ABORTO: {m}")
    sys.exit(1)

mode = sys.argv[1] if len(sys.argv) > 1 else ""
if mode not in ("--check", "--apply"):
    die("uso: --check | --apply")

# (fichero, ancla por strip(), lineas a insertar DESPUES con la indentacion del ancla)
EDITS = [
    (f"{ROOT}/src/userspace/ml_defender_features.cpp",
     "ddos->set_resource_saturation_score(extract_ddos_resource_saturation_score(flow));",
     [f"// {MARK} contrato v2 (8 rasgos, solo trafico entrante)",
      "ddos->set_mean_packet_size(calculate_mean(flow.all_lengths));",
      "ddos->set_flow_packet_count(static_cast<float>(flow.get_total_packets()));"]),
    (f"{ROOT}/src/userspace/ring_consumer.cpp",
     '#include "fast_detector.hpp"',
     [f'#include "ddos_contract_v2.hpp"  // {MARK}']),
    (f"{ROOT}/src/userspace/ring_consumer.cpp",
     "ddos->set_resource_saturation_score(MISSING_FEATURE_SENTINEL);",
     [f"// {MARK} centinelas del contrato v2",
      "ddos->set_mean_packet_size(MISSING_FEATURE_SENTINEL);",
      "ddos->set_reflection_signature(MISSING_FEATURE_SENTINEL);",
      "ddos->set_flow_packet_count(MISSING_FEATURE_SENTINEL);",
      "ddos->set_victim_rate_ratio(MISSING_FEATURE_SENTINEL);",
      "ddos->set_victim_pps(MISSING_FEATURE_SENTINEL);"]),
    (f"{ROOT}/src/userspace/ring_consumer.cpp",
     "ml_extractor_.populate_ml_defender_features(flow_stats, proto_event);",
     [f"// {MARK} reflection_signature: depende de la tupla del paquete, no de FlowStatistics",
      "proto_event.mutable_network_features()->mutable_ddos_embedded()->set_reflection_signature(",
      "    ::argus::ddos::reflection_signature(event.protocol, event.src_port, event.dst_port));"]),
    (f"{ROOT}/src/userspace/ring_consumer.cpp",
     "vw->set_snapshot_age_ms(r.age_ms);",
     [f"if (r.window_ms > 0) {{  // {MARK} victim_pps; la ventana de arranque deja el centinela",
      "    ev.mutable_network_features()->mutable_ddos_embedded()->set_victim_pps(",
      "        ::argus::ddos::victim_pps(r.d_pkts, r.window_ms));",
      "}"]),
]

files = {}
for path, _, _ in EDITS:
    if path not in files:
        if not os.path.exists(path):
            die(f"no existe {path}")
        files[path] = open(path).read().split("\n")

already = [p for p, ls in files.items() if any(MARK in l for l in ls)]
hdr_ok = os.path.exists(HDR) and open(HDR).read() == HDR_TXT
if len(already) == len(files) and hdr_ok:
    print("YA APLICADO: todos los ficheros llevan la marca y la cabecera existe. Nada que hacer.")
    sys.exit(0)
if already or os.path.exists(HDR):
    die(f"aplicacion parcial previa: marcados={already} cabecera_existe={os.path.exists(HDR)}")

plan = []
for path, anchor, add in EDITS:
    ls = files[path]
    hits = [i for i, l in enumerate(ls) if l.strip() == anchor]
    if len(hits) != 1:
        die(f"ancla {anchor!r} en {path}: {len(hits)} coincidencias (esperado 1)")
    plan.append((path, hits[0], add))

out = {p: list(ls) for p, ls in files.items()}
# insertar de abajo arriba por fichero para no desplazar indices
for path in out:
    for _, idx, add in sorted([x for x in plan if x[0] == path], key=lambda x: -x[1]):
        anc = out[path][idx]
        indent = anc[:len(anc) - len(anc.lstrip())]
        out[path][idx + 1:idx + 1] = [indent + a if a else a for a in add]

print("Plan:")
print(f"  crear {HDR}")
for path, idx, add in plan:
    print(f"  {path}:{idx+1} -> +{len(add)} lineas tras: {files[path][idx].strip()}")
    for a in add:
        print(f"      + {a}")
if mode == "--check":
    print("\n--check: no se escribe nada.")
    sys.exit(0)

with open(HDR, "w") as f:
    f.write(HDR_TXT)
for path, ls in out.items():
    with open(path, "w") as f:
        f.write("\n".join(ls))
for path in out:
    n = open(path).read().count(MARK)
    print(f"  verificado {path}: {n} marcas")
print("\nAPLICADO.")
