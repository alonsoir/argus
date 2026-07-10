// verdict_decision_logic.hpp
// aRGus NDR — ml-detector: lógica PURA de decisión del veredicto multicabeza L3.
// Authors: Alonso Isidoro Roman + Claude (Anthropic)
//
// PROCEDENCIA (DAY 214, 1b-hoist): la ORQUESTACIÓN del veredicto L3 —"¿qué
// threat_category sella el interno, y cuándo cuenta como hueco de cobertura?"—
// se extrae aquí desde process_event, como función pura y testeable, ANTES de
// izar las llamadas fuera del gate L1. Espejo del patrón de 1a/1b-extract
// (build_internal_features / build_traffic_features): entender → extraer a
// función pura + test → sólo entonces mover.
//
// QUÉ CONTIENE (y qué NO):
//   · SÍ: la lógica de orquestación — dado "el traffic dice interno", "el interno
//         dice sospechoso" y el estado de L1, decidir el sellado y el contador.
//   · NO: los umbrales de los detectores. is_internal()/is_suspicious() viven en
//         TrafficDetector::Prediction / InternalDetector::Prediction y son la
//         fuente de verdad de "qué es interno / qué es sospechoso". Esta función
//         recibe esos veredictos YA evaluados (bool), no re-implementa umbrales.
//         (Si esta función volviera a llamar is_suspicious(threshold), duplicaría
//          el umbral en dos sitios — deriva garantizada. Se evita a propósito.)
//
// FRONTERA CONSERVADOR/AGRESIVO (1b-hoist, OPCIÓN (a)):
//   El SELLADO (SUSPICIOUS_INTERNAL) sólo ocurre DENTRO del gate L1-attack. En
//   flujos L1-benigno las cabezas corren (contador puede subir) pero el veredicto
//   se CONGELA en NORMAL. "Correr izado, decidir congelado". Commit 2 (noisy-OR)
//   reemplazará el cuerpo de decide_l3_verdict sin tocar process_event otra vez.
//
// DECISIÓN CONGELADA — asimetría label_l1 / confidence_l1 (DAY 214):
//   El hueco se define como discrepancia de CLASE (label_l1 != 1), NO de confianza.
//   Un flujo (L1=attack, confianza < level1_attack) cae a NORMAL pero NO cuenta como
//   discrepancia — es coherente con "el interno vio un flujo que L1 NO clasificó como
//   ataque de clase". El contador lo evalúa el propio run_internal_head (evaluate_internal,
//   1a); esta función NO recuenta. Alinear con confidence_l1 es trabajo de commit 2.
#pragma once

#include <string_view>

namespace ml_defender {

// Entrada: veredictos YA evaluados por las Prediction (fuente de verdad de umbrales)
// + estado del gate L1. Sin punteros, sin protobuf, sin I/O: sólo booleanos y enteros.
struct L3VerdictInputs {
    bool     l1_gate_open;        // label_l1 == 1 && confidence_l1 >= level1_attack
    bool     traffic_is_internal; // traffic_result && traffic_result->is_internal(level3_web)
    bool     internal_ran;        // run_internal_head devolvió Prediction (no nullopt)
    bool     internal_is_suspicious; // internal_pred->is_suspicious(level3_internal)
};

// Salida: qué sella el orquestador. seal_suspicious_internal == true ⟺ el gate está
// abierto Y el interno corrió Y dio sospechoso. En cualquier otro caso, passthrough:
// el veredicto lo fija el resto de process_event (ATTACK dentro del gate, NORMAL fuera).
struct L3VerdictDecision {
    bool seal_suspicious_internal = false;

    explicit operator bool() const noexcept { return seal_suspicious_internal; }
};

// decide_l3_verdict — PURA. Réplica byte-idéntica de la condición de sellado que
// vivía inline en process_event (línea 837-838 pre-hoist):
//     if (internal_pred && internal_pred->is_suspicious(...)) { sella }
// ...pero AHORA con el sellado restringido al gate L1-attack (1b-hoist): el bloque
// inline vivía dentro del gate, así que "gate abierto" era implícito. Al izar las
// llamadas fuera del gate, "gate abierto" se hace EXPLÍCITO aquí — es lo que congela
// el veredicto en NORMAL para L1-benigno mientras las cabezas ya han corrido arriba.
[[nodiscard]] constexpr L3VerdictDecision
decide_l3_verdict(const L3VerdictInputs& in) noexcept {
    L3VerdictDecision d;
    // SELLADO sólo dentro del gate L1-attack (frontera conservador/agresivo, opción a).
    // internal_ran && internal_is_suspicious espeja el "internal_pred && is_suspicious()"
    // del original; l1_gate_open es la restricción nueva que hace 1b-hoist conservador.
    d.seal_suspicious_internal =
        in.l1_gate_open && in.internal_ran && in.internal_is_suspicious;
    return d;
}

// Etiqueta del veredicto sellado (única hoy; commit 2 amplía). Constante nombrada para
// que el test y process_event compartan el literal exacto — cero divergencia de string.
inline constexpr std::string_view SUSPICIOUS_INTERNAL_LABEL = "SUSPICIOUS_INTERNAL";

} // namespace ml_defender