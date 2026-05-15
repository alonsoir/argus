#pragma once
// ============================================================================
// crypto_provider.h — ICryptoProvider abstraction (ADR-044 DAY 151)
// ============================================================================
// Interfaz abstracta que desacopla los componentes del pipeline del mecanismo
// concreto de obtención de material criptográfico (seed-client vs Vault).
//
// Regla de oro: #ifdef ARGUS_VAULT_ENABLED aparece SOLO en
//               CryptoProvider::create(). Ningún componente ve ifdefs.
//
// Implementaciones:
//   SeedFileProvider — lee de /etc/ml-defender/<component>/ via seed-client
//   VaultProvider    — obtiene de HashiCorp Vault via VaultClient (ADR-044)
//
// Uso en componentes:
//   auto provider = CryptoProvider::create(config);
//   auto material = provider->get_material();   // bloquea hasta tener material
//   if (!provider->is_healthy()) { /* autonomy logic */ }
//
// Migración por canal (DAY 150):
//   sniffer + ml-detector deben migrar SIMULTÁNEAMENTE (canal A).
//   Si un extremo usa VaultProvider y el otro SeedFileProvider, los keypairs
//   serán incompatibles y el canal ZeroMQ no levantará.
//
// Referencia: ADR-044, ADR-013, ADR-025
// ============================================================================

#include "vault_client.h"  // CryptoMaterial, VaultClientConfig, et al.
#include <memory>
#include <string>
#include "crypto_autonomy.h"

namespace ml_defender {

// ── Interfaz abstracta ───────────────────────────────────────────────────────

class ICryptoProvider {
public:
    virtual ~ICryptoProvider() = default;

    // Obtiene material criptográfico.
    // Primera llamada: fetch desde la fuente (seed-client o Vault).
    // Llamadas subsiguientes: devuelve la cache interna del provider.
    // Lanza std::runtime_error si la fuente no está disponible Y no hay cache.
    virtual CryptoMaterial get_material() = 0;

    // Refresca material desde la fuente (rotación de clave, reload seed).
    // Retorna true si el refresh tuvo éxito.
    // Retorna false si la fuente no está disponible (edge autonomy: usa cache).
    virtual bool refresh() = 0;

    // true si la fuente está disponible y el material en cache es válido.
    virtual bool is_healthy() const = 0;

    // Nombre del componente para logging y registro en etcd.
    virtual std::string component_name() const = 0;

	// Modo operacional actual.
    // Default NORMAL — SeedFileProvider nunca entra en autonomy.
    // VaultProvider delega a CryptoAutonomyStateMachine.
    // DEBT-AUTONOMY-ZMQ-EVENTS-001: en el futuro emite evento ZeroMQ.
    virtual OperationalMode get_operational_mode() const noexcept {
        return OperationalMode::NORMAL;
    }
};

// ── Configuración de la factoría ─────────────────────────────────────────────

struct CryptoProviderConfig {
    // Nombre del componente: "etcd-server", "sniffer", "ml-detector", ...
    std::string component_name;

    // Ruta al directorio de claves del componente.
    // Usado por SeedFileProvider (ARGUS_VAULT_ENABLED=OFF).
    // Ejemplo: /etc/ml-defender/sniffer/
    std::string component_config_path;

    // Configuración de Vault.
    // Solo relevante cuando ARGUS_VAULT_ENABLED=ON (VaultProvider).
    // En compilación community el campo existe pero nunca se usa.
    VaultClientConfig vault_config;
};

// ── Factoría ─────────────────────────────────────────────────────────────────
// ÚNICO punto del codebase donde vive #ifdef ARGUS_VAULT_ENABLED.
// Implementación en crypto_provider.cpp.

class CryptoProvider {
public:
    // Crea el provider adecuado según el flag de compilación:
    //   ARGUS_VAULT_ENABLED=OFF → SeedFileProvider  (community)
    //   ARGUS_VAULT_ENABLED=ON  → VaultProvider     (enterprise)
    //
    // Nunca retorna nullptr.
    // Lanza std::runtime_error si la configuración es inválida o el provider
    // no puede inicializarse (Vault KO + cache vacía, seed file ausente, etc.).
    static std::unique_ptr<ICryptoProvider> create(const CryptoProviderConfig& config);

    // No instanciable.
    CryptoProvider() = delete;
};

} // namespace ml_defender