// http_etcd_registrar.cpp — DEBT-ETCD-REGISTRAR-REAL-001 (DAY 164)
// HttpEtcdRegistrar: REST client contra etcd-server custom
// POST /register · POST /v1/heartbeat/{component} · GET /v1/epoch (polling)
// ============================================================================
#include "http_etcd_registrar.h"
#include <nlohmann/json.hpp>
#include <httplib.h>
#include <iostream>
#include <sstream>
#include <chrono>

using namespace std::chrono_literals;

namespace ml_defender {

// ── Helpers ───────────────────────────────────────────────────────────────────

// Parsea "http://host:port" → {host, port}
static std::pair<std::string, int> parse_url(const std::string& url) {
    // Espera formato http://host:port
    std::string s = url;
    if (s.substr(0, 7) == "http://") s = s.substr(7);
    auto colon = s.rfind(':');
    if (colon == std::string::npos) return {s, 2379};
    return {s.substr(0, colon), std::stoi(s.substr(colon + 1))};
}

// ── Constructor / Destructor ──────────────────────────────────────────────────

HttpEtcdRegistrar::HttpEtcdRegistrar(
    const std::string& url, const std::string& component,
    int ka_ms, int poll_ms, int timeout_ms, int deg_threshold)
    : server_url_(url)
    , component_name_(component)
    , keepalive_interval_ms_(ka_ms)
    , poll_interval_ms_(poll_ms)
    , request_timeout_ms_(timeout_ms)
    , degraded_threshold_(deg_threshold)
{}

HttpEtcdRegistrar::~HttpEtcdRegistrar() {
    stop_keepalive();
    stop_watch();
}

// ── register_status ───────────────────────────────────────────────────────────

bool HttpEtcdRegistrar::register_status(const CryptoMaterial& material,
                                         const std::string&    component_name,
                                         bool                  started_with_cache) {
    auto [host, port] = parse_url(server_url_);
    httplib::Client cli(host, port);
    cli.set_connection_timeout(request_timeout_ms_ / 1000, 0);
    cli.set_read_timeout(request_timeout_ms_ / 1000, 0);

    nlohmann::json body;
    body["component"]          = component_name;
    body["key_version"]        = material.key_version;
    body["family"]             = material.family;
    body["started_with_cache"] = started_with_cache;

    auto res = cli.Post("/register", body.dump(), "application/json");
    if (!res || res->status != 200) {
        std::cerr << "[HttpEtcdRegistrar] ❌ register_status falló: "
                  << (res ? std::to_string(res->status) : "sin respuesta") << "\n";
        return false;
    }
    return true;
}

// ── start_keepalive ───────────────────────────────────────────────────────────

void HttpEtcdRegistrar::start_keepalive() {
    if (keepalive_running_.exchange(true)) return; // ya corriendo

    keepalive_thread_ = std::thread([this]() {
        auto [host, port] = parse_url(server_url_);
        const std::string path = "/v1/heartbeat/" + component_name_;

        while (keepalive_running_) {
            httplib::Client cli(host, port);
            cli.set_connection_timeout(request_timeout_ms_ / 1000, 0);
            cli.set_read_timeout(request_timeout_ms_ / 1000, 0);

            // /v1/heartbeat requiere campo timestamp (unix epoch)
            auto now_s = std::chrono::duration_cast<std::chrono::seconds>(
                std::chrono::system_clock::now().time_since_epoch()).count();
            std::string hb_body = R"({"timestamp":)" + std::to_string(now_s) + "}";
            auto res = cli.Post(path, hb_body, "application/json");
            if (!res || res->status != 200) {
                std::cerr << "[HttpEtcdRegistrar] ⚠️  heartbeat falló\n";
            }

            // Dormir en intervalos cortos para reaccionar a stop rápido
            int elapsed = 0;
            while (keepalive_running_ && elapsed < keepalive_interval_ms_) {
                std::this_thread::sleep_for(std::chrono::milliseconds(10));
                elapsed += 10;
            }
        }
    });
}

// ── stop_keepalive ────────────────────────────────────────────────────────────

void HttpEtcdRegistrar::stop_keepalive() {
    keepalive_running_ = false;
    if (keepalive_thread_.joinable()) keepalive_thread_.join();
}

// ── watch_epoch ───────────────────────────────────────────────────────────────

void HttpEtcdRegistrar::watch_epoch(
    std::function<void(uint16_t, const std::string&)> callback) {

    epoch_callback_ = std::move(callback);
    watch_running_  = true;
    watch_state_    = WatchState::CONNECTED;

    watch_thread_ = std::thread([this]() {
        auto [host, port] = parse_url(server_url_);
        int  consecutive_errors = 0;

        bool first_poll = true;
        while (watch_running_) {
            httplib::Client cli(host, port);
            cli.set_connection_timeout(request_timeout_ms_ / 1000,
                                       (request_timeout_ms_ % 1000) * 1000);
            cli.set_read_timeout(request_timeout_ms_ / 1000,
                                 (request_timeout_ms_ % 1000) * 1000);

            auto res = cli.Get("/v1/epoch");

            if (!res || res->status != 200) {
                consecutive_errors++;
                if (consecutive_errors >= degraded_threshold_) {
                    watch_state_ = WatchState::DEGRADED;
                }
                // Esperar antes del siguiente intento
                int elapsed = 0;
                while (watch_running_ && elapsed < poll_interval_ms_) {
                    std::this_thread::sleep_for(std::chrono::milliseconds(10));
                    elapsed += 10;
                }
                continue;
            }

            // Respuesta OK — reset errores
            consecutive_errors = 0;
            watch_state_       = WatchState::CONNECTED;

            try {
                auto j        = nlohmann::json::parse(res->body);
                int64_t  rev  = j.at("revision").get<int64_t>();
                uint16_t eid  = j.at("epoch_id").get<uint16_t>();
                std::string nb = j.at("not_before").get<std::string>();

                if (first_poll) {
                    // Primer poll: establece baseline sin disparar callback
                    last_seen_revision_ = rev;
                    first_poll = false;
                } else if (rev != last_seen_revision_.load()) {
                    last_seen_revision_ = rev;
                    if (epoch_callback_) epoch_callback_(eid, nb);
                }
            } catch (const std::exception& e) {
                std::cerr << "[HttpEtcdRegistrar] ⚠️  parse epoch: " << e.what() << "\n";
            }

            // Polling interval
            int elapsed = 0;
            while (watch_running_ && elapsed < poll_interval_ms_) {
                std::this_thread::sleep_for(std::chrono::milliseconds(10));
                elapsed += 10;
            }
        }
    });
}

// ── stop_watch ────────────────────────────────────────────────────────────────

void HttpEtcdRegistrar::stop_watch() {
    watch_running_ = false;
    if (watch_thread_.joinable()) watch_thread_.join();
}

// ── watch_state ───────────────────────────────────────────────────────────────

WatchState HttpEtcdRegistrar::watch_state() const {
    return watch_state_.load();
}

} // namespace ml_defender
