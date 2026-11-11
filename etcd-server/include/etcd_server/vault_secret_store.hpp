#pragma once
// etcd-server/include/etcd_server/vault_secret_store.hpp — [ETCD-CLAVES-D314]
// ISecretStore sobre Vault (kv v2, montaje con cas_required=true) por HTTPS con certificado de cliente (auth cert,
// rol almacen_claves.rol_login). Cliente propio con httplib::SSLClient (decisión V1 de Alonso, DAY314).
//   - Lista de direcciones: se empieza por la última que respondió; cada una se prueba reintentos_por_direccion veces
//     con espera creciente (espera_inicial_ms, doblando, hasta espera_max_ms); luego la siguiente. Agotada la lista:
//     no disponible (ultimo_error() trae el error de cada dirección) y desde entonces se falla rápido, sin red, hasta
//     que sondear() vuelve a encontrar una.
//   - Token: login con el certificado; se renueva al pasar la mitad de su vida o ante un 403 (una vez).
//   - Un 503 de Vault (sellado o en espera) cuenta como fallo de esa dirección: se pasa a la siguiente.
//   - Nunca escribe la clave en el log ni en ultimo_error().
#include "etcd_server/etcd_server_claves.hpp"
#include <chrono>
#include <mutex>
#include <ostream>
#include <string>
#include <vector>

namespace argus::claves {

class VaultSecretStore : public ISecretStore {
public:
    VaultSecretStore(const argus::etcdcfg::AlmacenClavesConfig& cfg, std::ostream& log);
    Estado leer(const std::string& ruta, nlohmann::json& datos, int& version) override;
    Estado escribir(const std::string& ruta, const nlohmann::json& datos, int cas, int& version_nueva) override;
    bool disponible() const override;
    bool sondear() override;
    std::string descripcion() const override { return descripcion_; }
    std::string ultimo_error() const override;

private:
    struct Respuesta {
        int status = 0;       // 0 = no hubo respuesta HTTP (conexión, TLS, timeout)
        std::string cuerpo;
        std::string error;    // texto del fallo de transporte
    };
    // Una petición a una dirección (sin reintentos)
    Respuesta pedir(size_t dir, const std::string& metodo, const std::string& ruta, const std::string& cuerpo,
                    bool con_token);
    bool login(size_t dir, std::string& error);
    // Recorre la lista con reintentos; devuelve la respuesta de Vault (status != 0) o status 0 si nadie respondió.
    // Reintenta también ante 5xx y 429; un 4xx es la respuesta (no se reintenta).
    Respuesta operar(const std::string& metodo, const std::string& ruta, const std::string& cuerpo);
    void marcar_caido(const std::string& detalle);

    argus::etcdcfg::AlmacenClavesConfig cfg_;
    std::ostream& log_;
    std::string descripcion_;
    struct Dir {
        std::string url, host;
        int puerto = 0;
    };
    std::vector<Dir> dirs_;

    mutable std::mutex m_;  // todo el estado: una operación a la vez
    size_t actual_ = 0;
    std::string token_;
    size_t token_dir_ = 0;
    std::chrono::steady_clock::time_point token_renovar_{};
    bool disponible_ = true;
    std::string ultimo_error_;
};

}  // namespace argus::claves
