// etcd-server/tests/test_secrets_manager_simple.cpp
// Day 55: pruebas básicas del SecretsManager. [ETCD-CLAVES-D314] reescritas para la API de la ventana de dos sobre
// ISecretStore (MemoriaSecretStore) con reloj inyectado: sin esperas reales (antes, 9 s de sleep).
//
// Co-authored-by: Claude (Anthropic)
// Co-authored-by: Alonso

#include "etcd_server/secrets_manager.hpp"
#include <cassert>
#include <ctime>
#include <iostream>
#include <memory>
#include <sstream>

using namespace etcd_server;

#define GREEN "\033[32m"
#define RESET "\033[0m"

namespace {
std::time_t g_t = 1'800'000'000;
std::ostringstream g_log;

std::unique_ptr<SecretsManager> hacer(int grace, int min_rot) {
    SecretsConfig c;
    c.grace_period_seconds = grace;
    c.min_rotation_interval_seconds = min_rot;
    c.default_key_length_bytes = 32;
    return std::make_unique<SecretsManager>(c, std::make_unique<argus::claves::MemoriaSecretStore>(), true, 60, 5,
                                            [] { return g_t; }, g_log);
}
}  // namespace

void test_generate_and_get() {
    std::cout << "Test 1: crear y leer la clave activa..." << std::flush;
    auto m = hacer(300, 300);
    ClaveHMAC k;
    bool copia = true;
    assert(m->activa("test-component", k, copia) == ResultadoClaves::Ok);
    assert(k.hex.size() == 64);  // 32 bytes = 64 hex
    assert(k.activa);
    assert(!copia);
    ClaveHMAC k2;
    assert(m->activa("test-component", k2, copia) == ResultadoClaves::Ok);
    assert(k2.hex == k.hex && k2.huella == k.huella);
    std::cout << GREEN << " PASS" << RESET << std::endl;
}

void test_rotation_grace_period() {
    std::cout << "Test 2: rotar con ventana de dos..." << std::flush;
    auto m = hacer(5, 5);
    ClaveHMAC k1, k2;
    bool copia = false;
    int reintentar = 0;
    assert(m->activa("test-rotate", k1, copia) == ResultadoClaves::Ok);
    g_t += 5;
    assert(m->rotar("test-rotate", false, k2, reintentar) == ResultadoClaves::Ok);
    assert(k2.hex != k1.hex);
    std::vector<ClaveHMAC> v;
    assert(m->validas("test-rotate", v, copia) == ResultadoClaves::Ok);
    assert(v.size() == 2);
    assert(v[0].activa && v[0].hex == k2.hex);
    assert(!v[1].activa && v[1].hex == k1.hex && v[1].expira == g_t + 5);
    std::cout << GREEN << " PASS" << RESET << std::endl;
}

void test_grace_period_expiry() {
    std::cout << "Test 3: la anterior caduca a los grace_period_seconds..." << std::flush;
    auto m = hacer(2, 2);
    ClaveHMAC k;
    bool copia = false;
    int reintentar = 0;
    assert(m->activa("test-expiry", k, copia) == ResultadoClaves::Ok);
    g_t += 2;
    assert(m->rotar("test-expiry", false, k, reintentar) == ResultadoClaves::Ok);
    std::vector<ClaveHMAC> v;
    assert(m->validas("test-expiry", v, copia) == ResultadoClaves::Ok && v.size() == 2);
    g_t += 1;
    assert(m->validas("test-expiry", v, copia) == ResultadoClaves::Ok && v.size() == 2);
    g_t += 1;  // justo en expira_anterior: ya no vale
    assert(m->validas("test-expiry", v, copia) == ResultadoClaves::Ok && v.size() == 1);
    assert(v[0].activa);
    std::cout << GREEN << " PASS" << RESET << std::endl;
}

void test_config_values() {
    std::cout << "Test 4: el grace period sale de la configuración..." << std::flush;
    auto m = hacer(42, 42);
    assert(m->get_grace_period_seconds() == 42);
    std::cout << GREEN << " PASS" << RESET << std::endl;
}

void test_cooldown() {
    std::cout << "Test 5: enfriamiento (429) y force..." << std::flush;
    auto m = hacer(10, 10);
    ClaveHMAC k1, k2, k3;
    bool copia = false;
    int reintentar = 0;
    assert(m->activa("test-cooldown", k1, copia) == ResultadoClaves::Ok);
    g_t += 3;
    assert(m->rotar("test-cooldown", false, k2, reintentar) == ResultadoClaves::Enfriamiento);
    assert(reintentar == 7);
    assert(m->rotar("test-cooldown", true, k2, reintentar) == ResultadoClaves::Ok);  // force
    assert(k2.hex != k1.hex);
    g_t += 10;
    assert(m->rotar("test-cooldown", false, k3, reintentar) == ResultadoClaves::Ok);
    assert(k3.hex != k2.hex);
    std::cout << GREEN << " PASS" << RESET << std::endl;
}

int main() {
    std::cout << "═══════════════════════════════════════════" << std::endl;
    std::cout << "  SecretsManager Basic Tests (Day 55; ventana de dos D314)" << std::endl;
    std::cout << "═══════════════════════════════════════════" << std::endl;
    test_generate_and_get();
    test_rotation_grace_period();
    test_grace_period_expiry();
    test_config_values();
    test_cooldown();
    std::cout << GREEN << "✅ Todas las pruebas básicas pasan" << RESET << std::endl;
    return 0;
}
