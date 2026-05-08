
// ADR-029 Variant B — Regression Test: estado limpio tras ciclos
// DAY 138 — 2026-05-01
#include <gtest/gtest.h>
#include "pcap_backend.hpp"

using namespace sniffer;

TEST(PcapBackendRegression, StateCleanAfterFailedOpen) {
    PcapBackend backend;
    backend.open("nonexistent_iface_xyz", 8*1024*1024, nullptr, nullptr);
    // Estado debe ser limpio: fd=-1, count=0, poll devuelve -1
    EXPECT_EQ(backend.get_fd(), -1);
    EXPECT_EQ(backend.get_packet_count(), 0u);
    EXPECT_EQ(backend.poll(0), -1);
}

TEST(PcapBackendRegression, MultipleDestructorCyclesSafe) {
    for (int i = 0; i < 50; ++i) {
        PcapBackend b;
        b.open("nonexistent_iface_xyz", 8*1024*1024, nullptr, nullptr);
        // destructor al salir del scope
    }
    SUCCEED(); // si llega aquí, no hay crash
}

TEST(PcapBackendRegression, PacketCountNeverDecreases) {
    PcapBackend backend;
    // Sin captura real, count debe mantenerse en 0
    uint64_t prev = backend.get_packet_count();
    for (int i = 0; i < 10; ++i) {
        backend.poll(0); // handle_ nulo, no incrementa
        EXPECT_GE(backend.get_packet_count(), prev);
        prev = backend.get_packet_count();
    }
}
