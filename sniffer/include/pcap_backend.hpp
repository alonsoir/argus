#pragma once
// ADR-029 Variant B — PcapBackend: implementación libpcap de CaptureBackend
// DEBT-VARIANT-B-PCAP-IMPL-001: stub compilable, implementación real pendiente
// DAY 137 — 2026-04-30
#include "capture_backend.hpp"
#include <pcap.h>

namespace sniffer {

// Datos pasados como 'user' a pcap_dispatch — evita friend/acceso privado
//
// CONTRATO DE LIFETIME (DEBT-PCAP-CALLBACK-LIFETIME-DOC-001):
//   - PcapCallbackData debe permanecer válido durante toda la sesión de captura.
//   - No destruir PcapBackend mientras pcap_dispatch() esté activo.
//   - La señalización asíncrona (stop desde otro hilo) no está soportada:
//     usar poll() con timeout y verificar condición de parada en el caller.
struct PcapCallbackData {
    CaptureBackend::PacketCallback cb;
    void* ctx;
};

class PcapBackend : public CaptureBackend {
public:
    PcapBackend();
    ~PcapBackend() override;

    bool open(const std::string& interface,
               int buffer_size_mb,
              PacketCallback cb, void* ctx) override;
    int  poll(int timeout_ms) override;
    void close() override;
    int  get_fd() const override;
    uint64_t get_packet_count() override;

    // Filter map fds — no aplicables en libpcap, heredan -1 de CaptureBackend

private:
    pcap_t*        handle_       = nullptr;
    PacketCallback cb_           = nullptr;
    void*          ctx_          = nullptr;
    PcapCallbackData cb_data_     = {nullptr, nullptr};
    uint64_t       packet_count_ = 0;
    int            pipe_fd_[2]   = {-1, -1};
};

} // namespace sniffer
