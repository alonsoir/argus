// kuzu_graph_sink.cpp — backend IGraphSink sobre Kuzu embebido (DAY 180 / batch DAY 184).
// Authors: Alonso Isidoro Roman + Claude (Anthropic).
#include "correlation_engine/kuzu_graph_sink.hpp"
#include "correlation_engine/cypher_builder.hpp"
#include "correlation_engine/ingest_clock.hpp"

#include <kuzu.hpp>

#include <fstream>
#include <sstream>
#include <stdexcept>
#include <utility>
#include <vector>

namespace argus::correlation {

using kuzu::main::Connection;
using kuzu::main::Database;
using kuzu::main::PreparedStatement;
using kuzu::main::SystemConfig;

namespace {

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

// Binder de PRODUCCION: ejecuta UNA fila via prepared statement parametrizado.
// 14 params distintos (ingested_at se referencia en f Y e pero se bindea UNA vez).
// Los std::string temporales viven hasta que execute() retorna (misma full-expression):
// el requisito "14 vivos a la vez" se cumple por construccion. Esto es el path que cierra
// H-1 ESTRUCTURALMENTE: cero interpolacion de datos de red.
bool exec_row(Connection& conn, PreparedStatement* prep,
              const CypherBindings& b, spdlog::logger& log) {
    auto r = conn.execute(prep,
        std::pair{std::string("flow_uid"),             std::string(b.flow_uid)},
        std::pair{std::string("node_id"),              std::string(b.node_id)},
        std::pair{std::string("community_id"),         std::string(b.community_id)},
        std::pair{std::string("flow_start_window"),    b.flow_start_window},   // uint64_t
        std::pair{std::string("seq_in_window"),        b.seq_in_window},       // uint32_t
        std::pair{std::string("ingested_at"),          b.ingested_at},         // uint64_t
        std::pair{std::string("temporal_anomaly"),     b.temporal_anomaly},    // bool
        std::pair{std::string("event_id"),             std::string(b.event_id)},
        std::pair{std::string("final_classification"), std::string(b.final_classification)},
        std::pair{std::string("threat_category"),      std::string(b.threat_category)},
        std::pair{std::string("fast_detector_score"),  b.fast_detector_score}, // double
        std::pair{std::string("ml_detector_score"),    b.ml_detector_score},   // double
        std::pair{std::string("overall_threat_score"), b.overall_threat_score},// double
        std::pair{std::string("authoritative_source"), std::string(b.authoritative_source)});
    if (!r->isSuccess()) {
        log.error("[KUZU-SINK] execute fallo (event_id='{}'): {}", b.event_id, r->getErrorMessage());
        return false;
    }
    return true;  // r (QueryResult) muere AQUI, dentro de la iteracion, antes de cerrar nada
}

}  // namespace

KuzuGraphSink::KuzuGraphSink(const std::string& db_path,
                             const std::string& schema_path,
                             std::shared_ptr<spdlog::logger> logger,
                             std::size_t flush_rows,
                             uint64_t    flush_interval_ns)
    : logger_(std::move(logger)),
      flush_rows_(flush_rows),
      flush_interval_ns_(flush_interval_ns) {
    SystemConfig cfg;
    db_   = std::make_unique<Database>(db_path, cfg);
    conn_ = std::make_unique<Connection>(db_.get());
    load_schema(schema_path);  // catalogo poblado ANTES de prepare (MERGE bindea contra labels)

    // Fail-closed: si una plantilla no prepara, el sink no nace.
    prep_alert_ = conn_->prepare(kAlertCypherTemplate);
    if (!prep_alert_ || !prep_alert_->isSuccess())
        throw std::runtime_error("KuzuGraphSink: prepare(alert) fallo: " +
            (prep_alert_ ? prep_alert_->getErrorMessage() : std::string("null")));
    prep_telemetry_ = conn_->prepare(kTelemetryCypherTemplate);
    if (!prep_telemetry_ || !prep_telemetry_->isSuccess())
        throw std::runtime_error("KuzuGraphSink: prepare(telemetry) fallo: " +
            (prep_telemetry_ ? prep_telemetry_->getErrorMessage() : std::string("null")));

    last_flush_ns_ = ingest_now_ns();
    logger_->info("[KUZU-SINK] BD '{}' lista; schema '{}' cargado; 2 prepared listas "
                  "(flush: {} filas | {} ns)", db_path, schema_path, flush_rows_, flush_interval_ns_);
}

KuzuGraphSink::~KuzuGraphSink() {
    // NO flush en destructor (no se puede surface el fallo; rollback-on-close = SEGFAULT zone).
    // Si queda buffer, la durabilidad SE VIOLO: alguien olvido el flush() final. Gritamos.
    if (!accumulator_.empty()) {
        logger_->error("[KUZU-SINK] DESTRUCTOR con {} filas SIN volcar (durabilidad violada: "
                       "falto flush() final). NO se materializaron.", accumulator_.size());
    }
}

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
    if (record.node_id.empty() || flow_uid.empty()) {
        logger_->error("[KUZU-SINK] descarto registro sin node_id/flow_uid (event_id='{}')",
                       record.event_id);
        return false;
    }
    const uint64_t ts = ingest_now_ns();  // first_seen sellado a la ENTRADA, per-fila (Frente C:
                                          // MISMA fuente que el resto del pipeline = replay-stable)
    accumulator_.push_back(AccumEntry{record, std::string(flow_uid), ts});  // copia

    // Trigger inline: tamaño O tiempo. CAVEAT: el de tiempo NO dispara si write() deja de
    // llamarse (idle) -> frontera del writer-con-tick (ADR-057 §8, diferido). No muerde para
    // reproducir throughput; si cuando T sea SLA de staleness.
    const bool by_size = accumulator_.size() >= flush_rows_;
    const bool by_time = (ts - last_flush_ns_) >= flush_interval_ns_;
    if (by_size || by_time) {
        const auto fr = flush();
        if (!fr) {
            // Fallo de durabilidad en flush inline: el buffer SE QUEDA (reintento en proximo
            // write/flush). La fila YA esta acumulada (no se pierde). La verdad de durabilidad
            // la da flush()->FlushResult; el flush() final en main es el gate (EXIT_FAILURE).
            // DEBT (ADR-057 §8): si flush falla sostenidamente el buffer crece sin cota.
            logger_->error("[KUZU-SINK] flush inline FALLO: {} filas pendientes (retenidas)",
                           fr.rows_pending);
            // 'aceptado' = entro al buffer durable: la fila esta a salvo y se reintentara.
            return true;
        }
    }
    return true;
}

FlushResult KuzuGraphSink::flush() {
    if (accumulator_.empty()) {
        return FlushResult{true, 0, 0};  // nada que volcar
    }
    const std::size_t n_pending = accumulator_.size();

    auto begin = conn_->query("BEGIN TRANSACTION");
    if (!begin->isSuccess()) {
        logger_->error("[KUZU-SINK] BEGIN fallo: {} | {} filas retenidas",
                       begin->getErrorMessage(), n_pending);
        return FlushResult{false, 0, n_pending};  // buffer INTACTO (reintento)
    }

    // 1 checkpoint por batch (la amortizacion). Cada QueryResult del execute muere DENTRO
    // del bucle (en exec_row), antes de COMMIT y antes de cerrar nada.
    for (const auto& e : accumulator_) {
        const CypherBindings b = make_bindings(e.record, e.flow_uid, e.ingested_at);
        PreparedStatement* prep = b.is_alert ? prep_alert_.get() : prep_telemetry_.get();
        if (!exec_row(*conn_, prep, b, *logger_)) {
            auto rb = conn_->query("ROLLBACK");
            if (!rb->isSuccess())
                logger_->error("[KUZU-SINK] ROLLBACK fallo: {}", rb->getErrorMessage());
            logger_->error("[KUZU-SINK] flush ROLLBACK: nada durable, {} filas retenidas",
                           n_pending);
            return FlushResult{false, 0, n_pending};  // tx entera revertida: 0 durable, buffer queda
        }
    }

    auto commit = conn_->query("COMMIT");
    if (!commit->isSuccess()) {
        logger_->error("[KUZU-SINK] COMMIT fallo: {} | {} filas retenidas",
                       commit->getErrorMessage(), n_pending);
        return FlushResult{false, 0, n_pending};  // conservador: buffer queda (reintento)
    }

    writes_       += n_pending;        // solo cuenta lo COMMITTEADO
    last_flush_ns_ = ingest_now_ns();
    accumulator_.clear();              // limpia SOLO en exito
    logger_->info("[KUZU-SINK] flush OK: {} filas committeadas (total durable {})",
                  n_pending, writes_);
    return FlushResult{true, n_pending, 0};
}

}  // namespace argus::correlation