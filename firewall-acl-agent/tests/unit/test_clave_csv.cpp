// test_clave_csv.cpp — [FW-CSV-CLAVE-B2-D316] DEBT-FW-HMAC-KEY-ALARM-001 (decisión G4 de Alonso, DAY316): clave HMAC del
// CSV pedida cada intervalo (ClaveCsv) y un CSV por clave con la huella en el nombre (FirewallLogger).
#include <gtest/gtest.h>

#include <chrono>
#include <filesystem>
#include <fstream>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include <openssl/hmac.h>

#include "firewall/clave_csv.hpp"
#include "firewall/logger.hpp"

namespace fs = std::filesystem;
using namespace mldefender::firewall;

namespace {

Clave clave_de(uint8_t b) { return Clave(32, b); }

// Proveedor y sumidero controlados por el test
struct Banco {
    std::mutex m;
    std::optional<Clave> siguiente;
    std::vector<std::string> lineas;
    std::time_t ahora = 1700000000;
    int llamadas = 0;

    ClaveCsv::Proveedor proveedor() {
        return [this]() { std::lock_guard<std::mutex> lk(m); ++llamadas; return siguiente; };
    }
    ClaveCsv::Sumidero sumidero() {
        return [this](const std::string& l) { std::lock_guard<std::mutex> lk(m); lineas.push_back(l); };
    }
    ClaveCsv::Reloj reloj() {
        return [this]() { return ahora; };
    }
    void pon(std::optional<Clave> k) { std::lock_guard<std::mutex> lk(m); siguiente = std::move(k); }
    std::string ultima() { std::lock_guard<std::mutex> lk(m); return lineas.empty() ? "" : lineas.back(); }
    size_t cuantas(const std::string& marca) {
        std::lock_guard<std::mutex> lk(m);
        size_t n = 0;
        for (const auto& l : lineas) n += l.find(marca) != std::string::npos;
        return n;
    }
};

}  // namespace

TEST(ClaveCsvTest, HuellaConocida) {
    // SHA-256 de 32 bytes a cero = 66687aad... (la misma huella que dan el etcd-server y el ml-detector)
    EXPECT_EQ(huella_clave(clave_de(0)), "66687aad");
    EXPECT_NE(huella_clave(clave_de(1)), huella_clave(clave_de(2)));
}

TEST(ClaveCsvTest, ConClaveAlArrancar) {
    Banco b;
    b.pon(clave_de(1));
    ClaveCsv c(b.proveedor(), 60, b.sumidero(), b.reloj());
    c.comprobar();
    ASSERT_TRUE(c.clave().has_value());
    EXPECT_EQ(*c.clave(), clave_de(1));
    EXPECT_NE(b.ultima().find("[FW-CSV-CLAVE] clave HMAC del CSV recibida"), std::string::npos);
    EXPECT_NE(b.ultima().find(huella_clave(clave_de(1))), std::string::npos);
    EXPECT_NE(b.ultima().find("al arrancar"), std::string::npos);
}

TEST(ClaveCsvTest, SinClaveAvisaYCuentaFilasLuegoRecupera) {
    Banco b;
    ClaveCsv c(b.proveedor(), 60, b.sumidero(), b.reloj());
    c.comprobar();
    EXPECT_FALSE(c.clave().has_value());
    EXPECT_EQ(b.cuantas("[FW-CSV-SIN-CLAVE]"), 1u);
    c.fila_sin_clave();
    c.fila_sin_clave();
    c.fila_sin_clave();
    b.ahora += 60;
    c.comprobar();
    EXPECT_EQ(b.cuantas("[FW-CSV-SIN-CLAVE]"), 2u);
    EXPECT_NE(b.ultima().find("(60 s): 3 filas sin escribir"), std::string::npos) << b.ultima();

    b.pon(clave_de(7));
    b.ahora += 60;
    c.comprobar();
    ASSERT_TRUE(c.clave().has_value());
    EXPECT_NE(b.ultima().find("[FW-CSV-CLAVE-RECUPERADA]"), std::string::npos) << b.ultima();
    EXPECT_NE(b.ultima().find("tras 120 s sin clave"), std::string::npos) << b.ultima();
    EXPECT_NE(b.ultima().find("3 filas sin escribir"), std::string::npos) << b.ultima();
}

TEST(ClaveCsvTest, ServidorCaidoSigueFirmandoYConfirmaAlVolver) {
    Banco b;
    b.pon(clave_de(1));
    ClaveCsv c(b.proveedor(), 60, b.sumidero(), b.reloj());
    c.comprobar();
    b.pon(std::nullopt);
    b.ahora += 60;
    c.comprobar();
    ASSERT_TRUE(c.clave().has_value());
    EXPECT_EQ(*c.clave(), clave_de(1));
    EXPECT_NE(b.ultima().find("[FW-CSV-CLAVE-SIN-CONFIRMAR]"), std::string::npos);
    EXPECT_EQ(b.cuantas("[FW-CSV-SIN-CLAVE]"), 0u);

    b.pon(clave_de(1));
    b.ahora += 60;
    c.comprobar();
    EXPECT_NE(b.ultima().find("[FW-CSV-CLAVE-CONFIRMADA]"), std::string::npos);
    EXPECT_NE(b.ultima().find("la misma clave"), std::string::npos);
}

TEST(ClaveCsvTest, OtraClaveSeCambia) {
    Banco b;
    b.pon(clave_de(1));
    ClaveCsv c(b.proveedor(), 60, b.sumidero(), b.reloj());
    c.comprobar();
    b.pon(clave_de(2));
    c.comprobar();
    ASSERT_TRUE(c.clave().has_value());
    EXPECT_EQ(*c.clave(), clave_de(2));
    EXPECT_NE(b.ultima().find("[FW-CSV-CLAVE-CAMBIADA]"), std::string::npos);
    EXPECT_NE(b.ultima().find(huella_clave(clave_de(1)) + " -> " + huella_clave(clave_de(2))), std::string::npos);
    const size_t n = b.lineas.size();
    c.comprobar();  // la misma: sin línea nueva
    EXPECT_EQ(b.lineas.size(), n);
}

TEST(ClaveCsvTest, ClaveDeTamanoInvalidoNoSeUsa) {
    Banco b;
    b.pon(Clave(16, 9));
    ClaveCsv c(b.proveedor(), 60, b.sumidero(), b.reloj());
    c.comprobar();
    EXPECT_FALSE(c.clave().has_value());
    EXPECT_EQ(b.cuantas("[FW-CSV-SIN-CLAVE]"), 1u);
}

TEST(ClaveCsvTest, HiloPideEnseguidaYParaSinEsperarElIntervalo) {
    Banco b;
    b.pon(clave_de(3));
    auto c = std::make_unique<ClaveCsv>(b.proveedor(), 3600, b.sumidero());
    c->arrancar();
    const auto fin = std::chrono::steady_clock::now() + std::chrono::seconds(2);
    while (!c->clave().has_value() && std::chrono::steady_clock::now() < fin)
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    EXPECT_TRUE(c->clave().has_value());
    const auto t0 = std::chrono::steady_clock::now();
    c.reset();
    EXPECT_LT(std::chrono::steady_clock::now() - t0, std::chrono::seconds(1));
}

TEST(CsvPorClaveTest, UnFicheroPorClaveConLaHuellaEnElNombre) {
    const std::string dir = "/tmp/ml_defender_csv_por_clave_test";
    fs::remove_all(dir);
    fs::create_directories(dir);
    {
        FirewallLogger logger(dir);
        BlockedEvent e;
        e.timestamp_ms = 1732901123456ULL;
        e.src_ip = "192.168.1.100";
        e.dst_ip = "10.0.0.5";
        e.threat_type = "DDOS_ATTACK";
        e.action = "BLOCKED";
        e.confidence = 0.9;

        ASSERT_TRUE(logger.append_csv_log(e, clave_de(1)));
        ASSERT_TRUE(logger.append_csv_log(e, clave_de(1)));
        const std::string f1 = logger.csv_actual();
        EXPECT_NE(f1.find("/firewall_blocks-"), std::string::npos);
        EXPECT_NE(f1.find("-" + huella_clave(clave_de(1)) + ".csv"), std::string::npos) << f1;

        ASSERT_TRUE(logger.append_csv_log(e, clave_de(2)));
        const std::string f2 = logger.csv_actual();
        EXPECT_NE(f2, f1);
        EXPECT_NE(f2.find("-" + huella_clave(clave_de(2))), std::string::npos) << f2;

        auto lineas = [](const std::string& f) {
            std::ifstream in(f);
            std::vector<std::string> v;
            for (std::string l; std::getline(in, l);) v.push_back(l);
            return v;
        };
        const auto l1 = lineas(f1), l2 = lineas(f2);
        ASSERT_EQ(l1.size(), 2u);
        ASSERT_EQ(l2.size(), 1u);
        // cada fila se verifica con la clave cuya huella lleva su fichero
        const auto coma = l2[0].rfind(',');
        const std::string datos = l2[0].substr(0, coma), firma = l2[0].substr(coma + 1);
        unsigned char md[EVP_MAX_MD_SIZE];
        unsigned int n = 0;
        const Clave k2 = clave_de(2);
        HMAC(EVP_sha256(), k2.data(), static_cast<int>(k2.size()), reinterpret_cast<const unsigned char*>(datos.data()),
             datos.size(), md, &n);
        char hex[2 * EVP_MAX_MD_SIZE + 1];
        for (unsigned int i = 0; i < n; ++i) std::snprintf(hex + 2 * i, 3, "%02x", md[i]);
        EXPECT_EQ(firma, std::string(hex, 2 * n));
    }
    size_t viejos = 0;
    for (const auto& it : fs::directory_iterator(dir)) viejos += it.path().filename() == "firewall_blocks.csv";
    EXPECT_EQ(viejos, 0u);
    fs::remove_all(dir);
}
