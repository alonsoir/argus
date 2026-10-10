// Cabeza DDoS v2 FACTORIZADA (DAY293, bloque 1 en docs/ml-heads/bloque1_day293.md).
// Etapa 1: victim_rate_ratio >= K (K global, en el JSON del ml-detector). Etapa 2: RandomForest sobre los 6 rasgos de flujo
// del contrato v2 (ddos_embedded), generado en ddos_v2_forest_inline.hpp. Rasgos CRUDOS, sin escalado.
// Paridad con sklearn: rasgo float promovido a double frente a umbral double; p = suma en orden de árbol / kNumTrees;
// clase 1 si p1 > p0 (empate -> 0). Si la etapa 1 no pasa: p0 = p1 = 0 y clase 0.
#pragma once

#include <cstddef>
#include <cstdint>

#include "ml_defender/ddos_v2_forest_inline.hpp"

namespace ml_defender::ddos_v2 {

struct Input {
    float syn_ack_ratio;
    float mean_packet_size;
    float reflection_signature;
    float packet_size_entropy;
    float flow_packet_count;
    float flow_completion_rate;
    float victim_rate_ratio;
};

struct Result {
    bool stage1 = false;
    double p0 = 0.0;
    double p1 = 0.0;
    int clase = 0;
};

inline Result evaluate(const Input& in, double k) noexcept {
    Result r;
    r.stage1 = static_cast<double>(in.victim_rate_ratio) >= k;
    if (!r.stage1) {
        return r;
    }
    const float x[kNumFeatures] = {in.syn_ack_ratio, in.mean_packet_size, in.reflection_signature,
                                   in.packet_size_entropy, in.flow_packet_count, in.flow_completion_rate};
    double s0 = 0.0;
    double s1 = 0.0;
    for (std::size_t t = 0; t < kNumTrees; ++t) {
        const Node* tree = kTrees[t];
        int32_t i = 0;
        while (tree[i].feature >= 0) {
            i = (static_cast<double>(x[tree[i].feature]) <= tree[i].threshold) ? tree[i].left : tree[i].right;
        }
        s0 += tree[i].p0;
        s1 += tree[i].p1;
    }
    r.p0 = s0 / static_cast<double>(kNumTrees);
    r.p1 = s1 / static_cast<double>(kNumTrees);
    r.clase = (r.p1 > r.p0) ? 1 : 0;
    return r;
}

}  // namespace ml_defender::ddos_v2
