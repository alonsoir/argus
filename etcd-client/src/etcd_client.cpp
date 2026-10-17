// etcd-client/src/etcd_client.cpp
#include "etcd_client/etcd_client.hpp"
#include <crypto_transport/contexts.hpp>
#include <nlohmann/json.hpp>
#include <iostream>
#include <mutex>
#include <condition_variable>  // [PARADA-INMEDIATA-D300]
#include <stdexcept>
#include <thread>
#include <openssl/hmac.h>
#include <openssl/evp.h>
#include <sstream>
#include <iomanip>
#include <atomic>
// ADR-013 PHASE 2 — DAY 98: CryptoTransport via SeedClient (sustituye CryptoManager)
// DEPRECATED DAY 98 — crypto_manager.hpp: #include "crypto_transport/crypto_manager.hpp"
#include <seed_client/seed_client.hpp>
#include <crypto_transport/transport.hpp>
#include <lz4.h>

using json = nlohmann::json;


// Forward declarations of helper functions (component namespace)
// Note: http namespace is now fully declared in etcd_client.hpp
namespace etcd_client {

namespace component {
    std::string build_registration_payload(const Config& config);
    std::string build_heartbeat_payload(const Config& config);
    std::string build_unregister_payload(const Config& config);
    ComponentInfo parse_component_info(const std::string& json_str);
    std::vector<ComponentInfo> parse_component_list(const std::string& json_str);
}

} // namespace etcd_client

namespace etcd_client {
// ============================================================================

struct EtcdClient::Impl {
    Config config_;
    // DEPRECATED DAY 98 — encryption_key_ sustituido por SeedClient + CryptoTransport
    // std::string encryption_key_;
    bool connected_ = false;
    mutable std::mutex mutex_;
    // ADR-013 PHASE 2 — DAY 98
    std::unique_ptr<ml_defender::SeedClient>           seed_client_;
    std::unique_ptr<crypto_transport::CryptoTransport> tx_;
    std::unique_ptr<crypto_transport::CryptoTransport> rx_;
    // Day 59: Service discovery paths from etcd-server
    ServicePaths service_paths_;
    // Heartbeat thread
    std::thread heartbeat_thread_;
    std::atomic<bool> heartbeat_running_{false};
    std::mutex hb_mtx_;               // [PARADA-INMEDIATA-D300] espera interrumpible del heartbeat
    std::condition_variable hb_cv_;   // [PARADA-INMEDIATA-D300]

    // Constructor — ADR-013 PHASE 2 (DAY 98)
    explicit Impl(const Config& config)
        : config_(config) {
        try {
            if (!config_.component_config_path.empty()) {
                seed_client_ = std::make_unique<ml_defender::SeedClient>(
                    config_.component_config_path);
                seed_client_->load();
                tx_ = std::make_unique<crypto_transport::CryptoTransport>(
                    *seed_client_, ml_defender::crypto::CTX_ETCD_TX);
                rx_ = std::make_unique<crypto_transport::CryptoTransport>(
                    *seed_client_, ml_defender::crypto::CTX_ETCD_RX);
                std::cout << "🔧 EtcdClient initialized with CryptoTransport (HKDF-SHA256): "
                          << config_.component_name << std::endl;
            } else {
                std::cerr << "⚠️  [etcd-client] component_config_path vacío — CryptoTransport no inicializado" << std::endl;
                std::cout << "🔧 EtcdClient initialized (no crypto): "
                          << config_.component_name << std::endl;
            }
        } catch (const std::exception& e) {
            std::cerr << "❌ [etcd-client] Error inicializando CryptoTransport: "
                      << e.what() << std::endl;
            throw;
        }
    }

    // Destructor
    ~Impl() {
        stop_heartbeat_thread();
    }

    // Start heartbeat thread
    void start_heartbeat_thread() {
        if (!config_.heartbeat_enabled) {
            return;
        }

        if (heartbeat_running_.exchange(true)) {
            return; // Already running
        }

        heartbeat_thread_ = std::thread([this]() {
            std::cout << "💓 Heartbeat thread started (interval: "
                      << config_.heartbeat_interval_seconds << "s)" << std::endl;

            while (heartbeat_running_) {
                {   // [PARADA-INMEDIATA-D300] espera interrumpible: la parada no espera al intervalo
                    std::unique_lock<std::mutex> lk(hb_mtx_);
                    if (hb_cv_.wait_for(lk, std::chrono::seconds(config_.heartbeat_interval_seconds),
                                        [this] { return !heartbeat_running_.load(); })) break;
                }

                if (!heartbeat_running_) break;

                try {
                    send_heartbeat();
                } catch (const std::exception& e) {
                    std::cerr << "⚠️  Heartbeat failed: " << e.what() << std::endl;
                }
            }

            std::cout << "💓 Heartbeat thread stopped" << std::endl;
        });
    }

    // Stop heartbeat thread
    void stop_heartbeat_thread() {
        if (heartbeat_running_.exchange(false)) {
            { std::lock_guard<std::mutex> lk(hb_mtx_); }  // [PARADA-INMEDIATA-D300] sin despertar perdido
            hb_cv_.notify_all();
            if (heartbeat_thread_.joinable()) {
                heartbeat_thread_.join();
            }
        }
    }

    // Send heartbeat
    bool send_heartbeat() {
        std::string payload = component::build_heartbeat_payload(config_);

        auto response = http::post(
            config_.host,
            config_.port,
            "/v1/heartbeat/" + config_.component_name,
            payload,
            config_.timeout_seconds,
            1, // Single attempt for heartbeat
            0,
            config_.component_name
        );

        return response.success;
    }

	// Day 60: Apply encryption and compression to outgoing data
std::string process_outgoing_data(const std::string& data) {

    std::string processed = data;
    size_t original_size = data.size();

    // ADR-013 PHASE 2 — DAY 98: LZ4 directo + CryptoTransport
    // Step 1: Compress con LZ4 (si habilitado y supera umbral)
    if (config_.compression_enabled &&
        original_size > static_cast<size_t>(config_.compression_min_size)) {
        try {
            int max_compressed = LZ4_compressBound(static_cast<int>(original_size));
            std::vector<uint8_t> compressed(sizeof(uint32_t) + max_compressed);
            uint32_t orig_le = static_cast<uint32_t>(original_size);
            std::memcpy(compressed.data(), &orig_le, sizeof(orig_le));
            int compressed_size = LZ4_compress_default(
                data.data(),
                reinterpret_cast<char*>(compressed.data() + sizeof(uint32_t)),
                static_cast<int>(original_size),
                max_compressed
            );
            if (compressed_size > 0) {
                compressed.resize(sizeof(uint32_t) + compressed_size);
                processed.assign(compressed.begin(), compressed.end());
                std::cout << "📦 Compressed: " << original_size << " → "
                          << processed.size() << " bytes" << std::endl;
            } else {
                std::cerr << "⚠️  LZ4 compression failed — enviando sin comprimir" << std::endl;
            }
        } catch (const std::exception& e) {
            std::cerr << "⚠️  Compression exception: " << e.what() << std::endl;
        }
    }

    // Step 2: Encrypt con CryptoTransport (si habilitado)
    if (config_.encryption_enabled && tx_) {
        try {
            std::vector<uint8_t> plain_bytes(processed.begin(), processed.end());
            auto cipher = tx_->encrypt(plain_bytes);
            std::cout << "🔒 Encrypted: " << cipher.size() << " bytes" << std::endl;
            return std::string(cipher.begin(), cipher.end());
        } catch (const std::exception& e) {
            std::cerr << "⚠️  Encryption failed: " << e.what() << std::endl;
            throw;
        }
    }

    return processed;
}
};

// ============================================================================
// EtcdClient - Public Interface Implementation
// ============================================================================

// Constructors
EtcdClient::EtcdClient(const Config& config)
    : pImpl(std::make_unique<Impl>(config)) {}

EtcdClient::EtcdClient(const std::string& config_json_path)
    : pImpl(std::make_unique<Impl>(Config::from_json_file(config_json_path))) {}

// Destructor
EtcdClient::~EtcdClient() = default;

// Move semantics
EtcdClient::EtcdClient(EtcdClient&&) noexcept = default;
EtcdClient& EtcdClient::operator=(EtcdClient&&) noexcept = default;

// Connection management
bool EtcdClient::connect() {
    std::lock_guard<std::mutex> lock(pImpl->mutex_);

    if (pImpl->connected_) {
        std::cout << "✅ Already connected" << std::endl;
        return true;
    }

    std::cout << "🔗 Connecting to etcd-server: "
              << pImpl->config_.host << ":" << pImpl->config_.port << std::endl;

    // Test connection with a simple GET request
    auto response = http::get(
        pImpl->config_.host,
        pImpl->config_.port,
        "/health",
        pImpl->config_.timeout_seconds,
        pImpl->config_.max_retry_attempts,
        pImpl->config_.retry_backoff_seconds,
        pImpl->config_.component_name
    );

    pImpl->connected_ = response.success;

    if (pImpl->connected_) {
        std::cout << "✅ Connected to etcd-server" << std::endl;
    } else {
        std::cerr << "❌ Failed to connect to etcd-server" << std::endl;
    }

    return pImpl->connected_;
}

bool EtcdClient::is_connected() const {
    std::lock_guard<std::mutex> lock(pImpl->mutex_);
    return pImpl->connected_;
}

void EtcdClient::disconnect() {
    std::lock_guard<std::mutex> lock(pImpl->mutex_);

    if (!pImpl->connected_) {
        return;
    }

    pImpl->stop_heartbeat_thread();
    pImpl->connected_ = false;

    std::cout << "🔌 Disconnected from etcd-server" << std::endl;
}

// Key-value operations
bool EtcdClient::set(const std::string& key, const std::string& value) {
    std::lock_guard<std::mutex> lock(pImpl->mutex_);

    if (!pImpl->connected_) {
        std::cerr << "❌ Not connected to etcd-server" << std::endl;
        return false;
    }

    try {
        // Process data (compress + encrypt)
        std::string processed_value = value;

        // Build JSON payload
        json payload = {
            {"key", key},
            {"value", processed_value},
            {"original_size", value.size()}
        };

        // Send to etcd-server
        auto response = http::post(
            pImpl->config_.host,
            pImpl->config_.port,
            "/kv/set",
            payload.dump(),
            pImpl->config_.timeout_seconds,
            pImpl->config_.max_retry_attempts,
            pImpl->config_.retry_backoff_seconds,
            pImpl->config_.component_name
        );

        if (response.success) {
            std::cout << "✅ Key set: " << key << std::endl;
            return true;
        }

        std::cerr << "❌ Failed to set key: " << key << std::endl;
        return false;

    } catch (const std::exception& e) {
        std::cerr << "❌ Exception in set(): " << e.what() << std::endl;
        return false;
    }
}

std::string EtcdClient::get(const std::string& key) {
    std::lock_guard<std::mutex> lock(pImpl->mutex_);

    if (!pImpl->connected_) {
        std::cerr << "❌ Not connected to etcd-server" << std::endl;
        return "";
    }

    try {
        // Request from etcd-server
        auto response = http::get(
            pImpl->config_.host,
            pImpl->config_.port,
            "/kv/get?key=" + key,
            pImpl->config_.timeout_seconds,
            pImpl->config_.max_retry_attempts,
            pImpl->config_.retry_backoff_seconds,
            pImpl->config_.component_name
        );

        if (!response.success) {
            std::cerr << "❌ Failed to get key: " << key << std::endl;
            return "";
        }

        // Parse response
        json j = json::parse(response.body);
        std::string value = j.value("value", "");
        // original_size = j.value("original_size", 0);

        // Process data (decrypt + decompress)
        std::string processed_value = value;

        std::cout << "✅ Key retrieved: " << key << std::endl;
        return processed_value;

    } catch (const std::exception& e) {
        std::cerr << "❌ Exception in get(): " << e.what() << std::endl;
        return "";
    }
}

bool EtcdClient::del(const std::string& key) {
    std::lock_guard<std::mutex> lock(pImpl->mutex_);

    if (!pImpl->connected_) {
        std::cerr << "❌ Not connected to etcd-server" << std::endl;
        return false;
    }

    auto response = http::del(
        pImpl->config_.host,
        pImpl->config_.port,
        "/kv/delete?key=" + key,
        pImpl->config_.timeout_seconds,
        pImpl->config_.max_retry_attempts,
        pImpl->config_.retry_backoff_seconds,
        pImpl->config_.component_name
    );

    if (response.success) {
        std::cout << "✅ Key deleted: " << key << std::endl;
        return true;
    }

    std::cerr << "❌ Failed to delete key: " << key << std::endl;
    return false;
}

std::vector<std::string> EtcdClient::list_keys(const std::string& prefix) {
    std::lock_guard<std::mutex> lock(pImpl->mutex_);

    std::vector<std::string> keys;

    if (!pImpl->connected_) {
        std::cerr << "❌ Not connected to etcd-server" << std::endl;
        return keys;
    }

    try {
        std::string path = "/kv/list";
        if (!prefix.empty()) {
            path += "?prefix=" + prefix;
        }

        auto response = http::get(
            pImpl->config_.host,
            pImpl->config_.port,
            path,
            pImpl->config_.timeout_seconds,
            pImpl->config_.max_retry_attempts,
            pImpl->config_.retry_backoff_seconds,
            pImpl->config_.component_name
        );

        if (response.success) {
            json j = json::parse(response.body);
            if (j.contains("keys") && j["keys"].is_array()) {
                for (const auto& key : j["keys"]) {
                    keys.push_back(key.get<std::string>());
                }
            }
        }

    } catch (const std::exception& e) {
        std::cerr << "❌ Exception in list_keys(): " << e.what() << std::endl;
    }

    return keys;
}

// Component discovery
bool EtcdClient::register_component() {
    std::lock_guard<std::mutex> lock(pImpl->mutex_);

    if (!pImpl->connected_) {
        std::cerr << "❌ Not connected, attempting to connect..." << std::endl;
        pImpl->mutex_.unlock(); // Unlock before calling connect()
        bool conn = connect();
        pImpl->mutex_.lock();   // Re-lock after connect()

        if (!conn) {
            std::cerr << "❌ Failed to connect for registration" << std::endl;
            return false;
        }
    }

    std::string payload = component::build_registration_payload(pImpl->config_);

    auto response = http::post(
        pImpl->config_.host,
        pImpl->config_.port,
        "/register",
        payload,
        pImpl->config_.timeout_seconds,
        pImpl->config_.max_retry_attempts,
        pImpl->config_.retry_backoff_seconds,
        pImpl->config_.component_name
    );

    if (response.success) {
        std::cout << "✅ Component registered: " << pImpl->config_.component_name << std::endl;

        // Day 59: Parse service discovery paths from registration response
        try {
            auto j = json::parse(response.body);

            if (j.contains("paths") && j["paths"].is_object()) {
                const auto& paths = j["paths"];
                pImpl->service_paths_.hmac_key = paths.value("hmac_key", "");
                pImpl->service_paths_.crypto_token = paths.value("crypto_token", "");
                pImpl->service_paths_.config = paths.value("config", "");

                std::cout << "🗺️  Service discovery paths received:" << std::endl;
                std::cout << "   - HMAC key: " << pImpl->service_paths_.hmac_key << std::endl;
                std::cout << "   - Crypto token: " << pImpl->service_paths_.crypto_token << std::endl;
                std::cout << "   - Config: " << pImpl->service_paths_.config << std::endl;
            } else {
                std::cerr << "⚠️  No service paths in registration response" << std::endl;
            }

            // DEPRECATED DAY 98 — encryption_key del servidor ya no se usa
            // CryptoTransport deriva la clave desde seed.bin via HKDF (ADR-013)
            if (j.contains("encryption_key")) {
                std::cerr << "⚠️  DEPRECATED: encryption_key ignorado — usando CryptoTransport" << std::endl;
            }

        } catch (const std::exception& e) {
            std::cerr << "⚠️  Failed to parse registration response: " << e.what() << std::endl;
        }

        // Start heartbeat thread
        pImpl->mutex_.unlock();
        pImpl->start_heartbeat_thread();
        pImpl->mutex_.lock();

        return true;
    }

    std::cerr << "❌ Component registration failed" << std::endl;
    return false;
}

bool EtcdClient::unregister_component() {
    std::lock_guard<std::mutex> lock(pImpl->mutex_);

    // Stop heartbeat first
    pImpl->mutex_.unlock();
    pImpl->stop_heartbeat_thread();
    pImpl->mutex_.lock();

    if (!pImpl->connected_) {
        std::cerr << "⚠️  Not connected, skipping unregister" << std::endl;
        return false;
    }

    std::string payload = component::build_unregister_payload(pImpl->config_);

    auto response = http::post(
        pImpl->config_.host,
        pImpl->config_.port,
        "/unregister",
        payload,
        pImpl->config_.timeout_seconds,
        1, // Single attempt
        0,
        pImpl->config_.component_name
    );

    if (response.success) {
        std::cout << "✅ Component unregistered: " << pImpl->config_.component_name << std::endl;
        return true;
    }

    std::cerr << "⚠️  Component unregister failed (non-critical)" << std::endl;
    return false;
}

bool EtcdClient::heartbeat() {
    std::lock_guard<std::mutex> lock(pImpl->mutex_);
    return pImpl->send_heartbeat();
}

ComponentInfo EtcdClient::get_component_info(const std::string& name) {
    std::lock_guard<std::mutex> lock(pImpl->mutex_);

    ComponentInfo info;

    if (!pImpl->connected_) {
        std::cerr << "❌ Not connected to etcd-server" << std::endl;
        return info;
    }

    auto response = http::get(
        pImpl->config_.host,
        pImpl->config_.port,
        "/component?name=" + name,
        pImpl->config_.timeout_seconds,
        pImpl->config_.max_retry_attempts,
        pImpl->config_.retry_backoff_seconds,
        pImpl->config_.component_name
    );

    if (response.success) {
        return component::parse_component_info(response.body);
    }

    return info;
}

std::vector<ComponentInfo> EtcdClient::list_components() {
    std::lock_guard<std::mutex> lock(pImpl->mutex_);

    std::vector<ComponentInfo> components;

    if (!pImpl->connected_) {
        std::cerr << "❌ Not connected to etcd-server" << std::endl;
        return components;
    }

    auto response = http::get(
        pImpl->config_.host,
        pImpl->config_.port,
        "/components",
        pImpl->config_.timeout_seconds,
        pImpl->config_.max_retry_attempts,
        pImpl->config_.retry_backoff_seconds,
        pImpl->config_.component_name
    );

    if (response.success) {
        return component::parse_component_list(response.body);
    }

    return components;
}

// Config management
bool EtcdClient::save_config_master(const std::string& config_json) {
    return set("/config/" + pImpl->config_.component_name + "/master", config_json);
}

bool EtcdClient::save_config_active(const std::string& config_json) {
    return set("/config/" + pImpl->config_.component_name + "/active", config_json);
}

std::string EtcdClient::get_config_master() {
    return get("/config/" + pImpl->config_.component_name + "/master");
}

std::string EtcdClient::get_config_active() {
    return get("/config/" + pImpl->config_.component_name + "/active");
}

bool EtcdClient::put_config(const std::string& json_config) {
    std::lock_guard<std::mutex> lock(pImpl->mutex_);

    if (!pImpl->connected_) {
        std::cerr << "❌ [etcd-client] Not connected to etcd-server" << std::endl;
        return false;
    }

    // 1. Validate JSON
    try {
        auto parsed = nlohmann::json::parse(json_config);
        std::cout << "✅ [etcd-client] JSON validated (" << json_config.size() << " bytes)" << std::endl;
        (void)parsed;
    } catch (const std::exception& e) {
        std::cerr << "❌ [etcd-client] Invalid JSON: " << e.what() << std::endl;
        return false;
    }

    try {
    	// 2. Process data (compress + encrypt)
    	size_t original_size = json_config.size();
    	std::string processed_config = pImpl->process_outgoing_data(json_config);

    	// 3. Determine Content-Type
    	std::string content_type = "application/json";
    	if (pImpl->config_.encryption_enabled || pImpl->config_.compression_enabled) {
        	content_type = "application/octet-stream";
    	}

        // 3. Build path
        std::string path = "/v1/config/" + pImpl->config_.component_name;

        std::cout << "📤 [etcd-client] Uploading config to "
                  << pImpl->config_.host << ":" << pImpl->config_.port << path << std::endl;
        std::cout << "   Original: " << json_config.size()
                  << " -> Processed: " << processed_config.size() << " bytes" << std::endl;

        // 4. Send PUT request (9 parameters - original_size will use default = 0)
        auto response = http::put(
    		pImpl->config_.host,
    		pImpl->config_.port,
    		path,
    		processed_config,
    		content_type,  // ← Ya no hardcoded
    		pImpl->config_.timeout_seconds,
    		pImpl->config_.max_retry_attempts,
    		pImpl->config_.retry_backoff_seconds,
    		original_size  // ← Añadir este parámetro
			);

        // 5. Check response
        if (!response.success) {
            std::cerr << "❌ [etcd-client] PUT request failed" << std::endl;
            return false;
        }

        if (response.status_code != 200 && response.status_code != 201) {
            std::cerr << "❌ [etcd-client] Server returned "
                      << response.status_code << ": " << response.body << std::endl;
            return false;
        }

        std::cout << "✅ [etcd-client] Config uploaded successfully!" << std::endl;
        return true;

    } catch (const std::exception& e) {
        std::cerr << "❌ [etcd-client] Exception in put_config(): " << e.what() << std::endl;
        return false;
    }
}

bool EtcdClient::rollback_config() {
    std::string master = get_config_master();
    if (master.empty()) {
        std::cerr << "❌ No master config found for rollback" << std::endl;
        return false;
    }

    bool result = save_config_active(master);
    if (result) {
        std::cout << "✅ Config rolled back to master" << std::endl;
    }

    return result;
}

// Encryption key management
void EtcdClient::set_encryption_key(const std::string& /*key*/) {
    // DEPRECATED DAY 98 — clave gestionada por SeedClient + HKDF (ADR-013)
    std::cerr << "⚠️  DEPRECATED: set_encryption_key() no-op — usar CryptoTransport via SeedClient" << std::endl;
}

bool EtcdClient::has_encryption_key() const {
    // DEPRECATED DAY 98 — retorna true si CryptoTransport está inicializado
    std::lock_guard<std::mutex> lock(pImpl->mutex_);
    return pImpl->tx_ != nullptr;
}


std::string EtcdClient::get_encryption_key() const {
    // DEPRECATED DAY 98 — clave HKDF no expuesta (ADR-013)
    std::cerr << "⚠️  DEPRECATED: get_encryption_key() no disponible con CryptoTransport" << std::endl;
    return "";
}

std::string EtcdClient::get_component_config(const std::string& component_name) {
    return get("/config/" + component_name + "/active");
}

std::optional<std::vector<uint8_t>> EtcdClient::get_hmac_key(const std::string& key_path) {
    std::lock_guard<std::mutex> lock(pImpl->mutex_);
    if (!pImpl->connected_) return std::nullopt;

    auto response = http::get(pImpl->config_.host, pImpl->config_.port, key_path,
                             pImpl->config_.timeout_seconds, pImpl->config_.max_retry_attempts,
                             pImpl->config_.retry_backoff_seconds,
                             pImpl->config_.component_name);
    if (!response.success) return std::nullopt;

    try {
        auto j = json::parse(response.body);
        std::string key_hex;
        if (j.contains("key_hex") && j["key_hex"].is_string()) {
            key_hex = j["key_hex"].get<std::string>();
        } else if (j.contains("key") && j["key"].is_string()) {
            key_hex = j["key"].get<std::string>();
        } else {
            return std::nullopt;
        }
        return EtcdClient::hex_to_bytes(key_hex);
    } catch (...) { return std::nullopt; }
}

ServicePaths EtcdClient::get_service_paths() const {
    std::lock_guard<std::mutex> lock(pImpl->mutex_);
    return pImpl->service_paths_;
}
std::string EtcdClient::compute_hmac_sha256(const std::string& data, const std::vector<uint8_t>& key) {
    unsigned char hmac_result[EVP_MAX_MD_SIZE];
    unsigned int hmac_len;
    HMAC(EVP_sha256(), key.data(), key.size(),
         reinterpret_cast<const unsigned char*>(data.data()), data.size(),
         hmac_result, &hmac_len);
    return EtcdClient::bytes_to_hex(std::vector<uint8_t>(hmac_result, hmac_result + hmac_len));
}

bool EtcdClient::validate_hmac_sha256(const std::string& data, const std::string& hmac_hex,
                                       const std::vector<uint8_t>& key) {
    return compute_hmac_sha256(data, key) == hmac_hex;
}

std::string EtcdClient::bytes_to_hex(const std::vector<uint8_t>& data) {
    std::ostringstream oss;
    oss << std::hex << std::setfill('0');
    for (uint8_t byte : data) oss << std::setw(2) << static_cast<int>(byte);
    return oss.str();
}

std::vector<uint8_t> EtcdClient::hex_to_bytes(const std::string& hex_string) {
    if (hex_string.length() % 2 != 0) throw std::invalid_argument("Hex must have even length");
    std::vector<uint8_t> bytes;
    bytes.reserve(hex_string.length() / 2);
    for (size_t i = 0; i < hex_string.length(); i += 2) {
        bytes.push_back(static_cast<uint8_t>(std::stoi(hex_string.substr(i, 2), nullptr, 16)));
    }
    return bytes;
}

} // namespace etcd_client