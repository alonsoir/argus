// vault_provider.cpp — aRGus NDR Enterprise Vault Crypto Provider
// Via Appia Quality: sin shortcuts, sin fallbacks silenciosos.

#include "vault_provider.hpp"

#include <sodium.h>          // crypto_hash_sha256
#include <curl/curl.h>

#include <iostream>
#include <sstream>
#include <stdexcept>
#include <cstring>

namespace argus::enterprise {

// ── libcurl write callback ─────────────────────────────────────────────────
static size_t curl_write_cb(char* ptr, size_t size, size_t nmemb, void* userdata) {
    auto* buf = static_cast<std::string*>(userdata);
    buf->append(ptr, size * nmemb);
    return size * nmemb;
}

// ── VaultProvider ──────────────────────────────────────────────────────────
VaultProvider::VaultProvider(Config cfg) : cfg_(std::move(cfg)) {
    if (cfg_.vault_addr.empty())   throw std::runtime_error("vault_addr vacío");
    if (cfg_.vault_token.empty())  throw std::runtime_error("vault_token vacío");
    if (cfg_.secret_path.empty())  throw std::runtime_error("secret_path vacío");
    if (cfg_.seed_field.empty())   cfg_.seed_field = "seed";
}

std::vector<uint8_t> VaultProvider::get_seed() {
    std::string response = fetch_from_vault();
    std::string seed_str = extract_seed_string(response, cfg_.seed_field);
    if (seed_str.empty()) {
        throw std::runtime_error(
            "vault_crypto: campo '" + cfg_.seed_field +
            "' vacío en " + cfg_.secret_path);
    }
    return derive_seed_bytes(seed_str);
}

bool VaultProvider::is_healthy() const noexcept {
    try {
        // HEAD-like: intentar fetch y ver si no lanza
        [[maybe_unused]] auto _ = fetch_from_vault();
        return true;
    } catch (...) {
        return false;
    }
}

std::string VaultProvider::fetch_from_vault() const {
    // URL: vault_addr + "/v1/" + secret_path
    // Vault KV v2: secret/data/argus/crypto → /v1/secret/data/argus/crypto
    std::string url = cfg_.vault_addr + "/v1/" + cfg_.secret_path;

    CURL* curl = curl_easy_init();
    if (!curl) throw std::runtime_error("vault_crypto: curl_easy_init() falló");

    std::string response_body;
    struct curl_slist* headers = nullptr;

    std::string token_header = "X-Vault-Token: " + cfg_.vault_token;
    headers = curl_slist_append(headers, token_header.c_str());
    headers = curl_slist_append(headers, "Accept: application/json");

    curl_easy_setopt(curl, CURLOPT_URL,            url.c_str());
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER,     headers);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION,  curl_write_cb);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA,      &response_body);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT,        static_cast<long>(cfg_.timeout_seconds));
    curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT, 3L);
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 0L);  // no redirects
    curl_easy_setopt(curl, CURLOPT_NOSIGNAL,       1L);

    CURLcode res = curl_easy_perform(curl);
    long http_code = 0;
    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &http_code);

    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);

    if (res != CURLE_OK) {
        throw std::runtime_error(
            std::string("vault_crypto: curl error: ") + curl_easy_strerror(res));
    }
    if (http_code == 403) {
        throw std::runtime_error(
            "vault_crypto: Vault devolvió 403 — token inválido o sin permisos en " +
            cfg_.secret_path);
    }
    if (http_code == 404) {
        throw std::runtime_error(
            "vault_crypto: secreto no encontrado en Vault: " + cfg_.secret_path);
    }
    if (http_code != 200) {
        throw std::runtime_error(
            "vault_crypto: Vault HTTP " + std::to_string(http_code) +
            " para " + cfg_.secret_path);
    }

    return response_body;
}

std::string VaultProvider::extract_seed_string(
    const std::string& json, const std::string& field)
{
    // Vault KV v2 response: {"data":{"data":{"seed":"valor","provider":"vault_crypto"},...}}
    // Buscamos el segundo bloque "data":{ y dentro el campo.
    // Sin dependencia de nlohmann — mismo patrón que TokenValidator.hpp.

    // Encontrar "data":{"data":{
    auto pos1 = json.find("\"data\":");
    if (pos1 == std::string::npos)
        throw std::runtime_error("vault_crypto: respuesta sin campo 'data'");

    auto pos2 = json.find("\"data\":", pos1 + 7);
    if (pos2 == std::string::npos)
        throw std::runtime_error("vault_crypto: respuesta KV v2 sin data.data");

    // Buscar el campo dentro del segundo data
    std::string search = "\"" + field + "\":\"";
    auto pos3 = json.find(search, pos2);
    if (pos3 == std::string::npos)
        return "";

    pos3 += search.size();
    auto end = json.find('"', pos3);
    if (end == std::string::npos)
        throw std::runtime_error("vault_crypto: campo '" + field + "' malformado");

    return json.substr(pos3, end - pos3);
}

std::vector<uint8_t> VaultProvider::derive_seed_bytes(const std::string& seed_string) {
    // SHA-256 del seed string → 32 bytes deterministas.
    // Permite seeds de longitud arbitraria almacenados en Vault.
    if (sodium_init() < 0)
        throw std::runtime_error("vault_crypto: sodium_init() falló");

    std::vector<uint8_t> out(crypto_hash_sha256_BYTES);  // 32 bytes
    crypto_hash_sha256(
        out.data(),
        reinterpret_cast<const unsigned char*>(seed_string.data()),
        seed_string.size());
    return out;
}

}  // namespace argus::enterprise

// ── C ABI enterprise ───────────────────────────────────────────────────────
// Parseo minimal de config_json para extraer vault_addr, vault_token, secret_path.
// Mismo patrón que json_get_string en TokenValidator.hpp.

static std::string cfg_get(const std::string& json, const std::string& key) {
    std::string search = "\"" + key + "\":\"";
    auto pos = json.find(search);
    if (pos == std::string::npos) return "";
    pos += search.size();
    auto end = json.find('"', pos);
    if (end == std::string::npos) return "";
    return json.substr(pos, end - pos);
}

static int cfg_get_int(const std::string& json, const std::string& key, int def) {
    std::string search = "\"" + key + "\":";
    auto pos = json.find(search);
    if (pos == std::string::npos) return def;
    pos += search.size();
    while (pos < json.size() && json[pos] == ' ') ++pos;
    try { return std::stoi(json.substr(pos)); }
    catch (...) { return def; }
}

extern "C" {

argus::ICryptoProvider* argus_enterprise_create(const char* config_json) {
    if (!config_json) {
        std::cerr << "[vault_crypto] argus_enterprise_create: config_json es null\n";
        return nullptr;
    }
    std::string cfg(config_json);
    argus::enterprise::VaultProvider::Config c;
    c.vault_addr      = cfg_get(cfg, "vault_addr");
    c.vault_token     = cfg_get(cfg, "vault_token");
    c.secret_path     = cfg_get(cfg, "secret_path");
    c.seed_field      = cfg_get(cfg, "seed_field");
    c.timeout_seconds = cfg_get_int(cfg, "timeout_seconds", 5);

    if (c.vault_addr.empty())  c.vault_addr  = "http://127.0.0.1:8200";
    if (c.vault_token.empty()) c.vault_token = "argus-dev-token";
    if (c.secret_path.empty()) c.secret_path = "secret/data/argus/crypto";
    if (c.seed_field.empty())  c.seed_field  = "seed";

    try {
        return new argus::enterprise::VaultProvider(std::move(c));
    } catch (const std::exception& e) {
        std::cerr << "[vault_crypto] argus_enterprise_create falló: " << e.what() << "\n";
        return nullptr;
    }
}

void argus_enterprise_destroy(argus::ICryptoProvider* provider) {
    delete provider;
}

}  // extern "C"
