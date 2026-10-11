#!/usr/bin/env python3
"""DAY293 — patcher atómico (todo o nada) [DDOS-SHADOW-RELOJ-D293]: la sombra usa UN SOLO reloj, el de los eventos de
FLUJO (EVENT_KIND_FLOW). Medido en el E2E: los eventos de flujo llevan event_timestamp en segundos desde el arranque
(monotónico, ~33900) y otros eventos (cada ~30 s) en epoch (~1,79e9); mezclarlos congelaba el reloj de la sombra.
 - zmq_subscriber.hpp: contador sombra_flujo_.
 - zmq_subscriber.cpp: es_flujo; solo los eventos de flujo avanzan el reloj y alimentan la política; resumen con flujo=.
Uso: --check | --apply. Idempotente por la marca. No commitea."""
import sys
from pathlib import Path

MARK = "[DDOS-SHADOW-RELOJ-D293]"
FW = Path("/vagrant/firewall-acl-agent")
HPP = FW / "include/firewall/zmq_subscriber.hpp"
CPP = FW / "src/api/zmq_subscriber.cpp"


def fail(m):
    print("ABORTA:", m); sys.exit(1)


def repl(t, a, b, n):
    c = t.count(a)
    if c != 1:
        fail("%s: ancla encontrada %d veces" % (n, c))
    return t.replace(a, b)


def p_hpp(t):
    return repl(t, "    uint64_t sombra_eventos_ = 0;\n",
                "    uint64_t sombra_eventos_ = 0;\n    uint64_t sombra_flujo_ = 0;  // [DDOS-SHADOW-RELOJ-D293]\n", "hpp")


def p_cpp(t):
    a = "        const int64_t ts_s = static_cast<int64_t>(event.event_timestamp().seconds());\n"
    t = repl(t, a, a +
             "        // [DDOS-SHADOW-RELOJ-D293] un solo reloj: el de los eventos de FLUJO (monotónico desde el arranque). Otros\n"
             "        // tipos de evento llegan con event_timestamp en epoch (DEBT-EVENT-TIMESTAMP-TIMEBASE-001) y no lo mueven.\n"
             "        const bool es_flujo = (event.event_kind() == protobuf::EVENT_KIND_FLOW);\n", "cpp es_flujo")
    t = repl(t,
             "            if (sombra_eventos_ == 0 || ts_s < sombra_ts_min_) sombra_ts_min_ = ts_s;\n"
             "            if (sombra_eventos_ == 0 || ts_s > sombra_ts_max_) sombra_ts_max_ = ts_s;\n"
             "            ++sombra_eventos_;\n",
             "            if (es_flujo) {  // [DDOS-SHADOW-RELOJ-D293] rango de ts solo de los eventos de flujo\n"
             "                if (sombra_flujo_ == 0 || ts_s < sombra_ts_min_) sombra_ts_min_ = ts_s;\n"
             "                if (sombra_flujo_ == 0 || ts_s > sombra_ts_max_) sombra_ts_max_ = ts_s;\n"
             "                ++sombra_flujo_;\n"
             "            }\n"
             "            ++sombra_eventos_;\n", "cpp contadores")
    t = repl(t, '                          << " eventos=" << sombra_eventos_ << " final_decision DROP=" << sombra_drop_\n',
             '                          << " eventos=" << sombra_eventos_ << " flujo=" << sombra_flujo_\n'
             '                          << " final_decision DROP=" << sombra_drop_\n', "cpp resumen")
    t = repl(t, "                sombra_eventos_ = 0;\n",
             "                sombra_eventos_ = 0;\n                sombra_flujo_ = 0;\n", "cpp reset")
    t = repl(t, "        if (config_.ddos_shadow.enabled) {\n            for (const auto& rec : ddos_shadow_.advance(ts_s)) {\n",
             "        if (config_.ddos_shadow.enabled && es_flujo) {\n            for (const auto& rec : ddos_shadow_.advance(ts_s)) {\n",
             "cpp advance")
    return repl(t, "        if (!drop || !config_.ddos_shadow.enabled) {\n",
                "        if (!drop || !config_.ddos_shadow.enabled || !es_flujo) {\n", "cpp drop")


if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
    fail("uso: --check | --apply")
cambios = {}
for p, f in ((HPP, p_hpp), (CPP, p_cpp)):
    t = p.read_text()
    if MARK in t:
        print("%s: ya aplicado" % p.name); continue
    cambios[p] = f(t); print("%s: preparado" % p.name)
if sys.argv[1] == "--apply":
    for p, t in cambios.items():
        p.with_suffix(p.suffix + ".tmp_d293").write_text(t)
    for p in cambios:
        p.with_suffix(p.suffix + ".tmp_d293").replace(p)
    print("APLICADO en %d fichero(s)" % len(cambios))
else:
    print("CHECK OK (nada escrito)")
