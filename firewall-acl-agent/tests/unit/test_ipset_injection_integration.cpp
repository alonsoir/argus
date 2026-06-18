// test_ipset_injection_integration.cpp — DAY 188 / H-2 (INTEGRACION).
// Demuestra END-TO-END que un IP malicioso NO inyecta comandos en 'ipset restore'.
// A diferencia del unit (guardian aislado), prueba que el guardian esta CABLEADO en el
// camino peligroso (add_batch -> restore file -> ipset restore) y que el efecto
// observable de la inyeccion NO ocurre.
// Authors: Alonso Isidoro Roman + Claude (Anthropic).
//
// REQUIERE: root + 'ipset' + kernel netfilter -> CORRE EN LA VM, NO en macOS.
//   vagrant ssh -c 'cd /vagrant/build/firewall-acl-agent && sudo ctest -L e2e --output-on-failure'
// Sin root -> GTEST_SKIP (no falla).
//
// CANARIO: si is_valid_ip dejara pasar "X/24\nadd <EVIL> ...", ipset restore crearia el
// set <EVIL>. Aserto central: set_exists(<EVIL>) == false tras el intento.
//
// NOTA API: las lineas '<-- AJUSTA' usan has_value()/struct fields asumidos. Si tu API de
// IPSetResult/IPSetConfig/IPSetEntry difiere, ajustalas. Los asertos set_exists/
// get_entry_count (los PRIMARIOS) no dependen de eso y prueban el cierre por si solos.
#include <gtest/gtest.h>
#include "firewall/ipset_wrapper.hpp"

#include <unistd.h>
#include <string>
#include <vector>

using namespace mldefender::firewall;

namespace {

constexpr const char* kTargetSet = "argus_h2_target";
constexpr const char* kEvilSet   = "argus_h2_evil";

class IpsetInjection : public ::testing::Test {
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
        ASSERT_TRUE(r.has_value()) << "no pude crear el set objetivo";  // <-- AJUSTA
    }

    void TearDown() override {
        if (::geteuid() != 0) return;
        w_.destroy_set(kTargetSet);
        w_.destroy_set(kEvilSet);
    }
};

TEST_F(IpsetInjection, AddBatchNewlineInjectionDoesNotCreateEvilSet) {
    // [H-2 DAY188 IPSetEntry ctor fix] IPSetEntry exige IP en el ctor (no default-construct).
    IPSetEntry evil{std::string("1.2.3.4/24\nadd ") + kEvilSet + " 6.6.6.6"};

    auto res = w_.add_batch(kTargetSet, {evil});

    EXPECT_FALSE(w_.set_exists(kEvilSet))
        << "INYECCION: el IP malicioso creo el set " << kEvilSet;
    EXPECT_EQ(w_.get_entry_count(kTargetSet), 0u);
    EXPECT_FALSE(res.has_value()) << "add_batch deberia rechazar la IP malformada";  // <-- AJUSTA
}

TEST_F(IpsetInjection, DeleteBatchNewlineInjectionDoesNotCreateEvilSet) {
    std::vector<std::string> ips = {
        std::string("9.9.9.9/24\nadd ") + kEvilSet + " 7.7.7.7"
    };
    auto res = w_.delete_batch(kTargetSet, ips);

    EXPECT_FALSE(w_.set_exists(kEvilSet))
        << "INYECCION via delete_batch: aparecio " << kEvilSet;
    EXPECT_FALSE(res.has_value());  // <-- AJUSTA
}

TEST_F(IpsetInjection, LegitimateIpStillAccepted) {
    IPSetEntry good{std::string("203.0.113.10")};
    auto res = w_.add_batch(kTargetSet, {good});
    EXPECT_TRUE(res.has_value()) << "una IP valida deberia entrar";  // <-- AJUSTA
    EXPECT_EQ(w_.get_entry_count(kTargetSet), 1u);
}

}  // namespace
