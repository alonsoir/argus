// ============================================================================
// etcd_registrar.cpp — StubEtcdRegistrar  (ADR-045, DAY 154)
// ============================================================================
#include "etcd_registrar.h"
#include "vault_client.h"   // fingerprint_hex, now_iso8601
#include <sstream>
#include <iostream>

namespace ml_defender {

bool StubEtcdRegistrar::register_status(const CryptoMaterial& material,
                                         const std::string&    component_name,
                                         bool started_with_cache) {
    std::ostringstream json;
    json << "{"
         << "\"component\":\""   << component_name << "\","
         << "\"crypto_ready\":true,"
         << "\"key_version\":"   << material.key_version << ","
         << "\"family\":\""      << material.family << "\","
         << "\"fingerprint\":\"" << VaultClient::fingerprint_hex(material.fingerprint) << "\","
         << "\"derivation_timestamp\":\"" << material.derivation_timestamp << "\","
         << "\"started_with_cache\":"
             << (started_with_cache ? "true" : "false")
         << "}";
    std::cerr << "[etcd_registrar] INFO: crypto_status (stub): "
              << json.str() << "\n";
    return true;
}

void StubEtcdRegistrar::start_keepalive() { keepalive_running_ = true; }
void StubEtcdRegistrar::stop_keepalive()  { keepalive_running_ = false; }

} // namespace ml_defender
