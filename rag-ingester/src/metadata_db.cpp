#include "metadata_db.hpp"
#include <iostream>
#include <cstring>

namespace rag {

MetadataDB::MetadataDB(const std::string& db_path)
    : db_(nullptr)
{
    int rc = sqlite3_open(db_path.c_str(), &db_);

    if (rc != SQLITE_OK) {
        std::string error = "Cannot open metadata database: ";
        error += db_path;
        error += " (";
        error += sqlite3_errmsg(db_);
        error += ")";

        if (db_) {
            sqlite3_close(db_);
            db_ = nullptr;
        }

        throw std::runtime_error(error);
    }

    std::cout << "📊 MetadataDB opened: " << db_path << std::endl;

    create_schema();

    // WAL mode for better concurrent read access (rag-local reads while rag-ingester writes)
    exec_sql("PRAGMA journal_mode=WAL");

    // Foreign keys
    exec_sql("PRAGMA foreign_keys=ON");
}

MetadataDB::~MetadataDB() {
    if (db_) {
        sqlite3_exec(db_, "PRAGMA wal_checkpoint(TRUNCATE)", nullptr, nullptr, nullptr);
        sqlite3_close(db_);
        db_ = nullptr;
    }
}

void MetadataDB::create_schema() {
    // Day 72: Complete schema from birth.
    // All columns present from the first CREATE TABLE — no ALTER TABLE migrations needed.
    // Existing DBs created before Day 72 already have these columns via historical
    // ALTER TABLE statements. New DBs get them from birth.
    //
    // Column notes:
    //   faiss_idx          — position in FAISS attack index (0-based, PRIMARY KEY)
    //   event_id           — unique event identifier from ml-detector CSV
    //   classification     — final_class from ml-detector (canonicalized in rag-ingester)
    //   discrepancy_score  — ADR-002 provenance discrepancy (0.0-1.0)
    //   timestamp          — alias of timestamp_ms (legacy compatibility)
    //   trace_id           — SHA256 prefix derived in rag-ingester (Day 72)
    //                        sha256_prefix_16b(src_ip|dst_ip|canonical_attack_type|bucket)
    //                        NULL if source_ip/dest_ip were unavailable at ingestion time
    //   source_ip          — network source IP
    //                        "0.0.0.0" if field was empty in CSV (see trace_id_generator.hpp)
    //   dest_ip            — network destination IP
    //                        "0.0.0.0" if field was empty in CSV
    //   timestamp_ms       — event timestamp in milliseconds (from ns/1e6)
    //   pb_artifact_path   — path to .pb.enc artifact (populated Day 7z+)
    //   firewall_action    — correlated firewall decision (BLOCK/ALLOW), NULL until correlated
    //   firewall_timestamp — when firewall acted (ms), NULL until correlated
    //   firewall_score     — firewall confidence score, NULL until correlated
    //   created_at         — ingestion timestamp (Unix seconds, auto)

    const char* schema = R"(
        CREATE TABLE IF NOT EXISTS events (
            faiss_idx          INTEGER PRIMARY KEY,
            event_id           TEXT    NOT NULL UNIQUE,
            classification     TEXT    NOT NULL,
            discrepancy_score  REAL    NOT NULL,
            timestamp          INTEGER NOT NULL,
            trace_id           TEXT,
            source_ip          TEXT,
            dest_ip            TEXT,
            timestamp_ms       INTEGER,
            pb_artifact_path   TEXT,
            firewall_action    TEXT,
            firewall_timestamp INTEGER,
            firewall_score     REAL,
            created_at         INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
        );

        CREATE INDEX IF NOT EXISTS idx_event_id
            ON events(event_id);

        CREATE INDEX IF NOT EXISTS idx_classification
            ON events(classification);

        CREATE INDEX IF NOT EXISTS idx_discrepancy
            ON events(discrepancy_score DESC);

        CREATE INDEX IF NOT EXISTS idx_timestamp
            ON events(timestamp DESC);

        CREATE INDEX IF NOT EXISTS idx_trace_id
            ON events(trace_id);

        CREATE INDEX IF NOT EXISTS idx_src_ip_ts
            ON events(source_ip, timestamp_ms);
    )";

    exec_sql(schema);

    std::cout << "✅ Metadata schema ready (Day 72 — complete schema from birth)" << std::endl;
}

void MetadataDB::insert_event(int64_t faiss_idx,
                              const std::string& event_id,
                              const std::string& classification,
                              float              discrepancy_score,
                              const std::string& trace_id,
                              const std::string& source_ip,
                              const std::string& dest_ip,
                              uint64_t           timestamp_ms,
                              const std::string& pb_artifact_path)
{
    const char* sql =
        "INSERT INTO events "
        "(faiss_idx, event_id, classification, discrepancy_score, "
        " timestamp, trace_id, source_ip, dest_ip, timestamp_ms, pb_artifact_path) "
        "VALUES (?,?,?,?,?,?,?,?,?,?);";

    sqlite3_stmt* stmt = nullptr;
    sqlite3_prepare_v2(db_, sql, -1, &stmt, nullptr);
    sqlite3_bind_int64 (stmt, 1, faiss_idx);
    sqlite3_bind_text  (stmt, 2, event_id.c_str(),          -1, SQLITE_STATIC);
    sqlite3_bind_text  (stmt, 3, classification.c_str(),     -1, SQLITE_STATIC);
    sqlite3_bind_double(stmt, 4, discrepancy_score);
    sqlite3_bind_int64 (stmt, 5, static_cast<int64_t>(timestamp_ms));
    sqlite3_bind_text  (stmt, 6, trace_id.empty()           ? nullptr : trace_id.c_str(),
                                 trace_id.empty()           ? 0       : -1, SQLITE_STATIC);
    sqlite3_bind_text  (stmt, 7, source_ip.c_str(),          -1, SQLITE_STATIC);
    sqlite3_bind_text  (stmt, 8, dest_ip.c_str(),            -1, SQLITE_STATIC);
    sqlite3_bind_int64 (stmt, 9, static_cast<int64_t>(timestamp_ms));
    sqlite3_bind_text  (stmt,10, pb_artifact_path.empty()   ? nullptr : pb_artifact_path.c_str(),
                                 pb_artifact_path.empty()   ? 0       : -1, SQLITE_STATIC);
    sqlite3_step(stmt);
    sqlite3_finalize(stmt);
}

void MetadataDB::update_firewall_by_trace_id(const std::string& trace_id,
                                              const std::string& action,
                                              uint64_t           fw_ts,
                                              float              fw_score)
{
    const char* sql =
        "UPDATE events SET firewall_action=?, firewall_timestamp=?, firewall_score=? "
        "WHERE trace_id=?;";

    sqlite3_stmt* stmt = nullptr;
    sqlite3_prepare_v2(db_, sql, -1, &stmt, nullptr);
    sqlite3_bind_text  (stmt, 1, action.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_int64 (stmt, 2, static_cast<int64_t>(fw_ts));
    sqlite3_bind_double(stmt, 3, fw_score);
    sqlite3_bind_text  (stmt, 4, trace_id.c_str(), -1, SQLITE_STATIC);
    sqlite3_step(stmt);
    sqlite3_finalize(stmt);
}

void MetadataDB::update_firewall_by_ip_ts(const std::string& source_ip,
                                           uint64_t           fw_ts_ms,
                                           const std::string& action,
                                           float              fw_score,
                                           uint64_t           window_ms)
{
    const char* sql =
        "UPDATE events SET firewall_action=?, firewall_timestamp=?, firewall_score=? "
        "WHERE faiss_idx = ("
        "  SELECT faiss_idx FROM events "
        "  WHERE source_ip=? "
        "    AND timestamp_ms BETWEEN ? AND ? "
        "    AND firewall_action IS NULL "
        "  ORDER BY ABS(CAST(timestamp_ms AS INTEGER) - ?) ASC "
        "  LIMIT 1"
        ");";

    int64_t ts_min = static_cast<int64_t>(fw_ts_ms) - static_cast<int64_t>(window_ms);
    int64_t ts_max = static_cast<int64_t>(fw_ts_ms) + static_cast<int64_t>(window_ms);

    sqlite3_stmt* stmt = nullptr;
    sqlite3_prepare_v2(db_, sql, -1, &stmt, nullptr);
    sqlite3_bind_text  (stmt, 1, action.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_int64 (stmt, 2, static_cast<int64_t>(fw_ts_ms));
    sqlite3_bind_double(stmt, 3, fw_score);
    sqlite3_bind_text  (stmt, 4, source_ip.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_int64 (stmt, 5, ts_min);
    sqlite3_bind_int64 (stmt, 6, ts_max);
    sqlite3_bind_int64 (stmt, 7, static_cast<int64_t>(fw_ts_ms));
    sqlite3_step(stmt);
    sqlite3_finalize(stmt);
}

size_t MetadataDB::count() const {
    const char* sql = "SELECT COUNT(*) FROM events";

    sqlite3_stmt* stmt = nullptr;
    sqlite3_prepare_v2(db_, sql, -1, &stmt, nullptr);

    size_t count = 0;
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        count = sqlite3_column_int64(stmt, 0);
    }

    sqlite3_finalize(stmt);
    return count;
}

bool MetadataDB::exists(const std::string& event_id) const {
    const char* sql = "SELECT 1 FROM events WHERE event_id=? LIMIT 1";

    sqlite3_stmt* stmt = nullptr;
    sqlite3_prepare_v2(db_, sql, -1, &stmt, nullptr);
    sqlite3_bind_text(stmt, 1, event_id.c_str(), -1, SQLITE_STATIC);

    bool found = (sqlite3_step(stmt) == SQLITE_ROW);

    sqlite3_finalize(stmt);
    return found;
}

void MetadataDB::flush() {
    exec_sql("PRAGMA wal_checkpoint(PASSIVE)");
}

void MetadataDB::exec_sql(const char* sql) {
    char* error_msg = nullptr;
    int rc = sqlite3_exec(db_, sql, nullptr, nullptr, &error_msg);

    if (rc != SQLITE_OK) {
        std::string error = "SQL execution failed: ";
        if (error_msg) {
            error += error_msg;
            sqlite3_free(error_msg);
        }
        throw std::runtime_error(error);
    }
}

} // namespace rag

// Compatibility shim — legacy callers (.pb watcher path) that don't pass Day 69 fields.
// Delegates to the full insert_event with empty/zero sentinel values.
void rag::MetadataDB::insert_event(
    size_t faiss_idx,
    const std::string& event_id,
    const std::string& classification,
    float discrepancy_score)
{
    insert_event(
        static_cast<int64_t>(faiss_idx),
        event_id,
        classification,
        discrepancy_score,
        "",  // trace_id         — not available on .pb path
        "",  // source_ip        — not available on .pb path
        "",  // dest_ip          — not available on .pb path
        0,   // timestamp_ms
        ""   // pb_artifact_path — Day 7z+
    );
}