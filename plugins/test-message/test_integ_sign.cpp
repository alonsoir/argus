// ============================================================================
// test_integ_sign.cpp — TEST-INTEG-SIGN-1 a 7 (ADR-025)
// ============================================================================
#include "plugin_loader/plugin_loader.hpp"
#include "plugin_loader/plugin_api.h"
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <filesystem>
#include <unistd.h>
#include <sys/stat.h>

using namespace ml_defender;
namespace fs = std::filesystem;

static const char* VALID_SO  = "/usr/lib/ml-defender/plugins/libplugin_test_message.so";
static const char* VALID_SIG = "/usr/lib/ml-defender/plugins/libplugin_test_message.so.sig";
static const char* VALID_CFG = "/vagrant/plugins/test-message/test_config.json";

// Directorio temporal unico por PID — evita colisiones entre ejecuciones
static std::string TMPDIR;

static void setup_tmpdir() {
    TMPDIR = std::string("/tmp/mld_sign_test_") + std::to_string(getpid());
    fs::create_directories(TMPDIR);
}

static void cleanup_tmpdir() {
    fs::remove_all(TMPDIR);
}

// Escribir JSON config con path dado
static std::string write_cfg(const std::string& name, const std::string& so_path) {
    std::string cfg = TMPDIR + "/" + name + ".json";
    FILE* f = fopen(cfg.c_str(), "w");
    fprintf(f, R"({
  "component": "%s",
  "plugins": {
    "directory": "/usr/lib/ml-defender/plugins",
    "budget_us": 500,
    "enabled": [{"name": "%s", "path": "%s", "active": true}]
  }
})", name.c_str(), name.c_str(), so_path.c_str());
    fclose(f);
    return cfg;
}

// ----------------------------------------------------------------
// SIGN-1: firma valida → carga exitosa
// ----------------------------------------------------------------
static int test_sign_1() {
    fprintf(stderr, "\n=== TEST-INTEG-SIGN-1: firma valida → carga exitosa ===\n");
    unsetenv("MLD_ALLOW_DEV_MODE");
    PluginLoader loader(VALID_CFG);
    loader.load_plugins();
    bool ok = (loader.loaded_count() == 1);
    fprintf(stderr, "SIGN-1: loaded_count=%zu → %s\n", loader.loaded_count(), ok ? "PASS" : "FAIL");
    return ok ? 0 : 1;
}

// ----------------------------------------------------------------
// SIGN-2: firma invalida → loaded_count==0
// ----------------------------------------------------------------
static int test_sign_2() {
    fprintf(stderr, "\n=== TEST-INTEG-SIGN-2: firma invalida → loaded_count==0 ===\n");
    setenv("MLD_ALLOW_DEV_MODE", "1", 1);

    std::string backup = TMPDIR + "/valid.sig.bak";
    fs::copy_file(VALID_SIG, backup, fs::copy_options::overwrite_existing);

    // Sobreescribir .sig con basura
    { FILE* f = fopen(VALID_SIG, "wb"); char z[64]={}; fwrite(z,1,64,f); fclose(f); }

    PluginLoader loader(VALID_CFG);
    loader.load_plugins();
    bool ok = (loader.loaded_count() == 0);
    fprintf(stderr, "SIGN-2: loaded_count=%zu (expect 0) → %s\n", loader.loaded_count(), ok ? "PASS" : "FAIL");

    fs::copy_file(backup, VALID_SIG, fs::copy_options::overwrite_existing);
    return ok ? 0 : 1;
}

// ----------------------------------------------------------------
// SIGN-3: .sig ausente → loaded_count==0
// ----------------------------------------------------------------
static int test_sign_3() {
    fprintf(stderr, "\n=== TEST-INTEG-SIGN-3: .sig ausente → loaded_count==0 ===\n");
    setenv("MLD_ALLOW_DEV_MODE", "1", 1);

    std::string backup = TMPDIR + "/valid.sig.bak";
    fs::copy_file(VALID_SIG, backup, fs::copy_options::overwrite_existing);
    fs::remove(VALID_SIG);

    PluginLoader loader(VALID_CFG);
    loader.load_plugins();
    bool ok = (loader.loaded_count() == 0);
    fprintf(stderr, "SIGN-3: loaded_count=%zu (expect 0) → %s\n", loader.loaded_count(), ok ? "PASS" : "FAIL");

    fs::copy_file(backup, VALID_SIG, fs::copy_options::overwrite_existing);
    return ok ? 0 : 1;
}

// ----------------------------------------------------------------
// SIGN-4: symlink attack O_NOFOLLOW → loaded_count==0
// ----------------------------------------------------------------
static int test_sign_4() {
    fprintf(stderr, "\n=== TEST-INTEG-SIGN-4: symlink attack → loaded_count==0 ===\n");
    setenv("MLD_ALLOW_DEV_MODE", "1", 1);

    std::string sym_so  = TMPDIR + "/libplugin_symlink.so";
    std::string sym_sig = TMPDIR + "/libplugin_symlink.so.sig";

    // Symlinks en TMPDIR — fuera del prefix permitido, test SIGN-4 verifica O_NOFOLLOW
    // Para testear O_NOFOLLOW necesitamos el symlink DENTRO del prefix
    std::string pfx_sym_so  = "/usr/lib/ml-defender/plugins/libplugin_symlink_test.so";
    std::string pfx_sym_sig = "/usr/lib/ml-defender/plugins/libplugin_symlink_test.so.sig";

    fs::remove(pfx_sym_so);
    fs::remove(pfx_sym_sig);
    fs::create_symlink(VALID_SO, pfx_sym_so);
    fs::create_symlink(VALID_SIG, pfx_sym_sig);

    std::string cfg = write_cfg("test-sign-4", pfx_sym_so);

    PluginLoader loader(cfg);
    loader.load_plugins();
    bool ok = (loader.loaded_count() == 0);
    fprintf(stderr, "SIGN-4: symlink rejected, loaded_count=%zu (expect 0) → %s\n",
            loader.loaded_count(), ok ? "PASS" : "FAIL");

    fs::remove(pfx_sym_so);
    fs::remove(pfx_sym_sig);
    return ok ? 0 : 1;
}

// ----------------------------------------------------------------
// SIGN-5: path traversal → loaded_count==0
// ----------------------------------------------------------------
static int test_sign_5() {
    fprintf(stderr, "\n=== TEST-INTEG-SIGN-5: path traversal → loaded_count==0 ===\n");
    setenv("MLD_ALLOW_DEV_MODE", "1", 1);

    std::string cfg = write_cfg("test-sign-5",
        "/usr/lib/ml-defender/plugins/../../../tmp/libplugin_test_message.so");

    PluginLoader loader(cfg);
    loader.load_plugins();
    bool ok = (loader.loaded_count() == 0);
    fprintf(stderr, "SIGN-5: traversal rejected, loaded_count=%zu (expect 0) → %s\n",
            loader.loaded_count(), ok ? "PASS" : "FAIL");
    return ok ? 0 : 1;
}

// ----------------------------------------------------------------
// SIGN-6: clave rotada (mismatch) → loaded_count==0
// ----------------------------------------------------------------
static int test_sign_6() {
    fprintf(stderr, "\n=== TEST-INTEG-SIGN-6: clave rotada → loaded_count==0 ===\n");
    setenv("MLD_ALLOW_DEV_MODE", "1", 1);

    std::string rot_sk  = TMPDIR + "/rotate.sk";
    std::string rot_sig = TMPDIR + "/rotate.sig";

    // Generar keypair temporal distinto al embebido
    std::string cmd1 = "openssl genpkey -algorithm ed25519 -out " + rot_sk + " 2>/dev/null";
    std::string cmd2 = "openssl pkeyutl -sign -inkey " + rot_sk + " -rawin -in " +
                       std::string(VALID_SO) + " -out " + rot_sig + " 2>/dev/null";
    system(cmd1.c_str());
    system(cmd2.c_str());

    std::string backup = TMPDIR + "/valid.sig.bak";
    fs::copy_file(VALID_SIG, backup, fs::copy_options::overwrite_existing);
    fs::copy_file(rot_sig, VALID_SIG, fs::copy_options::overwrite_existing);

    PluginLoader loader(VALID_CFG);
    loader.load_plugins();
    bool ok = (loader.loaded_count() == 0);
    fprintf(stderr, "SIGN-6: key mismatch rejected, loaded_count=%zu (expect 0) → %s\n",
            loader.loaded_count(), ok ? "PASS" : "FAIL");

    fs::copy_file(backup, VALID_SIG, fs::copy_options::overwrite_existing);
    return ok ? 0 : 1;
}

// ----------------------------------------------------------------
// SIGN-7: plugin truncado size check → loaded_count==0
// ----------------------------------------------------------------
static int test_sign_7() {
    fprintf(stderr, "\n=== TEST-INTEG-SIGN-7: plugin truncado → loaded_count==0 ===\n");
    setenv("MLD_ALLOW_DEV_MODE", "1", 1);

    std::string tiny_so  = "/usr/lib/ml-defender/plugins/libplugin_tiny_test.so";
    std::string tiny_sig = tiny_so + ".sig";

    // .so de 100 bytes — menor que MIN_PLUGIN_SIZE=4096
    { FILE* f = fopen(tiny_so.c_str(), "wb"); char b[100]={}; fwrite(b,1,100,f); fclose(f); chmod(tiny_so.c_str(), 0755); }

    std::string cmd = "openssl pkeyutl -sign -inkey /etc/ml-defender/plugins/plugin_signing.sk "
                      "-rawin -in " + tiny_so + " -out " + tiny_sig + " 2>/dev/null";
    system(cmd.c_str());

    std::string cfg = write_cfg("test-sign-7", tiny_so);

    PluginLoader loader(cfg);
    loader.load_plugins();
    bool ok = (loader.loaded_count() == 0);
    fprintf(stderr, "SIGN-7: tiny plugin rejected, loaded_count=%zu (expect 0) → %s\n",
            loader.loaded_count(), ok ? "PASS" : "FAIL");

    fs::remove(tiny_so);
    fs::remove(tiny_sig);
    return ok ? 0 : 1;
}

// ============================================================================
int main() {
    setup_tmpdir();
    int failures = 0;

    failures += test_sign_1();
    failures += test_sign_2();
    failures += test_sign_3();
    failures += test_sign_4();
    failures += test_sign_5();
    failures += test_sign_6();
    failures += test_sign_7();

    cleanup_tmpdir();

    fprintf(stderr, "\n=== TEST-INTEG-SIGN: %s (%d failures) ===\n",
            failures == 0 ? "PASSED" : "FAILED", failures);
    return failures == 0 ? 0 : 1;
}
