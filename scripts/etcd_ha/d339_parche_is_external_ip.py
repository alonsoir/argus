#!/usr/bin/env python3
# DAY339 — parcheador de DEBT-SNIFFER-IS-EXTERNAL-IP-BYTE-ORDER-001 (rama sugerida: fix/d339-is-external-ip-orden).
# 1) time_window_aggregator.cpp: el comentario de is_external_ip decía "assuming network byte order" y no
#    convertía nada; se cambia por el contrato medido (orden numérico de host, el de sniffer.bpf.c). Sin cambio de lógica.
# 2) sniffer/tests/test_is_external_ip.cpp: test nuevo, oráculo externo + control de que discrimina el orden.
# 3) sniffer/CMakeLists.txt: registra el test, justo después de test_ip_format.
# Conserva el modo de cada fichero. sha256 de partida comprobados, cada ancla exactamente 1 vez, nada escrito si algo falla, sha256 de llegada.
# Uso (Mac, raíz del repo): python3 -I scripts/etcd_ha/d339_parche_is_external_ip.py
import hashlib, os, sys

def sha(b): return hashlib.sha256(b).hexdigest()

TWA = 'sniffer/src/userspace/time_window_aggregator.cpp'
CMK = 'sniffer/CMakeLists.txt'
TST = 'sniffer/tests/test_is_external_ip.cpp'
PARTIDA = {
    TWA: '161a0833d1ed15c25acbeb5684b32e50e228fb34268c2d074c6bfa39cde3fddf',
    CMK: '447344f882151da0be9668abbd3fcaf491930ba132c51783cfdeb6ea8d8ddd98',
}

TWA_OLD = ("    // Convert to host byte order if needed (assuming network byte order)\n"
           "    // Check RFC 1918 private address ranges\n")
TWA_NEW = ("    // [EXTIP-ORDEN-D339] `ip` llega en orden NUMERICO de host (a.b.c.d = a<<24|b<<16|c<<8|d), tal como lo\n"
           "    // ensambla sniffer.bpf.c (event->dst_ip): no hay nada que convertir. Medido DAY339 sobre el bronce\n"
           "    // (DEBT-SNIFFER-IS-EXTERNAL-IP-BYTE-ORDER-001) y fijado por tests/test_is_external_ip.cpp.\n"
           "    // Rangos RFC 1918, loopback y link-local.\n")

CMK_ANCLA = 'message(STATUS "\U0001F9EA Unit Test: test_ip_format configured (DAY 229 - DEBT-SNIFFER-IP-BYTE-ORDER-001)")\n'
CMK_NUEVO = ("\n"
             "add_executable(test_is_external_ip  # [EXTIP-ORDEN-D339]\n"
             "        tests/test_is_external_ip.cpp\n"
             "        src/userspace/time_window_aggregator.cpp\n"
             "        src/userspace/flow_tracker.cpp\n"
             "        src/userspace/dns_analyzer.cpp\n"
             "        src/userspace/ip_whitelist.cpp\n"
             ")\n"
             "target_include_directories(test_is_external_ip PRIVATE\n"
             "        ${CMAKE_SOURCE_DIR}/include\n"
             ")\n"
             "target_link_libraries(test_is_external_ip\n"
             "        Threads::Threads\n"
             ")\n"
             "add_test(NAME test_is_external_ip COMMAND test_is_external_ip)\n"
             "message(STATUS \"\U0001F9EA Unit Test: test_is_external_ip configured (DAY339 - DEBT-SNIFFER-IS-EXTERNAL-IP-BYTE-ORDER-001)\")\n")

TEST = '// DAY339 — DEBT-SNIFFER-IS-EXTERNAL-IP-BYTE-ORDER-001\n//\n// TimeWindowAggregator::is_external_ip (fast path y ruta de ransomware) recibe event.dst_ip tal como lo\n// ensambla sniffer.bpf.c: a.b.c.d = a<<24|b<<16|c<<8|d, en orden NUMÉRICO de host. Medido DAY339 sobre el\n// bronce (~41,8 M filas argus desde el 24-jul: ninguna con la IP invertida).\n//\n// Oráculo EXTERNO: el entero se construye desde los cuatro octetos con la misma fórmula del eBPF\n// (sniffer.bpf.c:315), nunca desde la función bajo prueba. Y el test prueba que discrimina: cada caso no\n// capicúa se comprueba también con los bytes invertidos y tiene que dar la respuesta CONTRARIA; si una\n// regresión hiciera que el orden diera igual, ese control falla.\n//\n// No usa assert(): el perfil production lleva -DNDEBUG y vaciaría el test.\n#include "time_window_aggregator.hpp"\n\n#include <cstdint>\n#include <cstdio>\n\nusing sniffer::TimeWindowAggregator;\n\nstatic int failures = 0;\n\n// Misma fórmula que sniffer.bpf.c:315 (event->dst_ip).\nstatic uint32_t como_ebpf(uint8_t a, uint8_t b, uint8_t c, uint8_t d) {\n    return (static_cast<uint32_t>(a) << 24) | (static_cast<uint32_t>(b) << 16) |\n           (static_cast<uint32_t>(c) << 8) | static_cast<uint32_t>(d);\n}\n\nstatic uint32_t invertida(uint32_t v) {\n    return ((v & 0x000000FFu) << 24) | ((v & 0x0000FF00u) << 8) |\n           ((v & 0x00FF0000u) >> 8) | ((v & 0xFF000000u) >> 24);\n}\n\n// externa: lo que tiene que decir is_external_ip. control_invertida: si con los bytes al revés la\n// respuesta tiene que ser la contraria (false en los casos ciegos, donde invertir no cambia la clase).\nstatic void check(const char* ip, uint8_t a, uint8_t b, uint8_t c, uint8_t d, bool externa,\n                  bool control_invertida, const char* nota) {\n    const uint32_t v = como_ebpf(a, b, c, d);\n    const bool got = TimeWindowAggregator::is_external_ip(v);\n    if (got != externa) {\n        std::printf("FAIL  %-15s 0x%08X  esperado %s  obtenido %s  [%s]\\n", ip, v,\n                    externa ? "externa" : "interna", got ? "externa" : "interna", nota);\n        ++failures;\n        return;\n    }\n    if (control_invertida) {\n        const uint32_t w = invertida(v);\n        const bool got_w = TimeWindowAggregator::is_external_ip(w);\n        if (got_w == externa) {\n            std::printf("FAIL  %-15s 0x%08X  invertida 0x%08X da lo mismo: el test no discrimina  [%s]\\n",\n                        ip, v, w, nota);\n            ++failures;\n            return;\n        }\n    }\n    std::printf("ok    %-15s 0x%08X  %s%s  [%s]\\n", ip, v, externa ? "externa" : "interna",\n                control_invertida ? " (invertida: la contraria)" : "", nota);\n}\n\nint main() {\n    // Internas (RFC 1918, loopback, link-local)\n    check("192.168.100.20", 192, 168, 100, 20, false, true, "control-1 del lab");\n    check("192.168.56.1",   192, 168, 56, 1,   false, true, "anfitrion host-only, fila real del bronce");\n    check("10.0.2.15",      10, 0, 2, 15,      false, true, "NAT de VirtualBox");\n    check("172.16.0.1",     172, 16, 0, 1,     false, true, "borde inferior de 172.16/12");\n    check("172.31.255.254", 172, 31, 255, 254, false, true, "borde superior de 172.16/12");\n    check("127.0.0.1",      127, 0, 0, 1,      false, true, "loopback");\n    check("169.254.1.1",    169, 254, 1, 1,    false, true, "link-local");\n    // Externas\n    check("8.8.8.8",        8, 8, 8, 8,        true, false, "capicua: invertida da lo mismo, caso ciego");\n    check("147.32.84.165",  147, 32, 84, 165,  true, false, "victima del CTU-13 Neris; invertida tambien externa");\n    check("172.15.255.255", 172, 15, 255, 255, true, false, "justo debajo de 172.16/12");\n    check("172.32.0.1",     172, 32, 0, 1,     true, false, "justo encima de 172.16/12");\n    check("192.169.0.1",    192, 169, 0, 1,    true, false, "justo encima de 192.168/16");\n    check("1.2.168.192",    1, 2, 168, 192,    true, true, "externa que invertida seria 192.168.2.1");\n    check("20.100.168.192", 20, 100, 168, 192, true, true, "control-1 al reves: externa en el orden bueno");\n\n    if (failures != 0) {\n        std::printf("\\ntest_is_external_ip: %d FALLOS\\n", failures);\n        return 1;\n    }\n    std::printf("\\ntest_is_external_ip: OK\\n");\n    return 0;\n}\n'

def falla(m):
    print('[PARCHE] ERROR:', m, '- no se ha escrito nada'); sys.exit(1)

if not os.path.isdir('sniffer') or not os.path.isfile(CMK): falla('no estoy en la raiz del repo')
if os.path.exists(TST): falla(TST + ' ya existe')
datos = {}
for f, h in PARTIDA.items():
    b = open(f, 'rb').read()
    if sha(b) != h: falla('%s: sha256 de partida %s, esperado %s' % (f, sha(b), h))
    datos[f] = b.decode('utf-8')
for f, ancla in ((TWA, TWA_OLD), (CMK, CMK_ANCLA)):
    n = datos[f].count(ancla)
    if n != 1: falla('%s: ancla encontrada %d veces, esperada 1' % (f, n))
nuevo = {
    TWA: datos[TWA].replace(TWA_OLD, TWA_NEW, 1),
    CMK: datos[CMK].replace(CMK_ANCLA, CMK_ANCLA + CMK_NUEVO, 1),
    TST: TEST,
}
for f, t in nuevo.items():
    with open(f + '.d339tmp', 'w', encoding='utf-8', newline='') as h: h.write(t)
    if os.path.exists(f): os.chmod(f + '.d339tmp', os.stat(f).st_mode & 0o7777)  # conserva el modo (TWA es 100755)
for f in nuevo:
    os.replace(f + '.d339tmp', f)
for f in (TWA, CMK, TST):
    print('[PARCHE] llegada %s  %s' % (sha(open(f, 'rb').read()), f))
print('[PARCHE] OK')
