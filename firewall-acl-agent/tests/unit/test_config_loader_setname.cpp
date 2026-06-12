// test_config_loader_setname.cpp
//
// ACCEPTANCE TEST — H-2: set_name se interpola en system()/popen() (ipset_wrapper.cpp)
// y el agente corre como root. validate_config debe rechazar cualquier set_name que
// no encaje en la allow-list estricta de ipset ([A-Za-z0-9_-]{1,31}), cerrando
// inyeccion de comandos via fichero de config.
// Authors: Alonso Isidoro Roman + Claude (Anthropic).

#include <gtest/gtest.h>
#include "firewall/config_loader.hpp"

#include <string>

using mldefender::firewall::ConfigLoader;
using mldefender::firewall::FirewallAgentConfig;

namespace {

// Config minima valida salvo el set_name, que fija cada test.
FirewallAgentConfig make_config(const std::string& set_name) {
    FirewallAgentConfig c;
    c.zmq.endpoint        = "tcp://127.0.0.1:5555";
    c.iptables.chain_name = "ARGUS_BLACKLIST";
    c.ipset.set_name      = set_name;
    return c;
}

}  // namespace

// GREEN: nombres legitimos pasan.
TEST(ConfigLoaderSetName, AcceptsValidNames) {
    EXPECT_NO_THROW(ConfigLoader::validate_config(make_config("blacklist")));
    EXPECT_NO_THROW(ConfigLoader::validate_config(make_config("ml_defender_blacklist_test")));
    EXPECT_NO_THROW(ConfigLoader::validate_config(make_config("argus-v1_2025")));
}

// RED: inyeccion de comando clasica (separador de shell).
TEST(ConfigLoaderSetName, RejectsCommandSeparator) {
    EXPECT_THROW(ConfigLoader::validate_config(make_config("blacklist; rm -rf /")),
                 std::invalid_argument);
    EXPECT_THROW(ConfigLoader::validate_config(make_config("x$(reboot)")),
                 std::invalid_argument);
    EXPECT_THROW(ConfigLoader::validate_config(make_config("a`id`")),
                 std::invalid_argument);
    EXPECT_THROW(ConfigLoader::validate_config(make_config("a && curl evil")),
                 std::invalid_argument);
}

// RED: espacios y metacaracteres de shell.
TEST(ConfigLoaderSetName, RejectsShellMetacharacters) {
    EXPECT_THROW(ConfigLoader::validate_config(make_config("set name")),
                 std::invalid_argument);
    EXPECT_THROW(ConfigLoader::validate_config(make_config("set|name")),
                 std::invalid_argument);
    EXPECT_THROW(ConfigLoader::validate_config(make_config("set>name")),
                 std::invalid_argument);
}

// RED: vacio (ya cubierto) y exceso de longitud (limite real de ipset = 31).
TEST(ConfigLoaderSetName, RejectsEmptyAndTooLong) {
    EXPECT_THROW(ConfigLoader::validate_config(make_config("")),
                 std::invalid_argument);
    EXPECT_THROW(ConfigLoader::validate_config(make_config(std::string(32, 'a'))),
                 std::invalid_argument);
    // 31 chars es el limite -> debe pasar.
    EXPECT_NO_THROW(ConfigLoader::validate_config(make_config(std::string(31, 'a'))));
}
