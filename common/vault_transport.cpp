// ============================================================================
// vault_transport.cpp — HttpVaultTransport (ADR-045 DAY 153)
// ============================================================================
// Extraído de vault_client.cpp: apply_jitter() + vault_get_seed()
// ============================================================================
#include "vault_transport.h"

#include <curl/curl.h>
#include <chrono>
#include <iostream>
#include <random>
#include <sstream>
#include <thread>

namespace ml_defender {

namespace {

size_t curl_write_cb(char* ptr, size_t size, size_t nmemb, std::string* out) {
    out->append(ptr, size * nmemb);
    return size * nmemb;
}

} // namespace anon

// ── HttpVaultTransport ────────────────────────────────────────────────────────

std::optional<std::string> HttpVaultTransport::fetch_seed(
        const VaultClientConfig& config) {
    apply_jitter(config);
    return vault_http_get(config);
}

void HttpVaultTransport::apply_jitter(const VaultClientConfig& config) {
    std::mt19937 rng(std::random_device{}());
    std::uniform_int_distribution<uint32_t> dist(0, VAULT_JITTER_RAND_MS);
    uint32_t delay_ms = config.component_index * VAULT_JITTER_BASE_MS
                        + dist(rng);
    if (delay_ms > 0)
        std::this_thread::sleep_for(std::chrono::milliseconds(delay_ms));
}

std::optional<std::string> HttpVaultTransport::vault_http_get(
        const VaultClientConfig& config) {
    std::string path;
    if (config.family == "etcd") {
        path = "argus/" + config.env + "/components/etcd/seed";
    } else {
        path = "argus/" + config.env + "/families/family_"
               + config.family + "/seed";
    }

    std::string url = config.vault_addr + "/v1/" + path;
    std::string response;

    CURL* curl = curl_easy_init();
    if (!curl) return std::nullopt;

    struct curl_slist* headers = nullptr;
    std::string token_header = "X-Vault-Token: " + config.vault_token;
    headers = curl_slist_append(headers, token_header.c_str());

    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, curl_write_cb);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT_MS,
                     static_cast<long>(config.timeout_ms));

    CURLcode res = curl_easy_perform(curl);
    long http_code = 0;
    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &http_code);
    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);

    if (res != CURLE_OK || http_code != 200) return std::nullopt;
    return parse_vault_value(response);
}

std::optional<std::string> HttpVaultTransport::parse_vault_value(
        const std::string& json) {
    const std::string key = "\"value\":\"";
    auto pos = json.find(key);
    if (pos == std::string::npos) return std::nullopt;
    pos += key.size();
    auto end = json.find('"', pos);
    if (end == std::string::npos) return std::nullopt;
    return json.substr(pos, end - pos);
}

} // namespace ml_defender