// test_etcd_client_hmac.cpp
// ML Defender — Unit tests for EtcdClient::get_hmac_key()
// Day 64; reescrito DAY316 ([ETCD-CLIENTE-D316], DEBT-ETCD-HA-TLS-RAFT-001 paso 5)
// Authors: Alonso Isidoro Roman + Claude (Anthropic)
//
// La librería solo habla HTTPS con certificado de cliente, así que el etcd-server falso es un httplib::SSLServer
// que exige certificado de cliente. E2 (decisión de Alonso, DAY316): CA desechable generada por el test con openssl
// en un directorio temporal que se borra al terminar; ninguna clave privada en el repo.
// Mismo define que la librería (CPPHTTPLIB_OPENSSL_SUPPORT, puesto por CMake) para que httplib.h sea idéntico (ODR).

#include <gtest/gtest.h>

#include <httplib.h>
#include <etcd_client/etcd_client.hpp>

#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <map>
#include <memory>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>

#include "etcd_client.hpp"
using namespace ml_detector;
namespace fs = std::filesystem;

// ─────────────────────────────────────────────────────────────────────────────
// PKI desechable: CA, certificado de servidor (SAN 127.0.0.1) y de cliente ml-detector
// ─────────────────────────────────────────────────────────────────────────────
struct PkiDesechable {
    fs::path dir;
    bool ok = false;
    PkiDesechable() {
        char plantilla[] = "/tmp/argus_test_pki_XXXXXX";
        char* d = mkdtemp(plantilla);
        if (!d) return;
        dir = d;
        const std::string D = dir.string();
        std::ostringstream c;
        c << "set -e; cd '" << D << "'\n"
          << "openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes -keyout ca.key -out ca.crt"
             " -days 1 -subj /CN=ca >/dev/null 2>&1\n"
          << "hoja() { openssl req -new -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes -keyout $1.key -out $1.csr"
             " -subj \"/O=test/OU=$1/CN=$1\" >/dev/null 2>&1;"
             " printf 'extendedKeyUsage=%s\\n%s\\n' \"$2\" \"$3\" > $1.ext;"
             " openssl x509 -req -in $1.csr -CA ca.crt -CAkey ca.key -CAcreateserial -days 1 -out $1.crt"
             " -extfile $1.ext >/dev/null 2>&1; }\n"
          << "hoja etcd-server serverAuth 'subjectAltName=IP:127.0.0.1'\n"
          << "hoja ml-detector clientAuth 'basicConstraints=CA:FALSE'\n";
        std::ofstream(D + "/gen.sh") << c.str();
        ok = std::system(("bash '" + D + "/gen.sh'").c_str()) == 0;
    }
    ~PkiDesechable() {
        std::error_code ec;
        if (!dir.empty()) fs::remove_all(dir, ec);
    }
    std::string f(const std::string& n) const { return (dir / n).string(); }
};

// ─────────────────────────────────────────────────────────────────────────────
// etcd-server falso con mTLS: responde /secrets/* con el status y cuerpo configurados
// ─────────────────────────────────────────────────────────────────────────────
class MockEtcdServer {
public:
    explicit MockEtcdServer(const PkiDesechable& p) {
        srv_ = std::make_unique<httplib::SSLServer>(p.f("etcd-server.crt").c_str(), p.f("etcd-server.key").c_str(),
                                                    p.f("ca.crt").c_str());
        srv_->Get(".*", [this](const httplib::Request& req, httplib::Response& res) {
            std::lock_guard<std::mutex> lk(m_);
            ++cuentas_[req.path];
            if (req.path == "/health") {  // el adaptador hace connect() (GET /health) al construirse
                res.status = 200;
                res.set_content(R"({"status":"ok"})", "application/json");
            } else if (req.path.rfind("/secrets/", 0) == 0) {
                res.status = secrets_status_;
                res.set_content(secrets_body_, "application/json");
            } else {
                res.status = 404;
                res.set_content("{}", "application/json");
            }
        });
        port_ = srv_->bind_to_any_port("127.0.0.1");
        hilo_ = std::thread([this] { srv_->listen_after_bind(); });
        srv_->wait_until_ready();
    }
    ~MockEtcdServer() {
        srv_->stop();
        if (hilo_.joinable()) hilo_.join();
    }
    void on_get_secrets(int http_status, const std::string& body) {
        std::lock_guard<std::mutex> lk(m_);
        secrets_status_ = http_status;
        secrets_body_ = body;
    }
    int cuenta(const std::string& ruta) {
        std::lock_guard<std::mutex> lk(m_);
        return cuentas_[ruta];
    }
    int port() const { return port_; }

private:
    std::unique_ptr<httplib::SSLServer> srv_;
    std::thread hilo_;
    int port_ = 0;
    std::mutex m_;
    std::map<std::string, int> cuentas_;
    int secrets_status_ = 200;
    std::string secrets_body_ = "{}";
};

// ─────────────────────────────────────────────────────────────────────────────
// Fixture
// ─────────────────────────────────────────────────────────────────────────────
class EtcdClientHmacTest : public ::testing::Test {
protected:
    static PkiDesechable* pki_;
    std::unique_ptr<MockEtcdServer> mock_;

    static void SetUpTestSuite() { pki_ = new PkiDesechable(); }
    static void TearDownTestSuite() {
        delete pki_;
        pki_ = nullptr;
    }

    void SetUp() override {
        ASSERT_TRUE(pki_ && pki_->ok) << "no se pudo generar la PKI desechable con openssl";
        mock_ = std::make_unique<MockEtcdServer>(*pki_);
    }

    etcd_client::Config base(int puerto) const {
        etcd_client::Config c;
        c.endpoints = {"https://127.0.0.1:" + std::to_string(puerto)};
        c.ca_file = pki_->f("ca.crt");
        c.cert_file = pki_->f("ml-detector.crt");
        c.key_file = pki_->f("ml-detector.key");
        c.connection_timeout_ms = 1000;
        c.retry_attempts = 1;
        c.retry_interval_ms = 100;
        c.encryption_enabled = false;  // sin seed.bin en los tests
        c.heartbeat_enabled = false;
        return c;
    }
};
PkiDesechable* EtcdClientHmacTest::pki_ = nullptr;

// ─────────────────────────────────────────────────────────────────────────────
// Happy path
// ─────────────────────────────────────────────────────────────────────────────

TEST_F(EtcdClientHmacTest, Returns64CharHexOnSuccess) {
    const std::string key64(64, 'a');
    mock_->on_get_secrets(200, R"({"key_hex":")" + key64 + R"(","component":"ml-detector"})");

    EtcdClient client(base(mock_->port()), "ml-detector");
    std::string result = client.get_hmac_key();

    EXPECT_EQ(result.size(), 64u);
    EXPECT_EQ(result, key64);
}

TEST_F(EtcdClientHmacTest, FallbackKeyFieldAccepted) {
    const std::string key64(64, 'b');
    mock_->on_get_secrets(200, R"({"key":")" + key64 + R"("})");

    EtcdClient client(base(mock_->port()), "ml-detector");
    EXPECT_EQ(client.get_hmac_key(), key64);
}

TEST_F(EtcdClientHmacTest, KeyHexTakesPriorityOverKey) {
    const std::string primary(64, 'c');
    const std::string fallback(64, 'd');
    mock_->on_get_secrets(200, R"({"key_hex":")" + primary + R"(","key":")" + fallback + R"("})");

    EtcdClient client(base(mock_->port()), "ml-detector");
    EXPECT_EQ(client.get_hmac_key(), primary);
}

// ─────────────────────────────────────────────────────────────────────────────
// Error paths — must return empty string, never throw
// ─────────────────────────────────────────────────────────────────────────────

TEST_F(EtcdClientHmacTest, Returns404AsEmptyString) {
    mock_->on_get_secrets(404, R"({"error":"not found"})");

    EtcdClient client(base(mock_->port()), "ml-detector");
    EXPECT_NO_THROW({
        std::string result = client.get_hmac_key();
        EXPECT_TRUE(result.empty()) << "404 should return empty string, got: " << result;
    });
    EXPECT_EQ(mock_->cuenta("/secrets/ml-detector"), 1) << "F3: un 4xx no se reintenta";
}

TEST_F(EtcdClientHmacTest, Returns500AsEmptyString) {
    mock_->on_get_secrets(500, "Internal Server Error");

    EtcdClient client(base(mock_->port()), "ml-detector");
    EXPECT_TRUE(client.get_hmac_key().empty());
}

TEST_F(EtcdClientHmacTest, MalformedJsonReturnsEmptyString) {
    mock_->on_get_secrets(200, "{not valid json}}}");

    EtcdClient client(base(mock_->port()), "ml-detector");
    EXPECT_TRUE(client.get_hmac_key().empty());
}

TEST_F(EtcdClientHmacTest, JsonWithNoKeyFieldReturnsEmptyString) {
    mock_->on_get_secrets(200, R"({"status":"ok","other_field":"value"})");

    EtcdClient client(base(mock_->port()), "ml-detector");
    EXPECT_TRUE(client.get_hmac_key().empty());
}

TEST_F(EtcdClientHmacTest, ConnectionRefusedReturnsEmptyString) {
    httplib::Server cerrado;
    const int puerto = cerrado.bind_to_any_port("127.0.0.1");
    cerrado.stop();

    EtcdClient client(base(puerto), "ml-detector");
    std::string result;
    EXPECT_NO_THROW(result = client.get_hmac_key());
    EXPECT_TRUE(result.empty());
}

// ─────────────────────────────────────────────────────────────────────────────
// Path construction
// ─────────────────────────────────────────────────────────────────────────────

TEST_F(EtcdClientHmacTest, UsesComponentNameInPath) {
    const std::string key64(64, 'e');
    mock_->on_get_secrets(200, R"({"key_hex":")" + key64 + R"(","component":"ml-detector"})");

    EtcdClient client(base(mock_->port()), "ml-detector");
    EXPECT_EQ(client.get_hmac_key().size(), 64u);
    EXPECT_EQ(mock_->cuenta("/secrets/ml-detector"), 1);
}

// ─────────────────────────────────────────────────────────────────────────────
// TLS: sin HTTPS no hay clave (antes bastaba http://)
// ─────────────────────────────────────────────────────────────────────────────

TEST_F(EtcdClientHmacTest, WrongCaReturnsEmptyString) {
    mock_->on_get_secrets(200, R"({"key_hex":")" + std::string(64, 'f') + R"("})");

    auto c = base(mock_->port());
    c.ca_file = pki_->f("ml-detector.crt");  // no es la CA que firmó al servidor
    EtcdClient client(c, "ml-detector");
    EXPECT_TRUE(client.get_hmac_key().empty());
    EXPECT_EQ(mock_->cuenta("/secrets/ml-detector"), 0);
}
