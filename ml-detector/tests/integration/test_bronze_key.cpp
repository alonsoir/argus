// test_bronze_key.cpp — DAY310 [BRONCE-CLAVE-D310]: clave del bronce en el CorrelationWriter.
// Escribe con el CorrelationWriter REAL y verifica con parse_and_verify REAL (correlation-engine), como
// test_correlation_roundtrip. Reglas que fija: nunca bronce sin firma; cada segmento, una sola clave; un cambio de
// clave cierra el segmento abierto; una clave invalida no sustituye a la vigente; dos segmentos abiertos en el mismo
// segundo no se pisan (medido DAY310: antes se perdian filas).
#include <gtest/gtest.h>

#include "correlation_writer.hpp"
#include <correlation_engine/correlation_reader.hpp>

#include <network_security.pb.h>

#include <spdlog/spdlog.h>
#include <spdlog/sinks/null_sink.h>

#include <algorithm>
#include <cctype>
#include <cstdint>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <memory>
#include <string>
#include <vector>
#include <unistd.h>

namespace fs = std::filesystem;
using namespace argus::correlation;
using ml_defender::CorrelationWriter;
using KeyChange = ml_defender::CorrelationWriter::KeyChange;

namespace {

const std::string K1(64, 'a');
const std::string K2(64, 'b');

std::vector<uint8_t> hex_to_bytes(const std::string& hex) {
    std::vector<uint8_t> out;
    for (size_t i = 0; i + 1 < hex.size(); i += 2) {
        unsigned int b = 0;
        std::sscanf(hex.c_str() + i, "%02x", &b);
        out.push_back(static_cast<uint8_t>(b));
    }
    return out;
}

protobuf::NetworkSecurityEvent evento(int i) {
    protobuf::NetworkSecurityEvent e;
    e.set_event_id("evt-bk-" + std::to_string(i));
    e.set_originating_node_id("node-bk");
    e.set_final_classification("BENIGN");
    e.set_threat_category("NORMAL");
    e.set_authoritative_source(::protobuf::DETECTOR_SOURCE_ML_PRIORITY);
    auto* nf = e.mutable_network_features();
    nf->set_community_id("1:bk" + std::to_string(i));
    nf->set_source_ip("192.168.100.50");
    nf->set_destination_ip("192.168.100.1");
    nf->set_source_port(40000u + static_cast<unsigned>(i));
    nf->set_destination_port(80u);
    nf->set_protocol_name("tcp");
    nf->mutable_flow_start_time()->set_seconds(1793160000 + i);
    return e;
}

struct Dir {
    std::string path;
    explicit Dir(const char* nombre)
        : path((fs::temp_directory_path() / (std::string(nombre) + "_" + std::to_string(::getpid()))).string()) {
        fs::remove_all(path);
    }
    ~Dir() { fs::remove_all(path); }
};

std::shared_ptr<spdlog::logger> logger_nulo() {
    return std::make_shared<spdlog::logger>("bk-test", std::make_shared<spdlog::sinks::null_sink_mt>());
}

ml_defender::CorrelationWriterConfig cfg(const std::string& base, const std::string& clave) {
    ml_defender::CorrelationWriterConfig c;
    c.base_dir = base;
    c.hmac_key_hex = clave;
    return c;
}

// Segmentos finales (*.csv) ordenados por nombre, y sus lineas no vacias.
std::vector<std::vector<std::string>> segmentos(const std::string& base) {
    std::vector<fs::path> ficheros;
    for (auto& p : fs::directory_iterator(base))
        if (p.path().extension() == ".csv") ficheros.push_back(p.path());
    std::sort(ficheros.begin(), ficheros.end());
    std::vector<std::vector<std::string>> out;
    for (auto& f : ficheros) {
        std::ifstream in(f);
        std::vector<std::string> lineas;
        for (std::string l; std::getline(in, l);)
            if (!l.empty()) lineas.push_back(l);
        out.push_back(lineas);
    }
    return out;
}

bool verifica(const std::string& linea, const std::string& clave) {
    return parse_and_verify(linea, hex_to_bytes(clave)).has_value();
}

}  // namespace

TEST(BronzeKey, SinClaveNoEscribeYCuenta) {
    Dir d("bk_sin_clave");
    {
        CorrelationWriter w(cfg(d.path, ""), logger_nulo());
        EXPECT_FALSE(w.has_key());
        EXPECT_FALSE(w.write_record(evento(1)));
        EXPECT_FALSE(w.write_record(evento(2)));
        const auto s = w.get_stats();
        EXPECT_EQ(s.records_sin_clave, 2u);
        EXPECT_EQ(s.records_written, 0u);
    }
    EXPECT_TRUE(segmentos(d.path).empty()) << "sin clave no puede quedar ningun segmento: nunca bronce sin firma";
}

TEST(BronzeKey, PrimeraClaveEscribeFirmadoConElla) {
    Dir d("bk_primera");
    {
        CorrelationWriter w(cfg(d.path, ""), logger_nulo());
        EXPECT_EQ(w.set_key(K1), KeyChange::Primera);
        EXPECT_TRUE(w.has_key());
        EXPECT_TRUE(w.write_record(evento(1)));
    }
    const auto segs = segmentos(d.path);
    ASSERT_EQ(segs.size(), 1u);
    ASSERT_EQ(segs[0].size(), 1u);
    EXPECT_TRUE(verifica(segs[0][0], K1));
}

TEST(BronzeKey, MismaClaveNoCortaElSegmento) {
    Dir d("bk_misma");
    {
        CorrelationWriter w(cfg(d.path, ""), logger_nulo());
        ASSERT_EQ(w.set_key(K1), KeyChange::Primera);
        EXPECT_TRUE(w.write_record(evento(1)));
        std::string cerrado;
        EXPECT_EQ(w.set_key(K1, &cerrado), KeyChange::Igual);
        EXPECT_TRUE(cerrado.empty());
        EXPECT_TRUE(w.write_record(evento(2)));
    }
    const auto segs = segmentos(d.path);
    ASSERT_EQ(segs.size(), 1u);
    EXPECT_EQ(segs[0].size(), 2u);
}

TEST(BronzeKey, ClaveDistintaCierraElSegmentoYCadaUnoVerificaConLaSuya) {
    Dir d("bk_cambiada");
    std::string cerrado;
    {
        CorrelationWriter w(cfg(d.path, K1), logger_nulo());
        EXPECT_TRUE(w.write_record(evento(1)));
        EXPECT_EQ(w.set_key(K2, &cerrado), KeyChange::Cambiada);
        ASSERT_FALSE(cerrado.empty());
        EXPECT_TRUE(fs::exists(cerrado)) << "el segmento de la clave vieja debe quedar cerrado (rename) al cambiar";
        EXPECT_TRUE(w.write_record(evento(2)));
    }
    const auto segs = segmentos(d.path);
    ASSERT_EQ(segs.size(), 2u) << "un segmento por clave";
    std::vector<std::string> todas;
    for (const auto& s : segs) {
        ASSERT_EQ(s.size(), 1u);
        todas.push_back(s[0]);
    }
    const int con_k1 = static_cast<int>(std::count_if(todas.begin(), todas.end(), [](auto& l) { return verifica(l, K1); }));
    const int con_k2 = static_cast<int>(std::count_if(todas.begin(), todas.end(), [](auto& l) { return verifica(l, K2); }));
    EXPECT_EQ(con_k1, 1);
    EXPECT_EQ(con_k2, 1);
    for (const auto& l : todas) EXPECT_NE(verifica(l, K1), verifica(l, K2)) << "cada fila verifica con una sola clave";
}

TEST(BronzeKey, ClaveInvalidaConservaLaVigente) {
    Dir d("bk_invalida");
    {
        CorrelationWriter w(cfg(d.path, K1), logger_nulo());
        EXPECT_EQ(w.set_key(std::string(63, 'c')), KeyChange::Invalida);
        EXPECT_EQ(w.set_key(std::string(64, 'z')), KeyChange::Invalida);
        EXPECT_TRUE(w.write_record(evento(1)));
    }
    const auto segs = segmentos(d.path);
    ASSERT_EQ(segs.size(), 1u);
    ASSERT_EQ(segs[0].size(), 1u);
    EXPECT_TRUE(verifica(segs[0][0], K1));
}

TEST(BronzeKey, HuellaDeOchoHexEstableYSinLaClave) {
    const std::string h1 = CorrelationWriter::fingerprint(K1);
    const std::string h2 = CorrelationWriter::fingerprint(K2);
    EXPECT_EQ(h1.size(), 8u);
    EXPECT_TRUE(std::all_of(h1.begin(), h1.end(), [](char c) { return std::isxdigit(static_cast<unsigned char>(c)); }));
    EXPECT_EQ(h1, CorrelationWriter::fingerprint(K1));
    EXPECT_NE(h1, h2);
    EXPECT_EQ(K1.find(h1), std::string::npos);
    EXPECT_EQ(CorrelationWriter::fingerprint("xx"), "invalida");
}

TEST(BronzeKey, SegmentosAbiertosEnElMismoSegundoNoSePisan) {
    Dir d("bk_colision");
    auto c = cfg(d.path, K1);
    c.max_events_per_file = 1;  // un segmento por fila: los tres se abren en el mismo segundo
    {
        CorrelationWriter w(c, logger_nulo());
        for (int i = 0; i < 3; ++i) ASSERT_TRUE(w.write_record(evento(i)));
    }
    const auto segs = segmentos(d.path);
    size_t lineas = 0;
    for (const auto& s : segs) lineas += s.size();
    EXPECT_EQ(segs.size(), 3u);
    EXPECT_EQ(lineas, 3u) << "se perdieron filas: un segmento piso a otro";
}
