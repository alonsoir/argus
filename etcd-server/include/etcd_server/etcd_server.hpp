#include <mutex>
#include <string>
#pragma once

#include <memory>
#include <thread>
#include <atomic>
#include <unordered_map>
#include <vector>
#include "etcd_server/etcd_server_config.hpp"
#include "etcd_server/etcd_server_authz.hpp"
#include "etcd_server/etcd_server_almacen.hpp"

namespace httplib { class Server; }

// Forward declaration for SecretsManager
namespace etcd_server {
    class SecretsManager;
}

//etcd-server/include/etcd_server/etcd_server.hpp
class ComponentRegistry;

class EtcdServer {
private:
    std::unique_ptr<ComponentRegistry> component_registry_;
    etcd_server::SecretsManager* secrets_manager_ = nullptr;  // Non-owning pointer
    std::atomic<bool> running_{false};
    std::string host_;
    int port_;
    int heartbeat_interval_seconds_;
    std::thread server_thread_;
    // [ETCD-AUTHZ-D313] el servidor es miembro (antes, variable local de run_server(): stop() no podía pararlo)
    std::unique_ptr<httplib::Server> server_;
    argus::etcdcfg::TlsConfig tls_;
    std::vector<argus::etcdauthz::Regla> reglas_;

public:
    // [ETCD-CONFIG-D312] host, puerto y latidos salen de etcd-server.json (argus::etcdcfg, ya validados);
    // config_path es ese mismo JSON (SeedClient lee de él identity)
    // [ETCD-AUTHZ-D313] tls (modo mtls | http) y la tabla de autorización, del mismo JSON y ya validados
    // [ETCD-REGISTRO-D313] el almacén del registro (etcd real o memoria de transición) llega ya construido
    EtcdServer(const argus::etcdcfg::EtcdServerConfig& cfg, const argus::etcdcfg::TlsConfig& tls,
               std::vector<argus::etcdauthz::Regla> reglas, const argus::etcdcfg::AlmacenConfig& almacen_cfg,
               std::unique_ptr<argus::almacen::IRegistryStore> almacen, const std::string& config_path);
    ~EtcdServer();

    void set_secrets_manager(etcd_server::SecretsManager* manager) {
        secrets_manager_ = manager;
    }
    // [ETCD-AUTHZ-D313] crea el servidor (SSLServer con mTLS o, solo en transición, HTTP) y sus rutas.
    // Devuelve false si en modo mtls los certificados no se pueden cargar: sin TLS válido no se sirve.
    bool initialize();
    void start();
    void stop();
    bool is_running() const { return running_; }

    // Registro y latido en proceso del propio etcd-server ([ETCD-AUTHZ-D313]; false si el almacén no responde)
    bool register_component(const std::string& component_name, const std::string& config_json);
    bool update_heartbeat(const std::string& component_name);

    // Epoch management (ADR-045 v2 — DAY 164)
    struct EpochInfo {
        uint16_t    epoch_id{1};
        std::string not_before{"2026-01-01T00:00:00Z"};
        int64_t     revision{1};
    };
    bool        set_epoch(uint16_t epoch_id, const std::string& not_before);  // false si el almacén no responde
    EpochInfo   get_epoch() const;

private:
    void run_server();
    void configurar_rutas();
    EpochInfo           epoch_;
    mutable std::mutex  epoch_mutex_;
};