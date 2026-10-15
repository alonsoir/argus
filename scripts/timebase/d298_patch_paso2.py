#!/usr/bin/env python3
# DAY298 paso 2 (sniffer): EWMA por victima congelada en bajo_presion, entrada fria por abs_pps (defecto 200),
# ventana sin trafico = pps 0 (sale), estado de la victima en el tablero y sellado de DDoSFeatures.victim_state.
# Retira tau_s/alpha_slow (ddos_victim_ewma_tau_s en el JSON se ignora con [CONFIG-OBSOLETO]).
# Diseno: docs/ml-heads/diseno_etapa1_histeresis_day298.md. Atomico, todo o nada: comprueba cada ancla con su
# numero exacto de apariciones y que sniffer.json sigue siendo JSON valido antes de escribir.
# Uso, desde la raiz del repo: --check | --apply
import json, os, sys

MARCA = "DDOS-ETAPA1-D298"

C = "sniffer/include/ddos_contract_v2.hpp"
CFG = "sniffer/src/userspace/config_manager.cpp"
JS = "sniffer/config/sniffer.json"
BD = "sniffer/include/ddos_victim_board.hpp"
RC = "sniffer/src/userspace/ring_consumer.cpp"
TS = "sniffer/tests/test_ddos_victim_board.cpp"
A5 = "scripts/timebase/a5_ataque_largo.cpp"
DOC = "docs/ml-heads/diseno_etapa1_histeresis_day298.md"

STEP_OLD_START = "// Un paso por ventana en que la victima aparece. Las ventanas sin trafico entre medias\n"
STEP_OLD_END = "    s.seen += 1;\n    return ratio;\n}\n"
STEP_NEW = r'''// [DDOS-ETAPA1-D298] Estado de la victima. Valores alineados con protobuf VictimState (0 = sin estado).
enum class VictimEwmaEstado : uint8_t { Frio = 1, Normal = 2, BajoPresion = 3 };

inline VictimEwmaEstado victim_ewma_estado(const VictimEwmaState& s, const VictimEwmaParams& p) noexcept {
    if (s.bajo_presion) return VictimEwmaEstado::BajoPresion;
    return (s.seen < p.warm_windows) ? VictimEwmaEstado::Frio : VictimEwmaEstado::Normal;
}

// Un paso por ventana en que la victima aparece. Devuelve el ratio de ESTA ventana contra la EWMA previa.
// [DDOS-ETAPA1-D298] Las ventanas sin trafico entre medias cuentan como pps 0: fuera de bajo_presion decaen con
// alpha; dentro, la primera da ratio 0 < k_out (el episodio termina) y el resto decae con alpha. Dentro de
// bajo_presion la EWMA no cambia (congelada: no aprende del trafico de presion). Entrada: clave caliente con
// ratio >= k_in; clave fria (seen < warm_windows) con pps >= abs_pps.
// Si la clave reaparece tras mas de evict_windows, empieza de cero (igual que el arnes offline).
inline double victim_ewma_step(VictimEwmaState& s, uint64_t seq, double pps,
                               const VictimEwmaParams& p) noexcept {
    if (s.seen > 0 && seq > s.last_seq && seq - s.last_seq > p.evict_windows) s = VictimEwmaState{};
    double prior = 0.0;
    if (s.seen > 0) {
        const uint64_t gap = (seq > s.last_seq) ? (seq - s.last_seq) : 1;
        prior = s.ewma;
        if (gap > 1) {
            s.bajo_presion = false;  // ventanas sin trafico = pps 0 < k_out: el episodio termino
            for (uint64_t i = 1; i < gap; ++i) prior *= (1.0 - p.alpha);
        }
    }
    const double ratio = pps / (prior > p.floor_pps ? prior : p.floor_pps);
    const bool fria = s.seen < p.warm_windows;
    if (!s.bajo_presion && ((!fria && ratio >= p.k_in) || (fria && pps >= p.abs_pps))) s.bajo_presion = true;
    else if (s.bajo_presion && ratio < p.k_out) s.bajo_presion = false;
    s.ewma = s.bajo_presion ? prior : (1.0 - p.alpha) * prior + p.alpha * pps;
    s.last_seq = seq;
    s.seen += 1;
    return ratio;
}
'''

TEST13 = r'''    // 13. [DDOS-ETAPA1-D298] EWMA congelada en bajo_presion, entrada fria por abs_pps (defecto 200),
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

'''

DOC_JSON_OLD = ("Fuera del estado la EWMA aprende con alpha; dentro, con alpha_lento = "
                "(ddos_kernel_agg_interval_ms/1000)/tau_s.")
DOC_JSON_NEW = ("Fuera del estado la EWMA aprende con alpha; dentro se CONGELA ([DDOS-ETAPA1-D298]: con alfa lento "
                "absorbia un ataque sostenido en ~15-25 min, medido DAY297-298). Una clave fria (menos de "
                "warm_windows ventanas vistas) entra con pps >= abs_pps. Una ventana sin trafico de la victima "
                "cuenta como pps 0 (sale del estado).")
ABS_DOC = ("real (pps), rango [1, 1000000], defecto 200. [DDOS-ETAPA1-D298] Solo para claves frias (sin historia): "
           "entran en bajo_presion con pps >= abs_pps; sin esto un ataque presente al arrancar se aprende como base "
           "(DAY298: 60 pps aprendidos en 4 s). Defecto SEGURO, no optimo: por encima del trafico legitimo de "
           "arranque medido en el laboratorio (pico 14 pps en 5 arranques; 140 pps una vez, DAY297). Depende de "
           "cada instalacion (pipeline en una o varias maquinas, capacidad, trafico normal de cada victima): "
           "calibrarlo en cada despliegue. Precio: una victima sin historia que recibe un ataque por debajo de "
           "abs_pps lo aprende como base.")

CAMBIOS = {
    C: [
        ("// (solo clave caliente), sale con ratio < k_out; dentro, la EWMA aprende con alfa lento =\n"
         "// (intervalo/1000)/tau_s (tiempo de absorcion). Medido DAY291: sin histeresis un flood de 7x\n",
         "// (solo clave caliente), sale con ratio < k_out. [DDOS-ETAPA1-D298] Dentro, la EWMA se CONGELA (antes\n"
         "// aprendia con alfa lento 1/tau_s y absorbia un ataque sostenido en ~15-25 min, medido DAY297-298); una\n"
         "// clave FRIA entra con pps >= abs_pps; una ventana sin trafico cuenta como pps 0. Medido DAY291: sin\n"
         "// histeresis un flood de 7x\n", 1),
        ("    double tau_s = 3600.0;          // tiempo de absorcion dentro de bajo_presion (s)\n",
         "    double abs_pps = 200.0;         // [DDOS-ETAPA1-D298] clave fria entra en bajo_presion con pps >= abs_pps\n", 1),
        ("    double alpha_slow() const noexcept { return (interval_ms / 1000.0) / tau_s; }\n", "", 1),
        ("inline constexpr double kVictimEwmaTauMin = 60.0, kVictimEwmaTauMax = 86400.0;\n",
         "inline constexpr double kVictimEwmaAbsPpsMin = 1.0, kVictimEwmaAbsPpsMax = 1.0e6;  // [DDOS-ETAPA1-D298]\n", 1),
        ("// Validacion completa: rangos + reglas cruzadas (k_out < k_in; alfa lento < alfa).\n",
         "// Validacion completa: rangos + regla cruzada (k_out < k_in).\n", 1),
        ("           victim_ewma_in_range(p.tau_s, kVictimEwmaTauMin, kVictimEwmaTauMax) &&\n",
         "           victim_ewma_in_range(p.abs_pps, kVictimEwmaAbsPpsMin, kVictimEwmaAbsPpsMax) &&\n", 1),
        ("           p.interval_ms > 0.0 && p.k_out < p.k_in && p.alpha_slow() < p.alpha;\n",
         "           p.interval_ms > 0.0 && p.k_out < p.k_in;\n", 1),
    ],
    CFG: [
        ('    n += ddos_ewma_num(k, "ddos_victim_ewma_tau_s", d.tau_s, dd::kVictimEwmaTauMin, dd::kVictimEwmaTauMax, false, x);\n'
         '    p.tau_s = x;\n',
         '    n += ddos_ewma_num(k, "ddos_victim_ewma_abs_pps", d.abs_pps, dd::kVictimEwmaAbsPpsMin, dd::kVictimEwmaAbsPpsMax, false, x);\n'
         '    p.abs_pps = x;  // [DDOS-ETAPA1-D298]\n'
         '    if (k.isMember("ddos_victim_ewma_tau_s")) {\n'
         '        std::cerr << "[CONFIG-OBSOLETO] sniffer.json: ddos_victim_ewma_tau_s ya no se usa desde DAY298 (bajo_presion "\n'
         '                     "congela la EWMA; antes aprendia con alfa lento y absorbia los ataques sostenidos). Se ignora."\n'
         '                  << std::endl;\n'
         '    }\n', 1),
        ('    if (!(p.alpha_slow() < p.alpha)) {\n'
         '        std::cerr << "[CONFIG-DEFAULT] regla alfa_lento < alfa rota (alfa=" << p.alpha << ", alfa_lento="\n'
         '                  << p.alpha_slow() << ") -> defectos alfa=" << d.alpha << " tau_s=" << d.tau_s << std::endl;\n'
         '        p.alpha = d.alpha;\n'
         '        p.tau_s = d.tau_s;\n'
         '        ++n;\n'
         '    }\n', "", 1),
        ('    std::cout << "[DDOS-HYST] ewma alpha=" << p.alpha << " tau_s=" << p.tau_s << " alpha_lento=" << p.alpha_slow()\n',
         '    std::cout << "[DDOS-HYST] ewma alpha=" << p.alpha << " bajo_presion=congelada abs_pps=" << p.abs_pps\n', 1),
    ],
    JS: [
        (DOC_JSON_OLD, DOC_JSON_NEW, 1),
        ("Reglas cruzadas: k_out < k_in; alpha_lento < alpha.", "Regla cruzada: k_out < k_in.", 1),
        ('    "_doc_ddos_victim_ewma_tau_s": "real (segundos), rango [60, 86400], defecto 3600. Tiempo de absorcion '
         'dentro de bajo_presion: un aumento sostenido se acepta como normal en ~tau_s.",\n'
         '    "ddos_victim_ewma_tau_s": 3600,\n',
         '    "_doc_ddos_victim_ewma_abs_pps": "' + ABS_DOC + '",\n'
         '    "ddos_victim_ewma_abs_pps": 200.0,\n', 1),
    ],
    BD: [
        ("    float rate_ratio = 0.0f;  // [DDOS-H2-D286] escalada; 0 si ventana degenerada\n};\n",
         "    float rate_ratio = 0.0f;  // [DDOS-H2-D286] escalada; 0 si ventana degenerada\n"
         "    ::argus::ddos::VictimEwmaEstado estado = ::argus::ddos::VictimEwmaEstado::Normal;  // [DDOS-ETAPA1-D298]\n};\n", 1),
        ("    float rate_ratio = 0.0f;  // [DDOS-H2-D286]\n};\n",
         "    float rate_ratio = 0.0f;  // [DDOS-H2-D286]\n"
         "    // [DDOS-ETAPA1-D298] victima ausente de la instantanea (sin trafico en la ventana) = NORMAL: sin presion\n"
         "    ::argus::ddos::VictimEwmaEstado estado = ::argus::ddos::VictimEwmaEstado::Normal;\n};\n", 1),
        ("            float ratio = 0.0f;  // [DDOS-H2-D286] solo con ventana de duracion > 0\n"
         "            if (s->window_ms > 0) {\n"
         "                const double pps = static_cast<double>(v.d_pkts) * 1000.0 / static_cast<double>(s->window_ms);\n"
         "                ratio = static_cast<float>(::argus::ddos::victim_ewma_step(ewma_[key], seq, pps, ewma_params_));\n"
         "            }\n"
         "            s->by_key[key] = DdosVictimCounts{v.d_pkts, v.d_bytes, ratio};\n",
         "            float ratio = 0.0f;  // [DDOS-H2-D286] solo con ventana de duracion > 0\n"
         "            auto estado = ::argus::ddos::VictimEwmaEstado::Normal;  // [DDOS-ETAPA1-D298]\n"
         "            if (s->window_ms > 0) {\n"
         "                const double pps = static_cast<double>(v.d_pkts) * 1000.0 / static_cast<double>(s->window_ms);\n"
         "                auto& st = ewma_[key];\n"
         "                ratio = static_cast<float>(::argus::ddos::victim_ewma_step(st, seq, pps, ewma_params_));\n"
         "                estado = ::argus::ddos::victim_ewma_estado(st, ewma_params_);\n"
         "            }\n"
         "            s->by_key[key] = DdosVictimCounts{v.d_pkts, v.d_bytes, ratio, estado};\n", 1),
        ("            r.rate_ratio = it->second.rate_ratio;  // [DDOS-H2-D286]\n",
         "            r.rate_ratio = it->second.rate_ratio;  // [DDOS-H2-D286]\n"
         "            r.estado = it->second.estado;          // [DDOS-ETAPA1-D298]\n", 1),
    ],
    RC: [
        ("void RingBufferConsumer::stamp_victim_window(protobuf::NetworkSecurityEvent& ev,\n",
         "// [DDOS-ETAPA1-D298] el estado del sniffer se sella con static_cast: los valores deben coincidir con el proto.\n"
         "static_assert(static_cast<int>(::argus::ddos::VictimEwmaEstado::Frio) == protobuf::VICTIM_STATE_COLD &&\n"
         "              static_cast<int>(::argus::ddos::VictimEwmaEstado::Normal) == protobuf::VICTIM_STATE_NORMAL &&\n"
         "              static_cast<int>(::argus::ddos::VictimEwmaEstado::BajoPresion) == protobuf::VICTIM_STATE_UNDER_PRESSURE,\n"
         "              \"VictimEwmaEstado desalineado con protobuf::VictimState\");\n\n"
         "void RingBufferConsumer::stamp_victim_window(protobuf::NetworkSecurityEvent& ev,\n", 1),
        ("        ev.mutable_network_features()->mutable_ddos_embedded()->set_victim_rate_ratio(r.rate_ratio);  // [DDOS-H2-D286]\n",
         "        ev.mutable_network_features()->mutable_ddos_embedded()->set_victim_rate_ratio(r.rate_ratio);  // [DDOS-H2-D286]\n"
         "        ev.mutable_network_features()->mutable_ddos_embedded()->set_victim_state(\n"
         "            static_cast<protobuf::VictimState>(r.estado));  // [DDOS-ETAPA1-D298]\n", 1),
    ],
    TS: [
        ("entra en bajo_presion (alfa lento) [DDOS-HYST-D291]",
         "entra en bajo_presion (EWMA congelada) [DDOS-ETAPA1-D298]", 1),
        ("(defectos: k_in 3, k_out 1,5, tau 3600 s)", "(defectos: k_in 3, k_out 1,5, abs_pps 200)", 1),
        ("NO entra: 60 pps se absorben como antes",
         "NO entra: 60 pps se absorben como antes (60 < abs_pps 200: precio documentado de abs_pps)", 1),
        ("        p = {};\n        p.tau_s = 30.0;\n        CHECK(!::argus::ddos::victim_ewma_params_ok(p));\n"
         "        p = {};\n        p.alpha = 0.01;\n        p.tau_s = 60.0;\n        CHECK(!::argus::ddos::victim_ewma_params_ok(p));\n",
         "        p = {};\n        p.abs_pps = 0.5;  // [DDOS-ETAPA1-D298] fuera de rango [1, 1e6]\n"
         "        CHECK(!::argus::ddos::victim_ewma_params_ok(p));\n"
         "        p = {};\n        p.abs_pps = 2.0e6;\n        CHECK(!::argus::ddos::victim_ewma_params_ok(p));\n", 1),
        ("    if (g_fail) {\n", TEST13 + "    if (g_fail) {\n", 1),
    ],
    A5: [
        ("// DAY297 D15 A5 (offline): ataque sostenido largo contra la funcion REAL del sniffer, victim_ewma_step\n",
         "// [DDOS-ETAPA1-D298] REGISTRO DEL ANTES: compila contra el contrato de 2866f4cc (alpha_slow/tau_s se retiraron\n"
         "// en DAY298). El despues offline es test_ddos_victim_board, bloque 13a.\n"
         "// DAY297 D15 A5 (offline): ataque sostenido largo contra la funcion REAL del sniffer, victim_ewma_step\n", 1),
    ],
    DOC: [
        ("- Salida: ratio contra la EWMA congelada < k_out, es decir, cuando el tráfico vuelve a la base.\n",
         "- Salida: ratio contra la EWMA congelada < k_out, es decir, cuando el tráfico vuelve a la base.\n"
         "- Una ventana sin tráfico de la víctima cuenta como pps 0: ratio 0 < k_out, el episodio termina y el resto\n"
         "  del hueco decae con alpha (como fuera de presión). Por eso no hace falta publicar víctimas en presión\n"
         "  ausentes: ausente = sin tráfico = sin presión = NORMAL al sellar. [DDOS-ETAPA1-D298, paso 2]\n", 1),
    ],
}

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        sys.exit("uso: d298_patch_paso2.py --check | --apply")
    nuevos, errores = {}, []
    for f, cambios in CAMBIOS.items():
        txt = open(f).read()
        if MARCA in txt and f != DOC:
            errores.append(f"{f}: ya lleva la marca {MARCA}")
            continue
        for viejo, nuevo, n in cambios:
            c = txt.count(viejo)
            if c != n:
                errores.append(f"{f}: '{viejo.strip()[:70]}...' aparece {c} veces, se esperaban {n}")
            else:
                txt = txt.replace(viejo, nuevo)
        nuevos[f] = txt
    txt = nuevos.get(C, "")
    if C in nuevos:
        if txt.count(STEP_OLD_START) != 1:
            errores.append(f"{C}: inicio del paso aparece {txt.count(STEP_OLD_START)} veces, se esperaba 1")
        else:
            i = txt.index(STEP_OLD_START)
            j = txt.find(STEP_OLD_END, i)
            if j < 0:
                errores.append(f"{C}: no encuentro el final del paso")
            else:
                nuevos[C] = txt[:i] + STEP_NEW + txt[j + len(STEP_OLD_END):]
    if JS in nuevos:
        try:
            cfg = json.loads(nuevos[JS])
        except json.JSONDecodeError as e:
            errores.append(f"{JS}: el resultado no es JSON valido: {e}")
    restos = [f for f, t in nuevos.items() if f not in (A5, DOC) and ("alpha_slow" in t or "kVictimEwmaTau" in t)]
    if restos:
        errores.append(f"quedan alpha_slow/kVictimEwmaTau en: {restos}")
    if errores:
        sys.exit("NO APLICABLE:\n  " + "\n  ".join(errores))
    if sys.argv[1] == "--check":
        print(f"CHECK OK: {len(nuevos)} ficheros; paso nuevo de la EWMA; sniffer.json valido; sin restos de alpha_slow/tau")
        return
    for f, t in nuevos.items():
        modo = os.stat(f).st_mode
        with open(f + ".tmp", "w") as o:
            o.write(t)
        os.chmod(f + ".tmp", modo)
    for f in nuevos:
        os.replace(f + ".tmp", f)
    print(f"APLICADO [{MARCA}] en {len(nuevos)} ficheros")

main()
