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

bool IPSetWrapper::is_valid_ip(const std::string& ip) const {
    // [H-2 DAY188 is_valid_ip hardened] — NO BORRAR este marcador (idempotencia del parche).
    // La entrada cruda alimenta un fichero 'ipset restore' (mini-lenguaje por lineas):
    // un '\n' inyecta una linea add/del nueva. El bypass historico validaba SOLO el trozo
    // pre-'/' y aprobaba el todo (p.ej. "1.2.3.4/24\nadd evil 6.6.6.6"). Defensa: allowlist
    // estricto de caracteres ANTES de descomponer + prefijo CIDR numerico y en rango.
    if (ip.empty() || ip.size() > 64) {  // IPv6 textual ~45; /128 ~49; 64 holgado
        return false;
    }

    // Allowlist: solo el alfabeto de una IP/CIDR. Excluye \n \r \t espacio ; $ ` | & ( ) etc.
    for (unsigned char c : ip) {
        const bool ok = std::isxdigit(c) || c == '.' || c == ':' || c == '/';
        if (!ok) {
            return false;
        }
    }

    // A lo sumo un '/'.
    const auto slash = ip.find('/');
    if (slash != std::string::npos &&
        ip.find('/', slash + 1) != std::string::npos) {
        return false;
    }
    const std::string ip_part = (slash == std::string::npos) ? ip : ip.substr(0, slash);

    // La direccion debe ser IPv4 o IPv6 textual valida.
    struct sockaddr_in  sa4;
    struct sockaddr_in6 sa6;
    const bool is_v4 = inet_pton(AF_INET,  ip_part.c_str(), &sa4.sin_addr)  == 1;
    const bool is_v6 = inet_pton(AF_INET6, ip_part.c_str(), &sa6.sin6_addr) == 1;
    if (!is_v4 && !is_v6) {
        return false;
    }

    // Prefijo CIDR: 1-3 digitos numericos, en rango [0, 32|128]. Sin excepciones.
    if (slash != std::string::npos) {
        const std::string prefix = ip.substr(slash + 1);
        if (prefix.empty() || prefix.size() > 3) {
            return false;
        }
        int bits = 0;
        for (unsigned char c : prefix) {
            if (!std::isdigit(c)) {
                return false;
            }
            bits = bits * 10 + (c - '0');
        }
        const int max_bits = is_v6 ? 128 : 32;
        if (bits > max_bits) {
            return false;
        }
    }

    return true;
}

//===----------------------------------------------------------------------===//
// System Command Execution
//===----------------------------------------------------------------------===//

static std::pair<int, std::string> execute_command(const std::string& cmd) {
    FILE* pipe = popen(cmd.c_str(), "r");
    if (!pipe) {
        return {-1, "Failed to execute command"};
    }

    char buffer[512];
    std::string result;
    while (fgets(buffer, sizeof(buffer), pipe)) {
        result += buffer;
    }

    int ret = pclose(pipe);
    return {ret, result};
}

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

    // Build ipset create command
    std::ostringstream cmd;
    cmd << "ipset create " << config.name << " " << type_to_string(config.type)
        << " family " << family_to_string(config.family)
        << " hashsize " << config.hashsize
        << " maxelem " << config.maxelem;

    if (config.timeout > 0) {
        cmd << " timeout " << config.timeout;
    }

    if (config.counters) {
        cmd << " counters";
    }

    if (config.comment) {
        cmd << " comment";
    }

    if (config.type == IPSetType::HASH_NET) {
        cmd << " netmask " << config.netmask;
    }

    cmd << " 2>&1";

    if (m_dry_run) {
        std::cout << "[DRY-RUN] Would execute: " << cmd.str() << std::endl;
        return IPSetResult<void>(); // Success in dry-run
    }
    auto [ret, output] = execute_command(cmd.str());

    if (ret != 0) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::KERNEL_ERROR,
            "Failed to create set: " + output
        });
    }

    return IPSetResult<void>();
}

IPSetResult<void> IPSetWrapper::destroy_set(const std::string& set_name) {
    std::lock_guard<std::mutex> lock(mutex_);

    if (!set_exists_unlocked(set_name)) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::SET_NOT_FOUND,
            "Set '" + set_name + "' does not exist"
        });
    }

    std::string cmd = "ipset destroy " + set_name + " 2>&1";
    if (m_dry_run) {
        std::cout << "[DRY-RUN] Would execute: " << cmd << std::endl;
        return IPSetResult<void>(); // Success in dry-run
    }
    auto [ret, output] = execute_command(cmd);

    if (ret != 0) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::KERNEL_ERROR,
            "Failed to destroy set: " + output
        });
    }

    return IPSetResult<void>();
}

bool IPSetWrapper::set_exists_unlocked(const std::string& set_name) const {
    // Internal version - assumes caller already holds mutex_
    // NO lock here
    std::string cmd = "ipset list " + set_name + " -n > /dev/null 2>&1";
    int ret = system(cmd.c_str());
    return (ret == 0);
}

bool IPSetWrapper::set_exists(const std::string& set_name) const {
    std::lock_guard<std::mutex> lock(mutex_);
    return set_exists_unlocked(set_name);
}

std::vector<std::string> IPSetWrapper::list_sets() const {
    std::lock_guard<std::mutex> lock(mutex_);

    std::vector<std::string> sets;

    FILE* pipe = popen("ipset list -n 2>/dev/null", "r");
    if (!pipe) {
        return sets;
    }

    char buffer[256];
    while (fgets(buffer, sizeof(buffer), pipe)) {
        std::string line(buffer);
        // Remove trailing newline
        if (!line.empty() && line.back() == '\n') {
            line.pop_back();
        }
        if (!line.empty()) {
            sets.push_back(line);
        }
    }

    pclose(pipe);

    return sets;
}

IPSetResult<void> IPSetWrapper::flush_set(const std::string& set_name) {
    std::lock_guard<std::mutex> lock(mutex_);

    if (!set_exists_unlocked(set_name)) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::SET_NOT_FOUND,
            "Set '" + set_name + "' does not exist"
        });
    }

    std::string cmd = "ipset flush " + set_name + " 2>&1";
    if (m_dry_run) {
        std::cout << "[DRY-RUN] Would execute: " << cmd << std::endl;
        return IPSetResult<void>(); // Success in dry-run
    }
    auto [ret, output] = execute_command(cmd);

    if (ret != 0) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::KERNEL_ERROR,
            "Failed to flush set: " + output
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
    std::string cmd = "ipset restore < " + std::string(tmpfile) + " 2>&1";
    if (m_dry_run) {
        std::cout << "[DRY-RUN] Would execute: " << cmd << std::endl;
        return IPSetResult<void>(); // Success in dry-run
    }
    auto [ret, output] = execute_command(cmd);

    std::remove(tmpfile);

    if (ret != 0 && !output.empty()) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::KERNEL_ERROR,
            "Batch add failed: " + output
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

    std::string cmd = "ipset restore -exist < " + std::string(tmpfile) + " 2>&1";
    if (m_dry_run) {
        std::cout << "[DRY-RUN] Would execute: " << cmd << std::endl;
        return IPSetResult<void>(); // Success in dry-run
    }
    auto [ret, output] = execute_command(cmd);

    std::remove(tmpfile);

    if (ret != 0 && !output.empty()) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::KERNEL_ERROR,
            "Batch delete failed: " + output
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

    if (!is_valid_ip(ip)) {
        return false;
    }

    std::string cmd = "ipset test " + set_name + " " + ip + " > /dev/null 2>&1";
    int ret = system(cmd.c_str());

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

    // Get stats via ipset list
    std::string cmd = "ipset list " + set_name + " 2>&1";
    auto [ret, output] = execute_command(cmd);

    if (ret != 0) {
        return IPSetResult<IPSetStats>(IPSetError{
            IPSetErrorCode::KERNEL_ERROR,
            "Failed to get stats: " + output
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

    std::string cmd = "ipset save " + set_name + " 2>/dev/null | grep '^add'";
    FILE* pipe = popen(cmd.c_str(), "r");
    if (!pipe) {
        return entries;
    }

    char buffer[512];
    while (fgets(buffer, sizeof(buffer), pipe)) {
        std::string line(buffer);
        // Parse: "add setname ip [options]"
        std::istringstream iss(line);
        std::string cmd_word, setname, ip;
        iss >> cmd_word >> setname >> ip;
        if (!ip.empty()) {
            entries.push_back(ip);
        }
    }

    pclose(pipe);

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

    std::string cmd = "ipset rename " + old_name + " " + new_name + " 2>&1";
    if (m_dry_run) {
        std::cout << "[DRY-RUN] Would execute: " << cmd << std::endl;
        return IPSetResult<void>(); // Success in dry-run
    }
    auto [ret, output] = execute_command(cmd);

    if (ret != 0) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::KERNEL_ERROR,
            "Failed to rename set: " + output
        });
    }

    return IPSetResult<void>();
}

IPSetResult<void> IPSetWrapper::swap_sets(
    const std::string& set1,
    const std::string& set2
) {
    std::lock_guard<std::mutex> lock(mutex_);

    std::string cmd = "ipset swap " + set1 + " " + set2 + " 2>&1";
    if (m_dry_run) {
        std::cout << "[DRY-RUN] Would execute: " << cmd << std::endl;
        return IPSetResult<void>(); // Success in dry-run
    }
    auto [ret, output] = execute_command(cmd);

    if (ret != 0) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::KERNEL_ERROR,
            "Failed to swap sets: " + output
        });
    }

    return IPSetResult<void>();
}

IPSetResult<void> IPSetWrapper::save(const std::string& filepath) const {
    std::lock_guard<std::mutex> lock(mutex_);

    std::string cmd = "ipset save > " + filepath + " 2>&1";
    if (m_dry_run) {
        std::cout << "[DRY-RUN] Would execute: " << cmd << std::endl;
        return IPSetResult<void>(); // Success in dry-run
    }
    auto [ret, output] = execute_command(cmd);

    if (ret != 0) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::KERNEL_ERROR,
            "Failed to save ipsets: " + output
        });
    }

    return IPSetResult<void>();
}

IPSetResult<void> IPSetWrapper::restore(const std::string& filepath) {
    std::lock_guard<std::mutex> lock(mutex_);

    std::string cmd = "ipset restore < " + filepath + " 2>&1";
    if (m_dry_run) {
        std::cout << "[DRY-RUN] Would execute: " << cmd << std::endl;
        return IPSetResult<void>(); // Success in dry-run
    }
    auto [ret, output] = execute_command(cmd);

    if (ret != 0) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::KERNEL_ERROR,
            "Failed to restore ipsets: " + output
        });
    }

    return IPSetResult<void>();
}

} // namespace mldefender::firewall