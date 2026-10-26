#pragma once
// sniffer/include/flow_table_params.hpp — [FLOW-TABLE-D308]
// Parametros de la tabla de flujos del sniffer: los DEFECTOS validados (los mismos valores que trae sniffer.json) y
// los rangos, en un solo sitio del codigo. Sin dependencias (ni JSON): lo incluye ShardedFlowManager. El lector del
// JSON esta en flow_table_config.hpp.
#include <cstdint>

namespace argus::flowtable {

struct FlowTableParams {
    uint64_t shards = 16;
    uint64_t max_flows_per_shard = 10000;
    uint64_t idle_timeout_s = 300;
    uint64_t active_timeout_s = 0;  // 0 = sin tope de duracion activa
    uint64_t cleanup_interval_ms = 1000;
    uint64_t log_interval_s = 60;
};

constexpr uint64_t kShardsMin = 1, kShardsMax = 256;
constexpr uint64_t kMaxFlowsMin = 100, kMaxFlowsMax = 10'000'000;
constexpr uint64_t kIdleMin = 1, kIdleMax = 86'400;
constexpr uint64_t kActiveMin = 1, kActiveMax = 604'800;  // ademas de 0 = sin tope
constexpr uint64_t kCleanupMin = 100, kCleanupMax = 60'000;
constexpr uint64_t kLogMin = 1, kLogMax = 3'600;

// Reglas cruzadas: la limpieza pasa mas a menudo que la inactividad que caduca; un tope activo (si lo hay) no es
// menor que la inactividad.
inline bool regla_limpieza_ok(const FlowTableParams& p) { return p.idle_timeout_s * 1000 > p.cleanup_interval_ms; }
inline bool regla_tope_ok(const FlowTableParams& p) {
    return p.active_timeout_s == 0 || p.active_timeout_s >= p.idle_timeout_s;
}

}  // namespace argus::flowtable
