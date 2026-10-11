// sniffer/tests/test_ddos_victim_board.cpp
// DAY279 -- tablero de ventanas por victima: snapshot, lookup, clave {ip,proto}, sin tope,
// reemplazo, inmutabilidad del snapshot vivo, edad, ventana degenerada y humo de
// concurrencia (coherencia interna del snapshot). Sin root ni kernel.
#include "ddos_victim_board.hpp"

#include <atomic>
#include <cmath>  // [DDOS-H2-D286]
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

    // 11. [DDOS-H2-D286] H2: escalada por victima (EWMA dos alfas, opcion B)
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
        //      la ventana siguiente sigue > 5 porque entra en bajo_presion (alfa lento) [DDOS-HYST-D291]
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
        std::printf("H2: 11c r1=%.4f r2=%.4f\n", static_cast<double>(r1), static_cast<double>(r2));
    }

    // 12. [DDOS-HYST-D291] histeresis de la EWMA por victima (defectos: k_in 3, k_out 1,5, tau 3600 s)
    {
        auto win1s = [](uint64_t i, uint64_t pkts, uint32_t ip) {
            DdosWindow w = make_window(i * 1'000'000'000ULL, (i + 1) * 1'000'000'000ULL);
            if (pkts) w.victims.push_back({ip, 17u, pkts, pkts * 482});
            return w;
        };
        // 12a. piloto DAY291: base 10 pps (40 ventanas), ventana parcial a 48 y ataque de 60 pps
        //      (70 en la victima) con una ventana de jitter a 69: el ratio se SOSTIENE > 6 los
        //      90 s (sin histeresis colapsaba a ~1 en 20 s)
        DdosVictimBoard e;
        for (uint64_t i = 1; i <= 40; ++i) e.publish_window(i, win1s(i, 10, GW));
        e.publish_window(41, win1s(41, 48, GW));
        const float r_ent = e.lookup(GW, UDP).rate_ratio;
        float r_min = 1e9f;
        for (uint64_t i = 42; i <= 130; ++i) {
            e.publish_window(i, win1s(i, (i == 45) ? 69 : 70, GW));
            const float r = e.lookup(GW, UDP).rate_ratio;
            if (r < r_min) r_min = r;
        }
        CHECK(std::fabs(r_ent - 4.8f) < 1e-3f);
        CHECK(r_min > 6.0f);
        // 12b. el ataque cae a la base: sale (ratio < 1,5) y una subida sostenida de 2x se absorbe
        //      con alfa normal; si siguiera en bajo_presion el ratio quedaria ~1,75
        e.publish_window(131, win1s(131, 10, GW));
        const float r_sal = e.lookup(GW, UDP).rate_ratio;
        for (uint64_t i = 132; i <= 161; ++i) e.publish_window(i, win1s(i, 20, GW));
        const float r_2x = e.lookup(GW, UDP).rate_ratio;
        CHECK(r_sal < 1.5f);
        CHECK(r_2x < 1.1f);
        // 12c. clave fria (< 30 ventanas vistas) NO entra: 60 pps se absorben como antes
        DdosVictimBoard c;
        for (uint64_t i = 1; i <= 10; ++i) c.publish_window(i, win1s(i, 10, DNS));
        for (uint64_t i = 11; i <= 30; ++i) c.publish_window(i, win1s(i, 60, DNS));
        const float r_fria = c.lookup(DNS, UDP).rate_ratio;
        CHECK(r_fria < 1.2f);
        // 12d. validacion de parametros: defectos validos; reglas cruzadas y rangos
        ::argus::ddos::VictimEwmaParams p;
        CHECK(::argus::ddos::victim_ewma_params_ok(p));
        p.k_out = 3.0;
        CHECK(!::argus::ddos::victim_ewma_params_ok(p));
        p = {};
        p.tau_s = 30.0;
        CHECK(!::argus::ddos::victim_ewma_params_ok(p));
        p = {};
        p.alpha = 0.01;
        p.tau_s = 60.0;
        CHECK(!::argus::ddos::victim_ewma_params_ok(p));
        p = {};
        p.alpha = 0.0;
        CHECK(!::argus::ddos::victim_ewma_params_ok(p));
        std::printf("HYST: 12a r_ent=%.4f r_min=%.4f 12b r_sal=%.4f r_2x=%.4f 12c r_fria=%.4f\n",
                    static_cast<double>(r_ent), static_cast<double>(r_min), static_cast<double>(r_sal),
                    static_cast<double>(r_2x), static_cast<double>(r_fria));
    }

    if (g_fail) {
        std::fprintf(stderr, "test_ddos_victim_board: %d/%d FALLOS\n", g_fail, g_checks);
        return 1;
    }
    std::printf("test_ddos_victim_board: OK (%d checks)\n", g_checks);
    return 0;
}
