// test_protegidos_claves.cpp — [PROTEGIDOS-MANIFIESTO-D318] la clave pública compilada (CMake -> binario) es la que
// se usa: la misma que trae la definición, en las dos ranuras. Standalone, CHECK propio.
#include "firewall/protegidos_manifiesto.hpp"

#include <sodium.h>

#include <iostream>
#include <string>

using namespace mldefender::firewall;

static int g_fallos = 0;
static int g_checks = 0;
#define CHECK(c)                                                              \
    do {                                                                      \
        ++g_checks;                                                           \
        if (!(c)) {                                                           \
            std::cerr << "FALLO linea " << __LINE__ << ": " #c << std::endl;  \
            ++g_fallos;                                                       \
        }                                                                     \
    } while (0)

static std::string hex(const std::array<unsigned char, 32>& k) {
    char h[65];
    sodium_bin2hex(h, sizeof h, k.data(), k.size());
    return h;
}

int main() {
    if (sodium_init() < 0) return 2;
    const ClavesProtegidos& c = claves_protegidos_compiladas();
    CHECK(hex(c.actual) == ARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX);
    const std::string sig = ARGUS_PROTEGIDOS_PUBKEY_SIGUIENTE_HEX;
    CHECK(c.hay_siguiente == !sig.empty());
    if (c.hay_siguiente) CHECK(hex(c.siguiente) == sig);
    std::cout << "[PROTEGIDOS-CLAVE] actual huella=" << huella_clave_protegidos(c.actual)
              << (c.hay_siguiente ? " siguiente huella=" + huella_clave_protegidos(c.siguiente) : std::string(" siguiente=ninguna"))
              << std::endl;
    std::cout << "test_protegidos_claves: " << (g_checks - g_fallos) << "/" << g_checks << " OK" << std::endl;
    return g_fallos == 0 ? 0 : 1;
}
