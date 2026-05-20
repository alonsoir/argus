#pragma once
#include <nlohmann/json.hpp>
#include <string>
#include <vector>
#include <thread>
#define CPPHTTPLIB_OPENSSL_SUPPORT
#include <httplib.h>

namespace argus {

struct SosPayload {
    std::string node;
    std::string component;
    std::string event;
    std::string pipeline_status;
};

class AlertClient {
public:
    explicit AlertClient(const nlohmann::json& config) {
        if (!config.contains("alerting")) return;
        const auto& a = config["alerting"];
        enabled_ = a.value("enabled", false);
        if (!a.contains("providers")) return;
        for (const auto& p : a["providers"]) {
            Provider prov;
            prov.type    = p.value("type", "");
            prov.enabled = p.value("enabled", false);
            if (prov.type == "discord")
                prov.webhook_url = p.value("webhook_url", "");
            else if (prov.type == "telegram") {
                prov.bot_token = p.value("bot_token", "");
                prov.chat_id   = p.value("chat_id", "");
            }
            providers_.push_back(prov);
        }
    }

    bool is_enabled()               const { return enabled_; }
    size_t provider_count()         const { return providers_.size(); }
    size_t enabled_provider_count() const {
        size_t n = 0;
        for (const auto& p : providers_) if (p.enabled) ++n;
        return n;
    }

    static nlohmann::json build_discord_payload(const SosPayload& pl) {
        std::string msg = "🚨 **aRGus SOS** | node=" + pl.node +
                          " component=" + pl.component +
                          " event=" + pl.event +
                          " pipeline=" + pl.pipeline_status;
        return nlohmann::json{{"content", msg}};
    }

    static nlohmann::json build_telegram_payload(const std::string& chat_id,
                                                  const SosPayload& pl) {
        std::string msg = "🚨 aRGus SOS\nnode=" + pl.node +
                          "\ncomponent=" + pl.component +
                          "\nevent=" + pl.event +
                          "\npipeline=" + pl.pipeline_status;
        return nlohmann::json{{"chat_id", chat_id}, {"text", msg}};
    }

    void send_sos(const SosPayload& payload) {
        if (!enabled_) return;
        std::vector<Provider> active;
        for (const auto& p : providers_)
            if (p.enabled) active.push_back(p);
        if (active.empty()) return;

        std::thread([active, payload]() {
            for (const auto& p : active) {
                try {
                    if (p.type == "discord")
                        send_discord(p.webhook_url, payload);
                    else if (p.type == "telegram")
                        send_telegram(p.bot_token, p.chat_id, payload);
                } catch (...) {}
            }
        }).detach();
    }

private:
    struct Provider {
        std::string type;
        bool        enabled{false};
        std::string webhook_url;
        std::string bot_token;
        std::string chat_id;
    };

    bool                  enabled_{false};
    std::vector<Provider> providers_;

    static void send_discord(const std::string& url, const SosPayload& pl) {
        std::string host = "discord.com";
        std::string path = url.substr(url.find("/api"));
        auto body = build_discord_payload(pl).dump();
        httplib::SSLClient cli(host, 443);
        cli.set_connection_timeout(3);
        cli.set_read_timeout(3);
        cli.Post(path.c_str(), body, "application/json");
    }

    static void send_telegram(const std::string& token,
                               const std::string& chat_id,
                               const SosPayload& pl) {
        std::string host = "api.telegram.org";
        std::string path = "/bot" + token + "/sendMessage";
        auto body = build_telegram_payload(chat_id, pl).dump();
        httplib::SSLClient cli(host, 443);
        cli.set_connection_timeout(3);
        cli.set_read_timeout(3);
        cli.Post(path.c_str(), body, "application/json");
    }
};

} // namespace argus
