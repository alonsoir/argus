#!/usr/bin/env python3
# create_test_a.py — crea test_autonomy_e2e.cpp en la VM
from pathlib import Path

OK = '✅'; ERR = '❌'

TEST_A_PATH = Path('/vagrant/firewall-acl-agent/tests/test_autonomy_e2e.cpp')
TEST_A_PATH.parent.mkdir(parents=True, exist_ok=True)

content = '''// test_autonomy_e2e.cpp — DAY 156
// DEBT-AUTONOMY-CRYPTO-INTEGRATION-001 — Test A (E2E proceso-a-proceso)
// Verifica: Publisher -> ZMQ IPC -> Subscriber -> FirewallAutonomyReactor
// dry_run=true — sin root, sin iptables real.
#include <gtest/gtest.h>
#include "firewall/autonomy_reactor.hpp"
#include "firewall/autonomy_subscriber.hpp"
#include <vault_client/autonomy_publisher.h>
#include <vault_client/crypto_autonomy.h>
#include <chrono>
#include <thread>
#include <atomic>
#include <cstdio>

static constexpr const char* E2E_ENDPOINT = "ipc:///tmp/test_autonomy_e2e.sock";
static constexpr int SETTLE_MS = 300;

class AutonomyE2ETest : public ::testing::Test {
protected:
    void SetUp() override {
        ::unlink("/tmp/test_autonomy_e2e.sock");
        reactor_ = std::make_unique<mldefender::firewall::FirewallAutonomyReactor>(
            std::vector<std::string>{"127.0.0.1/8", "192.168.0.0/16"},
            true  // dry_run — sin iptables real
        );
    }

    void TearDown() override {
        if (sub_) { sub_->stop(); }
        sub_.reset();
        reactor_.reset();
        ::unlink("/tmp/test_autonomy_e2e.sock");
    }

    void start_subscriber(mldefender::firewall::AutonomySubscriber::PollCallback cb) {
        sub_ = std::make_unique<mldefender::firewall::AutonomySubscriber>(
            *reactor_,
            cb,
            E2E_ENDPOINT,
            3600  // reconcile largo para no interferir
        );
        sub_->start();
        std::this_thread::sleep_for(std::chrono::milliseconds(SETTLE_MS));
    }

    std::unique_ptr<mldefender::firewall::FirewallAutonomyReactor> reactor_;
    std::unique_ptr<mldefender::firewall::AutonomySubscriber>      sub_;
};

// E2E-1: Vault KO -> publisher emite AUTONOMOUS -> reactor aplica deny
TEST_F(AutonomyE2ETest, VaultKoTriggersAutonomousMode) {
    EXPECT_EQ(reactor_->current_mode(),
              mldefender::firewall::FirewallAutonomyMode::NORMAL);

    start_subscriber([]() {
        return mldefender::firewall::FirewallAutonomyMode::NORMAL;
    });

    ml_defender::common::AutonomyPublisher pub(E2E_ENDPOINT, "etcd-server", 0);
    ml_defender::CryptoAutonomy sm("etcd-server", pub.make_callback());

    sm.on_vault_unreachable();
    std::this_thread::sleep_for(std::chrono::milliseconds(SETTLE_MS));

    EXPECT_EQ(reactor_->current_mode(),
              mldefender::firewall::FirewallAutonomyMode::AUTONOMOUS);
    EXPECT_TRUE(reactor_->is_deny_active());
}

// E2E-2: Vault restaurado -> RECONCILING -> reactor levanta deny
TEST_F(AutonomyE2ETest, VaultRestoredLiftsAutonomousMode) {
    start_subscriber([]() {
        return mldefender::firewall::FirewallAutonomyMode::NORMAL;
    });

    ml_defender::common::AutonomyPublisher pub(E2E_ENDPOINT, "etcd-server", 0);
    ml_defender::CryptoAutonomy sm("etcd-server", pub.make_callback());

    // Vault KO
    sm.on_vault_unreachable();
    std::this_thread::sleep_for(std::chrono::milliseconds(SETTLE_MS));
    ASSERT_EQ(reactor_->current_mode(),
              mldefender::firewall::FirewallAutonomyMode::AUTONOMOUS);

    // Vault restaurado
    sm.on_vault_restored();
    std::this_thread::sleep_for(std::chrono::milliseconds(SETTLE_MS));

    EXPECT_EQ(reactor_->current_mode(),
              mldefender::firewall::FirewallAutonomyMode::NORMAL);
    EXPECT_FALSE(reactor_->is_deny_active());
}

// E2E-3: Ciclo completo NORMAL -> AUTONOMOUS -> RECONCILING -> NORMAL
TEST_F(AutonomyE2ETest, FullCycleNormalAutonomousReconcileNormal) {
    start_subscriber([]() {
        return mldefender::firewall::FirewallAutonomyMode::NORMAL;
    });

    ml_defender::common::AutonomyPublisher pub(E2E_ENDPOINT, "etcd-server", 0);
    ml_defender::CryptoAutonomy sm("etcd-server", pub.make_callback());

    // NORMAL inicial
    EXPECT_EQ(reactor_->current_mode(),
              mldefender::firewall::FirewallAutonomyMode::NORMAL);

    // -> AUTONOMOUS
    sm.on_vault_unreachable();
    std::this_thread::sleep_for(std::chrono::milliseconds(SETTLE_MS));
    EXPECT_EQ(reactor_->current_mode(),
              mldefender::firewall::FirewallAutonomyMode::AUTONOMOUS);

    // -> RECONCILING (subscriber lo mapea a NORMAL en el reactor)
    sm.on_vault_restored();
    std::this_thread::sleep_for(std::chrono::milliseconds(SETTLE_MS));
    EXPECT_EQ(reactor_->current_mode(),
              mldefender::firewall::FirewallAutonomyMode::NORMAL);
    EXPECT_FALSE(reactor_->is_deny_active());

    // -> NORMAL (no-op desde NORMAL)
    sm.on_reconciliation_ok();
    std::this_thread::sleep_for(std::chrono::milliseconds(SETTLE_MS));
    EXPECT_EQ(reactor_->current_mode(),
              mldefender::firewall::FirewallAutonomyMode::NORMAL);
}

// E2E-4: Subscriber arranca y corre sin evento — estado estable
TEST_F(AutonomyE2ETest, SubscriberRunsStableWithoutEvents) {
    start_subscriber([]() {
        return mldefender::firewall::FirewallAutonomyMode::NORMAL;
    });

    std::this_thread::sleep_for(std::chrono::milliseconds(SETTLE_MS));
    EXPECT_TRUE(sub_->is_running());
    EXPECT_EQ(reactor_->current_mode(),
              mldefender::firewall::FirewallAutonomyMode::NORMAL);
    EXPECT_FALSE(reactor_->is_deny_active());
}

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
'''

TEST_A_PATH.write_text(content)
print(f'{OK} {TEST_A_PATH} creado ({len(content)} bytes)')