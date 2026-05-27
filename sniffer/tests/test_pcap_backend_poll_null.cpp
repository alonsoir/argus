
// ADR-029 Variant B — Unit Test: PcapBackend poll con handle nulo
// DAY 138 — 2026-05-01
#include <gtest/gtest.h>
#include "pcap_backend.hpp"

using namespace sniffer;

TEST(PcapBackendPollNull, PollBeforeOpenReturnsError) {
    PcapBackend backend;
    int result = backend.poll(100);
    EXPECT_EQ(result, -1);
}

TEST(PcapBackendPollNull, PollAfterCloseReturnsError) {
    PcapBackend backend;
    backend.open("nonexistent_iface_xyz", 8*1024*1024, nullptr, nullptr);
    backend.close();
    int result = backend.poll(100);
    EXPECT_EQ(result, -1);
}
