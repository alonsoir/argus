// aRGus NDR — correlation-engine
// ADR-048 F2 — primary key: community_id, join cross-tool
// ADR-046 P0 — NTP gate obligatorio antes de cualquier subscripción ZMQ
//
// DAY 167: scaffold compilable con NTP gate real.
// TODO ADR-048 F2: subscripciones ZMQ Suricata/Zeek/Wazuh + join logic

#include <cstdlib>
#include <iostream>
#include "../../common/include/ntp_health_check.hpp"

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

    // TODO ADR-048 F2 — subscripciones ZMQ
    // source_wait_timeout: argus=5s / suricata=10s / zeek=20s / wazuh=90s
    // crisis_idle_timeout: 120s
    // community_id como primary key para join cross-tool
    spdlog::info("NTP gate OK — correlation loop pendiente (ADR-048 F2)");

    return EXIT_SUCCESS;
}
