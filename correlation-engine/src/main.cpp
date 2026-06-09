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
    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[i];
        if (a == "--follow") follow = true;
        else if (a == "--bronze" && i + 1 < argc) bronze_path = argv[++i];
    }
    if (bronze_path.empty()) {
        const char* env = std::getenv("ARGUS_BRONZE_CSV");
        bronze_path = env ? env : "";
    }
    if (bronze_path.empty()) {
        spdlog::critical("[CONSUMER] sin ruta de bronce (--bronze <path> o ARGUS_BRONZE_CSV)");
        return EXIT_FAILURE;
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

    auto sink = std::make_unique<ac::LoggingGraphSink>(spdlog::default_logger());

    uint64_t total = 0, discarded = 0;
    std::ifstream in(bronze_path);
    if (!in) {
        spdlog::critical("[CONSUMER] no se puede abrir bronce: {}", bronze_path);
        return EXIT_FAILURE;
    }
    spdlog::info("[CONSUMER] bronce={} follow={}", bronze_path, follow);

    auto drain = [&]() {
        std::string line;
        while (std::getline(in, line)) {
            if (line.empty()) continue;
            auto rec = ac::parse_and_verify(line, hmac_key);
            if (!rec) { ++discarded; continue; }  // invariante: corrupta antes del grafo
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
            in.clear();   // limpia EOF para releer cola nueva (append no-atomico del writer)
            drain();
        }
    }

    sink->flush();
    spdlog::info("[CONSUMER] one-shot fin: {} materializados, {} descartados", total, discarded);
    return EXIT_SUCCESS;

}
