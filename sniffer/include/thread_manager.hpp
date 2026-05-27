#pragma once
// sniffer/src/userspace/thread_manager.hpp
#include <thread>
#include <vector>
#include <memory>
#include <functional>
#include <atomic>
#include <condition_variable>
#include <mutex>
#include <queue>
#include <future>
#include <unordered_map>
#include <string>
#include <iomanip>
#ifdef NUMA_SUPPORT
#include <numa.h>
#endif

#include "config_manager.hpp"


namespace sniffer {

struct SimpleEvent;
// Thread priority levels
enum class ThreadPriority {
    LOW = 0,
    NORMAL = 1,
    HIGH = 2,
    REALTIME = 3
};

// Thread type enumeration
enum class ThreadType {
    RING_CONSUMER,
    FEATURE_PROCESSOR,
    ZMQ_SENDER,
    STATISTICS_COLLECTOR
};

// Thread pool worker state
enum class WorkerState {
    IDLE,
    WORKING,
    STOPPING,
    STOPPED
};

// Work item for thread pool
template<typename T>
struct WorkItem {
    std::function<void(T&)> task;
    T data;
    std::promise<void> completion;

    WorkItem(std::function<void(T&)> t, T d) : task(std::move(t)), data(std::move(d)) {}
};

struct ThreadStats {
        std::atomic<size_t> tasks_processed{0};
        std::atomic<size_t> tasks_queued{0};
        std::atomic<size_t> tasks_failed{0};
        std::atomic<double> cpu_usage_percent{0.0};
        std::atomic<bool> active{true};
        std::atomic<uint64_t> total_processing_time_us{0};
        std::chrono::steady_clock::time_point start_time;

        // Constructor por defecto
        ThreadStats() : start_time(std::chrono::steady_clock::now()) {}

        // Constructor de copia
        ThreadStats(const ThreadStats& other)
            : tasks_processed(other.tasks_processed.load())
            , tasks_queued(other.tasks_queued.load())
            , tasks_failed(other.tasks_failed.load())
            , cpu_usage_percent(other.cpu_usage_percent.load())
            , active(other.active.load())
            , total_processing_time_us(other.total_processing_time_us.load())
            , start_time(other.start_time) {}

        // Operador de asignación
        ThreadStats& operator=(const ThreadStats& other) {
            if (this != &other) {
                tasks_processed.store(other.tasks_processed.load());
                tasks_queued.store(other.tasks_queued.load());
                tasks_failed.store(other.tasks_failed.load());
                cpu_usage_percent.store(other.cpu_usage_percent.load());
                active.store(other.active.load());
                total_processing_time_us.store(other.total_processing_time_us.load());
                start_time = other.start_time;
            }
            return *this;
        }
};

// CPU affinity manager
class CpuAffinityManager {
public:
    explicit CpuAffinityManager(const ThreadingConfig& config);

    // Set CPU affinity for specific thread type
    bool set_thread_affinity(std::thread& thread, ThreadType type);
    bool set_thread_affinity(std::thread::native_handle_type handle, ThreadType type);

    // Get available CPUs for thread type
    std::vector<int> get_cpu_list(ThreadType type) const;

    // Check if affinity is enabled
    bool is_enabled() const { return enabled_; }

    // System information
    static int get_cpu_count();
    static int get_numa_node_count();

private:
    bool enabled_;
    std::unordered_map<ThreadType, std::vector<int>> cpu_assignments_;

    bool set_cpu_affinity(std::thread::native_handle_type handle, const std::vector<int>& cpus);
};

// Thread priority manager
class ThreadPriorityManager {
public:
    explicit ThreadPriorityManager(const ThreadingConfig& config);

    // Set thread priority
    bool set_thread_priority(std::thread& thread, ThreadType type);
    bool set_thread_priority(std::thread::native_handle_type handle, ThreadPriority priority);

    // Get priority for thread type
    ThreadPriority get_priority(ThreadType type) const;

private:
    std::unordered_map<ThreadType, ThreadPriority> priority_assignments_;

    ThreadPriority string_to_priority(const std::string& priority_str) const;
};

// Generic thread pool for different worker types
template<typename WorkDataType>
class ThreadPool {
public:
    using WorkFunction = std::function<void(WorkDataType&)>;

    ThreadPool(int thread_count, ThreadType type,
               CpuAffinityManager& affinity_mgr,
               ThreadPriorityManager& priority_mgr);
    ~ThreadPool();

    // Start the thread pool
    bool start();

    // Stop the thread pool
    void stop();

    // Submit work to the pool
    std::future<void> submit(WorkFunction task, WorkDataType data);

    // Get statistics
    std::vector<ThreadStats> get_thread_stats() const;
    size_t get_queue_size() const;
    bool is_running() const { return running_; }

    // Configuration
    void set_queue_timeout(std::chrono::milliseconds timeout) { queue_timeout_ = timeout; }

private:
    int thread_count_;
    ThreadType thread_type_;
    CpuAffinityManager& affinity_manager_;
    ThreadPriorityManager& priority_manager_;

    std::vector<std::thread> workers_;
    std::vector<std::unique_ptr<ThreadStats>> thread_stats_;

    std::queue<std::unique_ptr<WorkItem<WorkDataType>>> work_queue_;
    mutable std::mutex queue_mutex_;
    std::condition_variable work_condition_;

    std::atomic<bool> running_{false};
    std::atomic<bool> should_stop_{false};
    std::chrono::milliseconds queue_timeout_{100};

    void worker_loop(int worker_id);
};

// Main thread manager class
class ThreadManager {
public:
    explicit ThreadManager(const ThreadingConfig& config);
    ~ThreadManager();

    // Initialize thread pools
    bool initialize();

    // Start all thread pools
    bool start();

    // Stop all thread pools
    void stop();

    // Get thread pools by type
    ThreadPool<SimpleEvent>* get_ring_consumer_pool();
    ThreadPool<SimpleEvent>* get_feature_processor_pool();
    ThreadPool<std::vector<uint8_t>>* get_zmq_sender_pool();
    ThreadPool<std::string>* get_statistics_pool();

    // Submit work to appropriate pool
    std::future<void> submit_ring_work(std::function<void(SimpleEvent&)> task, SimpleEvent event);
    std::future<void> submit_processing_work(std::function<void(SimpleEvent&)> task, SimpleEvent event);
    std::future<void> submit_zmq_work(std::function<void(std::vector<uint8_t>&)> task, std::vector<uint8_t> data);
    std::future<void> submit_stats_work(std::function<void(std::string&)> task, std::string stats);

    // Statistics and monitoring
    struct GlobalStats {
        size_t total_threads;
        size_t active_threads;
        uint64_t total_tasks_processed;
        uint64_t total_tasks_failed;
        double average_cpu_usage;
        size_t total_queue_size;
    };

    GlobalStats get_global_stats() const;
    void print_stats() const;

    // Configuration access
    const ThreadingConfig& get_config() const { return config_; }

    // System information
    static bool is_numa_available();
    static int get_optimal_thread_count();

private:
    ThreadingConfig config_;
    std::unique_ptr<CpuAffinityManager> affinity_manager_;
    std::unique_ptr<ThreadPriorityManager> priority_manager_;

    // Thread pools for different work types
    std::unique_ptr<ThreadPool<SimpleEvent>> ring_consumer_pool_;
    std::unique_ptr<ThreadPool<SimpleEvent>> feature_processor_pool_;
    std::unique_ptr<ThreadPool<std::vector<uint8_t>>> zmq_sender_pool_;
    std::unique_ptr<ThreadPool<std::string>> statistics_pool_;

    std::atomic<bool> initialized_{false};
    std::atomic<bool> running_{false};

    // Performance monitoring
    mutable std::mutex stats_mutex_;
    std::chrono::steady_clock::time_point start_time_;

    bool validate_configuration() const;
    void log_thread_configuration() const;
};

// NUMA-aware memory allocator (if NUMA support is available)
#ifdef NUMA_SUPPORT
class NumaAllocator {
public:
    static void* allocate_on_node(size_t size, int node);
    static void deallocate(void* ptr, size_t size);
    static int get_current_node();
    static int get_preferred_node_for_cpu(int cpu);

private:
    static bool numa_initialized_;
    static bool initialize_numa();
};
#endif

// Utility functions
namespace thread_utils {
    // Get current thread CPU usage
    double get_thread_cpu_usage(std::thread::native_handle_type handle);

    // Set thread name (for debugging)
    void set_thread_name(const std::string& name);

    // Get optimal batch size for threading
    size_t get_optimal_batch_size(ThreadType type, size_t queue_size);

    // Thread-safe logging for thread operations
    void thread_log(ThreadType type, int worker_id, const std::string& message);
}

} // namespace sniffer