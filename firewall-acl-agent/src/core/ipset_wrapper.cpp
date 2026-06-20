//===----------------------------------------------------------------------===//
// ML Defender - Firewall ACL Agent
// ipset_wrapper.cpp - System Commands Implementation
//
// Design Decision: Use system ipset commands instead of C API
// Rationale:
//   - ipset CLI commands are professionally optimized
//   - Automatic benefits from ipset version upgrades
//   - Simple, maintainable, auditable
//   - Batch operations (ipset restore) are equally fast
//   - "Don't reinvent the wheel" - Via Appia Quality
//
// Performance: ipset restore is THE optimal way for batch operations
//===----------------------------------------------------------------------===//

#include "firewall/ipset_wrapper.hpp"
#include "firewall/set_name_validator.hpp"
#include "firewall/ip_cidr_validator.hpp"
#include "safe_exec.hpp"
#include <cstring>
#include <cctype>
#include <sstream>
#include <fstream>
#include <regex>
#include <arpa/inet.h>
#include <iostream>
#include <sys/socket.h>
#include <unistd.h>

namespace mldefender::firewall {

//===----------------------------------------------------------------------===//
// PIMPL Implementation - Minimal (no libipset needed)
//===----------------------------------------------------------------------===//

struct IPSetWrapper::Impl {
    // No state needed - all operations via system commands
    Impl() = default;
    ~Impl() = default;
};

//===----------------------------------------------------------------------===//
// Constructor / Destructor
//===----------------------------------------------------------------------===//

IPSetWrapper::IPSetWrapper()
    : impl_(std::make_unique<Impl>()) {
}

IPSetWrapper::~IPSetWrapper() = default;

//===----------------------------------------------------------------------===//
// Helper Functions
//===----------------------------------------------------------------------===//

// H-2 DAY189: ipset vive en /sbin (no en PATH de usuario). execv NO usa PATH → ruta absoluta.
static constexpr const char* kIpsetBin = "/sbin/ipset";

const char* IPSetWrapper::type_to_string(IPSetType type) {
    switch (type) {
        case IPSetType::HASH_IP:      return "hash:ip";
        case IPSetType::HASH_NET:     return "hash:net";
        case IPSetType::HASH_IP_PORT: return "hash:ip,port";
    }
    return "hash:ip";
}

const char* IPSetWrapper::family_to_string(IPSetFamily family) {
    switch (family) {
        case IPSetFamily::INET:  return "inet";
        case IPSetFamily::INET6: return "inet6";
    }
    return "inet";
}

// [H-2 DAY188 is_valid_ip hardened] — lógica MOVIDA a firewall/ip_cidr_validator.hpp
// (DAY190, DEBT-AUTONOMY-REACTOR-CWE78-001). Este método es ahora un alias de
// compatibilidad de la API pública; la implementación y su modelo de amenaza viven
// en el header compartido. NO BORRAR este marcador (idempotencia del parche).
bool IPSetWrapper::is_valid_ip(const std::string& ip) const { return is_valid_ip_cidr(ip); }

//===----------------------------------------------------------------------===//
// System Command Execution
//===----------------------------------------------------------------------===//

// execute_command ELIMINADA (H-2 DAY189): toda ejecución pasa por safe_exec* (sin shell).

//===----------------------------------------------------------------------===//
// Set Management
//===----------------------------------------------------------------------===//

IPSetResult<void> IPSetWrapper::create_set(const IPSetConfig& config) {
    std::lock_guard<std::mutex> lock(mutex_);

    // Check if set already exists (use unlocked version - we already have the lock)
    if (set_exists_unlocked(config.name)) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::SET_ALREADY_EXISTS,
            "Set '" + config.name + "' already exists"
        });
    }

    // H-2 DAY189: validar nombre antes de construir argv (sin shell).
    if (!is_valid_set_name(config.name)) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::INVALID_SET_NAME,
            "Invalid set name: '" + config.name + "'"
        });
    }

    // Build ipset create argv (token a token, NUNCA concatenado en shell).
    std::vector<std::string> args = {
        kIpsetBin, "create", config.name, type_to_string(config.type),
        "family", family_to_string(config.family),
        "hashsize", std::to_string(config.hashsize),
        "maxelem", std::to_string(config.maxelem)
    };
    if (config.timeout > 0) {
        args.push_back("timeout");
        args.push_back(std::to_string(config.timeout));
    }
    if (config.counters) {
        args.push_back("counters");
    }
    if (config.comment) {
        args.push_back("comment");
    }
    if (config.type == IPSetType::HASH_NET) {
        args.push_back("netmask");
        args.push_back(std::to_string(config.netmask));
    }

    if (m_dry_run) {
        std::cout << "[DRY-RUN] Would execute: " << kIpsetBin << " create "
                  << config.name << std::endl;
        return IPSetResult<void>(); // Success in dry-run
    }
    int ret = safe_exec(args);
    if (ret != 0) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::KERNEL_ERROR, "Failed to create set"
        });
    }
    return IPSetResult<void>();
}

IPSetResult<void> IPSetWrapper::destroy_set(const std::string& set_name) {
    std::lock_guard<std::mutex> lock(mutex_);

    if (!is_valid_set_name(set_name)) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::INVALID_SET_NAME,
            "Invalid set name: '" + set_name + "'"
        });
    }

    if (!set_exists_unlocked(set_name)) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::SET_NOT_FOUND,
            "Set '" + set_name + "' does not exist"
        });
    }

    if (m_dry_run) {
        std::cout << "[DRY-RUN] Would execute: " << kIpsetBin << " destroy "
                  << set_name << std::endl;
        return IPSetResult<void>(); // Success in dry-run
    }
    int ret = safe_exec({kIpsetBin, "destroy", set_name});
    if (ret != 0) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::KERNEL_ERROR, "Failed to destroy set"
        });
    }
    return IPSetResult<void>();
}

bool IPSetWrapper::set_exists_unlocked(const std::string& set_name) const {
    // Internal version - assumes caller already holds mutex_
    // NO lock here
    // H-2 DAY189: nombre inválido → el set no puede existir. Sin shell.
    if (!is_valid_set_name(set_name)) {
        return false;
    }
    int ret = safe_exec({kIpsetBin, "list", set_name, "-n"});
    return (ret == 0);
}

bool IPSetWrapper::set_exists(const std::string& set_name) const {
    std::lock_guard<std::mutex> lock(mutex_);
    return set_exists_unlocked(set_name);
}

std::vector<std::string> IPSetWrapper::list_sets() const {
    std::lock_guard<std::mutex> lock(mutex_);

    std::vector<std::string> sets;

    auto [ret, output] = safe_exec_with_output({kIpsetBin, "list", "-n"});
    if (ret != 0) {
        return sets;
    }

    std::istringstream iss(output);
    std::string line;
    while (std::getline(iss, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (!line.empty()) {
            sets.push_back(line);
        }
    }

    return sets;
}

IPSetResult<void> IPSetWrapper::flush_set(const std::string& set_name) {
    std::lock_guard<std::mutex> lock(mutex_);

    if (!is_valid_set_name(set_name)) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::INVALID_SET_NAME,
            "Invalid set name: '" + set_name + "'"
        });
    }

    if (!set_exists_unlocked(set_name)) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::SET_NOT_FOUND,
            "Set '" + set_name + "' does not exist"
        });
    }

    if (m_dry_run) {
        std::cout << "[DRY-RUN] Would execute: " << kIpsetBin << " flush "
                  << set_name << std::endl;
        return IPSetResult<void>(); // Success in dry-run
    }
    int ret = safe_exec({kIpsetBin, "flush", set_name});
    if (ret != 0) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::KERNEL_ERROR, "Failed to flush set"
        });
    }
    return IPSetResult<void>();
}

//===----------------------------------------------------------------------===//
// Batch Operations - THE CRITICAL HOT PATH
//===----------------------------------------------------------------------===//

IPSetResult<void> IPSetWrapper::add_batch(
    const std::string& set_name,
    const std::vector<IPSetEntry>& entries
) {
    std::lock_guard<std::mutex> lock(mutex_);

    if (entries.empty()) {
        return IPSetResult<void>();
    }

	if (!is_valid_set_name(set_name)) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::INVALID_SET_NAME,  // ¿hay un código mejor? ver nota
            "Invalid set name (rejected by allowlist): '" + set_name + "'"
        });
    }

    if (!set_exists_unlocked(set_name)) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::SET_NOT_FOUND,
            "Set '" + set_name + "' does not exist"
        });
    }

    // Validate and build restore input
    std::ostringstream restore_input;
    std::vector<std::string> failed_ips;

    for (const auto& entry : entries) {
        if (!is_valid_ip(entry.ip)) {
            failed_ips.push_back(entry.ip);
            continue;
        }

        restore_input << "add " << set_name << " " << entry.ip;

        if (entry.timeout) {
            restore_input << " timeout " << *entry.timeout;
        }

        if (entry.comment) {
            // Escape quotes in comment
            std::string safe_comment = *entry.comment;
            size_t pos = 0;
            while ((pos = safe_comment.find('"', pos)) != std::string::npos) {
                safe_comment.replace(pos, 1, "\\\"");
                pos += 2;
            }
            restore_input << " comment \"" << safe_comment << "\"";
        }

        restore_input << "\n";
    }

    if (!failed_ips.empty()) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::INVALID_IP_FORMAT,
            "Some IPs have invalid format",
            failed_ips
        });
    }

    // Write to temporary file
    const char* tmpfile = "/run/argus/irp/ipset_restore.tmp";  // DEBT-IRP-IPSET-TMP-001
    std::ofstream outfile(tmpfile);
    if (!outfile) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::KERNEL_ERROR,
            "Failed to create temporary restore file"
        });
    }
    outfile << restore_input.str();
    outfile.close();

    // Execute ipset restore (SINGLE SYSCALL for entire batch)
    if (m_dry_run) {
        std::cout << "[DRY-RUN] Would execute: " << kIpsetBin
                  << " restore < " << tmpfile << std::endl;
        return IPSetResult<void>();
    }
    int ret = safe_exec_with_file_in({kIpsetBin, "restore"}, tmpfile);
    std::remove(tmpfile);
    if (ret != 0) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::KERNEL_ERROR,
            "Batch add failed (ipset restore exit=" + std::to_string(ret) + ")"
        });
    }
    return IPSetResult<void>();
}

IPSetResult<void> IPSetWrapper::delete_batch(
    const std::string& set_name,
    const std::vector<std::string>& ips
) {
    std::lock_guard<std::mutex> lock(mutex_);

    if (ips.empty()) {
        return IPSetResult<void>();
    }

	if (!is_valid_set_name(set_name)) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::INVALID_SET_NAME,  // ¿hay un código mejor? ver nota
            "Invalid set name (rejected by allowlist): '" + set_name + "'"
        });
    }

    if (!set_exists_unlocked(set_name)) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::SET_NOT_FOUND,
            "Set '" + set_name + "' does not exist"
        });
    }

    // Build restore input for deletions
    std::ostringstream restore_input;
    std::vector<std::string> failed_ips;

    for (const auto& ip : ips) {
        if (!is_valid_ip(ip)) {
            failed_ips.push_back(ip);
            continue;
        }

        restore_input << "del " << set_name << " " << ip << "\n";
    }

    if (!failed_ips.empty()) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::INVALID_IP_FORMAT,
            "Some IPs have invalid format",
            failed_ips
        });
    }

    const char* tmpfile = "/run/argus/irp/ipset_delete.tmp";  // DEBT-IRP-IPSET-TMP-001
    std::ofstream outfile(tmpfile);
    if (!outfile) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::KERNEL_ERROR,
            "Failed to create temporary restore file"
        });
    }
    outfile << restore_input.str();
    outfile.close();

    if (m_dry_run) {
        std::cout << "[DRY-RUN] Would execute: " << kIpsetBin
                  << " restore -exist < " << tmpfile << std::endl;
        return IPSetResult<void>();
    }
    int ret = safe_exec_with_file_in({kIpsetBin, "restore", "-exist"}, tmpfile);
    std::remove(tmpfile);
    if (ret != 0) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::KERNEL_ERROR,
            "Batch delete failed (ipset restore exit=" + std::to_string(ret) + ")"
        });
    }
    return IPSetResult<void>();
}

//===----------------------------------------------------------------------===//
// Single Operations
//===----------------------------------------------------------------------===//

IPSetResult<void> IPSetWrapper::add(
    const std::string& set_name,
    const IPSetEntry& entry
) {
    return add_batch(set_name, {entry});
}

IPSetResult<void> IPSetWrapper::delete_ip(
    const std::string& set_name,
    const std::string& ip
) {
    return delete_batch(set_name, {ip});
}

bool IPSetWrapper::test(
    const std::string& set_name,
    const std::string& ip
) const {
    std::lock_guard<std::mutex> lock(mutex_);

    if (!is_valid_set_name(set_name)) {
        return false;
    }
    if (!is_valid_ip(ip)) {
        return false;
    }
    int ret = safe_exec({kIpsetBin, "test", set_name, ip});
    return (ret == 0);
}

//===----------------------------------------------------------------------===//
// Statistics and Monitoring
//===----------------------------------------------------------------------===//

uint64_t IPSetWrapper::get_entry_count(const std::string& set_name) const {
    auto stats = get_stats(set_name, false);
    if (stats.has_value()) {
        return stats->entry_count;
    }
    return 0;
}

IPSetResult<IPSetStats> IPSetWrapper::get_stats(
    const std::string& set_name,
    bool include_entries
) const {
    std::lock_guard<std::mutex> lock(mutex_);

    if (!set_exists_unlocked(set_name)) {
        return IPSetResult<IPSetStats>(IPSetError{
            IPSetErrorCode::SET_NOT_FOUND,
            "Set '" + set_name + "' does not exist"
        });
    }

    IPSetStats stats;
    stats.name = set_name;

    // Get stats via ipset list (sin shell). set_name ya validado por set_exists_unlocked arriba.
    auto [ret, output] = safe_exec_with_output({kIpsetBin, "list", set_name});

    if (ret != 0) {
        return IPSetResult<IPSetStats>(IPSetError{
            IPSetErrorCode::KERNEL_ERROR, "Failed to get stats"
        });
    }

    // Parse output
    std::istringstream iss(output);
    std::string line;
    while (std::getline(iss, line)) {
        if (line.find("Number of entries:") != std::string::npos) {
            std::istringstream line_ss(line);
            std::string dummy;
            line_ss >> dummy >> dummy >> dummy >> stats.entry_count;
        } else if (line.find("References:") != std::string::npos) {
            std::istringstream line_ss(line);
            std::string dummy;
            line_ss >> dummy >> stats.references;
        } else if (line.find("Size in memory:") != std::string::npos) {
            std::istringstream line_ss(line);
            std::string dummy;
            line_ss >> dummy >> dummy >> dummy >> stats.size_in_memory;
        }
    }

    if (include_entries) {
        // TODO: Parse individual entries if needed
        // For now, entries vector remains empty
    }

    return IPSetResult<IPSetStats>(stats);
}

std::vector<std::string> IPSetWrapper::list_entries(
    const std::string& set_name
) const {
    std::lock_guard<std::mutex> lock(mutex_);

    std::vector<std::string> entries;

    // H-2 DAY189: validar nombre antes de pasarlo a ipset (sin shell, grep → C++).
    if (!is_valid_set_name(set_name)) {
        return entries;
    }

    auto [ret, output] = safe_exec_with_output({kIpsetBin, "save", set_name});
    if (ret != 0) {
        return entries;
    }

    std::istringstream iss(output);
    std::string line;
    while (std::getline(iss, line)) {
        // Filtro equivalente al antiguo '| grep ^add', ahora en C++.
        if (line.rfind("add ", 0) != 0) {
            continue;
        }
        std::istringstream line_ss(line);
        std::string cmd_word, setname, ip;
        line_ss >> cmd_word >> setname >> ip;
        if (!ip.empty()) {
            entries.push_back(ip);
        }
    }

    return entries;
}

//===----------------------------------------------------------------------===//
// Advanced Operations
//===----------------------------------------------------------------------===//

IPSetResult<void> IPSetWrapper::rename_set(
    const std::string& old_name,
    const std::string& new_name
) {
    std::lock_guard<std::mutex> lock(mutex_);

    if (!is_valid_set_name(old_name) || !is_valid_set_name(new_name)) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::INVALID_SET_NAME,
            "Invalid set name in rename"
        });
    }

    if (m_dry_run) {
        std::cout << "[DRY-RUN] Would execute: " << kIpsetBin << " rename "
                  << old_name << " " << new_name << std::endl;
        return IPSetResult<void>(); // Success in dry-run
    }
    int ret = safe_exec({kIpsetBin, "rename", old_name, new_name});
    if (ret != 0) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::KERNEL_ERROR, "Failed to rename set"
        });
    }
    return IPSetResult<void>();
}

IPSetResult<void> IPSetWrapper::swap_sets(
    const std::string& set1,
    const std::string& set2
) {
    std::lock_guard<std::mutex> lock(mutex_);

    if (!is_valid_set_name(set1) || !is_valid_set_name(set2)) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::INVALID_SET_NAME,
            "Invalid set name in swap"
        });
    }

    if (m_dry_run) {
        std::cout << "[DRY-RUN] Would execute: " << kIpsetBin << " swap "
                  << set1 << " " << set2 << std::endl;
        return IPSetResult<void>(); // Success in dry-run
    }
    int ret = safe_exec({kIpsetBin, "swap", set1, set2});
    if (ret != 0) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::KERNEL_ERROR, "Failed to swap sets"
        });
    }
    return IPSetResult<void>();
}

IPSetResult<void> IPSetWrapper::save(const std::string& filepath) const {
    std::lock_guard<std::mutex> lock(mutex_);

    if (!validate_filepath(filepath)) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::KERNEL_ERROR,
            "Invalid filepath for save"
        });
    }
    if (m_dry_run) {
        std::cout << "[DRY-RUN] Would execute: " << kIpsetBin << " save > "
                  << filepath << std::endl;
        return IPSetResult<void>(); // Success in dry-run
    }
    int ret = safe_exec_with_file_out({kIpsetBin, "save"}, filepath);
    if (ret != 0) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::KERNEL_ERROR, "Failed to save ipsets"
        });
    }
    return IPSetResult<void>();
}

IPSetResult<void> IPSetWrapper::restore(const std::string& filepath) {
    std::lock_guard<std::mutex> lock(mutex_);

    if (!validate_filepath(filepath)) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::KERNEL_ERROR,
            "Invalid filepath for restore"
        });
    }
    if (m_dry_run) {
        std::cout << "[DRY-RUN] Would execute: " << kIpsetBin << " restore < "
                  << filepath << std::endl;
        return IPSetResult<void>(); // Success in dry-run
    }
    int ret = safe_exec_with_file_in({kIpsetBin, "restore"}, filepath);
    if (ret != 0) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::KERNEL_ERROR, "Failed to restore ipsets"
        });
    }
    return IPSetResult<void>();
}

} // namespace mldefender::firewall