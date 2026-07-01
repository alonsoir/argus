// correlation-engine/src/bronze_dir_watcher.cpp
// DAY 203 — DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001

#include "correlation_engine/bronze_dir_watcher.hpp"

#include <sys/inotify.h>
#include <unistd.h>
#include <poll.h>
#include <cstring>
#include <stdexcept>

namespace argus::correlation {

BronzeDirWatcher::BronzeDirWatcher(std::string dir_path, SegmentCallback callback)
    : dir_path_(std::move(dir_path)), callback_(std::move(callback)) {}

BronzeDirWatcher::~BronzeDirWatcher() { stop(); }

void BronzeDirWatcher::stop() {
    if (!running_.exchange(false)) return;
    if (inotify_fd_ >= 0) { close(inotify_fd_); inotify_fd_ = -1; }
}

uint64_t BronzeDirWatcher::segments_detected() const noexcept {
    return segments_detected_.load();
}

void BronzeDirWatcher::run() {
    inotify_fd_ = inotify_init1(IN_NONBLOCK);
    if (inotify_fd_ < 0) {
        throw std::runtime_error(
            std::string("BronzeDirWatcher: inotify_init1 failed: ") + strerror(errno));
    }

    // Solo IN_MOVED_TO: es la unica senal que garantiza que el fichero ya fue
    // cerrado y renombrado atomicamente por el writer (contrato .tmp->rename).
    int wd = inotify_add_watch(inotify_fd_, dir_path_.c_str(), IN_MOVED_TO);
    if (wd < 0) {
        int e = errno;
        close(inotify_fd_);
        inotify_fd_ = -1;
        throw std::runtime_error(
            std::string("BronzeDirWatcher: inotify_add_watch failed: ") + strerror(e));
    }

    running_.store(true);
    constexpr size_t BUF_LEN = 4096;
    char buf[BUF_LEN] __attribute__((aligned(__alignof__(struct inotify_event))));

    while (running_.load()) {
        struct pollfd pfd{inotify_fd_, POLLIN, 0};
        int ret = poll(&pfd, 1, 1000);
        if (ret < 0) {
            if (errno == EINTR) continue;
            break;  // fd cerrado por stop()
        }
        if (ret == 0) continue;  // timeout, nada que leer

        ssize_t len = read(inotify_fd_, buf, BUF_LEN);
        if (len <= 0) break;

        const char* ptr = buf;
        while (ptr < buf + len) {
            const auto* ev = reinterpret_cast<const struct inotify_event*>(ptr);
            ptr += sizeof(struct inotify_event) + ev->len;
            if (ev->len == 0) continue;

            std::string name(ev->name);
            // Filtro explicito por sufijo -- defensa real: solo segmentos
            // completos (*.csv), nunca *.csv.tmp (que ademas nunca dispararia
            // IN_MOVED_TO, solo IN_CLOSE_WRITE, que no vigilamos).
            if (name.size() < 4 || name.substr(name.size() - 4) != ".csv") continue;

            segments_detected_.fetch_add(1, std::memory_order_relaxed);
            if (callback_) callback_(dir_path_ + "/" + name);
        }
    }

    inotify_rm_watch(inotify_fd_, wd);
    if (inotify_fd_ >= 0) { close(inotify_fd_); inotify_fd_ = -1; }
}

} // namespace argus::correlation
