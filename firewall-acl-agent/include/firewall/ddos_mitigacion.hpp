// ddos_mitigacion.hpp -- [DDOS-MITIGACION-D301] paso 3b: mitigacion real de la cabeza ddos_v2 (funciones puras).
// Por cada DROP de ddos_v2 cuyo origen NO esta protegido (el suscriptor filtra antes con ddos_protegidos) decide:
//   NADA      mitigacion deshabilitada o victima {dst, proto} fuera de episodio: un DROP aislado no bloquea.
//   ESPERAR   victima en episodio; el origen aun no suma min_drops_origen DROP en ESTE episodio.
//   BLOQUEAR  primer bloqueo del origen en ESTE episodio: cuenta UN strike de reincidencia (RECIDIVISM-D276).
//   RENOVAR   origen ya bloqueado en este episodio: se re-anade al ipset con el escalon vigente SIN sumar strike
//             (decision de Alonso DAY301: un episodio = un strike; mientras siga atacando el bloqueo no vence;
//             tras su ultimo DROP corre el escalon entero).
// El episodio lo decide DdosShadowPolicy (INICIO..FIN) y aqui solo se consulta (en_episodio). Un origen que disparo
// el INICIO y sigue atacando se bloquea en su siguiente DROP; uno que ya no ataca no se bloquea.
// Un mismo origen contra dos victimas en episodio = dos episodios = dos strikes.
// Memoria acotada por max_origenes (todas las victimas): por encima, un origen nuevo sale como RENOVAR (se bloquea con
// el escalon vigente y NUNCA suma strike) y se cuenta en desbordes() para el log.
// Sin E/S ni reloj: testeable sin root (tests/unit/test_ddos_mitigacion.cpp).
#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>

namespace mldefender::firewall {

struct DdosMitigacionParams {
    bool habilitada = false;             // 2.a llave (la 1.a es operation.dry_run). Defecto: sombra pura.
    int min_drops_origen = 1;            // [1, 100]; techo PROVISIONAL, a fijar con la medida del E2E.
    int aviso_castigo_corto_sec = 3600;  // [1, 2147483]; escalones por debajo = solo pruebas (WARN periodico).
    int max_origenes = 100000;           // [1, 10000000]; origenes seguidos a la vez entre todas las victimas.
};

enum class AccionMitigacion : uint8_t { NADA = 0, ESPERAR = 1, BLOQUEAR = 2, RENOVAR = 3 };

inline const char* nombre_accion(AccionMitigacion a) {
    switch (a) {
        case AccionMitigacion::NADA: return "NADA";
        case AccionMitigacion::ESPERAR: return "ESPERAR";
        case AccionMitigacion::BLOQUEAR: return "BLOQUEAR";
        case AccionMitigacion::RENOVAR: return "RENOVAR";
    }
    return "?";
}

// Escalones de la escalera de reincidencia por debajo del umbral de aviso: van al log como WARN (solo pruebas).
inline std::vector<uint32_t> escalones_cortos(const std::vector<uint32_t>& escalera, uint32_t aviso_sec) {
    std::vector<uint32_t> out;
    for (uint32_t e : escalera) {
        if (e < aviso_sec) {
            out.push_back(e);
        }
    }
    return out;
}

class DdosMitigacion {
public:
    explicit DdosMitigacion(const DdosMitigacionParams& p) : p_(p) {}

    AccionMitigacion decidir(const std::string& dst, uint32_t proto, const std::string& src, bool en_episodio) {
        if (!p_.habilitada) {
            return AccionMitigacion::NADA;
        }
        const std::string key = clave(dst, proto);
        if (!en_episodio) {
            olvidar(key);
            return AccionMitigacion::NADA;
        }
        auto [vit, nueva] = v_.try_emplace(key);
        if (nueva) {
            vit->second.dst = dst;
            vit->second.proto = proto;
        }
        auto& origenes = vit->second.origenes;
        auto oit = origenes.find(src);
        if (oit == origenes.end()) {
            if (total_ >= static_cast<std::size_t>(p_.max_origenes)) {
                ++desbordes_;
                return AccionMitigacion::RENOVAR;
            }
            oit = origenes.emplace(src, Origen{}).first;
            ++total_;
        }
        Origen& o = oit->second;
        if (o.bloqueado) {
            return AccionMitigacion::RENOVAR;
        }
        if (++o.drops < static_cast<uint32_t>(p_.min_drops_origen)) {
            return AccionMitigacion::ESPERAR;
        }
        o.bloqueado = true;
        return AccionMitigacion::BLOQUEAR;
    }

    // Olvida las victimas que ya no estan en episodio (FIN sin DROP posterior). Llamar periodicamente.
    template <class F>
    std::size_t purgar(F en_episodio) {
        std::size_t n = 0;
        for (auto it = v_.begin(); it != v_.end();) {
            if (!en_episodio(it->second.dst, it->second.proto)) {
                total_ -= it->second.origenes.size();
                it = v_.erase(it);
                ++n;
            } else {
                ++it;
            }
        }
        return n;
    }

    std::size_t victimas_seguidas() const noexcept { return v_.size(); }
    std::size_t origenes_seguidos() const noexcept { return total_; }
    uint64_t desbordes() const noexcept { return desbordes_; }
    const DdosMitigacionParams& params() const noexcept { return p_; }

private:
    struct Origen {
        uint32_t drops = 0;
        bool bloqueado = false;
    };
    struct Victima {
        std::string dst;
        uint32_t proto = 0;
        std::unordered_map<std::string, Origen> origenes;
    };

    static std::string clave(const std::string& dst, uint32_t proto) { return dst + "/" + std::to_string(proto); }

    void olvidar(const std::string& key) {
        auto it = v_.find(key);
        if (it != v_.end()) {
            total_ -= it->second.origenes.size();
            v_.erase(it);
        }
    }

    DdosMitigacionParams p_;
    std::unordered_map<std::string, Victima> v_;
    std::size_t total_ = 0;
    uint64_t desbordes_ = 0;
};

}  // namespace mldefender::firewall
