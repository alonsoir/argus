// DAY339 — DEBT-SNIFFER-IS-EXTERNAL-IP-BYTE-ORDER-001
//
// TimeWindowAggregator::is_external_ip (fast path y ruta de ransomware) recibe event.dst_ip tal como lo
// ensambla sniffer.bpf.c: a.b.c.d = a<<24|b<<16|c<<8|d, en orden NUMÉRICO de host. Medido DAY339 sobre el
// bronce (~41,8 M filas argus desde el 24-jul: ninguna con la IP invertida).
//
// [EXTIP-MULTICAST-D339] DEBT-SNIFFER-IS-EXTERNAL-IP-MULTICAST-001: el multicast (224.0.0.0/4) y el broadcast
// limitado (255.255.255.255) no son un servidor externo; hasta DAY339 contaban como externos (medido: 111 259
// filas argus del bronce a 224.0.x.x). is_external_ip devuelve false para ellos ("no externa").
//
// Oráculo EXTERNO: el entero se construye desde los cuatro octetos con la misma fórmula del eBPF
// (sniffer.bpf.c:315), nunca desde la función bajo prueba. Y el test prueba que discrimina: cada caso no
// capicúa se comprueba también con los bytes invertidos y tiene que dar la respuesta CONTRARIA; si una
// regresión hiciera que el orden diera igual, ese control falla.
//
// No usa assert(): el perfil production lleva -DNDEBUG y vaciaría el test.
#include "time_window_aggregator.hpp"

#include <cstdint>
#include <cstdio>

using sniffer::TimeWindowAggregator;

static int failures = 0;

// Misma fórmula que sniffer.bpf.c:315 (event->dst_ip).
static uint32_t como_ebpf(uint8_t a, uint8_t b, uint8_t c, uint8_t d) {
    return (static_cast<uint32_t>(a) << 24) | (static_cast<uint32_t>(b) << 16) |
           (static_cast<uint32_t>(c) << 8) | static_cast<uint32_t>(d);
}

static uint32_t invertida(uint32_t v) {
    return ((v & 0x000000FFu) << 24) | ((v & 0x0000FF00u) << 8) |
           ((v & 0x00FF0000u) >> 8) | ((v & 0xFF000000u) >> 24);
}

// externa: lo que tiene que decir is_external_ip. control_invertida: si con los bytes al revés la
// respuesta tiene que ser la contraria (false en los casos ciegos, donde invertir no cambia la clase).
static void check(const char* ip, uint8_t a, uint8_t b, uint8_t c, uint8_t d, bool externa,
                  bool control_invertida, const char* nota) {
    const uint32_t v = como_ebpf(a, b, c, d);
    const bool got = TimeWindowAggregator::is_external_ip(v);
    if (got != externa) {
        std::printf("FAIL  %-15s 0x%08X  esperado %s  obtenido %s  [%s]\n", ip, v,
                    externa ? "externa" : "no externa", got ? "externa" : "no externa", nota);
        ++failures;
        return;
    }
    if (control_invertida) {
        const uint32_t w = invertida(v);
        const bool got_w = TimeWindowAggregator::is_external_ip(w);
        if (got_w == externa) {
            std::printf("FAIL  %-15s 0x%08X  invertida 0x%08X da lo mismo: el test no discrimina  [%s]\n",
                        ip, v, w, nota);
            ++failures;
            return;
        }
    }
    std::printf("ok    %-15s 0x%08X  %s%s  [%s]\n", ip, v, externa ? "externa" : "no externa",
                control_invertida ? " (invertida: la contraria)" : "", nota);
}

int main() {
    // Internas (RFC 1918, loopback, link-local)
    check("192.168.100.20", 192, 168, 100, 20, false, true, "control-1 del lab");
    check("192.168.56.1",   192, 168, 56, 1,   false, true, "anfitrion host-only, fila real del bronce");
    check("10.0.2.15",      10, 0, 2, 15,      false, true, "NAT de VirtualBox");
    check("172.16.0.1",     172, 16, 0, 1,     false, true, "borde inferior de 172.16/12");
    check("172.31.255.254", 172, 31, 255, 254, false, true, "borde superior de 172.16/12");
    check("127.0.0.1",      127, 0, 0, 1,      false, true, "loopback");
    check("169.254.1.1",    169, 254, 1, 1,    false, true, "link-local");
    // Multicast y broadcast limitado: no externas [EXTIP-MULTICAST-D339]
    check("224.0.0.251",     224, 0, 0, 251,     false, true, "mDNS, fila real del bronce");
    check("239.255.255.250", 239, 255, 255, 250, false, true, "SSDP, borde superior de 224/4");
    check("224.0.0.1",       224, 0, 0, 1,       false, true, "todos los nodos, borde inferior de 224/4");
    check("255.255.255.255", 255, 255, 255, 255, false, false, "broadcast limitado; capicua, caso ciego");
    // Externas
    check("8.8.8.8",        8, 8, 8, 8,        true, false, "capicua: invertida da lo mismo, caso ciego");
    check("147.32.84.165",  147, 32, 84, 165,  true, false, "victima del CTU-13 Neris; invertida tambien externa");
    check("172.15.255.255", 172, 15, 255, 255, true, false, "justo debajo de 172.16/12");
    check("172.32.0.1",     172, 32, 0, 1,     true, false, "justo encima de 172.16/12");
    check("192.169.0.1",    192, 169, 0, 1,    true, false, "justo encima de 192.168/16");
    check("1.2.168.192",    1, 2, 168, 192,    true, true, "externa que invertida seria 192.168.2.1");
    check("20.100.168.192", 20, 100, 168, 192, true, true, "control-1 al reves: externa en el orden bueno");
    check("223.255.255.254", 223, 255, 255, 254, true, false, "justo debajo de 224/4");
    check("240.0.0.1",       240, 0, 0, 1,       true, false, "clase E: fuera de la opcion (a), sigue externa");
    check("255.255.255.254", 255, 255, 255, 254, true, false, "junto al broadcast limitado");
    check("251.0.0.224",     251, 0, 0, 224,     true, true, "mDNS al reves: externa en el orden bueno");

    if (failures != 0) {
        std::printf("\ntest_is_external_ip: %d FALLOS\n", failures);
        return 1;
    }
    std::printf("\ntest_is_external_ip: OK\n");
    return 0;
}
