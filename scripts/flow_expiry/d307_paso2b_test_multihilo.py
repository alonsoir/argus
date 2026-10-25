#!/usr/bin/env python3
# DAY307 paso 2b — test_sharded_flow_multithread (FeatureExtractionUnderLoad) exigia has_ddos_embedded() tras populate.
# Tras el paso 2 populate ya no toca ddos_embedded: el test pasa a exigir la foto DDoS valida (ddos_v2_flow_snapshot)
# y que populate NO toque ddos_embedded. Este test se compila pero no esta registrado en ctest (deuda DAY307).
# Valida antes de escribir (sha256 de partida y de llegada, ancla unica). Reconoce "ya aplicado".
# Uso (Mac, raiz del repo): python3 scripts/flow_expiry/d307_paso2b_test_multihilo.py --check | --apply
import hashlib, os, sys
P = "sniffer/tests/test_sharded_flow_multithread.cpp"
ANTES = "2ce88e05e7e345c89a773f2cdc153c42d2347ff16e8e71b05eb527e16701786b"
DESPUES = "6ba16eab5369803a9c232b09980df584e7d6d7ad427cff51296a7249714923f9"
VIEJO = '                    // Validate features were populated\n                    if (proto_event.has_network_features() &&\n                        proto_event.network_features().has_ddos_embedded() &&\n'
NUEVO = '                    // [D307-PASO2] los 5 rasgos DDoS v2 salen de la foto en lock (ddos_v2_flow_snapshot), que\n                    // ring_consumer escribe en el protobuf; populate ya no toca ddos_embedded.\n                    DdosFlowSnap snap{};\n                    mgr.with_flow_stats(key, [&](const auto& fs) { snap = ml_extractor_->ddos_v2_flow_snapshot(fs); });\n\n                    // Validate features were populated\n                    if (proto_event.has_network_features() &&\n                        snap.valid &&\n                        !proto_event.network_features().has_ddos_embedded() &&\n'

def die(m):
    print("ABORTA: " + m)
    sys.exit(1)

def sha(b):
    return hashlib.sha256(b).hexdigest()

if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
    die("uso: --check | --apply")
if not os.path.isfile(P):
    die("no estoy en la raiz del repo (falta " + P + ")")
s = sha(open(P, "rb").read())
if s == DESPUES:
    print("[YA APLICADO] nada que hacer.")
    sys.exit(0)
if s != ANTES:
    die(f"{P} sha256 {s} no es el de partida")
t = open(P, encoding="utf-8").read()
if t.count(VIEJO) != 1:
    die(f"ancla x{t.count(VIEJO)} (esperado 1)")
n = t.replace(VIEJO, NUEVO)
if sha(n.encode("utf-8")) != DESPUES:
    die("el resultado no tendria el sha256 esperado")
print(f"[OK] editar {P} (FeatureExtractionUnderLoad: foto DDoS valida y populate sin ddos_embedded)")
if sys.argv[1] == "--check":
    print("[CHECK] todo valida; nada escrito. Repite con --apply.")
    sys.exit(0)
tmp = P + ".d307tmp"
with open(tmp, "w", encoding="utf-8") as f:
    f.write(n)
os.replace(tmp, P)
if sha(open(P, "rb").read()) != DESPUES:
    die("verificacion posterior fallida")
print("[APLICADO] paso 2b.")
