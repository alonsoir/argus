// test_protegidos_servidor.cpp — [PROTEGIDOS-MANIFIESTO-D318] ADR-060 8e.3b: GET/PUT del manifiesto de protegidos en el
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
