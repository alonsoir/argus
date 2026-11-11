#pragma once
// firewall-acl-agent/include/firewall/protegidos_rp_filter.hpp — [PROTEGIDOS-RP-FILTER-D321] ADR-060 H-F (8e.4c,
// DEBT-FW-ANTISPOOF-RP-FILTER-001): el agente LEE rp_filter de las interfaces del manifiesto vigente y lo INFORMA; no lo
// cambia nunca (medido DAY320: 0 en todas las interfaces del defender). El kernel usa el máximo de conf/all/rp_filter y
// conf/<interfaz>/rp_filter (0 sin filtro, 1 estricto, 2 laxo). Al arrancar y cada protegidos.aviso_sec, en el bucle
// principal (fuera del camino del paquete). O(interfaces): como mucho una por entrada del manifiesto.
// La raíz (/proc/sys/net/ipv4/conf) se inyecta para el test.
#include <cstddef>
#include <fstream>
#include <set>
#include <sstream>
#include <string>
#include <vector>

namespace mldefender::firewall {

inline constexpr const char* kRaizRpFilter = "/proc/sys/net/ipv4/conf";

struct RpFilterInterfaz {
    std::string interfaz;
    int todas = -1;     // conf/all/rp_filter; -1 = no se pudo leer
    int propio = -1;    // conf/<interfaz>/rp_filter; -1 = no se pudo leer (p. ej. la interfaz no existe)
    int efectivo = -1;  // max(todas, propio); -1 si falta alguno
};

namespace detalle_rp {
// Lee un entero en [0, 2] de un fichero de /proc; -1 si no existe, no se lee o no es 0, 1 o 2
inline int leer_valor(const std::string& ruta) {
    std::ifstream f(ruta);
    if (!f) return -1;
    std::string s;
    if (!std::getline(f, s)) return -1;
    while (!s.empty() && (s.back() == ' ' || s.back() == '\r' || s.back() == '\t')) s.pop_back();
    if (s == "0") return 0;
    if (s == "1") return 1;
    if (s == "2") return 2;
    return -1;
}
// Las interfaces vienen de un manifiesto verificado ([A-Za-z0-9._-]{1,15}); aun así, nada que salga de la raíz
inline bool interfaz_segura(const std::string& i) {
    if (i.empty() || i.size() > 15 || i == "." || i == "..") return false;
    for (const char c : i) {
        const bool ok = (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '.' ||
                        c == '_' || c == '-';
        if (!ok) return false;
    }
    return true;
}
inline const char* significado(int v) {
    switch (v) {
        case 0: return "sin filtro";
        case 1: return "estricto";
        case 2: return "laxo";
        default: return "ilegible";
    }
}
}  // namespace detalle_rp

// Interfaces distintas, en orden alfabético; las inseguras se devuelven con todo a -1 (salen como ilegibles)
inline std::vector<RpFilterInterfaz> leer_rp_filter(const std::vector<std::string>& interfaces,
                                                    const std::string& raiz = kRaizRpFilter) {
    const std::set<std::string> unicas(interfaces.begin(), interfaces.end());
    const int todas = detalle_rp::leer_valor(raiz + "/all/rp_filter");
    std::vector<RpFilterInterfaz> out;
    out.reserve(unicas.size());
    for (const auto& i : unicas) {
        RpFilterInterfaz r;
        r.interfaz = i;
        if (detalle_rp::interfaz_segura(i)) {
            r.todas = todas;
            r.propio = detalle_rp::leer_valor(raiz + "/" + i + "/rp_filter");
            if (r.todas >= 0 && r.propio >= 0) r.efectivo = r.todas > r.propio ? r.todas : r.propio;
        }
        out.push_back(r);
    }
    return out;
}

// Una línea para el log: [PROTEGIDOS-RP-FILTER] eth1=0 (all=0 if=0, sin filtro) ...; solo se informa
inline std::string linea_rp_filter(const std::vector<RpFilterInterfaz>& v, bool hay_manifiesto) {
    std::ostringstream o;
    o << "[PROTEGIDOS-RP-FILTER] ";
    if (!hay_manifiesto) {
        o << "sin manifiesto vigente: no hay interfaces que mirar";
        return o.str();
    }
    if (v.empty()) {
        o << "el manifiesto vigente no trae entradas IPv4 en este firewall: no hay interfaces que mirar";
        return o.str();
    }
    for (std::size_t k = 0; k < v.size(); ++k) {
        const auto& r = v[k];
        if (k) o << " ";
        o << r.interfaz << "=";
        if (r.efectivo >= 0) {
            o << r.efectivo;
        } else {
            o << "?";
        }
        o << " (all=" << (r.todas >= 0 ? std::to_string(r.todas) : std::string("?"))
          << " if=" << (r.propio >= 0 ? std::to_string(r.propio) : std::string("?")) << ", "
          << detalle_rp::significado(r.efectivo) << ")";
    }
    o << "; el kernel usa max(all, interfaz): 0 sin filtro, 1 estricto, 2 laxo; solo se informa, no se cambia (H-F)";
    return o.str();
}

}  // namespace mldefender::firewall
