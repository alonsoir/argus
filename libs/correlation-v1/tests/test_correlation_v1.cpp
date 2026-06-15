// test_correlation_v1.cpp
// aRGus NDR — DAY 185 — Propiedad de equivalencia/confinamiento de libcorrelation_v1.
// ESTE TEST ES LA SPEC EJECUTABLE. Entra en RED contra la superficie declarada en
// correlation_v1.hpp (serialize/validate sin cuerpo -> "undefined reference" = RED).
// La migración (mover el tramo de serialización probado desde correlation_writer.cpp)
// lo pone GREEN. El golden de caracterización garantiza que los bytes no se movieron.
//
// TAXONOMÍA (cada fuzzer, UN dominio):
//   - P0/P2/P3 sobre Row puro -> AQUÍ (lib, sin protobuf).
//   - P1 byte-idéntico (serialize(to_row(event)) == oráculo) -> vive en el test de
//     ml-detector, porque necesita to_row + NetworkSecurityEvent. Ver bloque al final.
//
// NOTA DE WIRING (no invento tu harness): este fichero usa un check mínimo local.
// Adáptalo a tu framework real (gtest/catch2/custom) y cuélgalo del Makefile -> test-all.

#include "correlation_v1/correlation_v1.hpp"
#include <cstdint>
#include <cstdio>
#include <locale>
#include <random>
#include <string>
#include <vector>

using correlation_v1::CorrelationV1Row;
using correlation_v1::serialize;
using correlation_v1::validate;

// --- check mínimo (sustituir por tu framework) ------------------------------
static int g_failures = 0;
#define CHECK(cond, msg)                                                        \
    do {                                                                        \
        if (!(cond)) { std::printf("  FAIL: %s\n", (msg)); ++g_failures; }      \
        else         { std::printf("  ok:   %s\n", (msg)); }                    \
    } while (0)

// Clave HMAC de test FIJA (32 bytes). En el harness real viene de
// ARGUS_BRONZE_HMAC_KEY_HEX; ausencia de clave = error ruidoso, nunca hardcode en prod.
static const std::vector<uint8_t> kTestKey(32, 0xAB);

// Row válido de referencia (todos los campos en dominio legal).
static CorrelationV1Row make_valid_row() {
    CorrelationV1Row r;
    r.schema_version       = "1";
    r.source_sensor        = "argus";
    r.event_id             = "evt-0001";
    r.node_id              = "node-badajoz-01";
    r.community_id         = "1:wCb3OG7yAFWAreSE2/VQ7Wc/cTU=";
    r.flow_start_sec       = 1718409600;
    r.flow_start_nano      = 123456789;
    r.src_ip               = "10.0.0.7";
    r.dst_ip               = "10.0.0.8";
    r.src_port             = 44321;
    r.dst_port             = 445;
    r.protocol             = "TCP";
    r.final_classification = "MALICIOUS";
    r.threat_category      = "RANSOMWARE";
    r.fast_detector_score  = 0.873421;
    r.ml_detector_score    = 0.991200;
    r.overall_threat_score = 0.950000;
    r.authoritative_source = "DETECTOR_SOURCE_ML_PRIORITY";
    return r;
}

// ----------------------------------------------------------------------------
// P0a — DETERMINISMO. Mismo Row -> mismos bytes. Precondición de byte-identidad.
// ----------------------------------------------------------------------------
static void test_P0a_determinism() {
    std::printf("[P0a] determinismo\n");
    const auto row = make_valid_row();
    auto a = serialize(row, kTestKey);
    auto b = serialize(row, kTestKey);
    CHECK(a.ok && b.ok, "serialize OK en dominio válido");
    CHECK(a.line == b.line, "dos serializaciones del mismo Row = bytes idénticos");
}

// ----------------------------------------------------------------------------
// P0b — INMUNIDAD AL LOCALE (el hallazgo D-E). Bajo es_ES, los enteros NO deben
// salir con separador de millares ni el decimal con coma. RED hasta que imbue
// classic esté DENTRO de serialize.
// ----------------------------------------------------------------------------
static void test_P0b_locale_immunity() {
    std::printf("[P0b] inmunidad al locale (D-E)\n");
    const auto row = make_valid_row();
    auto classic_line = serialize(row, kTestKey);

    std::string es_line;
    try {
        std::locale prev = std::locale::global(std::locale("es_ES.UTF-8"));
        es_line = serialize(row, kTestKey).line;
        std::locale::global(prev);                       // restaurar pase lo que pase
    } catch (const std::exception&) {
        std::printf("  skip: locale es_ES.UTF-8 no instalado en este host\n");
        return;
    }
    CHECK(classic_line.ok, "serialize OK bajo classic");
    CHECK(classic_line.line == es_line,
          "bytes idénticos bajo classic y es_ES (sin millares, decimal con punto)");
}

// ----------------------------------------------------------------------------
// P2 — CONFINAMIENTO DE IMAGEN (adversarial, enumerado). validate RECHAZA y
// serialize NO emite. D-B: dirección ⟹ ACOTADA por estos vectores, NO probada
// exhaustivamente. Cada caso es una clase del injector adversarial.
// ----------------------------------------------------------------------------
static void test_P2_confinement() {
    std::printf("[P2] confinamiento (D-B: acotado por enumeración)\n");

    // Caso D-F: community_id vacío llegó a la lib (bug del productor; to_row debió SKIP).
    {
        auto row = make_valid_row();
        row.community_id.clear();
        CHECK(!validate(row), "community_id vacío -> validate RECHAZA (defensa en profundidad)");
        CHECK(!serialize(row, kTestKey), "community_id vacío -> serialize NO emite");
    }

    // Caso D-D (v2, guard DIFERIDO): símbolo de col 17 ilegal -> "" o cualquier no-símbolo.
    // En v1 (refactor byte-idéntico) este check NO está activo todavía: marcado como
    // expectativa del commit de contrato, no del refactor. Descomentar en el commit D-D.
    // {
    //     auto row = make_valid_row();
    //     row.authoritative_source = "";            // firma de enum int fuera de {0..6}
    //     CHECK(!validate(row), "col 17 símbolo ilegal -> validate RECHAZA (guard D-D)");
    //     CHECK(!serialize(row, kTestKey), "col 17 símbolo ilegal -> serialize NO emite");
    // }
    // {
    //     auto row = make_valid_row();
    //     row.authoritative_source = "SURICATA_SIG"; // no es símbolo DetectorSource
    //     CHECK(!validate(row), "col 17 no-DetectorSource -> validate RECHAZA (guard D-D)");
    // }
    std::printf("  (guard col 17 -> commit de contrato D-D, no este refactor)\n");
}

// ----------------------------------------------------------------------------
// P3 — FUENTE ÚNICA DE VALIDEZ. serialize embuda por el MISMO validate: no hay
// bypass. Todo Row que validate rechaza, serialize también lo rechaza.
// ----------------------------------------------------------------------------
static void test_P3_single_notary() {
    std::printf("[P3] notario único\n");
    auto bad = make_valid_row();
    bad.community_id.clear();                 // sabemos que validate lo rechaza
    const bool v = static_cast<bool>(validate(bad));
    const bool s = static_cast<bool>(serialize(bad, kTestKey));
    CHECK(v == s, "validate y serialize coinciden en aceptar/rechazar (sin bypass)");
}

// ----------------------------------------------------------------------------
// P1 (struct-fuzzer, dominio VÁLIDO) — determinismo bajo carga aleatoria.
// El fuzzer constriñe authoritative_source a {7 símbolos legales}: el dominio
// drift (7/99 -> "") es territorio del generador adversarial P2, no de P1.
// La byte-identidad CONTRA EL ORÁCULO se prueba en el test de ml-detector (abajo),
// no aquí, porque requiere to_row + protobuf.
// ----------------------------------------------------------------------------
static void test_P1_struct_fuzz_determinism() {
    std::printf("[P1] struct-fuzzer (dominio válido, determinismo)\n");
    static const char* kLegalSources[] = {
        "DETECTOR_SOURCE_UNKNOWN", "DETECTOR_SOURCE_FAST_ONLY",
        "DETECTOR_SOURCE_ML_ONLY", "DETECTOR_SOURCE_FAST_PRIORITY",
        "DETECTOR_SOURCE_ML_PRIORITY", "DETECTOR_SOURCE_CONSENSUS",
        "DETECTOR_SOURCE_DIVERGENCE",
    };
    std::mt19937_64 rng(0xA11050);            // semilla fija = reproducible
    int bad = 0;
    const int N = 100000;                     // subir a 1M en el harness real
    for (int i = 0; i < N; ++i) {
        auto row = make_valid_row();
        row.flow_start_sec       = static_cast<int64_t>(rng());
        row.flow_start_nano      = static_cast<int32_t>(rng() % 1000000000);
        row.src_port             = static_cast<uint32_t>(rng() & 0xFFFF);
        row.dst_port             = static_cast<uint32_t>(rng() & 0xFFFF);
        row.fast_detector_score  = (rng() % 1000000) / 1000000.0;
        row.ml_detector_score    = (rng() % 1000000) / 1000000.0;
        row.overall_threat_score = (rng() % 1000000) / 1000000.0;
        row.authoritative_source = kLegalSources[rng() % 7];
        auto a = serialize(row, kTestKey);
        auto b = serialize(row, kTestKey);
        if (!a.ok || a.line != b.line) ++bad;
    }
    CHECK(bad == 0, "100k Rows válidos: serialize determinista y OK");
}

int main() {
    std::printf("== libcorrelation_v1 :: propiedad de equivalencia/confinamiento ==\n");
    test_P0a_determinism();
    test_P0b_locale_immunity();
    test_P2_confinement();
    test_P3_single_notary();
    test_P1_struct_fuzz_determinism();
    std::printf("== %d fallos ==\n", g_failures);
    return g_failures == 0 ? 0 : 1;
}

// ============================================================================
// BLOQUE ORÁCULO (vive en el test de ml-detector, NO aquí — necesita protobuf).
// Pasos, en orden, ANTES de migrar correlation_writer.cpp:
//
//   PASO A (congelar no-determinismo): fixture con locale classic + clave fija
//           (ARGUS_BRONZE_HMAC_KEY_HEX). flow_start_* son datos del evento, no reloj.
//
//   PASO B (golden de caracterización): contra el BINARIO ACTUAL (working tree con
//           4e221ede/112b9df1), N eventos deterministas -> capturar build_row(event)
//           byte a byte a un fichero golden. Este es el oráculo congelado. NO se
//           puede capturar desde un clone divergente: corre en tu Mac.
//
//   PASO C (equivalencia, RED -> GREEN con la migración):
//           para cada (event, golden_bytes):
//               assert serialize(to_row(event).row) == golden_bytes;   // byte-idéntico
//           + fuzzer de PROTOBUF 1M sobre to_row con authoritative_source ∈ {0..6}.
//           Aquí es donde "reubicación byte-idéntica" queda PROBADO sobre el dominio
//           válido. El guard D-D NO toca este test: diverge solo en drift (commit aparte).
// ============================================================================