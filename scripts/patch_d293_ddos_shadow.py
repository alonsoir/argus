#!/usr/bin/env python3
"""DAY293 — patcher atómico (todo o nada) [DDOS-SHADOW-D293]: firewall en SOMBRA + overall_threat_score de ddos_v2.
 ml-detector/src/zmq_handler.cpp       overall_threat_score = p1 de ddos_v2 (opción b); final_score sigue para usos internos.
 firewall-acl-agent/config/firewall.json  dry_run true + bloque ddos_shadow (_doc, rangos, defecto).
 .../include/firewall/config_loader.hpp   include + DdosShadowParams ddos_shadow en FirewallAgentConfig.
 .../src/core/config_loader.cpp           validación explícita + [CONFIG-DEFAULT].
 .../include/firewall/zmq_subscriber.hpp  include, Config::ddos_shadow, miembro ddos_shadow_.
 .../src/api/zmq_subscriber.cpp           compuerta: final_decision (no level1); DROP -> sombra; pasos 5-8 no se ejecutan.
 .../src/main.cpp                         copia la config y la anuncia.
 .../CMakeLists.txt                       test_ddos_shadow_policy.
Requiere los ficheros nuevos ddos_shadow_policy.hpp y tests/unit/test_ddos_shadow_policy.cpp.
Uso: --check | --apply. Idempotente por la marca. No commitea."""
import json, sys
from pathlib import Path

MARK = "[DDOS-SHADOW-D293]"
V = Path("/vagrant")
FW = V / "firewall-acl-agent"
F = {
    "zh": V / "ml-detector/src/zmq_handler.cpp",
    "json": FW / "config/firewall.json",
    "cfg_hpp": FW / "include/firewall/config_loader.hpp",
    "cfg_cpp": FW / "src/core/config_loader.cpp",
    "sub_hpp": FW / "include/firewall/zmq_subscriber.hpp",
    "sub_cpp": FW / "src/api/zmq_subscriber.cpp",
    "main": FW / "src/main.cpp",
    "cmake": FW / "CMakeLists.txt",
}
NUEVOS = [FW / "include/firewall/ddos_shadow_policy.hpp", FW / "tests/unit/test_ddos_shadow_policy.cpp"]


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


def first_include(t, ins, n):
    L = t.splitlines(keepends=True)
    i = next((k for k, l in enumerate(L) if l.startswith("#include")), None)
    if i is None:
        fail("%s: sin #include" % n)
    return "".join(L[:i]) + ins + "".join(L[i:])


def p_zh(t):
    t = after(t, "        bool ddos_v2_attack = false;\n",
              "        double ddos_v2_score = 0.0;  // [DDOS-SHADOW-D293] p1 de ddos_v2 si pasa la etapa 1; 0 si no\n", "zh score")
    t = after(t, "            ddos_v2_attack = (r2.clase == 1);\n",
              "            ddos_v2_score = r2.stage1 ? r2.p1 : 0.0;  // [DDOS-SHADOW-D293]\n", "zh asignación")
    return repl(t, "        event.set_overall_threat_score(final_score);\n",
                "        // [DDOS-SHADOW-D293] opción (b): overall_threat_score = p1 de ddos_v2, coherente con final_decision. La puntuación\n"
                "        // dual sigue en final_score solo para usos internos (umbral RAG, log, veredicto MALICIOUS/BENIGN).\n"
                "        event.set_overall_threat_score(ddos_v2_score);\n", "zh overall")


def p_json(t):
    t = repl(t, '    "dry_run": false,\n', '    "dry_run": true,\n', "json dry_run")
    return after(t, '    "max_processing_delay_ms": 10\n  },\n', """  "ddos_shadow": {
    "_doc": "[DDOS-SHADOW-D293] Política por víctima {dst_ip, proto} en SOMBRA (docs/ml-heads/bloque1_day293.md): solo registra [SOMBRA-DDOS] INICIO/FIN, no bloquea. Ventanas de 1 s por marca de tiempo del evento. enabled: true|false (defecto true). m: entero en [1, 1000], eventos DROP mínimos para que una ventana sea positiva (defecto 5). n: entero en [1, 60], ventanas de la cola (defecto 5). k: entero en [1, n], positivas en la cola para INICIO (defecto 3). hold_s: entero en [1, 3600], segundos sin positiva para FIN (defecto 30). Campo ausente o inválido: defecto con [CONFIG-DEFAULT] y el agente arranca igual. Valores de LABORATORIO (validados solo en latencia; frente a FP pendientes de la batería v3).",
    "enabled": true,
    "m": 5,
    "k": 3,
    "n": 5,
    "hold_s": 30
  },
""", "json bloque")


def p_cfg_hpp(t):
    t = after(t, "#include <json/json.h>\n", '#include "firewall/ddos_shadow_policy.hpp"  // [DDOS-SHADOW-D293]\n', "cfg_hpp include")
    return after(t, "    AutonomyConfig autonomy;   // DAY 155 — DEBT-FIREWALL-DENY-SELECTIVE-001\n",
                 "    DdosShadowParams ddos_shadow;  // [DDOS-SHADOW-D293] política por víctima en sombra\n", "cfg_hpp campo")


CFG_CPP_I = r"""
    // [DDOS-SHADOW-D293] política por víctima en sombra. El JSON manda; campo ausente o inválido -> defecto validado,
    // aviso [CONFIG-DEFAULT] con campo, formato y límites, y el agente arranca igual. Validación explícita (sin get_optional).
    {
        ::mldefender::firewall::DdosShadowParams d;
        const Json::Value s = root.isMember("ddos_shadow") ? root["ddos_shadow"] : Json::Value(Json::nullValue);
        if (!s.isObject()) {
            std::cerr << "[CONFIG-DEFAULT] ddos_shadow ausente o no es un objeto: enabled=true m=5 k=3 n=5 hold_s=30\n";
        } else {
            auto get_int = [&s](const char* name, int def, int lo, int hi) -> int {
                if (s.isMember(name) && s[name].isInt() && s[name].asInt() >= lo && s[name].asInt() <= hi) {
                    return s[name].asInt();
                }
                std::cerr << "[CONFIG-DEFAULT] ddos_shadow." << name << " ausente, no entero o fuera de rango (entero en ["
                          << lo << ", " << hi << "]): se usa " << def << "\n";
                return def;
            };
            if (s.isMember("enabled") && s["enabled"].isBool()) {
                d.enabled = s["enabled"].asBool();
            } else {
                std::cerr << "[CONFIG-DEFAULT] ddos_shadow.enabled ausente o no booleano (formato true|false): se usa true\n";
            }
            d.m = get_int("m", 5, 1, 1000);
            d.n = get_int("n", 5, 1, 60);
            d.k = get_int("k", d.n < 3 ? d.n : 3, 1, d.n);
            d.hold_s = get_int("hold_s", 30, 1, 3600);
        }
        config.ddos_shadow = d;
    }
"""


def p_cfg_cpp(t):
    return after(t, '    config.irp = parse_irp("/etc/ml-defender/firewall-acl-agent/isolate.json");\n', CFG_CPP_I, "cfg_cpp")


def p_sub_hpp(t):
    t = first_include(t, '#include "firewall/ddos_shadow_policy.hpp"  // [DDOS-SHADOW-D293]\n', "sub_hpp")
    t = after(t, "        std::string crypto_token;        ///< Decryption key (hex)\n",
              "        ::mldefender::firewall::DdosShadowParams ddos_shadow;  ///< [DDOS-SHADOW-D293] política por víctima en sombra\n",
              "sub_hpp Config")
    return after(t, "    mutable Stats stats_;                ///< Runtime statistics\n",
                 "    ::mldefender::firewall::DdosShadowPolicy ddos_shadow_{config_.ddos_shadow};  ///< [DDOS-SHADOW-D293]\n",
                 "sub_hpp miembro")


SUB_A = """    // Only process if attack was detected at Level 1
    if (!ml.attack_detected_level1()) {
        FIREWALL_LOG_DEBUG("No Level 1 attack detected, skipping",
            "level1_confidence", ml.level1_confidence());
        return;
    }
"""
SUB_N = r"""    // [DDOS-SHADOW-D293] La decisión viene de provenance.final_decision (hoy = SOLO la cabeza DDoS v2, la única
    // certificada; DAY285: las cabezas no certificadas no cuentan, level1 ya no decide). Este PR va en SOMBRA: los DROP
    // alimentan la política por víctima, que solo REGISTRA. Todo evento recibido avanza el reloj de la sombra.
    {
        const int64_t ts_s = static_cast<int64_t>(event.event_timestamp().seconds());
        if (config_.ddos_shadow.enabled) {
            for (const auto& rec : ddos_shadow_.advance(ts_s)) {
                FIREWALL_LOG_WARN("[SOMBRA-DDOS]", "registro", ::mldefender::firewall::format_ddos_shadow_record(rec));
            }
        }
        const bool drop = event.has_provenance() && event.provenance().final_decision() == "DROP";
        if (!drop || !config_.ddos_shadow.enabled) {
            return;
        }
        if (!event.has_network_features()) {
            FIREWALL_LOG_WARN("[SOMBRA-DDOS] evento DROP sin network_features", "event_id", event.event_id());
            return;
        }
        const auto& nf2 = event.network_features();
        double p1 = 0.0;
        std::string modelo;
        for (const auto& pr : ml.level2_specialized_predictions()) {
            if (pr.model_name().rfind("ddos_v2", 0) == 0) {
                p1 = static_cast<double>(pr.confidence_score());
                modelo = pr.model_name() + "@" + pr.model_version();
            }
        }
        const double ratio = nf2.has_ddos_embedded() ? static_cast<double>(nf2.ddos_embedded().victim_rate_ratio()) : 0.0;
        ddos_shadow_.add_drop(nf2.destination_ip(), static_cast<uint32_t>(nf2.protocol_number()), ts_s, nf2.source_ip(),
                              p1, ratio, event.event_id(), modelo);
        // [DDOS-SHADOW-D293] en este PR NO se bloquea nada: los pasos 5-8 (bloqueo por IP de origen, ipset, registro
        // BLOCKED) no se ejecutan. La mitigación real será por víctima (DEBT-FIREWALL-PER-VICTIM-001).
        return;
    }
"""


def p_sub_cpp(t):
    return repl(t, SUB_A, SUB_N, "sub_cpp compuerta")


def p_main(t):
    return after(t, "        zmq_config.log_directory = config.csv_batch_logger.output_dir;\n", r"""
        // [DDOS-SHADOW-D293] política por víctima en sombra (solo registra)
        zmq_config.ddos_shadow = config.ddos_shadow;
        std::cout << "[SOMBRA-DDOS] política por víctima " << (config.ddos_shadow.enabled ? "ACTIVA" : "DESACTIVADA")
                  << ": m=" << config.ddos_shadow.m << " k=" << config.ddos_shadow.k << " n=" << config.ddos_shadow.n
                  << " hold_s=" << config.ddos_shadow.hold_s << " (solo registra, no bloquea)" << std::endl;
""", "main")


def p_cmake(t):
    return after(t, "    add_test(NAME test_ip_cidr_validator COMMAND test_ip_cidr_validator)\n", """
    # test_ddos_shadow_policy — DAY293, política por víctima en sombra (header-only, propio CHECK) [DDOS-SHADOW-D293]
    add_executable(test_ddos_shadow_policy
            tests/unit/test_ddos_shadow_policy.cpp
    )
    target_include_directories(test_ddos_shadow_policy
            PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}/include
    )
    add_test(NAME test_ddos_shadow_policy COMMAND test_ddos_shadow_policy)
""", "cmake")


P = {"zh": p_zh, "json": p_json, "cfg_hpp": p_cfg_hpp, "cfg_cpp": p_cfg_cpp, "sub_hpp": p_sub_hpp,
     "sub_cpp": p_sub_cpp, "main": p_main, "cmake": p_cmake}

if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
    fail("uso: --check | --apply")
for n in NUEVOS:
    if not n.exists():
        fail("falta el fichero nuevo %s" % n)
cambios = {}
for k, f in P.items():
    t = F[k].read_text()
    if MARK in t:
        print("%s: ya aplicado" % F[k].name)
        continue
    cambios[k] = f(t)
    print("%s: preparado" % F[k].name)
if "json" in cambios:
    json.loads(cambios["json"])
    print("firewall.json: JSON válido tras el cambio")
if sys.argv[1] == "--apply":
    for k, t in cambios.items():
        F[k].with_suffix(F[k].suffix + ".tmp_d293").write_text(t)
    for k in cambios:
        F[k].with_suffix(F[k].suffix + ".tmp_d293").replace(F[k])
    print("APLICADO en %d fichero(s)" % len(cambios))
else:
    print("CHECK OK (nada escrito)")
