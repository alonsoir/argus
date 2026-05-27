// ZMQ Pool Manager for eBPF Sniffer
// Manages ZeroMQ connection pooling and load balancing with thread-safe operations

#include "zmq_pool_manager.hpp"
#include <zmq.h>
#include <iostream>
#include <thread>
#include <chrono>
#include <cstring>

namespace sniffer {

ZMQPoolManager::ZMQPoolManager(int pool_size)
    : pool_size_(pool_size), current_socket_(0) {

    if (pool_size <= 0) {
        throw std::runtime_error("ZMQ pool size must be positive");
    }

    // Create ZMQ context
    context_ = zmq_ctx_new();
    if (!context_) {
        throw std::runtime_error("Failed to create ZMQ context: " +
                                 std::string(zmq_strerror(errno)));
    }

    // Reserve space for sockets and their mutexes
    sockets_.reserve(pool_size);
    socket_mutexes_.reserve(pool_size);

    // Initialize socket pool and mutexes
    for (int i = 0; i < pool_size; ++i) {
        void* socket = zmq_socket(context_, ZMQ_PUSH);
        if (!socket) {
            // Cleanup on failure
            for (int j = 0; j < i; ++j) {
                zmq_close(sockets_[j]);
            }
            zmq_ctx_destroy(context_);
            throw std::runtime_error("Failed to create ZMQ socket " +
                                     std::to_string(i) + ": " +
                                     std::string(zmq_strerror(errno)));
        }
        sockets_.push_back(socket);

        // Create mutex for this socket (must use unique_ptr because mutex is non-copyable)
        socket_mutexes_.push_back(std::make_unique<std::mutex>());
    }

    std::cout << "[INFO] ZMQPoolManager: Initialized with " << pool_size
              << " sockets (thread-safe with per-socket mutexes)" << std::endl;
}

ZMQPoolManager::~ZMQPoolManager() {
    shutdown();
}

bool ZMQPoolManager::connect(const std::string& endpoint) {
    std::lock_guard<std::mutex> lock(pool_mutex_);

    if (connected_.load()) {
        std::cerr << "[WARN] ZMQPoolManager: Already connected to " << endpoint_
                  << std::endl;
        return true;
    }

    endpoint_ = endpoint;

    // Connect all sockets
    for (size_t i = 0; i < sockets_.size(); ++i) {
        if (zmq_connect(sockets_[i], endpoint.c_str()) != 0) {
            std::cerr << "[ERROR] ZMQPoolManager: Failed to connect socket " << i
                      << " to " << endpoint << ": " << zmq_strerror(errno)
                      << std::endl;

            // Disconnect already connected sockets
            for (size_t j = 0; j < i; ++j) {
                zmq_disconnect(sockets_[j], endpoint.c_str());
            }
            return false;
        }
    }

    connected_.store(true);
    std::cout << "[INFO] ZMQPoolManager: Connected " << sockets_.size()
              << " sockets to " << endpoint << std::endl;
    return true;
}

bool ZMQPoolManager::bind(const std::string& endpoint) {
    std::lock_guard<std::mutex> lock(pool_mutex_);

    if (connected_.load()) {
        std::cerr << "[WARN] ZMQPoolManager: Already connected/bound to " << endpoint_
                  << std::endl;
        return true;
    }

    endpoint_ = endpoint;

    // Bind all sockets
    for (size_t i = 0; i < sockets_.size(); ++i) {
        if (zmq_bind(sockets_[i], endpoint.c_str()) != 0) {
            std::cerr << "[ERROR] ZMQPoolManager: Failed to bind socket " << i
                      << " to " << endpoint << ": " << zmq_strerror(errno)
                      << std::endl;

            // Unbind already bound sockets
            for (size_t j = 0; j < i; ++j) {
                zmq_unbind(sockets_[j], endpoint.c_str());
            }
            return false;
        }
    }

    connected_.store(true);
    std::cout << "[INFO] ZMQPoolManager: Bound " << sockets_.size()
              << " sockets to " << endpoint << std::endl;
    return true;
}

void* ZMQPoolManager::get_socket() {
    if (!connected_.load() || sockets_.empty()) {
        return nullptr;
    }

    // Lock-free round-robin selection
    // Using memory_order_relaxed for performance (ordering not critical here)
    size_t idx = current_socket_.fetch_add(1, std::memory_order_relaxed) % sockets_.size();
    return sockets_[idx];
}

bool ZMQPoolManager::send_message(const void* data, size_t size) {
    if (!connected_.load() || sockets_.empty()) {
        std::cerr << "[ERROR] ZMQPoolManager: Not connected or no sockets" << std::endl;
        return false;
    }

    size_t idx = current_socket_.fetch_add(1, std::memory_order_relaxed) % sockets_.size();

    // 🔍 DEBUG: Log antes del lock
    std::cout << "[DEBUG] Thread " << std::this_thread::get_id()
              << " attempting to acquire mutex[" << idx << "]" << std::endl;

    std::lock_guard<std::mutex> lock(*socket_mutexes_[idx]);

    // 🔍 DEBUG: Log después del lock
    std::cout << "[DEBUG] Thread " << std::this_thread::get_id()
              << " acquired mutex[" << idx << "], sending " << size << " bytes" << std::endl;

    void* socket = sockets_[idx];

    zmq_msg_t message;
    if (zmq_msg_init_size(&message, size) != 0) {
        std::cerr << "[ERROR] zmq_msg_init_size failed: " << zmq_strerror(errno) << std::endl;
        return false;
    }

    memcpy(zmq_msg_data(&message), data, size);

    int rc = zmq_msg_send(&message, socket, ZMQ_DONTWAIT);

    // 🔍 DEBUG: Log resultado
    std::cout << "[DEBUG] Thread " << std::this_thread::get_id()
              << " zmq_msg_send returned: " << rc << std::endl;

    if (rc == -1) {
        zmq_msg_close(&message);
        if (errno != EAGAIN) {
            std::cerr << "[ERROR] zmq_msg_send failed: " << zmq_strerror(errno) << std::endl;
        }
        return false;
    }

    return true;
}

void ZMQPoolManager::shutdown() {
    std::lock_guard<std::mutex> lock(pool_mutex_);

    if (!context_) {
        return;  // Already shutdown
    }

    std::cout << "[INFO] ZMQPoolManager: Shutting down..." << std::endl;

    connected_.store(false);

    // Close all sockets
    for (size_t i = 0; i < sockets_.size(); ++i) {
        if (sockets_[i]) {
            zmq_close(sockets_[i]);
            sockets_[i] = nullptr;
        }
    }
    sockets_.clear();
    socket_mutexes_.clear();

    // Destroy context
    zmq_ctx_destroy(context_);
    context_ = nullptr;

    std::cout << "[INFO] ZMQPoolManager: Shutdown complete" << std::endl;
}

size_t ZMQPoolManager::get_pool_size() const {
    return pool_size_;
}

bool ZMQPoolManager::is_connected() const {
    return connected_.load();
}

} // namespace sniffer