
// ADR-029 Variant B — Unit Test: PcapCallbackData mecanismo de callback
// Verifica que cb() recibe ctx, data y size correctamente
// DAY 138 — 2026-05-01
#include <gtest/gtest.h>
#include "pcap_backend.hpp"
#include <cstring>

using namespace sniffer;

struct CallbackResult {
    void* received_ctx = nullptr;
    void* received_data = nullptr;
    size_t received_size = 0;
    int call_count = 0;
};

static int test_cb(void* ctx, void* data, size_t size) {
    auto* r = reinterpret_cast<CallbackResult*>(ctx);
    r->received_ctx  = ctx;
    r->received_data = data;
    r->received_size = size;
    r->call_count++;
    return 0;
}

TEST(PcapBackendCallback, CallbackDataPropagated) {
    CallbackResult result;
    PcapCallbackData cbd{test_cb, &result};

    uint8_t fake_data[64] = {0xAA};
    struct pcap_pkthdr hdr{};
    hdr.caplen = 64;
    hdr.len    = 64;

    // Invocar el callback directamente via PcapCallbackData
    if (cbd.cb)
        cbd.cb(cbd.ctx,
               static_cast<void*>(fake_data),
               static_cast<size_t>(hdr.caplen));

    EXPECT_EQ(result.call_count, 1);
    EXPECT_EQ(result.received_size, 64u);
    EXPECT_EQ(result.received_data, static_cast<void*>(fake_data));
}

TEST(PcapBackendCallback, NullCallbackDoesNotCrash) {
    PcapCallbackData cbd{nullptr, nullptr};
    EXPECT_NO_THROW({
        if (cbd.cb) cbd.cb(cbd.ctx, nullptr, 0);
    });
}
