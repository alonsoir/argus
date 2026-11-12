#!/usr/bin/env python3
# d318_8e3b_etcd_server_protegidos.py — DAY318, ADR-060 paso 8e.3b [PROTEGIDOS-MANIFIESTO-D318]: el manifiesto firmado de protegidos
# en el etcd-server (F-A, F-C, F-D). GET /v1/protegidos (ou:firewall-acl-agent, ou:argus-infra) y PUT /v1/protegidos (solo
# ou:argus-infra); el PUT verifica el documento entero (libs/protegidos, modo sin planta) con la clave publica COMPILADA,
# la misma que el firewall, y lo guarda en etcd (protegidos/vigente y protegidos/v/<N>). Bloque protegidos.hospital_id en
# etcd-server.json (Ansible desde argus_hospital_id). La clave compilada pasa a libs/protegidos (argus_protegidos_clave).
# Uso (Mac, raíz del repo):  python3 scripts/etcd_ha/d318_8e3b_etcd_server_protegidos.py --check|--apply <raíz>
# Todo o nada e idempotente: un fichero NUEVO se crea si no existe y se da por hecho si ya tiene su sha256; uno BORRADO
# se borra si tiene el sha256 esperado y se da por hecho si ya no está; cada CAMBIO se aplica si su texto viejo aparece
# una vez y se da por hecho si ya está el nuevo. Si algo no cuadra, no se escribe nada. Imprime los sha256.
import hashlib
import os
import sys

NUEVO_0_RUTA = 'etcd-server/include/etcd_server/protegidos_servidor.hpp'
NUEVO_0_SHA = '70e662cd15f6822bea1513f390af4a368703540e1ee2d50b5ae821a9fdaac423'
NUEVO_0 = r'''#pragma once
// etcd-server/include/etcd_server/protegidos_servidor.hpp — [PROTEGIDOS-MANIFIESTO-D318] ADR-060 paso 8e.3b (F-A, F-C,
// F-D): el manifiesto firmado de protegidos en el etcd-server.
//   - Bloque "protegidos" de etcd-server.json: hospital_id ([a-z0-9-], de 1 a 64). Un etcd-server sirve a UN hospital.
//     Sin valor sano por defecto: ausente o mal formado = defecto (--check-config da 1) y GET/PUT /v1/protegidos
//     responden 503. Ansible lo escribe desde argus_hospital_id del inventario.
//   - Almacén (el etcd del despliegue, mismo prefijo que el registro): protegidos/vigente = el sobre tal cual, y
//     protegidos/v/<N> = cada versión publicada, que no se vuelve a escribir.
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
'''

NUEVO_1_RUTA = 'etcd-server/src/protegidos_servidor.cpp'
NUEVO_1_SHA = '9d56e87b7bb66544c4cf741a27bf1ef91da344fef4b1e5caa0ece6ddfa644a1b'
NUEVO_1 = r'''// etcd-server/src/protegidos_servidor.cpp — [PROTEGIDOS-MANIFIESTO-D318] ADR-060 paso 8e.3b. Ver la cabecera.
#include "etcd_server/protegidos_servidor.hpp"

#include <algorithm>
#include <cstdio>
#include <map>

namespace argus::protegidos {

using ::argus::almacen::Estado;
using nlohmann::json;

namespace {
bool es_id(const std::string& s) {
    return !s.empty() && s.size() <= 64 && std::all_of(s.begin(), s.end(), [](char c) {
        return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-';
    });
}

std::string error_json(const std::string& motivo, const std::string& detalle) {
    return json{{"status", "error"}, {"motivo", motivo}, {"message", detalle}}.dump();
}

constexpr const char* kVigente = "protegidos/vigente";
constexpr const char* kHistorico = "protegidos/v/";
}  // namespace

ResultadoProtegidosConfig parse_protegidos_config(const json& root, std::ostream& aviso, std::ostream& info) {
    ResultadoProtegidosConfig r;
    const json* p = (root.is_object() && root.contains("protegidos")) ? &root["protegidos"] : nullptr;
    if (p != nullptr && p->is_object() && p->contains("hospital_id") && (*p)["hospital_id"].is_string() &&
        es_id((*p)["hospital_id"].get<std::string>())) {
        r.cfg.hospital_id = (*p)["hospital_id"].get<std::string>();
        info << "[ETCD-PROTEGIDOS] protegidos.hospital_id=" << r.cfg.hospital_id << " (JSON)" << std::endl;
        return r;
    }
    r.defectos = 1;
    const char* que = (p == nullptr) ? "protegidos ausente"
                      : !p->is_object() ? "protegidos no es un objeto"
                      : !p->contains("hospital_id") ? "protegidos.hospital_id ausente"
                                                    : "protegidos.hospital_id mal formado";
    aviso << "[CONFIG-DEFAULT] " << que << " ([a-z0-9-], de 1 a 64): sin valor sano por defecto; GET y PUT "
             "/v1/protegidos responderán 503 (ADR-060; Ansible lo escribe desde argus_hospital_id)" << std::endl;
    return r;
}

AlmacenProtegidos::AlmacenProtegidos(std::unique_ptr<::argus::almacen::IRegistryStore> almacen, ClavesProtegidos claves,
                                     std::string hospital_id, std::ostream& log)
    : almacen_(std::move(almacen)), claves_(claves), hospital_id_(std::move(hospital_id)), log_(log) {}

std::string AlmacenProtegidos::clave_version(uint64_t n) {
    char b[32];
    std::snprintf(b, sizeof b, "%020llu", static_cast<unsigned long long>(n));
    return std::string(kHistorico) + b;
}

bool AlmacenProtegidos::version_vigente(uint64_t& v) {
    v = 0;
    std::string s;
    const Estado e = almacen_->leer(kVigente, s);
    if (e == Estado::NoDisponible) return false;
    if (e == Estado::Ok) {
        const auto r = verificar_documento(s, claves_, hospital_id_, 0);
        if (r.ok) {
            v = r.manifiesto->version;
            return true;
        }
        log_ << "[PROTEGIDOS-ALMACEN] el vigente guardado ya no verifica (motivo=" << nombre_motivo(r.motivo) << " "
             << r.detalle << "): se toma la mayor versión del histórico" << std::endl;
    }
    std::map<std::string, std::string> h;
    if (almacen_->listar(kHistorico, h) == Estado::NoDisponible) return false;
    if (!h.empty()) {
        const std::string ultima = h.rbegin()->first.substr(std::string(kHistorico).size());
        v = std::strtoull(ultima.c_str(), nullptr, 10);
    }
    return true;
}

AlmacenProtegidos::Respuesta AlmacenProtegidos::obtener() {
    if (hospital_id_.empty()) return {503, error_json("sin-configurar", "protegidos.hospital_id sin valor en etcd-server.json")};
    std::lock_guard<std::mutex> l(m_);
    std::string s;
    const Estado e = almacen_->leer(kVigente, s);
    if (e == Estado::Ok) return {200, s};
    if (e == Estado::NoEncontrado) return {404, error_json("sin-manifiesto", "no hay manifiesto de protegidos publicado")};
    return {503, error_json("almacen", "almacén no disponible: " + almacen_->ultimo_error())};
}

AlmacenProtegidos::Respuesta AlmacenProtegidos::publicar(const std::string& sobre, const std::string& quien) {
    const std::string q = detalle_protegidos::saneado(quien);
    if (hospital_id_.empty()) return {503, error_json("sin-configurar", "protegidos.hospital_id sin valor en etcd-server.json")};
    if (sobre.size() > kProtegidosMaxSobreBytes) {
        log_ << "[PROTEGIDOS-PUT-RECHAZADO] cn=" << q << " motivo=formato " << sobre.size() << " bytes" << std::endl;
        return {413, error_json("formato", "sobre de " + std::to_string(sobre.size()) + " bytes (máximo " +
                                               std::to_string(kProtegidosMaxSobreBytes) + ")")};
    }
    std::lock_guard<std::mutex> l(m_);
    uint64_t vig = 0;
    if (!version_vigente(vig)) return {503, error_json("almacen", "almacén no disponible: " + almacen_->ultimo_error())};
    const auto r = verificar_documento(sobre, claves_, hospital_id_, vig);
    if (!r.ok) {
        const int http = r.motivo == MotivoRechazo::VERSION ? 409
                         : (r.motivo == MotivoRechazo::FIRMA || r.motivo == MotivoRechazo::HOSPITAL) ? 403
                                                                                                  : 400;
        log_ << "[PROTEGIDOS-PUT-RECHAZADO] cn=" << q << " motivo=" << nombre_motivo(r.motivo) << " " << r.detalle
             << " (vigente=" << vig << ")" << std::endl;
        return {http, error_json(nombre_motivo(r.motivo), r.detalle)};
    }
    const auto& m = *r.manifiesto;
    const std::string kv = clave_version(m.version);
    std::string ya;
    const Estado e0 = almacen_->leer(kv, ya);
    if (e0 == Estado::NoDisponible) return {503, error_json("almacen", "almacén no disponible: " + almacen_->ultimo_error())};
    if (e0 == Estado::Ok) {
        log_ << "[PROTEGIDOS-PUT-RECHAZADO] cn=" << q << " motivo=version la " << m.version
             << " ya está en el histórico (una publicación anterior se quedó a medias): firme la siguiente" << std::endl;
        return {409, error_json("version", "la versión " + std::to_string(m.version) + " ya existe en el histórico")};
    }
    if (almacen_->poner(kv, sobre) != Estado::Ok || almacen_->poner(kVigente, sobre) != Estado::Ok) {
        log_ << "[PROTEGIDOS-PUT-RECHAZADO] cn=" << q << " motivo=almacen " << almacen_->ultimo_error() << std::endl;
        return {503, error_json("almacen", "almacén no disponible: " + almacen_->ultimo_error())};
    }
    log_ << "[PROTEGIDOS-PUBLICADO] version=" << m.version << " anterior=" << vig << " cn=" << q
         << " firmante=" << detalle_protegidos::saneado(m.firmante) << " clave=" << m.clave << " entradas="
         << m.entradas.size() << " sha256=" << m.sha256_carga.substr(0, 16) << std::endl;
    return {201, json{{"status", "ok"}, {"version", m.version}, {"anterior", vig}, {"sha256", m.sha256_carga}}.dump()};
}

}  // namespace argus::protegidos
'''

NUEVO_2_RUTA = 'etcd-server/tests/test_protegidos_servidor.cpp'
NUEVO_2_SHA = 'dc72ff6238b3255d1e5e3319f721747792bb749f0d673586a61c68da78f29d79'
NUEVO_2 = r'''// test_protegidos_servidor.cpp — [PROTEGIDOS-MANIFIESTO-D318] ADR-060 8e.3b: GET/PUT del manifiesto de protegidos en el
// etcd-server, sobre MemoriaRegistryStore (sin red). Clave desechable generada aquí; firma con el formato de Vault
// transit (ayudantes de libs/protegidos/tests/ayuda_firma.hpp).
#include "etcd_server/protegidos_servidor.hpp"
#include "ayuda_firma.hpp"

#include <gtest/gtest.h>
#include <nlohmann/json.hpp>

#include <fstream>
#include <map>
#include <sstream>

using namespace argus::protegidos;
using namespace argus::protegidos::prueba;
using argus::almacen::MemoriaRegistryStore;
using nlohmann::json;

namespace {

const std::string kLab = entrada("infraestructura", "192.168.100.20/32") + "," + entrada("intranet", "192.168.100.61/32");

struct Banco {
    Par a, otra;
    ClavesProtegidos claves;
    MemoriaRegistryStore* mem = nullptr;  // propiedad del almacén
    std::ostringstream log;
    std::unique_ptr<AlmacenProtegidos> al;
    explicit Banco(const std::string& hospital = "hospital-lab") {
        EXPECT_GE(sodium_init(), 0);
        std::string err;
        EXPECT_TRUE(claves_protegidos_desde_hex(a.hex(), "", claves, err)) << err;
        auto m = std::make_unique<MemoriaRegistryStore>();
        mem = m.get();
        al = std::make_unique<AlmacenProtegidos>(std::move(m), claves, hospital, log);
    }
    std::string firmado(uint64_t v, const std::string& planta = kLab, const Par* p = nullptr,
                        const std::string& hospital = "hospital-lab", const std::string& otras = "",
                        const std::string& comun = "") {
        const std::string c = carga(v, planta, comun, "{\"infraestructura\":32,\"intranet\":24,\"dmz\":24,\"externos_criticos\":32}",
                                    hospital, "", otras);
        return sobre(c, firmar(p ? *p : a, c));
    }
};

}  // namespace

TEST(ProtegidosServidor, SinManifiestoGet404) {
    Banco b;
    const auto r = b.al->obtener();
    EXPECT_EQ(r.http, 404) << r.cuerpo;
}

TEST(ProtegidosServidor, PublicaYDevuelveElSobreTalCual) {
    Banco b;
    const std::string s1 = b.firmado(1);
    const auto p = b.al->publicar(s1, "argus-infra");
    ASSERT_EQ(p.http, 201) << p.cuerpo;
    EXPECT_EQ(json::parse(p.cuerpo)["version"], 1);
    const auto g = b.al->obtener();
    EXPECT_EQ(g.http, 200);
    EXPECT_EQ(g.cuerpo, s1);  // los bytes exactos: el firewall verifica la misma firma
    std::string h;
    EXPECT_EQ(b.mem->leer(AlmacenProtegidos::clave_version(1), h), argus::almacen::Estado::Ok);
    EXPECT_EQ(h, s1);
    EXPECT_NE(b.log.str().find("[PROTEGIDOS-PUBLICADO] version=1 anterior=0 cn=argus-infra"), std::string::npos) << b.log.str();
}

TEST(ProtegidosServidor, VersionNoMayor409YElHistoricoNoCambia) {
    Banco b;
    const std::string s1 = b.firmado(1), s2 = b.firmado(2);
    ASSERT_EQ(b.al->publicar(s2, "argus-infra").http, 201);
    EXPECT_EQ(b.al->publicar(s2, "argus-infra").http, 409);   // repetida
    EXPECT_EQ(b.al->publicar(s1, "argus-infra").http, 409);   // rollback
    EXPECT_EQ(b.al->obtener().cuerpo, s2);
    const std::string s3 = b.firmado(3);
    ASSERT_EQ(b.al->publicar(s3, "argus-infra").http, 201);
    std::string h;
    EXPECT_EQ(b.mem->leer(AlmacenProtegidos::clave_version(2), h), argus::almacen::Estado::Ok);
    EXPECT_EQ(h, s2);  // la anterior sigue en el histórico (deshacer = volver a firmarla como nueva)
    EXPECT_EQ(b.al->obtener().cuerpo, s3);
}

TEST(ProtegidosServidor, FirmaYHospital403FormatoYPlanta400) {
    Banco b;
    EXPECT_EQ(b.al->publicar(b.firmado(1, kLab, &b.otra), "argus-infra").http, 403);           // otra clave
    EXPECT_EQ(b.al->publicar(b.firmado(1, kLab, nullptr, "otro-hospital"), "x").http, 403);    // otro hospital
    EXPECT_EQ(b.al->publicar("{no es json", "x").http, 400);
    // En OTRA planta, la misma red e interfaz que en comun: ese firewall lo rechazaría, así que el servidor también
    const std::string dup = entrada("intranet", "10.9.0.0/24", "eth1");
    EXPECT_EQ(b.al->publicar(b.firmado(1, kLab, nullptr, "hospital-lab", ",\"planta-2\":[" + dup + "]", dup), "x").http, 400);
    EXPECT_EQ(b.al->obtener().http, 404);   // nada se guardó
    EXPECT_NE(b.log.str().find("[PROTEGIDOS-PUT-RECHAZADO] cn=argus-infra motivo=firma"), std::string::npos) << b.log.str();
}

TEST(ProtegidosServidor, DemasiadoGrande413) {
    Banco b;
    EXPECT_EQ(b.al->publicar(std::string(kProtegidosMaxSobreBytes + 1, ' '), "x").http, 413);
}

TEST(ProtegidosServidor, AlmacenCaido503YSeRecupera) {
    Banco b;
    b.mem->simular_caido(true);
    EXPECT_EQ(b.al->publicar(b.firmado(1), "x").http, 503);
    EXPECT_EQ(b.al->obtener().http, 503);
    b.mem->simular_caido(false);
    EXPECT_EQ(b.al->publicar(b.firmado(1), "x").http, 201);
}

TEST(ProtegidosServidor, YaExisteEnElHistorico409) {
    // Publicación anterior a medias: protegidos/v/2 escrito, vigente todavía en 1
    Banco b;
    ASSERT_EQ(b.al->publicar(b.firmado(1), "x").http, 201);
    const std::string s2 = b.firmado(2);
    ASSERT_EQ(b.mem->poner(AlmacenProtegidos::clave_version(2), s2), argus::almacen::Estado::Ok);
    EXPECT_EQ(b.al->publicar(s2, "x").http, 409);
    EXPECT_EQ(b.al->publicar(b.firmado(3), "x").http, 201);
}

TEST(ProtegidosServidor, VigenteQueYaNoVerificaUsaElHistorico) {
    Banco b;
    ASSERT_EQ(b.al->publicar(b.firmado(5), "x").http, 201);
    ASSERT_EQ(b.mem->poner("protegidos/vigente", "{basura"), argus::almacen::Estado::Ok);
    EXPECT_EQ(b.al->publicar(b.firmado(4), "x").http, 409);   // la mayor del histórico es 5
    EXPECT_EQ(b.al->publicar(b.firmado(6), "x").http, 201);
    EXPECT_NE(b.log.str().find("[PROTEGIDOS-ALMACEN] el vigente guardado ya no verifica"), std::string::npos);
}

TEST(ProtegidosServidor, SinHospital503) {
    Banco b("");
    EXPECT_EQ(b.al->obtener().http, 503);
    EXPECT_EQ(b.al->publicar(b.firmado(1), "x").http, 503);
}

TEST(ProtegidosServidor, ClaveVersionOrdenaBien) {
    EXPECT_EQ(AlmacenProtegidos::clave_version(7), "protegidos/v/00000000000000000007");
    EXPECT_LT(AlmacenProtegidos::clave_version(9), AlmacenProtegidos::clave_version(10));
}

// ── bloque protegidos de etcd-server.json ───────────────────────────────────

TEST(ProtegidosServidorConfig, LecturaYDefectos) {
    std::ostringstream a1, i1;
    auto r = parse_protegidos_config(json::parse(R"({"protegidos": {"hospital_id": "hospital-lab"}})"), a1, i1);
    EXPECT_EQ(r.defectos, 0);
    EXPECT_EQ(r.cfg.hospital_id, "hospital-lab");
    EXPECT_NE(i1.str().find("[ETCD-PROTEGIDOS] protegidos.hospital_id=hospital-lab (JSON)"), std::string::npos);
    for (const char* mal : {R"({})", R"({"protegidos": 3})", R"({"protegidos": {}})", R"({"protegidos": {"hospital_id": "Hosp_Lab"}})",
                            R"({"protegidos": {"hospital_id": ""}})"}) {
        std::ostringstream a, i;
        auto m = parse_protegidos_config(json::parse(mal), a, i);
        EXPECT_EQ(m.defectos, 1) << mal;
        EXPECT_TRUE(m.cfg.hospital_id.empty()) << mal;
        EXPECT_NE(a.str().find("[CONFIG-DEFAULT]"), std::string::npos) << mal;
    }
}

TEST(ProtegidosServidorConfig, LosDosJsonDelRepoLoTraen) {
    for (const char* f : {"etcd-server.json", "etcd-server.smoke-enterprise.json"}) {
        std::ifstream in(std::string(ETCD_SERVER_CONFIG_DIR) + "/" + f);
        ASSERT_TRUE(in.good()) << f;
        std::ostringstream a, i;
        auto r = parse_protegidos_config(json::parse(in), a, i);
        EXPECT_EQ(r.defectos, 0) << f << a.str();
        EXPECT_EQ(r.cfg.hospital_id, "hospital-lab") << f;
    }
}
'''

NUEVO_3_RUTA = 'libs/protegidos/src/claves.cpp'
NUEVO_3_SHA = '8cf0897bd5d59af63275ea7d833fc5a3a545fa3b561fa7045855d3a0cc94bf7e'
NUEVO_3 = r'''// libs/protegidos/src/claves.cpp (antes firewall-acl-agent/src/core/protegidos_claves.cpp) — [PROTEGIDOS-MANIFIESTO-D318] ADR-060 D3 (patrón ADR-025): la clave pública del manifiesto
// de protegidos, compilada en el binario en dos ranuras. CMake la valida (64 hex) y sin la actual no compila; aquí se
// convierte una vez. Si aun así llega mal formada, el agente no arranca: no hay defecto sano para una clave de confianza.
#include "protegidos/manifiesto.hpp"

#include <exception>
#include <iostream>

#ifndef ARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX
#error "ARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX sin definir (CMake: -DARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX=<64 hex>)"
#endif
#ifndef ARGUS_PROTEGIDOS_PUBKEY_SIGUIENTE_HEX
#error "ARGUS_PROTEGIDOS_PUBKEY_SIGUIENTE_HEX sin definir (vacía si no hay rotación en curso)"
#endif

namespace argus::protegidos {

const ClavesProtegidos& claves_protegidos_compiladas() {
    static const ClavesProtegidos c = [] {
        ClavesProtegidos k;
        std::string error;
        if (!claves_protegidos_desde_hex(ARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX, ARGUS_PROTEGIDOS_PUBKEY_SIGUIENTE_HEX, k, error)) {
            std::cerr << "[PROTEGIDOS-CLAVE] FATAL: clave pública compilada mal formada: " << error << std::endl;
            std::terminate();
        }
        return k;
    }();
    return c;
}

}  // namespace argus::protegidos
'''

NUEVO_4_RUTA = 'libs/protegidos/tests/ayuda_firma.hpp'
NUEVO_4_SHA = 'c61396ff9bf1540473a1892205f2bf278991899bacec58c57dfc26faf461e5a9'
NUEVO_4 = r'''// ayuda_firma.hpp — [PROTEGIDOS-MANIFIESTO-D318] ayudantes de los tests: un par Ed25519 desechable, la firma con el
// formato de Vault transit (vault:vN:<base64>), el sobre argus-protegidos/v1 y cargas de prueba del lab. Los comparten
// test_protegidos_manifiesto (libs/protegidos) y test_protegidos_servidor (etcd-server). Solo tests: nunca en un binario.
#pragma once
#include <sodium.h>

#include <cstdint>
#include <string>

namespace argus::protegidos::prueba {

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

inline std::string b64(const std::string& d) {
    std::string o(sodium_base64_ENCODED_LEN(d.size(), sodium_base64_VARIANT_ORIGINAL), '\0');
    sodium_bin2base64(o.data(), o.size(), reinterpret_cast<const unsigned char*>(d.data()), d.size(),
                      sodium_base64_VARIANT_ORIGINAL);
    o.resize(o.size() - 1);
    return o;
}

inline std::string firmar(const Par& p, const std::string& carga, int v = 1) {
    unsigned char sig[crypto_sign_BYTES];
    crypto_sign_detached(sig, nullptr, reinterpret_cast<const unsigned char*>(carga.data()), carga.size(), p.sk);
    return "vault:v" + std::to_string(v) + ":" + b64(std::string(reinterpret_cast<const char*>(sig), sizeof sig));
}

inline std::string sobre(const std::string& carga, const std::string& firma, const std::string& extra = "") {
    return "{\"formato\":\"argus-protegidos/v1\",\"carga_b64\":\"" + b64(carga) + "\",\"firma\":\"" + firma + "\"" + extra + "}";
}

inline std::string entrada(const std::string& cat, const std::string& cidr, const std::string& iface = "eth2",
                           const std::string& mac = "", const std::string& motivo = "prueba") {
    return "{\"categoria\":\"" + cat + "\",\"cidr\":\"" + cidr + "\",\"interfaz\":\"" + iface + "\",\"mac\":\"" + mac +
           "\",\"motivo\":\"" + motivo + "\"}";
}

inline std::string carga(uint64_t version, const std::string& planta_lab, const std::string& comun = "",
                         const std::string& limites = "{\"infraestructura\":32,\"intranet\":24,\"dmz\":24,\"externos_criticos\":32}",
                         const std::string& hospital = "hospital-lab", const std::string& extra = "",
                         const std::string& otras_plantas = "") {
    return "{\"esquema\":1,\"hospital_id\":\"" + hospital + "\",\"version\":" + std::to_string(version) +
           ",\"emitido_utc\":\"2026-11-05T08:00:00Z\",\"firmante\":\"argus-infra\",\"motivo\":\"alta del lab\","
           "\"hash_anterior\":\"\",\"limites\":" + limites + ",\"comun\":[" + comun + "],\"plantas\":{\"lab-vagrant\":[" +
           planta_lab + "]" + otras_plantas + "}" + extra + "}";
}

}  // namespace argus::protegidos::prueba
'''

NUEVO_5_RUTA = 'libs/protegidos/tests/test_protegidos_claves.cpp'
NUEVO_5_SHA = '15b62d40fbfce0b17a98470a0f602b340f04b6ba98acd31d3b8eb30cb1f9053f'
NUEVO_5 = r'''// test_protegidos_claves.cpp — [PROTEGIDOS-MANIFIESTO-D318] la clave pública compilada (CMake -> binario) es la que
// se usa: la misma que trae la definición, en las dos ranuras. Standalone, CHECK propio.
#include "protegidos/manifiesto.hpp"

#include <sodium.h>

#include <iostream>
#include <string>

using namespace argus::protegidos;

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

static std::string hex(const std::array<unsigned char, 32>& k) {
    char h[65];
    sodium_bin2hex(h, sizeof h, k.data(), k.size());
    return h;
}

int main() {
    if (sodium_init() < 0) return 2;
    const ClavesProtegidos& c = claves_protegidos_compiladas();
    CHECK(hex(c.actual) == ARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX);
    const std::string sig = ARGUS_PROTEGIDOS_PUBKEY_SIGUIENTE_HEX;
    CHECK(c.hay_siguiente == !sig.empty());
    if (c.hay_siguiente) CHECK(hex(c.siguiente) == sig);
    std::cout << "[PROTEGIDOS-CLAVE] actual huella=" << huella_clave_protegidos(c.actual)
              << (c.hay_siguiente ? " siguiente huella=" + huella_clave_protegidos(c.siguiente) : std::string(" siguiente=ninguna"))
              << std::endl;
    std::cout << "test_protegidos_claves: " << (g_checks - g_fallos) << "/" << g_checks << " OK" << std::endl;
    return g_fallos == 0 ? 0 : 1;
}
'''

NUEVOS = [(NUEVO_0_RUTA, NUEVO_0_SHA, NUEVO_0), (NUEVO_1_RUTA, NUEVO_1_SHA, NUEVO_1), (NUEVO_2_RUTA, NUEVO_2_SHA, NUEVO_2), (NUEVO_3_RUTA, NUEVO_3_SHA, NUEVO_3), (NUEVO_4_RUTA, NUEVO_4_SHA, NUEVO_4), (NUEVO_5_RUTA, NUEVO_5_SHA, NUEVO_5)]

BORRADO_0_RUTA = 'firewall-acl-agent/src/core/protegidos_claves.cpp'
BORRADO_0_SHA = 'f045ae57c23da7e91c75197273942c24719474722add46459a2e7eb005a44371'

BORRADO_1_RUTA = 'firewall-acl-agent/tests/unit/test_protegidos_claves.cpp'
BORRADO_1_SHA = '15b62d40fbfce0b17a98470a0f602b340f04b6ba98acd31d3b8eb30cb1f9053f'

BORRADOS = [(BORRADO_0_RUTA, BORRADO_0_SHA), (BORRADO_1_RUTA, BORRADO_1_SHA)]

CAMBIOS = {
    'ansible/playbooks/deploy_configs.yml': [
        ('          - argus_prefijo is string\n        fail_msg: >-\n          [ETCD-CONFIG-ENTORNO] {{ inventory_hostname }}: faltan o están mal etcd_almacen_endpoints (lista con TODOS los\n          miembros etcd del despliegue, "https://IPv4:puerto") o argus_prefijo (texto, p. ej. /argus/<hospital>/<planta>/)\n          en el group_vars del inventario. No hay defecto: sin ellos no se despliega.\n        quiet: true\n',
         '          - argus_prefijo is string\n          - argus_hospital_id is defined\n          - argus_hospital_id is string\n          - argus_hospital_id is match(\'^[a-z0-9-]{1,64}$\')\n        fail_msg: >-\n          [ETCD-CONFIG-ENTORNO] {{ inventory_hostname }}: faltan o están mal etcd_almacen_endpoints (lista con TODOS los\n          miembros etcd del despliegue, "https://IPv4:puerto") o argus_prefijo (texto, p. ej. /argus/<hospital>/<planta>/)\n          en el group_vars del inventario, o argus_hospital_id ([a-z0-9-], de 1 a 64: el hospital de este etcd-server,\n          ADR-060). No hay defecto: sin ellos no se despliega.\n        quiet: true\n'),
        ('\n    - name: "JSON del repo con almacen.endpoints y almacen.prefijo del inventario"\n      set_fact:\n        es_json: >-\n          {{ lookup(\'file\', es_json_repo) | from_json\n             | combine({\'almacen\': {\'endpoints\': etcd_almacen_endpoints, \'prefijo\': argus_prefijo}}, recursive=True) }}\n\n',
         '\n    # [PROTEGIDOS-MANIFIESTO-D318] y protegidos.hospital_id = argus_hospital_id (ADR-060 F-C: un etcd-server, un hospital)\n    - name: "JSON del repo con almacen.endpoints, almacen.prefijo y protegidos.hospital_id del inventario"\n      set_fact:\n        es_json: >-\n          {{ lookup(\'file\', es_json_repo) | from_json\n             | combine({\'almacen\': {\'endpoints\': etcd_almacen_endpoints, \'prefijo\': argus_prefijo},\n                        \'protegidos\': {\'hospital_id\': argus_hospital_id}}, recursive=True) }}\n\n'),
        ('      debug:\n        msg: "{{ (es_chk.stdout_lines + es_chk.stderr_lines) | select(\'search\', \'ETCD-CONFIG-CHECK|\\\\[ETCD-ALMACEN\\\\]\') | list }}"\n',
         '      debug:\n        msg: "{{ (es_chk.stdout_lines + es_chk.stderr_lines) | select(\'search\', \'ETCD-CONFIG-CHECK|\\\\[ETCD-ALMACEN\\\\]|\\\\[ETCD-PROTEGIDOS\\\\]\') | list }}"\n'),
    ],
    'etcd-server/CMakeLists.txt': [
        ('        src/vault_secret_store.cpp\n)\n\n',
         '        src/vault_secret_store.cpp\n        src/protegidos_servidor.cpp   # [PROTEGIDOS-MANIFIESTO-D318] GET/PUT /v1/protegidos (ADR-060 8e.3b)\n)\n\n# ============================================================================\n# [PROTEGIDOS-MANIFIESTO-D318] ADR-060 F-A/F-B: el verificador del manifiesto de protegidos (libs/protegidos, estática,\n# compilada con las opciones de este binario) y la clave pública compilada, la misma que el firewall-acl-agent: -D o el\n# fichero que deja el bootstrap en el defender, donde se compilan los dos. Sin la clave actual no compila.\n# ============================================================================\nset(ARGUS_PROTEGIDOS_TESTS OFF CACHE BOOL "Tests de libs/protegidos (los corre el firewall-acl-agent)" FORCE)\nadd_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../libs/protegidos ${CMAKE_CURRENT_BINARY_DIR}/libs-protegidos)\n\n'),
        ('        ${CRYPTO_PROVIDER_LIB}\n        sodium\n',
         '        ${CRYPTO_PROVIDER_LIB}\n        argus_protegidos_clave   # [PROTEGIDOS-MANIFIESTO-D318] (arrastra argus_protegidos)\n        sodium\n'),
        ('    add_test(NAME test_almacen_claves COMMAND test_almacen_claves)\n    # target_include_directories(test_hmac_integration\n',
         '    add_test(NAME test_almacen_claves COMMAND test_almacen_claves)\n    # [PROTEGIDOS-MANIFIESTO-D318] GET/PUT del manifiesto de protegidos sobre MemoriaRegistryStore (sin red): publicar,\n    # versión no mayor, ya existe, firma, hospital, planta con duplicado, almacén caído, vigente que ya no verifica,\n    # sin configurar; clave desechable generada en el test (ayudantes de libs/protegidos/tests)\n    add_executable(test_protegidos_servidor tests/test_protegidos_servidor.cpp src/protegidos_servidor.cpp)\n    target_include_directories(test_protegidos_servidor PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include\n            ${CMAKE_CURRENT_SOURCE_DIR}/../libs/protegidos/tests ${LIBSODIUM_INCLUDE_DIRS})\n    target_compile_definitions(test_protegidos_servidor PRIVATE\n            ETCD_SERVER_CONFIG_DIR="${CMAKE_CURRENT_SOURCE_DIR}/config")\n    target_link_libraries(test_protegidos_servidor PRIVATE GTest::gtest_main argus_protegidos sodium)\n    add_test(NAME test_protegidos_servidor COMMAND test_protegidos_servidor)\n    # target_include_directories(test_hmac_integration\n'),
    ],
    'etcd-server/config/etcd-server.json': [
        ('        ]\n      }\n    ]\n  },\n',
         '        ]\n      },\n      {\n        "metodo": "GET",\n        "ruta": "/v1/protegidos",\n        "permitir": [\n          "ou:firewall-acl-agent",\n          "ou:argus-infra"\n        ]\n      },\n      {\n        "metodo": "PUT",\n        "ruta": "/v1/protegidos",\n        "permitir": [\n          "ou:argus-infra"\n        ]\n      }\n    ]\n  },\n  "protegidos": {\n    "_doc": "[PROTEGIDOS-MANIFIESTO-D318] ADR-060 8e.3b. hospital_id: el hospital al que sirve ESTE etcd-server ([a-z0-9-], de 1 a 64); sin valor sano por defecto: ausente o mal formado = [CONFIG-DEFAULT] y GET/PUT /v1/protegidos responden 503. Ansible (make deploy-configs) lo escribe desde argus_hospital_id del inventario. GET /v1/protegidos da el sobre vigente (firewall-acl-agent, argus-infra); PUT /v1/protegidos solo con certificado OU=argus-infra: el etcd-server verifica firma (clave publica compilada, la misma que el firewall), formato, limites, hospital y version > la vigente antes de guardarlo en etcd (protegidos/vigente y protegidos/v/<N>).",\n    "hospital_id": "hospital-lab"\n  },\n'),
    ],
    'etcd-server/config/etcd-server.smoke-enterprise.json': [
        ('        ]\n      }\n    ]\n  },\n',
         '        ]\n      },\n      {\n        "metodo": "GET",\n        "ruta": "/v1/protegidos",\n        "permitir": [\n          "ou:firewall-acl-agent",\n          "ou:argus-infra"\n        ]\n      },\n      {\n        "metodo": "PUT",\n        "ruta": "/v1/protegidos",\n        "permitir": [\n          "ou:argus-infra"\n        ]\n      }\n    ]\n  },\n  "protegidos": {\n    "_doc": "[PROTEGIDOS-MANIFIESTO-D318] ADR-060 8e.3b. hospital_id: el hospital al que sirve ESTE etcd-server ([a-z0-9-], de 1 a 64); sin valor sano por defecto: ausente o mal formado = [CONFIG-DEFAULT] y GET/PUT /v1/protegidos responden 503. Ansible (make deploy-configs) lo escribe desde argus_hospital_id del inventario. GET /v1/protegidos da el sobre vigente (firewall-acl-agent, argus-infra); PUT /v1/protegidos solo con certificado OU=argus-infra: el etcd-server verifica firma (clave publica compilada, la misma que el firewall), formato, limites, hospital y version > la vigente antes de guardarlo en etcd (protegidos/vigente y protegidos/v/<N>).",\n    "hospital_id": "hospital-lab"\n  },\n'),
    ],
    'etcd-server/include/etcd_server/etcd_server.hpp': [
        ('    class SecretsManager;\n}\n\n//etcd-server/include/etcd_server/etcd_server.hpp\n',
         '    class SecretsManager;\n}\nnamespace argus::protegidos { class AlmacenProtegidos; }  // [PROTEGIDOS-MANIFIESTO-D318]\n\n//etcd-server/include/etcd_server/etcd_server.hpp\n'),
        ('    etcd_server::SecretsManager* secrets_manager_ = nullptr;  // Non-owning pointer\n    std::atomic<bool> running_{false};\n',
         '    etcd_server::SecretsManager* secrets_manager_ = nullptr;  // Non-owning pointer\n    argus::protegidos::AlmacenProtegidos* protegidos_ = nullptr;  // [PROTEGIDOS-MANIFIESTO-D318] no propietario\n    std::atomic<bool> running_{false};\n'),
        ('    }\n    // [ETCD-AUTHZ-D313] crea el servidor (SSLServer con mTLS o, solo en transición, HTTP) y sus rutas.\n',
         '    }\n    // [PROTEGIDOS-MANIFIESTO-D318] ADR-060 8e.3b: GET/PUT /v1/protegidos (antes de initialize())\n    void set_protegidos(argus::protegidos::AlmacenProtegidos* p) { protegidos_ = p; }\n    // [ETCD-AUTHZ-D313] crea el servidor (SSLServer con mTLS o, solo en transición, HTTP) y sus rutas.\n'),
    ],
    'etcd-server/include/etcd_server/etcd_server_authz.hpp': [
        ('  {"metodo": "GET",  "ruta": "/validate",             "permitir": ["ou:admin"]},\n  {"metodo": "GET",  "ruta": "/info",                 "permitir": ["ou:admin"]}\n])";\n',
         '  {"metodo": "GET",  "ruta": "/validate",             "permitir": ["ou:admin"]},\n  {"metodo": "GET",  "ruta": "/info",                 "permitir": ["ou:admin"]},\n  {"metodo": "GET",  "ruta": "/v1/protegidos",        "permitir": ["ou:firewall-acl-agent", "ou:argus-infra"]},\n  {"metodo": "PUT",  "ruta": "/v1/protegidos",        "permitir": ["ou:argus-infra"]}\n])";\n'),
    ],
    'etcd-server/src/etcd_server.cpp': [
        ('#include "etcd_server/secrets_manager.hpp"\n#include <fstream>\n',
         '#include "etcd_server/secrets_manager.hpp"\n#include "etcd_server/protegidos_servidor.hpp"  // [PROTEGIDOS-MANIFIESTO-D318]\n#include <fstream>\n'),
        ('\n    server.Get("/health", [](const httplib::Request& /*req*/, httplib::Response& res) {\n',
         '\n    // [PROTEGIDOS-MANIFIESTO-D318] ADR-060 8e.3b (F-C): el manifiesto firmado de protegidos de ESTE hospital. Quién puede,\n    // en la tabla authz (GET: ou:firewall-acl-agent y ou:argus-infra; PUT: solo ou:argus-infra). La autenticidad sale\n    // de la firma, que se verifica aquí antes de guardar (defensa en profundidad) y otra vez en cada firewall.\n    server.Get("/v1/protegidos", [this, error](const httplib::Request& /*req*/, httplib::Response& res) {\n        if (protegidos_ == nullptr) {\n            error(res, 503, "manifiesto de protegidos no disponible en este etcd-server");\n            return;\n        }\n        const auto r = protegidos_->obtener();\n        res.status = r.http;\n        res.set_content(r.cuerpo, "application/json");\n    });\n    server.Put("/v1/protegidos", [this, error, con_tls](const httplib::Request& req, httplib::Response& res) {\n        if (protegidos_ == nullptr) {\n            error(res, 503, "manifiesto de protegidos no disponible en este etcd-server");\n            return;\n        }\n        std::string cn = "-";\n        if (con_tls) {\n            const auto id = identidad_de_peticion(req);\n            cn = id.valida ? id.cn : "?";\n        }\n        const auto r = protegidos_->publicar(req.body, cn);\n        res.status = r.http;\n        res.set_content(r.cuerpo, "application/json");\n    });\n\n    server.Get("/health", [](const httplib::Request& /*req*/, httplib::Response& res) {\n'),
    ],
    'etcd-server/src/main.cpp': [
        ('#include "etcd_server/vault_secret_store.hpp"   // [ETCD-CLAVES-D314]\n#include <nlohmann/json.hpp>\n',
         '#include "etcd_server/vault_secret_store.hpp"   // [ETCD-CLAVES-D314]\n#include "etcd_server/protegidos_servidor.hpp"   // [PROTEGIDOS-MANIFIESTO-D318]\n#include <nlohmann/json.hpp>\n'),
        ('\nstd::unique_ptr<EtcdServer> g_server;\n',
         '\n// [PROTEGIDOS-MANIFIESTO-D318] declarado ANTES que g_server: se destruye después (el servidor lo usa hasta pararse)\nstd::unique_ptr<argus::protegidos::AlmacenProtegidos> g_protegidos;\nstd::unique_ptr<EtcdServer> g_server;\n'),
        ('    const auto& claves_cfg = leida_claves.cfg;\n    const int defectos = leida.defectos + leida_tls.defectos + leida_authz.defectos + leida_almacen.defectos +\n                         leida_claves.defectos;\n    if (defectos > 0) {\n',
         '    const auto& claves_cfg = leida_claves.cfg;\n    // [PROTEGIDOS-MANIFIESTO-D318] bloque protegidos (hospital_id; sin defecto sano: ausente = 503 en /v1/protegidos)\n    const auto leida_protegidos = argus::protegidos::parse_protegidos_config(root, std::cerr, std::cout);\n    const int defectos = leida.defectos + leida_tls.defectos + leida_authz.defectos + leida_almacen.defectos +\n                         leida_claves.defectos + leida_protegidos.defectos;\n    if (defectos > 0) {\n'),
        ('\n        if (!g_server->initialize()) {\n',
         '\n        // [PROTEGIDOS-MANIFIESTO-D318] ADR-060 8e.3b: el manifiesto de protegidos, en el mismo etcd que el registro (su\n        // propio cliente) y verificado con la clave pública compilada (F-A, la misma que el firewall-acl-agent)\n        {\n            const auto& k = argus::protegidos::claves_protegidos_compiladas();\n            std::cout << "[PROTEGIDOS-CLAVE] actual huella=" << argus::protegidos::huella_clave_protegidos(k.actual)\n                      << (k.hay_siguiente ? " siguiente huella=" + argus::protegidos::huella_clave_protegidos(k.siguiente)\n                                          : std::string(" siguiente=ninguna"))\n                      << " (compiladas) hospital=" << (leida_protegidos.cfg.hospital_id.empty()\n                                                           ? std::string("SIN CONFIGURAR (503)")\n                                                           : leida_protegidos.cfg.hospital_id)\n                      << std::endl;\n            std::unique_ptr<argus::almacen::IRegistryStore> almacen_prot;\n            if (almacen_cfg.modo == "etcd") {\n                almacen_prot = std::make_unique<argus::almacen::EtcdRegistryStore>(almacen_cfg);\n            } else {\n                almacen_prot = std::make_unique<argus::almacen::MemoriaRegistryStore>();\n            }\n            g_protegidos = std::make_unique<argus::protegidos::AlmacenProtegidos>(\n                std::move(almacen_prot), k, leida_protegidos.cfg.hospital_id, std::cout);\n            g_server->set_protegidos(g_protegidos.get());\n        }\n\n        if (!g_server->initialize()) {\n'),
    ],
    'etcd-server/tests/test_etcd_server_authz.cpp': [
        ('    EXPECT_EQ(r.defectos, 1);\n    EXPECT_EQ(r.reglas.size(), 13u);  // [ADR045-FUERA-D316] 15 menos las dos de /v1/epoch\n    EXPECT_NE(o.aviso.str().find("authz ausente"), std::string::npos);\n    EXPECT_NE(o.info.str().find("[ETCD-AUTHZ] regla 1/13: GET /health permitir=cualquiera (DEFECTO: ausente)"),\n              std::string::npos) << o.info.str();\n',
         '    EXPECT_EQ(r.defectos, 1);\n    EXPECT_EQ(r.reglas.size(), 15u);  // [ADR045-FUERA-D316] 15 menos las dos de /v1/epoch; [D318] + las dos de /v1/protegidos\n    EXPECT_NE(o.aviso.str().find("authz ausente"), std::string::npos);\n    EXPECT_NE(o.info.str().find("[ETCD-AUTHZ] regla 1/15: GET /health permitir=cualquiera (DEFECTO: ausente)"),\n              std::string::npos) << o.info.str();\n'),
        ('        EXPECT_EQ(r.defectos, 1) << mala;\n        EXPECT_EQ(r.reglas.size(), 13u) << mala;  // la tabla por defecto ENTERA, no la buena a medias\n        EXPECT_NE(o.aviso.str().find("authz.reglas[1]"), std::string::npos) << mala << "\\n" << o.aviso.str();\n',
         '        EXPECT_EQ(r.defectos, 1) << mala;\n        EXPECT_EQ(r.reglas.size(), 15u) << mala;  // la tabla por defecto ENTERA, no la buena a medias\n        EXPECT_NE(o.aviso.str().find("authz.reglas[1]"), std::string::npos) << mala << "\\n" << o.aviso.str();\n'),
        ('    EXPECT_TRUE(permite(t, "POST", "/register", sn));                 // nombre == CN: en 4b.3\n}\n',
         '    EXPECT_TRUE(permite(t, "POST", "/register", sn));                 // nombre == CN: en 4b.3\n}\n\nTEST(EtcdServerAuthz, ManifiestoDeProtegidos) {\n    // [PROTEGIDOS-MANIFIESTO-D318] ADR-060 8e.3b (D9 bis): leerlo, los firewalls y argus-infra; publicarlo, SOLO argus-infra\n    const auto t = tabla_defecto();\n    const auto fw = id("firewall-acl-agent", "firewall-acl-agent");\n    const auto inf = id("argus-infra", "argus-infra");\n    const auto adm = id("admin", "admin");\n    const auto sn = id("sniffer", "sniffer");\n    EXPECT_TRUE(permite(t, "GET", "/v1/protegidos", fw));\n    EXPECT_TRUE(permite(t, "GET", "/v1/protegidos", inf));\n    EXPECT_FALSE(permite(t, "GET", "/v1/protegidos", sn));\n    EXPECT_FALSE(permite(t, "GET", "/v1/protegidos", adm));\n    EXPECT_TRUE(permite(t, "PUT", "/v1/protegidos", inf));\n    EXPECT_FALSE(permite(t, "PUT", "/v1/protegidos", fw));    // un firewall no publica\n    EXPECT_FALSE(permite(t, "PUT", "/v1/protegidos", adm));   // admin tampoco: es otro rol (D9 bis)\n    EXPECT_FALSE(permite(t, "POST", "/v1/protegidos", inf));\n    EXPECT_FALSE(permite(t, "DELETE", "/v1/protegidos", inf)); // deshacer = firmar una versión nueva (D4)\n    EXPECT_FALSE(permite(t, "GET", "/v1/protegidos/hospital-lab", fw));\n}\n'),
    ],
    'firewall-acl-agent/CMakeLists.txt': [
        ('include_directories(${CMAKE_CURRENT_SOURCE_DIR}/../libs/protegidos/include)\n\n# ============================================================================\n# [PROTEGIDOS-MANIFIESTO-D318] ADR-060 D3 / D-E: clave PÚBLICA del manifiesto de protegidos (Vault transit del\n# hospital), compilada en dos ranuras (patrón ADR-025). No es un secreto. Sin la ranura actual NO se compila: no hay\n# defecto sano para una clave de confianza.\n#   -DARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX=<64 hex>     (producción: la pasa Jenkins)\n#   -DARGUS_PROTEGIDOS_PUBKEY_SIGUIENTE_HEX=<64 hex>  (solo durante una rotación; si no, vacía)\n# Sin -D se leen de /etc/ml-defender/firewall-acl-agent/protegidos_pubkey_{actual,siguiente}.hex; en el lab los\n# trae de la VM etcd `make protegidos-pubkey` (bootstrap [4b/8]).\n# ============================================================================\nset(ARGUS_PROTEGIDOS_PUBKEY_DIR /etc/ml-defender/firewall-acl-agent)\nforeach(RANURA ACTUAL SIGUIENTE)\n    string(TOLOWER ${RANURA} ranura)\n    set(_fich ${ARGUS_PROTEGIDOS_PUBKEY_DIR}/protegidos_pubkey_${ranura}.hex)\n    if(DEFINED ARGUS_PROTEGIDOS_PUBKEY_${RANURA}_HEX)\n        set(_origen "-D")\n    elseif(EXISTS ${_fich})\n        file(READ ${_fich} _v)\n        string(STRIP "${_v}" _v)\n        set(ARGUS_PROTEGIDOS_PUBKEY_${RANURA}_HEX "${_v}")\n        set(_origen "fichero ${_fich}")\n    else()\n        set(ARGUS_PROTEGIDOS_PUBKEY_${RANURA}_HEX "")\n        set(_origen "ausente: ni -D ni ${_fich}")\n    endif()\n    set(_v "${ARGUS_PROTEGIDOS_PUBKEY_${RANURA}_HEX}")\n    if(RANURA STREQUAL "ACTUAL" AND _v STREQUAL "")\n        message(FATAL_ERROR "[PROTEGIDOS-CLAVE] falta la clave pública ACTUAL del manifiesto de protegidos (${_origen}). "\n                            "Lab: make protegidos-pubkey desde el Mac. Producción: -DARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX=<64 hex>")\n    endif()\n    string(LENGTH "${_v}" _n)\n    if(NOT _v STREQUAL "" AND (NOT _n EQUAL 64 OR NOT _v MATCHES "^[0-9a-f]+$"))\n        message(FATAL_ERROR "[PROTEGIDOS-CLAVE] clave pública ${RANURA} mal formada (${_origen}): 64 caracteres hex en minúsculas")\n    endif()\n    if(_v STREQUAL "")\n        message(STATUS "[PROTEGIDOS-CLAVE] ${RANURA}: ninguna (${_origen})")\n    else()\n        string(SUBSTRING "${_v}" 0 16 _ini)\n        message(STATUS "[PROTEGIDOS-CLAVE] ${RANURA}: ${_ini}... (${_origen})")\n    endif()\nendforeach()\n\n# ============================================================================\n',
         'include_directories(${CMAKE_CURRENT_SOURCE_DIR}/../libs/protegidos/include)\n\n\n# ============================================================================\n'),
        ('        src/core/clave_csv.cpp           # [FW-CSV-CLAVE-B2-D316] clave HMAC del CSV pedida cada intervalo\n        src/core/protegidos_claves.cpp      # [PROTEGIDOS-MANIFIESTO-D318] clave pública compilada (dos ranuras)\n        # src/core/acl_intelligence.cpp     # TODO: Phase 2+\n',
         '        src/core/clave_csv.cpp           # [FW-CSV-CLAVE-B2-D316] clave HMAC del CSV pedida cada intervalo\n        # src/core/acl_intelligence.cpp     # TODO: Phase 2+\n'),
        ('\n# [PROTEGIDOS-MANIFIESTO-D318] verificador del manifiesto (libs/protegidos) y clave pública compilada (ADR-060)\ntarget_link_libraries(firewall_core PUBLIC argus_protegidos)\ntarget_compile_definitions(firewall_core PRIVATE\n        ARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX="${ARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX}"\n        ARGUS_PROTEGIDOS_PUBKEY_SIGUIENTE_HEX="${ARGUS_PROTEGIDOS_PUBKEY_SIGUIENTE_HEX}")\n\n',
         '\n# [PROTEGIDOS-MANIFIESTO-D318] verificador del manifiesto y clave pública compilada (libs/protegidos, ADR-060)\ntarget_link_libraries(firewall_core PUBLIC argus_protegidos argus_protegidos_clave)\n\n'),
        ('\n    # [PROTEGIDOS-MANIFIESTO-D318] test_protegidos_rangos y test_protegidos_manifiesto viven en libs/protegidos\n    # (ARGUS_PROTEGIDOS_TESTS = BUILD_TESTS). Aquí, la clave compilada es la de CMake, en las dos ranuras\n    add_executable(test_protegidos_claves\n            tests/unit/test_protegidos_claves.cpp\n            src/core/protegidos_claves.cpp\n    )\n    target_link_libraries(test_protegidos_claves PRIVATE argus_protegidos)\n    target_compile_definitions(test_protegidos_claves PRIVATE\n            ARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX="${ARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX}"\n            ARGUS_PROTEGIDOS_PUBKEY_SIGUIENTE_HEX="${ARGUS_PROTEGIDOS_PUBKEY_SIGUIENTE_HEX}")\n    add_test(NAME test_protegidos_claves COMMAND test_protegidos_claves)\n# [DDOS-MITIGACION-D301] test de la mitigacion ddos_v2 (mismo patron que test_protegidos_rangos)\n',
         '\n    # [PROTEGIDOS-MANIFIESTO-D318] test_protegidos_rangos, _manifiesto y _claves viven en libs/protegidos\n    # (ARGUS_PROTEGIDOS_TESTS = BUILD_TESTS)\n# [DDOS-MITIGACION-D301] test de la mitigacion ddos_v2 (mismo patron que test_protegidos_rangos)\n'),
    ],
    'libs/protegidos/CMakeLists.txt': [
        ('# en /usr/local/lib se podría cambiar por una que lo acepte todo sin tocar el binario.\n# La clave pública NO está aquí: claves_protegidos_compiladas() la define cada componente con sus -D (patrón ADR-025).\n# Opción ARGUS_PROTEGIDOS_TESTS (defecto OFF): el firewall la enciende con sus tests; el etcd-server no la repite.\n',
         '# en /usr/local/lib se podría cambiar por una que lo acepte todo sin tocar el binario.\n# La clave pública va en un objetivo aparte, argus_protegidos_clave (src/claves.cpp con los -D de la clave), que\n# enlazan el firewall-acl-agent y el etcd-server (ADR-060 F-A: el etcd-server verifica con la misma clave compilada).\n# Opción ARGUS_PROTEGIDOS_TESTS (defecto OFF): el firewall la enciende con sus tests; el etcd-server no la repite.\n'),
        ('\noption(ARGUS_PROTEGIDOS_TESTS "Tests de libs/protegidos" OFF)\n',
         '\n# ============================================================================\n# [PROTEGIDOS-MANIFIESTO-D318] ADR-060 D3 / D-E: clave PÚBLICA del manifiesto de protegidos (Vault transit del\n# hospital), compilada en dos ranuras (patrón ADR-025). No es un secreto. Sin la ranura actual NO se compila: no hay\n# defecto sano para una clave de confianza.\n#   -DARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX=<64 hex>     (producción: la pasa Jenkins)\n#   -DARGUS_PROTEGIDOS_PUBKEY_SIGUIENTE_HEX=<64 hex>  (solo durante una rotación; si no, vacía)\n# Sin -D se leen de /etc/ml-defender/firewall-acl-agent/protegidos_pubkey_{actual,siguiente}.hex; en el lab los\n# trae de la VM etcd `make protegidos-pubkey` (bootstrap [4b/8]). En el lab el firewall-acl-agent y el etcd-server se\n# compilan los dos en el defender: leen el mismo fichero (ADR-060 F-A).\n# ============================================================================\nset(ARGUS_PROTEGIDOS_PUBKEY_DIR /etc/ml-defender/firewall-acl-agent)\nforeach(RANURA ACTUAL SIGUIENTE)\n    string(TOLOWER ${RANURA} ranura)\n    set(_fich ${ARGUS_PROTEGIDOS_PUBKEY_DIR}/protegidos_pubkey_${ranura}.hex)\n    if(DEFINED ARGUS_PROTEGIDOS_PUBKEY_${RANURA}_HEX)\n        set(_origen "-D")\n    elseif(EXISTS ${_fich})\n        file(READ ${_fich} _v)\n        string(STRIP "${_v}" _v)\n        set(ARGUS_PROTEGIDOS_PUBKEY_${RANURA}_HEX "${_v}")\n        set(_origen "fichero ${_fich}")\n    else()\n        set(ARGUS_PROTEGIDOS_PUBKEY_${RANURA}_HEX "")\n        set(_origen "ausente: ni -D ni ${_fich}")\n    endif()\n    set(_v "${ARGUS_PROTEGIDOS_PUBKEY_${RANURA}_HEX}")\n    if(RANURA STREQUAL "ACTUAL" AND _v STREQUAL "")\n        message(FATAL_ERROR "[PROTEGIDOS-CLAVE] falta la clave pública ACTUAL del manifiesto de protegidos (${_origen}). "\n                            "Lab: make protegidos-pubkey desde el Mac. Producción: -DARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX=<64 hex>")\n    endif()\n    string(LENGTH "${_v}" _n)\n    if(NOT _v STREQUAL "" AND (NOT _n EQUAL 64 OR NOT _v MATCHES "^[0-9a-f]+$"))\n        message(FATAL_ERROR "[PROTEGIDOS-CLAVE] clave pública ${RANURA} mal formada (${_origen}): 64 caracteres hex en minúsculas")\n    endif()\n    if(_v STREQUAL "")\n        message(STATUS "[PROTEGIDOS-CLAVE] ${RANURA}: ninguna (${_origen})")\n    else()\n        string(SUBSTRING "${_v}" 0 16 _ini)\n        message(STATUS "[PROTEGIDOS-CLAVE] ${RANURA}: ${_ini}... (${_origen})")\n    endif()\nendforeach()\n\nadd_library(argus_protegidos_clave STATIC src/claves.cpp)\nset_target_properties(argus_protegidos_clave PROPERTIES POSITION_INDEPENDENT_CODE ON)\ntarget_link_libraries(argus_protegidos_clave PUBLIC argus_protegidos)\ntarget_compile_definitions(argus_protegidos_clave PRIVATE\n        ARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX="${ARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX}"\n        ARGUS_PROTEGIDOS_PUBKEY_SIGUIENTE_HEX="${ARGUS_PROTEGIDOS_PUBKEY_SIGUIENTE_HEX}")\n\noption(ARGUS_PROTEGIDOS_TESTS "Tests de libs/protegidos" OFF)\n'),
        ('    add_test(NAME test_protegidos_manifiesto COMMAND test_protegidos_manifiesto)\nendif()\n',
         '    add_test(NAME test_protegidos_manifiesto COMMAND test_protegidos_manifiesto)\n    # la clave compilada es la de CMake, en las dos ranuras\n    add_executable(test_protegidos_claves tests/test_protegidos_claves.cpp)\n    target_include_directories(test_protegidos_claves PRIVATE ${PROT_SODIUM_INCLUDE})\n    target_link_libraries(test_protegidos_claves PRIVATE argus_protegidos_clave ${PROT_SODIUM_LIB})\n    target_compile_definitions(test_protegidos_claves PRIVATE\n            ARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX="${ARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX}"\n            ARGUS_PROTEGIDOS_PUBKEY_SIGUIENTE_HEX="${ARGUS_PROTEGIDOS_PUBKEY_SIGUIENTE_HEX}")\n    add_test(NAME test_protegidos_claves COMMAND test_protegidos_claves)\nendif()\n'),
    ],
    'libs/protegidos/include/protegidos/manifiesto.hpp': [
        ('    std::string hospital_id;\n    std::string planta;          // despliegue_id de este firewall\n    std::string firmante;\n',
         '    std::string hospital_id;\n    std::string planta;          // despliegue_id de este firewall (vacía en verificar_documento)\n    std::string firmante;\n'),
        ('                                           uint64_t version_aplicada);\n\n',
         '                                           uint64_t version_aplicada);\n// [PROTEGIDOS-MANIFIESTO-D318] 8e.3b, documento entero sin planta (el etcd-server antes de guardarlo, ADR-060 F-D):\n// misma firma, formato, límites y hospital, y versión > version_aplicada; además trae al menos una planta y ninguna,\n// sumada a "comun", repite red en la misma interfaz. Lo que rechazaría cualquier firewall del hospital, lo rechaza.\n// manifiesto->planta queda vacía; manifiesto->entradas = comun + todas las plantas.\nResultadoVerificacion verificar_documento(const std::string& sobre, const ClavesProtegidos& claves,\n                                          const std::string& hospital_id, uint64_t version_aplicada);\n\n'),
    ],
    'libs/protegidos/src/manifiesto.cpp': [
        ('\nResultadoVerificacion verificar_manifiesto(const std::string& sobre, const ClavesProtegidos& claves,\n                                           const std::string& hospital_id, const std::string& planta,\n                                           uint64_t version_aplicada) {\n    if (sodium_init() < 0) return rechazo(MotivoRechazo::FIRMA, "libsodium no inicializa");\n',
         '\nnamespace {\n// [PROTEGIDOS-MANIFIESTO-D318] planta == nullptr: documento entero (etcd-server, 8e.3b); si no, para ESE firewall\nResultadoVerificacion verificar(const std::string& sobre, const ClavesProtegidos& claves, const std::string& hospital_id,\n                                const std::string* planta_p, uint64_t version_aplicada) {\n    if (sodium_init() < 0) return rechazo(MotivoRechazo::FIRMA, "libsodium no inicializa");\n'),
        ('    }\n    if (!plantas.isMember(planta)) {\n        return rechazo(MotivoRechazo::PLANTA, "el manifiesto no trae la planta \'" + detalle_protegidos::saneado(planta) + "\'");\n    }\n    auto m = std::make_shared<ManifiestoVerificado>();\n    std::size_t total2 = 0;\n    validar_entradas(c["comun"], "comun", lim, true, &m->entradas, total2);\n    validar_entradas(plantas[planta], "plantas." + planta, lim, false, &m->entradas, total2);\n    if (auto r = repetidas(m->entradas)) return rechazo(MotivoRechazo::FORMATO, "carga: " + *r);\n    m->version = version;\n    m->hospital_id = c["hospital_id"].asString();\n    m->planta = planta;\n    m->firmante = c["firmante"].asString();\n',
         '    }\n    auto m = std::make_shared<ManifiestoVerificado>();\n    std::size_t total2 = 0;\n    if (planta_p != nullptr) {\n        const std::string& planta = *planta_p;\n        if (!plantas.isMember(planta)) {\n            return rechazo(MotivoRechazo::PLANTA, "el manifiesto no trae la planta \'" + detalle_protegidos::saneado(planta) + "\'");\n        }\n        validar_entradas(c["comun"], "comun", lim, true, &m->entradas, total2);\n        validar_entradas(plantas[planta], "plantas." + planta, lim, false, &m->entradas, total2);\n        if (auto r = repetidas(m->entradas)) return rechazo(MotivoRechazo::FORMATO, "carga: " + *r);\n        m->planta = planta;\n    } else {\n        // Documento entero: lo que rechazaría CUALQUIER firewall del hospital lo rechaza el servidor\n        if (plantas.getMemberNames().empty()) return rechazo(MotivoRechazo::PLANTA, "el manifiesto no trae ninguna planta");\n        validar_entradas(c["comun"], "comun", lim, true, &m->entradas, total2);\n        for (const auto& p : plantas.getMemberNames()) {\n            std::vector<EntradaProtegida> una;\n            std::size_t t3 = 0;\n            validar_entradas(c["comun"], "comun", lim, true, &una, t3);\n            validar_entradas(plantas[p], "plantas." + p, lim, false, &una, t3);\n            if (auto r = repetidas(una)) return rechazo(MotivoRechazo::FORMATO, "carga: planta " + p + ": " + *r);\n            validar_entradas(plantas[p], "plantas." + p, lim, false, &m->entradas, total2);\n        }\n    }\n    m->version = version;\n    m->hospital_id = c["hospital_id"].asString();\n    m->firmante = c["firmante"].asString();\n'),
        ('    r.manifiesto = m;\n    return r;\n}\n\n',
         '    r.manifiesto = m;\n    return r;\n}\n}  // namespace\n\nResultadoVerificacion verificar_manifiesto(const std::string& sobre, const ClavesProtegidos& claves,\n                                           const std::string& hospital_id, const std::string& planta,\n                                           uint64_t version_aplicada) {\n    return verificar(sobre, claves, hospital_id, &planta, version_aplicada);\n}\n\nResultadoVerificacion verificar_documento(const std::string& sobre, const ClavesProtegidos& claves,\n                                          const std::string& hospital_id, uint64_t version_aplicada) {\n    return verificar(sobre, claves, hospital_id, nullptr, version_aplicada);\n}\n\n'),
    ],
    'libs/protegidos/tests/test_protegidos_manifiesto.cpp': [
        ('#include "protegidos/manifiesto.hpp"\n\n',
         '#include "protegidos/manifiesto.hpp"\n#include "ayuda_firma.hpp"\n\n'),
        ('using namespace argus::protegidos;\nusing C = CategoriaProtegida;\n',
         'using namespace argus::protegidos;\nusing namespace argus::protegidos::prueba;\nusing C = CategoriaProtegida;\n'),
        ('    } while (0)\n\nstruct Par {\n    unsigned char pk[crypto_sign_PUBLICKEYBYTES];\n    unsigned char sk[crypto_sign_SECRETKEYBYTES];\n    Par() { crypto_sign_keypair(pk, sk); }\n    std::string hex() const {\n        char h[crypto_sign_PUBLICKEYBYTES * 2 + 1];\n        sodium_bin2hex(h, sizeof h, pk, sizeof pk);\n        return h;\n    }\n};\n\nstatic std::string b64(const std::string& d) {\n    std::string o(sodium_base64_ENCODED_LEN(d.size(), sodium_base64_VARIANT_ORIGINAL), \'\\0\');\n    sodium_bin2base64(o.data(), o.size(), reinterpret_cast<const unsigned char*>(d.data()), d.size(),\n                      sodium_base64_VARIANT_ORIGINAL);\n    o.resize(o.size() - 1);\n    return o;\n}\n\nstatic std::string firmar(const Par& p, const std::string& carga, int v = 1) {\n    unsigned char sig[crypto_sign_BYTES];\n    crypto_sign_detached(sig, nullptr, reinterpret_cast<const unsigned char*>(carga.data()), carga.size(), p.sk);\n    return "vault:v" + std::to_string(v) + ":" + b64(std::string(reinterpret_cast<const char*>(sig), sizeof sig));\n}\n\nstatic std::string sobre(const std::string& carga, const std::string& firma, const std::string& extra = "") {\n    return "{\\"formato\\":\\"argus-protegidos/v1\\",\\"carga_b64\\":\\"" + b64(carga) + "\\",\\"firma\\":\\"" + firma + "\\"" + extra + "}";\n}\n\nstatic std::string entrada(const std::string& cat, const std::string& cidr, const std::string& iface = "eth2",\n                           const std::string& mac = "", const std::string& motivo = "prueba") {\n    return "{\\"categoria\\":\\"" + cat + "\\",\\"cidr\\":\\"" + cidr + "\\",\\"interfaz\\":\\"" + iface + "\\",\\"mac\\":\\"" + mac +\n           "\\",\\"motivo\\":\\"" + motivo + "\\"}";\n}\n\nstatic std::string carga(uint64_t version, const std::string& planta_lab, const std::string& comun = "",\n                         const std::string& limites = "{\\"infraestructura\\":32,\\"intranet\\":24,\\"dmz\\":24,\\"externos_criticos\\":32}",\n                         const std::string& hospital = "hospital-lab", const std::string& extra = "",\n                         const std::string& otras_plantas = "") {\n    return "{\\"esquema\\":1,\\"hospital_id\\":\\"" + hospital + "\\",\\"version\\":" + std::to_string(version) +\n           ",\\"emitido_utc\\":\\"2026-11-05T08:00:00Z\\",\\"firmante\\":\\"argus-infra\\",\\"motivo\\":\\"alta del lab\\","\n           "\\"hash_anterior\\":\\"\\",\\"limites\\":" + limites + ",\\"comun\\":[" + comun + "],\\"plantas\\":{\\"lab-vagrant\\":[" +\n           planta_lab + "]" + otras_plantas + "}" + extra + "}";\n}\n\n',
         '    } while (0)\n\n'),
        ('    }\n    // 11. Caché: escribir y leer; ausente; enlace simbólico; tamaño\n',
         '    }\n    // 10c. [8e.3b] documento entero (etcd-server): sin planta; lo que rechazaría cualquier firewall, lo rechaza\n    {\n        const std::string otra_ok = ",\\"planta-2\\":[" + entrada("intranet", "10.1.0.0/24", "eth1") + "]";\n        const std::string c1 = carga(3, kLab, "", "{\\"infraestructura\\":32,\\"intranet\\":24,\\"dmz\\":24,\\"externos_criticos\\":32}",\n                                     "hospital-lab", "", otra_ok);\n        const auto r = verificar_documento(sobre(c1, firmar(a, c1)), solo_a, "hospital-lab", 2);\n        CHECK(r.ok && r.manifiesto && r.manifiesto->planta.empty() && r.manifiesto->version == 3);\n        CHECK(r.ok && r.manifiesto->entradas.size() == 3);   // comun (0) + lab-vagrant (2) + planta-2 (1)\n        CHECK(rech(verificar_documento(sobre(c1, firmar(a, c1)), solo_a, "hospital-lab", 3), M::VERSION));\n        CHECK(rech(verificar_documento(sobre(c1, firmar(a, c1)), solo_a, "otro-hospital", 0), M::HOSPITAL));\n        CHECK(rech(verificar_documento(sobre(c1, firmar(otra, c1)), solo_a, "hospital-lab", 0), M::FIRMA));\n        // En OTRA planta, la misma red e interfaz que en comun: el firewall de lab-vagrant lo aceptaría, el servidor no\n        const std::string comun = entrada("intranet", "10.9.0.0/24", "eth1");\n        const std::string otra_mal = ",\\"planta-2\\":[" + entrada("intranet", "10.9.0.0/24", "eth1") + "]";\n        const std::string c2 = carga(4, kLab, comun, "{\\"infraestructura\\":32,\\"intranet\\":24,\\"dmz\\":24,\\"externos_criticos\\":32}",\n                                     "hospital-lab", "", otra_mal);\n        CHECK(verificar_manifiesto(sobre(c2, firmar(a, c2)), solo_a, "hospital-lab", "lab-vagrant", 0).ok);\n        CHECK(rech(verificar_documento(sobre(c2, firmar(a, c2)), solo_a, "hospital-lab", 0), M::FORMATO));\n        // Sin ninguna planta\n        std::string c3 = carga(5, kLab);\n        const std::string pl = "\\"plantas\\":{\\"lab-vagrant\\":[" + kLab + "]}";\n        c3.replace(c3.find(pl), pl.size(), "\\"plantas\\":{}");\n        CHECK(rech(verificar_documento(sobre(c3, firmar(a, c3)), solo_a, "hospital-lab", 0), M::PLANTA));\n    }\n    // 11. Caché: escribir y leer; ausente; enlace simbólico; tamaño\n'),
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
