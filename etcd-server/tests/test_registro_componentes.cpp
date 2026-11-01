// etcd-server/tests/test_registro_componentes.cpp — [ETCD-REGISTRO-D313]
// RegistroComponentes sobre MemoriaRegistryStore con reloj inyectado (sin red): registro, nombres, latidos, muerto que se
// marca y no se borra, revivido, almacén no disponible (lectura de copia, escritura NoDisponible, avisos), recuperación
// y recarga, persistencia entre instancias (= reinicio del etcd-server), época, y parada inmediata del monitor.
#include "etcd_server/registro_componentes.hpp"
#include <gtest/gtest.h>
#include <chrono>
#include <fstream>
#include <sstream>

using namespace argus::registro;
using argus::almacen::Estado;
using argus::almacen::IRegistryStore;
using argus::almacen::MemoriaRegistryStore;
using json = nlohmann::json;

namespace {
// Reenvía a un almacén compartido: dos RegistroComponentes sobre el mismo "etcd" = reinicio del etcd-server
class Compartido : public IRegistryStore {
public:
    explicit Compartido(std::shared_ptr<MemoriaRegistryStore> m) : m_(std::move(m)) {}
    Estado poner(const std::string& k, const std::string& v) override { return m_->poner(k, v); }
    Estado leer(const std::string& k, std::string& v) override { return m_->leer(k, v); }
    Estado borrar(const std::string& k) override { return m_->borrar(k); }
    Estado listar(const std::string& p, std::map<std::string, std::string>& o) override { return m_->listar(p, o); }
    std::string descripcion() const override { return "memoria compartida (test)"; }
    std::string ultimo_error() const override { return m_->ultimo_error(); }

private:
    std::shared_ptr<MemoriaRegistryStore> m_;
};

struct Banco {
    std::shared_ptr<MemoriaRegistryStore> etcd = std::make_shared<MemoriaRegistryStore>();
    std::time_t ahora = 1000;
    std::ostringstream log;
    std::unique_ptr<RegistroComponentes> nuevo(bool memoria = false) {
        return std::make_unique<RegistroComponentes>(std::make_unique<Compartido>(etcd), 30, 3, 10, 60, memoria,
                                                     [this] { return ahora; }, log);
    }
    size_t veces(const std::string& marca) const {
        const std::string s = log.str();
        size_t n = 0;
        for (size_t p = s.find(marca); p != std::string::npos; p = s.find(marca, p + 1)) ++n;
        return n;
    }
};
json doc(const std::string& n) { return json{{"component", n}}; }
}  // namespace

TEST(RegistroComponentes, RegistrarListarLeer) {
    Banco b;
    auto r = b.nuevo();
    EXPECT_EQ(r->registrar("sniffer", doc("sniffer")), Resultado::Ok);
    std::vector<std::string> v;
    bool copia = true;
    r->listar(v, copia);
    EXPECT_FALSE(copia);
    ASSERT_EQ(v.size(), 1u);
    EXPECT_EQ(v[0], "sniffer");
    json d;
    ASSERT_EQ(r->leer_documento("sniffer", d), Resultado::Ok);
    EXPECT_EQ(d["version"], "1.0");  // como antes: se completa
    EXPECT_EQ(r->estado_latido("sniffer"), "activo");
    EXPECT_EQ(r->leer_documento("ml-detector", d), Resultado::NoEncontrado);
}

TEST(RegistroComponentes, NombresYDocumentosInvalidos) {
    Banco b;
    auto r = b.nuevo();
    for (const char* n : {"", "Sniffer", "a/b", "../x", "sniffer\n", "-x", "cpp_evolutionary_sniffer"})
        EXPECT_EQ(r->registrar(n, doc("x")), Resultado::NombreInvalido) << n;
    EXPECT_EQ(r->registrar("sniffer", json{{"x", 1}}), Resultado::DocumentoInvalido);
    EXPECT_EQ(r->registrar("sniffer", json::array()), Resultado::DocumentoInvalido);
    EXPECT_EQ(r->registrar("sniffer", json{{"component", {{"name", "cpp_evolutionary_sniffer"}}}}), Resultado::Ok);
    std::map<std::string, std::string> m;
    b.etcd->listar("", m);
    for (const auto& [k, _] : m) EXPECT_TRUE(k == "registro/sniffer" || k == "latido/sniffer") << k;
}

TEST(RegistroComponentes, LatidoDeNoRegistrado404) {
    Banco b;
    auto r = b.nuevo();
    std::time_t t = 0;
    EXPECT_EQ(r->latir("ml-detector", t), Resultado::NoEncontrado);
}

TEST(RegistroComponentes, MuertoSeMarcaNoSeBorraYRevive) {
    Banco b;
    auto r = b.nuevo();
    ASSERT_EQ(r->registrar("sniffer", doc("sniffer")), Resultado::Ok);
    b.ahora += 90;  // justo el límite (30 * 3): aún no
    r->revisar_latidos();
    EXPECT_EQ(r->estado_latido("sniffer"), "activo");
    b.ahora += 1;
    r->revisar_latidos();
    EXPECT_EQ(r->estado_latido("sniffer"), "muerto");
    EXPECT_EQ(b.veces("[ETCD-COMPONENTE-MUERTO] sniffer sin latido hace 91 s"), 1u) << b.log.str();
    r->revisar_latidos();  // no se repite
    EXPECT_EQ(b.veces("[ETCD-COMPONENTE-MUERTO]"), 1u);
    json d;
    EXPECT_EQ(r->leer_documento("sniffer", d), Resultado::Ok);  // el registro se conserva
    b.ahora += 20;
    std::time_t t = 0;
    EXPECT_EQ(r->latir("sniffer", t), Resultado::Ok);
    EXPECT_EQ(t, b.ahora);
    EXPECT_EQ(r->estado_latido("sniffer"), "activo");
    EXPECT_EQ(b.veces("[ETCD-COMPONENTE-REVIVIDO] sniffer vuelve a latir tras 111 s"), 1u) << b.log.str();
}

TEST(RegistroComponentes, AlmacenCaidoLeeCopiaYEscritura503) {
    Banco b;
    auto r = b.nuevo();
    ASSERT_EQ(r->registrar("sniffer", doc("sniffer")), Resultado::Ok);
    b.etcd->simular_caido(true);
    EXPECT_EQ(r->registrar("ml-detector", doc("ml-detector")), Resultado::NoDisponible);
    EXPECT_EQ(b.veces("[ETCD-ALMACEN-NO-DISPONIBLE]"), 1u);
    json d;
    EXPECT_EQ(r->leer_documento("sniffer", d), Resultado::Ok);  // copia
    EXPECT_EQ(r->leer_documento("ml-detector", d), Resultado::NoDisponible);  // ni en etcd ni en copia
    std::vector<std::string> v;
    bool copia = false;
    r->listar(v, copia);
    EXPECT_TRUE(copia);
    EXPECT_EQ(v.size(), 1u);
    std::time_t t = 0;
    EXPECT_EQ(r->latir("sniffer", t), Resultado::NoDisponible);
    EXPECT_EQ(r->actualizar_campo("sniffer", "x", "1"), Resultado::NoDisponible);  // escritura: sin copia
    EXPECT_EQ(r->desregistrar("sniffer"), Resultado::NoDisponible);
    EXPECT_FALSE(r->almacen_disponible());
    // Sin almacén no se marca muerto a nadie (la copia puede estar vieja)
    b.ahora += 500;
    r->revisar_latidos();
    EXPECT_EQ(b.veces("[ETCD-COMPONENTE-MUERTO]"), 0u);
    EXPECT_EQ(b.veces("[ETCD-ALMACEN-NO-DISPONIBLE] sigue sin responder desde hace 500 s"), 1u) << b.log.str();
    b.ahora += 30;  // < aviso_intervalo_s: no repite
    r->revisar_latidos();
    EXPECT_EQ(b.veces("sigue sin responder"), 1u);
    // Vuelve: aviso de recuperación y recarga
    b.etcd->simular_caido(false);
    r->revisar_latidos();
    EXPECT_TRUE(r->almacen_disponible());
    EXPECT_EQ(b.veces("[ETCD-ALMACEN-RECUPERADO] tras 530 s"), 1u) << b.log.str();
    EXPECT_EQ(r->estado_latido("sniffer"), "muerto");  // 530 s sin latido, ya con almacén
    EXPECT_EQ(r->latir("sniffer", t), Resultado::Ok);
}

TEST(RegistroComponentes, ReinicioConservaRegistroLatidosYEpoca) {
    Banco b;
    {
        auto r = b.nuevo();
        ASSERT_EQ(r->registrar("sniffer", doc("sniffer")), Resultado::Ok);
        ASSERT_EQ(r->registrar("ml-detector", doc("ml-detector")), Resultado::Ok);
        json e;
        EXPECT_EQ(r->leer_epoca(e), Resultado::NoEncontrado);
        ASSERT_EQ(r->guardar_epoca(json{{"epoch_id", 7}, {"not_before", "2026-11-01T00:00:00Z"}, {"revision", 3}}),
                  Resultado::Ok);
    }
    b.ahora += 15;
    auto r2 = b.nuevo();  // el etcd-server reinicia
    EXPECT_EQ(b.veces("[ETCD-REGISTRO-CARGADO] 2 componentes del almacén: ml-detector,sniffer"), 1u) << b.log.str();
    std::time_t t = 0;
    EXPECT_EQ(r2->latir("sniffer", t), Resultado::Ok);  // antes: 404 tras reiniciar (DAY311)
    json e;
    ASSERT_EQ(r2->leer_epoca(e), Resultado::Ok);
    EXPECT_EQ(e["epoch_id"], 7);
    EXPECT_EQ(e["revision"], 3);
}

TEST(RegistroComponentes, ArranqueConAlmacenCaidoRecargaLuego) {
    Banco b;
    {
        auto r = b.nuevo();
        ASSERT_EQ(r->registrar("sniffer", doc("sniffer")), Resultado::Ok);
    }
    b.etcd->simular_caido(true);
    auto r2 = b.nuevo();
    EXPECT_EQ(b.veces("no se pudo cargar el registro del almacén"), 1u) << b.log.str();
    b.etcd->simular_caido(false);
    r2->revisar_latidos();
    EXPECT_EQ(b.veces("[ETCD-REGISTRO-CARGADO] 1 componentes del almacén: sniffer"), 1u) << b.log.str();
}

TEST(RegistroComponentes, DesregistrarYActualizar) {
    Banco b;
    auto r = b.nuevo();
    ASSERT_EQ(r->registrar("firewall-acl-agent", doc("firewall-acl-agent")), Resultado::Ok);
    EXPECT_EQ(r->actualizar_campo("firewall-acl-agent", "modo", "sombra"), Resultado::Ok);
    json d;
    ASSERT_EQ(r->leer_documento("firewall-acl-agent", d), Resultado::Ok);
    EXPECT_EQ(d["modo"], "sombra");
    EXPECT_EQ(r->actualizar_campo("sniffer", "x", "1"), Resultado::NoEncontrado);
    EXPECT_EQ(r->desregistrar("firewall-acl-agent"), Resultado::Ok);
    EXPECT_EQ(r->desregistrar("firewall-acl-agent"), Resultado::NoEncontrado);
    std::map<std::string, std::string> m;
    b.etcd->listar("", m);
    EXPECT_TRUE(m.empty());
}

TEST(RegistroComponentes, ModoMemoriaAvisaPeriodicamente) {
    Banco b;
    auto r = b.nuevo(/*memoria=*/true);
    r->revisar_latidos();
    b.ahora += 59;
    r->revisar_latidos();
    EXPECT_EQ(b.veces("[ETCD-ALMACEN-MEMORIA]"), 1u);
    b.ahora += 1;
    r->revisar_latidos();
    EXPECT_EQ(b.veces("[ETCD-ALMACEN-MEMORIA]"), 2u);
}

TEST(RegistroComponentes, MonitorParaAlInstante) {
    Banco b;
    auto r = b.nuevo();
    r->arrancar_monitor();
    std::this_thread::sleep_for(std::chrono::milliseconds(150));
    const auto t0 = std::chrono::steady_clock::now();
    r->parar_monitor();
    const auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - t0).count();
    EXPECT_LT(ms, 500) << "antes esperaba hasta check_interval_seconds (10 s)";
}

// ── bloque "almacen" de etcd-server.json ───────────────────────────────────
namespace {
json leer_json(const std::string& nombre) {
    std::ifstream f(std::string(ETCD_SERVER_CONFIG_DIR) + "/" + nombre);
    EXPECT_TRUE(f.good()) << nombre;
    return json::parse(f);
}
}  // namespace

TEST(AlmacenConfig, AusenteTodoDefecto) {
    std::ostringstream av, in;
    auto r = argus::etcdcfg::parse_almacen_config(json::object(), av, in);
    EXPECT_EQ(r.defectos, 9);
    EXPECT_EQ(r.cfg.modo, "etcd");
    EXPECT_EQ(r.cfg.endpoints, std::vector<std::string>{"https://127.0.0.1:2381"});
    EXPECT_EQ(r.cfg.reconexion_max_ms, 1000);
    EXPECT_NE(in.str().find("almacen.modo=etcd (DEFECTO: ausente)"), std::string::npos) << in.str();
}

TEST(AlmacenConfig, ErrataNuncaRebajaAMemoria) {
    for (const char* malo : {R"("Memoria")", R"("mem")", R"("")", R"(1)", R"(null)"}) {
        std::ostringstream av, in;
        auto r = argus::etcdcfg::parse_almacen_config(json::parse(std::string(R"({"almacen": {"modo": )") + malo + "}}"),
                                                      av, in);
        EXPECT_EQ(r.cfg.modo, "etcd") << malo;
    }
}

TEST(AlmacenConfig, CamposMalFormados) {
    std::ostringstream av, in;
    auto r = argus::etcdcfg::parse_almacen_config(json::parse(R"({"almacen": {"modo": "etcd",
        "endpoints": ["http://127.0.0.1:2381"], "ca_file": "rel", "cert_file": "/a", "key_file": "/b",
        "prefijo": "argus", "timeout_ms": 50, "aviso_intervalo_s": 5, "reconexion_max_ms": 60001}})"), av, in);
    EXPECT_EQ(r.defectos, 6) << av.str();
    EXPECT_EQ(r.cfg.endpoints[0], "https://127.0.0.1:2381");
    EXPECT_EQ(r.cfg.ca_file, "/etc/argus-pki/ca.crt");
    EXPECT_EQ(r.cfg.cert_file, "/a");
    EXPECT_EQ(r.cfg.prefijo, "/argus/");
    EXPECT_EQ(r.cfg.timeout_ms, 2000);
    EXPECT_EQ(r.cfg.reconexion_max_ms, 1000);
    for (const char* ep : {"https://1.2.3:2381", "https://1.2.3.4", "https://1.2.3.4:0", "https://1.2.3.4:70000",
                           "https://256.1.1.1:2381", "https://a.b.c.d:2381"}) {
        std::ostringstream a2, i2;
        auto r2 = argus::etcdcfg::parse_almacen_config(json{{"almacen", {{"endpoints", {ep}}}}}, a2, i2);
        EXPECT_NE(a2.str().find("almacen.endpoints="), std::string::npos) << ep;
    }
    std::ostringstream a3, i3;
    auto r3 = argus::etcdcfg::parse_almacen_config(
        json{{"almacen", {{"endpoints", {"https://192.168.100.20:2381", "https://192.168.100.21:2381"}}}}}, a3, i3);
    EXPECT_EQ(r3.cfg.endpoints.size(), 2u);  // PR2: varios nodos
}

TEST(AlmacenConfig, JsonDelRepo) {
    std::ostringstream a1, i1, a2, i2;
    auto def = argus::etcdcfg::parse_almacen_config(leer_json("etcd-server.json"), a1, i1);
    EXPECT_EQ(def.defectos, 0) << a1.str();
    EXPECT_EQ(def.cfg.modo, "memoria");  // transición del defender, hasta el paso 6
    auto vm = argus::etcdcfg::parse_almacen_config(leer_json("etcd-server.etcd-vm.json"), a2, i2);
    EXPECT_EQ(vm.defectos, 0) << a2.str();
    const argus::etcdcfg::AlmacenConfig d{};
    EXPECT_EQ(vm.cfg.modo, d.modo);
    EXPECT_EQ(vm.cfg.endpoints, d.endpoints);
    EXPECT_EQ(vm.cfg.ca_file, d.ca_file);
    EXPECT_EQ(vm.cfg.cert_file, d.cert_file);
    EXPECT_EQ(vm.cfg.key_file, d.key_file);
    EXPECT_EQ(vm.cfg.prefijo, d.prefijo);
    EXPECT_EQ(vm.cfg.timeout_ms, d.timeout_ms);
    EXPECT_EQ(vm.cfg.aviso_intervalo_s, d.aviso_intervalo_s);
    EXPECT_EQ(vm.cfg.reconexion_max_ms, d.reconexion_max_ms);
}
