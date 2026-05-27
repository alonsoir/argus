
// ADR-029 Variant B — Unit Test: PcapBackend error handling
// DAY 138 — 2026-05-01
#include <gtest/gtest.h>
#include "pcap_backend.hpp"

using namespace sniffer;

TEST(PcapBackendError, OpenEmptyIfaceFails) {
    PcapBackend backend;
    EXPECT_FALSE(backend.open("", 8*1024*1024, nullptr, nullptr));
}

TEST(PcapBackendError, OpenNonExistentIfaceFails) {
    PcapBackend backend;
    EXPECT_FALSE(backend.open("zzz_no_such_iface", 8*1024*1024, nullptr, nullptr));
}

TEST(PcapBackendError, DestructorAfterFailedOpenIsSafe) {
    EXPECT_NO_THROW({
        PcapBackend backend;
        backend.open("nonexistent_iface_xyz", 8*1024*1024, nullptr, nullptr);
        // destructor llamado al salir del scope
    });
}
