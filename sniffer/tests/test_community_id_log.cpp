// test_community_id_log.cpp — la línea nace verificada (TDH), robusto a NDEBUG
#include "flow/community_id.hpp"
#include "flow/community_id_log.hpp"
#include <cstdlib>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

static bool fail(const char* msg) { std::fprintf(stderr, "FAIL: %s\n", msg); return false; }

int main() {
    const char* tmp = "/tmp/cid_xcheck_test.tsv";
    std::remove(tmp);
    setenv("ARGUS_CID_CROSSCHECK_PATH", tmp, 1);

    // Diana DAY 170: tcp 147.32.84.165:1027 -> 74.125.232.195:80 (seed 0)
    const std::string saddr = "147.32.84.165", daddr = "74.125.232.195";
    const uint16_t sport = 1027, dport = 80; const uint8_t proto = 6;

    auto cid = sniffer::flow::compute_community_id(saddr, daddr, sport, dport, proto);
    if (!cid) return fail("compute_community_id devolvió nullopt para TCP") ? 0 : 1;
    if (*cid != "1:IN7uqVpMWxpmuhQTowSQB2XEe0E=") return fail("cid != diana DAY 170") ? 0 : 1;

    sniffer::flow::log_community_id_emission(*cid, saddr, daddr, sport, dport, proto);

    std::ifstream f(tmp);
    if (!f.is_open()) return fail("el helper no creó el fichero") ? 0 : 1;
    std::string line; std::getline(f, line);

    std::vector<std::string> col; std::stringstream ss(line); std::string c;
    while (std::getline(ss, c, '\t')) col.push_back(c);
    if (col.size() != 7) return fail("se esperaban 7 columnas TSV") ? 0 : 1;
    if (col[0] != *cid)  return fail("col 0 != cid") ? 0 : 1;
    if (col[1] != saddr) return fail("col 1 != saddr") ? 0 : 1;
    if (col[2] != daddr) return fail("col 2 != daddr") ? 0 : 1;
    if (col[3] != "1027") return fail("col 3 != sport") ? 0 : 1;
    if (col[4] != "80")   return fail("col 4 != dport") ? 0 : 1;
    if (col[5] != "6")    return fail("col 5 != proto") ? 0 : 1;
    if (std::stoll(col[6]) <= 0) return fail("col 6 (ts) no positivo") ? 0 : 1;

    std::printf("test_community_id_log PASSED: %s\n", line.c_str());
    return 0;
}