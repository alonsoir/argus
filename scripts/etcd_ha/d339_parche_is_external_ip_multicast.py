#!/usr/bin/env python3
# DAY339 — parcheador de DEBT-SNIFFER-IS-EXTERNAL-IP-MULTICAST-001 (rama sugerida: fix/d339-is-external-ip-multicast,
# APILADA sobre fix/d339-is-external-ip-orden). Decisión de Alonso DAY339: opción (a), excluir solo lo medido.
# 1) time_window_aggregator.cpp: is_external_ip devuelve false para 224.0.0.0/4 (multicast) y 255.255.255.255.
# 2) sniffer/tests/test_is_external_ip.cpp: casos de multicast, broadcast y sus bordes (se reemplaza entero).
# Conserva el modo de cada fichero. sha256 de partida (los de llegada de la pieza 1) comprobados, cada ancla
# exactamente 1 vez, nada escrito si algo falla, sha256 de llegada.
# Uso (Mac, raíz del repo): python3 -I scripts/etcd_ha/d339_parche_is_external_ip_multicast.py
import hashlib, os, sys

def sha(b): return hashlib.sha256(b).hexdigest()

TWA = 'sniffer/src/userspace/time_window_aggregator.cpp'
TST = 'sniffer/tests/test_is_external_ip.cpp'
PARTIDA = {
    TWA: '4a0418cf03cb85e617b67045d66148109177adab5eff72ae197c4b23512e660b',
    TST: 'aff82946cb5989c9638affcacc5025b64f8a845ed7a92f378b120ee1c922fead',
}
A1 = '    // Rangos RFC 1918, loopback y link-local.\n'
B1 = '    // Rangos RFC 1918, loopback y link-local; y, desde [EXTIP-MULTICAST-D339], multicast y broadcast limitado,\n    // que tampoco son un servidor externo (DEBT-SNIFFER-IS-EXTERNAL-IP-MULTICAST-001).\n'
A2 = '    // 169.254.0.0/16 (link-local)\n    if ((ip & 0xFFFF0000) == 0xA9FE0000) {\n        return false;\n    }\n'
B2 = '    // 169.254.0.0/16 (link-local)\n    if ((ip & 0xFFFF0000) == 0xA9FE0000) {\n        return false;\n    }\n\n    // 224.0.0.0/4 (multicast) [EXTIP-MULTICAST-D339]\n    if ((ip & 0xF0000000) == 0xE0000000) {\n        return false;\n    }\n\n    // 255.255.255.255 (broadcast limitado) [EXTIP-MULTICAST-D339]\n    if (ip == 0xFFFFFFFF) {\n        return false;\n    }\n'
TEST = '// DAY339 — DEBT-SNIFFER-IS-EXTERNAL-IP-BYTE-ORDER-001\n//\n// TimeWindowAggregator::is_external_ip (fast path y ruta de ransomware) recibe event.dst_ip tal como lo\n// ensambla sniffer.bpf.c: a.b.c.d = a<<24|b<<16|c<<8|d, en orden NUMÉRICO de host. Medido DAY339 sobre el\n// bronce (~41,8 M filas argus desde el 24-jul: ninguna con la IP invertida).\n//\n// [EXTIP-MULTICAST-D339] DEBT-SNIFFER-IS-EXTERNAL-IP-MULTICAST-001: el multicast (224.0.0.0/4) y el broadcast\n// limitado (255.255.255.255) no son un servidor externo; hasta DAY339 contaban como externos (medido: 111 259\n// filas argus del bronce a 224.0.x.x). is_external_ip devuelve false para ellos ("no externa").\n//\n// Oráculo EXTERNO: el entero se construye desde los cuatro octetos con la misma fórmula del eBPF\n// (sniffer.bpf.c:315), nunca desde la función bajo prueba. Y el test prueba que discrimina: cada caso no\n// capicúa se comprueba también con los bytes invertidos y tiene que dar la respuesta CONTRARIA; si una\n// regresión hiciera que el orden diera igual, ese control falla.\n//\n// No usa assert(): el perfil production lleva -DNDEBUG y vaciaría el test.\n#include "time_window_aggregator.hpp"\n\n#include <cstdint>\n#include <cstdio>\n\nusing sniffer::TimeWindowAggregator;\n\nstatic int failures = 0;\n\n// Misma fórmula que sniffer.bpf.c:315 (event->dst_ip).\nstatic uint32_t como_ebpf(uint8_t a, uint8_t b, uint8_t c, uint8_t d) {\n    return (static_cast<uint32_t>(a) << 24) | (static_cast<uint32_t>(b) << 16) |\n           (static_cast<uint32_t>(c) << 8) | static_cast<uint32_t>(d);\n}\n\nstatic uint32_t invertida(uint32_t v) {\n    return ((v & 0x000000FFu) << 24) | ((v & 0x0000FF00u) << 8) |\n           ((v & 0x00FF0000u) >> 8) | ((v & 0xFF000000u) >> 24);\n}\n\n// externa: lo que tiene que decir is_external_ip. control_invertida: si con los bytes al revés la\n// respuesta tiene que ser la contraria (false en los casos ciegos, donde invertir no cambia la clase).\nstatic void check(const char* ip, uint8_t a, uint8_t b, uint8_t c, uint8_t d, bool externa,\n                  bool control_invertida, const char* nota) {\n    const uint32_t v = como_ebpf(a, b, c, d);\n    const bool got = TimeWindowAggregator::is_external_ip(v);\n    if (got != externa) {\n        std::printf("FAIL  %-15s 0x%08X  esperado %s  obtenido %s  [%s]\\n", ip, v,\n                    externa ? "externa" : "no externa", got ? "externa" : "no externa", nota);\n        ++failures;\n        return;\n    }\n    if (control_invertida) {\n        const uint32_t w = invertida(v);\n        const bool got_w = TimeWindowAggregator::is_external_ip(w);\n        if (got_w == externa) {\n            std::printf("FAIL  %-15s 0x%08X  invertida 0x%08X da lo mismo: el test no discrimina  [%s]\\n",\n                        ip, v, w, nota);\n            ++failures;\n            return;\n        }\n    }\n    std::printf("ok    %-15s 0x%08X  %s%s  [%s]\\n", ip, v, externa ? "externa" : "no externa",\n                control_invertida ? " (invertida: la contraria)" : "", nota);\n}\n\nint main() {\n    // Internas (RFC 1918, loopback, link-local)\n    check("192.168.100.20", 192, 168, 100, 20, false, true, "control-1 del lab");\n    check("192.168.56.1",   192, 168, 56, 1,   false, true, "anfitrion host-only, fila real del bronce");\n    check("10.0.2.15",      10, 0, 2, 15,      false, true, "NAT de VirtualBox");\n    check("172.16.0.1",     172, 16, 0, 1,     false, true, "borde inferior de 172.16/12");\n    check("172.31.255.254", 172, 31, 255, 254, false, true, "borde superior de 172.16/12");\n    check("127.0.0.1",      127, 0, 0, 1,      false, true, "loopback");\n    check("169.254.1.1",    169, 254, 1, 1,    false, true, "link-local");\n    // Multicast y broadcast limitado: no externas [EXTIP-MULTICAST-D339]\n    check("224.0.0.251",     224, 0, 0, 251,     false, true, "mDNS, fila real del bronce");\n    check("239.255.255.250", 239, 255, 255, 250, false, true, "SSDP, borde superior de 224/4");\n    check("224.0.0.1",       224, 0, 0, 1,       false, true, "todos los nodos, borde inferior de 224/4");\n    check("255.255.255.255", 255, 255, 255, 255, false, false, "broadcast limitado; capicua, caso ciego");\n    // Externas\n    check("8.8.8.8",        8, 8, 8, 8,        true, false, "capicua: invertida da lo mismo, caso ciego");\n    check("147.32.84.165",  147, 32, 84, 165,  true, false, "victima del CTU-13 Neris; invertida tambien externa");\n    check("172.15.255.255", 172, 15, 255, 255, true, false, "justo debajo de 172.16/12");\n    check("172.32.0.1",     172, 32, 0, 1,     true, false, "justo encima de 172.16/12");\n    check("192.169.0.1",    192, 169, 0, 1,    true, false, "justo encima de 192.168/16");\n    check("1.2.168.192",    1, 2, 168, 192,    true, true, "externa que invertida seria 192.168.2.1");\n    check("20.100.168.192", 20, 100, 168, 192, true, true, "control-1 al reves: externa en el orden bueno");\n    check("223.255.255.254", 223, 255, 255, 254, true, false, "justo debajo de 224/4");\n    check("240.0.0.1",       240, 0, 0, 1,       true, false, "clase E: fuera de la opcion (a), sigue externa");\n    check("255.255.255.254", 255, 255, 255, 254, true, false, "junto al broadcast limitado");\n    check("251.0.0.224",     251, 0, 0, 224,     true, true, "mDNS al reves: externa en el orden bueno");\n\n    if (failures != 0) {\n        std::printf("\\ntest_is_external_ip: %d FALLOS\\n", failures);\n        return 1;\n    }\n    std::printf("\\ntest_is_external_ip: OK\\n");\n    return 0;\n}\n'

def falla(m):
    print('[PARCHE] ERROR:', m, '- no se ha escrito nada'); sys.exit(1)

if not os.path.isdir('sniffer'): falla('no estoy en la raiz del repo')
datos = {}
for f, h in PARTIDA.items():
    if not os.path.isfile(f): falla(f + ' no existe (¿falta la pieza 1?)')
    b = open(f, 'rb').read()
    if sha(b) != h: falla('%s: sha256 de partida %s, esperado %s' % (f, sha(b), h))
    datos[f] = b.decode('utf-8')
for a in (A1, A2):
    n = datos[TWA].count(a)
    if n != 1: falla('%s: ancla encontrada %d veces, esperada 1' % (TWA, n))
nuevo = {TWA: datos[TWA].replace(A1, B1, 1).replace(A2, B2, 1), TST: TEST}
for f, t in nuevo.items():
    with open(f + '.d339tmp', 'w', encoding='utf-8', newline='') as h: h.write(t)
    os.chmod(f + '.d339tmp', os.stat(f).st_mode & 0o7777)  # conserva el modo (TWA es 100755)
for f in nuevo:
    os.replace(f + '.d339tmp', f)
for f in (TWA, TST):
    print('[PARCHE] llegada %s  %s' % (sha(open(f, 'rb').read()), f))
print('[PARCHE] OK')
