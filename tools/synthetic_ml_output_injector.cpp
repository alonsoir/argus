// tools/synthetic_ml_output_injector.cpp
// Synthetic ML Detector → Firewall ACL Agent Event Generator
// Generates NetworkSecurityEvent with ML analysis for firewall stress testing
// AUTHORS: Alonso Isidoro Roman + Claude (Anthropic)
// DATE: 2 February 2026 - Day 49 | Migrated DAY 159: ADR-013 PHASE 2 CryptoTransport

#include <zmq.hpp>
#include <iostream>
#include <chrono>
#include <thread>
#include <random>
#include <iomanip>
#include <memory>

// Protobuf
#include "network_security.pb.h"

// Crypto-transport (ADR-013 PHASE 2 — DAY 159)
#include <seed_client/seed_client.hpp>
#include <crypto_transport/transport.hpp>
#include <crypto_transport/contexts.hpp>
#include <lz4.h>
#include <cstring>

// etcd-client
#include <etcd_client/etcd_client.hpp>
// JSON config
#include <nlohmann/json.hpp>
#include <fstream>

class SyntheticMLOutputInjector {
private:
    zmq::context_t zmq_ctx_;
    zmq::socket_t publisher_;
    std::unique_ptr<etcd_client::EtcdClient> etcd_client_;
    std::unique_ptr<ml_defender::SeedClient> seed_client_;
    std::string zmq_bind_address_{"tcp://*:5572"};  // default, overridden by JSON

    void load_zmq_config(const std::string& config_path) {
        try {
            std::ifstream f(config_path);
            if (!f.is_open()) {
                std::cerr << "⚠️  [config] Cannot open " << config_path << " — using defaults\n";
                return;
            }
            auto j = nlohmann::json::parse(f);
            auto& sock = j["network"]["output_socket"];
            std::string endpoint = sock["endpoint"].get<std::string>();
            // Normalize: replace 0.0.0.0 with * for bind
            std::string bind_ep = endpoint;
            auto pos = bind_ep.find("0.0.0.0");
            if (pos != std::string::npos) bind_ep.replace(pos, 7, "*");
            zmq_bind_address_ = bind_ep;
            std::cout << "📋 [config] ZMQ endpoint from JSON: bind " << zmq_bind_address_ << "\n";
        } catch (const std::exception& e) {
            std::cerr << "⚠️  [config] JSON parse error: " << e.what() << " — using defaults\n";
        }
    }
    std::unique_ptr<crypto_transport::CryptoTransport> tx_;
    std::mt19937 rng_;

    // Random generators
    float rand_float(float min, float max) {
        std::uniform_real_distribution<float> dist(min, max);
        return dist(rng_);
    }

    uint32_t rand_uint(uint32_t min, uint32_t max) {
        std::uniform_int_distribution<uint32_t> dist(min, max);
        return dist(rng_);
    }

    std::string generate_random_ip() {
        return std::to_string(rand_uint(1, 254)) + "." +
               std::to_string(rand_uint(0, 255)) + "." +
               std::to_string(rand_uint(0, 255)) + "." +
               std::to_string(rand_uint(1, 254));
    }

    // Create NetworkSecurityEvent with ML analysis (what firewall expects)
    protobuf::NetworkSecurityEvent create_synthetic_threat(uint64_t event_id) {
        protobuf::NetworkSecurityEvent event;

        // Event ID and timestamp
        event.set_event_id("threat-" + std::to_string(event_id));
        auto* timestamp = event.mutable_event_timestamp();
        auto now = std::chrono::system_clock::now();
        auto seconds = std::chrono::duration_cast<std::chrono::seconds>(now.time_since_epoch());
        timestamp->set_seconds(seconds.count());

        // Network Features (minimal - firewall only needs source_ip)
        auto* nf = event.mutable_network_features();
        nf->set_source_ip(generate_random_ip());
        nf->set_destination_ip(generate_random_ip());
        nf->set_source_port(rand_uint(1024, 65535));
        nf->set_destination_port(rand_uint(1, 1024));
        nf->set_protocol_number(rand_uint(6, 17)); // TCP or UDP

        // ML Analysis (CRITICAL - firewall checks this)
        auto* ml = event.mutable_ml_analysis();

        // Level 1 detection (MUST be true for firewall to process)
        ml->set_attack_detected_level1(true);
        ml->set_level1_confidence(rand_float(0.7, 0.99));

        // Threat category (determines ipset and timeout)
        std::vector<std::string> categories = {"DDOS", "RANSOMWARE", "SUSPICIOUS_INTERNAL"};
        std::string threat_cat = categories[rand_uint(0, categories.size() - 1)];
        event.set_threat_category(threat_cat);

        // Overall threat score
        event.set_overall_threat_score(ml->level1_confidence());
        event.set_final_classification("MALICIOUS");

        return event;
    }

public:
    public:
    SyntheticMLOutputInjector(const std::string& etcd_endpoint = "localhost:2379")
        : zmq_ctx_(1)
        , publisher_(zmq_ctx_, zmq::socket_type::pub)
        , rng_(std::random_device{}())
    {
        // Bind to firewall-acl-agent input port
        // DAY 159: leer endpoint desde ml_detector_config.json (Single Source of Truth)
        load_zmq_config("/etc/ml-defender/ml-detector/ml_detector_config.json");
        publisher_.bind(zmq_bind_address_);

        // Parse endpoint: "localhost:2379" → host="localhost", port=2379
        size_t colon_pos = etcd_endpoint.find(':');
        if (colon_pos == std::string::npos) {
            throw std::runtime_error("Invalid etcd endpoint format (expected host:port)");
        }

        std::string host = etcd_endpoint.substr(0, colon_pos);
        int port = std::stoi(etcd_endpoint.substr(colon_pos + 1));

        std::cout << "🔗 [etcd] Initializing etcd-client: " << host << ":" << port << "\n";

        // Build etcd-client Config
        etcd_client::Config etcd_config;
        etcd_config.host = host;
        etcd_config.port = port;
        etcd_config.timeout_seconds = 5;
        etcd_config.component_name = "synthetic-ml-output";
        etcd_config.encryption_enabled = true;
        etcd_config.heartbeat_enabled = true;

        // Initialize etcd-client
        etcd_client_ = std::make_unique<etcd_client::EtcdClient>(etcd_config);

        // Connect and register
        if (!etcd_client_->connect()) {
            throw std::runtime_error("Failed to connect to etcd-server");
        }

        if (!etcd_client_->register_component()) {
            throw std::runtime_error("Failed to register component");
        }

        std::cout << "✅ [etcd] Connected and registered\n";

        // ADR-013 PHASE 2 — DAY 159: CryptoTransport via SeedClient
        seed_client_ = std::make_unique<ml_defender::SeedClient>(
            "/etc/ml-defender/ml-detector/ml_detector_config.json");
        seed_client_->load();
        tx_ = std::make_unique<crypto_transport::CryptoTransport>(
            *seed_client_, ml_defender::crypto::CTX_ML_TO_FIREWALL);
        std::cout << "✅ [crypto] CryptoTransport inicializado (HKDF-SHA256 + ChaCha20-Poly1305)\n";

        // Give ZMQ time to bind
        std::this_thread::sleep_for(std::chrono::milliseconds(500));

        std::cout << "✅ Synthetic ML Output Injector initialized\n";
        std::cout << "   Port: 5572 (firewall-acl-agent input)\n";
        std::cout << "   Encryption: ChaCha20-Poly1305 + LZ4\n\n";
    }

    void inject_threats(uint64_t total_threats, uint64_t threats_per_sec) {
        const auto interval = std::chrono::nanoseconds(1'000'000'000 / threats_per_sec);

        std::cout << "🔥 Injecting " << total_threats << " threats @ "
                  << threats_per_sec << " threats/sec\n";
        std::cout << "   Interval: " << interval.count() << " ns\n\n";

        auto start_time = std::chrono::steady_clock::now();
        uint64_t sent = 0;
        uint64_t last_report = 0;

        for (uint64_t i = 0; i < total_threats; ++i) {
            auto event_start = std::chrono::steady_clock::now();

            // Create threat event
            auto event = create_synthetic_threat(i);

            // Serialize protobuf
            std::string serialized;
            if (!event.SerializeToString(&serialized)) {
                std::cerr << "❌ Failed to serialize event " << i << "\n";
                continue;
            }

            // ADR-013 PHASE 2 — DAY 159: LZ4 LE + CryptoTransport
            std::vector<uint8_t> to_encrypt;
            {
                int orig_size = static_cast<int>(serialized.size());
                int max_compressed = LZ4_compressBound(orig_size);
                std::vector<uint8_t> compressed(sizeof(uint32_t) + static_cast<size_t>(max_compressed));
                uint32_t orig_le = static_cast<uint32_t>(orig_size);
                std::memcpy(compressed.data(), &orig_le, sizeof(orig_le));
                int compressed_size = LZ4_compress_default(
                    serialized.data(),
                    reinterpret_cast<char*>(compressed.data() + sizeof(uint32_t)),
                    orig_size, max_compressed);
                if (compressed_size > 0) {
                    compressed.resize(sizeof(uint32_t) + static_cast<size_t>(compressed_size));
                    to_encrypt = std::move(compressed);
                } else {
                    to_encrypt = std::vector<uint8_t>(serialized.begin(), serialized.end());
                }
            }
            auto encrypted = tx_->encrypt(to_encrypt);

            // Send via ZMQ
            zmq::message_t msg(encrypted.data(), encrypted.size());
            publisher_.send(msg, zmq::send_flags::dontwait);

            sent++;

            // Progress report every second
            if (sent - last_report >= threats_per_sec) {
                auto elapsed = std::chrono::steady_clock::now() - start_time;
                auto elapsed_sec = std::chrono::duration<double>(elapsed).count();
                auto actual_rate = sent / elapsed_sec;

                std::cout << "\r📊 Sent: " << sent << "/" << total_threats
                          << " (" << std::fixed << std::setprecision(1)
                          << (100.0 * sent / total_threats) << "%) "
                          << "@ " << actual_rate << " threats/sec    " << std::flush;

                last_report = sent;
            }

            // Rate limiting
            auto event_end = std::chrono::steady_clock::now();
            auto elapsed = event_end - event_start;
            if (elapsed < interval) {
                std::this_thread::sleep_for(interval - elapsed);
            }
        }

        auto total_time = std::chrono::steady_clock::now() - start_time;
        auto total_sec = std::chrono::duration<double>(total_time).count();

        std::cout << "\n\n✅ Injection complete!\n";
        std::cout << "   Total threats: " << sent << "\n";
        std::cout << "   Total time: " << total_sec << " sec\n";
        std::cout << "   Actual rate: " << (sent / total_sec) << " threats/sec\n\n";
    }
};

int main(int argc, char* argv[]) {
    if (argc != 3) {
        std::cerr << "Usage: " << argv[0] << " <total_threats> <threats_per_second>\n";
        std::cerr << "Example: " << argv[0] << " 10000 1000\n";
        return 1;
    }

    uint64_t total = std::stoull(argv[1]);
    uint64_t rate = std::stoull(argv[2]);

    try {
        SyntheticMLOutputInjector injector;
        injector.inject_threats(total, rate);
    } catch (const std::exception& e) {
        std::cerr << "❌ Error: " << e.what() << "\n";
        return 1;
    }

    return 0;
}