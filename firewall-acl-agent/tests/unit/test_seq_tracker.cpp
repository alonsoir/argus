// [TIMEBASE-SEQ-D297] Pruebas de SeqTracker (firewall/seq_tracker.hpp). Header-only, CHECK propio.
// Los valores esperados son las predicciones escritas ANTES de compilar (DAY297).
#include "firewall/seq_tracker.hpp"

#include <cstdio>
#include <string>

namespace {
int g_ok = 0;
int g_fallos = 0;
using T = ::mldefender::firewall::SeqTracker;
}  // namespace

#define CHECK_EQ(a, b)                                                                              \
    do {                                                                                            \
        const unsigned long long va_ = static_cast<unsigned long long>(a);                          \
        const unsigned long long vb_ = static_cast<unsigned long long>(b);                          \
        if (va_ == vb_) {                                                                           \
            ++g_ok;                                                                                 \
        } else {                                                                                    \
            ++g_fallos;                                                                             \
            std::printf("FALLO %s:%d %s = %llu, esperado %llu\n", __FILE__, __LINE__, #a, va_, vb_); \
        }                                                                                           \
    } while (0)

// 1..10 en orden: nada que contar.
static void caso_orden() {
    T t(4096);
    for (unsigned s = 1; s <= 10; ++s) t.observe("A", s);
    CHECK_EQ(t.claves(), 1);
    CHECK_EQ(t.recibidos(), 10);
    CHECK_EQ(t.dup(), 0);
    CHECK_EQ(t.hueco(), 0);
    CHECK_EQ(t.desorden(), 0);
    CHECK_EQ(t.viejo(), 0);
    CHECK_EQ(t.invariante(), 0);
}

// 1,2,5 -> hueco 2; 3 y 4 tarde -> desorden 2, hueco 0; 5 y 3 otra vez -> dup 2.
static void caso_hueco_relleno_dup() {
    T t(4096);
    t.observe("A", 1);
    t.observe("A", 2);
    t.observe("A", 5);
    CHECK_EQ(t.hueco(), 2);
    t.observe("A", 3);
    CHECK_EQ(t.desorden(), 1);
    CHECK_EQ(t.hueco(), 1);
    t.observe("A", 4);
    CHECK_EQ(t.desorden(), 2);
    CHECK_EQ(t.hueco(), 0);
    t.observe("A", 5);
    t.observe("A", 3);
    CHECK_EQ(t.dup(), 2);
    CHECK_EQ(t.recibidos(), 7);
    CHECK_EQ(t.invariante(), 0);
}

// Ventana 64: 1 y 100 -> hueco 98 (salto >= ventana, se limpia todo); 2 -> viejo; 50 -> relleno (hueco 97).
static void caso_viejo() {
    T t(64);
    t.observe("B", 1);
    t.observe("B", 100);
    CHECK_EQ(t.hueco(), 98);
    t.observe("B", 2);
    CHECK_EQ(t.viejo(), 1);
    t.observe("B", 50);
    CHECK_EQ(t.desorden(), 1);
    CHECK_EQ(t.hueco(), 97);
    CHECK_EQ(t.dup(), 0);
    CHECK_EQ(t.recibidos(), 4);
}

// Ventana 64, 1..200 en orden: 150 y 137 (200-137 = 63) -> dup; 136 (= 64) y 130 -> viejo.
static void caso_frontera() {
    T t(64);
    for (unsigned s = 1; s <= 200; ++s) t.observe("D", s);
    t.observe("D", 150);
    t.observe("D", 137);
    CHECK_EQ(t.dup(), 2);
    t.observe("D", 136);
    t.observe("D", 130);
    CHECK_EQ(t.viejo(), 2);
    CHECK_EQ(t.hueco(), 0);
    CHECK_EQ(t.desorden(), 0);
}

// Reinicio del productor (otro arranque, mismo nodo y boot_id): clave nueva, sin duplicados ni viejos.
static void caso_reinicio() {
    T t(4096);
    for (unsigned s = 1; s <= 5; ++s) t.observe("n|b|1000", s);
    for (unsigned s = 1; s <= 3; ++s) t.observe("n|b|2000", s);
    CHECK_EQ(t.claves(), 2);
    CHECK_EQ(t.recibidos(), 8);
    CHECK_EQ(t.dup(), 0);
    CHECK_EQ(t.viejo(), 0);
    CHECK_EQ(t.hueco(), 0);
}

// La primera secuencia de una clave es su inicio: las anteriores no son hueco.
static void caso_inicio() {
    T t(4096);
    t.observe("A", 1000);
    t.observe("A", 1001);
    CHECK_EQ(t.hueco(), 0);
}

// producer_seq = 0: se cuenta aparte y no crea clave.
static void caso_cero() {
    T t(4096);
    t.observe("A", 0);
    t.observe("A", 0);
    CHECK_EQ(t.cero(), 2);
    CHECK_EQ(t.recibidos(), 0);
    CHECK_EQ(t.claves(), 0);
}

// Ventana por debajo del minimo -> 64; el resumen lleva todos los campos.
static void caso_ventana_y_resumen() {
    T t(10);
    CHECK_EQ(t.ventana(), 64);
    const std::string r = T(4096).resumen();
    CHECK_EQ(r.find("seq_dup=0") != std::string::npos ? 1 : 0, 1);
    CHECK_EQ(r.find("seq_invariante=0") != std::string::npos ? 1 : 0, 1);
    CHECK_EQ(r.find("seq_ventana=4096") != std::string::npos ? 1 : 0, 1);
}

// [TIMEBASE-SEQ-DET-D297] Resultado de observe() y datos del maximo previo (13 CHECK).
static void caso_resultados() {
    using R = ::mldefender::firewall::SeqResultado;
    T t(64);
    auto o = t.observe("K", 1, 100, 1);
    CHECK_EQ(static_cast<int>(o.r), static_cast<int>(R::kInicio));
    o = t.observe("K", 2, 200, 1);
    CHECK_EQ(static_cast<int>(o.r), static_cast<int>(R::kOrden));
    CHECK_EQ(o.max_previo, 1);
    o = t.observe("K", 5, 500, 2);
    CHECK_EQ(static_cast<int>(o.r), static_cast<int>(R::kHueco));
    CHECK_EQ(o.max_previo, 2);
    o = t.observe("K", 3, 300, 1);
    CHECK_EQ(static_cast<int>(o.r), static_cast<int>(R::kDesorden));
    CHECK_EQ(o.max_previo, 5);
    CHECK_EQ(o.mono_max, 500);
    CHECK_EQ(o.etiqueta_max, 2);
    o = t.observe("K", 3, 300, 1);
    CHECK_EQ(static_cast<int>(o.r), static_cast<int>(R::kDup));
    o = t.observe("K", 0);
    CHECK_EQ(static_cast<int>(o.r), static_cast<int>(R::kCero));
    T v(64);
    v.observe("V", 1);
    v.observe("V", 100);
    o = v.observe("V", 2);
    CHECK_EQ(static_cast<int>(o.r), static_cast<int>(R::kViejo));
    CHECK_EQ(std::string(::mldefender::firewall::seq_resultado_nombre(R::kDesorden)) == "desorden" ? 1 : 0, 1);
}

int main() {
    caso_orden();
    caso_hueco_relleno_dup();
    caso_viejo();
    caso_frontera();
    caso_reinicio();
    caso_inicio();
    caso_cero();
    caso_ventana_y_resumen();
    caso_resultados();  // [TIMEBASE-SEQ-DET-D297]
    std::printf("test_seq_tracker: ok=%d fallos=%d\n", g_ok, g_fallos);
    return g_fallos == 0 ? 0 : 1;
}
