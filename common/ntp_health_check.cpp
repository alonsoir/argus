// ADR-046 P0 — NTP health gate implementation
// DAY 167 — DEBT-ARGUSPP-NTP-001

#include "include/ntp_health_check.hpp"
#include <cstdio>
#include <cmath>
#include <stdexcept>

namespace argus {

double NtpHealthCheck::measure_offset_seconds() {
    FILE* pipe = popen("chronyc tracking 2>/dev/null", "r");
    if (!pipe) {
        throw std::runtime_error(
            "popen chronyc failed — chrony no instalado o no accesible");
    }

    char line[512];
    double offset = 0.0;
    bool found = false;

    while (fgets(line, sizeof(line), pipe)) {
        // Formato esperado:
        // "System time     :    0.000123456 seconds fast of NTP time"
        // "System time     :    0.000123456 seconds slow of NTP time"
        double val = 0.0;
        if (sscanf(line, " System time : %lf", &val) == 1) {
            offset = std::abs(val);
            found = true;
            break;
        }
    }
    pclose(pipe);

    if (!found) {
        throw std::runtime_error(
            "chronyc tracking: campo 'System time' no encontrado — "
            "chrony sin fuente NTP activa o no sincronizado todavia");
    }

    return offset;
}

bool NtpHealthCheck::is_synchronized(double threshold_seconds) noexcept {
    try {
        return measure_offset_seconds() <= threshold_seconds;
    } catch (...) {
        return false;
    }
}

} // namespace argus
