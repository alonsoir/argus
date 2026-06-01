// community_id_log.cpp — escribe a fichero dedicado, no a stdout (limpio para el parser)
#include "flow/community_id_log.hpp"
#include <atomic>
#include <chrono>
#include <cstdlib>
#include <cstdio>
#include <mutex>
namespace sniffer::flow {

    bool cid_crosscheck_enabled() {
        static std::atomic<int> cached{-1};
        int v = cached.load(std::memory_order_relaxed);
        if (v < 0) {
            const char* e = std::getenv("ARGUS_CID_CROSSCHECK");
            v = (e && e[0] == '1' && e[1] == '\0') ? 1 : 0;
            cached.store(v, std::memory_order_relaxed);
        }
        return v == 1;
    }

    void log_community_id_emission(
    const std::string& cid,
    const std::string& saddr,
    const std::string& daddr,
    uint16_t sport,
    uint16_t dport,
    uint8_t  proto) {
        static std::FILE* fp = [] {
            const char* p = std::getenv("ARGUS_CID_CROSSCHECK_PATH");
            const char* path = (p && p[0]) ? p : "/vagrant/logs/lab/cid-xcheck-argus.tsv";
            return std::fopen(path, "a");
        }();
        if (!fp) return;
        const auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::system_clock::now().time_since_epoch()).count();
        static std::mutex mtx;
        std::lock_guard<std::mutex> lk(mtx);
        std::fprintf(fp, "%s\t%s\t%s\t%u\t%u\t%u\t%lld\n",
            cid.c_str(), saddr.c_str(), daddr.c_str(),
            static_cast<unsigned>(sport), static_cast<unsigned>(dport),
            static_cast<unsigned>(proto),
            static_cast<long long>(ns));
        std::fflush(fp);
    }
}  // namespace sniffer::flow