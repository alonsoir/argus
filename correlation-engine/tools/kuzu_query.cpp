// kuzu_query.cpp — DAY 228
// Consulta ad-hoc contra una BD Kuzu existente, por ruta.
//
// Herramienta de VERIFICACIÓN, no test CI (mismo patrón que
// experiments/kuzu_concurrency_smoke.cpp). Existe porque en las VMs no hay
// CLI de Kuzu ni binding de Python, y fijar una versión por pip sería
// desincronizable respecto a la libkuzu.so (v0.11.3) que enlaza el sink.
//
// Idioma tomado de tests/test_flujo_b_end_to_end.cpp (no reinventado).
//
// USO: kuzu_query <kuzu_db_path> <cypher>

#include <kuzu.hpp>

#include <exception>
#include <iostream>
#include <memory>
#include <string>

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "USO: " << argv[0] << " <kuzu_db_path> <cypher>\n";
        return 1;
    }
    const std::string db_path = argv[1];
    const std::string cypher  = argv[2];

    try {
        kuzu::main::SystemConfig cfg;
        auto db   = std::make_unique<kuzu::main::Database>(db_path, cfg);
        auto conn = std::make_unique<kuzu::main::Connection>(db.get());

        auto result = conn->query(cypher);
        if (!result->isSuccess()) {
            std::cerr << "FATAL: la consulta no tuvo exito\n";
            return 1;
        }

        uint64_t n = 0;
        while (result->hasNext()) {
            std::cout << result->getNext()->toString() << "\n";
            ++n;
        }
        std::cout << "(" << n << " filas)\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "FATAL: " << e.what() << "\n";
        return 1;
    }
}
