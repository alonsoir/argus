// ml-detector/tests/unit/test_heads_config.cpp — [HEADS-TESTS-D305]
// Reglas de Alonso (DAY305) para la configuracion de las cabezas: casos validos sin aviso; ausentes e invalidos
// con el defecto y un [CONFIG-DEFAULT] que nombra el campo. Sin GTest, con main propio (como test_l2_gate).
#include "heads_config.hpp"
#include <iostream>
#include <sstream>
#include <string>

namespace {
int g_casos = 0;
int g_fallos = 0;
void comprueba(bool ok, const std::string& que) {
    ++g_casos;
    if (!ok) {
        ++g_fallos;
        std::cerr << "FALLA: " << que << "\n";
    }
}
using nlohmann::json;
using ml_detector::heads::read_enabled;
using ml_detector::heads::read_int_in_range;

// enabled: valor esperado y si debe avisar
void caso_enabled(const json& blk, bool esperado, bool aviso_esperado, const std::string& que) {
    std::ostringstream av;
    const bool r = read_enabled(blk, "ml.prueba", av);
    comprueba(r == esperado, "enabled " + que + ": valor");
    const bool avisa = av.str().find("[CONFIG-DEFAULT] ml.prueba.enabled") != std::string::npos;
    comprueba(avisa == aviso_esperado, "enabled " + que + ": aviso");
    if (aviso_esperado) {
        comprueba(av.str().find("APAGADA") != std::string::npos, "enabled " + que + ": el aviso dice APAGADA");
    }
}
void caso_entero(const json& blk, int esperado, bool aviso_esperado, const std::string& que) {
    std::ostringstream av;
    const int r = read_int_in_range(blk, "intervalo", "monitoring", 60, 10, 3600, av);
    comprueba(r == esperado, "entero " + que + ": valor (" + std::to_string(r) + ")");
    const bool avisa = av.str().find("[CONFIG-DEFAULT] monitoring.intervalo") != std::string::npos;
    comprueba(avisa == aviso_esperado, "entero " + que + ": aviso");
    if (aviso_esperado) {
        comprueba(av.str().find("[10, 3600]") != std::string::npos, "entero " + que + ": el aviso da los limites");
    }
}
}  // namespace

int main() {
    caso_enabled(json{{"enabled", true}}, true, false, "true");
    caso_enabled(json{{"enabled", false}}, false, false, "false");
    caso_enabled(json{{"enabled", "true"}}, true, false, "\"true\"");
    caso_enabled(json{{"enabled", "TRUE"}}, true, false, "\"TRUE\"");
    caso_enabled(json{{"enabled", "False"}}, false, false, "\"False\"");
    caso_enabled(json{{"enabled", "FALSE"}}, false, false, "\"FALSE\"");
    caso_enabled(json::object(), false, true, "ausente");
    caso_enabled(json{{"enabled", "yes"}}, false, true, "\"yes\"");
    caso_enabled(json{{"enabled", " true"}}, false, true, "\" true\" con espacio");
    caso_enabled(json{{"enabled", 1}}, false, true, "1");
    caso_enabled(json{{"enabled", 0}}, false, true, "0");
    caso_enabled(json{{"enabled", nullptr}}, false, true, "null");
    caso_enabled(json::array({true}), false, true, "bloque que no es objeto");

    caso_entero(json{{"intervalo", 60}}, 60, false, "60");
    caso_entero(json{{"intervalo", 10}}, 10, false, "limite inferior 10");
    caso_entero(json{{"intervalo", 3600}}, 3600, false, "limite superior 3600");
    caso_entero(json{{"intervalo", 300}}, 300, false, "300");
    caso_entero(json::object(), 60, true, "ausente");
    caso_entero(json{{"intervalo", 9}}, 60, true, "9 bajo el minimo");
    caso_entero(json{{"intervalo", 3601}}, 60, true, "3601 sobre el maximo");
    caso_entero(json{{"intervalo", -5}}, 60, true, "-5");
    caso_entero(json{{"intervalo", 60.0}}, 60, true, "60.0 (no es entero)");
    caso_entero(json{{"intervalo", 60.5}}, 60, true, "60.5");
    caso_entero(json{{"intervalo", "60"}}, 60, true, "\"60\" texto");
    caso_entero(json{{"intervalo", true}}, 60, true, "true");
    caso_entero(json{{"intervalo", nullptr}}, 60, true, "null");
    caso_entero(json{{"intervalo", 18446744073709551615ULL}}, 60, true, "uint64 enorme");

    std::cout << "[test_heads_config] ml-detector: " << (g_casos - g_fallos) << "/" << g_casos << " comprobaciones OK"
              << std::endl;
    return g_fallos == 0 ? 0 : 1;
}
