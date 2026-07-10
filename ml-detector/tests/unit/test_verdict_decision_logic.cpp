// test_verdict_decision_logic.cpp
// aRGus NDR — test de aceptación de la lógica pura de decisión del veredicto L3 (1b-hoist).
// Estilo calcado de test_traffic_head_logic / test_internal_head_logic (DAY 212-213):
// main() propio + macro CHECK (return 1 al primer fallo). NO usa GTest.
//
// LOS 4 TESTS DE CONTORNO del prompt de continuidad, traducidos a la función pura:
//   1. Interno lateral/exfil, L1 BENIGN → NO sella (veredicto cae a NORMAL en process_event).
//      [aquí: l1_gate_open=false → seal=false. El contador lo mide run_internal_head, no esta fn.]
//   2. FRONTERA conservador/agresivo: ese mismo flujo NO produce SUSPICIOUS_INTERNAL.
//      [seal=false ⟹ process_event no cambia threat_category ⟹ queda NORMAL.]
//   3. Interno L1-attack + sospechoso → SELLA SUSPICIOUS_INTERNAL (hot path intacto).
//   4. (Blindaje opción a) el guard is_internal / internal_ran gobierna: si el interno
//      NO corrió, no se sella aunque el gate esté abierto.
//
// Además: casos de tabla de verdad completa (2^3 relevantes) para que ningún cambio
// futuro en decide_l3_verdict pase en verde por accidente.

#include "ml_defender/verdict_decision_logic.hpp"
#include <cstdio>

static int g_failures = 0;
#define CHECK(cond) do { \
    if (!(cond)) { \
        std::printf("  ❌ FAIL L%d: %s\n", __LINE__, #cond); \
        ++g_failures; \
    } \
} while (0)

using ml_defender::L3VerdictInputs;
using ml_defender::decide_l3_verdict;

int main() {
    std::printf("== test_verdict_decision_logic (1b-hoist) ==\n");

    // ---- CONTORNO 1 + 2: interno sospechoso pero L1 BENIGN → NO sella ----
    // Flujo interno lateral/exfil que L1 marcó benigno. Las cabezas corrieron arriba
    // (traffic_is_internal, internal_ran, internal_is_suspicious todos true), PERO el
    // gate L1 está cerrado. Conservador: NO se sella. Veredicto congelado en NORMAL.
    {
        L3VerdictInputs in{
            .l1_gate_open           = false,  // L1 dijo BENIGN
            .traffic_is_internal    = true,
            .internal_ran           = true,
            .internal_is_suspicious = true,
        };
        auto d = decide_l3_verdict(in);
        CHECK(d.seal_suspicious_internal == false);  // FRONTERA: no sella fuera del gate
        CHECK(!d);                                    // operator bool coherente
    }

    // ---- CONTORNO 3: interno L1-attack + sospechoso → SELLA (hot path) ----
    {
        L3VerdictInputs in{
            .l1_gate_open           = true,
            .traffic_is_internal    = true,
            .internal_ran           = true,
            .internal_is_suspicious = true,
        };
        auto d = decide_l3_verdict(in);
        CHECK(d.seal_suspicious_internal == true);
        CHECK(bool(d) == true);
    }

    // ---- CONTORNO 4: gate abierto pero interno NO corrió → NO sella ----
    // (blinda opción a: si el interno no opinó, no hay sellado que colgar de la nada)
    {
        L3VerdictInputs in{
            .l1_gate_open           = true,
            .traffic_is_internal    = true,
            .internal_ran           = false,  // run_internal_head devolvió nullopt
            .internal_is_suspicious = false,  // irrelevante si no corrió
        };
        auto d = decide_l3_verdict(in);
        CHECK(d.seal_suspicious_internal == false);
    }

    // ---- gate abierto, interno corrió pero BENIGN → NO sella ----
    {
        L3VerdictInputs in{
            .l1_gate_open           = true,
            .traffic_is_internal    = true,
            .internal_ran           = true,
            .internal_is_suspicious = false,  // interno dijo benigno
        };
        auto d = decide_l3_verdict(in);
        CHECK(d.seal_suspicious_internal == false);
    }

    // ---- L1-attack pero traffic NO es interno → interno ni corrió → NO sella ----
    // (en process_event, traffic_is_internal=false ⟹ internal_ran=false por el guard.
    //  Reproducimos esa combinación coherente.)
    {
        L3VerdictInputs in{
            .l1_gate_open           = true,
            .traffic_is_internal    = false,
            .internal_ran           = false,
            .internal_is_suspicious = false,
        };
        auto d = decide_l3_verdict(in);
        CHECK(d.seal_suspicious_internal == false);
    }

    // ---- TABLA DE VERDAD: seal ⟺ (gate ∧ ran ∧ susp). Nada más lo activa. ----
    // Recorre las 8 combinaciones de (gate, ran, susp); traffic_is_internal no entra
    // en la decisión (es un guard aguas arriba), lo fijamos coherente con ran.
    for (int g = 0; g < 2; ++g)
    for (int r = 0; r < 2; ++r)
    for (int s = 0; s < 2; ++s) {
        L3VerdictInputs in{
            .l1_gate_open           = (g != 0),
            .traffic_is_internal    = (r != 0),   // coherente: si corrió, era interno
            .internal_ran           = (r != 0),
            .internal_is_suspicious = (s != 0),
        };
        bool expected = (g != 0) && (r != 0) && (s != 0);
        CHECK(decide_l3_verdict(in).seal_suspicious_internal == expected);
    }

    if (g_failures == 0) {
        std::printf("  ✅ ALL CHECKS PASSED\n");
        return 0;
    }
    std::printf("  💥 %d CHECK(s) FAILED\n", g_failures);
    return 1;
}