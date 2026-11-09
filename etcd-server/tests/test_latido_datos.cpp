// etcd-server/tests/test_latido_datos.cpp — [LATIDO-DATOS-D321] ADR-060 8e.4c (H-H)
// La regla única de los datos del latido (libs/latido/datos_latido.hpp, la misma que aplica el etcd-client) y lo que
// hace el registro con ellos: guardarlos en latido/<CN>, conservarlos al marcar muerto y tras un reinicio, quitarlos si
// el siguiente latido no los trae o los trae mal (el latido se guarda igual: decisión de Alonso DAY321) y avisar del
// rechazo solo cuando cambia. Sin red: MemoriaRegistryStore y reloj inyectado.
#include "etcd_server/registro_componentes.hpp"
#include "latido/datos_latido.hpp"
#include <gtest/gtest.h>
#include <sstream>

using namespace argus::registro;
using argus::almacen::MemoriaRegistryStore;
using json = nlohmann::json;
namespace L = argus::latido;

namespace {
struct Banco {
    MemoriaRegistryStore* etcd = nullptr;  // lo posee el registro
    std::time_t ahora = 1000;
    std::ostringstream log;
    std::unique_ptr<RegistroComponentes> r;
    Banco() {
        auto m = std::make_unique<MemoriaRegistryStore>();
        etcd = m.get();
        r = std::make_unique<RegistroComponentes>(std::move(m), 30, 3, 10, 60, false, [this] { return ahora; }, log);
        EXPECT_EQ(r->registrar("firewall-acl-agent", json{{"component", "firewall-acl-agent"}}), Resultado::Ok);
    }
    size_t veces(const std::string& marca) const {
        const std::string s = log.str();
        size_t n = 0;
        for (size_t p = s.find(marca); p != std::string::npos; p = s.find(marca, p + 1)) ++n;
        return n;
    }
    json en_etcd() {
        std::string v;
        EXPECT_EQ(etcd->leer("latido/firewall-acl-agent", v), argus::almacen::Estado::Ok);
        return json::parse(v);
    }
    // Lo mismo que hace la ruta POST /v1/heartbeat/{c} del etcd-server con el cuerpo
    Resultado latir_cuerpo(const json& body) {
        std::string rechazo;
        const json* datos = nullptr;
        if (body.contains("datos")) {
            rechazo = L::validar_datos(body["datos"]);
            if (rechazo.empty()) datos = &body["datos"];
        }
        std::time_t t = 0;
        return r->latir("firewall-acl-agent", t, datos, rechazo);
    }
};
}  // namespace

TEST(ReglaDatosLatido, ClavesValidasYNo) {
    EXPECT_TRUE(L::clave_valida("protegidos_version"));
    EXPECT_TRUE(L::clave_valida("a"));
    EXPECT_TRUE(L::clave_valida(std::string(32, 'a')));
    EXPECT_FALSE(L::clave_valida(std::string(33, 'a')));
    EXPECT_FALSE(L::clave_valida(""));
    EXPECT_FALSE(L::clave_valida("1version"));
    EXPECT_FALSE(L::clave_valida("_version"));
    EXPECT_FALSE(L::clave_valida("Version"));
    EXPECT_FALSE(L::clave_valida("ver-sion"));
    EXPECT_FALSE(L::clave_valida("ver sion"));
    EXPECT_FALSE(L::clave_valida("../x"));
}

TEST(ReglaDatosLatido, ValoresEnRango) {
    EXPECT_TRUE(L::valor_valido(0));
    EXPECT_TRUE(L::valor_valido(L::kMaxValor));
    EXPECT_FALSE(L::valor_valido(L::kMaxValor + 1));
    EXPECT_FALSE(L::valor_valido(-1));
    EXPECT_EQ(L::kMaxValor, 9007199254740991LL);
}

TEST(ReglaDatosLatido, ObjetoDatos) {
    EXPECT_EQ(L::validar_datos(json::object()), "");
    EXPECT_EQ(L::validar_datos(json{{"protegidos_version", 5}}), "");
    EXPECT_EQ(L::validar_datos(json{{"a", 0}, {"b", L::kMaxValor}}), "");
    json ocho = json::object();
    for (int i = 0; i < 8; ++i) ocho["d" + std::to_string(i)] = i;
    EXPECT_EQ(L::validar_datos(ocho), "");
    json nueve = ocho;
    nueve["d8"] = 8;
    EXPECT_NE(L::validar_datos(nueve).find("9 claves"), std::string::npos);
    EXPECT_NE(L::validar_datos(json::array({1})).find("no es un objeto"), std::string::npos);
    EXPECT_NE(L::validar_datos(json(5)).find("no es un objeto"), std::string::npos);
    EXPECT_NE(L::validar_datos(json{{"Mal", 1}}).find("clave 'Mal'"), std::string::npos);
    EXPECT_NE(L::validar_datos(json{{"v", -1}}).find("valor de 'v'"), std::string::npos);
    EXPECT_NE(L::validar_datos(json{{"v", 1.5}}).find("valor de 'v'"), std::string::npos);
    EXPECT_NE(L::validar_datos(json{{"v", 5.0}}).find("valor de 'v'"), std::string::npos);  // solo enteros
    EXPECT_NE(L::validar_datos(json{{"v", true}}).find("valor de 'v'"), std::string::npos);
    EXPECT_NE(L::validar_datos(json{{"v", "5"}}).find("valor de 'v'"), std::string::npos);
    EXPECT_NE(L::validar_datos(json{{"v", nullptr}}).find("valor de 'v'"), std::string::npos);
    EXPECT_NE(L::validar_datos(json{{"v", json::object()}}).find("valor de 'v'"), std::string::npos);
    EXPECT_NE(L::validar_datos(json{{"v", static_cast<std::uint64_t>(L::kMaxValor) + 1}}).find("valor de 'v'"),
              std::string::npos);
    EXPECT_NE(L::validar_datos(json{{"v", 18446744073709551615ULL}}).find("valor de 'v'"), std::string::npos);
    // El motivo lleva el formato completo (campo, formato y límites, como los avisos de configuración)
    EXPECT_NE(L::validar_datos(json{{"v", -1}}).find(L::formato()), std::string::npos);
    // Una clave con caracteres de control no llega tal cual al log
    const std::string m = L::validar_datos(json{{std::string("a\nb\x01"), 1}});
    EXPECT_EQ(m.find('\n'), std::string::npos);
    EXPECT_EQ(m.find('\x01'), std::string::npos);
}

TEST(RegistroLatidoDatos, GuardaDatosEnEtcdYEnLaCopia) {
    Banco b;
    ASSERT_EQ(b.latir_cuerpo(json{{"timestamp", 1}, {"datos", {{"protegidos_version", 5}}}}), Resultado::Ok);
    EXPECT_EQ(b.en_etcd()["datos"], (json{{"protegidos_version", 5}}));
    EXPECT_EQ(b.en_etcd()["estado"], "activo");
    EXPECT_EQ(b.r->datos_latido("firewall-acl-agent"), (json{{"protegidos_version", 5}}));
    ASSERT_EQ(b.latir_cuerpo(json{{"timestamp", 2}, {"datos", {{"protegidos_version", 6}}}}), Resultado::Ok);
    EXPECT_EQ(b.en_etcd()["datos"]["protegidos_version"], 6);
    EXPECT_EQ(b.veces("[ETCD-LATIDO-DATOS-RECHAZADOS]"), 0u);
}

TEST(RegistroLatidoDatos, SinDatosNoHayClaveDatos) {
    Banco b;
    ASSERT_EQ(b.latir_cuerpo(json{{"timestamp", 1}, {"datos", {{"protegidos_version", 5}}}}), Resultado::Ok);
    ASSERT_EQ(b.latir_cuerpo(json{{"timestamp", 2}}), Resultado::Ok);  // otro componente o el mismo sin datos
    EXPECT_FALSE(b.en_etcd().contains("datos"));
    EXPECT_EQ(b.r->datos_latido("firewall-acl-agent"), json::object());
}

TEST(RegistroLatidoDatos, RechazoGuardaElLatidoSinDatosYAvisaSoloAlCambiar) {
    Banco b;
    ASSERT_EQ(b.latir_cuerpo(json{{"timestamp", 1}, {"datos", {{"protegidos_version", 5}}}}), Resultado::Ok);
    b.ahora += 30;
    // Datos mal formados: el latido cuenta (ultimo avanza, sigue activo) pero sin datos
    ASSERT_EQ(b.latir_cuerpo(json{{"timestamp", 2}, {"datos", {{"protegidos_version", -3}}}}), Resultado::Ok);
    EXPECT_EQ(b.en_etcd()["ultimo"], 1030);
    EXPECT_EQ(b.en_etcd()["estado"], "activo");
    EXPECT_FALSE(b.en_etcd().contains("datos"));
    EXPECT_EQ(b.veces("[ETCD-LATIDO-DATOS-RECHAZADOS] firewall-acl-agent: valor de 'protegidos_version'"), 1u);
    // El mismo rechazo en cada latido: no se repite en el log
    ASSERT_EQ(b.latir_cuerpo(json{{"timestamp", 3}, {"datos", {{"protegidos_version", -3}}}}), Resultado::Ok);
    ASSERT_EQ(b.latir_cuerpo(json{{"timestamp", 4}, {"datos", {{"protegidos_version", -3}}}}), Resultado::Ok);
    EXPECT_EQ(b.veces("[ETCD-LATIDO-DATOS-RECHAZADOS]"), 1u);
    // Otro motivo: se avisa otra vez
    ASSERT_EQ(b.latir_cuerpo(json{{"timestamp", 5}, {"datos", json::array()}}), Resultado::Ok);
    EXPECT_EQ(b.veces("[ETCD-LATIDO-DATOS-RECHAZADOS]"), 2u);
    // Vuelven datos válidos: se avisa una vez y se guardan
    ASSERT_EQ(b.latir_cuerpo(json{{"timestamp", 6}, {"datos", {{"protegidos_version", 7}}}}), Resultado::Ok);
    ASSERT_EQ(b.latir_cuerpo(json{{"timestamp", 7}, {"datos", {{"protegidos_version", 7}}}}), Resultado::Ok);
    EXPECT_EQ(b.veces("[ETCD-LATIDO-DATOS-ACEPTADOS] firewall-acl-agent"), 1u);
    EXPECT_EQ(b.en_etcd()["datos"]["protegidos_version"], 7);
}

TEST(RegistroLatidoDatos, MuertoConservaLosDatosYElLatidoLosRenueva) {
    Banco b;
    ASSERT_EQ(b.latir_cuerpo(json{{"timestamp", 1}, {"datos", {{"protegidos_version", 4}}}}), Resultado::Ok);
    b.ahora += 91;  // > 30 * 3
    b.r->revisar_latidos();
    EXPECT_EQ(b.en_etcd()["estado"], "muerto");
    EXPECT_EQ(b.en_etcd()["datos"]["protegidos_version"], 4);  // pipeline-status ve la versión que tenía al morir
    EXPECT_EQ(b.r->datos_latido("firewall-acl-agent")["protegidos_version"], 4);
    ASSERT_EQ(b.latir_cuerpo(json{{"timestamp", 2}, {"datos", {{"protegidos_version", 5}}}}), Resultado::Ok);
    EXPECT_EQ(b.en_etcd()["estado"], "activo");
    EXPECT_EQ(b.en_etcd()["datos"]["protegidos_version"], 5);
}

TEST(RegistroLatidoDatos, NoRegistradoNoGuardaNada) {
    Banco b;
    std::time_t t = 0;
    const json d{{"protegidos_version", 1}};
    EXPECT_EQ(b.r->latir("otro", t, &d, ""), Resultado::NoEncontrado);
    std::string v;
    EXPECT_EQ(b.etcd->leer("latido/otro", v), argus::almacen::Estado::NoEncontrado);
    EXPECT_EQ(b.r->latir("otro", t, nullptr, "x"), Resultado::NoEncontrado);
    EXPECT_EQ(b.veces("[ETCD-LATIDO-DATOS-RECHAZADOS]"), 0u);  // ni el aviso de un nombre no registrado
}
