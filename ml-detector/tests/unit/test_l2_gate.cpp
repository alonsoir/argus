// test_l2_gate.cpp -- DAY271
//
// Verifica el predicado puro l2_gate_open, que decide si un flujo
// cruza la compuerta level1 -> level2 (cabezas especializadas).
//
// Cubre DOS cosas:
//   1) REGRESION: el camino NO forzado (force=false) es identico a hoy. El flag
//      force_all_heads no cambia el comportamiento de produccion.
//   2) MEDICION grieta B: el camino forzado (force=true) abre la compuerta SIEMPRE,
//      sea cual sea el veredicto de level1, para observar la cabeza DDoS.
//
// Es un test de UNIDAD: incluye solo l2_gate.hpp (sin dependencias). No
// depende de ZMQ, protobuf ni detectores en runtime; solo del predicado.
//
// La seguridad "un pipeline-start normal NUNCA abre la compuerta" descansa en el
// inicializador en-clase `bool force_all_heads_ = false;` (revisado en el .hpp) mas
// el caso 1 de abajo: con force=false, un flujo benigno queda fuera.

#include "l2_gate.hpp"

#include <cstdint>
#include <cstdio>

static int failures = 0;

static void check(const char* name, bool got, bool want) {
    if (got != want) {
        std::printf("  FAIL %-28s got=%d want=%d\n", name, (int)got, (int)want);
        ++failures;
    } else {
        std::printf("  ok   %-28s\n", name);
    }
}

int main() {
    // Umbral de referencia; la logica del predicado no depende del valor exacto.
    const double THR = 0.65;

    std::printf("test_l2_gate: camino NO forzado (regresion, == hoy)\n");
    // benigno (label 0): la compuerta NO se abre, la cabeza DDoS no corre.
    check("benigno no cruza",     l2_gate_open(false, 0, 0.99, THR), false);
    // ataque (label 1) con confianza >= umbral: cruza, como hoy.
    check("ataque>=umbral cruza", l2_gate_open(false, 1, 0.99, THR), true);
    // ataque con confianza por debajo del umbral: la cascada lo sigue vetando.
    check("ataque<umbral veta",   l2_gate_open(false, 1, 0.10, THR), false);
    // frontera: confianza == umbral cuenta como cruce (>=).
    check("umbral exacto cruza",  l2_gate_open(false, 1, THR,  THR), true);

    std::printf("test_l2_gate: camino forzado (grieta B, abre siempre)\n");
    // forzado sobre benigno: ABRE (este es el caso que mide B: la cabeza DDoS
    // corre sobre los flujos de 1 paquete que level1 despacha como benignos).
    check("forzado abre benigno", l2_gate_open(true, 0, 0.00, THR), true);
    // forzado no rompe el camino de ataque.
    check("forzado abre ataque",  l2_gate_open(true, 1, 0.99, THR), true);
    // forzado ignora el umbral por completo.
    check("forzado ignora umbral",l2_gate_open(true, 1, 0.10, THR), true);

    if (failures == 0) {
        std::printf("test_l2_gate: TODOS OK (7/7)\n");
        return 0;
    }
    std::printf("test_l2_gate: %d FALLO(S)\n", failures);
    return 1;
}