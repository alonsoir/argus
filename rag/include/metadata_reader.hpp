// /vagrant/rag/include/metadata_reader.hpp
#pragma once

#include <string>
#include <optional>
#include <vector>
#include <sqlite3.h>
#include <memory>
#include <stdexcept>

namespace ml_defender {

    class MetadataReader {
    public:
        struct EventMetadata {
            size_t faiss_idx;
            std::string event_id;
            std::string classification;
            float discrepancy_score;
            uint64_t timestamp;
            uint64_t created_at;
        };

        explicit MetadataReader(const std::string& db_path);
        ~MetadataReader();

        // Get metadata by FAISS index
        EventMetadata get_by_faiss_idx(size_t idx);

        // Get FAISS index by event_id
        std::optional<size_t> get_faiss_idx_by_event_id(const std::string& event_id);

        // Count total events
        size_t count() const;

        // Get all events with specific classification
        std::vector<EventMetadata> get_by_classification(const std::string& classification);

        // ========== NUEVOS MÉTODOS (Day 41B) ==========

        // Get N most recent events
        std::vector<EventMetadata> get_recent(size_t limit = 20);

        // Get events in time range
        std::vector<EventMetadata> get_by_time_range(
            uint64_t start_timestamp,
            uint64_t end_timestamp
        );

        // Get events with discrepancy >= threshold
        std::vector<EventMetadata> get_by_discrepancy_min(float threshold);

        // Combined filters
        std::vector<EventMetadata> search(
            const std::string& classification = "",  // empty = all
            float discrepancy_min = 0.0,
            float discrepancy_max = 1.0,
            size_t limit = 100
        );

    private:
        sqlite3* db_;
        std::string db_path_;

        void open_database();
        void prepare_statements();

        // Prepared statements for performance
        sqlite3_stmt* stmt_get_by_faiss_idx_;
        sqlite3_stmt* stmt_get_faiss_idx_by_event_id_;
        sqlite3_stmt* stmt_count_;
    };

} // namespace ml_defender