#pragma once

#include <string>
#include <memory>
#include <vector>
#include <optional>
#include <functional>
#include <cstdint>
#include <nlohmann/json.hpp>  // ← Include completo, no forward declaration
#include <ostream>

namespace etcd_client {

// Component information structure
struct ComponentInfo {
    std::string name;
    std::string status;           // "active", "inactive", "unhealthy"
    std::string config_path;
    uint64_t last_heartbeat_ms;
    std::string metadata_json;    // Additional metadata as JSON string
};

// Service discovery paths (Day 59 - Service Discovery)
// etcd-server owns path topology and tells components where to find resources
// [ETCD-B4-D315] con el nombre completo del componente (= CN del certificado); sin crypto_token (el etcd-server no tiene
// ninguna ruta /crypto: era un dato muerto que además hacía falta para is_valid())
struct ServicePaths {
    std::string hmac_key;      // e.g., "/secrets/firewall-acl-agent"
    std::string config;        // e.g., "/config/firewall-acl-agent"

    // Helper to check if paths were received from etcd-server
    bool is_valid() const {
        return !hmac_key.empty() && !config.empty();
    }
};
// Configuración del cliente. [ETCD-CLIENTE-D316] DEBT-ETCD-HA-TLS-RAFT-001 paso 5: HTTPS con certificado de cliente y
// lista de direcciones del etcd-server. Los componentes no la rellenan a mano: la construye leer_bloque_etcd() desde
// el bloque "etcd" de su JSON (F1, un solo lector para los tres). Los defectos de aquí son los mismos que trae el JSON.
struct Config {
    // etcd-server: lista de https://<host>:<puerto> (1-7, sin repetir). Se usa la primera que responde; si una deja de
    // responder (o da 5xx) se pasa a la siguiente. Sin defecto: la rellena el aprovisionamiento.
    std::vector<std::string> endpoints;
    std::string ca_file;    // CA que firma el certificado del etcd-server
    std::string cert_file;  // certificado de cliente del componente (CN = nombre del componente)
    std::string key_file;   // su clave privada
    int connection_timeout_ms = 5000;  // [100, 60000]
    int retry_attempts = 3;            // intentos por dirección, [1, 10]
    int retry_interval_ms = 1000;      // espera entre intentos, [100, 60000]

    // Component identity
    std::string component_name;
    std::string component_config_path;

    // Encryption settings
    bool encryption_enabled = true;
    std::string encryption_algorithm = "chacha20-poly1305";

    // Compression settings
    bool compression_enabled = true;
    std::string compression_algorithm = "lz4";
    int compression_min_size = 256;

    // Heartbeat settings
    bool heartbeat_enabled = true;
    int heartbeat_interval_seconds = 30;  // [5, 300]
};

// [ETCD-CLIENTE-D316] F1: lector único del bloque "etcd" del JSON de un componente. El JSON es la ley: cada campo se
// registra en `log` con su valor y su origen ([CONFIG] ... (JSON) o [CONFIG-DEFAULT] ... con campo, formato y límites).
// endpoints, ca_file, cert_file y key_file no tienen defecto (los rellena el aprovisionamiento, D1): si faltan o están
// mal formados van a `fatales` con [ETCD-CLIENTE-FATAL] y el componente se queda sin etcd (qué hace entonces el proceso
// lo decide cada componente). Los campos que ya no se usan dan [CONFIG-OBSOLETO].
struct LecturaBloque {
    Config config;
    std::vector<std::string> fatales;  // una línea por campo fatal; vacía = se puede hablar con el etcd-server
    int defectos = 0;
    int obsoletos = 0;
};
LecturaBloque leer_bloque_etcd(const nlohmann::json& bloque, std::ostream& log);
// Igual, desde el texto JSON del bloque (para los componentes que leen su JSON con jsoncpp)
LecturaBloque leer_bloque_etcd(const std::string& bloque_json, std::ostream& log);

// [ETCD-CLIENTE-B1-D316] G2: un bloque etcd con campos fatales no para el proceso. Mientras viva este objeto se repite
// cada intervalo_s «[ETCD-CLIENTE-FATAL] <CN>: bloque etcd con <n> campos fatales ...; el componente sigue sin etcd».
// Igual en los tres componentes.
class AvisoBloqueFatal {
public:
    AvisoBloqueFatal(std::string componente, size_t fatales, int intervalo_s = 30);
    ~AvisoBloqueFatal();
    AvisoBloqueFatal(const AvisoBloqueFatal&) = delete;
    AvisoBloqueFatal& operator=(const AvisoBloqueFatal&) = delete;
private:
    struct Impl;
    std::unique_ptr<Impl> pImpl;
};

// Main EtcdClient class
class EtcdClient {
public:
    // Constructor with config object
    explicit EtcdClient(const Config& config);

    // Destructor
    ~EtcdClient();

    // Disable copy (avoid accidental copies)
    EtcdClient(const EtcdClient&) = delete;
    EtcdClient& operator=(const EtcdClient&) = delete;

    // Enable move (for efficiency)
    EtcdClient(EtcdClient&&) noexcept;
    EtcdClient& operator=(EtcdClient&&) noexcept;

    // ========================================================================
    // Connection Management
    // ========================================================================

    // [ETCD-CLIENTE-B1-D316] connect(): una comprobación de /health (ya no condiciona nada). is_connected(): registrado
    // y latiendo. disconnect(): para el mantenedor.
    bool connect();
    bool is_connected() const;
    void disconnect();
    // [ETCD-CLIENTE-B1-D316] G1-G3 (DAY316): arranca el hilo mantenedor y vuelve enseguida. Cada
    // heartbeat_interval_seconds: registrado, latido; sin servicio, intenta registrarse (o reanudar el latido si el
    // registro se conservó). En cada registro sube el JSON de ruta_config (el de arranque del proceso) con
    // _registration.type = tipo. Logs: [ETCD-CLIENTE-MANTENEDOR], -REGISTRADO, -SIN-SERVICIO, -REANUDADO,
    // -REGISTRO-PERDIDO, -CONFIG-NO-SUBIDA, -BAJA (al destruirse, si estaba registrado).
    void iniciar(const std::string& ruta_config, const std::string& tipo);

    // ========================================================================
    // Component Discovery & Registration
    // ========================================================================

    // Register this component with etcd-server
    bool register_component();

    // Unregister this component from etcd-server
    bool unregister_component();

    // Send heartbeat (called automatically if heartbeat_enabled)
    bool heartbeat();

    // [LATIDO-DATOS-D321] ADR-060 8e.4c (H-H): dato genérico que viaja en cada latido ("datos": {clave: valor}) y el
    // etcd-server guarda en latido/<CN>. Regla única (libs/latido/datos_latido.hpp): clave ^[a-z][a-z0-9_]{0,31}$,
    // valor entero en [0, 2^53 - 1], como mucho 8 claves. Si no vale, no se guarda, devuelve false y lo dice
    // [ETCD-CLIENTE-LATIDO-DATO]. Seguro entre hilos; O(datos). Un cambio de valor sale en el log una vez.
    bool poner_dato_latido(const std::string& clave, std::int64_t valor);

    // Get info about a component
    ComponentInfo get_component_info(const std::string& name);

    // List all registered components
    std::vector<ComponentInfo> list_components();

    // Get service paths (returned by etcd-server during registration)
    // Returns paths where this component should find HMAC keys, crypto tokens, etc.
    ServicePaths get_service_paths() const;

    // ========================================================================
    // Config Management
    // ========================================================================

    /**
     * Upload configuration to etcd-server
     * Compresses and encrypts the JSON before sending
     * @param json_config JSON configuration string
     * @return true if successful, false otherwise
     */
    bool put_config(const std::string& json_config);

    // ========================================================================
    // Encryption Key Management (handled automatically by library)
    // ========================================================================

    // Set encryption key manually (normally received from etcd-server)
    void set_encryption_key(const std::string& key);

    // Check if encryption key is available
    bool has_encryption_key() const;

    // ========================================================================
    // HMAC Utilities (Day 53 - Log Integrity)
    // ========================================================================

    /**
     * @brief Get HMAC key from etcd-server
     *
     * Retrieves an HMAC key from etcd-server's SecretsManager.
     * The key is returned as raw bytes for immediate use.
     *
     * @param key_path Path to key in etcd (e.g., "/secrets/ml-detector")
     * @return Key bytes if successful, nullopt if key not found or error
     *
     * Example:
     *   auto key = client.get_hmac_key("/secrets/ml-detector");
     *   if (key.has_value()) {
     *       // Use key for HMAC operations
     *   }
     */
    std::optional<std::vector<uint8_t>> get_hmac_key(const std::string& key_path);

    // [PROTEGIDOS-MANIFIESTO-D318] ADR-060 8e.3c: GET /v1/protegidos (mismo transporte mTLS y conmutación de direcciones).
    // Devuelve el status HTTP (0 = ningún etcd-server respondió) y, con 200, el sobre tal cual en cuerpo; si no, el
    // error o la respuesta del servidor. No interpreta nada: verifica el firewall.
    int get_protegidos(std::string& cuerpo);

    /**
     * @brief Compute HMAC-SHA256 over data
     *
     * Computes HMAC-SHA256 signature over the provided data using the given key.
     * The result is returned as a hex-encoded string for easy storage/transmission.
     *
     * @param data Data to sign (log line, message, etc.)
     * @param key HMAC key (32 bytes recommended for HMAC-SHA256)
     * @return HMAC as hex string (64 characters for SHA256)
     *
     * Example:
     *   std::string log_line = "2026-02-09 event data";
     *   std::string hmac = client.compute_hmac_sha256(log_line, key);
     *   // hmac = "a3f5c2d8e9b14f7c..." (64 hex chars)
     */
    std::string compute_hmac_sha256(const std::string& data,
                                    const std::vector<uint8_t>& key);

    /**
     * @brief Validate HMAC-SHA256 signature
     *
     * Validates that the provided HMAC matches the data using constant-time
     * comparison to prevent timing attacks.
     *
     * @param data Original data
     * @param hmac_hex Expected HMAC (hex-encoded string)
     * @param key HMAC key used to generate the signature
     * @return true if HMAC is valid, false if invalid or mismatch
     *
     * Example:
     *   if (client.validate_hmac_sha256(data, hmac, key)) {
     *       // HMAC valid - data is authentic
     *   } else {
     *       // HMAC invalid - data may be tampered
     *   }
     */
    bool validate_hmac_sha256(const std::string& data,
                             const std::string& hmac_hex,
                             const std::vector<uint8_t>& key);

    /**
     * @brief Convert bytes to hex string (utility)
     *
     * Converts raw bytes to hex-encoded string for storage/transmission.
     *
     * @param data Raw bytes
     * @return Hex-encoded string (lowercase)
     */
    static std::string bytes_to_hex(const std::vector<uint8_t>& data);

    /**
     * @brief Convert hex string to bytes (utility)
     *
     * Converts hex-encoded string back to raw bytes.
     *
     * @param hex_string Hex-encoded string
     * @return Raw bytes
     * @throws std::invalid_argument if hex string is invalid
     */
    static std::vector<uint8_t> hex_to_bytes(const std::string& hex_string);

private:
    // PIMPL idiom - implementation hidden
    struct Impl;
    std::unique_ptr<Impl> pImpl;
};

} // namespace etcd_client