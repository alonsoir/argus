// sniffer/tests/test_heads_config.cpp — [HEADS-TESTS-D305]
// Reglas de Alonso (DAY305) para fast_detector.enabled y los intervalos del sniffer: casos validos sin aviso;
// ausentes e invalidos con el defecto y un [CONFIG-DEFAULT] que nombra el campo. Sin GTest, con main propio.
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
using sniffer::heads::leer_enabled;
using sniffer::heads::leer_entero;

Json::Value con(const char* k, const Json::Value& v) {
    Json::Value o(Json::objectValue);
    o[k] = v;
    return o;
}
void caso_enabled(const Json::Value& blk, bool esperado, bool aviso_esperado, const std::string& que) {
    std::ostringstream av;
    const bool r = leer_enabled(blk, "fast_detector", av);
    comprueba(r == esperado, "enabled " + que + ": valor");
    const bool avisa = av.str().find("[CONFIG-DEFAULT] fast_detector.enabled") != std::string::npos;
    comprueba(avisa == aviso_esperado, "enabled " + que + ": aviso");
    if (aviso_esperado) {
        comprueba(av.str().find("APAGADO") != std::string::npos, "enabled " + que + ": el aviso dice APAGADO");
    }
}
void caso_entero(const Json::Value& blk, int esperado, bool aviso_esperado, const std::string& que) {
    std::ostringstream av;
    const int r = leer_entero(blk, "window_interval_seconds", "fast_detector.ransomware", 30, 5, 3600, av);
    comprueba(r == esperado, "entero " + que + ": valor (" + std::to_string(r) + ")");
    const bool avisa =
        av.str().find("[CONFIG-DEFAULT] fast_detector.ransomware.window_interval_seconds") != std::string::npos;
    comprueba(avisa == aviso_esperado, "entero " + que + ": aviso");
    if (aviso_esperado) {
        comprueba(av.str().find("[5, 3600]") != std::string::npos, "entero " + que + ": el aviso da los limites");
    }
}
}  // namespace

int main() {
    caso_enabled(con("enabled", true), true, false, "true");
    caso_enabled(con("enabled", false), false, false, "false");
    caso_enabled(con("enabled", "true"), true, false, "\"true\"");
    caso_enabled(con("enabled", "TRUE"), true, false, "\"TRUE\"");
    caso_enabled(con("enabled", "False"), false, false, "\"False\"");
    caso_enabled(con("enabled", "FALSE"), false, false, "\"FALSE\"");
    caso_enabled(Json::Value(Json::objectValue), false, true, "ausente");
    caso_enabled(con("enabled", "yes"), false, true, "\"yes\"");
    caso_enabled(con("enabled", " true"), false, true, "\" true\" con espacio");
    caso_enabled(con("enabled", 1), false, true, "1");
    caso_enabled(con("enabled", 0), false, true, "0");
    caso_enabled(con("enabled", Json::Value()), false, true, "null");
    caso_enabled(Json::Value(Json::arrayValue), false, true, "bloque que no es objeto");

    caso_entero(con("window_interval_seconds", 30), 30, false, "30");
    caso_entero(con("window_interval_seconds", 5), 5, false, "limite inferior 5");
    caso_entero(con("window_interval_seconds", 3600), 3600, false, "limite superior 3600");
    caso_entero(con("window_interval_seconds", Json::UInt(120)), 120, false, "120 sin signo");
    caso_entero(Json::Value(Json::objectValue), 30, true, "ausente");
    caso_entero(con("window_interval_seconds", 4), 30, true, "4 bajo el minimo");
    caso_entero(con("window_interval_seconds", 3601), 30, true, "3601 sobre el maximo");
    caso_entero(con("window_interval_seconds", -5), 30, true, "-5");
    caso_entero(con("window_interval_seconds", 30.0), 30, true, "30.0 (no es entero)");
    caso_entero(con("window_interval_seconds", 30.5), 30, true, "30.5");
    caso_entero(con("window_interval_seconds", "30"), 30, true, "\"30\" texto");
    caso_entero(con("window_interval_seconds", true), 30, true, "true");
    caso_entero(con("window_interval_seconds", Json::Value()), 30, true, "null");
    caso_entero(con("window_interval_seconds", Json::UInt64(18446744073709551615ULL)), 30, true, "uint64 enorme");

    std::cout << "[test_heads_config] sniffer: " << (g_casos - g_fallos) << "/" << g_casos << " comprobaciones OK"
              << std::endl;
    return g_fallos == 0 ? 0 : 1;
}
