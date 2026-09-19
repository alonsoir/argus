// test_ddos_kernel_agg.cpp -- DAY273. Sin framework: devuelve != 0 si algo falla.
//
//   g++ -std=c++20 -Wall -Wextra -O1 -I sniffer/include test_ddos_kernel_agg.cpp -o test_ddos_agg -lbpf
//   ./test_ddos_agg                       # solo tests puros (no necesita kernel ni root)
//   sudo ./test_ddos_agg --bpf sniffer.bpf.o   # + integracion contra el verificador/kernel real
//
// El modo --bpf usa BPF_PROG_TEST_RUN (una CPU, sin NIC). NO prueba la carrera multi-CPU:
// eso es del E2E con el flood real.
#include <bpf/libbpf.h>

#include <cstdio>
#include <cstring>
#include <arpa/inet.h>
#include <net/if.h>

#include "ddos_kernel_agg.hpp"

using sniffer::DdosKernelAggregator;
using sniffer::DdosVictimVal;
using Snap = DdosKernelAggregator::Snapshot;

static int g_fail = 0;
#define CHECK(cond)                                                                  \
    do {                                                                             \
        if (!(cond)) {                                                               \
            std::printf("  FAIL %s:%d  %s\n", __FILE__, __LINE__, #cond);            \
            ++g_fail;                                                                \
        }                                                                            \
    } while (0)

static uint64_t K(uint32_t ip, uint32_t proto) { return DdosKernelAggregator::pack(ip, proto); }
static constexpr uint32_t V1 = (192u << 24) | (168u << 16) | (100u << 8) | 1u;
static constexpr uint32_t V2 = (10u << 24) | (1u << 16) | (2u << 8) | 3u;

static void test_ip_to_string() {
    std::puts("ip_to_string");
    CHECK(DdosKernelAggregator::ip_to_string(V1) == "192.168.100.1");
    CHECK(DdosKernelAggregator::ip_to_string(0xC0A86401u) == "192.168.100.1");
    CHECK(DdosKernelAggregator::ip_to_string(0xFFFFFFFFu) == "255.255.255.255");
    CHECK(DdosKernelAggregator::ip_to_string(0) == "0.0.0.0");
}

static void test_delta_basic() {
    std::puts("delta: baseline vacio, incremento, victima nueva, sin cambios omitida");
    Snap prev, cur;
    cur[K(V1, 17)] = {5000, 2410000};
    auto w = DdosKernelAggregator::compute_delta(prev, cur);  // primera lectura
    CHECK(w.victims.size() == 1 && w.victims[0].d_pkts == 5000 && w.victims[0].d_bytes == 2410000);
    CHECK(w.counter_resets == 0 && w.evicted == 0);

    prev = cur;
    cur[K(V1, 17)] = {8000, 3856000};   // +3000
    cur[K(V2, 6)] = {100, 30000};       // nueva
    w = DdosKernelAggregator::compute_delta(prev, cur);
    CHECK(w.victims.size() == 2);
    CHECK(w.victims[0].dst_ip == V1 && w.victims[0].d_pkts == 3000 && w.victims[0].d_bytes == 1446000);
    CHECK(w.victims[1].dst_ip == V2 && w.victims[1].d_pkts == 100);

    prev = cur;  // nada cambia -> ventana vacia (victimas frias no aparecen)
    w = DdosKernelAggregator::compute_delta(prev, cur);
    CHECK(w.victims.empty() && w.evicted == 0 && w.counter_resets == 0);
}

static void test_delta_eviction() {
    std::puts("delta: desalojo LRU y reinsercion (contador retrocede)");
    Snap prev, cur;
    prev[K(V1, 17)] = {9000, 4000000};
    prev[K(V2, 6)] = {50, 15000};
    cur[K(V1, 17)] = {120, 57840};  // desalojada y reinsertada: retrocedio
    // V2 ya no esta: desalojada
    auto w = DdosKernelAggregator::compute_delta(prev, cur);
    CHECK(w.counter_resets == 1);
    CHECK(w.evicted == 1);
    CHECK(w.victims.size() == 1 && w.victims[0].d_pkts == 120);  // no un delta negativo/enorme
}

static void test_delta_proto_is_part_of_key() {
    std::puts("delta: misma IP con distinto protocolo son victimas distintas");
    Snap prev, cur;
    cur[K(V1, 17)] = {10, 100};
    cur[K(V1, 6)] = {20, 200};
    auto w = DdosKernelAggregator::compute_delta(prev, cur);
    CHECK(w.victims.size() == 2 && w.victims[0].proto == 6 && w.victims[1].proto == 17);
}

// ---------------------------------------------------------------- integracion
static void build_pkt(uint8_t* p, int total, uint8_t proto, uint32_t dst) {
    std::memset(p, 0, total);
    p[12] = 0x08; p[13] = 0x00;
    uint8_t* ip = p + 14;
    ip[0] = 0x45;
    uint16_t tl = htons(total - 14);
    std::memcpy(ip + 2, &tl, 2);
    ip[8] = 64; ip[9] = proto;
    ip[12] = 10; ip[13] = 0; ip[14] = 0; ip[15] = 7;
    ip[16] = dst >> 24; ip[17] = dst >> 16; ip[18] = dst >> 8; ip[19] = dst;
    uint8_t* l4 = ip + 20;
    l4[0] = 0x30; l4[1] = 0x39; l4[2] = 0x1F; l4[3] = 0x90;
}

static bool send(int pfd, uint8_t proto, uint32_t dst, int len, int n) {
    uint8_t pkt[2048];
    build_pkt(pkt, len, proto, dst);
    // Struct explicito (no LIBBPF_OPTS): la macro usa extensiones GNU que -Wpedantic -Werror
    // (flags del proyecto) rechazan en C++.
    bpf_test_run_opts t;
    std::memset(&t, 0, sizeof(t));
    t.sz = sizeof(t);
    t.data_in = pkt;
    t.data_size_in = static_cast<uint32_t>(len);
    t.repeat = static_cast<uint32_t>(n);
    return bpf_prog_test_run_opts(pfd, &t) == 0 && t.retval == 2 /*XDP_PASS*/;
}

static void test_integration(const char* obj) {
    std::printf("integracion contra el kernel real: %s\n", obj);
    bpf_object* o = bpf_object__open_file(obj, nullptr);
    if (!o) { std::puts("  FAIL no abre el objeto"); ++g_fail; return; }
    bpf_program* p;
    bpf_object__for_each_program(p, o) bpf_program__set_type(p, BPF_PROG_TYPE_XDP);
    if (bpf_object__load(o)) { std::puts("  FAIL el verificador/kernel rechaza el objeto"); ++g_fail; return; }
    int pfd = bpf_program__fd(bpf_object__find_program_by_name(o, "xdp_sniffer_enhanced"));
    bpf_map* dm = bpf_object__find_map_by_name(o, "ddos_victims");
    if (!dm) { std::puts("  FAIL el objeto no tiene el mapa ddos_victims (patch aplicado?)"); ++g_fail; return; }
    CHECK(bpf_map__key_size(dm) == 8 && bpf_map__value_size(dm) == 16);

    // test_run sin ctx entrega los paquetes como recibidos por el loopback del netns
    // (ifindex de `lo`, normalmente 1): hay que dar de alta ESA interfaz en iface_configs,
    // o el programa sale por "interfaz no configurada" antes de contar nada.
    const uint32_t lo = if_nametoindex("lo");
    CHECK(lo != 0);
    struct { uint32_t ifindex; uint8_t mode, is_wan, res[2]; } ic = {lo, 1, 0, {0, 0}};
    CHECK(bpf_map_update_elem(bpf_map__fd(bpf_object__find_map_by_name(o, "iface_configs")), &lo, &ic, 0) == 0);
    uint32_t k0 = 0;  // filter_settings es un ARRAY de 1 entrada, clave 0
    uint8_t fc[8] = {1, 0, 0, 0, 0, 0, 0, 0};
    CHECK(bpf_map_update_elem(bpf_map__fd(bpf_object__find_map_by_name(o, "filter_settings")), &k0, fc, 0) == 0);

    DdosKernelAggregator agg(bpf_map__fd(dm), bpf_map__max_entries(dm));

    auto w = agg.poll();
    CHECK(w && w->victims.empty());                      // mapa vacio

    CHECK(send(pfd, 17, V1, 482, 5000));
    w = agg.poll();
    CHECK(w && w->victims.size() == 1);
    if (w && w->victims.size() == 1) {
        CHECK(w->victims[0].dst_ip == V1 && w->victims[0].proto == 17);
        CHECK(w->victims[0].d_pkts == 5000 && w->victims[0].d_bytes == 5000ull * 482);
        CHECK(w->t_end_ns > w->t_start_ns);
        std::printf("  ventana 1: %s/udp d_pkts=%llu d_bytes=%llu\n",
                    DdosKernelAggregator::ip_to_string(w->victims[0].dst_ip).c_str(),
                    (unsigned long long)w->victims[0].d_pkts, (unsigned long long)w->victims[0].d_bytes);
    }

    CHECK(send(pfd, 17, V1, 482, 3000));                 // el delta NO acumula lo anterior
    w = agg.poll();
    CHECK(w && w->victims.size() == 1 && w->victims[0].d_pkts == 3000);

    CHECK(send(pfd, 17, V1, 482, 200));
    CHECK(send(pfd, 6, V2, 300, 100));
    w = agg.poll();
    CHECK(w && w->victims.size() == 2);
    if (w && w->victims.size() == 2) {
        CHECK(w->victims[0].dst_ip == V1 && w->victims[0].d_pkts == 200);
        CHECK(w->victims[1].dst_ip == V2 && w->victims[1].proto == 6 && w->victims[1].d_pkts == 100);
        CHECK(w->victims[1].d_bytes == 100ull * 300);
    }

    w = agg.poll();                                      // sin trafico -> ventana vacia
    CHECK(w && w->victims.empty() && w->counter_resets == 0 && w->evicted == 0);

    bpf_object__close(o);
}

int main(int argc, char** argv) {
    test_ip_to_string();
    test_delta_basic();
    test_delta_eviction();
    test_delta_proto_is_part_of_key();
    if (argc >= 3 && std::strcmp(argv[1], "--bpf") == 0) test_integration(argv[2]);
    std::puts(g_fail ? "\nRESULTADO: FALLOS" : "\nRESULTADO: OK");
    return g_fail ? 1 : 0;
}