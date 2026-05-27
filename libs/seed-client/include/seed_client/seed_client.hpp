#pragma once

#include <array>
#include <string>
#include <cstdint>

/**
 * @file seed_client.hpp
 * @brief Lector de material criptográfico base para ML Defender.
 *
 * SeedClient lee el seed.bin generado por tools/provision.sh y lo expone
 * como material de entrada para que CryptoTransport aplique HKDF antes
 * de cualquier operación criptográfica.
 *
 * ╔══════════════════════════════════════════════════════════════════════╗
 * ║  CONTRATO DE USO — LEER ANTES DE LLAMAR A seed()                   ║
 * ╠══════════════════════════════════════════════════════════════════════╣
 * ║  seed() devuelve 32 bytes de MATERIAL BASE, NO una clave simétrica. ║
 * ║                                                                      ║
 * ║  USO CORRECTO:                                                       ║
 * ║    auto raw = client.seed();                                         ║
 * ║    auto key = HKDF(raw, context="ml-defender:{component}:v1");      ║
 * ║    chacha20_encrypt(data, key);                                      ║
 * ║                                                                      ║
 * ║  USO INCORRECTO (NUNCA HACER):                                       ║
 * ║    chacha20_encrypt(data, client.seed());  // sin HKDF = INSEGURO    ║
 * ║                                                                      ║
 * ║  Sin HKDF: no hay forward secrecy. Un seed comprometido permite     ║
 * ║  descifrar todo el tráfico histórico del componente.                 ║
 * ╚══════════════════════════════════════════════════════════════════════╝
 *
 * Responsabilidades de SeedClient:
 *   ✅  Leer seed.bin del path indicado en identity.keys_dir del JSON
 *   ✅  Verificar que el fichero tiene exactamente 32 bytes
 *   ✅  Advertir si los permisos del fichero no son 0600
 *   ✅  Limpiar buffers temporales con explicit_bzero tras la copia
 *   ✅  Exponer component_id y keys_dir para trazabilidad
 *
 *   ❌  NO cifra, NO descifra, NO genera seeds, NO hace red
 *   ❌  NO aplica HKDF (responsabilidad de CryptoTransport)
 *   ❌  NO gestiona nonces (responsabilidad de CryptoTransport)
 *
 * ADR refs: ADR-013 PHASE 1, DEBT-CRYPTO-001, DEBT-CRYPTO-002
 * Ver: docs/adr/ADR-013-seed-client.md
 */

namespace ml_defender {

class SeedClient {
public:
    /**
     * @brief Construye un SeedClient a partir del JSON del componente.
     *
     * No lee el fichero en el constructor — llama a load() explícitamente.
     *
     * @param component_json_path  Path absoluto al JSON del componente
     *                             (p.ej. "/etc/ml-defender/sniffer/sniffer.json")
     */
    explicit SeedClient(const std::string& component_json_path);

    /**
     * @brief Destructor — limpia el seed de memoria con explicit_bzero.
     */
    ~SeedClient();

    // No copiable — el material criptográfico no debe duplicarse
    SeedClient(const SeedClient&)            = delete;
    SeedClient& operator=(const SeedClient&) = delete;

    // Movible
    SeedClient(SeedClient&&)            = default;
    SeedClient& operator=(SeedClient&&) = default;

    /**
     * @brief Carga el seed.bin desde disco.
     *
     * Parsea el JSON del componente, construye el path al seed.bin,
     * lee exactamente 32 bytes y los almacena en memoria.
     *
     * @throws std::runtime_error  Si el JSON no contiene identity.keys_dir
     * @throws std::runtime_error  Si seed.bin no existe o no es legible
     * @throws std::runtime_error  Si seed.bin no contiene exactamente 32 bytes
     */
    void load();

    /**
     * @brief Devuelve el material criptográfico base (32 bytes).
     *
     * @pre  is_loaded() == true
     *
     * @return Referencia constante al array de 32 bytes.
     *         IMPORTANTE: Es material base para HKDF, no una clave de uso directo.
     *         Ver contrato en la cabecera del fichero.
     *
     * @throws std::runtime_error  Si is_loaded() == false
     */
    [[nodiscard]] const std::array<uint8_t, 32>& seed() const;

    /**
     * @brief Indica si el seed ha sido cargado correctamente desde disco.
     */
    [[nodiscard]] bool is_loaded() const noexcept;

    /**
     * @brief Devuelve el component_id leído del JSON (p.ej. "sniffer").
     * @throws std::runtime_error  Si is_loaded() == false
     */
    [[nodiscard]] const std::string& component_id() const;

    /**
     * @brief Devuelve el directorio de claves leído del JSON.
     *        (p.ej. "/etc/ml-defender/sniffer/")
     * @throws std::runtime_error  Si is_loaded() == false
     */
    [[nodiscard]] const std::string& keys_dir() const;

private:
    /**
     * @brief Verifica que seed.bin tiene permisos 0600.
     *        Emite una advertencia por stderr si no los tiene (no lanza excepción).
     */
    void check_seed_permissions(const std::string& seed_path) const;

    std::string component_json_path_;
    std::string keys_dir_;
    std::string component_id_;
    std::array<uint8_t, 32> seed_{};
    bool loaded_ = false;
};

} // namespace ml_defender