// etcd-server/src/protegidos_servidor.cpp — [PROTEGIDOS-MANIFIESTO-D318] ADR-060 paso 8e.3b. Ver la cabecera.
#include "etcd_server/protegidos_servidor.hpp"

#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <map>

namespace argus::protegidos {

using ::argus::almacen::Estado;
using nlohmann::json;

namespace {
bool es_id(const std::string& s) {
    return !s.empty() && s.size() <= 64 && std::all_of(s.begin(), s.end(), [](char c) {
        return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-';
    });
}

std::string error_json(const std::string& motivo, const std::string& detalle) {
    return json{{"status", "error"}, {"motivo", motivo}, {"message", detalle}}.dump();
}

constexpr const char* kVigente = "protegidos/vigente";
constexpr const char* kHistorico = "protegidos/v/";
}  // namespace

ResultadoProtegidosConfig parse_protegidos_config(const json& root, std::ostream& aviso, std::ostream& info) {
    ResultadoProtegidosConfig r;
    const json* p = (root.is_object() && root.contains("protegidos")) ? &root["protegidos"] : nullptr;
    if (p != nullptr && p->is_object() && p->contains("hospital_id") && (*p)["hospital_id"].is_string() &&
        es_id((*p)["hospital_id"].get<std::string>())) {
        r.cfg.hospital_id = (*p)["hospital_id"].get<std::string>();
        info << "[ETCD-PROTEGIDOS] protegidos.hospital_id=" << r.cfg.hospital_id << " (JSON)" << std::endl;
        return r;
    }
    r.defectos = 1;
    const char* que = (p == nullptr) ? "protegidos ausente"
                      : !p->is_object() ? "protegidos no es un objeto"
                      : !p->contains("hospital_id") ? "protegidos.hospital_id ausente"
                                                    : "protegidos.hospital_id mal formado";
    aviso << "[CONFIG-DEFAULT] " << que << " ([a-z0-9-], de 1 a 64): sin valor sano por defecto; GET y PUT "
             "/v1/protegidos responderán 503 (ADR-060; Ansible lo escribe desde argus_hospital_id)" << std::endl;
    return r;
}

AlmacenProtegidos::AlmacenProtegidos(std::unique_ptr<::argus::almacen::IRegistryStore> almacen, ClavesProtegidos claves,
                                     std::string hospital_id, std::ostream& log)
    : almacen_(std::move(almacen)), claves_(claves), hospital_id_(std::move(hospital_id)), log_(log) {}

std::string AlmacenProtegidos::clave_version(uint64_t n) {
    char b[32];
    std::snprintf(b, sizeof b, "%020llu", static_cast<unsigned long long>(n));
    return std::string(kHistorico) + b;
}

bool AlmacenProtegidos::version_vigente(uint64_t& v) {
    v = 0;
    std::string s;
    const Estado e = almacen_->leer(kVigente, s);
    if (e == Estado::NoDisponible) return false;
    if (e == Estado::Ok) {
        const auto r = verificar_documento(s, claves_, hospital_id_, 0);
        if (r.ok) {
            v = r.manifiesto->version;
            return true;
        }
        log_ << "[PROTEGIDOS-ALMACEN] el vigente guardado ya no verifica (motivo=" << nombre_motivo(r.motivo) << " "
             << r.detalle << "): se toma la mayor versión del histórico" << std::endl;
    }
    std::map<std::string, std::string> h;
    if (almacen_->listar(kHistorico, h) == Estado::NoDisponible) return false;
    if (!h.empty()) {
        const std::string ultima = h.rbegin()->first.substr(std::string(kHistorico).size());
        v = std::strtoull(ultima.c_str(), nullptr, 10);
    }
    return true;
}

AlmacenProtegidos::Respuesta AlmacenProtegidos::obtener() {
    if (hospital_id_.empty()) return {503, error_json("sin-configurar", "protegidos.hospital_id sin valor en etcd-server.json")};
    std::lock_guard<std::mutex> l(m_);
    std::string s;
    const Estado e = almacen_->leer(kVigente, s);
    if (e == Estado::Ok) return {200, s};
    if (e == Estado::NoEncontrado) return {404, error_json("sin-manifiesto", "no hay manifiesto de protegidos publicado")};
    return {503, error_json("almacen", "almacén no disponible: " + almacen_->ultimo_error())};
}

AlmacenProtegidos::Respuesta AlmacenProtegidos::obtener_version(const std::string& n) {
    if (hospital_id_.empty()) return {503, error_json("sin-configurar", "protegidos.hospital_id sin valor en etcd-server.json")};
    // [PROTEGIDOS-MANIFIESTO-D319] decimal >= 1, sin ceros a la izquierda, que quepa en 64 bits (20 cifras como mucho)
    static const std::string kMax = "18446744073709551615";
    const bool cifras = !n.empty() && n.size() <= kMax.size() && n[0] != '0' &&
                        std::all_of(n.begin(), n.end(), [](char c) { return c >= '0' && c <= '9'; });
    if (!cifras || (n.size() == kMax.size() && n > kMax)) {
        return {400, error_json("formato", "versión '" + detalle_protegidos::saneado(n) +
                                               "' mal formada (entero decimal >= 1 sin ceros a la izquierda, 64 bits)")};
    }
    const uint64_t v = std::strtoull(n.c_str(), nullptr, 10);
    std::lock_guard<std::mutex> l(m_);
    std::string s;
    const Estado e = almacen_->leer(clave_version(v), s);
    if (e == Estado::Ok) return {200, s};
    if (e == Estado::NoEncontrado) return {404, error_json("sin-version", "la versión " + n + " no está en el histórico")};
    return {503, error_json("almacen", "almacén no disponible: " + almacen_->ultimo_error())};
}

AlmacenProtegidos::Respuesta AlmacenProtegidos::publicar(const std::string& sobre, const std::string& quien) {
    const std::string q = detalle_protegidos::saneado(quien);
    if (hospital_id_.empty()) return {503, error_json("sin-configurar", "protegidos.hospital_id sin valor en etcd-server.json")};
    if (sobre.size() > kProtegidosMaxSobreBytes) {
        log_ << "[PROTEGIDOS-PUT-RECHAZADO] cn=" << q << " motivo=formato " << sobre.size() << " bytes" << std::endl;
        return {413, error_json("formato", "sobre de " + std::to_string(sobre.size()) + " bytes (máximo " +
                                               std::to_string(kProtegidosMaxSobreBytes) + ")")};
    }
    std::lock_guard<std::mutex> l(m_);
    uint64_t vig = 0;
    if (!version_vigente(vig)) return {503, error_json("almacen", "almacén no disponible: " + almacen_->ultimo_error())};
    const auto r = verificar_documento(sobre, claves_, hospital_id_, vig);
    if (!r.ok) {
        const int http = r.motivo == MotivoRechazo::VERSION ? 409
                         : (r.motivo == MotivoRechazo::FIRMA || r.motivo == MotivoRechazo::HOSPITAL) ? 403
                                                                                                  : 400;
        log_ << "[PROTEGIDOS-PUT-RECHAZADO] cn=" << q << " motivo=" << nombre_motivo(r.motivo) << " " << r.detalle
             << " (vigente=" << vig << ")" << std::endl;
        return {http, error_json(nombre_motivo(r.motivo), r.detalle)};
    }
    const auto& m = *r.manifiesto;
    const std::string kv = clave_version(m.version);
    std::string ya;
    const Estado e0 = almacen_->leer(kv, ya);
    if (e0 == Estado::NoDisponible) return {503, error_json("almacen", "almacén no disponible: " + almacen_->ultimo_error())};
    if (e0 == Estado::Ok) {
        log_ << "[PROTEGIDOS-PUT-RECHAZADO] cn=" << q << " motivo=version la " << m.version
             << " ya está en el histórico (una publicación anterior se quedó a medias): firme la siguiente" << std::endl;
        return {409, error_json("version", "la versión " + std::to_string(m.version) + " ya existe en el histórico")};
    }
    if (almacen_->poner(kv, sobre) != Estado::Ok || almacen_->poner(kVigente, sobre) != Estado::Ok) {
        log_ << "[PROTEGIDOS-PUT-RECHAZADO] cn=" << q << " motivo=almacen " << almacen_->ultimo_error() << std::endl;
        return {503, error_json("almacen", "almacén no disponible: " + almacen_->ultimo_error())};
    }
    log_ << "[PROTEGIDOS-PUBLICADO] version=" << m.version << " anterior=" << vig << " cn=" << q
         << " firmante=" << detalle_protegidos::saneado(m.firmante) << " clave=" << m.clave << " entradas="
         << m.entradas.size() << " sha256=" << m.sha256_carga.substr(0, 16) << std::endl;
    return {201, json{{"status", "ok"}, {"version", m.version}, {"anterior", vig}, {"sha256", m.sha256_carga}}.dump()};
}

}  // namespace argus::protegidos
