// test_safe_exec.cpp — Tests RED→GREEN para DEBT-IPTABLES-INJECTION-001
// Consejo 8/8 DAY 128: toda deuda de seguridad requiere (1) unit, (2) property, (3) integración.
// Regla: test debe FALLAR con código antiguo (popen/system) y PASAR con safe_exec.

#include <gtest/gtest.h>
#include "safe_exec.hpp"
#include <filesystem>
#include <fstream>
#include <sys/stat.h>

// ============================================================
// 1. UNIT TESTS — validate_chain_name allowlist
// ============================================================

TEST(SafeExecValidation, ChainNameAcceptsValid) {
    // Nombres válidos de chains iptables
    EXPECT_TRUE(validate_chain_name("INPUT"));
    EXPECT_TRUE(validate_chain_name("FORWARD"));
    EXPECT_TRUE(validate_chain_name("OUTPUT"));
    EXPECT_TRUE(validate_chain_name("ARGUS-BLACKLIST"));
    EXPECT_TRUE(validate_chain_name("argus_whitelist"));
    EXPECT_TRUE(validate_chain_name("ML-DEFENDER-01"));
    EXPECT_TRUE(validate_chain_name("A"));          // mínimo válido
    EXPECT_TRUE(validate_chain_name("ABCDEFGHIJ1234567890123456789")); // 30 - 1 = 29 chars
}

TEST(SafeExecValidation, ChainNameRejectsEmpty) {
    // RED: string vacío debe rechazarse
    EXPECT_FALSE(validate_chain_name(""));
}

TEST(SafeExecValidation, ChainNameRejectsTooLong) {
    // RED: >29 chars viola límite iptables
    EXPECT_FALSE(validate_chain_name("ABCDEFGHIJKLMNOPQRSTUVWXYZ12345")); // 31 chars
}

TEST(SafeExecValidation, ChainNameRejectsShellMetachars) {
    // RED — CRÍTICO: estos eran el vector CWE-78 con execute_command()
    // Con popen("iptables -D " + chain), cualquiera de estos ejecutaría shell
    EXPECT_FALSE(validate_chain_name("valid; rm -rf /"));
    EXPECT_FALSE(validate_chain_name("chain|cat /etc/passwd"));
    EXPECT_FALSE(validate_chain_name("chain&&evil"));
    EXPECT_FALSE(validate_chain_name("chain>>/etc/crontab"));
    EXPECT_FALSE(validate_chain_name("$(evil_cmd)"));
    EXPECT_FALSE(validate_chain_name("`evil_cmd`"));
    EXPECT_FALSE(validate_chain_name("chain name"));   // espacio
    EXPECT_FALSE(validate_chain_name("chain\nnewline"));
    EXPECT_FALSE(validate_chain_name(std::string("chain\x00null", 10))); // null byte — constructor con longitud
    EXPECT_FALSE(validate_chain_name("chain!bang"));
    EXPECT_FALSE(validate_chain_name("chain{brace}"));
    EXPECT_FALSE(validate_chain_name("chain*glob"));
    EXPECT_FALSE(validate_chain_name("chain?question"));
    EXPECT_FALSE(validate_chain_name("../traversal"));
}

// ============================================================
// 2. PROPERTY TESTS — invariantes de validate_chain_name
// ============================================================

TEST(SafeExecProperty, AnyMetacharMakesChainNameInvalid) {
    // Propiedad: para todo metacaracter shell, cualquier string que lo contenga → false
    const std::vector<char> metachar = {
        ';', '|', '&', '>', '<', '`', '$', '(', ')', '{', '}',
        '*', '?', '!', '\\', '"', '\'', ' ', '\n', '\t', '\r', '\0'
    };
    for (char c : metachar) {
        std::string name = "VALID";
        name += c;
        name += "SUFFIX";
        EXPECT_FALSE(validate_chain_name(name))
            << "Metachar " << (int)c << " deberia invalidar chain name";
    }
}

TEST(SafeExecProperty, ValidCharsAlwaysAccepted) {
    // Propiedad: strings compuestos solo de [A-Za-z0-9_-] de longitud 1..29 → siempre true
    const std::string valid_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-";
    for (char c : valid_chars) {
        std::string name(1, c);
        EXPECT_TRUE(validate_chain_name(name))
            << "Char '" << c << "' deberia ser valido en chain name";
    }
}

TEST(SafeExecProperty, ValidateTableNameKnownSet) {
    // Propiedad: solo tablas conocidas pasan
    EXPECT_TRUE(validate_table_name("filter"));
    EXPECT_TRUE(validate_table_name("nat"));
    EXPECT_TRUE(validate_table_name("mangle"));
    EXPECT_TRUE(validate_table_name("raw"));
    EXPECT_TRUE(validate_table_name("security"));
    // Cualquier otra cosa falla
    EXPECT_FALSE(validate_table_name(""));
    EXPECT_FALSE(validate_table_name("FILTER"));    // case-sensitive
    EXPECT_FALSE(validate_table_name("filter; evil"));
    EXPECT_FALSE(validate_table_name("unknown_table"));
}

TEST(SafeExecProperty, ValidateFilepathRejectsTraversal) {
    // Propiedad: path traversal siempre rechazado
    EXPECT_FALSE(validate_filepath("../etc/passwd"));
    EXPECT_FALSE(validate_filepath("/safe/../etc/passwd"));
    EXPECT_FALSE(validate_filepath("../../root/.ssh/authorized_keys"));
    // Paths válidos
    EXPECT_TRUE(validate_filepath("/tmp/iptables-backup.rules"));
    EXPECT_TRUE(validate_filepath("/etc/argus/rules.bak"));
    EXPECT_FALSE(validate_filepath(""));
    EXPECT_FALSE(validate_filepath("/path/with spaces/file"));
    EXPECT_FALSE(validate_filepath("/path/with;semicolon"));
}

// ============================================================
// 3. INTEGRATION TESTS — safe_exec() execve() sin shell
// ============================================================

TEST(SafeExecIntegration, ExecSimpleCommandReturnsZero) {
    // GREEN: /bin/true siempre retorna 0
    int ret = safe_exec({"/bin/true"});
    EXPECT_EQ(ret, 0);
}

TEST(SafeExecIntegration, ExecFalseReturnsNonZero) {
    // GREEN: /bin/false siempre retorna != 0
    int ret = safe_exec({"/bin/false"});
    EXPECT_NE(ret, 0);
}

TEST(SafeExecIntegration, MetacharsNotInterpretedAsShell) {
    // CRÍTICO RED→GREEN: con popen() el metacaracter ';' ejecutaría el segundo comando.
    // Con safe_exec(execv) el argumento se pasa literalmente — el proceso falla
    // porque "validchain;evil" no es un binario válido, pero NO ejecuta shell.
    // Usamos /bin/echo con argumento que contiene metacaracteres — echo los imprime,
    // no los interpreta. safe_exec_with_output debe capturar la cadena literal.
    auto [ret, out] = safe_exec_with_output({"/bin/echo", "chain;evil&&cmd|pipe"});
    EXPECT_EQ(ret, 0);
    // La salida debe ser el string literal, NO el resultado de ejecutar los comandos
    EXPECT_NE(out.find("chain;evil&&cmd|pipe"), std::string::npos);
    // No debe haber ejecutado nada extra
    EXPECT_EQ(out.find("sh:"), std::string::npos);
}

TEST(SafeExecIntegration, SafeExecWithOutputCapturesStdout) {
    // GREEN: captura stdout correctamente
    auto [ret, out] = safe_exec_with_output({"/bin/echo", "ARGUS_TEST_OK"});
    EXPECT_EQ(ret, 0);
    EXPECT_NE(out.find("ARGUS_TEST_OK"), std::string::npos);
}

TEST(SafeExecIntegration, SafeExecWithOutputEmptyArgs) {
    // GREEN: args vacíos retorna -1, no crash
    auto [ret, out] = safe_exec_with_output({});
    EXPECT_EQ(ret, -1);
}

TEST(SafeExecIntegration, SafeExecWithFileOut) {
    // GREEN: redirige stdout a fichero sin shell
    const std::string tmp = "/tmp/argus_safe_exec_test.txt";
    int ret = safe_exec_with_file_out({"/bin/echo", "SAFE_EXEC_FILE_OUT"}, tmp);
    EXPECT_EQ(ret, 0);
    std::ifstream f(tmp);
    std::string content((std::istreambuf_iterator<char>(f)),
                         std::istreambuf_iterator<char>());
    EXPECT_NE(content.find("SAFE_EXEC_FILE_OUT"), std::string::npos);
    std::remove(tmp.c_str());
}

TEST(SafeExecIntegration, SafeExecWithFileIn) {
    // GREEN: lee stdin desde fichero sin shell
    const std::string tmp = "/tmp/argus_safe_exec_input.txt";
    { std::ofstream f(tmp); f << "hello from file\n"; }
    // safe_exec_with_file_in: cat lee desde fichero
    int ret2 = safe_exec_with_file_in({"/bin/cat"}, tmp);
    // Solo verificamos que no crashea y retorna 0
    EXPECT_EQ(ret2, 0);
    std::remove(tmp.c_str());
}

// ============================================================
// 4. NULL BYTE TESTS — DEBT-SAFE-EXEC-NULLBYTE-001 (Consejo 8/8 DAY 129)
// is_safe_for_exec(): defensa en profundidad independiente de validadores upstream.
// Un null byte en argv[i] trunca el argumento silenciosamente en execv() → fail-closed.
// ============================================================

TEST(SafeExecIntegration, RejectsNullByteInArgument) {
    // RED: argumento con null byte interno → safe_exec retorna -1 (fail-closed)
    // Con código antiguo sin is_safe_for_exec(), execv truncaría el argumento
    // y ejecutaría algo diferente a lo esperado sin error visible.
    std::string arg_with_null("chain\x00evil", 10);
    int ret = safe_exec({"/bin/echo", arg_with_null});
    EXPECT_EQ(ret, -1) << "safe_exec debe rechazar null bytes en argumentos";
}

TEST(SafeExecProperty, IsAlwaysSafeForNormalStrings) {
    // Propiedad: strings sin null byte → is_safe_for_exec siempre true
    const std::vector<std::string> safe_strings = {
        "INPUT", "FORWARD", "/usr/sbin/iptables", "-t", "filter", "-N",
        "ARGUS-BLACKLIST", "192.168.1.1", "--dport", "443"
    };
    for (const auto& s : safe_strings) {
        EXPECT_TRUE(is_safe_for_exec(s))
            << "String normal debe ser safe: " << s;
    }
}
