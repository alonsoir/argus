// etcd-server/src/etcd_registry_store.cpp — [ETCD-ALMACEN-D313]
#include "etcd_server/etcd_registry_store.hpp"
#include <etcd/SyncClient.hpp>
#include <chrono>

namespace argus::almacen {

namespace {
// etcdv3::ERROR_KEY_NOT_FOUND (100) en v0.15.3; la constante no está en las cabeceras públicas instaladas
constexpr int kNoEncontrado = 100;

std::string unir(const std::vector<std::string>& v) {
    std::string s;
    for (const auto& e : v) {
        if (!s.empty()) s += ',';
        s += e;
    }
    return s;
}
}  // namespace

EtcdRegistryStore::EtcdRegistryStore(const argus::etcdcfg::AlmacenConfig& cfg)
    : cfg_(cfg),
      prefijo_(cfg.prefijo),
      descripcion_("etcd " + unir(cfg.endpoints) + " (gRPC, TLS, prefijo " + cfg.prefijo + ")") {
    std::lock_guard<std::mutex> lk(cli_m_);
    crear_cliente();
}

// El constructor de SyncClient no conecta: el canal gRPC se abre en la primera llamada (v0.15.3: CreateCustomChannel)
void EtcdRegistryStore::crear_cliente() {
    cli_ = std::make_unique<etcd::SyncClient>(unir(cfg_.endpoints), cfg_.ca_file, cfg_.cert_file, cfg_.key_file, "");
    cli_->set_grpc_timeout(std::chrono::milliseconds(cfg_.timeout_ms));
    ultima_creacion_ = std::chrono::steady_clock::now();
    roto_ = false;
}

etcd::SyncClient& EtcdRegistryStore::cliente() {
    if (roto_ && std::chrono::steady_clock::now() - ultima_creacion_ >= std::chrono::milliseconds(cfg_.reconexion_max_ms))
        crear_cliente();
    return *cli_;
}

EtcdRegistryStore::~EtcdRegistryStore() = default;

std::string EtcdRegistryStore::ultimo_error() const {
    std::lock_guard<std::mutex> lk(m_);
    return ultimo_error_;
}

Estado EtcdRegistryStore::traducir(int codigo, const std::string& mensaje) {
    if (codigo == 0) return Estado::Ok;
    if (codigo == kNoEncontrado) return Estado::NoEncontrado;
    roto_ = true;  // bajo cli_m_ (lo llaman las operaciones)
    std::lock_guard<std::mutex> lk(m_);
    ultimo_error_ = "código " + std::to_string(codigo) + ": " + mensaje;
    return Estado::NoDisponible;
}

Estado EtcdRegistryStore::poner(const std::string& clave, const std::string& valor) {
    std::lock_guard<std::mutex> lk(cli_m_);
    try {
        auto r = cliente().put(prefijo_ + clave, valor);
        return traducir(r.error_code(), r.error_message());
    } catch (const std::exception& e) {
        return traducir(-1, e.what());
    }
}

Estado EtcdRegistryStore::leer(const std::string& clave, std::string& valor) {
    std::lock_guard<std::mutex> lk(cli_m_);
    try {
        auto r = cliente().get(prefijo_ + clave);
        const Estado e = traducir(r.error_code(), r.error_message());
        if (e == Estado::Ok) valor = r.value().as_string();
        return e;
    } catch (const std::exception& e) {
        return traducir(-1, e.what());
    }
}

Estado EtcdRegistryStore::borrar(const std::string& clave) {
    std::lock_guard<std::mutex> lk(cli_m_);
    try {
        auto r = cliente().rm(prefijo_ + clave);
        const Estado e = traducir(r.error_code(), r.error_message());
        return e == Estado::NoEncontrado ? Estado::Ok : e;  // idempotente
    } catch (const std::exception& e) {
        return traducir(-1, e.what());
    }
}

Estado EtcdRegistryStore::listar(const std::string& subprefijo, std::map<std::string, std::string>& out) {
    out.clear();
    std::lock_guard<std::mutex> lk(cli_m_);
    try {
        auto r = cliente().ls(prefijo_ + subprefijo);
        const Estado e = traducir(r.error_code(), r.error_message());
        if (e == Estado::NoEncontrado) return Estado::Ok;  // prefijo vacío
        if (e != Estado::Ok) return e;
        const auto& vals = r.values();
        for (size_t i = 0; i < vals.size(); ++i) {
            const std::string& k = vals[i].key();
            if (k.rfind(prefijo_, 0) == 0) out[k.substr(prefijo_.size())] = vals[i].as_string();
        }
        return Estado::Ok;
    } catch (const std::exception& e) {
        return traducir(-1, e.what());
    }
}

}  // namespace argus::almacen
