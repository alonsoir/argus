// host_parquet_to_kuzu_loader — oro host Parquet -> Kuzu (BD host propia).
// Uso: host_parquet_to_kuzu_loader <oro.parquet> <kuzu_db_path> <schema.cypher>
// ISLA: la BD es del host, NUNCA el $KUZU de red.
#include <arrow/api.h>
#include <arrow/io/api.h>
#include <parquet/arrow/reader.h>
#include <kuzu.hpp>
#include <filesystem>
#include <cstdio>
#include <fstream>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

#include "host_engine/host_row.hpp"

using namespace host_engine;

namespace {

// Escapa una string para meterla como literal Cypher entre comillas simples.
std::string cy(const std::string& s) {
    std::string o;
    o.reserve(s.size() + 2);
    for (char c : s) {
        if (c == '\'') o += "\\'";
        else if (c == '\\') o += "\\\\";
        else o.push_back(c);
    }
    return o;
}

// Lee un fichero de texto entero (el schema.cypher).
std::string slurp(const std::string& path) {
    std::ifstream f(path);
    std::stringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

// Divide el schema en statements por ';' y los ejecuta uno a uno.
// (Kuzu 0.11.3 ejecuta un statement por query().)
void apply_schema(kuzu::main::Connection& conn, const std::string& schema) {
    std::string stmt;
    for (char c : schema) {
        if (c == ';') {
            std::string trimmed;
            for (char t : stmt) if (t!='\n' && t!='\r') trimmed.push_back(t);
            // salta líneas de comentario // ... y vacíos
            bool only_comment = true;
            {
                std::istringstream ls(stmt);
                std::string line;
                while (std::getline(ls, line)) {
                    std::size_t p = line.find_first_not_of(" \t\r\n");
                    if (p == std::string::npos) continue;
                    if (line.compare(p, 2, "//") == 0) continue;
                    only_comment = false; break;
                }
            }
            if (!only_comment) {
                auto r = conn.query(stmt + ";");
                if (!r->isSuccess()) {
                    std::fprintf(stderr, "[schema] fallo: %s\n", r->getErrorMessage().c_str());
                }
            }
            stmt.clear();
        } else {
            stmt.push_back(c);
        }
    }
}

// Extrae la columna utf8 i-ésima como vector<string>.
std::vector<std::string> col_utf8(const std::shared_ptr<arrow::Table>& t, int idx) {
    std::vector<std::string> out;
    auto chunked = t->column(idx);
    for (int c = 0; c < chunked->num_chunks(); ++c) {
        auto arr = std::static_pointer_cast<arrow::StringArray>(chunked->chunk(c));
        for (int64_t j = 0; j < arr->length(); ++j)
            out.push_back(arr->IsNull(j) ? "" : arr->GetString(j));
    }
    return out;
}

std::vector<int32_t> col_i32(const std::shared_ptr<arrow::Table>& t, int idx) {
    std::vector<int32_t> out;
    auto chunked = t->column(idx);
    for (int c = 0; c < chunked->num_chunks(); ++c) {
        auto arr = std::static_pointer_cast<arrow::Int32Array>(chunked->chunk(c));
        for (int64_t j = 0; j < arr->length(); ++j)
            out.push_back(arr->IsNull(j) ? 0 : arr->Value(j));
    }
    return out;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 4) {
        std::fprintf(stderr,
            "uso: %s <oro.parquet> <kuzu_db_path> <schema.cypher>\n", argv[0]);
        return 1;
    }
    const std::string parquet_path = argv[1];
    const std::string db_path      = argv[2];
    const std::string schema_path  = argv[3];

    try {
        // --- 1. Leer el Parquet oro por índice de columna (mismo orden que el converter) ---
        auto pool = arrow::default_memory_pool();
        std::shared_ptr<arrow::io::ReadableFile> infile;
        {
            auto res = arrow::io::ReadableFile::Open(parquet_path, pool);
            if (!res.ok()) { std::fprintf(stderr, "no abre %s: %s\n",
                parquet_path.c_str(), res.status().ToString().c_str()); return 2; }
            infile = *res;
        }
        std::unique_ptr<parquet::arrow::FileReader> reader;
        {
            auto res = parquet::arrow::OpenFile(infile, pool);
            if (!res.ok()) {
                std::fprintf(stderr, "no lee parquet %s: %s\n",
                    parquet_path.c_str(), res.status().ToString().c_str());
                return 2;
            }
            reader = std::move(*res);
        }
        std::shared_ptr<arrow::Table> table;
        {
            auto res = reader->ReadTable();
            if (!res.ok()) {
                std::fprintf(stderr, "no materializa tabla: %s\n",
                    res.status().ToString().c_str());
                return 2;
            }
            table = *res;
        }
        const int64_t nrows = table->num_rows();
        std::fprintf(stderr, "[host-loader] oro=%s filas=%lld cols=%d\n",
            parquet_path.c_str(), (long long)nrows, table->num_columns());

        // Índices de columna del oro host_domain_v1 (orden del contrato §5 / builders del converter).
        // AJUSTA estos índices si el converter emite otro orden — se verifica contra el schema del Parquet.
        enum Col {
            C_SCHEMA_VERSION=0, C_SOURCE_SENSOR=1, C_EVENT_ID=2, C_HOST_ID=3,
            C_WAZUH_ALERT_ID=4, C_TIMESTAMP=5, C_AGENT_ID=6, C_AGENT_NAME=7,
            C_AGENT_IP=8, C_OS_HOSTNAME=9, C_RULE_ID=10, C_RULE_LEVEL=11,
            C_RULE_DESCRIPTION=12, C_RULE_GROUPS=13, C_DECODER=14, C_LOCATION=15,
            C_FULL_LOG=16, C_DATA_JSON=17,
            C_SRCUSER=18, C_DSTUSER=19, C_SRCIP=20, C_SRCPORT=21, C_UID=22, C_COMMAND=23,
            C_MITRE_IDS=24, C_MITRE_TACTICS=25, C_MITRE_TECHNIQUES=26
        };

        auto event_id   = col_utf8(table, C_EVENT_ID);
        auto host_id    = col_utf8(table, C_HOST_ID);
        auto agent_name = col_utf8(table, C_AGENT_NAME);
        auto agent_ip   = col_utf8(table, C_AGENT_IP);
        auto os_host    = col_utf8(table, C_OS_HOSTNAME);
        auto ts         = col_utf8(table, C_TIMESTAMP);
        auto rule_id    = col_utf8(table, C_RULE_ID);
        auto level      = col_i32 (table, C_RULE_LEVEL);
        auto rule_desc  = col_utf8(table, C_RULE_DESCRIPTION);
        auto decoder    = col_utf8(table, C_DECODER);
        auto location   = col_utf8(table, C_LOCATION);
        auto full_log   = col_utf8(table, C_FULL_LOG);
        auto srcuser    = col_utf8(table, C_SRCUSER);
        auto dstuser    = col_utf8(table, C_DSTUSER);
        auto srcip      = col_utf8(table, C_SRCIP);
        auto srcport    = col_utf8(table, C_SRCPORT);
        auto uid        = col_utf8(table, C_UID);
        auto command    = col_utf8(table, C_COMMAND);
        auto data_json  = col_utf8(table, C_DATA_JSON);
        auto groups     = col_utf8(table, C_RULE_GROUPS);
        auto tactics    = col_utf8(table, C_MITRE_TACTICS);
        auto mids       = col_utf8(table, C_MITRE_IDS);
        auto mtech      = col_utf8(table, C_MITRE_TECHNIQUES);
        auto wz_id      = col_utf8(table, C_WAZUH_ALERT_ID);

        // Crea el dir padre de la BD si falta (cierra la fragilidad DAY 228:
        // el loader de red hacía terminate con el padre ausente).
        {
            std::filesystem::path dbp(db_path);
            if (dbp.has_parent_path())
                std::filesystem::create_directories(dbp.parent_path());
        }

        // --- 2. Abrir Kuzu (BD host propia) y aplicar el schema ---
        kuzu::main::SystemConfig cfg;
        auto db   = std::make_unique<kuzu::main::Database>(db_path, cfg);
        auto conn = std::make_unique<kuzu::main::Connection>(db.get());
        apply_schema(*conn, slurp(schema_path));

        // --- 3. Cargar. Un statement por fila con MERGE encadenados (idempotente). ---
        int64_t ok = 0, mism = 0;
        for (int64_t i = 0; i < nrows; ++i) {
            std::ostringstream q;
            q << "MERGE (h:Host {host_id:'" << cy(host_id[i]) << "'})"
              << " ON CREATE SET h.name='" << cy(agent_name[i]) << "', h.ip='"
              << cy(agent_ip[i]) << "', h.os_hostname='" << cy(os_host[i]) << "' ";
            q << "MERGE (e:HostEvent {event_id:'" << cy(event_id[i]) << "'})"
              << " ON CREATE SET e.timestamp='" << cy(ts[i]) << "', e.rule_id='"
              << cy(rule_id[i]) << "', e.level=" << level[i]
              << ", e.decoder='" << cy(decoder[i]) << "', e.location='" << cy(location[i])
              << "', e.full_log='" << cy(full_log[i]) << "', e.srcuser='" << cy(srcuser[i])
              << "', e.dstuser='" << cy(dstuser[i]) << "', e.srcip='" << cy(srcip[i])
              << "', e.srcport='" << cy(srcport[i]) << "', e.uid='" << cy(uid[i])
              << "', e.command='" << cy(command[i]) << "', e.data_json='" << cy(data_json[i])
              << "', e.wazuh_alert_id='" << cy(wz_id[i]) << "' ";
            q << "MERGE (r:Rule {rule_id:'" << cy(rule_id[i]) << "'})"
              << " ON CREATE SET r.level=" << level[i] << ", r.description='"
              << cy(rule_desc[i]) << "', r.groups='" << cy(groups[i])
              << "', r.tactics='" << cy(tactics[i]) << "' ";
            q << "MERGE (e)-[:ON_HOST]->(h) ";
            q << "MERGE (e)-[:MATCHED]->(r);";

            auto res = conn->query(q.str());
            if (!res->isSuccess()) {
                std::fprintf(stderr, "[fila %lld] fallo: %s\n",
                    (long long)i, res->getErrorMessage().c_str());
                continue;
            }
            ++ok;

            // Técnicas: zip alineado ids<->names, y MAPS_TO desde la regla.
            bool mismatch = false;
            auto techs = zip_techniques(mids[i], mtech[i], mismatch);
            if (mismatch) { ++mism; continue; }
            for (const auto& t : techs) {
                std::ostringstream tq;
                tq << "MERGE (m:MitreTechnique {technique_id:'" << cy(t.id) << "'})"
                   << " ON CREATE SET m.name='" << cy(t.name) << "' "
                   << "WITH m MATCH (r:Rule {rule_id:'" << cy(rule_id[i]) << "'}) "
                   << "MERGE (r)-[:MAPS_TO]->(m);";
                auto tr = conn->query(tq.str());
                if (!tr->isSuccess())
                    std::fprintf(stderr, "[fila %lld tecnica %s] fallo: %s\n",
                        (long long)i, t.id.c_str(), tr->getErrorMessage().c_str());
            }
        }

        std::fprintf(stderr, "[host-loader] cargadas=%lld mitre_mismatch=%lld\n",
            (long long)ok, (long long)mism);
        std::printf("OK host graph: %lld filas -> %s\n", (long long)ok, db_path.c_str());
        return 0;

    } catch (const std::exception& ex) {
        std::fprintf(stderr, "[host-loader] EXCEPCION: %s\n", ex.what());
        return 3;
    }
}