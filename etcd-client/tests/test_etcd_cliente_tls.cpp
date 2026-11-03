// etcd-client/tests/test_etcd_cliente_tls.cpp — [ETCD-CLIENTE-D316] DEBT-ETCD-HA-TLS-RAFT-001 paso 5.
// Lector único del bloque "etcd" (F1) y transporte HTTPS con lista de direcciones (C1, F3).
// E2 (decisión de Alonso, DAY316): CA desechable generada por el propio test con openssl en un directorio temporal
// que se borra al terminar; nada en el repo ni en /vagrant. Dos servidores httplib::SSLServer con certificado de
// cliente obligatorio hacen de etcd-server.
#include <etcd_client/etcd_client.hpp>
#include <httplib.h>
#include <nlohmann/json.hpp>

#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>

namespace fs = std::filesystem;
using etcd_client::Config;
using etcd_client::EtcdClient;
using etcd_client::leer_bloque_etcd;
using json = nlohmann::json;

static int fallos = 0, total = 0;
#define COMPRUEBA(nombre, cond)                                                     \
    do {                                                                             \
        ++total;                                                                     \
        const bool ok_ = (cond);                                                     \
        std::printf("%s%s\n", ok_ ? "PASA  " : "FALLA ", std::string(nombre).c_str()); \
        std::fflush(stdout);  /* printf: la captura de cout/cerr no se lo come */  \
        if (!ok_) ++fallos;                                                          \
    } while (0)

// ── PKI desechable ───────────────────────────────────────────────────────────
struct Pki {
    fs::path dir;
    bool ok = false;
    Pki() {
        char plantilla[] = "/tmp/argus_test_pki_XXXXXX";
        char* d = mkdtemp(plantilla);
        if (!d) return;
        dir = d;
        const std::string D = dir.string();
        std::ostringstream c;
        c << "set -e; cd '" << D << "'\n"
          << "ca() { openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes -keyout $1.key -out $1.crt"
             " -days 1 -subj \"/CN=$1\" >/dev/null 2>&1; }\n"
          << "hoja() { openssl req -new -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes -keyout $1.key -out $1.csr"
             " -subj \"/O=test/OU=$3/CN=$3\" >/dev/null 2>&1;"
             " printf 'extendedKeyUsage=%s\\n%s\\n' \"$4\" \"$5\" > $1.ext;"
             " openssl x509 -req -in $1.csr -CA $2.crt -CAkey $2.key -CAcreateserial -days 1 -out $1.crt"
             " -extfile $1.ext >/dev/null 2>&1; }\n"
          << "ca ca; ca otra\n"
          << "hoja servidor ca etcd-server serverAuth 'subjectAltName=IP:127.0.0.1'\n"
          << "hoja servidor_otra otra etcd-server serverAuth 'subjectAltName=IP:127.0.0.1'\n"
          << "hoja sniffer ca sniffer clientAuth 'basicConstraints=CA:FALSE'\n";
        std::ofstream(D + "/gen.sh") << c.str();
        ok = std::system(("bash '" + D + "/gen.sh'").c_str()) == 0;
    }
    ~Pki() {
        std::error_code ec;
        if (!dir.empty()) fs::remove_all(dir, ec);
    }
    std::string f(const std::string& n) const { return (dir / n).string(); }
};

// ── etcd-server falso con mTLS ───────────────────────────────────────────────
struct Falso {
    std::unique_ptr<httplib::SSLServer> srv;
    std::thread hilo;
    int puerto = 0;
    std::mutex m;
    std::map<std::string, int> cuentas;   // ruta -> peticiones recibidas
    std::map<std::string, int> estado;    // ruta -> status que responde (defecto 200)
    // [ETCD-CLIENTE-B1-D316] puerto_fijo > 0: escucha en ese puerto (un servidor que "aparece" o "vuelve" donde ya
    // apunta el cliente)
    Falso(const Pki& p, const std::string& cert, const std::string& key, int puerto_fijo = 0) {
        srv = std::make_unique<httplib::SSLServer>(p.f(cert).c_str(), p.f(key).c_str(), p.f("ca.crt").c_str());
        auto h = [this](const httplib::Request& req, httplib::Response& res) {
            int st = 200;
            {
                std::lock_guard<std::mutex> lk(m);
                ++cuentas[req.path];
                if (estado.count(req.path)) st = estado[req.path];
            }
            res.status = st;
            if (req.path.rfind("/secrets/", 0) == 0)
                res.set_content(json{{"key", std::string(64, puerto % 2 ? 'b' : 'a')}}.dump(), "application/json");
            else
                res.set_content(R"({"status":"ok"})", "application/json");
        };
        srv->Get(".*", h);
        srv->Post(".*", h);
        srv->Put(".*", h);  // [ETCD-CLIENTE-B1-D316] PUT /v1/config/<CN>
        if (puerto_fijo > 0) {
            puerto = srv->bind_to_port("127.0.0.1", puerto_fijo) ? puerto_fijo : -1;
        } else {
            puerto = srv->bind_to_any_port("127.0.0.1");
        }
        hilo = std::thread([this] { srv->listen_after_bind(); });
        srv->wait_until_ready();
    }
    ~Falso() {
        srv->stop();
        if (hilo.joinable()) hilo.join();
    }
    void pon_estado(const std::string& r, int st) {
        std::lock_guard<std::mutex> lk(m);
        if (st == 200) estado.erase(r); else estado[r] = st;
    }
    int cuenta(const std::string& r) {
        std::lock_guard<std::mutex> lk(m);
        return cuentas[r];
    }
    std::string url() const { return "https://127.0.0.1:" + std::to_string(puerto); }
};

int puerto_cerrado() {  // un puerto en el que no escucha nadie
    httplib::Server s;
    const int p = s.bind_to_any_port("127.0.0.1");
    s.stop();
    return p;
}

Config base(const Pki& p, const std::vector<std::string>& eps) {
    Config c;
    c.endpoints = eps;
    c.ca_file = p.f("ca.crt");
    c.cert_file = p.f("sniffer.crt");
    c.key_file = p.f("sniffer.key");
    c.connection_timeout_ms = 1000;
    c.retry_attempts = 3;
    c.retry_interval_ms = 100;
    c.component_name = "sniffer";
    c.encryption_enabled = false;
    c.compression_enabled = false;
    c.heartbeat_enabled = false;
    return c;
}

// [ETCD-CLIENTE-B1-D316] Captura std::cout y std::cerr juntos, segura con el hilo mantenedor escribiendo a la vez
struct BufSeguro : std::streambuf {
    std::mutex m;
    std::string s;
    int overflow(int c) override {
        if (c != EOF) { std::lock_guard<std::mutex> lk(m); s.push_back(static_cast<char>(c)); }
        return c;
    }
    std::streamsize xsputn(const char* p, std::streamsize n) override {
        std::lock_guard<std::mutex> lk(m);
        s.append(p, static_cast<size_t>(n));
        return n;
    }
    std::string texto() { std::lock_guard<std::mutex> lk(m); return s; }
};
struct CapturaTodo {
    BufSeguro buf;
    std::streambuf* vo;
    std::streambuf* ve;
    CapturaTodo() : vo(std::cout.rdbuf(&buf)), ve(std::cerr.rdbuf(&buf)) {}
    ~CapturaTodo() { std::cout.rdbuf(vo); std::cerr.rdbuf(ve); }
    std::string str() { return buf.texto(); }
    size_t veces(const std::string& marca) {
        const std::string t = str();
        size_t n = 0;
        for (size_t i = t.find(marca); i != std::string::npos; i = t.find(marca, i + 1)) ++n;
        return n;
    }
};

// Espera hasta que se cumpla la condición o pasen ms
template <class F>
bool espera(F cond, int ms) {
    const auto fin = std::chrono::steady_clock::now() + std::chrono::milliseconds(ms);
    while (std::chrono::steady_clock::now() < fin) {
        if (cond()) return true;
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
    }
    return cond();
}

// Captura std::cerr mientras vive
struct CapturaCerr {
    std::ostringstream buf;
    std::streambuf* viejo;
    CapturaCerr() : viejo(std::cerr.rdbuf(buf.rdbuf())) {}
    ~CapturaCerr() { std::cerr.rdbuf(viejo); }
    std::string str() const { return buf.str(); }
};

int main() {
    Pki p;
    if (!p.ok) {
        std::cerr << "FALLA no se pudo generar la PKI desechable con openssl" << std::endl;
        return 1;
    }

    // ── Lector (F1) ──────────────────────────────────────────────────────────
    json bueno = {{"endpoints", {"https://192.168.100.20:2379", "https://etcd-2.lab:2379"}},
                  {"ca_file", p.f("ca.crt")},
                  {"cert_file", p.f("sniffer.crt")},
                  {"key_file", p.f("sniffer.key")},
                  {"connection_timeout_ms", 2500},
                  {"retry_attempts", 2},
                  {"retry_interval_ms", 300},
                  {"heartbeat_interval_seconds", 15},
                  {"_doc", "texto"}};
    {
        std::ostringstream log;
        auto r = leer_bloque_etcd(bueno, log);
        COMPRUEBA("L1 bloque bueno: 0 fatales, 0 defectos", r.fatales.empty() && r.defectos == 0);
        COMPRUEBA("L1 valores aplicados", r.config.endpoints.size() == 2 && r.config.connection_timeout_ms == 2500 &&
                                              r.config.retry_attempts == 2 && r.config.retry_interval_ms == 300 &&
                                              r.config.heartbeat_interval_seconds == 15);
        COMPRUEBA("L1 cada campo en el log con su origen",
                  log.str().find("[CONFIG] etcd.endpoints=") != std::string::npos &&
                      log.str().find("[CONFIG] etcd.retry_attempts=2 (JSON)") != std::string::npos);
    }
    auto con = [&](const char* k, const json& v) {
        json b = bueno;
        b[k] = v;
        return b;
    };
    auto sin = [&](const char* k) {
        json b = bueno;
        b.erase(k);
        return b;
    };
    {
        std::ostringstream log;
        auto r = leer_bloque_etcd(sin("endpoints"), log);
        COMPRUEBA("L2 sin endpoints: fatal", r.fatales.size() == 1 && log.str().find("[ETCD-CLIENTE-FATAL] etcd.endpoints") != std::string::npos);
    }
    {
        std::ostringstream log;
        auto r = leer_bloque_etcd(con("endpoints", {"http://192.168.100.20:2379"}), log);
        COMPRUEBA("L3 http:// es mal formado (solo TLS)", r.fatales.size() == 1);
    }
    {
        std::ostringstream log;
        auto r = leer_bloque_etcd(con("endpoints", {"https://a:1", "https://a:1"}), log);
        COMPRUEBA("L4 endpoints repetidos: fatal", r.fatales.size() == 1);
    }
    {
        std::ostringstream log;
        json l = json::array();
        for (int i = 1; i <= 8; ++i) l.push_back("https://e" + std::to_string(i) + ":2379");
        auto r = leer_bloque_etcd(con("endpoints", l), log);
        COMPRUEBA("L5 ocho endpoints (máx. 7): fatal", r.fatales.size() == 1);
    }
    {
        std::ostringstream log;
        auto r = leer_bloque_etcd(con("ca_file", "/no/existe/ca.crt"), log);
        COMPRUEBA("L6 ca_file ilegible: fatal", r.fatales.size() == 1 && log.str().find("etcd.ca_file") != std::string::npos);
    }
    {
        std::ostringstream log;
        auto r = leer_bloque_etcd(con("retry_attempts", 0), log);
        COMPRUEBA("L7 retry_attempts fuera de rango: defecto 3 y aviso",
                  r.fatales.empty() && r.config.retry_attempts == 3 && r.defectos == 1 &&
                      log.str().find("[CONFIG-DEFAULT] etcd.retry_attempts=0 fuera de rango") != std::string::npos);
    }
    {
        std::ostringstream log;
        auto r = leer_bloque_etcd(con("enabled", true), log);
        COMPRUEBA("L8 campo obsoleto avisado", r.obsoletos == 1 && log.str().find("[CONFIG-OBSOLETO] etcd.enabled") != std::string::npos);
    }
    {
        std::ostringstream log;
        auto r = leer_bloque_etcd(std::string(), log);
        COMPRUEBA("L9 sin bloque: fatal", r.fatales.size() == 1);
    }

    // ── Transporte (C1, F3) ──────────────────────────────────────────────────
    Falso a(p, "servidor.crt", "servidor.key");
    Falso b(p, "servidor.crt", "servidor.key");
    Falso otra(p, "servidor_otra.crt", "servidor_otra.key");
    const std::string muerto = "https://127.0.0.1:" + std::to_string(puerto_cerrado());
    {
        EtcdClient c(base(p, {a.url()}));
        COMPRUEBA("T1 mTLS: connect y register", c.connect() && c.register_component() && a.cuenta("/register") == 1);
    }
    {
        CapturaCerr cap;
        EtcdClient c(base(p, {muerto, b.url()}));
        const bool ok = c.connect();
        COMPRUEBA("T2 primera dirección muerta: pasa a la segunda", ok && b.cuenta("/health") == 1);
        COMPRUEBA("T2 log [ETCD-CLIENTE-CAMBIO]", cap.str().find("[ETCD-CLIENTE-CAMBIO]") != std::string::npos);
    }
    {
        CapturaCerr cap;
        EtcdClient c(base(p, {muerto}));
        COMPRUEBA("T3 ninguna responde: falla con [ETCD-CLIENTE-NO-DISPONIBLE]",
                  !c.connect() && cap.str().find("[ETCD-CLIENTE-NO-DISPONIBLE]") != std::string::npos);
    }
    {
        CapturaCerr cap;
        EtcdClient c(base(p, {otra.url()}));
        COMPRUEBA("T4 servidor con certificado de otra CA: no conecta", !c.connect() && otra.cuenta("/health") == 0);
    }
    {
        a.estado["/secrets/sniffer"] = 403;
        EtcdClient c(base(p, {a.url(), b.url()}));
        const bool conectado = c.connect();
        const auto k = c.get_hmac_key("/secrets/sniffer");
        COMPRUEBA("T5 un 403 no se reintenta ni cambia de dirección",
                  conectado && !k.has_value() && a.cuenta("/secrets/sniffer") == 1 && b.cuenta("/secrets/sniffer") == 0);
        a.estado.erase("/secrets/sniffer");
    }
    {
        a.estado["/secrets/sniffer"] = 503;
        const int antes_a = a.cuenta("/secrets/sniffer"), antes_b = b.cuenta("/secrets/sniffer");
        EtcdClient c(base(p, {a.url(), b.url()}));
        const bool conectado = c.connect();
        const auto k = c.get_hmac_key("/secrets/sniffer");
        COMPRUEBA("T6 un 503 agota los intentos y pasa a la siguiente dirección",
                  conectado && k.has_value() && k->size() == 32 && a.cuenta("/secrets/sniffer") - antes_a == 3 &&
                      b.cuenta("/secrets/sniffer") - antes_b == 1);
        a.estado.erase("/secrets/sniffer");
    }
    {
        Config c = base(p, {});
        CapturaCerr cap;
        EtcdClient cl(c);
        COMPRUEBA("T7 sin endpoints: connect falla con mensaje", !cl.connect() && cap.str().find("[ETCD-CLIENTE-FATAL]") != std::string::npos);
    }

    // ── [ETCD-CLIENTE-B1-D316] mantenedor (G1-G3) ──────────────────────────────────────────────────────────────
    {
        const std::string ruta_cfg = (p.dir / "componente.json").string();
        std::ofstream(ruta_cfg) << R"({"component": {"name": "sniffer"}, "x": 1})";
        const int pf = puerto_cerrado();
        Config c = base(p, {"https://127.0.0.1:" + std::to_string(pf)});
        c.heartbeat_enabled = true;
        c.heartbeat_interval_seconds = 1;  // el lector exige [5, 300]; aquí la Config va directa para acortar el test
        c.retry_interval_ms = 100;
        CapturaTodo cap;
        auto cl = std::make_unique<EtcdClient>(c);
        const auto t0 = std::chrono::steady_clock::now();
        cl->iniciar(ruta_cfg, "packet-sniffer");
        const auto ms_iniciar = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - t0).count();
        const bool sin = espera([&] { return cap.veces("[ETCD-CLIENTE-SIN-SERVICIO]") >= 2; }, 4000);
        COMPRUEBA("R1 sin etcd-server: iniciar() vuelve enseguida y avisa en cada latido",
                  ms_iniciar < 200 && sin && !cl->is_connected() &&
                      cap.str().find("el componente sigue protegiendo") != std::string::npos);

        auto srv = std::make_unique<Falso>(p, "servidor.crt", "servidor.key", pf);
        const bool reg = espera([&] { return cl->is_connected(); }, 3000);
        espera([&] { return srv->cuenta("/v1/config/sniffer") >= 1; }, 2000);
        COMPRUEBA("R2 el etcd-server aparece: se registra en <= 1 latido y sube la config del JSON de arranque",
                  reg && srv->cuenta("/register") == 1 && srv->cuenta("/v1/config/sniffer") == 1 &&
                      cap.str().find("[ETCD-CLIENTE-REGISTRADO] sniffer") != std::string::npos &&
                      cap.str().find("config subida: " + ruta_cfg) != std::string::npos);
        COMPRUEBA("R2 latidos tras registrarse", espera([&] { return srv->cuenta("/v1/heartbeat/sniffer") >= 2; }, 3500));

        srv->pon_estado("/v1/heartbeat/sniffer", 404);
        const bool rereg = espera([&] { return srv->cuenta("/register") == 2 && srv->cuenta("/v1/config/sniffer") == 2; }, 3500);
        srv->pon_estado("/v1/heartbeat/sniffer", 200);
        COMPRUEBA("R3 404 al latido: vuelve a registrarse y a subir la config",
                  rereg && cap.str().find("[ETCD-CLIENTE-REGISTRO-PERDIDO]") != std::string::npos);

        espera([&] { return cl->is_connected(); }, 3000);
        srv.reset();  // el etcd-server cae
        const size_t sin_antes = cap.veces("[ETCD-CLIENTE-SIN-SERVICIO]");
        const bool cae = espera([&] { return !cl->is_connected() && cap.veces("[ETCD-CLIENTE-SIN-SERVICIO]") > sin_antes; }, 4000);
        srv = std::make_unique<Falso>(p, "servidor.crt", "servidor.key", pf);  // vuelve con el registro conservado
        const bool vuelve = espera([&] { return cl->is_connected(); }, 4000);
        COMPRUEBA("R4 cae y vuelve: SIN-SERVICIO y luego REANUDADO, sin nuevo /register",
                  cae && vuelve && srv->cuenta("/register") == 0 && srv->cuenta("/v1/heartbeat/sniffer") >= 1 &&
                      cap.str().find("[ETCD-CLIENTE-REANUDADO] sniffer") != std::string::npos);

        // Parada: con un latido de 1 s; la espera es interrumpible y da de baja una vez
        const auto t1 = std::chrono::steady_clock::now();
        cl.reset();
        const auto ms_parada = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - t1).count();
        COMPRUEBA("R5 parada inmediata y baja una vez",
                  ms_parada < 1000 && srv->cuenta("/unregister") == 1 &&
                      cap.str().find("[ETCD-CLIENTE-BAJA] sniffer: dado de baja") != std::string::npos);
    }
    {
        Config c = base(p, {a.url()});
        EtcdClient cl(c);  // sin connect() ni registro
        const auto k = cl.get_hmac_key("/secrets/sniffer");
        COMPRUEBA("R6 get_hmac_key sin connect() ni registro", k.has_value() && k->size() == 32);
    }
    {
        Config c = base(p, {a.url()});
        c.heartbeat_enabled = true;
        c.heartbeat_interval_seconds = 30;
        const int antes = a.cuenta("/v1/heartbeat/sniffer");
        auto cl = std::make_unique<EtcdClient>(c);
        const bool r = cl->register_component();
        const bool latio = espera([&] { return a.cuenta("/v1/heartbeat/sniffer") - antes >= 1; }, 2000);
        const auto t1 = std::chrono::steady_clock::now();
        cl.reset();
        const auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - t1).count();
        COMPRUEBA("R7 register_component(): primer latido sin esperar los 30 s y parada < 1 s",
                  r && latio && ms < 1000);
    }
    {
        CapturaTodo cap;
        const auto t1 = std::chrono::steady_clock::now();
        { etcd_client::AvisoBloqueFatal aviso("sniffer", 2, 30); }
        const auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - t1).count();
        COMPRUEBA("R8 AvisoBloqueFatal: avisa al momento y para enseguida",
                  ms < 1000 && cap.str().find("[ETCD-CLIENTE-FATAL] sniffer: bloque etcd con 2 campos fatales") != std::string::npos);
    }

    std::cout << "test_etcd_cliente_tls: " << (total - fallos) << "/" << total << std::endl;
    return fallos == 0 ? 0 : 1;
}
