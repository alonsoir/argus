// test_vault_provider.cpp — 6 tests RED->GREEN para vault_crypto plugin
// TDH: cada test es independiente, falla rapido, mensaje claro.
// Vault dev mode debe estar corriendo en 127.0.0.1:8200 con token argus-dev-token.

#include "vault_provider.hpp"
#include <argus/ICryptoProvider.hpp>
#include <dlfcn.h>
#include <cassert>
#include <iostream>
#include <stdexcept>

#define RED   "\033[31m"
#define GREEN "\033[32m"
#define RESET "\033[0m"

static int passed = 0;
static int failed = 0;

#define TEST(name, body) \
    do { \
        std::cout << "  TEST: " << name << " ... "; \
        try { body; \
            std::cout << GREEN << "PASSED" << RESET << "\n"; \
            ++passed; \
        } catch (const std::exception& e) { \
            std::cout << RED << "FAILED: " << e.what() << RESET << "\n"; \
            ++failed; \
        } \
    } while(0)

#define EXPECT_THROW(expr, msg) \
    do { \
        bool threw = false; \
        try { (void)(expr); } catch (...) { threw = true; } \
        if (!threw) throw std::runtime_error(msg); \
    } while(0)

#define EXPECT_TRUE(expr, msg) \
    do { if (!(expr)) throw std::runtime_error(msg); } while(0)

#define EXPECT_EQ(a, b, msg) \
    do { if ((a) != (b)) throw std::runtime_error(msg); } while(0)

// T1: config vacia -> constructor lanza
void t1_empty_config() {
    argus::enterprise::VaultProvider::Config cfg;
    cfg.vault_addr  = "";
    cfg.vault_token = "argus-dev-token";
    cfg.secret_path = "secret/data/argus/crypto";
    EXPECT_THROW(
        argus::enterprise::VaultProvider(cfg),
        "Config vacia deberia lanzar runtime_error"
    );
}

// T2: token invalido -> get_seed() lanza (403)
void t2_invalid_token() {
    argus::enterprise::VaultProvider::Config cfg;
    cfg.vault_addr      = "http://127.0.0.1:8200";
    cfg.vault_token     = "token-invalido-xyz";
    cfg.secret_path     = "secret/data/argus/crypto";
    cfg.timeout_seconds = 5;
    argus::enterprise::VaultProvider vp(std::move(cfg));
    EXPECT_THROW(vp.get_seed(), "Token invalido deberia lanzar runtime_error");
}

// T3: secreto inexistente -> get_seed() lanza (404)
void t3_missing_secret() {
    argus::enterprise::VaultProvider::Config cfg;
    cfg.vault_addr      = "http://127.0.0.1:8200";
    cfg.vault_token     = "argus-dev-token";
    cfg.secret_path     = "secret/data/argus/no-existe-xyz";
    cfg.timeout_seconds = 5;
    argus::enterprise::VaultProvider vp(std::move(cfg));
    EXPECT_THROW(vp.get_seed(), "Secreto inexistente deberia lanzar runtime_error");
}

// T4: Vault inalcanzable -> get_seed() lanza (curl error)
void t4_vault_unreachable() {
    argus::enterprise::VaultProvider::Config cfg;
    cfg.vault_addr      = "http://127.0.0.1:19999";
    cfg.vault_token     = "argus-dev-token";
    cfg.secret_path     = "secret/data/argus/crypto";
    cfg.timeout_seconds = 2;
    argus::enterprise::VaultProvider vp(std::move(cfg));
    EXPECT_THROW(vp.get_seed(), "Vault inalcanzable deberia lanzar runtime_error");
}

// T5: token valido + secreto correcto -> 32 bytes
void t5_valid_seed() {
    argus::enterprise::VaultProvider::Config cfg;
    cfg.vault_addr      = "http://127.0.0.1:8200";
    cfg.vault_token     = "argus-dev-token";
    cfg.secret_path     = "secret/data/argus/crypto";
    cfg.seed_field      = "seed";
    cfg.timeout_seconds = 5;
    argus::enterprise::VaultProvider vp(std::move(cfg));

    auto seed = vp.get_seed();
    EXPECT_EQ(seed.size(), size_t(32), "seed debe ser exactamente 32 bytes");
    bool all_zero = true;
    for (auto b : seed) if (b != 0) { all_zero = false; break; }
    EXPECT_TRUE(!all_zero, "seed no debe ser todo ceros");
}

// T6: C ABI via dlopen — create / get_seed / destroy
void t6_c_abi_dlopen() {
    const char* so_path = "/vagrant/enterprise/plugins/vault_crypto/build/libvault_provider.so";
    void* handle = dlopen(so_path, RTLD_LAZY | RTLD_LOCAL);
    EXPECT_TRUE(handle != nullptr,
        std::string("dlopen fallo: ") + (dlerror() ? dlerror() : "unknown"));

    using CreateFn  = argus::ICryptoProvider*(*)(const char*);
    using DestroyFn = void(*)(argus::ICryptoProvider*);

    auto create  = reinterpret_cast<CreateFn> (dlsym(handle, "argus_enterprise_create"));
    auto destroy = reinterpret_cast<DestroyFn>(dlsym(handle, "argus_enterprise_destroy"));

    EXPECT_TRUE(create  != nullptr, "simbolo argus_enterprise_create no encontrado");
    EXPECT_TRUE(destroy != nullptr, "simbolo argus_enterprise_destroy no encontrado");

    const char* cfg_json =
        "{\"vault_addr\":\"http://127.0.0.1:8200\","
        "\"vault_token\":\"argus-dev-token\","
        "\"secret_path\":\"secret/data/argus/crypto\","
        "\"seed_field\":\"seed\"}";

    argus::ICryptoProvider* provider = create(cfg_json);
    EXPECT_TRUE(provider != nullptr, "argus_enterprise_create devolvio nullptr");

    EXPECT_EQ(provider->provider_name(), std::string("vault_crypto"),
        "provider_name() debe ser vault_crypto");

    auto seed = provider->get_seed();
    EXPECT_EQ(seed.size(), size_t(32), "C ABI: seed debe ser 32 bytes");

    EXPECT_TRUE(provider->is_healthy(), "is_healthy() debe ser true con Vault activo");

    destroy(provider);
    dlclose(handle);
}

int main() {
    std::cout << "\n=== test_vault_provider — aRGus NDR DAY 160 ===\n\n";

    TEST("T1 config-vacia-lanza",          t1_empty_config());
    TEST("T2 token-invalido-403",          t2_invalid_token());
    TEST("T3 secreto-inexistente-404",     t3_missing_secret());
    TEST("T4 vault-inalcanzable-curl",     t4_vault_unreachable());
    TEST("T5 seed-valido-32bytes",         t5_valid_seed());
    TEST("T6 c-abi-dlopen-create-destroy", t6_c_abi_dlopen());

    std::cout << "\n--- Resultado: "
              << GREEN << passed << " PASSED" << RESET << " / "
              << (failed ? RED : GREEN) << failed << " FAILED" << RESET
              << " ---\n\n";

    return failed == 0 ? 0 : 1;
}