#pragma once
// crypto_epoch_coordinator.h — BACKLOG-CRYPTO-EPOCH-001 (DAY 164)
// Coordina rotación de época criptográfica via HttpEtcdRegistrar
// watch /v1/epoch → callback → caller hace handle.reload()
// ============================================================================
#include "http_etcd_registrar.h"
#include "crypto_provider_handle.hpp"
#include <string>
#include <functional>
#include <atomic>
#include <cstdint>
#include <chrono>

namespace ml_defender {

struct EpochAck {
    uint16_t    epoch_id;
    std::string component;
    int64_t     ack_ts_monotonic_ns;  // timestamp monotónico en ns
};

class CryptoEpochCoordinator {
public:
    // on_epoch_change: caller debe hacer handle.reload(new_provider)
    using EpochCallback = std::function<void(uint16_t epoch_id,
                                             const std::string& not_before)>;

    explicit CryptoEpochCoordinator(
        HttpEtcdRegistrar& registrar,
        const std::string& component_name,
        EpochCallback      on_epoch_change = nullptr);

    ~CryptoEpochCoordinator();

    // Arranca el watch de época
    void start(EpochCallback cb);
    void stop();

    uint16_t    current_epoch()  const { return current_epoch_.load(); }
    std::string current_not_before() const;
    WatchState  watch_state()    const;

private:
    HttpEtcdRegistrar& registrar_;
    std::string        component_name_;
    EpochCallback      on_epoch_change_;

    std::atomic<uint16_t>   current_epoch_{1};
    std::atomic<bool>       running_{false};

    mutable std::mutex      nb_mutex_;
    std::string             current_not_before_{"2026-01-01T00:00:00Z"};
};

} // namespace ml_defender
