#pragma once
#include <memory>
#include <string>

// Forward declaration de la librería etcd-client
namespace etcd_client {
    class EtcdClient;
    struct Config;
}

namespace sniffer {

    /**
     * Adapter para etcd_client library
     * Patrón PIMPL para mantener API limpia y usar la biblioteca con encryption + compression
     */
    class EtcdClient {
    public:
        EtcdClient(const etcd_client::Config& base, const std::string& component_name);  // [ETCD-CLIENTE-D316]
        ~EtcdClient();

        // [ETCD-CLIENTE-B1-D316] Arranca el mantenedor de la librería y vuelve enseguida (G1-G3, DAY316). ruta_config: el
        // JSON con el que arrancó el sniffer (-c); se sube al etcd-server en cada registro.
        void arrancar(const std::string& ruta_config);

    private:
        struct Impl;
        std::unique_ptr<Impl> pImpl;
    };

} // namespace sniffer