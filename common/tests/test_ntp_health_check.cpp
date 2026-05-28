// Tests NtpHealthCheck — ADR-046 P0 (DAY 167)
// NTP-1: offset nominal en VM con chrony activo → no lanza, offset < 1s
// NTP-2: threshold=0.0 → siempre false (cualquier offset > 0 la falla)
// NTP-3: threshold=1.0 nominal → true en VM sincronizada

#include <cassert>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include "../include/ntp_health_check.hpp"

int main() {
    int passed = 0;
    int failed = 0;

    // ── NTP-1: measure_offset_seconds no lanza en entorno normal ─────────
    {
        bool ok = false;
        double offset = 0.0;
        try {
            offset = argus::NtpHealthCheck::measure_offset_seconds();
            ok = true;
        } catch (const std::exception& e) {
            std::cerr << "[NTP-1] FAIL: exception: " << e.what() << "\n";
        }

        if (ok && offset < 1.0) {
            std::cout << "[NTP-1] PASS — offset=" << offset << "s\n";
            ++passed;
        } else if (ok) {
            // Offset alto — la VM tiene problemas NTP reales
            std::cerr << "[NTP-1] FAIL — offset=" << offset
                      << "s >= 1.0s (VM sin sync NTP)\n";
            ++failed;
        } else {
            ++failed;
        }
    }

    // ── NTP-2: threshold=0.0 → is_synchronized siempre false ─────────────
    // No necesita mock: cualquier offset real > 0.0 falla el threshold.
    // Cubre el caso de arranque abortado correctamente.
    {
        bool result = argus::NtpHealthCheck::is_synchronized(0.0);
        if (!result) {
            std::cout << "[NTP-2] PASS — threshold=0.0 correctamente rechazado\n";
            ++passed;
        } else {
            std::cerr << "[NTP-2] FAIL — offset exactamente 0.0 (imposible en práctica)\n";
            ++failed;
        }
    }

    // ── NTP-3: threshold=1.0 nominal → true en VM sincronizada ───────────
    {
        bool result = argus::NtpHealthCheck::is_synchronized(1.0);
        if (result) {
            std::cout << "[NTP-3] PASS — is_synchronized(1.0)=true\n";
            ++passed;
        } else {
            std::cerr << "[NTP-3] FAIL — VM no sincronizada o chrony no disponible\n";
            ++failed;
        }
    }

    std::cout << "\nResultado: " << passed << " passed, "
              << failed << " failed\n";
    return (failed == 0) ? 0 : 1;
}
