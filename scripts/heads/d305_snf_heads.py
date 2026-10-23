#!/usr/bin/env python3
# DAY305 — [HEADS-SNIFFER-D305] sniffer: la unica cabeza es el fast-path; el resto es recogida de rasgos (siempre).
# Decisiones de Alonso DAY305 (opcion A):
#  - fast_detector.enabled gobierna DE VERDAD el fast-path: ingesta + alerta rapida (capa 1) y emision de ventanas
#    de ransomware con su puntuacion (capa 2). Regla de 'enabled': booleano o texto true/false sin distinguir
#    mayusculas; ausente o invalido -> false (APAGADO) con [CONFIG-DEFAULT]. Seccion ausente -> APAGADO con aviso.
#  - El procesador de ransomware (agregador de ventana) se crea y arranca SIEMPRE: es recogida de rasgos (8 rasgos de
#    traffic/internal). Su hilo de emision de ventanas solo existe con el fast-path encendido.
#  - fast_detector.ransomware.window_interval_seconds: entero en [5, 3600], defecto 30 (sustituye a las dos
#    constantes de 30 s). monitoring.heads_log_interval_seconds: entero en [10, 3600], defecto 60. Ausente o
#    invalido -> defecto con [CONFIG-DEFAULT]; valores efectivos registrados al cargar.
#  - Linea [HEADS] al arrancar y cada heads_log_interval_seconds.
#  - Parada (DEBT-SNIFFER-RANSOMWARE-STOP-RACE-001): el procesador se para y libera DESPUES de unir los hilos que lo
#    usan; antes se emite la ventana pendiente (si el fast-path esta encendido) y se vacia la cola de envio; ya no
#    se pone ransomware_enabled_=false al parar (las estadisticas finales dicen la verdad).
#  - sniffer.json del laboratorio: fast_detector.enabled=false (DAY300: todo lo que no sea ddos_v2 apagado).
# Requiere aplicado d305_snf_retirar_inferencia.py. Valida TODO antes de escribir NADA.
# Uso, raiz del repo:  python3 d305_snf_heads.py --check | --apply
import json, sys

MARK = "[HEADS-SNIFFER-D305]"
PREV = "[SNIFFER-NO-INFER-D305]"
CTH = "sniffer/include/config_types.h"
CTC = "sniffer/src/userspace/config_types.cpp"
FDC = "sniffer/include/fast_detector_config.hpp"
MN  = "sniffer/src/userspace/main.cpp"
RPH = "sniffer/include/ransomware_feature_processor.hpp"
RH  = "sniffer/include/ring_consumer.hpp"
RC  = "sniffer/src/userspace/ring_consumer.cpp"
SJ  = "sniffer/config/sniffer.json"

EDITS = []
def E(f, old, new):
    EDITS.append((f, old, new))

# ------------------------------------------------------------------ config_types.h
E(CTH, "    struct {\n        int stats_interval_seconds;\n        std::string metrics_format;\n",
       f"    struct {{\n        int stats_interval_seconds;\n        int heads_log_interval_seconds = 60;  // {MARK} [10, 3600] s\n"
       "        std::string metrics_format;\n")
E(CTH, "    struct {\n        bool enabled;\n\n        struct {\n            struct {\n                double high_threat;\n",
       f"    struct {{\n        bool enabled = false;  // {MARK} ausente o invalido -> APAGADO\n\n"
       "        struct {\n            struct {\n                double high_threat;\n")
E(CTH, "            } activation_thresholds;\n        } ransomware;\n",
       f"            }} activation_thresholds;\n            int window_interval_seconds = 30;  // {MARK} [5, 3600] s\n"
       "        } ransomware;\n")

# ------------------------------------------------------------------ config_types.cpp
E(CTC, "#include <fstream>\n#include <iostream>\n\nbool strict_load_json_config(",
f"""#include <fstream>
#include <iostream>
#include <cctype>  // {MARK}
#include <string>  // {MARK}

// {MARK} reglas de Alonso: el JSON manda y ningun campo se lee en silencio.
namespace {{
// 'enabled': booleano o texto "true"/"false" sin distinguir mayusculas; ausente o invalido -> false + aviso.
bool leer_enabled(const Json::Value& blk, const std::string& ctx) {{
    if (blk.isObject() && blk.isMember("enabled")) {{
        const Json::Value& v = blk["enabled"];
        if (v.isBool()) {{
            return v.asBool();
        }}
        if (v.isString()) {{
            std::string s = v.asString();
            for (auto& c : s) {{
                c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
            }}
            if (s == "true") {{
                return true;
            }}
            if (s == "false") {{
                return false;
            }}
        }}
        std::cerr << "[CONFIG-DEFAULT] " << ctx << ".enabled invalido (formato true|false, tambien como texto sin "
                     "distinguir mayusculas): se usa false (APAGADO)" << std::endl;
        return false;
    }}
    std::cerr << "[CONFIG-DEFAULT] " << ctx << ".enabled ausente (formato true|false): se usa false (APAGADO)"
              << std::endl;
    return false;
}}
// entero en [mn, mx]; ausente, no entero o fuera de rango -> defecto + aviso con campo, formato y limites.
int leer_entero(const Json::Value& blk, const char* clave, const std::string& ctx, int def, int mn, int mx) {{
    if (!blk.isObject() || !blk.isMember(clave)) {{
        std::cerr << "[CONFIG-DEFAULT] " << ctx << "." << clave << " ausente (entero en [" << mn << ", " << mx
                  << "]): se usa " << def << std::endl;
        return def;
    }}
    const Json::Value& v = blk[clave];
    if (!v.isInt() || v.asInt() < mn || v.asInt() > mx) {{
        std::cerr << "[CONFIG-DEFAULT] " << ctx << "." << clave << " invalido (entero en [" << mn << ", " << mx
                  << "]): se usa " << def << std::endl;
        return def;
    }}
    return v.asInt();
}}
}}  // namespace

bool strict_load_json_config(""")
E(CTC, "            config_file >> root;\n            config_file.close();\n",
       "            config_file >> root;\n            config_file.close();\n"
       f"            config.monitoring.heads_log_interval_seconds = leer_entero(  // {MARK}\n"
       "                root.get(\"monitoring\", Json::Value()), \"heads_log_interval_seconds\", \"monitoring\", 60, 10, 3600);\n")
E(CTC, "                config.fast_detector.enabled = fd.get(\"enabled\", true).asBool();\n",
       f"                config.fast_detector.enabled = leer_enabled(fd, \"fast_detector\");  // {MARK}\n"
       "                config.fast_detector.ransomware.window_interval_seconds = leer_entero(\n"
       "                    fd.get(\"ransomware\", Json::Value()), \"window_interval_seconds\", \"fast_detector.ransomware\",\n"
       "                    30, 5, 3600);\n")
E(CTC, """                // Set defaults if section missing
                config.fast_detector.enabled = false;
                if (verbose) {
                    std::cout << "⚠️  Fast Detector section not found, disabled by default" << std::endl;
                }
""", f"""                // {MARK} seccion ausente: fast-path APAGADO, siempre avisado (no solo con verbose)
                config.fast_detector.enabled = false;
                config.fast_detector.ransomware.window_interval_seconds = 30;
                std::cerr << "[CONFIG-DEFAULT] seccion fast_detector ausente: fast-path APAGADO (enabled=false), "
                             "ransomware.window_interval_seconds=30" << std::endl;
""")
E(CTC, """        }

        if (verbose) {
            std::cout << "✅ Configuration loaded and converted successfully" << std::endl;
""", f"""            std::cout << "[Config] [HEADS] efectivo: fast_detector.enabled="  // {MARK}
                      << (config.fast_detector.enabled ? "true" : "false")
                      << " fast_detector.ransomware.window_interval_seconds="
                      << config.fast_detector.ransomware.window_interval_seconds
                      << " monitoring.heads_log_interval_seconds=" << config.monitoring.heads_log_interval_seconds
                      << std::endl;
        }}

        if (verbose) {{
            std::cout << "✅ Configuration loaded and converted successfully" << std::endl;
""")

# ------------------------------------------------------------------ fast_detector_config.hpp
E(FDC, "        FastDetectorRansomwareThresholds activation_thresholds;\n    };\n",
       "        FastDetectorRansomwareThresholds activation_thresholds;\n"
       f"        int window_interval_seconds = 30;  // {MARK} emision de ventanas (capa 2), [5, 3600] s\n    }};\n")
E(FDC, "        bool enabled = true;\n",
       f"        bool enabled = false;  // {MARK} el JSON decide; apagado si no se dice lo contrario\n")

# ------------------------------------------------------------------ main.cpp
E(MN, "            g_config.fast_detector.ransomware.activation_thresholds.unique_destinations_30s;\n",
      "            g_config.fast_detector.ransomware.activation_thresholds.unique_destinations_30s;\n"
      "        fast_detector_config.ransomware.window_interval_seconds =\n"
      f"            g_config.fast_detector.ransomware.window_interval_seconds;  // {MARK}\n")
E(MN, "        ring_consumer.set_stats_interval(g_config.monitoring.stats_interval_seconds);\n",
      "        ring_consumer.set_stats_interval(g_config.monitoring.stats_interval_seconds);\n"
      f"        ring_consumer.set_heads_log(g_config.monitoring.heads_log_interval_seconds,  // {MARK}\n"
      "                                    g_config.kernel_space.ddos_kernel_agg_enabled);\n")

# ------------------------------------------------------------------ ransomware_feature_processor.hpp
E(RPH, "        TimeWindowAggregator* get_aggregator() { return aggregator_.get(); }\n",
       "        TimeWindowAggregator* get_aggregator() { return aggregator_.get(); }\n"
       f"        // {MARK} intervalo de extraccion = fast_detector.ransomware.window_interval_seconds (JSON)\n"
       "        void set_extraction_interval_seconds(uint32_t s) { extraction_interval_seconds_ = s; }\n")

# ------------------------------------------------------------------ ring_consumer.hpp
E(RH, "    void set_stats_interval(int seconds) { stats_interval_seconds_ = seconds; }\n",
      "    void set_stats_interval(int seconds) { stats_interval_seconds_ = seconds; }\n"
      f"    // {MARK} intervalo de la linea [HEADS] y estado del agregador del kernel (solo para informar)\n"
      "    void set_heads_log(int interval_s, bool kernel_agg) {\n"
      "        heads_log_interval_seconds_ = interval_s;\n        kernel_agg_enabled_ = kernel_agg;\n    }\n")
E(RH, "    // CONSTANTS - Ransomware detection\n    static constexpr int RANSOMWARE_EXTRACTION_INTERVAL_SEC = 30;  // Deep analysis interval\n",
      f"    // {MARK} el intervalo de ventanas de ransomware vive en el JSON (fast_detector.ransomware.window_interval_seconds)\n")
E(RH, "    int stats_interval_seconds_{30};  // Default 30 seconds todo esto hay que cambiarlo, quitar números mágicos\n",
      "    int stats_interval_seconds_{30};  // Default 30 seconds todo esto hay que cambiarlo, quitar números mágicos\n"
      f"    int heads_log_interval_seconds_{{60}};  // {MARK}\n    bool kernel_agg_enabled_{{false}};  // {MARK}\n")
E(RH, """    bool espera_o_parada(std::chrono::seconds s) {
        std::unique_lock<std::mutex> lk(parada_mtx_);
        return parada_cv_.wait_for(lk, s, [this] { return should_stop_.load(); });
    }
""", f"""    bool espera_o_parada(std::chrono::seconds s) {{
        std::unique_lock<std::mutex> lk(parada_mtx_);
        return parada_cv_.wait_for(lk, s, [this] {{ return should_stop_.load(); }});
    }}
    bool espera_o_parada_ms(std::chrono::milliseconds ms) {{  // {MARK} varios plazos en un mismo hilo
        std::unique_lock<std::mutex> lk(parada_mtx_);
        return parada_cv_.wait_for(lk, ms, [this] {{ return should_stop_.load(); }});
    }}
""")
E(RH, "    void shutdown_ransomware_detection();\n",
      "    void shutdown_ransomware_detection();\n"
      f"    void log_heads_state(const char* momento) const;  // {MARK}\n"
      f"    void emitir_ventana_ransomware_pendiente();  // {MARK}\n"
      f"    void vaciar_cola_envio();  // {MARK}\n")

# ------------------------------------------------------------------ ring_consumer.cpp
E(RC, """    // Fast Detection (thread-local, O(1))
    fast_detector_.ingest(event);
    if (fast_detector_.is_suspicious()) {
        send_fast_alert(event);
    }
""", f"""    // Fast Detection (thread-local, O(1)). {MARK} solo con el fast-path encendido (fast_detector.enabled)
    if (fast_detector_config_.enabled) {{
        fast_detector_.ingest(event);
        if (fast_detector_.is_suspicious()) {{
            send_fast_alert(event);
        }}
    }}
""")
E(RC, """    if (!initialize_ransomware_detection()) {
        std::cerr << "[WARNING] Ransomware detection disabled" << std::endl;
    }else{
        std::cout << "[INFO] Ransomware detection initialized successfully" << std::endl;
    }
""", f"""    if (!initialize_ransomware_detection()) {{  // {MARK}
        std::cerr << "[WARNING] procesador ransomware NO inicializado: 8 rasgos de traffic/internal iran a centinela y "
                     "no habra ventanas de ransomware aunque el fast-path este encendido" << std::endl;
    }}
""")
E(RC, """        ransomware_processor_ = std::make_unique<RansomwareFeatureProcessor>();

        if (!ransomware_processor_->initialize()) {
""", f"""        ransomware_processor_ = std::make_unique<RansomwareFeatureProcessor>();
        ransomware_processor_->set_extraction_interval_seconds(  // {MARK}
            static_cast<uint32_t>(fast_detector_config_.ransomware.window_interval_seconds));

        if (!ransomware_processor_->initialize()) {{
""")
E(RC, """        ransomware_enabled_ = true;
        std::cout << "[INFO] ✅ Ransomware detection initialized (2-layer system)" << std::endl;
        std::cout << "       Layer 1: FastDetector (10s window, heuristics)" << std::endl;
        std::cout << "       Layer 2: FeatureProcessor (30s aggregation)" << std::endl;
""", f"""        ransomware_enabled_ = true;
        std::cout << "[INFO] procesador ransomware INICIALIZADO: agregador de ventana para la recogida de rasgos "  // {MARK}
                     "(siempre); emision de ventanas de ransomware: "
                  << (fast_detector_config_.enabled ? "SI" : "NO (fast-path apagado)") << ", cada "
                  << fast_detector_config_.ransomware.window_interval_seconds << " s" << std::endl;
""")
E(RC, """    // Start ransomware processor thread
    if (ransomware_enabled_) {
        ransomware_processor_->start();
        consumer_threads_.emplace_back(&RingBufferConsumer::ransomware_processor_loop, this);
        std::cout << "[INFO] + 1 ransomware detection thread (30s aggregation)" << std::endl;
    }
""", f"""    // {MARK} el procesador arranca siempre (recogida de rasgos); su hilo de emision de ventanas, solo con fast-path
    if (ransomware_enabled_) {{
        ransomware_processor_->start();
        if (fast_detector_config_.enabled) {{
            consumer_threads_.emplace_back(&RingBufferConsumer::ransomware_processor_loop, this);
            std::cout << "[INFO] + 1 hilo de emision de ventanas de ransomware (cada "
                      << fast_detector_config_.ransomware.window_interval_seconds << " s)" << std::endl;
        }}
    }}
""")
E(RC, "    std::cout << \"[INFO] Multi-threaded protobuf pipeline active\" << std::endl;\n",
      "    std::cout << \"[INFO] Multi-threaded protobuf pipeline active\" << std::endl;\n"
      f"    log_heads_state(\"arranque\");  // {MARK}\n")
E(RC, """    // 1️⃣ Parar ransomware detection PRIMERO (más costoso, tiene timer threads)
    shutdown_ransomware_detection();

""", f"""    // 1️⃣ {MARK} el procesador de ransomware ya NO se libera aqui: lo usan los hilos que aun no se han unido
    // (DEBT-SNIFFER-RANSOMWARE-STOP-RACE-001). Se libera tras shutdown_consumers().

""")
E(RC, """    // 4️⃣ Parar consumer threads (ya no recibirán eventos)
    shutdown_consumers();

""", f"""    // 4️⃣ Parar consumer threads (ya no recibirán eventos)
    shutdown_consumers();

    // 4b {MARK} con todos los hilos unidos: ventana pendiente, cola de envio y despues liberar el procesador
    emitir_ventana_ransomware_pendiente();
    vaciar_cola_envio();
    shutdown_ransomware_detection();

""")
E(RC, """    while (!should_stop_) {
        if (espera_o_parada(std::chrono::seconds(stats_interval_seconds_))) break;  // [PARADA-INMEDIATA-D300]

        if (should_stop_) break;

""", f"""    // {MARK} dos plazos en el mismo hilo: ESTADISTICAS (stats_interval_seconds) y [HEADS] (heads_log_interval_seconds)
    auto prox_stats = std::chrono::steady_clock::now() + std::chrono::seconds(stats_interval_seconds_);
    auto prox_heads = std::chrono::steady_clock::now() + std::chrono::seconds(heads_log_interval_seconds_);
    while (!should_stop_) {{
        const auto ahora0 = std::chrono::steady_clock::now();
        const auto prox = (prox_stats < prox_heads) ? prox_stats : prox_heads;
        if (prox > ahora0 &&
            espera_o_parada_ms(std::chrono::ceil<std::chrono::milliseconds>(prox - ahora0))) break;  // [PARADA-INMEDIATA-D300]

        if (should_stop_) break;
        const auto ahora1 = std::chrono::steady_clock::now();
        if (ahora1 >= prox_heads) {{
            log_heads_state("periodico");
            prox_heads = ahora1 + std::chrono::seconds(heads_log_interval_seconds_);
        }}
        if (ahora1 < prox_stats) continue;
        prox_stats = ahora1 + std::chrono::seconds(stats_interval_seconds_);

""")
E(RC, """              << RANSOMWARE_EXTRACTION_INTERVAL_SEC << "s extraction)" << std::endl;
""", f"""              << fast_detector_config_.ransomware.window_interval_seconds << "s extraction)" << std::endl;  // {MARK}
""")
E(RC, "        if (espera_o_parada(std::chrono::seconds(RANSOMWARE_EXTRACTION_INTERVAL_SEC))) break;  // [PARADA-INMEDIATA-D300]\n",
      "        if (espera_o_parada(std::chrono::seconds(fast_detector_config_.ransomware.window_interval_seconds))) break;  "
      f"// [PARADA-INMEDIATA-D300] {MARK}\n")
E(RC, """        ransomware_processor_.reset();
    }
    ransomware_enabled_ = false;
}
""", f"""        ransomware_processor_.reset();
    }}
    // {MARK} ransomware_enabled_ NO se toca: dice si el procesador estuvo inicializado (estadisticas finales veraces)
}}

// {MARK} estado EFECTIVO: en el sniffer la unica cabeza es el fast-path; lo demas es recogida de rasgos.
void RingBufferConsumer::log_heads_state(const char* momento) const {{
    std::cout << "[HEADS] (" << momento << ") fast_path=" << (fast_detector_config_.enabled ? "ON" : "OFF")
              << " ventanas_ransomware=" << ((fast_detector_config_.enabled && ransomware_enabled_) ? "ON" : "OFF")
              << " (cada " << fast_detector_config_.ransomware.window_interval_seconds << " s)"
              << " procesador_ransomware=" << (ransomware_enabled_ ? "INICIALIZADO" : "NO_INICIALIZADO")
              << " recogida_rasgos=SIEMPRE agregador_kernel=" << (kernel_agg_enabled_ ? "ON" : "OFF")
              << " | la inferencia de las cabezas vive en el ml-detector" << std::endl;
}}

// {MARK} parada: la ultima ventana calculada y no enviada se emite antes de liberar el procesador.
void RingBufferConsumer::emitir_ventana_ransomware_pendiente() {{
    if (!fast_detector_config_.enabled || !ransomware_enabled_ || !ransomware_processor_) {{
        return;
    }}
    protobuf::RansomwareFeatures f;
    if (ransomware_processor_->get_features_if_ready(f)) {{
        send_ransomware_features(f);
        std::cout << "[PARADA] ventana de ransomware pendiente emitida" << std::endl;
    }} else {{
        std::cout << "[PARADA] sin ventana de ransomware pendiente" << std::endl;
    }}
}}

// {MARK} parada: los hilos de envio ya estan unidos; lo que quede en la cola se envia aqui, antes de cerrar ZMQ.
void RingBufferConsumer::vaciar_cola_envio() {{
    std::queue<std::vector<uint8_t>> pendientes;
    {{
        std::lock_guard<std::mutex> lk(send_queue_mutex_);
        pendientes.swap(send_queue_);
    }}
    const size_t n = pendientes.size();
    size_t ok = 0;
    while (!pendientes.empty()) {{
        if (send_protobuf_message(pendientes.front())) {{
            ++ok;
        }}
        pendientes.pop();
    }}
    std::cout << "[PARADA] cola de envio vaciada: " << ok << " de " << n << " mensajes enviados" << std::endl;
}}
""")

# ------------------------------------------------------------------ sniffer.json (valores de LABORATORIO)
DOC_EN = (f"{MARK} enabled: el fast-path es la UNICA cabeza que vive en el sniffer (capa 1: alerta rapida por paquete; "
          "capa 2: ventanas de ransomware con su puntuacion). true|false, tambien como texto sin distinguir "
          "mayusculas; si falta o tiene otro valor: false (APAGADO) con [CONFIG-DEFAULT]. Apagado no calcula ni emite "
          "nada; la recogida de rasgos sigue siempre. Valor de LABORATORIO false (DAY300: mientras se trabaja DDoS, "
          "todo lo que no sea ddos_v2 apagado).")
E(SJ, "    \"_scope\": \"Selective detection - only activates when suspicious patterns exceed thresholds\",\n    \"enabled\": true,\n",
      "    \"_scope\": \"Selective detection - only activates when suspicious patterns exceed thresholds\",\n"
      f"    \"_doc_enabled\": {json.dumps(DOC_EN, ensure_ascii=False)},\n    \"enabled\": false,\n")
DOC_WIN = (f"{MARK} window_interval_seconds: cada cuantos segundos se calcula y emite una ventana de ransomware "
           "(capa 2 del fast-path). Entero en [5, 3600]; defecto 30. Si falta, no es entero o esta fuera de rango: "
           "30 con [CONFIG-DEFAULT].")
E(SJ, "      \"_description\": \"Ransomware-specific heuristics (C&C communication, lateral movement, exfiltration)\",\n",
      "      \"_description\": \"Ransomware-specific heuristics (C&C communication, lateral movement, exfiltration)\",\n"
      f"      \"_doc_window_interval_seconds\": {json.dumps(DOC_WIN, ensure_ascii=False)},\n"
      "      \"window_interval_seconds\": 30,\n")
DOC_HL = (f"{MARK} heads_log_interval_seconds: cada cuantos segundos escribe el sniffer la linea [HEADS] (estado del "
          "fast-path, de las ventanas de ransomware y de la recogida de rasgos), siempre visible. Entero en [10, 3600]; "
          "defecto 60. Si falta, no es entero o esta fuera de rango: 60 con [CONFIG-DEFAULT].")
E(SJ, "    \"stats_interval_seconds\": 30,\n",
      "    \"stats_interval_seconds\": 30,\n"
      f"    \"_doc_heads_log_interval_seconds\": {json.dumps(DOC_HL, ensure_ascii=False)},\n"
      "    \"heads_log_interval_seconds\": 60,\n")

EXP = {CTH: 3, CTC: 6, FDC: 2, MN: 2, RPH: 1, RH: 7, RC: 15, SJ: 3}

def die(m):
    print("ABORTA (no se ha escrito nada): " + m)
    sys.exit(1)

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        die("uso: python3 d305_snf_heads.py --check | --apply")
    files = sorted({f for f, _, _ in EDITS})
    text = {}
    for f in files:
        try:
            text[f] = open(f, encoding="utf-8").read()
        except OSError as e:
            die(f"no puedo leer {f}: {e}")
        if MARK in text[f]:
            die(f"{f} ya contiene {MARK}: el parche ya se aplico (o a medias)")
    if PREV not in text[RC]:
        die(f"falta {PREV}: aplica antes d305_snf_retirar_inferencia.py")
    new = dict(text)
    for i, (f, old, rep) in enumerate(EDITS, 1):
        c = new[f].count(old)
        if c != 1:
            die(f"edicion {i} en {f}: el ancla aparece {c} veces (se esperaba 1):\n---\n{old}---")
        new[f] = new[f].replace(old, rep, 1)
    for f in files:
        if new[f].count(MARK) < EXP[f]:
            die(f"{f}: {new[f].count(MARK)} marcas (se esperaban al menos {EXP[f]})")
    for f in (RC, RH):
        if "RANSOMWARE_EXTRACTION_INTERVAL_SEC" in new[f]:
            die(f"{f}: sigue la constante RANSOMWARE_EXTRACTION_INTERVAL_SEC")
    if 'fd.get("enabled", true)' in new[CTC]:
        die("config_types.cpp: sigue la lectura silenciosa de fast_detector.enabled")
    # orden de parada: shutdown_consumers -> emitir -> vaciar -> shutdown_ransomware -> shutdown_zmq
    stop = new[RC][new[RC].index("void RingBufferConsumer::stop()"):]
    stop = stop[:stop.index("\n}\n")]
    orden = ["shutdown_consumers();", "emitir_ventana_ransomware_pendiente();", "vaciar_cola_envio();",
             "shutdown_ransomware_detection();", "shutdown_zmq();"]
    pos = [stop.find(x) for x in orden]
    if -1 in pos or pos != sorted(pos) or stop.count("shutdown_ransomware_detection();") != 1:
        die(f"stop(): orden de parada inesperado {list(zip(orden, pos))}")
    try:
        j = json.loads(new[SJ])
    except json.JSONDecodeError as e:
        die(f"sniffer.json resultante no parsea: {e}")
    fd = j["fast_detector"]
    if fd.get("enabled") is not False or fd["ransomware"].get("window_interval_seconds") != 30 or \
       j["monitoring"].get("heads_log_interval_seconds") != 60:
        die("sniffer.json: valores resultantes inesperados")
    print(f"OK: {len(EDITS)} ediciones validadas en {len(files)} ficheros; orden de parada correcto; sniffer.json valido "
          "(fast_detector.enabled=false, window_interval_seconds=30, heads_log_interval_seconds=60)")
    for f in files:
        print(f"   {f}: {new[f].count(chr(10)) - text[f].count(chr(10)):+d} lineas")
    if sys.argv[1] == "--check":
        print("--check: no se ha escrito nada")
        return
    for f in files:
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(new[f])
    print("--apply: escrito. Siguiente: compilacion completa en production")

if __name__ == "__main__":
    main()
