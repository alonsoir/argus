// ADR-029 Variant B — PcapBackend implementation
// DEBT-VARIANT-B-PCAP-IMPL-001: pcap_dispatch → callback → ZeroMQ pipeline
// DAY 138 — 2026-05-01
#include "pcap_backend.hpp"
#include <iostream>
#include <unistd.h>

namespace sniffer {

// Static callback requerido por pcap_dispatch.
// user apunta a PcapCallbackData — sin acceso a miembros privados.
static void pcap_packet_handler(u_char* user,
                                const struct pcap_pkthdr* hdr,
                                const u_char* data) {
    auto* d = reinterpret_cast<PcapCallbackData*>(user);
    if (d->cb && data && hdr->caplen > 0)
        d->cb(d->ctx,
              const_cast<void*>(reinterpret_cast<const void*>(data)),
              static_cast<size_t>(hdr->caplen));
}

PcapBackend::PcapBackend() {
    pipe_fd_[0] = pipe_fd_[1] = -1;
}

PcapBackend::~PcapBackend() {
    close();
}

bool PcapBackend::open(const std::string& interface,
                        int buffer_size_mb,
                        PacketCallback cb, void* ctx) {
    cb_  = cb;
    ctx_ = ctx;
    cb_data_ = {cb, ctx};

    char errbuf[PCAP_ERRBUF_SIZE];

    // DEBT-VARIANT-B-BUFFER-SIZE-001 closed DAY 142
    // pcap_create()+pcap_set_buffer_size()+pcap_activate()
    // Critico en ARM64/RPi donde kernel default es 2MB
    handle_ = pcap_create(interface.c_str(), errbuf);
    if (!handle_) {
        std::cerr << "[pcap] pcap_create: " << errbuf << std::endl;
        return false;
    }
    int buffer_bytes = buffer_size_mb * 1024 * 1024;
    if (pcap_set_buffer_size(handle_, buffer_bytes) != 0) {
        std::cerr << "[pcap] pcap_set_buffer_size(" << buffer_size_mb
                  << "MB) failed: " << pcap_geterr(handle_) << std::endl;
        pcap_close(handle_); handle_ = nullptr; return false;
    }
    pcap_set_snaplen(handle_, 65535);
    pcap_set_promisc(handle_, 1);
    pcap_set_timeout(handle_, 1000);
    int rc = pcap_activate(handle_);
    if (rc < 0) {
        std::cerr << "[pcap] pcap_activate: " << pcap_statustostr(rc) << std::endl;
        pcap_close(handle_); handle_ = nullptr; return false;
    }
    if (rc > 0)
        std::cerr << "[pcap] pcap_activate warning: " << pcap_statustostr(rc) << std::endl;
    if (pipe(pipe_fd_) != 0) {
        std::cerr << "[pcap] pipe() failed" << std::endl;
        pcap_close(handle_); handle_ = nullptr; return false;
    }
    std::cout << "[pcap] Variant B opened on " << interface
              << " buffer=" << buffer_size_mb << "MB" << std::endl;
    return true;
}

// poll(): despacha hasta 64 paquetes por llamada, no bloqueante.
// Retorna: >0 pkts procesados, 0 timeout/vacío, <0 error.
int PcapBackend::poll(int /*timeout_ms*/) {
    if (!handle_) return -1;
    int n = pcap_dispatch(handle_, 64,
                          pcap_packet_handler,
                          reinterpret_cast<u_char*>(&cb_data_));
    if (n > 0)
        packet_count_ += static_cast<uint64_t>(n);
    else if (n < 0 && n != PCAP_ERROR_BREAK)
        std::cerr << "❌ [pcap] pcap_dispatch error: "
                  << pcap_geterr(handle_) << std::endl;
    return n;
}

void PcapBackend::close() {
    if (handle_) {
        pcap_close(handle_);
        handle_ = nullptr;
    }
    if (pipe_fd_[0] != -1) { ::close(pipe_fd_[0]); pipe_fd_[0] = -1; }
    if (pipe_fd_[1] != -1) { ::close(pipe_fd_[1]); pipe_fd_[1] = -1; }
}

int PcapBackend::get_fd() const {
    return pipe_fd_[0];
}

uint64_t PcapBackend::get_packet_count() {
    return packet_count_;
}

} // namespace sniffer
