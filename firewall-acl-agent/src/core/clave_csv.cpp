// firewall-acl-agent/src/core/clave_csv.cpp — [FW-CSV-CLAVE-B2-D316] ver clave_csv.hpp
#include "firewall/clave_csv.hpp"

#include <cstdio>
#include <openssl/evp.h>

namespace mldefender::firewall {

std::string huella_clave(const Clave& clave) {
    unsigned char md[EVP_MAX_MD_SIZE];
    unsigned int n = 0;
    if (EVP_Digest(clave.data(), clave.size(), md, &n, EVP_sha256(), nullptr) != 1 || n < 4) return "error";
    char out[9];
    std::snprintf(out, sizeof(out), "%02x%02x%02x%02x", md[0], md[1], md[2], md[3]);
    return out;
}

ClaveCsv::ClaveCsv(Proveedor proveedor, int intervalo_s, Sumidero log, Reloj reloj)
    : proveedor_(std::move(proveedor)), intervalo_s_(intervalo_s > 0 ? intervalo_s : 60), log_(std::move(log)),
      reloj_(std::move(reloj)) {}

ClaveCsv::~ClaveCsv() { parar(); }

std::string ClaveCsv::hora_utc(std::time_t t) {
    std::tm tm{};
    gmtime_r(&t, &tm);
    char b[32];
    std::strftime(b, sizeof b, "%Y-%m-%dT%H:%M:%SZ", &tm);
    return b;
}

void ClaveCsv::arrancar() {
    if (en_marcha_.exchange(true)) return;
    hilo_ = std::thread([this]() {
        while (en_marcha_) {
            comprobar();
            std::unique_lock<std::mutex> lk(hm_);  // espera interrumpible: la parada no espera al intervalo
            if (cv_.wait_for(lk, std::chrono::seconds(intervalo_s_), [this] { return !en_marcha_.load(); })) break;
        }
    });
}

void ClaveCsv::parar() {
    if (en_marcha_.exchange(false)) {
        { std::lock_guard<std::mutex> lk(hm_); }
        cv_.notify_all();
    }
    if (hilo_.joinable()) hilo_.join();
}

std::optional<Clave> ClaveCsv::clave() const {
    std::lock_guard<std::mutex> lk(m_);
    return clave_;
}

void ClaveCsv::comprobar() {
    std::optional<Clave> k;
    try {
        if (proveedor_) k = proveedor_();
    } catch (const std::exception& e) {
        log_(std::string("[FW-CSV-CLAVE] fallo al pedir la clave al etcd-server: ") + e.what());
        k.reset();
    }
    const std::time_t ahora = reloj_();
    std::lock_guard<std::mutex> lk(m_);

    if (!k.has_value() || k->size() != 32) {
        if (!clave_.has_value()) {
            if (!sin_clave_) {
                sin_clave_ = true;
                sin_clave_desde_ = ahora;
                filas_base_ = filas_sin_clave_.load();
            }
            log_("[FW-CSV-SIN-CLAVE] el etcd-server no entrega la clave HMAC del CSV (/secrets/firewall-acl-agent) desde " +
                 hora_utc(sin_clave_desde_) + " (" + std::to_string(ahora - sin_clave_desde_) + " s): " +
                 std::to_string(filas_sin_clave_.load() - filas_base_) +
                 " filas sin escribir. El firewall sigue bloqueando; el CSV no recibe filas hasta recuperar la clave "
                 "(nunca se escribe sin firma). Próximo intento en " + std::to_string(intervalo_s_) + " s");
        } else {
            if (!sin_confirmar_) {
                sin_confirmar_ = true;
                sin_confirmar_desde_ = ahora;
            }
            log_("[FW-CSV-CLAVE-SIN-CONFIRMAR] el etcd-server no responde desde " + hora_utc(sin_confirmar_desde_) + " (" +
                 std::to_string(ahora - sin_confirmar_desde_) + " s en modo extendido): se sigue firmando el CSV con la "
                 "clave vigente (huella " + huella_ + "). Si al volver trae otra, se abrirá otro CSV");
        }
        return;
    }

    const std::string h = huella_clave(*k);
    const bool igual = clave_.has_value() && *clave_ == *k;
    if (sin_confirmar_) {
        log_("[FW-CSV-CLAVE-CONFIRMADA] el etcd-server vuelve a responder tras " +
             std::to_string(ahora - sin_confirmar_desde_) + " s en modo extendido (desde " +
             hora_utc(sin_confirmar_desde_) + " hasta " + hora_utc(ahora) + "); entrega " +
             (igual ? "la misma clave" : "otra clave") + " (huella " + h + ")");
        sin_confirmar_ = false;
    }
    if (igual) return;
    if (!clave_.has_value()) {
        if (sin_clave_) {
            log_("[FW-CSV-CLAVE-RECUPERADA] clave HMAC del CSV recibida (huella " + h + ") tras " +
                 std::to_string(ahora - sin_clave_desde_) + " s sin clave: hueco del CSV de " + hora_utc(sin_clave_desde_) +
                 " a " + hora_utc(ahora) + ", " + std::to_string(filas_sin_clave_.load() - filas_base_) +
                 " filas sin escribir");
            sin_clave_ = false;
        } else {
            log_("[FW-CSV-CLAVE] clave HMAC del CSV recibida de /secrets/firewall-acl-agent (huella " + h + ")" +
                 (primera_ ? " al arrancar" : ""));
        }
    } else {
        log_("[FW-CSV-CLAVE-CAMBIADA] el etcd-server entrega otra clave HMAC del CSV (huella " + huella_ + " -> " + h +
             "): desde ahora se firma con la nueva en otro CSV");
    }
    primera_ = false;
    clave_ = std::move(k);
    huella_ = h;
}

}  // namespace mldefender::firewall
