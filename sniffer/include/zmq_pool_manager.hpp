#pragma once

#include <vector>
#include <string>
#include <mutex>
#include <atomic>
#include <memory>

namespace sniffer {

/**
 * @brief ZMQ Pool Manager for high-performance message sending
 *
 * Manages a pool of ZeroMQ sockets for load balancing and better throughput
 * when sending large volumes of network security events.
 *
 * THREAD-SAFETY:
 * - Each socket has its own mutex for thread-safe operations
 * - Lock-free round-robin socket selection using atomic counter
 * - Safe for concurrent send_message() calls from multiple threads
 * - Pool size should match number of sender threads for optimal performance
 */
class ZMQPoolManager {
public:
    /**
     * @brief Construct ZMQ pool manager
     * @param pool_size Number of sockets in the pool (should match zmq_sender_threads)
     * @throws std::runtime_error if context or socket creation fails
     */
    explicit ZMQPoolManager(int pool_size = 4);

    /**
     * @brief Destructor - cleanup resources
     */
    ~ZMQPoolManager();

    // Non-copyable (ZMQ sockets cannot be copied)
    ZMQPoolManager(const ZMQPoolManager&) = delete;
    ZMQPoolManager& operator=(const ZMQPoolManager&) = delete;

    // Move operations (default is fine)
    ZMQPoolManager(ZMQPoolManager&&) noexcept = default;
    ZMQPoolManager& operator=(ZMQPoolManager&&) noexcept = default;

    /**
     * @brief Connect all sockets to endpoint
     * @param endpoint ZMQ endpoint (e.g., "tcp://192.168.56.20:5571")
     * @return true if all sockets connected successfully
     */
    bool connect(const std::string& endpoint);

    /**
     * @brief Bind all sockets to endpoint (server mode)
     * @param endpoint ZMQ endpoint to bind (e.g., "tcp://0.0.0.0:5571")
     * @return true if all sockets bound successfully
     */
    bool bind(const std::string& endpoint);

    /**
     * @brief Get next available socket from pool (round-robin)
     * @deprecated Use send_message() directly instead
     * @return Socket pointer or nullptr if not connected
     * @note This method is kept for backward compatibility but should not be used
     *       directly. Use send_message() which handles thread-safety internally.
     */
    void* get_socket();

    /**
     * @brief Send message using pool (non-blocking, thread-safe)
     * @param data Message data
     * @param size Message size in bytes
     * @return true if message sent successfully
     *
     * THREAD-SAFETY: Safe to call from multiple threads concurrently.
     * Uses per-socket mutex to ensure only one thread uses each socket at a time.
     * Lock-free round-robin ensures optimal distribution across sockets.
     */
    bool send_message(const void* data, size_t size);

    /**
     * @brief Shutdown pool and cleanup all resources
     *
     * Closes all sockets and destroys ZMQ context.
     * Safe to call multiple times.
     */
    void shutdown();

    /**
     * @brief Get pool size
     * @return Number of sockets in pool
     */
    size_t get_pool_size() const;

    /**
     * @brief Check if pool is connected
     * @return true if connected
     */
    bool is_connected() const;

private:
    void* context_;                                        ///< ZMQ context
    std::vector<void*> sockets_;                           ///< Socket pool
    std::vector<std::unique_ptr<std::mutex>> socket_mutexes_;  ///< Per-socket mutexes (unique_ptr because mutex is non-copyable)
    std::string endpoint_;                                 ///< Connection endpoint
    int pool_size_;                                        ///< Pool size
    std::atomic<size_t> current_socket_;                   ///< Lock-free round-robin counter
    std::mutex pool_mutex_;                                ///< Mutex for pool management operations
    std::atomic<bool> connected_{false};                   ///< Connection status
};

} // namespace sniffer