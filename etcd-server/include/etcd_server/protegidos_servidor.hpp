#pragma once
// etcd-server/include/etcd_server/protegidos_servidor.hpp — [PROTEGIDOS-MANIFIESTO-D318] ADR-060 paso 8e.3b (F-A, F-C,
// F-D): el manifiesto firmado de protegidos en el etcd-server.
//   - Bloque "protegidos" de etcd-server.json: hospital_id ([a-z0-9-], de 1 a 64). Un etcd-server sirve a UN hospital.
//     Sin valor sano por defecto: ausente o mal formado = defecto (--check-config da 1) y GET/PUT /v1/protegidos
//     responden 503. Ansible lo escribe desde argus_hospital_id del inventario.
//   - Almacén (el etcd del despliegue, mismo prefijo que el registro): protegidos/vigente = el sobre tal cual, y
//     protegidos/v/<N> = cada versión publicada, que no se vuelve a escribir.
//   - GET /v1/protegidos/v/{n} (solo ou:argus-infra, 8e.3d-0): protegidos/v/<n> tal cual.
//   - PUT: verificar_documento (libs/protegidos) con la clave pública COMPILADA (la misma que el firewall): firma,
//     formato, límites, hospital propio, versión > la vigente y, en cada planta, nada que su firewall rechazaría. Con
//     Vault caído se verifica igual: Vault solo hace falta para firmar.
//   - Orden de escritura: primero protegidos/v/<N>, después protegidos/vigente. Si se cae entre las dos, GET sigue dando
//     la anterior y un PUT de la misma N responde 409 (ya existe): se firma la N+1. Un PUT a la vez (mutex): con un
//     etcd-server por despliegue basta; con varios (PR2) hará falta una transacción de etcd.
#include "etcd_server/etcd_server_almacen.hpp"
#include "protegidos/manifiesto.hpp"

#include <nlohmann/json.hpp>

#include <cstdint>
#include <memory>
#include <mutex>
#include <ostream>
#include <string>

namespace argus::protegidos {

struct ProtegidosServidorConfig {
    std::string hospital_id;  // vacío = sin configurar (503)
};

struct ResultadoProtegidosConfig {
    ProtegidosServidorConfig cfg;
    int defectos = 0;
};

ResultadoProtegidosConfig parse_protegidos_config(const nlohmann::json& root, std::ostream& aviso, std::ostream& info);

class AlmacenProtegidos {
public:
    AlmacenProtegidos(std::unique_ptr<::argus::almacen::IRegistryStore> almacen, ClavesProtegidos claves,
                      std::string hospital_id, std::ostream& log);

    struct Respuesta {
        int http = 500;
        std::string cuerpo;       // JSON (el sobre tal cual en un GET 200)
    };
    // GET /v1/protegidos: 200 con el sobre vigente, 404 si no hay, 503 sin configurar o almacén no disponible
    Respuesta obtener();
    // [PROTEGIDOS-MANIFIESTO-D319] 8e.3d-0 (decisión G-C de Alonso): GET /v1/protegidos/v/{n}, una versión del histórico
    // (protegidos/v/<N>) tal cual, para que argus-infra haga diff y deshacer N (el contenido de N firmado como N+1).
    // 200 con el sobre; 400 si n no es un decimal >= 1 sin ceros a la izquierda que quepa en 64 bits; 404 si esa
    // versión no existe; 503 sin configurar o almacén no disponible. No verifica: quien lo pide verifica la firma.
    Respuesta obtener_version(const std::string& n);
    // PUT /v1/protegidos: 201 publicado; 400 formato, límites o planta; 403 firma u hospital; 409 versión no mayor que
    // la vigente o ya existe; 413 demasiado grande; 503 sin configurar o almacén no disponible. quien = CN del
    // certificado (para el log).
    Respuesta publicar(const std::string& sobre, const std::string& quien);

    const std::string& hospital_id() const { return hospital_id_; }
    static std::string clave_version(uint64_t n);  // "protegidos/v/" + 20 dígitos (ordena bien al listar)

private:
    // Versión vigente: la del sobre de protegidos/vigente; si falta o ya no verifica, la mayor de protegidos/v/.
    // false si el almacén no responde.
    bool version_vigente(uint64_t& v);

    std::unique_ptr<::argus::almacen::IRegistryStore> almacen_;
    const ClavesProtegidos claves_;
    const std::string hospital_id_;
    std::ostream& log_;
    std::mutex m_;
};

}  // namespace argus::protegidos
