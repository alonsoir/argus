// main.cpp
// RAG Ingester - Main Entry Point
// Day 40: Producer complete - metadata_db + FAISS persistence
// Day 68: CSV streaming path (CsvFileWatcher + CsvEventLoader)
// Day 69: Dual CSV sources — ml-detector (dir rotation) + firewall (single file)
// Day 70: replay_on_start=true en CsvDirWatcher — procesa CSVs existentes al arrancar
//         Checkpoint periódico SAVE_INTERVAL añadido al CSV ml-detector callback
// Day 72: Idempotency guard — exists() check before embed+index
//         trace_id generation — deterministic, O(1), zero-coordination
//         Prevents FAISS/MetadataDB desync on multi-file replay

#include <iostream>
#include <csignal>
#include <atomic>
#include <thread>
#include <chrono>
#include <filesystem>
#include <vector>
#include <spdlog/spdlog.h>
#include "metadata_db.hpp"
#include <faiss/index_io.h>
#include <faiss/IndexFlat.h>

#include "common/config_parser.hpp"
#include "file_watcher.hpp"
#include "event_loader.hpp"
#include "csv_event_loader.hpp"
#include "csv_file_watcher.hpp"
#include "csv_dir_watcher.hpp"
#include "firewall_csv_event_loader.hpp"
#include "embedders/simple_embedder.hpp"
#include "indexers/multi_index_manager.hpp"
#include "utils/trace_id_generator.hpp"   // Day 72

// Day 38: etcd-client integration (PRODUCTION CODE)
#include <etcd_client/etcd_client.hpp>
// DAY 109 PHASE 2b: plugin-loader
#include <plugin_loader/plugin_loader.hpp>
#include <plugin_loader/plugin_api.h>
#include <crypto_transport/utils.hpp>
#include <exception>

namespace {
    std::atomic<bool> running{true};

    // Global for save_indices_to_disk()
    rag_ingester::MultiIndexManager* g_index_manager = nullptr;
    rag::MetadataDB* g_metadata_db = nullptr;

    // Day 72: Global trace_id policy (v1 — window config per attack type)
    // Increment policy.version if window values change in production,
    // to preserve reproducibility of historical trace_ids.
    const rag_ingester::TraceIdPolicy g_trace_policy;

    void signal_handler(int signal) {
        if (signal == SIGINT || signal == SIGTERM) {
            spdlog::info("Received signal {}, shutting down gracefully...", signal);
            running = false;
        }
    }
}

// ============================================================================
// FUNCTION: Save indices to disk
// ============================================================================
void save_indices_to_disk() {
    if (!g_index_manager) {
        spdlog::warn("Cannot save indices: index_manager not initialized");
        return;
    }

    std::string base_path = "/vagrant/shared/indices/";

    spdlog::info("💾 Saving FAISS indices to disk...");

    try {
        // Create directory if it doesn't exist
        std::filesystem::create_directories(base_path);

        // Get raw FAISS indices from MultiIndexManager
        auto& chronos_index = g_index_manager->get_chronos_index();
        auto& sbert_index = g_index_manager->get_sbert_index();
        auto& attack_index = g_index_manager->get_entity_malicious_index();

        // Write indices to disk
        faiss::write_index(&chronos_index, (base_path + "chronos.faiss").c_str());
        faiss::write_index(&sbert_index, (base_path + "sbert.faiss").c_str());
        faiss::write_index(&attack_index, (base_path + "attack.faiss").c_str());

        // Flush metadata
        if (g_metadata_db) {
            g_metadata_db->flush();
        }

        spdlog::info("✅ FAISS indices saved:");
        spdlog::info("   Chronos: {} vectors", chronos_index.ntotal);
        spdlog::info("   SBERT:   {} vectors", sbert_index.ntotal);
        spdlog::info("   Attack:  {} vectors", attack_index.ntotal);

    } catch (const std::exception& e) {
        spdlog::error("❌ Failed to save indices: {}", e.what());
    }
}

int main(int argc, char* argv[]) {
    // SET_TERMINATE — DAY 100 (ADR-022: fail-closed, unhandled exceptions)
    std::set_terminate([]() {
        std::cerr << "[FATAL] std::terminate() called — unhandled exception or contract violation\n";
        std::abort();
    });
    try {
        // ====================================================================
        // 1. Parse Configuration
        // ====================================================================
        std::string config_path = argc > 1 ? argv[1] : "config/rag-ingester.json";

        spdlog::info("RAG Ingester starting...");
        spdlog::info("Loading configuration from: {}", config_path);

        auto config = rag_ingester::ConfigParser::load(config_path);

        spdlog::info("Configuration loaded:");
        spdlog::info("  Service ID: {}", config.service.id);
        spdlog::info("  Location: {}", config.service.location);
        spdlog::info("  Threading mode: {}", config.ingester.threading.mode);
        spdlog::info("  Input directory: {}", config.ingester.input.directory);
        spdlog::info("  File pattern: {}", config.ingester.input.pattern);
        spdlog::info("  Encrypted: {}", config.ingester.input.encrypted);
        spdlog::info("  Compressed: {}", config.ingester.input.compressed);

        // ====================================================================
        // 1.1 Initialize metadata_db
        // ====================================================================
        std::unique_ptr<rag::MetadataDB> metadata_db;

        // ====================================================================
        // 2. ADR-013 PHASE 2 — DAY 98: CryptoTransport via SeedClient
        // DEPRECATED DAY 98 — bloque etcd→CryptoManager eliminado
        // EventLoader inicializa CryptoTransport internamente desde seed.bin
        // ====================================================================

        // ====================================================================
        // 3. Initialize EventLoader (ADR-013 PHASE 2)
        // ====================================================================
        spdlog::info("Initializing EventLoader...");
        rag_ingester::EventLoader loader;

        // ====================================================================
        // 3.5. Initialize SimpleEmbedder and MultiIndexManager (Day 38.5)
        // ====================================================================
        spdlog::info("Initializing SimpleEmbedder...");
        rag_ingester::SimpleEmbedder embedder;

        spdlog::info("Initializing MultiIndexManager...");
        rag_ingester::MultiIndexManager index_manager;

        // ====================================================================
        // 3.7. Initialize PluginLoader (DAY 109 PHASE 2b — ADR-023)
        // ====================================================================
        spdlog::info("Initializing PluginLoader (PHASE 2b)...");
        ml_defender::PluginLoader plugin_loader(config_path);
        plugin_loader.load_plugins();
        spdlog::info("PluginLoader: {} plugin(s) loaded", plugin_loader.loaded_count());

        // index_manager vive en main() durante todo el proceso; el puntero global
        // nunca cuelga. NO refactorizar esta init a una funcion que retorne.
        // cppcheck-suppress danglingLifetime
        g_index_manager = &index_manager;

        // ====================================================================
        // 3.6. Initialize MetadataDB (Day 40)
        // ====================================================================
        try {
            // Create shared indices directory
            std::filesystem::create_directories("/vagrant/shared/indices/");

            std::string db_path = "/vagrant/shared/indices/metadata.db";
            metadata_db = std::make_unique<rag::MetadataDB>(db_path);
            g_metadata_db = metadata_db.get();

            spdlog::info("✅ Metadata DB initialized: {}", db_path);
            spdlog::info("   Existing events: {}", metadata_db->count());

        } catch (const std::exception& e) {
            spdlog::error("❌ Failed to init metadata DB: {}", e.what());
            return 1;
        }

        // ====================================================================
        // 4. Initialize FileWatcher
        // ====================================================================
        spdlog::info("Initializing FileWatcher...");
        spdlog::info("  Watching: {}", config.ingester.input.directory);
        spdlog::info("  Pattern: {}", config.ingester.input.pattern);

        rag_ingester::FileWatcher watcher(
            config.ingester.input.directory,
            config.ingester.input.pattern
        );

        // ====================================================================
        // 5. Set up signal handlers
        // ====================================================================
        std::signal(SIGINT, signal_handler);
        std::signal(SIGTERM, signal_handler);

        // ====================================================================
        // 6. Event processing callback (Day 40: + metadata_db)
        // ====================================================================
        uint64_t events_processed = 0;
        uint64_t events_failed = 0;
        uint64_t vectors_indexed = 0;

        const size_t SAVE_INTERVAL = 100;  // Save every 100 events
        size_t events_since_last_save = 0;

        auto callback = [&](const std::string& filepath) {
            spdlog::info("New file detected: {}", filepath);

            try {
                // Load event
                auto event = loader.load(filepath);
                events_processed++;

                spdlog::info("Event loaded: id={}, features={}, class={}, confidence={:.4f}",
                    event.event_id,
                    event.features.size(),
                    event.final_class,
                    event.confidence
                );

                // DAY 109 PHASE 2b: plugin_process_message READ-ONLY
                // Contrato: payload=nullptr, mode=PLUGIN_MODE_READONLY
                // Early return si result_code != 0 (ADR-023)
                {
                    MessageContext ctx_readonly{};
                    ctx_readonly.payload     = nullptr;
                    ctx_readonly.payload_len = 0;
                    ctx_readonly.mode        = PLUGIN_MODE_READONLY;
                    ctx_readonly.result_code = 0;
                    plugin_loader.invoke_all(ctx_readonly);
                    if (ctx_readonly.result_code != 0) {
                        spdlog::warn("Plugin anomaly (result_code={}) — skipping event {}",
                            ctx_readonly.result_code, event.event_id);
                        events_failed++;
                        return;
                    }
                }
                // Day 38.5: Generate embeddings
                auto chronos_emb = embedder.embed_chronos(event);
                auto sbert_emb = embedder.embed_sbert(event);
                auto attack_emb = embedder.embed_attack(event);

                spdlog::debug("Embeddings generated: chronos={}, sbert={}, attack={}",
                    chronos_emb.size(), sbert_emb.size(), attack_emb.size());

                // Day 38.5: Add to FAISS indices
                index_manager.add_chronos(chronos_emb);
                index_manager.add_sbert(sbert_emb);
                index_manager.add_entity_malicious(attack_emb);

                vectors_indexed++;

                // ============================================================
                // DAY 40: Insert metadata (Producer responsibility)
                // ============================================================

                size_t faiss_idx = vectors_indexed - 1;

                std::string event_id = event.event_id;
                std::string classification = event.final_class;
                float discrepancy_score = event.discrepancy_score;

                try {
                    metadata_db->insert_event(
                        faiss_idx,
                        event_id,
                        classification,
                        discrepancy_score
                    );

                    spdlog::debug("Metadata inserted: faiss_idx={}, event_id={}",
                                 faiss_idx, event_id);

                } catch (const std::exception& e) {
                    spdlog::error("Failed to insert metadata for {}: {}",
                                 event_id, e.what());
                }

                // ============================================================
                // Periodic save to disk
                // ============================================================
                events_since_last_save++;
                if (events_since_last_save >= SAVE_INTERVAL) {
                    save_indices_to_disk();
                    events_since_last_save = 0;
                }

                if (config.ingester.input.delete_after_process) {
                    std::filesystem::remove(filepath);
                    spdlog::debug("Deleted processed file: {}", filepath);
                }

            } catch (const std::exception& e) {
                events_failed++;
                spdlog::error("Failed to process {}: {}", filepath, e.what());
            }
        };

        // ====================================================================
        // 7. Start watching .pb files
        // ====================================================================
        watcher.start(callback);

        // ====================================================================
        // Day 69 — Source A: ml-detector CSV (directory, daily rotation)
        // CsvDirWatcher detects IN_CREATE (new YYYY-MM-DD.csv) + IN_MODIFY
        // Day 70: replay_on_start=true — procesa contenido existente al arrancar
        // Day 72: Idempotency guard — exists() before embed+index
        //         trace_id — O(1), deterministic, zero-coordination
        // ====================================================================
        std::shared_ptr<rag_ingester::CsvEventLoader>  ml_csv_loader;
        std::shared_ptr<rag_ingester::CsvDirWatcher>   dir_watcher;

        if (!config.ingester.input.csv_ml_detector_dir.empty()) {
            spdlog::info("Initializing CSV ml-detector path...");
            spdlog::info("  Dir: {}", config.ingester.input.csv_ml_detector_dir);

            rag_ingester::CsvEventLoaderConfig ml_cfg;
            ml_cfg.hmac_key_hex = config.ingester.input.csv_ml_detector_hmac_key_hex;
            ml_cfg.verify_hmac  = !ml_cfg.hmac_key_hex.empty();

            ml_csv_loader = std::make_shared<rag_ingester::CsvEventLoader>(ml_cfg);

            dir_watcher = std::make_shared<rag_ingester::CsvDirWatcher>(
                config.ingester.input.csv_ml_detector_dir,
                [&](const std::string& line) {
                    static std::atomic<uint64_t> lineno{0};
                    uint64_t ln = ++lineno;

                    auto result = ml_csv_loader->parse(line, ln);
                    if (result.status != rag_ingester::CsvParseStatus::OK) {
                        spdlog::warn("[csv-ml] line {} rejected: {}", ln, result.error);
                        events_failed++;
                        return;
                    }

                    auto& event = result.event;

                    // ============================================================
                    // Day 72: IDEMPOTENCY GUARD
                    // Must be checked BEFORE embed_attack() + add_entity_malicious()
                    // to prevent FAISS/MetadataDB desync on multi-file replay.
                    // vectors_indexed is an ephemeral in-memory counter — if the same
                    // event_id is replayed from multiple CSVs, FAISS would accumulate
                    // duplicate vectors while MetadataDB silently rejects the INSERT.
                    // ============================================================
                    if (metadata_db->exists(event.event_id)) {
                        spdlog::debug("[csv-ml] skip duplicate: {}", event.event_id);
                        return;
                    }

                    // Zero-pad S2 features 62→105 (ADR: Day 68)
                    if (event.features.size() < rag_ingester::SimpleEmbedder::INPUT_DIM) {
                        event.features.resize(rag_ingester::SimpleEmbedder::INPUT_DIM, 0.0f);
                    }

                    try {
                        // ============================================================
                        // Day 72: Generate trace_id BEFORE insert
                        // Deterministic: sha256_prefix_16b(src|dst|attack|bucket)
                        // O(1), stateless, zero-coordination, reproducible after restart.
                        // window_ms_used + policy_version stored for historical auditability.
                        // ============================================================
                        auto trace_meta = rag_ingester::generate_trace_id_with_metadata(
                            event.source_ip,
                            event.dest_ip,
                            event.final_class,
                            event.timestamp_ms,
                            event.event_id,     // for sentinel warn logs
                            g_trace_policy
                        );

                        spdlog::debug("[csv-ml] trace_id={} attack={} window={}ms event={}",
                                      trace_meta.trace_id,
                                      trace_meta.canonical_attack_type,
                                      trace_meta.window_ms_used,
                                      event.event_id);

                        auto attack_emb = embedder.embed_attack(event);
                        index_manager.add_entity_malicious(attack_emb);
                        vectors_indexed++;

                        metadata_db->insert_event(
                            static_cast<int64_t>(vectors_indexed - 1),
                            event.event_id,
                            event.final_class,
                            event.discrepancy_score,
                            trace_meta.trace_id,    // Day 72: populated
                            event.source_ip,
                            event.dest_ip,
                            event.timestamp_ms,
                            ""                       // pb_artifact_path — Day 7z
                        );

                        events_processed++;

                        events_since_last_save++;
                        if (events_since_last_save >= SAVE_INTERVAL) {
                            save_indices_to_disk();
                            events_since_last_save = 0;
                        }

                        spdlog::debug("[csv-ml] indexed: id={} class={} conf={:.3f} trace={} line={}",
                                      event.event_id, event.final_class, event.confidence,
                                      trace_meta.trace_id, ln);

                    } catch (const std::exception& e) {
                        events_failed++;
                        spdlog::error("[csv-ml] indexing failed (line {}): {}", ln, e.what());
                    }
                },
                config.ingester.input.replay_on_start
            );

            dir_watcher->start();
            spdlog::info("✅ CSV ml-detector dir watcher started (replay_on_start={})",
                         config.ingester.input.replay_on_start);
            spdlog::info("   trace_id policy v{} active", g_trace_policy.version);

        } else {
            spdlog::info("CSV ml-detector path disabled (csv_ml_detector_dir not set)");
        }

        // ====================================================================
        // Day 69 — Source B: firewall-acl-agent CSV (single file, append-only)
        // CsvFileWatcher (inotify IN_MODIFY + offset) + FirewallCsvEventLoader
        // Does NOT insert into FAISS — UPDATE MetadataDB WHERE src_ip + ts window
        // ====================================================================
        std::shared_ptr<ml_defender::FirewallCsvEventLoader> fw_csv_loader;
        std::unique_ptr<rag_ingester::CsvFileWatcher>        fw_watcher;

        if (!config.ingester.input.csv_firewall_path.empty()) {
            spdlog::info("Initializing CSV firewall path...");
            spdlog::info("  File: {}", config.ingester.input.csv_firewall_path);

            fw_csv_loader = std::make_shared<ml_defender::FirewallCsvEventLoader>(
                config.ingester.input.csv_firewall_hmac_key_hex
            );

            fw_watcher = std::make_unique<rag_ingester::CsvFileWatcher>(
                config.ingester.input.csv_firewall_path,
                false,
                500
            );

            fw_watcher->start([&](const std::string& line, uint64_t lineno) {
                ml_defender::FirewallEvent fw_ev;
                auto result = fw_csv_loader->parse(line, fw_ev);

                if (result == ml_defender::FirewallParseResult::EMPTY_LINE) return;

                if (result != ml_defender::FirewallParseResult::OK) {
                    spdlog::warn("[csv-fw] line {} rejected (result={})", lineno,
                                 static_cast<int>(result));
                    return;
                }

                try {
                    if (!fw_ev.trace_id.empty()) {
                        metadata_db->update_firewall_by_trace_id(
                            fw_ev.trace_id,
                            fw_ev.action,
                            fw_ev.timestamp_ms,
                            fw_ev.score
                        );
                    } else {
                        metadata_db->update_firewall_by_ip_ts(
                            fw_ev.source_ip,
                            fw_ev.timestamp_ms,
                            fw_ev.action,
                            fw_ev.score
                        );
                    }

                    spdlog::debug("[csv-fw] correlated: src={} action={} score={:.3f} line={}",
                                  fw_ev.source_ip, fw_ev.action, fw_ev.score, lineno);

                } catch (const std::exception& e) {
                    spdlog::error("[csv-fw] correlation failed (line {}): {}", lineno, e.what());
                }
            });

            spdlog::info("✅ CSV firewall watcher started");

        } else {
            spdlog::info("CSV firewall path disabled (csv_firewall_path not set)");
        }

        spdlog::info("✅ RAG Ingester ready and waiting for events");
        spdlog::info("   Indices will be saved every {} events", SAVE_INTERVAL);

        // ====================================================================
        // 8. Main loop with statistics
        // ====================================================================
        auto last_stats = std::chrono::steady_clock::now();

        while (running) {
            std::this_thread::sleep_for(std::chrono::seconds(1));

            auto now = std::chrono::steady_clock::now();
            auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - last_stats);

            if (elapsed.count() >= 60) {
                auto stats = loader.get_stats();

                spdlog::info("=== Statistics (last 60s) ===");
                spdlog::info("  Events processed: {}", events_processed);
                spdlog::info("  Events failed: {}", events_failed);
                spdlog::info("  Vectors indexed: {}", vectors_indexed);
                spdlog::info("  Metadata entries: {}", metadata_db->count());
                spdlog::info("  Total loaded: {}", stats.total_loaded);
                spdlog::info("  Total failed: {}", stats.total_failed);
                spdlog::info("  Bytes processed: {}", stats.bytes_processed);
                spdlog::info("  Partial features: {}", stats.partial_feature_count);

                if (dir_watcher && ml_csv_loader) {
                    auto cs = ml_csv_loader->get_stats();
                    spdlog::info("  [csv-ml] lines={} rotations={} parsed_ok={} hmac_fail={} parse_err={}",
                                 dir_watcher->lines_detected(),
                                 dir_watcher->files_rotated(),
                                 cs.parsed_ok, cs.hmac_failures, cs.parse_errors);
                }

                if (fw_watcher && fw_csv_loader) {
                    spdlog::info("  [csv-fw] lines={} parsed_ok={} hmac_fail={} parse_err={}",
                                 fw_watcher->lines_detected(),
                                 fw_csv_loader->parsed_ok(),
                                 fw_csv_loader->hmac_failures(),
                                 fw_csv_loader->parse_errors());
                }

                last_stats = now;
            }
        }

        // ====================================================================
        // 9. Graceful shutdown
        // ====================================================================
        spdlog::info("Shutting down...");
        watcher.stop();

        if (dir_watcher)  { dir_watcher->stop();  spdlog::info("CSV ml-detector watcher stopped"); }
        if (fw_watcher)   { fw_watcher->stop();   spdlog::info("CSV firewall watcher stopped"); }

        spdlog::info("🔒 Saving final state to disk...");
        save_indices_to_disk();

        auto final_stats = loader.get_stats();
        spdlog::info("=== Final Statistics ===");
        spdlog::info("  Total events: {}", events_processed);
        spdlog::info("  Failed events: {}", events_failed);
        spdlog::info("  Vectors indexed: {}", vectors_indexed);
        spdlog::info("  Metadata entries: {}", metadata_db->count());
        spdlog::info("  Bytes processed: {}", final_stats.bytes_processed);

        spdlog::info("RAG Ingester stopped gracefully");
        return 0;

    } catch (const std::exception& e) {
        spdlog::error("Fatal error: {}", e.what());
        return 1;
    }
}