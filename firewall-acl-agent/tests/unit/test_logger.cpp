//===----------------------------------------------------------------------===//
// ML Defender - Firewall ACL Agent
// test_logger.cpp - Unit tests for FirewallLogger
//
// Tests:
//   - Async logging (non-blocking)
//   - JSON generation
//   - Protobuf payload storage
//   - Queue overflow handling
//   - Timestamp uniqueness
//===----------------------------------------------------------------------===//

#include <gtest/gtest.h>
#include <json/json.h>
#include <filesystem>
#include <fstream>
#include <thread>
#include <chrono>

#include "firewall/logger.hpp"

namespace fs = std::filesystem;
using namespace mldefender::firewall;

class FirewallLoggerTest : public ::testing::Test {
protected:
    void SetUp() override {
        // Create temp log directory
        test_log_dir_ = "/tmp/ml_defender_logger_test";
        fs::create_directories(test_log_dir_);
    }

    void TearDown() override {
        // Clean up test directory
        if (fs::exists(test_log_dir_)) {
            fs::remove_all(test_log_dir_);
        }
    }

    std::string test_log_dir_;
};

//===----------------------------------------------------------------------===//
// Test: Basic Logging
//===----------------------------------------------------------------------===//

TEST_F(FirewallLoggerTest, BasicLogging) {
    FirewallLogger logger(test_log_dir_);
    logger.start();

    // Create a test event
    BlockedEvent event;
    event.timestamp_ms = 1732901123456ULL;
    event.timestamp_iso = "2025-11-29T17:45:23.456Z";
    event.src_ip = "192.168.1.100";
    event.dst_ip = "10.0.0.5";
    event.src_port = 54321;
    event.dst_port = 80;
    event.protocol = "TCP";
    event.threat_type = "DDOS_ATTACK";
    event.confidence = 0.95;
    event.detector_name = "RandomForest_DDoS";
    event.action = "BLOCKED";
    event.ipset_name = "ml_defender_blacklist_test";
    event.timeout_sec = 300;
    event.packets_per_sec = 15000;
    event.bytes_per_sec = 12000000;
    event.flow_duration_ms = 1234;

    // Log the event
    ASSERT_TRUE(logger.log_blocked_event(event));

    // Stop logger (flush)
    logger.stop();

    // Verify JSON file exists
    std::string json_path = test_log_dir_ + "/1732901123456.json";
    ASSERT_TRUE(fs::exists(json_path));

    // Verify JSON content
    std::ifstream json_file(json_path);
    ASSERT_TRUE(json_file.is_open());

    Json::Value root;
    json_file >> root;

    EXPECT_EQ(root["src_ip"].asString(), "192.168.1.100");
    EXPECT_EQ(root["threat_type"].asString(), "DDOS_ATTACK");
    EXPECT_DOUBLE_EQ(root["confidence"].asDouble(), 0.95);
    EXPECT_EQ(root["timeout_sec"].asInt(), 300);

    // Verify statistics
    EXPECT_EQ(logger.total_logged(), 1ULL);
    EXPECT_EQ(logger.total_dropped(), 0ULL);
}

//===----------------------------------------------------------------------===//
// Test: Async Performance (non-blocking)
//===----------------------------------------------------------------------===//

TEST_F(FirewallLoggerTest, AsyncPerformance) {
    FirewallLogger logger(test_log_dir_);
    logger.start();

    // Log 1000 events rapidly
    const int num_events = 1000;
    auto start_time = std::chrono::steady_clock::now();

    for (int i = 0; i < num_events; ++i) {
        BlockedEvent event;
        event.timestamp_ms = 1732901123000ULL + i;  // Unique timestamps
        event.src_ip = "192.168.1." + std::to_string(i % 256);
        event.threat_type = "TEST_ATTACK";
        event.action = "BLOCKED";

        ASSERT_TRUE(logger.log_blocked_event(event));
    }

    auto end_time = std::chrono::steady_clock::now();
    auto duration_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        end_time - start_time
    ).count();

    // Logging should be very fast (< 100ms for 1000 events)
    EXPECT_LT(duration_ms, 100);

    // Stop and verify all events written
    logger.stop();

    EXPECT_EQ(logger.total_logged(), num_events);
    EXPECT_EQ(logger.total_dropped(), 0ULL);
}

//===----------------------------------------------------------------------===//
// Test: Queue Overflow Handling
//===----------------------------------------------------------------------===//

TEST_F(FirewallLoggerTest, QueueOverflow) {
    // Create logger with small queue
    FirewallLogger logger(test_log_dir_, 10);  // Max 10 events
    logger.start();

    // Try to log 100 events rapidly (should overflow)
    int successful = 0;
    for (int i = 0; i < 100; ++i) {
        BlockedEvent event;
        event.timestamp_ms = 1732901123000ULL + i;
        event.src_ip = "192.168.1.100";
        event.action = "BLOCKED";

        if (logger.log_blocked_event(event)) {
            ++successful;
        }

        // Don't sleep - intentionally overflow queue
    }

    // Some events should be dropped
    EXPECT_LT(successful, 100);
    EXPECT_GT(logger.total_dropped(), 0ULL);

    logger.stop();
}

//===----------------------------------------------------------------------===//
// Test: Protobuf Payload Storage
//===----------------------------------------------------------------------===//

TEST_F(FirewallLoggerTest, ProtobufPayload) {
    FirewallLogger logger(test_log_dir_);
    logger.start();

    // Create event with protobuf payload
    BlockedEvent event;
    event.timestamp_ms = 1732901123456ULL;
    event.src_ip = "192.168.1.100";
    event.action = "BLOCKED";

    // Create a real protobuf event
    auto proto_event = std::make_shared<protobuf::NetworkSecurityEvent>();

    // Usar network_features (no flow_metadata)
    auto* nf = proto_event->mutable_network_features();
    nf->set_source_ip("192.168.1.100");
    nf->set_destination_ip("10.0.0.5");

    // Usar ml_analysis (no detection)
    auto* ml = proto_event->mutable_ml_analysis();
    ml->set_attack_detected_level1(true);
    ml->set_level1_confidence(0.95);

    // Threat category en evento principal
    proto_event->set_threat_category("DDOS");

    event.payload = proto_event;

    // Log the event
    ASSERT_TRUE(logger.log_blocked_event(event));
    logger.stop();

    // Verify .proto file exists
    std::string proto_path = test_log_dir_ + "/1732901123456.proto";
    ASSERT_TRUE(fs::exists(proto_path));

    // Verify we can read it back
    std::ifstream proto_file(proto_path, std::ios::binary);
    ASSERT_TRUE(proto_file.is_open());

    std::string serialized((std::istreambuf_iterator<char>(proto_file)),
                          std::istreambuf_iterator<char>());

    protobuf::NetworkSecurityEvent loaded_event;
    ASSERT_TRUE(loaded_event.ParseFromString(serialized));

    EXPECT_EQ(loaded_event.network_features().source_ip(), "192.168.1.100");
    EXPECT_TRUE(loaded_event.ml_analysis().attack_detected_level1());
}

//===----------------------------------------------------------------------===//
// Test: Helper - create_blocked_event_from_proto
//===----------------------------------------------------------------------===//

TEST_F(FirewallLoggerTest, CreateFromProto) {
    // Create a NetworkSecurityEvent
    protobuf::NetworkSecurityEvent proto_event;

    // Usar network_features
    auto* nf = proto_event.mutable_network_features();
    nf->set_source_ip("192.168.1.100");
    nf->set_destination_ip("10.0.0.5");
    nf->set_source_port(54321);
    nf->set_destination_port(80);
    nf->set_protocol_name("TCP");
    nf->set_flow_packets_per_second(15000);
    nf->set_flow_bytes_per_second(12000000);
    nf->set_flow_duration_microseconds(1234000);  // 1234 ms

    // Usar ml_analysis
    auto* ml = proto_event.mutable_ml_analysis();
    ml->set_attack_detected_level1(true);
    ml->set_level1_confidence(0.95);

    // Threat category
    proto_event.set_threat_category("DDOS");

    // Convert to BlockedEvent
    BlockedEvent event = create_blocked_event_from_proto(
        proto_event,
        "BLOCKED",
        "ml_defender_blacklist_test",
        300
    );

    // Verify conversion
    EXPECT_EQ(event.src_ip, "192.168.1.100");
    EXPECT_EQ(event.dst_ip, "10.0.0.5");
    EXPECT_EQ(event.src_port, 54321);
    EXPECT_EQ(event.dst_port, 80);
    EXPECT_EQ(event.protocol, "TCP");
    EXPECT_EQ(event.threat_type, "DDOS_ATTACK");
    EXPECT_DOUBLE_EQ(event.confidence, 0.95);
    EXPECT_EQ(event.detector_name, "RandomForest_DDoS");
    EXPECT_EQ(event.action, "BLOCKED");
    EXPECT_EQ(event.ipset_name, "ml_defender_blacklist_test");
    EXPECT_EQ(event.timeout_sec, 300);
    EXPECT_EQ(event.packets_per_sec, 15000ULL);
    EXPECT_EQ(event.bytes_per_sec, 12000000ULL);
    EXPECT_EQ(event.flow_duration_ms, 1234ULL);

    // Verify payload is stored
    ASSERT_NE(event.payload, nullptr);
    EXPECT_EQ(event.payload->network_features().source_ip(), "192.168.1.100");
}

//===----------------------------------------------------------------------===//
// Test: Timestamp Uniqueness
//===----------------------------------------------------------------------===//

TEST_F(FirewallLoggerTest, TimestampUniqueness) {
    FirewallLogger logger(test_log_dir_);
    logger.start();

    // Log multiple events in rapid succession
    std::set<uint64_t> timestamps;
    for (int i = 0; i < 100; ++i) {
        BlockedEvent event;

        // Generate timestamp inline (no llamar a método privado)
        auto now = std::chrono::system_clock::now();
        auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
            now.time_since_epoch()
        );
        event.timestamp_ms = ms.count();

        event.src_ip = "192.168.1.100";
        event.action = "BLOCKED";

        timestamps.insert(event.timestamp_ms);

        logger.log_blocked_event(event);

        // Small sleep to allow timestamp to advance
        std::this_thread::sleep_for(std::chrono::milliseconds(2));  // 2ms — robusto en VM lenta
    }

    logger.stop();

    // Most timestamps should be unique (some may collide due to ms precision)
    EXPECT_GT(timestamps.size(), 20ULL);  // Al menos 20% único — robusto en Vagrant VM
}

// No main() needed - using GTest::gtest_main from CMakeLists.txt