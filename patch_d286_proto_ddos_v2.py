#!/usr/bin/env python3
"""DAY286: contrato DDoS v2 (8 rasgos, solo trafico entrante) en network_security.proto.
Anade campos 11-15 al mensaje DDoSFeatures y anota como fuera del vector 2,3,4,6,9,10
(comentario, NO [deprecated]: con -Werror romperia a los lectores).
Idempotente, atomico. Uso: --check | --apply. No regenera, no compila, no commitea."""
import re, sys

PATH = "/vagrant/protobuf/network_security.proto"
ANCHOR = "    float resource_saturation_score = 10;"
MARK = "    // DAY286 contrato DDoS v2 (8 rasgos, solo trafico entrante; calculado una vez en el sniffer)"
NEW = [
    ("mean_packet_size", 11, "media de all_lengths del flujo, bytes"),
    ("reflection_signature", 12, "UDP desde puerto de servicio conocido a puerto alto. Sustituye a 4"),
    ("flow_packet_count", 13, "paquetes del flujo (contexto de packet_size_entropy)"),
    ("victim_rate_ratio", 14, "pps victima / max(EWMA previa, suelo). Sustituye a 9"),
    ("victim_pps", 15, "d_pkts/window_ms de la ventana del kernel (dst_ip, proto). Sustituye a 10"),
]
OLD = {
    "    float packet_symmetry = 2;": "FUERA DEL VECTOR DAY286: la captura no ve el trafico de vuelta",
    "    float source_ip_dispersion = 3;": "FUERA DEL VECTOR DAY286: hasta pcap multi-origen (H1)",
    "    float protocol_anomaly_score = 4;": "FUERA DEL VECTOR DAY286: ver 12",
    "    float traffic_amplification_factor = 6;": "FUERA DEL VECTOR DAY286: la captura no ve el trafico de vuelta",
    "    float traffic_escalation_rate = 9;": "FUERA DEL VECTOR DAY286: ver 14",
    "    float resource_saturation_score = 10;": "FUERA DEL VECTOR DAY286: ver 15",
}

def die(msg):
    print(f"ABORTO: {msg}")
    sys.exit(1)

mode = sys.argv[1] if len(sys.argv) > 1 else ""
if mode not in ("--check", "--apply"):
    die("uso: --check | --apply")

lines = open(PATH).read().split("\n")
hits = [i for i, l in enumerate(lines) if l.startswith(ANCHOR)]
if len(hits) != 1:
    die(f"ancla encontrada {len(hits)} veces (esperado 1)")
a = hits[0]
s = a
while s >= 0 and not re.match(r"^\s*message\s+\w+\s*\{", lines[s]):
    s -= 1
if s < 0:
    die("no encuentro el 'message' que contiene el ancla")
name = re.match(r"^\s*message\s+(\w+)", lines[s]).group(1)
depth, e = 0, None
for j in range(s, len(lines)):
    depth += lines[j].count("{") - lines[j].count("}")
    if depth == 0:
        e = j
        break
if e is None:
    die("llaves desbalanceadas")
block = lines[s:e + 1]
print(f"mensaje={name} lineas {s+1}-{e+1}")
for l in block:
    print(f"  | {l}")

present = [n for n, _, _ in NEW if any(re.search(rf"\b{n}\s*=", l) for l in block)]
if len(present) == len(NEW):
    print("YA APLICADO: los 5 campos existen. Nada que hacer.")
    sys.exit(0)
if present:
    die(f"aplicacion parcial previa: {present}")
nums = {int(m.group(1)) for l in block for m in [re.search(r"=\s*(\d+)\s*;", l)] if m}
if any(l.strip().startswith("reserved") for l in block):
    die("el mensaje tiene 'reserved': revisar a mano")
clash = nums & {n for _, n, _ in NEW}
if clash:
    die(f"numeros ya usados: {sorted(clash)}")
for old in OLD:
    if old not in block:
        die(f"no encuentro la linea vieja exacta (sin comentario): {old!r}")

new_lines = [MARK] + [f"    float {n} = {k};  // {c}" for n, k, c in NEW]
out = []
for i, l in enumerate(lines):
    if s <= i <= e and l in OLD:
        out.append(f"{l}  // {OLD[l]}")
    else:
        out.append(l)
    if i == a:
        out.extend(new_lines)

print("\nPlan:")
for l in new_lines:
    print(f"  + {l}")
for l in OLD:
    print(f"  ~ {l}  // {OLD[l]}")
if mode == "--check":
    print("\n--check: no se escribe nada.")
    sys.exit(0)
open(PATH, "w").write("\n".join(out))
chk = open(PATH).read()
miss = [n for n, _, _ in NEW if not re.search(rf"\bfloat {n} = \d+;", chk)]
if miss:
    die(f"verificacion tras escribir fallida: {miss}")
print("\nAPLICADO y verificado.")
