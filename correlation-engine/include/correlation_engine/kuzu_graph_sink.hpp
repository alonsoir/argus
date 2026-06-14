// kuzu_graph_sink.hpp — backend IGraphSink sobre Kuzu v0.11.3 embebido (DAY 180 / batch DAY 184).
// aRGus NDR. Authors: Alonso Isidoro Roman + Claude (Anthropic).
//
// DAY 184: write() ACUMULA (copia record+flow_uid+ts), flush() ejecuta el batch en UNA
// transaccion via PreparedStatement parametrizado (cierra H-1 en el path EJECUTADO).
#pragma once
#include "correlation_engine/i_graph_sink.hpp"

#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include <spdlog/spdlog.h>

// Forward-decl: el header NO arrastra kuzu.hpp. unique_ptr a tipo incompleto -> dtor out-of-line.
namespace kuzu::main { class Database; class Connection; class PreparedStatement; }

namespace argus::correlation {

    class KuzuGraphSink final : public IGraphSink {
    public:
        // flush_rows / flush_interval_ns: triggers inline del flush (tamaño O tiempo).
        // PLACEHOLDER a calibrar en la tortura E2E (medir, no votar) — como kTemporalMarginNs.
        KuzuGraphSink(const std::string& db_path,
                      const std::string& schema_path,
                      std::shared_ptr<spdlog::logger> logger,
                      std::size_t flush_rows        = 512,
                      uint64_t    flush_interval_ns = 1'000'000'000ULL);  // 1s
        ~KuzuGraphSink() override;  // out-of-line: tipos Kuzu incompletos en el header

        KuzuGraphSink(const KuzuGraphSink&)            = delete;
        KuzuGraphSink& operator=(const KuzuGraphSink&) = delete;

        bool        write(const CorrelationRecord& record, std::string_view flow_uid) override;
        FlushResult flush() override;

        uint64_t writes() const noexcept { return writes_; }              // filas COMMITTEADAS
        std::size_t pending() const noexcept { return accumulator_.size(); }  // en buffer

    private:
        void load_schema(const std::string& schema_path);

        struct AccumEntry {
            CorrelationRecord record;       // copia: el record de write() no sobrevive al batch
            std::string       flow_uid;     // materializado del string_view de write()
            uint64_t          ingested_at;  // ingest_now_ns() sellado a la ENTRADA, per-fila
        };

        // ── ORDEN DE LIFETIME (NO REORDENAR) ──────────────────────────────────────────
        // Destruccion = orden inverso: preps -> conn -> db. PreparedStatement/QueryResult
        // sostienen refs al BufferManager de la Database: DEBEN morir antes que conn_/db_.
        // El header de Kuzu lo dice literal: rollback-on-destruction sobre db cerrada = SEGFAULT.
        std::unique_ptr<kuzu::main::Database>          db_;
        std::unique_ptr<kuzu::main::Connection>        conn_;
        std::unique_ptr<kuzu::main::PreparedStatement> prep_alert_;
        std::unique_ptr<kuzu::main::PreparedStatement> prep_telemetry_;
        // ──────────────────────────────────────────────────────────────────────────────

        std::shared_ptr<spdlog::logger> logger_;
        std::vector<AccumEntry>         accumulator_;
        uint64_t                        last_flush_ns_    = 0;
        std::size_t                     flush_rows_;
        uint64_t                        flush_interval_ns_;
        uint64_t                        writes_ = 0;  // total COMMITTEADO (no aceptado)
    };

}  // namespace argus::correlation