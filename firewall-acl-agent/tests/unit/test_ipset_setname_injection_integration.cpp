// test_ipset_setname_injection_integration.cpp — DAY 189 / H-2 NÚCLEO 1 (INTEGRACION).
// Gemelo de test_ipset_injection_integration.cpp pero atacando el SET_NAME, no la IP.
// Demuestra END-TO-END que un set_name con '\n' NO inyecta una línea en 'ipset restore'
// y que el rechazo viene del guard is_valid_set_name (cableado en add_batch/delete_batch
// ANTES de set_exists_unlocked), no de un SET_NOT_FOUND incidental.
// Authors: Alonso Isidoro Roman + Claude (Anthropic).
//
// REQUIERE: root + ipset + kernel netfilter -> CORRE EN LA VM con sudo (label e2e).
//   vagrant ssh -c 'cd /vagrant/firewall-acl-agent/build-debug && sudo ctest -L e2e --output-on-failure'
// Sin root -> GTEST_SKIP.
#include <gtest/gtest.h>
#include "firewall/ipset_wrapper.hpp"

#include <unistd.h>
#include <string>
#include <vector>

using namespace mldefender::firewall;

namespace {

constexpr const char* kTargetSet = "argus_h2sn_target";
constexpr const char* kEvilSet   = "argus_h2sn_evil";

class IpsetSetNameInjection : public ::testing::Test {
protected:
    IPSetWrapper w_;

    void SetUp() override {
        if (::geteuid() != 0) {
            GTEST_SKIP() << "requiere root + ipset (correr en la VM con sudo)";
        }
        w_.destroy_set(kTargetSet);
        w_.destroy_set(kEvilSet);

        IPSetConfig cfg;
        cfg.name   = kTargetSet;
        cfg.type   = IPSetType::HASH_IP;
        cfg.family = IPSetFamily::INET;
        auto r = w_.create_set(cfg);
        ASSERT_TRUE(r.has_value()) << "no pude crear el set objetivo";
    }

    void TearDown() override {
        if (::geteuid() != 0) return;
        w_.destroy_set(kTargetSet);
        w_.destroy_set(kEvilSet);
    }
};

// ATAQUE PRINCIPAL: set_name con '\n' que intentaría inyectar 'add <EVIL>' en restore.
TEST_F(IpsetSetNameInjection, AddBatchEvilSetNameDoesNotCreateEvilSet) {
    const std::string evil_name =
        std::string(kTargetSet) + "\nadd " + kEvilSet + " 6.6.6.6";
    IPSetEntry good{std::string("203.0.113.10")};  // IP válida: el rechazo será por el NOMBRE

    auto res = w_.add_batch(evil_name, {good});

    // PRIMARIO (efecto): la inyección NO creó el set evil.
    EXPECT_FALSE(w_.set_exists(kEvilSet))
        << "INYECCION: el set_name malicioso creó " << kEvilSet;
    // El set objetivo legítimo tampoco recibió la entrada (se rechazó antes).
    EXPECT_EQ(w_.get_entry_count(kTargetSet), 0u);
    // CONTRATO: rechazado, y por nombre inválido — NO por SET_NOT_FOUND incidental.
    ASSERT_FALSE(res.has_value()) << "add_batch debería rechazar el set_name con '\\n'";
    EXPECT_EQ(res.get_error().code, IPSetErrorCode::INVALID_SET_NAME)
        << "el rechazo debe venir del guard is_valid_set_name, no de SET_NOT_FOUND";
}

// CWE-88: set_name '-X' (flag injection).
TEST_F(IpsetSetNameInjection, AddBatchLeadingDashSetNameRejected) {
    IPSetEntry good{std::string("203.0.113.10")};
    auto res = w_.add_batch("-X", {good});
    EXPECT_FALSE(res.has_value()) << "set_name '-X' debería rechazarse (CWE-88)";
    EXPECT_EQ(res.get_error().code, IPSetErrorCode::INVALID_SET_NAME);
    EXPECT_EQ(w_.get_entry_count(kTargetSet), 0u);
}

// delete_batch: mismo ataque por el otro camino.
TEST_F(IpsetSetNameInjection, DeleteBatchEvilSetNameDoesNotCreateEvilSet) {
    const std::string evil_name =
        std::string(kTargetSet) + "\nadd " + kEvilSet + " 7.7.7.7";
    std::vector<std::string> ips = {"9.9.9.9"};
    auto res = w_.delete_batch(evil_name, ips);

    EXPECT_FALSE(w_.set_exists(kEvilSet))
        << "INYECCION via delete_batch: apareció " << kEvilSet;
    ASSERT_FALSE(res.has_value());
    EXPECT_EQ(res.get_error().code, IPSetErrorCode::INVALID_SET_NAME);
}

// Control: set_name legítimo sigue funcionando (no rompimos el camino feliz).
TEST_F(IpsetSetNameInjection, LegitimateSetNameStillWorks) {
    IPSetEntry good{std::string("203.0.113.20")};
    auto res = w_.add_batch(kTargetSet, {good});
    EXPECT_TRUE(res.has_value()) << "un set_name válido debería funcionar";
    EXPECT_EQ(w_.get_entry_count(kTargetSet), 1u);
}

}  // namespace
