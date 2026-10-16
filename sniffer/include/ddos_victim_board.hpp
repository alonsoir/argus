// sniffer/include/ddos_victim_board.hpp
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
#include "ddos_contract_v2.hpp"  // [DDOS-H2-D286]

#include <atomic>
#include <chrono>
#include <cstdint>
#include <memory>
#include <mutex>
#include <optional>  // [DDOS-ESTADO-ARRANQUE-D299]
#include <algorithm>     // [DDOS-ESTADO-PERSIST-D299]
#include <cinttypes>
#include <cmath>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <system_error>
#include <unordered_map>

namespace sniffer {

struct DdosVictimCounts {
    uint64_t d_pkts = 0;
    uint64_t d_bytes = 0;
    float rate_ratio = 0.0f;  // [DDOS-H2-D286] escalada; 0 si ventana degenerada
    ::argus::ddos::VictimEwmaEstado estado = ::argus::ddos::VictimEwmaEstado::Normal;  // [DDOS-ETAPA1-D298]
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
    bool en_arranque = false;       // [DDOS-ESTADO-ARRANQUE-D299] sin foto y dentro del plazo de arranque
    bool arranque_vencido = false;  // [DDOS-ESTADO-ARRANQUE-D299] sin foto, plazo marcado y ya vencido
    float rate_ratio = 0.0f;  // [DDOS-H2-D286]
    // [DDOS-ETAPA1-D298] victima ausente de la instantanea (sin trafico en la ventana) = NORMAL: sin presion
    ::argus::ddos::VictimEwmaEstado estado = ::argus::ddos::VictimEwmaEstado::Normal;
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

// [DDOS-ESTADO-ARRANQUE-D299] Estado que se sella en el evento. Con foto: el del tablero (victima ausente = NORMAL).
// Sin foto y dentro del plazo de arranque: FRIO (la victima aun no tiene historia). Sin foto fuera
// del plazo, o sin plazo marcado (agregador apagado o lector sin arrancar): nada; el evento llega con
// victim_state UNKNOWN y el ml-detector avisa [DDOS-V2-ANOMALIA] estado_victima_ausente.
inline std::optional<::argus::ddos::VictimEwmaEstado> sello_estado_victima(const DdosVictimLookup& r) noexcept {
    if (r.have_snapshot) return r.estado;
    if (r.en_arranque) return ::argus::ddos::VictimEwmaEstado::Frio;
    return std::nullopt;
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
        s->window_ms = ddos_window_ms(w);  // [DDOS-WMS-D286] definicion unica (redondeo), la misma que el CSV
        s->published_ns = now_ns;
        s->by_key.reserve(w.victims.size());
        aplicar_rebase_si_pendiente(seq);  // [DDOS-ESTADO-PERSIST-D299] huecos contados desde el rearranque
        for (const auto& v : w.victims) {
            const uint64_t key = ddos_victim_key(v.dst_ip, v.proto);
            float ratio = 0.0f;  // [DDOS-H2-D286] solo con ventana de duracion > 0
            auto estado = ::argus::ddos::VictimEwmaEstado::Normal;  // [DDOS-ETAPA1-D298]
            if (s->window_ms > 0) {
                const double pps = static_cast<double>(v.d_pkts) * 1000.0 / static_cast<double>(s->window_ms);
                auto& st = ewma_[key];
                ratio = static_cast<float>(::argus::ddos::victim_ewma_step(st, seq, pps, ewma_params_));
                estado = ::argus::ddos::victim_ewma_estado(st, ewma_params_);
            }
            s->by_key[key] = DdosVictimCounts{v.d_pkts, v.d_bytes, ratio, estado};
        }
        if (seq % 60 == 0) evict_stale_ewma(seq);  // [DDOS-H2-D286] memoria acotada
        if (persistencia_activa_ && ewma_params_.estado_volcado_ventanas > 0 &&
            seq % ewma_params_.estado_volcado_ventanas == 0) {
            volcado_periodico();  // [DDOS-ESTADO-PERSIST-D299] mismo hilo que escribe la EWMA: sin cerrojos
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
        if (!s) {  // [DDOS-ESTADO-ARRANQUE-D299]
            const uint64_t ini = arranque_ns_.load(std::memory_order_acquire);
            if (ini != 0) {
                const uint64_t plazo = arranque_plazo_ns_.load(std::memory_order_relaxed);
                if (now_ns < ini || now_ns - ini < plazo) {
                    r.en_arranque = true;
                    frio_arranque_.fetch_add(1, std::memory_order_relaxed);
                } else {
                    r.arranque_vencido = true;
                }
            }
            return r;
        }
        r.have_snapshot = true;
        r.seq = s->seq;
        r.window_ms = s->window_ms;
        r.age_ms = (now_ns >= s->published_ns) ? (now_ns - s->published_ns) / 1'000'000ULL : 0;
        const auto it = s->by_key.find(ddos_victim_key(dst_ip, proto));
        if (it != s->by_key.end()) {
            r.d_pkts = it->second.d_pkts;
            r.d_bytes = it->second.d_bytes;
            r.rate_ratio = it->second.rate_ratio;  // [DDOS-H2-D286]
            r.estado = it->second.estado;          // [DDOS-ETAPA1-D298]
        }
        return r;
    }

    uint64_t published() const { return published_.load(std::memory_order_relaxed); }

    // [DDOS-ESTADO-ARRANQUE-D299] Plazo de arranque: main lo marca ANTES de arrancar el consumidor del anillo si el
    // agregador esta activo, y lo borra si el lector no llega a arrancar.
    void marcar_arranque(uint64_t inicio_ns, uint64_t plazo_ns) {
        arranque_plazo_ns_.store(plazo_ns, std::memory_order_relaxed);
        arranque_ns_.store(inicio_ns == 0 ? 1 : inicio_ns, std::memory_order_release);
    }
    void borrar_arranque() { arranque_ns_.store(0, std::memory_order_release); }
    uint64_t arranque_ns() const { return arranque_ns_.load(std::memory_order_acquire); }
    uint64_t frio_arranque() const { return frio_arranque_.load(std::memory_order_relaxed); }

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

    // [DDOS-HYST-D291] parametros de la EWMA por victima (de sniffer.json, ya validados).
    // Llamar ANTES de arrancar el lector: publish_window (escritor unico) es quien los lee.
    void set_ewma_params(const ::argus::ddos::VictimEwmaParams& p) { ewma_params_ = p; }
    const ::argus::ddos::VictimEwmaParams& ewma_params() const { return ewma_params_; }

private:
    mutable std::mutex m_;
    std::shared_ptr<const DdosVictimSnapshot> snap_;
    std::atomic<uint64_t> published_{0};
    std::atomic<uint64_t> arranque_ns_{0};            // [DDOS-ESTADO-ARRANQUE-D299] 0 = sin plazo marcado
    std::atomic<uint64_t> arranque_plazo_ns_{0};      // [DDOS-ESTADO-ARRANQUE-D299]
    mutable std::atomic<uint64_t> frio_arranque_{0};  // [DDOS-ESTADO-ARRANQUE-D299] eventos sellados FRIO sin foto
    bool persistencia_activa_ = false;   // [DDOS-ESTADO-PERSIST-D299] solo main la activa; los tests no escriben
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
    // [DDOS-H2-D286] estado de la EWMA por victima. SOLO lo toca el hilo que llama a
    // publish_window (el lector del kernel, escritor unico): sin cerrojo propio.
    std::unordered_map<uint64_t, ::argus::ddos::VictimEwmaState> ewma_;
    ::argus::ddos::VictimEwmaParams ewma_params_{};  // [DDOS-HYST-D291]
    void evict_stale_ewma(uint64_t seq) {
        for (auto it = ewma_.begin(); it != ewma_.end();) {
            if (seq > it->second.last_seq + ewma_params_.evict_windows) it = ewma_.erase(it);
            else ++it;
        }
    }
};

}  // namespace sniffer
