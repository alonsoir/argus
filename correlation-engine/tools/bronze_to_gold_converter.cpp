// bronze_to_gold_converter.cpp — DAY 205
// Converter mínimo de Eslabón 1, Flujo A (ADR-058 §3, ratificado por el Consejo DAY 205).
//
// Lee un segmento bronce REAL (contrato correlation_v1, 19 cols) con el parser
// REAL del correlation-engine (parse_and_verify, cierra DEBT-CIRCUIT-PARSER-
// CROSSLANG-001 por reuso, no por promesa). Escribe:
//   1. bronce AVRO (cols 0-18, copia exacta — bronce PRESERVA)
//   2. oro Parquet, columnas D del predicado §3.1 (cols 0-21: bronce + flow_start_window
//      + seq_in_window + flow_uid materializados — cierra DEBT-GOLD-NODE-DIMENSION-001)
//
// FUERA DE ALCANCE HOY (deliberado, "un día, una batalla"):
//   - cols 22-23 (ingested_at, temporal_anomaly) — clase E, pendiente de la
//     decisión de jerarquía WAL (DEBT-CIRCUIT-TEMPORAL-ANOMALY-PARITY-001)
//   - test de equivalencia Camino0 vs FlujoA+B completo (ADR-058 §3.1)
//   - firma del Parquet consolidado como artefacto (DEBT-GOLD-INTEGRITY-HMAC-001,
//     la parte de "firma del artefacto"; el HMAC POR FILA sí se preserva aquí)
//
// CANONICALIZACION IEEE754 (DAY 207): la definicion local de
// canonicalize_double() y sus 3 llamadas SE RETIRARON de este
// fichero. El punto unico ahora vive en parse_and_verify
// (correlation_engine/canonical_double.hpp) -- corrige ADR-058 v3
// fila 16a ("punto unico: converter"): el confluente REAL de
// Camino 0 y Flujo A+B es parse_and_verify, no este converter.
// Este fichero hereda records ya canonicalizados sin hacer nada
// especial. Verificado: 24/24 filas identicas antes/despues del
// cambio contra logs/correlation/argus/2026-07-04-032653.csv.
//
// USO: bronze_to_gold_converter <bronce.csv> <bronce_salida.avro> <oro_salida.parquet>
//      Requiere env ARGUS_BRONZE_HMAC_KEY_HEX (64 hex chars, mismo patrón que el
//      lado lector de DEBT-BRONZE-KEY-PROVISIONING-001).

#include "correlation_engine/correlation_reader.hpp"
#include "correlation_engine/correlation_record.hpp"
#include "correlation_engine/flow_uid.hpp"

#include <avro.h>
#include <sodium.h>

#include <arrow/api.h>
#include <arrow/io/api.h>
#include <parquet/arrow/writer.h>

#include <bit>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <optional>
#include <sstream>
#include <string>
#include <vector>

using argus::correlation::CorrelationRecord;
using argus::correlation::parse_and_verify;

namespace {

// hex_decode: mismo patrón que CorrelationWriter (ml-detector), lado escritor.
// 64 hex chars -> 32 bytes crudos. Aquí, lado lector del converter.
std::vector<uint8_t> hex_decode(const std::string& hex) {
    if (hex.size() != 64) {
        throw std::invalid_argument(
            "ARGUS_BRONZE_HMAC_KEY_HEX debe ser 64 hex chars (32 bytes), obtenido " +
            std::to_string(hex.size()));
    }
    std::vector<uint8_t> out;
    out.reserve(32);
    for (size_t i = 0; i < hex.size(); i += 2) {
        unsigned int byte;
        if (std::sscanf(hex.c_str() + i, "%02x", &byte) != 1) {
            throw std::invalid_argument("hex inválido en posición " + std::to_string(i));
        }
        out.push_back(static_cast<uint8_t>(byte));
    }
    return out;
}

// El HMAC (col 18) no vive en CorrelationRecord — parse_and_verify lo valida y
// lo descarta tras confirmar la firma. Lo extraemos por nuestra cuenta con la
// MISMA técnica que usa correlation_reader.cpp internamente (última coma de la
// línea): DEBT-GOLD-INTEGRITY-HMAC-001 exige preservarlo, la librería no lo expone.
std::optional<std::string> extract_hmac_field(const std::string& line) {
    auto last = line.rfind(',');
    if (last == std::string::npos) return std::nullopt;
    return line.substr(last + 1);
}

const char* kBronzeAvroSchemaJson = R"({
  "type": "record",
  "name": "CorrelationV1Bronze",
  "namespace": "argus.correlation.gold_v1",
  "fields": [
    { "name": "schema_version",       "type": "string" },
    { "name": "source_sensor",        "type": "string" },
    { "name": "event_id",             "type": "string" },
    { "name": "node_id",              "type": "string" },
    { "name": "community_id",         "type": "string" },
    { "name": "flow_start_sec",       "type": "long" },
    { "name": "flow_start_nano",      "type": "int" },
    { "name": "src_ip",               "type": "string" },
    { "name": "dst_ip",               "type": "string" },
    { "name": "src_port",             "type": "int",
      "doc": "Unsigned uint32_t del proto. Rango válido: 0-65535. Valores >= 2^31 son reservados para extensión futura." },
    { "name": "dst_port",             "type": "int",
      "doc": "Unsigned uint32_t del proto. Rango válido: 0-65535. Valores >= 2^31 son reservados para extensión futura." },
    { "name": "protocol",             "type": "string" },
    { "name": "final_classification", "type": "string" },
    { "name": "threat_category",      "type": "string" },
    { "name": "fast_detector_score",  "type": "double" },
    { "name": "ml_detector_score",    "type": "double" },
    { "name": "overall_threat_score", "type": "double" },
    { "name": "authoritative_source", "type": "string" },
    { "name": "hmac_row",             "type": "string" }
  ]
})";

struct GoldRow {
    CorrelationRecord bronze;
    std::string hmac_row;
    uint64_t flow_start_window;
    uint32_t seq_in_window;
    std::string flow_uid;
};

void die(const std::string& msg) {
    std::cerr << "FATAL: " << msg << "\n";
    std::exit(1);
}

// --- Paso 1: leer bronce, validar+parsear con el parser REAL, materializar oro ---
std::vector<GoldRow> read_bronze_segment(const std::string& path,
                                          const std::vector<uint8_t>& hmac_key,
                                          size_t& total_lines,
                                          size_t& rejected_lines) {
    std::ifstream in(path);
    if (!in.is_open()) die("no se pudo abrir bronce: " + path);

    std::vector<GoldRow> rows;
    std::string line;
    total_lines = 0;
    rejected_lines = 0;

    while (std::getline(in, line)) {
        if (line.empty()) continue;
        ++total_lines;

        auto parsed = parse_and_verify(line, hmac_key);
        if (!parsed) {
            ++rejected_lines;
            std::cerr << "  [DESCARTADA] línea " << total_lines
                      << " — HMAC inválido, columnas incorrectas, o campo numérico ilegible\n";
            continue;
        }
        auto hmac = extract_hmac_field(line);
        if (!hmac) {
            ++rejected_lines;
            std::cerr << "  [DESCARTADA] línea " << total_lines << " — sin campo HMAC extraíble\n";
            continue;
        }

        GoldRow row;
        row.bronze = *parsed;
        row.hmac_row = *hmac;

        // Bloque oro: flow_start_window materializado con el MISMO window_micros()
        // que alimenta el hash en Camino 0 (correlation-engine/src/main.cpp:117).
        row.flow_start_window =
            argus::correlation::window_micros(row.bronze.flow_start_sec, row.bronze.flow_start_nano);
        // seq_in_window fijo a 0 — DEBT-FLOWUID-SEQ-COLLISION-001, sin resolver aún.
        row.seq_in_window = 0;
        // flow_uid recomputado con el encoding canónico REAL, verificable bit a bit
        // contra lo que Kuzu ya materializa en Camino 0 (cypher_builder.hpp:101,110).
        row.flow_uid = argus::correlation::compute_flow_uid(
            row.bronze.node_id, row.bronze.community_id, row.flow_start_window, row.seq_in_window);

        rows.push_back(std::move(row));
    }
    return rows;
}

// --- Paso 2: escribir bronce AVRO (cols 0-18, copia exacta) ---
void write_bronze_avro(const std::string& path, const std::vector<GoldRow>& rows) {
    avro_schema_t schema;
    if (avro_schema_from_json_length(kBronzeAvroSchemaJson, std::strlen(kBronzeAvroSchemaJson),
                                      &schema) != 0) {
        die("avro_schema_from_json_length falló");
    }
    avro_value_iface_t* iface = avro_generic_class_from_schema(schema);
    avro_value_t value;
    avro_generic_value_new(iface, &value);

    avro_file_writer_t writer;
    if (avro_file_writer_create(path.c_str(), schema, &writer) != 0) {
        die("avro_file_writer_create falló para " + path);
    }

    for (const auto& row : rows) {
        avro_value_reset(&value);
        avro_value_t field;

        auto set_str = [&](const char* name, const std::string& s) {
            avro_value_get_by_name(&value, name, &field, nullptr);
            avro_value_set_string(&field, s.c_str());
        };

        set_str("schema_version", row.bronze.schema_version);
        set_str("source_sensor", row.bronze.source_sensor);
        set_str("event_id", row.bronze.event_id);
        set_str("node_id", row.bronze.node_id);
        set_str("community_id", row.bronze.community_id);

        avro_value_get_by_name(&value, "flow_start_sec", &field, nullptr);
        avro_value_set_long(&field, row.bronze.flow_start_sec);
        avro_value_get_by_name(&value, "flow_start_nano", &field, nullptr);
        avro_value_set_int(&field, row.bronze.flow_start_nano);

        set_str("src_ip", row.bronze.src_ip);
        set_str("dst_ip", row.bronze.dst_ip);

        avro_value_get_by_name(&value, "src_port", &field, nullptr);
        avro_value_set_int(&field, static_cast<int32_t>(row.bronze.src_port));
        avro_value_get_by_name(&value, "dst_port", &field, nullptr);
        avro_value_set_int(&field, static_cast<int32_t>(row.bronze.dst_port));

        set_str("protocol", row.bronze.protocol);
        set_str("final_classification", row.bronze.final_classification);
        set_str("threat_category", row.bronze.threat_category);

        avro_value_get_by_name(&value, "fast_detector_score", &field, nullptr);
        avro_value_set_double(&field, row.bronze.fast_detector_score);
        avro_value_get_by_name(&value, "ml_detector_score", &field, nullptr);
        avro_value_set_double(&field, row.bronze.ml_detector_score);
        avro_value_get_by_name(&value, "overall_threat_score", &field, nullptr);
        avro_value_set_double(&field, row.bronze.overall_threat_score);

        set_str("authoritative_source", row.bronze.authoritative_source);
        set_str("hmac_row", row.hmac_row);

        if (avro_file_writer_append_value(writer, &value) != 0) {
            die("avro_file_writer_append_value falló");
        }
    }

    avro_file_writer_close(writer);
    avro_value_decref(&value);
    avro_value_iface_decref(iface);
    avro_schema_decref(schema);
}

// --- Paso 3: escribir oro Parquet (cols D: 0-21) ---
void write_gold_parquet(const std::string& path, const std::vector<GoldRow>& rows) {
    arrow::StringBuilder schema_version_b, source_sensor_b, event_id_b, node_id_b,
        community_id_b, src_ip_b, dst_ip_b, protocol_b, final_classification_b,
        threat_category_b, authoritative_source_b, hmac_row_b, flow_uid_b;
    arrow::Int64Builder flow_start_sec_b;
    arrow::Int32Builder flow_start_nano_b, src_port_b, dst_port_b, seq_in_window_b;
    arrow::DoubleBuilder fast_score_b, ml_score_b, overall_score_b;
    arrow::Int64Builder flow_start_window_b;  // uint64_t cabe en int64 para timestamps reales

    for (const auto& row : rows) {
        auto ok = [](const arrow::Status& s) {
            if (!s.ok()) die("Arrow builder Append falló: " + s.ToString());
        };
        ok(schema_version_b.Append(row.bronze.schema_version));
        ok(source_sensor_b.Append(row.bronze.source_sensor));
        ok(event_id_b.Append(row.bronze.event_id));
        ok(node_id_b.Append(row.bronze.node_id));
        ok(community_id_b.Append(row.bronze.community_id));
        ok(flow_start_sec_b.Append(row.bronze.flow_start_sec));
        ok(flow_start_nano_b.Append(row.bronze.flow_start_nano));
        ok(src_ip_b.Append(row.bronze.src_ip));
        ok(dst_ip_b.Append(row.bronze.dst_ip));
        ok(src_port_b.Append(static_cast<int32_t>(row.bronze.src_port)));
        ok(dst_port_b.Append(static_cast<int32_t>(row.bronze.dst_port)));
        ok(protocol_b.Append(row.bronze.protocol));
        ok(final_classification_b.Append(row.bronze.final_classification));
        ok(threat_category_b.Append(row.bronze.threat_category));
        ok(fast_score_b.Append(row.bronze.fast_detector_score));
        ok(ml_score_b.Append(row.bronze.ml_detector_score));
        ok(overall_score_b.Append(row.bronze.overall_threat_score));
        ok(authoritative_source_b.Append(row.bronze.authoritative_source));
        ok(hmac_row_b.Append(row.hmac_row));
        ok(flow_start_window_b.Append(static_cast<int64_t>(row.flow_start_window)));
        ok(seq_in_window_b.Append(static_cast<int32_t>(row.seq_in_window)));
        ok(flow_uid_b.Append(row.flow_uid));
    }

    std::vector<std::shared_ptr<arrow::Array>> arrays(21);
    auto finish = [](arrow::ArrayBuilder& b, std::shared_ptr<arrow::Array>& out) {
        if (!b.Finish(&out).ok()) die("Arrow builder Finish falló");
    };
    finish(schema_version_b, arrays[0]);
    finish(source_sensor_b, arrays[1]);
    finish(event_id_b, arrays[2]);
    finish(node_id_b, arrays[3]);
    finish(community_id_b, arrays[4]);
    finish(flow_start_sec_b, arrays[5]);
    finish(flow_start_nano_b, arrays[6]);
    finish(src_ip_b, arrays[7]);
    finish(dst_ip_b, arrays[8]);
    finish(src_port_b, arrays[9]);
    finish(dst_port_b, arrays[10]);
    finish(protocol_b, arrays[11]);
    finish(final_classification_b, arrays[12]);
    finish(threat_category_b, arrays[13]);
    finish(fast_score_b, arrays[14]);
    finish(ml_score_b, arrays[15]);
    finish(overall_score_b, arrays[16]);
    finish(authoritative_source_b, arrays[17]);
    finish(hmac_row_b, arrays[18]);
    finish(flow_start_window_b, arrays[19]);
    finish(seq_in_window_b, arrays[20]);
    // arrays tiene 21 elementos (índices 0-20) tras los finish() de arriba.
    // flow_uid se añade como col 21 (índice 21) para completar las 22 columnas
    // del esquema D del oro (cols 0-21 del predicado §3.1).

    std::shared_ptr<arrow::Array> flow_uid_arr;
    if (!flow_uid_b.Finish(&flow_uid_arr).ok()) die("flow_uid_b.Finish falló");
    arrays.push_back(flow_uid_arr);  // col 21

    auto schema = arrow::schema({
        arrow::field("schema_version", arrow::utf8()),
        arrow::field("source_sensor", arrow::utf8()),
        arrow::field("event_id", arrow::utf8()),
        arrow::field("node_id", arrow::utf8()),
        arrow::field("community_id", arrow::utf8()),
        arrow::field("flow_start_sec", arrow::int64()),
        arrow::field("flow_start_nano", arrow::int32()),
        arrow::field("src_ip", arrow::utf8()),
        arrow::field("dst_ip", arrow::utf8()),
        arrow::field("src_port", arrow::int32()),
        arrow::field("dst_port", arrow::int32()),
        arrow::field("protocol", arrow::utf8()),
        arrow::field("final_classification", arrow::utf8()),
        arrow::field("threat_category", arrow::utf8()),
        arrow::field("fast_detector_score", arrow::float64()),
        arrow::field("ml_detector_score", arrow::float64()),
        arrow::field("overall_threat_score", arrow::float64()),
        arrow::field("authoritative_source", arrow::utf8()),
        arrow::field("hmac_row", arrow::utf8()),
        arrow::field("flow_start_window", arrow::int64()),
        arrow::field("seq_in_window", arrow::int32()),
        arrow::field("flow_uid", arrow::utf8()),
    });

    auto table = arrow::Table::Make(schema, arrays);

    auto maybe_outfile = arrow::io::FileOutputStream::Open(path);
    if (!maybe_outfile.ok()) die("FileOutputStream::Open falló: " + maybe_outfile.status().ToString());
    auto status = parquet::arrow::WriteTable(*table, arrow::default_memory_pool(), *maybe_outfile, 1024);
    if (!status.ok()) die("parquet::arrow::WriteTable falló: " + status.ToString());
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 4) {
        std::cerr << "USO: " << argv[0] << " <bronce.csv> <bronce_salida.avro> <oro_salida.parquet>\n";
        return 1;
    }
    const std::string in_path = argv[1];
    const std::string avro_out_path = argv[2];
    const std::string parquet_out_path = argv[3];

    if (sodium_init() < 0) die("sodium_init() falló");

    const char* key_hex_env = std::getenv("ARGUS_BRONZE_HMAC_KEY_HEX");
    if (!key_hex_env) die("ARGUS_BRONZE_HMAC_KEY_HEX no definida (DEBT-BRONZE-KEY-PROVISIONING-001)");
    std::vector<uint8_t> hmac_key = hex_decode(key_hex_env);

    size_t total_lines = 0, rejected_lines = 0;
    std::cout << "Leyendo bronce: " << in_path << "\n";
    auto rows = read_bronze_segment(in_path, hmac_key, total_lines, rejected_lines);

    std::cout << "  líneas totales:  " << total_lines << "\n";
    std::cout << "  filas válidas:   " << rows.size() << "\n";
    std::cout << "  filas descartadas: " << rejected_lines << "\n";

    if (rows.empty()) {
        std::cerr << "Sin filas válidas — nada que escribir.\n";
        return 1;
    }

    std::cout << "Escribiendo bronce AVRO: " << avro_out_path << "\n";
    write_bronze_avro(avro_out_path, rows);

    std::cout << "Escribiendo oro Parquet (cols D, 0-21): " << parquet_out_path << "\n";
    write_gold_parquet(parquet_out_path, rows);

    std::cout << "\nOK — " << rows.size() << " filas convertidas.\n";
    std::cout << "Ejemplo flow_uid recomputado (fila 0): " << rows[0].flow_uid << "\n";
    std::cout << "  (verificar bit a bit contra la propiedad flow_uid ya materializada en Kuzu)\n";
    return 0;
}