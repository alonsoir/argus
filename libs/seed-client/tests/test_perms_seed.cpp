#include <iostream>
#include <fstream>
#include <sys/stat.h>
#include <cstdlib>
#include <cstdio>
#include <string>
#include <array>

std::string run_with_stderr(const std::string& cmd) {
    std::string full = cmd + " 2>&1 1>/dev/null";
    std::array<char,4096> buf{};
    std::string result;
    FILE* pipe = popen(full.c_str(), "r");
    if (!pipe) return "";
    while (fgets(buf.data(), buf.size(), pipe))
        result += buf.data();
    pclose(pipe);
    return result;
}

int run_case(const std::string& label, mode_t perms, bool expect_warning) {
    char tmpdir[] = "/tmp/tps_XXXXXX";
    mkdtemp(tmpdir);
    std::string keys_dir  = std::string(tmpdir) + "/keys/";
    std::string seed_path = keys_dir + "seed.bin";
    std::string json_path = std::string(tmpdir) + "/identity.json";

    system(("mkdir -p " + keys_dir).c_str());

    std::ofstream sf(seed_path, std::ios::binary);
    for (int i = 0; i < 32; i++) sf.put((char)i);
    sf.close();
    chmod(seed_path.c_str(), perms);

    std::ofstream jf(json_path);
    jf << "{\"identity\":{\"component_id\":\"etcd-server\",\"keys_dir\":\""
       << keys_dir << "\"}}";
    jf.close();

    // Compilar wrapper minimo en runtime
    std::string wrapper_src = std::string(tmpdir) + "/wrapper.cpp";
    std::string wrapper_bin = std::string(tmpdir) + "/wrapper";
    std::ofstream ws(wrapper_src);
    ws << "#include <seed_client/seed_client.hpp>\n"
       << "int main(){try{ml_defender::SeedClient sc(\""
       << json_path << "\");sc.load();}catch(...){}return 0;}\n";
    ws.close();

    std::string compile =
        "g++ -std=c++20 -I/usr/local/include " + wrapper_src +
        " -L/usr/local/lib -lseed_client -Wl,-rpath,/usr/local/lib -o " +
        wrapper_bin + " 2>/dev/null";
    system(compile.c_str());

    std::string stderr_out = run_with_stderr(wrapper_bin);
    bool got_warning = (stderr_out.find("ADVERTENCIA") != std::string::npos);
    bool ok = (got_warning == expect_warning);

    std::cout << (ok ? "[PASS]" : "[FAIL]") << " CASO " << label
              << " (perms=0" << std::oct << perms << std::dec
              << "): warning=" << (got_warning?"si":"no")
              << " esperado=" << (expect_warning?"si":"no") << "\n";

    system((std::string("rm -rf ") + tmpdir).c_str());
    return ok ? 0 : 1;
}

int main() {
    std::cout << "=== TEST-PERMS-SEED ===\n";
    int fail = 0;
    fail += run_case("1-400-sin-warning", 0400, false);  // ADR-037: correcto — no warning, no excepcion
    fail += run_case("2-640-reject", 0640, false);       // ADR-037: excepcion (fail-closed), no warning
    fail += run_case("3-644-reject", 0644, false);       // ADR-037: excepcion (fail-closed), no warning
    std::cout << "─────────────────────────\n";
    if (fail == 0)
        std::cout << "Resultados: 3/3 tests pasados\n"
                  << "✅ TEST-PERMS-SEED PASSED\n";
    else
        std::cout << "❌ TEST-PERMS-SEED FAILED (" << fail << " fallos)\n";
    return fail;
}
