// etcd-client/src/http_client.cpp
// Day 62: Contextual logging - timestamp + component_name on every HTTP call
#include "etcd_client/etcd_client.hpp"
#include <httplib.h>
#include <string>
#include <iostream>
#include <thread>
#include <chrono>
#include <sstream>
#include <iomanip>
#include <ctime>

namespace etcd_client {
namespace http {

static std::string iso8601_now() {
    auto now = std::chrono::system_clock::now();
    auto now_t = std::chrono::system_clock::to_time_t(now);
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        now.time_since_epoch()) % 1000;
    std::ostringstream ss;
    ss << std::put_time(std::gmtime(&now_t), "%Y-%m-%dT%H:%M:%S")
       << '.' << std::setfill('0') << std::setw(3) << ms.count() << 'Z';
    return ss.str();
}

static long duration_us(std::chrono::steady_clock::time_point start) {
    return std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::steady_clock::now() - start).count();
}

Response post(const std::string& host, int port, const std::string& path,
              const std::string& body, int timeout_seconds, int max_retries,
              int backoff_seconds, const std::string& component_name) {
    Response response;
    for (int attempt = 0; attempt < max_retries; ++attempt) {
        try {
            httplib::Client cli(host, port);
            cli.set_connection_timeout(timeout_seconds);
            cli.set_read_timeout(timeout_seconds);
            cli.set_write_timeout(timeout_seconds);
            httplib::Headers headers = {
                {"X-Component-Name", component_name},
                {"X-Request-Timestamp", iso8601_now()}
            };
            std::cout << "[HTTP→] POST " << host << ":" << port << path
                      << " | ts=" << iso8601_now()
                      << " | component=" << component_name << std::endl;
            auto t0 = std::chrono::steady_clock::now();
            auto res = cli.Post(path, headers, body, "application/json");
            if (res) {
                response.status_code = res->status;
                response.body = res->body;
                response.success = (res->status >= 200 && res->status < 300);
                std::cout << "[HTTP←] " << res->status << " | POST " << path
                          << " | duration_us=" << duration_us(t0)
                          << " | component=" << component_name << std::endl;
                if (response.success) return response;
                std::cerr << "⚠️  HTTP POST failed: " << res->status
                          << " - " << res->body << std::endl;
            } else {
                std::cerr << "⚠️  HTTP POST connection failed to "
                          << host << ":" << port << path << std::endl;
            }
        } catch (const std::exception& e) {
            std::cerr << "⚠️  HTTP POST exception: " << e.what() << std::endl;
        }
        if (attempt < max_retries - 1) {
            std::cerr << "🔄 Retrying in " << backoff_seconds
                      << "s (attempt " << (attempt + 2) << "/" << max_retries << ")" << std::endl;
            std::this_thread::sleep_for(std::chrono::seconds(backoff_seconds));
        }
    }
    response.success = false;
    return response;
}

Response get(const std::string& host, int port, const std::string& path,
             int timeout_seconds, int max_retries, int backoff_seconds,
             const std::string& component_name) {
    Response response;
    for (int attempt = 0; attempt < max_retries; ++attempt) {
        try {
            httplib::Client cli(host, port);
            cli.set_connection_timeout(timeout_seconds);
            cli.set_read_timeout(timeout_seconds);
            httplib::Headers headers = {
                {"X-Component-Name", component_name},
                {"X-Request-Timestamp", iso8601_now()}
            };
            std::cout << "[HTTP→] GET " << host << ":" << port << path
                      << " | ts=" << iso8601_now()
                      << " | component=" << component_name << std::endl;
            auto t0 = std::chrono::steady_clock::now();
            auto res = cli.Get(path, headers);
            if (res) {
                response.status_code = res->status;
                response.body = res->body;
                response.success = (res->status >= 200 && res->status < 300);
                std::cout << "[HTTP←] " << res->status << " | GET " << path
                          << " | duration_us=" << duration_us(t0)
                          << " | component=" << component_name << std::endl;
                if (response.success) return response;
                std::cerr << "⚠️  HTTP GET failed: " << res->status
                          << " - " << res->body << std::endl;
            } else {
                std::cerr << "⚠️  HTTP GET connection failed to "
                          << host << ":" << port << path << std::endl;
            }
        } catch (const std::exception& e) {
            std::cerr << "⚠️  HTTP GET exception: " << e.what() << std::endl;
        }
        if (attempt < max_retries - 1) {
            std::cerr << "🔄 Retrying in " << backoff_seconds
                      << "s (attempt " << (attempt + 2) << "/" << max_retries << ")" << std::endl;
            std::this_thread::sleep_for(std::chrono::seconds(backoff_seconds));
        }
    }
    response.success = false;
    return response;
}

Response put(const std::string& host, int port, const std::string& path,
             const std::string& body, const std::string& content_type,
             int timeout_seconds, int max_retries, int backoff_seconds,
             size_t original_size, const std::string& component_name) {
    Response response;
    for (int attempt = 0; attempt < max_retries; ++attempt) {
        try {
            httplib::Client cli(host, port);
            cli.set_connection_timeout(timeout_seconds);
            cli.set_read_timeout(timeout_seconds);
            cli.set_write_timeout(timeout_seconds);
            httplib::Headers headers = {
                {"Content-Type", content_type},
                {"X-Component-Name", component_name},
                {"X-Request-Timestamp", iso8601_now()}
            };
            if (original_size > 0) {
                headers.insert({"X-Original-Size", std::to_string(original_size)});
            }
            std::cout << "[HTTP→] PUT " << host << ":" << port << path
                      << " | ts=" << iso8601_now()
                      << " | component=" << component_name << std::endl;
            auto t0 = std::chrono::steady_clock::now();
            auto res = cli.Put(path.c_str(), headers, body, content_type.c_str());
            if (res) {
                response.status_code = res->status;
                response.body = res->body;
                response.success = (res->status >= 200 && res->status < 300);
                std::cout << "[HTTP←] " << res->status << " | PUT " << path
                          << " | duration_us=" << duration_us(t0)
                          << " | component=" << component_name << std::endl;
                if (response.success) return response;
                std::cerr << "⚠️  HTTP PUT failed: " << res->status
                          << " - " << res->body << std::endl;
            } else {
                std::cerr << "⚠️  HTTP PUT connection failed to "
                          << host << ":" << port << path << std::endl;
            }
        } catch (const std::exception& e) {
            std::cerr << "⚠️  HTTP PUT exception: " << e.what() << std::endl;
        }
        if (attempt < max_retries - 1) {
            std::cerr << "🔄 Retrying in " << backoff_seconds
                      << "s (attempt " << (attempt + 2) << "/" << max_retries << ")" << std::endl;
            std::this_thread::sleep_for(std::chrono::seconds(backoff_seconds));
        }
    }
    response.success = false;
    return response;
}

Response del(const std::string& host, int port, const std::string& path,
             int timeout_seconds, int max_retries, int backoff_seconds,
             const std::string& component_name) {
    Response response;
    for (int attempt = 0; attempt < max_retries; ++attempt) {
        try {
            httplib::Client cli(host, port);
            cli.set_connection_timeout(timeout_seconds);
            cli.set_read_timeout(timeout_seconds);
            httplib::Headers headers = {
                {"X-Component-Name", component_name},
                {"X-Request-Timestamp", iso8601_now()}
            };
            std::cout << "[HTTP→] DELETE " << host << ":" << port << path
                      << " | ts=" << iso8601_now()
                      << " | component=" << component_name << std::endl;
            auto t0 = std::chrono::steady_clock::now();
            auto res = cli.Delete(path, headers);
            if (res) {
                response.status_code = res->status;
                response.body = res->body;
                response.success = (res->status >= 200 && res->status < 300);
                std::cout << "[HTTP←] " << res->status << " | DELETE " << path
                          << " | duration_us=" << duration_us(t0)
                          << " | component=" << component_name << std::endl;
                if (response.success) return response;
                std::cerr << "⚠️  HTTP DELETE failed: " << res->status
                          << " - " << res->body << std::endl;
            } else {
                std::cerr << "⚠️  HTTP DELETE connection failed to "
                          << host << ":" << port << path << std::endl;
            }
        } catch (const std::exception& e) {
            std::cerr << "⚠️  HTTP DELETE exception: " << e.what() << std::endl;
        }
        if (attempt < max_retries - 1) {
            std::cerr << "🔄 Retrying in " << backoff_seconds
                      << "s (attempt " << (attempt + 2) << "/" << max_retries << ")" << std::endl;
            std::this_thread::sleep_for(std::chrono::seconds(backoff_seconds));
        }
    }
    response.success = false;
    return response;
}

} // namespace http
} // namespace etcd_client
