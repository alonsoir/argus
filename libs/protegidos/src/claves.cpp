// libs/protegidos/src/claves.cpp (antes firewall-acl-agent/src/core/protegidos_claves.cpp) — [PROTEGIDOS-MANIFIESTO-D318] ADR-060 D3 (patrón ADR-025): la clave pública del manifiesto
// de protegidos, compilada en el binario en dos ranuras. CMake la valida (64 hex) y sin la actual no compila; aquí se
// convierte una vez. Si aun así llega mal formada, el agente no arranca: no hay defecto sano para una clave de confianza.
#include "protegidos/manifiesto.hpp"

#include <exception>
#include <iostream>

#ifndef ARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX
#error "ARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX sin definir (CMake: -DARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX=<64 hex>)"
#endif
#ifndef ARGUS_PROTEGIDOS_PUBKEY_SIGUIENTE_HEX
#error "ARGUS_PROTEGIDOS_PUBKEY_SIGUIENTE_HEX sin definir (vacía si no hay rotación en curso)"
#endif

namespace argus::protegidos {

const ClavesProtegidos& claves_protegidos_compiladas() {
    static const ClavesProtegidos c = [] {
        ClavesProtegidos k;
        std::string error;
        if (!claves_protegidos_desde_hex(ARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX, ARGUS_PROTEGIDOS_PUBKEY_SIGUIENTE_HEX, k, error)) {
            std::cerr << "[PROTEGIDOS-CLAVE] FATAL: clave pública compilada mal formada: " << error << std::endl;
            std::terminate();
        }
        return k;
    }();
    return c;
}

}  // namespace argus::protegidos
