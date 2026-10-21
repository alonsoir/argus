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
    {   // 14. [DDOS-ESTADO-ARRANQUE-D299] sellado sin foto del agregador (plazo de arranque)
        using ::sniffer::sello_estado_victima;
        using E = ::argus::ddos::VictimEwmaEstado;
        const uint64_t T0 = 1000000000ULL, PLAZO = 5000000000ULL;
        ::sniffer::DdosVictimBoard b;
        // 14a sin plazo marcado (agregador apagado o lector sin arrancar): no se sella
        auto r = b.lookup(0x0A000001u, 17u, T0);
        CHECK(!r.have_snapshot && !r.en_arranque && !r.arranque_vencido);
        CHECK(!sello_estado_victima(r).has_value());
        // 14b sin foto dentro del plazo: FRIO
        b.marcar_arranque(T0, PLAZO);
        r = b.lookup(0x0A000001u, 17u, T0 + PLAZO - 1);
        CHECK(r.en_arranque && !r.arranque_vencido);
        CHECK(sello_estado_victima(r) == std::optional<E>(E::Frio));
        CHECK(b.frio_arranque() == 1);
        // 14c plazo vencido sin foto: no se sella, vencido
        r = b.lookup(0x0A000001u, 17u, T0 + PLAZO);
        CHECK(!r.en_arranque && r.arranque_vencido);
        CHECK(!sello_estado_victima(r).has_value());
        // 14d plazo borrado (el lector no arranco): no se sella
        b.borrar_arranque();
        r = b.lookup(0x0A000001u, 17u, T0 + 1);
        CHECK(!r.en_arranque && !r.arranque_vencido && !sello_estado_victima(r).has_value());
        // 14e llega la foto dentro del plazo: manda la foto (victima ausente = NORMAL, contrato DAY298)
        b.marcar_arranque(T0, PLAZO);
        auto s = std::make_shared<::sniffer::DdosVictimSnapshot>();
        s->seq = 1;
        s->window_ms = 1000;
        s->published_ns = T0;
        b.publish(s);
        r = b.lookup(0x0A000001u, 17u, T0 + 1000);
        CHECK(r.have_snapshot && !r.en_arranque && !r.arranque_vencido);
        CHECK(sello_estado_victima(r) == std::optional<E>(E::Normal));
        CHECK(b.frio_arranque() == 1);
        // 14f con foto, el estado del tablero pasa tal cual
        ::sniffer::DdosVictimLookup f;
        f.have_snapshot = true;
        f.window_ms = 1000;
        f.estado = E::BajoPresion;
        CHECK(sello_estado_victima(f) == std::optional<E>(E::BajoPresion));
        std::printf("ESTADO-ARRANQUE: 14a-14f frio_arranque=%llu\n",
                    static_cast<unsigned long long>(b.frio_arranque()));
    }
    {   // 15. [DDOS-ESTADO-PERSIST-D299] persistencia del estado por victima
        namespace dd = ::argus::ddos;
        const std::string dir = "/tmp/argus_d299_estado_test";
        std::filesystem::remove_all(dir);
        const std::string f1 = dir + "/a/estado.csv", f2 = dir + "/b/estado.csv", f3 = dir + "/c/estado.csv";
        const uint64_t W = 1700000000000000000ULL;   // pared del volcado
        const uint64_t H = 3600000000000ULL;         // 1 h en ns
        dd::VictimEwmaParams p;                      // warm 30, interval 1000
        auto escribe = [](const std::string& ruta, const std::string& txt) {
            std::filesystem::create_directories(std::filesystem::path(ruta).parent_path());
            std::ofstream o(ruta, std::ios::trunc);
            o << txt;
        };
        const std::string cab = "argus-ddos-victim-estado v1\n";
        const std::string col = "dst_ip,proto,ewma,seen,bajo_presion\n";
        auto meta = [&](uint64_t wall, const char* iv, int filas) {
            return "volcado_wall_ns=" + std::to_string(wall) + " interval_ms=" + iv + " filas=" +
                   std::to_string(filas) + "\n";
        };
        const std::string filas2 = "3232261121,17,10.5,5,1\n3232261132,6,30.25,100,0\n";  // .1 UDP, .12 TCP
        const uint64_t k1 = ::sniffer::ddos_victim_key(0xC0A86401u, 17u);
        const uint64_t k2 = ::sniffer::ddos_victim_key(0xC0A8640Cu, 6u);
        // 15a ida y vuelta: seen promovido a warm, bajo_presion y ewma conservados, last_seq a 0
        escribe(f1, cab + meta(W, "1000", 2) + col + filas2);
        ::sniffer::DdosVictimBoard b1;
        b1.set_ewma_params(p);
        auto r = b1.restaurar_estado(f1, W + H, 24 * H);
        CHECK(r.existe && r.ok && r.victimas == 2 && r.bajo_presion == 1 && r.edad_ns == H);
        auto e1 = b1.estado_ewma(k1);
        CHECK(e1 && e1->ewma == 10.5 && e1->seen == 30 && e1->bajo_presion && e1->last_seq == 0);
        auto e2 = b1.estado_ewma(k2);
        CHECK(e2 && e2->ewma == 30.25 && e2->seen == 100 && !e2->bajo_presion);
        std::string err;
        CHECK(b1.volcar_estado(f2, W + H, err));
        ::sniffer::DdosVictimBoard b2;
        b2.set_ewma_params(p);
        r = b2.restaurar_estado(f2, W + 2 * H, 24 * H);
        CHECK(r.ok && r.victimas == 2 && r.bajo_presion == 1);
        auto e1b = b2.estado_ewma(k1);
        CHECK(e1b && e1b->ewma == 10.5 && e1b->seen == 30 && e1b->bajo_presion);
        // 15b [DDOS-ESTADO-PERSIST-D299-15B] rebase en la banda de histeresis (k_out <= ratio < k_in): 20 pps sobre base 10,5.
        // Sin rebase el gap 2 la saca y no vuelve a entrar (ratio 2 < k_in); con rebase sigue bajo presion
        // con la EWMA congelada. Con un ataque fuerte (300 pps, ratio 30) reentra solo: el rebase protege
        // los ataques moderados.
        auto sin_rebase = *b2.estado_ewma(k1);
        dd::victim_ewma_step(sin_rebase, 2, 20.0, p);
        CHECK(!sin_rebase.bajo_presion);
        b1.aplicar_rebase_si_pendiente(2);
        auto st = *b1.estado_ewma(k1);
        CHECK(st.last_seq == 1);
        const double rat = dd::victim_ewma_step(st, 2, 20.0, p);
        CHECK(st.bajo_presion && rat >= p.k_out && st.ewma == 10.5);
        // 15c caducado y 15d fecha futura: se descarta entero
        ::sniffer::DdosVictimBoard b3;
        b3.set_ewma_params(p);
        r = b3.restaurar_estado(f1, W + 25 * H, 24 * H);
        CHECK(r.existe && !r.ok && r.motivo == "caducado" && !b3.estado_ewma(k1));
        r = b3.restaurar_estado(f1, W - 1, 24 * H);
        CHECK(!r.ok && r.motivo.find("futuro") != std::string::npos && !b3.estado_ewma(k1));
        // 15e corrupto: cabecera, numero de filas, NaN, basura al final, interval_ms distinto
        escribe(f3, "otra cosa\n" + meta(W, "1000", 2) + col + filas2);
        CHECK(!b3.restaurar_estado(f3, W + H, 24 * H).ok);
        escribe(f3, cab + meta(W, "1000", 3) + col + filas2);
        CHECK(!b3.restaurar_estado(f3, W + H, 24 * H).ok);
        escribe(f3, cab + meta(W, "1000", 1) + col + "3232261121,17,nan,5,1\n");
        CHECK(!b3.restaurar_estado(f3, W + H, 24 * H).ok);
        escribe(f3, cab + meta(W, "1000", 1) + col + "3232261121,17,10.5,5,1 x\n");
        CHECK(!b3.restaurar_estado(f3, W + H, 24 * H).ok);
        escribe(f3, cab + meta(W, "500", 2) + col + filas2);
        r = b3.restaurar_estado(f3, W + H, 24 * H);
        CHECK(!r.ok && r.motivo.find("interval_ms") != std::string::npos);
        CHECK(!b3.estado_ewma(k1) && !b3.estado_ewma(k2));
        // 15f inexistente y ruta no escribible: sin excepcion
        r = b3.restaurar_estado(dir + "/no/existe.csv", W, 24 * H);
        CHECK(!r.existe && !r.ok);
        err.clear();
        CHECK(!b1.volcar_estado("/proc/argus_d299_no/estado.csv", W, err) && !err.empty());
        std::filesystem::remove_all(dir);
        std::printf("ESTADO-PERSIST: 15a-15f\n");
    }
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
        //      la ventana siguiente sigue > 5 porque entra en bajo_presion (EWMA congelada) [DDOS-ETAPA1-D298]
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

    // 12. [DDOS-HYST-D291] histeresis de la EWMA por victima (defectos: k_in 3, k_out 1,5, abs_pps 200)
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
        // 12c. clave fria (< 30 ventanas vistas) NO entra: 60 pps se absorben como antes (60 < abs_pps 200: precio documentado de abs_pps)
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
        p.abs_pps = 0.5;  // [DDOS-ETAPA1-D298] fuera de rango [1, 1e6]
        CHECK(!::argus::ddos::victim_ewma_params_ok(p));
        p = {};
        p.abs_pps = 2.0e6;
        CHECK(!::argus::ddos::victim_ewma_params_ok(p));
        p = {};
        p.alpha = 0.0;
        CHECK(!::argus::ddos::victim_ewma_params_ok(p));
        std::printf("HYST: 12a r_ent=%.4f r_min=%.4f 12b r_sal=%.4f r_2x=%.4f 12c r_fria=%.4f\n",
                    static_cast<double>(r_ent), static_cast<double>(r_min), static_cast<double>(r_sal),
                    static_cast<double>(r_2x), static_cast<double>(r_fria));
    }

    // 13. [DDOS-ETAPA1-D298] EWMA congelada en bajo_presion, entrada fria por abs_pps (defecto 200),
    //     ventana sin trafico = pps 0, estado de la victima en el tablero
    {
        namespace dd = ::argus::ddos;
        auto win1s = [](uint64_t i, uint64_t pkts, uint32_t ip) {
            DdosWindow w = make_window(i * 1'000'000'000ULL, (i + 1) * 1'000'000'000ULL);
            if (pkts) w.victims.push_back({ip, 17u, pkts, pkts * 482});
            return w;
        };
        // 13a. A5 (antes: la etapa 1 dejaba de pasar a ~889 s): base 10 pps 600 ventanas y ataque de 60 pps
        //      (70 en la victima) 2 h: el ratio se SOSTIENE y la victima sigue en presion; vuelve a la base y sale
        DdosVictimBoard a;
        for (uint64_t i = 1; i <= 600; ++i) a.publish_window(i, win1s(i, 10, GW));
        float a_min = 1e9f;
        bool a_presion = true;
        for (uint64_t i = 601; i <= 7800; ++i) {
            a.publish_window(i, win1s(i, 70, GW));
            const auto r = a.lookup(GW, UDP);
            if (r.rate_ratio < a_min) a_min = r.rate_ratio;
            if (r.estado != dd::VictimEwmaEstado::BajoPresion) a_presion = false;
        }
        a.publish_window(7801, win1s(7801, 10, GW));
        const auto a_fin = a.lookup(GW, UDP);
        CHECK(a_min > 6.9f);
        CHECK(a_presion);
        CHECK(a_fin.estado == dd::VictimEwmaEstado::Normal);
        // 13b. clave fria con pps >= abs_pps (ataque presente al arrancar): presion desde la primera ventana,
        //      EWMA congelada (ratio sostenido); al caer el trafico sale
        DdosVictimBoard f;
        f.publish_window(1, win1s(1, 300, GW));
        const auto f_1 = f.lookup(GW, UDP);
        float f_min = 1e9f;
        bool f_presion = true;
        for (uint64_t i = 2; i <= 300; ++i) {
            f.publish_window(i, win1s(i, 300, GW));
            const auto r = f.lookup(GW, UDP);
            if (r.rate_ratio < f_min) f_min = r.rate_ratio;
            if (r.estado != dd::VictimEwmaEstado::BajoPresion) f_presion = false;
        }
        f.publish_window(301, win1s(301, 5, GW));
        const auto f_fin = f.lookup(GW, UDP);
        CHECK(f_1.estado == dd::VictimEwmaEstado::BajoPresion);
        CHECK(f_presion);
        CHECK(f_min > 29.9f);
        CHECK(f_fin.estado == dd::VictimEwmaEstado::Normal);
        // 13c. clave fria por debajo de abs_pps (frio benigno DAY298, 50 pps): FRIA mientras seen < 30, nunca
        //      entra en presion, luego NORMAL con la base aprendida
        DdosVictimBoard b;
        bool b_nunca = true;
        dd::VictimEwmaEstado b_1{}, b_29{}, b_30{};
        for (uint64_t i = 1; i <= 40; ++i) {
            b.publish_window(i, win1s(i, 50, GW));
            const auto r = b.lookup(GW, UDP);
            if (r.estado == dd::VictimEwmaEstado::BajoPresion) b_nunca = false;
            if (i == 1) b_1 = r.estado;
            if (i == 29) b_29 = r.estado;
            if (i == 30) b_30 = r.estado;
        }
        const float b_40 = b.lookup(GW, UDP).rate_ratio;
        CHECK(b_nunca);
        CHECK(b_1 == dd::VictimEwmaEstado::Frio);
        CHECK(b_29 == dd::VictimEwmaEstado::Frio);
        CHECK(b_30 == dd::VictimEwmaEstado::Normal);
        CHECK(b_40 < 1.1f);
        // 13d. victima ausente de la instantanea: estado NORMAL (sin trafico no hay presion)
        CHECK(b.lookup(DNS, UDP).estado == dd::VictimEwmaEstado::Normal);
        // 13e. un hueco sin trafico termina el episodio: 40 ventanas a 20, entra con 100, 5 ventanas
        //      sin trafico y vuelve a 20 -> ratio 20 / (19,70 * 0,9^5) = 1,72 < k_in: NORMAL
        DdosVictimBoard g;
        for (uint64_t i = 1; i <= 40; ++i) g.publish_window(i, win1s(i, 20, GW));
        g.publish_window(41, win1s(41, 100, GW));
        const auto g_41 = g.lookup(GW, UDP);
        g.publish_window(47, win1s(47, 20, GW));
        const auto g_47 = g.lookup(GW, UDP);
        CHECK(g_41.estado == dd::VictimEwmaEstado::BajoPresion);
        CHECK(g_47.estado == dd::VictimEwmaEstado::Normal);
        CHECK(std::fabs(g_47.rate_ratio - 1.72f) < 0.01f);
        std::printf("ETAPA1: 13a a_min=%.4f 13b f_min=%.4f 13c b_40=%.4f 13e g_47=%.4f\n",
                    static_cast<double>(a_min), static_cast<double>(f_min), static_cast<double>(b_40),
                    static_cast<double>(g_47.rate_ratio));
    }

    if (g_fail) {
        std::fprintf(stderr, "test_ddos_victim_board: %d/%d FALLOS\n", g_fail, g_checks);
        return 1;
    }
    std::printf("test_ddos_victim_board: OK (%d checks)\n", g_checks);
    return 0;
}
