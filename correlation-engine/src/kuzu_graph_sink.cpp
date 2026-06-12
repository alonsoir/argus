// kuzu_graph_sink.cpp — backend IGraphSink sobre Kuzu embebido (DAY 180).
// Authors: Alonso Isidoro Roman + Claude (Anthropic).
#include "correlation_engine/kuzu_graph_sink.hpp"
#include "correlation_engine/cypher_builder.hpp"
#include "correlation_engine/ingest_clock.hpp"

#include <kuzu.hpp>

#include <fstream>
#include <sstream>
#include <stdexcept>
#include <vector>

namespace argus::correlation {

using kuzu::main::Connection;
using kuzu::main::Database;
using kuzu::main::SystemConfig;

namespace {
// Parte schema.cypher en statements: quita comentarios // (no hay // dentro de strings)
// y separa por ';'. Devuelve cada DDL trim-eado y no vacio.
std::vector<std::string> split_statements(const std::string& path) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("KuzuGraphSink: no puedo abrir schema: " + path);
    std::ostringstream clean;
    std::string line;
    while (std::getline(in, line)) {
        const auto pos = line.find("//");
        clean << (pos == std::string::npos ? line : line.substr(0, pos)) << '\n';
    }
    std::vector<std::string> out;
    std::istringstream parts(clean.str());
    std::string seg;
    while (std::getline(parts, seg, ';')) {
        const auto b = seg.find_first_not_of(" \t\r\n");
        if (b == std::string::npos) continue;
        const auto e = seg.find_last_not_of(" \t\r\n");
        out.push_back(seg.substr(b, e - b + 1));
    }
    return out;
}
}  // namespace

KuzuGraphSink::KuzuGraphSink(const std::string& db_path,
                             const std::string& schema_path,
                             std::shared_ptr<spdlog::logger> logger)
    : logger_(std::move(logger)) {
    SystemConfig cfg;
    db_   = std::make_unique<Database>(db_path, cfg);
    conn_ = std::make_unique<Connection>(db_.get());
    load_schema(schema_path);
    logger_->info("[KUZU-SINK] BD '{}' lista; schema '{}' cargado", db_path, schema_path);
}

KuzuGraphSink::~KuzuGraphSink() = default;

void KuzuGraphSink::load_schema(const std::string& schema_path) {
    for (const auto& stmt : split_statements(schema_path)) {
        auto r = conn_->query(stmt);
        if (!r->isSuccess())
            throw std::runtime_error("KuzuGraphSink: DDL fallo: " + r->getErrorMessage()
                                     + " | stmt: " + stmt);
    }
}

bool KuzuGraphSink::write(const CorrelationRecord& record, std::string_view flow_uid) {
    // INVARIANTE DE ENGINE (schema.cypher): no se materializa ningun nodo sin node_id.
    // community_id nunca llega vacio (el writer del bronce lo descarta); guard defensivo.
    if (record.node_id.empty() || flow_uid.empty()) {
        logger_->error("[KUZU-SINK] descarto registro sin node_id/flow_uid (event_id='{}')",
                       record.event_id);
        return false;
    }
    const std::string cypher = build_cypher(record, flow_uid, ingest_now_ns());
    auto r = conn_->query(cypher);
    if (!r->isSuccess()) {
        logger_->error("[KUZU-SINK] write fallo: {} | cypher: {}", r->getErrorMessage(), cypher);
        return false;
    }
    ++writes_;
    return true;
}

void KuzuGraphSink::flush() {
    // Kuzu auto-commitea cada query (1 statement = 1 transaccion). No hay buffer que vaciar.
    logger_->info("[KUZU-SINK] flush: {} registros materializados "
                  "(NetworkFlow + Alert/TelemetryEvent + arista)", writes_);
}

}  // namespace argus::correlation