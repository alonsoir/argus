// protegidos_manifiesto.hpp — [PROTEGIDOS-MANIFIESTO-D318] ADR-060 (DEBT-FW-MANIFIESTO-PROTEGIDOS-001), paso 8e.1a.
// Manifiesto firmado de rangos protegidos, uno por hospital con sus plantas dentro (ADR-060, sección 6).
//
// Sobre (lo que viaja y se guarda en disco):
//   {"formato": "argus-protegidos/v1", "carga_b64": "<base64 de los bytes exactos>", "firma": "vault:vN:<base64 Ed25519>"}
// Lo que se firma son los bytes exactos de la carga, nunca un JSON reformateado. La firma (Vault transit, ed25519) se
// verifica ANTES de interpretar la carga, con la clave pública compilada en el agente: primero la ranura actual y, si no,
// la siguiente (sin campo que diga cuál: D-F). Después se valida la carga entera, con los límites de prefijo que ella
// misma declara (fijados por la plantilla de despliegue) y los fijos de ADR-060 (infraestructura solo /32 y /128).
//
// Funciones puras salvo leer_cache/escribir_cache: sin red ni kernel. Las usa el agente al arrancar (caché), al
// re-verificar la caché (D7) y, desde 8e.3, al recibir un manifiesto del etcd-server.
#pragma once
#include "firewall/ddos_protegidos.hpp"
#include <array>
#include <cstdint>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <vector>

namespace mldefender::firewall {

// Formato del sobre y límites de tamaño (parte del formato v1; no son parámetros de operación).
inline constexpr const char* kProtegidosFormato = "argus-protegidos/v1";
inline constexpr std::size_t kProtegidosMaxSobreBytes = 4u * 1024u * 1024u;   // sobre entero en disco o en red
inline constexpr std::size_t kProtegidosMaxCargaBytes = 2u * 1024u * 1024u;   // carga ya decodificada
inline constexpr std::size_t kProtegidosMaxEntradas = 65536u;                 // comun + todas las plantas
// Límite de prefijo IPv4 que puede declarar la plantilla para intranet, dmz y externos_criticos: [8, 32].
// infraestructura: exactamente 32 (solo hosts, ADR-060 D2). IPv6: solo /128 en cualquier categoría (D-I, hasta
// DEBT-FW-IPV6-SETS-001).
inline constexpr int kProtegidosLimiteMin = 8;

// Clave pública Ed25519 compilada en dos ranuras (ADR-060 D3; patrón ADR-025).
struct ClavesProtegidos {
    std::array<unsigned char, 32> actual{};
    bool hay_siguiente = false;
    std::array<unsigned char, 32> siguiente{};
};
// "actual" obligatoria (64 hex en minúsculas); "siguiente" vacía o 64 hex. false + error si no.
bool claves_protegidos_desde_hex(const std::string& actual_hex, const std::string& siguiente_hex,
                                 ClavesProtegidos& out, std::string& error);
// Las compiladas en el binario (ARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX / _SIGUIENTE_HEX, CMake). Mal formadas: terminate.
const ClavesProtegidos& claves_protegidos_compiladas();
// 16 hex del sha256 de los 32 bytes (la misma huella que imprime protegidos_pubkey.sh).
std::string huella_clave_protegidos(const std::array<unsigned char, 32>& k);

struct EntradaProtegida {
    RangoProtegido rango;   // cidr ya validado y normalizado, con su categoría
    std::string interfaz;   // obligatoria, [A-Za-z0-9._-]{1,15}
    std::string mac;        // "" o xx:xx:xx:xx:xx:xx (hex en minúsculas)
    std::string motivo;     // texto corto, imprimible
    bool comun = false;     // true si viene de "comun"; false si de la planta
};

struct ManifiestoVerificado {
    uint64_t version = 0;
    std::string hospital_id;
    std::string planta;          // despliegue_id de este firewall
    std::string firmante;
    std::string emitido_utc;
    std::string motivo;
    std::string hash_anterior;   // tal cual (se registra; no se exige: un firewall puede saltarse versiones)
    std::string clave;           // "actual" | "siguiente": la ranura que verificó
    std::string sha256_carga;    // hex, 64
    std::string sobre;           // bytes exactos del sobre verificado (lo que se guarda en la caché)
    std::array<int, 5> limites{};             // por CategoriaProtegida (índice 0 sin uso)
    std::vector<EntradaProtegida> entradas;   // comun + la planta de este firewall, en ese orden
    std::array<std::size_t, 5> por_categoria() const;
    RangosProtegidos rangos() const;          // para la barrera de usuario (protege por IP siempre: D-G)
};

enum class MotivoRechazo { FORMATO, FIRMA, VERSION, HOSPITAL, PLANTA, LIMITE };
const char* nombre_motivo(MotivoRechazo m);

struct ResultadoVerificacion {
    bool ok = false;
    MotivoRechazo motivo = MotivoRechazo::FORMATO;
    std::string detalle;                                  // saneado, para el log
    std::shared_ptr<const ManifiestoVerificado> manifiesto;
};

// Verifica un sobre para ESTE firewall: firma con las claves dadas, hospital_id y planta propios, y version
// estrictamente mayor que version_aplicada (0 = ninguna aplicada todavía).
ResultadoVerificacion verificar_manifiesto(const std::string& sobre, const ClavesProtegidos& claves,
                                           const std::string& hospital_id, const std::string& planta,
                                           uint64_t version_aplicada);

// Línea de log [PROTEGIDOS-MANIFIESTO] verificado ... (sin la carga).
std::string resumen_manifiesto(const ManifiestoVerificado& m);

// Lo vigente en el agente (ADR-060 D7): el último manifiesto verificado. Un rechazo no lo toca. Seguro entre hilos.
class ProtegidosVigentes {
public:
    struct Propuesta {
        ResultadoVerificacion resultado;
        std::shared_ptr<const ManifiestoVerificado> anterior;   // el vigente antes de aplicar (null si no había)
    };
    ProtegidosVigentes(ClavesProtegidos claves, std::string hospital_id, std::string planta);
    // Verifica y, si vale, lo hace vigente. Exige version > la vigente.
    Propuesta proponer(const std::string& sobre);
    // Verifica sin aplicar contra la versión vigente admitiendo la misma (D7: re-verificar la caché ya aplicada).
    ResultadoVerificacion reverificar(const std::string& sobre) const;
    std::shared_ptr<const ManifiestoVerificado> vigente() const;
    bool verificado() const;   // candado (D6): hay manifiesto verificado
    uint64_t rechazos() const;
    const std::string& hospital_id() const { return hospital_id_; }
    const std::string& planta() const { return planta_; }

private:
    const ClavesProtegidos claves_;
    const std::string hospital_id_;
    const std::string planta_;
    mutable std::mutex m_;
    std::shared_ptr<const ManifiestoVerificado> vigente_;
    uint64_t rechazos_ = 0;
};

// Caché en disco del último manifiesto verificado (ADR-060 D5.5). Lectura sin seguir enlaces y con tope de tamaño;
// escritura atómica (temporal 0640 + rename). false + error si no se puede.
bool leer_cache_protegidos(const std::string& ruta, std::string& sobre, std::string& error);
bool escribir_cache_protegidos(const std::string& ruta, const std::string& sobre, std::string& error);

// [PROTEGIDOS-INFRA-INCOMPLETA] (D-C): hosts de etcd.endpoints ("https://IPv4:puerto") que no cubre ninguna entrada
// infraestructura del manifiesto. Una entrada de endpoints mal formada se devuelve tal cual (también falta).
std::vector<std::string> infra_sin_cubrir(const ManifiestoVerificado& m, const std::vector<std::string>& endpoints);

}  // namespace mldefender::firewall
