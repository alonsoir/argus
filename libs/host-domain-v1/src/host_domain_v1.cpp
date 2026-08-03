// host_domain_v1.cpp
// aRGus NDR — libhost_domain_v1: implementación de la capa de serialización bronce host.
// Authors: Alonso Isidoro Roman + Claude (Anthropic)
//
// DEFINICIÓN PRIMARIA (DAY 241). No transcribe un oráculo (host no tiene binario previo);
// implementa el contrato tal como lo fija host_domain_v1_ref.py, y el golden byte-idéntico
// se prueba contra los vectores que esa referencia congela. Espeja el estilo de
// correlation_v1.cpp: csv_string / compute_hmac verbatim; SIN fmt_double (host no tiene
// campos double); + dos primitivas que la red no tiene (mint_event_id, encode_string_list).
//
// D-E   imbue(std::locale::classic()) en el stream de columnas (rule_level es el único
//       entero; bajo es_ES saldría con separador de millares y rompería los bytes).
// D-HOST-5  csv_string en TODAS las columnas string; rule_level entero crudo.

#include "host_domain_v1/host_domain_v1.hpp"

#include <cstdio>
#include <iomanip>
#include <locale>
#include <sstream>
#include <string>

#include <openssl/hmac.h>
#include <openssl/evp.h>
#include <sodium.h>

namespace host_domain_v1 {

namespace {

// --- csv_string — COPIA VERBATIM de correlation_v1 (manipulación de chars, locale-safe) --
std::string csv_string(const std::string& s) {
    bool needs_quote = s.find_first_of(",\"\n") != std::string::npos;
    if (!needs_quote) return s;
    std::string out = "\"";
    for (char c : s) { if (c == '"') out += "\"\""; else out += c; }
    out += "\"";
    return out;
}

// --- json_escape_string — escaping de string JSON idéntico a json.dumps(ensure_ascii=False)
// Escapa " \ y los cinco control-cortos (\b\f\n\r\t); el resto de control < 0x20 -> \u00xx
// (hex minúsculas, como Python); bytes >= 0x20 (incl. UTF-8 >= 0x80) pasan crudos. NO escapa
// '/'. Es el mecanismo de encode_string_list (D-HOST-2), sin traer dependencia JSON. -------
std::string json_escape_string(const std::string& s) {
    std::string out;
    out.reserve(s.size() + 2);
    for (unsigned char c : s) {
        switch (c) {
            case '"':  out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\b': out += "\\b";  break;
            case '\f': out += "\\f";  break;
            case '\n': out += "\\n";  break;
            case '\r': out += "\\r";  break;
            case '\t': out += "\\t";  break;
            default:
                if (c < 0x20) {
                    char buf[8];
                    std::snprintf(buf, sizeof buf, "\\u%04x", c);
                    out += buf;
                } else {
                    out += static_cast<char>(c);
                }
        }
    }
    return out;
}

// --- compute_hmac — COPIA VERBATIM de correlation_v1; HMAC-SHA256, hex minúsculas --------
std::string compute_hmac(const std::string& content, const std::vector<uint8_t>& key) {
    unsigned char digest[EVP_MAX_MD_SIZE];
    unsigned int digest_len = 0;
    HMAC(EVP_sha256(), key.data(), static_cast<int>(key.size()),
         reinterpret_cast<const unsigned char*>(content.data()), content.size(),
         digest, &digest_len);
    std::ostringstream ss;
    ss << std::hex << std::setfill('0');
    for (unsigned int i = 0; i < digest_len; ++i)
        ss << std::setw(2) << static_cast<unsigned int>(digest[i]);
    return ss.str();
}

// --- build_cols_0_32 — orden/separadores/quoting del contrato (D-HOST-5) -----------------
// cols 0-32; rule_level (11) crudo, el resto csv_string. imbue classic (D-E).
std::string build_cols_0_32(const HostDomainV1Row& r) {
    std::ostringstream ss;
    ss.imbue(std::locale::classic());                              // D-E
    ss << csv_string(r.schema_version)                             // 0
       << ',' << csv_string(r.source_sensor)                       // 1
       << ',' << csv_string(r.event_id)                            // 2
       << ',' << csv_string(r.host_id)                             // 3
       << ',' << csv_string(r.wazuh_alert_id)                      // 4
       << ',' << csv_string(r.timestamp)                           // 5
       << ',' << csv_string(r.agent_id)                            // 6
       << ',' << csv_string(r.agent_name)                          // 7
       << ',' << csv_string(r.agent_ip)                            // 8
       << ',' << csv_string(r.os_hostname)                         // 9
       << ',' << csv_string(r.rule_id)                             // 10
       << ',' << r.rule_level                                      // 11 (crudo int32)
       << ',' << csv_string(r.rule_description)                    // 12
       << ',' << csv_string(r.rule_groups)                         // 13 [json]
       << ',' << csv_string(r.decoder_name)                        // 14
       << ',' << csv_string(r.location)                            // 15
       << ',' << csv_string(r.full_log)                            // 16
       << ',' << csv_string(r.data_json)                           // 17 [json]
       << ',' << csv_string(r.srcuser)                             // 18
       << ',' << csv_string(r.dstuser)                             // 19
       << ',' << csv_string(r.srcip)                               // 20
       << ',' << csv_string(r.srcport)                             // 21
       << ',' << csv_string(r.uid)                                 // 22
       << ',' << csv_string(r.command)                             // 23
       << ',' << csv_string(r.mitre_ids)                           // 24 [json]
       << ',' << csv_string(r.mitre_tactics)                       // 25 [json]
       << ',' << csv_string(r.mitre_techniques)                    // 26 [json]
       << ',' << csv_string(r.pci_dss)                             // 27 [json]
       << ',' << csv_string(r.gdpr)                                // 28 [json]
       << ',' << csv_string(r.hipaa)                               // 29 [json]
       << ',' << csv_string(r.nist_800_53)                         // 30 [json]
       << ',' << csv_string(r.tsc)                                 // 31 [json]
       << ',' << csv_string(r.gpg13);                              // 32 [json]
    return ss.str();
}

} // anonymous namespace

// ----------------------------------------------------------------------------
// mint_event_id (D-HOST-1). "wz1:" + base64_std(BLAKE2b-256("argus-hostevent-v1" || raw_line))
// ----------------------------------------------------------------------------
std::string mint_event_id(const std::string& raw_line) {
    // sodium_init() es idempotente; asegura la detección de features en corridas aisladas
    // (el test llama a mint directamente). No hay canal de error en la firma; en estas
    // plataformas no falla, y generichash/base64 no dependen del RNG.
    if (sodium_init() < 0) {
        // Fallo de init: no ocurre en estas plataformas y generichash/base64 no dependen
        // del RNG. No hay canal de error en la firma; seguimos (fail-open consciente).
    }

    static const char TAG[] = "argus-hostevent-v1";
    const size_t TAG_LEN = sizeof(TAG) - 1;                        // sin el '\0'

    std::string msg;
    msg.reserve(TAG_LEN + raw_line.size());
    msg.append(TAG, TAG_LEN);
    msg.append(raw_line);

    unsigned char digest[32];
    crypto_generichash(digest, sizeof digest,
                       reinterpret_cast<const unsigned char*>(msg.data()), msg.size(),
                       nullptr, 0);                                // sin clave (unkeyed)

    const size_t b64_cap = sodium_base64_ENCODED_LEN(sizeof digest,
                                                      sodium_base64_VARIANT_ORIGINAL);
    std::string b64(b64_cap, '\0');
    sodium_bin2base64(b64.data(), b64.size(), digest, sizeof digest,
                      sodium_base64_VARIANT_ORIGINAL);
    b64.resize(b64_cap - 1);                                       // recorta el '\0' final

    return "wz1:" + b64;
}

// ----------------------------------------------------------------------------
// encode_string_list (D-HOST-2). JSON compacto canónico: ["a","b"], sin espacios.
// ----------------------------------------------------------------------------
std::string encode_string_list(const std::vector<std::string>& items) {
    std::string out = "[";
    for (size_t i = 0; i < items.size(); ++i) {
        if (i) out += ',';
        out += '"';
        out += json_escape_string(items[i]);
        out += '"';
    }
    out += ']';
    return out;
}

// ----------------------------------------------------------------------------
// validate — NOTARIO ÚNICO (P3). v1 mínimo: host_id vacío (fundamental) + newline-guard.
// ----------------------------------------------------------------------------
ValidationResult validate(const HostDomainV1Row& row) noexcept {
    // ERROR FUNDAMENTAL (D-HOST-3): host_id (= agent.id) es la PK del nodo Host. Va primero.
    if (row.host_id.empty()) {
        return ValidationResult{
            false, "host_id vacío: PK del nodo Host ausente (error fundamental)"};
    }

    // NEWLINE-GUARD (heredado, DEBT-BRONZE-EMBEDDED-NEWLINE-001): \n/\r embebido rompe el
    // reader getline (1 fila lógica != 1 línea física). \t NO se rechaza.
    auto tiene_newline = [](const std::string& s) noexcept {
        return s.find('\n') != std::string::npos ||
               s.find('\r') != std::string::npos;
    };
    const std::pair<const std::string&, const char*> campos_texto[] = {
        {row.schema_version,   "schema_version"},   {row.source_sensor,    "source_sensor"},
        {row.event_id,         "event_id"},         {row.host_id,          "host_id"},
        {row.wazuh_alert_id,   "wazuh_alert_id"},   {row.timestamp,        "timestamp"},
        {row.agent_id,         "agent_id"},         {row.agent_name,       "agent_name"},
        {row.agent_ip,         "agent_ip"},         {row.os_hostname,      "os_hostname"},
        {row.rule_id,          "rule_id"},          {row.rule_description, "rule_description"},
        {row.rule_groups,      "rule_groups"},      {row.decoder_name,     "decoder_name"},
        {row.location,         "location"},         {row.full_log,         "full_log"},
        {row.data_json,        "data_json"},        {row.srcuser,          "srcuser"},
        {row.dstuser,          "dstuser"},          {row.srcip,            "srcip"},
        {row.srcport,          "srcport"},          {row.uid,              "uid"},
        {row.command,          "command"},          {row.mitre_ids,        "mitre_ids"},
        {row.mitre_tactics,    "mitre_tactics"},    {row.mitre_techniques, "mitre_techniques"},
        {row.pci_dss,          "pci_dss"},          {row.gdpr,             "gdpr"},
        {row.hipaa,            "hipaa"},            {row.nist_800_53,      "nist_800_53"},
        {row.tsc,              "tsc"},              {row.gpg13,            "gpg13"},
    };
    for (const auto& campo : campos_texto) {
        if (tiene_newline(campo.first)) {
            return ValidationResult{
                false, std::string("col texto '") + campo.second +
                "' contiene \\n o \\r embebido: rompe el reader getline "
                "(DEBT-BRONZE-EMBEDDED-NEWLINE-001)"};
        }
    }

    // DIFERIDO a commit de contrato posterior (no en v1, medir la necesidad primero):
    //   - rule_id no vacío
    //   - rango de rule_level
    //   - formato de event_id ("wz1:" + base64)
    return ValidationResult{true, ""};
}

// ----------------------------------------------------------------------------
// serialize — Row -> línea bronce (cols 0-33). PURA: (row, hmac_key) y nada más.
// ----------------------------------------------------------------------------
SerializeResult serialize(const HostDomainV1Row& row,
                          const std::vector<uint8_t>& hmac_key) {
    if (auto v = validate(row); !v) {                              // P3: notario único
        return SerializeResult{false, "", v.error};
    }
    if (hmac_key.size() != 32) {                                   // clave ausente/errónea = ruidoso
        return SerializeResult{
            false, "",
            "hmac_key debe ser 32 bytes (got " + std::to_string(hmac_key.size()) +
            "): clave ausente o incorrecta"};
    }
    const std::string cols_0_32 = build_cols_0_32(row);            // cols 0-32
    const std::string hmac      = compute_hmac(cols_0_32, hmac_key); // col 33
    return SerializeResult{true, cols_0_32 + "," + hmac, ""};
}

} // namespace host_domain_v1