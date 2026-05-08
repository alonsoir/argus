// ADR-029 Variant A — EbpfBackend implementation
// DAY 137 — 2026-04-30
#include "ebpf_backend.hpp"
#include <bpf/libbpf.h>
#include <iostream>

namespace sniffer {

EbpfBackend::EbpfBackend()
    : loader_(std::make_unique<EbpfLoader>()) {}

EbpfBackend::~EbpfBackend() {
    close();
}

bool EbpfBackend::open(const std::string& interface,
                        PacketCallback cb, void* ctx) {
    cb_  = cb;
    ctx_ = ctx;
    if (!loader_->load_program("sniffer.bpf.o")) {
        std::cerr << "❌ [ebpf] Failed to load eBPF program" << std::endl;
        return false;
    }
    if (!loader_->attach_skb(interface)) {
        std::cerr << "❌ [ebpf] Failed to attach to " << interface << std::endl;
        return false;
    }
    ring_buf_ = ring_buffer__new(loader_->get_ringbuf_fd(), cb_, ctx_, nullptr);
    if (!ring_buf_) {
        std::cerr << "❌ [ebpf] Failed to create ring buffer" << std::endl;
        return false;
    }
    std::cout << "✅ [ebpf] Variant A — eBPF/XDP attached to " << interface << std::endl;
    return true;
}

int EbpfBackend::poll(int timeout_ms) {
    if (!ring_buf_) return -1;
    return ring_buffer__poll(ring_buf_, timeout_ms);
}

void EbpfBackend::close() {
    if (ring_buf_) {
        ring_buffer__free(ring_buf_);
        ring_buf_ = nullptr;
    }
}

int EbpfBackend::get_fd() const {
    return loader_ ? loader_->get_ringbuf_fd() : -1;
}

uint64_t EbpfBackend::get_packet_count() {
    return loader_ ? loader_->get_packet_count() : 0;
}

int EbpfBackend::get_excluded_ports_fd()    const { return loader_ ? loader_->get_excluded_ports_fd()    : -1; }
int EbpfBackend::get_included_ports_fd()    const { return loader_ ? loader_->get_included_ports_fd()    : -1; }
int EbpfBackend::get_filter_settings_fd()   const { return loader_ ? loader_->get_filter_settings_fd()   : -1; }
int EbpfBackend::get_interface_configs_fd() const { return loader_ ? loader_->get_interface_configs_fd() : -1; }

} // namespace sniffer
