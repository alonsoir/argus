// aRGus NDR — Sniffer Variant B (libpcap)
// ADR-029 — pipeline completo: pcap → protobuf → LZ4 → ChaCha20 → ZeroMQ
// Wire format idéntico a Variant A (ring_consumer.cpp DAY 98)
// DAY 141 — 2026-05-04 — DEBT-VARIANT-B-CONFIG-001: config desde sniffer-libpcap.json
#include "pcap_backend.hpp"
#include "capture_backend.hpp"
#include "network_security.pb.h"
#include <seed_client/seed_client.hpp>
#include <crypto_transport/transport.hpp>
#include <crypto_transport/contexts.hpp>
#include <zmq.hpp>
#include <lz4.h>
#include <nlohmann/json.hpp>
#include <fstream>
#include <iostream>
#include <csignal>
#include <atomic>
#include <cstring>
#include <chrono>
#include <string>
// ETH/IP/TCP/UDP parsing
#include <netinet/ether.h>
#include <netinet/ip.h>
#include <netinet/tcp.h>
#include <netinet/udp.h>
#include <arpa/inet.h>

using json = nlohmann::json;

// ============================================================================
// Configuración leída del JSON — solo campos relevantes para Variant B
// ============================================================================
struct LibpcapConfig {
    // capture
    std::string interface       = "eth1";
    int         timeout_ms      = 1000;
    int         buffer_size_mb  = 8;   // closed DAY 142 — DEBT-VARIANT-B-BUFFER-SIZE-001
    // network
    std::string zmq_address     = "127.0.0.1";
    int         zmq_port        = 5571;
    // logging
    std::string log_file        = "/vagrant/logs/lab/sniffer-libpcap.log";
    std::string log_level       = "INFO";
    // monitoring
    double max_drop_rate_pct    = 0.1;
};

static LibpcapConfig load_config(const std::string& path) {
    LibpcapConfig cfg;
    std::ifstream f(path);
    if (!f.is_open())
        throw std::runtime_error("[config] No se puede abrir: " + path);
    json j = json::parse(f);

    if (j.contains("capture")) {
        const auto& c = j["capture"];
        if (c.contains("interface"))   cfg.interface      = c["interface"].get<std::string>();
        if (c.contains("timeout_ms"))  cfg.timeout_ms     = c["timeout_ms"].get<int>();
        if (c.contains("buffer_size_mb")) cfg.buffer_size_mb = c["buffer_size_mb"].get<int>();
    }
    if (j.contains("network") && j["network"].contains("output_socket")) {
        const auto& s = j["network"]["output_socket"];
        if (s.contains("address")) cfg.zmq_address = s["address"].get<std::string>();
        if (s.contains("port"))    cfg.zmq_port    = s["port"].get<int>();
    }
    if (j.contains("logging")) {
        const auto& l = j["logging"];
        if (l.contains("file"))  cfg.log_file  = l["file"].get<std::string>();
        if (l.contains("level")) cfg.log_level = l["level"].get<std::string>();
    }
    if (j.contains("monitoring") && j["monitoring"].contains("alerts")) {
        const auto& a = j["monitoring"]["alerts"];
        if (a.contains("max_drop_rate_percent"))
            cfg.max_drop_rate_pct = a["max_drop_rate_percent"].get<double>();
    }
    return cfg;
}

// ============================================================================
// Contexto pasado al callback de captura
// ============================================================================
struct PcapPipelineContext {
    zmq::socket_t*                          socket;
    crypto_transport::CryptoTransport*      tx;
    std::atomic<uint64_t>*                  packets_sent;
    std::atomic<uint64_t>*                  send_failures;
};

static std::atomic<bool> g_running{true};
static void signal_handler(int) { g_running = false; }

// ============================================================================
// packet_callback: raw ETH frame → NetworkSecurityEvent → LZ4 → encrypt → ZMQ
// Mismo wire format que Variant A (ring_consumer.cpp:689-760)
// Hardcodeado: snaplen=65535, promiscuous=1, dontwait policy (Consejo DAY 138)
// ============================================================================
static int packet_callback(void* ctx, void* data, size_t size) {
    auto* pc = reinterpret_cast<PcapPipelineContext*>(ctx);
    if (!pc || !data || size < sizeof(struct ether_header)) return 0;

    const auto* eth = reinterpret_cast<const struct ether_header*>(data);
    if (ntohs(eth->ether_type) != ETHERTYPE_IP) return 0;

    if (size < sizeof(struct ether_header) + sizeof(struct ip)) return 0;
    const auto* iph = reinterpret_cast<const struct ip*>(
        static_cast<const uint8_t*>(data) + sizeof(struct ether_header));

    // --- Construir NetworkSecurityEvent mínimo ---
    protobuf::NetworkSecurityEvent event;
    auto* nf = event.mutable_network_features();

    char src_str[INET_ADDRSTRLEN], dst_str[INET_ADDRSTRLEN];
    inet_ntop(AF_INET, &iph->ip_src, src_str, sizeof(src_str));
    inet_ntop(AF_INET, &iph->ip_dst, dst_str, sizeof(dst_str));
    nf->set_source_ip(src_str);
    nf->set_destination_ip(dst_str);
    nf->set_protocol_number(iph->ip_p);

    size_t ip_hdr_len = static_cast<size_t>(iph->ip_hl) * 4;
    size_t transport_offset = sizeof(struct ether_header) + ip_hdr_len;

    if (iph->ip_p == IPPROTO_TCP &&
        size >= transport_offset + sizeof(struct tcphdr)) {
        const auto* tcp = reinterpret_cast<const struct tcphdr*>(
            static_cast<const uint8_t*>(data) + transport_offset);
        nf->set_source_port(ntohs(tcp->source));
        nf->set_destination_port(ntohs(tcp->dest));
    } else if (iph->ip_p == IPPROTO_UDP &&
               size >= transport_offset + sizeof(struct udphdr)) {
        const auto* udp = reinterpret_cast<const struct udphdr*>(
            static_cast<const uint8_t*>(data) + transport_offset);
        nf->set_source_port(ntohs(udp->source));
        nf->set_destination_port(ntohs(udp->dest));
    }

    auto ts = std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
    event.mutable_event_timestamp()->set_seconds(ts / 1'000'000'000LL);
    event.mutable_event_timestamp()->set_nanos(
        static_cast<int32_t>(ts % 1'000'000'000LL));
    event.mutable_custom_metadata()->insert({"capture_variant", "libpcap"});

    // --- Serialize ---
    std::string serialized;
    if (!event.SerializeToString(&serialized)) return 0;

    // --- LZ4 compress: [uint32_t orig_size LE] + compressed ---
    std::vector<uint8_t> to_encrypt;
    {
        int orig  = static_cast<int>(serialized.size());
        int max_c = LZ4_compressBound(orig);
        std::vector<uint8_t> compressed(sizeof(uint32_t) + max_c);
        uint32_t orig_le = static_cast<uint32_t>(orig);
        std::memcpy(compressed.data(), &orig_le, sizeof(orig_le));
        int c_size = LZ4_compress_default(
            serialized.data(),
            reinterpret_cast<char*>(compressed.data() + sizeof(uint32_t)),
            orig, max_c);
        if (c_size > 0) {
            compressed.resize(sizeof(uint32_t) + c_size);
            to_encrypt = std::move(compressed);
        } else {
            to_encrypt.assign(serialized.begin(), serialized.end());
        }
    }

    // --- Encrypt ---
    auto encrypted = pc->tx->encrypt(to_encrypt);

    // --- ZeroMQ PUSH (dontwait — NDR policy: mejor perder que bloquear) ---
    zmq::message_t msg(encrypted.size());
    std::memcpy(msg.data(), encrypted.data(), encrypted.size());
    auto result = pc->socket->send(msg, zmq::send_flags::dontwait);
    if (result.has_value()) {
        pc->packets_sent->fetch_add(1, std::memory_order_relaxed);
    } else {
        pc->send_failures->fetch_add(1, std::memory_order_relaxed);
    }
    return 0;
}

// ============================================================================
// main
// ============================================================================
int main(int argc, char* argv[]) {
    std::cout << "╔════════════════════════════════════════════════╗\n";
    std::cout << "║  aRGus NDR — Sniffer Variant B (libpcap)      ║\n";
    std::cout << "║  ADR-029 — pipeline completo DAY 141          ║\n";
    std::cout << "╚════════════════════════════════════════════════╝\n\n";

    // --- Parsear argumentos: -c <config_path> ---
    std::string config_path = "/etc/ml-defender/sniffer/sniffer-libpcap.json";
    for (int i = 1; i < argc - 1; ++i) {
        if (std::string(argv[i]) == "-c") {
            config_path = argv[i + 1];
        }
    }
    std::cout << "📄 Config: " << config_path << "\n";

    // --- Cargar configuración ---
    LibpcapConfig cfg;
    try {
        cfg = load_config(config_path);
    } catch (const std::exception& e) {
        std::cerr << "❌ Error cargando config: " << e.what() << "\n";
        return 1;
    }

    std::cout << "✅ Config cargada:\n";
    std::cout << "   interface:      " << cfg.interface << "\n";
    std::cout << "   zmq endpoint:   tcp://" << cfg.zmq_address << ":" << cfg.zmq_port << "\n";
    std::cout << "   buffer_size_mb: " << cfg.buffer_size_mb
              << " (DEBT-VARIANT-B-BUFFER-SIZE-001: reservado, no aplicado aún)\n";
    std::cout << "   max_drop_rate:  " << cfg.max_drop_rate_pct << "%\n";
    std::cout << "   log:            " << cfg.log_file << "\n\n";

    signal(SIGINT,  signal_handler);
    signal(SIGTERM, signal_handler);

    // --- CryptoTransport ---
    std::unique_ptr<ml_defender::SeedClient> seed_client;
    std::unique_ptr<crypto_transport::CryptoTransport> tx;
    try {
        seed_client = std::make_unique<ml_defender::SeedClient>(config_path);
        seed_client->load();
        tx = std::make_unique<crypto_transport::CryptoTransport>(
            *seed_client, ml_defender::crypto::CTX_SNIFFER_TO_ML);
        std::cout << "✅ CryptoTransport inicializado (HKDF-SHA256 + ChaCha20-Poly1305)\n";
    } catch (const std::exception& e) {
        std::cerr << "❌ CryptoTransport init failed: " << e.what() << "\n";
        return 1;
    }

    // --- ZeroMQ PUSH socket ---
    // Hardcodeado: zmq_sender_threads=1, io_thread_pools=1 (monohilo por diseño libpcap)
    zmq::context_t zmq_ctx(1);
    zmq::socket_t  zmq_sock(zmq_ctx, zmq::socket_type::push);
    std::string zmq_endpoint = "tcp://" + cfg.zmq_address + ":" + std::to_string(cfg.zmq_port);
    zmq_sock.connect(zmq_endpoint);
    std::cout << "✅ ZeroMQ PUSH conectado a " << zmq_endpoint << "\n";

    // --- Stats ---
    std::atomic<uint64_t> packets_sent{0};
    std::atomic<uint64_t> send_failures{0};

    PcapPipelineContext pc{&zmq_sock, tx.get(), &packets_sent, &send_failures};

    // --- Abrir captura ---
    // Hardcodeado: snaplen=65535 (parser ETH/IP), promiscuous=1 (captura completa)
    sniffer::PcapBackend backend;
    if (!backend.open(cfg.interface, cfg.buffer_size_mb, packet_callback, &pc)) {
        std::cerr << "❌ Failed to open libpcap on " << cfg.interface << "\n";
        return 1;
    }

    std::cout << "✅ Variant B running — interface: " << cfg.interface << "\n";
    std::cout << "   Ctrl+C para detener\n\n";

    // --- Stats periódicas ---
    auto t_start    = std::chrono::steady_clock::now();
    auto t_last_log = t_start;

    while (g_running) {
        backend.poll(cfg.timeout_ms);

        // Log de send_failures cada 30s
        auto now = std::chrono::steady_clock::now();
        auto elapsed_log = std::chrono::duration_cast<std::chrono::seconds>(
            now - t_last_log).count();
        if (elapsed_log >= 30) {
            uint64_t sent    = packets_sent.load(std::memory_order_relaxed);
            uint64_t fails   = send_failures.load(std::memory_order_relaxed);
            uint64_t total   = sent + fails;
            double drop_rate = total > 0
                ? (static_cast<double>(fails) / static_cast<double>(total)) * 100.0
                : 0.0;
            std::cout << "[stats] pkts_sent=" << sent
                      << " send_failures=" << fails
                      << " drop_rate=" << drop_rate << "%";
            if (drop_rate > cfg.max_drop_rate_pct)
                std::cout << " ⚠️  DROP_RATE_ALERT";
            std::cout << "\n";
            t_last_log = now;
        }
    }

    backend.close();

    auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
        std::chrono::steady_clock::now() - t_start).count();
    std::cout << "\n✅ Variant B stopped — "
              << backend.get_packet_count() << " pkts capturados, "
              << packets_sent.load()        << " enviados, "
              << send_failures.load()       << " fallos, "
              << elapsed << "s\n";
    return 0;
}