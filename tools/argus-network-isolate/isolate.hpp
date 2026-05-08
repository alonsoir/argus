#pragma once
// argus-network-isolate — ADR-042 Incident Response Protocol
// Aislamiento de red transaccional via nftables
// Via Appia Quality — DAY 142
// Authors: Alonso Isidoro Roman + Claude (Anthropic)

#include <string>
#include <vector>
#include <nlohmann/json.hpp>
#include <spdlog/spdlog.h>

namespace argus::irp {

struct IsolateConfig {
    std::string nft_path          = "/usr/sbin/nft";
    std::string backup_dir        = "/run/argus/irp";  // DEBT-IRP-BACKUP-DIR-001
    std::string table_name        = "argus_isolate";
    std::string log_path          = "/var/log/argus/network-isolate.log";
    std::string forensic_log_path = "/var/log/argus/network-isolate-forensic.jsonl";
    int         rollback_timeout_sec = 300;
    std::vector<std::string> whitelist_ips;
    std::vector<int>         whitelist_ports;
    bool                     auto_isolate           = true;
    double                   threat_score_threshold = 0.95;
    std::vector<std::string> auto_isolate_event_types;
    std::string              isolate_interface      = "eth0";

    static IsolateConfig from_file(const std::string& path);
};

enum class IsolateResult {
    OK, DRY_RUN_OK, VALIDATION_FAILED, SNAPSHOT_FAILED,
    APPLY_FAILED, ROLLBACK_OK, ROLLBACK_FAILED,
    ALREADY_ISOLATED, NOT_ISOLATED, ERROR
};

std::string to_string(IsolateResult r);

class NetworkIsolator {
public:
    explicit NetworkIsolator(const IsolateConfig& cfg);

    IsolateResult snapshot(std::string& backup_path_out);
    IsolateResult generate_rules(const std::string& interface,
                                 std::string& rules_path_out);
    IsolateResult validate_dry_run(const std::string& rules_path);
    IsolateResult apply(const std::string& rules_path);
    IsolateResult arm_rollback_timer(const std::string& backup_path);
    IsolateResult rollback(const std::string& backup_path);
    IsolateResult emergency_link_down(const std::string& interface);
    IsolateResult status();
    bool is_isolated() const;

private:
    IsolateConfig cfg_;
    std::pair<int,std::string> run_cmd(const std::string& cmd);
    void log_forensic(const std::string& event, const nlohmann::json& details);
    std::string build_nft_ruleset(const std::string& interface);
};

} // namespace argus::irp
