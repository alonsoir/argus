// aRGus NDR — correlation-engine
// ADR-048 F2 — primary key: community_id, join cross-tool
// ADR-046 P0 — NTP gate obligatorio antes de cualquier subscripción ZMQ
//
// DAY 167: scaffold compilable con NTP gate real.
// TODO ADR-048 F2: subscripciones ZMQ Suricata/Zeek/Wazuh + join logic

#include <cstdlib>
#include <iostream>
#include "../../common/include/ntp_health_check.hpp"
#include <fstream>
#include <string>
#include <vector>
#include <cstdint>
#include <thread>
#include <chrono>
#include <memory>
#include "correlation_engine/correlation_reader.hpp"
#include "correlation_engine/flow_uid.hpp"
#include "correlation_engine/logging_graph_sink.hpp"
#include "correlation_engine/kuzu_graph_sink.hpp"
#include "correlation_engine/config_loader.hpp"
#include "correlation_engine/bronze_dir_watcher.hpp"
#include "correlation_engine/segment_processor.hpp"
#include <ctime>
#include <filesystem>
#include <algorithm>

// spdlog — disponible en el sistema (instalado en all-dependencies)
#include <spdlog/spdlog.h>

int main(int argc, char* argv[]) {
    spdlog::set_level(spdlog::level::info);
    spdlog::set_pattern("[%Y-%m-%dT%H:%M:%S.%e] [%l] [correlation-engine] %v");

    spdlog::info("aRGus NDR correlation-engine — arrancando (ADR-048 F2)");

    // ── ADR-046 P0: NTP gate ──────────────────────────────────────────────
    // community_id como primary key requiere timestamps sincronizados.
    // Sin esta garantía los Parquet de Suricata/Zeek/Wazuh no tienen
    // join key válida entre sí. Gate obligatorio antes de ZMQ.
    try {
        double offset = argus::NtpHealthCheck::measure_offset_seconds();
        if (offset > 1.0) {
            spdlog::critical(
                "[NTP-GATE] offset {:.3f}s > 1.0s — arranque abortado "
                "(ADR-046 P0, community_id join key invalida)", offset);
            return EXIT_FAILURE;
        }
        spdlog::info("[NTP-GATE] offset {:.6f}s OK", offset);
    } catch (const std::exception& e) {
        spdlog::critical(
            "[NTP-GATE] health-check fallido: {} — arranque abortado "
            "(chrony no disponible o no sincronizado)", e.what());
        return EXIT_FAILURE;
    }
    // ─────────────────────────────────────────────────────────────────────

    // === DAY179 CONSUMER LOOP ===
    // Consumidor F1 (aRGus): file_watch bronce -> parse_and_verify -> flow_uid -> IGraphSink.
    // one-shot por defecto; --follow = tail-poll daemon. Clave HMAC por env (lado lector de
    // DEBT-BRONZE-KEY-PROVISIONING-001). flow_uid seq=0 (DEBT-FLOWUID-SEQ-COLLISION-001 P2).
    namespace ac = argus::correlation;

    bool follow = false;
    std::string bronze_path;
    std::string config_path = "/etc/ml-defender/correlation-engine/correlation_engine.json";
    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[i];
        if (a == "--follow") follow = true;
        else if (a == "--bronze" && i + 1 < argc) bronze_path = argv[++i];
        else if (a == "--config" && i + 1 < argc) config_path = argv[++i];
    }
    if (bronze_path.empty()) {
        const char* env = std::getenv("ARGUS_BRONZE_CSV");
        bronze_path = env ? env : "";
    }

    const char* key_hex = std::getenv("ARGUS_BRONZE_HMAC_KEY_HEX");
    if (!key_hex || std::string(key_hex).size() != 64) {
        spdlog::critical("[CONSUMER] ARGUS_BRONZE_HMAC_KEY_HEX ausente o != 64 hex chars "
                         "(DEBT-BRONZE-KEY-PROVISIONING-001: cablear a etcd /secrets/<comp> key)");
        return EXIT_FAILURE;
    }
    std::vector<uint8_t> hmac_key;
    {
        const std::string hx = key_hex;
        hmac_key.reserve(hx.size() / 2);
        for (size_t i = 0; i + 1 < hx.size(); i += 2)
            hmac_key.push_back(static_cast<uint8_t>(std::stoul(hx.substr(i, 2), nullptr, 16)));
    }

    // Backend de grafo seleccionable. Default: logging (no requiere Kuzu, util para CI).
    //   ARGUS_GRAPH_BACKEND=kuzu  + ARGUS_KUZU_DB_PATH + ARGUS_KUZU_SCHEMA_PATH
    std::unique_ptr<ac::IGraphSink> sink;
    if (const char* be = std::getenv("ARGUS_GRAPH_BACKEND"); be && std::string(be) == "kuzu") {
        const char* db     = std::getenv("ARGUS_KUZU_DB_PATH");
        const char* schema = std::getenv("ARGUS_KUZU_SCHEMA_PATH");
        sink = std::make_unique<ac::KuzuGraphSink>(
            db     ? db     : "/var/lib/argus/argus_graph.kuzu",
            schema ? schema : "/vagrant/correlation-engine/schema/schema.cypher",
            spdlog::default_logger());
    } else {
        sink = std::make_unique<ac::LoggingGraphSink>(spdlog::default_logger());
    }

    uint64_t total = 0, discarded = 0;

    // DAY 204: la logica de parseo/verificacion/sink vive en process_segment
    // (correlation_engine, libreria compartida) -- mismo codigo que ejercen
    // los tests de circuito completo (emecas+++). Este wrapper solo acumula
    // los contadores locales de main().
    auto handle_segment = [&](const std::string& path) {
        auto r = ac::process_segment(path, hmac_key, *sink);
        total += r.total;
        discarded += r.discarded;
    };

    if (!bronze_path.empty()) {
        // Modo LEGACY: fichero explicito (--bronze/ARGUS_BRONZE_CSV), compatibilidad
        // con tests/scripts existentes. Tail-poll clasico -- este path NO participa
        // de la segmentacion DAY 203 (el llamador controla el fichero directamente).
        std::ifstream in(bronze_path);
        if (!in) {
            spdlog::critical("[CONSUMER] no se puede abrir bronce: {}", bronze_path);
            return EXIT_FAILURE;
        }
        spdlog::info("[CONSUMER] modo legacy (fichero explicito): bronce={} follow={}",
                     bronze_path, follow);

        auto drain = [&]() {
            std::string line;
            while (std::getline(in, line)) {
                if (line.empty()) continue;
                auto rec = ac::parse_and_verify(line, hmac_key);
                if (!rec) { ++discarded; continue; }
                const uint64_t window = ac::window_micros(rec->flow_start_sec, rec->flow_start_nano);
                const std::string fuid = ac::compute_flow_uid(rec->node_id, rec->community_id, window);
                sink->write(*rec, fuid);
                ++total;
            }
        };

        drain();
        if (follow) {
            spdlog::info("[CONSUMER] --follow: tail-poll cada 1s (Ctrl-C para salir)");
            while (true) {
                std::this_thread::sleep_for(std::chrono::seconds(1));
                in.clear();   // limpia EOF para releer cola nueva (fichero explicito, sin rotacion)
                drain();
            }
        }
    } else {
        // Modo DIRECTORIO (DAY 203, DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001):
        // sin fichero explicito, vigila root_dir del config JSON. Los segmentos
        // son inmutables desde que aparecen (writer: .tmp -> rename atomico) --
        // se leen enteros, sin offset, sin riesgo de linea a medias.
        std::string root_dir;
        try {
            auto cfg = ac::load_correlation_engine_config(config_path);
            root_dir = cfg.bronze.root_dir;
        } catch (const std::exception& e) {
            spdlog::critical("[CONSUMER] sin ruta de bronce -- ni --bronze/ARGUS_BRONZE_CSV "
                             "ni config JSON valido ({}): {}", config_path, e.what());
            return EXIT_FAILURE;
        }
        spdlog::info("[CONSUMER] modo directorio: root_dir={} follow={}", root_dir, follow);

        // Replay: segmentos ya cerrados presentes al arrancar, orden cronologico
        // natural (nombre = fecha+hora de apertura -> std::sort basta).
        std::vector<std::string> existing;
        if (std::filesystem::is_directory(root_dir)) {
            for (const auto& entry : std::filesystem::directory_iterator(root_dir)) {
                if (entry.path().extension() == ".csv") {
                    existing.push_back(entry.path().string());
                }
            }
            std::sort(existing.begin(), existing.end());
        }
        for (const auto& path : existing) handle_segment(path);

        if (follow) {
            spdlog::info("[CONSUMER] --follow: vigilando {} (inotify IN_MOVED_TO, Ctrl-C para salir)",
                        root_dir);
            ac::BronzeDirWatcher watcher(root_dir, handle_segment);
            watcher.run();  // bloqueante
        }
    }

    const auto fr = sink->flush();
    spdlog::info("[CONSUMER] fin: {} materializados, {} descartados", total, discarded);
    if (!fr) {
        // Fallo de durabilidad: filas aceptadas por write() pero NO committeadas.
        // EXIT_FAILURE para que el harness E2E no lea 'ok' sobre datos perdidos.
        spdlog::error("[CONSUMER] flush final FALLO: {} filas sin materializar (NO durable)",
                      fr.rows_pending);
        return EXIT_FAILURE;
    }

}
