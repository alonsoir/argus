// sniffer/include/protocol_numbers.hpp
#pragma once

#include <cstdint>
#include <string>
#include <string_view>

// ============================================================================
// IP Protocol Numbers - IANA Registry
// ============================================================================
// Source: https://www.iana.org/assignments/protocol-numbers/
// RFC 5237 - IANA Allocation Guidelines for the Protocol Field
//
// This enum provides a type-safe, semantic way to work with IP protocol
// numbers throughout the sniffer codebase.
//
// Design Philosophy:
//   - Single source of truth for protocol numbers
//   - Future-proof: Easy to add new protocols when ransomware evolves
//   - Data-driven: Log "Protocol-X" instead of generic "UNKNOWN"
//   - Maintainable: One place to update when IANA adds protocols
//
// Full registry: 0-255 (8-bit field in IPv4/IPv6 header)
// Included here: ~30 most common + security-relevant protocols
// ============================================================================

namespace sniffer {

enum class IPProtocol : uint8_t {
    // === Core Internet Protocols ===
    HOPOPT          = 0,    // IPv6 Hop-by-Hop Option (RFC 8200)
    ICMP            = 1,    // Internet Control Message Protocol (RFC 792)
    IGMP            = 2,    // Internet Group Management Protocol (RFC 1112)
    GGP             = 3,    // Gateway-to-Gateway Protocol (RFC 823)
    IPv4            = 4,    // IPv4 encapsulation (RFC 2003)
    ST              = 5,    // Stream (RFC 1190, RFC 1819)
    TCP             = 6,    // Transmission Control Protocol (RFC 793)
    UDP             = 17,   // User Datagram Protocol (RFC 768)
    
    // === IPv6 Extensions ===
    IPv6            = 41,   // IPv6 Encapsulation (RFC 2473)
    IPv6_Route      = 43,   // Routing Header for IPv6 (RFC 8200)
    IPv6_Frag       = 44,   // Fragment Header for IPv6 (RFC 8200)
    IPv6_NoNxt      = 59,   // No Next Header for IPv6 (RFC 8200)
    IPv6_Opts       = 60,   // Destination Options for IPv6 (RFC 8200)
    ICMPv6          = 58,   // ICMP for IPv6 (RFC 4443)
    
    // === Tunneling Protocols ===
    GRE             = 47,   // Generic Routing Encapsulation (RFC 2784)
    IPIP            = 94,   // IP-within-IP Encapsulation (RFC 2003)
    ETHERIP         = 97,   // Ethernet-within-IP Encapsulation (RFC 3378)
    ENCAP           = 98,   // Encapsulation Header (RFC 1241)
    
    // === Security Protocols (IPsec) ===
    ESP             = 50,   // Encapsulating Security Payload (RFC 4303)
    AH              = 51,   // Authentication Header (RFC 4302)
    
    // === Transport Layer ===
    DCCP            = 33,   // Datagram Congestion Control Protocol (RFC 4340)
    SCTP            = 132,  // Stream Control Transmission Protocol (RFC 4960)
    UDPLite         = 136,  // UDP-Lite (RFC 3828)
    
    // === Routing Protocols ===
    EIGRP           = 88,   // Enhanced Interior Gateway Routing Protocol
    OSPF            = 89,   // Open Shortest Path First (RFC 2328, RFC 5340)
    
    // === Multicast ===
    PIM             = 103,  // Protocol Independent Multicast (RFC 7761)
    
    // === VPN/Tunneling ===
    L2TP            = 115,  // Layer Two Tunneling Protocol (RFC 3931)
    
    // === Mobility ===
    Mobility        = 135,  // Mobility Header (RFC 6275)
    
    // === Experimental/Research ===
    HIP             = 139,  // Host Identity Protocol (RFC 7401)
    Shim6           = 140,  // Shim6 Protocol (RFC 5533)
    
    // === Management ===
    VRRP            = 112,  // Virtual Router Redundancy Protocol (RFC 5798)
    
    // === Special ===
    Reserved        = 255   // Reserved for future use
};

// ============================================================================
// Protocol Name Conversion - Constexpr for Zero Runtime Cost
// ============================================================================

constexpr std::string_view protocol_to_string(IPProtocol protocol) noexcept {
    switch (protocol) {
        // Core protocols
        case IPProtocol::HOPOPT:        return "HOPOPT";
        case IPProtocol::ICMP:          return "ICMP";
        case IPProtocol::IGMP:          return "IGMP";
        case IPProtocol::GGP:           return "GGP";
        case IPProtocol::IPv4:          return "IPv4";
        case IPProtocol::ST:            return "ST";
        case IPProtocol::TCP:           return "TCP";
        case IPProtocol::UDP:           return "UDP";
        
        // IPv6
        case IPProtocol::IPv6:          return "IPv6";
        case IPProtocol::IPv6_Route:    return "IPv6-Route";
        case IPProtocol::IPv6_Frag:     return "IPv6-Frag";
        case IPProtocol::IPv6_NoNxt:    return "IPv6-NoNxt";
        case IPProtocol::IPv6_Opts:     return "IPv6-Opts";
        case IPProtocol::ICMPv6:        return "ICMPv6";
        
        // Tunneling
        case IPProtocol::GRE:           return "GRE";
        case IPProtocol::IPIP:          return "IPIP";
        case IPProtocol::ETHERIP:       return "ETHERIP";
        case IPProtocol::ENCAP:         return "ENCAP";
        
        // Security
        case IPProtocol::ESP:           return "ESP";
        case IPProtocol::AH:            return "AH";
        
        // Transport
        case IPProtocol::DCCP:          return "DCCP";
        case IPProtocol::SCTP:          return "SCTP";
        case IPProtocol::UDPLite:       return "UDPLite";
        
        // Routing
        case IPProtocol::EIGRP:         return "EIGRP";
        case IPProtocol::OSPF:          return "OSPF";
        
        // Multicast
        case IPProtocol::PIM:           return "PIM";
        
        // VPN
        case IPProtocol::L2TP:          return "L2TP";
        
        // Mobility
        case IPProtocol::Mobility:      return "Mobility";
        
        // Experimental
        case IPProtocol::HIP:           return "HIP";
        case IPProtocol::Shim6:         return "Shim6";
        
        // Management
        case IPProtocol::VRRP:          return "VRRP";
        
        // Special
        case IPProtocol::Reserved:      return "Reserved";
        
        default:                        return "UNKNOWN";
    }
}

// ============================================================================
// Helper Functions - Protocol Analysis
// ============================================================================

// Convert raw uint8_t to string (with numeric fallback for unknown protocols)
inline std::string protocol_to_string(uint8_t protocol_num) noexcept {
    auto protocol = static_cast<IPProtocol>(protocol_num);
    auto name = protocol_to_string(protocol);
    
    if (name == "UNKNOWN") {
        // Return "Protocol-X" for unknown protocols
        // This helps in future ransomware analysis:
        // - See "Protocol-89" in logs → investigate OSPF abuse
        // - See "Protocol-47" in logs → investigate GRE tunneling
        // Instead of generic "UNKNOWN" → no actionable data
        return "Protocol-" + std::to_string(protocol_num);
    }
    
    return std::string(name);
}

// Check if protocol is in our known list
constexpr bool is_known_protocol(uint8_t protocol_num) noexcept {
    auto protocol = static_cast<IPProtocol>(protocol_num);
    return protocol_to_string(protocol) != "UNKNOWN";
}

// Check if protocol is transport layer (has ports)
constexpr bool is_transport_protocol(IPProtocol protocol) noexcept {
    return protocol == IPProtocol::TCP || 
           protocol == IPProtocol::UDP ||
           protocol == IPProtocol::SCTP ||
           protocol == IPProtocol::DCCP ||
           protocol == IPProtocol::UDPLite;
}

constexpr bool is_transport_protocol(uint8_t protocol_num) noexcept {
    return is_transport_protocol(static_cast<IPProtocol>(protocol_num));
}

// Check if protocol is IPv6 extension header
constexpr bool is_ipv6_extension(IPProtocol protocol) noexcept {
    return protocol == IPProtocol::HOPOPT ||
           protocol == IPProtocol::IPv6_Route ||
           protocol == IPProtocol::IPv6_Frag ||
           protocol == IPProtocol::IPv6_Opts ||
           protocol == IPProtocol::IPv6_NoNxt;
}

// Check if protocol is IPsec security protocol
constexpr bool is_security_protocol(IPProtocol protocol) noexcept {
    return protocol == IPProtocol::ESP ||
           protocol == IPProtocol::AH;
}

// Check if protocol is tunneling/encapsulation
constexpr bool is_tunneling_protocol(IPProtocol protocol) noexcept {
    return protocol == IPProtocol::GRE ||
           protocol == IPProtocol::IPIP ||
           protocol == IPProtocol::ETHERIP ||
           protocol == IPProtocol::ENCAP ||
           protocol == IPProtocol::L2TP ||
           protocol == IPProtocol::IPv6;  // IPv6-in-IPv4 tunneling
}

// Check if protocol is routing protocol
constexpr bool is_routing_protocol(IPProtocol protocol) noexcept {
    return protocol == IPProtocol::EIGRP ||
           protocol == IPProtocol::OSPF ||
           protocol == IPProtocol::PIM ||
           protocol == IPProtocol::VRRP;
}

// Get protocol category (for logging/stats)
constexpr std::string_view get_protocol_category(IPProtocol protocol) noexcept {
    if (is_transport_protocol(protocol)) return "Transport";
    if (is_security_protocol(protocol)) return "Security";
    if (is_tunneling_protocol(protocol)) return "Tunneling";
    if (is_routing_protocol(protocol)) return "Routing";
    if (is_ipv6_extension(protocol)) return "IPv6-Extension";
    if (protocol == IPProtocol::ICMP || protocol == IPProtocol::ICMPv6) return "Control";
    return "Other";
}

inline std::string get_protocol_category(uint8_t protocol_num) noexcept {
    return std::string(get_protocol_category(static_cast<IPProtocol>(protocol_num)));
}

} // namespace sniffer
