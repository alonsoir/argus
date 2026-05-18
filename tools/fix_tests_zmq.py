#!/usr/bin/env python3
# fix_tests_zmq.py — corrige slow joiner (Test B) y orden bind/connect (Test A)
from pathlib import Path
import sys

OK = '✅'; ERR = '❌'

# ─── Test B: aumentar sleep en SetUp ──────────────────────────────────────────
test_b = Path('/vagrant/etcd-server/tests/test_autonomy_integration.cpp')
content = test_b.read_text()

old = '''        sub_->connect(TEST_ENDPOINT);
        std::this_thread::sleep_for(std::chrono::milliseconds(50));'''
new = '''        sub_->connect(TEST_ENDPOINT);
        // ZMQ slow joiner: esperar propagación de suscripción antes de publicar.
        std::this_thread::sleep_for(std::chrono::milliseconds(300));'''

if old not in content:
    print(f'{ERR} Test B: anchor SetUp sleep no encontrado')
    sys.exit(1)
content = content.replace(old, new, 1)
test_b.write_text(content)
print(f'{OK} Test B: SetUp sleep aumentado a 300ms')

# ─── Test A: publisher bind antes de start_subscriber ─────────────────────────
test_a = Path('/vagrant/firewall-acl-agent/tests/test_autonomy_e2e.cpp')
content = test_a.read_text()

# Reestructurar los tests E2E: pub+sm se crean antes de start_subscriber
# E2E-1
old1 = '''    EXPECT_EQ(reactor_->current_mode(),
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
    EXPECT_TRUE(reactor_->is_deny_active());'''

new1 = '''    EXPECT_EQ(reactor_->current_mode(),
              mldefender::firewall::FirewallAutonomyMode::NORMAL);

    // Publisher bind ANTES de que subscriber conecte — evita slow joiner.
    ml_defender::common::AutonomyPublisher pub(E2E_ENDPOINT, "etcd-server", 0);
    ml_defender::CryptoAutonomy sm("etcd-server", pub.make_callback());

    start_subscriber([]() {
        return mldefender::firewall::FirewallAutonomyMode::NORMAL;
    });

    sm.on_vault_unreachable();
    std::this_thread::sleep_for(std::chrono::milliseconds(SETTLE_MS));

    EXPECT_EQ(reactor_->current_mode(),
              mldefender::firewall::FirewallAutonomyMode::AUTONOMOUS);
    EXPECT_TRUE(reactor_->is_deny_active());'''

if old1 not in content:
    print(f'{ERR} Test A E2E-1: anchor no encontrado')
    sys.exit(1)
content = content.replace(old1, new1, 1)
print(f'{OK} Test A: E2E-1 corregido (pub antes de subscriber)')

# E2E-2
old2 = '''    start_subscriber([]() {
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
    sm.on_vault_restored();'''

new2 = '''    // Publisher bind ANTES de que subscriber conecte.
    ml_defender::common::AutonomyPublisher pub(E2E_ENDPOINT, "etcd-server", 0);
    ml_defender::CryptoAutonomy sm("etcd-server", pub.make_callback());

    start_subscriber([]() {
        return mldefender::firewall::FirewallAutonomyMode::NORMAL;
    });

    // Vault KO
    sm.on_vault_unreachable();
    std::this_thread::sleep_for(std::chrono::milliseconds(SETTLE_MS));
    ASSERT_EQ(reactor_->current_mode(),
              mldefender::firewall::FirewallAutonomyMode::AUTONOMOUS);

    // Vault restaurado
    sm.on_vault_restored();'''

if old2 not in content:
    print(f'{ERR} Test A E2E-2: anchor no encontrado')
    sys.exit(1)
content = content.replace(old2, new2, 1)
print(f'{OK} Test A: E2E-2 corregido')

# E2E-3
old3 = '''    start_subscriber([]() {
        return mldefender::firewall::FirewallAutonomyMode::NORMAL;
    });

    ml_defender::common::AutonomyPublisher pub(E2E_ENDPOINT, "etcd-server", 0);
    ml_defender::CryptoAutonomy sm("etcd-server", pub.make_callback());

    // NORMAL inicial'''

new3 = '''    // Publisher bind ANTES de que subscriber conecte.
    ml_defender::common::AutonomyPublisher pub(E2E_ENDPOINT, "etcd-server", 0);
    ml_defender::CryptoAutonomy sm("etcd-server", pub.make_callback());

    start_subscriber([]() {
        return mldefender::firewall::FirewallAutonomyMode::NORMAL;
    });

    // NORMAL inicial'''

if old3 not in content:
    print(f'{ERR} Test A E2E-3: anchor no encontrado')
    sys.exit(1)
content = content.replace(old3, new3, 1)
print(f'{OK} Test A: E2E-3 corregido')

test_a.write_text(content)
print(f'\n{OK} Ambos ficheros corregidos — recompilar y ejecutar')