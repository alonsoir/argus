#include "seed_client/seed_client.hpp"
#include <safe_path/safe_path.hpp>

#include <nlohmann/json.hpp>

#include <fstream>
#include <sstream>
#include <stdexcept>
#include <sys/stat.h>

// explicit_bzero está en string.h en Linux (glibc 2.25+)
// En sistemas sin él, usamos la barrera de compilador equivalente
#if defined(__linux__)
#  include <string.h>   // explicit_bzero
#elif defined(__APPLE__)
#  include <string.h>
#  ifndef explicit_bzero
     // macOS < 10.12 no tiene explicit_bzero — fallback seguro
     static void explicit_bzero(void* s, size_t n) {
         volatile unsigned char* p = static_cast<volatile unsigned char*>(s);
         while (n--) *p++ = 0;
     }
#  endif
#endif

namespace ml_defender {

// ─── Constructor / Destructor ─────────────────────────────────────────────────

SeedClient::SeedClient(const std::string& component_json_path)
    : component_json_path_(component_json_path)
{
}

SeedClient::~SeedClient() {
    // Limpiar el seed de memoria al destruir el objeto
    explicit_bzero(seed_.data(), seed_.size());
}

// ─── load() ───────────────────────────────────────────────────────────────────

void SeedClient::load() {
    // 1. Parsear JSON del componente
    std::ifstream json_file(component_json_path_);
    if (!json_file.is_open()) {
        throw std::runtime_error(
            "[SeedClient] No se puede abrir el JSON del componente: " +
            component_json_path_
        );
    }

    nlohmann::json config;
    try {
        json_file >> config;
    } catch (const nlohmann::json::parse_error& e) {
        throw std::runtime_error(
            "[SeedClient] Error parseando JSON '" + component_json_path_ +
            "': " + e.what()
        );
    }

    // 2. Leer identity.component_id y identity.keys_dir
    if (!config.contains("identity")) {
        throw std::runtime_error(
            "[SeedClient] El JSON no contiene el bloque 'identity': " +
            component_json_path_
        );
    }

    const auto& identity = config["identity"];

    if (!identity.contains("component_id")) {
        throw std::runtime_error(
            "[SeedClient] identity.component_id no encontrado en: " +
            component_json_path_
        );
    }
    if (!identity.contains("keys_dir")) {
        throw std::runtime_error(
            "[SeedClient] identity.keys_dir no encontrado en: " +
            component_json_path_
        );
    }

    component_id_ = identity["component_id"].get<std::string>();
    keys_dir_     = identity["keys_dir"].get<std::string>();

    // Normalizar: asegurar que keys_dir termina en '/'
    if (!keys_dir_.empty() && keys_dir_.back() != '/') {
        keys_dir_ += '/';
    }

    // 3. Construir path al seed.bin
    const std::string seed_path = keys_dir_ + "seed.bin";

    // 4+5. Validar path, permisos 0400, O_NOFOLLOW|O_CLOEXEC (ADR-037)
    {
        const int seed_fd = argus::safe_path::resolve_seed(seed_path, keys_dir_);
        ::close(seed_fd); // validación completada — ifstream abre por path
    }

    // 5. Abrir seed.bin en modo binario
    std::ifstream seed_file(seed_path, std::ios::binary);
    if (!seed_file.is_open()) {
        throw std::runtime_error(
            "[SeedClient] No se puede abrir seed.bin: " + seed_path +
            " — ¿ejecutaste 'make provision'?"
        );
    }

    // 6. Leer exactamente 32 bytes con buffer temporal
    std::array<uint8_t, 32> tmp_buf{};
    seed_file.read(reinterpret_cast<char*>(tmp_buf.data()), 32);

    const std::streamsize bytes_read = seed_file.gcount();

    if (bytes_read != 32) {
        // Limpiar buffer temporal antes de lanzar
        explicit_bzero(tmp_buf.data(), tmp_buf.size());
        throw std::runtime_error(
            "[SeedClient] seed.bin debe tener exactamente 32 bytes, "
            "encontrados: " + std::to_string(bytes_read) +
            " en: " + seed_path
        );
    }

    // Verificar que no hay más bytes (fichero corrupto / sobreescrito)
    {
        char extra;
        if (seed_file.read(&extra, 1) && seed_file.gcount() > 0) {
            explicit_bzero(tmp_buf.data(), tmp_buf.size());
            throw std::runtime_error(
                "[SeedClient] seed.bin contiene más de 32 bytes — "
                "fichero corrupto o generado incorrectamente: " + seed_path
            );
        }
    }

    // 7. Copiar al array permanente y limpiar el temporal
    seed_ = tmp_buf;
    explicit_bzero(tmp_buf.data(), tmp_buf.size());

    loaded_ = true;
}

// ─── Accesores ────────────────────────────────────────────────────────────────

const std::array<uint8_t, 32>& SeedClient::seed() const {
    if (!loaded_) {
        throw std::runtime_error(
            "[SeedClient] seed() llamado antes de load(). "
            "Llama a load() primero."
        );
    }
    return seed_;
}

bool SeedClient::is_loaded() const noexcept {
    return loaded_;
}

const std::string& SeedClient::component_id() const {
    if (!loaded_) {
        throw std::runtime_error(
            "[SeedClient] component_id() llamado antes de load()."
        );
    }
    return component_id_;
}

const std::string& SeedClient::keys_dir() const {
    if (!loaded_) {
        throw std::runtime_error(
            "[SeedClient] keys_dir() llamado antes de load()."
        );
    }
    return keys_dir_;
}

// ─── Helpers privados ─────────────────────────────────────────────────────────

void SeedClient::check_seed_permissions(const std::string& seed_path) const {
    struct stat st{};
    if (stat(seed_path.c_str(), &st) != 0) {
        // El fichero no existe o no es accesible — load() lanzará el error real
        return;
    }

    const mode_t perms = st.st_mode & 0777;
    if (perms != 0400) {
        // Advertencia — no es un error fatal, pero sí un problema de seguridad
        std::ostringstream oss;
        oss << "[SeedClient] ADVERTENCIA DE SEGURIDAD: seed.bin tiene permisos "
            << std::oct << perms << std::dec
            << " en lugar de 0400 (ADR-037). Path: " << seed_path
            << " — ejecuta: chmod 640 " << seed_path;
        // stderr para no contaminar stdout del pipeline
        fputs((oss.str() + "\n").c_str(), stderr);
    }
}

} // namespace ml_defender