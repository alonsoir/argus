#!/usr/bin/env python3
"""DAY293 — patcher atómico (todo o nada) [DDOS-SHADOW-OBS-D293]: observabilidad de la sombra DDoS del firewall.
 - ddos_shadow_policy.hpp: DdosShadowParams::resumen_s.
 - config_loader.cpp: ddos_shadow.resumen_s validado ([1, 3600], defecto 10) con [CONFIG-DEFAULT].
 - firewall.json: resumen_s + _doc.
 - zmq_subscriber.hpp: contadores de la sombra (solo hilo receptor).
 - zmq_subscriber.cpp: resumen periódico por reloj de pared (eventos, final_decision DROP/ALLOW/otro, ts min/max,
   víctimas, habilitada), primer DROP recibido, e INICIO/FIN también por std::cout (firewall-agent.log).
 - main.cpp: anuncia resumen_s.
Uso: --check | --apply. Idempotente por la marca. No commitea."""
import json, sys
from pathlib import Path

MARK = "[DDOS-SHADOW-OBS-D293]"
FW = Path("/vagrant/firewall-acl-agent")
F = {
    "pol": FW / "include/firewall/ddos_shadow_policy.hpp",
    "cfg": FW / "src/core/config_loader.cpp",
    "json": FW / "config/firewall.json",
    "hpp": FW / "include/firewall/zmq_subscriber.hpp",
    "cpp": FW / "src/api/zmq_subscriber.cpp",
    "main": FW / "src/main.cpp",
}


def fail(m):
    print("ABORTA:", m); sys.exit(1)


def once(t, a, n):
    c = t.count(a)
    if c != 1:
        fail("%s: ancla encontrada %d veces" % (n, c))


def after(t, a, i, n):
    once(t, a, n); return t.replace(a, a + i)


def repl(t, a, b, n):
    once(t, a, n); return t.replace(a, b)


def p_pol(t):
    return after(t, "    int hold_s = 30;\n", "    int resumen_s = 10;  // [DDOS-SHADOW-OBS-D293] segundos entre resúmenes (reloj de pared)\n", "pol")


def p_cfg(t):
    return after(t, '            d.hold_s = get_int("hold_s", 30, 1, 3600);\n',
                 '            d.resumen_s = get_int("resumen_s", 10, 1, 3600);  // [DDOS-SHADOW-OBS-D293]\n', "cfg")


def p_json(t):
    t = repl(t, '    "hold_s": 30\n  },\n', '    "hold_s": 30,\n    "resumen_s": 10\n  },\n', "json resumen_s")
    return repl(t, "hold_s: entero en [1, 3600], segundos sin positiva para FIN (defecto 30).",
                "hold_s: entero en [1, 3600], segundos sin positiva para FIN (defecto 30). resumen_s: entero en [1, 3600], "
                "segundos (reloj de pared) entre resúmenes [SOMBRA-DDOS] resumen (defecto 10) [DDOS-SHADOW-OBS-D293].", "json doc")


def p_hpp(t):
    L = t.splitlines(keepends=True)
    i = next((k for k, l in enumerate(L) if l.startswith("#include")), None)
    if i is None:
        fail("hpp: sin #include")
    t = "".join(L[:i]) + "#include <chrono>  // [DDOS-SHADOW-OBS-D293]\n" + "".join(L[i:])
    return after(t, "    ::mldefender::firewall::DdosShadowPolicy ddos_shadow_{config_.ddos_shadow};  ///< [DDOS-SHADOW-D293]\n",
                 "    // [DDOS-SHADOW-OBS-D293] observabilidad de la sombra (solo hilo receptor)\n"
                 "    uint64_t sombra_eventos_ = 0;\n"
                 "    uint64_t sombra_drop_ = 0;\n"
                 "    uint64_t sombra_allow_ = 0;\n"
                 "    uint64_t sombra_otro_ = 0;\n"
                 "    int64_t sombra_ts_min_ = 0;\n"
                 "    int64_t sombra_ts_max_ = 0;\n"
                 "    bool sombra_primer_drop_ = false;\n"
                 "    std::chrono::steady_clock::time_point sombra_ultimo_resumen_{std::chrono::steady_clock::now()};\n", "hpp miembros")


CPP_A1 = "        const int64_t ts_s = static_cast<int64_t>(event.event_timestamp().seconds());\n"
CPP_I1 = r"""        {  // [DDOS-SHADOW-OBS-D293] contadores y resumen periódico por reloj de pared, siempre visible (std::cout)
            const std::string fd = event.has_provenance() ? event.provenance().final_decision() : std::string();
            if (sombra_eventos_ == 0 || ts_s < sombra_ts_min_) sombra_ts_min_ = ts_s;
            if (sombra_eventos_ == 0 || ts_s > sombra_ts_max_) sombra_ts_max_ = ts_s;
            ++sombra_eventos_;
            if (fd == "DROP") {
                ++sombra_drop_;
            } else if (fd == "ALLOW") {
                ++sombra_allow_;
            } else {
                ++sombra_otro_;
            }
            const auto ahora = std::chrono::steady_clock::now();
            if (ahora - sombra_ultimo_resumen_ >= std::chrono::seconds(config_.ddos_shadow.resumen_s)) {
                std::cout << "[SOMBRA-DDOS] resumen: habilitada=" << (config_.ddos_shadow.enabled ? 1 : 0)
                          << " eventos=" << sombra_eventos_ << " final_decision DROP=" << sombra_drop_
                          << " ALLOW=" << sombra_allow_ << " otro_o_vacio=" << sombra_otro_
                          << " ts_evento_min=" << sombra_ts_min_ << " ts_evento_max=" << sombra_ts_max_
                          << " victimas_activas=" << ddos_shadow_.victims() << std::endl;
                sombra_eventos_ = 0;
                sombra_drop_ = 0;
                sombra_allow_ = 0;
                sombra_otro_ = 0;
                sombra_ultimo_resumen_ = ahora;
            }
        }
"""
CPP_A2 = '                FIREWALL_LOG_WARN("[SOMBRA-DDOS]", "registro", ::mldefender::firewall::format_ddos_shadow_record(rec));\n'
CPP_N2 = (CPP_A2 +
          '                std::cout << "[SOMBRA-DDOS] " << ::mldefender::firewall::format_ddos_shadow_record(rec)\n'
          '                          << std::endl;  // [DDOS-SHADOW-OBS-D293]\n')
CPP_A3 = "                              p1, ratio, event.event_id(), modelo);\n"
CPP_I3 = r"""        if (!sombra_primer_drop_) {  // [DDOS-SHADOW-OBS-D293]
            sombra_primer_drop_ = true;
            std::cout << "[SOMBRA-DDOS] primer DROP recibido: ts_s=" << ts_s << " victima=" << nf2.destination_ip()
                      << " proto=" << nf2.protocol_number() << " origen=" << nf2.source_ip() << " ratio=" << ratio
                      << " p1=" << p1 << " modelo=" << modelo << " evento=" << event.event_id() << std::endl;
        }
"""


def p_cpp(t):
    t = after(t, CPP_A1, CPP_I1, "cpp contadores")
    t = repl(t, CPP_A2, CPP_N2, "cpp INICIO/FIN cout")
    return after(t, CPP_A3, CPP_I3, "cpp primer DROP")


def p_main(t):
    return repl(t, '<< " hold_s=" << config.ddos_shadow.hold_s << " (solo registra, no bloquea)" << std::endl;\n',
                '<< " hold_s=" << config.ddos_shadow.hold_s << " resumen_s=" << config.ddos_shadow.resumen_s\n'
                '                  << " (solo registra, no bloquea)" << std::endl;  // [DDOS-SHADOW-OBS-D293]\n', "main")


P = {"pol": p_pol, "cfg": p_cfg, "json": p_json, "hpp": p_hpp, "cpp": p_cpp, "main": p_main}
if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
    fail("uso: --check | --apply")
cambios = {}
for k, f in P.items():
    t = F[k].read_text()
    if MARK in t:
        print("%s: ya aplicado" % F[k].name); continue
    cambios[k] = f(t); print("%s: preparado" % F[k].name)
if "json" in cambios:
    json.loads(cambios["json"]); print("firewall.json: JSON válido tras el cambio")
if sys.argv[1] == "--apply":
    for k, t in cambios.items():
        F[k].with_suffix(F[k].suffix + ".tmp_d293").write_text(t)
    for k in cambios:
        F[k].with_suffix(F[k].suffix + ".tmp_d293").replace(F[k])
    print("APLICADO en %d fichero(s)" % len(cambios))
else:
    print("CHECK OK (nada escrito)")
