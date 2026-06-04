#include <gtest/gtest.h>
#include <nlohmann/json.hpp>
#include <correlation_engine/flow_uid.hpp>
#include <fstream>
#include <map>
#include <string>

using argus::correlation::compute_flow_uid;
using nlohmann::json;

namespace {
json load_vectors() {
    std::ifstream f(VECTORS_PATH);  // ruta inyectada por CMake
    EXPECT_TRUE(f.is_open()) << "no se abre " << VECTORS_PATH;
    json doc; f >> doc; return doc["vectors"];
}
std::map<std::string, std::string> by_id() {
    std::map<std::string, std::string> m;
    for (const auto& v : load_vectors()) m[v["id"]] = v["expected_flow_uid"];
    return m;
}
}  // namespace

// Regresión de encoding: cada vector reproduce su flow_uid congelado.
TEST(FlowUid, MatchesFrozenVectors) {
    for (const auto& v : load_vectors()) {
        EXPECT_EQ(compute_flow_uid(v["node_id"].get<std::string>(),
                                   v["community_id"].get<std::string>(),
                                   v["flow_start_window"].get<uint64_t>(),
                                   v["seq_in_window"].get<uint32_t>()),
                  v["expected_flow_uid"].get<std::string>()) << "vector " << v["id"];
    }
}
TEST(FlowUid, ClosureDistinctNode)    { auto m = by_id(); EXPECT_NE(m["V2"], m["V1"]); }
TEST(FlowUid, ClosureRecycledWindow)  { auto m = by_id(); EXPECT_NE(m["V3"], m["V1"]); }
TEST(FlowUid, ClosureSeqDisambig)     { auto m = by_id(); EXPECT_NE(m["V4"], m["V1"]); }
