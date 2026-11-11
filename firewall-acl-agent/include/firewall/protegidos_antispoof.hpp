// protegidos_antispoof.hpp -- [PROTEGIDOS-ANTISPOOF-D320] ADR-060 D8, paso 8e.4b: antispoofing en raw PREROUTING
// generado desde el manifiesto vigente (diseño fino: ADR-060 sección 7, H-B..H-G, I-A..I-G).
//
// Cadena (medida DAY320 en el defender con scripts/etcd_ha/d320_medir_antispoof.sh, 19/19). Coste por paquete
// constante: el tráfico no protegido sale en la regla 2 con un solo lookup; como mucho cuatro:
//   1 -i lo                                               -> RETURN
//   2 origen NO en <set_redes>                            -> RETURN
//   3 (origen, interfaz de entrada) NO en <protegidos>    -> goto <cadena>_IF   (spoofing por interfaz)
//   4 origen NO en <set_ips_mac>                          -> RETURN
//   5 (origen, MAC de origen) NO en <set_mac>             -> goto <cadena>_MAC  (spoofing por MAC)
//   6                                                     -> RETURN
//   <cadena>_IF / _MAC: LOG con límite (evidencia, al journal) y una regla de cuenta que descarta (DROP) solo con la
//   mitigación real (modo descarta); si no, solo cuenta. goto (no -j): al acabar la cadena de spoofing el paquete sale a
//   PREROUTING, así cuenta una vez en sombra y con DROP (medido en la v1 de la medida).
// Sin hash:ip,mac en el kernel, las reglas 4-5 no se generan (se avisa: sin comprobación de MAC).
// <protegidos> es el set hash:net,iface de siempre (la exención del filtro): no se duplica.
// set_redes solo lleva las redes con al menos una entrada cuya interfaz casa con la ruta del kernel (H-D): una red
// cuya interfaz no casa nunca cuenta ni se descarta (sería el DoS autoinfligido) y es alarma [PROTEGIDOS-RUTA].
// IPv6: solo la barrera de usuario (D-I, DEBT-FW-IPV6-SETS-001).
#pragma once

#include "firewall/ipset_wrapper.hpp"
#include "firewall/iptables_wrapper.hpp"
#include "firewall/protegidos_vigia.hpp"

#include <arpa/inet.h>

#include <cstdint>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

namespace mldefender::firewall {

struct EntradaAntispoof {
    std::string cidr;   // IPv4 con prefijo, tal como viene en el manifiesto verificado
    std::string iface;  // interfaz de entrada esperada
    std::string mac;    // "" o xx:xx:xx:xx:xx:xx
};

struct RepartoAntispoof {
    std::vector<std::string> redes;    // set_redes (hash:net), forma canónica red/prefijo, sin repetir
    std::vector<std::string> ips_mac;  // set_ips_mac (hash:ip)
    std::vector<std::string> mac;      // set_mac (hash:ip,mac): "ip,mac"
    std::vector<std::string> sin_ruta; // "cidr por <iface> (la ruta va por <dev>)": redes que quedan fuera (H-D)
};

// Red canónica (sin el ",iface") de un cidr IPv4; "" si no es válido.
inline std::string red_canonica(const std::string& cidr) {
    std::string c;
    if (!canon_protegido(cidr, "x", c)) return "";
    return c.substr(0, c.size() - 2);
}

// ruta(red_canonica) -> interfaz por la que sale el kernel hacia esa red ("" si no se sabe). Una red entra en
// set_redes si al menos una de sus entradas casa con la ruta (un host con varias interfaces legítimas lleva una
// entrada por interfaz: con que una case, las otras son caminos alternativos). Las MAC solo en las /32.
template <class Ruta>
RepartoAntispoof repartir_antispoof(const std::vector<EntradaAntispoof>& entradas, Ruta&& ruta) {
    RepartoAntispoof r;
    std::map<std::string, std::vector<const EntradaAntispoof*>> por_red;
    std::vector<std::string> orden;
    for (const auto& e : entradas) {
        const std::string red = red_canonica(e.cidr);
        if (red.empty()) continue;
        if (por_red.find(red) == por_red.end()) orden.push_back(red);
        por_red[red].push_back(&e);
    }
    std::set<std::string> vistos_ip, vistos_mac;
    for (const auto& red : orden) {
        const std::string dev = ruta(red.substr(0, red.find('/')));
        bool casa = false;
        for (const auto* e : por_red[red]) casa = casa || (!dev.empty() && e->iface == dev);
        if (!casa) {
            for (const auto* e : por_red[red]) {
                r.sin_ruta.push_back(red + " por " + e->iface + " (la ruta va por " + (dev.empty() ? "?" : dev) + ")");
            }
            continue;
        }
        r.redes.push_back(red);
        if (red.size() < 3 || red.compare(red.size() - 3, 3, "/32") != 0) continue;
        const std::string ip = red.substr(0, red.size() - 3);
        for (const auto* e : por_red[red]) {
            if (e->mac.empty()) continue;
            if (vistos_ip.insert(ip).second) r.ips_mac.push_back(ip);
            if (vistos_mac.insert(ip + "," + e->mac).second) r.mac.push_back(ip + "," + e->mac);
        }
    }
    return r;
}

struct NombresAntispoof {
    std::string cadena, set_redes, set_protegidos, set_ips_mac, set_mac;
    int log_por_minuto = 5, log_rafaga = 5;
    bool con_mac = true;  // el kernel tiene hash:ip,mac
};

// Reglas exactamente como las imprime 'iptables -S' (medido DAY320: con --limit-burst 5, el valor por defecto de
// iptables, -S lo omite). La primera línea de cada cadena es "-N <cadena>".
inline std::vector<std::string> reglas_esperadas_principal(const NombresAntispoof& n) {
    std::vector<std::string> v{"-N " + n.cadena, "-A " + n.cadena + " -i lo -j RETURN",
                               "-A " + n.cadena + " -m set ! --match-set " + n.set_redes + " src -j RETURN",
                               "-A " + n.cadena + " -m set ! --match-set " + n.set_protegidos + " src,src -g " + n.cadena + "_IF"};
    if (n.con_mac) {
        v.push_back("-A " + n.cadena + " -m set ! --match-set " + n.set_ips_mac + " src -j RETURN");
        v.push_back("-A " + n.cadena + " -m set ! --match-set " + n.set_mac + " src,src -g " + n.cadena + "_MAC");
    }
    v.push_back("-A " + n.cadena + " -j RETURN");
    return v;
}

inline std::vector<std::string> reglas_esperadas_spoof(const NombresAntispoof& n, const std::string& sufijo,
                                                       const std::string& prefijo_log, bool descarta) {
    const std::string ch = n.cadena + sufijo;
    const std::string limite = "-m limit --limit " + std::to_string(n.log_por_minuto) + "/min" +
                               (n.log_rafaga == 5 ? std::string() : " --limit-burst " + std::to_string(n.log_rafaga));
    std::string comentario = "argus-spoof-if";
    if (sufijo == "_MAC") comentario = "argus-spoof-mac";
    return {"-N " + ch, "-A " + ch + " " + limite + " -j LOG --log-prefix \"" + prefijo_log + "\"",
            "-A " + ch + " -m comment --comment " + comentario + (descarta ? " -j DROP" : "")};
}

// Texto para 'iptables-restore --noflush' (tabla raw): declara las tres cadenas (se vacían y se rellenan de golpe).
inline std::string texto_restore_antispoof(const NombresAntispoof& n, bool descarta) {
    std::ostringstream o;
    o << "*raw\n:" << n.cadena << " - [0:0]\n:" << n.cadena << "_IF - [0:0]\n:" << n.cadena << "_MAC - [0:0]\n";
    auto cuerpo = [&o](const std::vector<std::string>& v) {
        for (std::size_t i = 1; i < v.size(); ++i) o << v[i] << "\n";
    };
    cuerpo(reglas_esperadas_principal(n));
    // la regla LOG en restore lleva siempre --limit-burst (es igual de válida y explícita)
    const std::string limite = "-m limit --limit " + std::to_string(n.log_por_minuto) + "/min --limit-burst " +
                               std::to_string(n.log_rafaga);
    o << "-A " << n.cadena << "_IF " << limite << " -j LOG --log-prefix \"ARGUS-SPOOF-IF \"\n";
    o << "-A " << n.cadena << "_IF -m comment --comment argus-spoof-if" << (descarta ? " -j DROP" : "") << "\n";
    o << "-A " << n.cadena << "_MAC " << limite << " -j LOG --log-prefix \"ARGUS-SPOOF-MAC \"\n";
    o << "-A " << n.cadena << "_MAC -m comment --comment argus-spoof-mac" << (descarta ? " -j DROP" : "") << "\n";
    o << "COMMIT\n";
    return o.str();
}

// "" si la tabla raw está como se generó; si no, el motivo.
inline std::string comprobar_reglas_antispoof(const std::vector<std::string>& prerouting,
                                              const std::vector<std::string>& principal,
                                              const std::vector<std::string>& spoof_if,
                                              const std::vector<std::string>& spoof_mac, const NombresAntispoof& n,
                                              bool descarta) {
    const std::string salto = "-A PREROUTING -j " + n.cadena;
    std::size_t saltos = 0;
    for (const auto& l : prerouting) {
        if (l == salto) ++saltos;
    }
    if (prerouting.empty() || prerouting.front() != salto) return "el salto raw PREROUTING -> " + n.cadena + " no está en la posición 1";
    if (saltos != 1) return std::to_string(saltos) + " saltos raw PREROUTING -> " + n.cadena + " (se espera 1)";
    if (principal != reglas_esperadas_principal(n)) return "la cadena " + n.cadena + " no es la generada";
    if (spoof_if != reglas_esperadas_spoof(n, "_IF", "ARGUS-SPOOF-IF ", descarta)) {
        return "la cadena " + n.cadena + "_IF no es la generada (modo " + (descarta ? "descarta" : "cuenta") + ")";
    }
    if (spoof_mac != reglas_esperadas_spoof(n, "_MAC", "ARGUS-SPOOF-MAC ", descarta)) {
        return "la cadena " + n.cadena + "_MAC no es la generada (modo " + (descarta ? "descarta" : "cuenta") + ")";
    }
    return "";
}

// Contenido de un set (líneas de list_entries_opciones) frente a lo esperado. Para hash:net las dos formas se normalizan
// (el kernel omite /32). Una línea con opciones (nomatch...) nunca casa: en hash:net no es un CIDR válido y en los demás
// el texto difiere (medido DAY320 con mutaciones: una comprobación aparte de opciones era redundante y se quitó).
inline bool set_cuadra(const std::vector<std::string>& kernel, const std::vector<std::string>& esperado, bool es_red) {
    auto norma = [es_red](const std::string& x) {
        if (!es_red) return x;
        const std::string c = red_canonica(x);
        return c.empty() ? std::string("?") + x : c;
    };
    std::set<std::string> a, b;
    for (const auto& x : kernel) {
        if (!a.insert(norma(x)).second) return false;
    }
    for (const auto& x : esperado) b.insert(norma(x));
    // hash:ip,mac: el kernel imprime la MAC en mayúsculas (medido DAY320)
    if (!es_red) {
        std::set<std::string> a2, b2;
        auto mayus = [](std::string s) {
            for (auto& c : s) c = static_cast<char>(std::toupper(static_cast<unsigned char>(c)));
            return s;
        };
        for (const auto& x : a) a2.insert(mayus(x));
        for (const auto& x : b) b2.insert(mayus(x));
        return a2 == b2;
    }
    return a == b;
}

inline IPSetConfig config_set_antispoof(const std::string& nombre, IPSetType tipo, uint32_t maxelem) {
    IPSetConfig c;
    c.name = nombre;
    c.type = tipo;
    c.family = IPSetFamily::INET;
    c.hashsize = 1024;
    c.maxelem = maxelem;
    c.timeout = 0;
    c.counters = true;
    c.comment = false;
    return c;
}

struct ResultadoAntispoof {
    bool divergente = false, reconciliado = false;
    std::vector<std::string> motivos;  // qué no cuadraba
    std::string error;
};

// Lleva al kernel (o comprueba y reconcilia) los tres sets y las tres cadenas. solo_comprobar=false: aplica sin
// mirar (arranque o manifiesto nuevo); true: vigía (aplica solo si algo no cuadra y luego vuelve a leer).
// El set <protegidos> lo lleva el vigía de 8e.4a.
template <class IPS, class IPT>
ResultadoAntispoof antispoof_paso(IPS& ipset, IPT& ipt, const NombresAntispoof& n, const RepartoAntispoof& rep,
                                  bool descarta, uint32_t maxelem, bool solo_comprobar) {
    ResultadoAntispoof r;
    struct S { const std::string* nombre; IPSetType tipo; const std::vector<std::string>* esp; bool es_red; };
    std::vector<S> sets{{&n.set_redes, IPSetType::HASH_NET, &rep.redes, true}};
    if (n.con_mac) {
        sets.push_back({&n.set_ips_mac, IPSetType::HASH_IP, &rep.ips_mac, false});
        sets.push_back({&n.set_mac, IPSetType::HASH_IP_MAC, &rep.mac, false});
    }
    static const char* kTipos[] = {"hash:ip", "hash:net", "hash:ip,port", "hash:net,iface", "hash:ip,mac"};
    auto tipo_txt = [](IPSetType t) { return std::string(kTipos[static_cast<int>(t)]); };
    for (const auto& s : sets) {
        const auto tipo = ipset.set_type(*s.nombre);
        if (tipo && *tipo != tipo_txt(s.tipo)) {
            r.divergente = true;
            r.motivos.push_back("el set " + *s.nombre + " existe con tipo " + *tipo + " (se espera " + tipo_txt(s.tipo) + ")");
            r.error += (r.error.empty() ? "" : "; ") + std::string("set ajeno ") + *s.nombre + " (no se destruye)";
            continue;
        }
        bool aplicar = !solo_comprobar;
        if (!tipo) {
            r.divergente = r.divergente || solo_comprobar;
            if (solo_comprobar) r.motivos.push_back("el set " + *s.nombre + " no existe");
            if (!ipset.create_set(config_set_antispoof(*s.nombre, s.tipo, maxelem))) {
                r.error += (r.error.empty() ? "" : "; ") + std::string("no se pudo crear ") + *s.nombre;
                continue;
            }
            aplicar = true;
        } else if (solo_comprobar && !set_cuadra(ipset.list_entries_opciones(*s.nombre), *s.esp, s.es_red)) {
            r.divergente = true;
            r.motivos.push_back("el set " + *s.nombre + " no tiene lo que dice el manifiesto");
            aplicar = true;
        }
        if (aplicar) {
            const auto res = ipset.replace_set(*s.nombre, s.tipo, *s.esp, maxelem);
            if (!res) r.error += (r.error.empty() ? "" : "; ") + *s.nombre + ": " + res.get_error().message;
        }
    }
    if (!r.error.empty() && r.error.find("set ajeno") != std::string::npos) {
        return r;  // con un set ajeno no se instala la cadena que lo usaría
    }
    auto leer = [&]() {
        return comprobar_reglas_antispoof(ipt.list_rules("PREROUTING", IPTablesTable::RAW),
                                          ipt.list_rules(n.cadena, IPTablesTable::RAW),
                                          ipt.list_rules(n.cadena + "_IF", IPTablesTable::RAW),
                                          ipt.list_rules(n.cadena + "_MAC", IPTablesTable::RAW), n, descarta);
    };
    const std::string motivo = solo_comprobar ? leer() : std::string("aplicación");
    if (!motivo.empty()) {
        if (solo_comprobar) {
            r.divergente = true;
            r.motivos.push_back(motivo);
        }
        const auto a = ipt.restaurar_sin_vaciar(texto_restore_antispoof(n, descarta));
        if (!a) {
            r.error += (r.error.empty() ? "" : "; ") + std::string("iptables-restore: ") + a.get_error().message;
        } else {
            const auto b = ipt.salto_en_primera(IPTablesTable::RAW, "PREROUTING", n.cadena);
            if (!b) r.error += (r.error.empty() ? "" : "; ") + std::string("salto: ") + b.get_error().message;
        }
    }
    // relectura: solo cuenta lo que se comprueba
    bool bien = leer().empty();
    for (const auto& s : sets) bien = bien && set_cuadra(ipset.list_entries_opciones(*s.nombre), *s.esp, s.es_red);
    if (!bien && r.error.empty()) r.error = "tras aplicar, el kernel sigue sin cuadrar";
    r.reconciliado = bien && r.error.empty();
    return r;
}

}  // namespace mldefender::firewall
