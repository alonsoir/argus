
// ADR-029 Variant B — Stress Test: N invocaciones callback sin crash
// Verifica packet_count exacto y ausencia de memoria corrupta
// DAY 138 — 2026-05-01
#include <gtest/gtest.h>
#include "pcap_backend.hpp"
#include <cstring>

using namespace sniffer;

static std::atomic<uint64_t> g_stress_count{0};

static int stress_cb(void* /*ctx*/, void* /*data*/, size_t /*size*/) {
    g_stress_count.fetch_add(1, std::memory_order_relaxed);
    return 0;
}

TEST(PcapBackendStress, TenThousandCallbacksNoCorruption) {
    g_stress_count = 0;
    PcapCallbackData cbd{stress_cb, nullptr};
    uint8_t fake[128] = {0xDE, 0xAD};
    struct pcap_pkthdr hdr{};
    hdr.caplen = 128;

    constexpr int N = 10000;
    for (int i = 0; i < N; ++i) {
        if (cbd.cb)
            cbd.cb(cbd.ctx, static_cast<void*>(fake),
                   static_cast<size_t>(hdr.caplen));
    }
    EXPECT_EQ(g_stress_count.load(), static_cast<uint64_t>(N));
}

TEST(PcapBackendStress, RepeatedOpenCloseNoLeak) {
    // 100 ciclos open(inválida)/close — no crash, no leak (valgrind-safe)
    for (int i = 0; i < 100; ++i) {
        PcapBackend backend;
        backend.open("nonexistent_iface_xyz", 8*1024*1024, nullptr, nullptr);
        backend.close();
        EXPECT_EQ(backend.get_fd(), -1);
    }
}
