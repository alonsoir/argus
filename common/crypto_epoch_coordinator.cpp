// crypto_epoch_coordinator.cpp — BACKLOG-CRYPTO-EPOCH-001 (DAY 164)
#include "crypto_epoch_coordinator.h"
#include <iostream>
#include <chrono>

namespace ml_defender {

CryptoEpochCoordinator::CryptoEpochCoordinator(
    HttpEtcdRegistrar& registrar,
    const std::string& component_name,
    EpochCallback      on_epoch_change)
    : registrar_(registrar)
    , component_name_(component_name)
    , on_epoch_change_(std::move(on_epoch_change))
{}

CryptoEpochCoordinator::~CryptoEpochCoordinator() {
    stop();
}

void CryptoEpochCoordinator::start(EpochCallback cb) {
    if (cb) on_epoch_change_ = std::move(cb);
    running_ = true;

    registrar_.watch_epoch([this](uint16_t eid, const std::string& nb) {
        // Actualizar estado local
        current_epoch_ = eid;
        {
            std::lock_guard<std::mutex> lk(nb_mutex_);
            current_not_before_ = nb;
        }

        // Timestamp monotónico del ACK
        auto now_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count();

        std::cout << "[CryptoEpochCoordinator] Epoch " << eid
                  << " not_before=" << nb
                  << " ack_ts_ns=" << now_ns << "\n";

        // Notificar al caller para que haga handle.reload()
        if (on_epoch_change_) on_epoch_change_(eid, nb);
    });
}

void CryptoEpochCoordinator::stop() {
    if (!running_.exchange(false)) return;
    registrar_.stop_watch();
}

std::string CryptoEpochCoordinator::current_not_before() const {
    std::lock_guard<std::mutex> lk(nb_mutex_);
    return current_not_before_;
}

WatchState CryptoEpochCoordinator::watch_state() const {
    return registrar_.watch_state();
}

} // namespace ml_defender
