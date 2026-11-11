// protegidos_vigia.hpp -- [PROTEGIDOS-VIGIA-D320] ADR-060 D8, paso 8e.4a: el vigía kernel <-> manifiesto.
// Cada protegidos.comprobacion_kernel_sec el agente compara con lo vigente (el manifiesto verificado):
//   K1 el set de protegidos existe y es hash:net,iface (si falta se crea; si es de otro tipo, alarma y no se destruye);
//   K2 su contenido = las entradas IPv4 del vigente (sin vigente, vacío). Cualquier entrada de más, de menos o con
//      opciones (p. ej. 'nomatch', que anularía la exención) es divergencia y se reconcilia con la sustitución atómica;
//   K3 la cadena de aRGus: un único salto INPUT -> cadena en la posición 1 y dentro exactamente
//      [protegidos src,src RETURN] y [blacklist DROP], en ese orden. Si no, se rehace con setup_base_rules. Con el
//      set de otro tipo, la cadena se rehace SIN el RETURN (lo no firmado pierde la protección, D8).
// Coste: O(n) por vuelta con n acotado por kProtegidosMaxEntradas (conjunto hash), dos lecturas de ipset/iptables
// (medidas DAY320: 2-3 ms). Nada de esto va por el camino del paquete. En dry_run el agente no toca el kernel
// (regla de DAY302): el vigía no compara ni escribe, solo lo dice en el log.
#pragma once

#include "firewall/ipset_wrapper.hpp"
#include "firewall/iptables_wrapper.hpp"

#include <arpa/inet.h>

#include <cstdint>
#include <sstream>
#include <string>
#include <unordered_set>
#include <utility>
#include <vector>

namespace mldefender::firewall {

// Forma canónica de una entrada IPv4 del set: "<red con los bits de host a cero>/<prefijo>,<interfaz>".
// cidr sin '/' = /32. false si no es una IPv4 con prefijo en [0, 32] o la interfaz está vacía.
inline bool canon_protegido(const std::string& cidr, const std::string& iface, std::string& out) {
    if (iface.empty()) return false;
    const auto barra = cidr.find('/');
    const std::string ip = barra == std::string::npos ? cidr : cidr.substr(0, barra);
    int prefijo = 32;
    if (barra != std::string::npos) {
        const std::string p = cidr.substr(barra + 1);
        if (p.empty() || p.size() > 2) return false;
        for (char c : p) {
            if (c < '0' || c > '9') return false;
        }
        prefijo = std::stoi(p);
        if (prefijo > 32) return false;
    }
    in_addr a{};
    if (inet_pton(AF_INET, ip.c_str(), &a) != 1) return false;
    const uint32_t h = ntohl(a.s_addr);
    const uint32_t mascara = prefijo == 0 ? 0u : (0xFFFFFFFFu << (32 - prefijo));
    in_addr r{};
    r.s_addr = htonl(h & mascara);
    char buf[INET_ADDRSTRLEN] = {};
    if (inet_ntop(AF_INET, &r, buf, sizeof(buf)) == nullptr) return false;
    out = std::string(buf) + "/" + std::to_string(prefijo) + "," + iface;
    return true;
}

struct DiferenciaKernel {
    std::vector<std::string> sobran;  // en el kernel y no en el manifiesto (o con opciones, o ilegibles), tal cual
    std::vector<std::string> faltan;  // en el manifiesto y no en el kernel (forma canónica)
    bool vacia() const { return sobran.empty() && faltan.empty(); }
};

// esperado: (cidr, interfaz) IPv4 del vigente. kernel: una línea por entrada, "cidr,iface[ opciones]" sin contadores
// (IPSetWrapper::list_entries_opciones). O(n) con conjuntos hash.
inline DiferenciaKernel comparar_protegidos_kernel(const std::vector<std::pair<std::string, std::string>>& esperado,
                                                   const std::vector<std::string>& kernel) {
    DiferenciaKernel d;
    std::unordered_set<std::string> esp;
    std::vector<std::string> orden;
    esp.reserve(esperado.size() * 2 + 1);
    for (const auto& [cidr, iface] : esperado) {
        std::string c;
        if (!canon_protegido(cidr, iface, c)) continue;  // lo verificado ya es IPv4 válida con interfaz
        if (esp.insert(c).second) orden.push_back(c);
    }
    std::unordered_set<std::string> vistas;
    vistas.reserve(kernel.size() * 2 + 1);
    for (const auto& linea : kernel) {
        const auto sp = linea.find(' ');
        const std::string tok = sp == std::string::npos ? linea : linea.substr(0, sp);
        const bool con_opciones = sp != std::string::npos && linea.find_first_not_of(' ', sp) != std::string::npos;
        const auto coma = tok.rfind(',');
        std::string c;
        if (con_opciones || coma == std::string::npos || !canon_protegido(tok.substr(0, coma), tok.substr(coma + 1), c) ||
            esp.count(c) == 0 || !vistas.insert(c).second) {
            d.sobran.push_back(linea);
        }
    }
    for (const auto& c : orden) {
        if (vistas.count(c) == 0) d.faltan.push_back(c);
    }
    return d;
}

// Reglas de 'iptables -S' (sin las líneas -P) de INPUT y de la cadena de aRGus contra lo que escribe
// setup_base_rules. "" si cuadran; si no, el motivo.
inline std::string comprobar_reglas_protegidos(const std::vector<std::string>& input, const std::vector<std::string>& cadena,
                                               const std::string& ch, const std::string& prot, const std::string& bl) {
    const std::string salto = "-A INPUT -j " + ch;
    std::size_t saltos = 0;
    for (const auto& l : input) {
        if (l == salto) ++saltos;
    }
    if (input.empty() || input.front() != salto) return "el salto INPUT -> " + ch + " no está en la posición 1";
    if (saltos != 1) return std::to_string(saltos) + " saltos INPUT -> " + ch + " (se espera 1)";
    std::vector<std::string> esperado{"-N " + ch};
    if (!prot.empty()) {
        esperado.push_back("-A " + ch + " -m set --match-set " + prot +
                           " src,src -m comment --comment argus-protegidos -j RETURN");
    }
    if (!bl.empty()) {
        esperado.push_back("-A " + ch + " -m set --match-set " + bl + " src -m comment --comment argus-blacklist -j DROP");
    }
    if (cadena.empty()) return "la cadena " + ch + " no existe";
    if (cadena != esperado) {
        std::ostringstream o;
        o << "la cadena " << ch << " tiene " << (cadena.empty() ? 0 : cadena.size() - 1) << " reglas y no son las de aRGus"
          << " (se esperan " << esperado.size() - 1 << ": " << (prot.empty() ? "" : "protegidos RETURN, ")
          << (bl.empty() ? "" : "blacklist DROP") << ")";
        return o.str();
    }
    return "";
}

// Configuración del set de protegidos (la misma al arrancar y si el vigía tiene que recrearlo).
inline IPSetConfig config_set_protegidos(const std::string& nombre, uint32_t maxelem) {
    IPSetConfig c;
    c.name = nombre;
    c.type = IPSetType::HASH_NET_IFACE;
    c.family = IPSetFamily::INET;
    c.hashsize = 1024;
    c.maxelem = maxelem;
    c.timeout = 0;
    c.counters = true;
    c.comment = false;
    return c;
}

struct ResultadoVigia {
    bool set_divergente = false;     // K1 o K2
    bool reglas_divergentes = false; // K3
    bool set_reconciliado = false;
    bool reglas_reconciliadas = false;
    bool set_tipo_ajeno = false;     // K1: existe con otro tipo (no se toca)
    DiferenciaKernel diferencia;     // K2 antes de reconciliar
    std::string motivo_set;          // K1/K2, para el log
    std::string motivo_reglas;       // K3, para el log
    std::string error;               // si la reconciliación falló o no se comprobó
    bool divergente() const { return set_divergente || reglas_divergentes; }
};

// Una vuelta del vigía contra el kernel. set_ok=false: el set no es utilizable (tipo ajeno al arrancar) y solo se
// comprueban las reglas (sin regla de protegidos). Después de reconciliar se vuelve a leer: solo cuenta como
// reconciliado lo que se comprueba que ha quedado bien. Plantilla sobre los dos wrappers para que el test puro pueda
// darle unos falsos que digan "hecho" sin hacerlo (el agente usa IPSetWrapper e IPTablesWrapper).
template <class IPS, class IPT>
ResultadoVigia vigia_protegidos_paso(IPS& ipset, IPT& ipt, const FirewallConfig& fc,
                                            const std::string& set, bool set_ok,
                                            const std::vector<std::pair<std::string, std::string>>& esperado,
                                            uint32_t maxelem) {
    ResultadoVigia r;
    if (set_ok) {
        const auto tipo = ipset.set_type(set);
        if (tipo && *tipo != "hash:net,iface") {
            r.set_divergente = true;
            r.set_tipo_ajeno = true;
            r.motivo_set = "el set " + set + " existe con tipo " + *tipo + " (se espera hash:net,iface)";
        } else {
            bool listo = true;
            if (!tipo) {
                r.set_divergente = true;
                r.motivo_set = "el set " + set + " no existe";
                if (!ipset.create_set(config_set_protegidos(set, maxelem))) {
                    listo = false;
                    r.error = "no se pudo recrear el set " + set;
                }
            }
            if (listo) {
                r.diferencia = comparar_protegidos_kernel(esperado, ipset.list_entries_opciones(set));
                if (!r.diferencia.vacia()) r.set_divergente = true;
                if (r.set_divergente) {
                    const auto res = ipset.replace_net_iface(set, esperado, maxelem);
                    if (!res) {
                        r.error = "sustitución atómica fallida: " + res.get_error().message;
                    } else {
                        r.set_reconciliado = comparar_protegidos_kernel(esperado, ipset.list_entries_opciones(set)).vacia();
                        if (!r.set_reconciliado) r.error = "tras la sustitución el set sigue sin cuadrar";
                    }
                }
            }
        }
    }
    // Con un set ajeno (otro tipo con el mismo nombre) la regla RETURN eximiría por un contenido que nadie ha firmado
    // (medido DAY320: iptables acepta '--match-set <hash:ip> src,src' e ignora la dimensión de más). D8: lo no firmado
    // pierde la protección, así que la cadena se rehace sin RETURN. No hay riesgo: el agente nunca mete a un protegido
    // en el blacklist (barrera por IP); el RETURN es defensa en profundidad y vuelve cuando el set vuelve a estar bien.
    const bool usar_set = set_ok && !r.set_tipo_ajeno;
    FirewallConfig fc_reglas = fc;
    if (!usar_set) fc_reglas.protegidos_ipset.clear();
    const std::string prot = fc_reglas.protegidos_ipset;
    r.motivo_reglas = comprobar_reglas_protegidos(ipt.list_rules("INPUT"), ipt.list_rules(fc.blacklist_chain),
                                                  fc.blacklist_chain, prot, fc.blacklist_ipset);
    if (!r.motivo_reglas.empty()) {
        r.reglas_divergentes = true;
        const auto res = ipt.setup_base_rules(fc_reglas);
        if (!res) {
            r.error += (r.error.empty() ? "" : "; ") + std::string("setup_base_rules: ") + res.get_error().message;
        } else {
            r.reglas_reconciliadas = comprobar_reglas_protegidos(ipt.list_rules("INPUT"), ipt.list_rules(fc.blacklist_chain),
                                                                 fc.blacklist_chain, prot, fc.blacklist_ipset)
                                         .empty();
            if (!r.reglas_reconciliadas) {
                r.error += (r.error.empty() ? "" : "; ") + std::string("tras setup_base_rules las reglas siguen sin cuadrar");
            }
        }
    }
    return r;
}

}  // namespace mldefender::firewall
