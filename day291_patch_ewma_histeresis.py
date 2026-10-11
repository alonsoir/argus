#!/usr/bin/env python3
"""DAY291 [DDOS-HYST-D291] Histeresis en la EWMA por victima + parametros en sniffer.json.
Atomico (todo o nada), idempotente. Uso (desde la raiz del repo): --check | --apply. No commitea."""
import json, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MARK = "[DDOS-HYST-D291]"
F_CON = "sniffer/include/ddos_contract_v2.hpp"
F_BRD = "sniffer/include/ddos_victim_board.hpp"
F_CMH = "sniffer/include/config_manager.hpp"
F_CTH = "sniffer/include/config_types.h"
F_CTC = "sniffer/src/userspace/config_types.cpp"
F_CMC = "sniffer/src/userspace/config_manager.cpp"
F_MAIN = "sniffer/src/userspace/main.cpp"
F_JSON = "sniffer/config/sniffer.json"
F_TEST = "sniffer/tests/test_ddos_victim_board.cpp"

CONTRACT_NEW = r'''// [DDOS-H2-D286] H2: escalada por victima = pps_ventana / max(EWMA previa, suelo).
// [DDOS-HYST-D291] Histeresis: estado bajo_presion por victima. Entra con ratio >= k_in
// (solo clave caliente), sale con ratio < k_out; dentro, la EWMA aprende con alfa lento =
// (intervalo/1000)/tau_s (tiempo de absorcion). Medido DAY291: sin histeresis un flood de 7x
// desaparecia en ~5 s por UNA ventana de jitter (ratio 4,95 < 5). Offline (18 dias, 83
// arranques): k_in=3, k_out=1,5, tau=3600 s sostienen 30 y 60 pps los 90 s y cuestan 33
// episodios de ambiente (max 10 s). Los valores vivos vienen de sniffer.json; estos son los
// DEFECTOS validados, que se usan con aviso [CONFIG-DEFAULT] si el JSON falta o es invalido.
struct VictimEwmaParams {
    double alpha = 0.1;             // por ventana, fuera de bajo_presion
    double tau_s = 3600.0;          // tiempo de absorcion dentro de bajo_presion (s)
    double k_in = 3.0;              // entra con ratio >= k_in
    double k_out = 1.5;             // sale con ratio < k_out
    uint64_t warm_windows = 30;     // ventanas vistas para poder entrar (clave caliente)
    double floor_pps = 10.0;        // suelo del denominador
    uint64_t evict_windows = 3600;  // ventanas sin aparecer -> la clave se olvida
    double interval_ms = 1000.0;    // ventana nominal del lector (ddos_kernel_agg_interval_ms)
    double alpha_slow() const noexcept { return (interval_ms / 1000.0) / tau_s; }
};

// Rangos aceptados (inclusive). Documentados tambien en sniffer.json.
inline constexpr double kVictimEwmaAlphaMin = 0.001, kVictimEwmaAlphaMax = 1.0;
inline constexpr double kVictimEwmaTauMin = 60.0, kVictimEwmaTauMax = 86400.0;
inline constexpr double kVictimEwmaKInMin = 1.1, kVictimEwmaKInMax = 100.0;
inline constexpr double kVictimEwmaKOutMin = 1.0, kVictimEwmaKOutMax = 99.0;
inline constexpr double kVictimEwmaWarmMin = 0.0, kVictimEwmaWarmMax = 3600.0;
inline constexpr double kVictimEwmaFloorMin = 0.1, kVictimEwmaFloorMax = 1.0e6;
inline constexpr double kVictimEwmaEvictMin = 60.0, kVictimEwmaEvictMax = 86400.0;

inline bool victim_ewma_in_range(double x, double lo, double hi) noexcept { return x >= lo && x <= hi; }

// Validacion completa: rangos + reglas cruzadas (k_out < k_in; alfa lento < alfa).
inline bool victim_ewma_params_ok(const VictimEwmaParams& p) noexcept {
    return victim_ewma_in_range(p.alpha, kVictimEwmaAlphaMin, kVictimEwmaAlphaMax) &&
           victim_ewma_in_range(p.tau_s, kVictimEwmaTauMin, kVictimEwmaTauMax) &&
           victim_ewma_in_range(p.k_in, kVictimEwmaKInMin, kVictimEwmaKInMax) &&
           victim_ewma_in_range(p.k_out, kVictimEwmaKOutMin, kVictimEwmaKOutMax) &&
           victim_ewma_in_range(static_cast<double>(p.warm_windows), kVictimEwmaWarmMin, kVictimEwmaWarmMax) &&
           victim_ewma_in_range(p.floor_pps, kVictimEwmaFloorMin, kVictimEwmaFloorMax) &&
           victim_ewma_in_range(static_cast<double>(p.evict_windows), kVictimEwmaEvictMin, kVictimEwmaEvictMax) &&
           p.interval_ms > 0.0 && p.k_out < p.k_in && p.alpha_slow() < p.alpha;
}

struct VictimEwmaState {
    double ewma = 0.0;
    uint64_t last_seq = 0;
    uint64_t seen = 0;          // ventanas en que la victima aparecio (delta > 0)
    bool bajo_presion = false;  // [DDOS-HYST-D291]
};

// Un paso por ventana en que la victima aparece. Las ventanas sin trafico entre medias
// cuentan como 0 (decaen con alpha). Devuelve el ratio de ESTA ventana contra la EWMA previa.
// Si la clave reaparece tras mas de evict_windows, empieza de cero (igual que el arnes offline).
inline double victim_ewma_step(VictimEwmaState& s, uint64_t seq, double pps,
                               const VictimEwmaParams& p) noexcept {
    if (s.seen > 0 && seq > s.last_seq && seq - s.last_seq > p.evict_windows) s = VictimEwmaState{};
    double prior = 0.0;
    if (s.seen > 0) {
        const uint64_t gap = (seq > s.last_seq) ? (seq - s.last_seq) : 1;
        prior = s.ewma;
        for (uint64_t i = 1; i < gap; ++i) prior *= (1.0 - p.alpha);
    }
    const double ratio = pps / (prior > p.floor_pps ? prior : p.floor_pps);
    if (!s.bajo_presion && s.seen >= p.warm_windows && ratio >= p.k_in) s.bajo_presion = true;
    else if (s.bajo_presion && ratio < p.k_out) s.bajo_presion = false;
    const double a = s.bajo_presion ? p.alpha_slow() : p.alpha;
    s.ewma = (1.0 - a) * prior + a * pps;
    s.last_seq = seq;
    s.seen += 1;
    return ratio;
}
'''

BOARD_SETTER = r'''
    // [DDOS-HYST-D291] parametros de la EWMA por victima (de sniffer.json, ya validados).
    // Llamar ANTES de arrancar el lector: publish_window (escritor unico) es quien los lee.
    void set_ewma_params(const ::argus::ddos::VictimEwmaParams& p) { ewma_params_ = p; }
    const ::argus::ddos::VictimEwmaParams& ewma_params() const { return ewma_params_; }
'''

CMC_HELPER = r'''// [DDOS-HYST-D291] Parametros de la EWMA por victima. Politica DAY291 (Alonso): el JSON
// manda; si un campo falta, no es numerico o esta fuera de rango, se usa el DEFECTO validado
// (ddos_contract_v2.hpp) y se avisa con [CONFIG-DEFAULT]. El sniffer arranca siempre.
namespace {
int ddos_ewma_num(const Json::Value& j, const char* field, double def, double lo, double hi,
                  bool integral, double& out) {
    out = def;
    if (!j.isMember(field)) {
        std::cerr << "[CONFIG-DEFAULT] kernel_space." << field << " ausente -> defecto=" << def
                  << " rango=[" << lo << ", " << hi << "]" << std::endl;
        return 1;
    }
    const Json::Value& v = j[field];
    if (!v.isNumeric()) {
        std::cerr << "[CONFIG-DEFAULT] kernel_space." << field << " no es numerico -> defecto=" << def
                  << " rango=[" << lo << ", " << hi << "]" << std::endl;
        return 1;
    }
    const double x = v.asDouble();
    if (!(x >= lo && x <= hi) || (integral && x != static_cast<double>(static_cast<uint64_t>(x)))) {
        std::cerr << "[CONFIG-DEFAULT] kernel_space." << field << "=" << x
                  << " fuera de rango o no entero -> defecto=" << def
                  << " rango=[" << lo << ", " << hi << "]" << std::endl;
        return 1;
    }
    out = x;
    return 0;
}

::argus::ddos::VictimEwmaParams parse_victim_ewma(const Json::Value& k, int interval_ms) {
    namespace dd = ::argus::ddos;
    const dd::VictimEwmaParams d{};
    dd::VictimEwmaParams p{};
    int n = 0;
    double x = 0.0;
    n += ddos_ewma_num(k, "ddos_victim_ewma_alpha", d.alpha, dd::kVictimEwmaAlphaMin, dd::kVictimEwmaAlphaMax, false, x);
    p.alpha = x;
    n += ddos_ewma_num(k, "ddos_victim_ewma_tau_s", d.tau_s, dd::kVictimEwmaTauMin, dd::kVictimEwmaTauMax, false, x);
    p.tau_s = x;
    n += ddos_ewma_num(k, "ddos_victim_ewma_k_in", d.k_in, dd::kVictimEwmaKInMin, dd::kVictimEwmaKInMax, false, x);
    p.k_in = x;
    n += ddos_ewma_num(k, "ddos_victim_ewma_k_out", d.k_out, dd::kVictimEwmaKOutMin, dd::kVictimEwmaKOutMax, false, x);
    p.k_out = x;
    n += ddos_ewma_num(k, "ddos_victim_ewma_warm_windows", static_cast<double>(d.warm_windows),
                       dd::kVictimEwmaWarmMin, dd::kVictimEwmaWarmMax, true, x);
    p.warm_windows = static_cast<uint64_t>(x);
    n += ddos_ewma_num(k, "ddos_victim_ewma_floor_pps", d.floor_pps, dd::kVictimEwmaFloorMin, dd::kVictimEwmaFloorMax, false, x);
    p.floor_pps = x;
    n += ddos_ewma_num(k, "ddos_victim_ewma_evict_windows", static_cast<double>(d.evict_windows),
                       dd::kVictimEwmaEvictMin, dd::kVictimEwmaEvictMax, true, x);
    p.evict_windows = static_cast<uint64_t>(x);
    if (interval_ms > 0) {
        p.interval_ms = static_cast<double>(interval_ms);
    } else {
        std::cerr << "[CONFIG-DEFAULT] kernel_space.ddos_kernel_agg_interval_ms=" << interval_ms
                  << " no valido para la EWMA -> " << d.interval_ms << std::endl;
        ++n;
    }
    if (!(p.k_out < p.k_in)) {
        std::cerr << "[CONFIG-DEFAULT] regla k_out < k_in rota (k_in=" << p.k_in << ", k_out=" << p.k_out
                  << ") -> defectos k_in=" << d.k_in << " k_out=" << d.k_out << std::endl;
        p.k_in = d.k_in;
        p.k_out = d.k_out;
        ++n;
    }
    if (!(p.alpha_slow() < p.alpha)) {
        std::cerr << "[CONFIG-DEFAULT] regla alfa_lento < alfa rota (alfa=" << p.alpha << ", alfa_lento="
                  << p.alpha_slow() << ") -> defectos alfa=" << d.alpha << " tau_s=" << d.tau_s << std::endl;
        p.alpha = d.alpha;
        p.tau_s = d.tau_s;
        ++n;
    }
    if (!dd::victim_ewma_params_ok(p)) {
        std::cerr << "[CONFIG-DEFAULT] combinacion de parametros de la EWMA invalida -> todos los defectos" << std::endl;
        const double iv = p.interval_ms;
        p = d;
        p.interval_ms = iv;
        ++n;
    }
    if (n > 0) {
        std::cerr << "[CONFIG-DEFAULT] " << n
                  << " ajustes con valor por defecto en la EWMA por victima: revisar sniffer.json" << std::endl;
    }
    std::cout << "[DDOS-HYST] ewma alpha=" << p.alpha << " tau_s=" << p.tau_s << " alpha_lento=" << p.alpha_slow()
              << " k_in=" << p.k_in << " k_out=" << p.k_out << " warm=" << p.warm_windows
              << " floor_pps=" << p.floor_pps << " evict=" << p.evict_windows
              << " interval_ms=" << p.interval_ms << std::endl;
    return p;
}
}  // namespace

'''

MAIN_INS = r'''        // [DDOS-HYST-D291] parametros de la EWMA por victima, antes de arrancar el lector
        g_ddos_victim_board->set_ewma_params(g_config.kernel_space.ddos_victim_ewma);

'''

JSON_INS = r'''    "_doc_ddos_victim_ewma": "[DDOS-HYST-D291] EWMA por victima {dst_ip, proto} con histeresis. ratio = pps_ventana / max(EWMA previa, floor_pps). Entra en bajo_presion con ratio >= k_in si la clave lleva >= warm_windows ventanas vistas; sale con ratio < k_out. Fuera del estado la EWMA aprende con alpha; dentro, con alpha_lento = (ddos_kernel_agg_interval_ms/1000)/tau_s. Si un campo falta, no es numerico o esta fuera de rango, se usa el defecto y el log muestra [CONFIG-DEFAULT]; el sniffer arranca igual. Reglas cruzadas: k_out < k_in; alpha_lento < alpha. Defectos medidos DAY291 (offline 18 dias + pilotos 30/60 pps). La linea [DDOS-HYST] del log muestra los valores activos.",
    "_doc_ddos_victim_ewma_alpha": "real, rango [0.001, 1.0], defecto 0.1. Aprendizaje por ventana fuera de bajo_presion.",
    "ddos_victim_ewma_alpha": 0.1,
    "_doc_ddos_victim_ewma_tau_s": "real (segundos), rango [60, 86400], defecto 3600. Tiempo de absorcion dentro de bajo_presion: un aumento sostenido se acepta como normal en ~tau_s.",
    "ddos_victim_ewma_tau_s": 3600,
    "_doc_ddos_victim_ewma_k_in": "real, rango [1.1, 100], defecto 3.0. Ratio para entrar en bajo_presion. Debe ser mayor que k_out.",
    "ddos_victim_ewma_k_in": 3.0,
    "_doc_ddos_victim_ewma_k_out": "real, rango [1.0, 99], defecto 1.5. Ratio por debajo del cual se sale de bajo_presion.",
    "ddos_victim_ewma_k_out": 1.5,
    "_doc_ddos_victim_ewma_warm_windows": "entero, rango [0, 3600], defecto 30. Ventanas vistas para que la clave pueda entrar (sin esta condicion el ambiente da 10 veces mas episodios).",
    "ddos_victim_ewma_warm_windows": 30,
    "_doc_ddos_victim_ewma_floor_pps": "real (pps), rango [0.1, 1000000], defecto 10. Suelo del denominador del ratio.",
    "ddos_victim_ewma_floor_pps": 10.0,
    "_doc_ddos_victim_ewma_evict_windows": "entero, rango [60, 86400], defecto 3600. Ventanas sin aparecer tras las que la clave se olvida.",
    "ddos_victim_ewma_evict_windows": 3600,
'''

TEST_INS = r'''    // 12. [DDOS-HYST-D291] histeresis de la EWMA por victima (defectos: k_in 3, k_out 1,5, tau 3600 s)
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

'''

EDITS = [
    (F_CON, "span", "// [DDOS-H2-D286] H2: escalada por victima", CONTRACT_NEW, "    return ratio;\n}\n"),
    (F_BRD, "replace", "victim_ewma_step(ewma_[key], seq, pps)", "victim_ewma_step(ewma_[key], seq, pps, ewma_params_)"),
    (F_BRD, "replace", "::argus::ddos::kVictimEvictWindows", "ewma_params_.evict_windows"),
    (F_BRD, "after", "    uint64_t published() const { return published_.load(std::memory_order_relaxed); }\n", BOARD_SETTER),
    (F_BRD, "after", "    std::unordered_map<uint64_t, ::argus::ddos::VictimEwmaState> ewma_;\n",
     "    ::argus::ddos::VictimEwmaParams ewma_params_{};  // [DDOS-HYST-D291]\n"),
    (F_CMH, "after", "#include <json/json.h>\n", "#include \"ddos_contract_v2.hpp\"  // [DDOS-HYST-D291]\n"),
    (F_CMH, "after", "    std::string ddos_kernel_agg_csv_path;\n",
     "    ::argus::ddos::VictimEwmaParams ddos_victim_ewma{};  // [DDOS-HYST-D291]\n"),
    (F_CTH, "after", "#include <json/json.h>\n", "#include \"ddos_contract_v2.hpp\"  // [DDOS-HYST-D291]\n"),
    (F_CTH, "after", "        std::string ddos_kernel_agg_csv_path;\n",
     "        ::argus::ddos::VictimEwmaParams ddos_victim_ewma{};  // [DDOS-HYST-D291]\n"),
    (F_CTC, "after",
     "        config.kernel_space.ddos_kernel_agg_csv_path = sniffer_config->kernel_space.ddos_kernel_agg_csv_path;\n",
     "        config.kernel_space.ddos_victim_ewma = sniffer_config->kernel_space.ddos_victim_ewma;  // [DDOS-HYST-D291]\n"),
    (F_CMC, "before", "KernelSpaceConfig ConfigManager::parse_kernel_space(const Json::Value& kernel_json) {\n", CMC_HELPER),
    (F_CMC, "after",
     "    kernel.ddos_kernel_agg_csv_path = kernel_json.get(\"ddos_kernel_agg_csv_path\", \"\").asString();\n",
     "    kernel.ddos_victim_ewma = parse_victim_ewma(kernel_json, kernel.ddos_kernel_agg_interval_ms);  // [DDOS-HYST-D291]\n"),
    (F_MAIN, "before",
     "        // [DDOS-KREAD-D274:MAIN-START] Lector del agregador DDoS en-kernel (opcional, DAY274).\n", MAIN_INS),
    (F_JSON, "after", "    \"ddos_kernel_agg_csv_path\": \"/vagrant/logs/lab/ddos_windows.csv\",\n", JSON_INS),
    (F_TEST, "replace",
     "        //      la ventana siguiente sigue > 5 porque aprende con alpha/60 (con alpha seria 3,6)\n",
     "        //      la ventana siguiente sigue > 5 porque entra en bajo_presion (alfa lento) [DDOS-HYST-D291]\n"),
    (F_TEST, "before", "    if (g_fail) {\n", TEST_INS),
]


def apply_edit(text, e):
    f, op, anchor, payload = e[0], e[1], e[2], e[3]
    n = text.count(anchor)
    if n != 1:
        raise ValueError("ancla aparece %d veces (se exige 1): %r" % (n, anchor[:70]))
    if op == "replace":
        return text.replace(anchor, payload, 1)
    if op == "after":
        return text.replace(anchor, anchor + payload, 1)
    if op == "before":
        return text.replace(anchor, payload + anchor, 1)
    if op == "span":
        end = e[4]
        i = text.find(anchor)
        j = text.find(end, i)
        if j < 0:
            raise ValueError("fin de tramo no encontrado: %r" % end)
        seg = text[i:j + len(end)]
        for must in ("victim_ewma_step", "kVictimRatioHot", "struct VictimEwmaState"):
            if must not in seg:
                raise ValueError("el tramo a sustituir no contiene %r" % must)
        return text[:i] + payload + text[j + len(end):]
    raise ValueError("op desconocida " + op)


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        sys.exit("uso: day291_patch_ewma_histeresis.py --check | --apply")
    files = []
    for e in EDITS:
        if e[0] not in files:
            files.append(e[0])
    orig = {}
    for f in files:
        with open(os.path.join(ROOT, f), encoding="utf-8") as fh:
            orig[f] = fh.read()
    marked = [f for f in files if MARK in orig[f]]
    if len(marked) == len(files):
        print("YA APLICADO: la marca %s esta en los %d ficheros. Nada que hacer." % (MARK, len(files)))
        return 0
    if marked:
        print("ESTADO PARCIAL: la marca esta solo en %s. ABORTO sin escribir." % marked)
        return 2
    new = dict(orig)
    for k, e in enumerate(EDITS, 1):
        try:
            new[e[0]] = apply_edit(new[e[0]], e)
        except ValueError as ex:
            print("FALLO edicion %d (%s): %s. ABORTO sin escribir nada." % (k, e[0], ex))
            return 1
        print("OK edicion %2d %-46s %s" % (k, e[0], e[1]))
    try:
        cfg = json.loads(new[F_JSON])
    except ValueError as ex:
        print("FALLO: sniffer.json deja de ser JSON valido: %s. ABORTO." % ex)
        return 1
    ks = cfg.get("kernel_space", {})
    for fld in ("alpha", "tau_s", "k_in", "k_out", "warm_windows", "floor_pps", "evict_windows"):
        if "ddos_victim_ewma_" + fld not in ks:
            print("FALLO: falta kernel_space.ddos_victim_ewma_%s tras la edicion. ABORTO." % fld)
            return 1
    for f in files:
        if MARK not in new[f]:
            print("FALLO: %s quedaria sin la marca. ABORTO." % f)
            return 1
    if sys.argv[1] == "--check":
        print("CHECK OK: %d ediciones en %d ficheros; sniffer.json valido. Nada escrito." % (len(EDITS), len(files)))
        return 0
    for f in files:
        p = os.path.join(ROOT, f)
        tmp = p + ".d291tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(new[f])
        os.replace(tmp, p)
    print("APLICADO: %d ediciones en %d ficheros. No se ha commiteado." % (len(EDITS), len(files)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
