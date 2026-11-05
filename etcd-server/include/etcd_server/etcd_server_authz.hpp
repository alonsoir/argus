#pragma once
// etcd-server/include/etcd_server/etcd_server_authz.hpp — [ETCD-AUTHZ-D313]
// HTTPS con mTLS y autorización por (OU, CN) del certificado de cliente (DEBT-ETCD-HA-TLS-RAFT-001, paso 4b.2).
//   - Bloque "tls" de etcd-server.json: modo (mtls | http), ca_file, cert_file, key_file, aviso_http_intervalo_s.
//     El JSON es la ley (DAY291/DAY300/DAY308): campo ausente o mal formado -> defecto validado + [CONFIG-DEFAULT].
//     Un modo ausente o mal escrito va a "mtls": una errata nunca rebaja a HTTP. "http" solo queda para el smoke enterprise
//     de emecas++ (etcd-server.smoke-enterprise.json; DEBT-VAULT-ENTERPRISE-SMOKE-VM-001) y se borra entonces.
//   - Bloque "authz": tabla de reglas {metodo, ruta, permitir}. Denegar por defecto: lo que no casa con ninguna regla
//     es 403. La ruta es una plantilla por segmentos ("/secrets/{c}"); {c} casa con UN segmento [a-z0-9-]{1,63}. Sin
//     regex en el JSON. permitir: "propio" (CN == {c}), "ou:<rol>", "cualquiera" (cualquier certificado de la CA).
//     Una regla mal formada invalida la tabla entera: se avisa de cada error y se usa la tabla por defecto (B2).
//   - Identidad (B3, DAY312): CN = instancia, OU = rol; exactamente un CN y un OU con forma de nombre, o se deniega.
// Sin estado y sin dependencias del resto del etcd-server, para probarlo suelto (tests/test_etcd_server_authz.cpp).
#include <nlohmann/json.hpp>
#include <openssl/asn1.h>
#include <openssl/crypto.h>
#include <openssl/objects.h>
#include <openssl/x509.h>
#include <iostream>
#include <string>
#include <vector>

namespace argus::etcdcfg {

// Defectos validados: iguales a etcd-server.json (el del smoke enterprise lleva modo "http" a propósito).
struct TlsConfig {
    std::string modo = "mtls";                                  // tls.modo: "mtls" | "http"
    std::string ca_file = "/etc/argus-pki/ca.crt";              // tls.ca_file: ruta absoluta
    std::string cert_file = "/etc/argus-pki/etcd-server.crt";   // tls.cert_file: ruta absoluta
    std::string key_file = "/etc/argus-pki/etcd-server.key";    // tls.key_file: ruta absoluta
    int aviso_http_intervalo_s = 60;                            // tls.aviso_http_intervalo_s: [10, 3600]
};

struct ResultadoTls {
    TlsConfig cfg;
    int defectos = 0;
};

namespace detalle_tls {
inline bool ruta_absoluta_valida(const std::string& s) {
    if (s.empty() || s.size() > 4096 || s[0] != '/') return false;
    for (unsigned char ch : s) {
        if (ch < 0x20 || ch == 0x7f) return false;
    }
    return true;
}
}  // namespace detalle_tls

inline ResultadoTls parse_tls_config(const nlohmann::json& root, std::ostream& aviso = std::cerr,
                                     std::ostream& info = std::cout) {
    ResultadoTls r;
    TlsConfig& c = r.cfg;
    const TlsConfig d{};
    static const nlohmann::json kVacio = nlohmann::json::object();
    const nlohmann::json* blk = &kVacio;
    if (root.is_object() && root.contains("tls")) {
        if (root["tls"].is_object()) {
            blk = &root["tls"];
        } else {
            aviso << "[CONFIG-DEFAULT] tls no es un objeto: se usan los defectos de todos sus campos" << std::endl;
        }
    }
    std::string o_modo = "JSON";
    if (!blk->contains("modo")) {
        aviso << "[CONFIG-DEFAULT] tls.modo ausente (\"mtls\" o \"http\"): se usa " << d.modo << std::endl;
        o_modo = "DEFECTO: ausente";
        ++r.defectos;
    } else {
        const auto& v = (*blk)["modo"];
        if (v.is_string() && (v.get<std::string>() == "mtls" || v.get<std::string>() == "http")) {
            c.modo = v.get<std::string>();
        } else {
            aviso << "[CONFIG-DEFAULT] tls.modo=" << v.dump() << " no es \"mtls\" ni \"http\": se usa " << d.modo
                  << " (una errata nunca rebaja a HTTP)" << std::endl;
            o_modo = "DEFECTO: mal formado";
            ++r.defectos;
        }
    }
    auto ruta = [&](const char* clave, const std::string& def, std::string& out) -> std::string {
        out = def;
        const std::string campo = std::string("tls.") + clave;
        if (!blk->contains(clave)) {
            aviso << "[CONFIG-DEFAULT] " << campo << " ausente (ruta absoluta): se usa " << def << std::endl;
            ++r.defectos;
            return "DEFECTO: ausente";
        }
        const auto& v = (*blk)[clave];
        if (!v.is_string() || !detalle_tls::ruta_absoluta_valida(v.get<std::string>())) {
            aviso << "[CONFIG-DEFAULT] " << campo << "=" << v.dump()
                  << " no es una ruta absoluta (empieza por /, sin caracteres de control, hasta 4096): se usa " << def
                  << std::endl;
            ++r.defectos;
            return "DEFECTO: mal formado";
        }
        out = v.get<std::string>();
        return "JSON";
    };
    const std::string o_ca = ruta("ca_file", d.ca_file, c.ca_file);
    const std::string o_cert = ruta("cert_file", d.cert_file, c.cert_file);
    const std::string o_key = ruta("key_file", d.key_file, c.key_file);
    std::string o_aviso = "JSON";
    {
        const char* clave = "aviso_http_intervalo_s";
        const char* formato = "entero en [10, 3600]";
        if (!blk->contains(clave)) {
            aviso << "[CONFIG-DEFAULT] tls." << clave << " ausente (" << formato << "): se usa "
                  << d.aviso_http_intervalo_s << std::endl;
            o_aviso = "DEFECTO: ausente";
            ++r.defectos;
        } else if (!(*blk)[clave].is_number_integer()) {
            aviso << "[CONFIG-DEFAULT] tls." << clave << "=" << (*blk)[clave].dump() << " no es entero (" << formato
                  << "): se usa " << d.aviso_http_intervalo_s << std::endl;
            o_aviso = "DEFECTO: no entero";
            ++r.defectos;
        } else {
            const long long x = (*blk)[clave].get<long long>();
            if (x < 10 || x > 3600) {
                aviso << "[CONFIG-DEFAULT] tls." << clave << "=" << x << " fuera de rango (" << formato << "): se usa "
                      << d.aviso_http_intervalo_s << std::endl;
                o_aviso = "DEFECTO: fuera de rango";
                ++r.defectos;
            } else {
                c.aviso_http_intervalo_s = static_cast<int>(x);
            }
        }
    }
    info << "[ETCD-TLS] tls.modo=" << c.modo << " (" << o_modo << ") tls.ca_file=" << c.ca_file << " (" << o_ca
         << ") tls.cert_file=" << c.cert_file << " (" << o_cert << ") tls.key_file=" << c.key_file << " (" << o_key
         << ") tls.aviso_http_intervalo_s=" << c.aviso_http_intervalo_s << " (" << o_aviso << ")" << std::endl;
    return r;
}

}  // namespace argus::etcdcfg

namespace argus::etcdauthz {

// Nombre de instancia o de rol: el mismo patrón que d312_pki.sh (minúsculas, cifras y guiones, 1-63, sin guion inicial).
inline bool nombre_valido(const std::string& s) {
    if (s.empty() || s.size() > 63) return false;
    for (size_t i = 0; i < s.size(); ++i) {
        const char ch = s[i];
        const bool ok = (ch >= 'a' && ch <= 'z') || (ch >= '0' && ch <= '9') || (ch == '-' && i > 0);
        if (!ok) return false;
    }
    return true;
}

enum class TipoPermiso { Propio, Ou, Cualquiera };

struct Permiso {
    TipoPermiso tipo = TipoPermiso::Propio;
    std::string ou;  // solo para TipoPermiso::Ou
    std::string texto() const {
        if (tipo == TipoPermiso::Propio) return "propio";
        if (tipo == TipoPermiso::Cualquiera) return "cualquiera";
        return "ou:" + ou;
    }
};

struct Regla {
    std::string metodo;              // GET | POST | PUT | DELETE
    std::string ruta;                // plantilla tal cual, para el log
    std::vector<std::string> segs;   // segmentos; "{c}" = un segmento con forma de nombre
    std::vector<Permiso> permitir;
};

struct ResultadoAuthz {
    std::vector<Regla> reglas;
    int defectos = 0;  // 1 si la tabla entera va a defecto
};

// Tabla por defecto: la misma que traen etcd-server.json y etcd-server.smoke-enterprise.json (lo comprueba el test).
inline const char* kReglasDefecto = R"([
  {"metodo": "GET",  "ruta": "/health",               "permitir": ["cualquiera"]},
  {"metodo": "POST", "ruta": "/register",             "permitir": ["cualquiera"]},
  {"metodo": "POST", "ruta": "/unregister",           "permitir": ["cualquiera"]},
  {"metodo": "POST", "ruta": "/v1/heartbeat/{c}",     "permitir": ["propio"]},
  {"metodo": "PUT",  "ruta": "/v1/config/{c}",        "permitir": ["propio"]},
  {"metodo": "GET",  "ruta": "/config/{c}",           "permitir": ["propio"]},
  {"metodo": "PUT",  "ruta": "/config/{c}",           "permitir": ["propio"]},
  {"metodo": "GET",  "ruta": "/secrets/{c}",          "permitir": ["propio"]},
  {"metodo": "GET",  "ruta": "/secrets/valid/{c}",    "permitir": ["propio", "ou:bronze-to-gold-converter"]},
  {"metodo": "POST", "ruta": "/secrets/rotate/{c}",   "permitir": ["ou:admin"]},
  {"metodo": "GET",  "ruta": "/components",           "permitir": ["ou:admin"]},
  {"metodo": "GET",  "ruta": "/validate",             "permitir": ["ou:admin"]},
  {"metodo": "GET",  "ruta": "/info",                 "permitir": ["ou:admin"]},
  {"metodo": "GET",  "ruta": "/v1/protegidos",        "permitir": ["ou:firewall-acl-agent", "ou:argus-infra"]},
  {"metodo": "PUT",  "ruta": "/v1/protegidos",        "permitir": ["ou:argus-infra"]}
])";

namespace detalle {
inline bool segmento_literal_valido(const std::string& s) {
    if (s.empty() || s.size() > 63) return false;
    for (char ch : s) {
        const bool ok = (ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') || (ch >= '0' && ch <= '9') ||
                        ch == '-' || ch == '_' || ch == '.';
        if (!ok) return false;
    }
    return true;
}

// "/a/b" -> {"a","b"}; "/" -> {}; conserva los segmentos vacíos ("/a//b" -> {"a","","b"}; "/a/" -> {"a",""}).
inline bool partir(const std::string& ruta, std::vector<std::string>& segs) {
    segs.clear();
    if (ruta.empty() || ruta[0] != '/') return false;
    if (ruta == "/") return true;
    size_t ini = 1;
    while (true) {
        const size_t fin = ruta.find('/', ini);
        if (fin == std::string::npos) {
            segs.push_back(ruta.substr(ini));
            break;
        }
        segs.push_back(ruta.substr(ini, fin - ini));
        ini = fin + 1;
    }
    return true;
}

// Una regla del JSON -> Regla. Devuelve "" si es válida, o el motivo.
inline std::string regla_de_json(const nlohmann::json& j, Regla& out) {
    if (!j.is_object()) return "no es un objeto";
    if (!j.contains("metodo") || !j["metodo"].is_string()) return "metodo ausente o no es texto";
    out.metodo = j["metodo"].get<std::string>();
    if (out.metodo != "GET" && out.metodo != "POST" && out.metodo != "PUT" && out.metodo != "DELETE")
        return "metodo '" + out.metodo + "' no es GET, POST, PUT ni DELETE";
    if (!j.contains("ruta") || !j["ruta"].is_string()) return "ruta ausente o no es texto";
    out.ruta = j["ruta"].get<std::string>();
    if (!partir(out.ruta, out.segs) || out.segs.empty()) return "ruta '" + out.ruta + "' no empieza por / o está vacía";
    int comodines = 0;
    for (const auto& s : out.segs) {
        if (s == "{c}") {
            ++comodines;
        } else if (!segmento_literal_valido(s)) {
            return "ruta '" + out.ruta + "': segmento '" + s + "' mal formado ([A-Za-z0-9._-]{1,63} o {c})";
        }
    }
    if (comodines > 1) return "ruta '" + out.ruta + "': más de un {c}";
    if (!j.contains("permitir") || !j["permitir"].is_array() || j["permitir"].empty())
        return "permitir ausente, no es lista o está vacía";
    for (const auto& p : j["permitir"]) {
        if (!p.is_string()) return "permitir: " + p.dump() + " no es texto";
        const std::string t = p.get<std::string>();
        Permiso pm;
        if (t == "propio") {
            if (comodines != 1) return "permitir 'propio' en una ruta sin {c} ('" + out.ruta + "')";
            pm.tipo = TipoPermiso::Propio;
        } else if (t == "cualquiera") {
            pm.tipo = TipoPermiso::Cualquiera;
        } else if (t.rfind("ou:", 0) == 0 && nombre_valido(t.substr(3))) {
            pm.tipo = TipoPermiso::Ou;
            pm.ou = t.substr(3);
        } else {
            return "permitir '" + t + "' no es propio, cualquiera ni ou:<rol> ([a-z0-9-]{1,63})";
        }
        out.permitir.push_back(pm);
    }
    return "";
}

inline bool parsear_tabla(const nlohmann::json& arr, std::vector<Regla>& reglas, std::vector<std::string>& errores) {
    reglas.clear();
    errores.clear();
    if (!arr.is_array() || arr.empty()) {
        errores.push_back("authz.reglas no es una lista o está vacía");
        return false;
    }
    for (size_t i = 0; i < arr.size(); ++i) {
        Regla r;
        const std::string e = regla_de_json(arr[i], r);
        if (!e.empty()) {
            errores.push_back("authz.reglas[" + std::to_string(i) + "]: " + e);
        } else {
            reglas.push_back(std::move(r));
        }
    }
    return errores.empty();
}
}  // namespace detalle

inline ResultadoAuthz parse_authz(const nlohmann::json& root, std::ostream& aviso = std::cerr,
                                  std::ostream& info = std::cout) {
    ResultadoAuthz r;
    std::string origen = "JSON";
    std::vector<std::string> errores;
    bool ok = false;
    if (!root.is_object() || !root.contains("authz")) {
        aviso << "[CONFIG-DEFAULT] authz ausente (objeto con \"reglas\": lista de {metodo, ruta, permitir}): se usa "
                 "la tabla por defecto"
              << std::endl;
        origen = "DEFECTO: ausente";
    } else if (!root["authz"].is_object() || !root["authz"].contains("reglas")) {
        aviso << "[CONFIG-DEFAULT] authz no es un objeto con \"reglas\": se usa la tabla por defecto" << std::endl;
        origen = "DEFECTO: mal formado";
    } else {
        ok = detalle::parsear_tabla(root["authz"]["reglas"], r.reglas, errores);
        if (!ok) {
            for (const auto& e : errores) aviso << "[CONFIG-DEFAULT] " << e << std::endl;
            aviso << "[CONFIG-DEFAULT] authz: " << errores.size()
                  << " regla(s) mal formada(s): se usa la tabla por defecto ENTERA (no una tabla a medias)" << std::endl;
            origen = "DEFECTO: mal formado";
        }
    }
    if (!ok) {
        std::vector<std::string> e2;
        detalle::parsear_tabla(nlohmann::json::parse(kReglasDefecto), r.reglas, e2);
        r.defectos = 1;
    }
    for (size_t i = 0; i < r.reglas.size(); ++i) {
        const auto& g = r.reglas[i];
        std::string p;
        // Sin el temporal (const char* + std::string): con GCC 12 + LTO + -O3 da un falso -Wstringop-overflow
        // (medido DAY313 en el defender y reproducido en bookworm, etcd_server_authz.hpp:312)
        for (const auto& x : g.permitir) {
            if (!p.empty()) p += ',';
            p += x.texto();
        }
        info << "[ETCD-AUTHZ] regla " << (i + 1) << "/" << r.reglas.size() << ": " << g.metodo << " " << g.ruta
             << " permitir=" << p << " (" << origen << ")" << std::endl;
    }
    return r;
}

struct Identidad {
    bool valida = false;
    std::string cn, ou;
    std::string motivo;  // por qué no es válida
};

// Exactamente un CN y un OU en el sujeto, con forma de nombre; si no, identidad no válida (se deniega todo).
inline Identidad identidad_de_certificado(X509* cert) {
    Identidad id;
    if (cert == nullptr) {
        id.motivo = "sin certificado de cliente";
        return id;
    }
    X509_NAME* n = X509_get_subject_name(cert);
    if (n == nullptr) {
        id.motivo = "certificado sin sujeto";
        return id;
    }
    auto uno = [&](int nid, const char* nom, std::string& out) -> bool {
        const int idx = X509_NAME_get_index_by_NID(n, nid, -1);
        if (idx < 0) {
            id.motivo = std::string("certificado sin ") + nom;
            return false;
        }
        if (X509_NAME_get_index_by_NID(n, nid, idx) >= 0) {
            id.motivo = std::string("certificado con más de un ") + nom;
            return false;
        }
        ASN1_STRING* d = X509_NAME_ENTRY_get_data(X509_NAME_get_entry(n, idx));
        unsigned char* u = nullptr;
        const int len = ASN1_STRING_to_UTF8(&u, d);
        if (len < 0 || u == nullptr) {
            id.motivo = std::string(nom) + " ilegible";
            return false;
        }
        out.assign(reinterpret_cast<const char*>(u), static_cast<size_t>(len));
        OPENSSL_free(u);
        if (!nombre_valido(out)) {
            out.clear();
            id.motivo = std::string(nom) + " mal formado ([a-z0-9-]{1,63})";
            return false;
        }
        return true;
    };
    if (!uno(NID_commonName, "CN", id.cn) || !uno(NID_organizationalUnitName, "OU", id.ou)) return id;
    id.valida = true;
    return id;
}

struct Decision {
    bool permitido = false;
    std::string motivo;
};

// Denegar por defecto. Se permite si ALGUNA regla que casa (método y plantilla) permite a esta identidad.
inline Decision decidir(const std::vector<Regla>& reglas, const std::string& metodo_in, const std::string& ruta,
                        const Identidad& id) {
    Decision d;
    if (!id.valida) {
        d.motivo = "identidad no válida: " + id.motivo;
        return d;
    }
    const std::string metodo = (metodo_in == "HEAD") ? "GET" : metodo_in;
    std::vector<std::string> segs;
    if (!detalle::partir(ruta, segs)) {
        d.motivo = "ruta no empieza por /";
        return d;
    }
    bool alguna_casa = false;
    for (const auto& r : reglas) {
        if (r.metodo != metodo || r.segs.size() != segs.size()) continue;
        std::string c;
        bool casa = true;
        for (size_t i = 0; i < segs.size() && casa; ++i) {
            if (r.segs[i] == "{c}") {
                if (nombre_valido(segs[i])) {
                    c = segs[i];
                } else {
                    casa = false;
                }
            } else {
                casa = (r.segs[i] == segs[i]);
            }
        }
        if (!casa) continue;
        alguna_casa = true;
        for (const auto& p : r.permitir) {
            const bool ok = (p.tipo == TipoPermiso::Cualquiera) || (p.tipo == TipoPermiso::Ou && id.ou == p.ou) ||
                            (p.tipo == TipoPermiso::Propio && !c.empty() && id.cn == c);
            if (ok) {
                d.permitido = true;
                d.motivo = "regla " + r.metodo + " " + r.ruta + " permitir=" + p.texto();
                return d;
            }
        }
    }
    d.motivo = alguna_casa ? "ninguna regla que casa permite a esta identidad" : "ninguna regla casa (denegar por defecto)";
    return d;
}

// Para el log: sin caracteres de control (la ruta llega decodificada y la escribe quien conecta) y acotada.
inline std::string para_log(const std::string& s, size_t max = 256) {
    std::string o;
    for (unsigned char ch : s) {
        if (o.size() >= max) {
            o += "...";
            break;
        }
        o += (ch < 0x20 || ch == 0x7f) ? '?' : static_cast<char>(ch);
    }
    return o;
}

}  // namespace argus::etcdauthz
