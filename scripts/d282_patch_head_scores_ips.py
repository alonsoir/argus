#!/usr/bin/env python3
# DAY282 — anade src/dst (ip:puerto) a [HEAD-SCORES]. Idempotente, aborta si un ancla no casa 1 vez.
import sys, pathlib
p = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/vagrant/ml-detector/src/zmq_handler.cpp")
src = p.read_text()
if "[HEAD-SCORES] event={}, src=" in src:
    sys.exit("ABORT: ya parcheado")
A_FMT  = "[HEAD-SCORES] event={}, gate={}"
A_ARGS = "event.event_id(), hs_gate ? 1 : 0"
for a in (A_FMT, A_ARGS):
    n = src.count(a)
    if n != 1:
        sys.exit(f"ABORT: ancla aparece {n} veces: {a!r}")
src = src.replace(A_FMT, "[HEAD-SCORES] event={}, src={}:{}, dst={}:{}, gate={}")
src = src.replace(A_ARGS,
    "event.event_id(),\n"
    "                  event.network_features().source_ip(), event.network_features().source_port(),\n"
    "                  event.network_features().destination_ip(), event.network_features().destination_port(),\n"
    "                  hs_gate ? 1 : 0")
p.write_text(src)
print("OK: src/dst anadidos en", p)
