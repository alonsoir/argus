
// ADR-029 Variant B — Unit Test: PcapBackend lifecycle
// No requiere red real ni root — iface inválida → false limpio
// DAY 138 — 2026-05-01
#include <gtest/gtest.h>
#include "pcap_backend.hpp"

using namespace sniffer;

TEST(PcapBackendLifecycle, OpenInvalidIfaceReturnsFalse) {
    PcapBackend backend;
    bool result = backend.open("nonexistent_iface_xyz", 8*1024*1024, nullptr, nullptr);
    EXPECT_FALSE(result);
}

TEST(PcapBackendLifecycle, CloseAfterFailedOpenIsSafe) {
    PcapBackend backend;
    backend.open("nonexistent_iface_xyz", 8*1024*1024, nullptr, nullptr);
    EXPECT_NO_THROW(backend.close());
}

TEST(PcapBackendLifecycle, CloseIdempotent) {
    PcapBackend backend;
    EXPECT_NO_THROW(backend.close());
    EXPECT_NO_THROW(backend.close());
    EXPECT_NO_THROW(backend.close());
}

TEST(PcapBackendLifecycle, PacketCountZeroOnInit) {
    PcapBackend backend;
    EXPECT_EQ(backend.get_packet_count(), 0u);
}

TEST(PcapBackendLifecycle, FdNegativeBeforeOpen) {
    PcapBackend backend;
    EXPECT_EQ(backend.get_fd(), -1);
}
