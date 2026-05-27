//===----------------------------------------------------------------------===//
// ML Defender - Firewall ACL Agent
// logger.cpp - Asynchronous Structured Logger Implementation
//
// Via Appia Quality: Production-grade logging for decades
//===----------------------------------------------------------------------===//

#include "firewall/logger.hpp"

#include <fstream>
#include <sstream>
#include <iomanip>
#include <filesystem>
#include <ctime>
#include <json/json.h>
#include <openssl/hmac.h>
#include <openssl/evp.h>

namespace fs = std::filesystem;

namespace mldefender {
namespace firewall {

//===----------------------------------------------------------------------===//
// Constructor / Destructor
//===----------------------------------------------------------------------===//

FirewallLogger::FirewallLogger(const std::string& output_dir,
                               size_t max_queue_size)
    : output_dir_(output_dir)
    , max_queue_size_(max_queue_size)
{
    // Ensure output directory exists
    if (!ensure_directory_exists(output_dir_)) {
        throw std::runtime_error("Failed to create log directory: " + output_dir_);
    }
}

FirewallLogger::~FirewallLogger() {
    if (running_.load()) {
        stop();
    }
}

//===----------------------------------------------------------------------===//
// Public API
//===----------------------------------------------------------------------===//

void FirewallLogger::start() {
    if (running_.exchange(true)) {
        // Already running
        return;
    }

    worker_thread_ = std::thread(&FirewallLogger::worker_loop, this);
}

void FirewallLogger::stop(int timeout_ms) {
    if (!running_.exchange(false)) {
        // Already stopped
        return;
    }

    // Wake up worker thread
    queue_cv_.notify_one();

    // Wait for worker to finish (with timeout if specified)
    if (timeout_ms > 0) {
        // Detach if timeout expires
        auto start = std::chrono::steady_clock::now();
        while (worker_thread_.joinable()) {
            auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::steady_clock::now() - start
            ).count();

            if (elapsed > timeout_ms) {
                worker_thread_.detach();
                break;
            }

            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
    }

    if (worker_thread_.joinable()) {
        worker_thread_.join();
    }
}

bool FirewallLogger::log_blocked_event(const BlockedEvent& event) {
    std::unique_lock<std::mutex> lock(queue_mutex_);

    // Check if queue is full
    if (event_queue_.size() >= max_queue_size_) {
        total_dropped_.fetch_add(1);
        return false;
    }

    // Add to queue
    event_queue_.push(event);
    queue_size_.fetch_add(1);

    // Notify worker
    queue_cv_.notify_one();

    return true;
}

//===----------------------------------------------------------------------===//
// Worker Thread
//===----------------------------------------------------------------------===//

void FirewallLogger::worker_loop() {
    while (running_.load()) {
        BlockedEvent event;

        {
            std::unique_lock<std::mutex> lock(queue_mutex_);

            // Wait for events or stop signal
            queue_cv_.wait(lock, [this] {
                return !event_queue_.empty() || !running_.load();
            });

            // Check if we should stop
            if (!running_.load() && event_queue_.empty()) {
                break;
            }

            // Get next event
            if (!event_queue_.empty()) {
                event = event_queue_.front();
                event_queue_.pop();
                queue_size_.fetch_sub(1);
            } else {
                continue;
            }
        }

        // Write to disk (outside lock)
        if (write_event_to_disk(event)) {
            total_logged_.fetch_add(1);
        } else {
            // Log write failure (to stderr)
            std::cerr << "[FirewallLogger] Failed to write event for IP: "
                      << event.src_ip << std::endl;
        }
    }

    // Flush remaining events
    std::unique_lock<std::mutex> lock(queue_mutex_);
    while (!event_queue_.empty()) {
        BlockedEvent event = event_queue_.front();
        event_queue_.pop();
        queue_size_.fetch_sub(1);

        lock.unlock();
        if (write_event_to_disk(event)) {
            total_logged_.fetch_add(1);
        }
        lock.lock();
    }
}

//===----------------------------------------------------------------------===//
// Disk Writing
//===----------------------------------------------------------------------===//

bool FirewallLogger::write_event_to_disk(const BlockedEvent& event) {
    // Generate filename with timestamp
    std::string base_filename = std::to_string(event.timestamp_ms);
    std::string json_path = output_dir_ + "/" + base_filename + ".json";
    std::string proto_path = output_dir_ + "/" + base_filename + ".proto";

    // Write JSON metadata
    std::string json_content = generate_json(event);
    std::ofstream json_file(json_path);
    if (!json_file) {
        std::cerr << "[FirewallLogger] Failed to open JSON file: "
                  << json_path << std::endl;
        return false;
    }
    json_file << json_content;
    json_file.close();

    // Write protobuf payload
    if (event.payload) {
        if (!write_payload(event, proto_path)) {
            std::cerr << "[FirewallLogger] Failed to write payload: "
                      << proto_path << std::endl;
            // Continue anyway - JSON is more important
        }
    }

    return true;
}

std::string FirewallLogger::generate_json(const BlockedEvent& event) {
    Json::Value root;

    // Temporal context
    root["timestamp"] = Json::Value::UInt64(event.timestamp_ms);
    root["timestamp_iso"] = event.timestamp_iso;

    // Network context
    root["src_ip"] = event.src_ip;
    root["dst_ip"] = event.dst_ip;
    root["src_port"] = event.src_port;
    root["dst_port"] = event.dst_port;
    root["protocol"] = event.protocol;

    // Detection context
    root["threat_type"] = event.threat_type;
    root["confidence"] = event.confidence;
    root["detector_name"] = event.detector_name;

    // Action context
    root["action"] = event.action;
    root["ipset_name"] = event.ipset_name;
    root["timeout_sec"] = event.timeout_sec;

    // Features summary
    Json::Value features;
    features["packets_per_sec"] = Json::Value::UInt64(event.packets_per_sec);
    features["bytes_per_sec"] = Json::Value::UInt64(event.bytes_per_sec);
    features["flow_duration_ms"] = Json::Value::UInt64(event.flow_duration_ms);
    root["features_summary"] = features;

    // Payload reference
    root["payload_file"] = std::to_string(event.timestamp_ms) + ".proto";

    // Pretty print JSON
    Json::StreamWriterBuilder builder;
    builder["indentation"] = "  ";
    return Json::writeString(builder, root);
}

bool FirewallLogger::write_payload(const BlockedEvent& event,
                                   const std::string& filename) {
    if (!event.payload) {
        return false;
    }

    // Serialize protobuf to string (uncompressed, unencrypted)
    std::string serialized;
    if (!event.payload->SerializeToString(&serialized)) {
        return false;
    }

    // Write to file
    std::ofstream proto_file(filename, std::ios::binary);
    if (!proto_file) {
        return false;
    }

    proto_file.write(serialized.data(), serialized.size());
    proto_file.close();

    return true;
}

//===----------------------------------------------------------------------===//
// Helper Functions
//===----------------------------------------------------------------------===//

uint64_t FirewallLogger::get_timestamp_ms() {
    auto now = std::chrono::system_clock::now();
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        now.time_since_epoch()
    );
    return ms.count();
}

std::string FirewallLogger::timestamp_to_iso(uint64_t timestamp_ms) {
    auto tp = std::chrono::system_clock::time_point(
        std::chrono::milliseconds(timestamp_ms)
    );
    auto time_t = std::chrono::system_clock::to_time_t(tp);
    auto ms = timestamp_ms % 1000;

    std::stringstream ss;
    ss << std::put_time(std::gmtime(&time_t), "%Y-%m-%dT%H:%M:%S");
    ss << '.' << std::setfill('0') << std::setw(3) << ms << 'Z';

    return ss.str();
}

bool FirewallLogger::ensure_directory_exists(const std::string& path) {
    try {
        if (!fs::exists(path)) {
            return fs::create_directories(path);
        }
        return fs::is_directory(path);
    } catch (const fs::filesystem_error& e) {
        std::cerr << "[FirewallLogger] Directory error: " << e.what() << std::endl;
        return false;
    }
}

//===----------------------------------------------------------------------===//
// Helper - Create BlockedEvent from Protobuf
//===----------------------------------------------------------------------===//

BlockedEvent create_blocked_event_from_proto(
    const protobuf::NetworkSecurityEvent& proto_event,
    const std::string& action,
    const std::string& ipset_name,
    int timeout_sec
) {
    BlockedEvent event;

    // Generate timestamp - llamar funciones directamente
    auto now = std::chrono::system_clock::now();
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        now.time_since_epoch()
    );
    event.timestamp_ms = ms.count();

    // Generate ISO timestamp
    auto tp = std::chrono::system_clock::time_point(
        std::chrono::milliseconds(event.timestamp_ms)
    );
    auto time_t = std::chrono::system_clock::to_time_t(tp);
    auto ms_part = event.timestamp_ms % 1000;

    std::stringstream ss;
    ss << std::put_time(std::gmtime(&time_t), "%Y-%m-%dT%H:%M:%S");
    ss << '.' << std::setfill('0') << std::setw(3) << ms_part << 'Z';
    event.timestamp_iso = ss.str();

    // Extract network info from protobuf
    if (proto_event.has_network_features()) {
        const auto& nf = proto_event.network_features();
        event.src_ip = nf.source_ip();
        event.dst_ip = nf.destination_ip();
        event.src_port = nf.source_port();
        event.dst_port = nf.destination_port();

        // Protocol name (campo directo en tu schema)
        event.protocol = nf.protocol_name();
    }

    // Extract detection info
    if (proto_event.has_ml_analysis()) {
        const auto& ml = proto_event.ml_analysis();

        // Usar threat_category del evento principal
        std::string threat_cat = proto_event.threat_category();

        if (threat_cat == "DDOS") {
            event.threat_type = "DDOS_ATTACK";
            event.confidence = ml.level1_confidence();
            event.detector_name = "RandomForest_DDoS";
        } else if (threat_cat == "RANSOMWARE") {
            event.threat_type = "RANSOMWARE";
            event.confidence = ml.level1_confidence();
            event.detector_name = "RandomForest_Ransomware";
        } else if (threat_cat == "SUSPICIOUS_INTERNAL") {
            event.threat_type = "INTERNAL_THREAT";
            event.confidence = ml.level1_confidence();
            event.detector_name = "RandomForest_Internal";
        } else {
            event.threat_type = "TRAFFIC_ANOMALY";
            event.confidence = ml.level1_confidence();
            event.detector_name = "RandomForest_Traffic";
        }
    }

    // Action context
    event.action = action;
    event.ipset_name = ipset_name;
    event.timeout_sec = timeout_sec;

    // Extract features summary (campos directos disponibles en tu schema)
    if (proto_event.has_network_features()) {
        const auto& nf = proto_event.network_features();

        // Usar campos que SÍ existen en tu NetworkFeatures
        event.packets_per_sec = static_cast<uint64_t>(nf.flow_packets_per_second());
        event.bytes_per_sec = static_cast<uint64_t>(nf.flow_bytes_per_second());

        // Flow duration en microsegundos (convertir a ms)
        event.flow_duration_ms = nf.flow_duration_microseconds() / 1000;
    }

    // Store full payload
    event.payload = std::make_shared<protobuf::NetworkSecurityEvent>(proto_event);

    return event;
}

    //===----------------------------------------------------------------------===//
// CSV + HMAC Support (Day 58 - Pioneer Pattern)
//===----------------------------------------------------------------------===//

bool FirewallLogger::append_csv_log(const BlockedEvent& event,
                                    const std::vector<uint8_t>& hmac_key) {
    if (hmac_key.size() != 32) {
        std::cerr << "[FirewallLogger] Invalid HMAC key size: "
                  << hmac_key.size() << " (expected 32)" << std::endl;
        return false;
    }

    // Generate CSV line (without HMAC)
    std::string csv_line = generate_csv_line(event);

    // Compute HMAC signature
    std::string hmac_sig = compute_hmac_for_csv(csv_line, hmac_key);
    if (hmac_sig.empty()) {
        std::cerr << "[FirewallLogger] Failed to compute HMAC signature" << std::endl;
        return false;
    }

    // Append HMAC to line
    std::string full_line = csv_line + "," + hmac_sig;

    // Write to CSV file (append mode)
    std::string csv_path = output_dir_ + "/firewall_blocks.csv";
    std::ofstream csv_file(csv_path, std::ios::app);
    if (!csv_file) {
        std::cerr << "[FirewallLogger] Failed to open CSV file: " << csv_path << std::endl;
        return false;
    }

    csv_file << full_line << "\n";
    csv_file.close();

    return true;
}

std::string FirewallLogger::generate_csv_line(const BlockedEvent& event) {
    std::ostringstream oss;

    // Format: timestamp_ms,src_ip,dst_ip,threat_type,action,confidence
    oss << event.timestamp_ms << ","
        << event.src_ip << ","
        << event.dst_ip << ","
        << event.threat_type << ","
        << event.action << ","
        << std::fixed << std::setprecision(4) << event.confidence;

    return oss.str();
}

std::string FirewallLogger::compute_hmac_for_csv(const std::string& csv_line,
                                                 const std::vector<uint8_t>& key) {
    if (key.size() != 32) {
        return "";
    }

    // Compute HMAC-SHA256
    unsigned char hmac_result[EVP_MAX_MD_SIZE];
    unsigned int hmac_len = 0;

    HMAC(EVP_sha256(),
         key.data(), key.size(),
         reinterpret_cast<const unsigned char*>(csv_line.data()), csv_line.size(),
         hmac_result, &hmac_len);

    // Convert to hex string
    std::ostringstream hex_stream;
    hex_stream << std::hex << std::setfill('0');
    for (unsigned int i = 0; i < hmac_len; ++i) {
        hex_stream << std::setw(2) << static_cast<int>(hmac_result[i]);
    }

    return hex_stream.str();
}

} // namespace firewall
} // namespace mldefender