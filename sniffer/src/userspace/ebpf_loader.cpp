#include "ebpf_loader.hpp"
#include "ddos_kernel_agg.hpp"  // [DDOS-KAGG-D273:LOADER-CPP-INC] layout de ddos_key/ddos_val
#include <iostream>
#include <cstring>
#include <unistd.h>
#include <net/if.h>
#include <linux/if_link.h>
#include <fcntl.h>
// sniffer/src/userspace/ebpf_loader.hpp

namespace sniffer {

EbpfLoader::EbpfLoader() 
    : bpf_obj_(nullptr), 
      xdp_prog_(nullptr), 
      events_map_(nullptr), 
      stats_map_(nullptr),
      excluded_ports_map_(nullptr),
      included_ports_map_(nullptr),
      filter_settings_map_(nullptr),
      prog_fd_(-1), 
      events_fd_(-1), 
      stats_fd_(-1),
      excluded_ports_fd_(-1),
      included_ports_fd_(-1),
      filter_settings_fd_(-1),
      program_loaded_(false),
      xdp_attached_(false),
      skb_attached_(false){}

    EbpfLoader::~EbpfLoader() {
    // Guardar stderr original
    int stderr_backup = dup(STDERR_FILENO);

    // Redirigir stderr a /dev/null para suprimir warnings de libbpf
    // (es normal que el qdisc ya no exista al limpiar)
    int devnull = open("/dev/null", O_WRONLY);
    if (devnull >= 0) {
        dup2(devnull, STDERR_FILENO);
        close(devnull);
    }

    if (skb_attached_) {
        // Desadjuntar de TODAS las interfaces
        for (int ifindex : attached_ifindexes_) {
            int err = bpf_xdp_detach(ifindex, 0, nullptr);
            if (err) {
                // Silencioso - ya redirigimos stderr a /dev/null
            }
        }
    }

    // Restaurar stderr
    if (stderr_backup >= 0) {
        dup2(stderr_backup, STDERR_FILENO);
        close(stderr_backup);
    }

    if (bpf_obj_) {
        bpf_object__close(bpf_obj_);
        std::cout << "[INFO] eBPF object closed" << std::endl;
    }
}

bool EbpfLoader::load_program(const std::string& bpf_obj_path) {
    std::cout << "[INFO] Loading eBPF program from: " << bpf_obj_path << std::endl;
    
    // Abrir objeto eBPF
    bpf_obj_ = bpf_object__open(bpf_obj_path.c_str());
    if (!bpf_obj_) {
        std::cerr << "[ERROR] Failed to open eBPF object: " << bpf_obj_path << std::endl;
        return false;
    }
    
    // Cargar programa en el kernel
    int err = bpf_object__load(bpf_obj_);
    if (err) {
        std::cerr << "[ERROR] Failed to load eBPF program: " << strerror(-err) << std::endl;
        bpf_object__close(bpf_obj_);
        bpf_obj_ = nullptr;
        return false;
    }
    
    // Obtener el programa XDP. Está definido en src/kernel/sniffer.bpf.c
    xdp_prog_ = bpf_object__find_program_by_name(bpf_obj_, "xdp_sniffer_enhanced");
    if (!xdp_prog_) {
        std::cerr << "[ERROR] Failed to find XDP program 'xdp_sniffer_enhanced'" << std::endl;
        bpf_object__close(bpf_obj_);
        bpf_obj_ = nullptr;
        return false;
    }
    
    prog_fd_ = bpf_program__fd(xdp_prog_);
    if (prog_fd_ < 0) {
        std::cerr << "[ERROR] Failed to get program file descriptor" << std::endl;
        bpf_object__close(bpf_obj_);
        bpf_obj_ = nullptr;
        return false;
    }
    
    // Obtener maps
    events_map_ = bpf_object__find_map_by_name(bpf_obj_, "events");
    if (!events_map_) {
        std::cerr << "[ERROR] Failed to find 'events' map" << std::endl;
        bpf_object__close(bpf_obj_);
        bpf_obj_ = nullptr;
        return false;
    }
    
    stats_map_ = bpf_object__find_map_by_name(bpf_obj_, "stats");
    if (!stats_map_) {
        std::cerr << "[ERROR] Failed to find 'stats' map" << std::endl;
        bpf_object__close(bpf_obj_);
        bpf_obj_ = nullptr;
        return false;
    }
    
    events_fd_ = bpf_map__fd(events_map_);
    stats_fd_ = bpf_map__fd(stats_map_);
    
    if (events_fd_ < 0 || stats_fd_ < 0) {
        std::cerr << "[ERROR] Failed to get map file descriptors" << std::endl;
        bpf_object__close(bpf_obj_);
        bpf_obj_ = nullptr;
        return false;
    }

    // Get filter maps
    excluded_ports_map_ = bpf_object__find_map_by_name(bpf_obj_, "excluded_ports");
    if (excluded_ports_map_) {
        excluded_ports_fd_ = bpf_map__fd(excluded_ports_map_);
        std::cout << "[INFO] Found excluded_ports map, FD: " << excluded_ports_fd_ << std::endl;
    } else {
        std::cerr << "[WARNING] excluded_ports map not found in eBPF program" << std::endl;
    }

    included_ports_map_ = bpf_object__find_map_by_name(bpf_obj_, "included_ports");
    if (included_ports_map_) {
        included_ports_fd_ = bpf_map__fd(included_ports_map_);
        std::cout << "[INFO] Found included_ports map, FD: " << included_ports_fd_ << std::endl;
    } else {
        std::cerr << "[WARNING] included_ports map not found in eBPF program" << std::endl;
    }

    filter_settings_map_ = bpf_object__find_map_by_name(bpf_obj_, "filter_settings");
    if (filter_settings_map_) {
        filter_settings_fd_ = bpf_map__fd(filter_settings_map_);
        std::cout << "[INFO] Found filter_settings map, FD: " << filter_settings_fd_ << std::endl;
    } else {
        std::cerr << "[WARNING] filter_settings map not found in eBPF program" << std::endl;
    }

    interface_configs_map_ = bpf_object__find_map_by_name(bpf_obj_, "iface_configs");
    if (interface_configs_map_) {
        interface_configs_fd_ = bpf_map__fd(interface_configs_map_);
        std::cout << "[INFO] Found iface_configs map (Dual-NIC), FD: "
                  << interface_configs_fd_ << std::endl;
    } else {
        std::cout << "[INFO] iface_configs map not found (legacy single-interface mode)" << std::endl;
    }

    // [DDOS-KAGG-D273:LOADER-CPP-FIND] Agregador DDoS en-kernel. Opcional: un .bpf.o anterior al parche
    // no lo trae. Si el layout no coincide con ddos_kernel_agg.hpp se desactiva en vez
    // de leer basura.
    ddos_victims_map_ = bpf_object__find_map_by_name(bpf_obj_, "ddos_victims");
    if (ddos_victims_map_) {
        if (bpf_map__key_size(ddos_victims_map_) != sizeof(DdosVictimKey) ||
            bpf_map__value_size(ddos_victims_map_) != sizeof(DdosVictimVal)) {
            std::cerr << "[WARNING] ddos_victims map layout mismatch (key="
                      << bpf_map__key_size(ddos_victims_map_) << " val="
                      << bpf_map__value_size(ddos_victims_map_) << ", expected "
                      << sizeof(DdosVictimKey) << "/" << sizeof(DdosVictimVal)
                      << "); in-kernel DDoS aggregator disabled" << std::endl;
            ddos_victims_map_ = nullptr;
        } else {
            ddos_victims_fd_ = bpf_map__fd(ddos_victims_map_);
            ddos_victims_max_entries_ = bpf_map__max_entries(ddos_victims_map_);
            std::cout << "[INFO] Found ddos_victims map (in-kernel DDoS aggregator), FD: "
                      << ddos_victims_fd_ << ", max_entries: " << ddos_victims_max_entries_
                      << std::endl;
        }
    } else {
        std::cout << "[INFO] ddos_victims map not found (eBPF object without in-kernel DDoS aggregator)"
                  << std::endl;
    }

    program_loaded_ = true;
    std::cout << "[INFO] eBPF program loaded successfully" << std::endl;
    std::cout << "[INFO] Program FD: " << prog_fd_ << ", Events FD: " << events_fd_ 
              << ", Stats FD: " << stats_fd_ << std::endl;
    
    return true;
}

bool EbpfLoader::attach_xdp(const std::string& interface_name) {
    if (!program_loaded_) {
        std::cerr << "[ERROR] Program not loaded. Call load_program() first" << std::endl;
        return false;
    }
    
    int ifindex = get_ifindex(interface_name);
    if (ifindex < 0) {
        std::cerr << "[ERROR] Interface not found: " << interface_name << std::endl;
        return false;
    }
    
    std::cout << "[INFO] Attaching XDP program to interface: " << interface_name 
              << " (ifindex: " << ifindex << ")" << std::endl;
    
    // Adjuntar programa XDP
    int err = bpf_xdp_attach(ifindex, prog_fd_, 0, nullptr);
    if (err) {
        std::cerr << "[ERROR] Failed to attach XDP program: " << strerror(-err) << std::endl;
        return false;
    }
    
    xdp_attached_ = true;

    std::cout << "[INFO] XDP program attached successfully to " << interface_name << std::endl;
    return true;
}

bool EbpfLoader::detach_xdp(const std::string& interface_name) {
    if (!xdp_attached_) {
        std::cout << "[INFO] No XDP program attached" << std::endl;
        return true;
    }
    
    int ifindex = get_ifindex(interface_name);
    if (ifindex < 0) {
        std::cerr << "[ERROR] Interface not found: " << interface_name << std::endl;
        return false;
    }
    
    std::cout << "[INFO] Detaching XDP program from interface: " << interface_name << std::endl;
    
    int err = bpf_xdp_detach(ifindex, 0, nullptr);
    if (err) {
        std::cerr << "[ERROR] Failed to detach XDP program: " << strerror(-err) << std::endl;
        return false;
    }
    
    xdp_attached_ = false;

    std::cout << "[INFO] XDP program detached successfully" << std::endl;
    return true;
}

    bool EbpfLoader::attach_skb(const std::string& interface_name) {
    if (!program_loaded_) {
        std::cerr << "[ERROR] eBPF program not loaded" << std::endl;
        return false;
    }

    int ifindex = get_ifindex(interface_name);
    if (ifindex < 0) {
        std::cerr << "[ERROR] Failed to get interface index for " << interface_name << std::endl;
        return false;
    }

    // Verificar si YA está attached a ESTA interfaz
    if (std::find(attached_ifindexes_.begin(), attached_ifindexes_.end(), ifindex)
        != attached_ifindexes_.end()) {
        std::cout << "[INFO] XDP already attached to " << interface_name << std::endl;
        return true;
        }

    std::cout << "[INFO] Attaching XDP program in SKB/Generic mode to interface: " << interface_name
              << " (ifindex: " << ifindex << ")" << std::endl;

    // XDP_FLAGS_SKB_MODE = modo genérico/software
    __u32 xdp_flags = (1U << 1);

    int err = bpf_xdp_attach(ifindex, prog_fd_, xdp_flags, nullptr);
    if (err) {
        std::cerr << "[ERROR] Failed to attach XDP in SKB mode: " << strerror(-err) << std::endl;
        return false;
    }

    skb_attached_ = true;
    attached_ifindexes_.push_back(ifindex);  // ✅ Agregar a la lista

    std::cout << "[INFO] XDP program attached successfully in SKB/Generic mode to " << interface_name << std::endl;
    return true;
}


bool EbpfLoader::detach_skb(const std::string& interface_name) {
    if (!skb_attached_) {
        return true;
    }

    int ifindex = get_ifindex(interface_name);
    if (ifindex < 0) {
        return false;
    }

    std::cout << "[INFO] Detaching XDP program (SKB mode) from interface: " << interface_name << std::endl;

    // Desadjuntar XDP
    int err = bpf_xdp_detach(ifindex, 0, nullptr);
    if (err) {
        std::cerr << "[WARN] Failed to detach XDP (SKB mode): " << strerror(-err) << std::endl;
    }

    skb_attached_ = false;

    std::cout << "[INFO] XDP program (SKB mode) detached from " << interface_name << std::endl;
    return true;
}

int EbpfLoader::get_ringbuf_fd() const {
    return events_fd_;
}

int EbpfLoader::get_stats_fd() const {
    return stats_fd_;
}

uint64_t EbpfLoader::get_packet_count() {
    if (!program_loaded_ || stats_fd_ < 0) {
        return 0;
    }
    
    uint32_t key = 0;
    uint64_t value = 0;
    
    int err = bpf_map_lookup_elem(stats_fd_, &key, &value);
    if (err) {
        return 0;
    }
    
    return value;
}

int EbpfLoader::get_ifindex(const std::string& interface_name) {
    return if_nametoindex(interface_name.c_str());
}

} // namespace sniffer
