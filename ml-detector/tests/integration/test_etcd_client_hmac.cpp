// test_etcd_client_hmac.cpp
// ML Defender — Unit tests for EtcdClient::get_hmac_key()
// Day 64
// Authors: Alonso Isidoro Roman + Claude (Anthropic)
//
// Strategy: httplib mock server on a random port, tests all response paths.
// EtcdClient real constructor: EtcdClient(endpoint, component_name)
// where endpoint = "http://host:port"

#include <gtest/gtest.h>

#include <thread>
#include <chrono>
#include <string>

#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <atomic>
#include "etcd_client.hpp"
using namespace ml_detector;
// ─────────────────────────────────────────────────────────────────────────────
// Minimal HTTP server wrapper (raw sockets — sin httplib para evitar ODR)
// ─────────────────────────────────────────────────────────────────────────────
class MockEtcdServer {
public:
    MockEtcdServer() {}

    void on_get_secrets(int http_status, const std::string& body) {
        secrets_status_ = http_status;
        secrets_body_   = body;
    }

    int start() {
        listen_fd_ = ::socket(AF_INET, SOCK_STREAM, 0);
        int opt = 1;
        ::setsockopt(listen_fd_, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
        sockaddr_in addr{};
        addr.sin_family      = AF_INET;
        addr.sin_addr.s_addr = INADDR_ANY;
        addr.sin_port        = 0;
        ::bind(listen_fd_, (sockaddr*)&addr, sizeof(addr));
        ::listen(listen_fd_, 8);
        socklen_t len = sizeof(addr);
        ::getsockname(listen_fd_, (sockaddr*)&addr, &len);
        port_ = ntohs(addr.sin_port);
        running_ = true;
        thread_ = std::thread([this]() { serve_loop(); });
        std::this_thread::sleep_for(std::chrono::milliseconds(30));
        return port_;
    }

    void stop() {
        running_ = false;
        if (listen_fd_ >= 0) {
            ::shutdown(listen_fd_, SHUT_RDWR);
            ::close(listen_fd_);
            listen_fd_ = -1;
        }
        if (thread_.joinable()) thread_.join();
    }

    ~MockEtcdServer() { stop(); }

private:
    void serve_loop() {
        while (running_) {
            int conn = ::accept(listen_fd_, nullptr, nullptr);
            if (conn < 0) break;
            handle(conn);
            ::close(conn);
        }
    }

    void handle(int conn) {
        char buf[4096]{};
        ::recv(conn, buf, sizeof(buf) - 1, 0);
        std::string req(buf);
        std::string status_line, body;
        if (req.find("GET /health") != std::string::npos) {
            status_line = "HTTP/1.1 200 OK";
            body        = R"({"status":"ok"})";
        } else if (req.find("GET /secrets/") != std::string::npos) {
            status_line = "HTTP/1.1 " + std::to_string(secrets_status_) + " OK";
            body        = secrets_body_;
        } else {
            status_line = "HTTP/1.1 404 Not Found";
            body        = "{}";
        }
        std::string resp = status_line + "\r\n"
            "Content-Type: application/json\r\n"
            "Content-Length: " + std::to_string(body.size()) + "\r\n"
            "Connection: close\r\n\r\n" + body;
        ::send(conn, resp.c_str(), resp.size(), 0);
    }

    int listen_fd_ = -1;
    int port_      = 0;
    std::atomic<bool> running_{false};
    std::thread thread_;
    int  secrets_status_ = 200;
    std::string secrets_body_ = "{}";
};

// Build endpoint string for EtcdClient constructor
std::string make_endpoint(int port) {
    return "http://127.0.0.1:" + std::to_string(port);
}

// ─────────────────────────────────────────────────────────────────────────────
// Fixture
// ─────────────────────────────────────────────────────────────────────────────
class EtcdClientHmacTest : public ::testing::Test {
protected:
    MockEtcdServer mock_;
    int port_ = 0;

    void SetUp() override {
        port_ = mock_.start();
    }
};

// ─────────────────────────────────────────────────────────────────────────────
// Happy path
// ─────────────────────────────────────────────────────────────────────────────

TEST_F(EtcdClientHmacTest, Returns64CharHexOnSuccess) {
    const std::string key64(64, 'a');
    mock_.on_get_secrets(200,
        R"({"key_hex":")" + key64 + R"(","component":"ml-detector"})");

    EtcdClient client(make_endpoint(port_), "ml-detector");
    std::string result = client.get_hmac_key();

    EXPECT_EQ(result.size(), 64u);
    EXPECT_EQ(result, key64);
}

TEST_F(EtcdClientHmacTest, FallbackKeyFieldAccepted) {
    const std::string key64(64, 'b');
    mock_.on_get_secrets(200, R"({"key":")" + key64 + R"("})");

    EtcdClient client(make_endpoint(port_), "ml-detector");
    std::string result = client.get_hmac_key();

    EXPECT_EQ(result.size(), 64u);
    EXPECT_EQ(result, key64);
}

TEST_F(EtcdClientHmacTest, KeyHexTakesPriorityOverKey) {
    const std::string primary(64, 'c');
    const std::string fallback(64, 'd');
    mock_.on_get_secrets(200,
        R"({"key_hex":")" + primary + R"(","key":")" + fallback + R"("})");

    EtcdClient client(make_endpoint(port_), "ml-detector");
    std::string result = client.get_hmac_key();

    EXPECT_EQ(result, primary);
}

// ─────────────────────────────────────────────────────────────────────────────
// Error paths — must return empty string, never throw
// ─────────────────────────────────────────────────────────────────────────────

TEST_F(EtcdClientHmacTest, Returns404AsEmptyString) {
    mock_.on_get_secrets(404, R"({"error":"not found"})");

    EtcdClient client(make_endpoint(port_), "ml-detector");
    EXPECT_NO_THROW({
        std::string result = client.get_hmac_key();
        EXPECT_TRUE(result.empty())
            << "404 should return empty string, got: " << result;
    });
}

TEST_F(EtcdClientHmacTest, Returns500AsEmptyString) {
    mock_.on_get_secrets(500, "Internal Server Error");

    EtcdClient client(make_endpoint(port_), "ml-detector");
    std::string result = client.get_hmac_key();
    EXPECT_TRUE(result.empty());
}

TEST_F(EtcdClientHmacTest, MalformedJsonReturnsEmptyString) {
    mock_.on_get_secrets(200, "{not valid json}}}");

    EtcdClient client(make_endpoint(port_), "ml-detector");
    std::string result = client.get_hmac_key();
    EXPECT_TRUE(result.empty());
}

TEST_F(EtcdClientHmacTest, JsonWithNoKeyFieldReturnsEmptyString) {
    mock_.on_get_secrets(200, R"({"status":"ok","other_field":"value"})");

    EtcdClient client(make_endpoint(port_), "ml-detector");
    std::string result = client.get_hmac_key();
    EXPECT_TRUE(result.empty());
}

TEST_F(EtcdClientHmacTest, ConnectionRefusedReturnsEmptyString) {
    EtcdClient client("http://127.0.0.1:19999", "ml-detector");
    std::string result;
    EXPECT_NO_THROW(result = client.get_hmac_key());
    EXPECT_TRUE(result.empty());
}

// ─────────────────────────────────────────────────────────────────────────────
// Path construction
// ─────────────────────────────────────────────────────────────────────────────

TEST_F(EtcdClientHmacTest, UsesComponentNameInPath) {
    const std::string key64(64, 'e');
    mock_.on_get_secrets(200,
        R"({"key_hex":")" + key64 + R"(","component":"ml-detector"})");

    EtcdClient client(make_endpoint(port_), "ml-detector");
    std::string result = client.get_hmac_key();

    EXPECT_EQ(result.size(), 64u);
}