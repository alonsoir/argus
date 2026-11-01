#include "etcd_server/component_registry.hpp"
#include <crypto_transport/contexts.hpp>
#include <iostream>

//etcd-server/src/component_registry.cpp

ComponentRegistry::ComponentRegistry(const std::string& config_path,
                                     std::unique_ptr<argus::almacen::IRegistryStore> almacen,
                                     int heartbeat_interval_seconds, int timeout_multiplier, int check_interval_seconds,
                                     int aviso_intervalo_s, bool modo_memoria) {
    try {
        // ADR-013 PHASE 2 — CryptoTransport via SeedClient (DAY 98); el JSON es el de -c/--config [ETCD-CONFIG-D312]
        seed_client_ = std::make_unique<ml_defender::SeedClient>(config_path);
        seed_client_->load();
        tx_ = std::make_unique<crypto_transport::CryptoTransport>(
            *seed_client_, ml_defender::crypto::CTX_ETCD_RX);
        rx_ = std::make_unique<crypto_transport::CryptoTransport>(
            *seed_client_, ml_defender::crypto::CTX_ETCD_TX);
        std::cout << "[REGISTRY] ComponentRegistry inicializado con CryptoTransport (HKDF-SHA256)" << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "[REGISTRY] ❌ Error inicializando CryptoTransport: " << e.what() << std::endl;
        throw;
    }
    // [ETCD-REGISTRO-D313] registro sobre el almacén; el monitor marca muertos (no borra) y para al instante
    registro_ = std::make_unique<argus::registro::RegistroComponentes>(
        std::move(almacen), heartbeat_interval_seconds, timeout_multiplier, check_interval_seconds, aviso_intervalo_s,
        modo_memoria);
    registro_->arrancar_monitor();
}

ComponentRegistry::~ComponentRegistry() {
    if (registro_) registro_->parar_monitor();
    std::cout << "[REGISTRY] ComponentRegistry destruido" << std::endl;
}

std::string ComponentRegistry::decrypt_data(const std::string& ciphertext) {
    if (!rx_) return ciphertext;
    try {
        // CryptoTransport lanza en MAC fail — no se necesita validate_ciphertext
        std::vector<uint8_t> cipher_bytes(ciphertext.begin(), ciphertext.end());
        auto plain_bytes = rx_->decrypt(cipher_bytes);
        std::string plaintext(plain_bytes.begin(), plain_bytes.end());
        std::cout << "[REGISTRY] 🔓 Datos descifrados (" << ciphertext.length()
                  << " bytes -> " << plaintext.length() << " bytes)" << std::endl;
        return plaintext;
    } catch (const std::exception& e) {
        std::cerr << "[REGISTRY] ❌ Error descifrando datos: " << e.what() << std::endl;
        throw;
    }
}

std::string ComponentRegistry::validate_configuration() {
    std::vector<std::string> nombres;
    bool desde_copia = false;
    registro_->listar(nombres, desde_copia);
    json result;
    result["status"] = "valid";
    result["components_registered"] = nombres.size();
    result["registro_desde_copia"] = desde_copia;
    result["almacen_disponible"] = registro_->almacen_disponible();
    result["encryption_seed_set"] = (seed_client_ != nullptr && seed_client_->is_loaded());
    json anomalias = json::array();
    if (nombres.empty()) anomalias.push_back("No hay componentes registrados");
    for (const auto& n : nombres) {
        json doc;
        if (registro_->leer_documento(n, doc) != argus::registro::Resultado::Ok) continue;
        if (!doc.contains("component")) anomalias.push_back("Componente " + n + " no tiene campo 'component'");
        if (!doc.contains("version")) anomalias.push_back("Componente " + n + " no tiene campo 'version'");
    }
    result["anomalies_detected"] = anomalias.size();
    result["anomalies"] = anomalias;
    return result.dump();
}
