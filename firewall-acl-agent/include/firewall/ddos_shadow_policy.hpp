// [DDOS-SHADOW-D293] Política del firewall POR VÍCTIMA en SOMBRA (bloque 1c DAY293, docs/ml-heads/bloque1_day293.md).
// Réplica exacta de scripts/d293_politica.py: víctima = {dst_ip, proto}; ventanas de 1 s (segundos de la marca de tiempo
// del EVENTO); ventana positiva si eventos DROP >= m; INICIO cuando hay k positivas en las últimas n ventanas; FIN cuando
// w - última_positiva >= hold_s (y se vacía la cola). Solo REGISTRA: no toca ipset ni iptables.
// Uso: advance(ts) con TODO evento recibido (reloj monótono) y add_drop(...) con cada evento final_decision == "DROP".
// No es thread-safe: la usa solo el hilo receptor del ZMQSubscriber.
#pragma once

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <iomanip>
#include <map>
#include <sstream>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

namespace mldefender::firewall {

struct DdosShadowParams {
    bool enabled = true;
    int m = 5;
    int k = 3;
    int n = 5;
    int hold_s = 30;
};

struct DdosShadowRecord {
    bool inicio = true;  // true = INICIO, false = FIN
    std::string dst_ip;
    uint32_t proto = 0;
    int64_t start_s = 0;
    int64_t end_s = 0;
    uint64_t drop_events = 0;
    uint64_t positive_windows = 0;
    double p1_min = 0.0;
    double p1_mean = 0.0;
    double p1_max = 0.0;
    double ratio_max = 0.0;
    std::string modelo;
    std::vector<std::pair<std::string, uint64_t>> top_sources;
    std::string first_event_id;
    std::string last_event_id;
};

class DdosShadowPolicy {
public:
    explicit DdosShadowPolicy(const DdosShadowParams& p) : p_(p) {}

    std::vector<DdosShadowRecord> advance(int64_t now_s) {
        std::vector<DdosShadowRecord> out;
        if (!have_clock_) {
            clock_ = now_s;
            have_clock_ = true;
            return out;
        }
        if (now_s <= clock_) {
            return out;
        }
        clock_ = now_s;
        const int64_t limit = static_cast<int64_t>(p_.n) + static_cast<int64_t>(p_.hold_s) + 1;
        for (auto it = st_.begin(); it != st_.end();) {
            State& s = it->second;
            while (s.next_w < now_s) {
                const int64_t next_event_w = s.counts.empty() ? now_s : std::min(now_s, s.counts.begin()->first);
                if (next_event_w - s.next_w > limit) {
                    for (int64_t i = 0; i < limit; ++i) {
                        close_window(s, s.next_w++, 0, out);
                    }
                    s.next_w = next_event_w;
                    continue;
                }
                uint64_t c = 0;
                auto cit = s.counts.find(s.next_w);
                if (cit != s.counts.end()) {
                    c = cit->second;
                    s.counts.erase(cit);
                }
                close_window(s, s.next_w, c, out);
                ++s.next_w;
            }
            const bool alguna = std::any_of(s.q.begin(), s.q.end(), [](bool b) { return b; });
            if (!s.blocked && s.counts.empty() && !alguna) {
                it = st_.erase(it);
            } else {
                ++it;
            }
        }
        return out;
    }

    void add_drop(const std::string& dst, uint32_t proto, int64_t ts_s, const std::string& src, double p1, double ratio,
                  const std::string& event_id, const std::string& modelo) {
        const std::string key = dst + "/" + std::to_string(proto);
        auto [it, nuevo] = st_.try_emplace(key);
        State& s = it->second;
        if (nuevo) {
            s.dst = dst;
            s.proto = proto;
            s.next_w = have_clock_ ? clock_ : ts_s;
        }
        s.counts[std::max(ts_s, s.next_w)]++;
        if (s.drops == 0) {
            s.p1_min = p1;
            s.p1_max = p1;
            s.first_id = event_id;
        }
        s.drops++;
        s.p1_min = std::min(s.p1_min, p1);
        s.p1_max = std::max(s.p1_max, p1);
        s.p1_sum += p1;
        s.ratio_max = std::max(s.ratio_max, ratio);
        if (s.src.size() < kMaxSources || s.src.count(src) != 0) {
            s.src[src]++;
        }
        s.last_id = event_id;
        s.modelo = modelo;
    }

    std::size_t victims() const noexcept { return st_.size(); }
    const DdosShadowParams& params() const noexcept { return p_; }

private:
    static constexpr std::size_t kMaxSources = 4096;
    static constexpr std::size_t kTopSources = 5;

    struct State {
        std::string dst;
        uint32_t proto = 0;
        int64_t next_w = 0;
        std::map<int64_t, uint64_t> counts;
        std::deque<bool> q;
        bool blocked = false;
        int64_t last_pos = INT64_MIN / 2;
        int64_t start = 0;
        uint64_t drops = 0;
        uint64_t pos_windows = 0;
        double p1_min = 0.0;
        double p1_max = 0.0;
        double p1_sum = 0.0;
        double ratio_max = 0.0;
        std::unordered_map<std::string, uint64_t> src;
        std::string first_id;
        std::string last_id;
        std::string modelo;
    };

    DdosShadowRecord make(const State& s, bool inicio, int64_t start, int64_t end) const {
        DdosShadowRecord r;
        r.inicio = inicio;
        r.dst_ip = s.dst;
        r.proto = s.proto;
        r.start_s = start;
        r.end_s = end;
        r.drop_events = s.drops;
        r.positive_windows = s.pos_windows;
        r.p1_min = s.p1_min;
        r.p1_max = s.p1_max;
        r.p1_mean = s.drops ? s.p1_sum / static_cast<double>(s.drops) : 0.0;
        r.ratio_max = s.ratio_max;
        r.modelo = s.modelo;
        std::vector<std::pair<std::string, uint64_t>> v(s.src.begin(), s.src.end());
        std::sort(v.begin(), v.end(), [](const auto& a, const auto& b) {
            return a.second != b.second ? a.second > b.second : a.first < b.first;
        });
        if (v.size() > kTopSources) {
            v.resize(kTopSources);
        }
        r.top_sources = std::move(v);
        r.first_event_id = s.first_id;
        r.last_event_id = s.last_id;
        return r;
    }

    void close_window(State& s, int64_t w, uint64_t c, std::vector<DdosShadowRecord>& out) {
        const bool pos = c >= static_cast<uint64_t>(p_.m);
        s.q.push_back(pos);
        while (s.q.size() > static_cast<std::size_t>(p_.n)) {
            s.q.pop_front();
        }
        if (pos) {
            s.last_pos = w;
            s.pos_windows++;
        }
        const auto sum = std::count(s.q.begin(), s.q.end(), true);
        if (!s.blocked && sum >= p_.k) {
            s.blocked = true;
            s.start = w;
            out.push_back(make(s, true, w, w));
        } else if (s.blocked && w - s.last_pos >= p_.hold_s) {
            out.push_back(make(s, false, s.start, w));
            s.blocked = false;
            s.q.clear();
            s.drops = 0;
            s.pos_windows = 0;
            s.p1_sum = 0.0;
            s.ratio_max = 0.0;
            s.src.clear();
            s.first_id.clear();
            s.last_id.clear();
        }
    }

    DdosShadowParams p_;
    bool have_clock_ = false;
    int64_t clock_ = 0;
    std::map<std::string, State> st_;
};

inline std::string format_ddos_shadow_record(const DdosShadowRecord& r) {
    std::ostringstream o;
    o << (r.inicio ? "INICIO" : "FIN") << " victima=" << r.dst_ip << " proto=" << r.proto << " inicio_s=" << r.start_s;
    if (!r.inicio) {
        o << " fin_s=" << r.end_s << " duracion_s=" << (r.end_s - r.start_s);
    }
    o << " eventos_drop=" << r.drop_events << " ventanas_positivas=" << r.positive_windows << std::fixed
      << std::setprecision(4) << " p1_min=" << r.p1_min << " p1_media=" << r.p1_mean << " p1_max=" << r.p1_max
      << std::setprecision(3) << " ratio_max=" << r.ratio_max << " modelo=" << r.modelo << " origenes=";
    for (std::size_t i = 0; i < r.top_sources.size(); ++i) {
        o << (i ? "," : "") << r.top_sources[i].first << ":" << r.top_sources[i].second;
    }
    o << " primer_evento=" << r.first_event_id << " ultimo_evento=" << r.last_event_id;
    return o.str();
}

}  // namespace mldefender::firewall
