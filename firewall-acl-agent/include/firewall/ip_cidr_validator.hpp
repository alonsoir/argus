// ip_cidr_validator.hpp
// H-2 / DEBT-AUTONOMY-REACTOR-CWE78-001: validación única de IP/CIDR, compartida
// por ipset_wrapper (frontera ipset restore) y config_loader (frontera de carga:
// autonomy.whitelist_cidrs → system("iptables ... -s <cidr>")). Una allowlist,
// dos fronteras — mismo patrón que set_name_validator.hpp (evita divergencia DRY).
#pragma once
#include <string>
#include <cctype>
#include <arpa/inet.h>
#include <sys/socket.h>

namespace mldefender::firewall {

    /// SEGURIDAD: allowlist estricto [0-9a-fA-F.:/] ANTES de descomponer — excluye
    /// \n \r \t espacio ; $ ` | & ( ) y todo metacarácter de shell (cierra CWE-78
    /// al interpolar en system()/restore).
    /// ESTRUCTURAL (no de seguridad): dirección válida vía inet_pton + prefijo CIDR
    /// numérico en rango [0, 32|128].
    inline bool is_valid_ip_cidr(const std::string& ip) {
        if (ip.empty() || ip.size() > 64) return false;
        for (unsigned char c : ip)
            if (!(std::isxdigit(c) || c == '.' || c == ':' || c == '/')) return false;

        const auto slash = ip.find('/');
        if (slash != std::string::npos &&
            ip.find('/', slash + 1) != std::string::npos) return false;
        const std::string ip_part = (slash == std::string::npos) ? ip : ip.substr(0, slash);

        struct sockaddr_in  sa4;
        struct sockaddr_in6 sa6;
        const bool is_v4 = inet_pton(AF_INET,  ip_part.c_str(), &sa4.sin_addr)  == 1;
        const bool is_v6 = inet_pton(AF_INET6, ip_part.c_str(), &sa6.sin6_addr) == 1;
        if (!is_v4 && !is_v6) return false;

        if (slash != std::string::npos) {
            const std::string prefix = ip.substr(slash + 1);
            if (prefix.empty() || prefix.size() > 3) return false;
            int bits = 0;
            for (unsigned char c : prefix) {
                if (!std::isdigit(c)) return false;
                bits = bits * 10 + (c - '0');
            }
            if (bits > (is_v6 ? 128 : 32)) return false;
        }
        return true;
    }

}  // namespace mldefender::firewall