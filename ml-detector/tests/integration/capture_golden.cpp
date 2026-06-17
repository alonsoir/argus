// capture_golden.cpp — aRGus NDR — DAY 185 (B2)
// Captura el GOLDEN del oráculo: para cada vector, escribe con el CorrelationWriter
// REAL (path write_record/build_row, NUNCA serialize()), lee los bytes exactos que
// aterrizan en el CSV bronce, y los vuelca a un TSV reproducible.
//
// NO es un test (no add_test). Es una herramienta de captura de un solo disparo.
// Se corre con build_row VIRGEN (B1 no lo tocó) -> el golden congela el oráculo
// ANTES del rewire de B4. Authors: Alonso Isidoro Roman + Claude (Anthropic).
//
// LOCALE: fija classic a propósito (asunción de producción de un daemon). build_row
// no hace imbue; bajo es_ES saldrían millares/coma y el golden no casaría con
// serialize() (que sí fuerza classic). Avisa si el locale ambiental no era classic.
//
// BYTES EXACTOS: un tmpdir por vector -> el fichero contiene UN registro. Se lee
// entero (no por getline, que rompería el vector con \n embebido) y se quita el
// único '\n' final que añade write_record. Eso = lo que serialize() debe reproducir.

#include "correlation_v1_golden_vectors.hpp"
#include "correlation_writer.hpp"

#include <spdlog/spdlog.h>
#include <spdlog/sinks/null_sink.h>

#include <filesystem>
#include <fstream>
#include <iostream>
#include <locale>
#include <sstream>
#include <string>

namespace fs = std::filesystem;

// Misma clave que test_correlation_roundtrip (convención CsvEventWriter): 64 hex.
static const std::string KEY_HEX =
    "abababababababababababababababababababababababababababababababab";

static std::string hex_encode(const std::string& bytes) {
    static const char* H = "0123456789abcdef";
    std::string out;
    out.reserve(bytes.size() * 2);
    for (unsigned char c : bytes) { out += H[c >> 4]; out += H[c & 0xF]; }
    return out;
}

static std::string read_whole_file(const std::string& path) {
    std::ifstream f(path, std::ios::binary);
    std::ostringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

int main(int argc, char* argv[]) {
    if (argc != 2) {
        std::cerr << "Uso: " << argv[0] << " <ruta_salida_golden.tsv>\n";
        return 1;
    }
    const std::string out_path = argv[1];

    // Pin del locale de producción. Aviso ruidoso si el ambiental no era classic.
    const std::string ambient = std::locale("").name();
    if (ambient != "C" && ambient != "POSIX" && !ambient.empty()) {
        std::cerr << "⚠️  Locale ambiental = '" << ambient
                  << "'. Forzando classic para la captura (asunción de producción).\n"
                  << "   Si producción corre bajo este locale, el bronce viejo ya está\n"
                  << "   corrupto (millares/coma) — el refactor D-E lo arregla.\n";
    }
    std::locale::global(std::locale::classic());

    auto logger = std::make_shared<spdlog::logger>(
        "capture", std::make_shared<spdlog::sinks::null_sink_mt>());

    std::ofstream out(out_path, std::ios::trunc);
    if (!out.is_open()) {
        std::cerr << "❌ No puedo abrir salida: " << out_path << "\n";
        return 1;
    }
    out << "# correlation_v1 golden — capture_golden (DAY 185 B2)\n"
        << "# clave HMAC test: " << KEY_HEX << "\n"
        << "# locale: classic (C) — asunción de producción (ver D-E)\n"
        << "# formato: <id>\\t<category>\\t<status>\\t<hex(linea bronce 0-18, sin \\n final)>\n"
        << "# status: WRITTEN | SKIPPED  (SKIPPED -> hex vacío, community_id vacío D-F)\n"
        << "# fuente de vectores: correlation_v1_golden_vectors.hpp (compartida con B3)\n";

    const auto vectors = argus_golden::make_golden_vectors();
    int written = 0, skipped = 0, rejected = 0, mismatches = 0;

    for (const auto& gv : vectors) {
        const std::string base =
            (fs::temp_directory_path() / ("golden_" + gv.id)).string();
        fs::remove_all(base);

        ml_defender::CorrelationWriterConfig cfg;
        cfg.base_dir     = base;
        cfg.hmac_key_hex = KEY_HEX;

        bool ok = false;
        std::string path;
        {
            ml_defender::CorrelationWriter w(cfg, logger);
            ok = w.write_record(gv.event);
            w.flush();
            path = w.get_stats().current_file;
        }

        // Sanity: lo que esperamos del vector debe casar con lo que hizo
        // write_record. Tres estados: SKIP (community_id vacío, D-F) y REJECT
        // (\n/\r, validate Camino A) esperan NO-escribió (ok=false); el resto
        // espera escribió (ok=true). NOTA: REJECT solo casa tras el rewire de
        // write_record a serialize+validate; con build_row vivo dará mismatch.
        const bool expected_no_write = gv.expect_skip || gv.expect_reject;
        if (ok == expected_no_write) {  // ok=true cuando esperábamos no-escribir, o viceversa
            std::cerr << "⚠️  [" << gv.id << "] expect_skip=" << gv.expect_skip
                      << " expect_reject=" << gv.expect_reject
                      << " pero write_record devolvió ok=" << ok
                      << " — vector o contrato incoherente "
                      << "(¿recongelando antes del rewire de write_record?).\n";
            ++mismatches;
        }

        std::string status, hexbytes;
        if (ok && !path.empty() && fs::exists(path)) {
            std::string content = read_whole_file(path);
            if (!content.empty() && content.back() == '\n')
                content.pop_back();           // quita el único \n de write_record
            status = "WRITTEN";
            hexbytes = hex_encode(content);
            ++written;
        } else if (gv.expect_reject) {
            // \n/\r rechazado en origen por validate (Camino A). Sin bytes, igual
            // que SKIP, pero semánticamente distinto: REJECT = veneno rechazado,
            // SKIP = filtrado legítimo (community_id vacío).
            status = "REJECTED";
            hexbytes = "";
            ++rejected;
        } else {
            status = "SKIPPED";
            hexbytes = "";
            ++skipped;
        }

        out << "# [" << gv.id << "] " << gv.note << "\n";
        out << gv.id << '\t' << gv.category << '\t' << status << '\t' << hexbytes << '\n';

        fs::remove_all(base);
    }

    out.close();
    std::cout << "✅ Golden escrito: " << out_path << "\n"
              << "   vectores=" << vectors.size()
              << "  WRITTEN=" << written
              << "  SKIPPED=" << skipped
              << "  REJECTED=" << rejected
              << "  mismatches=" << mismatches << "\n";
    if (mismatches) {
        std::cerr << "❌ " << mismatches
                  << " vector(es) con expect_skip incoherente. Revisa antes de confiar el golden.\n";
        return 2;
    }
    return 0;
}