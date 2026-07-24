// DAY 229 — DEBT-SNIFFER-IP-BYTE-ORDER-001
//
// Oráculo EXTERNO: los valores esperados salen de la aritmética de la RFC, no de
// recalcular nada desde la propia fila del bronce. El criterio anterior de la deuda
// (recomputar community_id desde las IPs de la misma fila) pasaba en verde con el
// bug presente, porque hash y cadena beben de la misma fuente.
//
// No usa assert(): el perfil production lleva -DNDEBUG y vaciaria el test.
#include "ip_format.hpp"

#include <cstdint>
#include <cstdio>
#include <cstring>

static int failures = 0;

static void check(uint32_t ip_host_order, const char* expected, const char* note) {
    char got[INET_ADDRSTRLEN];
    if (!argus::sniffer::ip_host_to_buffer(ip_host_order, got, sizeof(got))) {
        std::printf("FAIL  0x%08X  inet_ntop devolvio error   [%s]\n", ip_host_order, note);
        ++failures;
        return;
    }
    if (std::strcmp(got, expected) != 0) {
        std::printf("FAIL  0x%08X  esperado %-15s  obtenido %-15s  [%s]\n",
                    ip_host_order, expected, got, note);
        ++failures;
        return;
    }
    std::printf("ok    0x%08X  %-15s  [%s]\n", ip_host_order, got, note);
}

int main() {
    check(0xC0A83801u, "192.168.56.1",    "fila real del bronce, DAY 226");
    check(0xC0A838FFu, "192.168.56.255",  "broadcast host-only de VirtualBox");
    check(0x932054A5u, "147.32.84.165",   "victima del CTU-13 Neris");
    check(0x0A01010Au, "10.1.1.10",       "capicua: invertida da lo mismo, caso ciego");
    check(0x00000000u, "0.0.0.0",         "borde");
    check(0xFFFFFFFFu, "255.255.255.255", "borde");

    if (failures != 0) {
        std::printf("\ntest_ip_format: %d FALLOS\n", failures);
        return 1;
    }
    std::printf("\ntest_ip_format: OK\n");
    return 0;
}
