// ml-detector/tests/unit/test_zmq_memory_overflow.cpp
//
// ACCEPTANCE TEST — DEBT-INTEGER-OVERFLOW-TEST-001 (ADR-037 F17)
// RED→GREEN: demuestra que el código antiguo overflowea y el nuevo no.
// Consejo DAY 124 (7/7): Opción A + C.

#include <gtest/gtest.h>
#include <climits>
#include <cstdint>
#include "memory_utils.hpp"

using namespace ml_detector;

// ─── RED ────────────────────────────────────────────────────────────────────
// Código ANTIGUO: multiplicación long*long desborda con valores extremos.

TEST(ZmqMemoryOverflow, OldCodeOverflowsWithLargePages) {
    long pages = LONG_MAX / 4096 + 1;
    long page_size = 4096;

    volatile long old_product = pages * page_size; // overflow intencional
    double old_result = static_cast<double>(old_product) / (1024.0 * 1024.0);

    EXPECT_TRUE(old_result < 0.0 || old_result > 1e15)
        << "OLD CODE: expected overflow evidence, got: " << old_result;
}

// ─── GREEN ───────────────────────────────────────────────────────────────────
// Código NUEVO: cast a int64_t antes de multiplicar → resultado correcto.

TEST(ZmqMemoryOverflow, NewCodeHandlesExtremeValues) {
    long pages = LONG_MAX / 4096;
    long page_size = 4096;

    double result = compute_memory_mb(pages, page_size);

    EXPECT_GT(result, 0.0)   << "Result must be positive";
    EXPECT_LT(result, 1e13)  << "Result must be bounded (< 10 PB)";
}

// ─── PROPERTY: nunca negativo ────────────────────────────────────────────────

TEST(ZmqMemoryOverflow, PropertyNeverNegative) {
    const long page_sizes[] = {4096, 8192, 16384, 65536};
    const long page_values[] = {
        0, 1, 1000, 100000,
        LONG_MAX / 65536,
        LONG_MAX / 16384,
        LONG_MAX / 8192,
        LONG_MAX / 4096
    };

    for (long page_size : page_sizes) {
        for (long pages : page_values) {
            double result = compute_memory_mb(pages, page_size);
            EXPECT_GE(result, 0.0)
                << "Negative result for pages=" << pages
                << " page_size=" << page_size;
            // EXPECT_LE(MAX_REALISTIC_MEMORY_MB) no aplica aquí:
            // este loop usa valores extremos (stress de overflow), no valores realistas.
            // El bound realista lo verifica RealisticBounds.
        }
    }
}

// ─── PROPERTY: monotonicidad ─────────────────────────────────────────────────

TEST(ZmqMemoryOverflow, PropertyMonotonicallyIncreasing) {
    long page_size = 4096;
    double prev_result = compute_memory_mb(0, page_size);

    for (long pages : {1L, 1000L, 1000000L, 1000000000L}) {
        double result = compute_memory_mb(pages, page_size);
        EXPECT_GE(result, prev_result)
            << "Non-monotonic at pages=" << pages;
        prev_result = result;
    }
}


// ─── BOUNDS: 1 TB realista ───────────────────────────────────────────────────

TEST(ZmqMemoryOverflow, RealisticBounds) {
    // 1 TB de RAM = 256M páginas de 4KB
    const long max_pages_realistic = (1024LL * 1024 * 1024 * 1024) / 4096;
    double result = compute_memory_mb(max_pages_realistic, 4096);
    EXPECT_NEAR(result, 1024.0 * 1024.0, 1.0); // 1 TB en MB
    EXPECT_LE(result, MAX_REALISTIC_MEMORY_MB);
}

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    std::cout << "\n";
    std::cout << "═══════════════════════════════════════════════════════\n";
    std::cout << "  DEBT-INTEGER-OVERFLOW-TEST-001 — F17 RED→GREEN gate  \n";
    std::cout << "  A: unit sintético · C: property loop sin deps        \n";
    std::cout << "═══════════════════════════════════════════════════════\n\n";
    return RUN_ALL_TESTS();
}
