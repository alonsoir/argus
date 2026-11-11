//===----------------------------------------------------------------------===//
// ML Defender - Firewall ACL Agent
// iptables_wrapper.hpp - iptables Management
//
// Design Decision: Use system iptables commands instead of libiptc API
// Rationale:
//   - Simple, maintainable, auditable (same as ipset_wrapper)
//   - iptables CLI is stable and well-tested
//   - Automatic benefits from iptables version upgrades
//   - No libiptc dependency
//
// Performance: iptables-restore for batch operations
// Philosophy: "Don't reinvent the wheel" - Via Appia Quality
//===----------------------------------------------------------------------===//

#pragma once

#include <string>
#include <vector>
#include <optional>
#include <mutex>
#include <memory>

namespace mldefender::firewall {

//===----------------------------------------------------------------------===//
// Forward Declarations
//===----------------------------------------------------------------------===//

struct IPTablesError;
template<typename T> struct IPTablesResult;

//===----------------------------------------------------------------------===//
// Types and Enumerations
//===----------------------------------------------------------------------===//

/// iptables table type
enum class IPTablesTable {
    FILTER,   ///< Standard filtering (INPUT, FORWARD, OUTPUT)
    NAT,      ///< Network Address Translation
    MANGLE,   ///< Packet alteration
    RAW,      ///< Connection tracking bypass
};

/// iptables built-in chains
enum class IPTablesChain {
    INPUT,        ///< Incoming packets
    FORWARD,      ///< Forwarded packets
    OUTPUT,       ///< Outgoing packets
    PREROUTING,   ///< Before routing decision
    POSTROUTING,  ///< After routing decision
    CUSTOM,       ///< Custom chain (use custom_chain_name)
};

/// iptables target actions
enum class IPTablesTarget {
    ACCEPT,  ///< Accept packet
    DROP,    ///< Drop packet silently
    REJECT,  ///< Reject packet with ICMP
    RETURN,  ///< Return to calling chain
    JUMP,    ///< Jump to custom chain
};

/// Network protocol
enum class IPTablesProtocol {
    TCP,   ///< TCP protocol
    UDP,   ///< UDP protocol
    ICMP,  ///< ICMP protocol
    ALL,   ///< All protocols
};

/// Error codes
enum class IPTablesErrorCode {
    SUCCESS = 0,
    CHAIN_ALREADY_EXISTS,
    CHAIN_NOT_FOUND,
    KERNEL_ERROR,
    INVALID_RULE,
};

/// Error information
struct IPTablesError {
    IPTablesErrorCode code;
    std::string message;
};

/// Result type (C++20 compatible - no std::expected)
template<typename T>
struct IPTablesResult {
    std::optional<T> value;
    std::optional<IPTablesError> error;

    // Success constructor
    IPTablesResult() : value(T{}), error(std::nullopt) {}
    explicit IPTablesResult(T val) : value(std::move(val)), error(std::nullopt) {}

    // Error constructor
    explicit IPTablesResult(IPTablesError err) : value(std::nullopt), error(std::move(err)) {}

    // Check if successful
    explicit operator bool() const { return value.has_value(); }
    bool has_value() const { return value.has_value(); }
    bool has_error() const { return error.has_value(); }

    // Access value (undefined if error)
    T& operator*() { return *value; }
    const T& operator*() const { return *value; }
    T* operator->() { return &(*value); }
    const T* operator->() const { return &(*value); }

    // Access error
    const IPTablesError& get_error() const { return *error; }
};

// Specialization for void
template<>
struct IPTablesResult<void> {
    std::optional<IPTablesError> error;

    // Success constructor
    IPTablesResult() : error(std::nullopt) {}

    // Error constructor
    explicit IPTablesResult(IPTablesError err) : error(std::move(err)) {}

    // Check if successful
    explicit operator bool() const { return !error.has_value(); }
    bool has_value() const { return !error.has_value(); }
    bool has_error() const { return error.has_value(); }

    // Access error
    const IPTablesError& get_error() const { return *error; }
};

//===----------------------------------------------------------------------===//
// Configuration Structures
//===----------------------------------------------------------------------===//

/// iptables rule specification
struct IPTablesRule {
    // Table and chain
    IPTablesTable table{IPTablesTable::FILTER};
    IPTablesChain chain{IPTablesChain::INPUT};
    std::string custom_chain_name{};  // For custom chains

    // Rule position (0 = append, >0 = insert at position)
    uint32_t position{0};

    // Match criteria
    IPTablesProtocol protocol{IPTablesProtocol::ALL};
    std::string source{};          // Source IP/CIDR
    std::string destination{};     // Destination IP/CIDR
    std::string in_interface{};    // Input interface (eth0, etc)
    std::string out_interface{};   // Output interface
    uint16_t source_port{0};       // Source port
    uint16_t dest_port{0};         // Destination port

    // Match extensions
    std::string match_set{};           // ipset name for -m set
    std::string match_extensions{};    // Additional match criteria

    // Target
    IPTablesTarget target{IPTablesTarget::DROP};
    std::string jump_target{};         // For JUMP target
    std::string target_options{};      // Additional target options

    // Metadata
    std::string comment{};
};

/// Firewall configuration
struct FirewallConfig {
    std::string blacklist_chain{"ML_DEFENDER_BLACKLIST"};
    std::string whitelist_chain{"ML_DEFENDER_WHITELIST"};
    std::string ratelimit_chain{"ML_DEFENDER_RATELIMIT"};

    std::string blacklist_ipset{"ml_defender_blacklist"};
    // [PROTEGIDOS-MANIFIESTO-D318] set hash:net,iface de protegidos (ADR-060); vacío = sin regla de exención
    std::string protegidos_ipset{};

    bool enable_rate_limiting{true};
    uint32_t rate_limit_connections{100};  // Connections per 60 seconds
};

//===----------------------------------------------------------------------===//
// IPTables Wrapper Class
//===----------------------------------------------------------------------===//

/// Thread-safe wrapper for iptables operations
class IPTablesWrapper {
public:
    IPTablesWrapper();
    ~IPTablesWrapper();

    // Non-copyable
    IPTablesWrapper(const IPTablesWrapper&) = delete;
    IPTablesWrapper& operator=(const IPTablesWrapper&) = delete;

    //===------------------------------------------------------------------===//
    // Chain Management
    //===------------------------------------------------------------------===//

    /// Create a new custom chain
    IPTablesResult<void> create_chain(
        const std::string& chain_name,
        IPTablesTable table = IPTablesTable::FILTER
    );

    /// Delete a custom chain (must be empty)
    IPTablesResult<void> delete_chain(
        const std::string& chain_name,
        IPTablesTable table = IPTablesTable::FILTER
    );

    /// Check if chain exists
    bool chain_exists(
        const std::string& chain_name,
        IPTablesTable table = IPTablesTable::FILTER
    ) const;

    /// Flush all rules from a chain
    IPTablesResult<void> flush_chain(
        const std::string& chain_name,
        IPTablesTable table = IPTablesTable::FILTER
    );
    //===------------------------------------------------------------------===//
    // Dry-Run Mode
    //===------------------------------------------------------------------===//

    /// Enable/disable dry-run mode (no actual commands executed)
    void set_dry_run(bool enabled) { m_dry_run = enabled; }
    
    /// Check if dry-run mode is enabled
    bool is_dry_run() const { return m_dry_run; }


    /// List all chains in a table
    std::vector<std::string> list_chains(
        IPTablesTable table = IPTablesTable::FILTER
    ) const;

    //===------------------------------------------------------------------===//
    // Rule Management
    //===------------------------------------------------------------------===//

    /// Add a rule to a chain
    IPTablesResult<void> add_rule(const IPTablesRule& rule);

    /// Delete a rule by position
    IPTablesResult<void> delete_rule(
        const std::string& chain_name,
        int position,
        IPTablesTable table = IPTablesTable::FILTER
    );

    /// List all rules in a chain
    std::vector<std::string> list_rules(
        const std::string& chain_name,
        IPTablesTable table = IPTablesTable::FILTER
    ) const;

    //===------------------------------------------------------------------===//
    // High-Level Setup
    //===------------------------------------------------------------------===//

    /// Setup base firewall rules for ML Defender
    /// Creates chains and links them to INPUT with ipset matches
    IPTablesResult<void> setup_base_rules(const FirewallConfig& config);

    /// [PROTEGIDOS-ANTISPOOF-D320] ADR-060 8e.4b: carga 'contenido' (formato iptables-save, una o más tablas) con
    /// 'iptables-restore -w --noflush': cada tabla en una sola transacción; las cadenas declaradas (":C - [0:0]") se
    /// vacían y se rellenan, las demás no se tocan. En dry_run solo imprime.
    IPTablesResult<void> restaurar_sin_vaciar(const std::string& contenido);

    /// [PROTEGIDOS-ANTISPOOF-D320] un único salto 'base -> destino' en la posición 1 de la tabla (retira los anteriores).
    IPTablesResult<void> salto_en_primera(IPTablesTable tabla, const std::string& base, const std::string& destino);

    /// [PROTEGIDOS-ANTISPOOF-D320] contador de paquetes de cada regla de una cadena, en orden ('iptables -L -v -x -n').
    /// Vacío si la cadena no existe o no se pudo leer.
    std::vector<uint64_t> contadores(const std::string& chain_name, IPTablesTable tabla) const;

    /// [PROTEGIDOS-ANTISPOOF-D320] H-D: interfaz por la que el kernel enruta hacia una IPv4 ('ip -o route get', sin
    /// shell). "" si la IP no es una IPv4 o no hay ruta.
    static std::string interfaz_de_ruta(const std::string& ipv4);

    /// Cleanup all ML Defender rules
    IPTablesResult<void> cleanup_rules(const FirewallConfig& config);

    //===------------------------------------------------------------------===//
    // Save/Restore
    //===------------------------------------------------------------------===//

    /// Save current iptables rules to file
    IPTablesResult<void> save(const std::string& filepath) const;

    /// Restore iptables rules from file
    IPTablesResult<void> restore(const std::string& filepath);

    //===------------------------------------------------------------------===//
    // Helper Methods
    //===------------------------------------------------------------------===//

    static const char* table_to_string(IPTablesTable table);
    static const char* chain_to_string(IPTablesChain chain);
    static const char* target_to_string(IPTablesTarget target);
    static const char* protocol_to_string(IPTablesProtocol proto);

private:
    //===------------------------------------------------------------------===//
    // Internal State
    //===------------------------------------------------------------------===//

    struct Impl;
    std::unique_ptr<Impl> impl_;
    mutable std::mutex mutex_;  ///< Thread-safety
    bool m_dry_run = false;  ///< Dry-run mode flag

    //===------------------------------------------------------------------===//
    // Internal Helpers
    //===------------------------------------------------------------------===//

    /// Internal version of chain_exists without mutex lock
    bool chain_exists_unlocked(
        const std::string& chain_name,
        IPTablesTable table
    ) const;
};

} // namespace mldefender::firewall