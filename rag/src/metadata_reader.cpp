// /vagrant/rag/src/metadata_reader.cpp
#include "metadata_reader.hpp"
#include <iostream>
#include <sstream>

namespace ml_defender {

MetadataReader::MetadataReader(const std::string& db_path)
    : db_(nullptr)
    , db_path_(db_path)
    , stmt_get_by_faiss_idx_(nullptr)
    , stmt_get_faiss_idx_by_event_id_(nullptr)
    , stmt_count_(nullptr)
{
    open_database();
    prepare_statements();
}

MetadataReader::~MetadataReader() {
    if (stmt_get_by_faiss_idx_) sqlite3_finalize(stmt_get_by_faiss_idx_);
    if (stmt_get_faiss_idx_by_event_id_) sqlite3_finalize(stmt_get_faiss_idx_by_event_id_);
    if (stmt_count_) sqlite3_finalize(stmt_count_);

    if (db_) {
        sqlite3_close(db_);
    }
}

void MetadataReader::open_database() {
    int rc = sqlite3_open_v2(
        db_path_.c_str(),
        &db_,
        SQLITE_OPEN_READONLY,  // Read-only mode (Consumer)
        nullptr
    );

    if (rc != SQLITE_OK) {
        std::ostringstream oss;
        oss << "Failed to open database: " << db_path_
            << " - " << sqlite3_errmsg(db_);
        throw std::runtime_error(oss.str());
    }

    // Set WAL mode for better concurrent reads
    char* err_msg = nullptr;
    rc = sqlite3_exec(db_, "PRAGMA journal_mode=WAL;", nullptr, nullptr, &err_msg);
    if (rc != SQLITE_OK) {
        std::string error = err_msg;
        sqlite3_free(err_msg);
        throw std::runtime_error("Failed to set WAL mode: " + error);
    }
}

void MetadataReader::prepare_statements() {
    // Prepare: get_by_faiss_idx
    const char* sql1 = "SELECT faiss_idx, event_id, classification, discrepancy_score, "
                       "timestamp, created_at FROM events WHERE faiss_idx = ?;";

    int rc = sqlite3_prepare_v2(db_, sql1, -1, &stmt_get_by_faiss_idx_, nullptr);
    if (rc != SQLITE_OK) {
        throw std::runtime_error("Failed to prepare get_by_faiss_idx statement");
    }

    // Prepare: get_faiss_idx_by_event_id
    const char* sql2 = "SELECT faiss_idx FROM events WHERE event_id = ?;";

    rc = sqlite3_prepare_v2(db_, sql2, -1, &stmt_get_faiss_idx_by_event_id_, nullptr);
    if (rc != SQLITE_OK) {
        throw std::runtime_error("Failed to prepare get_faiss_idx_by_event_id statement");
    }

    // Prepare: count
    const char* sql3 = "SELECT COUNT(*) FROM events;";

    rc = sqlite3_prepare_v2(db_, sql3, -1, &stmt_count_, nullptr);
    if (rc != SQLITE_OK) {
        throw std::runtime_error("Failed to prepare count statement");
    }
}

MetadataReader::EventMetadata MetadataReader::get_by_faiss_idx(size_t idx) {
    sqlite3_reset(stmt_get_by_faiss_idx_);
    sqlite3_bind_int64(stmt_get_by_faiss_idx_, 1, static_cast<int64_t>(idx));

    int rc = sqlite3_step(stmt_get_by_faiss_idx_);

    if (rc != SQLITE_ROW) {
        std::ostringstream oss;
        oss << "Event not found for faiss_idx: " << idx;
        throw std::runtime_error(oss.str());
    }

    EventMetadata meta;
    meta.faiss_idx = static_cast<size_t>(sqlite3_column_int64(stmt_get_by_faiss_idx_, 0));
    meta.event_id = reinterpret_cast<const char*>(sqlite3_column_text(stmt_get_by_faiss_idx_, 1));
    meta.classification = reinterpret_cast<const char*>(sqlite3_column_text(stmt_get_by_faiss_idx_, 2));
    meta.discrepancy_score = static_cast<float>(sqlite3_column_double(stmt_get_by_faiss_idx_, 3));
    meta.timestamp = static_cast<uint64_t>(sqlite3_column_int64(stmt_get_by_faiss_idx_, 4));
    meta.created_at = static_cast<uint64_t>(sqlite3_column_int64(stmt_get_by_faiss_idx_, 5));

    return meta;
}

std::optional<size_t> MetadataReader::get_faiss_idx_by_event_id(const std::string& event_id) {
    sqlite3_reset(stmt_get_faiss_idx_by_event_id_);
    sqlite3_bind_text(stmt_get_faiss_idx_by_event_id_, 1, event_id.c_str(), -1, SQLITE_STATIC);

    int rc = sqlite3_step(stmt_get_faiss_idx_by_event_id_);

    if (rc != SQLITE_ROW) {
        return std::nullopt;
    }

    return static_cast<size_t>(sqlite3_column_int64(stmt_get_faiss_idx_by_event_id_, 0));
}

size_t MetadataReader::count() const {
    // Note: const_cast needed because sqlite3 API doesn't have const statements
    sqlite3_stmt* stmt = const_cast<sqlite3_stmt*>(stmt_count_);
    sqlite3_reset(stmt);

    int rc = sqlite3_step(stmt);

    if (rc != SQLITE_ROW) {
        return 0;
    }

    return static_cast<size_t>(sqlite3_column_int64(stmt, 0));
}

std::vector<MetadataReader::EventMetadata> MetadataReader::get_by_classification(
    const std::string& classification)
{
    std::vector<EventMetadata> results;

    const char* sql = "SELECT faiss_idx, event_id, classification, discrepancy_score, "
                      "timestamp, created_at FROM events WHERE classification = ?;";

    sqlite3_stmt* stmt;
    int rc = sqlite3_prepare_v2(db_, sql, -1, &stmt, nullptr);

    if (rc != SQLITE_OK) {
        throw std::runtime_error("Failed to prepare get_by_classification statement");
    }

    sqlite3_bind_text(stmt, 1, classification.c_str(), -1, SQLITE_STATIC);

    while ((rc = sqlite3_step(stmt)) == SQLITE_ROW) {
        EventMetadata meta;
        meta.faiss_idx = static_cast<size_t>(sqlite3_column_int64(stmt, 0));
        meta.event_id = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 1));
        meta.classification = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 2));
        meta.discrepancy_score = static_cast<float>(sqlite3_column_double(stmt, 3));
        meta.timestamp = static_cast<uint64_t>(sqlite3_column_int64(stmt, 4));
        meta.created_at = static_cast<uint64_t>(sqlite3_column_int64(stmt, 5));

        results.push_back(meta);
    }

    sqlite3_finalize(stmt);

    return results;
}
// /vagrant/rag/src/metadata_reader.cpp

std::vector<MetadataReader::EventMetadata> MetadataReader::get_recent(size_t limit) {
    std::vector<EventMetadata> results;

    std::string sql = "SELECT faiss_idx, event_id, classification, discrepancy_score, "
                      "timestamp, created_at FROM events "
                      "ORDER BY timestamp DESC LIMIT ?;";

    sqlite3_stmt* stmt;
    int rc = sqlite3_prepare_v2(db_, sql.c_str(), -1, &stmt, nullptr);

    if (rc != SQLITE_OK) {
        throw std::runtime_error("Failed to prepare get_recent statement");
    }

    sqlite3_bind_int64(stmt, 1, static_cast<int64_t>(limit));

    while ((rc = sqlite3_step(stmt)) == SQLITE_ROW) {
        EventMetadata meta;
        meta.faiss_idx = static_cast<size_t>(sqlite3_column_int64(stmt, 0));
        meta.event_id = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 1));
        meta.classification = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 2));
        meta.discrepancy_score = static_cast<float>(sqlite3_column_double(stmt, 3));
        meta.timestamp = static_cast<uint64_t>(sqlite3_column_int64(stmt, 4));
        meta.created_at = static_cast<uint64_t>(sqlite3_column_int64(stmt, 5));

        results.push_back(meta);
    }

    sqlite3_finalize(stmt);
    return results;
}

std::vector<MetadataReader::EventMetadata> MetadataReader::get_by_time_range(
    uint64_t start_timestamp,
    uint64_t end_timestamp)
{
    std::vector<EventMetadata> results;

    std::string sql = "SELECT faiss_idx, event_id, classification, discrepancy_score, "
                      "timestamp, created_at FROM events "
                      "WHERE timestamp >= ? AND timestamp <= ? "
                      "ORDER BY timestamp DESC;";

    sqlite3_stmt* stmt;
    int rc = sqlite3_prepare_v2(db_, sql.c_str(), -1, &stmt, nullptr);

    if (rc != SQLITE_OK) {
        throw std::runtime_error("Failed to prepare get_by_time_range statement");
    }

    sqlite3_bind_int64(stmt, 1, static_cast<int64_t>(start_timestamp));
    sqlite3_bind_int64(stmt, 2, static_cast<int64_t>(end_timestamp));

    while ((rc = sqlite3_step(stmt)) == SQLITE_ROW) {
        EventMetadata meta;
        meta.faiss_idx = static_cast<size_t>(sqlite3_column_int64(stmt, 0));
        meta.event_id = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 1));
        meta.classification = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 2));
        meta.discrepancy_score = static_cast<float>(sqlite3_column_double(stmt, 3));
        meta.timestamp = static_cast<uint64_t>(sqlite3_column_int64(stmt, 4));
        meta.created_at = static_cast<uint64_t>(sqlite3_column_int64(stmt, 5));

        results.push_back(meta);
    }

    sqlite3_finalize(stmt);
    return results;
}

std::vector<MetadataReader::EventMetadata> MetadataReader::search(
    const std::string& classification,
    float discrepancy_min,
    float discrepancy_max,
    size_t limit)
{
    std::vector<EventMetadata> results;

    std::string sql = "SELECT faiss_idx, event_id, classification, discrepancy_score, "
                      "timestamp, created_at FROM events WHERE 1=1 ";

    if (!classification.empty()) {
        sql += "AND classification = ? ";
    }

    sql += "AND discrepancy_score >= ? AND discrepancy_score <= ? "
           "ORDER BY timestamp DESC LIMIT ?;";

    sqlite3_stmt* stmt;
    int rc = sqlite3_prepare_v2(db_, sql.c_str(), -1, &stmt, nullptr);

    if (rc != SQLITE_OK) {
        throw std::runtime_error("Failed to prepare search statement");
    }

    int bind_idx = 1;

    if (!classification.empty()) {
        sqlite3_bind_text(stmt, bind_idx++, classification.c_str(), -1, SQLITE_STATIC);
    }

    sqlite3_bind_double(stmt, bind_idx++, discrepancy_min);
    sqlite3_bind_double(stmt, bind_idx++, discrepancy_max);
    sqlite3_bind_int64(stmt, bind_idx++, static_cast<int64_t>(limit));

    while ((rc = sqlite3_step(stmt)) == SQLITE_ROW) {
        EventMetadata meta;
        meta.faiss_idx = static_cast<size_t>(sqlite3_column_int64(stmt, 0));
        meta.event_id = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 1));
        meta.classification = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 2));
        meta.discrepancy_score = static_cast<float>(sqlite3_column_double(stmt, 3));
        meta.timestamp = static_cast<uint64_t>(sqlite3_column_int64(stmt, 4));
        meta.created_at = static_cast<uint64_t>(sqlite3_column_int64(stmt, 5));

        results.push_back(meta);
    }

    sqlite3_finalize(stmt);
    return results;
}

} // namespace ml_defender