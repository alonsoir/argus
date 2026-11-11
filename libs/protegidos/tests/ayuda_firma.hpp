// ayuda_firma.hpp — [PROTEGIDOS-MANIFIESTO-D318] ayudantes de los tests: un par Ed25519 desechable, la firma con el
// formato de Vault transit (vault:vN:<base64>), el sobre argus-protegidos/v1 y cargas de prueba del lab. Los comparten
// test_protegidos_manifiesto (libs/protegidos) y test_protegidos_servidor (etcd-server). Solo tests: nunca en un binario.
#pragma once
#include <sodium.h>

#include <cstdint>
#include <string>

namespace argus::protegidos::prueba {

struct Par {
    unsigned char pk[crypto_sign_PUBLICKEYBYTES];
    unsigned char sk[crypto_sign_SECRETKEYBYTES];
    Par() { crypto_sign_keypair(pk, sk); }
    std::string hex() const {
        char h[crypto_sign_PUBLICKEYBYTES * 2 + 1];
        sodium_bin2hex(h, sizeof h, pk, sizeof pk);
        return h;
    }
};

inline std::string b64(const std::string& d) {
    std::string o(sodium_base64_ENCODED_LEN(d.size(), sodium_base64_VARIANT_ORIGINAL), '\0');
    sodium_bin2base64(o.data(), o.size(), reinterpret_cast<const unsigned char*>(d.data()), d.size(),
                      sodium_base64_VARIANT_ORIGINAL);
    o.resize(o.size() - 1);
    return o;
}

inline std::string firmar(const Par& p, const std::string& carga, int v = 1) {
    unsigned char sig[crypto_sign_BYTES];
    crypto_sign_detached(sig, nullptr, reinterpret_cast<const unsigned char*>(carga.data()), carga.size(), p.sk);
    return "vault:v" + std::to_string(v) + ":" + b64(std::string(reinterpret_cast<const char*>(sig), sizeof sig));
}

inline std::string sobre(const std::string& carga, const std::string& firma, const std::string& extra = "") {
    return "{\"formato\":\"argus-protegidos/v1\",\"carga_b64\":\"" + b64(carga) + "\",\"firma\":\"" + firma + "\"" + extra + "}";
}

inline std::string entrada(const std::string& cat, const std::string& cidr, const std::string& iface = "eth2",
                           const std::string& mac = "", const std::string& motivo = "prueba") {
    return "{\"categoria\":\"" + cat + "\",\"cidr\":\"" + cidr + "\",\"interfaz\":\"" + iface + "\",\"mac\":\"" + mac +
           "\",\"motivo\":\"" + motivo + "\"}";
}

inline std::string carga(uint64_t version, const std::string& planta_lab, const std::string& comun = "",
                         const std::string& limites = "{\"infraestructura\":32,\"intranet\":24,\"dmz\":24,\"externos_criticos\":32}",
                         const std::string& hospital = "hospital-lab", const std::string& extra = "",
                         const std::string& otras_plantas = "") {
    return "{\"esquema\":1,\"hospital_id\":\"" + hospital + "\",\"version\":" + std::to_string(version) +
           ",\"emitido_utc\":\"2026-11-05T08:00:00Z\",\"firmante\":\"argus-infra\",\"motivo\":\"alta del lab\","
           "\"hash_anterior\":\"\",\"limites\":" + limites + ",\"comun\":[" + comun + "],\"plantas\":{\"lab-vagrant\":[" +
           planta_lab + "]" + otras_plantas + "}" + extra + "}";
}

}  // namespace argus::protegidos::prueba
