// logging_graph_sink.hpp — backend IGraphSink que emite Cypher a log (DAY 179).
// Sustituible por backend Kuzu sin tocar el loop. Authors: Alonso + Claude.
#pragma once
#include "correlation_engine/i_graph_sink.hpp"
#include <cstdint>
#include <memory>
#include <string>

#include <spdlog/spdlog.h>

namespace argus::correlation {

// Emite por cada write el Cypher completo (MERGE :NetworkFlow -[:RAISED]-> :Alert)
// y, en flush(), un contador agregado. NO toca disco de grafo: solo log.
class LoggingGraphSink final : public IGraphSink {
public:
    explicit LoggingGraphSink(std::shared_ptr<spdlog::logger> logger);

    bool write(const CorrelationRecord& record, std::string_view flow_uid) override;
    FlushResult flush() override;

    uint64_t writes() const noexcept { return writes_; }

    // Construye el Cypher para un registro (expuesto para test del formato).
    static std::string build_cypher(const CorrelationRecord& record,
                                    std::string_view flow_uid);

private:
    std::shared_ptr<spdlog::logger> logger_;
    uint64_t writes_ = 0;
};

}  // namespace argus::correlation
