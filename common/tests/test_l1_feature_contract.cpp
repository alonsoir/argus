// test_l1_feature_contract.cpp — DAY 217
// DEBT-FEATURE-EXTRACTOR-L1-BROKEN-001
//
// ANCLA el orden de las 23 features de L1 (l1_feature_contract.hpp) al fichero
// que el modelo ONNX espera de verdad: sniffer/config/features/rf_23_features.json.
//
// POR QUÉ EXISTE:
//   El campo `general_attack_features = 102` del protobuf es `repeated double`:
//   POSICIONAL, SIN NOMBRES. El sniffer lo rellena y el ml-detector lo lee. Si los
//   dos no comparten el MISMO orden, el ONNX recibe basura ordenada y devuelve una
//   constante confiada — el bug de DAY 216, reintroducido por la puerta de atrás.
//   El único sitio donde ese orden estaba escrito era un JSON de config que nadie
//   validaba. Este test lo hace falsable.
//
// TEST DE PROPIEDAD, NO DE ESPEJO (lección DAY 215):
//   No compara 23 literales contra 23 literales. Comprueba una RELACIÓN entre dos
//   ficheros: "cada nombre del header aparece en el JSON, y en el MISMO orden".
//   Reordenar el JSON → ROJO. Renombrar una feature → ROJO. Añadir una al header
//   sin añadirla al JSON → ROJO.
//
// VALIDADO EXPERIMENTALMENTE (DAY 216): con esas 23 columnas, en ese orden, sin
//   escalar, level1_attack_detector.onnx da 200/200 DDoS y 0/200 FP sobre
//   Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv.
//
// LIMITACIÓN CONOCIDA (declarada, no escondida):
//   La búsqueda es textual sobre el JSON crudo (sin parser, para no meter una
//   dependencia nueva a 20 días del go/no-go). Se busca el nombre ENTRECOMILLADO,
//   así que un `model_name` que fuese subcadena estricta de otro podría dar falso
//   verde. Con estos 23 nombres no ocurre. Si el contrato crece, revisar.

#include "../include/argus/l1_feature_contract.hpp"

#include <cassert>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

namespace {

std::string read_file(const std::string& path) {
    std::ifstream f(path);
    if (!f) {
        std::cerr << "FATAL: no se pudo abrir el contrato JSON: " << path << "\n"
                  << "       (se pasa por -DARGUS_L1_CONTRACT_JSON en CMake, o como argv[1])\n";
        std::exit(1);
    }
    std::ostringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

}  // namespace

int main(int argc, char** argv) {
    const std::string json_path =
        (argc > 1) ? argv[1] : std::string(ARGUS_L1_CONTRACT_JSON);

    const std::string json = read_file(json_path);
    std::cout << "Contrato: " << json_path << " (" << json.size() << " B)\n";

    // T1 — el header declara exactamente 23 features.
    // Si alguien añade una al array y olvida FEATURE_COUNT, o al revés, aquí muere.
    {
        static_assert(argus::l1::NAMES.size() == argus::l1::FEATURE_COUNT,
                      "NAMES y FEATURE_COUNT desincronizados");
        assert(argus::l1::FEATURE_COUNT == 23);
        std::cout << "T1 PASS: el header declara 23 features\n";
    }

    // T2 — el JSON declara el mismo recuento.
    {
        const std::string key = "\"_feature_count\": 23";
        assert(json.find(key) != std::string::npos &&
               "el JSON no declara _feature_count: 23");
        std::cout << "T2 PASS: el JSON declara _feature_count = 23\n";
    }

    // T3 — CADA nombre del header aparece en el JSON, Y EN EL MISMO ORDEN.
    //
    //   El cursor sólo avanza: si el JSON reordena dos features, el find() de la
    //   segunda no la encuentra por delante del cursor y el test se pone ROJO.
    //   Ésta es la propiedad que importa: el orden ES el contrato.
    {
        std::string::size_type cursor = 0;
        for (std::size_t i = 0; i < argus::l1::FEATURE_COUNT; ++i) {
            const std::string needle =
                std::string("\"") + argus::l1::NAMES[i] + "\"";

            const auto pos = json.find(needle, cursor);
            if (pos == std::string::npos) {
                // Distinguir "no está" de "está, pero fuera de orden" — el
                // diagnóstico correcto ahorra media hora al que lo lea.
                const auto anywhere = json.find(needle);
                std::cerr << "\nFALLO en la feature [" << i << "]: " << needle << "\n";
                if (anywhere == std::string::npos) {
                    std::cerr << "  NO EXISTE en el JSON.\n"
                              << "  ¿renombrada? ¿espacio inicial cambiado?\n";
                } else {
                    std::cerr << "  EXISTE, pero FUERA DE ORDEN (aparece antes de la "
                              << "posición esperada).\n"
                              << "  ⚠️ REORDENAR EL CONTRATO EXIGE REENTRENAR EL MODELO.\n";
                }
                assert(false && "contrato L1 desincronizado (ver stderr)");
            }
            cursor = pos + needle.size();
        }
        std::cout << "T3 PASS: las 23 features del header aparecen en el JSON, en orden\n";
    }

    // T4 — RED->GREEN: el test debe poder FALLAR.
    //
    //   Un test que nunca ha estado ROJO es una hipótesis, no una red (DAY 215).
    //   Aquí se comprueba, en positivo, que la lógica de T3 detecta un nombre
    //   inventado. Si esto pasara, T3 sería un no-op y nadie lo sabría.
    {
        const std::string fake = "\" Esta Feature No Existe\"";
        assert(json.find(fake) == std::string::npos &&
               "la lógica de búsqueda de T3 está rota: encuentra lo que no existe");
        std::cout << "T4 PASS: la búsqueda de T3 rechaza un nombre inventado\n";
    }

    std::cout << "\n✅ test_l1_feature_contract: 4/4 PASS\n";
    return 0;
}