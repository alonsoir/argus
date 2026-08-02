#include "host_engine/host_row.hpp"
#include <cassert>
#include <cstdio>
#include <string>
#include <vector>

using namespace host_engine;

static int failures = 0;
#define CHECK(cond) do { if(!(cond)) { \
    std::fprintf(stderr, "FALLO L%d: %s\n", __LINE__, #cond); ++failures; } } while(0)

int main() {
    // 1. lista simple
    {
        auto v = parse_json_string_list("[\"syslog\",\"sudo\"]");
        CHECK(v.size() == 2);
        CHECK(v[0] == "syslog");
        CHECK(v[1] == "sudo");
    }
    // 2. lista vacía y basura -> vacío
    {
        CHECK(parse_json_string_list("[]").empty());
        CHECK(parse_json_string_list("").empty());
        CHECK(parse_json_string_list("null").empty());
    }
    // 3. un elemento
    {
        auto v = parse_json_string_list("[\"T1548.003\"]");
        CHECK(v.size() == 1 && v[0] == "T1548.003");
    }
    // 4. escape de comilla interna
    {
        auto v = parse_json_string_list("[\"a\\\"b\"]");
        CHECK(v.size() == 1 && v[0] == "a\"b");
    }
    // 5. zip alineado 1:1 (caso 5715: T1078+T1021)
    {
        bool mism = false;
        auto z = zip_techniques("[\"T1078\",\"T1021\"]",
                                "[\"Valid Accounts\",\"Remote Services\"]", mism);
        CHECK(!mism);
        CHECK(z.size() == 2);
        CHECK(z[0].id == "T1078" && z[0].name == "Valid Accounts");
        CHECK(z[1].id == "T1021" && z[1].name == "Remote Services");
    }
    // 6. zip desalineado -> mismatch, sin inventar
    {
        bool mism = false;
        auto z = zip_techniques("[\"T1078\",\"T1021\"]", "[\"Valid Accounts\"]", mism);
        CHECK(mism);
        CHECK(z.empty());
    }
    // 7. caso 5402/5403: 1 técnica, tácticas planas NO entran en el zip
    {
        bool mism = false;
        auto z = zip_techniques("[\"T1548.003\"]", "[\"Sudo and Sudo Caching\"]", mism);
        CHECK(!mism && z.size() == 1);
        CHECK(z[0].id == "T1548.003" && z[0].name == "Sudo and Sudo Caching");
    }

    if (failures == 0) { std::printf("test_host_row: OK\n"); return 0; }
    std::fprintf(stderr, "test_host_row: %d fallos\n", failures);
    return 1;
}