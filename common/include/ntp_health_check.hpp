#pragma once
// ADR-046 P0 — NTP health gate
// Bloquea arranque del correlation-engine si offset NTP > threshold.
//
// Justificación: community_id como primary key (ADR-048 F2) es inútil
// sin timestamps sincronizados. Sin este gate, los Parquet de
// Suricata/Zeek/Wazuh no tienen join key válida entre sí.
//
// Dependencias: solo chronyc (chrony debe estar instalado en el sistema).
// Sin dependencias C++ externas — linkea limpio desde cualquier componente.

#include <stdexcept>

namespace argus {

class NtpHealthCheck {
public:
    // Mide el offset NTP actual via chronyc tracking.
    // Retorna offset en segundos (siempre >= 0.0).
    // Lanza std::runtime_error si chronyc no está disponible
    // o si el campo "System time" no aparece en la salida
    // (chrony no sincronizado, sin fuente NTP activa).
    static double measure_offset_seconds();

    // Retorna true si el sistema está sincronizado y dentro del threshold.
    // No lanza — absorbe excepciones y retorna false.
    static bool is_synchronized(double threshold_seconds = 1.0) noexcept;
};

} // namespace argus
