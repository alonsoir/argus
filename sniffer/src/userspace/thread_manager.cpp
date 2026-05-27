#include "thread_manager.hpp"
#include "ring_consumer.hpp"
#include <iomanip>
#include <iostream>
#include <sched.h>
#include <sys/resource.h>
#include <unistd.h>
#include <cstring>
// sniffer/src/userspace/thread_manager.cpp
#ifdef __linux__
#include <sys/syscall.h>
#include <linux/sched.h>
#endif

namespace sniffer {

// CpuAffinityManager implementation
CpuAffinityManager::CpuAffinityManager(const ThreadingConfig& config)
    : enabled_(config.cpu_affinity.enabled) {

    if (enabled_) {
        cpu_assignments_[ThreadType::RING_CONSUMER] = config.cpu_affinity.ring_consumers;
        cpu_assignments_[ThreadType::FEATURE_PROCESSOR] = config.cpu_affinity.processors;
        cpu_assignments_[ThreadType::ZMQ_SENDER] = config.cpu_affinity.zmq_senders;
        cpu_assignments_[ThreadType::STATISTICS_COLLECTOR] = config.cpu_affinity.statistics;

        std::cout << "[INFO] CPU affinity enabled" << std::endl;
        for (const auto& [type, cpus] : cpu_assignments_) {
            std::cout << "[INFO] Thread type " << static_cast<int>(type) << " -> CPUs: ";
            for (size_t i = 0; i < cpus.size(); ++i) {
                std::cout << cpus[i];
                if (i < cpus.size() - 1) std::cout << ",";
            }
            std::cout << std::endl;
        }
    }
}

bool CpuAffinityManager::set_thread_affinity(std::thread& thread, ThreadType type) {
    return set_thread_affinity(thread.native_handle(), type);
}

bool CpuAffinityManager::set_thread_affinity(std::thread::native_handle_type handle, ThreadType type) {
    if (!enabled_) return true;

    auto it = cpu_assignments_.find(type);
    if (it == cpu_assignments_.end() || it->second.empty()) {
        return true; // No specific assignment
    }

    return set_cpu_affinity(handle, it->second);
}

std::vector<int> CpuAffinityManager::get_cpu_list(ThreadType type) const {
    auto it = cpu_assignments_.find(type);
    if (it != cpu_assignments_.end()) {
        return it->second;
    }
    return {};
}

int CpuAffinityManager::get_cpu_count() {
    return static_cast<int>(std::thread::hardware_concurrency());
}

int CpuAffinityManager::get_numa_node_count() {
#ifdef NUMA_SUPPORT
    if (numa_available() != -1) {
        return numa_max_node() + 1;
    }
#endif
    return 1;
}

bool CpuAffinityManager::set_cpu_affinity(std::thread::native_handle_type handle, const std::vector<int>& cpus) {
#ifdef __linux__
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);

    for (int cpu : cpus) {
        if (cpu >= 0 && cpu < get_cpu_count()) {
            CPU_SET(cpu, &cpuset);
        }
    }

    int result = pthread_setaffinity_np(handle, sizeof(cpu_set_t), &cpuset);
    if (result != 0) {
        std::cerr << "[WARNING] Failed to set CPU affinity: " << strerror(result) << std::endl;
        return false;
    }
    return true;
#else
    // Non-Linux systems - affinity not supported
    return true;
#endif
}

// ThreadPriorityManager implementation
ThreadPriorityManager::ThreadPriorityManager(const ThreadingConfig& config) {
    // Default priorities
    priority_assignments_[ThreadType::RING_CONSUMER] = ThreadPriority::HIGH;
    priority_assignments_[ThreadType::FEATURE_PROCESSOR] = ThreadPriority::NORMAL;
    priority_assignments_[ThreadType::ZMQ_SENDER] = ThreadPriority::NORMAL;
    priority_assignments_[ThreadType::STATISTICS_COLLECTOR] = ThreadPriority::LOW;

    // Override with config
    for (const auto& [type_str, priority_str] : config.thread_priorities) {
        ThreadPriority priority = string_to_priority(priority_str);

        if (type_str == "ring_consumers") {
            priority_assignments_[ThreadType::RING_CONSUMER] = priority;
        } else if (type_str == "processors") {
            priority_assignments_[ThreadType::FEATURE_PROCESSOR] = priority;
        } else if (type_str == "zmq_senders") {
            priority_assignments_[ThreadType::ZMQ_SENDER] = priority;
        }
    }
}

bool ThreadPriorityManager::set_thread_priority(std::thread& thread, ThreadType type) {
    return set_thread_priority(thread.native_handle(), get_priority(type));
}

bool ThreadPriorityManager::set_thread_priority(std::thread::native_handle_type handle, ThreadPriority priority) {
#ifdef __linux__
    int policy = SCHED_OTHER;
    int priority_value = 0;

    switch (priority) {
        case ThreadPriority::LOW:
            policy = SCHED_OTHER;
            priority_value = -10;
            break;
        case ThreadPriority::NORMAL:
            policy = SCHED_OTHER;
            priority_value = 0;
            break;
        case ThreadPriority::HIGH:
            policy = SCHED_OTHER;
            priority_value = -5;
            break;
        case ThreadPriority::REALTIME:
            policy = SCHED_FIFO;
            priority_value = 1;
            break;
    }

    struct sched_param param;
    param.sched_priority = priority_value;

    int result = pthread_setschedparam(handle, policy, &param);
    if (result != 0) {
        std::cerr << "[WARNING] Failed to set thread priority: " << strerror(result) << std::endl;
        return false;
    }
    return true;
#else
    return true;
#endif
}

ThreadPriority ThreadPriorityManager::get_priority(ThreadType type) const {
    auto it = priority_assignments_.find(type);
    if (it != priority_assignments_.end()) {
        return it->second;
    }
    return ThreadPriority::NORMAL;
}

ThreadPriority ThreadPriorityManager::string_to_priority(const std::string& priority_str) const {
    if (priority_str == "low") return ThreadPriority::LOW;
    if (priority_str == "high") return ThreadPriority::HIGH;
    if (priority_str == "realtime") return ThreadPriority::REALTIME;
    return ThreadPriority::NORMAL;
}

// ThreadPool implementation
template<typename WorkDataType>
ThreadPool<WorkDataType>::ThreadPool(int thread_count, ThreadType type,
                                      CpuAffinityManager& affinity_mgr,
                                      ThreadPriorityManager& priority_mgr)
    : thread_count_(thread_count), thread_type_(type),
      affinity_manager_(affinity_mgr), priority_manager_(priority_mgr) {

    thread_stats_.reserve(thread_count);
    for (int i = 0; i < thread_count; ++i) {
        thread_stats_.push_back(std::make_unique<ThreadStats>());
    }
}

template<typename WorkDataType>
ThreadPool<WorkDataType>::~ThreadPool() {
    if (running_) {
        stop();
    }
}

template<typename WorkDataType>
bool ThreadPool<WorkDataType>::start() {
    if (running_) return true;

    should_stop_ = false;
    running_ = true;

    workers_.reserve(thread_count_);

    for (int i = 0; i < thread_count_; ++i) {
        workers_.emplace_back(&ThreadPool::worker_loop, this, i);

        // Set affinity and priority
        affinity_manager_.set_thread_affinity(workers_.back(), thread_type_);
        priority_manager_.set_thread_priority(workers_.back(), thread_type_);

        thread_stats_[i]->start_time = std::chrono::steady_clock::now();
        thread_stats_[i]->active = true;
    }

    std::cout << "[INFO] Thread pool started with " << thread_count_
              << " workers (type: " << static_cast<int>(thread_type_) << ")" << std::endl;
    return true;
}

template<typename WorkDataType>
void ThreadPool<WorkDataType>::stop() {
    if (!running_) return;

    should_stop_ = true;
    work_condition_.notify_all();

    for (auto& worker : workers_) {
        if (worker.joinable()) {
            worker.join();
        }
    }

    // Mark all stats as inactive
    for (auto& stats : thread_stats_) {
        stats->active = false;
    }

    workers_.clear();
    running_ = false;

    std::cout << "[INFO] Thread pool stopped (type: " << static_cast<int>(thread_type_) << ")" << std::endl;
}

template<typename WorkDataType>
std::future<void> ThreadPool<WorkDataType>::submit(WorkFunction task, WorkDataType data) {
    auto work_item = std::make_unique<WorkItem<WorkDataType>>(std::move(task), std::move(data));
    auto future = work_item->completion.get_future();

    {
        std::lock_guard<std::mutex> lock(queue_mutex_);
        work_queue_.push(std::move(work_item));
    }

    work_condition_.notify_one();
    return future;
}

template<typename WorkDataType>
void ThreadPool<WorkDataType>::worker_loop(int worker_id) {
    thread_utils::set_thread_name("worker_" + std::to_string(worker_id));

    while (!should_stop_) {
        std::unique_ptr<WorkItem<WorkDataType>> work_item;

        {
            std::unique_lock<std::mutex> lock(queue_mutex_);
            work_condition_.wait_for(lock, queue_timeout_, [this] {
                return !work_queue_.empty() || should_stop_;
            });

            if (!work_queue_.empty()) {
                work_item = std::move(work_queue_.front());
                work_queue_.pop();
            }
        }

        if (work_item) {
            auto start_time = std::chrono::steady_clock::now();

            try {
                work_item->task(work_item->data);
                work_item->completion.set_value();
                thread_stats_[worker_id]->tasks_processed++;
            } catch (const std::exception& e) {
                work_item->completion.set_exception(std::current_exception());
                thread_stats_[worker_id]->tasks_failed++;
                thread_utils::thread_log(thread_type_, worker_id,
                    "Task failed: " + std::string(e.what()));
            }

            auto end_time = std::chrono::steady_clock::now();
            auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time);
            thread_stats_[worker_id]->total_processing_time_us += duration.count();
        }
    }

    thread_utils::thread_log(thread_type_, worker_id, "Worker thread stopping");
}

template<typename WorkDataType>
std::vector<ThreadStats> ThreadPool<WorkDataType>::get_thread_stats() const {
    std::vector<ThreadStats> stats;
    stats.reserve(thread_stats_.size());

    for (const auto& stat : thread_stats_) {
        ThreadStats copy;
        copy.tasks_processed = stat->tasks_processed.load();
        copy.tasks_failed = stat->tasks_failed.load();
        copy.total_processing_time_us = stat->total_processing_time_us.load();
        copy.cpu_usage_percent = stat->cpu_usage_percent.load();
        copy.start_time = stat->start_time;
        copy.active = stat->active.load();
        stats.push_back(copy);
    }

    return stats;
}

template<typename WorkDataType>
size_t ThreadPool<WorkDataType>::get_queue_size() const {
    std::lock_guard<std::mutex> lock(queue_mutex_);
    return work_queue_.size();
}

// ThreadManager implementation
ThreadManager::ThreadManager(const ThreadingConfig& config)
    : config_(config) {

    affinity_manager_ = std::make_unique<CpuAffinityManager>(config);
    priority_manager_ = std::make_unique<ThreadPriorityManager>(config);
}

ThreadManager::~ThreadManager() {
    if (running_) {
        stop();
    }
}

bool ThreadManager::initialize() {
    if (initialized_) return true;

    if (!validate_configuration()) {
        return false;
    }

    // Create thread pools
    ring_consumer_pool_ = std::make_unique<ThreadPool<SimpleEvent>>(
        config_.ring_consumer_threads, ThreadType::RING_CONSUMER,
        *affinity_manager_, *priority_manager_);

    feature_processor_pool_ = std::make_unique<ThreadPool<SimpleEvent>>(
        config_.feature_processor_threads, ThreadType::FEATURE_PROCESSOR,
        *affinity_manager_, *priority_manager_);

    zmq_sender_pool_ = std::make_unique<ThreadPool<std::vector<uint8_t>>>(
        config_.zmq_sender_threads, ThreadType::ZMQ_SENDER,
        *affinity_manager_, *priority_manager_);

    statistics_pool_ = std::make_unique<ThreadPool<std::string>>(
        config_.statistics_collector_threads, ThreadType::STATISTICS_COLLECTOR,
        *affinity_manager_, *priority_manager_);

    initialized_ = true;
    log_thread_configuration();

    std::cout << "[INFO] ThreadManager initialized with " << config_.total_worker_threads
              << " total threads" << std::endl;
    return true;
}

bool ThreadManager::start() {
    if (!initialized_ && !initialize()) {
        return false;
    }

    if (running_) return true;

    start_time_ = std::chrono::steady_clock::now();

    bool success = true;
    success &= ring_consumer_pool_->start();
    success &= feature_processor_pool_->start();
    success &= zmq_sender_pool_->start();
    success &= statistics_pool_->start();

    if (success) {
        running_ = true;
        std::cout << "[INFO] All thread pools started successfully" << std::endl;
    } else {
        std::cerr << "[ERROR] Failed to start some thread pools" << std::endl;
    }

    return success;
}

void ThreadManager::stop() {
    if (!running_) return;

    std::cout << "[INFO] Stopping all thread pools..." << std::endl;

    if (ring_consumer_pool_) ring_consumer_pool_->stop();
    if (feature_processor_pool_) feature_processor_pool_->stop();
    if (zmq_sender_pool_) zmq_sender_pool_->stop();
    if (statistics_pool_) statistics_pool_->stop();

    running_ = false;
    std::cout << "[INFO] All thread pools stopped" << std::endl;
}

// Get thread pools
ThreadPool<SimpleEvent>* ThreadManager::get_ring_consumer_pool() {
    return ring_consumer_pool_.get();
}

ThreadPool<SimpleEvent>* ThreadManager::get_feature_processor_pool() {
    return feature_processor_pool_.get();
}

ThreadPool<std::vector<uint8_t>>* ThreadManager::get_zmq_sender_pool() {
    return zmq_sender_pool_.get();
}

ThreadPool<std::string>* ThreadManager::get_statistics_pool() {
    return statistics_pool_.get();
}

// Submit work methods
std::future<void> ThreadManager::submit_ring_work(std::function<void(SimpleEvent&)> task, SimpleEvent event) {
    return ring_consumer_pool_->submit(std::move(task), std::move(event));
}

std::future<void> ThreadManager::submit_processing_work(std::function<void(SimpleEvent&)> task, SimpleEvent event) {
    return feature_processor_pool_->submit(std::move(task), std::move(event));
}

std::future<void> ThreadManager::submit_zmq_work(std::function<void(std::vector<uint8_t>&)> task, std::vector<uint8_t> data) {
    return zmq_sender_pool_->submit(std::move(task), std::move(data));
}

std::future<void> ThreadManager::submit_stats_work(std::function<void(std::string&)> task, std::string stats) {
    return statistics_pool_->submit(std::move(task), std::move(stats));
}

ThreadManager::GlobalStats ThreadManager::get_global_stats() const {
    std::lock_guard<std::mutex> lock(stats_mutex_);

    GlobalStats global;
    global.total_threads = config_.total_worker_threads;
    global.active_threads = 0;
    global.total_tasks_processed = 0;
    global.total_tasks_failed = 0;
    global.average_cpu_usage = 0.0;
    global.total_queue_size = 0;

    // Aggregate stats from all pools
    auto aggregate_pool_stats = [&](const auto& pool) {
        if (!pool) return;

        auto stats = pool->get_thread_stats();
        for (const auto& stat : stats) {
            if (stat.active) global.active_threads++;
            global.total_tasks_processed += stat.tasks_processed;
            global.total_tasks_failed += stat.tasks_failed;
            global.average_cpu_usage += stat.cpu_usage_percent;
        }
        global.total_queue_size += pool->get_queue_size();
    };

    aggregate_pool_stats(ring_consumer_pool_);
    aggregate_pool_stats(feature_processor_pool_);
    aggregate_pool_stats(zmq_sender_pool_);
    aggregate_pool_stats(statistics_pool_);

    if (global.total_threads > 0) {
        global.average_cpu_usage /= global.total_threads;
    }

    return global;
}

void ThreadManager::print_stats() const {
    auto stats = get_global_stats();

    std::cout << "\n=== ThreadManager Statistics ===" << std::endl;
    std::cout << "Total threads: " << stats.total_threads << std::endl;
    std::cout << "Active threads: " << stats.active_threads << std::endl;
    std::cout << "Tasks processed: " << stats.total_tasks_processed << std::endl;
    std::cout << "Tasks failed: " << stats.total_tasks_failed << std::endl;
    std::cout << "Average CPU usage: " << std::fixed << std::setprecision(1)
              << stats.average_cpu_usage << "%" << std::endl;
    std::cout << "Total queue size: " << stats.total_queue_size << std::endl;
    std::cout << "===============================" << std::endl;
}

bool ThreadManager::validate_configuration() const {
    if (config_.total_worker_threads <= 0) {
        std::cerr << "[ERROR] Total worker threads must be > 0" << std::endl;
        return false;
    }

    int calculated_total = config_.ring_consumer_threads +
                          config_.feature_processor_threads +
                          config_.zmq_sender_threads +
                          config_.statistics_collector_threads;

    if (calculated_total != config_.total_worker_threads) {
        std::cout << "[WARNING] Thread count mismatch: calculated=" << calculated_total
                  << ", configured=" << config_.total_worker_threads << std::endl;
    }

    int max_cpus = CpuAffinityManager::get_cpu_count();
    if (config_.total_worker_threads > max_cpus * 2) {
        std::cout << "[WARNING] Thread count (" << config_.total_worker_threads
                  << ") exceeds 2x CPU count (" << max_cpus << ")" << std::endl;
    }

    return true;
}

void ThreadManager::log_thread_configuration() const {
    std::cout << "\n=== Thread Configuration ===" << std::endl;
    std::cout << "Ring consumer threads: " << config_.ring_consumer_threads << std::endl;
    std::cout << "Feature processor threads: " << config_.feature_processor_threads << std::endl;
    std::cout << "ZMQ sender threads: " << config_.zmq_sender_threads << std::endl;
    std::cout << "Statistics threads: " << config_.statistics_collector_threads << std::endl;
    std::cout << "Total threads: " << config_.total_worker_threads << std::endl;

    if (affinity_manager_->is_enabled()) {
        std::cout << "CPU affinity: ENABLED" << std::endl;
    } else {
        std::cout << "CPU affinity: DISABLED" << std::endl;
    }

    std::cout << "System CPUs: " << CpuAffinityManager::get_cpu_count() << std::endl;
    std::cout << "NUMA nodes: " << CpuAffinityManager::get_numa_node_count() << std::endl;
    std::cout << "============================" << std::endl;
}

// Static methods
bool ThreadManager::is_numa_available() {
#ifdef NUMA_SUPPORT
    return numa_available() != -1;
#else
    return false;
#endif
}

int ThreadManager::get_optimal_thread_count() {
    int cpu_count = std::thread::hardware_concurrency();

    // For I/O intensive workloads, optimal thread count can be higher than CPU count
    // For eBPF ring buffer processing (CPU intensive), use CPU count
    // For feature processing (mixed), use CPU count + 25%
    // For ZMQ sending (I/O), use CPU count / 2

    return cpu_count > 0 ? cpu_count : 4; // fallback to 4
}

#ifdef NUMA_SUPPORT
// NumaAllocator implementation
bool NumaAllocator::numa_initialized_ = false;

void* NumaAllocator::allocate_on_node(size_t size, int node) {
    if (!initialize_numa()) {
        return malloc(size);
    }

    return numa_alloc_onnode(size, node);
}

void NumaAllocator::deallocate(void* ptr, size_t size) {
    if (!numa_initialized_) {
        free(ptr);
        return;
    }

    numa_free(ptr, size);
}

int NumaAllocator::get_current_node() {
    if (!initialize_numa()) {
        return 0;
    }

    return numa_node_of_cpu(sched_getcpu());
}

int NumaAllocator::get_preferred_node_for_cpu(int cpu) {
    if (!initialize_numa()) {
        return 0;
    }

    return numa_node_of_cpu(cpu);
}

bool NumaAllocator::initialize_numa() {
    if (numa_initialized_) {
        return true;
    }

    if (numa_available() == -1) {
        return false;
    }

    numa_initialized_ = true;
    return true;
}
#endif

// Utility functions
namespace thread_utils {

double get_thread_cpu_usage([[maybe_unused]] std::thread::native_handle_type handle) {
    // This is a simplified implementation - real CPU monitoring would require
    // more complex system calls or /proc parsing
    return 0.0; // Placeholder
}

void set_thread_name(const std::string& name) {
#ifdef __linux__
    pthread_setname_np(pthread_self(), name.substr(0, 15).c_str());
#endif
}

size_t get_optimal_batch_size(ThreadType type, size_t queue_size) {
    switch (type) {
        case ThreadType::RING_CONSUMER:
            // Small batches for low latency
            return std::min(queue_size, size_t(10));
        case ThreadType::FEATURE_PROCESSOR:
            // Medium batches for balance
            return std::min(queue_size, size_t(50));
        case ThreadType::ZMQ_SENDER:
            // Larger batches for throughput
            return std::min(queue_size, size_t(100));
        case ThreadType::STATISTICS_COLLECTOR:
            // Large batches - not latency critical
            return std::min(queue_size, size_t(200));
        default:
            return std::min(queue_size, size_t(10));
    }
}

void thread_log(ThreadType type, int worker_id, const std::string& message) {
    const char* type_names[] = {"RING", "PROC", "ZMQ", "STATS"};
    const char* type_name = type_names[static_cast<int>(type)];

    std::cout << "[" << type_name << "-" << worker_id << "] " << message << std::endl;
}

} // namespace thread_utils

// Explicit template instantiations
template class ThreadPool<SimpleEvent>;
template class ThreadPool<std::vector<uint8_t>>;
template class ThreadPool<std::string>;

} // namespace sniffer