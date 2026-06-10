// test_cypher_injection.cpp — H-1: el escape de literales Cypher debe resistir
// payloads con barra invertida. Los campos string del CorrelationRecord derivan
// de trafico de red (fuente NO confiable); un campo terminado en '\' rompia el
// escape de la comilla y abria el literal. Este test fija el invariante.
// Authors: Alonso Isidoro Roman + Claude (Anthropic).
#include <gtest/gtest.h>

#include "correlation_engine/cypher_builder.hpp"
#include "correlation_engine/correlation_record.hpp"

#include <string>

using namespace argus::correlation;

namespace {

// Record minimo valido (MALICIOUS -> Alert) con un campo bajo control del test.
CorrelationRecord make_record() {
    CorrelationRecord r;
    r.event_id             = "ev-inj";
    r.node_id              = "node-1";
    r.community_id         = "1:abc=";
    r.flow_start_sec       = 1000;
    r.flow_start_nano      = 0;
    r.final_classification = "MALICIOUS";
    r.threat_category      = "ransomware";
    r.authoritative_source = "XGBoostPlugin";
    return r;
}

// Cuenta comillas simples NO escapadas (sin '\' inmediatamente antes).
// En un Cypher bien formado por este builder deben quedar en numero par:
// cada literal abre y cierra. Un escape roto deja un numero impar.
size_t unescaped_single_quotes(const std::string& s) {
    size_t count = 0;
    for (size_t i = 0; i < s.size(); ++i) {
        if (s[i] != '\'') continue;
        size_t backslashes = 0;
        for (size_t j = i; j-- > 0 && s[j] == '\\'; ) ++backslashes;
        if (backslashes % 2 == 0) ++count;  // numero par de '\' => comilla activa
    }
    return count;
}

}  // namespace

// El payload clasico de inyeccion via backslash: campo terminado en '\'.
// Antes del fix, esc("evil\\") devolvia "evil\\" (sin tocar la barra), de modo
// que la comilla de cierre del literal quedaba escapada y el literal seguia abierto.
TEST(CypherInjection, TrailingBackslashDoesNotBreakLiteral) {
    auto r = make_record();
    r.threat_category = "evil\\";   // un solo backslash final

    const std::string cypher = build_cypher(r, "flow-uid-x");

    // El backslash del dato debe quedar duplicado (escapado), no crudo.
    EXPECT_NE(cypher.find("evil\\\\"), std::string::npos)
        << "el backslash del dato no se escapo: " << cypher;
    // Y todas las comillas de literal deben quedar balanceadas (numero par).
    EXPECT_EQ(unescaped_single_quotes(cypher) % 2, 0u)
        << "literal Cypher descuadrado (escape roto): " << cypher;
}

// Intento de inyectar estructura Cypher cerrando el literal y anyadiendo clausula.
TEST(CypherInjection, QuoteAndClauseStayInsideLiteral) {
    auto r = make_record();
    // Si el escape fallara, esto cerraria el literal e inyectaria un MATCH/DELETE.
    r.community_id = "x'}) DETACH DELETE f //";

    const std::string cypher = build_cypher(r, "flow-uid-y");

    // La comilla del dato debe ir escapada (\') -> el literal no se cierra ahi.
    EXPECT_NE(cypher.find("x\\'"), std::string::npos)
        << "la comilla del dato no se escapo: " << cypher;
    EXPECT_EQ(unescaped_single_quotes(cypher) % 2, 0u)
        << "literal Cypher descuadrado: " << cypher;
}

// Mezcla backslash + comilla: \' del dato no debe colapsar en cierre de literal.
TEST(CypherInjection, BackslashBeforeQuoteIsNeutralized) {
    auto r = make_record();
    r.authoritative_source = "a\\'; MATCH (n) DELETE n //";

    const std::string cypher = build_cypher(r, "flow-uid-z");

    EXPECT_EQ(unescaped_single_quotes(cypher) % 2, 0u)
        << "literal Cypher descuadrado con \\' : " << cypher;
}
