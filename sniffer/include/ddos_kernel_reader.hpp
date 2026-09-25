// sniffer/include/ddos_kernel_reader.hpp
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
#include "ddos_victim_board.hpp"  // [DDOS-VWIN-D279:READER-INC]

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

    // [DDOS-VWIN-D279:SET-BOARD] tablero compartido con el RingBufferConsumer. Llamar ANTES de start().
    void set_board(std::shared_ptr<DdosVictimBoard> board) { board_ = std::move(board); }

    // false si no hay ruta o no se puede abrir el CSV: el sniffer sigue sin el lector.
    bool start() {
        if (thread_.joinable()) return true;
        // [DDOS-VWIN-D279:CSV-OPTIONAL] el CSV es salida de laboratorio, no condicion de la senal
        if (!csv_path_.empty() && !open_csv()) {
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
            // [DDOS-VWIN-D279:PUBLISH] snapshot COMPLETO (sin tope CSV); la baseline (t_start_ns == 0) no es tasa
            if (board_ && w->t_start_ns != 0) board_->publish_window(win, *w);
            if (w->victims.empty() || csv_failed_ || csv_path_.empty()) return;
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
    std::shared_ptr<DdosVictimBoard> board_;  // [DDOS-VWIN-D279:BOARD-MEMBER]
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
