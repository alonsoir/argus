// etcd-client/src/http_client.cpp — [ETCD-CLIENTE-D316] transporte HTTPS con certificado de cliente y lista de
// direcciones (DEBT-ETCD-HA-TLS-RAFT-001 paso 5, C1 y F3). Antes: httplib::Client en claro contra host:port y
// reintento de toda respuesta no 2xx (también 403/404). Day 62: cada línea lleva componente y hora.
#include "transporte.hpp"
#include <httplib.h>
#include <chrono>
#include <ctime>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <thread>

namespace etcd_client {

namespace {

std::string iso8601_now() {
    auto now = std::chrono::system_clock::now();
    auto now_t = std::chrono::system_clock::to_time_t(now);
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch()) % 1000;
    std::tm tm_utc{};
    gmtime_r(&now_t, &tm_utc);
    std::ostringstream ss;
    ss << std::put_time(&tm_utc, "%Y-%m-%dT%H:%M:%S") << '.' << std::setfill('0') << std::setw(3) << ms.count()
       << 'Z';
    return ss.str();
}

long duracion_us(std::chrono::steady_clock::time_point t0) {
    return static_cast<long>(
        std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now() - t0).count());
}

}  // namespace

bool partir_url(const std::string& url, std::string& host, int& puerto) {
    const std::string pre = "https://";
    if (url.compare(0, pre.size(), pre) != 0) return false;
    const std::string resto = url.substr(pre.size());
    const size_t dos = resto.rfind(':');
    if (dos == std::string::npos || dos == 0 || dos + 1 >= resto.size()) return false;
    host = resto.substr(0, dos);
    try {
        puerto = std::stoi(resto.substr(dos + 1));
    } catch (...) {
        return false;
    }
    return puerto >= 1 && puerto <= 65535;
}

std::string Transporte::direccion_actual() const {
    std::lock_guard<std::mutex> lk(m_);
    return c_.endpoints.empty() ? std::string() : c_.endpoints[actual_ % c_.endpoints.size()];
}

Respuesta Transporte::peticion(const std::string& metodo, const std::string& ruta, const std::string& cuerpo,
                               const std::string& content_type, size_t original_size, int intentos, bool callado) {
    Respuesta r;
    const std::string& comp = c_.component_name;
    if (c_.endpoints.empty()) {
        r.error = "sin direcciones";
        std::cerr << "[ETCD-CLIENTE-SIN-ENDPOINTS] " << comp << ": " << metodo << " " << ruta
                  << " sin direcciones del etcd-server (bloque etcd del JSON)" << std::endl;
        return r;
    }
    if (intentos <= 0) intentos = c_.retry_attempts;
    size_t inicio;
    {
        std::lock_guard<std::mutex> lk(m_);
        inicio = actual_ % c_.endpoints.size();
    }
    const time_t to_s = c_.connection_timeout_ms / 1000;
    const time_t to_us = static_cast<time_t>(c_.connection_timeout_ms % 1000) * 1000;
    std::ostringstream errores;

    for (size_t k = 0; k < c_.endpoints.size(); ++k) {
        const size_t idx = (inicio + k) % c_.endpoints.size();
        const std::string& url = c_.endpoints[idx];
        std::string host;
        int puerto = 0;
        if (!partir_url(url, host, puerto)) {
            errores << " " << url << ": URL mal formada;";
            continue;
        }
        std::string ultimo_error;
        for (int i = 0; i < intentos; ++i) {
            if (i > 0) std::this_thread::sleep_for(std::chrono::milliseconds(c_.retry_interval_ms));
            httplib::SSLClient cli(host, puerto, c_.cert_file, c_.key_file);
            cli.set_ca_cert_path(c_.ca_file);
            cli.enable_server_certificate_verification(true);
            cli.enable_server_hostname_verification(true);
            cli.set_connection_timeout(to_s, to_us);
            cli.set_read_timeout(to_s, to_us);
            cli.set_write_timeout(to_s, to_us);
            httplib::Headers h = {{"X-Component-Name", comp}, {"X-Request-Timestamp", iso8601_now()}};
            if (original_size > 0) h.insert({"X-Original-Size", std::to_string(original_size)});
            std::cout << "[HTTP→] " << metodo << " " << url << ruta << " | ts=" << iso8601_now()
                      << " | component=" << comp << std::endl;
            const auto t0 = std::chrono::steady_clock::now();
            httplib::Result res;
            if (metodo == "GET") res = cli.Get(ruta, h);
            else if (metodo == "POST") res = cli.Post(ruta, h, cuerpo, content_type);
            else if (metodo == "PUT") res = cli.Put(ruta, h, cuerpo, content_type);
            else if (metodo == "DELETE") res = cli.Delete(ruta, h);
            else {
                std::cerr << "[ETCD-CLIENTE] método no soportado: " << metodo << std::endl;
                return r;
            }
            if (!res) {
                ultimo_error = httplib::to_string(res.error());
                if (!callado)
                    std::cerr << "[ETCD-CLIENTE] " << comp << ": " << metodo << " " << url << ruta
                              << " sin respuesta (" << ultimo_error << "), intento " << (i + 1) << "/" << intentos
                              << std::endl;
                continue;
            }
            std::cout << "[HTTP←] " << res->status << " | " << metodo << " " << url << ruta
                      << " | duration_us=" << duracion_us(t0) << " | component=" << comp << std::endl;
            if (res->status >= 500) {  // F3: el etcd-server no puede servir (p. ej. almacén caído): otro lo intenta
                ultimo_error = "HTTP " + std::to_string(res->status);
                continue;
            }
            // F3: respuesta definitiva (2xx, 3xx o 4xx): sin reintento ni cambio de dirección
            {
                std::lock_guard<std::mutex> lk(m_);
                if (idx != actual_ % c_.endpoints.size())
                    std::cerr << "[ETCD-CLIENTE-CAMBIO] " << comp << ": " << c_.endpoints[actual_ % c_.endpoints.size()]
                              << " -> " << url << std::endl;
                actual_ = idx;
            }
            r.status = res->status;
            r.body = res->body;
            r.exito = (res->status >= 200 && res->status < 300);
            if (!r.exito)
                std::cerr << "[ETCD-CLIENTE] " << comp << ": " << metodo << " " << ruta << " -> " << res->status
                          << " " << res->body << std::endl;
            return r;
        }
        errores << " " << url << ": " << ultimo_error << ";";
    }
    r.error = errores.str();
    if (!callado)
        std::cerr << "[ETCD-CLIENTE-NO-DISPONIBLE] " << comp << ": " << metodo << " " << ruta << " ninguna de las "
                  << c_.endpoints.size() << " direcciones del etcd-server responde:" << r.error << std::endl;
    return r;
}

}  // namespace etcd_client
