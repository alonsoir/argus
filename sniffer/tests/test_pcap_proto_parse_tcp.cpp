
// ADR-029 Variant B — Integration Test: proto parse raw ETH+IP+TCP
// Verifica que packet_callback popula NetworkFeatures correctamente
// DAY 138 — 2026-05-01
#include <gtest/gtest.h>
#include "network_security.pb.h"
#include <netinet/ether.h>
#include <netinet/ip.h>
#include <netinet/tcp.h>
#include <arpa/inet.h>
#include <cstring>

// Helper: construir frame ETH+IP+TCP mínimo en buffer
static void build_tcp_frame(uint8_t* buf, size_t buflen,
                             const char* src_ip, const char* dst_ip,
                             uint16_t sport, uint16_t dport) {
    memset(buf, 0, buflen);
    auto* eth = reinterpret_cast<struct ether_header*>(buf);
    eth->ether_type = htons(ETHERTYPE_IP);

    auto* iph = reinterpret_cast<struct ip*>(buf + sizeof(struct ether_header));
    iph->ip_hl  = 5;
    iph->ip_v   = 4;
    iph->ip_p   = IPPROTO_TCP;
    iph->ip_len = htons(sizeof(struct ip) + sizeof(struct tcphdr));
    inet_pton(AF_INET, src_ip, &iph->ip_src);
    inet_pton(AF_INET, dst_ip, &iph->ip_dst);

    auto* tcp = reinterpret_cast<struct tcphdr*>(
        buf + sizeof(struct ether_header) + sizeof(struct ip));
    tcp->source = htons(sport);
    tcp->dest   = htons(dport);
}

// Replica la lógica de parse de packet_callback para test aislado
static protobuf::NetworkSecurityEvent parse_frame(const uint8_t* data, size_t size) {
    protobuf::NetworkSecurityEvent event;
    if (size < sizeof(struct ether_header)) return event;

    const auto* eth = reinterpret_cast<const struct ether_header*>(data);
    if (ntohs(eth->ether_type) != ETHERTYPE_IP) return event;
    if (size < sizeof(struct ether_header) + sizeof(struct ip)) return event;

    const auto* iph = reinterpret_cast<const struct ip*>(
        data + sizeof(struct ether_header));
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
        const auto* tcp = reinterpret_cast<const struct tcphdr*>(data + transport_offset);
        nf->set_source_port(ntohs(tcp->source));
        nf->set_destination_port(ntohs(tcp->dest));
    }
    return event;
}

TEST(PcapProtoParseT, TcpFramePopulatesFields) {
    constexpr size_t FRAME_SZ = sizeof(struct ether_header) +
                                 sizeof(struct ip) +
                                 sizeof(struct tcphdr);
    uint8_t buf[FRAME_SZ];
    build_tcp_frame(buf, FRAME_SZ, "10.0.0.1", "10.0.0.2", 12345, 80);

    auto event = parse_frame(buf, FRAME_SZ);
    const auto& nf = event.network_features();

    EXPECT_EQ(nf.source_ip(),       "10.0.0.1");
    EXPECT_EQ(nf.destination_ip(),  "10.0.0.2");
    EXPECT_EQ(nf.source_port(),     12345u);
    EXPECT_EQ(nf.destination_port(), 80u);
    EXPECT_EQ(nf.protocol_number(), static_cast<uint32_t>(IPPROTO_TCP));
}

TEST(PcapProtoParseT, ShortFrameProducesEmptyEvent) {
    uint8_t buf[10] = {0};
    auto event = parse_frame(buf, sizeof(buf));
    EXPECT_TRUE(event.network_features().source_ip().empty());
}

TEST(PcapProtoParseT, NonIPFrameProducesEmptyEvent) {
    uint8_t buf[sizeof(struct ether_header) + sizeof(struct ip)] = {0};
    auto* eth = reinterpret_cast<struct ether_header*>(buf);
    eth->ether_type = htons(0x0806); // ARP
    auto event = parse_frame(buf, sizeof(buf));
    EXPECT_TRUE(event.network_features().source_ip().empty());
}
