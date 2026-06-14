// kuzu_graph_sink.hpp — backend IGraphSink sobre Kuzu v0.11.3 embebido (DAY 180).
// aRGus NDR. Authors: Alonso Isidoro Roman + Claude (Anthropic).
//
// Materializa el modelo del schema.cypher (ADR-052) ejecutando el Cypher de
// cypher_builder.hpp contra una BD Kuzu embebida (fichero unico .kuzu, v0.11.0+).
// Mismo build_cypher() que LoggingGraphSink -> ambos backends emiten Cypher identico.
//
// Forward-declaration de los tipos Kuzu: el header NO arrastra kuzu.hpp a sus
// consumidores (solo el .cpp lo incluye). unique_ptr a tipo incompleto -> dtor out-of-line.
#pragma once
#include "correlation_engine/i_graph_sink.hpp"

#include <cstdint>
#include <memory>
#include <string>

#include <spdlog/spdlog.h>

namespace kuzu::main { class Database; class Connection; }

namespace argus::correlation {

    class KuzuGraphSink final : public IGraphSink {
    public:
        // db_path:     fichero .kuzu (single-file). Persistente entre runs (MERGE = idempotente).
        // schema_path: schema.cypher (DDL idempotente con IF NOT EXISTS), cargado al construir.
        KuzuGraphSink(const std::string& db_path,
                      const std::string& schema_path,
                      std::shared_ptr<spdlog::logger> logger);
        ~KuzuGraphSink() override;  // out-of-line: tipos Kuzu incompletos en el header

        KuzuGraphSink(const KuzuGraphSink&)            = delete;
        KuzuGraphSink& operator=(const KuzuGraphSink&) = delete;

        bool write(const CorrelationRecord& record, std::string_view flow_uid) override;
        FlushResult flush() override;

        uint64_t writes() const noexcept { return writes_; }

    private:
        void load_schema(const std::string& schema_path);

        std::unique_ptr<kuzu::main::Database>   db_;
        std::unique_ptr<kuzu::main::Connection> conn_;
        std::shared_ptr<spdlog::logger>         logger_;
        uint64_t writes_ = 0;
    };

}  // namespace argus::correlation