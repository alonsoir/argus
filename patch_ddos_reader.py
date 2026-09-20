#!/usr/bin/env python3
"""patch_ddos_reader.py -- DAY274, punto 3: hilo lector del agregador DDoS en-kernel.

Que hace (mide, NO detecta):
  * crea sniffer/include/ddos_kernel_reader.hpp   (hilo que llama a poll() cada T ms y escribe un CSV)
  * crea sniffer/tests/test_ddos_kernel_reader.cpp (test sin kernel ni root: formato CSV + ciclo de vida)
  * config: 3 claves nuevas en kernel_space (ddos_kernel_agg_enabled / _interval_ms / _csv_path)
      -> config_manager.hpp/.cpp (parseo) y config_types.h/.cpp (copia a g_config) y sniffer.json
  * main.cpp: crea el lector antes del bucle principal y lo PARA (join) antes de cada
    `delete ebpf_loader_ptr` (el fd del mapa muere con el loader).

Uso (desde la RAIZ del repo, en la VM `defender`: hace falta g++ y libbpf):
    python3 patch_ddos_reader.py --dry      # diff; compila y prueba en un ESPEJO; no escribe nada
    python3 patch_ddos_reader.py --apply    # igual y, SOLO si todo pasa, escribe en el repo
    python3 patch_ddos_reader.py --check    # verifica lo aplicado: marcadores, compila el repo real, test

Verificacion (salvo --skip-compile):
  1. copia sniffer/include y sniffer/src a un directorio temporal, aplica ahi los cambios,
  2. compila main.cpp, config_manager.cpp y config_types.cpp con -fsyntax-only y los FLAGS REALES
     de sniffer/build-debug/CMakeFiles/sniffer.dir/flags.make (incluye -Wpedantic -Werror),
     con las rutas -I redirigidas al espejo,
  3. compila y EJECUTA el test nuevo (g++ -Wall -Wextra -Wpedantic -Werror ... -lbpf -pthread).
  Si el parcheado falla, recompila el original en el espejo para decir si el culpable es el
  entorno o el parche.

Idempotente: cada cambio lleva un marcador [DDOS-KREAD-D274:*]; reaplicar no cambia nada.
Precondicion: parche del loader aplicado (marcador DDOS-KAGG-D273:LOADER-HPP-API).
NO commitea.
"""
import argparse
import difflib
import json
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

TAG = "DDOS-KREAD-D274"

HEADER_REL = "sniffer/include/ddos_kernel_reader.hpp"
TEST_REL = "sniffer/tests/test_ddos_kernel_reader.cpp"
AGG_REL = "sniffer/include/ddos_kernel_agg.hpp"
LOADER_HPP_REL = "sniffer/include/ebpf_loader.hpp"
LOADER_MARKER = "DDOS-KAGG-D273:LOADER-HPP-API"
JSON_REL = "sniffer/config/sniffer.json"
FLAGS_MAKE_REL = "sniffer/build-debug/CMakeFiles/sniffer.dir/flags.make"
SYNTAX_SOURCES = [
    "sniffer/src/userspace/main.cpp",
    "sniffer/src/userspace/config_manager.cpp",
    "sniffer/src/userspace/config_types.cpp",
]

HEADER_TEXT = r'''// sniffer/include/ddos_kernel_reader.hpp
// [DDOS-KREAD-D274:HEADER]
// DAY274 -- hilo lector del agregador DDoS en-kernel: llama a DdosKernelAggregator::poll()
// cada T ms y vuelca las ventanas tumbling a un CSV para el harness de ajuste (Paso 4).
//
// Contrato:
//   - NO detecta nada: solo mide. Un fallo aqui nunca debe afectar a la captura.
//   - Header-only (no toca CMakeLists), igual que ddos_kernel_agg.hpp.
//   - stop() despierta al hilo al instante (condition_variable); no espera a T.
//   - stop() debe llamarse ANTES de liberar el loader eBPF: el fd del mapa muere con el.
//   - stop() no es seguro entre llamadas concurrentes (solo lo llama el hilo principal).
//   - La primera ventana (window_ms = 0) es lo contado desde la carga del programa
//     (baseline). Se escribe para que la suma de deltas cuadre con los contadores del
//     kernel; el harness la distingue por window_ms = 0. El resto llevan la duracion
//     real de la ventana, medida con CLOCK_MONOTONIC.
//   - Al parar se hace una ultima lectura (ventana parcial) para no perder lo contado
//     desde la ultima pasada.
//   - Solo se escriben victimas con delta > 0 (una ventana ociosa no produce filas), como
//     maximo kDdosMaxRowsPerWindow por ventana (las de mayor d_pkts; el resto se cuenta
//     en Stats::rows_truncated).
//
// CSV: win,ts_ms,window_ms,dst_ip,proto,d_pkts,d_bytes
//   win        indice de ventana dentro de esta ejecucion (1 = baseline)
//   ts_ms      reloj de pared (epoch, ms) al final de la lectura
//   window_ms  duracion real de la ventana (0 = baseline)
//   dst_ip     dotted quad (DdosKernelAggregator::ip_to_string)
//   proto      numero de protocolo IP (6 TCP, 17 UDP, 1 ICMP)
// El fichero se abre en append: cada ejecucion vuelve a empezar en win = 1.
#pragma once

#include "ddos_kernel_agg.hpp"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <exception>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <mutex>
#include <optional>
#include <string>
#include <system_error>
#include <thread>
#include <utility>

namespace sniffer {

inline constexpr std::size_t kDdosMaxRowsPerWindow = 4096;

// ---- Funciones puras (testeables sin kernel ni hilos) ---------------------------------

inline std::string ddos_csv_header() {
    return "win,ts_ms,window_ms,dst_ip,proto,d_pkts,d_bytes\n";
}

// Duracion de la ventana en ms, redondeada al mas cercano. 0 = baseline (o reloj inconsistente).
inline uint64_t ddos_window_ms(const DdosWindow& w) {
    if (w.t_start_ns == 0 || w.t_end_ns <= w.t_start_ns) return 0;
    return (w.t_end_ns - w.t_start_ns + 500000ull) / 1000000ull;
}

// Filas CSV de una ventana (las victimas ya vienen ordenadas por d_pkts desc).
inline std::string ddos_csv_rows(uint64_t win, uint64_t ts_ms, const DdosWindow& w,
                                 std::size_t max_rows = kDdosMaxRowsPerWindow) {
    const std::size_t n = std::min(w.victims.size(), max_rows);
    std::string out;
    out.reserve(n * 64);
    const std::string prefix = std::to_string(win) + ',' + std::to_string(ts_ms) + ',' +
                               std::to_string(ddos_window_ms(w)) + ',';
    for (std::size_t i = 0; i < n; ++i) {
        const DdosVictimDelta& v = w.victims[i];
        out += prefix;
        out += DdosKernelAggregator::ip_to_string(v.dst_ip);
        out += ',';
        out += std::to_string(v.proto);
        out += ',';
        out += std::to_string(v.d_pkts);
        out += ',';
        out += std::to_string(v.d_bytes);
        out += '\n';
    }
    return out;
}

// ---- Hilo lector ------------------------------------------------------------------------

class DdosKernelReader {
public:
    struct Stats {
        uint64_t windows = 0;         // lecturas correctas (incluye baseline y la parcial final)
        uint64_t rows = 0;            // filas escritas al CSV
        uint64_t rows_truncated = 0;  // victimas que no cupieron en kDdosMaxRowsPerWindow
        uint64_t read_errors = 0;     // lecturas del mapa fallidas (o excepciones)
        uint64_t counter_resets = 0;  // suma de DdosWindow::counter_resets
        uint64_t evicted = 0;         // suma de DdosWindow::evicted
    };

    // Intervalo valido: [100, 60000] ms; <= 0 -> 1000 (por defecto).
    static int clamp_interval_ms(int ms) {
        if (ms <= 0) return 1000;
        if (ms < 100) return 100;
        if (ms > 60000) return 60000;
        return ms;
    }

    DdosKernelReader(int map_fd, uint32_t max_entries, int interval_ms, std::string csv_path)
        : agg_(map_fd, max_entries),
          interval_ms_(clamp_interval_ms(interval_ms)),
          csv_path_(std::move(csv_path)) {}

    DdosKernelReader(const DdosKernelReader&) = delete;
    DdosKernelReader& operator=(const DdosKernelReader&) = delete;
    ~DdosKernelReader() { stop(); }

    int interval_ms() const { return interval_ms_; }
    const std::string& csv_path() const { return csv_path_; }

    // false si no hay ruta o no se puede abrir el CSV: el sniffer sigue sin el lector.
    bool start() {
        if (thread_.joinable()) return true;
        if (csv_path_.empty()) return false;
        if (!open_csv()) {
            out_.close();
            std::cerr << "[WARNING] DDoS kernel reader: no puedo abrir " << csv_path_ << std::endl;
            return false;
        }
        {
            std::lock_guard<std::mutex> lk(m_);
            stop_ = false;
        }
        thread_ = std::thread(&DdosKernelReader::loop, this);
        std::cout << "[INFO] DDoS kernel reader started: interval_ms=" << interval_ms_
                  << " csv=" << csv_path_ << std::endl;
        return true;
    }

    // Idempotente. Bloquea hasta que el hilo termina (ultima lectura incluida).
    void stop() {
        if (!thread_.joinable()) return;
        {
            std::lock_guard<std::mutex> lk(m_);
            stop_ = true;
        }
        cv_.notify_all();
        thread_.join();
        out_.close();
        const Stats s = stats();
        std::cout << "[INFO] DDoS kernel reader stopped: windows=" << s.windows
                  << " rows=" << s.rows << " rows_truncated=" << s.rows_truncated
                  << " read_errors=" << s.read_errors << " counter_resets=" << s.counter_resets
                  << " evicted=" << s.evicted << std::endl;
    }

    Stats stats() const {
        Stats s;
        s.windows = windows_.load();
        s.rows = rows_.load();
        s.rows_truncated = rows_truncated_.load();
        s.read_errors = read_errors_.load();
        s.counter_resets = counter_resets_.load();
        s.evicted = evicted_.load();
        return s;
    }

private:
    bool open_csv() {
        out_.clear();
        std::error_code ec;
        const auto sz = std::filesystem::file_size(csv_path_, ec);
        const bool need_header = static_cast<bool>(ec) || sz == 0;
        out_.open(csv_path_, std::ios::out | std::ios::app);
        if (!out_.is_open()) return false;
        if (need_header) {
            out_ << ddos_csv_header();
            out_.flush();
        }
        return static_cast<bool>(out_);
    }

    void loop() {
        using clock = std::chrono::steady_clock;
        const auto step = std::chrono::milliseconds(interval_ms_);
        poll_once();  // baseline: lo contado desde la carga del programa (window_ms = 0)
        auto next = clock::now();
        for (;;) {
            next += step;
            const auto now = clock::now();
            if (next < now) next = now;  // nos quedamos atras: no acumular rafagas de lecturas
            {
                std::unique_lock<std::mutex> lk(m_);
                if (cv_.wait_until(lk, next, [this] { return stop_; })) break;
            }
            poll_once();
        }
        poll_once();  // ultima ventana (parcial): no se pierde lo contado desde la ultima pasada
    }

    void poll_once() {
        try {
            std::optional<DdosWindow> w = agg_.poll();
            if (!w) {
                const uint64_t n = ++read_errors_;
                if (n == 1 || n % 60 == 0) {
                    std::cerr << "[WARNING] DDoS kernel reader: lectura del mapa fallida (errno="
                              << agg_.last_errno() << ", fallos=" << n << ")" << std::endl;
                }
                return;
            }
            const uint64_t win = ++windows_;
            counter_resets_ += w->counter_resets;
            evicted_ += w->evicted;
            if (w->victims.empty() || csv_failed_) return;
            const std::size_t n_rows = std::min(w->victims.size(), kDdosMaxRowsPerWindow);
            const uint64_t ts_ms = static_cast<uint64_t>(
                std::chrono::duration_cast<std::chrono::milliseconds>(
                    std::chrono::system_clock::now().time_since_epoch())
                    .count());
            out_ << ddos_csv_rows(win, ts_ms, *w);
            out_.flush();
            if (!out_) {
                csv_failed_ = true;
                std::cerr << "[WARNING] DDoS kernel reader: fallo escribiendo " << csv_path_
                          << "; dejo de escribir filas (sigo leyendo)" << std::endl;
                return;
            }
            rows_ += n_rows;
            rows_truncated_ += w->victims.size() - n_rows;
        } catch (const std::exception& e) {
            ++read_errors_;
            std::cerr << "[WARNING] DDoS kernel reader: excepcion: " << e.what() << std::endl;
        }
    }

    DdosKernelAggregator agg_;
    int interval_ms_;
    std::string csv_path_;
    std::ofstream out_;
    std::mutex m_;
    std::condition_variable cv_;
    bool stop_ = false;  // protegido por m_
    std::thread thread_;
    bool csv_failed_ = false;  // solo lo toca el hilo lector
    std::atomic<uint64_t> windows_{0};
    std::atomic<uint64_t> rows_{0};
    std::atomic<uint64_t> rows_truncated_{0};
    std::atomic<uint64_t> read_errors_{0};
    std::atomic<uint64_t> counter_resets_{0};
    std::atomic<uint64_t> evicted_{0};
};

}  // namespace sniffer
'''

TEST_TEXT = r'''// sniffer/tests/test_ddos_kernel_reader.cpp
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
'''


class Edit:
    """Insercion idempotente: `insert` va antes/despues de `anchor` (que debe aparecer UNA vez)."""

    def __init__(self, label, rel, anchor, insert, where):
        assert where in ("after", "before")
        self.label = label
        self.rel = rel
        self.anchor = anchor
        self.insert = insert
        self.where = where
        self.marker = "[%s:%s]" % (TAG, label)
        assert self.marker in insert, "el texto insertado de %s no lleva su marcador" % label


EDITS = [
    # ---- configuracion: capa 1 (parseo del JSON) -------------------------------------------
    Edit("CFG-MGR-HPP", "sniffer/include/config_manager.hpp",
         "    std::string ebpf_program;\n",
         "    // [%s:CFG-MGR-HPP] lector del agregador DDoS en-kernel (DAY274)\n"
         "    bool ddos_kernel_agg_enabled = false;\n"
         "    int ddos_kernel_agg_interval_ms = 1000;\n"
         "    std::string ddos_kernel_agg_csv_path;\n" % TAG,
         "after"),
    Edit("CFG-MGR-CPP", "sniffer/src/userspace/config_manager.cpp",
         '    kernel.ebpf_program = kernel_json.get("ebpf_program", "sniffer.bpf.o").asString();\n',
         "    // [%s:CFG-MGR-CPP] lector del agregador DDoS en-kernel (DAY274)\n"
         '    kernel.ddos_kernel_agg_enabled = kernel_json.get("ddos_kernel_agg_enabled", false).asBool();\n'
         '    kernel.ddos_kernel_agg_interval_ms = kernel_json.get("ddos_kernel_agg_interval_ms", 1000).asInt();\n'
         '    kernel.ddos_kernel_agg_csv_path = kernel_json.get("ddos_kernel_agg_csv_path", "").asString();\n' % TAG,
         "after"),
    # ---- configuracion: capa 2 (g_config) ----------------------------------------------------
    Edit("CFG-TYPES-H", "sniffer/include/config_types.h",
         "        std::string ebpf_program;\n",
         "        // [%s:CFG-TYPES-H] lector del agregador DDoS en-kernel (DAY274)\n"
         "        bool ddos_kernel_agg_enabled = false;\n"
         "        int ddos_kernel_agg_interval_ms = 1000;\n"
         "        std::string ddos_kernel_agg_csv_path;\n" % TAG,
         "after"),
    Edit("CFG-TYPES-CPP", "sniffer/src/userspace/config_types.cpp",
         "        config.kernel_space.ebpf_program = sniffer_config->kernel_space.ebpf_program;\n",
         "        // [%s:CFG-TYPES-CPP] lector del agregador DDoS en-kernel (DAY274)\n"
         "        config.kernel_space.ddos_kernel_agg_enabled = sniffer_config->kernel_space.ddos_kernel_agg_enabled;\n"
         "        config.kernel_space.ddos_kernel_agg_interval_ms = sniffer_config->kernel_space.ddos_kernel_agg_interval_ms;\n"
         "        config.kernel_space.ddos_kernel_agg_csv_path = sniffer_config->kernel_space.ddos_kernel_agg_csv_path;\n" % TAG,
         "after"),
    # ---- main.cpp ---------------------------------------------------------------------------
    Edit("MAIN-INC", "sniffer/src/userspace/main.cpp",
         '#include "ebpf_loader.hpp"\n',
         '#include "ddos_kernel_reader.hpp"  // [%s:MAIN-INC]\n' % TAG,
         "after"),
    Edit("MAIN-PTR", "sniffer/src/userspace/main.cpp",
         "sniffer::EbpfLoader* ebpf_loader_ptr = nullptr;\n",
         "sniffer::DdosKernelReader* ddos_reader_ptr = nullptr;  // [%s:MAIN-PTR]\n" % TAG,
         "after"),
    Edit("MAIN-START", "sniffer/src/userspace/main.cpp",
         "        while (g_running) {\n"
         "            std::this_thread::sleep_for(std::chrono::seconds(1));\n"
         "        }\n",
         "        // [%s:MAIN-START] Lector del agregador DDoS en-kernel (opcional, DAY274).\n"
         "        // Es una capa de MEDICION: un fallo aqui nunca tumba el sniffer.\n"
         "        if (g_config.kernel_space.ddos_kernel_agg_enabled) {\n"
         "            const int ddos_fd = ebpf_loader_ptr ? ebpf_loader_ptr->get_ddos_victims_fd() : -1;\n"
         "            if (ddos_fd < 0) {\n"
         '                std::cerr << "[WARNING] ddos_kernel_agg_enabled=true pero el mapa ddos_victims no esta "\n'
         '                             "disponible (objeto eBPF anterior al parche); lector DDoS desactivado"\n'
         "                          << std::endl;\n"
         "            } else if (g_config.kernel_space.ddos_kernel_agg_csv_path.empty()) {\n"
         '                std::cerr << "[WARNING] ddos_kernel_agg_csv_path vacio; lector DDoS desactivado"\n'
         "                          << std::endl;\n"
         "            } else {\n"
         "                ddos_reader_ptr = new sniffer::DdosKernelReader(\n"
         "                    ddos_fd, ebpf_loader_ptr->get_ddos_victims_max_entries(),\n"
         "                    g_config.kernel_space.ddos_kernel_agg_interval_ms,\n"
         "                    g_config.kernel_space.ddos_kernel_agg_csv_path);\n"
         "                if (!ddos_reader_ptr->start()) {\n"
         '                    std::cerr << "[WARNING] no se pudo arrancar el lector DDoS; sigo sin el"\n'
         "                              << std::endl;\n"
         "                    delete ddos_reader_ptr;\n"
         "                    ddos_reader_ptr = nullptr;\n"
         "                }\n"
         "            }\n"
         "        }\n"
         "\n" % TAG,
         "before"),
    Edit("MAIN-STOP", "sniffer/src/userspace/main.cpp",
         '        std::cout << "\\n[Cleanup] Stopping components..." << std::endl;\n',
         "\n"
         "        // [%s:MAIN-STOP] Parar el lector DDoS ANTES de liberar el loader:\n"
         "        // el fd del mapa ddos_victims se cierra con el (leerlo despues = fd invalido/reutilizado).\n"
         "        if (ddos_reader_ptr) {\n"
         "            ddos_reader_ptr->stop();\n"
         "            delete ddos_reader_ptr;\n"
         "            ddos_reader_ptr = nullptr;\n"
         "        }\n" % TAG,
         "after"),
    Edit("MAIN-EMERG", "sniffer/src/userspace/main.cpp",
         "        // Emergency cleanup\n",
         "        // [%s:MAIN-EMERG] mismo orden que en el cleanup normal: lector antes que el loader\n"
         "        if (ddos_reader_ptr) {\n"
         "            ddos_reader_ptr->stop();\n"
         "            delete ddos_reader_ptr;\n"
         "            ddos_reader_ptr = nullptr;\n"
         "        }\n" % TAG,
         "after"),
]

JSON_ANCHOR = '    "ebpf_program": "sniffer.bpf.o",\n'
JSON_KEY = '"ddos_kernel_agg_enabled"'
JSON_INSERT = (
    '    "ddos_kernel_agg_enabled": true,\n'
    '    "ddos_kernel_agg_interval_ms": 1000,\n'
    '    "ddos_kernel_agg_csv_path": "/vagrant/logs/lab/ddos_windows.csv",\n'
)


# --------------------------------------------------------------------------------------------
# plan: que habria que escribir (sin escribir nada)
# --------------------------------------------------------------------------------------------
def read_text(p):
    return p.read_bytes().decode("utf-8")


def write_text(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(text.encode("utf-8"))


def plan(root):
    """Devuelve (cambios, problemas, estado).
    cambios: rel -> (texto_viejo | None si el fichero es nuevo, texto_nuevo)
    estado : etiqueta -> True (ya aplicado) / False (pendiente)"""
    changes, problems, state = {}, [], {}
    texts, origs = {}, {}

    agg = root / AGG_REL
    if not agg.is_file():
        problems.append("falta %s (parche del agregador DAY273)" % AGG_REL)
    lh = root / LOADER_HPP_REL
    if not lh.is_file() or LOADER_MARKER not in read_text(lh):
        problems.append("el loader no expone ddos_victims: aplica antes patch_ebpf_loader_ddos.py "
                        "(falta el marcador %s en %s)" % (LOADER_MARKER, LOADER_HPP_REL))

    for rel, content in ((HEADER_REL, HEADER_TEXT), (TEST_REL, TEST_TEXT)):
        p = root / rel
        if not p.exists():
            changes[rel] = (None, content)
            state[rel] = False
        elif read_text(p) == content:
            state[rel] = True
        else:
            problems.append("%s ya existe y difiere de la version embebida: no lo piso "
                            "(revisalo o borralo y reaplica)" % rel)

    for e in EDITS:
        if e.rel not in texts:
            p = root / e.rel
            if not p.is_file():
                problems.append("falta %s" % e.rel)
                continue
            texts[e.rel] = origs[e.rel] = read_text(p)
        t = texts[e.rel]
        n_mark = t.count(e.marker)
        if n_mark == 1:
            state[e.label] = True
            continue
        if n_mark > 1:
            problems.append("%s: el marcador %s aparece %d veces" % (e.rel, e.marker, n_mark))
            continue
        n_anchor = t.count(e.anchor)
        if n_anchor != 1:
            problems.append("%s: el ancla de %s aparece %d veces (se esperaba 1):\n      %r"
                            % (e.rel, e.label, n_anchor, e.anchor))
            continue
        if e.where == "after":
            t = t.replace(e.anchor, e.anchor + e.insert, 1)
        else:
            t = t.replace(e.anchor, e.insert + e.anchor, 1)
        texts[e.rel] = t
        state[e.label] = False

    for rel, t in texts.items():
        if t != origs[rel]:
            changes[rel] = (origs[rel], t)
    return changes, problems, state


def plan_json(root):
    """(cambio | None, problemas, aplicado)"""
    p = root / JSON_REL
    if not p.is_file():
        return None, ["falta %s" % JSON_REL], False
    t = read_text(p)
    if JSON_KEY in t:
        return None, [], True
    n = t.count(JSON_ANCHOR)
    if n != 1:
        return None, ["%s: el ancla de kernel_space aparece %d veces (se esperaba 1)" % (JSON_REL, n)], False
    new = t.replace(JSON_ANCHOR, JSON_ANCHOR + JSON_INSERT, 1)
    try:
        json.loads(t)
    except ValueError:
        return (t, new), [], False  # el original ya no era JSON estricto: no podemos validar
    try:
        data = json.loads(new)
        assert data["kernel_space"]["ddos_kernel_agg_enabled"] is True
    except Exception as exc:  # noqa: BLE001
        return None, ["%s: el resultado no es JSON valido o no tiene las claves (%s)" % (JSON_REL, exc)], False
    return (t, new), [], False


def print_diff(rel, old, new):
    if old is None:
        print("NUEVO   : %s (%d lineas)" % (rel, new.count("\n")))
        return
    a = old.splitlines(keepends=True)
    b = new.splitlines(keepends=True)
    for line in difflib.unified_diff(a, b, "%s (antes)" % rel, "%s (despues)" % rel, n=2):
        sys.stdout.write(line if line.endswith("\n") else line + "\n")


# --------------------------------------------------------------------------------------------
# compilacion y test
# --------------------------------------------------------------------------------------------
def load_flags(root):
    fm = root / FLAGS_MAKE_REL
    if not fm.is_file():
        return None
    kv = {}
    for line in read_text(fm).splitlines():
        m = re.match(r"^(CXX_DEFINES|CXX_INCLUDES|CXX_FLAGS)\s*=\s*(.*)$", line)
        if m:
            kv[m.group(1)] = shlex.split(m.group(2))
    return kv.get("CXX_DEFINES", []) + kv.get("CXX_INCLUDES", []) + kv.get("CXX_FLAGS", [])


def retarget(flags, mirror):
    """-I<x>/sniffer/(include|src)[/...] -> -I<espejo>/sniffer/(include|src)[/...]"""
    out = []
    for tok in flags:
        m = re.match(r"^-I(.*)/sniffer/(include|src)(/.*)?$", tok)
        out.append("-I%s/sniffer/%s%s" % (mirror, m.group(2), m.group(3) or "") if m else tok)
    return out


def compile_sources(cxx, flags, base):
    def one(rel):
        cmd = shlex.split(cxx) + ["-fsyntax-only"] + flags + [str(base / rel)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        return rel, r.returncode, r.stdout + r.stderr

    with ThreadPoolExecutor(max_workers=len(SYNTAX_SOURCES)) as ex:
        return list(ex.map(one, SYNTAX_SOURCES))


def report_compile(results, label):
    ok = True
    for rel, rc, out in results:
        print("compile : %s %s: %s" % (label, rel.split("/")[-1], "OK" if rc == 0 else "FALLA"))
        if rc != 0:
            ok = False
            lines = out.strip().splitlines()
            for line in lines[:40]:
                print("    " + line)
            if len(lines) > 40:
                print("    ... (%d lineas mas)" % (len(lines) - 40))
    return ok


def build_and_run_test(cxx, base, tmp):
    exe = tmp / "test_ddos_kernel_reader"
    cmd = shlex.split(cxx) + ["-std=c++20", "-Wall", "-Wextra", "-Wpedantic", "-Werror",
                              "-I", str(base / "sniffer/include"), str(base / TEST_REL),
                              "-o", str(exe), "-lbpf", "-pthread"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        print("test    : COMPILACION FALLA")
        for line in (r.stdout + r.stderr).strip().splitlines()[:40]:
            print("    " + line)
        return False
    r = subprocess.run([str(exe)], capture_output=True, text=True, timeout=120)
    print("test    : %s" % (r.stdout.strip() or "(sin salida)"))
    if r.stderr.strip():
        for line in r.stderr.strip().splitlines()[:20]:
            print("    " + line)
    return r.returncode == 0


def verify_in_mirror(root, changes, cxx):
    flags = load_flags(root)
    if flags is None:
        print("ERROR: no encuentro %s; compila antes (make sniffer-build) o usa --skip-compile."
              % FLAGS_MAKE_REL)
        return False
    tmp = Path(tempfile.mkdtemp(prefix="ddos_reader_"))
    try:
        for sub in ("include", "src"):
            shutil.copytree(root / "sniffer" / sub, tmp / "sniffer" / sub, symlinks=True,
                            ignore=shutil.ignore_patterns("*.o", "*.a", "build*"))
        for rel, (_, new) in changes.items():
            write_text(tmp / rel, new)
        mflags = retarget(flags, str(tmp))
        print("compile : espejo en %s (flags reales de flags.make, con -Wpedantic -Werror)" % tmp)
        results = compile_sources(cxx, mflags, tmp)
        if not report_compile(results, "parcheado"):
            # diagnostico: restaurar el original en el espejo y recompilar
            for rel, (old, _) in changes.items():
                if old is None:
                    (tmp / rel).unlink()
                else:
                    write_text(tmp / rel, old)
            base_ok = report_compile(compile_sources(cxx, mflags, tmp), "baseline ")
            if not base_ok:
                print("compile : el BASELINE tampoco compila en el espejo: es el entorno/rutas relativas, "
                      "no el parche. Prueba --skip-compile y compila con make sniffer-build.")
            else:
                print("compile : el baseline compila y el parcheado no: el error es del parche.")
            return False
        return build_and_run_test(cxx, tmp, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------------------------
# modos
# --------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Hilo lector del agregador DDoS en-kernel (DAY274)")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry", action="store_true", help="diff + verificacion en espejo; no escribe")
    mode.add_argument("--apply", action="store_true", help="verifica en espejo y, si pasa, escribe")
    mode.add_argument("--check", action="store_true", help="verifica lo aplicado (marcadores, compila, test)")
    ap.add_argument("--cxx", default="g++", help="compilador (por defecto g++)")
    ap.add_argument("--skip-compile", action="store_true", help="no compilar ni ejecutar el test")
    ap.add_argument("--no-json", action="store_true", help="no tocar sniffer/config/sniffer.json")
    args = ap.parse_args()

    root = Path.cwd().resolve()
    if not (root / "sniffer").is_dir():
        print("ERROR: ejecuta desde la raiz del repo (aqui no hay sniffer/): %s" % root)
        return 2

    changes, problems, state = plan(root)
    jchange, jproblems, japplied = (None, [], True) if args.no_json else plan_json(root)
    problems += jproblems
    if problems:
        print("ERROR: no se puede continuar:")
        for p in problems:
            print("  - " + p)
        return 2

    pending = [k for k, v in state.items() if not v]
    json_pending = jchange is not None

    # ---------------- --check ----------------
    if args.check:
        counts = {}
        for e in EDITS:
            t = read_text(root / e.rel)
            counts[e.label] = t.count(e.marker)
        print("check   : marcadores %s" % counts)
        if pending or json_pending or any(v != 1 for v in counts.values()):
            print("check   : FALTA aplicar: %s%s" % (pending, " + sniffer.json" if json_pending else ""))
            return 1
        print("check   : estructura OK%s" % ("" if args.no_json else " (sniffer.json con las claves)"))
        if args.skip_compile:
            return 0
        flags = load_flags(root)
        if flags is None:
            print("ERROR: no encuentro %s (compila antes con make sniffer-build)" % FLAGS_MAKE_REL)
            return 2
        ok = report_compile(compile_sources(args.cxx, flags, root), "actual   ")
        tmp = Path(tempfile.mkdtemp(prefix="ddos_reader_chk_"))
        try:
            ok = build_and_run_test(args.cxx, root, tmp) and ok
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return 0 if ok else 2

    # ---------------- --dry / --apply ----------------
    if not changes and not json_pending:
        print("ya aplicado; nada que hacer.")
        return 0

    for rel, (old, new) in sorted(changes.items()):
        print_diff(rel, old, new)
    if json_pending:
        print_diff(JSON_REL, jchange[0], jchange[1])
    print()

    if not args.skip_compile:
        if not verify_in_mirror(root, changes, args.cxx):
            print("\nABORTADO: la verificacion fallo; no se ha escrito nada en el repo.")
            return 2
    else:
        print("compile : SALTADO (--skip-compile)")

    if args.dry:
        print("\n--dry: no se ha escrito nada.")
        return 0

    for rel, (_, new) in changes.items():
        write_text(root / rel, new)
    if json_pending:
        write_text(root / JSON_REL, jchange[1])
    print("\nAPLICADO: %s%s" % (", ".join(sorted(changes)), " + " + JSON_REL if json_pending else ""))
    print("Siguiente: `git diff --stat`, `--check`, `make sniffer-build` y relanzar el pipeline; "
          "el CSV sale en la ruta ddos_kernel_agg_csv_path. El patcher NO commitea.")
    print("Pendiente: cablear el test nuevo en CMakeLists/Makefile (como sniffer-ddos-agg-test).")
    return 0


if __name__ == "__main__":
    sys.exit(main())