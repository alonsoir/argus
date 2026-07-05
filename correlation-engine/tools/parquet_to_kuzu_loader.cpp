// parquet_to_kuzu_loader.cpp — DAY 208
// Flujo B, Eslabón 2 (ADR-058 §6, DEBT-PARQUET-KUZU-CONNECTOR-001).
// Ratificado por el Consejo de Sabios (9/9, DAY 207) — ver
// docs/council/PROPUESTA -- Flujo B, parquet_to_kuzu_loader (DAY 207).md
// y su resolución final anexada al mismo fichero.
//
// Lee el Parquet oro (cols 0-21, ya materializado por Flujo A —
// bronze_to_gold_converter.cpp) y lo escribe a Kuzu reusando el sink
// existente. CERO cambios en IGraphSink/KuzuGraphSink.
//
// PUNTO ÚNICO DE VERDAD (ChatGPT, ronda de Consejo DAY 207): este loader
// no genera Cypher ni conoce el esquema de Kuzu. Toda la lógica de
// persistencia permanece encapsulada en KuzuGraphSink — único punto de
// mantenimiento para la escritura al grafo.
//
// ALCANCE v1 (decisión Alonso, DAY 207): esquema mono-fuente correlation_v1
// únicamente (source_sensor="argus"). El caso multi-sensor (aRGus+Suricata+
// Zeek+Wazuh combinables) es DEBT-PARQUET-GOLD-SCHEMA-MULTISENSOR-001,
// requiere su propio diseño + su propia ronda de Consejo. NO tratar de
// generalizar este fichero para ese caso sin pasar por ahí primero.
//
// DECISIÓN DE CHUNKING (Alonso, DAY 207 — desviación deliberada de la
// mayoría del Consejo, que proponía assert-y-diferir): bucle multi-chunk
// COMPLETO desde el primer commit. Procesa TODOS los chunks de cada
// columna siempre — dato correcto, cero pérdida silenciosa — y emite un
// WARNING (nunca excepción/fail-fast) si num_chunks() > 1, únicamente
// para visibilidad de cuándo el supuesto de "ficheros pequeños,
// particionado por fecha" empieza a dejar de cumplirse en la práctica.
//
// MANEJO DE ERROR (GLM, ronda de Consejo DAY 207): si el Parquet gold no
// existe todavía (Flujo B corriendo antes que Flujo A), falla con mensaje
// explícito, no con un crash genérico de Arrow.
//
// Cols NO usadas como fuente de verdad (documentado explícitamente, no
// dejarlo implícito — lección de la propia crítica adversarial DAY 207):
//   18 hmac_row           — no forma parte de CorrelationRecord; se valida
//                           y descarta en parse_and_verify (Flujo A). El
//                           control de integridad bronce↔oro-ledger vive
//                           en DEBT-GOLD-INTEGRITY-HMAC-001, fuera de aquí.
//   19 flow_start_window  — KuzuGraphSink/cypher_builder.hpp::make_bindings
//                           RECALCULA window_micros(flow_start_sec,
//                           flow_start_nano) internamente; no acepta un
//                           valor precomputado. Leerla sería trabajo
//                           redundante sin efecto.
//   20 seq_in_window      — siempre 0 hoy (DEBT-FLOWUID-SEQ-COLLISION-001).
//                           No es un parámetro que IGraphSink::write() acepte.
//
// USO: parquet_to_kuzu_loader <oro.parquet> <kuzu_db_path> <kuzu_schema_path>

#include "correlation_engine/correlation_record.hpp"
#include "correlation_engine/kuzu_graph_sink.hpp"

#include <arrow/api.h>
#include <arrow/io/api.h>
#include <parquet/arrow/reader.h>

#include <spdlog/spdlog.h>
#include <spdlog/sinks/stdout_color_sinks.h>

#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

namespace fs = std::filesystem;
using argus::correlation::CorrelationRecord;
using argus::correlation::IGraphSink;
using argus::correlation::KuzuGraphSink;

namespace {

void die(const std::string& msg) {
    std::cerr << "FATAL: " << msg << "\n";
    std::exit(1);
}

// --- Extracción de columna completa, TODOS los chunks (decisión DAY 207) ---
// Concatena los valores de cada chunk en un vector plano indexado 0..num_rows-1,
// sin importar cuántos chunks tenga la ChunkedArray. WARNING (no excepción) si
// num_chunks() > 1 — visibilidad, no bloqueo.
template <typename ArrowArrayT, typename ValueT, typename ExtractFn>
std::vector<ValueT> extract_column(const std::shared_ptr<arrow::ChunkedArray>& chunked,
                                    const std::string& col_name,
                                    std::shared_ptr<spdlog::logger>& logger,
                                    ExtractFn extract) {
    std::vector<ValueT> out;
    out.reserve(static_cast<size_t>(chunked->length()));

    if (chunked->num_chunks() > 1) {
        logger->warn("parquet_to_kuzu_loader: columna '{}' tiene {} chunks "
                     "(esperado 1 dado el particionado actual) — procesando "
                     "todos, sin pérdida de datos", col_name, chunked->num_chunks());
    }

    for (int c = 0; c < chunked->num_chunks(); ++c) {
        auto arr = std::static_pointer_cast<ArrowArrayT>(chunked->chunk(c));
        for (int64_t i = 0; i < arr->length(); ++i) {
            out.push_back(extract(*arr, i));
        }
    }
    return out;
}

std::vector<std::string> extract_utf8(const std::shared_ptr<arrow::ChunkedArray>& chunked,
                                       const std::string& col_name,
                                       std::shared_ptr<spdlog::logger>& logger) {
    return extract_column<arrow::StringArray, std::string>(
        chunked, col_name, logger,
        [](const arrow::StringArray& a, int64_t i) { return a.GetString(i); });
}

std::vector<int64_t> extract_int64(const std::shared_ptr<arrow::ChunkedArray>& chunked,
                                    const std::string& col_name,
                                    std::shared_ptr<spdlog::logger>& logger) {
    return extract_column<arrow::Int64Array, int64_t>(
        chunked, col_name, logger,
        [](const arrow::Int64Array& a, int64_t i) { return a.Value(i); });
}

std::vector<int32_t> extract_int32(const std::shared_ptr<arrow::ChunkedArray>& chunked,
                                    const std::string& col_name,
                                    std::shared_ptr<spdlog::logger>& logger) {
    return extract_column<arrow::Int32Array, int32_t>(
        chunked, col_name, logger,
        [](const arrow::Int32Array& a, int64_t i) { return a.Value(i); });
}

std::vector<double> extract_double(const std::shared_ptr<arrow::ChunkedArray>& chunked,
                                    const std::string& col_name,
                                    std::shared_ptr<spdlog::logger>& logger) {
    return extract_column<arrow::DoubleArray, double>(
        chunked, col_name, logger,
        [](const arrow::DoubleArray& a, int64_t i) { return a.Value(i); });
}

// --- Paso 1: abrir y leer el Parquet oro completo en un arrow::Table ---
std::shared_ptr<arrow::Table> read_gold_parquet(const std::string& path) {
    if (!fs::exists(path)) {
        die("gold Parquet not found: " + path);
    }

    auto maybe_infile = arrow::io::ReadableFile::Open(path);
    if (!maybe_infile.ok()) {
        die("ReadableFile::Open falló para " + path + ": " +
            maybe_infile.status().ToString());
    }
    auto infile = maybe_infile.ValueOrDie();

    auto maybe_reader = parquet::arrow::OpenFile(infile, arrow::default_memory_pool());
    if (!maybe_reader.ok()) {
        die("parquet::arrow::OpenFile falló: " + maybe_reader.status().ToString());
    }
    std::unique_ptr<parquet::arrow::FileReader> reader = std::move(maybe_reader).ValueOrDie();

    auto maybe_table = reader->ReadTable();
    if (!maybe_table.ok()) {
        die("ReadTable falló: " + maybe_table.status().ToString());
    }
    return maybe_table.ValueOrDie();
}

// --- Paso 2: reconstruir CorrelationRecord (cols 0-17) + flow_uid (col 21) ---
// Cols 18-20 deliberadamente NO leídas — ver cabecera del fichero.
struct GoldRow {
    CorrelationRecord record;
    std::string flow_uid;
};

std::vector<GoldRow> table_to_gold_rows(const std::shared_ptr<arrow::Table>& table,
                                         std::shared_ptr<spdlog::logger>& logger) {
    const int64_t n = table->num_rows();

    auto schema_version = extract_utf8(table->column(0), "schema_version", logger);
    auto source_sensor   = extract_utf8(table->column(1), "source_sensor", logger);
    auto event_id        = extract_utf8(table->column(2), "event_id", logger);
    auto node_id         = extract_utf8(table->column(3), "node_id", logger);
    auto community_id    = extract_utf8(table->column(4), "community_id", logger);
    auto flow_start_sec  = extract_int64(table->column(5), "flow_start_sec", logger);
    auto flow_start_nano = extract_int32(table->column(6), "flow_start_nano", logger);
    auto src_ip          = extract_utf8(table->column(7), "src_ip", logger);
    auto dst_ip          = extract_utf8(table->column(8), "dst_ip", logger);
    auto src_port        = extract_int32(table->column(9), "src_port", logger);
    auto dst_port        = extract_int32(table->column(10), "dst_port", logger);
    auto protocol        = extract_utf8(table->column(11), "protocol", logger);
    auto final_class      = extract_utf8(table->column(12), "final_classification", logger);
    auto threat_category  = extract_utf8(table->column(13), "threat_category", logger);
    auto fast_score       = extract_double(table->column(14), "fast_detector_score", logger);
    auto ml_score         = extract_double(table->column(15), "ml_detector_score", logger);
    auto overall_score    = extract_double(table->column(16), "overall_threat_score", logger);
    auto authoritative    = extract_utf8(table->column(17), "authoritative_source", logger);
    // col 18 (hmac_row), 19 (flow_start_window), 20 (seq_in_window): omitidas a propósito.
    auto flow_uid_col     = extract_utf8(table->column(21), "flow_uid", logger);

    std::vector<GoldRow> rows;
    rows.reserve(static_cast<size_t>(n));
    for (int64_t i = 0; i < n; ++i) {
        CorrelationRecord r;
        r.schema_version       = schema_version[i];
        r.source_sensor        = source_sensor[i];
        r.event_id             = event_id[i];
        r.node_id              = node_id[i];
        r.community_id         = community_id[i];
        r.flow_start_sec       = flow_start_sec[i];
        r.flow_start_nano      = flow_start_nano[i];
        r.src_ip               = src_ip[i];
        r.dst_ip               = dst_ip[i];
        r.src_port             = static_cast<uint32_t>(src_port[i]);
        r.dst_port             = static_cast<uint32_t>(dst_port[i]);
        r.protocol             = protocol[i];
        r.final_classification = final_class[i];
        r.threat_category      = threat_category[i];
        r.fast_detector_score  = fast_score[i];
        r.ml_detector_score    = ml_score[i];
        r.overall_threat_score = overall_score[i];
        r.authoritative_source = authoritative[i];

        rows.push_back(GoldRow{std::move(r), flow_uid_col[i]});
    }
    return rows;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 4) {
        std::cerr << "USO: " << argv[0]
                  << " <oro.parquet> <kuzu_db_path> <kuzu_schema_path>\n";
        return 1;
    }
    const std::string parquet_path = argv[1];
    const std::string db_path      = argv[2];
    const std::string schema_path  = argv[3];

    auto logger = spdlog::stdout_color_mt("parquet-to-kuzu-loader");
    logger->info("Leyendo Parquet oro: {}", parquet_path);

    auto table = read_gold_parquet(parquet_path);
    logger->info("  filas totales: {}", table->num_rows());

    auto gold_rows = table_to_gold_rows(table, logger);

    logger->info("Abriendo Kuzu: {} (schema: {})", db_path, schema_path);
    KuzuGraphSink sink(db_path, schema_path, logger);

    uint64_t written = 0, failed = 0;
    for (const auto& gr : gold_rows) {
        if (sink.write(gr.record, gr.flow_uid)) {
            ++written;
        } else {
            ++failed;
            logger->warn("write() falló para event_id={}", gr.record.event_id);
        }
    }

    const auto fr = sink.flush();
    logger->info("Escritas: {}, fallidas: {}, flush ok={}, rows_flushed={}, rows_pending={}",
                 written, failed, fr.ok, fr.rows_flushed, fr.rows_pending);

    if (!fr) {
        logger->error("flush final FALLÓ: {} filas sin materializar (NO durable)",
                      fr.rows_pending);
        return 1;
    }
    if (failed > 0) {
        logger->warn("{} filas no se pudieron escribir (ver warnings arriba)", failed);
    }

    std::cout << "\nOK — " << written << " filas materializadas en Kuzu"
              << (failed > 0 ? " (con " + std::to_string(failed) + " fallidas)" : "")
              << ".\n";
    return 0;
}