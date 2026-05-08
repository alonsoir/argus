#pragma once
// ADR-029 Variant A — EbpfBackend: implementación eBPF/XDP de CaptureBackend
// DAY 137 — 2026-04-30
#include "capture_backend.hpp"
#include "ebpf_loader.hpp"
#include <memory>

namespace sniffer {

class EbpfBackend : public CaptureBackend {
public:
    EbpfBackend();
    ~EbpfBackend() override;

    bool open(const std::string& interface,
              PacketCallback cb, void* ctx) override;
    int  poll(int timeout_ms) override;
    void close() override;
    int  get_fd() const override;
    uint64_t get_packet_count() override;

    int get_excluded_ports_fd()    const;
    int get_included_ports_fd()    const;
    int get_filter_settings_fd()   const;
    int get_interface_configs_fd() const;

    // eBPF-specific: attach/detach XDP/SKB program
    bool attach_skb(const std::string& iface);
    bool detach_skb(const std::string& iface);

    // eBPF-specific: ring buffer fd alias
    int get_ringbuf_fd() const;

    // Acceso directo al loader para BPFMapManager (main.cpp)
    EbpfLoader& loader() { return *loader_; }

private:
    std::unique_ptr<EbpfLoader> loader_;
    struct ring_buffer* ring_buf_ = nullptr;
    PacketCallback cb_  = nullptr;
    void*          ctx_ = nullptr;
};

} // namespace sniffer
