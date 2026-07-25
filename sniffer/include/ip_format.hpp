#pragma once
// ip_format.hpp — DAY 229, DEBT-SNIFFER-IP-BYTE-ORDER-001
//
// Punto ÚNICO de conversión IP → texto para el camino eBPF.
//
// Contrato del evento (sniffer/src/kernel/sniffer.bpf.c:232): todos los campos se
// ensamblan a mano como NÚMEROS en orden de host, de forma independiente del
// endianness de la máquina. inet_ntop consume BYTES en orden de red: aquí, y solo
// aquí, hay que deshacer esa conversión.
//
// Existía por duplicado en ring_consumer.cpp (:844 sin htonl, :1235 con htonl).
// Una de las dos estaba mal por definición.

#include <arpa/inet.h>
#include <netinet/in.h>

#include <cstddef>
#include <cstdint>

namespace argus::sniffer {

// Escribe la IP en `out` como texto punteado. `out_len` debe ser >= INET_ADDRSTRLEN.
// No asigna memoria: apto para el camino caliente.
inline bool ip_host_to_buffer(uint32_t ip_host_order, char* out, size_t out_len) {
    struct in_addr addr;
    addr.s_addr = htonl(ip_host_order);  // DAY 229: deshace el orden de host de sniffer.bpf.c:232
    return inet_ntop(AF_INET, &addr, out, static_cast<socklen_t>(out_len)) != nullptr;
}

}  // namespace argus::sniffer
