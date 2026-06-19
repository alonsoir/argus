// set_name_validator.hpp
// H-2: validación única de nombres de ipset set, compartida por config_loader
// (frontera de carga) e ipset_wrapper (frontera de ejecución). Una allowlist,
// dos fronteras — evita divergencia DRY.
#pragma once
#include <string>
#include <linux/netfilter/ipset/ip_set.h>  // IPSET_MAXNAMELEN

namespace mldefender::firewall {

    /// Devuelve true si `name` es un nombre de ipset set seguro y válido.
    /// Allowlist: [A-Za-z0-9_-], longitud 1..IPSET_MAXNAMELEN-1 (31), y
    /// RECHAZA '-' inicial (CWE-88 argument injection: "-X" se interpretaría
    /// como flag de ipset). El allowlist ya excluye control chars como '\n'
    /// por construcción (un newline no es alnum/'_'/'-').
    inline bool is_valid_set_name(const std::string& name) {
        if (name.empty() || name.size() >= IPSET_MAXNAMELEN) {
            return false;
        }
        if (name.front() == '-') {  // CWE-88: argument injection
            return false;
        }
        for (unsigned char c : name) {
            if (!(std::isalnum(c) || c == '_' || c == '-')) {
                return false;
            }
        }
        return true;
    }

}  // namespace mldefender::firewall
