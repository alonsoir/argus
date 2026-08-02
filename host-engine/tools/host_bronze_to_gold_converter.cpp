// host_bronze_to_gold_converter.cpp — aRGus NDR, Pieza 2 (host bronce -> oro Parquet)
// Authors: Alonso Isidoro Roman + Claude (Anthropic)
//
// CIRCUITO HOST = ISLA. NO enlaza correlation_engine ni la lib de red; NO usa AVRO ni
// libsodium (el event_id wz1: ya viene minteado en la col 2 del bronce -> solo se copia).
// Lee el bronce host_domain_v1 (CSV sellado, 34 cols), VERIFICA el HMAC por fila (puerta
// Vía Appia: el oro solo nace de bronce cuya integridad se comprobó) y escribe oro Parquet
// = proyección RECTA de las 34 cols, sin enriquecido (host no tiene ventana). Las 10
// columnas-lista se preservan como string JSON tal cual (opción a, DAY 244); el re-modelado
// a aristas Rule->MitreTechnique es trabajo del loader (Pieza 3), no de aquí.
//
// USO: host_bronze_to_gold_converter <bronce.csv> <oro.parquet>
//      Requiere env ARGUS_BRONZE_HMAC_KEY_HEX (64 hex = 32 bytes), la MISMA clave con la
//      que el wazuh-adapter selló el bronce (toy key en mitre-start).
//
// CONTRATO host_domain_v1 (34 cols): 0-32 datos + 33 HMAC-SHA256 sobre 0-32.
// Todas string salvo col 11 rule_level (int32, único entero del contrato).

#include <arrow/api.h>
#include <arrow/io/api.h>
#include <parquet/arrow/writer.h>

#include <openssl/hmac.h>
#include <openssl/evp.h>

#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace {

constexpr int kTotalCols    = 34;  // 0-33
constexpr int kDataCols     = 33;  // 0-32 (preimagen del HMAC)
constexpr int kRuleLevelIdx = 11;

[[noreturn]] void die(const std::string& msg) {
    std::cerr << "ERROR: " << msg << "\n";
    std::exit(1);
}

std::vector<uint8_t> hex_decode_key(const std::string& hex) {
    if (hex.size() != 64) {
        die("ARGUS_BRONZE_HMAC_KEY_HEX debe ser 64 hex chars (32 bytes), obtenido "
            + std::to_string(hex.size()));
    }
    auto nib = [](char c) -> int {
        if (c >= '0' && c <= '9') return c - '0';
        if (c >= 'a' && c <= 'f') return c - 'a' + 10;
        if (c >= 'A' && c <= 'F') return c - 'A' + 10;
        return -1;
    };
    std::vector<uint8_t> out(32);
    for (size_t i = 0; i < 32; ++i) {
        int hi = nib(hex[2 * i]);
        int lo = nib(hex[2 * i + 1]);
        if (hi < 0 || lo < 0) die("ARGUS_BRONZE_HMAC_KEY_HEX contiene un carácter no-hex");
        out[i] = static_cast<uint8_t>((hi << 4) | lo);
    }
    return out;
}

// HMAC-SHA256(key, msg) -> hex minúsculo.
std::string hmac_sha256_hex(const std::vector<uint8_t>& key, const std::string& msg) {
    unsigned char mac[EVP_MAX_MD_SIZE];
    unsigned int mac_len = 0;
    if (HMAC(EVP_sha256(), key.data(), static_cast<int>(key.size()),
             reinterpret_cast<const unsigned char*>(msg.data()), msg.size(),
             mac, &mac_len) == nullptr) {
        die("HMAC() de OpenSSL falló");
    }
    static const char* h = "0123456789abcdef";
    std::string out;
    out.reserve(mac_len * 2);
    for (unsigned int i = 0; i < mac_len; ++i) {
        out.push_back(h[mac[i] >> 4]);
        out.push_back(h[mac[i] & 0x0F]);
    }
    return out;
}

bool ieq(const std::string& a, const std::string& b) {
    if (a.size() != b.size()) return false;
    auto low = [](char c) { return (c >= 'A' && c <= 'Z') ? char(c - 'A' + 'a') : c; };
    for (size_t i = 0; i < a.size(); ++i)
        if (low(a[i]) != low(b[i])) return false;
    return true;
}

// Parseo CSV quote-aware de UN registro (sin newline embebido: el newline-guard del
// contrato lo garantiza -> 1 fila = 1 línea física). RFC4180: campo con coma/comilla
// va entrecomillado, comilla interna doblada.
std::vector<std::string> parse_csv_record(const std::string& s) {
    std::vector<std::string> fields;
    std::string cur;
    bool in_quotes = false;
    const size_t n = s.size();
    for (size_t i = 0; i < n; ++i) {
        char c = s[i];
        if (in_quotes) {
            if (c == '"') {
                if (i + 1 < n && s[i + 1] == '"') { cur.push_back('"'); ++i; }
                else in_quotes = false;                 // comilla de cierre
            } else {
                cur.push_back(c);
            }
        } else {
            if (c == '"' && cur.empty()) in_quotes = true;   // apertura solo a inicio de campo
            else if (c == ',') { fields.push_back(cur); cur.clear(); }
            else cur.push_back(c);
        }
    }
    fields.push_back(cur);                                   // último campo
    return fields;
}

struct Counters {
    long leidas = 0, escritas = 0;
    long err_sin_hmac = 0, err_hmac = 0, err_cols = 0, err_rule_level = 0;
    long descartadas() const { return err_sin_hmac + err_hmac + err_cols + err_rule_level; }
};

// Cada fila válida -> 34 celdas (0-32 des-escapadas + 33 hmac hex).
std::vector<std::vector<std::string>> read_and_verify(
        const std::string& path, const std::vector<uint8_t>& key, Counters& c) {
    std::ifstream in(path, std::ios::binary);
    if (!in) die("no se pudo abrir el bronce: " + path);

    std::vector<std::vector<std::string>> rows;
    std::string line;
    while (std::getline(in, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();   // CRLF defensivo
        if (line.empty()) continue;
        ++c.leidas;

        // Puerta HMAC: rsplit en la ÚLTIMA coma. col 33 (hmac hex) no tiene comas ->
        // el último separador es siempre la frontera col32|col33. La preimagen son los
        // bytes EXACTOS de cols 0-32 tal cual en disco (la forma que se selló).
        auto pos = line.rfind(',');
        if (pos == std::string::npos) { ++c.err_sin_hmac; continue; }
        std::string preimage = line.substr(0, pos);
        std::string hmac_hex = line.substr(pos + 1);

        if (!ieq(hmac_sha256_hex(key, preimage), hmac_hex)) { ++c.err_hmac; continue; }

        // Solo tras verificar la integridad se parsea la preimagen en 33 celdas.
        std::vector<std::string> cells = parse_csv_record(preimage);
        if (static_cast<int>(cells.size()) != kDataCols) { ++c.err_cols; continue; }

        // col 11 rule_level debe ser entero (validate() lo garantizó en escritura; el
        // HMAC confirma bytes auténticos -> esto es defensa en profundidad).
        try {
            size_t consumed = 0;
            (void)std::stoi(cells[kRuleLevelIdx], &consumed);
            if (consumed != cells[kRuleLevelIdx].size()) { ++c.err_rule_level; continue; }
        } catch (...) { ++c.err_rule_level; continue; }

        cells.push_back(hmac_hex);              // col 33
        rows.push_back(std::move(cells));
        ++c.escritas;
    }
    return rows;
}

// Oro Parquet: 34 cols, todas utf8 salvo col 11 int32.
void write_gold_parquet(const std::string& path,
                        const std::vector<std::vector<std::string>>& rows) {
    static const char* kNames[kTotalCols] = {
        "schema_version", "source_sensor", "event_id", "host_id", "wazuh_alert_id",
        "timestamp", "agent_id", "agent_name", "agent_ip", "os_hostname",
        "rule_id", "rule_level", "rule_description", "rule_groups", "decoder_name",
        "location", "full_log", "data_json", "srcuser", "dstuser",
        "srcip", "srcport", "uid", "command", "mitre_ids",
        "mitre_tactics", "mitre_techniques", "pci_dss", "gdpr", "hipaa",
        "nist_800_53", "tsc", "gpg13", "hmac_row"
    };

    auto ok = [](const arrow::Status& s) {
        if (!s.ok()) die("Arrow Append/Finish falló: " + s.ToString());
    };

    std::vector<std::shared_ptr<arrow::Array>> arrays(kTotalCols);
    std::vector<std::shared_ptr<arrow::Field>> fields;
    fields.reserve(kTotalCols);

    for (int col = 0; col < kTotalCols; ++col) {
        std::shared_ptr<arrow::Array> arr;
        if (col == kRuleLevelIdx) {
            arrow::Int32Builder b;
            for (const auto& r : rows) ok(b.Append(static_cast<int32_t>(std::stoi(r[col]))));
            ok(b.Finish(&arr));
            fields.push_back(arrow::field(kNames[col], arrow::int32()));
        } else {
            arrow::StringBuilder b;
            for (const auto& r : rows) ok(b.Append(r[col]));
            ok(b.Finish(&arr));
            fields.push_back(arrow::field(kNames[col], arrow::utf8()));
        }
        arrays[col] = arr;
    }

    auto schema = arrow::schema(fields);
    auto table  = arrow::Table::Make(schema, arrays);

    auto maybe_out = arrow::io::FileOutputStream::Open(path);
    if (!maybe_out.ok()) die("FileOutputStream::Open falló: " + maybe_out.status().ToString());
    auto st = parquet::arrow::WriteTable(*table, arrow::default_memory_pool(), *maybe_out, 1024);
    if (!st.ok()) die("parquet::arrow::WriteTable falló: " + st.ToString());
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "USO: " << argv[0] << " <bronce.csv> <oro.parquet>\n";
        return 2;
    }
    const std::string in_path  = argv[1];
    const std::string out_path = argv[2];

    const char* key_hex = std::getenv("ARGUS_BRONZE_HMAC_KEY_HEX");
    if (!key_hex) die("ARGUS_BRONZE_HMAC_KEY_HEX no definida");
    std::vector<uint8_t> key = hex_decode_key(key_hex);

    Counters c;
    auto rows = read_and_verify(in_path, key, c);

    if (c.escritas == 0) {
        die("cero filas válidas (leidas=" + std::to_string(c.leidas)
            + " descartadas=" + std::to_string(c.descartadas()) + ")");
    }

    write_gold_parquet(out_path, rows);

    std::cout << "[host-bronze-to-gold]"
              << " leidas="      << c.leidas
              << " escritas="    << c.escritas
              << " descartadas=" << c.descartadas()
              << " (sin_hmac="   << c.err_sin_hmac
              << " hmac="        << c.err_hmac
              << " cols="        << c.err_cols
              << " rule_level="  << c.err_rule_level << ")\n"
              << " salida: " << out_path << "\n";
    return 0;
}