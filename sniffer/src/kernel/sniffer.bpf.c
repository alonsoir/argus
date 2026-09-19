//sniffer/src/kernel/sniffer.bpf.c
// Enhanced eBPF sniffer v3.3 - Hybrid filtering + Dual-NIC deployment
// Supports both blacklist (excluded_ports) and whitelist (included_ports)
// Phase 1, Day 7: Added dual-NIC deployment support

// Type definitions
typedef unsigned char __u8;
typedef unsigned short __u16;
typedef unsigned int __u32;
typedef unsigned long long __u64;
typedef signed char __s8;
typedef signed short __s16;
typedef signed int __s32;
typedef signed long long __s64;

typedef __u16 __be16;
typedef __u32 __be32;
typedef __u64 __be64;
typedef __u32 __wsum;

struct iphdr;
struct ipv6hdr;
struct tcphdr;
struct __sk_buff;

#include <bpf/bpf_helpers.h>

// Basic definitions
#define ETH_HLEN 14
#define XDP_PASS 2
#define BPF_MAP_TYPE_RINGBUF 27
#define BPF_MAP_TYPE_ARRAY 2
#define BPF_MAP_TYPE_HASH 1
#define BPF_ANY 0
/* [DDOS-KAGG-D273:DEFS] agregador DDoS en-kernel */
#define BPF_NOEXIST 1
#define BPF_MAP_TYPE_LRU_HASH 9

// TCP flags
#define TCP_FLAG_FIN 0x01
#define TCP_FLAG_SYN 0x02
#define TCP_FLAG_RST 0x04
#define TCP_FLAG_PSH 0x08
#define TCP_FLAG_ACK 0x10
#define TCP_FLAG_URG 0x20
#define TCP_FLAG_ECE 0x40
#define TCP_FLAG_CWR 0x80

// Filter actions
#define ACTION_DROP 0
#define ACTION_CAPTURE 1

// ============================================================================
// DUAL-NIC DEPLOYMENT SUPPORT - Phase 1, Day 7
// ============================================================================

// Interface deployment modes
#define INTERFACE_MODE_DISABLED    0
#define INTERFACE_MODE_HOST_BASED  1  // Capture only traffic destined to host
#define INTERFACE_MODE_GATEWAY     2  // Capture ALL transit traffic (inline)

// Interface configuration (populated from userspace)
struct interface_config {
    __u32 ifindex;           // Network interface index
    __u8 mode;               // 0=disabled, 1=host-based, 2=gateway
    __u8 is_wan;             // 1=WAN-facing (internet), 0=LAN-facing (DMZ)
    __u8 reserved[2];        // Alignment padding
};

// BPF map: Interface configurations (key=ifindex, value=config)
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 16);              // Support up to 16 NICs
    __type(key, __u32);                    // ifindex
    __type(value, struct interface_config);
} iface_configs SEC(".maps");

// XDP context
struct xdp_md {
    __u32 data;
    __u32 data_end;
    __u32 data_meta;
    __u32 ingress_ifindex;
    __u32 rx_queue_index;
    __u32 egress_ifindex;
};

// Event structure
struct simple_event {
    __u32 src_ip;
    __u32 dst_ip;
    __u16 src_port;
    __u16 dst_port;
    __u8 protocol;
    __u8 tcp_flags;
    __u32 packet_len;
    __u16 ip_header_len;
    __u16 l4_header_len;
    __u64 timestamp;
    __u16 payload_len;
    __u8 payload[512];

    // Dual-NIC deployment metadata (Phase 1, Day 7)
    __u8 interface_mode;     // 0=disabled, 1=host-based, 2=gateway
    __u8 is_wan_facing;      // 1=WAN, 0=LAN
    __u32 source_ifindex;    // Network interface index where packet arrived
    char source_interface[16]; // Interface name (e.g., "eth0", "eth1")
} __attribute__((packed));

// Filter configuration
struct filter_config {
    __u8 default_action;  // 0 = drop, 1 = capture
    __u8 reserved[7];
};

// 🔥 MAP 1: Excluded ports (blacklist)
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 1024);
    __type(key, __u16);    // Port number
    __type(value, __u8);   // 1 = excluded
} excluded_ports SEC(".maps");

// 🔥 MAP 2: Included ports (whitelist - HIGH PRIORITY)
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 1024);
    __type(key, __u16);    // Port number
    __type(value, __u8);   // 1 = included
} included_ports SEC(".maps");

// 🔥 MAP 3: Global filter settings
struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, struct filter_config);
} filter_settings SEC(".maps");

// Ring buffer for events
struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 1 << 20);  // 1MB
} events SEC(".maps");

// Statistics
struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, __u64);
} stats SEC(".maps");

/* [DDOS-KAGG-D273:MAP] Agregador DDoS en-kernel: contadores MONOTONOS por victima.
 * Clave = dst_ip + protocolo. Userspace lee cada T s; delta = ventana tumbling.
 * dst_ip en orden numerico (a.b.c.d = a<<24|b<<16|c<<8|d), IDENTICO a
 * event->dst_ip: userspace debe interpretarlo igual que ya interpreta ese campo
 * (ver DEBT-SNIFFER-IP-BYTE-ORDER-001).
 * proto es __u32 (no __u8) a proposito: sin padding en la clave, el verificador
 * exige que todos los bytes de la clave en pila esten inicializados.
 * LRU: el desalojo de una victima fria es benigno (no esta bajo flood). */
struct ddos_key {
    __u32 dst_ip;
    __u32 proto;
};
struct ddos_val {
    __u64 pkts;
    __u64 bytes;
};
struct {
    __uint(type, BPF_MAP_TYPE_LRU_HASH);
    __uint(max_entries, 65536);
    __type(key, struct ddos_key);
    __type(value, struct ddos_val);
} ddos_victims SEC(".maps");

// 🔥 FILTER LOGIC: Decide if port should be captured
// Returns: 1 = capture, 0 = drop
static __always_inline int should_capture_port(__u16 port) {
    // STEP 1: Check whitelist (HIGHEST PRIORITY)
    __u8 *included = bpf_map_lookup_elem(&included_ports, &port);
    if (included && *included == 1) {
        return ACTION_CAPTURE;  // ✅ Whitelist always wins
    }

    // STEP 2: Check blacklist
    __u8 *excluded = bpf_map_lookup_elem(&excluded_ports, &port);
    if (excluded && *excluded == 1) {
        return ACTION_DROP;  // ❌ In blacklist, drop
    }

    // STEP 3: Apply default action
    __u32 key = 0;
    struct filter_config *config = bpf_map_lookup_elem(&filter_settings, &key);
    if (config) {
        return config->default_action;
    }

    return ACTION_CAPTURE;  // Fallback: capture
}

// Helper: Extract TCP flags
static __always_inline __u8 extract_tcp_flags(void *tcp_start, void *data_end) {
    if (tcp_start + 20 > data_end)
        return 0;
    __u8 *tcp = (__u8*)tcp_start;
    return tcp[13];  // Flags byte
}

// Helper: Get TCP header length
static __always_inline __u16 get_tcp_header_len(void *tcp_start, void *data_end) {
    if (tcp_start + 13 > data_end)
        return 0;
    __u8 *tcp = (__u8*)tcp_start;
    __u8 data_offset = (tcp[12] >> 4) & 0x0F;
    return data_offset * 4;
}

SEC("xdp")
int xdp_sniffer_enhanced(struct xdp_md *ctx) {
    void *data = (void *)(long)ctx->data;
    void *data_end = (void *)(long)ctx->data_end;

    // Dual-NIC deployment support - check interface config
    __u32 ifindex = ctx->ingress_ifindex;
    struct interface_config *iface_config = bpf_map_lookup_elem(&iface_configs, &ifindex);

    // If interface not configured or disabled, pass packet without processing
    if (!iface_config || iface_config->mode == INTERFACE_MODE_DISABLED) {
        return XDP_PASS;
    }

    // Verify ethernet header
    if (data + ETH_HLEN > data_end)
        return XDP_PASS;

    void *ip_start = data + ETH_HLEN;

    // Verify IP header
    if (ip_start + 20 > data_end)
        return XDP_PASS;

    __u8 *ip = (__u8*)ip_start;

    // Verify IPv4
    if ((ip[0] >> 4) != 4)
        return XDP_PASS;

    /* [DDOS-KAGG-D273:COUNT] Conteo por victima ANTES del reserve: independiente del ring,
     * asi no hereda la perdida que queremos medir. Cuenta todo IPv4 de una
     * interfaz activa, incluidos puertos que should_capture_port() descartaria
     * mas abajo (el filtro por puerto es del camino ring, no de este). */
    {
        struct ddos_key dk = {
            .dst_ip = ((__u32)ip[16] << 24) | ((__u32)ip[17] << 16) |
                      ((__u32)ip[18] << 8)  |  (__u32)ip[19],
            .proto  = ip[9],
        };
        __u64 wlen = (__u64)(data_end - data);
        struct ddos_val *dv = bpf_map_lookup_elem(&ddos_victims, &dk);
        if (!dv) {
            /* Primera vez que se ve la victima. NOEXIST + re-lookup: si otra CPU
             * inserto a la vez, el update falla con EEXIST y el re-lookup coge
             * la entrada ganadora; no se pierde ningun conteo. */
            struct ddos_val nv = { .pkts = 0, .bytes = 0 };
            bpf_map_update_elem(&ddos_victims, &dk, &nv, BPF_NOEXIST);
            dv = bpf_map_lookup_elem(&ddos_victims, &dk);
        }
        if (dv) {
            __sync_fetch_and_add(&dv->pkts, 1);
            __sync_fetch_and_add(&dv->bytes, wlen);
        }
    }

    // Reserve ring buffer space
    struct simple_event *event = bpf_ringbuf_reserve(&events, sizeof(*event), 0);
    if (!event) {
        return XDP_PASS;
    }

    __builtin_memset(event, 0, sizeof(*event));

    // Extract IPs
    event->src_ip = (ip[12] << 24) | (ip[13] << 16) | (ip[14] << 8) | ip[15];
    event->dst_ip = (ip[16] << 24) | (ip[17] << 16) | (ip[18] << 8) | ip[19];

    // Protocol
    event->protocol = ip[9];

    // Packet length
    event->packet_len = data_end - data;

    // IP header length
    __u8 ihl = (ip[0] & 0x0F) * 4;
    event->ip_header_len = ihl;

    // Timestamp
    event->timestamp = bpf_ktime_get_ns();

    // Layer 4 processing
    void *l4_start = ip_start + ihl;

    if (event->protocol == 6) {
        // ============ TCP ============
        if (l4_start + 4 > data_end) {
            bpf_ringbuf_discard(event, 0);
            return XDP_PASS;
        }

        __u8 *tcp = (__u8*)l4_start;

        // Extract ports
        event->src_port = (tcp[0] << 8) | tcp[1];
        event->dst_port = (tcp[2] << 8) | tcp[3];

        // 🔥 APPLY FILTER - Check destination port
        if (!should_capture_port(event->dst_port)) {
            bpf_ringbuf_discard(event, 0);
            return XDP_PASS;
        }

        // 🔥 APPLY FILTER - Check source port
        if (!should_capture_port(event->src_port)) {
            bpf_ringbuf_discard(event, 0);
            return XDP_PASS;
        }

        // Extract TCP flags
        event->tcp_flags = extract_tcp_flags(l4_start, data_end);

        // TCP header length
        event->l4_header_len = get_tcp_header_len(l4_start, data_end);

    } else if (event->protocol == 17) {
        // ============ UDP ============
        if (l4_start + 4 > data_end) {
            bpf_ringbuf_discard(event, 0);
            return XDP_PASS;
        }

        __u8 *udp = (__u8*)l4_start;

        // Extract ports
        event->src_port = (udp[0] << 8) | udp[1];
        event->dst_port = (udp[2] << 8) | udp[3];

        // 🔥 APPLY FILTER - Check destination port
        if (!should_capture_port(event->dst_port)) {
            bpf_ringbuf_discard(event, 0);
            return XDP_PASS;
        }

        // 🔥 APPLY FILTER - Check source port
        if (!should_capture_port(event->src_port)) {
            bpf_ringbuf_discard(event, 0);
            return XDP_PASS;
        }

        // UDP header is always 8 bytes
        event->l4_header_len = 8;
        event->tcp_flags = 0;

    } else {
        // ============ OTHER PROTOCOLS ============
        event->src_port = 0;
        event->dst_port = 0;
        event->tcp_flags = 0;
        event->l4_header_len = 0;
    }

    // ===== Payload Capture with eBPF Verifier Compliance =====
    // Calculate payload start (after IP + L4 headers)
    void *payload_start = ip_start + ihl + event->l4_header_len;

    // Initialize payload_len to 0
    event->payload_len = 0;

    // Bounds check: ensure payload_start is within packet
    if (payload_start < data_end && payload_start >= data) {
        // Copy up to 512 bytes with explicit bounds checking
        #pragma unroll
        for (int i = 0; i < 512; i++) {
            // eBPF verifier requires explicit check on every iteration
            if (payload_start + i >= data_end) {
                break;
            }

            // Safe copy with bounds verification
            event->payload[i] = *(__u8*)(payload_start + i);
            event->payload_len++;
        }
    }

    // Populate dual-NIC metadata before submit
    event->interface_mode = iface_config->mode;
    event->is_wan_facing = iface_config->is_wan;
    event->source_ifindex = ifindex;

    // Store interface index as string (userspace will resolve to name)
    __builtin_memset(event->source_interface, 0, sizeof(event->source_interface));
    if (ifindex < 100) {  // Sanity check
        // Simple ifindex to string conversion
        event->source_interface[0] = 'i';
        event->source_interface[1] = 'f';
        event->source_interface[2] = '0' + (ifindex / 10);
        event->source_interface[3] = '0' + (ifindex % 10);
    }

    // Submit event to ring buffer
    bpf_ringbuf_submit(event, 0);

    // Update statistics
    __u32 key = 0;
    __u64 *count = bpf_map_lookup_elem(&stats, &key);
    if (count)
        __sync_fetch_and_add(count, 1);
    else {
        __u64 initial = 1;
        bpf_map_update_elem(&stats, &key, &initial, BPF_ANY);
    }

    return XDP_PASS;
}

char _license[] SEC("license") = "GPL";