// etcd-client/src/etcd_client.cpp
#include "etcd_client/etcd_client.hpp"
#include "transporte.hpp"  // [ETCD-CLIENTE-D316] HTTPS + lista de endpoints
#include <cstring>
#include <crypto_transport/contexts.hpp>
#include <nlohmann/json.hpp>
#include <iostream>
#include <mutex>
#include <condition_variable>  // [PARADA-INMEDIATA-D300]
#include <stdexcept>
#include <thread>
#include <openssl/hmac.h>
#include <openssl/evp.h>
#include <sstream>
#include <iomanip>
#include <atomic>
#include <chrono>
#include <ctime>
#include <filesystem>
#include <fstream>
// ADR-013 PHASE 2 — DAY 98: CryptoTransport via SeedClient (sustituye CryptoManager)
// DEPRECATED DAY 98 — crypto_manager.hpp: #include "crypto_transport/crypto_manager.hpp"
#include <seed_client/seed_client.hpp>
#include <crypto_transport/transport.hpp>
#include <lz4.h>

using json = nlohmann::json;


// Forward declarations of helper functions (component namespace)
// Note: http namespace is now fully declared in etcd_client.hpp
namespace etcd_client {

namespace component {
    std::string build_registration_payload(const Config& config);
    std::string build_heartbeat_payload(const Config& config);
    std::string build_unregister_payload(const Config& config);
    ComponentInfo parse_component_info(const std::string& json_str);
    std::vector<ComponentInfo> parse_component_list(const std::string& json_str);
}

} // namespace etcd_client

namespace etcd_client {
// ============================================================================

struct EtcdClient::Impl {
    Config config_;
    mutable std::mutex mutex_;  // service_paths_ y el cifrado de salida
    // ADR-013 PHASE 2 — DAY 98
    std::unique_ptr<ml_defender::SeedClient>           seed_client_;
    std::unique_ptr<crypto_transport::CryptoTransport> tx_;
    std::unique_ptr<crypto_transport::CryptoTransport> rx_;
    // Day 59: Service discovery paths from etcd-server
    ServicePaths service_paths_;
    Transporte transporte_;  // [ETCD-CLIENTE-D316]
    // [ETCD-CLIENTE-B1-D316] mantenedor: un hilo, un ritmo (heartbeat_interval_seconds, G1). Registrado: latido. Sin
    // servicio: intenta registrarse (o reanudar el latido si ya lo estaba). El proceso nunca espera ni sale por esto (G2).
    std::recursive_mutex est_m_;       // estado del mantenedor; lo usan el hilo y register/unregister_component
    std::atomic<bool> registrado_{false};
    bool registrado_antes_ = false;    // el etcd-server lo tuvo registrado: al volver se prueba el latido primero
    bool sin_servicio_ = false;
    std::time_t sin_servicio_desde_ = 0;
    int intentos_ = 0;
    std::string ruta_config_;          // G3: JSON con el que arrancó el proceso; se sube al (re)registrarse
    std::string tipo_;
    bool config_pendiente_ = false;
    std::thread mantenedor_;
    std::atomic<bool> en_marcha_{false};
    std::mutex hb_mtx_;                // [PARADA-INMEDIATA-D300] espera interrumpible
    std::condition_variable hb_cv_;

    // Constructor — ADR-013 PHASE 2 (DAY 98)
    explicit Impl(const Config& config)
        : config_(config), transporte_(config) {
        try {
            if (!config_.component_config_path.empty()) {
                seed_client_ = std::make_unique<ml_defender::SeedClient>(
                    config_.component_config_path);
                seed_client_->load();
                tx_ = std::make_unique<crypto_transport::CryptoTransport>(
                    *seed_client_, ml_defender::crypto::CTX_ETCD_TX);
                rx_ = std::make_unique<crypto_transport::CryptoTransport>(
                    *seed_client_, ml_defender::crypto::CTX_ETCD_RX);
                std::cout << "🔧 EtcdClient initialized with CryptoTransport (HKDF-SHA256): "
                          << config_.component_name << std::endl;
            } else {
                std::cerr << "⚠️  [etcd-client] component_config_path vacío — CryptoTransport no inicializado" << std::endl;
                std::cout << "🔧 EtcdClient initialized (no crypto): "
                          << config_.component_name << std::endl;
            }
        } catch (const std::exception& e) {
            std::cerr << "❌ [etcd-client] Error inicializando CryptoTransport: "
                      << e.what() << std::endl;
            throw;
        }
    }

    ~Impl() {
        parar_mantenedor();
        // Parada ordenada: se da de baja una vez si estaba registrado (un intento por dirección, sin esperar más)
        if (registrado_.exchange(false)) {
            auto r = transporte_.peticion("POST", "/unregister", component::build_unregister_payload(config_),
                                          "application/json", 0, 1, true);
            std::cout << "[ETCD-CLIENTE-BAJA] " << config_.component_name
                      << (r.exito ? ": dado de baja en el etcd-server" : ": no se pudo dar de baja (" + baja_error(r) + ")")
                      << std::endl;
        }
    }

    static std::string baja_error(const Respuesta& r) {
        return r.status ? "HTTP " + std::to_string(r.status) : "sin respuesta:" + r.error;
    }

    static std::string hora_utc(std::time_t t) {
        std::tm tm{};
        gmtime_r(&t, &tm);
        char b[32];
        std::strftime(b, sizeof b, "%Y-%m-%dT%H:%M:%SZ", &tm);
        return b;
    }

    void arrancar_mantenedor() {
        if (en_marcha_.exchange(true)) return;
        mantenedor_ = std::thread([this]() {
            while (en_marcha_) {
                try {
                    ciclo();
                } catch (const std::exception& e) {
                    std::cerr << "[ETCD-CLIENTE] " << config_.component_name << ": excepción en el mantenedor: "
                              << e.what() << std::endl;
                }
                std::unique_lock<std::mutex> lk(hb_mtx_);  // [PARADA-INMEDIATA-D300]
                if (hb_cv_.wait_for(lk, std::chrono::seconds(config_.heartbeat_interval_seconds),
                                    [this] { return !en_marcha_.load(); })) break;
            }
        });
    }

    void parar_mantenedor() {
        if (en_marcha_.exchange(false)) {
            { std::lock_guard<std::mutex> lk(hb_mtx_); }  // [PARADA-INMEDIATA-D300] sin despertar perdido
            hb_cv_.notify_all();
        }
        if (mantenedor_.joinable() && mantenedor_.get_id() != std::this_thread::get_id()) mantenedor_.join();
    }

    Respuesta latido(bool callado) {
        return transporte_.peticion("POST", "/v1/heartbeat/" + config_.component_name,
                                    component::build_heartbeat_payload(config_), "application/json", 0, 1, callado);
    }

    // POST /register; con éxito guarda las rutas de la respuesta y marca registrado
    Respuesta registrar(int intentos, bool callado) {
        auto r = transporte_.peticion("POST", "/register", component::build_registration_payload(config_),
                                      "application/json", 0, intentos, callado);
        if (!r.exito) return r;
        try {
            auto j = json::parse(r.body);
            if (j.contains("paths") && j["paths"].is_object()) {
                std::lock_guard<std::mutex> lk(mutex_);
                service_paths_.hmac_key = j["paths"].value("hmac_key", "");
                service_paths_.config = j["paths"].value("config", "");
            }
        } catch (const std::exception& e) {
            std::cerr << "[ETCD-CLIENTE] " << config_.component_name << ": respuesta de /register ilegible: " << e.what()
                      << std::endl;
        }
        registrado_ = true;
        registrado_antes_ = true;
        return r;
    }

    // G3: sube el JSON con el que arrancó el proceso; devuelve la descripción para el log
    std::string subir_config() {
        if (ruta_config_.empty()) { config_pendiente_ = false; return "sin config que subir"; }
        std::string motivo;
        nlohmann::json j;
        std::ifstream f(ruta_config_);
        if (!f.is_open()) {
            motivo = "no se puede abrir";
        } else {
            j = json::parse(f, nullptr, false);
            if (j.is_discarded() || !j.is_object()) motivo = "JSON ilegible";
        }
        if (motivo.empty()) {
            j["_registration"] = {{"timestamp", std::time(nullptr)}, {"component", config_.component_name},
                                  {"type", tipo_}, {"status", "active"}};
            const std::string texto = j.dump(2);
            if (put_config_impl(texto)) {
                config_pendiente_ = false;
                return "config subida: " + ruta_config_ + " (" + std::to_string(texto.size()) + " bytes)";
            }
            motivo = "PUT /v1/config/" + config_.component_name + " falló";
        }
        config_pendiente_ = true;
        std::cerr << "[ETCD-CLIENTE-CONFIG-NO-SUBIDA] " << config_.component_name << ": " << ruta_config_ << ": " << motivo
                  << "; se reintenta en el siguiente latido (" << config_.heartbeat_interval_seconds << " s)" << std::endl;
        return "config NO subida: " + ruta_config_ + " (" + motivo + ")";
    }

    void anotar_sin_servicio(const std::string& error) {
        const std::time_t ahora = std::time(nullptr);
        if (!sin_servicio_) {
            sin_servicio_ = true;
            sin_servicio_desde_ = ahora;
            intentos_ = 0;
        }
        ++intentos_;
        std::cerr << "[ETCD-CLIENTE-SIN-SERVICIO] " << config_.component_name << " sin etcd-server desde "
                  << hora_utc(sin_servicio_desde_) << " (" << (ahora - sin_servicio_desde_) << " s, intento " << intentos_
                  << "):" << error << " el componente sigue protegiendo; próximo intento en "
                  << config_.heartbeat_interval_seconds << " s" << std::endl;
    }

    std::string tras_sin_servicio() {
        if (!sin_servicio_) return "al primer intento";
        std::string t = "tras " + std::to_string(std::time(nullptr) - sin_servicio_desde_) + " s sin servicio (" +
                        std::to_string(intentos_) + " intentos)";
        sin_servicio_ = false;
        intentos_ = 0;
        return t;
    }

    void intentar_registro() {
        auto r = registrar(1, true);
        if (r.exito) {
            const std::string tras = tras_sin_servicio();
            const std::string cfg = subir_config();
            std::cout << "[ETCD-CLIENTE-REGISTRADO] " << config_.component_name << " en " << transporte_.direccion_actual()
                      << " " << tras << "; " << cfg << "; latido cada " << config_.heartbeat_interval_seconds << " s"
                      << std::endl;
            return;
        }
        anotar_sin_servicio(r.status ? " /register rechazado: HTTP " + std::to_string(r.status) + " " + r.body + ";"
                                     : r.error);
    }

    // Un paso del mantenedor (G1)
    void ciclo() {
        std::lock_guard<std::recursive_mutex> lk(est_m_);
        if (registrado_) {
            auto r = latido(true);
            if (r.exito) {
                if (config_pendiente_) subir_config();
                return;
            }
            registrado_ = false;
            if (r.status == 404) {
                std::cerr << "[ETCD-CLIENTE-REGISTRO-PERDIDO] " << config_.component_name
                          << ": el etcd-server no lo tiene registrado (404 al latido); se vuelve a registrar" << std::endl;
                registrado_antes_ = false;
                intentar_registro();
                return;
            }
            anotar_sin_servicio(r.status ? " latido: HTTP " + std::to_string(r.status) + ";" : r.error);
            return;
        }
        if (registrado_antes_) {  // el registro vive en el etcd real: al volver basta con latir
            auto r = latido(true);
            if (r.exito) {
                registrado_ = true;
                std::cout << "[ETCD-CLIENTE-REANUDADO] " << config_.component_name << " en "
                          << transporte_.direccion_actual() << " " << tras_sin_servicio()
                          << "; el registro se conservó: latido sin nuevo /register" << std::endl;
                if (config_pendiente_) subir_config();
                return;
            }
            if (r.status != 404) {
                anotar_sin_servicio(r.status ? " latido: HTTP " + std::to_string(r.status) + ";" : r.error);
                return;
            }
            std::cerr << "[ETCD-CLIENTE-REGISTRO-PERDIDO] " << config_.component_name
                      << ": el etcd-server vuelve sin su registro (404 al latido); se vuelve a registrar" << std::endl;
            registrado_antes_ = false;
        }
        intentar_registro();
    }

    // [ETCD-CLIENTE-B1-D316] cuerpo de put_config(); lo usa también el mantenedor al (re)registrarse (G3)
    bool put_config_impl(const std::string& json_config) {
        std::lock_guard<std::mutex> lock(mutex_);

        // 1. Validate JSON
        try {
            auto parsed = nlohmann::json::parse(json_config);
            std::cout << "✅ [etcd-client] JSON validated (" << json_config.size() << " bytes)" << std::endl;
            (void)parsed;
        } catch (const std::exception& e) {
            std::cerr << "❌ [etcd-client] Invalid JSON: " << e.what() << std::endl;
            return false;
        }

        try {
            // 2. Process data (compress + encrypt)
            size_t original_size = json_config.size();
            std::string processed_config = process_outgoing_data(json_config);

            // 3. Determine Content-Type
            std::string content_type = "application/json";
            if (config_.encryption_enabled || config_.compression_enabled) {
                content_type = "application/octet-stream";
            }

            // 3. Build path
            std::string path = "/v1/config/" + config_.component_name;

            std::cout << "📤 [etcd-client] Uploading config to "
                      << transporte_.direccion_actual() << path << std::endl;
            std::cout << "   Original: " << json_config.size()
                      << " -> Processed: " << processed_config.size() << " bytes" << std::endl;

            // 4. Send PUT request (9 parameters - original_size will use default = 0)
            auto response = transporte_.peticion("PUT", path, processed_config, content_type, original_size);

            // 5. Check response
            if (!response.exito) {
                std::cerr << "❌ [etcd-client] PUT request failed" << std::endl;
                return false;
            }

            if (response.status != 200 && response.status != 201) {
                std::cerr << "❌ [etcd-client] Server returned "
                          << response.status << ": " << response.body << std::endl;
                return false;
            }

            std::cout << "✅ [etcd-client] Config uploaded successfully!" << std::endl;
            return true;

        } catch (const std::exception& e) {
            std::cerr << "❌ [etcd-client] Exception in put_config(): " << e.what() << std::endl;
            return false;
        }
    }

	// Day 60: Apply encryption and compression to outgoing data
std::string process_outgoing_data(const std::string& data) {

    std::string processed = data;
    size_t original_size = data.size();

    // ADR-013 PHASE 2 — DAY 98: LZ4 directo + CryptoTransport
    // Step 1: Compress con LZ4 (si habilitado y supera umbral)
    if (config_.compression_enabled &&
        original_size > static_cast<size_t>(config_.compression_min_size)) {
        try {
            int max_compressed = LZ4_compressBound(static_cast<int>(original_size));
            std::vector<uint8_t> compressed(sizeof(uint32_t) + max_compressed);
            uint32_t orig_le = static_cast<uint32_t>(original_size);
            std::memcpy(compressed.data(), &orig_le, sizeof(orig_le));
            int compressed_size = LZ4_compress_default(
                data.data(),
                reinterpret_cast<char*>(compressed.data() + sizeof(uint32_t)),
                static_cast<int>(original_size),
                max_compressed
            );
            if (compressed_size > 0) {
                compressed.resize(sizeof(uint32_t) + compressed_size);
                processed.assign(compressed.begin(), compressed.end());
                std::cout << "📦 Compressed: " << original_size << " → "
                          << processed.size() << " bytes" << std::endl;
            } else {
                std::cerr << "⚠️  LZ4 compression failed — enviando sin comprimir" << std::endl;
            }
        } catch (const std::exception& e) {
            std::cerr << "⚠️  Compression exception: " << e.what() << std::endl;
        }
    }

    // Step 2: Encrypt con CryptoTransport (si habilitado)
    if (config_.encryption_enabled && tx_) {
        try {
            std::vector<uint8_t> plain_bytes(processed.begin(), processed.end());
            auto cipher = tx_->encrypt(plain_bytes);
            std::cout << "🔒 Encrypted: " << cipher.size() << " bytes" << std::endl;
            return std::string(cipher.begin(), cipher.end());
        } catch (const std::exception& e) {
            std::cerr << "⚠️  Encryption failed: " << e.what() << std::endl;
            throw;
        }
    }

    return processed;
}
};

// ============================================================================
// EtcdClient - Public Interface Implementation
// ============================================================================

// Constructors
EtcdClient::EtcdClient(const Config& config)
    : pImpl(std::make_unique<Impl>(config)) {}

// Destructor
EtcdClient::~EtcdClient() = default;

// Move semantics
EtcdClient::EtcdClient(EtcdClient&&) noexcept = default;
EtcdClient& EtcdClient::operator=(EtcdClient&&) noexcept = default;

// Connection management. [ETCD-CLIENTE-B1-D316] connect() solo comprueba si algún etcd-server responde (/health);
// ya no condiciona las demás llamadas: cada petición va al transporte y falla como cualquiera sin respuesta.
bool EtcdClient::connect() {
    if (pImpl->config_.endpoints.empty() || pImpl->config_.ca_file.empty() || pImpl->config_.cert_file.empty() ||
        pImpl->config_.key_file.empty()) {
        std::cerr << "[ETCD-CLIENTE-FATAL] " << pImpl->config_.component_name
                  << ": faltan endpoints o rutas TLS (ver [ETCD-CLIENTE-FATAL] del bloque etcd del JSON)" << std::endl;
        return false;
    }
    std::cout << "🔗 Connecting to etcd-server (" << pImpl->config_.endpoints.size() << " direcciones, TLS): "
              << pImpl->config_.endpoints.front() << (pImpl->config_.endpoints.size() > 1 ? " ..." : "")
              << std::endl;
    auto response = pImpl->transporte_.peticion("GET", "/health");
    if (response.exito) {
        std::cout << "✅ Connected to etcd-server " << pImpl->transporte_.direccion_actual() << std::endl;
    } else {
        std::cerr << "❌ Failed to connect to etcd-server" << std::endl;
    }
    return response.exito;
}

// true = registrado y latiendo
bool EtcdClient::is_connected() const {
    return pImpl->registrado_.load();
}

// Para el mantenedor (sin darse de baja)
void EtcdClient::disconnect() {
    pImpl->parar_mantenedor();
    std::cout << "🔌 Mantenedor parado: " << pImpl->config_.component_name << std::endl;
}

// G1-G3: arranca el mantenedor sin esperar al etcd-server. ruta_config: el JSON con el que arrancó el proceso (se
// sube en cada registro); tipo: el campo _registration.type.
void EtcdClient::iniciar(const std::string& ruta_config_arranque, const std::string& tipo) {
    // [FW-CSV-CLAVE-B2-D316] ruta absoluta en el log y en la subida (el ml-detector arranca con ../config/... por defecto)
    std::string ruta_config = ruta_config_arranque;
    if (!ruta_config.empty()) {
        std::error_code ec;
        const auto abs = std::filesystem::weakly_canonical(std::filesystem::absolute(ruta_config, ec), ec);
        if (!ec) ruta_config = abs.string();
    }
    {
        std::lock_guard<std::recursive_mutex> lk(pImpl->est_m_);
        pImpl->ruta_config_ = ruta_config;
        pImpl->tipo_ = tipo;
    }
    std::cout << "[ETCD-CLIENTE-MANTENEDOR] " << pImpl->config_.component_name << ": registro y latido cada "
              << pImpl->config_.heartbeat_interval_seconds << " s contra " << pImpl->config_.endpoints.size()
              << " direcciones; config que se sube al registrarse: "
              << (ruta_config.empty() ? std::string("(ninguna)") : ruta_config)
              << ". Sin etcd-server el componente arranca y sigue protegiendo" << std::endl;
    pImpl->arrancar_mantenedor();
}

// Component discovery
// Registro inmediato (lo usan los inyectores y los tests): con éxito arranca el mantenedor (latidos), si heartbeat_enabled
bool EtcdClient::register_component() {
    Respuesta r;
    {
        std::lock_guard<std::recursive_mutex> lk(pImpl->est_m_);
        r = pImpl->registrar(0, false);
    }
    if (!r.exito) {
        std::cerr << "❌ Component registration failed" << std::endl;
        return false;
    }
    std::cout << "✅ Component registered: " << pImpl->config_.component_name << std::endl;
    if (pImpl->config_.heartbeat_enabled) pImpl->arrancar_mantenedor();
    return true;
}

bool EtcdClient::unregister_component() {
    pImpl->parar_mantenedor();
    std::lock_guard<std::recursive_mutex> lk(pImpl->est_m_);
    if (!pImpl->registrado_.exchange(false)) {
        std::cerr << "⚠️  Not registered, skipping unregister" << std::endl;
        return false;
    }
    pImpl->registrado_antes_ = false;
    auto response = pImpl->transporte_.peticion("POST", "/unregister", component::build_unregister_payload(pImpl->config_),
                                                "application/json", 0, 1);
    if (response.exito) {
        std::cout << "✅ Component unregistered: " << pImpl->config_.component_name << std::endl;
        return true;
    }
    std::cerr << "⚠️  Component unregister failed (non-critical)" << std::endl;
    return false;
}

bool EtcdClient::heartbeat() {
    return pImpl->latido(false).exito;
}

ComponentInfo EtcdClient::get_component_info(const std::string& name) {
    std::lock_guard<std::mutex> lock(pImpl->mutex_);

    ComponentInfo info;

    auto response = pImpl->transporte_.peticion("GET", "/component?name=" + name);

    if (response.exito) {
        return component::parse_component_info(response.body);
    }

    return info;
}

std::vector<ComponentInfo> EtcdClient::list_components() {
    std::lock_guard<std::mutex> lock(pImpl->mutex_);

    std::vector<ComponentInfo> components;

    auto response = pImpl->transporte_.peticion("GET", "/components");

    if (response.exito) {
        return component::parse_component_list(response.body);
    }

    return components;
}

// Config management
bool EtcdClient::put_config(const std::string& json_config) {
    return pImpl->put_config_impl(json_config);
}

// Encryption key management
void EtcdClient::set_encryption_key(const std::string& /*key*/) {
    // DEPRECATED DAY 98 — clave gestionada por SeedClient + HKDF (ADR-013)
    std::cerr << "⚠️  DEPRECATED: set_encryption_key() no-op — usar CryptoTransport via SeedClient" << std::endl;
}

bool EtcdClient::has_encryption_key() const {
    // DEPRECATED DAY 98 — retorna true si CryptoTransport está inicializado
    std::lock_guard<std::mutex> lock(pImpl->mutex_);
    return pImpl->tx_ != nullptr;
}

std::optional<std::vector<uint8_t>> EtcdClient::get_hmac_key(const std::string& key_path) {
    // [ETCD-CLIENTE-B1-D316] sin depender del registro: /secrets/{CN} solo exige el certificado con ese CN
    auto response = pImpl->transporte_.peticion("GET", key_path);
    if (!response.exito) return std::nullopt;

    try {
        auto j = json::parse(response.body);
        std::string key_hex;
        if (j.contains("key_hex") && j["key_hex"].is_string()) {
            key_hex = j["key_hex"].get<std::string>();
        } else if (j.contains("key") && j["key"].is_string()) {
            key_hex = j["key"].get<std::string>();
        } else {
            return std::nullopt;
        }
        return EtcdClient::hex_to_bytes(key_hex);
    } catch (...) { return std::nullopt; }
}

// [PROTEGIDOS-MANIFIESTO-D318] ADR-060 8e.3c
int EtcdClient::get_protegidos(std::string& cuerpo) {
    auto r = pImpl->transporte_.peticion("GET", "/v1/protegidos");
    cuerpo = r.status == 0 ? r.error : r.body;
    return r.status;
}

ServicePaths EtcdClient::get_service_paths() const {
    std::lock_guard<std::mutex> lock(pImpl->mutex_);
    return pImpl->service_paths_;
}
std::string EtcdClient::compute_hmac_sha256(const std::string& data, const std::vector<uint8_t>& key) {
    unsigned char hmac_result[EVP_MAX_MD_SIZE];
    unsigned int hmac_len;
    HMAC(EVP_sha256(), key.data(), key.size(),
         reinterpret_cast<const unsigned char*>(data.data()), data.size(),
         hmac_result, &hmac_len);
    return EtcdClient::bytes_to_hex(std::vector<uint8_t>(hmac_result, hmac_result + hmac_len));
}

bool EtcdClient::validate_hmac_sha256(const std::string& data, const std::string& hmac_hex,
                                       const std::vector<uint8_t>& key) {
    return compute_hmac_sha256(data, key) == hmac_hex;
}

std::string EtcdClient::bytes_to_hex(const std::vector<uint8_t>& data) {
    std::ostringstream oss;
    oss << std::hex << std::setfill('0');
    for (uint8_t byte : data) oss << std::setw(2) << static_cast<int>(byte);
    return oss.str();
}

std::vector<uint8_t> EtcdClient::hex_to_bytes(const std::string& hex_string) {
    if (hex_string.length() % 2 != 0) throw std::invalid_argument("Hex must have even length");
    std::vector<uint8_t> bytes;
    bytes.reserve(hex_string.length() / 2);
    for (size_t i = 0; i < hex_string.length(); i += 2) {
        bytes.push_back(static_cast<uint8_t>(std::stoi(hex_string.substr(i, 2), nullptr, 16)));
    }
    return bytes;
}

// [ETCD-CLIENTE-B1-D316] G2: aviso periódico de bloque etcd con fatales
struct AvisoBloqueFatal::Impl {
    std::string cn;
    size_t n;
    int intervalo;
    std::atomic<bool> vivo{true};
    std::mutex m;
    std::condition_variable cv;
    std::thread hilo;
};

AvisoBloqueFatal::AvisoBloqueFatal(std::string componente, size_t fatales, int intervalo_s)
    : pImpl(std::make_unique<Impl>()) {
    pImpl->cn = std::move(componente);
    pImpl->n = fatales;
    pImpl->intervalo = intervalo_s > 0 ? intervalo_s : 30;
    Impl* d = pImpl.get();
    d->hilo = std::thread([d]() {
        while (true) {
            std::cerr << "[ETCD-CLIENTE-FATAL] " << d->cn << ": bloque etcd con " << d->n
                      << " campos fatales (detalle al arrancar, arriba); el componente sigue sin etcd: sin registro y sin "
                         "clave HMAC hasta corregir el JSON y reiniciar. Próximo aviso en "
                      << d->intervalo << " s" << std::endl;
            std::unique_lock<std::mutex> lk(d->m);
            if (d->cv.wait_for(lk, std::chrono::seconds(d->intervalo), [d] { return !d->vivo.load(); })) break;
        }
    });
}

AvisoBloqueFatal::~AvisoBloqueFatal() {
    pImpl->vivo = false;
    { std::lock_guard<std::mutex> lk(pImpl->m); }
    pImpl->cv.notify_all();
    if (pImpl->hilo.joinable()) pImpl->hilo.join();
}

} // namespace etcd_client
