#pragma once

#include <sqlite3.h>
#include <string>
#include <stdexcept>
#include <ctime>
#include <optional>

namespace rag {

    /**
     * MetadataDB - Producer side (rag-ingester)
     *
     * Responsibilities:
     * - Create/manage metadata database schema
     * - Insert event metadata as events are indexed
     * - Map FAISS index → event metadata
     *
     * Usage:
     *   MetadataDB db("/vagrant/shared/indices/metadata.db");
     *   db.insert_event(faiss_idx, event_id, classification, discrepancy);
     */
    class MetadataDB {
    public:
        /**
         * Constructor - opens/creates database
         * @param db_path Path to SQLite database file
         * @throws std::runtime_error if database cannot be opened
         */
        explicit MetadataDB(const std::string& db_path);

        /**
         * Destructor - closes database connection
         */
        ~MetadataDB();

        // Disable copy (SQLite connection cannot be copied)
        MetadataDB(const MetadataDB&) = delete;
        MetadataDB& operator=(const MetadataDB&) = delete;

        /**
         * Insert event metadata
         * @param faiss_idx FAISS index (0-based, matches vector position)
         * @param event_id Event identifier (e.g. "synthetic_000059")
         * @param classification Event classification ("DDoS", "BENIGN", etc.)
         * @param discrepancy_score Provenance discrepancy score (0.0-1.0)
         * @throws std::runtime_error if insert fails
         */
        void insert_event(
            size_t faiss_idx,
            const std::string& event_id,
            const std::string& classification,
            float discrepancy_score
        );

        /**
         * Get total number of events in database
         * @return Event count
         */
        size_t count() const;

        /**
         * Check if event_id already exists in database (idempotency guard)
         * Day 72: prevents FAISS/MetadataDB desync on multi-file replay
         * @param event_id Event identifier to check
         * @return true if event already indexed
         */
        bool exists(const std::string& event_id) const;

        /**
         * Flush any pending writes to disk
         */
        void flush();

        // Day 69 additions to MetadataDB class
        //
        // ADD to metadata_db.hpp (public interface):

        // Extended insert with new Day 69 fields
        void insert_event(int64_t     faiss_idx,
                          const std::string& event_id,
                          const std::string& classification,
                          float              discrepancy_score,
                          const std::string& trace_id,          // "" until Day 7z
                          const std::string& source_ip,
                          const std::string& dest_ip,
                          uint64_t           timestamp_ms,
                          const std::string& pb_artifact_path); // "" until Day 7z

        // Firewall correlation — by trace_id (clean path, Day 7z)
        void update_firewall_by_trace_id(const std::string& trace_id,
                                         const std::string& action,
                                         uint64_t           firewall_timestamp_ms,
                                         float              firewall_score);

        // Firewall correlation — provisional by src_ip + timestamp window (±5000ms)
        // Used until trace_id propagation is wired
        void update_firewall_by_ip_ts(const std::string& source_ip,
                                      uint64_t           firewall_timestamp_ms,
                                      const std::string& action,
                                      float              firewall_score,
                                      uint64_t           window_ms = 5000);

    private:
        sqlite3* db_;

        /**
         * Create database schema if it doesn't exist
         */
        void create_schema();

        /**
         * Execute SQL with error handling
         */
        void exec_sql(const char* sql);
    };

} // namespace rag