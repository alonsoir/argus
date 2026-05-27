#ifndef FEATURE_LOGGER_HPP
#define FEATURE_LOGGER_HPP

#include <string>
#include <vector>

// Forward declaration - no incluir el .pb.h aquí
namespace protobuf {
    class NetworkSecurityEvent;
}

namespace FeatureLogger {

    // Verbosity levels
    enum class VerbosityLevel {
        NONE = 0,      // No feature logging
        BASIC = 1,     // Basic packet summary (--verbose or -v)
        GROUPED = 2,   // Features grouped by category (-vv)
        DETAILED = 3   // All features with index and values (-vvv)
    };

    // Main logging function
    void log_packet_features(const protobuf::NetworkSecurityEvent& event, VerbosityLevel level);

    // Level-specific functions
    void print_basic_summary(const protobuf::NetworkSecurityEvent& event);
    void print_grouped_features(const protobuf::NetworkSecurityEvent& event);
    void print_all_features_detailed(const protobuf::NetworkSecurityEvent& event);

    // Helper functions
    std::string format_timestamp(uint64_t timestamp_ns);
    std::string protocol_name(uint32_t protocol_num);
    std::string tcp_flags_string(uint32_t flags);
    void print_separator(const std::string& title = "");
    void print_subsection(const std::string& title);

} // namespace FeatureLogger

#endif // FEATURE_LOGGER_HPP