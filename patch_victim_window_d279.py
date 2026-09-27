#!/usr/bin/env python3
"""
patch_victim_window_d279.py -- DAY279, opcion (a): la ventana por victima contada en el
kernel (mapa ddos_victims) llega al ml-detector DENTRO de cada NetworkSecurityEvent
(campo victim_window = 36). En el ml-detector solo se OBSERVA (log [VICTIM-WINDOW]):
no entra en ninguna cabeza ni en final_score.

Uso (raiz del repo):
  python3 patch_victim_window_d279.py --check   # no escribe; informa op a op
  python3 patch_victim_window_d279.py --apply   # atomico: o todas las ops o ninguna
Idempotente (marcadores [DDOS-VWIN-D279:*]). No commitea.
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path.cwd()


def flex(anchor):
    """Anclaje tolerante a espacios/saltos de linea: tokens literales unidos por \\s+."""
    return r"\s+".join(re.escape(t) for t in anchor.split())


# ---------------------------------------------------------------------------
# Ficheros nuevos
# ---------------------------------------------------------------------------
BOARD_HPP = r'''// sniffer/include/ddos_victim_board.hpp
// DAY279 -- tablero compartido de ventanas por victima (agregador DDoS en-kernel).
//
// El lector (DdosKernelReader) PUBLICA un snapshot por ventana; el RingBufferConsumer
// CONSULTA al construir cada NetworkSecurityEvent (campo victim_window). Lector y consumer
// no se conocen: comparten un shared_ptr<DdosVictimBoard> creado en main, asi que el orden
// de destruccion (lector antes que consumer) no deja punteros colgantes.
//
// Semantica (contrato DAY279):
//   - Sin snapshot publicado      -> lookup().have_snapshot = false (evento SIN victim_window).
//   - Snapshot y victima ausente  -> have_snapshot = true, d_pkts = d_bytes = 0.
//   - El snapshot guarda TODAS las victimas de la ventana (el tope kDdosMaxRowsPerWindow
//     es solo del CSV). La baseline (t_start_ns == 0) NO se publica: no es una tasa.
//   - Snapshot inmutable: quien tenga un shared_ptr viejo lo sigue leyendo entero.
#pragma once

#include "ddos_kernel_agg.hpp"

#include <atomic>
#include <chrono>
#include <cstdint>
#include <memory>
#include <mutex>
#include <unordered_map>

namespace sniffer {

struct DdosVictimCounts {
    uint64_t d_pkts = 0;
    uint64_t d_bytes = 0;
};

struct DdosVictimSnapshot {
    uint64_t seq = 0;           // n de ventana del lector
    uint64_t window_ms = 0;     // duracion real de la ventana
    uint64_t published_ns = 0;  // steady_clock en la publicacion
    std::unordered_map<uint64_t, DdosVictimCounts> by_key;
};

struct DdosVictimLookup {
    bool have_snapshot = false;
    uint64_t seq = 0;
    uint64_t window_ms = 0;
    uint64_t d_pkts = 0;
    uint64_t d_bytes = 0;
    uint64_t age_ms = 0;  // edad del snapshot al consultar
};

// Misma clave que el kernel: dst_ip NUMERICO (a<<24|b<<16|c<<8|d) + proto IANA.
inline uint64_t ddos_victim_key(uint32_t dst_ip, uint32_t proto) {
    return (static_cast<uint64_t>(dst_ip) << 32) | static_cast<uint64_t>(proto);
}

inline uint64_t ddos_steady_now_ns() {
    return static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
                                     std::chrono::steady_clock::now().time_since_epoch())
                                     .count());
}

class DdosVictimBoard {
public:
    void publish(std::shared_ptr<const DdosVictimSnapshot> s) {
        std::lock_guard<std::mutex> lk(m_);
        snap_ = std::move(s);
        published_.fetch_add(1, std::memory_order_relaxed);
    }

    void publish_window(uint64_t seq, const DdosWindow& w, uint64_t now_ns = ddos_steady_now_ns()) {
        auto s = std::make_shared<DdosVictimSnapshot>();
        s->seq = seq;
        s->window_ms = (w.t_end_ns > w.t_start_ns) ? (w.t_end_ns - w.t_start_ns) / 1'000'000ULL : 0;
        s->published_ns = now_ns;
        s->by_key.reserve(w.victims.size());
        for (const auto& v : w.victims) {
            s->by_key[ddos_victim_key(v.dst_ip, v.proto)] = DdosVictimCounts{v.d_pkts, v.d_bytes};
        }
        publish(std::move(s));
    }

    std::shared_ptr<const DdosVictimSnapshot> load() const {
        std::lock_guard<std::mutex> lk(m_);
        return snap_;
    }

    DdosVictimLookup lookup(uint32_t dst_ip, uint32_t proto,
                            uint64_t now_ns = ddos_steady_now_ns()) const {
        DdosVictimLookup r;
        const std::shared_ptr<const DdosVictimSnapshot> s = load();
        if (!s) return r;
        r.have_snapshot = true;
        r.seq = s->seq;
        r.window_ms = s->window_ms;
        r.age_ms = (now_ns >= s->published_ns) ? (now_ns - s->published_ns) / 1'000'000ULL : 0;
        const auto it = s->by_key.find(ddos_victim_key(dst_ip, proto));
        if (it != s->by_key.end()) {
            r.d_pkts = it->second.d_pkts;
            r.d_bytes = it->second.d_bytes;
        }
        return r;
    }

    uint64_t published() const { return published_.load(std::memory_order_relaxed); }

private:
    mutable std::mutex m_;
    std::shared_ptr<const DdosVictimSnapshot> snap_;
    std::atomic<uint64_t> published_{0};
};

}  // namespace sniffer
'''

BOARD_TEST = r'''// sniffer/tests/test_ddos_victim_board.cpp
// DAY279 -- tablero de ventanas por victima: snapshot, lookup, clave {ip,proto}, sin tope,
// reemplazo, inmutabilidad del snapshot vivo, edad, ventana degenerada y humo de
// concurrencia (coherencia interna del snapshot). Sin root ni kernel.
#include "ddos_victim_board.hpp"

#include <atomic>
#include <cstdio>
#include <thread>

using namespace sniffer;

static int g_fail = 0;
static int g_checks = 0;
#define CHECK(c)                                                                   \
    do {                                                                           \
        ++g_checks;                                                                \
        if (!(c)) {                                                                \
            std::fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #c);      \
            ++g_fail;                                                              \
        }                                                                          \
    } while (0)

static DdosWindow make_window(uint64_t t0, uint64_t t1) {
    DdosWindow w;
    w.t_start_ns = t0;
    w.t_end_ns = t1;
    return w;
}

int main() {
    constexpr uint32_t GW = 0xC0A86401u;   // 192.168.100.1 (victima del flood cic2)
    constexpr uint32_t DNS = 0x08080808u;  // 8.8.8.8
    constexpr uint32_t UDP = 17;
    constexpr uint32_t TCP = 6;

    // 1. Tablero vacio: sin snapshot (= lector apagado -> evento sin victim_window)
    {
        DdosVictimBoard e;
        const auto r = e.lookup(GW, UDP);
        CHECK(!r.have_snapshot);
        CHECK(e.published() == 0);
        CHECK(e.load() == nullptr);
    }

    DdosVictimBoard b;
    // 2. Ventana normal de 1 s: valores, edad
    {
        DdosWindow w = make_window(1'000'000'000ULL, 2'000'000'000ULL);
        w.victims.push_back({GW, UDP, 100, 48'200});
        w.victims.push_back({DNS, UDP, 2, 148});
        b.publish_window(7, w, 5'000'000'000ULL);
        const auto r = b.lookup(GW, UDP, 5'250'000'000ULL);
        CHECK(r.have_snapshot);
        CHECK(r.seq == 7);
        CHECK(r.window_ms == 1000);
        CHECK(r.d_pkts == 100);
        CHECK(r.d_bytes == 48'200);
        CHECK(r.age_ms == 250);
        const auto d = b.lookup(DNS, UDP, 5'000'000'000ULL);
        CHECK(d.d_pkts == 2);
        CHECK(d.d_bytes == 148);
        CHECK(d.age_ms == 0);
        // 3. Misma IP, otro proto -> 0 (la clave es {ip, proto}, como en el kernel)
        const auto t = b.lookup(GW, TCP);
        CHECK(t.have_snapshot);
        CHECK(t.d_pkts == 0);
        CHECK(t.d_bytes == 0);
        // 4. IP no vista con snapshot presente -> 0, pero have_snapshot = true
        const auto u = b.lookup(0x0A000001u, UDP);
        CHECK(u.have_snapshot);
        CHECK(u.d_pkts == 0);
        // 7. Reloj por detras de la publicacion -> edad 0 (sin underflow)
        const auto early = b.lookup(GW, UDP, 4'000'000'000ULL);
        CHECK(early.age_ms == 0);
    }
    // 5. Sin tope: 5000 victimas, todas consultables (el tope es solo del CSV)
    {
        DdosWindow w = make_window(2'000'000'000ULL, 3'000'000'000ULL);
        for (uint32_t i = 0; i < 5000; ++i) w.victims.push_back({0x0A000000u + i, UDP, 5000u - i, 64});
        b.publish_window(8, w, 6'000'000'000ULL);
        const auto last = b.lookup(0x0A000000u + 4999u, UDP, 6'000'000'000ULL);
        CHECK(last.seq == 8);
        CHECK(last.d_pkts == 1);
        CHECK(b.load()->by_key.size() == 5000);
    }
    // 6. Reemplazo + inmutabilidad: una ventana vacia es valida (todo a 0) y el snapshot
    //    viejo sigue entero para quien lo tenga
    {
        const auto held = b.load();
        b.publish_window(9, make_window(3'000'000'000ULL, 4'000'000'000ULL), 7'000'000'000ULL);
        const auto r = b.lookup(GW, UDP, 7'000'000'000ULL);
        CHECK(r.have_snapshot);
        CHECK(r.seq == 9);
        CHECK(r.d_pkts == 0);
        CHECK(held->seq == 8);
        CHECK(held->by_key.size() == 5000);
        CHECK(b.published() == 3);
    }
    // 8. Ventana degenerada (t_end <= t_start) -> window_ms = 0
    {
        DdosVictimBoard g;
        g.publish_window(1, make_window(5'000'000'000ULL, 5'000'000'000ULL));
        CHECK(g.lookup(GW, UDP).window_ms == 0);
    }
    // 9. Concurrencia: un publicador y un lector; cada snapshot i lleva d_pkts == seq == i.
    //    Si el lector viera un snapshot a medio construir, d_pkts != seq.
    {
        DdosVictimBoard c;
        std::atomic<bool> stop{false};
        std::atomic<uint64_t> incoherent{0};
        std::atomic<uint64_t> reads{0};
        std::thread reader([&] {
            while (!stop.load()) {
                const auto r = c.lookup(GW, UDP);
                if (r.have_snapshot) {
                    reads.fetch_add(1);
                    if (r.d_pkts != r.seq) incoherent.fetch_add(1);
                }
            }
        });
        for (uint64_t i = 1; i <= 20000; ++i) {
            DdosWindow w = make_window(i * 1'000'000ULL, (i + 1) * 1'000'000ULL);
            w.victims.push_back({GW, UDP, i, i * 482});
            c.publish_window(i, w);
        }
        stop.store(true);
        reader.join();
        CHECK(incoherent.load() == 0);
        CHECK(c.lookup(GW, UDP).seq == 20000);
        std::printf("concurrencia: %llu lecturas con snapshot, %llu incoherentes\n",
                    static_cast<unsigned long long>(reads.load()),
                    static_cast<unsigned long long>(incoherent.load()));
    }
    // 10. La IP que se estampara en el evento: mismo formateo que el CSV del lector
    CHECK(DdosKernelAggregator::ip_to_string(GW) == "192.168.100.1");

    if (g_fail) {
        std::fprintf(stderr, "test_ddos_victim_board: %d/%d FALLOS\n", g_fail, g_checks);
        return 1;
    }
    std::printf("test_ddos_victim_board: OK (%d checks)\n", g_checks);
    return 0;
}
'''

# ---------------------------------------------------------------------------
# Payloads de insercion
# ---------------------------------------------------------------------------
PROTO_MSG = '''// [DDOS-VWIN-D279:PROTO-MSG] Agregado por victima contado en el kernel (mapa ddos_victims,
// XDP), independiente del ring buffer: el contador es exacto aunque el ring pierda eventos.
// Sin campo victim_window en el evento = lector apagado o sin ventana publicada.
// Con campo y d_pkts = 0 = el lector funciona y esa victima no recibio nada en la ventana.
message VictimWindow {
  string victim_ip       = 1;  // = destination_ip del evento
  uint32 protocol        = 2;  // IANA (17 = UDP)
  uint64 d_pkts          = 3;  // paquetes a {victim_ip, protocol} en la ultima ventana cerrada
  uint64 d_bytes         = 4;
  uint64 window_ms       = 5;  // duracion real de esa ventana
  uint64 window_seq      = 6;  // n de ventana del lector
  uint64 snapshot_age_ms = 7;  // edad del snapshot al estampar el evento
}

'''

PROTO_FIELD = '''
  // [DDOS-VWIN-D279:PROTO-FIELD] ventana por victima del kernel (DAY279, opcion a)
  VictimWindow victim_window = 36;'''

STAMP_DEF = '''// [DDOS-VWIN-D279:STAMP-DEF] Estampa en el evento la ventana por victima contada en el
// kernel (mapa ddos_victims). Sin tablero o sin snapshot publicado -> el evento sale SIN
// victim_window (= lector apagado). Con snapshot y victima ausente -> d_pkts = 0.
void RingBufferConsumer::stamp_victim_window(protobuf::NetworkSecurityEvent& ev,
                                             const SimpleEvent& e) const {
    if (!victim_board_) return;
    const uint32_t dst = static_cast<uint32_t>(e.dst_ip);
    const uint32_t proto = static_cast<uint32_t>(e.protocol);
    const ::sniffer::DdosVictimLookup r = victim_board_->lookup(dst, proto);
    if (!r.have_snapshot) return;
    auto* vw = ev.mutable_victim_window();
    vw->set_victim_ip(::sniffer::DdosKernelAggregator::ip_to_string(dst));
    vw->set_protocol(proto);
    vw->set_d_pkts(r.d_pkts);
    vw->set_d_bytes(r.d_bytes);
    vw->set_window_ms(r.window_ms);
    vw->set_window_seq(r.seq);
    vw->set_snapshot_age_ms(r.age_ms);
}

'''

ML_LOG = '''

        // [DDOS-VWIN-D279:ML-LOG] senal agregada por victima (kernel). SOLO observacion:
        // no entra en ninguna cabeza ni en final_score (DAY279, paso 1 de la opcion a).
        if (event.has_victim_window()) {
            const auto& vw = event.victim_window();
            logger_->info("[VICTIM-WINDOW] event={}, victim={}, proto={}, d_pkts={}, d_bytes={}, window_ms={}, seq={}, age_ms={}",
                          event.event_id(), vw.victim_ip(), vw.protocol(), vw.d_pkts(), vw.d_bytes(),
                          vw.window_ms(), vw.window_seq(), vw.snapshot_age_ms());
        } else {
            logger_->info("[VICTIM-WINDOW] event={}, absent", event.event_id());
        }'''

MAKE_TARGET = (
    "\n\n.PHONY: sniffer-ddos-board-test\n"
    "# [DDOS-VWIN-D279:MAKE-TEST] tablero de ventanas por victima (snapshot + lookup, sin root ni kernel)\n"
    "sniffer-ddos-board-test:\n"
    "\t@echo \"🧪 test_ddos_victim_board (snapshot + lookup, sin root ni kernel)...\"\n"
    "\t@vagrant ssh -c \"cd $(SNIFFER_BUILD_DIR) && cmake . > /dev/null && cmake --build . "
    "--target test_ddos_victim_board && ctest -R test_ddos_victim_board --output-on-failure\""
)

# ---------------------------------------------------------------------------
# Operaciones: (id, fichero, tipo, regex, payload, marcador)
#   after   -> inserta payload tras el anclaje (extendido hasta fin de linea)
#   before  -> inserta payload antes del anclaje
#   replace -> sustituye el anclaje por payload (el marcador va dentro del payload)
#   cmakedup-> duplica el bloque del test del lector con otro nombre
# ---------------------------------------------------------------------------
RD = "sniffer/include/ddos_kernel_reader.hpp"
RCH = "sniffer/include/ring_consumer.hpp"
RCC = "sniffer/src/userspace/ring_consumer.cpp"
MAIN = "sniffer/src/userspace/main.cpp"
PROTO = "protobuf/network_security.proto"
ZH = "ml-detector/src/zmq_handler.cpp"
CM = "sniffer/CMakeLists.txt"
MK = "Makefile"

OPS = [
    # --- proto
    ("proto-msg", PROTO, "before", flex("message NetworkSecurityEvent {"), PROTO_MSG,
     "[DDOS-VWIN-D279:PROTO-MSG]"),
    ("proto-field", PROTO, "after", flex("DetectionProvenance provenance = 35;"), PROTO_FIELD,
     "[DDOS-VWIN-D279:PROTO-FIELD]"),
    # --- lector
    ("reader-inc", RD, "after", flex('#include "ddos_kernel_agg.hpp"'),
     '\n#include "ddos_victim_board.hpp"  // [DDOS-VWIN-D279:READER-INC]',
     "[DDOS-VWIN-D279:READER-INC]"),
    ("reader-setter", RD, "after", flex("const std::string& csv_path() const { return csv_path_; }"),
     "\n\n    // [DDOS-VWIN-D279:SET-BOARD] tablero compartido con el RingBufferConsumer. Llamar ANTES de start().\n"
     "    void set_board(std::shared_ptr<DdosVictimBoard> board) { board_ = std::move(board); }",
     "[DDOS-VWIN-D279:SET-BOARD]"),
    ("reader-csv-optional", RD, "replace",
     flex("if (csv_path_.empty()) return false;") + r"\s+" + flex("if (!open_csv()) {"),
     "// [DDOS-VWIN-D279:CSV-OPTIONAL] el CSV es salida de laboratorio, no condicion de la senal\n"
     "        if (!csv_path_.empty() && !open_csv()) {",
     "[DDOS-VWIN-D279:CSV-OPTIONAL]"),
    ("reader-publish", RD, "replace", flex("if (w->victims.empty() || csv_failed_) return;"),
     "// [DDOS-VWIN-D279:PUBLISH] snapshot COMPLETO (sin tope CSV); la baseline (t_start_ns == 0) no es tasa\n"
     "            if (board_ && w->t_start_ns != 0) board_->publish_window(win, *w);\n"
     "            if (w->victims.empty() || csv_failed_ || csv_path_.empty()) return;",
     "[DDOS-VWIN-D279:PUBLISH]"),
    ("reader-member", RD, "after", flex("std::string csv_path_;"),
     "\n    std::shared_ptr<DdosVictimBoard> board_;  // [DDOS-VWIN-D279:BOARD-MEMBER]",
     "[DDOS-VWIN-D279:BOARD-MEMBER]"),
    # --- ring consumer (header)
    ("rc-inc", RCH, "after", flex('#include "ml_defender_features.hpp"'),
     '\n#include "ddos_victim_board.hpp"  // [DDOS-VWIN-D279:RC-INC]',
     "[DDOS-VWIN-D279:RC-INC]"),
    ("rc-setter", RCH, "before", r"(?m)^[ \t]*private:[ \t]*$",
     "    // [DDOS-VWIN-D279:RC-SETTER] tablero de ventanas por victima (agregador en-kernel).\n"
     "    // Llamar ANTES de start(): el puntero se fija una vez y despues solo se lee.\n"
     "    void set_victim_board(std::shared_ptr<::sniffer::DdosVictimBoard> board) {\n"
     "        victim_board_ = std::move(board);\n"
     "    }\n\n",
     "[DDOS-VWIN-D279:RC-SETTER]"),
    ("rc-stamp-decl", RCH, "after", flex("void send_fast_alert(const SimpleEvent& event);"),
     "\n    // [DDOS-VWIN-D279:RC-STAMP-DECL]\n"
     "    void stamp_victim_window(protobuf::NetworkSecurityEvent& ev, const SimpleEvent& e) const;",
     "[DDOS-VWIN-D279:RC-STAMP-DECL]"),
    ("rc-member", RCH, "after", flex("FastDetectorConfig fast_detector_config_;"),
     "\n    std::shared_ptr<::sniffer::DdosVictimBoard> victim_board_;  // [DDOS-VWIN-D279:RC-MEMBER]",
     "[DDOS-VWIN-D279:RC-MEMBER]"),
    # --- ring consumer (cpp)
    ("rc-stamp-def", RCC, "before", flex("void RingBufferConsumer::send_fast_alert(const SimpleEvent& event) {"),
     STAMP_DEF, "[DDOS-VWIN-D279:STAMP-DEF]"),
    ("rc-stamp-main", RCC, "after", flex("time_window->set_sequence_number(event.timestamp);"),
     "\n\n    // [DDOS-VWIN-D279:STAMP-MAIN] ventana por victima (kernel) -> evento\n"
     "    stamp_victim_window(proto_event, event);",
     "[DDOS-VWIN-D279:STAMP-MAIN]"),
    ("rc-stamp-fast", RCC, "after", flex("alert.set_originating_node_id(config_.node_id);"),
     "\n        stamp_victim_window(alert, event);  // [DDOS-VWIN-D279:STAMP-FAST]",
     "[DDOS-VWIN-D279:STAMP-FAST]"),
    # --- main
    ("main-board", MAIN, "after", flex("sniffer::DdosKernelReader* ddos_reader_ptr = nullptr;"),
     "\n// [DDOS-VWIN-D279:MAIN-BOARD] tablero compartido lector->consumer (vive mientras alguno lo tenga)\n"
     "std::shared_ptr<sniffer::DdosVictimBoard> g_ddos_victim_board = std::make_shared<sniffer::DdosVictimBoard>();",
     "[DDOS-VWIN-D279:MAIN-BOARD]"),
    ("main-rc", MAIN, "after", flex("auto& ring_consumer = *ring_consumer_ptr;"),
     "\n        ring_consumer.set_victim_board(g_ddos_victim_board);  // [DDOS-VWIN-D279:MAIN-RC]",
     "[DDOS-VWIN-D279:MAIN-RC]"),
    ("main-csv-optional", MAIN, "replace",
     flex("} else if (g_config.kernel_space.ddos_kernel_agg_csv_path.empty()) {") + r".*?" + flex("} else {"),
     "} else {  // [DDOS-VWIN-D279:MAIN-CSV-OPTIONAL] sin ruta CSV el lector sigue publicando al tablero",
     "[DDOS-VWIN-D279:MAIN-CSV-OPTIONAL]"),
    ("main-reader-board", MAIN, "after", flex("g_config.kernel_space.ddos_kernel_agg_csv_path);"),
     "\n                ddos_reader_ptr->set_board(g_ddos_victim_board);  // [DDOS-VWIN-D279:MAIN-READER]",
     "[DDOS-VWIN-D279:MAIN-READER]"),
    # --- ml-detector: solo observacion
    ("ml-log", ZH, "after", r'logger_->info\("\[DUAL-SCORE\].*?score_divergence\);', ML_LOG,
     "[DDOS-VWIN-D279:ML-LOG]"),
    # --- build del test
    ("cmake-test", CM, "cmakedup",
     r'[ \t]*add_executable\(test_ddos_kernel_reader\b.*?message\(STATUS "[^"\n]*test_ddos_kernel_reader[^\n]*\n',
     None, "test_ddos_victim_board"),
    ("make-test", MK, "after",
     flex('--target test_ddos_kernel_reader && ctest -R test_ddos_kernel_reader --output-on-failure"'),
     MAKE_TARGET, "[DDOS-VWIN-D279:MAKE-TEST]"),
]

NEW_FILES = [
    ("sniffer/include/ddos_victim_board.hpp", BOARD_HPP),
    ("sniffer/tests/test_ddos_victim_board.cpp", BOARD_TEST),
]


def apply_op(text, kind, rx, payload, marker):
    """Devuelve (nuevo_texto, estado). estado: 'ya', 'ok' o 'FALLO: ...'."""
    if marker in text:
        return text, "ya aplicado"
    flags = re.DOTALL if kind in ("replace", "cmakedup") or ".*?" in rx else 0
    if kind == "after":
        rx = rx + r"[^\n]*"
    matches = list(re.finditer(rx, text, flags))
    if len(matches) != 1:
        return text, "FALLO: el anclaje aparece %d veces (se exige 1)" % len(matches)
    m = matches[0]
    if kind == "after":
        return text[:m.end()] + payload + text[m.end():], "ok"
    if kind == "before":
        return text[:m.start()] + payload + text[m.start():], "ok"
    if kind == "replace":
        return text[:m.start()] + payload + text[m.end():], "ok"
    if kind == "cmakedup":
        block = m.group(0).replace("test_ddos_kernel_reader", "test_ddos_victim_board")
        block = re.sub(r'message\(STATUS "[^"\n]*"\)',
                       'message(STATUS "Unit Test: test_ddos_victim_board configured '
                       '(DAY 279 - tablero de ventanas por victima) [DDOS-VWIN-D279:CMAKE-TEST]")',
                       block, count=1)
        return text[:m.end()] + "\n" + block + text[m.end():], "ok"
    return text, "FALLO: tipo desconocido " + kind


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    contents, originals, failed = {}, {}, False
    for _, path, *_ in OPS:
        p = ROOT / path
        if path not in contents:
            if not p.is_file():
                print("FALLO: no existe %s (ejecuta desde la raiz del repo)" % path)
                return 2
            contents[path] = originals[path] = p.read_text(encoding="utf-8")

    for op_id, path, kind, rx, payload, marker in OPS:
        new, st = apply_op(contents[path], kind, rx, payload, marker)
        contents[path] = new
        print("  %-22s %-40s %s" % (op_id, path, st))
        failed |= st.startswith("FALLO")

    new_files = {}
    for path, body in NEW_FILES:
        p = ROOT / path
        if p.exists():
            same = p.read_text(encoding="utf-8") == body
            st = "ya existe (identico)" if same else "FALLO: existe y DIFIERE"
            failed |= not same
        else:
            new_files[path] = body
            st = "nuevo"
        print("  %-22s %-40s %s" % ("new-file", path, st))

    if failed:
        print("\nABORTO: alguna op falla; no se ha escrito nada.")
        return 1
    changed = [p for p in contents if contents[p] != originals[p]]
    if a.check:
        print("\n--check OK: %d ficheros a modificar, %d ficheros nuevos. Nada escrito."
              % (len(changed), len(new_files)))
        return 0
    for path in changed:
        (ROOT / path).write_text(contents[path], encoding="utf-8")
    for path, body in new_files.items():
        (ROOT / path).write_text(body, encoding="utf-8")
    print("\n--apply OK: %d modificados, %d nuevos. No commiteado." % (len(changed), len(new_files)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
