// comment_validator.hpp
// H-2 NÚCLEO 2 (DAY191): validación del campo `comment` de ipset, escrito por
// IPSetWrapper::add_batch en un stream 'ipset restore' (mini-lenguaje por líneas).
//
// MODELO DE AMENAZA — MEDIDO sobre Debian 12 Bookworm, ipset v7.17:
//   El comment va a una línea  add <set> <ip> comment "<texto>"  . Un '\n' parte la
//   línea física; un '"' cierra el token de comment y permite reabrir un comando.
//   Combinados, el payload  x"\nadd <set> <ip>  INYECTÓ una entrada (PoC: 66.66.66.66).
//   La línea inyectada puede ser flush/destroy -> vaciar la blocklist entera. CWE-93.
//   La indulgencia del parser varía entre versiones (v7.17 abortó la comilla suelta,
//   v7.19 la aceptó) -> la defensa vive AQUÍ, en la frontera C++, NUNCA en ipset.
//
// POLÍTICA: allowlist fail-fast. NO escapar (escapar '"' no funciona: es delimitador
// del tokenizer, no un carácter embebible). Rechazar control chars, '"' y '\'.
#pragma once
#include <string>

namespace mldefender::firewall {

    /// true si `comment` es seguro para escribir en un stream 'ipset restore'.
    /// Allowlist: sin control chars (< 0x20 ni 0x7f), sin '"' ni '\\', longitud
    /// <= 255 (IPSET_MAX_COMMENT_SIZE). Bytes >= 0x80 (UTF-8) permitidos: inocuos
    /// para el parser de restore (el único carácter estructural es '\n').
    inline bool is_valid_comment(const std::string& comment) {
        if (comment.size() > 255) {  // IPSET_MAX_COMMENT_SIZE
            return false;
        }
        for (unsigned char c : comment) {
            if (c < 0x20 || c == 0x7f) {  // control: \n \r \t \0 ...
                return false;
            }
            if (c == '"' || c == '\\') {  // delimitador de token / backslash
                return false;
            }
        }
        return true;
    }

}  // namespace mldefender::firewall
