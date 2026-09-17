// l2_gate.hpp -- DAY271
// Predicado puro de la compuerta level1 -> level2 (cabezas especializadas).
// Extraido a su PROPIA cabecera, SIN dependencias, para testearlo como unidad sin
// arrastrar zmq_handler.hpp (zmq/protobuf/spdlog). Lo incluyen zmq_handler.cpp
// (guard de la linea 549) y test_l2_gate.cpp. `inline` => sin violacion de ODR.
#pragma once
#include <cstdint>

// force_all_heads (flag debug DAY271) abre la compuerta SIEMPRE. En su defecto, la
// regla de produccion intacta: level1 dijo ATTACK (label==1) con confianza >= umbral.
inline bool l2_gate_open(bool force_all_heads, int64_t label_l1,
                         double confidence_l1, double level1_threshold) {
    return force_all_heads || (label_l1 == 1 && confidence_l1 >= level1_threshold);
}