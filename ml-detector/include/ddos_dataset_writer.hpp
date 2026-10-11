// ddos_dataset_writer.hpp — aRGus NDR — DAY287 [DDOS-DATASET-D287]
// Dataset DDoS v2 de laboratorio: una fila por evento, en el mismo punto que [DDOS-V2],
// sin depender de VERBOSE. CSV plano (sin HMAC): la integridad la da el sha256 en el
// manifiesto del entrenamiento. Un fichero por arranque del ml-detector.
#pragma once
#include <cstdint>
#include <cstdio>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <mutex>
#include <stdexcept>
#include <string>
#include <network_security.pb.h>

namespace ml_defender {

class DdosDatasetWriter {
public:
    explicit DdosDatasetWriter(const std::string& base_dir) {
        std::filesystem::create_directories(base_dir);
        std::time_t t = std::time(nullptr);
        std::tm tm{};
        localtime_r(&t, &tm);
        char ts[32];
        std::strftime(ts, sizeof(ts), "%Y%m%d-%H%M%S", &tm);
        path_ = base_dir + "/ddos_dataset_" + ts + ".csv";
        out_.open(path_, std::ios::out | std::ios::trunc);
        if (!out_) throw std::runtime_error("no se pudo abrir " + path_);
        out_ << "ts_ns,community_id,src_ip,dst_ip,src_port,dst_port,proto,event_kind,"
                "syn_ack_ratio,mean_packet_size,reflection_signature,packet_size_entropy,"
                "flow_packet_count,flow_completion_rate,victim_rate_ratio,victim_pps,"
                "old_ddos_prob,old_ddos_class\n";
        out_.flush();
    }

    ~DdosDatasetWriter() {
        std::lock_guard<std::mutex> lock(mutex_);
        out_.flush();
    }

    DdosDatasetWriter(const DdosDatasetWriter&) = delete;
    DdosDatasetWriter& operator=(const DdosDatasetWriter&) = delete;

    // old_class < 0 => la cabeza vieja no corrio en este evento: prob y clase = -1
    void write(const protobuf::NetworkSecurityEvent& ev, int old_class, double old_prob) {
        const auto& nf = ev.network_features();
        const auto& d  = nf.ddos_embedded();
        const auto& ts = ev.event_timestamp();
        const unsigned long long ts_ns =
            static_cast<unsigned long long>(ts.seconds()) * 1000000000ULL +
            static_cast<unsigned long long>(ts.nanos());
        char buf[1024];  // [DDOS-V2-D293] rasgos con %.9g: round-trip exacto de float (%.6g redondeaba)
        const int n = std::snprintf(buf, sizeof(buf),
            "%llu,%s,%s,%s,%u,%u,%u,%d,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.6f,%d\n",
            ts_ns, nf.community_id().c_str(), nf.source_ip().c_str(), nf.destination_ip().c_str(),
            static_cast<unsigned>(nf.source_port()), static_cast<unsigned>(nf.destination_port()),
            static_cast<unsigned>(nf.protocol_number()), static_cast<int>(ev.event_kind()),
            static_cast<double>(d.syn_ack_ratio()), static_cast<double>(d.mean_packet_size()),
            static_cast<double>(d.reflection_signature()), static_cast<double>(d.packet_size_entropy()),
            static_cast<double>(d.flow_packet_count()), static_cast<double>(d.flow_completion_rate()),
            static_cast<double>(d.victim_rate_ratio()), static_cast<double>(d.victim_pps()),
            old_class < 0 ? -1.0 : old_prob, old_class < 0 ? -1 : old_class);
        std::lock_guard<std::mutex> lock(mutex_);
        if (n <= 0 || n >= static_cast<int>(sizeof(buf))) { ++dropped_; return; }
        out_.write(buf, n);
        ++rows_;
        out_.flush();  // flush por fila: pipeline-stop no corre destructores (DAY287 P11, 26 filas perdidas)
    }

    const std::string& path() const noexcept { return path_; }

private:
    std::string path_;
    std::ofstream out_;
    std::mutex mutex_;
    uint64_t rows_ = 0;
    uint64_t dropped_ = 0;
};

}  // namespace ml_defender
