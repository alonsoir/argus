// test_host_domain_v1.cpp
// aRGus NDR — DAY 241 — Spec ejecutable de libhost_domain_v1.
// Authors: Alonso Isidoro Roman + Claude (Anthropic)
//
// DOS bloques:
//   (A) PROPIEDAD — sin dependencias externas (solo la lib): determinismo, inmunidad al
//       locale (D-E), confinamiento/rechazo, notario único, primitivas. Es el RED->GREEN
//       central: sin cuerpo en el .cpp, no linka.
//   (B) GOLDEN — byte-idéntico contra host_domain_v1_vectors.json (la referencia Python).
//       Usa nlohmann/json (mismo enfoque que el test de vectores de flow_uid). Si tu árbol
//       usa otro parser, la carga está aislada en run_golden(); es lo único a adaptar.
//
// NOTA DE WIRING: check mínimo local (como test_correlation_v1). Adáptalo a tu framework y
// cuélgalo del Makefile -> test-all.

#include "host_domain_v1/host_domain_v1.hpp"

#include <cstdint>
#include <cstdio>
#include <fstream>
#include <locale>
#include <string>
#include <vector>

#include <nlohmann/json.hpp>

using host_domain_v1::HostDomainV1Row;
using host_domain_v1::mint_event_id;
using host_domain_v1::encode_string_list;
using host_domain_v1::serialize;
using host_domain_v1::validate;
using json = nlohmann::json;

// --- check mínimo (sustituir por tu framework) ------------------------------
static int g_failures = 0;
#define CHECK(cond, msg)                                                        \
    do {                                                                        \
        if (!(cond)) { std::printf("  FAIL: %s\n", (msg)); ++g_failures; }      \
        else         { std::printf("  ok:   %s\n", (msg)); }                    \
    } while (0)

// Clave HMAC de test FIJA (32 bytes 0xAB) = kTestKey de correlation_v1 = hmac_key_hex del JSON.
static const std::vector<uint8_t> kTestKey(32, 0xAB);

static std::vector<uint8_t> hex_to_bytes(const std::string& hex) {
    std::vector<uint8_t> out;
    out.reserve(hex.size() / 2);
    for (size_t i = 0; i + 1 < hex.size(); i += 2)
        out.push_back(static_cast<uint8_t>(std::stoul(hex.substr(i, 2), nullptr, 16)));
    return out;
}

// Row válido de referencia (host_id presente = pasa el error fundamental).
static HostDomainV1Row make_valid_row() {
    HostDomainV1Row r;
    r.schema_version    = "host_domain_v1";
    r.source_sensor     = "wazuh";
    r.event_id          = "wz1:AAAA";
    r.host_id           = "002";
    r.wazuh_alert_id    = "1785468156.2917";
    r.timestamp         = "2026-07-31T03:22:09.071+0000";
    r.agent_id          = "002";
    r.agent_name        = "zeek";
    r.agent_ip          = "192.168.100.11";
    r.os_hostname       = "argus-zeek";
    r.rule_id           = "5715";
    r.rule_level        = 3;
    r.rule_description  = "sshd: authentication success";
    r.rule_groups       = encode_string_list({"syslog", "sshd", "authentication_success"});
    r.decoder_name      = "sshd";
    r.location          = "journald";
    r.full_log          = "Accepted password for root from 10.0.2.2 port 55043 ssh2";
    r.data_json         = "{\"srcip\":\"10.0.2.2\"}";
    r.srcip             = "10.0.2.2";
    r.mitre_ids         = encode_string_list({"T1078", "T1021"});
    r.mitre_tactics     = encode_string_list({"Lateral Movement"});
    r.mitre_techniques  = encode_string_list({"Valid Accounts"});
    return r;
}

// ----------------------------------------------------------------------------
// (A1) DETERMINISMO — mismo Row -> mismos bytes.
// ----------------------------------------------------------------------------
static void test_determinism() {
    std::printf("[A1] determinismo\n");
    const auto row = make_valid_row();
    auto a = serialize(row, kTestKey);
    auto b = serialize(row, kTestKey);
    CHECK(a.ok && b.ok, "serialize OK en dominio válido");
    CHECK(a.line == b.line, "dos serializaciones del mismo Row = bytes idénticos");
}

// ----------------------------------------------------------------------------
// (A2) INMUNIDAD AL LOCALE (D-E) — rule_level no debe salir con separador de millares.
// ----------------------------------------------------------------------------
static void test_locale_immunity() {
    std::printf("[A2] inmunidad al locale (D-E)\n");
    auto row = make_valid_row();
    row.rule_level = 1234567;                    // valor con posible agrupación de millares
    auto classic = serialize(row, kTestKey);
    std::string es_line;
    try {
        std::locale prev = std::locale::global(std::locale("es_ES.UTF-8"));
        es_line = serialize(row, kTestKey).line;
        std::locale::global(prev);
    } catch (const std::exception&) {
        std::printf("  skip: locale es_ES.UTF-8 no instalado en este host\n");
        return;
    }
    CHECK(classic.ok, "serialize OK bajo classic");
    CHECK(classic.line == es_line, "bytes idénticos classic vs es_ES (sin millares en rule_level)");
    CHECK(classic.line.find("1234567") != std::string::npos, "rule_level sin separador de millares");
}

// ----------------------------------------------------------------------------
// (A3) CONFINAMIENTO — validate RECHAZA y serialize NO emite; \t aceptado.
// ----------------------------------------------------------------------------
static void test_confinement() {
    std::printf("[A3] confinamiento\n");
    {
        auto row = make_valid_row(); row.host_id.clear();
        CHECK(!validate(row), "host_id vacío -> validate RECHAZA (error fundamental)");
        CHECK(!serialize(row, kTestKey), "host_id vacío -> serialize NO emite");
    }
    {
        auto row = make_valid_row(); row.full_log = "linea1\nlinea2";
        CHECK(!validate(row), "\\n en full_log -> validate RECHAZA");
        CHECK(!serialize(row, kTestKey), "\\n en full_log -> serialize NO emite");
    }
    {
        auto row = make_valid_row(); row.event_id = "wz1:AA\rBB";
        CHECK(!validate(row), "\\r en event_id -> validate RECHAZA");
    }
    {
        auto row = make_valid_row(); row.command = "col1\tcol2";
        CHECK(validate(row), "\\t en command -> validate ACEPTA (no rompe el reader)");
        CHECK(serialize(row, kTestKey), "\\t en command -> serialize SÍ emite");
    }
    {
        auto row = make_valid_row();
        CHECK(!serialize(row, std::vector<uint8_t>(31, 0xAB)), "clave de 31 bytes -> serialize NO emite");
    }
}

// ----------------------------------------------------------------------------
// (A4) NOTARIO ÚNICO — validate y serialize coinciden en aceptar/rechazar.
// ----------------------------------------------------------------------------
static void test_single_notary() {
    std::printf("[A4] notario único\n");
    auto bad = make_valid_row(); bad.host_id.clear();
    CHECK(static_cast<bool>(validate(bad)) == static_cast<bool>(serialize(bad, kTestKey)),
          "validate y serialize coinciden (sin bypass)");
}

// ----------------------------------------------------------------------------
// (A5) PRIMITIVAS — mint determinista + prefijo; encode básico.
// ----------------------------------------------------------------------------
static void test_primitives() {
    std::printf("[A5] primitivas (mint / encode)\n");
    const std::string raw = "{\"id\":\"1785468156.2917\"}";
    CHECK(mint_event_id(raw) == mint_event_id(raw), "mint_event_id determinista");
    CHECK(mint_event_id(raw).rfind("wz1:", 0) == 0, "mint_event_id lleva prefijo wz1:");
    CHECK(mint_event_id(raw) != mint_event_id(raw + "x"), "raw distinto -> event_id distinto");
    CHECK(encode_string_list({}) == "[]", "lista vacía -> []");
    CHECK(encode_string_list({"a", "b"}) == "[\"a\",\"b\"]", "lista -> JSON compacto");
    CHECK(encode_string_list({"he said \"hi\""}) == "[\"he said \\\"hi\\\"\"]",
          "escaping de comilla en encode_string_list");
}

// ----------------------------------------------------------------------------
// (B) GOLDEN — byte-idéntico contra los vectores congelados (referencia Python).
// ----------------------------------------------------------------------------
static HostDomainV1Row row_from_json(const json& j) {
    HostDomainV1Row r;
    r.schema_version   = j.value("schema_version", "");
    r.source_sensor    = j.value("source_sensor", "");
    r.event_id         = j.value("event_id", "");
    r.host_id          = j.value("host_id", "");
    r.wazuh_alert_id   = j.value("wazuh_alert_id", "");
    r.timestamp        = j.value("timestamp", "");
    r.agent_id         = j.value("agent_id", "");
    r.agent_name       = j.value("agent_name", "");
    r.agent_ip         = j.value("agent_ip", "");
    r.os_hostname      = j.value("os_hostname", "");
    r.rule_id          = j.value("rule_id", "");
    r.rule_level       = j.value("rule_level", 0);
    r.rule_description = j.value("rule_description", "");
    r.rule_groups      = j.value("rule_groups", "");
    r.decoder_name     = j.value("decoder_name", "");
    r.location         = j.value("location", "");
    r.full_log         = j.value("full_log", "");
    r.data_json        = j.value("data_json", "");
    r.srcuser          = j.value("srcuser", "");
    r.dstuser          = j.value("dstuser", "");
    r.srcip            = j.value("srcip", "");
    r.srcport          = j.value("srcport", "");
    r.uid              = j.value("uid", "");
    r.command          = j.value("command", "");
    r.mitre_ids        = j.value("mitre_ids", "");
    r.mitre_tactics    = j.value("mitre_tactics", "");
    r.mitre_techniques = j.value("mitre_techniques", "");
    r.pci_dss          = j.value("pci_dss", "");
    r.gdpr             = j.value("gdpr", "");
    r.hipaa            = j.value("hipaa", "");
    r.nist_800_53      = j.value("nist_800_53", "");
    r.tsc              = j.value("tsc", "");
    r.gpg13            = j.value("gpg13", "");
    return r;
}

static void run_golden(const std::string& path) {
    std::printf("[B] golden byte-idéntico contra %s\n", path.c_str());
    std::ifstream in(path);
    if (!in) { std::printf("  FAIL: no se pudo abrir %s\n", path.c_str()); ++g_failures; return; }
    json v; in >> v;

    const auto key = hex_to_bytes(v.at("hmac_key_hex").get<std::string>());

    for (const auto& m : v.at("mint_event_id")) {
        const bool ok = mint_event_id(m.at("raw_line").get<std::string>()) ==
                        m.at("expected").get<std::string>();
        CHECK(ok, ("mint_event_id[" + m.at("name").get<std::string>() + "]").c_str());
    }
    for (const auto& e : v.at("encode_string_list")) {
        std::vector<std::string> items = e.at("items").get<std::vector<std::string>>();
        const bool ok = encode_string_list(items) == e.at("expected").get<std::string>();
        CHECK(ok, ("encode_string_list[" + e.at("name").get<std::string>() + "]").c_str());
    }
    for (const auto& s : v.at("serialize_ok")) {
        auto r = row_from_json(s.at("row"));
        auto res = serialize(r, key);
        const bool ok = res.ok && res.line == s.at("expected_line").get<std::string>();
        CHECK(ok, ("serialize_ok[" + s.at("name").get<std::string>() + "] byte-idéntico").c_str());
    }
    for (const auto& s : v.at("serialize_reject")) {
        auto r = row_from_json(s.at("row"));
        const bool rejected = !static_cast<bool>(validate(r)) &&
                              !static_cast<bool>(serialize(r, key));
        CHECK(rejected, ("serialize_reject[" + s.at("name").get<std::string>() + "] rechazado").c_str());
    }
}

int main(int argc, char** argv) {
    std::printf("== libhost_domain_v1 :: spec ejecutable ==\n");
    test_determinism();
    test_locale_immunity();
    test_confinement();
    test_single_notary();
    test_primitives();
    const std::string vpath = (argc > 1) ? argv[1]
                            : "tests/vectors/host_domain_v1_vectors.json";
    run_golden(vpath);
    std::printf("== %d fallos ==\n", g_failures);
    return g_failures == 0 ? 0 : 1;
}