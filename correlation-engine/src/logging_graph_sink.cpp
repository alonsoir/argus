// logging_graph_sink.cpp — backend IGraphSink que emite Cypher a log (DAY 179, actualizado DAY 180).
// Authors: Alonso Isidoro Roman + Claude (Anthropic).
//
// DAY 180: build_cypher() ahora DELEGA en el builder compartido (cypher_builder.hpp),
// para que LoggingGraphSink y KuzuGraphSink emitan Cypher IDENTICO por construccion.
// El modelo viejo (:NetworkFlow)-[:RAISED]->(:Alert) con 5-tupla+scores aplanados queda RETIRADO.
#include "correlation_engine/logging_graph_sink.hpp"
#include "correlation_engine/cypher_builder.hpp"
#include "correlation_engine/ingest_clock.hpp"

namespace argus::correlation {

    // Delega en el builder compartido. Cualificado con ::argus::correlation:: para nombrar la
    // funcion libre (no el metodo estatico homonimo) y evitar recursion infinita.
    std::string LoggingGraphSink::build_cypher(const CorrelationRecord& record,
                                               std::string_view flow_uid) {
        return ::argus::correlation::build_cypher(record, flow_uid, ingest_now_ns());
    }

    bool LoggingGraphSink::write(const CorrelationRecord& record, std::string_view flow_uid) {
        // INVARIANTE DE ENGINE (schema.cypher): no se materializa ningun nodo sin node_id.
        if (record.node_id.empty() || flow_uid.empty()) {
            logger_->error("[GRAPH-SINK] descarto registro sin node_id/flow_uid (event_id='{}')",
                           record.event_id);
            return false;
        }
        logger_->info("[CYPHER] {}", build_cypher(record, flow_uid));
        ++writes_;
        return true;
    }

    FlushResult LoggingGraphSink::flush() {
        logger_->info("[GRAPH-SINK] flush: {} registros materializados "
                      "(NetworkFlow + Alert/TelemetryEvent + arista)", writes_);
        // Sin buffer: cada write() ya volco su Cypher al log (commit inmediato).
        // Este flush no vuelca nada NUEVO -> exito trivial, 0 en este flush, 0 pendientes.
        return FlushResult{true, 0, 0};
    }

    LoggingGraphSink::LoggingGraphSink(std::shared_ptr<spdlog::logger> logger)
        : logger_(std::move(logger)) {}

}  // namespace argus::correlation