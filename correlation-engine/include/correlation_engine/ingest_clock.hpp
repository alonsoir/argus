// ingest_clock.hpp — reloj de INGESTA (first_seen) para ADR-057 Fase 0.
// aRGus NDR. Authors: Alonso Isidoro Roman + Claude (Anthropic).
//
// Wall-clock epoch-ns (system_clock). Es el EJE DE INGESTA -- provenance, NO
// reproducibilidad -- deliberadamente distinto del reloj del sensor (bpf_ktime)
// que envenena event_id. Por eso aqui SI vale el reloj de pared.
// La inyeccion de reloj para reproducibilidad vive en el ADR de clock-injection,
// no aqui: build_cypher recibe now_ns por parametro y se testea con valor fijo.
#pragma once
#include <chrono>
#include <cstdint>
namespace argus::correlation {
inline uint64_t ingest_now_ns() {
    return static_cast<uint64_t>(
        std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::system_clock::now().time_since_epoch()).count());
}
}  // namespace argus::correlation
