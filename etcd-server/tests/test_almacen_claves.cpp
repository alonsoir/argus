// etcd-server/tests/test_almacen_claves.cpp — [ETCD-CLAVES-D314]
// Bloque almacen_claves de etcd-server.json (fatales sin defecto en modo vault, rangos, JSON del repo) y ventana de dos
// del SecretsManager sobre MemoriaSecretStore con reloj inyectado (sin red): crear, reinicio con la misma huella,
// rotar, caducar, enfriamiento, almacén caído con y sin copia (nunca se genera una clave sin guardar), CAS entre dos
// instancias (creación y rotación), huella repetida, entrada incoherente, avisos periódicos, y que el log nunca
// lleve una clave.
#include "etcd_server/secrets_manager.hpp"
#include <gtest/gtest.h>
#include <fstream>
#include <regex>
#include <sstream>
#include <thread>

using argus::claves::Estado;
using argus::claves::ISecretStore;
using argus::claves::MemoriaSecretStore;
using etcd_server::ClaveHMAC;
using etcd_server::ResultadoClaves;
using etcd_server::SecretsConfig;
using etcd_server::SecretsManager;
using json = nlohmann::json;

namespace {

json leer_json(const std::string& f) {
    std::ifstream in(std::string(ETCD_SERVER_CONFIG_DIR) + "/" + f);
    return json::parse(in);
}

// Varios SecretsManager (reinicio, o dos instancias del PR2) sobre el mismo almacén
class Compartido : public ISecretStore {
public:
    explicit Compartido(std::shared_ptr<MemoriaSecretStore> s) : s_(std::move(s)) {}
    Estado leer(const std::string& r, json& d, int& v) override { return s_->leer(r, d, v); }
    Estado escribir(const std::string& r, const json& d, int cas, int& v) override { return s_->escribir(r, d, cas, v); }
    bool disponible() const override { return s_->disponible(); }
    bool sondear() override { return s_->sondear(); }
    std::string descripcion() const override { return s_->descripcion(); }
    std::string ultimo_error() const override { return s_->ultimo_error(); }

private:
    std::shared_ptr<MemoriaSecretStore> s_;
};

struct Banco {
    std::time_t t = 1'800'000'000;
    std::ostringstream log;
    std::shared_ptr<MemoriaSecretStore> s = std::make_shared<MemoriaSecretStore>();
    std::unique_ptr<SecretsManager> nuevo(bool memoria = false, SecretsManager::Generador g = {}) {
        SecretsConfig c;  // 300 / 32 / 300
        return std::make_unique<SecretsManager>(c, std::make_unique<Compartido>(s), memoria, 60, 5,
                                                [this] { return t; }, log, std::move(g));
    }
};

ClaveHMAC activa(SecretsManager& m, const std::string& cn, ResultadoClaves esperado = ResultadoClaves::Ok,
                 bool* copia_out = nullptr) {
    ClaveHMAC k;
    bool copia = false;
    EXPECT_EQ(m.activa(cn, k, copia), esperado);
    if (copia_out) *copia_out = copia;
    return k;
}

std::string hex_de(char c) { return std::string(64, c); }

}  // namespace

// ── configuración ────────────────────────────────────────────────────────────
TEST(AlmacenClavesConfig, VaultSinDireccionesEsFatal) {
    std::ostringstream av, in;
    auto r = argus::etcdcfg::parse_almacen_claves_config(json::object(), av, in);
    EXPECT_EQ(r.cfg.modo, "vault");                 // un modo ausente nunca rebaja a memoria
    EXPECT_EQ(r.fatales.size(), 4u) << av.str();    // vault_addrs, ca_file, cert_file, key_file
    EXPECT_NE(av.str().find("[ETCD-VAULT-FATAL] almacen_claves.vault_addrs ausente"), std::string::npos) << av.str();
    EXPECT_NE(in.str().find("almacen_claves.vault_addrs=[\"https://127.0.0.1:8200\"] (FATAL: ausente)"),
              std::string::npos)
        << in.str();
}

TEST(AlmacenClavesConfig, DireccionesMalFormadas) {
    for (const char* malo : {R"("https://127.0.0.1:8200")", R"([])", R"(["http://127.0.0.1:8200"])",
                             R"(["https://vault:8200"])", R"(["https://127.0.0.1:99999"])",
                             R"(["https://127.0.0.1:8200", "https://127.0.0.1:8200"])",
                             R"(["https://10.0.0.1:1","https://10.0.0.2:1","https://10.0.0.3:1","https://10.0.0.4:1",
                                 "https://10.0.0.5:1","https://10.0.0.6:1","https://10.0.0.7:1","https://10.0.0.8:1"])"}) {
        std::ostringstream av, in;
        json j = leer_json("etcd-server.etcd-vm.json");
        j["almacen_claves"]["vault_addrs"] = json::parse(malo);
        auto r = argus::etcdcfg::parse_almacen_claves_config(j, av, in);
        ASSERT_EQ(r.fatales.size(), 1u) << malo << "\n" << av.str();
        EXPECT_NE(r.fatales[0].find("vault_addrs mal formado"), std::string::npos) << r.fatales[0];
    }
}

TEST(AlmacenClavesConfig, ModoMemoriaNoEsFatal) {
    std::ostringstream av, in;
    auto r = argus::etcdcfg::parse_almacen_claves_config(json{{"almacen_claves", {{"modo", "memoria"}}}}, av, in);
    EXPECT_EQ(r.cfg.modo, "memoria");
    EXPECT_TRUE(r.fatales.empty());
    EXPECT_NE(av.str().find("no se usa en modo memoria"), std::string::npos) << av.str();
}

TEST(AlmacenClavesConfig, ModoMalEscritoVaAVault) {
    std::ostringstream av, in;
    json j = leer_json("etcd-server.json");
    j["almacen_claves"]["modo"] = "Memoria";
    auto r = argus::etcdcfg::parse_almacen_claves_config(j, av, in);
    EXPECT_EQ(r.cfg.modo, "vault");
    EXPECT_EQ(r.defectos, 1);
    EXPECT_TRUE(r.fatales.empty());  // el JSON del defender trae las direcciones
}

TEST(AlmacenClavesConfig, EnterosRangosYRegla) {
    std::ostringstream av, in;
    json j = leer_json("etcd-server.etcd-vm.json");
    j["almacen_claves"]["reintentos_por_direccion"] = 0;
    j["almacen_claves"]["timeout_ms"] = "2000";
    j["almacen_claves"]["espera_inicial_ms"] = 5000;
    j["almacen_claves"]["espera_max_ms"] = 1000;  // < espera_inicial_ms
    auto r = argus::etcdcfg::parse_almacen_claves_config(j, av, in);
    EXPECT_TRUE(r.fatales.empty());
    EXPECT_EQ(r.cfg.reintentos_por_direccion, 3);
    EXPECT_EQ(r.cfg.timeout_ms, 2000);
    EXPECT_EQ(r.cfg.espera_inicial_ms, 5000);
    EXPECT_EQ(r.cfg.espera_max_ms, 5000);
    EXPECT_EQ(r.defectos, 3) << av.str();
    EXPECT_NE(av.str().find("entero en [1, 10]"), std::string::npos) << av.str();
}

TEST(AlmacenClavesConfig, JsonDelRepo) {
    std::ostringstream a1, i1, a2, i2;
    auto def = argus::etcdcfg::parse_almacen_claves_config(leer_json("etcd-server.json"), a1, i1);
    EXPECT_EQ(def.defectos, 0) << a1.str();
    EXPECT_TRUE(def.fatales.empty());
    EXPECT_EQ(def.cfg.modo, "memoria");  // transición del defender, hasta el paso 6
    auto vm = argus::etcdcfg::parse_almacen_claves_config(leer_json("etcd-server.etcd-vm.json"), a2, i2);
    EXPECT_EQ(vm.defectos, 0) << a2.str();
    EXPECT_TRUE(vm.fatales.empty());
    const argus::etcdcfg::AlmacenClavesConfig d{};
    EXPECT_EQ(vm.cfg.modo, d.modo);
    EXPECT_EQ(vm.cfg.vault_addrs, d.vault_addrs);
    EXPECT_EQ(vm.cfg.ca_file, d.ca_file);
    EXPECT_EQ(vm.cfg.cert_file, d.cert_file);
    EXPECT_EQ(vm.cfg.key_file, d.key_file);
    EXPECT_EQ(vm.cfg.montaje, d.montaje);
    EXPECT_EQ(vm.cfg.rol_login, d.rol_login);
    EXPECT_EQ(vm.cfg.timeout_ms, d.timeout_ms);
    EXPECT_EQ(vm.cfg.reintentos_por_direccion, d.reintentos_por_direccion);
    EXPECT_EQ(vm.cfg.espera_inicial_ms, d.espera_inicial_ms);
    EXPECT_EQ(vm.cfg.espera_max_ms, d.espera_max_ms);
    EXPECT_EQ(vm.cfg.sondeo_s, d.sondeo_s);
    EXPECT_EQ(vm.cfg.aviso_intervalo_s, d.aviso_intervalo_s);
}

// ── huella y fechas ──────────────────────────────────────────────────────────
TEST(Huella, IgualQueElMlDetector) {
    // SHA-256 de 32 bytes a cero = 66687aad f862bd77...: huella = 4 primeros bytes
    EXPECT_EQ(SecretsManager::huella(hex_de('0')), "66687aad");
    EXPECT_EQ(SecretsManager::huella("abc"), "invalida");
    EXPECT_EQ(SecretsManager::huella("zz"), "invalida");
}

TEST(Fechas, IsoEnUtc) {
    std::time_t t = 0;
    ASSERT_TRUE(SecretsManager::desde_iso("2026-11-01T08:00:00Z", t));
    EXPECT_EQ(t, 1793520000);
    EXPECT_EQ(SecretsManager::iso(t), "2026-11-01T08:00:00Z");
    EXPECT_FALSE(SecretsManager::desde_iso("2026-11-01 08:00:00", t));
}

// ── ventana de dos ───────────────────────────────────────────────────────────
TEST(Ventana, CreaUnaVezYSobreviveAlReinicio) {
    Banco b;
    std::string huella;
    {
        auto m = b.nuevo();
        const auto k1 = activa(*m, "ml-detector");
        const auto k2 = activa(*m, "ml-detector");
        EXPECT_EQ(k1.hex, k2.hex);
        EXPECT_EQ(k1.huella, SecretsManager::huella(k1.hex));
        huella = k1.huella;
        EXPECT_EQ(b.s->cuantos(), 2u);  // la clave y la ventana
    }
    auto m2 = b.nuevo();  // "reinicio del etcd-server": misma clave
    EXPECT_EQ(activa(*m2, "ml-detector").huella, huella);
    EXPECT_EQ(b.s->cuantos(), 2u);
    json d;
    int v = 0;
    ASSERT_EQ(b.s->leer("ml-detector/" + huella, d, v), Estado::Ok);
    EXPECT_EQ(v, 1);
    ASSERT_EQ(b.s->leer("ml-detector/ventana", d, v), Estado::Ok);
    EXPECT_EQ(d["activa"], huella);
    EXPECT_EQ(d["anterior"], "");
}

TEST(Ventana, DosPeticionesALaVezUnaSolaClave) {  // la carrera de DAY311
    Banco b;
    auto m = b.nuevo();
    std::string h1, h2;
    std::thread a([&] { h1 = activa(*m, "sniffer").huella; });
    std::thread c([&] { h2 = activa(*m, "sniffer").huella; });
    a.join();
    c.join();
    EXPECT_EQ(h1, h2);
    EXPECT_EQ(b.s->cuantos(), 2u);
}

TEST(Ventana, RotarCaducarYEnfriamiento) {
    Banco b;
    auto m = b.nuevo();
    const auto k1 = activa(*m, "sniffer");
    ClaveHMAC k2;
    int reintentar = 0;
    b.t += 100;
    EXPECT_EQ(m->rotar("sniffer", false, k2, reintentar), ResultadoClaves::Enfriamiento);
    EXPECT_EQ(reintentar, 200);
    b.t += 200;
    ASSERT_EQ(m->rotar("sniffer", false, k2, reintentar), ResultadoClaves::Ok);
    EXPECT_NE(k2.hex, k1.hex);
    EXPECT_EQ(activa(*m, "sniffer").hex, k2.hex);
    std::vector<ClaveHMAC> v;
    bool copia = true;
    ASSERT_EQ(m->validas("sniffer", v, copia), ResultadoClaves::Ok);
    EXPECT_FALSE(copia);
    ASSERT_EQ(v.size(), 2u);
    EXPECT_TRUE(v[0].activa);
    EXPECT_EQ(v[1].hex, k1.hex);
    EXPECT_EQ(v[1].expira, b.t + 300);
    b.t += 299;
    ASSERT_EQ(m->validas("sniffer", v, copia), ResultadoClaves::Ok);
    EXPECT_EQ(v.size(), 2u);
    b.t += 1;
    ASSERT_EQ(m->validas("sniffer", v, copia), ResultadoClaves::Ok);
    EXPECT_EQ(v.size(), 1u);
    // la clave anterior sigue en el almacén (nunca se borra)
    EXPECT_EQ(b.s->cuantos(), 3u);
    // force salta el enfriamiento
    ClaveHMAC k3;
    EXPECT_EQ(m->rotar("sniffer", true, k3, reintentar), ResultadoClaves::Ok);
    EXPECT_NE(b.log.str().find("[ETCD-CLAVES-FORZADA] sniffer"), std::string::npos);
}

TEST(Ventana, ValidasSinClaveTodaviaEsVacio) {
    Banco b;
    auto m = b.nuevo();
    std::vector<ClaveHMAC> v{ClaveHMAC{}};
    bool copia = true;
    EXPECT_EQ(m->validas("ml-detector", v, copia), ResultadoClaves::Ok);
    EXPECT_TRUE(v.empty());
    EXPECT_EQ(b.s->cuantos(), 0u);  // /secrets/valid no crea
}

TEST(Ventana, NombreInvalido) {
    Banco b;
    auto m = b.nuevo();
    activa(*m, "../x", ResultadoClaves::NombreInvalido);
    activa(*m, "Sniffer", ResultadoClaves::NombreInvalido);
    EXPECT_EQ(b.s->cuantos(), 0u);
}

// ── almacén caído ────────────────────────────────────────────────────────────
TEST(Caido, ConCopiaSirveSinCopiaNoGenera) {
    Banco b;
    auto m = b.nuevo();
    const auto k = activa(*m, "ml-detector");
    b.s->simular_caido(true);
    bool copia = false;
    EXPECT_EQ(activa(*m, "ml-detector", ResultadoClaves::Ok, &copia).hex, k.hex);
    EXPECT_TRUE(copia);
    EXPECT_NE(b.log.str().find("[ETCD-VAULT-NO-DISPONIBLE]"), std::string::npos);
    // rotar exige el almacén
    ClaveHMAC n;
    int r = 0;
    EXPECT_EQ(m->rotar("ml-detector", true, n, r), ResultadoClaves::NoDisponible);
    // un CN sin copia: 503 y no se genera nada
    activa(*m, "firewall-acl-agent", ResultadoClaves::NoDisponible);
    // reinicio con el almacén caído: sin copia, 503
    auto m2 = b.nuevo();
    activa(*m2, "ml-detector", ResultadoClaves::NoDisponible);
    b.s->simular_caido(false);
    EXPECT_EQ(b.s->cuantos(), 2u);  // solo lo de antes de caer
    EXPECT_EQ(activa(*m2, "ml-detector").hex, k.hex);
    EXPECT_NE(b.log.str().find("[ETCD-VAULT-RECUPERADO]"), std::string::npos);
}

// Medido DAY314 en el banco (2ª pasada de d314_claves_medir.sh, C10): tras reiniciar, la copia tenía la ventana y la
// activa pero no la anterior, y con Vault caído /secrets/valid daba 503
TEST(Caido, LaCopiaIncluyeLaAnteriorTrasReiniciar) {
    Banco b;
    {
        auto m = b.nuevo();
        activa(*m, "ml-detector");
        ClaveHMAC n;
        int r = 0;
        ASSERT_EQ(m->rotar("ml-detector", true, n, r), ResultadoClaves::Ok);
    }
    auto m2 = b.nuevo();  // reinicio
    activa(*m2, "ml-detector");  // la copia se llena al pedir la activa
    b.s->simular_caido(true);
    std::vector<ClaveHMAC> v;
    bool copia = false;
    ASSERT_EQ(m2->validas("ml-detector", v, copia), ResultadoClaves::Ok);
    EXPECT_TRUE(copia);
    EXPECT_EQ(v.size(), 2u);
}

TEST(Caido, AvisosPeriodicosYSondeo) {
    Banco b;
    auto m = b.nuevo();
    activa(*m, "sniffer");
    b.s->simular_caido(true);
    activa(*m, "sniffer");  // primera línea
    auto cuenta = [&](const std::string& p) {
        const std::string l = b.log.str();
        size_t n = 0;
        for (size_t i = l.find(p); i != std::string::npos; i = l.find(p, i + 1)) ++n;
        return n;
    };
    EXPECT_EQ(cuenta("[ETCD-VAULT-NO-DISPONIBLE]"), 1u);
    b.t += 30;
    m->revisar();
    EXPECT_EQ(cuenta("[ETCD-VAULT-NO-DISPONIBLE]"), 1u);
    b.t += 30;
    m->revisar();
    EXPECT_EQ(cuenta("[ETCD-VAULT-NO-DISPONIBLE] sigue sin responder desde hace 60 s"), 1u);
    b.s->simular_caido(false);
    b.t += 5;
    m->revisar();  // el sondeo lo encuentra
    EXPECT_EQ(cuenta("[ETCD-VAULT-RECUPERADO] tras 65 s"), 1u) << b.log.str();
    EXPECT_TRUE(m->almacen_disponible());
}

TEST(Caido, AvisoDeModoMemoria) {
    Banco b;
    auto m = b.nuevo(/*memoria=*/true);
    m->revisar();
    b.t += 59;
    m->revisar();
    b.t += 1;
    m->revisar();
    const std::string l = b.log.str();
    size_t n = 0;
    for (size_t i = l.find("[ETCD-CLAVES-MEMORIA]"); i != std::string::npos; i = l.find("[ETCD-CLAVES-MEMORIA]", i + 1))
        ++n;
    EXPECT_EQ(n, 2u);
}

// ── dos instancias (PR2): el CAS decide ──────────────────────────────────────
TEST(Cas, OtraInstanciaCreaAntes) {
    Banco b;
    auto m = b.nuevo();
    const std::string suya = hex_de('1');
    const std::string hs = SecretsManager::huella(suya);
    bool una = true;
    b.s->antes_de_escribir = [&](const std::string& ruta) {
        if (una && ruta == "ml-detector/ventana") {  // la otra instancia escribe su clave y su ventana justo antes
            una = false;
            b.s->poner("ml-detector/" + hs, json{{"clave", suya}, {"creada", "2027-01-15T08:00:00Z"}});
            b.s->poner("ml-detector/ventana", json{{"activa", hs}, {"anterior", ""}, {"expira_anterior", ""}});
        }
    };
    EXPECT_EQ(activa(*m, "ml-detector").hex, suya);
    EXPECT_NE(b.log.str().find("[ETCD-CLAVES-CONCURRENTE] ml-detector"), std::string::npos);
    b.s->antes_de_escribir = nullptr;
    EXPECT_EQ(activa(*m, "ml-detector").hex, suya);
}

TEST(Cas, OtraInstanciaRotaALaVez) {
    Banco b;
    auto m = b.nuevo();
    const auto k1 = activa(*m, "sniffer");
    b.t += 400;
    b.s->antes_de_escribir = [&](const std::string& ruta) {
        if (ruta == "sniffer/ventana") {  // la otra cambia la ventana (sube su versión) antes que esta
            json d;
            int v = 0;
            b.s->leer("sniffer/ventana", d, v);
            b.s->poner("sniffer/ventana", d);
        }
    };
    ClaveHMAC n;
    int r = 0;
    EXPECT_EQ(m->rotar("sniffer", false, n, r), ResultadoClaves::Conflicto);
    b.s->antes_de_escribir = nullptr;
    EXPECT_EQ(activa(*m, "sniffer").hex, k1.hex);  // la rotación no se aplicó
}

TEST(Cas, HuellaRepetidaGeneraOtra) {
    Banco b;
    int n = 0;
    auto m = b.nuevo(false, [&](size_t) { return hex_de(n++ < 2 ? '2' : '3'); });
    // ya hay una clave con la huella de '2...' (de otro CN no: del mismo, p. ej. un resto)
    b.s->poner("sniffer/" + SecretsManager::huella(hex_de('2')),
               json{{"clave", hex_de('2')}, {"creada", "2027-01-15T08:00:00Z"}});
    EXPECT_EQ(activa(*m, "sniffer").hex, hex_de('3'));
    EXPECT_NE(b.log.str().find("[ETCD-CLAVES-HUELLA-REPETIDA]"), std::string::npos);
}

TEST(Cas, EntradaIncoherenteNoSeSirve) {
    Banco b;
    auto m = b.nuevo();
    b.s->poner("sniffer/aaaaaaaa", json{{"clave", hex_de('4')}, {"creada", "2027-01-15T08:00:00Z"}});
    b.s->poner("sniffer/ventana", json{{"activa", "aaaaaaaa"}, {"anterior", ""}, {"expira_anterior", ""}});
    activa(*m, "sniffer", ResultadoClaves::NoDisponible);
    EXPECT_NE(b.log.str().find("[ETCD-CLAVES-INCOHERENTE] sniffer/aaaaaaaa"), std::string::npos);
}

TEST(Log, NuncaLlevaUnaClave) {
    Banco b;
    auto m = b.nuevo(true);
    activa(*m, "ml-detector");
    b.t += 400;
    ClaveHMAC n;
    int r = 0;
    m->rotar("ml-detector", false, n, r);
    std::vector<ClaveHMAC> v;
    bool c = false;
    m->validas("ml-detector", v, c);
    m->revisar();
    EXPECT_FALSE(std::regex_search(b.log.str(), std::regex("[0-9a-f]{64}"))) << b.log.str();
    EXPECT_NE(b.log.str().find("[ETCD-CLAVES-ROTADA] ml-detector"), std::string::npos);
}
