#pragma once
// TokenValidator.hpp — aRGus NDR Enterprise Token Validator
// Header-only. Depende únicamente de libsodium (ya en el proyecto).
// Uso: TokenValidator::validate_or_abort("/etc/argus/enterprise.token",
//                                        pubkey_bytes, {"vault_crypto"});

#include <array>
#include <chrono>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include <sodium.h>

// JSON mínimo sin dependencias externas — solo para este validator.
// En el futuro puede migrarse a nlohmann/json si ya está en el proyecto.
namespace argus::enterprise {

// base64 decode mínimo usando libsodium
inline std::vector<uint8_t> b64_decode(const std::string &s) {
    std::vector<uint8_t> out(s.size());  // upper bound
    size_t out_len = 0;
    if (sodium_base642bin(out.data(), out.size(),
                          s.c_str(), s.size(),
                          nullptr, &out_len,
                          nullptr, sodium_base64_VARIANT_ORIGINAL) != 0) {
        throw std::runtime_error("base64 decode failed");
    }
    out.resize(out_len);
    return out;
}

// Extrae el valor de una clave string en JSON plano (sin anidamiento).
inline std::string json_get_string(const std::string &json, const std::string &key) {
    std::string search = "\"" + key + "\":\"";
    auto pos = json.find(search);
    if (pos == std::string::npos) throw std::runtime_error("key not found: " + key);
    pos += search.size();
    auto end = json.find('"', pos);
    if (end == std::string::npos) throw std::runtime_error("malformed json for: " + key);
    return json.substr(pos, end - pos);
}

// Extrae array de strings de una clave JSON plana.
inline std::set<std::string> json_get_string_array(const std::string &json,
                                                     const std::string &key) {
    std::string search = "\"" + key + "\":[";
    auto pos = json.find(search);
    if (pos == std::string::npos) throw std::runtime_error("key not found: " + key);
    pos += search.size();
    auto end = json.find(']', pos);
    std::string raw = json.substr(pos, end - pos);
    std::set<std::string> result;
    std::stringstream ss(raw);
    std::string item;
    while (std::getline(ss, item, ',')) {
        // strip quotes and whitespace
        auto s = item.find('"');
        auto e = item.rfind('"');
        if (s != std::string::npos && e != s)
            result.insert(item.substr(s + 1, e - s - 1));
    }
    return result;
}

struct TokenValidator {
    // pubkey_hex: clave pública Ed25519 en hex (32 bytes = 64 chars hex)
    // required_features: features que este componente necesita
    static void validate_or_abort(
        const std::string &token_path,
        const std::string &pubkey_hex,
        const std::set<std::string> &required_features)
    {
        if (sodium_init() < 0) {
            fatal("libsodium init failed");
        }

        // Leer token
        std::ifstream f(token_path);
        if (!f.is_open()) {
            fatal("Enterprise token not found: " + token_path +
                  "\n  Configure enterprise_token_path in argus.conf"
                  "\n  or set crypto_provider=seed_file for OSS mode.");
        }
        std::string token_json((std::istreambuf_iterator<char>(f)),
                                std::istreambuf_iterator<char>());

        // Extraer payload y signature
        std::string payload_b64, sig_b64;
        try {
            payload_b64 = json_get_string(token_json, "payload");
            sig_b64     = json_get_string(token_json, "signature");
        } catch (const std::exception &e) {
            fatal("Malformed enterprise token: " + std::string(e.what()));
        }

        auto payload_bytes = b64_decode(payload_b64);
        auto sig_bytes     = b64_decode(sig_b64);

        // Verificar firma Ed25519
        std::vector<uint8_t> pubkey(crypto_sign_PUBLICKEYBYTES);
        if (sodium_hex2bin(pubkey.data(), pubkey.size(),
                           pubkey_hex.c_str(), pubkey_hex.size(),
                           nullptr, nullptr, nullptr) != 0) {
            fatal("Invalid enterprise public key format");
        }

        if (sig_bytes.size() != crypto_sign_BYTES) {
            fatal("Enterprise token signature has wrong length");
        }

        if (crypto_sign_verify_detached(
                sig_bytes.data(),
                payload_bytes.data(), payload_bytes.size(),
                pubkey.data()) != 0) {
            fatal("Enterprise token signature verification FAILED."
                  "\n  The token may have been tampered with or was signed"
                  "\n  with a different key.");
        }

        // Verificar expiración
        std::string payload_str(payload_bytes.begin(), payload_bytes.end());
        std::string expires_at;
        try {
            expires_at = json_get_string(payload_str, "expires_at");
        } catch (...) {
            fatal("Enterprise token missing expires_at field");
        }

        // ISO 8601 básico: comparación lexicográfica es suficiente para UTC
        auto now_str = current_utc_iso8601();
        if (now_str > expires_at) {
            fatal("Enterprise token EXPIRED.\n  expired_at: " + expires_at +
                  "\n  now:        " + now_str +
                  "\n  Renew the token to continue using enterprise features.");
        }

        // Verificar features requeridas
        std::set<std::string> token_features;
        try {
            token_features = json_get_string_array(payload_str, "features");
        } catch (...) {
            fatal("Enterprise token missing features field");
        }

        for (const auto &f : required_features) {
            if (token_features.find(f) == token_features.end()) {
                fatal("Enterprise token does not include required feature: " + f +
                      "\n  Token features: " + join(token_features) +
                      "\n  Required: " + join(required_features));
            }
        }

        // Todo OK
        std::string instance_id;
        try { instance_id = json_get_string(payload_str, "instance_id"); }
        catch (...) { instance_id = "(unknown)"; }

        std::cout << "[ARGUS ENTERPRISE] Token validated OK\n"
                  << "  instance_id : " << instance_id << "\n"
                  << "  features    : " << join(token_features) << "\n"
                  << "  expires_at  : " << expires_at << "\n";
    }

private:
    [[noreturn]] static void fatal(const std::string &msg) {
        std::cerr << "\n[ARGUS FATAL] Enterprise token validation failed.\n"
                  << "  " << msg << "\n"
                  << "  System halted. Review your enterprise configuration.\n\n";
        std::abort();
    }

    static std::string join(const std::set<std::string> &s) {
        std::string r;
        for (const auto &x : s) { if (!r.empty()) r += ", "; r += x; }
        return r;
    }

    static std::string current_utc_iso8601() {
        auto now = std::chrono::system_clock::now();
        auto t   = std::chrono::system_clock::to_time_t(now);
        char buf[32];
        // formato: 2026-05-22T10:00:00+00:00
        std::strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%S+00:00", std::gmtime(&t));
        return buf;
    }
};

}  // namespace argus::enterprise
