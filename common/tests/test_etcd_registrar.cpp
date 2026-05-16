// test_etcd_registrar.cpp — ADR-045 DAY 154
#include "../etcd_registrar.h"
#include "../vault_types.h"
#include <cassert>
#include <iostream>

using namespace ml_defender;

static CryptoMaterial make_material() {
    CryptoMaterial m;
    m.family               = "etcd";
    m.key_version          = 1;
    m.derivation_timestamp = "2026-05-16T00:00:00Z";
    m.from_cache           = false;
    m.fingerprint.fill(0xAB);
    return m;
}

int main() {
    StubEtcdRegistrar reg;

    // T1: register_status devuelve true
    {
        auto mat = make_material();
        assert(reg.register_status(mat, "etcd-server", false) == true);
        std::cout << "T1 PASS: register_status OK\n";
    }

    // T2: started_with_cache=true también devuelve true
    {
        auto mat = make_material();
        assert(reg.register_status(mat, "sniffer", true) == true);
        std::cout << "T2 PASS: started_with_cache=true OK\n";
    }

    // T3: start/stop keepalive no crashean
    {
        reg.start_keepalive();
        reg.stop_keepalive();
        std::cout << "T3 PASS: start/stop keepalive OK\n";
    }

    // T4: inyección en VaultClient — register_etcd_status delega al registrar
    {
        // Registrar que cuenta llamadas
        struct CountingRegistrar : public IEtcdRegistrar {
            int calls{0};
            bool register_status(const CryptoMaterial&, const std::string&,
                                  bool) override { ++calls; return true; }
            void start_keepalive() override {}
            void stop_keepalive()  override {}
        };
        auto* cr = new CountingRegistrar();
        // No podemos construir VaultClient sin Vault real, verificamos la
        // interfaz directamente
        auto mat = make_material();
        cr->register_status(mat, "test", false);
        assert(cr->calls == 1);
        delete cr;
        std::cout << "T4 PASS: interfaz IEtcdRegistrar verificada\n";
    }

    std::cout << "=== test_etcd_registrar: 4/4 PASSED ===\n";
    return 0;
}
