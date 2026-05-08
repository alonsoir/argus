
// ADR-029 Variant B — Integration Test: proto parse raw ETH+IP+UDP
// DAY 138 — 2026-05-01
#include <gtest/gtest.h>
#include "network_security.pb.h"
#include <netinet/ether.h>
#include <netinet/ip.h>
#include <netinet/udp.h>
#include <arpa/inet.h>
#include <cstring>

static protobuf::NetworkSecurityEvent parse_udp_frame(const uint8_t* data, size_t size) {
    protobuf::NetworkSecurityEvent event;
    if (size < sizeof(struct ether_header)) return event;
    const auto* eth = reinterpret_cast<const struct ether_header*>(data);
    if (ntohs(eth->ether_type) != ETHERTYPE_IP) return event;
    if (size < sizeof(struct ether_header) + sizeof(struct ip)) return event;
    const auto* iph = reinterpret_cast<const struct ip*>(
        data + sizeof(struct ether_header));
    auto* nf = event.mutable_network_features();
    char src[INET_ADDRSTRLEN], dst[INET_ADDRSTRLEN];
    inet_ntop(AF_INET, &iph->ip_src, src, sizeof(src));
    inet_ntop(AF_INET, &iph->ip_dst, dst, sizeof(dst));
    nf->set_source_ip(src);
    nf->set_destination_ip(dst);
    nf->set_protocol_number(iph->ip_p);
    size_t transport_offset = sizeof(struct ether_header) + iph->ip_hl * 4u;
    if (iph->ip_p == IPPROTO_UDP &&
        size >= transport_offset + sizeof(struct udphdr)) {
        const auto* udp = reinterpret_cast<const struct udphdr*>(data + transport_offset);
        nf->set_source_port(ntohs(udp->source));
        nf->set_destination_port(ntohs(udp->dest));
    }
    return event;
}

TEST(PcapProtoParseUDP, UdpFramePopulatesFields) {
    constexpr size_t SZ = sizeof(struct ether_header) +
                           sizeof(struct ip) + sizeof(struct udphdr);
    uint8_t buf[SZ] = {0};
    auto* eth = reinterpret_cast<struct ether_header*>(buf);
    eth->ether_type = htons(ETHERTYPE_IP);
    auto* iph = reinterpret_cast<struct ip*>(buf + sizeof(struct ether_header));
    iph->ip_hl = 5; iph->ip_v = 4; iph->ip_p = IPPROTO_UDP;
    inet_pton(AF_INET, "192.168.1.1", &iph->ip_src);
    inet_pton(AF_INET, "8.8.8.8",     &iph->ip_dst);
    auto* udp = reinterpret_cast<struct udphdr*>(
        buf + sizeof(struct ether_header) + sizeof(struct ip));
    udp->source = htons(53000);
    udp->dest   = htons(53);

    auto event = parse_udp_frame(buf, SZ);
    const auto& nf = event.network_features();
    EXPECT_EQ(nf.source_ip(),        "192.168.1.1");
    EXPECT_EQ(nf.destination_ip(),   "8.8.8.8");
    EXPECT_EQ(nf.source_port(),      53000u);
    EXPECT_EQ(nf.destination_port(), 53u);
    EXPECT_EQ(nf.protocol_number(),  static_cast<uint32_t>(IPPROTO_UDP));
}
