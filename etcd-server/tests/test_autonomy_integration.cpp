// test_autonomy_integration.cpp — DAY 156
// DEBT-AUTONOMY-CRYPTO-INTEGRATION-001 — Test B (unitario)
// Verifica: CryptoAutonomyStateMachine + AutonomyPublisher via ZMQ real.
// Sin procesos externos. Socket temporal.
#include <gtest/gtest.h>
#include <vault_client/autonomy_publisher.h>
#include <vault_client/crypto_autonomy.h>
#include <zmq.hpp>
#include <nlohmann/json.hpp>
#include <chrono>
#include <thread>
#include <vector>
#include <string>
#include <cstdio>

static constexpr const char* TEST_ENDPOINT = "ipc:///tmp/test_autonomy_integration.sock";
static constexpr int RECV_TIMEOUT_MS = 2000;

static std::string recv_one(zmq::socket_t& sub) {
    zmq::message_t topic, payload;
    auto r1 = sub.recv(topic,   zmq::recv_flags::none);
    auto r2 = sub.recv(payload, zmq::recv_flags::none);
    if (!r1 || !r2) return "";
    return std::string(static_cast<char*>(payload.data()), payload.size());
}

class AutonomyIntegrationTest : public ::testing::Test {
protected:
    void SetUp() override {
        ::unlink("/tmp/test_autonomy_integration.sock");
        // Publisher bind PRIMERO — luego subscriber conecta.
        // Evita slow joiner: la suscripción se propaga antes del primer mensaje.
        pub_ = std::make_unique<ml_defender::common::AutonomyPublisher>(
            TEST_ENDPOINT, "etcd-server", 0);
        ctx_ = std::make_unique<zmq::context_t>(1);
        sub_ = std::make_unique<zmq::socket_t>(*ctx_, zmq::socket_type::sub);
        sub_->set(zmq::sockopt::rcvtimeo, RECV_TIMEOUT_MS);
        sub_->set(zmq::sockopt::subscribe, "argus.crypto.autonomy");
        sub_->connect(TEST_ENDPOINT);
        std::this_thread::sleep_for(std::chrono::milliseconds(200));
    }

    void TearDown() override {
        sub_.reset();
        ctx_.reset();
        pub_.reset();
        ::unlink("/tmp/test_autonomy_integration.sock");
    }

    std::unique_ptr<ml_defender::common::AutonomyPublisher> pub_;
    std::unique_ptr<zmq::context_t> ctx_;
    std::unique_ptr<zmq::socket_t>  sub_;
};

// T1: Estado inicial NORMAL — no emite evento
TEST_F(AutonomyIntegrationTest, InitialStateNoEvent) {
    ml_defender::CryptoAutonomy sm("test", pub_->make_callback());

    EXPECT_EQ(sm.current_mode(), ml_defender::OperationalMode::NORMAL);
    EXPECT_TRUE(sm.can_operate());

    // No debe haber mensaje
    auto msg = recv_one(*sub_);
    EXPECT_TRUE(msg.empty());
}

// T2: on_vault_unreachable() publica AUTONOMOUS
TEST_F(AutonomyIntegrationTest, VaultKoPublishesAutonomous) {
    ml_defender::CryptoAutonomy sm("etcd-server", pub_->make_callback());

    sm.on_vault_unreachable();

    EXPECT_EQ(sm.current_mode(), ml_defender::OperationalMode::AUTONOMOUS);

    auto msg = recv_one(*sub_);
    ASSERT_FALSE(msg.empty()) << "No message received within timeout";

    auto j = nlohmann::json::parse(msg);
    EXPECT_EQ(j["state"].get<std::string>(),     "AUTONOMOUS");
    EXPECT_EQ(j["from"].get<std::string>(),      "NORMAL");
    EXPECT_EQ(j["component"].get<std::string>(), "etcd-server");
    EXPECT_GT(j["timestamp_utc_ns"].get<int64_t>(), 0);
}

// T3: AUTONOMOUS -> on_vault_restored() publica RECONCILING
TEST_F(AutonomyIntegrationTest, VaultRestoredPublishesReconciling) {
    ml_defender::CryptoAutonomy sm("etcd-server", pub_->make_callback());

    sm.on_vault_unreachable();
    recv_one(*sub_); // consumir AUTONOMOUS

    sm.on_vault_restored();
    EXPECT_EQ(sm.current_mode(), ml_defender::OperationalMode::RECONCILING);

    auto msg = recv_one(*sub_);
    ASSERT_FALSE(msg.empty());
    auto j = nlohmann::json::parse(msg);
    EXPECT_EQ(j["state"].get<std::string>(), "RECONCILING");
    EXPECT_EQ(j["from"].get<std::string>(),  "AUTONOMOUS");
}

// T4: RECONCILING -> on_reconciliation_ok() publica NORMAL
TEST_F(AutonomyIntegrationTest, ReconciliationOkPublishesNormal) {
    ml_defender::CryptoAutonomy sm("etcd-server", pub_->make_callback());

    sm.on_vault_unreachable(); recv_one(*sub_);
    sm.on_vault_restored();    recv_one(*sub_);

    sm.on_reconciliation_ok();
    EXPECT_EQ(sm.current_mode(), ml_defender::OperationalMode::NORMAL);

    auto msg = recv_one(*sub_);
    ASSERT_FALSE(msg.empty());
    auto j = nlohmann::json::parse(msg);
    EXPECT_EQ(j["state"].get<std::string>(), "NORMAL");
    EXPECT_EQ(j["from"].get<std::string>(),  "RECONCILING");
}

// T5: on_vault_unreachable() desde AUTONOMOUS es no-op
TEST_F(AutonomyIntegrationTest, VaultKoFromAutonomousIsNoop) {
    ml_defender::CryptoAutonomy sm("etcd-server", pub_->make_callback());

    sm.on_vault_unreachable();
    recv_one(*sub_); // consumir primer evento

    sm.on_vault_unreachable(); // no-op
    EXPECT_EQ(sm.current_mode(), ml_defender::OperationalMode::AUTONOMOUS);

    auto msg = recv_one(*sub_);
    EXPECT_TRUE(msg.empty()) << "Unexpected event: " << msg;
}

// T6: on_revocation() publica DEGRADED (terminal)
TEST_F(AutonomyIntegrationTest, RevocationPublishesDegraded) {
    ml_defender::CryptoAutonomy sm("etcd-server", pub_->make_callback());

    sm.on_revocation();
    EXPECT_EQ(sm.current_mode(), ml_defender::OperationalMode::DEGRADED);
    EXPECT_FALSE(sm.can_operate());

    auto msg = recv_one(*sub_);
    ASSERT_FALSE(msg.empty());
    auto j = nlohmann::json::parse(msg);
    EXPECT_EQ(j["state"].get<std::string>(), "DEGRADED");
}

// T7: simulacion del health-check loop de etcd-server/main.cpp
TEST_F(AutonomyIntegrationTest, HealthCheckLoopSimulation) {
    ml_defender::CryptoAutonomy sm("etcd-server", pub_->make_callback());

    bool vault_healthy = true;
    bool was_healthy   = true;
    std::vector<std::string> transitions;

    auto tick = [&]() {
        if (!vault_healthy && was_healthy) {
            sm.on_vault_unreachable();
            transitions.push_back("AUTONOMOUS");
        } else if (vault_healthy && !was_healthy) {
            sm.on_vault_restored();
            transitions.push_back("RECONCILING");
            sm.on_reconciliation_ok();
            transitions.push_back("NORMAL");
        }
        was_healthy = vault_healthy;
    };

    tick(); // saludable, no-op
    EXPECT_EQ(sm.current_mode(), ml_defender::OperationalMode::NORMAL);

    vault_healthy = false;
    tick(); // KO -> AUTONOMOUS
    EXPECT_EQ(sm.current_mode(), ml_defender::OperationalMode::AUTONOMOUS);

    vault_healthy = true;
    tick(); // restaurado -> NORMAL
    EXPECT_EQ(sm.current_mode(), ml_defender::OperationalMode::NORMAL);

    ASSERT_EQ(transitions.size(), 3u);
    EXPECT_EQ(transitions[0], "AUTONOMOUS");
    EXPECT_EQ(transitions[1], "RECONCILING");
    EXPECT_EQ(transitions[2], "NORMAL");
}

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
