// etcd-server/src/secrets_manager.cpp — [ETCD-CLAVES-D314] (ver la cabecera)
#include "etcd_server/secrets_manager.hpp"
#include "etcd_server/etcd_server_authz.hpp"
#include <openssl/evp.h>
#include <openssl/rand.h>
#include <chrono>
#include <cstdio>
#include <stdexcept>

namespace etcd_server {

using argus::claves::Estado;

namespace {
int hexval(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}
bool huella_ok(const std::string& h) {
    if (h.size() != 8) return false;
    for (char c : h) {
        if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return false;
    }
    return true;
}
}  // namespace

SecretsManager::SecretsManager(const SecretsConfig& cfg, std::unique_ptr<argus::claves::ISecretStore> almacen,
                               bool modo_memoria, int aviso_intervalo_s, int sondeo_s, Reloj reloj, std::ostream& log,
                               Generador generador)
    : cfg_(cfg),
      almacen_(std::move(almacen)),
      modo_memoria_(modo_memoria),
      aviso_(aviso_intervalo_s),
      sondeo_(sondeo_s),
      reloj_(std::move(reloj)),
      log_(log),
      generador_(std::move(generador)) {
    log_ << "[ETCD-CLAVES] almacén de claves: " << almacen_->descripcion() << "; ventana de dos: la anterior vale "
         << cfg_.grace_period_seconds << " s tras rotar; enfriamiento " << cfg_.min_rotation_interval_seconds
         << " s; claves de " << cfg_.default_key_length_bytes << " bytes" << std::endl;
}

SecretsManager::~SecretsManager() { parar_monitor(); }

void SecretsManager::arrancar_monitor() {
    if (monitor_activo_.exchange(true)) return;
    monitor_ = std::thread([this] {
        while (monitor_activo_) {
            for (int i = 0; i < 10 && monitor_activo_; ++i) std::this_thread::sleep_for(std::chrono::milliseconds(100));
            if (monitor_activo_) revisar();
        }
    });
}

void SecretsManager::parar_monitor() {
    if (!monitor_activo_.exchange(false)) return;
    if (monitor_.joinable()) monitor_.join();
}

std::string SecretsManager::huella(const std::string& hex) {
    if (hex.empty() || hex.size() % 2 != 0) return "invalida";
    std::string bytes;
    bytes.reserve(hex.size() / 2);
    for (size_t i = 0; i < hex.size(); i += 2) {
        const int a = hexval(hex[i]), b = hexval(hex[i + 1]);
        if (a < 0 || b < 0) return "invalida";
        bytes.push_back(static_cast<char>(a * 16 + b));
    }
    unsigned char md[EVP_MAX_MD_SIZE];
    unsigned int n = 0;
    if (EVP_Digest(bytes.data(), bytes.size(), md, &n, EVP_sha256(), nullptr) != 1 || n < 4) return "error";
    char out[9];
    std::snprintf(out, sizeof(out), "%02x%02x%02x%02x", md[0], md[1], md[2], md[3]);
    return std::string(out, 8);
}

std::string SecretsManager::iso(std::time_t t) {
    std::tm tm{};
    gmtime_r(&t, &tm);
    char b[32];
    std::strftime(b, sizeof(b), "%Y-%m-%dT%H:%M:%SZ", &tm);
    return b;
}

bool SecretsManager::desde_iso(const std::string& s, std::time_t& t) {
    std::tm tm{};
    const char* fin = strptime(s.c_str(), "%Y-%m-%dT%H:%M:%SZ", &tm);
    if (fin == nullptr || *fin != '\0') return false;
    t = timegm(&tm);  // UTC (antes: mktime, hora local)
    return true;
}

std::string SecretsManager::generar(size_t bytes) {
    if (generador_) return generador_(bytes);
    std::string b(bytes, '\0');
    if (RAND_bytes(reinterpret_cast<unsigned char*>(b.data()), static_cast<int>(bytes)) != 1)
        throw std::runtime_error("RAND_bytes falló");
    static const char* kHex = "0123456789abcdef";
    std::string hex;
    hex.reserve(bytes * 2);
    for (unsigned char c : b) {
        hex.push_back(kHex[c >> 4]);
        hex.push_back(kHex[c & 0x0f]);
    }
    return hex;
}

// Toda llamada al almacén pasa por aquí: lleva el estado disponible / no disponible y sus avisos
Estado SecretsManager::anotar(Estado e) {
    const auto t = reloj_();
    if (e == Estado::NoDisponible) {
        if (disponible_) {
            disponible_ = false;
            caida_desde_ = t;
            ultimo_aviso_caida_ = t;
            log_ << "[ETCD-VAULT-NO-DISPONIBLE] " << almacen_->descripcion() << ": " << almacen_->ultimo_error()
                 << ". Se sirve la última ventana conocida; sin ella, /secrets 503; rotar 503. Se sondea cada " << sondeo_
                 << " s" << std::endl;
        }
    } else if (!disponible_) {
        disponible_ = true;
        log_ << "[ETCD-VAULT-RECUPERADO] tras " << (t - caida_desde_) << " s sin almacén de claves" << std::endl;
    }
    return e;
}

bool SecretsManager::almacen_disponible() {
    std::lock_guard<std::mutex> lk(m_);
    return disponible_;
}

void SecretsManager::comprobar_al_arrancar() {
    if (modo_memoria_) return;  // no hay Vault: ya lo dice [ETCD-CLAVES] almacén de claves: memoria (...)
    const bool ok = almacen_->sondear();
    std::lock_guard<std::mutex> lk(m_);
    ultimo_sondeo_ = reloj_();
    if (ok) {
        log_ << "[ETCD-VAULT] conectado: " << almacen_->descripcion() << std::endl;
    } else {
        anotar(Estado::NoDisponible);
    }
}

void SecretsManager::revisar() {
    bool sondear = false;
    {
        std::lock_guard<std::mutex> lk(m_);
        const auto t = reloj_();
        if (modo_memoria_ && (!aviso_memoria_dado_ || t - ultimo_aviso_memoria_ >= aviso_)) {
            log_ << "[ETCD-CLAVES-MEMORIA] claves HMAC solo en memoria (almacen_claves.modo=memoria): se pierden al "
                    "reiniciar y el bronce firmado antes ya no se podrá verificar. Solo transición hasta el paso 6 de "
                    "DEBT-ETCD-HA-TLS-RAFT-001"
                 << std::endl;
            ultimo_aviso_memoria_ = t;
            aviso_memoria_dado_ = true;
        }
        if (!disponible_ && t - ultimo_aviso_caida_ >= aviso_) {
            log_ << "[ETCD-VAULT-NO-DISPONIBLE] sigue sin responder desde hace " << (t - caida_desde_)
                 << " s: " << almacen_->ultimo_error() << std::endl;
            ultimo_aviso_caida_ = t;
        }
        sondear = (!disponible_ || !almacen_->disponible()) && t - ultimo_sondeo_ >= sondeo_;
        if (sondear) ultimo_sondeo_ = t;
    }
    if (!sondear) return;
    const bool ok = almacen_->sondear();  // sin el mutex: mientras tanto se sigue sirviendo la copia
    std::lock_guard<std::mutex> lk(m_);
    anotar(ok ? Estado::Ok : Estado::NoDisponible);
}

Estado SecretsManager::leer_ventana_locked(const std::string& cn, Ventana& v, bool permitir_copia,
                                           bool& desde_copia) {
    desde_copia = false;
    nlohmann::json d;
    int ver = 0;
    const Estado e = anotar(almacen_->leer(cn + "/ventana", d, ver));
    if (e == Estado::Ok) {
        Ventana n;
        n.version = ver;
        try {
            n.activa = d.at("activa").get<std::string>();
            n.anterior = d.value("anterior", "");
            const std::string ex = d.value("expira_anterior", "");
            if (!ex.empty() && !desde_iso(ex, n.expira_anterior)) throw std::runtime_error("expira_anterior");
            if (!huella_ok(n.activa) || (!n.anterior.empty() && !huella_ok(n.anterior)))
                throw std::runtime_error("huella");
        } catch (const std::exception& ex) {
            log_ << "[ETCD-CLAVES-INCOHERENTE] " << cn << "/ventana mal formada (" << ex.what()
                 << "): no se sirve ni se rota esa clave" << std::endl;
            return Estado::NoDisponible;
        }
        ventanas_[cn] = n;
        v = n;
        // [D314] la copia lleva las dos claves de la ventana: con el almacén caído /secrets/valid necesita también la
        // anterior (medido DAY314: tras reiniciar solo se cargaba la activa y daba 503). Si falla, se reintenta luego.
        ClaveHMAC tmp;
        leer_clave_locked(cn, n.activa, tmp);
        if (!n.anterior.empty() && reloj_() < n.expira_anterior) leer_clave_locked(cn, n.anterior, tmp);
        return Estado::Ok;
    }
    if (e == Estado::NoEncontrado) return Estado::NoEncontrado;
    if (!permitir_copia) return e;
    auto it = ventanas_.find(cn);
    if (it == ventanas_.end()) return Estado::NoDisponible;
    v = it->second;
    desde_copia = true;
    return Estado::Ok;
}

Estado SecretsManager::leer_clave_locked(const std::string& cn, const std::string& h, ClaveHMAC& out) {
    const std::string k = cn + "/" + h;
    auto it = claves_.find(k);
    if (it != claves_.end()) {
        out = it->second;
        return Estado::Ok;
    }
    nlohmann::json d;
    int ver = 0;
    const Estado e = anotar(almacen_->leer(k, d, ver));
    if (e != Estado::Ok) return e == Estado::NoEncontrado ? Estado::NoDisponible : e;
    ClaveHMAC c;
    try {
        c.hex = d.at("clave").get<std::string>();
        if (!desde_iso(d.at("creada").get<std::string>(), c.creada)) throw std::runtime_error("creada");
    } catch (const std::exception& ex) {
        log_ << "[ETCD-CLAVES-INCOHERENTE] " << k << " mal formada (" << ex.what() << ")" << std::endl;
        return Estado::NoDisponible;
    }
    c.huella = huella(c.hex);
    if (c.huella != h) {  // la entrada no es la clave que dice su nombre: no se sirve
        log_ << "[ETCD-CLAVES-INCOHERENTE] " << k << ": la clave guardada tiene huella " << c.huella << std::endl;
        return Estado::NoDisponible;
    }
    claves_[k] = c;
    out = c;
    return Estado::Ok;
}

Estado SecretsManager::crear_clave_locked(const std::string& cn, ClaveHMAC& out) {
    for (int i = 0; i < 3; ++i) {
        ClaveHMAC c;
        c.hex = generar(static_cast<size_t>(cfg_.default_key_length_bytes));
        c.huella = huella(c.hex);
        c.creada = reloj_();
        const nlohmann::json d = {{"clave", c.hex}, {"creada", iso(c.creada)}};
        int ver = 0;
        const Estado e = anotar(almacen_->escribir(cn + "/" + c.huella, d, 0, ver));
        if (e == Estado::Ok) {
            claves_[cn + "/" + c.huella] = c;
            out = c;
            return Estado::Ok;
        }
        if (e != Estado::Conflicto) return e;
        log_ << "[ETCD-CLAVES-HUELLA-REPETIDA] " << cn << "/" << c.huella << " ya existe: se genera otra clave"
             << std::endl;
    }
    return Estado::NoDisponible;
}

ResultadoClaves SecretsManager::activa(const std::string& cn, ClaveHMAC& out, bool& desde_copia) {
    if (!argus::etcdauthz::nombre_valido(cn)) return ResultadoClaves::NombreInvalido;
    std::lock_guard<std::mutex> lk(m_);
    for (int vuelta = 0; vuelta < 2; ++vuelta) {
        Ventana v;
        const Estado e = leer_ventana_locked(cn, v, /*permitir_copia=*/true, desde_copia);
        if (e == Estado::Ok) {
            if (leer_clave_locked(cn, v.activa, out) != Estado::Ok) return ResultadoClaves::NoDisponible;
            out.activa = true;
            out.expira = 0;
            return ResultadoClaves::Ok;
        }
        if (e != Estado::NoEncontrado) return ResultadoClaves::NoDisponible;
        // Primera vez para este CN: clave nueva + ventana con CAS 0
        ClaveHMAC c;
        if (crear_clave_locked(cn, c) != Estado::Ok) return ResultadoClaves::NoDisponible;
        const nlohmann::json vd = {{"activa", c.huella}, {"anterior", ""}, {"expira_anterior", ""}};
        int ver = 0;
        const Estado w = anotar(almacen_->escribir(cn + "/ventana", vd, 0, ver));
        if (w == Estado::Ok) {
            Ventana n;
            n.activa = c.huella;
            n.version = ver;
            ventanas_[cn] = n;
            log_ << "[ETCD-CLAVES-CREADA] " << cn << ": primera clave, huella " << c.huella << std::endl;
            out = c;
            out.activa = true;
            desde_copia = false;
            return ResultadoClaves::Ok;
        }
        if (w != Estado::Conflicto) return ResultadoClaves::NoDisponible;
        // Otro proceso creó la ventana a la vez: se usa la suya (la clave generada aquí queda sin usar, inmutable)
        log_ << "[ETCD-CLAVES-CONCURRENTE] " << cn << ": otra instancia creó la ventana antes; se usa la suya (la "
             << "clave " << c.huella << " queda sin usar)" << std::endl;
    }
    return ResultadoClaves::NoDisponible;
}

ResultadoClaves SecretsManager::rotar(const std::string& cn, bool force, ClaveHMAC& nueva, int& reintentar_s) {
    if (!argus::etcdauthz::nombre_valido(cn)) return ResultadoClaves::NombreInvalido;
    std::unique_lock<std::mutex> lk(m_);
    Ventana v;
    bool copia = false;
    const Estado e = leer_ventana_locked(cn, v, /*permitir_copia=*/false, copia);
    if (e == Estado::NoEncontrado) {  // nada que rotar: es la primera clave
        lk.unlock();
        return activa(cn, nueva, copia);
    }
    if (e != Estado::Ok) return ResultadoClaves::NoDisponible;
    ClaveHMAC vieja;
    if (leer_clave_locked(cn, v.activa, vieja) != Estado::Ok) return ResultadoClaves::NoDisponible;
    const auto t = reloj_();
    const auto edad = t - vieja.creada;
    if (!force && edad < cfg_.min_rotation_interval_seconds) {
        reintentar_s = static_cast<int>(cfg_.min_rotation_interval_seconds - edad);
        log_ << "[ETCD-CLAVES-ENFRIAMIENTO] " << cn << ": rotación rechazada, la activa tiene " << edad
             << " s (mínimo " << cfg_.min_rotation_interval_seconds << " s); faltan " << reintentar_s << " s"
             << std::endl;
        return ResultadoClaves::Enfriamiento;
    }
    if (force) {
        log_ << "[ETCD-CLAVES-FORZADA] " << cn << ": rotación de emergencia (force=true), enfriamiento saltado"
             << std::endl;
    }
    ClaveHMAC c;
    if (crear_clave_locked(cn, c) != Estado::Ok) return ResultadoClaves::NoDisponible;
    const std::time_t expira = t + cfg_.grace_period_seconds;
    const nlohmann::json vd = {{"activa", c.huella}, {"anterior", v.activa}, {"expira_anterior", iso(expira)}};
    int ver = 0;
    const Estado w = anotar(almacen_->escribir(cn + "/ventana", vd, v.version, ver));
    if (w == Estado::Conflicto) {
        log_ << "[ETCD-CLAVES-CONCURRENTE] " << cn << ": otra instancia rotó a la vez; esta rotación no se aplica (la "
             << "clave " << c.huella << " queda sin usar)" << std::endl;
        return ResultadoClaves::Conflicto;
    }
    if (w != Estado::Ok) return ResultadoClaves::NoDisponible;
    Ventana n;
    n.activa = c.huella;
    n.anterior = v.activa;
    n.expira_anterior = expira;
    n.version = ver;
    ventanas_[cn] = n;
    log_ << "[ETCD-CLAVES-ROTADA] " << cn << ": activa " << c.huella << ", anterior " << v.activa << " válida hasta "
         << iso(expira) << std::endl;
    nueva = c;
    nueva.activa = true;
    return ResultadoClaves::Ok;
}

ResultadoClaves SecretsManager::validas(const std::string& cn, std::vector<ClaveHMAC>& out, bool& desde_copia) {
    if (!argus::etcdauthz::nombre_valido(cn)) return ResultadoClaves::NombreInvalido;
    std::lock_guard<std::mutex> lk(m_);
    out.clear();
    Ventana v;
    const Estado e = leer_ventana_locked(cn, v, /*permitir_copia=*/true, desde_copia);
    if (e == Estado::NoEncontrado) return ResultadoClaves::Ok;
    if (e != Estado::Ok) return ResultadoClaves::NoDisponible;
    ClaveHMAC a;
    if (leer_clave_locked(cn, v.activa, a) != Estado::Ok) return ResultadoClaves::NoDisponible;
    a.activa = true;
    a.expira = 0;
    out.push_back(a);
    if (!v.anterior.empty() && reloj_() < v.expira_anterior) {
        ClaveHMAC p;
        if (leer_clave_locked(cn, v.anterior, p) != Estado::Ok) return ResultadoClaves::NoDisponible;
        p.activa = false;
        p.expira = v.expira_anterior;
        out.push_back(p);
    }
    return ResultadoClaves::Ok;
}

}  // namespace etcd_server
