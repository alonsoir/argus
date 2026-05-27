// integration_example.cpp
// RAG Ingester - Day 36 Integration Example
// Demonstrates FileWatcher + EventLoader pipeline

#include "file_watcher.hpp"
#include "event_loader.hpp"
#include <iostream>
#include <csignal>
#include <atomic>
#include <thread>
#include <chrono>

using namespace rag_ingester;

// Global flag for graceful shutdown
std::atomic<bool> g_running{true};

void signal_handler(int signal) {
    if (signal == SIGINT || signal == SIGTERM) {
        std::cout << "\n[INFO] Shutdown signal received..." << std::endl;
        g_running.store(false);
    }
}

int main(int argc, char* argv[]) {
    std::cout << "=== RAG Ingester - Day 36 Integration Demo ===" << std::endl;
    std::cout << "FileWatcher + EventLoader Pipeline\n" << std::endl;
    
    // Parse arguments
    std::string watch_dir = (argc > 1) ? argv[1] : "/vagrant/logs/rag/events/";
    std::string key_path = (argc > 2) ? argv[2] : "/vagrant/config/encryption.key";
    
    std::cout << "[CONFIG] Watch directory: " << watch_dir << std::endl;
    std::cout << "[CONFIG] Encryption key: " << key_path << std::endl;
    std::cout << "[CONFIG] Pattern: *.pb" << std::endl;
    std::cout << std::endl;
    
    // Setup signal handlers
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    
    try {
        // Initialize EventLoader (decrypt + decompress + parse)
        EventLoader loader(key_path);
        std::cout << "[INFO] EventLoader initialized" << std::endl;
        
        // Initialize FileWatcher (inotify-based monitoring)
        FileWatcher watcher(watch_dir, "*.pb");
        std::cout << "[INFO] FileWatcher initialized" << std::endl;
        std::cout << std::endl;
        
        // Define callback: when .pb file detected, load and process it
        auto on_file_detected = [&loader](const std::string& filepath) {
            std::cout << "[EVENT] New file detected: " << filepath << std::endl;
            
            try {
                // Load event (decrypt → decompress → parse)
                auto event = loader.load(filepath);
                
                // Display event information
                std::cout << "  ├─ Event ID: " << event.event_id << std::endl;
                std::cout << "  ├─ Class: " << event.final_class 
                          << " (confidence: " << event.confidence << ")" << std::endl;
                std::cout << "  ├─ Features: " << event.features.size() 
                          << " dimensions";
                
                if (event.is_partial) {
                    std::cout << " [PARTIAL - FlowManager bug]";
                }
                std::cout << std::endl;
                
                std::cout << "  ├─ Source: " << event.source_detector << std::endl;
                std::cout << "  └─ Timestamp: " << event.timestamp_ns << " ns" << std::endl;
                std::cout << std::endl;
                
                // TODO Day 37-38: Generate embeddings and index in FAISS
                // ChronosEmbedder embedder;
                // auto embedding = embedder.generate(event);
                // multi_index_manager.add(embedding, event);
                
            } catch (const std::exception& e) {
                std::cerr << "[ERROR] Failed to process event: " 
                          << e.what() << std::endl;
            }
        };
        
        // Start watching
        watcher.start(on_file_detected);
        std::cout << "[INFO] ✓ Pipeline active - watching for .pb files..." << std::endl;
        std::cout << "[INFO] Press Ctrl+C to stop" << std::endl;
        std::cout << std::string(60, '=') << std::endl;
        std::cout << std::endl;
        
        // Main loop - wait for shutdown signal
        while (g_running.load()) {
            std::this_thread::sleep_for(std::chrono::seconds(1));
            
            // Optionally print stats every 60 seconds
            static int seconds = 0;
            if (++seconds % 60 == 0) {
                auto stats = loader.get_stats();
                std::cout << "[STATS] Events loaded: " << stats.total_loaded 
                          << " | Failed: " << stats.total_failed
                          << " | Bytes: " << stats.bytes_processed
                          << " | Partial: " << stats.partial_feature_count
                          << std::endl;
            }
        }
        
        // Graceful shutdown
        std::cout << "\n[INFO] Stopping pipeline..." << std::endl;
        watcher.stop();
        
        // Final stats
        auto final_stats = loader.get_stats();
        std::cout << "\n=== Final Statistics ===" << std::endl;
        std::cout << "Events loaded: " << final_stats.total_loaded << std::endl;
        std::cout << "Events failed: " << final_stats.total_failed << std::endl;
        std::cout << "Bytes processed: " << final_stats.bytes_processed << std::endl;
        std::cout << "Partial events: " << final_stats.partial_feature_count << std::endl;
        std::cout << "Files detected: " << watcher.get_files_detected() << std::endl;
        
        std::cout << "\n[INFO] Shutdown complete" << std::endl;
        return 0;
        
    } catch (const std::exception& e) {
        std::cerr << "[FATAL] " << e.what() << std::endl;
        return 1;
    }
}
