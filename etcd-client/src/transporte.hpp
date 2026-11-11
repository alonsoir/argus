#pragma once
// etcd-client/src/transporte.hpp — [ETCD-CLIENTE-D316] transporte interno de la librería hacia el etcd-server
// (DEBT-ETCD-HA-TLS-RAFT-001 paso 5). Sustituye al espacio http:: (host/port en claro, sin usuarios fuera de la
// librería): HTTPS con certificado de cliente y verificación del certificado del servidor (nombre incluido), y una
// lista de direcciones (C1). Decisión F3 de Alonso: se pasa a la siguiente dirección solo si no hay respuesta o hay
// un 5xx; un 4xx (403, 404...) se devuelve enseguida, sin reintentar. Privado: no se instala.
#include "etcd_client/etcd_client.hpp"
#include <cstddef>
#include <mutex>
#include <string>

namespace etcd_client {

struct Respuesta {
    int status = 0;            // 0 = ninguna dirección respondió
    std::string body;
    bool exito = false;        // 2xx
    std::string error;         // [ETCD-CLIENTE-B1-D316] status 0: el error de cada dirección («url: error;» ...)
};

class Transporte {
public:
    explicit Transporte(const Config& c) : c_(c) {}

    // intentos_por_direccion <= 0: los de la configuración (retry_attempts). callado: sin las líneas por intento ni
    // [ETCD-CLIENTE-NO-DISPONIBLE] (las usa el mantenedor, que lo resume en [ETCD-CLIENTE-SIN-SERVICIO] con r.error).
    Respuesta peticion(const std::string& metodo, const std::string& ruta, const std::string& cuerpo = "",
                       const std::string& content_type = "application/json", size_t original_size = 0,
                       int intentos_por_direccion = 0, bool callado = false);

    std::string direccion_actual() const;

private:
    Config c_;
    mutable std::mutex m_;
    size_t actual_ = 0;  // índice de la última dirección que respondió
};

// https://host:puerto -> host y puerto (la URL ya la validó leer_bloque_etcd)
bool partir_url(const std::string& url, std::string& host, int& puerto);

}  // namespace etcd_client
