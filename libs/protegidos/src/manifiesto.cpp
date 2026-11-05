// libs/protegidos/src/manifiesto.cpp (antes firewall-acl-agent/src/core/protegidos_manifiesto.cpp) — [PROTEGIDOS-MANIFIESTO-D318] ADR-060, paso 8e.1a. Ver la cabecera.
#include "protegidos/manifiesto.hpp"

#include <json/json.h>
#include <sodium.h>

#include <algorithm>
#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <set>
#include <sstream>
#include <sys/stat.h>
#include <unistd.h>

namespace argus::protegidos {

namespace {

const char* const kCategoriasManifiesto[] = {"infraestructura", "intranet", "dmz", "externos_criticos"};

CategoriaProtegida categoria_por_nombre(const std::string& n) {
    if (n == "infraestructura") return CategoriaProtegida::INFRAESTRUCTURA;
    if (n == "intranet") return CategoriaProtegida::INTRANET;
    if (n == "dmz") return CategoriaProtegida::DMZ;
    if (n == "externos_criticos") return CategoriaProtegida::EXTERNOS_CRITICOS;
    return CategoriaProtegida::NINGUNA;
}

bool es_hex_min(const std::string& s, std::size_t n) {
    if (s.size() != n) return false;
    return std::all_of(s.begin(), s.end(), [](char c) { return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'); });
}

bool hex_a_32(const std::string& hex, std::array<unsigned char, 32>& out) {
    if (!es_hex_min(hex, 64)) return false;
    std::size_t n = 0;
    return sodium_hex2bin(out.data(), out.size(), hex.data(), hex.size(), nullptr, &n, nullptr) == 0 && n == 32;
}

// [a-z0-9-]{1,64}
bool es_id(const std::string& s) {
    if (s.empty() || s.size() > 64) return false;
    return std::all_of(s.begin(), s.end(), [](char c) { return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-'; });
}

// [A-Za-z0-9._-]{1,15} (IFNAMSIZ - 1)
bool es_interfaz(const std::string& s) {
    if (s.empty() || s.size() > 15) return false;
    return std::all_of(s.begin(), s.end(), [](char c) {
        return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '.' || c == '_' || c == '-';
    });
}

// "" o xx:xx:xx:xx:xx:xx en minúsculas
bool es_mac(const std::string& s) {
    if (s.empty()) return true;
    if (s.size() != 17) return false;
    for (std::size_t i = 0; i < s.size(); ++i) {
        const char c = s[i];
        if (i % 3 == 2) {
            if (c != ':') return false;
        } else if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) {
            return false;
        }
    }
    return true;
}

// Texto imprimible ASCII o UTF-8 sin caracteres de control, de 1 a max bytes.
bool es_texto(const std::string& s, std::size_t max) {
    if (s.empty() || s.size() > max) return false;
    return std::none_of(s.begin(), s.end(), [](char c) {
        const auto u = static_cast<unsigned char>(c);
        return u < 0x20 || u == 0x7f;
    });
}

// AAAA-MM-DDTHH:MM:SSZ
bool es_fecha_utc(const std::string& s) {
    static const char* const forma = "dddd-dd-ddTdd:dd:ddZ";
    if (s.size() != std::strlen(forma)) return false;
    for (std::size_t i = 0; i < s.size(); ++i) {
        if (forma[i] == 'd') {
            if (s[i] < '0' || s[i] > '9') return false;
        } else if (s[i] != forma[i]) {
            return false;
        }
    }
    return true;
}

bool claves_exactas(const Json::Value& o, std::initializer_list<const char*> claves, std::string& sobra) {
    if (!o.isObject()) return false;
    std::set<std::string> esperadas(claves.begin(), claves.end());
    for (const auto& k : o.getMemberNames()) {
        if (esperadas.count(k) == 0) {
            sobra = "campo desconocido '" + detalle_protegidos::saneado(k) + "'";
            return false;
        }
    }
    for (const auto* k : claves) {
        if (!o.isMember(k)) {
            sobra = std::string("falta el campo '") + k + "'";
            return false;
        }
    }
    return true;
}

bool entero(const Json::Value& v) { return v.type() == Json::intValue || v.type() == Json::uintValue; }

bool leer_json_estricto(const std::string& texto, Json::Value& out, std::string& error) {
    Json::CharReaderBuilder b;
    Json::CharReaderBuilder::strictMode(&b.settings_);
    std::unique_ptr<Json::CharReader> r(b.newCharReader());
    std::string errs;
    if (!r->parse(texto.data(), texto.data() + texto.size(), &out, &errs)) {
        error = "JSON inválido: " + detalle_protegidos::saneado(errs);
        return false;
    }
    return true;
}

bool base64_a_bytes(const std::string& b64, std::size_t max, std::string& out) {
    if (b64.empty() || b64.size() > (max / 3 + 1) * 4) return false;
    std::string buf(b64.size(), '\0');
    std::size_t n = 0;
    const char* fin = nullptr;
    if (sodium_base642bin(reinterpret_cast<unsigned char*>(buf.data()), buf.size(), b64.data(), b64.size(), nullptr, &n,
                          &fin, sodium_base64_VARIANT_ORIGINAL) != 0) {
        return false;
    }
    if (fin != b64.data() + b64.size() || n > max) return false;
    buf.resize(n);
    out.swap(buf);
    return true;
}

std::string sha256_hex(const std::string& datos) {
    unsigned char h[crypto_hash_sha256_BYTES];
    crypto_hash_sha256(h, reinterpret_cast<const unsigned char*>(datos.data()), datos.size());
    char hex[crypto_hash_sha256_BYTES * 2 + 1];
    sodium_bin2hex(hex, sizeof hex, h, sizeof h);
    return hex;
}

ResultadoVerificacion rechazo(MotivoRechazo m, std::string detalle) {
    ResultadoVerificacion r;
    r.ok = false;
    r.motivo = m;
    r.detalle = std::move(detalle);
    return r;
}

struct ErrorEntrada {
    MotivoRechazo motivo;
    std::string detalle;
};

// Valida una lista de entradas (comun o una planta). Añade a 'salida' si no es null.
std::optional<ErrorEntrada> validar_entradas(const Json::Value& lista, const std::string& donde, const std::array<int, 5>& lim,
                                             bool es_comun, std::vector<EntradaProtegida>* salida, std::size_t& total) {
    if (!lista.isArray()) return ErrorEntrada{MotivoRechazo::FORMATO, donde + " no es una lista"};
    for (Json::ArrayIndex i = 0; i < lista.size(); ++i) {
        const Json::Value& e = lista[i];
        const std::string w = donde + "[" + std::to_string(i) + "]";
        std::string sobra;
        if (!claves_exactas(e, {"categoria", "cidr", "interfaz", "mac", "motivo"}, sobra)) {
            return ErrorEntrada{MotivoRechazo::FORMATO, w + ": " + (sobra.empty() ? "no es un objeto" : sobra)};
        }
        for (const char* k : {"categoria", "cidr", "interfaz", "mac", "motivo"}) {
            if (!e[k].isString()) return ErrorEntrada{MotivoRechazo::FORMATO, w + "." + k + " no es una cadena"};
        }
        if (++total > kProtegidosMaxEntradas) {
            return ErrorEntrada{MotivoRechazo::FORMATO, "más de " + std::to_string(kProtegidosMaxEntradas) + " entradas"};
        }
        const std::string cat_n = e["categoria"].asString();
        const CategoriaProtegida cat = categoria_por_nombre(cat_n);
        if (cat == CategoriaProtegida::NINGUNA) {
            return ErrorEntrada{MotivoRechazo::FORMATO, w + ".categoria '" + detalle_protegidos::saneado(cat_n) + "' desconocida"};
        }
        const std::string cidr = e["cidr"].asString();
        RangoProtegido r;
        if (cidr.find('/') == std::string::npos || !parsear_rango(cidr, cat, r)) {
            return ErrorEntrada{MotivoRechazo::FORMATO, w + ".cidr '" + detalle_protegidos::saneado(cidr) +
                                                            "' mal formado (IPv4 o IPv6 con prefijo explícito)"};
        }
        {   // sin bits de host: lo firmado es exactamente lo que se aplica
            bool v6 = false;
            std::array<uint8_t, 16> ip{};
            detalle_protegidos::a_bytes(cidr.substr(0, cidr.find('/')), v6, ip);
            if (ip != r.red) {
                return ErrorEntrada{MotivoRechazo::FORMATO, w + ".cidr '" + detalle_protegidos::saneado(cidr) +
                                                                "' tiene bits de host (escriba la red)"};
            }
        }
        const int idx = static_cast<int>(cat);
        if (r.v6 ? (r.prefijo != 128) : (r.prefijo < lim[static_cast<std::size_t>(idx)])) {
            return ErrorEntrada{MotivoRechazo::LIMITE,
                                w + ": " + detalle_protegidos::saneado(cidr) + " más amplio que el límite de " + cat_n + " (" +
                                    (r.v6 ? std::string("IPv6: solo /128") : "/" + std::to_string(lim[static_cast<std::size_t>(idx)])) + ")"};
        }
        const std::string iface = e["interfaz"].asString();
        if (!es_interfaz(iface)) {
            return ErrorEntrada{MotivoRechazo::FORMATO, w + ".interfaz '" + detalle_protegidos::saneado(iface) +
                                                            "' mal formada ([A-Za-z0-9._-], de 1 a 15)"};
        }
        const std::string mac = e["mac"].asString();
        if (!es_mac(mac)) {
            return ErrorEntrada{MotivoRechazo::FORMATO, w + ".mac '" + detalle_protegidos::saneado(mac) +
                                                            "' mal formada (vacía o xx:xx:xx:xx:xx:xx en minúsculas)"};
        }
        const std::string motivo = e["motivo"].asString();
        if (!es_texto(motivo, 200)) {
            return ErrorEntrada{MotivoRechazo::FORMATO, w + ".motivo vacío, de más de 200 bytes o con caracteres de control"};
        }
        if (salida) {
            EntradaProtegida en;
            en.rango = r;
            en.interfaz = iface;
            en.mac = mac;
            en.motivo = motivo;
            en.comun = es_comun;
            salida->push_back(std::move(en));
        }
    }
    return std::nullopt;
}

// Dentro de lo que aplica un firewall (comun + su planta): ni la misma red dos veces en la misma interfaz, ni la misma
// red en dos categorías.
std::optional<std::string> repetidas(const std::vector<EntradaProtegida>& es) {
    for (std::size_t i = 0; i < es.size(); ++i) {
        for (std::size_t j = i + 1; j < es.size(); ++j) {
            const auto& a = es[i].rango;
            const auto& b = es[j].rango;
            if (a.v6 == b.v6 && a.prefijo == b.prefijo && a.red == b.red) {
                if (a.cat != b.cat) return "la red " + a.texto + " aparece en dos categorías";
                if (es[i].interfaz == es[j].interfaz) return "la red " + a.texto + " aparece dos veces en " + es[i].interfaz;
            }
        }
    }
    return std::nullopt;
}

}  // namespace

const char* nombre_motivo(MotivoRechazo m) {
    switch (m) {
        case MotivoRechazo::FORMATO: return "formato";
        case MotivoRechazo::FIRMA: return "firma";
        case MotivoRechazo::VERSION: return "version";
        case MotivoRechazo::HOSPITAL: return "hospital";
        case MotivoRechazo::PLANTA: return "planta";
        case MotivoRechazo::LIMITE: return "limite";
    }
    return "formato";
}

bool claves_protegidos_desde_hex(const std::string& actual_hex, const std::string& siguiente_hex, ClavesProtegidos& out,
                                 std::string& error) {
    ClavesProtegidos c;
    if (!hex_a_32(actual_hex, c.actual)) {
        error = "clave actual mal formada (64 caracteres hex en minúsculas)";
        return false;
    }
    if (!siguiente_hex.empty()) {
        if (!hex_a_32(siguiente_hex, c.siguiente)) {
            error = "clave siguiente mal formada (vacía o 64 caracteres hex en minúsculas)";
            return false;
        }
        if (c.siguiente == c.actual) {
            error = "la clave siguiente es igual a la actual";
            return false;
        }
        c.hay_siguiente = true;
    }
    out = c;
    return true;
}

std::string huella_clave_protegidos(const std::array<unsigned char, 32>& k) {
    return sha256_hex(std::string(reinterpret_cast<const char*>(k.data()), k.size())).substr(0, 16);
}

std::array<std::size_t, 5> ManifiestoVerificado::por_categoria() const {
    std::array<std::size_t, 5> n{};
    for (const auto& e : entradas) ++n[static_cast<std::size_t>(e.rango.cat)];
    return n;
}

RangosProtegidos ManifiestoVerificado::rangos() const {
    RangosProtegidos out;
    for (const auto& e : entradas) out.rangos.push_back(e.rango);
    // categoria_de devuelve la primera coincidencia: infraestructura delante y, después, lo más específico.
    std::stable_sort(out.rangos.begin(), out.rangos.end(), [](const RangoProtegido& a, const RangoProtegido& b) {
        const bool ia = a.cat == CategoriaProtegida::INFRAESTRUCTURA;
        const bool ib = b.cat == CategoriaProtegida::INFRAESTRUCTURA;
        if (ia != ib) return ia;
        return a.prefijo > b.prefijo;
    });
    return out;
}

namespace {
// [PROTEGIDOS-MANIFIESTO-D318] planta == nullptr: documento entero (etcd-server, 8e.3b); si no, para ESE firewall
ResultadoVerificacion verificar(const std::string& sobre, const ClavesProtegidos& claves, const std::string& hospital_id,
                                const std::string* planta_p, uint64_t version_aplicada) {
    if (sodium_init() < 0) return rechazo(MotivoRechazo::FIRMA, "libsodium no inicializa");
    if (sobre.size() > kProtegidosMaxSobreBytes) {
        return rechazo(MotivoRechazo::FORMATO, "sobre de " + std::to_string(sobre.size()) + " bytes (máximo " +
                                                   std::to_string(kProtegidosMaxSobreBytes) + ")");
    }
    // 1. Sobre
    Json::Value s;
    std::string err;
    if (!leer_json_estricto(sobre, s, err)) return rechazo(MotivoRechazo::FORMATO, "sobre: " + err);
    std::string sobra;
    if (!claves_exactas(s, {"formato", "carga_b64", "firma"}, sobra)) {
        return rechazo(MotivoRechazo::FORMATO, "sobre: " + (sobra.empty() ? "no es un objeto" : sobra));
    }
    if (!s["formato"].isString() || s["formato"].asString() != kProtegidosFormato) {
        return rechazo(MotivoRechazo::FORMATO, std::string("sobre: formato distinto de ") + kProtegidosFormato);
    }
    if (!s["carga_b64"].isString() || !s["firma"].isString()) {
        return rechazo(MotivoRechazo::FORMATO, "sobre: carga_b64 y firma tienen que ser cadenas");
    }
    std::string carga;
    if (!base64_a_bytes(s["carga_b64"].asString(), kProtegidosMaxCargaBytes, carga)) {
        return rechazo(MotivoRechazo::FORMATO, "sobre: carga_b64 no es base64 válido o pasa de " +
                                                   std::to_string(kProtegidosMaxCargaBytes) + " bytes");
    }
    // 2. Firma ("vault:vN:<base64 de 64 bytes>"), sobre los bytes exactos, ANTES de interpretar la carga
    const std::string firma = s["firma"].asString();
    std::string firma_b;
    {
        const std::string pre = "vault:v";
        const std::size_t dos = firma.find(':', pre.size());
        const std::string num = (firma.rfind(pre, 0) == 0 && dos != std::string::npos) ? firma.substr(pre.size(), dos - pre.size()) : "";
        const bool num_ok = !num.empty() && num.size() <= 10 && num[0] != '0' &&
                            std::all_of(num.begin(), num.end(), [](char c) { return c >= '0' && c <= '9'; });
        if (!num_ok || !base64_a_bytes(firma.substr(dos + 1), crypto_sign_BYTES, firma_b) || firma_b.size() != crypto_sign_BYTES) {
            return rechazo(MotivoRechazo::FORMATO, "firma mal formada (vault:vN:<base64 de 64 bytes>)");
        }
    }
    const auto* sig = reinterpret_cast<const unsigned char*>(firma_b.data());
    const auto* msg = reinterpret_cast<const unsigned char*>(carga.data());
    std::string clave_usada;
    if (crypto_sign_verify_detached(sig, msg, carga.size(), claves.actual.data()) == 0) {
        clave_usada = "actual";
    } else if (claves.hay_siguiente && crypto_sign_verify_detached(sig, msg, carga.size(), claves.siguiente.data()) == 0) {
        clave_usada = "siguiente";
    } else {
        return rechazo(MotivoRechazo::FIRMA, std::string("la firma no verifica con la clave actual (") +
                                                 huella_clave_protegidos(claves.actual) + ")" +
                                                 (claves.hay_siguiente ? " ni con la siguiente (" + huella_clave_protegidos(claves.siguiente) + ")" : ""));
    }
    // 3. Carga
    Json::Value c;
    if (!leer_json_estricto(carga, c, err)) return rechazo(MotivoRechazo::FORMATO, "carga: " + err);
    if (!claves_exactas(c, {"esquema", "hospital_id", "version", "emitido_utc", "firmante", "motivo", "hash_anterior",
                            "limites", "comun", "plantas"},
                        sobra)) {
        return rechazo(MotivoRechazo::FORMATO, "carga: " + (sobra.empty() ? "no es un objeto" : sobra));
    }
    if (!entero(c["esquema"]) || !c["esquema"].isUInt64() || c["esquema"].asUInt64() != 1) {
        return rechazo(MotivoRechazo::FORMATO, "carga: esquema distinto de 1");
    }
    if (!c["hospital_id"].isString() || !es_id(c["hospital_id"].asString())) {
        return rechazo(MotivoRechazo::FORMATO, "carga: hospital_id mal formado ([a-z0-9-], de 1 a 64)");
    }
    if (!entero(c["version"]) || !c["version"].isUInt64() || c["version"].asUInt64() < 1) {
        return rechazo(MotivoRechazo::FORMATO, "carga: version tiene que ser un entero >= 1");
    }
    if (!c["emitido_utc"].isString() || !es_fecha_utc(c["emitido_utc"].asString())) {
        return rechazo(MotivoRechazo::FORMATO, "carga: emitido_utc mal formado (AAAA-MM-DDTHH:MM:SSZ)");
    }
    if (!c["firmante"].isString() || !es_texto(c["firmante"].asString(), 128)) {
        return rechazo(MotivoRechazo::FORMATO, "carga: firmante vacío, de más de 128 bytes o con caracteres de control");
    }
    if (!c["motivo"].isString() || !es_texto(c["motivo"].asString(), 200)) {
        return rechazo(MotivoRechazo::FORMATO, "carga: motivo vacío, de más de 200 bytes o con caracteres de control");
    }
    if (!c["hash_anterior"].isString() || !(c["hash_anterior"].asString().empty() || es_hex_min(c["hash_anterior"].asString(), 64))) {
        return rechazo(MotivoRechazo::FORMATO, "carga: hash_anterior tiene que ser vacío o 64 hex en minúsculas");
    }
    std::array<int, 5> lim{};
    {
        const Json::Value& l = c["limites"];
        if (!claves_exactas(l, {"infraestructura", "intranet", "dmz", "externos_criticos"}, sobra)) {
            return rechazo(MotivoRechazo::FORMATO, "carga: limites: " + (sobra.empty() ? "no es un objeto" : sobra));
        }
        for (const char* k : kCategoriasManifiesto) {
            if (!entero(l[k]) || !l[k].isInt()) return rechazo(MotivoRechazo::FORMATO, std::string("carga: limites.") + k + " no es un entero");
            const int v = l[k].asInt();
            const bool infra = std::string(k) == "infraestructura";
            if (infra ? (v != 32) : (v < kProtegidosLimiteMin || v > 32)) {
                return rechazo(MotivoRechazo::LIMITE, std::string("carga: limites.") + k + "=" + std::to_string(v) +
                                                          (infra ? " (infraestructura: solo 32)" : " fuera de [8, 32]"));
            }
            lim[static_cast<std::size_t>(categoria_por_nombre(k))] = v;
        }
    }
    const Json::Value& plantas = c["plantas"];
    if (!plantas.isObject()) return rechazo(MotivoRechazo::FORMATO, "carga: plantas no es un objeto");
    std::size_t total = 0;
    // Todo el documento se valida entero: todos los firewalls del hospital aceptan o rechazan el mismo manifiesto.
    if (auto e = validar_entradas(c["comun"], "comun", lim, true, nullptr, total)) return rechazo(e->motivo, "carga: " + e->detalle);
    for (const auto& p : plantas.getMemberNames()) {
        if (!es_id(p)) return rechazo(MotivoRechazo::FORMATO, "carga: planta '" + detalle_protegidos::saneado(p) + "' mal formada ([a-z0-9-], de 1 a 64)");
        if (auto e = validar_entradas(plantas[p], "plantas." + p, lim, false, nullptr, total)) return rechazo(e->motivo, "carga: " + e->detalle);
    }
    // 4. Para ESTE firewall
    if (c["hospital_id"].asString() != hospital_id) {
        return rechazo(MotivoRechazo::HOSPITAL, "manifiesto de '" + c["hospital_id"].asString() + "', este firewall es de '" +
                                                    detalle_protegidos::saneado(hospital_id) + "'");
    }
    const uint64_t version = c["version"].asUInt64();
    if (version <= version_aplicada) {
        return rechazo(MotivoRechazo::VERSION, "version " + std::to_string(version) + " <= la aplicada " + std::to_string(version_aplicada));
    }
    auto m = std::make_shared<ManifiestoVerificado>();
    std::size_t total2 = 0;
    if (planta_p != nullptr) {
        const std::string& planta = *planta_p;
        if (!plantas.isMember(planta)) {
            return rechazo(MotivoRechazo::PLANTA, "el manifiesto no trae la planta '" + detalle_protegidos::saneado(planta) + "'");
        }
        validar_entradas(c["comun"], "comun", lim, true, &m->entradas, total2);
        validar_entradas(plantas[planta], "plantas." + planta, lim, false, &m->entradas, total2);
        if (auto r = repetidas(m->entradas)) return rechazo(MotivoRechazo::FORMATO, "carga: " + *r);
        m->planta = planta;
    } else {
        // Documento entero: lo que rechazaría CUALQUIER firewall del hospital lo rechaza el servidor
        if (plantas.getMemberNames().empty()) return rechazo(MotivoRechazo::PLANTA, "el manifiesto no trae ninguna planta");
        validar_entradas(c["comun"], "comun", lim, true, &m->entradas, total2);
        for (const auto& p : plantas.getMemberNames()) {
            std::vector<EntradaProtegida> una;
            std::size_t t3 = 0;
            validar_entradas(c["comun"], "comun", lim, true, &una, t3);
            validar_entradas(plantas[p], "plantas." + p, lim, false, &una, t3);
            if (auto r = repetidas(una)) return rechazo(MotivoRechazo::FORMATO, "carga: planta " + p + ": " + *r);
            validar_entradas(plantas[p], "plantas." + p, lim, false, &m->entradas, total2);
        }
    }
    m->version = version;
    m->hospital_id = c["hospital_id"].asString();
    m->firmante = c["firmante"].asString();
    m->emitido_utc = c["emitido_utc"].asString();
    m->motivo = c["motivo"].asString();
    m->hash_anterior = c["hash_anterior"].asString();
    m->clave = clave_usada;
    m->sha256_carga = sha256_hex(carga);
    m->sobre = sobre;
    m->limites = lim;
    ResultadoVerificacion r;
    r.ok = true;
    r.manifiesto = m;
    return r;
}
}  // namespace

ResultadoVerificacion verificar_manifiesto(const std::string& sobre, const ClavesProtegidos& claves,
                                           const std::string& hospital_id, const std::string& planta,
                                           uint64_t version_aplicada) {
    return verificar(sobre, claves, hospital_id, &planta, version_aplicada);
}

ResultadoVerificacion verificar_documento(const std::string& sobre, const ClavesProtegidos& claves,
                                          const std::string& hospital_id, uint64_t version_aplicada) {
    return verificar(sobre, claves, hospital_id, nullptr, version_aplicada);
}

std::string resumen_manifiesto(const ManifiestoVerificado& m) {
    const auto n = m.por_categoria();
    std::ostringstream o;
    o << "[PROTEGIDOS-MANIFIESTO] verificado version=" << m.version << " clave=" << m.clave
      << " firmante=" << detalle_protegidos::saneado(m.firmante) << " hospital=" << m.hospital_id << " planta=" << m.planta
      << " emitido=" << m.emitido_utc << " entradas=" << m.entradas.size()
      << " (infraestructura=" << n[static_cast<std::size_t>(CategoriaProtegida::INFRAESTRUCTURA)]
      << " intranet=" << n[static_cast<std::size_t>(CategoriaProtegida::INTRANET)]
      << " dmz=" << n[static_cast<std::size_t>(CategoriaProtegida::DMZ)]
      << " externos_criticos=" << n[static_cast<std::size_t>(CategoriaProtegida::EXTERNOS_CRITICOS)] << ")"
      << " sha256=" << m.sha256_carga.substr(0, 16);
    return o.str();
}

ProtegidosVigentes::ProtegidosVigentes(ClavesProtegidos claves, std::string hospital_id, std::string planta)
    : claves_(claves), hospital_id_(std::move(hospital_id)), planta_(std::move(planta)),
      rangos_(std::make_shared<const RangosProtegidos>()) {}

ProtegidosVigentes::Propuesta ProtegidosVigentes::proponer(const std::string& sobre) {
    std::lock_guard<std::mutex> l(m_);
    Propuesta p;
    p.anterior = vigente_;
    p.resultado = verificar_manifiesto(sobre, claves_, hospital_id_, planta_, vigente_ ? vigente_->version : 0);
    if (p.resultado.ok) {
        vigente_ = p.resultado.manifiesto;
        rangos_ = std::make_shared<const RangosProtegidos>(vigente_->rangos());
    } else {
        ++rechazos_;
    }
    return p;
}

ResultadoVerificacion ProtegidosVigentes::reverificar(const std::string& sobre) const {
    std::lock_guard<std::mutex> l(m_);
    if (!vigente_) return verificar_manifiesto(sobre, claves_, hospital_id_, planta_, 0);
    ResultadoVerificacion r = verificar_manifiesto(sobre, claves_, hospital_id_, planta_, vigente_->version - 1);
    if (r.ok && r.manifiesto->sobre != vigente_->sobre) {
        return rechazo(MotivoRechazo::VERSION, "la caché verifica pero no es el manifiesto vigente (version " +
                                                   std::to_string(r.manifiesto->version) + ")");
    }
    return r;
}

std::shared_ptr<const ManifiestoVerificado> ProtegidosVigentes::vigente() const {
    std::lock_guard<std::mutex> l(m_);
    return vigente_;
}

bool ProtegidosVigentes::verificado() const {
    std::lock_guard<std::mutex> l(m_);
    return vigente_ != nullptr;
}

std::shared_ptr<const RangosProtegidos> ProtegidosVigentes::rangos() const {
    std::lock_guard<std::mutex> l(m_);
    return rangos_;
}

uint64_t ProtegidosVigentes::rechazos() const {
    std::lock_guard<std::mutex> l(m_);
    return rechazos_;
}

bool leer_cache_protegidos(const std::string& ruta, std::string& sobre, std::string& error) {
    if (ruta.empty() || ruta[0] != '/') {
        error = "ruta no absoluta";
        return false;
    }
    const int fd = ::open(ruta.c_str(), O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) {
        error = std::string("no se puede abrir: ") + std::strerror(errno);
        return false;
    }
    struct stat st {};
    if (::fstat(fd, &st) != 0 || !S_ISREG(st.st_mode)) {
        ::close(fd);
        error = "no es un fichero regular";
        return false;
    }
    if (static_cast<std::size_t>(st.st_size) > kProtegidosMaxSobreBytes) {
        ::close(fd);
        error = "pasa de " + std::to_string(kProtegidosMaxSobreBytes) + " bytes";
        return false;
    }
    std::string buf(static_cast<std::size_t>(st.st_size), '\0');
    std::size_t leidos = 0;
    while (leidos < buf.size()) {
        const ssize_t n = ::read(fd, buf.data() + leidos, buf.size() - leidos);
        if (n <= 0) {
            ::close(fd);
            error = "lectura corta";
            return false;
        }
        leidos += static_cast<std::size_t>(n);
    }
    ::close(fd);
    sobre.swap(buf);
    return true;
}

bool escribir_cache_protegidos(const std::string& ruta, const std::string& sobre, std::string& error) {
    if (ruta.empty() || ruta[0] != '/') {
        error = "ruta no absoluta";
        return false;
    }
    const std::string tmp = ruta + ".tmp";
    ::unlink(tmp.c_str());
    const int fd = ::open(tmp.c_str(), O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0640);
    if (fd < 0) {
        error = std::string("no se puede crear ") + tmp + ": " + std::strerror(errno);
        return false;
    }
    std::size_t escritos = 0;
    while (escritos < sobre.size()) {
        const ssize_t n = ::write(fd, sobre.data() + escritos, sobre.size() - escritos);
        if (n <= 0) {
            ::close(fd);
            ::unlink(tmp.c_str());
            error = "escritura corta";
            return false;
        }
        escritos += static_cast<std::size_t>(n);
    }
    if (::fsync(fd) != 0 || ::close(fd) != 0) {
        ::unlink(tmp.c_str());
        error = "fsync o close";
        return false;
    }
    if (::rename(tmp.c_str(), ruta.c_str()) != 0) {
        ::unlink(tmp.c_str());
        error = std::string("rename: ") + std::strerror(errno);
        return false;
    }
    return true;
}

std::vector<std::string> infra_sin_cubrir(const ManifiestoVerificado& m, const std::vector<std::string>& endpoints) {
    RangosProtegidos infra;
    for (const auto& e : m.entradas) {
        if (e.rango.cat == CategoriaProtegida::INFRAESTRUCTURA) infra.rangos.push_back(e.rango);
    }
    std::vector<std::string> faltan;
    for (const auto& ep : endpoints) {
        const std::string pre = "https://";
        std::string host;
        if (ep.rfind(pre, 0) == 0) {
            const std::size_t dos = ep.find(':', pre.size());
            host = ep.substr(pre.size(), dos == std::string::npos ? std::string::npos : dos - pre.size());
        }
        if (host.empty() || infra.categoria_de(host) != CategoriaProtegida::INFRAESTRUCTURA) faltan.push_back(ep);
    }
    return faltan;
}

}  // namespace argus::protegidos
