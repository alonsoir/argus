#pragma once
// memory_utils.hpp — Pure memory calculation helpers (ADR-037 F17)
// Header-only, zero external dependencies — testable without zmq/fmt/onnx.
#include <cstdint>

namespace ml_detector {

// Use double arithmetic directly — avoids int64_t overflow for extreme values.
// int64_t cast is insufficient: LONG_MAX/4096 * 8192 still overflows int64_t.
// double has 53-bit mantissa, sufficient for any realistic memory value.
constexpr double MAX_REALISTIC_MEMORY_MB = 1024.0 * 1024.0; // 1 TB en MB

[[nodiscard]] inline double compute_memory_mb(long pages, long page_size) noexcept {
    const double result = (static_cast<double>(pages) * static_cast<double>(page_size))
                          / (1024.0 * 1024.0);
    // noexcept — mejor métrica incorrecta que componente caído
    // En producción: if (result > MAX_REALISTIC_MEMORY_MB || result < 0.0) log_warning(...)
    return result;
}

} // namespace ml_detector
