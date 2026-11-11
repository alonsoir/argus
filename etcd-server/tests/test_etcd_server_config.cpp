// etcd-server/tests/test_etcd_server_config.cpp — [ETCD-CONFIG-D312]
// Lector de etcd-server.json (server/secrets/heartbeat): JSON bueno, ausente, tipo, rango, reglas, obsoletos, y que
// la línea [ETCD-CONFIG] diga de dónde sale cada valor. Sin red ni ficheros.
#include "etcd_server/etcd_server_config.hpp"
#include <gtest/gtest.h>
#include <sstream>

using argus::etcdcfg::parse_etcd_server_config;
using json = nlohmann::json;

namespace {
json bueno() {
    return json::parse(R"({
      "server": {"host": "192.168.100.20", "port": 2379},
      "secrets": {"grace_period_seconds": 300, "default_key_length_bytes": 32, "min_rotation_interval_seconds": 600},
      "heartbeat": {"interval_seconds": 30, "timeout_multiplier": 3, "check_interval_seconds": 10},
      "identity": {"component_id": "etcd-server", "keys_dir": "/etc/ml-defender/etcd-server"},
      "alerting": {"enabled": false, "providers": []}
    })");
}
struct Salida { std::ostringstream aviso, info; };
}  // namespace

TEST(EtcdServerConfig, JsonBuenoTodoDelJson) {
    Salida o;
    auto r = parse_etcd_server_config(bueno(), o.aviso, o.info);
    EXPECT_EQ(r.defectos, 0);
    EXPECT_EQ(r.obsoletos, 0);
    EXPECT_EQ(r.cfg.host, "192.168.100.20");
    EXPECT_EQ(r.cfg.port, 2379);
    EXPECT_EQ(r.cfg.min_rotation_interval_seconds, 600);
    EXPECT_TRUE(o.aviso.str().empty()) << o.aviso.str();
    EXPECT_NE(o.info.str().find("server.host=192.168.100.20 (JSON)"), std::string::npos) << o.info.str();
    EXPECT_EQ(o.info.str().find("DEFECTO"), std::string::npos) << o.info.str();
}

TEST(EtcdServerConfig, VacioTodoDefectoYArranca) {
    Salida o;
    auto r = parse_etcd_server_config(json::object(), o.aviso, o.info);
    EXPECT_EQ(r.defectos, 8);
    EXPECT_EQ(r.cfg.host, "0.0.0.0");
    EXPECT_EQ(r.cfg.port, 2379);
    EXPECT_EQ(r.cfg.grace_period_seconds, 300);
    EXPECT_EQ(r.cfg.heartbeat_check_interval_seconds, 10);
    EXPECT_NE(o.aviso.str().find("[CONFIG-DEFAULT] server.port ausente (entero en [1024, 65535]): se usa 2379"),
              std::string::npos) << o.aviso.str();
    EXPECT_NE(o.info.str().find("server.port=2379 (DEFECTO: ausente)"), std::string::npos) << o.info.str();
}

TEST(EtcdServerConfig, RaizNoObjeto) {
    Salida o;
    auto r = parse_etcd_server_config(json::array(), o.aviso, o.info);
    EXPECT_EQ(r.defectos, 8);
    EXPECT_NE(o.aviso.str().find("la raíz de etcd-server.json no es un objeto"), std::string::npos);
}

TEST(EtcdServerConfig, TiposEquivocados) {
    auto j = bueno();
    j["server"]["port"] = "2379";                     // cadena
    j["secrets"]["grace_period_seconds"] = 300.0;     // real
    j["heartbeat"]["timeout_multiplier"] = true;      // booleano
    j["server"]["host"] = 3232261140;                 // número, no cadena
    Salida o;
    auto r = parse_etcd_server_config(j, o.aviso, o.info);
    EXPECT_EQ(r.defectos, 4);
    EXPECT_EQ(r.cfg.port, 2379);
    EXPECT_EQ(r.cfg.grace_period_seconds, 300);
    EXPECT_EQ(r.cfg.heartbeat_timeout_multiplier, 3);
    EXPECT_EQ(r.cfg.host, "0.0.0.0");
    EXPECT_NE(o.aviso.str().find("server.port=\"2379\" no es entero"), std::string::npos) << o.aviso.str();
    EXPECT_NE(o.info.str().find("secrets.grace_period_seconds=300 (DEFECTO: no entero)"), std::string::npos);
}

TEST(EtcdServerConfig, IpMalFormada) {
    for (const char* mala : {"0.0.0", "256.1.1.1", "localhost", "", "::1"}) {
        auto j = bueno();
        j["server"]["host"] = mala;
        Salida o;
        auto r = parse_etcd_server_config(j, o.aviso, o.info);
        EXPECT_EQ(r.cfg.host, "0.0.0.0") << mala;
        EXPECT_EQ(r.defectos, 1) << mala;
    }
}

TEST(EtcdServerConfig, FueraDeRango) {
    auto j = bueno();
    j["server"]["port"] = 80;                          // < 1024
    j["secrets"]["default_key_length_bytes"] = 16;     // < 32: HMAC-SHA256 con clave corta
    j["heartbeat"]["interval_seconds"] = -5;
    Salida o;
    auto r = parse_etcd_server_config(j, o.aviso, o.info);
    EXPECT_EQ(r.defectos, 3);
    EXPECT_EQ(r.cfg.port, 2379);
    EXPECT_EQ(r.cfg.default_key_length_bytes, 32);
    EXPECT_EQ(r.cfg.heartbeat_interval_seconds, 30);
    EXPECT_NE(o.aviso.str().find("secrets.default_key_length_bytes=16 fuera de rango (entero en [32, 64])"),
              std::string::npos) << o.aviso.str();
}

TEST(EtcdServerConfig, LimitesExactosValen) {
    auto j = bueno();
    j["server"]["port"] = 1024;
    j["secrets"]["default_key_length_bytes"] = 64;
    Salida o;
    auto r = parse_etcd_server_config(j, o.aviso, o.info);
    EXPECT_EQ(r.defectos, 0) << o.aviso.str();
    EXPECT_EQ(r.cfg.port, 1024);
    EXPECT_EQ(r.cfg.default_key_length_bytes, 64);
}

TEST(EtcdServerConfig, ReglaRotacionMinimaContraGracia) {
    auto j = bueno();
    j["secrets"]["grace_period_seconds"] = 900;
    j["secrets"]["min_rotation_interval_seconds"] = 600;  // < gracia: las claves se acumularían
    Salida o;
    auto r = parse_etcd_server_config(j, o.aviso, o.info);
    EXPECT_EQ(r.defectos, 1);
    EXPECT_EQ(r.cfg.grace_period_seconds, 300);
    EXPECT_EQ(r.cfg.min_rotation_interval_seconds, 300);
    EXPECT_NE(o.info.str().find("(DEFECTO: regla min_rotation >= grace)"), std::string::npos) << o.info.str();
}

TEST(EtcdServerConfig, ReglaLatidos) {
    auto j = bueno();
    j["heartbeat"]["interval_seconds"] = 5;
    j["heartbeat"]["timeout_multiplier"] = 2;
    j["heartbeat"]["check_interval_seconds"] = 60;  // > 5 * 2: un muerto pasaría sin detectarse
    Salida o;
    auto r = parse_etcd_server_config(j, o.aviso, o.info);
    EXPECT_EQ(r.defectos, 1);
    EXPECT_EQ(r.cfg.heartbeat_interval_seconds, 30);
    EXPECT_EQ(r.cfg.heartbeat_timeout_multiplier, 3);
    EXPECT_EQ(r.cfg.heartbeat_check_interval_seconds, 10);
}

TEST(EtcdServerConfig, ObsoletosAvisanYNoCuentanComoDefecto) {
    auto j = bueno();
    j["server"]["worker_threads"] = 4;
    j["secrets"]["rotation_interval_hours"] = 168;
    j["secrets"]["storage"] = json::object();
    j["heartbeat"]["enabled"] = true;
    j["auto_restart"] = json::object();
    j["security"] = json::object();
    Salida o;
    auto r = parse_etcd_server_config(j, o.aviso, o.info);
    EXPECT_EQ(r.defectos, 0);
    EXPECT_EQ(r.obsoletos, 6);
    EXPECT_NE(o.aviso.str().find("[CONFIG-OBSOLETO] auto_restart ya no se usa"), std::string::npos) << o.aviso.str();
    EXPECT_NE(o.aviso.str().find("[CONFIG-OBSOLETO] secrets.rotation_interval_hours ya no se usa"), std::string::npos);
}

TEST(EtcdServerConfig, BloqueQueNoEsObjeto) {
    auto j = bueno();
    j["heartbeat"] = 30;
    Salida o;
    auto r = parse_etcd_server_config(j, o.aviso, o.info);
    EXPECT_EQ(r.defectos, 3);
    EXPECT_NE(o.aviso.str().find("[CONFIG-DEFAULT] heartbeat no es un objeto"), std::string::npos);
}
