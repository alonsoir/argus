// ============================================================================
// plugin_loader.cpp — ML Defender Plugin Loader Implementation
// ============================================================================
// dlopen/dlsym lazy loading + Ed25519 verification (ADR-025 PHASE 2).
// Verificacion: prefix check + O_NOFOLLOW + fstat + SHA-256 + Ed25519 + /proc/self/fd
// ============================================================================

#include "plugin_loader/plugin_loader.hpp"
#include <dlfcn.h>
#include <sodium.h>      // ADR-025: Ed25519 + SHA-256
#include <fcntl.h>       // ADR-025: O_NOFOLLOW, O_CLOEXEC
#include <sys/stat.h>    // ADR-025: fstat, S_ISREG
#include <unistd.h>      // ADR-025: read, close
#include <chrono>
#include <stdexcept>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <iostream>
#include <set>
#include <tuple>
// Enterprise token validation (ADR-044 DAY 161 PASO 1)
// Solo se incluye si ARGUS_VAULT_ENABLED — en community, TokenValidator no se llama
#ifdef ARGUS_VAULT_ENABLED
#include "enterprise/token/TokenValidator.hpp"
#endif

// Minimal JSON parsing — evitamos dependencia de nlohmann aquí.
// El componente host ya tiene nlohmann; usamos una lectura simple
// basada en buscar la clave "plugins" en el JSON raw.
// Para PHASE 2 con seed-client se migrará a nlohmann completo.

namespace ml_defender {

// ----------------------------------------------------------------------------
// LoadedPlugin — internal representation of a loaded plugin
// ----------------------------------------------------------------------------
struct PluginLoader::LoadedPlugin {
    void*         handle   = nullptr;

    // Resolved symbols
    const char*  (*fn_name)()            = nullptr;
    const char*  (*fn_version)()         = nullptr;
    int          (*fn_api_version)()     = nullptr;
    PluginResult (*fn_init)(const PluginConfig*) = nullptr;
    PluginResult (*fn_process)(PacketContext*)         = nullptr;
    PluginResult (*fn_process_message)(MessageContext*) = nullptr;  // ADR-023 PHASE 2a — opcional
    void         (*fn_shutdown)()                       = nullptr;

    std::string   name;

    ~LoadedPlugin() {
        if (handle) {
            dlclose(handle);
            handle = nullptr;
        }
    }
};

// ----------------------------------------------------------------------------
// Simple helpers
// ----------------------------------------------------------------------------
static std::string read_file(const std::string& path) {
    std::ifstream f(path);
    if (!f.is_open()) return "";
    std::ostringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

// Minimal extraction of a string value from flat JSON.
// Only used to read plugins.directory and plugins.budget_us.
// Full JSON parsing delegated to component host.
static std::string json_string_value(const std::string& json, const std::string& key) {
    auto pos = json.find("\"" + key + "\"");
    if (pos == std::string::npos) return "";
    pos = json.find(":", pos);
    if (pos == std::string::npos) return "";
    pos = json.find("\"", pos);
    if (pos == std::string::npos) return "";
    auto end = json.find("\"", pos + 1);
    if (end == std::string::npos) return "";
    return json.substr(pos + 1, end - pos - 1);
}

static uint32_t json_uint_value(const std::string& json, const std::string& key, uint32_t def) {
    auto pos = json.find("\"" + key + "\"");
    if (pos == std::string::npos) return def;
    pos = json.find(":", pos);
    if (pos == std::string::npos) return def;
    // skip whitespace
    while (pos < json.size() && (json[pos] == ':' || json[pos] == ' ')) ++pos;
    try { return static_cast<uint32_t>(std::stoul(json.substr(pos))); }
    catch (...) { return def; }
}

// Extract the "plugins" JSON block as a string
static std::string extract_plugins_block(const std::string& json) {
    auto pos = json.find("\"plugins\"");
    if (pos == std::string::npos) return "";
    pos = json.find("{", pos);
    if (pos == std::string::npos) return "";
    int depth = 0;
    size_t start = pos;
    for (size_t i = pos; i < json.size(); ++i) {
        if (json[i] == '{') ++depth;
        else if (json[i] == '}') { --depth; if (depth == 0) return json.substr(start, i - start + 1); }
    }
    return "";
}

// Extract enabled plugin descriptors from "enabled": [{name, path, active, ...}]
// Returns pairs of {name, path} for entries where active==true only.
static std::vector<std::tuple<std::string,std::string,bool,std::string>>
extract_enabled_objects(const std::string& plugins_block) {
    // (name, so_path, is_enterprise, token_path)
    std::vector<std::tuple<std::string,std::string,bool,std::string>> result;
    auto pos = plugins_block.find("\"enabled\"");
    if (pos == std::string::npos) return result;
    pos = plugins_block.find("[", pos);
    if (pos == std::string::npos) return result;

    // Walk each object {...} inside the array
    for (size_t i = pos + 1; i < plugins_block.size(); ++i) {
        if (plugins_block[i] == ']') break;
        if (plugins_block[i] != '{') continue;

        // Extract the object substring
        int depth = 0; size_t obj_start = i;
        std::string obj;
        for (size_t j = i; j < plugins_block.size(); ++j) {
            if (plugins_block[j] == '{') ++depth;
            else if (plugins_block[j] == '}') {
                --depth;
                if (depth == 0) { obj = plugins_block.substr(obj_start, j - obj_start + 1); i = j; break; }
            }
        }
        if (obj.empty()) continue;

        // active must be true
        auto act_pos = obj.find("\"active\"");
        if (act_pos == std::string::npos) continue;
        auto colon = obj.find(":", act_pos);
        if (colon == std::string::npos) continue;
        size_t vstart = colon + 1;
        while (vstart < obj.size() && obj[vstart] == ' ') ++vstart;
        if (obj.substr(vstart, 4) != "true") continue;

        // Extract name
        std::string name = json_string_value(obj, "name");
        if (name.empty()) continue;

        // Extract path (explicit .so path from JSON)
        std::string so_path = json_string_value(obj, "path");
        if (so_path.empty()) continue;

        std::string ent_flag  = json_string_value(obj, "enterprise");
        std::string tok_path   = json_string_value(obj, "enterprise_token_path");
        bool is_enterprise = (ent_flag == "true");
        result.push_back({name, so_path, is_enterprise, tok_path});
    }
    return result;
}

// ----------------------------------------------------------------------------
// PluginLoader implementation
// ----------------------------------------------------------------------------
PluginLoader::PluginLoader(const std::string& config_json_path)
    : config_path_(config_json_path) {}

PluginLoader::~PluginLoader() {
    if (!shutdown_called_) {
        shutdown();
    }
}


// ============================================================================
// verify_plugin_signature — ADR-025 Ed25519 + TOCTOU-safe dlopen
// D1: Ed25519 offline, D2: O_NOFOLLOW+fstat+size, D3: prefix check,
// D4: fd discipline, D5: .sig fd, D6: SHA-256 forense, D7: pubkey hardcoded,
// D9: fail-closed std::terminate() si require_signature=true
// Retorna fd_so abierto (caller cierra tras dlopen) o -1 en dev mode
// ============================================================================

static constexpr size_t MIN_PLUGIN_SIZE = 4096;
static constexpr size_t MAX_PLUGIN_SIZE = 10 * 1024 * 1024;
static constexpr size_t MAX_SIG_SIZE    = 512;
static const std::string ALLOWED_PREFIX = "/usr/lib/ml-defender/plugins/";

static bool hex_to_bytes(const std::string& hex, unsigned char* out, size_t expected_len) {
    if (hex.size() != expected_len * 2) return false;
    for (size_t i = 0; i < expected_len; ++i) {
        try { out[i] = static_cast<unsigned char>(std::stoi(hex.substr(i*2, 2), nullptr, 16)); }
        catch (...) { return false; }
    }
    return true;
}

static int verify_plugin_signature(const std::string& so_path,
                                   const std::string& sig_path,
                                   bool require_signature,
                                   const std::string& plugin_name) {
    namespace fs = std::filesystem;

    // D3: prefix check ANTES de open()
    auto canon_so  = fs::weakly_canonical(so_path);
    auto canon_sig = fs::weakly_canonical(sig_path);
    if (canon_so.string().substr(0, ALLOWED_PREFIX.size())  != ALLOWED_PREFIX ||
        canon_sig.string().substr(0, ALLOWED_PREFIX.size()) != ALLOWED_PREFIX) {
        std::cerr << "[plugin-loader] CRITICAL: path outside allowed prefix: " << so_path << "\n";
        if (require_signature) std::terminate();
        return -1;
    }

    // D2: open .so con O_NOFOLLOW
    int fd_so = open(so_path.c_str(), O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
    if (fd_so < 0) {
        std::cerr << "[plugin-loader] CRITICAL: cannot open plugin (symlink?): " << so_path << "\n";
        if (require_signature) std::terminate();
        return -1;
    }
    struct stat st_so;
    if (fstat(fd_so, &st_so) < 0 || !S_ISREG(st_so.st_mode) ||
        st_so.st_size < static_cast<off_t>(MIN_PLUGIN_SIZE) ||
        st_so.st_size > static_cast<off_t>(MAX_PLUGIN_SIZE)) {
        std::cerr << "[plugin-loader] CRITICAL: plugin size/type invalid: " << so_path << "\n";
        close(fd_so);
        if (require_signature) std::terminate();
        return -1;
    }

    // D5: open .sig con O_NOFOLLOW
    int fd_sig = open(sig_path.c_str(), O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
    if (fd_sig < 0) {
        std::cerr << "[plugin-loader] CRITICAL: .sig not found for '" << plugin_name << "'\n";
        close(fd_so);
        if (require_signature) std::terminate();
        return -1;
    }
    struct stat st_sig;
    if (fstat(fd_sig, &st_sig) < 0 || !S_ISREG(st_sig.st_mode) ||
        st_sig.st_size > static_cast<off_t>(MAX_SIG_SIZE) || st_sig.st_size < 64) {
        std::cerr << "[plugin-loader] CRITICAL: .sig size invalid: " << sig_path << "\n";
        close(fd_so); close(fd_sig);
        if (require_signature) std::terminate();
        return -1;
    }

    // D4: leer .so desde fd
    std::vector<unsigned char> so_buf(static_cast<size_t>(st_so.st_size));
    if (read(fd_so, so_buf.data(), so_buf.size()) != static_cast<ssize_t>(so_buf.size())) {
        std::cerr << "[plugin-loader] CRITICAL: read error: " << so_path << "\n";
        close(fd_so); close(fd_sig);
        if (require_signature) std::terminate();
        return -1;
    }

    // Leer .sig desde fd
    std::vector<unsigned char> sig_buf(static_cast<size_t>(st_sig.st_size));
    if (read(fd_sig, sig_buf.data(), sig_buf.size()) != static_cast<ssize_t>(sig_buf.size())) {
        std::cerr << "[plugin-loader] CRITICAL: read error: " << sig_path << "\n";
        close(fd_so); close(fd_sig);
        if (require_signature) std::terminate();
        return -1;
    }
    close(fd_sig);

    // D6: SHA-256 forense
    unsigned char sha256[crypto_hash_sha256_BYTES];
    crypto_hash_sha256(sha256, so_buf.data(), so_buf.size());
    char sha256_hex[crypto_hash_sha256_BYTES * 2 + 1];
    for (size_t i = 0; i < crypto_hash_sha256_BYTES; ++i)
        snprintf(sha256_hex + i*2, 3, "%02x", sha256[i]);
    std::cerr << "[plugin-loader] INFO: '" << plugin_name
              << "' SHA-256=" << sha256_hex
              << " size=" << st_so.st_size
              << " mtime=" << st_so.st_mtime << "\n";

    // D7: pubkey hardcodeada en binario via CMake
    static const std::string PUBKEY_HEX = MLD_PLUGIN_PUBKEY_HEX;
    unsigned char pubkey[crypto_sign_PUBLICKEYBYTES];
    if (!hex_to_bytes(PUBKEY_HEX, pubkey, crypto_sign_PUBLICKEYBYTES)) {
        std::cerr << "[plugin-loader] CRITICAL: MLD_PLUGIN_PUBKEY_HEX malformed\n";
        close(fd_so);
        std::terminate();
    }

    // D1: verificacion Ed25519
    if (sig_buf.size() != crypto_sign_BYTES) {
        std::cerr << "[plugin-loader] CRITICAL: .sig wrong size " << sig_buf.size() << "\n";
        close(fd_so);
        if (require_signature) std::terminate();
        return -1;
    }
    if (crypto_sign_verify_detached(sig_buf.data(), so_buf.data(), so_buf.size(), pubkey) != 0) {
        std::cerr << "[plugin-loader] CRITICAL: Ed25519 INVALID for '" << plugin_name << "'\n";
        close(fd_so);
        if (require_signature) std::terminate();
        return -1;
    }

    std::cerr << "[plugin-loader] INFO: '" << plugin_name << "' signature OK\n";
    return fd_so;
}

void PluginLoader::load_plugins() {
    std::string raw = read_file(config_path_);
    if (raw.empty()) {
        std::cerr << "[plugin-loader] WARNING: cannot read config: " << config_path_ << "\n";
        return;
    }

    std::string plugins_block = extract_plugins_block(raw);
    if (plugins_block.empty()) {
        std::cerr << "[plugin-loader] INFO: no 'plugins' section in " << config_path_ << " — no plugins loaded\n";
        return;
    }

    std::string directory = json_string_value(plugins_block, "directory");
    if (directory.empty()) directory = "/usr/lib/ml-defender/plugins";

    budget_us_ = json_uint_value(plugins_block, "budget_us", 100);

    auto enabled = extract_enabled_objects(plugins_block);
    if (enabled.empty()) {
        std::cerr << "[plugin-loader] INFO: plugins.enabled is empty — no plugins loaded\n";
        return;
    }

    for (const auto& [plugin_name, so_path, is_enterprise, token_path] : enabled) {

        // ADR-025: require_signature=true produccion, false con MLD_ALLOW_DEV_MODE=1
        bool require_sig = true;
        const char* dev_mode = std::getenv("MLD_ALLOW_DEV_MODE");
        if (dev_mode && std::string(dev_mode) == "1") require_sig = false;

        std::string sig_path = so_path + ".sig";
        int fd_so = verify_plugin_signature(so_path, sig_path, require_sig, plugin_name);
        if (fd_so < 0) {
            std::cerr << "[plugin-loader] WARNING: '" << plugin_name
                      << "' skipped (sig check failed, dev mode)\n";
            continue;
        }

        // PASO 1 DAY 161 — Enterprise token validation (ADR-044)
        // Si el plugin es enterprise, validar token ANTES de dlopen.
        // Fail-closed: abort() si token inválido, expirado o feature ausente.
#ifdef ARGUS_VAULT_ENABLED
        {
            if (is_enterprise) {
                std::string eff_token_path = token_path.empty()
                    ? "/etc/ml-defender/enterprise.token" : token_path;
                argus::enterprise::TokenValidator::validate_or_abort(
                    eff_token_path,
                    ARGUS_ENTERPRISE_PUBKEY_HEX,
                    {"vault_crypto"}
                );
            }
        }
#endif
        // D4: dlopen via /proc/self/fd/ — nunca volver al path en disco
        std::string fd_path = "/proc/self/fd/" + std::to_string(fd_so);
        void* handle = dlopen(fd_path.c_str(), RTLD_LAZY | RTLD_LOCAL);
        close(fd_so); // cerrar DESPUES de dlopen (D4)
        if (!handle) {
            std::cerr << "[plugin-loader] WARNING: dlopen failed for '" << plugin_name
                      << "': " << dlerror() << " â skipping\n";
            continue;
        }

        auto plugin = std::make_shared<LoadedPlugin>();
        plugin->handle = handle;

        // Resolve mandatory symbols
        #define RESOLVE(sym, type, field) \
            plugin->field = reinterpret_cast<type>(dlsym(handle, #sym)); \
            if (!plugin->field) { \
                std::cerr << "[plugin-loader] WARNING: symbol '" #sym "' not found in '" \
                          << plugin_name << "' — skipping\n"; \
                goto skip_plugin; \
            }

        RESOLVE(plugin_name,           const char*(*)(void),          fn_name)
        RESOLVE(plugin_version,        const char*(*)(void),          fn_version)
        RESOLVE(plugin_api_version,    int(*)(void),                  fn_api_version)
        RESOLVE(plugin_init,           PluginResult(*)(const PluginConfig*), fn_init)
        RESOLVE(plugin_process_packet, PluginResult(*)(PacketContext*),      fn_process)
        RESOLVE(plugin_shutdown,       void(*)(void),                 fn_shutdown)
        #undef RESOLVE

        // API version check
        if (plugin->fn_api_version() != PLUGIN_API_VERSION) {
            std::cerr << "[plugin-loader] WARNING: plugin '" << plugin_name
                      << "' API version mismatch (got " << plugin->fn_api_version()
                      << ", expected " << PLUGIN_API_VERSION << ") — skipping\n";
            goto skip_plugin;
        }

        // Call init
        {
            // Extract plugin-specific config JSON section
            std::string plugin_cfg = "{}";
            auto cfg_pos = plugins_block.find("\"" + plugin_name + "\"");
            if (cfg_pos != std::string::npos) {
                auto brace = plugins_block.find("{", cfg_pos);
                if (brace != std::string::npos) {
                    int depth = 0; size_t start = brace;
                    for (size_t i = brace; i < plugins_block.size(); ++i) {
                        if (plugins_block[i] == '{') ++depth;
                        else if (plugins_block[i] == '}') {
                            --depth;
                            if (depth == 0) { plugin_cfg = plugins_block.substr(start, i - start + 1); break; }
                        }
                    }
                }
            }

            PluginConfig cfg;
            cfg.name        = plugin_name.c_str();
            cfg.config_json = plugin_cfg.c_str();

            PluginResult r = plugin->fn_init(&cfg);
            if (r != PLUGIN_OK) {
                std::cerr << "[plugin-loader] WARNING: plugin_init() failed for '"
                          << plugin_name << "' (result=" << r << ") — skipping\n";
                goto skip_plugin;
            }
        }

        // Resolución opcional de plugin_process_message (ADR-023 D1 Graceful Degradation)
        plugin->fn_process_message = reinterpret_cast<PluginResult(*)(MessageContext*)>(
            dlsym(handle, "plugin_process_message"));
        if (!plugin->fn_process_message) {
            std::cerr << "[plugin-loader] INFO: plugin '" << plugin_name
                      << "' no exporta plugin_process_message — Graceful Degradation D1 aplicada\n";
        }

        plugin->name = plugin->fn_name();
        plugins_.push_back(plugin);
        stats_.push_back(PluginStats{plugin->name, 0, 0, 0});
        std::cerr << "[plugin-loader] INFO: loaded plugin '" << plugin->name
                  << "' v" << plugin->fn_version() << "\n";
        continue;

        skip_plugin:
        dlclose(handle);
        plugin->handle = nullptr;
    }
}

void PluginLoader::invoke_all(PacketContext& ctx) {
    for (size_t i = 0; i < plugins_.size(); ++i) {
        auto& p = plugins_[i];
        auto  t0 = std::chrono::steady_clock::now();

        PluginResult r = p->fn_process(&ctx);

        auto elapsed_us = std::chrono::duration_cast<std::chrono::microseconds>(
            std::chrono::steady_clock::now() - t0).count();

        stats_[i].invocations++;

        if (r == PLUGIN_ERROR) {
            stats_[i].errors++;
            std::cerr << "[plugin-loader] WARNING: plugin '" << p->name
                      << "' returned PLUGIN_ERROR\n";
        }

        if (static_cast<uint32_t>(elapsed_us) > budget_us_) {
            stats_[i].budget_overruns++;
            std::cerr << "[plugin-loader] WARNING: plugin '" << p->name
                      << "' overrun: " << elapsed_us << "us > " << budget_us_ << "us budget\n";
        }
    }
}

void PluginLoader::shutdown() {
    for (size_t i = 0; i < plugins_.size(); ++i) {
        auto& p = plugins_[i];
        if (p && p->fn_shutdown) {
            p->fn_shutdown();
        }
        std::cerr << "[plugin-loader] INFO: shutdown plugin '" << p->name
                  << "' — invocations=" << stats_[i].invocations
                  << " overruns=" << stats_[i].budget_overruns
                  << " errors=" << stats_[i].errors << "\n";
    }
    plugins_.clear();
    shutdown_called_ = true;
}

const std::vector<PluginStats>& PluginLoader::stats() const { return stats_; }
size_t PluginLoader::loaded_count() const { return plugins_.size(); }

void PluginLoader::invoke_all(MessageContext& ctx) {
    for (size_t i = 0; i < plugins_.size(); ++i) {
        auto& p = plugins_[i];

        // D1 Graceful Degradation: si no exporta el símbolo, skip silencioso
        if (!p->fn_process_message) continue;
        // D8-pre: validacion de coherencia mode (Q1 Consejo DAY 109)
        // PLUGIN_MODE_READONLY garantiza payload=nullptr. Violacion = terminate().
        if (ctx.mode == PLUGIN_MODE_READONLY &&
            (ctx.payload != nullptr || ctx.payload_len != 0)) {
            std::cerr << "[plugin-loader] SECURITY: PLUGIN_MODE_READONLY violado "
                      << "payload no es nullptr antes de invocar plugin '"
                      << p->name << "' std::terminate()\n";
            std::terminate();
        }

        // D8-pre inverso (FIX-C, Consejo DAY 110 — ChatGPT5 obligatorio)
        // PLUGIN_MODE_NORMAL garantiza payload presente. payload==nullptr = violacion.
        if (ctx.mode == PLUGIN_MODE_NORMAL &&
            (ctx.payload == nullptr || ctx.payload_len == 0)) {
            std::cerr << "[plugin-loader] SECURITY: PLUGIN_MODE_NORMAL violado — "
                      << "payload es nullptr antes de invocar plugin '"
                      << p->name << "' — std::terminate()\n";
            std::terminate();
        }
        // D8-pre size limit (FIX-D, Consejo DAY 110 — ChatGPT5 obligatorio)
        if (ctx.payload != nullptr && ctx.payload_len > MAX_PLUGIN_PAYLOAD_SIZE) {
            std::cerr << "[plugin-loader] SECURITY: payload_len=" << ctx.payload_len
                      << " excede MAX_PLUGIN_PAYLOAD_SIZE=" << MAX_PLUGIN_PAYLOAD_SIZE
                      << " — std::terminate()\n";
            std::terminate();
        }
        // D8: snapshot de campos read-only antes de invocar el plugin
        const uint8_t* snap_payload   = ctx.payload;
        size_t         snap_len        = ctx.payload_len;
        uint32_t       snap_src_ip     = ctx.src_ip;
        uint32_t       snap_dst_ip     = ctx.dst_ip;
        uint16_t       snap_src_port   = ctx.src_port;
        uint16_t       snap_dst_port   = ctx.dst_port;
        uint8_t        snap_protocol   = ctx.protocol;
        uint8_t        snap_direction  = ctx.direction;
        uint8_t        snap_mode       = ctx.mode;
        const uint8_t* snap_nonce      = ctx.nonce;
        const uint8_t* snap_tag        = ctx.tag;

        auto t0 = std::chrono::steady_clock::now();
        PluginResult r = p->fn_process_message(&ctx);
        auto elapsed_us = std::chrono::duration_cast<std::chrono::microseconds>(
            std::chrono::steady_clock::now() - t0).count();

        // D8: post-invocation validation — byte-wise comparison de campos read-only
        bool invariant_ok =
            (ctx.payload    == snap_payload)  &&
            (ctx.payload_len == snap_len)     &&
            (ctx.src_ip     == snap_src_ip)   &&
            (ctx.dst_ip     == snap_dst_ip)   &&
            (ctx.src_port   == snap_src_port) &&
            (ctx.dst_port   == snap_dst_port) &&
            (ctx.protocol   == snap_protocol) &&
            (ctx.direction  == snap_direction)&&
            (ctx.nonce      == snap_nonce)    &&
            (ctx.tag        == snap_tag)        &&
            (ctx.mode       == snap_mode);

        if (!invariant_ok) {
            std::cerr << "[plugin-loader] SECURITY: plugin '" << p->name
                      << "' modificó campos read-only en MessageContext — D8 VIOLATION\n";
            stats_[i].errors++;
            // D1 fail-closed: se registra el error; en PHASE 2 el plugin será descargado.
            // En DEV_MODE (MLD_ALLOW_DEV_MODE): solo warning, no se aborta.
        }

        stats_[i].invocations++;

        if (r == PLUGIN_ERROR) {
            stats_[i].errors++;
            std::cerr << "[plugin-loader] WARNING: plugin '" << p->name
                      << "' returned PLUGIN_ERROR en MessageContext\n";
        }

        if (static_cast<uint32_t>(elapsed_us) > budget_us_) {
            stats_[i].budget_overruns++;
            std::cerr << "[plugin-loader] WARNING: plugin '" << p->name
                      << "' overrun: " << elapsed_us << "us > " << budget_us_ << "us budget\n";
        }
    }
}


}  // namespace ml_defender
