// test_parse_autonomy_cidr_injection.cpp — DAY190 · DEBT-AUTONOMY-REACTOR-CWE78-001
// Test de ATAQUE de integración: un CIDR malicioso en firewall.json["autonomy"]
// DEBE hacer throw en ConfigLoader::parse_autonomy ANTES de que llegue a
// autonomy_reactor::system("iptables ... -s <cidr>").
//
// REQUISITO DE VISIBILIDAD: parse_autonomy debe ser invocable desde el test.
//   - Si es público/estático en ConfigLoader: este test compila tal cual.
//   - Si es privado: o bien (a) declarar 'friend' el fixture, o (b) ejercitar
//     vía ConfigLoader::load_from_file con un JSON completo (ver fallback abajo).
// Alonso: ajusta el include/llamada al estado real de config_loader.hpp.
#include <gtest/gtest.h>
#include <json/json.h>
#include "firewall/config_loader.hpp"

using mldefender::firewall::ConfigLoader;

static Json::Value autonomy_with(const std::vector<std::string>& cidrs) {
    Json::Value j;
    j["whitelist_cidrs"] = Json::Value(Json::arrayValue);
    for (const auto& c : cidrs) j["whitelist_cidrs"].append(c);
    return j;
}

// ATAQUE-1: separador de comando ';' → throw
TEST(ParseAutonomyCidrInjection, RejectsSemicolonCommandChain) {
    auto j = autonomy_with({"10.0.0.0/8", "1.2.3.0/24; iptables -F"});
    EXPECT_THROW(ConfigLoader::parse_autonomy(j, "test.json"), std::runtime_error);
}

// ATAQUE-2: bypass histórico por newline → throw
TEST(ParseAutonomyCidrInjection, RejectsNewlineInjection) {
    auto j = autonomy_with({"1.2.3.4/24\nadd evil 6.6.6.6"});
    EXPECT_THROW(ConfigLoader::parse_autonomy(j, "test.json"), std::runtime_error);
}

// ATAQUE-3: sustitución de comando → throw
TEST(ParseAutonomyCidrInjection, RejectsCommandSubstitution) {
    auto j = autonomy_with({"$(reboot)"});
    EXPECT_THROW(ConfigLoader::parse_autonomy(j, "test.json"), std::runtime_error);
}

// CONTROL: config legítima NO lanza (no rompimos el camino feliz)
TEST(ParseAutonomyCidrInjection, AcceptsLegitimateCidrs) {
    auto j = autonomy_with({"10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"});
    EXPECT_NO_THROW(ConfigLoader::parse_autonomy(j, "test.json"));
}

