#pragma once
// http_etcd_registrar.h — DEBT-ETCD-REGISTRAR-REAL-001 (DAY 164)
#include "etcd_registrar.h"
#include <string>
#include <functional>
#include <atomic>
#include <thread>

namespace ml_defender {

enum class WatchState { CONNECTED, DEGRADED, STALE };

class HttpEtcdRegistrar : public IEtcdRegistrar {
public:
    explicit HttpEtcdRegistrar(
        const std::string& server_url,
        const std::string& component_name,
        int keepalive_interval_ms = 30000,
        int poll_interval_ms      = 2000,
        int request_timeout_ms    = 5000,
        int degraded_threshold    = 3);

    ~HttpEtcdRegistrar() override;

    // IEtcdRegistrar
    bool register_status(const CryptoMaterial& material,
                         const std::string&    component_name,
                         bool started_with_cache = false) override;
    void start_keepalive() override;
    void stop_keepalive()  override;

    // Watch epoch
    void watch_epoch(std::function<void(uint16_t, const std::string&)> callback);
    void stop_watch();
    WatchState watch_state() const;

private:
    std::string server_url_;
    std::string component_name_;
    int         keepalive_interval_ms_;
    int         poll_interval_ms_;
    int         request_timeout_ms_;
    int         degraded_threshold_;

    std::atomic<bool>       keepalive_running_{false};
    std::atomic<bool>       watch_running_{false};
    std::atomic<WatchState> watch_state_{WatchState::CONNECTED};
    std::atomic<int64_t>    last_seen_revision_{-1};

    std::thread keepalive_thread_;
    std::thread watch_thread_;

    std::function<void(uint16_t, const std::string&)> epoch_callback_;
};

} // namespace ml_defender
