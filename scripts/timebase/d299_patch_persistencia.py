#!/usr/bin/env python3
"""DAY299 paso 4 -- DEBT-DDOS-STATE-PERSIST-001. Estado por victima (ewma, seen, bajo_presion) volcado cada
N ventanas (hilo del lector) y en la parada (main, lector parado); restaurado al arrancar (main, antes del
lector) con caducidad; restauradas = calientes, conservan bajo_presion; rebase de last_seq en la primera
ventana publicada (si no, gap>1 sacaria a la victima de bajo_presion). Fallo = aviso [DDOS-ESTADO] y arranque
en frio. Uso: --check | --apply (desde la raiz del repo). Atomico: todo o nada."""
import os
import sys

M = "[DDOS-ESTADO-PERSIST-D299]"
CONTRATO = "sniffer/include/ddos_contract_v2.hpp"
CFG = "sniffer/src/userspace/config_manager.cpp"
JSONF = "sniffer/config/sniffer.json"
BOARD = "sniffer/include/ddos_victim_board.hpp"
MAIN = "sniffer/src/userspace/main.cpp"
TEST = "sniffer/tests/test_ddos_victim_board.cpp"
GUIA = "docs/operaciones/GUIA_OPERACIONES.md"

EDITS = []
APPENDS = []


def ins_after(p, a, t):
    EDITS.append((p, a, a + t))


def ins_before(p, a, t):
    EDITS.append((p, a, t + a))


def repl(p, a, t):
    EDITS.append((p, a, t))


# ---------------- contrato ----------------
ins_after(CONTRATO, "#pragma once\n", "#include <string>  // [DDOS-ESTADO-PERSIST-D299]\n")
ins_after(CONTRATO,
    "    uint64_t arranque_ventanas = 5; // [DDOS-ESTADO-ARRANQUE-D299] plazo sin foto del agregador aceptado como arranque\n",
    r'''    std::string estado_ruta = "/var/lib/argus/sniffer/ddos_victim_estado.csv";  // [DDOS-ESTADO-PERSIST-D299]
    uint64_t estado_volcado_ventanas = 60;      // [DDOS-ESTADO-PERSIST-D299] volcado periodico del estado
    uint64_t estado_max_edad_ventanas = 86400;  // [DDOS-ESTADO-PERSIST-D299] caducidad al restaurar
''')
ins_after(CONTRATO,
    "inline constexpr double kVictimArranqueVentanasMin = 2.0, kVictimArranqueVentanasMax = 60.0;  // [DDOS-ESTADO-ARRANQUE-D299]\n",
    r'''inline constexpr double kVictimEstadoVolcadoMin = 5.0, kVictimEstadoVolcadoMax = 3600.0;   // [DDOS-ESTADO-PERSIST-D299]
inline constexpr double kVictimEstadoEdadMin = 60.0, kVictimEstadoEdadMax = 604800.0;      // [DDOS-ESTADO-PERSIST-D299]
''')
ins_before(CONTRATO,
    "// Validacion completa: rangos + regla cruzada (k_out < k_in).\n",
    r'''// [DDOS-ESTADO-PERSIST-D299] ruta absoluta de fichero: empieza por '/', no acaba en '/', sin saltos de linea.
inline bool victim_estado_ruta_ok(const std::string& r) noexcept {
    return r.size() > 1 && r.front() == '/' && r.back() != '/' && r.find('\n') == std::string::npos;
}

''')
ins_after(CONTRATO,
    "           victim_ewma_in_range(static_cast<double>(p.arranque_ventanas), kVictimArranqueVentanasMin,\n"
    "                                kVictimArranqueVentanasMax) &&  // [DDOS-ESTADO-ARRANQUE-D299]\n",
    r'''           victim_ewma_in_range(static_cast<double>(p.estado_volcado_ventanas), kVictimEstadoVolcadoMin,
                                kVictimEstadoVolcadoMax) &&  // [DDOS-ESTADO-PERSIST-D299]
           victim_ewma_in_range(static_cast<double>(p.estado_max_edad_ventanas), kVictimEstadoEdadMin,
                                kVictimEstadoEdadMax) &&
           victim_estado_ruta_ok(p.estado_ruta) &&
''')

# ---------------- config ----------------
ins_after(CFG,
    "    p.arranque_ventanas = static_cast<uint64_t>(x);  // [DDOS-ESTADO-ARRANQUE-D299]\n",
    r'''    n += ddos_ewma_num(k, "ddos_victim_estado_volcado_ventanas", static_cast<double>(d.estado_volcado_ventanas),
                       dd::kVictimEstadoVolcadoMin, dd::kVictimEstadoVolcadoMax, true, x);
    p.estado_volcado_ventanas = static_cast<uint64_t>(x);  // [DDOS-ESTADO-PERSIST-D299]
    n += ddos_ewma_num(k, "ddos_victim_estado_max_edad_ventanas", static_cast<double>(d.estado_max_edad_ventanas),
                       dd::kVictimEstadoEdadMin, dd::kVictimEstadoEdadMax, true, x);
    p.estado_max_edad_ventanas = static_cast<uint64_t>(x);
    if (k.isMember("ddos_victim_estado_ruta") && k["ddos_victim_estado_ruta"].isString() &&
        dd::victim_estado_ruta_ok(k["ddos_victim_estado_ruta"].asString())) {
        p.estado_ruta = k["ddos_victim_estado_ruta"].asString();
    } else {
        std::cerr << "[CONFIG-DEFAULT] kernel_space.ddos_victim_estado_ruta: falta, no es texto o no es una ruta "
                     "absoluta de fichero (formato /dir/fichero) -> " << d.estado_ruta << std::endl;
        ++n;
    }
''')
repl(CFG,
    "              << std::endl;  // [DDOS-ESTADO-ARRANQUE-D299]\n",
    r'''              << " estado_ruta=" << p.estado_ruta << " volcado_ventanas=" << p.estado_volcado_ventanas
              << " max_edad_ventanas=" << p.estado_max_edad_ventanas
              << std::endl;  // [DDOS-ESTADO-ARRANQUE-D299] [DDOS-ESTADO-PERSIST-D299]
''')

# ---------------- sniffer.json ----------------
ins_after(JSONF, '    "ddos_victim_arranque_ventanas": 5,\n',
    r'''    "_doc_ddos_victim_estado_ruta": "texto, ruta absoluta de fichero (empieza por /, no acaba en /), defecto /var/lib/argus/sniffer/ddos_victim_estado.csv. [DDOS-ESTADO-PERSIST-D299] Estado por victima (EWMA, ventanas vistas, bajo_presion) que se vuelca periodicamente y en la parada y se restaura al arrancar: un reinicio en mitad de un ataque no lo olvida (sin esto todas las victimas vuelven a frio y un ataque por debajo de abs_pps se aprende como base). Es estado, no log: no ponerlo en logs/. El sniffer crea el directorio; el fichero queda con permisos 600. Fallo de lectura o escritura: aviso [DDOS-ESTADO] y el sniffer arranca igual, en frio (docs/operaciones/GUIA_OPERACIONES.md seccion DDOS-ESTADO). Integridad frente a manipulacion pendiente (DEBT-DDOS-STATE-HMAC-001). Si falta o no es valida: defecto con [CONFIG-DEFAULT].",
    "ddos_victim_estado_ruta": "/var/lib/argus/sniffer/ddos_victim_estado.csv",
    "_doc_ddos_victim_estado_volcado_ventanas": "entero, rango [5, 3600], defecto 60 (1 min con ventanas de 1000 ms). [DDOS-ESTADO-PERSIST-D299] Cada cuantas ventanas se vuelca el estado: es lo que se pierde como mucho con un kill -9 o un corte de luz (la parada ordenada vuelca siempre). Defecto SEGURO, no optimo: calibrar en cada instalacion.",
    "ddos_victim_estado_volcado_ventanas": 60,
    "_doc_ddos_victim_estado_max_edad_ventanas": "entero, rango [60, 604800], defecto 86400 (1 dia con ventanas de 1000 ms). [DDOS-ESTADO-PERSIST-D299] Un volcado mas viejo se descarta al arrancar (aviso y arranque en frio). Largo a proposito: un DDoS puede durar dias y el estado restaurado se corrige solo (una victima normal reaprende en unas 10 ventanas; una bajo presion sale cuando su trafico vuelve a la base). Tambien se descarta un volcado con fecha futura o con otro ddos_kernel_agg_interval_ms. Defecto SEGURO, no optimo.",
    "ddos_victim_estado_max_edad_ventanas": 86400,
''')

# ---------------- tablero ----------------
ins_after(BOARD, "#include <optional>  // [DDOS-ESTADO-ARRANQUE-D299]\n",
    r'''#include <algorithm>     // [DDOS-ESTADO-PERSIST-D299]
#include <cinttypes>
#include <cmath>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <system_error>
''')
ins_after(BOARD, "        s->by_key.reserve(w.victims.size());\n",
    "        aplicar_rebase_si_pendiente(seq);  // [DDOS-ESTADO-PERSIST-D299] huecos contados desde el rearranque\n")
ins_after(BOARD, "        if (seq % 60 == 0) evict_stale_ewma(seq);  // [DDOS-H2-D286] memoria acotada\n",
    r'''        if (persistencia_activa_ && ewma_params_.estado_volcado_ventanas > 0 &&
            seq % ewma_params_.estado_volcado_ventanas == 0) {
            volcado_periodico();  // [DDOS-ESTADO-PERSIST-D299] mismo hilo que escribe la EWMA: sin cerrojos
        }
''')
ins_after(BOARD, "    uint64_t frio_arranque() const { return frio_arranque_.load(std::memory_order_relaxed); }\n",
    r'''
    // ===== [DDOS-ESTADO-PERSIST-D299] persistencia del estado por victima =====
    // Todo lo que toca ewma_ se llama desde el hilo del lector (volcado periodico) o con el lector
    // parado o sin arrancar (main: restauracion antes de start(), volcado de parada tras stop()).
    struct RestauracionEstado {
        bool existe = false;
        bool ok = false;
        std::size_t victimas = 0;
        std::size_t bajo_presion = 0;
        uint64_t edad_ns = 0;
        std::string motivo;
    };
    static constexpr const char* kEstadoCabecera = "argus-ddos-victim-estado v1";
    static constexpr const char* kEstadoColumnas = "dst_ip,proto,ewma,seen,bajo_presion";

    void activar_persistencia() { persistencia_activa_ = true; }

    bool volcar_estado(const std::string& ruta, uint64_t wall_ns, std::string& err) const {
        std::error_code ec;
        const std::filesystem::path dest(ruta);
        if (dest.has_parent_path()) std::filesystem::create_directories(dest.parent_path(), ec);
        if (ec) {
            err = "no se puede crear " + dest.parent_path().string() + ": " + ec.message();
            return false;
        }
        const std::string tmp = ruta + ".tmp";
        {
            std::ofstream f(tmp, std::ios::trunc);
            if (!f) {
                err = "no se puede abrir " + tmp;
                return false;
            }
            f << kEstadoCabecera << '\n'
              << "volcado_wall_ns=" << wall_ns << " interval_ms=" << ewma_params_.interval_ms
              << " filas=" << ewma_.size() << '\n'
              << kEstadoColumnas << '\n';
            f.precision(17);
            for (const auto& [key, st] : ewma_) {
                f << (key >> 32) << ',' << (key & 0xffffffffULL) << ',' << st.ewma << ',' << st.seen << ','
                  << (st.bajo_presion ? 1 : 0) << '\n';
            }
            f.flush();
            if (!f) {
                err = "error de escritura en " + tmp;
                return false;
            }
        }
        std::filesystem::permissions(tmp, std::filesystem::perms::owner_read | std::filesystem::perms::owner_write,
                                     std::filesystem::perm_options::replace, ec);
        std::filesystem::rename(tmp, dest, ec);
        if (ec) {
            err = "no se puede renombrar " + tmp + ": " + ec.message();
            return false;
        }
        return true;
    }

    RestauracionEstado restaurar_estado(const std::string& ruta, uint64_t ahora_wall_ns, uint64_t max_edad_ns) {
        RestauracionEstado r;
        std::ifstream f(ruta);
        if (!f) {
            r.motivo = "no existe o no se puede leer";
            return r;
        }
        r.existe = true;
        std::string l;
        if (!std::getline(f, l) || l != kEstadoCabecera) {
            r.motivo = "cabecera desconocida";
            return r;
        }
        uint64_t wall = 0;
        double iv = 0.0;
        unsigned long long filas = 0;
        if (!std::getline(f, l) ||
            std::sscanf(l.c_str(), "volcado_wall_ns=%" SCNu64 " interval_ms=%lf filas=%llu", &wall, &iv, &filas) != 3) {
            r.motivo = "linea de metadatos mal formada";
            return r;
        }
        if (!std::getline(f, l) || l != kEstadoColumnas) {
            r.motivo = "columnas desconocidas";
            return r;
        }
        if (wall > ahora_wall_ns) {
            r.motivo = "fecha del volcado en el futuro (reloj de pared atrasado o fichero ajeno)";
            return r;
        }
        r.edad_ns = ahora_wall_ns - wall;
        if (r.edad_ns > max_edad_ns) {
            r.motivo = "caducado";
            return r;
        }
        if (!(std::fabs(iv - ewma_params_.interval_ms) < 0.5)) {
            r.motivo = "interval_ms del volcado distinto del actual";
            return r;
        }
        std::unordered_map<uint64_t, ::argus::ddos::VictimEwmaState> nuevo;
        unsigned long long leidas = 0;
        while (std::getline(f, l)) {
            if (l.empty()) continue;
            unsigned long long ip = 0, proto = 0, seen = 0;
            double ewma = 0.0;
            int bajo = -1, usados = 0;
            if (std::sscanf(l.c_str(), "%llu,%llu,%lf,%llu,%d%n", &ip, &proto, &ewma, &seen, &bajo, &usados) != 5 ||
                static_cast<std::size_t>(usados) != l.size() || ip > 0xffffffffULL || proto > 255ULL ||
                seen > (1ULL << 40) || !std::isfinite(ewma) || ewma < 0.0 || (bajo != 0 && bajo != 1)) {
                r.motivo = "fila " + std::to_string(leidas + 1) + " mal formada";
                return r;
            }
            ::argus::ddos::VictimEwmaState st;
            st.ewma = ewma;
            st.seen = std::max<uint64_t>(static_cast<uint64_t>(seen), ewma_params_.warm_windows);
            st.bajo_presion = (bajo == 1);
            st.last_seq = 0;
            nuevo[ddos_victim_key(static_cast<uint32_t>(ip), static_cast<uint32_t>(proto))] = st;
            ++leidas;
        }
        if (leidas != filas) {
            r.motivo = "filas leidas (" + std::to_string(leidas) + ") distintas de la cabecera (" +
                       std::to_string(filas) + ")";
            return r;
        }
        for (const auto& kv : nuevo) if (kv.second.bajo_presion) ++r.bajo_presion;
        r.victimas = nuevo.size();
        ewma_ = std::move(nuevo);
        rebase_pendiente_ = true;
        r.ok = true;
        return r;
    }

    // Primera ventana publicada tras restaurar: last_seq = seq - 1 para que el hueco cuente desde el
    // rearranque (el lector numera desde 1 y publica desde 2; con last_seq 0 el gap 2 sacaria de bajo_presion).
    void aplicar_rebase_si_pendiente(uint64_t seq) {
        if (!rebase_pendiente_) return;
        for (auto& kv : ewma_) kv.second.last_seq = (seq > 0) ? seq - 1 : 0;
        rebase_pendiente_ = false;
    }

    std::optional<::argus::ddos::VictimEwmaState> estado_ewma(uint64_t key) const {
        const auto it = ewma_.find(key);
        if (it == ewma_.end()) return std::nullopt;
        return it->second;
    }

    void restaurar_al_arrancar() {
        const auto& p = ewma_params_;
        const uint64_t max_ns =
            static_cast<uint64_t>(static_cast<double>(p.estado_max_edad_ventanas) * p.interval_ms * 1.0e6);
        const RestauracionEstado r = restaurar_estado(p.estado_ruta, wall_now_ns(), max_ns);
        if (r.ok) {
            std::cout << "[DDOS-ESTADO] restauradas " << r.victimas << " victimas (" << r.bajo_presion
                      << " bajo presion) de " << p.estado_ruta << ", volcado de hace " << r.edad_ns / 1000000000ULL
                      << " s" << std::endl;
        } else if (!r.existe) {
            std::cout << "[DDOS-ESTADO] sin estado previo en " << p.estado_ruta
                      << ": todas las victimas arrancan en frio (normal en la primera ejecucion)" << std::endl;
        } else {
            std::cerr << "[DDOS-ESTADO] AVISO estado previo descartado (" << r.motivo
                      << "): todas las victimas arrancan en frio. Guia: docs/operaciones/GUIA_OPERACIONES.md "
                         "seccion DDOS-ESTADO" << std::endl;
        }
    }

    void volcar_parada() {
        if (!persistencia_activa_ || published() == 0) return;  // sin foto no hay nada observado que guardar
        std::string err;
        std::size_t bajo = 0;
        for (const auto& kv : ewma_) if (kv.second.bajo_presion) ++bajo;
        if (volcar_estado(ewma_params_.estado_ruta, wall_now_ns(), err)) {
            std::cout << "[DDOS-ESTADO] volcado de parada: " << ewma_.size() << " victimas (" << bajo
                      << " bajo presion) en " << ewma_params_.estado_ruta << std::endl;
        } else {
            std::cerr << "[DDOS-ESTADO] AVISO volcado de parada fallido: " << err << std::endl;
        }
    }
''')
ins_after(BOARD,
    "    mutable std::atomic<uint64_t> frio_arranque_{0};  // [DDOS-ESTADO-ARRANQUE-D299] eventos sellados FRIO sin foto\n",
    r'''    bool persistencia_activa_ = false;   // [DDOS-ESTADO-PERSIST-D299] solo main la activa; los tests no escriben
    bool rebase_pendiente_ = false;      // [DDOS-ESTADO-PERSIST-D299]
    bool primer_volcado_hecho_ = false;  // [DDOS-ESTADO-PERSIST-D299]
    static uint64_t wall_now_ns() {
        return static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
                                         std::chrono::system_clock::now().time_since_epoch())
                                         .count());
    }
    void volcado_periodico() {  // [DDOS-ESTADO-PERSIST-D299] hilo del lector
        std::string err;
        if (volcar_estado(ewma_params_.estado_ruta, wall_now_ns(), err)) {
            if (!primer_volcado_hecho_) {
                primer_volcado_hecho_ = true;
                std::cout << "[DDOS-ESTADO] primer volcado: " << ewma_.size() << " victimas en "
                          << ewma_params_.estado_ruta << " (cada " << ewma_params_.estado_volcado_ventanas
                          << " ventanas)" << std::endl;
            }
        } else {
            std::cerr << "[DDOS-ESTADO] AVISO no se pudo volcar el estado por victima: " << err
                      << ". Si el sniffer se reinicia, las victimas arrancaran en frio. Guia: "
                         "docs/operaciones/GUIA_OPERACIONES.md seccion DDOS-ESTADO" << std::endl;
        }
    }
''')

# ---------------- main ----------------
ins_after(MAIN, "        g_ddos_victim_board->set_ewma_params(g_config.kernel_space.ddos_victim_ewma);\n",
    r'''        // [DDOS-ESTADO-PERSIST-D299] estado por victima del arranque anterior, ANTES de arrancar el lector
        // (escritor unico de la EWMA). Fallo o caducidad = aviso y arranque en frio; nunca tumba el sniffer.
        if (g_config.kernel_space.ddos_kernel_agg_enabled) {
            g_ddos_victim_board->activar_persistencia();
            g_ddos_victim_board->restaurar_al_arrancar();
        }
''')
repl(MAIN,
    "        if (ddos_reader_ptr) {\n"
    "            ddos_reader_ptr->stop();\n"
    "            delete ddos_reader_ptr;\n"
    "            ddos_reader_ptr = nullptr;\n"
    "        }\n"
    "\n"
    "        // Stop RingBufferConsumer first\n",
    "        if (ddos_reader_ptr) {\n"
    "            ddos_reader_ptr->stop();\n"
    "            delete ddos_reader_ptr;\n"
    "            ddos_reader_ptr = nullptr;\n"
    "        }\n"
    "        g_ddos_victim_board->volcar_parada();  // [DDOS-ESTADO-PERSIST-D299] el lector ya no toca la EWMA\n"
    "\n"
    "        // Stop RingBufferConsumer first\n")

# ---------------- test 15 ----------------
ins_after(TEST,
    "                    static_cast<unsigned long long>(b.frio_arranque()));\n    }\n",
    r'''    {   // 15. [DDOS-ESTADO-PERSIST-D299] persistencia del estado por victima
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
        // 15b rebase: primera ventana publicada (seq 2) con la victima presente -> sigue bajo presion,
        // EWMA congelada; sin rebase (gap 2) el episodio terminaria
        auto sin_rebase = *b2.estado_ewma(k1);
        dd::victim_ewma_step(sin_rebase, 2, 300.0, p);
        CHECK(!sin_rebase.bajo_presion);
        b1.aplicar_rebase_si_pendiente(2);
        auto st = *b1.estado_ewma(k1);
        CHECK(st.last_seq == 1);
        const double rat = dd::victim_ewma_step(st, 2, 300.0, p);
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
''')

# ---------------- guia ----------------
APPENDS.append((GUIA, """
---

## DDOS-ESTADO

El sniffer guarda el estado de cada víctima de la cabeza DDoS (su tráfico de base, cuántas ventanas lleva
vista y si está bajo presión) en `ddos_victim_estado_ruta` (por defecto
`/var/lib/argus/sniffer/ddos_victim_estado.csv`): cada `ddos_victim_estado_volcado_ventanas` ventanas y
al parar. Al arrancar lo restaura, para que un reinicio en mitad de un ataque no lo olvide. Sin ese
estado, todas las víctimas arrancan en frío y un ataque por debajo de `ddos_victim_ewma_abs_pps` se
aprendería como tráfico normal.

Líneas de `sniffer.log`:

- `[DDOS-ESTADO] restauradas N víctimas (M bajo presión) ..., volcado de hace X s`: normal.
- `[DDOS-ESTADO] sin estado previo ...`: normal en la primera ejecución. Si aparece en un reinicio
  normal, el volcado no está funcionando: buscar el AVISO de volcado.
- `[DDOS-ESTADO] primer volcado: ...` y `volcado de parada: ...`: normales.
- `[DDOS-ESTADO] AVISO no se pudo volcar ...`: se repite en cada intento fallido. Causas: permisos o disco
  lleno en el directorio de `ddos_victim_estado_ruta`. Corregirlo; el sniffer sigue protegiendo, pero un
  reinicio dejaría las víctimas en frío.
- `[DDOS-ESTADO] AVISO estado previo descartado (motivo)`: el sniffer arranca en frío. Según el motivo:
  - `caducado`: el sniffer estuvo parado más de `ddos_victim_estado_max_edad_ventanas`. Normal tras una
    parada larga.
  - `fecha del volcado en el futuro`: el reloj de la máquina va atrasado. Revisar la sincronización
    horaria (chrony; en el laboratorio, `make lab-clock-step`).
  - `interval_ms del volcado distinto del actual`: se cambió `ddos_kernel_agg_interval_ms`. Esperado una
    vez tras el cambio.
  - `cabecera desconocida`, `columnas desconocidas`, `fila N mal formada`, `filas leídas distintas`: el
    fichero está dañado o lo ha modificado alguien. **Guardar una copia para investigarlo** y abrir
    incidencia: un fichero manipulado podría intentar cegar la detección (la firma del fichero está
    pendiente, DEBT-DDOS-STATE-HMAC-001). El sniffer ya lo ha descartado y sigue en frío.

El fichero queda con permisos 600 (solo su dueño lo lee y escribe).
"""))


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: --check | --apply")
        return 2
    files = sorted({p for p, _, _ in EDITS} | {p for p, _ in APPENDS})
    t = {}
    for p in files:
        if not os.path.isfile(p):
            print(f"[FALLA] no existe {p}")
            return 1
        t[p] = open(p, encoding="utf-8").read()
    hechos = [new in t[p] for p, _, new in EDITS] + [txt.strip()[:40] in t[p] for p, txt in APPENDS]
    if all(hechos):
        print("[YA-APLICADO]")
        return 0
    if any(hechos):
        print("[ABORTA] mezcla de aplicado y pendiente:", hechos)
        return 1
    for i, (p, old, _) in enumerate(EDITS):
        n = t[p].count(old)
        if n != 1:
            print(f"[ABORTA] edicion {i} en {p}: ancla {n} veces: {old.splitlines()[0][:90]}")
            return 1
    if sys.argv[1] == "--check":
        print(f"[CHECK-OK] {len(EDITS)} ediciones y {len(APPENDS)} anexo pendientes en {len(files)} ficheros")
        return 0
    for p, old, new in EDITS:
        if t[p].count(old) != 1:
            print(f"[ABORTA] el ancla dejo de ser unica al aplicar en {p}")
            return 1
        t[p] = t[p].replace(old, new, 1)
    for p, txt in APPENDS:
        t[p] = t[p].rstrip("\n") + "\n" + txt
    for p in files:
        tmp = p + ".d299tmp"
        open(tmp, "w", encoding="utf-8").write(t[p])
        os.replace(tmp, p)
    print(f"[APLICADO] {len(EDITS)} ediciones y {len(APPENDS)} anexo en {len(files)} ficheros {M}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
