#!/usr/bin/env python3
# d318_8e3a_libs_protegidos.py — DAY318, ADR-060 paso 8e.3a [PROTEGIDOS-MANIFIESTO-D318] (F-B): el verificador del manifiesto
# de protegidos y los rangos pasan del firewall-acl-agent a libs/protegidos (estática, espacio de nombres
# argus::protegidos), para compartirlos con el etcd-server; el validador de CIDR (H-2, CWE-78) pasa a
# common/include/argus. Sin cambios de comportamiento: mismos tests, mismas cuentas.
# Uso (Mac, raíz del repo):  python3 scripts/etcd_ha/d318_8e3a_libs_protegidos.py --check|--apply <raíz>
# Todo o nada e idempotente: un fichero NUEVO se crea si no existe y se da por hecho si ya tiene su sha256; uno BORRADO
# se borra si tiene el sha256 esperado y se da por hecho si ya no está; cada CAMBIO se aplica si su texto viejo aparece
# una vez y se da por hecho si ya está el nuevo. Si algo no cuadra, no se escribe nada. Imprime los sha256.
import hashlib
import os
import sys

NUEVO_0_RUTA = 'common/include/argus/ip_cidr_validator.hpp'
NUEVO_0_SHA = '5a1bf193bd563a1401b7e9c7a82de1dafb6ffd25d6180588d37bca1e57261c56'
NUEVO_0 = r'''// common/include/argus/ip_cidr_validator.hpp (antes firewall-acl-agent/include/firewall/ip_cidr_validator.hpp)
// [PROTEGIDOS-MANIFIESTO-D318] en common: también lo usan los rangos de libs/protegidos (firewall y etcd-server).
// H-2 / DEBT-AUTONOMY-REACTOR-CWE78-001: validación única de IP/CIDR, compartida
// por ipset_wrapper (frontera ipset restore) y config_loader (frontera de carga:
// autonomy.whitelist_cidrs → system("iptables ... -s <cidr>")). Una allowlist,
// dos fronteras — mismo patrón que set_name_validator.hpp (evita divergencia DRY).
#pragma once
#include <string>
#include <cctype>
#include <arpa/inet.h>
#include <sys/socket.h>

namespace argus {

    /// SEGURIDAD: allowlist estricto [0-9a-fA-F.:/] ANTES de descomponer — excluye
    /// \n \r \t espacio ; $ ` | & ( ) y todo metacarácter de shell (cierra CWE-78
    /// al interpolar en system()/restore).
    /// ESTRUCTURAL (no de seguridad): dirección válida vía inet_pton + prefijo CIDR
    /// numérico en rango [0, 32|128].
    inline bool is_valid_ip_cidr(const std::string& ip) {
        if (ip.empty() || ip.size() > 64) return false;
        for (unsigned char c : ip)
            if (!(std::isxdigit(c) || c == '.' || c == ':' || c == '/')) return false;

        const auto slash = ip.find('/');
        if (slash != std::string::npos &&
            ip.find('/', slash + 1) != std::string::npos) return false;
        const std::string ip_part = (slash == std::string::npos) ? ip : ip.substr(0, slash);

        struct sockaddr_in  sa4;
        struct sockaddr_in6 sa6;
        const bool is_v4 = inet_pton(AF_INET,  ip_part.c_str(), &sa4.sin_addr)  == 1;
        const bool is_v6 = inet_pton(AF_INET6, ip_part.c_str(), &sa6.sin6_addr) == 1;
        if (!is_v4 && !is_v6) return false;

        if (slash != std::string::npos) {
            const std::string prefix = ip.substr(slash + 1);
            if (prefix.empty() || prefix.size() > 3) return false;
            int bits = 0;
            for (unsigned char c : prefix) {
                if (!std::isdigit(c)) return false;
                bits = bits * 10 + (c - '0');
            }
            if (bits > (is_v6 ? 128 : 32)) return false;
        }
        return true;
    }

}  // namespace argus'''

NUEVO_1_RUTA = 'libs/protegidos/CMakeLists.txt'
NUEVO_1_SHA = 'e9cb37b54fc51f2847715ede80868792dec98459e9ffbc590deb1d30128067ce'
NUEVO_1 = r'''# libs/protegidos — [PROTEGIDOS-MANIFIESTO-D318] ADR-060 F-B: el verificador del manifiesto firmado de protegidos y los
# rangos, UNO solo para el firewall-acl-agent y el etcd-server (dos verificadores acabarían divergiendo).
# Librería ESTÁTICA a propósito, incluida con add_subdirectory desde cada componente: se compila con las opciones del
# componente (production: -O3 -flto -Werror ...) y queda DENTRO de su binario, cubierta por su firma (ADR-025). Una .so
# en /usr/local/lib se podría cambiar por una que lo acepte todo sin tocar el binario.
# La clave pública NO está aquí: claves_protegidos_compiladas() la define cada componente con sus -D (patrón ADR-025).
# Opción ARGUS_PROTEGIDOS_TESTS (defecto OFF): el firewall la enciende con sus tests; el etcd-server no la repite.
cmake_minimum_required(VERSION 3.16)
project(argus_protegidos LANGUAGES CXX)

find_package(PkgConfig REQUIRED)
pkg_check_modules(PROT_JSONCPP REQUIRED jsoncpp)
# La libsodium compilada desde el código fuente (1.0.19), como plugin-loader (DEBT-LIBSODIUM-SO-VERSION-CONFLICT-001)
find_library(PROT_SODIUM_LIB sodium PATHS /usr/local/lib /usr/lib NO_DEFAULT_PATH)
find_path(PROT_SODIUM_INCLUDE sodium.h PATHS /usr/local/include /usr/include NO_DEFAULT_PATH)
if(NOT PROT_SODIUM_LIB OR NOT PROT_SODIUM_INCLUDE)
    message(FATAL_ERROR "[PROTEGIDOS-CLAVE] libsodium no encontrada (lib=${PROT_SODIUM_LIB} include=${PROT_SODIUM_INCLUDE})")
endif()
message(STATUS "[PROTEGIDOS] libsodium: ${PROT_SODIUM_LIB}")

add_library(argus_protegidos STATIC src/manifiesto.cpp)
set_target_properties(argus_protegidos PROPERTIES POSITION_INDEPENDENT_CODE ON)
target_compile_features(argus_protegidos PUBLIC cxx_std_20)
target_include_directories(argus_protegidos PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include
        ${CMAKE_CURRENT_SOURCE_DIR}/../../common/include  # argus/ip_cidr_validator.hpp
        PRIVATE ${PROT_JSONCPP_INCLUDE_DIRS} ${PROT_SODIUM_INCLUDE})
target_link_libraries(argus_protegidos PRIVATE ${PROT_JSONCPP_LIBRARIES} ${PROT_SODIUM_LIB})

option(ARGUS_PROTEGIDOS_TESTS "Tests de libs/protegidos" OFF)
if(ARGUS_PROTEGIDOS_TESTS)
    enable_testing()
    # rangos (header-only, CHECK propio) [PROTEGIDOS-D300]
    add_executable(test_protegidos_rangos tests/test_protegidos_rangos.cpp)
    target_link_libraries(test_protegidos_rangos PRIVATE argus_protegidos)
    add_test(NAME test_protegidos_rangos COMMAND test_protegidos_rangos)
    # verificador (ADR-060 8e.1a): clave desechable generada en el propio test, CHECK propio
    add_executable(test_protegidos_manifiesto tests/test_protegidos_manifiesto.cpp)
    target_include_directories(test_protegidos_manifiesto PRIVATE ${PROT_JSONCPP_INCLUDE_DIRS} ${PROT_SODIUM_INCLUDE})
    target_link_libraries(test_protegidos_manifiesto PRIVATE argus_protegidos ${PROT_JSONCPP_LIBRARIES} ${PROT_SODIUM_LIB})
    add_test(NAME test_protegidos_manifiesto COMMAND test_protegidos_manifiesto)
endif()
'''

NUEVO_2_RUTA = 'libs/protegidos/include/protegidos/rangos.hpp'
NUEVO_2_SHA = '6fbe8b3578a39d7ffec43e676894c154ea659cdce4c288c0c41f051031f1e3db'
NUEVO_2 = r'''// libs/protegidos/include/protegidos/rangos.hpp (antes firewall-acl-agent/include/firewall/ddos_protegidos.hpp; libs/protegidos, ADR-060 F-B)
// [PROTEGIDOS-D300] rangos protegidos: un DROP de la cabeza DDoS cuyo ORIGEN cae en un rango protegido se registra
// como ALERTA_PROTEGIDO y nunca se convierte en bloqueo automatico; ningun camino lo mete en el blacklist.
// [PROTEGIDOS-MANIFIESTO-D318] ADR-060: los rangos salen SOLO del manifiesto firmado verificado
// (protegidos/manifiesto.hpp). Fuera ddos_protegidos de firewall.json y el defecto RFC 1918 de DAY300: con el
// candado (D6), sin manifiesto verificado no hay bloqueo real del que proteger. La barrera protege por IP siempre
// (D-G). Funciones puras, sin JSON ni red.
#pragma once
#include "argus/ip_cidr_validator.hpp"
#include <arpa/inet.h>
#include <array>
#include <cstdint>
#include <cstring>
#include <ostream>
#include <sstream>  // [PROTEGIDOS-D300]
#include <string>
#include <vector>

namespace argus::protegidos {

// [PROTEGIDOS-MANIFIESTO-D318] INFRAESTRUCTURA (ADR-060 D1): el plano de control de aRGus (etcd, etcd-server, Vault).
enum class CategoriaProtegida : uint8_t { NINGUNA = 0, DMZ = 1, INTRANET = 2, EXTERNOS_CRITICOS = 3, INFRAESTRUCTURA = 4 };

inline const char* nombre_categoria(CategoriaProtegida c) {
    switch (c) {
        case CategoriaProtegida::DMZ: return "dmz";
        case CategoriaProtegida::INTRANET: return "intranet";
        case CategoriaProtegida::EXTERNOS_CRITICOS: return "externos_criticos";
        case CategoriaProtegida::INFRAESTRUCTURA: return "infraestructura";
        default: return "ninguna";
    }
}

struct RangoProtegido {
    bool v6 = false;
    std::array<uint8_t, 16> red{};
    int prefijo = 0;
    CategoriaProtegida cat = CategoriaProtegida::NINGUNA;
    std::string texto;
};

namespace detalle_protegidos {

inline bool a_bytes(const std::string& ip, bool& v6, std::array<uint8_t, 16>& b) {
    b.fill(0);
    in_addr a4{};
    in6_addr a6{};
    if (inet_pton(AF_INET, ip.c_str(), &a4) == 1) {
        v6 = false;
        std::memcpy(b.data(), &a4, 4);
        return true;
    }
    if (inet_pton(AF_INET6, ip.c_str(), &a6) == 1) {
        v6 = true;
        std::memcpy(b.data(), &a6, 16);
        return true;
    }
    return false;
}

inline bool coincide(const std::array<uint8_t, 16>& ip, const std::array<uint8_t, 16>& red, int prefijo) {
    const std::size_t completos = static_cast<std::size_t>(prefijo / 8);
    for (std::size_t i = 0; i < completos; ++i) {
        if (ip[i] != red[i]) return false;
    }
    const int resto = prefijo % 8;
    if (resto == 0) return true;
    const uint8_t mascara = static_cast<uint8_t>(0xFFu << (8 - resto));
    return (ip[completos] & mascara) == (red[completos] & mascara);
}

// Para el log: sin caracteres de control (una entrada invalida del JSON no puede inyectar lineas).
inline std::string saneado(const std::string& s) {
    std::string o;
    for (unsigned char c : s) {
        if (o.size() >= 64) {
            o += "...";
            break;
        }
        o += (c >= 0x20 && c < 0x7f) ? static_cast<char>(c) : '?';
    }
    return o;
}

}  // namespace detalle_protegidos

inline bool parsear_rango(const std::string& cidr, CategoriaProtegida cat, RangoProtegido& out) {
    if (!::argus::is_valid_ip_cidr(cidr)) return false;
    const auto barra = cidr.find('/');
    const std::string ip = (barra == std::string::npos) ? cidr : cidr.substr(0, barra);
    RangoProtegido r;
    if (!detalle_protegidos::a_bytes(ip, r.v6, r.red)) return false;
    r.prefijo = r.v6 ? 128 : 32;
    if (barra != std::string::npos) r.prefijo = std::stoi(cidr.substr(barra + 1));
    // Normaliza la red: bits de host a cero (192.168.100.77/24 -> 192.168.100.0/24).
    for (std::size_t i = 0; i < r.red.size(); ++i) {
        const int bit_ini = static_cast<int>(i) * 8;
        if (bit_ini >= r.prefijo) {
            r.red[i] = 0;
        } else if (bit_ini + 8 > r.prefijo) {
            r.red[i] &= static_cast<uint8_t>(0xFFu << (8 - (r.prefijo - bit_ini)));
        }
    }
    r.cat = cat;
    r.texto = cidr;
    out = r;
    return true;
}

struct RangosProtegidos {
    std::vector<RangoProtegido> rangos;

    // Categoria del primer rango que contiene la IP; NINGUNA si ninguno o si la IP no es valida.
    CategoriaProtegida categoria_de(const std::string& ip) const {
        bool v6 = false;
        std::array<uint8_t, 16> b{};
        if (!detalle_protegidos::a_bytes(ip, v6, b)) return CategoriaProtegida::NINGUNA;
        for (const auto& r : rangos) {
            if (r.v6 == v6 && detalle_protegidos::coincide(b, r.red, r.prefijo)) return r.cat;
        }
        return CategoriaProtegida::NINGUNA;
    }
};

}  // namespace argus::protegidos
'''

NUEVO_3_RUTA = 'libs/protegidos/include/protegidos/manifiesto.hpp'
NUEVO_3_SHA = '62dd1337efa9a577605992b53672355cd877e56a01b3ecc67c7b723cc0783d58'
NUEVO_3 = r'''// libs/protegidos/include/protegidos/manifiesto.hpp (antes firewall/protegidos_manifiesto.hpp; libs/protegidos, ADR-060 F-B) — [PROTEGIDOS-MANIFIESTO-D318] ADR-060 (DEBT-FW-MANIFIESTO-PROTEGIDOS-001), paso 8e.1a.
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
#include "protegidos/rangos.hpp"
#include <array>
#include <cstdint>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <vector>

namespace argus::protegidos {

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
    // [PROTEGIDOS-MANIFIESTO-D318] 8e.1b: los rangos del vigente, ya ordenados (vacíos sin manifiesto). La barrera
    // los consulta en cada DROP de la cabeza DDoS: se construyen una vez por manifiesto, no por evento.
    std::shared_ptr<const RangosProtegidos> rangos() const;
    uint64_t rechazos() const;
    const std::string& hospital_id() const { return hospital_id_; }
    const std::string& planta() const { return planta_; }

private:
    const ClavesProtegidos claves_;
    const std::string hospital_id_;
    const std::string planta_;
    mutable std::mutex m_;
    std::shared_ptr<const ManifiestoVerificado> vigente_;
    std::shared_ptr<const RangosProtegidos> rangos_;
    uint64_t rechazos_ = 0;
};

// [PROTEGIDOS-MANIFIESTO-D318] candado (ADR-060 D6): con la mitigación habilitada, sin manifiesto verificado la
// mitigación no actúa (ni simulada en dry_run: lo simulado es lo que haría de verdad). true = cerrado.
inline bool candado_cerrado(bool mitigacion_habilitada, const ProtegidosVigentes* v) {
    return mitigacion_habilitada && (v == nullptr || !v->verificado());
}

// Caché en disco del último manifiesto verificado (ADR-060 D5.5). Lectura sin seguir enlaces y con tope de tamaño;
// escritura atómica (temporal 0640 + rename). false + error si no se puede.
bool leer_cache_protegidos(const std::string& ruta, std::string& sobre, std::string& error);
bool escribir_cache_protegidos(const std::string& ruta, const std::string& sobre, std::string& error);

// [PROTEGIDOS-INFRA-INCOMPLETA] (D-C): hosts de etcd.endpoints ("https://IPv4:puerto") que no cubre ninguna entrada
// infraestructura del manifiesto. Una entrada de endpoints mal formada se devuelve tal cual (también falta).
std::vector<std::string> infra_sin_cubrir(const ManifiestoVerificado& m, const std::vector<std::string>& endpoints);

}  // namespace argus::protegidos
'''

NUEVO_4_RUTA = 'libs/protegidos/src/manifiesto.cpp'
NUEVO_4_SHA = 'e2a0c7998f94a20549301900ce5b5c74ad0d40af9ad8babce3b9fda7793b397f'
NUEVO_4 = r'''// libs/protegidos/src/manifiesto.cpp (antes firewall-acl-agent/src/core/protegidos_manifiesto.cpp) — [PROTEGIDOS-MANIFIESTO-D318] ADR-060, paso 8e.1a. Ver la cabecera.
#include "protegidos/manifiesto.hpp"

#include <json/json.h>
#include <sodium.h>

#include <algorithm>
#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <set>
#include <sstream>
#include <sys/stat.h>
#include <unistd.h>

namespace argus::protegidos {

namespace {

const char* const kCategoriasManifiesto[] = {"infraestructura", "intranet", "dmz", "externos_criticos"};

CategoriaProtegida categoria_por_nombre(const std::string& n) {
    if (n == "infraestructura") return CategoriaProtegida::INFRAESTRUCTURA;
    if (n == "intranet") return CategoriaProtegida::INTRANET;
    if (n == "dmz") return CategoriaProtegida::DMZ;
    if (n == "externos_criticos") return CategoriaProtegida::EXTERNOS_CRITICOS;
    return CategoriaProtegida::NINGUNA;
}

bool es_hex_min(const std::string& s, std::size_t n) {
    if (s.size() != n) return false;
    return std::all_of(s.begin(), s.end(), [](char c) { return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'); });
}

bool hex_a_32(const std::string& hex, std::array<unsigned char, 32>& out) {
    if (!es_hex_min(hex, 64)) return false;
    std::size_t n = 0;
    return sodium_hex2bin(out.data(), out.size(), hex.data(), hex.size(), nullptr, &n, nullptr) == 0 && n == 32;
}

// [a-z0-9-]{1,64}
bool es_id(const std::string& s) {
    if (s.empty() || s.size() > 64) return false;
    return std::all_of(s.begin(), s.end(), [](char c) { return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-'; });
}

// [A-Za-z0-9._-]{1,15} (IFNAMSIZ - 1)
bool es_interfaz(const std::string& s) {
    if (s.empty() || s.size() > 15) return false;
    return std::all_of(s.begin(), s.end(), [](char c) {
        return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '.' || c == '_' || c == '-';
    });
}

// "" o xx:xx:xx:xx:xx:xx en minúsculas
bool es_mac(const std::string& s) {
    if (s.empty()) return true;
    if (s.size() != 17) return false;
    for (std::size_t i = 0; i < s.size(); ++i) {
        const char c = s[i];
        if (i % 3 == 2) {
            if (c != ':') return false;
        } else if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) {
            return false;
        }
    }
    return true;
}

// Texto imprimible ASCII o UTF-8 sin caracteres de control, de 1 a max bytes.
bool es_texto(const std::string& s, std::size_t max) {
    if (s.empty() || s.size() > max) return false;
    return std::none_of(s.begin(), s.end(), [](char c) {
        const auto u = static_cast<unsigned char>(c);
        return u < 0x20 || u == 0x7f;
    });
}

// AAAA-MM-DDTHH:MM:SSZ
bool es_fecha_utc(const std::string& s) {
    static const char* const forma = "dddd-dd-ddTdd:dd:ddZ";
    if (s.size() != std::strlen(forma)) return false;
    for (std::size_t i = 0; i < s.size(); ++i) {
        if (forma[i] == 'd') {
            if (s[i] < '0' || s[i] > '9') return false;
        } else if (s[i] != forma[i]) {
            return false;
        }
    }
    return true;
}

bool claves_exactas(const Json::Value& o, std::initializer_list<const char*> claves, std::string& sobra) {
    if (!o.isObject()) return false;
    std::set<std::string> esperadas(claves.begin(), claves.end());
    for (const auto& k : o.getMemberNames()) {
        if (esperadas.count(k) == 0) {
            sobra = "campo desconocido '" + detalle_protegidos::saneado(k) + "'";
            return false;
        }
    }
    for (const auto* k : claves) {
        if (!o.isMember(k)) {
            sobra = std::string("falta el campo '") + k + "'";
            return false;
        }
    }
    return true;
}

bool entero(const Json::Value& v) { return v.type() == Json::intValue || v.type() == Json::uintValue; }

bool leer_json_estricto(const std::string& texto, Json::Value& out, std::string& error) {
    Json::CharReaderBuilder b;
    Json::CharReaderBuilder::strictMode(&b.settings_);
    std::unique_ptr<Json::CharReader> r(b.newCharReader());
    std::string errs;
    if (!r->parse(texto.data(), texto.data() + texto.size(), &out, &errs)) {
        error = "JSON inválido: " + detalle_protegidos::saneado(errs);
        return false;
    }
    return true;
}

bool base64_a_bytes(const std::string& b64, std::size_t max, std::string& out) {
    if (b64.empty() || b64.size() > (max / 3 + 1) * 4) return false;
    std::string buf(b64.size(), '\0');
    std::size_t n = 0;
    const char* fin = nullptr;
    if (sodium_base642bin(reinterpret_cast<unsigned char*>(buf.data()), buf.size(), b64.data(), b64.size(), nullptr, &n,
                          &fin, sodium_base64_VARIANT_ORIGINAL) != 0) {
        return false;
    }
    if (fin != b64.data() + b64.size() || n > max) return false;
    buf.resize(n);
    out.swap(buf);
    return true;
}

std::string sha256_hex(const std::string& datos) {
    unsigned char h[crypto_hash_sha256_BYTES];
    crypto_hash_sha256(h, reinterpret_cast<const unsigned char*>(datos.data()), datos.size());
    char hex[crypto_hash_sha256_BYTES * 2 + 1];
    sodium_bin2hex(hex, sizeof hex, h, sizeof h);
    return hex;
}

ResultadoVerificacion rechazo(MotivoRechazo m, std::string detalle) {
    ResultadoVerificacion r;
    r.ok = false;
    r.motivo = m;
    r.detalle = std::move(detalle);
    return r;
}

struct ErrorEntrada {
    MotivoRechazo motivo;
    std::string detalle;
};

// Valida una lista de entradas (comun o una planta). Añade a 'salida' si no es null.
std::optional<ErrorEntrada> validar_entradas(const Json::Value& lista, const std::string& donde, const std::array<int, 5>& lim,
                                             bool es_comun, std::vector<EntradaProtegida>* salida, std::size_t& total) {
    if (!lista.isArray()) return ErrorEntrada{MotivoRechazo::FORMATO, donde + " no es una lista"};
    for (Json::ArrayIndex i = 0; i < lista.size(); ++i) {
        const Json::Value& e = lista[i];
        const std::string w = donde + "[" + std::to_string(i) + "]";
        std::string sobra;
        if (!claves_exactas(e, {"categoria", "cidr", "interfaz", "mac", "motivo"}, sobra)) {
            return ErrorEntrada{MotivoRechazo::FORMATO, w + ": " + (sobra.empty() ? "no es un objeto" : sobra)};
        }
        for (const char* k : {"categoria", "cidr", "interfaz", "mac", "motivo"}) {
            if (!e[k].isString()) return ErrorEntrada{MotivoRechazo::FORMATO, w + "." + k + " no es una cadena"};
        }
        if (++total > kProtegidosMaxEntradas) {
            return ErrorEntrada{MotivoRechazo::FORMATO, "más de " + std::to_string(kProtegidosMaxEntradas) + " entradas"};
        }
        const std::string cat_n = e["categoria"].asString();
        const CategoriaProtegida cat = categoria_por_nombre(cat_n);
        if (cat == CategoriaProtegida::NINGUNA) {
            return ErrorEntrada{MotivoRechazo::FORMATO, w + ".categoria '" + detalle_protegidos::saneado(cat_n) + "' desconocida"};
        }
        const std::string cidr = e["cidr"].asString();
        RangoProtegido r;
        if (cidr.find('/') == std::string::npos || !parsear_rango(cidr, cat, r)) {
            return ErrorEntrada{MotivoRechazo::FORMATO, w + ".cidr '" + detalle_protegidos::saneado(cidr) +
                                                            "' mal formado (IPv4 o IPv6 con prefijo explícito)"};
        }
        {   // sin bits de host: lo firmado es exactamente lo que se aplica
            bool v6 = false;
            std::array<uint8_t, 16> ip{};
            detalle_protegidos::a_bytes(cidr.substr(0, cidr.find('/')), v6, ip);
            if (ip != r.red) {
                return ErrorEntrada{MotivoRechazo::FORMATO, w + ".cidr '" + detalle_protegidos::saneado(cidr) +
                                                                "' tiene bits de host (escriba la red)"};
            }
        }
        const int idx = static_cast<int>(cat);
        if (r.v6 ? (r.prefijo != 128) : (r.prefijo < lim[static_cast<std::size_t>(idx)])) {
            return ErrorEntrada{MotivoRechazo::LIMITE,
                                w + ": " + detalle_protegidos::saneado(cidr) + " más amplio que el límite de " + cat_n + " (" +
                                    (r.v6 ? std::string("IPv6: solo /128") : "/" + std::to_string(lim[static_cast<std::size_t>(idx)])) + ")"};
        }
        const std::string iface = e["interfaz"].asString();
        if (!es_interfaz(iface)) {
            return ErrorEntrada{MotivoRechazo::FORMATO, w + ".interfaz '" + detalle_protegidos::saneado(iface) +
                                                            "' mal formada ([A-Za-z0-9._-], de 1 a 15)"};
        }
        const std::string mac = e["mac"].asString();
        if (!es_mac(mac)) {
            return ErrorEntrada{MotivoRechazo::FORMATO, w + ".mac '" + detalle_protegidos::saneado(mac) +
                                                            "' mal formada (vacía o xx:xx:xx:xx:xx:xx en minúsculas)"};
        }
        const std::string motivo = e["motivo"].asString();
        if (!es_texto(motivo, 200)) {
            return ErrorEntrada{MotivoRechazo::FORMATO, w + ".motivo vacío, de más de 200 bytes o con caracteres de control"};
        }
        if (salida) {
            EntradaProtegida en;
            en.rango = r;
            en.interfaz = iface;
            en.mac = mac;
            en.motivo = motivo;
            en.comun = es_comun;
            salida->push_back(std::move(en));
        }
    }
    return std::nullopt;
}

// Dentro de lo que aplica un firewall (comun + su planta): ni la misma red dos veces en la misma interfaz, ni la misma
// red en dos categorías.
std::optional<std::string> repetidas(const std::vector<EntradaProtegida>& es) {
    for (std::size_t i = 0; i < es.size(); ++i) {
        for (std::size_t j = i + 1; j < es.size(); ++j) {
            const auto& a = es[i].rango;
            const auto& b = es[j].rango;
            if (a.v6 == b.v6 && a.prefijo == b.prefijo && a.red == b.red) {
                if (a.cat != b.cat) return "la red " + a.texto + " aparece en dos categorías";
                if (es[i].interfaz == es[j].interfaz) return "la red " + a.texto + " aparece dos veces en " + es[i].interfaz;
            }
        }
    }
    return std::nullopt;
}

}  // namespace

const char* nombre_motivo(MotivoRechazo m) {
    switch (m) {
        case MotivoRechazo::FORMATO: return "formato";
        case MotivoRechazo::FIRMA: return "firma";
        case MotivoRechazo::VERSION: return "version";
        case MotivoRechazo::HOSPITAL: return "hospital";
        case MotivoRechazo::PLANTA: return "planta";
        case MotivoRechazo::LIMITE: return "limite";
    }
    return "formato";
}

bool claves_protegidos_desde_hex(const std::string& actual_hex, const std::string& siguiente_hex, ClavesProtegidos& out,
                                 std::string& error) {
    ClavesProtegidos c;
    if (!hex_a_32(actual_hex, c.actual)) {
        error = "clave actual mal formada (64 caracteres hex en minúsculas)";
        return false;
    }
    if (!siguiente_hex.empty()) {
        if (!hex_a_32(siguiente_hex, c.siguiente)) {
            error = "clave siguiente mal formada (vacía o 64 caracteres hex en minúsculas)";
            return false;
        }
        if (c.siguiente == c.actual) {
            error = "la clave siguiente es igual a la actual";
            return false;
        }
        c.hay_siguiente = true;
    }
    out = c;
    return true;
}

std::string huella_clave_protegidos(const std::array<unsigned char, 32>& k) {
    return sha256_hex(std::string(reinterpret_cast<const char*>(k.data()), k.size())).substr(0, 16);
}

std::array<std::size_t, 5> ManifiestoVerificado::por_categoria() const {
    std::array<std::size_t, 5> n{};
    for (const auto& e : entradas) ++n[static_cast<std::size_t>(e.rango.cat)];
    return n;
}

RangosProtegidos ManifiestoVerificado::rangos() const {
    RangosProtegidos out;
    for (const auto& e : entradas) out.rangos.push_back(e.rango);
    // categoria_de devuelve la primera coincidencia: infraestructura delante y, después, lo más específico.
    std::stable_sort(out.rangos.begin(), out.rangos.end(), [](const RangoProtegido& a, const RangoProtegido& b) {
        const bool ia = a.cat == CategoriaProtegida::INFRAESTRUCTURA;
        const bool ib = b.cat == CategoriaProtegida::INFRAESTRUCTURA;
        if (ia != ib) return ia;
        return a.prefijo > b.prefijo;
    });
    return out;
}

ResultadoVerificacion verificar_manifiesto(const std::string& sobre, const ClavesProtegidos& claves,
                                           const std::string& hospital_id, const std::string& planta,
                                           uint64_t version_aplicada) {
    if (sodium_init() < 0) return rechazo(MotivoRechazo::FIRMA, "libsodium no inicializa");
    if (sobre.size() > kProtegidosMaxSobreBytes) {
        return rechazo(MotivoRechazo::FORMATO, "sobre de " + std::to_string(sobre.size()) + " bytes (máximo " +
                                                   std::to_string(kProtegidosMaxSobreBytes) + ")");
    }
    // 1. Sobre
    Json::Value s;
    std::string err;
    if (!leer_json_estricto(sobre, s, err)) return rechazo(MotivoRechazo::FORMATO, "sobre: " + err);
    std::string sobra;
    if (!claves_exactas(s, {"formato", "carga_b64", "firma"}, sobra)) {
        return rechazo(MotivoRechazo::FORMATO, "sobre: " + (sobra.empty() ? "no es un objeto" : sobra));
    }
    if (!s["formato"].isString() || s["formato"].asString() != kProtegidosFormato) {
        return rechazo(MotivoRechazo::FORMATO, std::string("sobre: formato distinto de ") + kProtegidosFormato);
    }
    if (!s["carga_b64"].isString() || !s["firma"].isString()) {
        return rechazo(MotivoRechazo::FORMATO, "sobre: carga_b64 y firma tienen que ser cadenas");
    }
    std::string carga;
    if (!base64_a_bytes(s["carga_b64"].asString(), kProtegidosMaxCargaBytes, carga)) {
        return rechazo(MotivoRechazo::FORMATO, "sobre: carga_b64 no es base64 válido o pasa de " +
                                                   std::to_string(kProtegidosMaxCargaBytes) + " bytes");
    }
    // 2. Firma ("vault:vN:<base64 de 64 bytes>"), sobre los bytes exactos, ANTES de interpretar la carga
    const std::string firma = s["firma"].asString();
    std::string firma_b;
    {
        const std::string pre = "vault:v";
        const std::size_t dos = firma.find(':', pre.size());
        const std::string num = (firma.rfind(pre, 0) == 0 && dos != std::string::npos) ? firma.substr(pre.size(), dos - pre.size()) : "";
        const bool num_ok = !num.empty() && num.size() <= 10 && num[0] != '0' &&
                            std::all_of(num.begin(), num.end(), [](char c) { return c >= '0' && c <= '9'; });
        if (!num_ok || !base64_a_bytes(firma.substr(dos + 1), crypto_sign_BYTES, firma_b) || firma_b.size() != crypto_sign_BYTES) {
            return rechazo(MotivoRechazo::FORMATO, "firma mal formada (vault:vN:<base64 de 64 bytes>)");
        }
    }
    const auto* sig = reinterpret_cast<const unsigned char*>(firma_b.data());
    const auto* msg = reinterpret_cast<const unsigned char*>(carga.data());
    std::string clave_usada;
    if (crypto_sign_verify_detached(sig, msg, carga.size(), claves.actual.data()) == 0) {
        clave_usada = "actual";
    } else if (claves.hay_siguiente && crypto_sign_verify_detached(sig, msg, carga.size(), claves.siguiente.data()) == 0) {
        clave_usada = "siguiente";
    } else {
        return rechazo(MotivoRechazo::FIRMA, std::string("la firma no verifica con la clave actual (") +
                                                 huella_clave_protegidos(claves.actual) + ")" +
                                                 (claves.hay_siguiente ? " ni con la siguiente (" + huella_clave_protegidos(claves.siguiente) + ")" : ""));
    }
    // 3. Carga
    Json::Value c;
    if (!leer_json_estricto(carga, c, err)) return rechazo(MotivoRechazo::FORMATO, "carga: " + err);
    if (!claves_exactas(c, {"esquema", "hospital_id", "version", "emitido_utc", "firmante", "motivo", "hash_anterior",
                            "limites", "comun", "plantas"},
                        sobra)) {
        return rechazo(MotivoRechazo::FORMATO, "carga: " + (sobra.empty() ? "no es un objeto" : sobra));
    }
    if (!entero(c["esquema"]) || !c["esquema"].isUInt64() || c["esquema"].asUInt64() != 1) {
        return rechazo(MotivoRechazo::FORMATO, "carga: esquema distinto de 1");
    }
    if (!c["hospital_id"].isString() || !es_id(c["hospital_id"].asString())) {
        return rechazo(MotivoRechazo::FORMATO, "carga: hospital_id mal formado ([a-z0-9-], de 1 a 64)");
    }
    if (!entero(c["version"]) || !c["version"].isUInt64() || c["version"].asUInt64() < 1) {
        return rechazo(MotivoRechazo::FORMATO, "carga: version tiene que ser un entero >= 1");
    }
    if (!c["emitido_utc"].isString() || !es_fecha_utc(c["emitido_utc"].asString())) {
        return rechazo(MotivoRechazo::FORMATO, "carga: emitido_utc mal formado (AAAA-MM-DDTHH:MM:SSZ)");
    }
    if (!c["firmante"].isString() || !es_texto(c["firmante"].asString(), 128)) {
        return rechazo(MotivoRechazo::FORMATO, "carga: firmante vacío, de más de 128 bytes o con caracteres de control");
    }
    if (!c["motivo"].isString() || !es_texto(c["motivo"].asString(), 200)) {
        return rechazo(MotivoRechazo::FORMATO, "carga: motivo vacío, de más de 200 bytes o con caracteres de control");
    }
    if (!c["hash_anterior"].isString() || !(c["hash_anterior"].asString().empty() || es_hex_min(c["hash_anterior"].asString(), 64))) {
        return rechazo(MotivoRechazo::FORMATO, "carga: hash_anterior tiene que ser vacío o 64 hex en minúsculas");
    }
    std::array<int, 5> lim{};
    {
        const Json::Value& l = c["limites"];
        if (!claves_exactas(l, {"infraestructura", "intranet", "dmz", "externos_criticos"}, sobra)) {
            return rechazo(MotivoRechazo::FORMATO, "carga: limites: " + (sobra.empty() ? "no es un objeto" : sobra));
        }
        for (const char* k : kCategoriasManifiesto) {
            if (!entero(l[k]) || !l[k].isInt()) return rechazo(MotivoRechazo::FORMATO, std::string("carga: limites.") + k + " no es un entero");
            const int v = l[k].asInt();
            const bool infra = std::string(k) == "infraestructura";
            if (infra ? (v != 32) : (v < kProtegidosLimiteMin || v > 32)) {
                return rechazo(MotivoRechazo::LIMITE, std::string("carga: limites.") + k + "=" + std::to_string(v) +
                                                          (infra ? " (infraestructura: solo 32)" : " fuera de [8, 32]"));
            }
            lim[static_cast<std::size_t>(categoria_por_nombre(k))] = v;
        }
    }
    const Json::Value& plantas = c["plantas"];
    if (!plantas.isObject()) return rechazo(MotivoRechazo::FORMATO, "carga: plantas no es un objeto");
    std::size_t total = 0;
    // Todo el documento se valida entero: todos los firewalls del hospital aceptan o rechazan el mismo manifiesto.
    if (auto e = validar_entradas(c["comun"], "comun", lim, true, nullptr, total)) return rechazo(e->motivo, "carga: " + e->detalle);
    for (const auto& p : plantas.getMemberNames()) {
        if (!es_id(p)) return rechazo(MotivoRechazo::FORMATO, "carga: planta '" + detalle_protegidos::saneado(p) + "' mal formada ([a-z0-9-], de 1 a 64)");
        if (auto e = validar_entradas(plantas[p], "plantas." + p, lim, false, nullptr, total)) return rechazo(e->motivo, "carga: " + e->detalle);
    }
    // 4. Para ESTE firewall
    if (c["hospital_id"].asString() != hospital_id) {
        return rechazo(MotivoRechazo::HOSPITAL, "manifiesto de '" + c["hospital_id"].asString() + "', este firewall es de '" +
                                                    detalle_protegidos::saneado(hospital_id) + "'");
    }
    const uint64_t version = c["version"].asUInt64();
    if (version <= version_aplicada) {
        return rechazo(MotivoRechazo::VERSION, "version " + std::to_string(version) + " <= la aplicada " + std::to_string(version_aplicada));
    }
    if (!plantas.isMember(planta)) {
        return rechazo(MotivoRechazo::PLANTA, "el manifiesto no trae la planta '" + detalle_protegidos::saneado(planta) + "'");
    }
    auto m = std::make_shared<ManifiestoVerificado>();
    std::size_t total2 = 0;
    validar_entradas(c["comun"], "comun", lim, true, &m->entradas, total2);
    validar_entradas(plantas[planta], "plantas." + planta, lim, false, &m->entradas, total2);
    if (auto r = repetidas(m->entradas)) return rechazo(MotivoRechazo::FORMATO, "carga: " + *r);
    m->version = version;
    m->hospital_id = c["hospital_id"].asString();
    m->planta = planta;
    m->firmante = c["firmante"].asString();
    m->emitido_utc = c["emitido_utc"].asString();
    m->motivo = c["motivo"].asString();
    m->hash_anterior = c["hash_anterior"].asString();
    m->clave = clave_usada;
    m->sha256_carga = sha256_hex(carga);
    m->sobre = sobre;
    m->limites = lim;
    ResultadoVerificacion r;
    r.ok = true;
    r.manifiesto = m;
    return r;
}

std::string resumen_manifiesto(const ManifiestoVerificado& m) {
    const auto n = m.por_categoria();
    std::ostringstream o;
    o << "[PROTEGIDOS-MANIFIESTO] verificado version=" << m.version << " clave=" << m.clave
      << " firmante=" << detalle_protegidos::saneado(m.firmante) << " hospital=" << m.hospital_id << " planta=" << m.planta
      << " emitido=" << m.emitido_utc << " entradas=" << m.entradas.size()
      << " (infraestructura=" << n[static_cast<std::size_t>(CategoriaProtegida::INFRAESTRUCTURA)]
      << " intranet=" << n[static_cast<std::size_t>(CategoriaProtegida::INTRANET)]
      << " dmz=" << n[static_cast<std::size_t>(CategoriaProtegida::DMZ)]
      << " externos_criticos=" << n[static_cast<std::size_t>(CategoriaProtegida::EXTERNOS_CRITICOS)] << ")"
      << " sha256=" << m.sha256_carga.substr(0, 16);
    return o.str();
}

ProtegidosVigentes::ProtegidosVigentes(ClavesProtegidos claves, std::string hospital_id, std::string planta)
    : claves_(claves), hospital_id_(std::move(hospital_id)), planta_(std::move(planta)),
      rangos_(std::make_shared<const RangosProtegidos>()) {}

ProtegidosVigentes::Propuesta ProtegidosVigentes::proponer(const std::string& sobre) {
    std::lock_guard<std::mutex> l(m_);
    Propuesta p;
    p.anterior = vigente_;
    p.resultado = verificar_manifiesto(sobre, claves_, hospital_id_, planta_, vigente_ ? vigente_->version : 0);
    if (p.resultado.ok) {
        vigente_ = p.resultado.manifiesto;
        rangos_ = std::make_shared<const RangosProtegidos>(vigente_->rangos());
    } else {
        ++rechazos_;
    }
    return p;
}

ResultadoVerificacion ProtegidosVigentes::reverificar(const std::string& sobre) const {
    std::lock_guard<std::mutex> l(m_);
    if (!vigente_) return verificar_manifiesto(sobre, claves_, hospital_id_, planta_, 0);
    ResultadoVerificacion r = verificar_manifiesto(sobre, claves_, hospital_id_, planta_, vigente_->version - 1);
    if (r.ok && r.manifiesto->sobre != vigente_->sobre) {
        return rechazo(MotivoRechazo::VERSION, "la caché verifica pero no es el manifiesto vigente (version " +
                                                   std::to_string(r.manifiesto->version) + ")");
    }
    return r;
}

std::shared_ptr<const ManifiestoVerificado> ProtegidosVigentes::vigente() const {
    std::lock_guard<std::mutex> l(m_);
    return vigente_;
}

bool ProtegidosVigentes::verificado() const {
    std::lock_guard<std::mutex> l(m_);
    return vigente_ != nullptr;
}

std::shared_ptr<const RangosProtegidos> ProtegidosVigentes::rangos() const {
    std::lock_guard<std::mutex> l(m_);
    return rangos_;
}

uint64_t ProtegidosVigentes::rechazos() const {
    std::lock_guard<std::mutex> l(m_);
    return rechazos_;
}

bool leer_cache_protegidos(const std::string& ruta, std::string& sobre, std::string& error) {
    if (ruta.empty() || ruta[0] != '/') {
        error = "ruta no absoluta";
        return false;
    }
    const int fd = ::open(ruta.c_str(), O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) {
        error = std::string("no se puede abrir: ") + std::strerror(errno);
        return false;
    }
    struct stat st {};
    if (::fstat(fd, &st) != 0 || !S_ISREG(st.st_mode)) {
        ::close(fd);
        error = "no es un fichero regular";
        return false;
    }
    if (static_cast<std::size_t>(st.st_size) > kProtegidosMaxSobreBytes) {
        ::close(fd);
        error = "pasa de " + std::to_string(kProtegidosMaxSobreBytes) + " bytes";
        return false;
    }
    std::string buf(static_cast<std::size_t>(st.st_size), '\0');
    std::size_t leidos = 0;
    while (leidos < buf.size()) {
        const ssize_t n = ::read(fd, buf.data() + leidos, buf.size() - leidos);
        if (n <= 0) {
            ::close(fd);
            error = "lectura corta";
            return false;
        }
        leidos += static_cast<std::size_t>(n);
    }
    ::close(fd);
    sobre.swap(buf);
    return true;
}

bool escribir_cache_protegidos(const std::string& ruta, const std::string& sobre, std::string& error) {
    if (ruta.empty() || ruta[0] != '/') {
        error = "ruta no absoluta";
        return false;
    }
    const std::string tmp = ruta + ".tmp";
    ::unlink(tmp.c_str());
    const int fd = ::open(tmp.c_str(), O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0640);
    if (fd < 0) {
        error = std::string("no se puede crear ") + tmp + ": " + std::strerror(errno);
        return false;
    }
    std::size_t escritos = 0;
    while (escritos < sobre.size()) {
        const ssize_t n = ::write(fd, sobre.data() + escritos, sobre.size() - escritos);
        if (n <= 0) {
            ::close(fd);
            ::unlink(tmp.c_str());
            error = "escritura corta";
            return false;
        }
        escritos += static_cast<std::size_t>(n);
    }
    if (::fsync(fd) != 0 || ::close(fd) != 0) {
        ::unlink(tmp.c_str());
        error = "fsync o close";
        return false;
    }
    if (::rename(tmp.c_str(), ruta.c_str()) != 0) {
        ::unlink(tmp.c_str());
        error = std::string("rename: ") + std::strerror(errno);
        return false;
    }
    return true;
}

std::vector<std::string> infra_sin_cubrir(const ManifiestoVerificado& m, const std::vector<std::string>& endpoints) {
    RangosProtegidos infra;
    for (const auto& e : m.entradas) {
        if (e.rango.cat == CategoriaProtegida::INFRAESTRUCTURA) infra.rangos.push_back(e.rango);
    }
    std::vector<std::string> faltan;
    for (const auto& ep : endpoints) {
        const std::string pre = "https://";
        std::string host;
        if (ep.rfind(pre, 0) == 0) {
            const std::size_t dos = ep.find(':', pre.size());
            host = ep.substr(pre.size(), dos == std::string::npos ? std::string::npos : dos - pre.size());
        }
        if (host.empty() || infra.categoria_de(host) != CategoriaProtegida::INFRAESTRUCTURA) faltan.push_back(ep);
    }
    return faltan;
}

}  // namespace argus::protegidos
'''

NUEVO_5_RUTA = 'libs/protegidos/tests/test_protegidos_rangos.cpp'
NUEVO_5_SHA = '12d987dec9df9131a1d5d8fe4ae05365b141789f8d99676bced9626f119c9dde'
NUEVO_5 = r'''// test_protegidos_rangos.cpp (antes test_ddos_protegidos.cpp del firewall) — [PROTEGIDOS-D300] rangos protegidos: análisis de CIDR y pertenencia. Standalone, CHECK propio.
// [PROTEGIDOS-MANIFIESTO-D318] ADR-060: los rangos salen solo del manifiesto firmado (test_protegidos_manifiesto.cpp);
// fuera construir_rangos_protegidos y el defecto RFC 1918, y con ellos sus casos.
#include "protegidos/rangos.hpp"
#include <iostream>
#include <string>
#include <vector>

using namespace argus::protegidos;
using C = CategoriaProtegida;

static int g_fallos = 0;
static int g_checks = 0;
#define CHECK(c)                                                              \
    do {                                                                      \
        ++g_checks;                                                           \
        if (!(c)) {                                                           \
            std::cerr << "FALLO linea " << __LINE__ << ": " #c << std::endl;  \
            ++g_fallos;                                                       \
        }                                                                     \
    } while (0)

static RangosProtegidos rangos(const std::vector<std::pair<std::string, C>>& v) {
    RangosProtegidos r;
    for (const auto& [cidr, cat] : v) {
        RangoProtegido x;
        if (parsear_rango(cidr, cat, x)) r.rangos.push_back(x);
    }
    return r;
}

int main() {
    // 1. Host único; vecinos no protegidos.
    {
        auto r = rangos({{"192.168.100.61/32", C::INTRANET}, {"192.168.100.20/32", C::INFRAESTRUCTURA}});
        CHECK(r.categoria_de("192.168.100.61") == C::INTRANET);
        CHECK(r.categoria_de("192.168.100.20") == C::INFRAESTRUCTURA);
        CHECK(r.categoria_de("192.168.100.50") == C::NINGUNA);
        CHECK(std::string(nombre_categoria(C::INFRAESTRUCTURA)) == "infraestructura");
        CHECK(std::string(nombre_categoria(C::NINGUNA)) == "ninguna");
    }
    // 2. Red /24 y frontera; red no normalizada; IP sin prefijo = host.
    {
        auto r = rangos({{"192.168.100.77/24", C::DMZ}, {"10.1.2.3", C::INTRANET}});
        CHECK(r.categoria_de("192.168.100.1") == C::DMZ);
        CHECK(r.categoria_de("192.168.100.254") == C::DMZ);
        CHECK(r.categoria_de("192.168.101.1") == C::NINGUNA);
        CHECK(r.categoria_de("10.1.2.3") == C::INTRANET);
        CHECK(r.categoria_de("10.1.2.4") == C::NINGUNA);
        RangoProtegido x;
        CHECK(parsear_rango("192.168.100.77/24", C::DMZ, x) && x.red[3] == 0 && x.prefijo == 24);
    }
    // 3. Prefijo no múltiplo de 8 (/12).
    {
        auto r = rangos({{"172.16.0.0/12", C::EXTERNOS_CRITICOS}});
        CHECK(r.categoria_de("172.31.255.255") == C::EXTERNOS_CRITICOS);
        CHECK(r.categoria_de("172.32.0.1") == C::NINGUNA);
        CHECK(r.categoria_de("172.15.255.255") == C::NINGUNA);
    }
    // 4. IPv6 /128 y /64; las familias no se mezclan.
    {
        auto r = rangos({{"2001:db8:1:2::/64", C::INTRANET}, {"fd00::20/128", C::INFRAESTRUCTURA}});
        CHECK(r.categoria_de("2001:db8:1:2::abcd") == C::INTRANET);
        CHECK(r.categoria_de("2001:db8:1:3::1") == C::NINGUNA);
        CHECK(r.categoria_de("fd00::20") == C::INFRAESTRUCTURA);
        CHECK(r.categoria_de("fd00::21") == C::NINGUNA);
        CHECK(r.categoria_de("192.168.1.1") == C::NINGUNA);
    }
    // 5. Entradas inválidas: parsear_rango las rechaza (nunca protege por error).
    {
        RangoProtegido x;
        for (const std::string& e : {std::string("999.1.1.1"), std::string("10.0.0.0/33"), std::string("abc"),
                                     std::string("1.2.3.4;rm -rf /"), std::string("1.2.3.4\nINYECTADO"),
                                     std::string("::/129"), std::string("")}) {
            CHECK(!parsear_rango(e, C::INTRANET, x));
        }
    }
    // 6. IP de consulta inválida o vacía: NINGUNA; sin rangos, nada protegido.
    {
        auto r = rangos({{"10.0.0.0/8", C::INTRANET}});
        CHECK(r.categoria_de("") == C::NINGUNA);
        CHECK(r.categoria_de("no-es-ip") == C::NINGUNA);
        RangosProtegidos vacio;
        CHECK(vacio.categoria_de("10.1.2.3") == C::NINGUNA);
    }
    // 7. Primera coincidencia gana (el manifiesto ordena: infraestructura delante, luego lo más específico).
    {
        auto r = rangos({{"10.0.0.0/8", C::DMZ}, {"10.1.0.0/16", C::INTRANET}});
        CHECK(r.categoria_de("10.1.2.3") == C::DMZ);
    }
    // 8. El log no se rompe con entradas hostiles.
    {
        const std::string s = detalle_protegidos::saneado("a\nb\x01" + std::string(100, 'x'));
        CHECK(s.find('\n') == std::string::npos && s.size() <= 67);
    }

    if (g_fallos != 0) {
        std::cerr << "test_protegidos_rangos: " << g_fallos << " FALLOS de " << g_checks << " comprobaciones" << std::endl;
        return 1;
    }
    std::cout << "OK test_protegidos_rangos: " << g_checks << " comprobaciones" << std::endl;
    return 0;
}
'''

NUEVO_6_RUTA = 'libs/protegidos/tests/test_protegidos_manifiesto.cpp'
NUEVO_6_SHA = 'e670e565bced1d7ac04c265e3c874c5bffc79dbbc374ade20384fb5d303ac016'
NUEVO_6 = r'''// test_protegidos_manifiesto.cpp — [PROTEGIDOS-MANIFIESTO-D318] ADR-060 8e.1a. Standalone, CHECK propio.
// Clave desechable generada aquí (tests unitarios, DAY316). El formato de firma es el de Vault transit (vault:vN:<b64>);
// la compatibilidad real con Vault 2.2.1 se midió en el banco DAY318 (BACKLOG [PROTEGIDOS-PUBKEY-D318]).
#include "protegidos/manifiesto.hpp"

#include <sodium.h>

#include <cstdio>
#include <iostream>
#include <string>
#include <unistd.h>

using namespace argus::protegidos;
using C = CategoriaProtegida;
using M = MotivoRechazo;

static int g_fallos = 0;
static int g_checks = 0;
#define CHECK(c)                                                              \
    do {                                                                      \
        ++g_checks;                                                           \
        if (!(c)) {                                                           \
            std::cerr << "FALLO linea " << __LINE__ << ": " #c << std::endl;  \
            ++g_fallos;                                                       \
        }                                                                     \
    } while (0)

struct Par {
    unsigned char pk[crypto_sign_PUBLICKEYBYTES];
    unsigned char sk[crypto_sign_SECRETKEYBYTES];
    Par() { crypto_sign_keypair(pk, sk); }
    std::string hex() const {
        char h[crypto_sign_PUBLICKEYBYTES * 2 + 1];
        sodium_bin2hex(h, sizeof h, pk, sizeof pk);
        return h;
    }
};

static std::string b64(const std::string& d) {
    std::string o(sodium_base64_ENCODED_LEN(d.size(), sodium_base64_VARIANT_ORIGINAL), '\0');
    sodium_bin2base64(o.data(), o.size(), reinterpret_cast<const unsigned char*>(d.data()), d.size(),
                      sodium_base64_VARIANT_ORIGINAL);
    o.resize(o.size() - 1);
    return o;
}

static std::string firmar(const Par& p, const std::string& carga, int v = 1) {
    unsigned char sig[crypto_sign_BYTES];
    crypto_sign_detached(sig, nullptr, reinterpret_cast<const unsigned char*>(carga.data()), carga.size(), p.sk);
    return "vault:v" + std::to_string(v) + ":" + b64(std::string(reinterpret_cast<const char*>(sig), sizeof sig));
}

static std::string sobre(const std::string& carga, const std::string& firma, const std::string& extra = "") {
    return "{\"formato\":\"argus-protegidos/v1\",\"carga_b64\":\"" + b64(carga) + "\",\"firma\":\"" + firma + "\"" + extra + "}";
}

static std::string entrada(const std::string& cat, const std::string& cidr, const std::string& iface = "eth2",
                           const std::string& mac = "", const std::string& motivo = "prueba") {
    return "{\"categoria\":\"" + cat + "\",\"cidr\":\"" + cidr + "\",\"interfaz\":\"" + iface + "\",\"mac\":\"" + mac +
           "\",\"motivo\":\"" + motivo + "\"}";
}

static std::string carga(uint64_t version, const std::string& planta_lab, const std::string& comun = "",
                         const std::string& limites = "{\"infraestructura\":32,\"intranet\":24,\"dmz\":24,\"externos_criticos\":32}",
                         const std::string& hospital = "hospital-lab", const std::string& extra = "",
                         const std::string& otras_plantas = "") {
    return "{\"esquema\":1,\"hospital_id\":\"" + hospital + "\",\"version\":" + std::to_string(version) +
           ",\"emitido_utc\":\"2026-11-05T08:00:00Z\",\"firmante\":\"argus-infra\",\"motivo\":\"alta del lab\","
           "\"hash_anterior\":\"\",\"limites\":" + limites + ",\"comun\":[" + comun + "],\"plantas\":{\"lab-vagrant\":[" +
           planta_lab + "]" + otras_plantas + "}" + extra + "}";
}

static bool rech(const ResultadoVerificacion& r, MotivoRechazo m) { return !r.ok && r.motivo == m; }

static const std::string kLab = entrada("infraestructura", "192.168.100.20/32") + "," +
                                entrada("intranet", "192.168.100.61/32");

int main() {
    if (sodium_init() < 0) return 2;
    Par a, b, otra;
    ClavesProtegidos solo_a, a_y_b;
    std::string err;
    CHECK(claves_protegidos_desde_hex(a.hex(), "", solo_a, err));
    CHECK(claves_protegidos_desde_hex(a.hex(), b.hex(), a_y_b, err));
    auto V = [&](const std::string& s, const ClavesProtegidos& k = ClavesProtegidos{}, uint64_t aplicada = 0,
                 const std::string& planta = "lab-vagrant", const std::string& hosp = "hospital-lab") {
        return verificar_manifiesto(s, k.actual == std::array<unsigned char, 32>{} ? a_y_b : k, hosp, planta, aplicada);
    };

    // 1. Válido con la actual: entradas, categorías, rangos, sha256, resumen
    {
        const std::string c = carga(1, kLab);
        auto r = V(sobre(c, firmar(a, c)), solo_a);
        CHECK(r.ok);
        if (r.ok) {
            const auto& m = *r.manifiesto;
            CHECK(m.version == 1 && m.clave == "actual" && m.hospital_id == "hospital-lab" && m.planta == "lab-vagrant");
            CHECK(m.entradas.size() == 2);
            const auto n = m.por_categoria();
            CHECK(n[static_cast<std::size_t>(C::INFRAESTRUCTURA)] == 1 && n[static_cast<std::size_t>(C::INTRANET)] == 1);
            const auto rg = m.rangos();
            CHECK(rg.categoria_de("192.168.100.20") == C::INFRAESTRUCTURA);
            CHECK(rg.categoria_de("192.168.100.61") == C::INTRANET);
            CHECK(rg.categoria_de("192.168.100.50") == C::NINGUNA);
            CHECK(m.entradas[0].interfaz == "eth2");
            unsigned char h[crypto_hash_sha256_BYTES];
            crypto_hash_sha256(h, reinterpret_cast<const unsigned char*>(c.data()), c.size());
            char hx[65];
            sodium_bin2hex(hx, sizeof hx, h, sizeof h);
            CHECK(m.sha256_carga == hx);
            const std::string res = resumen_manifiesto(m);
            CHECK(res.find("version=1 clave=actual") != std::string::npos);
            CHECK(res.find("(infraestructura=1 intranet=1 dmz=0 externos_criticos=0)") != std::string::npos);
        }
    }
    // 2. Firmado con la siguiente: vale con dos ranuras, no con una
    {
        const std::string c = carga(1, kLab);
        auto r = V(sobre(c, firmar(b, c, 2)), a_y_b);
        CHECK(r.ok && r.manifiesto->clave == "siguiente");
        auto r1 = V(sobre(c, firmar(b, c, 2)), solo_a);
        CHECK(!r1.ok && r1.motivo == M::FIRMA);
    }
    // 3. Otra clave; carga alterada un byte; firma alterada un bit; firma truncada
    {
        const std::string c = carga(1, kLab);
        auto r = V(sobre(c, firmar(otra, c)));
        CHECK(!r.ok && r.motivo == M::FIRMA);
        std::string c2 = c;
        c2[c2.find("\"version\":1") + 10] = '2';
        auto r2 = V(sobre(c2, firmar(a, c)));
        CHECK(!r2.ok && r2.motivo == M::FIRMA);
        unsigned char sig[crypto_sign_BYTES];
        crypto_sign_detached(sig, nullptr, reinterpret_cast<const unsigned char*>(c.data()), c.size(), a.sk);
        sig[10] ^= 1;
        auto r3 = V(sobre(c, "vault:v1:" + b64(std::string(reinterpret_cast<const char*>(sig), sizeof sig))));
        CHECK(!r3.ok && r3.motivo == M::FIRMA);
        auto r4 = V(sobre(c, "vault:v1:" + b64(std::string(reinterpret_cast<const char*>(sig), 63))));
        CHECK(!r4.ok && r4.motivo == M::FORMATO);
        for (const std::string& f : {std::string("v1:abc"), std::string("vault:v0:") + firmar(a, c).substr(9),
                                    std::string("vault:vx:") + firmar(a, c).substr(9), std::string("")}) {
            auto rf = V(sobre(c, f));
            CHECK(!rf.ok && rf.motivo == M::FORMATO);
        }
    }
    // 4. Versión igual y menor que la aplicada; mayor sí
    {
        const std::string c = carga(5, kLab);
        const std::string s = sobre(c, firmar(a, c));
        CHECK(rech(V(s, solo_a, 5), M::VERSION));
        CHECK(rech(V(s, solo_a, 7), M::VERSION));
        CHECK(V(s, solo_a, 4).ok);
    }
    // 5. Otro hospital; planta ausente; otra planta no se mezcla
    {
        const std::string c = carga(1, kLab, "", "{\"infraestructura\":32,\"intranet\":24,\"dmz\":24,\"externos_criticos\":32}",
                                    "hospital-otro");
        auto r = V(sobre(c, firmar(a, c)));
        CHECK(!r.ok && r.motivo == M::HOSPITAL);
        const std::string c2 = carga(1, kLab, entrada("externos_criticos", "203.0.113.10/32", "eth1"),
                                     "{\"infraestructura\":32,\"intranet\":24,\"dmz\":24,\"externos_criticos\":32}", "hospital-lab",
                                     "", ",\"planta-2\":[" + entrada("dmz", "10.2.0.0/24") + "]");
        auto r2 = V(sobre(c2, firmar(a, c2)), solo_a, 0, "planta-3");
        CHECK(!r2.ok && r2.motivo == M::PLANTA);
        auto r3 = V(sobre(c2, firmar(a, c2)), solo_a, 0, "lab-vagrant");
        CHECK(r3.ok && r3.manifiesto->entradas.size() == 3);
        if (r3.ok) {
            CHECK(r3.manifiesto->entradas[0].comun && !r3.manifiesto->entradas[1].comun);
            CHECK(r3.manifiesto->rangos().categoria_de("10.2.0.1") == C::NINGUNA);  // de planta-2, no de esta
            CHECK(r3.manifiesto->rangos().categoria_de("203.0.113.10") == C::EXTERNOS_CRITICOS);
        }
        auto r4 = V(sobre(c2, firmar(a, c2)), solo_a, 0, "planta-2");
        CHECK(r4.ok && r4.manifiesto->entradas.size() == 2);
    }
    // 6. Límites: infraestructura /31; intranet /23 con límite 24; IPv6 /64 y /128; limites mal declarados
    {
        const std::string c = carga(1, entrada("infraestructura", "192.168.100.20/31"));
        CHECK(rech(V(sobre(c, firmar(a, c))), M::LIMITE));
        const std::string c2 = carga(1, entrada("intranet", "192.168.100.0/23"));
        CHECK(rech(V(sobre(c2, firmar(a, c2))), M::LIMITE));
        const std::string c3 = carga(1, entrada("intranet", "192.168.100.0/24"));
        CHECK(V(sobre(c3, firmar(a, c3))).ok);
        const std::string c4 = carga(1, entrada("infraestructura", "fd00::20/128"));
        CHECK(V(sobre(c4, firmar(a, c4))).ok);
        const std::string c5 = carga(1, entrada("intranet", "fd00::/64"));
        CHECK(rech(V(sobre(c5, firmar(a, c5))), M::LIMITE));
        for (const std::string& l : {std::string("{\"infraestructura\":31,\"intranet\":24,\"dmz\":24,\"externos_criticos\":32}"),
                                    std::string("{\"infraestructura\":32,\"intranet\":4,\"dmz\":24,\"externos_criticos\":32}"),
                                    std::string("{\"infraestructura\":32,\"intranet\":33,\"dmz\":24,\"externos_criticos\":32}")}) {
            const std::string cl = carga(1, kLab, "", l);
            CHECK(rech(V(sobre(cl, firmar(a, cl))), M::LIMITE));
        }
        const std::string cf = carga(1, kLab, "", "{\"infraestructura\":32,\"intranet\":24,\"dmz\":24}");
        CHECK(rech(V(sobre(cf, firmar(a, cf))), M::FORMATO));
    }
    // 7. Entradas mal formadas: sin interfaz, interfaz/MAC/categoría/cidr malos, bits de host, sin prefijo, repetidas
    {
        const std::string sin_iface = "{\"categoria\":\"intranet\",\"cidr\":\"192.168.100.61/32\",\"mac\":\"\",\"motivo\":\"x\"}";
        for (const std::string& e : {sin_iface, entrada("intranet", "192.168.100.61/32", ""),
                                    entrada("intranet", "192.168.100.61/32", "eth2;rm"),
                                    entrada("intranet", "192.168.100.61/32", "interfaz-demasiado-larga"),
                                    entrada("intranet", "192.168.100.61/32", "eth2", "AA:BB:CC:DD:EE:FF"),
                                    entrada("intranet", "192.168.100.61/32", "eth2", "aa:bb:cc:dd:ee"),
                                    entrada("lan", "192.168.100.61/32"), entrada("intranet", "192.168.100.300/32"),
                                    entrada("intranet", "192.168.100.61/24"), entrada("intranet", "192.168.100.61"),
                                    entrada("intranet", "192.168.100.61/32", "eth2", "", ""),
                                    entrada("intranet", "192.168.100.61/32") + "," + entrada("intranet", "192.168.100.61/32"),
                                    entrada("intranet", "192.168.100.61/32") + "," + entrada("dmz", "192.168.100.61/32", "eth1")}) {
            const std::string c = carga(1, e);
            auto r = V(sobre(c, firmar(a, c)));
            CHECK(!r.ok && r.motivo == M::FORMATO);
            if (r.ok || r.motivo != M::FORMATO) std::cerr << "  entrada: " << e << std::endl;
        }
        // La misma red en dos interfaces (host con dos caminos legítimos) sí vale; con MAC también
        const std::string c = carga(1, entrada("intranet", "192.168.100.61/32") + "," +
                                           entrada("intranet", "192.168.100.61/32", "eth1", "08:00:27:aa:bb:cc"));
        CHECK(V(sobre(c, firmar(a, c))).ok);
        // Una entrada mala en OTRA planta invalida el documento entero (todos los firewalls deciden igual)
        const std::string c2 = carga(1, kLab, "", "{\"infraestructura\":32,\"intranet\":24,\"dmz\":24,\"externos_criticos\":32}",
                                     "hospital-lab", "", ",\"planta-2\":[" + entrada("dmz", "10.0.0.0/8") + "]");
        CHECK(rech(V(sobre(c2, firmar(a, c2))), M::LIMITE));
    }
    // 8. Sobre y carga: campos desconocidos (ranura_clave fuera, D-F), duplicados, formato, esquema, JSON roto
    {
        const std::string c = carga(1, kLab);
        CHECK(rech(V(sobre(c, firmar(a, c), ",\"ranura_clave\":\"actual\"")), M::FORMATO));
        CHECK(rech(V("{\"formato\":\"argus-protegidos/v1\",\"formato\":\"x\",\"carga_b64\":\"" + b64(c) + "\",\"firma\":\"" +
                     firmar(a, c) + "\"}"), M::FORMATO));
        std::string s2 = sobre(c, firmar(a, c));
        s2.replace(s2.find("/v1"), 3, "/v2");
        CHECK(rech(V(s2), M::FORMATO));
        CHECK(rech(V("no es json"), M::FORMATO));
        CHECK(rech(V("[]"), M::FORMATO));
        const std::string ce = carga(1, kLab, "", "{\"infraestructura\":32,\"intranet\":24,\"dmz\":24,\"externos_criticos\":32}",
                                     "hospital-lab", ",\"extra\":1");
        CHECK(rech(V(sobre(ce, firmar(a, ce))), M::FORMATO));
        std::string c2 = carga(1, kLab);
        c2.replace(c2.find("\"esquema\":1"), 11, "\"esquema\":2");
        CHECK(rech(V(sobre(c2, firmar(a, c2))), M::FORMATO));
        std::string c3 = carga(1, kLab);
        c3.replace(c3.find("\"version\":1"), 11, "\"version\":1.0");
        CHECK(rech(V(sobre(c3, firmar(a, c3))), M::FORMATO));
        std::string c4 = carga(1, kLab);
        c4.replace(c4.find("2026-11-05T08:00:00Z"), 20, "2026-11-05 08:00:00");
        CHECK(rech(V(sobre(c4, firmar(a, c4))), M::FORMATO));
        const std::string c5 = "{\"no\":\"es la carga\"";
        CHECK(rech(V(sobre(c5, firmar(a, c5))), M::FORMATO));
        CHECK(V(sobre(c, firmar(a, c)) + " ").ok);   // espacio final: JSON válido
        CHECK(rech(V(sobre(c, firmar(a, c)) + "{}"), M::FORMATO));
    }
    // 9. Claves desde hex
    {
        ClavesProtegidos k;
        CHECK(!claves_protegidos_desde_hex("", "", k, err));
        CHECK(!claves_protegidos_desde_hex(a.hex().substr(1), "", k, err));
        std::string mayus = a.hex();
        for (auto& ch : mayus) ch = static_cast<char>(std::toupper(static_cast<unsigned char>(ch)));
        CHECK(mayus == a.hex() || !claves_protegidos_desde_hex(mayus, "", k, err));
        CHECK(!claves_protegidos_desde_hex(a.hex(), "zz", k, err));
        CHECK(!claves_protegidos_desde_hex(a.hex(), a.hex(), k, err));
        CHECK(huella_clave_protegidos(solo_a.actual).size() == 16);
    }
    // 10. Vigentes: aplica, un rechazo conserva el último verificado (D7), versión monótona, reverificar
    {
        ProtegidosVigentes v(solo_a, "hospital-lab", "lab-vagrant");
        CHECK(!v.verificado());
        const std::string c1 = carga(1, kLab);
        const std::string s1 = sobre(c1, firmar(a, c1));
        auto p1 = v.proponer(s1);
        CHECK(p1.resultado.ok && !p1.anterior && v.verificado() && v.vigente()->version == 1);
        const std::string c2 = carga(2, kLab);
        auto p2 = v.proponer(sobre(c2, firmar(otra, c2)));   // firma mala
        CHECK(!p2.resultado.ok && v.vigente()->version == 1 && v.rechazos() == 1);
        auto p3 = v.proponer(s1);                            // reproducción de la misma versión
        CHECK(!p3.resultado.ok && p3.resultado.motivo == M::VERSION && v.vigente()->version == 1);
        CHECK(v.reverificar(s1).ok);
        auto p4 = v.proponer(sobre(c2, firmar(a, c2)));
        CHECK(p4.resultado.ok && p4.anterior && p4.anterior->version == 1 && v.vigente()->version == 2);
        auto rv = v.reverificar(s1);                         // la caché vieja ya no es la vigente
        CHECK(!rv.ok);
        CHECK(v.reverificar(sobre(c2, firmar(a, c2))).ok);   // la caché es la vigente
        std::string c2b = carga(2, kLab);                    // misma versión, otro contenido, firma válida
        c2b.replace(c2b.find("alta del lab"), 12, "otra cosa!!!");
        CHECK(rech(v.reverificar(sobre(c2b, firmar(a, c2b))), M::VERSION));
        std::string s_mal = sobre(c2, firmar(a, c2));
        s_mal[s_mal.size() - 5] = (s_mal[s_mal.size() - 5] == 'A') ? 'B' : 'A';
        CHECK(!v.reverificar(s_mal).ok);
        CHECK(v.vigente()->version == 2);
    }
    // 10b. [8e.1b] rangos cacheados (vacíos sin manifiesto) y candado (D6)
    {
        ProtegidosVigentes v(solo_a, "hospital-lab", "lab-vagrant");
        CHECK(v.rangos() && v.rangos()->rangos.empty());
        CHECK(candado_cerrado(true, &v) && !candado_cerrado(false, &v) && candado_cerrado(true, nullptr));
        const std::string c1 = carga(1, kLab);
        CHECK(v.proponer(sobre(c1, firmar(a, c1))).resultado.ok);
        CHECK(!candado_cerrado(true, &v));
        const auto r1 = v.rangos();
        CHECK(r1->rangos.size() == 2 && r1->categoria_de("192.168.100.20") == C::INFRAESTRUCTURA);
        const std::string c2 = carga(2, entrada("intranet", "192.168.100.61/32"));
        CHECK(!v.proponer(sobre(c2, firmar(otra, c2))).resultado.ok);
        CHECK(v.rangos() == r1);   // un rechazo no toca los rangos
        CHECK(v.proponer(sobre(c2, firmar(a, c2))).resultado.ok);
        CHECK(v.rangos()->rangos.size() == 1 && v.rangos()->categoria_de("192.168.100.20") == C::NINGUNA);
        CHECK(r1->rangos.size() == 2);   // quien tenía la copia anterior la conserva entera
    }
    // 11. Caché: escribir y leer; ausente; enlace simbólico; tamaño
    {
        char dir[] = "/tmp/test_protegidos_XXXXXX";
        CHECK(mkdtemp(dir) != nullptr);
        const std::string ruta = std::string(dir) + "/protegidos.manifiesto";
        std::string leido;
        CHECK(!leer_cache_protegidos(ruta, leido, err));
        const std::string c = carga(1, kLab);
        const std::string s = sobre(c, firmar(a, c));
        CHECK(escribir_cache_protegidos(ruta, s, err));
        CHECK(leer_cache_protegidos(ruta, leido, err) && leido == s);
        CHECK(escribir_cache_protegidos(ruta, s, err));   // sobrescribe (temporal + rename)
        const std::string enlace = std::string(dir) + "/enlace";
        CHECK(symlink(ruta.c_str(), enlace.c_str()) == 0);
        CHECK(!leer_cache_protegidos(enlace, leido, err));
        CHECK(!leer_cache_protegidos("relativa", leido, err));
        unlink(enlace.c_str());
        unlink(ruta.c_str());
        rmdir(dir);
    }
    // 12. Plano de control ausente (D-C)
    {
        const std::string c = carga(1, kLab);
        auto r = V(sobre(c, firmar(a, c)));
        CHECK(r.ok);
        if (r.ok) {
            CHECK(infra_sin_cubrir(*r.manifiesto, {"https://192.168.100.20:2379"}).empty());
            auto f = infra_sin_cubrir(*r.manifiesto, {"https://192.168.100.20:2379", "https://192.168.100.21:2379"});
            CHECK(f.size() == 1 && f[0] == "https://192.168.100.21:2379");
            CHECK(infra_sin_cubrir(*r.manifiesto, {"https://192.168.100.61:2379"}).size() == 1);   // intranet no basta
            CHECK(infra_sin_cubrir(*r.manifiesto, {"mal"}).size() == 1);
        }
    }
    std::cout << "test_protegidos_manifiesto: " << (g_checks - g_fallos) << "/" << g_checks << " OK" << std::endl;
    return g_fallos == 0 ? 0 : 1;
}
'''

NUEVOS = [(NUEVO_0_RUTA, NUEVO_0_SHA, NUEVO_0), (NUEVO_1_RUTA, NUEVO_1_SHA, NUEVO_1), (NUEVO_2_RUTA, NUEVO_2_SHA, NUEVO_2), (NUEVO_3_RUTA, NUEVO_3_SHA, NUEVO_3), (NUEVO_4_RUTA, NUEVO_4_SHA, NUEVO_4), (NUEVO_5_RUTA, NUEVO_5_SHA, NUEVO_5), (NUEVO_6_RUTA, NUEVO_6_SHA, NUEVO_6)]

BORRADO_0_RUTA = 'firewall-acl-agent/include/firewall/ip_cidr_validator.hpp'
BORRADO_0_SHA = '31bdbac25d7ef7d7fce50623dff3cad1ef8c627ddbf3eb5abae2af0a0e2230e0'

BORRADO_1_RUTA = 'firewall-acl-agent/include/firewall/ddos_protegidos.hpp'
BORRADO_1_SHA = 'fbfea53ff4f95cda3fec887d2347a82a2ccd3cb3a2b7ba5065a04ff04682417e'

BORRADO_2_RUTA = 'firewall-acl-agent/include/firewall/protegidos_manifiesto.hpp'
BORRADO_2_SHA = '082e240b5b38b3f14467d51be1e8a19ae4225ebf8831f2e108e9103a2012968b'

BORRADO_3_RUTA = 'firewall-acl-agent/src/core/protegidos_manifiesto.cpp'
BORRADO_3_SHA = 'b90a9b8430816f0dff7306c0567ec35cc8967e5026ca13288c33ff40334fd843'

BORRADO_4_RUTA = 'firewall-acl-agent/tests/unit/test_ddos_protegidos.cpp'
BORRADO_4_SHA = '9410e7965e6211268c3bbc9d460b86296616c55f95b87b89abd3ef59636d650a'

BORRADO_5_RUTA = 'firewall-acl-agent/tests/unit/test_protegidos_manifiesto.cpp'
BORRADO_5_SHA = 'a8fc2c288b92ef1c442d8c1dcfe52b856f2e0e24ff18f1bc4b4aed9496cc8482'

BORRADOS = [(BORRADO_0_RUTA, BORRADO_0_SHA), (BORRADO_1_RUTA, BORRADO_1_SHA), (BORRADO_2_RUTA, BORRADO_2_SHA), (BORRADO_3_RUTA, BORRADO_3_SHA), (BORRADO_4_RUTA, BORRADO_4_SHA), (BORRADO_5_RUTA, BORRADO_5_SHA)]

CAMBIOS = {
    'firewall-acl-agent/CMakeLists.txt': [
        ('# ============================================================================\n# [PROTEGIDOS-MANIFIESTO-D318] ADR-060: libsodium (verificación Ed25519 del manifiesto de protegidos), la compilada\n# desde el código fuente (1.0.19), como plugin-loader.\n# ============================================================================\nfind_library(SODIUM_LIB sodium PATHS /usr/local/lib /usr/lib NO_DEFAULT_PATH)\nfind_path(SODIUM_INCLUDE sodium.h PATHS /usr/local/include /usr/include NO_DEFAULT_PATH)\nif(NOT SODIUM_LIB OR NOT SODIUM_INCLUDE)\n    message(FATAL_ERROR "[PROTEGIDOS-CLAVE] libsodium no encontrada (lib=${SODIUM_LIB} include=${SODIUM_INCLUDE})")\nendif()\nmessage(STATUS "libsodium: ${SODIUM_LIB}")\n\n',
         '# ============================================================================\n# [PROTEGIDOS-MANIFIESTO-D318] ADR-060 F-B: verificador del manifiesto de protegidos y rangos en libs/protegidos,\n# compartido con el etcd-server. Estática y compilada aquí con las opciones de este binario (ver su CMakeLists.txt).\n# ============================================================================\noption(BUILD_TESTS "Build unit tests" ON)\nset(ARGUS_PROTEGIDOS_TESTS ${BUILD_TESTS} CACHE BOOL "Tests de libs/protegidos" FORCE)\nadd_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../libs/protegidos ${CMAKE_CURRENT_BINARY_DIR}/libs-protegidos)\ninclude_directories(${CMAKE_CURRENT_SOURCE_DIR}/../libs/protegidos/include)\n\n'),
        ('        src/core/clave_csv.cpp           # [FW-CSV-CLAVE-B2-D316] clave HMAC del CSV pedida cada intervalo\n        src/core/protegidos_manifiesto.cpp  # [PROTEGIDOS-MANIFIESTO-D318] verificador del manifiesto (ADR-060)\n        src/core/protegidos_claves.cpp      # [PROTEGIDOS-MANIFIESTO-D318] clave pública compilada (dos ranuras)\n',
         '        src/core/clave_csv.cpp           # [FW-CSV-CLAVE-B2-D316] clave HMAC del CSV pedida cada intervalo\n        src/core/protegidos_claves.cpp      # [PROTEGIDOS-MANIFIESTO-D318] clave pública compilada (dos ranuras)\n'),
        ('\n# [PROTEGIDOS-MANIFIESTO-D318] verificación Ed25519 del manifiesto y clave pública compilada (ADR-060)\ntarget_include_directories(firewall_core PUBLIC ${SODIUM_INCLUDE})\ntarget_link_libraries(firewall_core PUBLIC ${SODIUM_LIB})\ntarget_compile_definitions(firewall_core PRIVATE\n',
         '\n# [PROTEGIDOS-MANIFIESTO-D318] verificador del manifiesto (libs/protegidos) y clave pública compilada (ADR-060)\ntarget_link_libraries(firewall_core PUBLIC argus_protegidos)\ntarget_compile_definitions(firewall_core PRIVATE\n'),
        ('#===----------------------------------------------------------------------===//\n# Testing\n#===----------------------------------------------------------------------===//\n\noption(BUILD_TESTS "Build unit tests" ON)\n\n',
         '#===----------------------------------------------------------------------===//\n# Testing (BUILD_TESTS se declara arriba, con libs/protegidos)\n#===----------------------------------------------------------------------===//\n\n'),
        ('            ${CMAKE_CURRENT_SOURCE_DIR}/include\n    )\n    add_test(NAME test_ip_cidr_validator COMMAND test_ip_cidr_validator)\n\n    # test_ddos_protegidos — DAY300, rangos protegidos de la cabeza DDoS (header-only, CHECK propio) [PROTEGIDOS-D300]\n    add_executable(test_ddos_protegidos\n            tests/unit/test_ddos_protegidos.cpp\n    )\n    target_include_directories(test_ddos_protegidos\n            PRIVATE\n            ${CMAKE_CURRENT_SOURCE_DIR}/include\n    )\n    add_test(NAME test_ddos_protegidos COMMAND test_ddos_protegidos)\n    # [PROTEGIDOS-MANIFIESTO-D318] verificador del manifiesto (ADR-060 8e.1a): clave desechable, CHECK propio\n    add_executable(test_protegidos_manifiesto\n            tests/unit/test_protegidos_manifiesto.cpp\n            src/core/protegidos_manifiesto.cpp\n    )\n    target_include_directories(test_protegidos_manifiesto PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include\n            ${JSONCPP_INCLUDE_DIRS} ${SODIUM_INCLUDE})\n    target_link_libraries(test_protegidos_manifiesto PRIVATE ${JSONCPP_LIBRARIES} ${SODIUM_LIB})\n    add_test(NAME test_protegidos_manifiesto COMMAND test_protegidos_manifiesto)\n    # [PROTEGIDOS-MANIFIESTO-D318] la clave compilada es la de CMake, en las dos ranuras\n    add_executable(test_protegidos_claves\n            tests/unit/test_protegidos_claves.cpp\n            src/core/protegidos_manifiesto.cpp\n            src/core/protegidos_claves.cpp\n    )\n    target_include_directories(test_protegidos_claves PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include\n            ${JSONCPP_INCLUDE_DIRS} ${SODIUM_INCLUDE})\n    target_link_libraries(test_protegidos_claves PRIVATE ${JSONCPP_LIBRARIES} ${SODIUM_LIB})\n    target_compile_definitions(test_protegidos_claves PRIVATE\n            ARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX="${ARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX}"\n            ARGUS_PROTEGIDOS_PUBKEY_SIGUIENTE_HEX="${ARGUS_PROTEGIDOS_PUBKEY_SIGUIENTE_HEX}")\n    add_test(NAME test_protegidos_claves COMMAND test_protegidos_claves)\n# [DDOS-MITIGACION-D301] test de la mitigacion ddos_v2 (mismo patron que test_ddos_protegidos)\n    # test_ddos_mitigacion — DAY300, rangos protegidos de la cabeza DDoS (header-only, CHECK propio) [PROTEGIDOS-D300]\n',
         '            ${CMAKE_CURRENT_SOURCE_DIR}/include\n            ${CMAKE_CURRENT_SOURCE_DIR}/../common/include  # [PROTEGIDOS-MANIFIESTO-D318] argus/ip_cidr_validator.hpp\n    )\n    add_test(NAME test_ip_cidr_validator COMMAND test_ip_cidr_validator)\n\n    # [PROTEGIDOS-MANIFIESTO-D318] test_protegidos_rangos y test_protegidos_manifiesto viven en libs/protegidos\n    # (ARGUS_PROTEGIDOS_TESTS = BUILD_TESTS). Aquí, la clave compilada es la de CMake, en las dos ranuras\n    add_executable(test_protegidos_claves\n            tests/unit/test_protegidos_claves.cpp\n            src/core/protegidos_claves.cpp\n    )\n    target_link_libraries(test_protegidos_claves PRIVATE argus_protegidos)\n    target_compile_definitions(test_protegidos_claves PRIVATE\n            ARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX="${ARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX}"\n            ARGUS_PROTEGIDOS_PUBKEY_SIGUIENTE_HEX="${ARGUS_PROTEGIDOS_PUBKEY_SIGUIENTE_HEX}")\n    add_test(NAME test_protegidos_claves COMMAND test_protegidos_claves)\n# [DDOS-MITIGACION-D301] test de la mitigacion ddos_v2 (mismo patron que test_protegidos_rangos)\n    # test_ddos_mitigacion — DAY300, rangos protegidos de la cabeza DDoS (header-only, CHECK propio) [PROTEGIDOS-D300]\n'),
    ],
    'firewall-acl-agent/include/firewall/batch_processor.hpp': [
        ('#include <optional>  // DAY277-NEVER-PERMANENT\n#include "firewall/ddos_protegidos.hpp"  // [DDOS-MITIGACION-B2-D302] barrera de protegidos\n\n',
         '#include <optional>  // DAY277-NEVER-PERMANENT\n#include "protegidos/rangos.hpp"  // [DDOS-MITIGACION-B2-D302] barrera de protegidos\n\n'),
        ('    /// [DDOS-MITIGACION-B2-D302] Rangos que NUNCA entran en la blacklist (vacio = sin barrera). Toma mutex_.\n    void set_rangos_protegidos(const RangosProtegidos& rangos);\n    /// [DDOS-MITIGACION-B2-D302] Rechazos de la barrera (entrada + flush) desde el arranque. Toma mutex_.\n',
         '    /// [DDOS-MITIGACION-B2-D302] Rangos que NUNCA entran en la blacklist (vacio = sin barrera). Toma mutex_.\n    void set_rangos_protegidos(const ::argus::protegidos::RangosProtegidos& rangos);\n    /// [DDOS-MITIGACION-B2-D302] Rechazos de la barrera (entrada + flush) desde el arranque. Toma mutex_.\n'),
        ('    std::unordered_map<std::string, std::optional<uint32_t>> pending_penalty_;\n    RangosProtegidos rangos_protegidos_;     ///< [DDOS-MITIGACION-B2-D302] barrera; guardado por mutex_\n    uint64_t rechazos_protegidos_{0};        ///< [DDOS-MITIGACION-B2-D302] guardado por mutex_\n',
         '    std::unordered_map<std::string, std::optional<uint32_t>> pending_penalty_;\n    ::argus::protegidos::RangosProtegidos rangos_protegidos_;     ///< [DDOS-MITIGACION-B2-D302] barrera; guardado por mutex_\n    uint64_t rechazos_protegidos_{0};        ///< [DDOS-MITIGACION-B2-D302] guardado por mutex_\n'),
    ],
    'firewall-acl-agent/include/firewall/config_loader.hpp': [
        ('#include "firewall/ddos_shadow_policy.hpp"  // [DDOS-SHADOW-D293]\n#include "firewall/ddos_protegidos.hpp"  // [PROTEGIDOS-D300]\n\n',
         '#include "firewall/ddos_shadow_policy.hpp"  // [DDOS-SHADOW-D293]\n#include "protegidos/rangos.hpp"  // [PROTEGIDOS-D300]\n\n'),
    ],
    'firewall-acl-agent/include/firewall/zmq_subscriber.hpp': [
        ('#include "firewall/ddos_shadow_policy.hpp"  // [DDOS-SHADOW-D293]\n#include "firewall/protegidos_manifiesto.hpp"  // [PROTEGIDOS-MANIFIESTO-D318] ADR-060\n#include "firewall/ddos_mitigacion.hpp"  // [DDOS-MITIGACION-B2-D302]\n',
         '#include "firewall/ddos_shadow_policy.hpp"  // [DDOS-SHADOW-D293]\n#include "protegidos/manifiesto.hpp"  // [PROTEGIDOS-MANIFIESTO-D318] ADR-060\n#include "firewall/ddos_mitigacion.hpp"  // [DDOS-MITIGACION-B2-D302]\n'),
        ('        /// [PROTEGIDOS-MANIFIESTO-D318] lo vigente (ADR-060). null = nada protegido y candado cerrado\n        std::shared_ptr<::mldefender::firewall::ProtegidosVigentes> protegidos;\n        ::mldefender::firewall::DdosMitigacionParams ddos_mitigacion;  ///< [DDOS-MITIGACION-B2-D302] mitigacion real\n',
         '        /// [PROTEGIDOS-MANIFIESTO-D318] lo vigente (ADR-060). null = nada protegido y candado cerrado\n        std::shared_ptr<::argus::protegidos::ProtegidosVigentes> protegidos;\n        ::mldefender::firewall::DdosMitigacionParams ddos_mitigacion;  ///< [DDOS-MITIGACION-B2-D302] mitigacion real\n'),
    ],
    'firewall-acl-agent/src/api/zmq_subscriber.cpp': [
        ('                              << (!config_.ddos_mitigacion.habilitada ? "deshabilitada"\n                                  : (::mldefender::firewall::candado_cerrado(true, config_.protegidos.get())\n                                         ? "CANDADO" : (config_.dry_run ? "dry_run" : "ACTIVA")))\n',
         '                              << (!config_.ddos_mitigacion.habilitada ? "deshabilitada"\n                                  : (::argus::protegidos::candado_cerrado(true, config_.protegidos.get())\n                                         ? "CANDADO" : (config_.dry_run ? "dry_run" : "ACTIVA")))\n'),
        ('            const auto rg = config_.protegidos ? config_.protegidos->rangos() : nullptr;\n            const auto cat = rg ? rg->categoria_de(nf2.source_ip()) : ::mldefender::firewall::CategoriaProtegida::NINGUNA;\n            if (cat != ::mldefender::firewall::CategoriaProtegida::NINGUNA) {\n                ++prot_alertas_[static_cast<std::size_t>(cat)];\n                if (prot_detalle_ < static_cast<uint64_t>(config_.ddos_shadow.anomalias_detalle_max)) {\n                    ++prot_detalle_;\n                    std::cout << "[SOMBRA-DDOS] ALERTA_PROTEGIDO origen=" << nf2.source_ip()\n                              << " categoria=" << ::mldefender::firewall::nombre_categoria(cat)\n                              << " victima=" << nf2.destination_ip() << " proto=" << nf2.protocol_number()\n',
         '            const auto rg = config_.protegidos ? config_.protegidos->rangos() : nullptr;\n            const auto cat = rg ? rg->categoria_de(nf2.source_ip()) : ::argus::protegidos::CategoriaProtegida::NINGUNA;\n            if (cat != ::argus::protegidos::CategoriaProtegida::NINGUNA) {\n                ++prot_alertas_[static_cast<std::size_t>(cat)];\n                if (prot_detalle_ < static_cast<uint64_t>(config_.ddos_shadow.anomalias_detalle_max)) {\n                    ++prot_detalle_;\n                    std::cout << "[SOMBRA-DDOS] ALERTA_PROTEGIDO origen=" << nf2.source_ip()\n                              << " categoria=" << ::argus::protegidos::nombre_categoria(cat)\n                              << " victima=" << nf2.destination_ip() << " proto=" << nf2.protocol_number()\n'),
        ('            using Estado = ::mldefender::firewall::ResultadoEpisodio::Estado;\n            if (::mldefender::firewall::candado_cerrado(config_.ddos_mitigacion.habilitada, config_.protegidos.get())) {\n                ++mit_candado_;  // [PROTEGIDOS-MANIFIESTO-D318] D6: sin manifiesto verificado, la mitigación no actúa\n',
         '            using Estado = ::mldefender::firewall::ResultadoEpisodio::Estado;\n            if (::argus::protegidos::candado_cerrado(config_.ddos_mitigacion.habilitada, config_.protegidos.get())) {\n                ++mit_candado_;  // [PROTEGIDOS-MANIFIESTO-D318] D6: sin manifiesto verificado, la mitigación no actúa\n'),
    ],
    'firewall-acl-agent/src/core/batch_processor.cpp': [
        ('    for (const auto& ip : pending_ips_) {\n        if (rangos_protegidos_.categoria_de(ip) != ::mldefender::firewall::CategoriaProtegida::NINGUNA) {\n            // [DDOS-MITIGACION-B2-D302] 2.a puerta de la barrera: NINGUN camino mete un protegido en el ipset\n',
         '    for (const auto& ip : pending_ips_) {\n        if (rangos_protegidos_.categoria_de(ip) != ::argus::protegidos::CategoriaProtegida::NINGUNA) {\n            // [DDOS-MITIGACION-B2-D302] 2.a puerta de la barrera: NINGUN camino mete un protegido en el ipset\n'),
        ('        std::array<uint8_t, 16> b{};\n        if (!::mldefender::firewall::detalle_protegidos::a_bytes(ip, v6, b)) {\n            r.estado = ResultadoEpisodio::Estado::IP_INVALIDA;\n            return r;\n        }\n        if (rangos_protegidos_.categoria_de(ip) != ::mldefender::firewall::CategoriaProtegida::NINGUNA) {\n            ++rechazos_protegidos_;\n',
         '        std::array<uint8_t, 16> b{};\n        if (!::argus::protegidos::detalle_protegidos::a_bytes(ip, v6, b)) {\n            r.estado = ResultadoEpisodio::Estado::IP_INVALIDA;\n            return r;\n        }\n        if (rangos_protegidos_.categoria_de(ip) != ::argus::protegidos::CategoriaProtegida::NINGUNA) {\n            ++rechazos_protegidos_;\n'),
        ('\nvoid BatchProcessor::set_rangos_protegidos(const RangosProtegidos& rangos) {\n    std::lock_guard<std::mutex> lock(mutex_);\n',
         '\nvoid BatchProcessor::set_rangos_protegidos(const ::argus::protegidos::RangosProtegidos& rangos) {\n    std::lock_guard<std::mutex> lock(mutex_);\n'),
    ],
    'firewall-acl-agent/src/core/config_loader.cpp': [
        ('#include "firewall/set_name_validator.hpp"\n#include "firewall/ip_cidr_validator.hpp"\n#include <algorithm>\n',
         '#include "firewall/set_name_validator.hpp"\n#include "argus/ip_cidr_validator.hpp"\n#include <algorithm>\n'),
        ('    for (const auto& cidr : config.whitelist_cidrs) {\n        if (!is_valid_ip_cidr(cidr)) {\n            throw std::runtime_error(\n',
         '    for (const auto& cidr : config.whitelist_cidrs) {\n        if (!::argus::is_valid_ip_cidr(cidr)) {\n            throw std::runtime_error(\n'),
    ],
    'firewall-acl-agent/src/core/ipset_wrapper.cpp': [
        ('#include "firewall/comment_validator.hpp"\n#include "firewall/ip_cidr_validator.hpp"\n#include "safe_exec.hpp"\n',
         '#include "firewall/comment_validator.hpp"\n#include "argus/ip_cidr_validator.hpp"\n#include "safe_exec.hpp"\n'),
        ('\n// [H-2 DAY188 is_valid_ip hardened] — lógica MOVIDA a firewall/ip_cidr_validator.hpp\n// (DAY190, DEBT-AUTONOMY-REACTOR-CWE78-001). Este método es ahora un alias de\n// compatibilidad de la API pública; la implementación y su modelo de amenaza viven\n// en el header compartido. NO BORRAR este marcador (idempotencia del parche).\nbool IPSetWrapper::is_valid_ip(const std::string& ip) const { return is_valid_ip_cidr(ip); }\n\n',
         '\n// [H-2 DAY188 is_valid_ip hardened] — lógica MOVIDA a argus/ip_cidr_validator.hpp (common/include)\n// (DAY190, DEBT-AUTONOMY-REACTOR-CWE78-001). Este método es ahora un alias de\n// compatibilidad de la API pública; la implementación y su modelo de amenaza viven\n// en el header compartido. NO BORRAR este marcador (idempotencia del parche).\nbool IPSetWrapper::is_valid_ip(const std::string& ip) const { return ::argus::is_valid_ip_cidr(ip); }\n\n'),
        ('    for (const auto& [cidr, iface] : entradas) {\n        if (!is_valid_ip_cidr(cidr) || cidr.find(\':\') != std::string::npos || !es_interfaz_ipset(iface)) {\n            malas.push_back(cidr + "," + iface);\n',
         '    for (const auto& [cidr, iface] : entradas) {\n        if (!::argus::is_valid_ip_cidr(cidr) || cidr.find(\':\') != std::string::npos || !es_interfaz_ipset(iface)) {\n            malas.push_back(cidr + "," + iface);\n'),
    ],
    'firewall-acl-agent/src/core/protegidos_claves.cpp': [
        ('// convierte una vez. Si aun así llega mal formada, el agente no arranca: no hay defecto sano para una clave de confianza.\n#include "firewall/protegidos_manifiesto.hpp"\n\n',
         '// convierte una vez. Si aun así llega mal formada, el agente no arranca: no hay defecto sano para una clave de confianza.\n#include "protegidos/manifiesto.hpp"\n\n'),
        ('\nnamespace mldefender::firewall {\n\n',
         '\nnamespace argus::protegidos {\n\n'),
        ('\n}  // namespace mldefender::firewall\n',
         '\n}  // namespace argus::protegidos\n'),
    ],
    'firewall-acl-agent/src/main.cpp': [
        ('#include "firewall/batch_processor.hpp"\n#include "firewall/protegidos_manifiesto.hpp"  // [PROTEGIDOS-MANIFIESTO-D318] ADR-060\n#include <fstream>\n',
         '#include "firewall/batch_processor.hpp"\n#include "protegidos/manifiesto.hpp"  // [PROTEGIDOS-MANIFIESTO-D318] ADR-060\n#include <fstream>\n'),
        ('// ═══════════════════════════════════════════════════════════════════════\nusing ::mldefender::firewall::ProtegidosVigentes;\nusing ::mldefender::firewall::ManifiestoVerificado;\nusing ::mldefender::firewall::candado_cerrado;\nusing ::mldefender::firewall::claves_protegidos_compiladas;\n\n// El set hash:net,iface existe y es de ese tipo (lo crea si falta). false = sin exención del kernel (solo barrera).\nstatic bool protegidos_preparar_set(IPSetWrapper& ipset, const FirewallAgentConfig& config) {\n    const auto& pc = config.protegidos;\n    const auto& k = claves_protegidos_compiladas();\n    std::cout << "[PROTEGIDOS-CLAVE] actual huella=" << ::mldefender::firewall::huella_clave_protegidos(k.actual)\n              << (k.hay_siguiente ? " siguiente huella=" + ::mldefender::firewall::huella_clave_protegidos(k.siguiente)\n                                  : std::string(" siguiente=ninguna"))\n',
         '// ═══════════════════════════════════════════════════════════════════════\nusing ::argus::protegidos::ProtegidosVigentes;\nusing ::argus::protegidos::ManifiestoVerificado;\nusing ::argus::protegidos::candado_cerrado;\nusing ::argus::protegidos::claves_protegidos_compiladas;\n\n// El set hash:net,iface existe y es de ese tipo (lo crea si falta). false = sin exención del kernel (solo barrera).\nstatic bool protegidos_preparar_set(IPSetWrapper& ipset, const FirewallAgentConfig& config) {\n    const auto& pc = config.protegidos;\n    const auto& k = claves_protegidos_compiladas();\n    std::cout << "[PROTEGIDOS-CLAVE] actual huella=" << ::argus::protegidos::huella_clave_protegidos(k.actual)\n              << (k.hay_siguiente ? " siguiente huella=" + ::argus::protegidos::huella_clave_protegidos(k.siguiente)\n                                  : std::string(" siguiente=ninguna"))\n'),
        ('    c.hashsize = 1024;\n    c.maxelem = static_cast<uint32_t>(::mldefender::firewall::kProtegidosMaxEntradas);\n    c.timeout = 0;\n',
         '    c.hashsize = 1024;\n    c.maxelem = static_cast<uint32_t>(::argus::protegidos::kProtegidosMaxEntradas);\n    c.timeout = 0;\n'),
        ('    }\n    const auto r = ipset.replace_net_iface(set, e, static_cast<uint32_t>(::mldefender::firewall::kProtegidosMaxEntradas));\n    if (r) {\n',
         '    }\n    const auto r = ipset.replace_net_iface(set, e, static_cast<uint32_t>(::argus::protegidos::kProtegidosMaxEntradas));\n    if (r) {\n'),
        ('static void protegidos_infra(const ManifiestoVerificado& m, const FirewallAgentConfig& config) {\n    const auto f = ::mldefender::firewall::infra_sin_cubrir(m, config.protegidos.etcd_endpoints);\n    if (f.empty()) return;\n    std::ostringstream o;\n    for (std::size_t i = 0; i < f.size(); ++i) o << (i ? " " : "") << ::mldefender::firewall::detalle_protegidos::saneado(f[i]);\n    std::cerr << "[PROTEGIDOS-INFRA-INCOMPLETA] etcd.endpoints sin entrada infraestructura en el manifiesto version "\n',
         'static void protegidos_infra(const ManifiestoVerificado& m, const FirewallAgentConfig& config) {\n    const auto f = ::argus::protegidos::infra_sin_cubrir(m, config.protegidos.etcd_endpoints);\n    if (f.empty()) return;\n    std::ostringstream o;\n    for (std::size_t i = 0; i < f.size(); ++i) o << (i ? " " : "") << ::argus::protegidos::detalle_protegidos::saneado(f[i]);\n    std::cerr << "[PROTEGIDOS-INFRA-INCOMPLETA] etcd.endpoints sin entrada infraestructura en el manifiesto version "\n'),
        ('    std::string sobre, err;\n    if (!::mldefender::firewall::leer_cache_protegidos(pc.manifiesto_cache, sobre, err)) {\n        std::cerr << "[PROTEGIDOS-SIN-MANIFIESTO] caché " << pc.manifiesto_cache << ": " << err\n                  << " (hospital=" << pc.hospital_id << " planta=" << pc.despliegue_id << "; candado cerrado)" << std::endl;\n        return;\n    }\n    const auto p = v.proponer(sobre);\n    if (!p.resultado.ok) {\n        std::cerr << "[PROTEGIDOS-MANIFIESTO-RECHAZADO] motivo=" << ::mldefender::firewall::nombre_motivo(p.resultado.motivo)\n                  << " " << p.resultado.detalle << " (caché " << pc.manifiesto_cache << "; candado cerrado)" << std::endl;\n        return;\n    }\n    std::cout << ::mldefender::firewall::resumen_manifiesto(*p.resultado.manifiesto) << " (caché " << pc.manifiesto_cache\n              << ")" << std::endl;\n',
         '    std::string sobre, err;\n    if (!::argus::protegidos::leer_cache_protegidos(pc.manifiesto_cache, sobre, err)) {\n        std::cerr << "[PROTEGIDOS-SIN-MANIFIESTO] caché " << pc.manifiesto_cache << ": " << err\n                  << " (hospital=" << pc.hospital_id << " planta=" << pc.despliegue_id << "; candado cerrado)" << std::endl;\n        return;\n    }\n    const auto p = v.proponer(sobre);\n    if (!p.resultado.ok) {\n        std::cerr << "[PROTEGIDOS-MANIFIESTO-RECHAZADO] motivo=" << ::argus::protegidos::nombre_motivo(p.resultado.motivo)\n                  << " " << p.resultado.detalle << " (caché " << pc.manifiesto_cache << "; candado cerrado)" << std::endl;\n        return;\n    }\n    std::cout << ::argus::protegidos::resumen_manifiesto(*p.resultado.manifiesto) << " (caché " << pc.manifiesto_cache\n              << ")" << std::endl;\n'),
        ('    std::string sobre, err;\n    if (!::mldefender::firewall::leer_cache_protegidos(pc.manifiesto_cache, sobre, err)) {\n        std::cerr << "[PROTEGIDOS-CACHE] no se puede leer " << pc.manifiesto_cache << ": " << err\n                  << "; se conserva en memoria la version " << m->version << " (D7)" << std::endl;\n    } else {\n        const auto r = v.reverificar(sobre);\n        if (!r.ok) {\n            std::cerr << "[PROTEGIDOS-CACHE] la caché ya no verifica (motivo=" << ::mldefender::firewall::nombre_motivo(r.motivo)\n                      << " " << r.detalle << "): se conserva en memoria la version " << m->version\n',
         '    std::string sobre, err;\n    if (!::argus::protegidos::leer_cache_protegidos(pc.manifiesto_cache, sobre, err)) {\n        std::cerr << "[PROTEGIDOS-CACHE] no se puede leer " << pc.manifiesto_cache << ": " << err\n                  << "; se conserva en memoria la version " << m->version << " (D7)" << std::endl;\n    } else {\n        const auto r = v.reverificar(sobre);\n        if (!r.ok) {\n            std::cerr << "[PROTEGIDOS-CACHE] la caché ya no verifica (motivo=" << ::argus::protegidos::nombre_motivo(r.motivo)\n                      << " " << r.detalle << "): se conserva en memoria la version " << m->version\n'),
        ('                            std::cerr << "[CONFIG-DEFAULT] ipsets." << name << ".set_type \'"\n                                      << ::mldefender::firewall::detalle_protegidos::saneado(ipset_cfg.set_type)\n                                      << "\' no admitido (formato: hash:ip | hash:net): se usa hash:ip" << std::endl;\n',
         '                            std::cerr << "[CONFIG-DEFAULT] ipsets." << name << ".set_type \'"\n                                      << ::argus::protegidos::detalle_protegidos::saneado(ipset_cfg.set_type)\n                                      << "\' no admitido (formato: hash:ip | hash:net): se usa hash:ip" << std::endl;\n'),
        ('            for (const auto& r : protegidos->rangos()->rangos) {\n                std::cout << " " << ::mldefender::firewall::nombre_categoria(r.cat) << "=" << r.texto;\n            }\n',
         '            for (const auto& r : protegidos->rangos()->rangos) {\n                std::cout << " " << ::argus::protegidos::nombre_categoria(r.cat) << "=" << r.texto;\n            }\n'),
    ],
    'firewall-acl-agent/tests/unit/test_batch_processor_episodio.cpp': [
        ('#include "firewall/ipset_wrapper.hpp"\n#include "firewall/ddos_protegidos.hpp"\n\nusing namespace mldefender::firewall;\nusing Estado = ResultadoEpisodio::Estado;\n',
         '#include "firewall/ipset_wrapper.hpp"\n#include "protegidos/rangos.hpp"\n\nusing namespace mldefender::firewall;\nusing namespace argus::protegidos;  // [PROTEGIDOS-MANIFIESTO-D318] libs/protegidos\nusing Estado = ResultadoEpisodio::Estado;\n'),
    ],
    'firewall-acl-agent/tests/unit/test_ip_cidr_validator.cpp': [
        ('// Sin gtest: macro CHECK propio (compila en cualquier sitio, como add_newline_guard).\n#include "firewall/ip_cidr_validator.hpp"\n#include <cstdio>\n#include <string>\n\nusing mldefender::firewall::is_valid_ip_cidr;\n\n',
         '// Sin gtest: macro CHECK propio (compila en cualquier sitio, como add_newline_guard).\n#include "argus/ip_cidr_validator.hpp"\n#include <cstdio>\n#include <string>\n\nusing argus::is_valid_ip_cidr;\n\n'),
    ],
    'firewall-acl-agent/tests/unit/test_protegidos_claves.cpp': [
        ('// se usa: la misma que trae la definición, en las dos ranuras. Standalone, CHECK propio.\n#include "firewall/protegidos_manifiesto.hpp"\n\n#include <sodium.h>\n\n#include <iostream>\n#include <string>\n\nusing namespace mldefender::firewall;\n\n',
         '// se usa: la misma que trae la definición, en las dos ranuras. Standalone, CHECK propio.\n#include "protegidos/manifiesto.hpp"\n\n#include <sodium.h>\n\n#include <iostream>\n#include <string>\n\nusing namespace argus::protegidos;\n\n'),
    ],
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    nombre = os.path.basename(sys.argv[0])
    if len(sys.argv) != 3 or sys.argv[1] not in ("--check", "--apply"):
        print(f"uso: {nombre} --check|--apply <raíz del repo>")
        return 2
    modo, raiz = sys.argv[1], sys.argv[2]
    errores, hechos, pendientes = [], [], []
    crear, borrar = {}, []
    for rel, esperado, contenido in NUEVOS:
        b = contenido.encode("utf-8")
        if sha(b) != esperado:
            errores.append(f"{rel}: el contenido embebido no da su sha256 (parcheador dañado)")
            continue
        p = os.path.join(raiz, rel)
        if os.path.exists(p):
            a = sha(open(p, "rb").read())
            if a == esperado:
                hechos.append(f"{rel}: creado")
            else:
                errores.append(f"{rel}: ya existe con otro contenido (sha256 {a})")
        else:
            pendientes.append(f"{rel}: crear")
            crear[rel] = b
    for rel, esperado in BORRADOS:
        p = os.path.join(raiz, rel)
        if not os.path.exists(p):
            hechos.append(f"{rel}: borrado")
            continue
        a = sha(open(p, "rb").read())
        print(f"sha256 previo  {rel}: {a}")
        if a == esperado:
            pendientes.append(f"{rel}: borrar")
            borrar.append(rel)
        else:
            errores.append(f"{rel}: sha256 {a}, no el esperado para borrarlo")
    orig, nuevo = {}, {}
    for rel, cambios in CAMBIOS.items():
        p = os.path.join(raiz, rel)
        if not os.path.isfile(p):
            errores.append(f"no existe {rel}")
            continue
        orig[rel] = open(p, "rb").read()
        print(f"sha256 previo  {rel}: {sha(orig[rel])}")
        t = orig[rel].decode("utf-8")
        for n, (viejo, nv) in enumerate(cambios, 1):
            cv, cn = t.count(viejo), (t.count(nv) if nv else 0)
            if nv and viejo in nv:
                aplicar, hecho = cv == 1 and cn == 0, cn == 1
            elif nv in viejo:
                aplicar, hecho = cv == 1, cv == 0 and (not nv or cn >= 1)
            else:
                aplicar, hecho = cv == 1 and cn == 0, cv == 0 and cn == 1
            if aplicar:
                t = t.replace(viejo, nv)
                pendientes.append(f"{rel}: cambio {n}")
            elif hecho:
                hechos.append(f"{rel}: cambio {n}")
            else:
                errores.append(f"{rel}: cambio {n}: texto viejo {cv} veces, nuevo {cn} veces")
        nuevo[rel] = t.encode("utf-8")
    print(f"ya aplicados ({len(hechos)})")
    for h in hechos:
        print(f"  = {h}")
    print(f"por aplicar  ({len(pendientes)})")
    for h in pendientes:
        print(f"  + {h}")
    if errores:
        for e in errores:
            print(f"FALLA: {e}")
        print("RESULTADO: FALLA (no se ha escrito nada)")
        return 1
    if modo == "--apply":
        for rel, b in crear.items():
            p = os.path.join(raiz, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p + ".d318tmp", "wb") as f:
                f.write(b)
            os.chmod(p + ".d318tmp", 0o644)
            os.replace(p + ".d318tmp", p)
        for rel in CAMBIOS:
            if nuevo[rel] != orig[rel]:
                p = os.path.join(raiz, rel)
                m = os.stat(p).st_mode
                with open(p + ".d318tmp", "wb") as f:
                    f.write(nuevo[rel])
                os.chmod(p + ".d318tmp", m)
                os.replace(p + ".d318tmp", p)
        for rel in borrar:
            os.remove(os.path.join(raiz, rel))
    for rel, esperado, _ in NUEVOS:
        print(f"sha256 nuevo   {rel}: {esperado}")
    for rel in CAMBIOS:
        estado = "igual" if nuevo[rel] == orig[rel] else ("escrito" if modo == "--apply" else "cambiaría")
        print(f"sha256 final   {rel}: {sha(nuevo[rel])} ({estado})")
    print("RESULTADO: PASA" + (" (solo comprobación)" if modo == "--check" else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
