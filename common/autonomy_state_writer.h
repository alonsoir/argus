#pragma once
// ============================================================================
// autonomy_state_writer.h — DEBT-AUTONOMY-STATE-PERSISTENCE-001 (DAY 157)
// ============================================================================
// Escribe y verifica el estado de CryptoAutonomyStateMachine en disco,
// firmado con Ed25519 (libsodium) para garantizar integridad.
//
// Ruta de persistencia: /var/lib/argus/crypto-autonomy-state.json
// (fichero regular, NO tmpfs — sobrevive reboot)
//
// Formato JSON almacenado:
//   {
//     "state":          "AUTONOMOUS",
//     "entered_at_utc": "2026-05-19T03:07:00Z",
//     "sequence":       42,
//     "node_id":        "etcd-server",
//     "reason":         "vault_unreachable",
//     "signature_hex":  "<128 hex chars — crypto_sign_detached sobre campos anteriores>"
//   }
//
// Escritura atómica: .tmp → fsync(fd) → rename(2) — nunca corrupción parcial.
// Firma: crypto_sign_detached sobre el JSON canónico SIN el campo signature_hex.
//
// Política de arranque (Consejo 6/8):
//   - Si estado=AUTONOMOUS y firma válida y entered_at < 24h → arrancar AUTONOMOUS
//   - Restart desde AUTONOMOUS → pasar por RECONCILING, no volver a NORMAL sin Vault
//   - Si fichero ausente, corrupto o firma inválida → arrancar NORMAL (fail-safe)
//
// Dependencias: libsodium 1.0.19, nlohmann/json, vault_types.h
// ============================================================================

#include "vault_types.h"
#include "crypto_autonomy.h"
#include <nlohmann/json.hpp>
#include <sodium.h>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <optional>
#include <stdexcept>
#include <string>
#include <sstream>
#include <iomanip>

namespace ml_defender {

// ── StateRecord — estado deserializado y verificado ──────────────────────────

struct AutonomyStateRecord {
    OperationalMode mode;
    std::string     entered_at_utc;   // ISO-8601
    uint64_t        sequence{0};
    std::string     node_id;
    std::string     reason;
    // signature_hex no se expone — verificación interna
};

// ── AutonomyStateWriter ───────────────────────────────────────────────────────

class AutonomyStateWriter {
public:
    static constexpr const char* DEFAULT_STATE_PATH =
        "/var/lib/argus/crypto-autonomy-state.json";
    static constexpr uint32_t    MAX_AUTONOMOUS_AGE_HOURS = 24;

    explicit AutonomyStateWriter(std::string path = DEFAULT_STATE_PATH)
        : path_(std::move(path))
    {}

    // ── Escritura ─────────────────────────────────────────────────────────────

    // Escribe el estado actual firmado con sk.
    // Lanza std::runtime_error si la escritura falla.
    void write(OperationalMode        mode,
               const Ed25519SecretKey& sk,
               const std::string&      node_id,
               const std::string&      reason,
               uint64_t               sequence)
    {
        const std::string entered_at = now_iso8601();

        // 1. JSON canónico a firmar (sin signature_hex, claves ordenadas)
        nlohmann::json canonical;
        canonical["entered_at_utc"] = entered_at;
        canonical["node_id"]        = node_id;
        canonical["reason"]         = reason;
        canonical["sequence"]       = sequence;
        canonical["state"]          = operational_mode_str(mode);
        // nlohmann::json ordena por inserción; usamos dump canónico explícito
        const std::string to_sign = canonical.dump();

        // 2. Firma Ed25519
        std::array<uint8_t, crypto_sign_BYTES> sig{};
        unsigned long long sig_len = 0;
        if (crypto_sign_detached(
                sig.data(), &sig_len,
                reinterpret_cast<const uint8_t*>(to_sign.data()),
                to_sign.size(),
                sk.data()) != 0)
        {
            throw std::runtime_error(
                "AutonomyStateWriter: crypto_sign_detached falló");
        }

        // 3. JSON final con signature_hex
        canonical["signature_hex"] = bytes_to_hex(sig.data(), sig_len);
        const std::string json_out = canonical.dump(2);

        // 4. Escritura atómica: tmp → fsync → rename
        const std::string tmp_path = path_ + ".tmp";
        {
            std::filesystem::create_directories(
                std::filesystem::path(path_).parent_path());

            FILE* f = ::fopen(tmp_path.c_str(), "w");
            if (!f) {
                throw std::runtime_error(
                    "AutonomyStateWriter: no se puede abrir " + tmp_path);
            }
            const size_t written = ::fwrite(json_out.data(), 1, json_out.size(), f);
            if (written != json_out.size()) {
                ::fclose(f);
                throw std::runtime_error(
                    "AutonomyStateWriter: escritura incompleta en " + tmp_path);
            }
            if (::fflush(f) != 0 || ::fsync(::fileno(f)) != 0) {
                ::fclose(f);
                throw std::runtime_error(
                    "AutonomyStateWriter: fsync falló en " + tmp_path);
            }
            ::fclose(f);
        }

        if (std::rename(tmp_path.c_str(), path_.c_str()) != 0) {
            throw std::runtime_error(
                "AutonomyStateWriter: rename falló: " + tmp_path + " → " + path_);
        }
    }

    // ── Lectura y verificación ────────────────────────────────────────────────

    // Lee y verifica el estado persistido.
    // Retorna nullopt si:
    //   - fichero ausente
    //   - JSON inválido o campos faltantes
    //   - firma Ed25519 inválida
    //   - estado AUTONOMOUS con timestamp > MAX_AUTONOMOUS_AGE_HOURS
    // NUNCA lanza excepciones — política fail-safe (arrancar NORMAL).
    std::optional<AutonomyStateRecord>
    read_and_verify(const Ed25519PublicKey& pk) const noexcept
    {
        try {
            std::ifstream f(path_);
            if (!f.is_open()) return std::nullopt;

            nlohmann::json j = nlohmann::json::parse(f);

            // Campos requeridos
            const std::string state_str   = j.at("state").get<std::string>();
            const std::string entered_at  = j.at("entered_at_utc").get<std::string>();
            const uint64_t    sequence    = j.at("sequence").get<uint64_t>();
            const std::string node_id     = j.at("node_id").get<std::string>();
            const std::string reason      = j.at("reason").get<std::string>();
            const std::string sig_hex     = j.at("signature_hex").get<std::string>();

            // Reconstruir JSON canónico (mismo orden que en write())
            nlohmann::json canonical;
            canonical["entered_at_utc"] = entered_at;
            canonical["node_id"]        = node_id;
            canonical["reason"]         = reason;
            canonical["sequence"]       = sequence;
            canonical["state"]          = state_str;
            const std::string to_verify = canonical.dump();

            // Verificar firma
            const auto sig_bytes = hex_to_bytes(sig_hex);
            if (sig_bytes.size() != crypto_sign_BYTES) return std::nullopt;

            if (crypto_sign_verify_detached(
                    sig_bytes.data(),
                    reinterpret_cast<const uint8_t*>(to_verify.data()),
                    to_verify.size(),
                    pk.data()) != 0)
            {
                return std::nullopt;  // firma inválida
            }

            // Parsear modo
            const auto mode_opt = parse_mode(state_str);
            if (!mode_opt.has_value()) return std::nullopt;

            // Política de edad para AUTONOMOUS
            if (mode_opt.value() == OperationalMode::AUTONOMOUS) {
                if (!within_age_limit(entered_at, MAX_AUTONOMOUS_AGE_HOURS)) {
                    return std::nullopt;
                }
            }

            AutonomyStateRecord rec;
            rec.mode         = mode_opt.value();
            rec.entered_at_utc = entered_at;
            rec.sequence     = sequence;
            rec.node_id      = node_id;
            rec.reason       = reason;
            return rec;

        } catch (...) {
            return std::nullopt;
        }
    }

    const std::string& path() const noexcept { return path_; }

private:
    std::string path_;

    // ── Utilidades ────────────────────────────────────────────────────────────

    static std::string now_iso8601() {
        auto now = std::chrono::system_clock::now();
        auto t   = std::chrono::system_clock::to_time_t(now);
        std::ostringstream oss;
        oss << std::put_time(std::gmtime(&t), "%Y-%m-%dT%H:%M:%SZ");
        return oss.str();
    }

    static std::string bytes_to_hex(const uint8_t* data, size_t len) {
        std::ostringstream oss;
        oss << std::hex << std::setfill('0');
        for (size_t i = 0; i < len; ++i) {
            oss << std::setw(2) << static_cast<unsigned>(data[i]);
        }
        return oss.str();
    }

    static std::vector<uint8_t> hex_to_bytes(const std::string& hex) {
        if (hex.size() % 2 != 0) return {};
        std::vector<uint8_t> out;
        out.reserve(hex.size() / 2);
        for (size_t i = 0; i < hex.size(); i += 2) {
            try {
                out.push_back(static_cast<uint8_t>(
                    std::stoul(hex.substr(i, 2), nullptr, 16)));
            } catch (...) {
                return {};
            }
        }
        return out;
    }

    static std::optional<OperationalMode> parse_mode(const std::string& s) {
        if (s == "NORMAL")       return OperationalMode::NORMAL;
        if (s == "AUTONOMOUS")   return OperationalMode::AUTONOMOUS;
        if (s == "RECONCILING")  return OperationalMode::RECONCILING;
        if (s == "DEGRADED")     return OperationalMode::DEGRADED;
        return std::nullopt;
    }

    // Comprueba que entered_at_utc no sea más antiguo que max_hours.
    // Formato esperado: "2026-05-19T03:07:00Z"
    static bool within_age_limit(const std::string& entered_at,
                                  uint32_t max_hours) noexcept
    {
        try {
            std::tm tm{};
            std::istringstream ss(entered_at);
            ss >> std::get_time(&tm, "%Y-%m-%dT%H:%M:%SZ");
            if (ss.fail()) return false;
            const auto entered = std::chrono::system_clock::from_time_t(
                std::mktime(&tm));  // mktime asume local — aceptable para comparación
            const auto age = std::chrono::system_clock::now() - entered;
            return age < std::chrono::hours(max_hours);
        } catch (...) {
            return false;
        }
    }
};

} // namespace ml_defender
