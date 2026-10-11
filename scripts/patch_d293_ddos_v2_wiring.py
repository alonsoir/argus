#!/usr/bin/env python3
"""DAY293 — patcher atómico (todo o nada) [DDOS-V2-D293]: cablea la cabeza DDoS v2 factorizada en el ml-detector.
 - config_loader.hpp/.cpp: ml.ddos_v2 {enabled, k_ratio} con defecto validado + [CONFIG-DEFAULT] (arranca igual).
 - ml_detector_config.json: bloque ml.ddos_v2 con _doc (rango, formato, defecto).
 - ddos_v2_head.hpp: kModelName / kModelVersion.
 - zmq_handler.hpp/.cpp: evaluación en cada evento de flujo (sin compuerta de level1), predicción level2 propia,
   final_decision = solo ddos_v2, contadores y resumen periódico [DDOS-V2], línea de arranque.
 NO toca threat_category (el firewall lo lee: este PR va en sombra). Uso: --check | --apply. Idempotente. No commitea."""
import sys
from pathlib import Path

MARK = "[DDOS-V2-D293]"
R = Path("/vagrant/ml-detector")
F = {
    "cfg_hpp": R / "include/config_loader.hpp",
    "cfg_cpp": R / "src/config_loader.cpp",
    "json": R / "config/ml_detector_config.json",
    "head": R / "include/ml_defender/ddos_v2_head.hpp",
    "zh_hpp": R / "include/zmq_handler.hpp",
    "zh_cpp": R / "src/zmq_handler.cpp",
}


def fail(m):
    print("ABORTA:", m); sys.exit(1)


def once(txt, anchor, nombre):
    n = txt.count(anchor)
    if n != 1:
        fail("%s: ancla encontrada %d veces" % (nombre, n))


def after(txt, anchor, ins, nombre):
    once(txt, anchor, nombre); return txt.replace(anchor, anchor + ins)


def before(txt, anchor, ins, nombre):
    once(txt, anchor, nombre); return txt.replace(anchor, ins + anchor)


def repl(txt, old, new, nombre):
    once(txt, old, nombre); return txt.replace(old, new)


CFG_HPP_A = "            float level3_internal{};\n        } thresholds;\n"
CFG_HPP_I = r"""
        // [DDOS-V2-D293] cabeza DDoS v2 factorizada: etapa 1 = victim_rate_ratio >= k_ratio
        struct {
            bool enabled = true;
            double k_ratio = 3.0;
        } ddos_v2;
"""

CFG_CPP_A = '        config.ml.thresholds.level3_internal = get_required<float>(thresh, "level3_internal", "ml.thresholds");\n'
CFG_CPP_I = r"""
        // [DDOS-V2-D293] ml.ddos_v2: el JSON manda; si un campo falta o es inválido se aplica el defecto validado,
        // se avisa con [CONFIG-DEFAULT] (campo, formato y límites) y el ml-detector arranca igual.
        {
            constexpr double kDefK = 3.0;
            constexpr double kMinK = 1.5;
            constexpr double kMaxK = 50.0;
            config.ml.ddos_v2.enabled = true;
            config.ml.ddos_v2.k_ratio = kDefK;
            if (!ml.contains("ddos_v2") || !ml["ddos_v2"].is_object()) {
                std::cerr << "[CONFIG-DEFAULT] ml.ddos_v2 ausente o no es un objeto: enabled=true, k_ratio=" << kDefK
                          << " (número en [" << kMinK << ", " << kMaxK << "])\n";
            } else {
                const auto& d2 = ml["ddos_v2"];
                if (d2.contains("enabled") && d2["enabled"].is_boolean()) {
                    config.ml.ddos_v2.enabled = d2["enabled"].get<bool>();
                } else {
                    std::cerr << "[CONFIG-DEFAULT] ml.ddos_v2.enabled ausente o no booleano (formato true|false): se usa true\n";
                }
                if (d2.contains("k_ratio") && d2["k_ratio"].is_number() &&
                    d2["k_ratio"].get<double>() >= kMinK && d2["k_ratio"].get<double>() <= kMaxK) {
                    config.ml.ddos_v2.k_ratio = d2["k_ratio"].get<double>();
                } else {
                    std::cerr << "[CONFIG-DEFAULT] ml.ddos_v2.k_ratio ausente, no numérico o fuera de rango (número en ["
                              << kMinK << ", " << kMaxK << "]): se usa " << kDefK << "\n";
                }
            }
        }
"""

JSON_A = '      "level3_internal": 0.65\n    },\n'
JSON_I = """    "ddos_v2": {
      "_doc": "[DDOS-V2-D293] Cabeza DDoS v2 factorizada (docs/ml-heads/bloque1_day293.md). enabled: true|false, defecto true. k_ratio: número en [1.5, 50], defecto 3.0 = umbral de la etapa 1 sobre victim_rate_ratio (alineado con k_in de la histéresis del sniffer). Si un campo falta o es inválido se aplica el defecto con [CONFIG-DEFAULT] y el ml-detector arranca igual. Valores de LABORATORIO: en un despliegue real se consensúan con el personal de la instalación.",
      "enabled": true,
      "k_ratio": 3.0
    },
"""

HEAD_A = "namespace ml_defender::ddos_v2 {\n\nstruct Input {"
HEAD_N = ("namespace ml_defender::ddos_v2 {\n\n"
          "// [DDOS-V2-D293] identidad del modelo (consolidado f3d6b261, bloque 1 DAY293). Mantener en sintonía con la cabecera\n"
          "// de ddos_v2_forest_inline.hpp al regenerarlo (deuda: que lo emita el exportador).\n"
          "inline constexpr const char* kModelName = \"ddos_v2_fact_rf\";\n"
          "inline constexpr const char* kModelVersion = \"day293-f3d6b261\";\n\n"
          "struct Input {")

ZH_HPP_A = "        uint64_t detections_internal = 0;    // [SUMMARY-D285]\n"
ZH_HPP_I = ("        uint64_t ddos_v2_presion = 0;        // [DDOS-V2-D293] eventos que pasan la etapa 1\n"
            "        uint64_t ddos_v2_ataque = 0;         // [DDOS-V2-D293] eventos que la cabeza v2 marca DDoS\n")

ZH_INC = '#include "ml_defender/ddos_v2_head.hpp"  // [DDOS-V2-D293]\n'

ZH_CTOR_A = "    if (ddos_detector_) {\n"
ZH_CTOR_I = r"""    logger_->info("[DDOS-V2] cabeza factorizada {}: modelo {} ({}), {} árboles, {} rasgos de flujo, k_ratio={}",  // [DDOS-V2-D293]
                  config_.ml.ddos_v2.enabled ? "ACTIVA" : "DESACTIVADA", ml_defender::ddos_v2::kModelName,
                  ml_defender::ddos_v2::kModelVersion, ml_defender::ddos_v2::kNumTrees,
                  ml_defender::ddos_v2::kNumFeatures, config_.ml.ddos_v2.k_ratio);
"""

ZH_EVAL_A = "            ml_analysis->set_level1_confidence(confidence_l1);\n        }\n\n        // Dual-Score Architecture\n"
ZH_EVAL_N = ("            ml_analysis->set_level1_confidence(confidence_l1);\n        }\n" + r"""
        // [DDOS-V2-D293] cabeza DDoS v2 factorizada (docs/ml-heads/bloque1_day293.md): corre en TODO evento de flujo,
        // sin compuerta de level1 (sin veto, DAY272). Etapa 1: victim_rate_ratio >= k_ratio; etapa 2: bosque sobre los
        // 6 rasgos de flujo de ddos_embedded (contrato v2). Decide final_decision (más abajo).
        bool ddos_v2_attack = false;
        if (is_flow_event && config_.ml.ddos_v2.enabled && event.has_network_features() &&
            event.network_features().has_ddos_embedded()) {
            const auto& dv2 = event.network_features().ddos_embedded();
            const ml_defender::ddos_v2::Input in2{dv2.syn_ack_ratio(), dv2.mean_packet_size(), dv2.reflection_signature(),
                                                  dv2.packet_size_entropy(), dv2.flow_packet_count(),
                                                  dv2.flow_completion_rate(), dv2.victim_rate_ratio()};
            const auto r2 = ml_defender::ddos_v2::evaluate(in2, config_.ml.ddos_v2.k_ratio);
            ddos_v2_attack = (r2.clase == 1);
            auto* p2 = ml_analysis->add_level2_specialized_predictions();
            p2->set_model_name(ml_defender::ddos_v2::kModelName);
            p2->set_model_version(ml_defender::ddos_v2::kModelVersion);
            p2->set_model_type(protobuf::ModelPrediction::RANDOM_FOREST_DDOS);
            p2->set_prediction_class(ddos_v2_attack ? "DDOS" : (r2.stage1 ? "NORMAL" : "NO_PRESSURE"));
            p2->set_confidence_score(static_cast<float>(r2.p1));
            if (r2.stage1) {
                std::lock_guard<std::mutex> lock(stats_mutex_);
                stats_.ddos_v2_presion++;
                if (ddos_v2_attack) {
                    stats_.ddos_v2_ataque++;
                }
            }
            logger_->debug("🤖 DDoS-v2: etapa1={} ratio={:.3f} p1={:.4f} clase={} event={}",
                           r2.stage1, dv2.victim_rate_ratio(), r2.p1, r2.clase, event.event_id());
        }

        // Dual-Score Architecture
""")

ZH_FD_A = ('        provenance->set_final_decision(\n'
           '            final_score >= config_.scoring.malicious_threshold ? "DROP" : "ALLOW"\n'
           '        );\n')
ZH_FD_N = ('        // [DDOS-V2-D293] final_decision = SOLO la cabeza DDoS v2 (única certificada; DAY285: las cabezas no arregladas\n'
           '        // no cuentan). La puntuación dual (fast + level1) sigue en overall_threat_score, sin decidir.\n'
           '        provenance->set_final_decision(ddos_v2_attack ? "DROP" : "ALLOW");\n')

ZH_SUM_A1 = "                const uint64_t d_int  = summary_delta(s.detections_internal, summary_prev.detections_internal);\n"
ZH_SUM_I1 = ("                const uint64_t d_v2p  = summary_delta(s.ddos_v2_presion, summary_prev.ddos_v2_presion);  // [DDOS-V2-D293]\n"
             "                const uint64_t d_v2a  = summary_delta(s.ddos_v2_ataque, summary_prev.ddos_v2_ataque);\n")
ZH_SUM_A2 = "                summary_prev = s;\n                summary_last = now;\n"
ZH_SUM_I2 = r"""                if (d_v2p > 0) {  // [DDOS-V2-D293]
                    logger_->warn("[DDOS-V2] bajo_presion={} ataque={} en los últimos {} s (k_ratio={})",
                                  d_v2p, d_v2a, secs, config_.ml.ddos_v2.k_ratio);
                }
"""


def plan():
    out = {}
    t = {k: p.read_text() for k, p in F.items()}
    if MARK in t["cfg_hpp"]:
        print("config_loader.hpp: ya aplicado")
    else:
        out["cfg_hpp"] = after(t["cfg_hpp"], CFG_HPP_A, CFG_HPP_I, "config_loader.hpp")
    if MARK in t["cfg_cpp"]:
        print("config_loader.cpp: ya aplicado")
    else:
        out["cfg_cpp"] = after(t["cfg_cpp"], CFG_CPP_A, CFG_CPP_I, "config_loader.cpp")
    if MARK in t["json"]:
        print("ml_detector_config.json: ya aplicado")
    else:
        out["json"] = after(t["json"], JSON_A, JSON_I, "ml_detector_config.json")
    if MARK in t["head"]:
        print("ddos_v2_head.hpp: ya aplicado")
    else:
        out["head"] = repl(t["head"], HEAD_A, HEAD_N, "ddos_v2_head.hpp")
    if MARK in t["zh_hpp"]:
        print("zmq_handler.hpp: ya aplicado")
    else:
        out["zh_hpp"] = after(t["zh_hpp"], ZH_HPP_A, ZH_HPP_I, "zmq_handler.hpp")
    if MARK in t["zh_cpp"]:
        print("zmq_handler.cpp: ya aplicado")
    else:
        z = t["zh_cpp"]
        lines = z.splitlines(keepends=True)
        i = next((k for k, l in enumerate(lines) if l.startswith("#include")), None)
        if i is None:
            fail("zmq_handler.cpp: sin #include")
        z = "".join(lines[:i]) + ZH_INC + "".join(lines[i:])
        z = before(z, ZH_CTOR_A, ZH_CTOR_I, "zmq_handler.cpp ctor")
        z = repl(z, ZH_EVAL_A, ZH_EVAL_N, "zmq_handler.cpp evaluación")
        z = repl(z, ZH_FD_A, ZH_FD_N, "zmq_handler.cpp final_decision")
        z = after(z, ZH_SUM_A1, ZH_SUM_I1, "zmq_handler.cpp resumen 1")
        z = before(z, ZH_SUM_A2, ZH_SUM_I2, "zmq_handler.cpp resumen 2")
        out["zh_cpp"] = z
    for k in out:
        print("%s: preparado" % F[k].name)
    return out


if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
    fail("uso: --check | --apply")
cambios = plan()
if "json" in cambios:
    import json
    json.loads(cambios["json"])
    print("ml_detector_config.json: JSON válido tras el cambio")
if sys.argv[1] == "--apply":
    for k, txt in cambios.items():
        F[k].with_suffix(F[k].suffix + ".tmp_d293").write_text(txt)
    for k in cambios:
        F[k].with_suffix(F[k].suffix + ".tmp_d293").replace(F[k])
    print("APLICADO en %d fichero(s)" % len(cambios))
else:
    print("CHECK OK (nada escrito)")
