// etcd-server/src/vault_secret_store.cpp — [ETCD-CLAVES-D314]
#include "etcd_server/vault_secret_store.hpp"
#include <httplib.h>
#include <algorithm>
#include <thread>

namespace argus::claves {

namespace {
std::string unir(const std::vector<std::string>& v) {
    std::string s;
    for (const auto& e : v) {
        if (!s.empty()) s += ',';
        s += e;
    }
    return s;
}
// Primeros 200 caracteres de un cuerpo de error de Vault, sin saltos de línea (los cuerpos de error no llevan claves)
std::string recorte(const std::string& s) {
    std::string r = s.substr(0, 200);
    std::replace(r.begin(), r.end(), '\n', ' ');
    return r;
}
}  // namespace

VaultSecretStore::VaultSecretStore(const argus::etcdcfg::AlmacenClavesConfig& cfg, std::ostream& log)
    : cfg_(cfg), log_(log) {
    descripcion_ = "Vault ";
    descripcion_ += unir(cfg.vault_addrs);
    descripcion_ += " (kv v2 ";
    descripcion_ += cfg.montaje;
    descripcion_ += "/, mTLS, auth cert rol ";
    descripcion_ += cfg.rol_login;
    descripcion_ += ")";
    for (const auto& u : cfg.vault_addrs) {  // ya validadas: "https://IPv4:puerto"
        Dir d;
        d.url = u;
        const std::string resto = u.substr(std::string("https://").size());
        const size_t dos = resto.rfind(':');
        d.host = resto.substr(0, dos);
        d.puerto = std::stoi(resto.substr(dos + 1));
        dirs_.push_back(d);
    }
}

bool VaultSecretStore::disponible() const {
    std::lock_guard<std::mutex> lk(m_);
    return disponible_;
}

std::string VaultSecretStore::ultimo_error() const {
    std::lock_guard<std::mutex> lk(m_);
    return ultimo_error_;
}

VaultSecretStore::Respuesta VaultSecretStore::pedir(size_t dir, const std::string& metodo, const std::string& ruta,
                                                     const std::string& cuerpo, bool con_token) {
    Respuesta r;
    const Dir& d = dirs_[dir];
    httplib::SSLClient cli(d.host, d.puerto, cfg_.cert_file, cfg_.key_file);
    cli.set_ca_cert_path(cfg_.ca_file.c_str());
    cli.enable_server_certificate_verification(true);
    const auto to = std::chrono::milliseconds(cfg_.timeout_ms);
    cli.set_connection_timeout(to);
    cli.set_read_timeout(to);
    cli.set_write_timeout(to);
    httplib::Headers h;
    if (con_token) h.emplace("X-Vault-Token", token_);
    httplib::Result res = metodo == "GET" ? cli.Get(ruta, h) : cli.Post(ruta, h, cuerpo, "application/json");
    if (!res) {
        r.error = httplib::to_string(res.error());
        if (res.ssl_error() != 0) {
            r.error += " (ssl ";
            r.error += std::to_string(res.ssl_error());
            r.error += ")";
        }
        return r;
    }
    r.status = res->status;
    r.cuerpo = res->body;
    return r;
}

bool VaultSecretStore::login(size_t dir, std::string& error) {
    const nlohmann::json body = {{"name", cfg_.rol_login}};
    Respuesta r = pedir(dir, "POST", "/v1/auth/cert/login", body.dump(), false);
    if (r.status != 200) {
        error = r.status == 0 ? r.error : ("login HTTP " + std::to_string(r.status) + " " + recorte(r.cuerpo));
        return false;
    }
    try {
        const auto j = nlohmann::json::parse(r.cuerpo);
        token_ = j.at("auth").at("client_token").get<std::string>();
        const int vida = j.at("auth").value("lease_duration", 0);
        token_dir_ = dir;
        // a la mitad de su vida (como poco 1 s) se renueva con un login nuevo
        token_renovar_ = std::chrono::steady_clock::now() + std::chrono::seconds(std::max(1, vida / 2));
        return true;
    } catch (const std::exception& e) {
        error = std::string("login: respuesta inesperada (") + e.what() + ")";
        return false;
    }
}

VaultSecretStore::Respuesta VaultSecretStore::operar(const std::string& metodo, const std::string& ruta,
                                                      const std::string& cuerpo) {
    const size_t n = dirs_.size();
    std::string detalle;
    for (size_t k = 0; k < n; ++k) {
        const size_t dir = (actual_ + k) % n;
        int espera = cfg_.espera_inicial_ms;
        std::string ultimo;
        for (int intento = 1; intento <= cfg_.reintentos_por_direccion; ++intento) {
            Respuesta r;
            bool relogin = false;
            for (;;) {
                if (token_.empty() || std::chrono::steady_clock::now() >= token_renovar_ || relogin) {
                    std::string e;
                    if (!login(dir, e)) {
                        r.status = 0;
                        r.error = e;
                        break;
                    }
                }
                r = pedir(dir, metodo, ruta, cuerpo, true);
                if (r.status == 403 && !relogin) {  // token caducado o revocado: un login nuevo, una vez
                    relogin = true;
                    continue;
                }
                break;
            }
            if (r.status != 0 && r.status < 500 && r.status != 429) {
                if (dir != actual_) {
                    log_ << "[ETCD-VAULT-CAMBIO] " << dirs_[actual_].url << " no respondía: se usa " << dirs_[dir].url
                         << std::endl;
                    actual_ = dir;
                }
                return r;
            }
            ultimo = r.status == 0 ? r.error : ("HTTP " + std::to_string(r.status) + " " + recorte(r.cuerpo));
            if (intento < cfg_.reintentos_por_direccion) {
                std::this_thread::sleep_for(std::chrono::milliseconds(espera));
                espera = std::min(espera * 2, cfg_.espera_max_ms);
            }
        }
        if (!detalle.empty()) detalle += "; ";
        detalle += dirs_[dir].url;
        detalle += ": ";
        detalle += ultimo;
        detalle += " (";
        detalle += std::to_string(cfg_.reintentos_por_direccion);
        detalle += " intentos)";
    }
    marcar_caido(detalle);
    return Respuesta{};
}

void VaultSecretStore::marcar_caido(const std::string& detalle) {
    disponible_ = false;
    ultimo_error_ = detalle;
    token_.clear();
}

Estado VaultSecretStore::leer(const std::string& ruta, nlohmann::json& datos, int& version) {
    std::lock_guard<std::mutex> lk(m_);
    if (!disponible_) return Estado::NoDisponible;
    std::string p = "/v1/";
    p += cfg_.montaje;
    p += "/data/";
    p += ruta;
    Respuesta r = operar("GET", p, "");
    if (r.status == 0) return Estado::NoDisponible;
    if (r.status == 404) return Estado::NoEncontrado;
    if (r.status != 200) {
        ultimo_error_ = "GET " + ruta + ": HTTP " + std::to_string(r.status) + " " + recorte(r.cuerpo);
        return Estado::NoDisponible;
    }
    try {
        const auto j = nlohmann::json::parse(r.cuerpo);
        datos = j.at("data").at("data");
        version = j.at("data").at("metadata").at("version").get<int>();
        return Estado::Ok;
    } catch (const std::exception& e) {
        ultimo_error_ = "GET " + ruta + ": respuesta inesperada (" + e.what() + ")";
        return Estado::NoDisponible;
    }
}

Estado VaultSecretStore::escribir(const std::string& ruta, const nlohmann::json& datos, int cas, int& version_nueva) {
    std::lock_guard<std::mutex> lk(m_);
    if (!disponible_) return Estado::NoDisponible;
    std::string p = "/v1/";
    p += cfg_.montaje;
    p += "/data/";
    p += ruta;
    const nlohmann::json body = {{"options", {{"cas", cas}}}, {"data", datos}};
    Respuesta r = operar("POST", p, body.dump());
    if (r.status == 0) return Estado::NoDisponible;
    if (r.status == 400 && r.cuerpo.find("check-and-set") != std::string::npos) return Estado::Conflicto;
    if (r.status != 200) {
        ultimo_error_ = "POST " + ruta + ": HTTP " + std::to_string(r.status) + " " + recorte(r.cuerpo);
        return Estado::NoDisponible;
    }
    try {
        version_nueva = nlohmann::json::parse(r.cuerpo).at("data").at("version").get<int>();
        return Estado::Ok;
    } catch (const std::exception& e) {
        ultimo_error_ = "POST " + ruta + ": respuesta inesperada (" + e.what() + ")";
        return Estado::NoDisponible;
    }
}

// Una vuelta por la lista, un login por dirección (sin reintentos: se llama cada sondeo_s)
bool VaultSecretStore::sondear() {
    std::lock_guard<std::mutex> lk(m_);
    const size_t n = dirs_.size();
    std::string detalle;
    for (size_t k = 0; k < n; ++k) {
        const size_t dir = (actual_ + k) % n;
        std::string e;
        if (login(dir, e)) {
            if (dir != actual_) {
                log_ << "[ETCD-VAULT-CAMBIO] se usa " << dirs_[dir].url << std::endl;
                actual_ = dir;
            }
            disponible_ = true;
            ultimo_error_.clear();
            return true;
        }
        if (!detalle.empty()) detalle += "; ";
        detalle += dirs_[dir].url;
        detalle += ": ";
        detalle += e;
    }
    marcar_caido(detalle);
    return false;
}

}  // namespace argus::claves
