// test_community_id.cpp — RED->GREEN contra el oráculo pycommunityid (seed 0).
// Vectores generados DAY 170. NO editar a mano: regenerar con el fixture.
#include "flow/community_id.hpp"

#include <cstdint>
#include <iostream>
#include <string>

namespace {

struct Vec {
    const char* proto_name;
    uint8_t     proto;
    const char* saddr;
    const char* daddr;
    uint16_t    sport;
    uint16_t    dport;
    const char* expected;
};

// Fuente: pycommunityid (Corelight spec v1, seed=0).
const Vec kVectors[] = {
    {"tcp", 6,  "128.232.110.120", "66.35.250.204",   34855, 80,  "1:LQU9qZlK+B5F3KDmev6m5PMibrg="},
    {"tcp", 6,  "10.0.0.5",        "10.0.0.9",         51000, 443, "1:4Njg2koYznoNULhUQ6zl1H6JDJg="},
    {"tcp", 6,  "10.0.0.9",        "10.0.0.5",         443,   51000,"1:4Njg2koYznoNULhUQ6zl1H6JDJg="}, // reverso == mismo id
    {"udp", 17, "192.168.100.50",  "192.168.100.1",    40000, 53,  "1:v81UNOpRIu1PJHhuyINajs/4ngU="},
    {"udp", 17, "8.8.8.8",         "192.168.100.50",   53,    40000,"1:O0ZgUUNNqNn7BDaMAHxe/vhZFTE="},
    {"tcp", 6,  "192.168.100.50",  "192.168.100.10",   55000, 22,  "1:7CixKDbKMG7dOCBrqbEhvutXv8Y="},
};

}  // namespace

int main() {
    int failed = 0;
    int total = 0;
    for (const auto& v : kVectors) {
        ++total;
        auto got = sniffer::flow::compute_community_id(v.saddr, v.daddr, v.sport, v.dport, v.proto);
        const std::string g = got.value_or("<nullopt>");
        const bool ok = (g == v.expected);
        std::cout << (ok ? "  PASS  " : "  FAIL  ")
                  << v.proto_name << " " << v.saddr << ":" << v.sport
                  << " -> " << v.daddr << ":" << v.dport << "  " << g << "\n";
        if (!ok) {
            std::cout << "        expected: " << v.expected << "\n";
            ++failed;
        }
    }

    ++total;
    auto ab = sniffer::flow::compute_community_id("172.16.0.1", "172.16.0.2", 1234, 5678, 6);
    auto ba = sniffer::flow::compute_community_id("172.16.0.2", "172.16.0.1", 5678, 1234, 6);
    if (ab && ba && *ab == *ba) {
        std::cout << "  PASS  bidireccional A->B == B->A  " << *ab << "\n";
    } else {
        std::cout << "  FAIL  bidireccional\n";
        ++failed;
    }

    ++total;
    auto icmp = sniffer::flow::compute_community_id("10.0.0.1", "10.0.0.2", 0, 0, 1);
    if (!icmp.has_value()) {
        std::cout << "  PASS  ICMP diferido -> nullopt\n";
    } else {
        std::cout << "  FAIL  ICMP debería ser nullopt\n";
        ++failed;
    }

    std::cout << "\n" << (total - failed) << "/" << total << " OK\n";
    return failed == 0 ? 0 : 1;
}