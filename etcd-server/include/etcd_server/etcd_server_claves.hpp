#pragma once
// etcd-server/include/etcd_server/etcd_server_claves.hpp — [ETCD-CLAVES-D314]
// Almacén de las claves HMAC (DEBT-ETCD-HA-TLS-RAFT-001, paso 4b.4). Decisiones de Alonso (DAY314):
//   - V1: cliente propio de Vault en el etcd-server (httplib::SSLClient, mTLS, auth cert); common/vault_client hace otra
//     cosa (semilla, token, solo lectura) y lo usan otros componentes.
//   - V2: escritura única también en Vault: cas_required=true en el montaje (aprovisionamiento) y CAS desde el código.
//   - V3: almacen_claves.modo = "memoria" en el defender hasta el paso 6 (como almacen.modo y tls.modo).
//   - V4: buscar una clave antigua por huella (re-verificar el grafo años después) queda FUERA (DEBT-BRONZE-KEY-ID-001).
//   - JSON es la ley. Las direcciones de Vault NO tienen defecto: en modo vault, una lista ausente o mal formada (o una
//     ruta de certificado ausente o mal formada) es [ETCD-VAULT-FATAL] y el etcd-server no arranca (--check-config lo
//     detecta antes). Solo en dev se puede suponer algo escuchando en localhost. Los enteros siguen la regla general:
//     ausente o fuera de rango -> defecto validado + [CONFIG-DEFAULT].
//   - Vault inalcanzable con la configuración bien: cada dirección se prueba reintentos_por_direccion veces con espera
//     creciente (espera_inicial_ms, doblando, hasta espera_max_ms) y luego la siguiente de la lista; agotada la lista,
//     [ETCD-VAULT-NO-DISPONIBLE] con el error de cada dirección, y se vuelve a sondear cada sondeo_s sin fin.
// Interfaz ISecretStore: documentos JSON por ruta (relativa al montaje) con versión, y escritura con CAS. Tres
// resultados más Conflicto (el CAS no coincide: otro escribió antes). MemoriaSecretStore: transición y tests.
#include "etcd_server/etcd_server_almacen.hpp"
#include <nlohmann/json.hpp>
#include <functional>
#include <iostream>
#include <map>
#include <mutex>
#include <string>
#include <vector>

namespace argus::etcdcfg {

// Defectos validados: iguales a etcd-server.etcd-vm.json (el del defender lleva modo "memoria": transición).
// vault_addrs, ca_file, cert_file y key_file NO se sustituyen por su defecto en modo vault: ausentes o mal formados son
// fatales. El valor de abajo es el del JSON de la VM y solo sirve de ejemplo en los mensajes.
struct AlmacenClavesConfig {
    std::string modo = "vault";                                    // almacen_claves.modo: "vault" | "memoria"
    std::vector<std::string> vault_addrs{"https://127.0.0.1:8200"}; // almacen_claves.vault_addrs: 1-7 "https://IPv4:puerto"
    std::string ca_file = "/etc/argus-pki/ca.crt";                 // almacen_claves.ca_file: ruta absoluta
    std::string cert_file = "/etc/argus-pki/etcd-server.crt";      // almacen_claves.cert_file: ruta absoluta (CN del login)
    std::string key_file = "/etc/argus-pki/etcd-server.key";       // almacen_claves.key_file: ruta absoluta
    std::string montaje = "argus-hmac";                            // almacen_claves.montaje: [a-z0-9-], 1-64
    std::string rol_login = "etcd-server";                         // almacen_claves.rol_login: auth/cert/certs/<rol>
    int timeout_ms = 2000;                                         // almacen_claves.timeout_ms: [100, 30000]
    int reintentos_por_direccion = 3;                              // almacen_claves.reintentos_por_direccion: [1, 10]
    int espera_inicial_ms = 200;                                   // almacen_claves.espera_inicial_ms: [10, 10000]
    int espera_max_ms = 2000;                                      // almacen_claves.espera_max_ms: [100, 60000]
    int sondeo_s = 5;                                              // almacen_claves.sondeo_s: [1, 300]
    int aviso_intervalo_s = 60;                                    // almacen_claves.aviso_intervalo_s: [10, 3600]
};

struct ResultadoAlmacenClaves {
    AlmacenClavesConfig cfg;
    int defectos = 0;
    std::vector<std::string> fatales;  // en modo vault: direcciones o rutas ausentes o mal formadas (no arranca)
};

namespace detalle_claves {
inline bool nombre_ok(const std::string& s) {
    if (s.empty() || s.size() > 64) return false;
    for (char c : s) {
        const bool ok = (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-';
        if (!ok) return false;
    }
    return true;
}
}  // namespace detalle_claves

inline ResultadoAlmacenClaves parse_almacen_claves_config(const nlohmann::json& root, std::ostream& aviso = std::cerr,
                                                          std::ostream& info = std::cout) {
    ResultadoAlmacenClaves r;
    AlmacenClavesConfig& c = r.cfg;
    const AlmacenClavesConfig d{};
    static const nlohmann::json kVacio = nlohmann::json::object();
    const nlohmann::json* blk = &kVacio;
    if (root.is_object() && root.contains("almacen_claves")) {
        if (root["almacen_claves"].is_object()) {
            blk = &root["almacen_claves"];
        } else {
            aviso << "[CONFIG-DEFAULT] almacen_claves no es un objeto: se tratan todos sus campos como ausentes"
                  << std::endl;
        }
    }
    auto ausente = [&](const char* campo, const std::string& formato, const std::string& def) {
        aviso << "[CONFIG-DEFAULT] almacen_claves." << campo << " ausente (" << formato << "): se usa " << def
              << std::endl;
        ++r.defectos;
        return std::string("DEFECTO: ausente");
    };
    auto malo = [&](const char* campo, const nlohmann::json& v, const std::string& formato, const std::string& def) {
        aviso << "[CONFIG-DEFAULT] almacen_claves." << campo << "=" << v.dump() << " mal formado (" << formato
              << "): se usa " << def << std::endl;
        ++r.defectos;
        return std::string("DEFECTO: mal formado");
    };

    std::string o_modo = "JSON";
    if (!blk->contains("modo")) {
        o_modo = ausente("modo", "\"vault\" o \"memoria\"", d.modo);
    } else {
        const auto& v = (*blk)["modo"];
        if (v.is_string() && (v.get<std::string>() == "vault" || v.get<std::string>() == "memoria")) {
            c.modo = v.get<std::string>();
        } else {
            o_modo = malo("modo", v, "\"vault\" o \"memoria\"; una errata nunca rebaja a memoria", d.modo);
        }
    }
    const bool vault = c.modo == "vault";
    // Campos de conexión: sin defecto en modo vault (fatal); en modo memoria no se usan y solo se avisa
    auto fatal = [&](const std::string& campo, const std::string& que, const std::string& formato) {
        std::string m = "almacen_claves.";
        m += campo;
        m += ' ';
        m += que;
        m += " (";
        m += formato;
        m += ")";
        if (vault) {
            r.fatales.push_back(m);
            aviso << "[ETCD-VAULT-FATAL] " << m << ": sin dirección de Vault fiable no hay claves; no se arranca"
                  << std::endl;
        } else {
            aviso << "[CONFIG-DEFAULT] " << m << ": no se usa en modo memoria" << std::endl;
            ++r.defectos;
        }
        return std::string(vault ? "FATAL: " : "SIN USO: ") + que;
    };

    std::string o_addr = "JSON";
    {
        const std::string fmt = "lista de 1 a 7 \"https://IPv4:puerto\", sin repetir";
        if (!blk->contains("vault_addrs")) {
            o_addr = fatal("vault_addrs", "ausente", fmt);
        } else {
            const auto& v = (*blk)["vault_addrs"];
            bool ok = v.is_array() && !v.empty() && v.size() <= 7;
            std::vector<std::string> lista;
            if (ok) {
                for (const auto& e : v) {
                    if (!e.is_string() || !detalle_almacen::endpoint_ok(e.get<std::string>())) {
                        ok = false;
                        break;
                    }
                    for (const auto& x : lista) {
                        if (x == e.get<std::string>()) ok = false;
                    }
                    lista.push_back(e.get<std::string>());
                }
            }
            if (ok) {
                c.vault_addrs = lista;
            } else {
                std::string que = "mal formado: ";
                que += v.dump();
                o_addr = fatal("vault_addrs", que, fmt);
            }
        }
    }

    auto ruta = [&](const char* clave, std::string& out) -> std::string {
        const std::string fmt = "ruta absoluta, sin caracteres de control, hasta 4096";
        if (!blk->contains(clave)) return fatal(clave, "ausente", fmt);
        const auto& v = (*blk)[clave];
        if (!v.is_string() || !detalle_almacen::ruta_ok(v.get<std::string>())) {
            std::string que = "mal formado: ";
            que += v.dump();
            return fatal(clave, que, fmt);
        }
        out = v.get<std::string>();
        return "JSON";
    };
    const std::string o_ca = ruta("ca_file", c.ca_file);
    const std::string o_cert = ruta("cert_file", c.cert_file);
    const std::string o_key = ruta("key_file", c.key_file);

    auto nombre = [&](const char* clave, const std::string& def, std::string& out) -> std::string {
        out = def;
        const std::string fmt = "[a-z0-9-], de 1 a 64";
        if (!blk->contains(clave)) return ausente(clave, fmt, def);
        const auto& v = (*blk)[clave];
        if (!v.is_string() || !detalle_claves::nombre_ok(v.get<std::string>())) return malo(clave, v, fmt, def);
        out = v.get<std::string>();
        return "JSON";
    };
    const std::string o_mon = nombre("montaje", d.montaje, c.montaje);
    const std::string o_rol = nombre("rol_login", d.rol_login, c.rol_login);

    auto entero = [&](const char* clave, int def, int mn, int mx, int& out) -> std::string {
        out = def;
        const std::string fmt = "entero en [" + std::to_string(mn) + ", " + std::to_string(mx) + "]";
        if (!blk->contains(clave)) return ausente(clave, fmt, std::to_string(def));
        const auto& v = (*blk)[clave];
        if (!v.is_number_integer()) return malo(clave, v, fmt, std::to_string(def));
        const long long x = v.get<long long>();
        if (x < mn || x > mx) return malo(clave, v, fmt, std::to_string(def));
        out = static_cast<int>(x);
        return "JSON";
    };
    const std::string o_to = entero("timeout_ms", d.timeout_ms, 100, 30000, c.timeout_ms);
    const std::string o_re =
        entero("reintentos_por_direccion", d.reintentos_por_direccion, 1, 10, c.reintentos_por_direccion);
    const std::string o_ei = entero("espera_inicial_ms", d.espera_inicial_ms, 10, 10000, c.espera_inicial_ms);
    std::string o_em = entero("espera_max_ms", d.espera_max_ms, 100, 60000, c.espera_max_ms);
    if (c.espera_max_ms < c.espera_inicial_ms) {
        aviso << "[CONFIG-DEFAULT] almacen_claves.espera_max_ms=" << c.espera_max_ms << " < espera_inicial_ms="
              << c.espera_inicial_ms << " (regla: espera_max_ms >= espera_inicial_ms): se usa espera_max_ms="
              << c.espera_inicial_ms << std::endl;
        ++r.defectos;
        c.espera_max_ms = c.espera_inicial_ms;
        o_em = "DEFECTO: menor que espera_inicial_ms";
    }
    const std::string o_so = entero("sondeo_s", d.sondeo_s, 1, 300, c.sondeo_s);
    const std::string o_av = entero("aviso_intervalo_s", d.aviso_intervalo_s, 10, 3600, c.aviso_intervalo_s);

    info << "[ETCD-CLAVES] almacen_claves.modo=" << c.modo << " (" << o_modo << ") almacen_claves.vault_addrs="
         << nlohmann::json(c.vault_addrs).dump() << " (" << o_addr << ") almacen_claves.ca_file=" << c.ca_file << " ("
         << o_ca << ") almacen_claves.cert_file=" << c.cert_file << " (" << o_cert << ") almacen_claves.key_file="
         << c.key_file << " (" << o_key << ") almacen_claves.montaje=" << c.montaje << " (" << o_mon
         << ") almacen_claves.rol_login=" << c.rol_login << " (" << o_rol << ") almacen_claves.timeout_ms="
         << c.timeout_ms << " (" << o_to << ") almacen_claves.reintentos_por_direccion=" << c.reintentos_por_direccion
         << " (" << o_re << ") almacen_claves.espera_inicial_ms=" << c.espera_inicial_ms << " (" << o_ei
         << ") almacen_claves.espera_max_ms=" << c.espera_max_ms << " (" << o_em << ") almacen_claves.sondeo_s="
         << c.sondeo_s << " (" << o_so << ") almacen_claves.aviso_intervalo_s=" << c.aviso_intervalo_s << " (" << o_av
         << ")" << std::endl;
    return r;
}

}  // namespace argus::etcdcfg

namespace argus::claves {

enum class Estado { Ok, NoEncontrado, NoDisponible, Conflicto };

inline const char* texto(Estado e) {
    switch (e) {
        case Estado::Ok: return "ok";
        case Estado::NoEncontrado: return "no encontrado";
        case Estado::NoDisponible: return "no disponible";
        case Estado::Conflicto: return "conflicto (CAS)";
    }
    return "?";
}

// Rutas relativas al montaje ("ml-detector/ventana"). version: la de kv v2 (1, 2, ...).
// escribir: cas = 0 -> solo si la ruta no existe; cas = N -> solo si la versión actual es N. Nunca sin CAS.
class ISecretStore {
public:
    virtual ~ISecretStore() = default;
    virtual Estado leer(const std::string& ruta, nlohmann::json& datos, int& version) = 0;
    virtual Estado escribir(const std::string& ruta, const nlohmann::json& datos, int cas, int& version_nueva) = 0;
    // Sin red mientras se sabe caído (falla rápido: se sirve la caché); sondear() es el único que prueba de nuevo.
    virtual bool disponible() const = 0;
    virtual bool sondear() = 0;
    virtual std::string descripcion() const = 0;
    virtual std::string ultimo_error() const = 0;
};

class MemoriaSecretStore : public ISecretStore {
public:
    // Para tests: se llama dentro de escribir(), antes de comprobar el CAS (simula a otro etcd-server escribiendo antes)
    std::function<void(const std::string&)> antes_de_escribir;

    Estado leer(const std::string& ruta, nlohmann::json& datos, int& version) override {
        std::lock_guard<std::mutex> lk(m_);
        if (caido_) return Estado::NoDisponible;
        auto it = docs_.find(ruta);
        if (it == docs_.end()) return Estado::NoEncontrado;
        datos = it->second.first;
        version = it->second.second;
        return Estado::Ok;
    }
    Estado escribir(const std::string& ruta, const nlohmann::json& datos, int cas, int& version_nueva) override {
        if (antes_de_escribir) antes_de_escribir(ruta);
        std::lock_guard<std::mutex> lk(m_);
        if (caido_) return Estado::NoDisponible;
        auto it = docs_.find(ruta);
        const int actual = it == docs_.end() ? 0 : it->second.second;
        if (cas != actual) return Estado::Conflicto;
        docs_[ruta] = {datos, actual + 1};
        version_nueva = actual + 1;
        return Estado::Ok;
    }
    // Solo para tests: escribir sin CAS (lo que haría otro proceso)
    void poner(const std::string& ruta, const nlohmann::json& datos) {
        std::lock_guard<std::mutex> lk(m_);
        auto it = docs_.find(ruta);
        const int actual = it == docs_.end() ? 0 : it->second.second;
        docs_[ruta] = {datos, actual + 1};
    }
    bool disponible() const override {
        std::lock_guard<std::mutex> lk(m_);
        return !caido_;
    }
    bool sondear() override { return disponible(); }
    std::string descripcion() const override { return "memoria (SIN persistencia: transición o tests)"; }
    std::string ultimo_error() const override { return disponible() ? "" : "simulado caído"; }
    void simular_caido(bool c) {
        std::lock_guard<std::mutex> lk(m_);
        caido_ = c;
    }
    size_t cuantos() const {
        std::lock_guard<std::mutex> lk(m_);
        return docs_.size();
    }

private:
    mutable std::mutex m_;
    std::map<std::string, std::pair<nlohmann::json, int>> docs_;
    bool caido_ = false;
};

}  // namespace argus::claves
