// canonical_double.hpp — canonicalización IEEE 754 de doubles (ADR-058 §3.1).
// aRGus NDR. Punto único (DAY 207 — corrige ADR-058 v3 fila 16a: el punto único
// vive en parse_and_verify, no en el converter, porque es el confluente real de
// Camino 0 y Flujo A+B — ambos llaman parse_and_verify, no al revés).
//
// NaN -> quiet NaN canónico 0x7ff8000000000000 ; -0.0 -> +0.0. Sin esto, dos
// bit patterns válidos de IEEE 754 para el "mismo" valor lógico rompen
// cualquier comparación bit-exacta aguas abajo (Kuzu, Parquet).
#pragma once
#include <bit>
#include <cmath>
#include <cstdint>

namespace argus::correlation {

    inline double canonicalize_double(double v) {
        if (std::isnan(v)) {
            return std::bit_cast<double>(std::uint64_t{0x7ff8000000000000ULL});
        }
        if (v == 0.0) {  // cubre -0.0 == 0.0 en IEEE 754
            return 0.0;  // fuerza +0.0
        }
        return v;
    }

}  // namespace argus::correlation