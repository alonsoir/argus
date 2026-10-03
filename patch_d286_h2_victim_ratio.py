#!/usr/bin/env python3
"""DAY286 H2: campo 14 victim_rate_ratio = EWMA por victima con dos alfas (opcion B).
Toca: ddos_contract_v2.hpp (formula), ddos_victim_board.hpp (estado + publish),
ring_consumer.cpp (estampa), test_ddos_victim_board.cpp (caso 11).
Atomico, idempotente (marca [DDOS-H2-D286]). Uso: --check | --apply. No compila."""
import sys

R = "/vagrant/sniffer"
MARK = "[DDOS-H2-D286]"
CONTRACT = f"{R}/include/ddos_contract_v2.hpp"
BOARD = f"{R}/include/ddos_victim_board.hpp"
RC = f"{R}/src/userspace/ring_consumer.cpp"
TEST = f"{R}/tests/test_ddos_victim_board.cpp"

H2_BLOCK = """// [DDOS-H2-D286] H2: escalada por victima = pps_ventana / max(EWMA previa, suelo).
// Medida offline DAY286 (v4, opcion B) sobre ddos_windows.csv: dos alfas para que un
// ataque no envenene la linea base sin dejar falsos positivos permanentes.
inline constexpr double kVictimEwmaAlpha = 0.1;                      // por ventana
inline constexpr double kVictimEwmaAlphaAnom = kVictimEwmaAlpha / 60.0;  // clave caliente y anomala
inline constexpr double kVictimRatioHot = 5.0;                       // K
inline constexpr uint64_t kVictimWarmWindows = 30;                   // W: ventanas vistas
inline constexpr double kVictimPpsFloor = 10.0;                      // suelo, pps
inline constexpr uint64_t kVictimEvictWindows = 3600;                // 1 h sin aparecer -> se olvida

struct VictimEwmaState {
    double ewma = 0.0;
    uint64_t last_seq = 0;
    uint64_t seen = 0;  // ventanas en que la victima aparecio (delta > 0)
};

// Un paso por ventana en que la victima aparece. Las ventanas sin trafico entre medias
// cuentan como 0 (decaen con alpha). Devuelve el ratio de ESTA ventana contra la EWMA previa.
inline double victim_ewma_step(VictimEwmaState& s, uint64_t seq, double pps) noexcept {
    double prior = 0.0;
    if (s.seen > 0) {
        const uint64_t gap = (seq > s.last_seq) ? (seq - s.last_seq) : 1;
        if (gap <= kVictimEvictWindows) {
            prior = s.ewma;
            for (uint64_t i = 1; i < gap; ++i) prior *= (1.0 - kVictimEwmaAlpha);
        }
    }
    const double ratio = pps / (prior > kVictimPpsFloor ? prior : kVictimPpsFloor);
    const bool hot = s.seen >= kVictimWarmWindows && ratio >= kVictimRatioHot;
    const double a = hot ? kVictimEwmaAlphaAnom : kVictimEwmaAlpha;
    s.ewma = (1.0 - a) * prior + a * pps;
    s.last_seq = seq;
    s.seen += 1;
    return ratio;
}

"""

TEST_BLOCK = """    // 11. [DDOS-H2-D286] H2: escalada por victima (EWMA dos alfas, opcion B)
    {
        auto win1s = [](uint64_t i, uint64_t pkts, uint32_t ip) {
            DdosWindow w = make_window(i * 1'000'000'000ULL, (i + 1) * 1'000'000'000ULL);
            if (pkts) w.victims.push_back({ip, 17u, pkts, pkts * 482});
            return w;
        };
        // 11a. victima fria: ratio = pps / suelo = 100 / 10
        DdosVictimBoard h;
        h.publish_window(1, win1s(1, 100, GW));
        CHECK(std::fabs(h.lookup(GW, UDP).rate_ratio - 10.0f) < 1e-4f);
        // 11b. victima ausente en la ventana -> 0
        CHECK(h.lookup(DNS, UDP).rate_ratio == 0.0f);
        // 11c. 40 ventanas a 20 pps (EWMA 19,70, caliente) y ataque a 100 pps -> 5,075;
        //      la ventana siguiente sigue > 5 porque aprende con alpha/60 (con alpha seria 3,6)
        DdosVictimBoard k;
        for (uint64_t i = 1; i <= 40; ++i) k.publish_window(i, win1s(i, 20, GW));
        k.publish_window(41, win1s(41, 100, GW));
        const float r1 = k.lookup(GW, UDP).rate_ratio;
        k.publish_window(42, win1s(42, 100, GW));
        const float r2 = k.lookup(GW, UDP).rate_ratio;
        CHECK(r1 > 5.0f && r1 < 5.2f);
        CHECK(r2 > 5.0f);
        // 11d. 100 ventanas sin trafico: la EWMA decae a ~0 -> ratio = 100 / suelo
        k.publish_window(143, win1s(143, 100, GW));
        CHECK(std::fabs(k.lookup(GW, UDP).rate_ratio - 10.0f) < 0.01f);
        std::printf("H2: 11c r1=%.4f r2=%.4f\\n", static_cast<double>(r1), static_cast<double>(r2));
    }

"""

# (fichero, viejo, nuevo): reemplazo de texto exacto; 'viejo' debe aparecer 1 vez
SUBS = [
    (CONTRACT, "}  // namespace argus::ddos", H2_BLOCK + "}  // namespace argus::ddos"),
    (BOARD, '#include "ddos_kernel_agg.hpp"\n',
     '#include "ddos_kernel_agg.hpp"\n#include "ddos_contract_v2.hpp"  // [DDOS-H2-D286]\n'),
    (BOARD, "    uint64_t d_bytes = 0;\n};\n\nstruct DdosVictimSnapshot {",
     "    uint64_t d_bytes = 0;\n    float rate_ratio = 0.0f;  // [DDOS-H2-D286] escalada; 0 si ventana degenerada\n};\n\nstruct DdosVictimSnapshot {"),
    (BOARD, "    uint64_t age_ms = 0;  // edad del snapshot al consultar\n};",
     "    uint64_t age_ms = 0;  // edad del snapshot al consultar\n    float rate_ratio = 0.0f;  // [DDOS-H2-D286]\n};"),
    (BOARD,
     "        for (const auto& v : w.victims) {\n"
     "            s->by_key[ddos_victim_key(v.dst_ip, v.proto)] = DdosVictimCounts{v.d_pkts, v.d_bytes};\n"
     "        }\n"
     "        publish(std::move(s));",
     "        for (const auto& v : w.victims) {\n"
     "            const uint64_t key = ddos_victim_key(v.dst_ip, v.proto);\n"
     "            float ratio = 0.0f;  // [DDOS-H2-D286] solo con ventana de duracion > 0\n"
     "            if (s->window_ms > 0) {\n"
     "                const double pps = static_cast<double>(v.d_pkts) * 1000.0 / static_cast<double>(s->window_ms);\n"
     "                ratio = static_cast<float>(::argus::ddos::victim_ewma_step(ewma_[key], seq, pps));\n"
     "            }\n"
     "            s->by_key[key] = DdosVictimCounts{v.d_pkts, v.d_bytes, ratio};\n"
     "        }\n"
     "        if (seq % 60 == 0) evict_stale_ewma(seq);  // [DDOS-H2-D286] memoria acotada\n"
     "        publish(std::move(s));"),
    (BOARD, "            r.d_bytes = it->second.d_bytes;\n",
     "            r.d_bytes = it->second.d_bytes;\n            r.rate_ratio = it->second.rate_ratio;  // [DDOS-H2-D286]\n"),
    (BOARD, "    std::atomic<uint64_t> published_{0};\n};",
     "    std::atomic<uint64_t> published_{0};\n"
     "    // [DDOS-H2-D286] estado de la EWMA por victima. SOLO lo toca el hilo que llama a\n"
     "    // publish_window (el lector del kernel, escritor unico): sin cerrojo propio.\n"
     "    std::unordered_map<uint64_t, ::argus::ddos::VictimEwmaState> ewma_;\n"
     "    void evict_stale_ewma(uint64_t seq) {\n"
     "        for (auto it = ewma_.begin(); it != ewma_.end();) {\n"
     "            if (seq > it->second.last_seq + ::argus::ddos::kVictimEvictWindows) it = ewma_.erase(it);\n"
     "            else ++it;\n"
     "        }\n"
     "    }\n"
     "};"),
    (TEST, "#include <cstdio>\n", "#include <cmath>  // [DDOS-H2-D286]\n#include <cstdio>\n"),
    (TEST, "    if (g_fail) {\n", TEST_BLOCK + "    if (g_fail) {\n"),
]
RC_ANCHOR = "::argus::ddos::victim_pps(r.d_pkts, r.window_ms));"

def die(m):
    print(f"ABORTO: {m}")
    sys.exit(1)

mode = sys.argv[1] if len(sys.argv) > 1 else ""
if mode not in ("--check", "--apply"):
    die("uso: --check | --apply")

paths = [CONTRACT, BOARD, RC, TEST]
txt = {p: open(p).read() for p in paths}
marked = [p for p in paths if MARK in txt[p]]
if len(marked) == len(paths):
    print("YA APLICADO. Nada que hacer.")
    sys.exit(0)
if marked:
    die(f"aplicacion parcial previa: {marked}")

new = dict(txt)
for p, old, rep in SUBS:
    c = new[p].count(old)
    if c != 1:
        die(f"{p}: fragmento encontrado {c} veces (esperado 1):\n{old}")
    new[p] = new[p].replace(old, rep)

ls = new[RC].split("\n")
hits = [i for i, l in enumerate(ls) if l.strip() == RC_ANCHOR]
if len(hits) != 1:
    die(f"ancla de ring_consumer: {len(hits)} coincidencias (esperado 1)")
i = hits[0]
prev = ls[i - 1]
indent = prev[:len(prev) - len(prev.lstrip())]
ls.insert(i + 1, indent + f"ev.mutable_network_features()->mutable_ddos_embedded()->set_victim_rate_ratio(r.rate_ratio);  // {MARK}")
new[RC] = "\n".join(ls)

print("Plan:")
for p in paths:
    print(f"  {p}: {txt[p].count(chr(10))} -> {new[p].count(chr(10))} lineas, marcas {new[p].count(MARK)}")
print(f"  ring_consumer: insercion tras linea {i+1}: {ls[i].strip()}")
if mode == "--check":
    print("\n--check: no se escribe nada.")
    sys.exit(0)
for p in paths:
    open(p, "w").write(new[p])
print("\nAPLICADO.")
