#pragma once

#include <string>
#include <memory>
#include <bpf/libbpf.h>
#include <bpf/bpf.h>
#include <vector>
#include <algorithm>
// sniffer/src/userspace/ebpf_loader.hpp

namespace sniffer {

class EbpfLoader {
public:
    EbpfLoader();
    ~EbpfLoader();

    // Cargar programa eBPF desde archivo objeto
    bool load_program(const std::string& bpf_obj_path);
    
    // Adjuntar programa XDP a interfaz
    bool attach_xdp(const std::string& interface_name);
    
    // Adjuntar programa SKB (TC) a interfaz
    bool attach_skb(const std::string& interface_name);

    // Desadjuntar programa XDP de interfaz
    bool detach_xdp(const std::string& interface_name);

    // Desadjuntar programa SKB de interfaz
    bool detach_skb(const std::string& interface_name);
    
    // Obtener file descriptor del ring buffer map
    int get_ringbuf_fd() const;
    
    // Obtener file descriptor del stats map
    int get_stats_fd() const;

    // Get filter map file descriptors
    int get_excluded_ports_fd() const { return excluded_ports_fd_; }
    int get_included_ports_fd() const { return included_ports_fd_; }
    int get_filter_settings_fd() const { return filter_settings_fd_; }
    int get_interface_configs_fd() const { return interface_configs_fd_; }

    // [DDOS-KAGG-D273:LOADER-HPP-API] Agregador DDoS en-kernel (mapa `ddos_victims`).
    // fd = -1 / max_entries = 0 si el .bpf.o cargado no lo trae (objeto anterior al parche).
    int get_ddos_victims_fd() const { return ddos_victims_fd_; }
    uint32_t get_ddos_victims_max_entries() const { return ddos_victims_max_entries_; }

    // Verificar si el programa está cargado y adjuntado
    bool is_loaded() const { return program_loaded_; }
    bool is_attached() const { return xdp_attached_; }
    
    // Obtener estadísticas del programa eBPF
    uint64_t get_packet_count();
    
private:
    struct bpf_object* bpf_obj_;
    struct bpf_program* xdp_prog_;
    struct bpf_map* events_map_;
    struct bpf_map* stats_map_;

    struct bpf_map* excluded_ports_map_ = nullptr;
    struct bpf_map* included_ports_map_ = nullptr;
    struct bpf_map* filter_settings_map_ = nullptr;
    struct bpf_map* interface_configs_map_ = nullptr;  // <<< AÑADIR
    int prog_fd_;
    int events_fd_;
    int stats_fd_;

    int excluded_ports_fd_ = -1;
    int included_ports_fd_ = -1;
    int filter_settings_fd_ = -1;
    int interface_configs_fd_ = -1;

    // [DDOS-KAGG-D273:LOADER-HPP-MEM] Agregador DDoS en-kernel
    struct bpf_map* ddos_victims_map_ = nullptr;
    int ddos_victims_fd_ = -1;
    uint32_t ddos_victims_max_entries_ = 0;
    bool program_loaded_;
    bool xdp_attached_;
    bool skb_attached_;
    std::vector<int> attached_ifindexes_;
    
    // Helper para obtener ifindex desde nombre
    int get_ifindex(const std::string& interface_name);
};

} // namespace sniffer
