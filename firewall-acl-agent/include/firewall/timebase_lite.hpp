// [TIMEBASE-D295] Lecturas minimas del contrato temporal v1 para el firewall: boot_id y CLOCK_MONOTONIC.
// Duplica dos funciones de sniffer/include/timebase.hpp (otro componente): DEBT-TIMEBASE-COMMON-001
// (unificar ambas en common/).
#pragma once

#include <cstdint>
#include <fstream>
#include <iostream>
#include <string>
#include <time.h>

namespace mldefender::firewall::timebase_lite {

// /proc/sys/kernel/random/boot_id (36 caracteres); vacio si no se puede leer.
inline std::string read_boot_id() {
    std::ifstream f("/proc/sys/kernel/random/boot_id");
    std::string s;
    if (f) std::getline(f, s);
    while (!s.empty() && (s.back() == '\n' || s.back() == '\r' || s.back() == ' ')) s.pop_back();
    return s;
}

inline uint64_t mono_now_ns() noexcept {
    timespec t{};
    clock_gettime(CLOCK_MONOTONIC, &t);
    return static_cast<uint64_t>(t.tv_sec) * 1000000000ULL + static_cast<uint64_t>(t.tv_nsec);
}

}  // namespace mldefender::firewall::timebase_lite
