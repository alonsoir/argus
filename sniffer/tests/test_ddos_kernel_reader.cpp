// sniffer/tests/test_ddos_kernel_reader.cpp
// [DDOS-KREAD-D274:TEST]
// Tests del lector DDoS (DAY274): formato del CSV (funciones puras) y ciclo de vida del
// hilo (start/stop, parada inmediata, cadencia) SIN kernel: con fd = -1 cada lectura del
// mapa falla, asi que solo se ejercita el hilo. No necesita root.
//
// Build manual (desde la raiz del repo, en la VM; una sola linea):
//   g++ -std=c++20 -Wall -Wextra -Wpedantic -Werror -I sniffer/include sniffer/tests/test_ddos_kernel_reader.cpp -o /tmp/test_ddos_kernel_reader -lbpf -pthread
#include "ddos_kernel_reader.hpp"

#include <unistd.h>

#include <chrono>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <thread>

namespace {

int g_fail = 0;

#define CHECK(cond)                                                            \
    do {                                                                       \
        if (!(cond)) {                                                         \
            std::fprintf(stderr, "FAIL %s:%d  %s\n", __FILE__, __LINE__, #cond); \
            ++g_fail;                                                          \
        }                                                                      \
    } while (0)

using sniffer::DdosKernelAggregator;
using sniffer::DdosKernelReader;
using sniffer::DdosVictimDelta;
using sniffer::DdosWindow;

DdosWindow make_window() {
    DdosWindow w;
    w.t_start_ns = 1000000000ull;
    w.t_end_ns = 2000000000ull;  // 1000 ms exactos
    w.victims.push_back(DdosVictimDelta{0xC0A86401u, 17u, 100u, 48000u});
    w.victims.push_back(DdosVictimDelta{0xC0A86402u, 6u, 5u, 300u});
    return w;
}

std::string tmp_path(const std::string& tag) {
    return "/tmp/ddos_reader_test_" + std::to_string(::getpid()) + "_" + tag + ".csv";
}

std::string slurp(const std::string& path) {
    std::ifstream f(path);
    std::stringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

void test_csv_format() {
    CHECK(sniffer::ddos_csv_header() == "win,ts_ms,window_ms,dst_ip,proto,d_pkts,d_bytes\n");
    CHECK(DdosKernelAggregator::ip_to_string(0xC0A86401u) == "192.168.100.1");

    // ventana normal
    const DdosWindow w = make_window();
    const std::string rows = sniffer::ddos_csv_rows(7, 1234567890123ull, w);
    CHECK(rows ==
          "7,1234567890123,1000,192.168.100.1,17,100,48000\n"
          "7,1234567890123,1000,192.168.100.2,6,5,300\n");

    // baseline: t_start_ns == 0 -> window_ms = 0
    DdosWindow b = make_window();
    b.t_start_ns = 0;
    CHECK(sniffer::ddos_window_ms(b) == 0);
    CHECK(sniffer::ddos_csv_rows(1, 42, b) ==
          "1,42,0,192.168.100.1,17,100,48000\n"
          "1,42,0,192.168.100.2,6,5,300\n");

    // truncado a max_rows (se conservan las de mayor d_pkts, que ya vienen primero)
    CHECK(sniffer::ddos_csv_rows(7, 1234567890123ull, w, 1) ==
          "7,1234567890123,1000,192.168.100.1,17,100,48000\n");
    CHECK(sniffer::ddos_csv_rows(7, 1, w, 0).empty());

    // ventana ociosa: sin filas
    DdosWindow idle;
    idle.t_start_ns = 1;
    idle.t_end_ns = 2;
    CHECK(sniffer::ddos_csv_rows(3, 1, idle).empty());

    // redondeo de window_ms al ms mas cercano
    DdosWindow r = make_window();
    r.t_end_ns = r.t_start_ns + 1000499999ull;
    CHECK(sniffer::ddos_window_ms(r) == 1000);
    r.t_end_ns = r.t_start_ns + 1000500000ull;
    CHECK(sniffer::ddos_window_ms(r) == 1001);

    // reloj inconsistente (fin <= inicio): 0, nunca un valor gigante por underflow
    DdosWindow bad = make_window();
    bad.t_end_ns = bad.t_start_ns - 1;
    CHECK(sniffer::ddos_window_ms(bad) == 0);
}

void test_clamp() {
    CHECK(DdosKernelReader::clamp_interval_ms(0) == 1000);
    CHECK(DdosKernelReader::clamp_interval_ms(-5) == 1000);
    CHECK(DdosKernelReader::clamp_interval_ms(50) == 100);
    CHECK(DdosKernelReader::clamp_interval_ms(100) == 100);
    CHECK(DdosKernelReader::clamp_interval_ms(1000) == 1000);
    CHECK(DdosKernelReader::clamp_interval_ms(60000) == 60000);
    CHECK(DdosKernelReader::clamp_interval_ms(999999) == 60000);
}

// stop() debe despertar al hilo al instante aunque el intervalo sea largo.
void test_prompt_stop() {
    const std::string path = tmp_path("prompt");
    std::remove(path.c_str());
    {
        DdosKernelReader r(-1, 65536, 60000, path);
        CHECK(r.start());
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        const auto t0 = std::chrono::steady_clock::now();
        r.stop();
        const auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                            std::chrono::steady_clock::now() - t0)
                            .count();
        CHECK(ms < 1000);
        const DdosKernelReader::Stats s = r.stats();
        CHECK(s.read_errors == 2);  // baseline + ultima lectura parcial; ambas fallan con fd=-1
        CHECK(s.windows == 0);
        r.stop();  // idempotente
    }
    CHECK(slurp(path) == sniffer::ddos_csv_header());
    std::remove(path.c_str());
}

// Con T = 100 ms el hilo lee con cadencia (ni se queda dormido ni gira en vacio).
void test_cadence() {
    const std::string path = tmp_path("cadence");
    std::remove(path.c_str());
    {
        DdosKernelReader r(-1, 65536, 100, path);
        CHECK(r.start());
        std::this_thread::sleep_for(std::chrono::milliseconds(450));
        r.stop();
        const DdosKernelReader::Stats s = r.stats();
        // esperado ~6 (baseline + 4 ticks + parcial); margen amplio por si la VM va cargada
        CHECK(s.read_errors >= 3);
        CHECK(s.read_errors <= 10);
    }
    std::remove(path.c_str());
}

void test_start_failures_and_restart() {
    {
        DdosKernelReader r(-1, 65536, 100, "");
        CHECK(!r.start());  // sin ruta: no arranca
    }
    {
        DdosKernelReader r(-1, 65536, 100, "/nonexistent_dir_ddos_reader/x.csv");
        CHECK(!r.start());  // ruta no escribible: no arranca, no revienta
    }
    const std::string path = tmp_path("restart");
    std::remove(path.c_str());
    {
        DdosKernelReader r(-1, 65536, 100, path);
        CHECK(r.start());
        CHECK(r.start());  // ya arrancado: true, sin segundo hilo
        r.stop();
        CHECK(r.start());  // rearranque tras stop
        r.stop();
    }
    // la cabecera se escribe una sola vez aunque se reabra el fichero
    CHECK(slurp(path) == sniffer::ddos_csv_header());
    std::remove(path.c_str());
}

}  // namespace

int main() {
    test_csv_format();
    test_clamp();
    test_prompt_stop();
    test_cadence();
    test_start_failures_and_restart();
    std::printf("test_ddos_kernel_reader: %s (%d fallos)\n", g_fail ? "FAIL" : "OK", g_fail);
    return g_fail ? 1 : 0;
}
