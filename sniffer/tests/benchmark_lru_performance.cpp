// Day 44 - LRU Performance Benchmark
// Tests hypothesis: list::remove() is O(n) and degrades with flow count

#include "flow/sharded_flow_manager.hpp"
#include "main.h"
#include <iostream>
#include <chrono>
#include <random>
#include <vector>
#include <iomanip>
#include <cstring>

struct BenchmarkResult {
    size_t num_flows;
    size_t num_updates;
    double total_time_ms;
    double time_per_update_us;
    bool meets_target;
};

BenchmarkResult run_lru_benchmark(size_t num_flows, size_t num_updates) {
    auto& manager = sniffer::flow::ShardedFlowManager::instance();
    sniffer::flow::ShardedFlowManager::Config config;
    config.shard_count = 4;
    config.max_flows_per_shard = num_flows * 2;
    
    manager.initialize(config);
    
    std::vector<sniffer::FlowKey> keys;
    keys.reserve(num_flows);
    
    std::cout << "  Creando " << num_flows << " flows iniciales..." << std::flush;
    
    for (size_t i = 0; i < num_flows; ++i) {
        sniffer::FlowKey key;
        key.src_ip = static_cast<uint32_t>(0x0a000001 + i);
        key.dst_ip = static_cast<uint32_t>(0x0a000001 + i + 1000000);
        key.src_port = static_cast<uint16_t>(50000 + (i % 1000));
        key.dst_port = static_cast<uint16_t>(80 + (i % 100));
        key.protocol = 6;
        
        sniffer::SimpleEvent event;
        memset(&event, 0, sizeof(event));
        event.src_ip = key.src_ip;
        event.dst_ip = key.dst_ip;
        event.src_port = key.src_port;
        event.dst_port = key.dst_port;
        event.protocol = key.protocol;
        event.packet_len = 64;
        event.timestamp = 1000000000ULL;
        
        manager.add_packet(key, event);
        keys.push_back(key);
    }
    
    std::cout << " OK" << std::endl;
    
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<size_t> dist(0, num_flows - 1);
    
    std::cout << "  Ejecutando " << num_updates << " updates aleatorios..." << std::flush;
    
    auto start = std::chrono::high_resolution_clock::now();
    
    for (size_t i = 0; i < num_updates; ++i) {
        size_t idx = dist(gen);
        sniffer::FlowKey key = keys[idx];
        
        sniffer::SimpleEvent event;
        memset(&event, 0, sizeof(event));
        event.src_ip = key.src_ip;
        event.dst_ip = key.dst_ip;
        event.src_port = key.src_port;
        event.dst_port = key.dst_port;
        event.protocol = key.protocol;
        event.packet_len = 64;
        event.timestamp = 1000000000ULL + i;
        
        manager.add_packet(key, event);  // ← Aquí está el remove() O(n)
    }
    
    auto end = std::chrono::high_resolution_clock::now();
    
    std::cout << " OK" << std::endl;
    
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
    double total_time_ms = duration.count() / 1000.0;
    double time_per_update_us = static_cast<double>(duration.count()) / num_updates;
    
    bool meets_target = (time_per_update_us < 10000.0);
    
    manager.cleanup_all();
    
    return BenchmarkResult{
        .num_flows = num_flows,
        .num_updates = num_updates,
        .total_time_ms = total_time_ms,
        .time_per_update_us = time_per_update_us,
        .meets_target = meets_target
    };
}

void run_benchmark_suite() {
    std::cout << "🧪 Test 2: LRU Performance Benchmark" << std::endl;
    std::cout << "Testing hypothesis: list::remove() is O(n)" << std::endl;
    std::cout << std::endl;
    
    std::vector<std::pair<size_t, size_t>> scenarios = {
        {100, 1000},
        {1000, 1000},
        {5000, 1000},
        {10000, 1000},
        {20000, 500}
    };
    
    std::cout << "┌─────────┬──────────┬──────────────┬─────────────────┬────────┐" << std::endl;
    std::cout << "│  Flows  │ Updates  │  Total (ms)  │  Per Update(μs) │ Status │" << std::endl;
    std::cout << "├─────────┼──────────┼──────────────┼─────────────────┼────────┤" << std::endl;
    
    bool all_pass = true;
    
    for (const auto& [flows, updates] : scenarios) {
        std::cout << "│ " << std::setw(7) << flows << " │ ";
        std::cout << std::setw(8) << updates << " │ ";
        
        auto result = run_lru_benchmark(flows, updates);
        
        std::cout << std::setw(12) << std::fixed << std::setprecision(2) 
                  << result.total_time_ms << " │ ";
        std::cout << std::setw(15) << std::fixed << std::setprecision(2) 
                  << result.time_per_update_us << " │ ";
        std::cout << (result.meets_target ? "  ✅   " : "  ❌   ") << " │" << std::endl;
        
        if (!result.meets_target) {
            all_pass = false;
        }
    }
    
    std::cout << "└─────────┴──────────┴──────────────┴─────────────────┴────────┘" << std::endl;
    std::cout << std::endl;
    std::cout << "Target: < 10,000 μs/update (10ms)" << std::endl;
    std::cout << std::endl;
    
    if (all_pass) {
        std::cout << "✅ PASS: Performance acceptable" << std::endl;
        std::cout << "Conclusion: O(n) impact negligible OR already optimized" << std::endl;
    } else {
        std::cout << "❌ FAIL: Performance degrades with flow count" << std::endl;
        std::cout << "Conclusion: O(n) remove() is bottleneck - needs O(1) fix" << std::endl;
    }
}

int main() {
    run_benchmark_suite();
    return 0;
}
