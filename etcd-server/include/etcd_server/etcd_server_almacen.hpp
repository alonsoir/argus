#pragma once
// etcd-server/include/etcd_server/etcd_server_almacen.hpp — [ETCD-ALMACEN-D313]
// Almacén del registro de componentes (DEBT-ETCD-HA-TLS-RAFT-001, paso 4b.3).
//   - Bloque "almacen" de etcd-server.json: modo (etcd | memoria), endpoints, ca_file, cert_file, key_file, prefijo,
//     timeout_ms, aviso_intervalo_s. El JSON es la ley: ausente o mal formado -> defecto validado + [CONFIG-DEFAULT].
//   - [ETCD-ALMACEN-FATAL-D315] Excepción (decisión de Alonso DAY315, como vault_addrs en DAY314): en modo etcd,
//     endpoints, prefijo, ca_file, cert_file y key_file NO tienen defecto. Ausentes o mal formados (endpoints
//     repetidos incluidos) son [ETCD-ALMACEN-FATAL] y el etcd-server no arranca (--check-config lo cuenta). Los
//     rellena Ansible por despliegue (DEBT-ANSIBLE-DEPLOY-CONFIGS-001): un prefijo con errata nunca cae en /argus/ en
//     silencio, donde dos despliegues del mismo clúster se pisarían. En modo memoria no se usan: solo se avisa.
//     Un modo ausente o mal escrito va a "etcd". "memoria" solo queda para el smoke enterprise de
//     emecas++ (etcd-server.smoke-enterprise.json; DEBT-VAULT-ENTERPRISE-SMOKE-VM-001) y se borra entonces.
//   - IRegistryStore: clave -> valor (texto) bajo un prefijo. Tres resultados: Ok, NoEncontrado, NoDisponible.
//     NoDisponible = el almacén no responde (etcd caído o inalcanzable): quien llama decide (503 en escrituras, caché
//     en lecturas; decisión de Alonso DAY313).
//   - MemoriaRegistryStore: para el modo de transición y para los tests. EtcdRegistryStore (gRPC, TLS) va aparte
//     (etcd_registry_store.hpp) para que esta cabecera no dependa de etcd-cpp-apiv3.
#include <nlohmann/json.hpp>
#include <iostream>
#include <map>
#include <mutex>
#include <optional>
#include <string>
#include <vector>

namespace argus::etcdcfg {

// Defectos validados: iguales a etcd-server.json (el del smoke enterprise lleva modo "memoria").
// [ETCD-ALMACEN-FATAL-D315] endpoints, ca_file, cert_file, key_file y prefijo NO se sustituyen por su defecto en modo
// etcd: ausentes o mal formados son fatales. Su valor de abajo es el del JSON del lab y solo sirve de ejemplo.
struct AlmacenConfig {
    std::string modo = "etcd";                                   // almacen.modo: "etcd" | "memoria"
    std::vector<std::string> endpoints{"https://127.0.0.1:2381"}; // almacen.endpoints: 1-7 "https://IPv4:puerto"
    std::string ca_file = "/etc/argus-pki/ca.crt";               // almacen.ca_file: ruta absoluta
    std::string cert_file = "/etc/argus-pki/etcd-server.crt";    // almacen.cert_file: ruta absoluta (CN = usuario RBAC)
    std::string key_file = "/etc/argus-pki/etcd-server.key";     // almacen.key_file: ruta absoluta
    std::string prefijo = "/argus/";                             // almacen.prefijo: empieza y acaba en /, [a-z0-9/-]
    int timeout_ms = 2000;                                       // almacen.timeout_ms: [100, 30000]
    int aviso_intervalo_s = 60;                                  // almacen.aviso_intervalo_s: [10, 3600]
    // almacen.reconexion_max_ms: [100, 60000]. Tras un fallo, intervalo mínimo entre canales gRPC nuevos. Medido
    // DAY313: un canal que ha fallado tarda ~30 s en volver a usar etcd aunque etcd ya esté de vuelta (los argumentos de
    // backoff de gRPC no lo cambian); un canal nuevo conecta en 0,37 s.
    int reconexion_max_ms = 1000;
};

struct ResultadoAlmacen {
    AlmacenConfig cfg;
    int defectos = 0;
    std::vector<std::string> fatales;  // [ETCD-ALMACEN-FATAL-D315] en modo etcd: campos sin defecto ausentes o mal formados
};

namespace detalle_almacen {
inline bool ruta_ok(const std::string& s) {
    if (s.empty() || s.size() > 4096 || s[0] != '/') return false;
    for (unsigned char ch : s) {
        if (ch < 0x20 || ch == 0x7f) return false;
    }
    return true;
}
// "https://" + IPv4 con puntos + ":" + puerto [1, 65535]
inline bool endpoint_ok(const std::string& s) {
    const std::string pre = "https://";
    if (s.rfind(pre, 0) != 0) return false;
    const std::string resto = s.substr(pre.size());
    const size_t dos = resto.rfind(':');
    if (dos == std::string::npos) return false;
    const std::string ip = resto.substr(0, dos), puerto = resto.substr(dos + 1);
    if (puerto.empty() || puerto.size() > 5) return false;
    for (char c : puerto) {
        if (c < '0' || c > '9') return false;
    }
    const long p = std::stol(puerto);
    if (p < 1 || p > 65535) return false;
    int partes = 0;
    size_t i = 0;
    while (i <= ip.size()) {
        const size_t j = ip.find('.', i);
        const std::string oct = ip.substr(i, (j == std::string::npos ? ip.size() : j) - i);
        if (oct.empty() || oct.size() > 3) return false;
        for (char c : oct) {
            if (c < '0' || c > '9') return false;
        }
        if (std::stoi(oct) > 255) return false;
        ++partes;
        if (j == std::string::npos) break;
        i = j + 1;
    }
    return partes == 4;
}
inline bool prefijo_ok(const std::string& s) {
    if (s.size() < 2 || s.size() > 64 || s.front() != '/' || s.back() != '/') return false;
    for (char c : s) {
        const bool ok = (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-' || c == '/';
        if (!ok) return false;
    }
    return s.find("//") == std::string::npos;
}
}  // namespace detalle_almacen

inline ResultadoAlmacen parse_almacen_config(const nlohmann::json& root, std::ostream& aviso = std::cerr,
                                             std::ostream& info = std::cout) {
    ResultadoAlmacen r;
    AlmacenConfig& c = r.cfg;
    const AlmacenConfig d{};
    static const nlohmann::json kVacio = nlohmann::json::object();
    const nlohmann::json* blk = &kVacio;
    if (root.is_object() && root.contains("almacen")) {
        if (root["almacen"].is_object()) {
            blk = &root["almacen"];
        } else {
            aviso << "[CONFIG-DEFAULT] almacen no es un objeto: se usan los defectos de todos sus campos" << std::endl;
        }
    }
    auto ausente = [&](const char* campo, const std::string& formato, const std::string& def) {
        aviso << "[CONFIG-DEFAULT] almacen." << campo << " ausente (" << formato << "): se usa " << def << std::endl;
        ++r.defectos;
        return std::string("DEFECTO: ausente");
    };
    auto malo = [&](const char* campo, const nlohmann::json& v, const std::string& formato, const std::string& def) {
        aviso << "[CONFIG-DEFAULT] almacen." << campo << "=" << v.dump() << " mal formado (" << formato << "): se usa "
              << def << std::endl;
        ++r.defectos;
        return std::string("DEFECTO: mal formado");
    };

    std::string o_modo = "JSON";
    if (!blk->contains("modo")) {
        o_modo = ausente("modo", "\"etcd\" o \"memoria\"", d.modo);
    } else {
        const auto& v = (*blk)["modo"];
        if (v.is_string() && (v.get<std::string>() == "etcd" || v.get<std::string>() == "memoria")) {
            c.modo = v.get<std::string>();
        } else {
            o_modo = malo("modo", v, "\"etcd\" o \"memoria\"; una errata nunca rebaja a memoria", d.modo);
        }
    }
    // [ETCD-ALMACEN-FATAL-D315] campos del despliegue: sin defecto en modo etcd (fatal); en modo memoria no se usan y
    // solo se avisa
    const bool etcd = c.modo == "etcd";
    auto fatal = [&](const std::string& campo, const std::string& que, const std::string& formato) {
        std::string m = "almacen.";
        m += campo;
        m += ' ';
        m += que;
        m += " (";
        m += formato;
        m += ")";
        if (etcd) {
            r.fatales.push_back(m);
            aviso << "[ETCD-ALMACEN-FATAL] " << m << ": sin defecto (lo pone el inventario del despliegue); no se arranca"
                  << std::endl;
        } else {
            aviso << "[CONFIG-DEFAULT] " << m << ": no se usa en modo memoria" << std::endl;
            ++r.defectos;
        }
        return std::string(etcd ? "FATAL: " : "SIN USO: ") + que;
    };

    std::string o_ep = "JSON";
    {
        const std::string fmt = "lista de 1 a 7 \"https://IPv4:puerto\", sin repetir";
        if (!blk->contains("endpoints")) {
            o_ep = fatal("endpoints", "ausente", fmt);
        } else {
            const auto& v = (*blk)["endpoints"];
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
                c.endpoints = lista;
            } else {
                o_ep = fatal("endpoints", "mal formado: " + v.dump(), fmt);
            }
        }
    }

    auto ruta = [&](const char* clave, std::string& out) -> std::string {
        const std::string fmt = "ruta absoluta, sin caracteres de control, hasta 4096";
        if (!blk->contains(clave)) return fatal(clave, "ausente", fmt);
        const auto& v = (*blk)[clave];
        if (!v.is_string() || !detalle_almacen::ruta_ok(v.get<std::string>()))
            return fatal(clave, "mal formado: " + v.dump(), fmt);
        out = v.get<std::string>();
        return "JSON";
    };
    const std::string o_ca = ruta("ca_file", c.ca_file);
    const std::string o_cert = ruta("cert_file", c.cert_file);
    const std::string o_key = ruta("key_file", c.key_file);

    std::string o_pre = "JSON";
    {
        const std::string fmt = "empieza y acaba en /, [a-z0-9-/], hasta 64, sin //";
        if (!blk->contains("prefijo")) {
            o_pre = fatal("prefijo", "ausente", fmt);
        } else {
            const auto& v = (*blk)["prefijo"];
            if (v.is_string() && detalle_almacen::prefijo_ok(v.get<std::string>())) {
                c.prefijo = v.get<std::string>();
            } else {
                o_pre = fatal("prefijo", "mal formado: " + v.dump(), fmt);
            }
        }
    }

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
    const std::string o_av = entero("aviso_intervalo_s", d.aviso_intervalo_s, 10, 3600, c.aviso_intervalo_s);
    const std::string o_rx = entero("reconexion_max_ms", d.reconexion_max_ms, 100, 60000, c.reconexion_max_ms);

    info << "[ETCD-ALMACEN] almacen.modo=" << c.modo << " (" << o_modo << ") almacen.endpoints="
         << nlohmann::json(c.endpoints).dump() << " (" << o_ep << ") almacen.ca_file=" << c.ca_file << " (" << o_ca
         << ") almacen.cert_file=" << c.cert_file << " (" << o_cert << ") almacen.key_file=" << c.key_file << " ("
         << o_key << ") almacen.prefijo=" << c.prefijo << " (" << o_pre << ") almacen.timeout_ms=" << c.timeout_ms
         << " (" << o_to << ") almacen.aviso_intervalo_s=" << c.aviso_intervalo_s << " (" << o_av
         << ") almacen.reconexion_max_ms=" << c.reconexion_max_ms << " (" << o_rx << ")" << std::endl;
    return r;
}

}  // namespace argus::etcdcfg

namespace argus::almacen {

enum class Estado { Ok, NoEncontrado, NoDisponible };

inline const char* texto(Estado e) {
    switch (e) {
        case Estado::Ok: return "ok";
        case Estado::NoEncontrado: return "no encontrado";
        case Estado::NoDisponible: return "no disponible";
    }
    return "?";
}

// Claves relativas al prefijo ("registro/sniffer"); cada implementación antepone su prefijo.
class IRegistryStore {
public:
    virtual ~IRegistryStore() = default;
    virtual Estado poner(const std::string& clave, const std::string& valor) = 0;
    virtual Estado leer(const std::string& clave, std::string& valor) = 0;
    virtual Estado borrar(const std::string& clave) = 0;  // borrar algo que no existe = Ok (idempotente)
    // Todas las claves que empiezan por subprefijo ("registro/"), con la clave relativa completa.
    virtual Estado listar(const std::string& subprefijo, std::map<std::string, std::string>& out) = 0;
    virtual std::string descripcion() const = 0;
    virtual std::string ultimo_error() const = 0;
};

class MemoriaRegistryStore : public IRegistryStore {
public:
    Estado poner(const std::string& clave, const std::string& valor) override {
        std::lock_guard<std::mutex> lk(m_);
        if (caido_) return Estado::NoDisponible;
        datos_[clave] = valor;
        return Estado::Ok;
    }
    Estado leer(const std::string& clave, std::string& valor) override {
        std::lock_guard<std::mutex> lk(m_);
        if (caido_) return Estado::NoDisponible;
        auto it = datos_.find(clave);
        if (it == datos_.end()) return Estado::NoEncontrado;
        valor = it->second;
        return Estado::Ok;
    }
    Estado borrar(const std::string& clave) override {
        std::lock_guard<std::mutex> lk(m_);
        if (caido_) return Estado::NoDisponible;
        datos_.erase(clave);
        return Estado::Ok;
    }
    Estado listar(const std::string& subprefijo, std::map<std::string, std::string>& out) override {
        std::lock_guard<std::mutex> lk(m_);
        if (caido_) return Estado::NoDisponible;
        out.clear();
        for (auto it = datos_.lower_bound(subprefijo); it != datos_.end() && it->first.rfind(subprefijo, 0) == 0; ++it)
            out.insert(*it);
        return Estado::Ok;
    }
    std::string descripcion() const override { return "memoria (SIN persistencia: transición o tests)"; }
    std::string ultimo_error() const override { return caido_ ? "simulado caído" : ""; }
    // Solo para tests: simular un etcd caído
    void simular_caido(bool c) {
        std::lock_guard<std::mutex> lk(m_);
        caido_ = c;
    }

private:
    std::mutex m_;
    std::map<std::string, std::string> datos_;
    bool caido_ = false;
};

}  // namespace argus::almacen
