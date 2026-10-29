// Medida "antes" (DAY310): dos segmentos abiertos en el mismo segundo se pisan.
#include <gtest/gtest.h>
#include "correlation_writer.hpp"
#include <correlation_engine/correlation_reader.hpp>
#include <spdlog/spdlog.h>
#include <spdlog/sinks/null_sink.h>
#include <filesystem>
#include <fstream>
#include <unistd.h>
namespace fs = std::filesystem;
static protobuf::NetworkSecurityEvent ev(int i) {
    protobuf::NetworkSecurityEvent e;
    e.set_event_id("evt-" + std::to_string(i));
    e.set_final_classification("BENIGN");
    e.set_authoritative_source(::protobuf::DETECTOR_SOURCE_ML_PRIORITY);
    auto* nf = e.mutable_network_features();
    nf->set_community_id("1:abc" + std::to_string(i));
    nf->set_source_ip("10.0.0.1"); nf->set_destination_ip("10.0.0.2");
    nf->set_protocol_name("tcp");
    return e;
}
TEST(ColisionAntes, TresSegmentosEnElMismoSegundo) {
    std::string base = (fs::temp_directory_path() / ("colision_" + std::to_string(::getpid()))).string();
    fs::remove_all(base);
    ml_defender::CorrelationWriterConfig cfg;
    cfg.base_dir = base;
    cfg.hmac_key_hex = std::string(64, 'a');
    cfg.max_events_per_file = 1;
    auto lg = std::make_shared<spdlog::logger>("t", std::make_shared<spdlog::sinks::null_sink_mt>());
    {
        ml_defender::CorrelationWriter w(cfg, lg);
        for (int i = 0; i < 3; ++i) ASSERT_TRUE(w.write_record(ev(i)));
    }
    size_t ficheros = 0, lineas = 0;
    for (auto& p : fs::directory_iterator(base)) {
        ++ficheros;
        std::ifstream f(p.path()); std::string l;
        while (std::getline(f, l)) if (!l.empty()) ++lineas;
    }
    std::printf("[MEDIDA] ficheros=%zu lineas=%zu (escritas 3)\n", ficheros, lineas);
    EXPECT_EQ(lineas, 3u) << "se perdieron filas: un segmento piso a otro";
    fs::remove_all(base);
}
