#pragma once
// etcd-server/include/etcd_server/etcd_registry_store.hpp — [ETCD-ALMACEN-D313]
// IRegistryStore sobre el etcd real (gRPC con etcd-cpp-apiv3 v0.15.3, TLS y certificado de cliente; RBAC por CN en
// etcd: el usuario etcd-server solo lee/escribe bajo /argus/). La pasarela JSON de etcd 3.6 rechaza peticiones con
// certificado de cliente (medido DAY312): por eso gRPC. Varios endpoints separados por coma (PR2, HA).
#include "etcd_server/etcd_server_almacen.hpp"
#include <chrono>
#include <memory>
#include <mutex>
#include <string>

namespace etcd { class SyncClient; }

namespace argus::almacen {

class EtcdRegistryStore : public IRegistryStore {
public:
    explicit EtcdRegistryStore(const argus::etcdcfg::AlmacenConfig& cfg);
    ~EtcdRegistryStore() override;
    Estado poner(const std::string& clave, const std::string& valor) override;
    Estado leer(const std::string& clave, std::string& valor) override;
    Estado borrar(const std::string& clave) override;
    Estado listar(const std::string& subprefijo, std::map<std::string, std::string>& out) override;
    std::string descripcion() const override { return descripcion_; }
    std::string ultimo_error() const override;

private:
    Estado traducir(int codigo, const std::string& mensaje);
    // [D313B] Tras un NoDisponible, el siguiente intento crea un canal gRPC nuevo (como mucho uno cada
    // reconexion_max_ms). Medido DAY313 (gRPC 1.51, v0.15.3): un canal que ha fallado tarda ~30 s en volver a usar etcd
    // aunque etcd esté de vuelta, y los argumentos de backoff de reconexión no lo cambian; un cliente nuevo conecta en
    // 0,37 s.
    etcd::SyncClient& cliente();
    void crear_cliente();
    argus::etcdcfg::AlmacenConfig cfg_;
    std::unique_ptr<etcd::SyncClient> cli_;
    std::string prefijo_, descripcion_;
    mutable std::mutex m_;    // ultimo_error_
    std::mutex cli_m_;        // cli_, roto_, ultima_creacion_ (una operación a la vez)
    std::string ultimo_error_;
    bool roto_ = false;
    std::chrono::steady_clock::time_point ultima_creacion_{};
};

}  // namespace argus::almacen
