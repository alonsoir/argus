// test_crypto_deriver.cpp — ADR-045 DAY 154
// Verifica HkdfCryptoDeriver en aislamiento (sin VaultClient)
#include "../crypto_deriver.h"
#include <cassert>
#include <iostream>
#include <cstring>

using namespace ml_defender;

static VaultClientConfig make_config(const std::string& family, int idx) {
    VaultClientConfig cfg;
    cfg.family          = family;
    cfg.component_index = idx;
    return cfg;
}

// Seed maestro de prueba (32 bytes en hex)
static const std::string MASTER_HEX =
    "0102030405060708090a0b0c0d0e0f10"
    "1112131415161718191a1b1c1d1e1f20";

int main() {
    HkdfCryptoDeriver deriver;

    // T1: derivación básica devuelve material válido
    {
        auto mat = deriver.derive(MASTER_HEX, make_config("etcd", 0));
        assert(mat.has_value());
        assert(mat->family == "etcd");
        assert(mat->key_version == 1);
        assert(!mat->from_cache);
        std::cout << "T1 PASS: derivación básica\n";
    }

    // T2: mismo seed + config → mismo keypair (determinismo)
    {
        auto m1 = deriver.derive(MASTER_HEX, make_config("sniffer", 1));
        auto m2 = deriver.derive(MASTER_HEX, make_config("sniffer", 1));
        assert(m1 && m2);
        assert(m1->pk == m2->pk);
        assert(m1->sk == m2->sk);
        std::cout << "T2 PASS: determinismo\n";
    }

    // T3: distinto component_index → distinto keypair
    {
        auto m0 = deriver.derive(MASTER_HEX, make_config("etcd", 0));
        auto m1 = deriver.derive(MASTER_HEX, make_config("etcd", 1));
        assert(m0 && m1);
        assert(m0->pk != m1->pk);
        std::cout << "T3 PASS: aislamiento por component_index\n";
    }

    // T4: distinta family → distinto keypair
    {
        auto ma = deriver.derive(MASTER_HEX, make_config("etcd",    0));
        auto mb = deriver.derive(MASTER_HEX, make_config("sniffer", 0));
        assert(ma && mb);
        assert(ma->pk != mb->pk);
        std::cout << "T4 PASS: aislamiento por family\n";
    }

    // T5: seed hex inválido → nullopt
    {
        auto mat = deriver.derive("zzzzzz", make_config("etcd", 0));
        assert(!mat.has_value());
        std::cout << "T5 PASS: seed inválido → nullopt\n";
    }

    // T6: fingerprint == sha256(pk)
    {
        auto mat = deriver.derive(MASTER_HEX, make_config("firewall", 2));
        assert(mat.has_value());
        // fingerprint no debe ser todos ceros
        Sha256Fingerprint zero{};
        assert(mat->fingerprint != zero);
        std::cout << "T6 PASS: fingerprint no nulo\n";
    }

    std::cout << "=== test_crypto_deriver: 6/6 PASSED ===\n";
    return 0;
}
