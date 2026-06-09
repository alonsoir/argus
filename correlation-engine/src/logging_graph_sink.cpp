// logging_graph_sink.cpp — DAY 179. Authors: Alonso Isidoro Roman + Claude.
#include "correlation_engine/logging_graph_sink.hpp"
#include <sstream>

namespace argus::correlation {

namespace {
// Escapa comillas simples para literales Cypher (defensa minima; node_id es opaco).
std::string esc(const std::string& s) {
    std::string out;
    out.reserve(s.size());
    for (char c : s) {
        if (c == '\'') out += "\\'";
        else out += c;
    }
    return out;
}
}  // namespace

std::string LoggingGraphSink::build_cypher(const CorrelationRecord& r,
                                           std::string_view flow_uid) {
    std::ostringstream q;
    // :NetworkFlow identificado por flow_uid (server-side). :Alert con los 4 scores
    // + fuente autoritativa: "bronce PRESERVA, gold DECIDE" -> no se aplana nada aqui.
    q << "MERGE (f:NetworkFlow {flow_uid:'" << esc(std::string(flow_uid)) << "'}) "
      << "SET f.community_id='" << esc(r.community_id) << "', "
      << "f.node_id='" << esc(r.node_id) << "', "
      << "f.src_ip='" << esc(r.src_ip) << "', f.dst_ip='" << esc(r.dst_ip) << "', "
      << "f.src_port=" << r.src_port << ", f.dst_port=" << r.dst_port << ", "
      << "f.protocol='" << esc(r.protocol) << "', "
      << "f.flow_start_sec=" << r.flow_start_sec << ", f.flow_start_nano=" << r.flow_start_nano
      << " "
      << "MERGE (f)-[:RAISED]->(a:Alert {event_id:'" << esc(r.event_id) << "'}) "
      << "SET a.source_sensor='" << esc(r.source_sensor) << "', "
      << "a.final_classification='" << esc(r.final_classification) << "', "
      << "a.threat_category='" << esc(r.threat_category) << "', "
      << "a.fast_detector_score=" << r.fast_detector_score << ", "
      << "a.ml_detector_score=" << r.ml_detector_score << ", "
      << "a.overall_threat_score=" << r.overall_threat_score << ", "
      << "a.authoritative_source='" << esc(r.authoritative_source) << "', "
      << "a.schema_version='" << esc(r.schema_version) << "'";
    return q.str();
}

bool LoggingGraphSink::write(const CorrelationRecord& record, std::string_view flow_uid) {
    logger_->info("[CYPHER] {}", build_cypher(record, flow_uid));
    ++writes_;
    return true;
}

void LoggingGraphSink::flush() {
    logger_->info("[GRAPH-SINK] flush: {} registros materializados (:NetworkFlow + :Alert)",
                  writes_);
}

LoggingGraphSink::LoggingGraphSink(std::shared_ptr<spdlog::logger> logger)
    : logger_(std::move(logger)) {}

}  // namespace argus::correlation
