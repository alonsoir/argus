// etcd-server/tests/test_etcd_server_authz.cpp — [ETCD-AUTHZ-D313]
// Bloques tls y authz de etcd-server.json: lectura con defectos, tabla y plantillas, decisión (denegar por defecto),
// identidad (CN, OU) de certificados X.509 creados aquí mismo con OpenSSL, casos ambiguos, y que los defectos del código
// sean los que traen los JSON del repo. Sin red.
#include "etcd_server/etcd_server_authz.hpp"
#include <gtest/gtest.h>
#include <openssl/evp.h>
#include <openssl/x509.h>
#include <fstream>
#include <sstream>
#include <memory>
#include <vector>

using namespace argus::etcdauthz;
using argus::etcdcfg::parse_tls_config;
using json = nlohmann::json;

namespace {
struct Salida { std::ostringstream aviso, info; };

std::vector<Regla> tabla_defecto() {
    Salida o;
    return parse_authz(json::object(), o.aviso, o.info).reglas;
}
Identidad id(const std::string& cn, const std::string& ou) {
    Identidad i;
    i.valida = true;
    i.cn = cn;
    i.ou = ou;
    return i;
}
bool permite(const std::vector<Regla>& t, const std::string& m, const std::string& r, const Identidad& i) {
    return decidir(t, m, r, i).permitido;
}

// Certificado autofirmado con el sujeto dado: lista de (campo, valor), p. ej. {{"OU","sniffer"},{"CN","sniffer"}}.
struct X509Del { void operator()(X509* x) const { X509_free(x); } };
std::unique_ptr<X509, X509Del> cert_con(const std::vector<std::pair<std::string, std::string>>& sujeto) {
    EVP_PKEY* k = EVP_EC_gen("P-256");
    X509* x = X509_new();
    ASN1_INTEGER_set(X509_get_serialNumber(x), 1);
    X509_gmtime_adj(X509_getm_notBefore(x), 0);
    X509_gmtime_adj(X509_getm_notAfter(x), 3600);
    X509_set_pubkey(x, k);
    X509_NAME* n = X509_get_subject_name(x);
    X509_NAME_add_entry_by_txt(n, "O", MBSTRING_ASC, reinterpret_cast<const unsigned char*>("aRGus-lab"), -1, -1, 0);
    for (const auto& [campo, valor] : sujeto) {
        X509_NAME_add_entry_by_txt(n, campo.c_str(), MBSTRING_UTF8,
                                   reinterpret_cast<const unsigned char*>(valor.c_str()), -1, -1, 0);
    }
    X509_set_issuer_name(x, n);
    X509_sign(x, k, EVP_sha256());
    EVP_PKEY_free(k);
    return std::unique_ptr<X509, X509Del>(x);
}

json leer(const std::string& nombre) {
    std::ifstream f(std::string(ETCD_SERVER_CONFIG_DIR) + "/" + nombre);
    EXPECT_TRUE(f.good()) << nombre;
    return json::parse(f);
}
std::string texto_tabla(const std::vector<Regla>& t) {
    std::string s;
    for (const auto& r : t) {
        s += r.metodo + " " + r.ruta + " ->";
        for (const auto& p : r.permitir) s += " " + p.texto();
        s += "\n";
    }
    return s;
}
}  // namespace

// ── tls ──────────────────────────────────────────────────────────────────────

TEST(EtcdServerTls, AusenteVaAMtlsConDefectos) {
    Salida o;
    auto r = parse_tls_config(json::object(), o.aviso, o.info);
    EXPECT_EQ(r.cfg.modo, "mtls");
    EXPECT_EQ(r.cfg.ca_file, "/etc/argus-pki/ca.crt");
    EXPECT_EQ(r.cfg.cert_file, "/etc/argus-pki/etcd-server.crt");
    EXPECT_EQ(r.cfg.key_file, "/etc/argus-pki/etcd-server.key");
    EXPECT_EQ(r.cfg.aviso_http_intervalo_s, 60);
    EXPECT_EQ(r.defectos, 5);
    EXPECT_NE(o.info.str().find("tls.modo=mtls (DEFECTO: ausente)"), std::string::npos) << o.info.str();
}

TEST(EtcdServerTls, ErrataNuncaRebajaAHttp) {
    for (const char* malo : {R"("HTTP")", R"("htp")", R"("")", R"(true)", R"(1)", R"(null)"}) {
        Salida o;
        json root = json::parse(std::string(R"({"tls": {"modo": )") + malo + "}}");
        auto r = parse_tls_config(root, o.aviso, o.info);
        EXPECT_EQ(r.cfg.modo, "mtls") << malo;
        EXPECT_NE(o.aviso.str().find("una errata nunca rebaja a HTTP"), std::string::npos) << malo;
    }
}

TEST(EtcdServerTls, HttpExplicitoSeRespeta) {
    Salida o;
    json root = json::parse(R"({"tls": {"modo": "http", "ca_file": "/a/ca.crt", "cert_file": "/a/s.crt",
                                        "key_file": "/a/s.key", "aviso_http_intervalo_s": 10}})");
    auto r = parse_tls_config(root, o.aviso, o.info);
    EXPECT_EQ(r.defectos, 0) << o.aviso.str();
    EXPECT_EQ(r.cfg.modo, "http");
    EXPECT_EQ(r.cfg.ca_file, "/a/ca.crt");
    EXPECT_EQ(r.cfg.aviso_http_intervalo_s, 10);
}

TEST(EtcdServerTls, RutasYAvisoMalFormados) {
    Salida o;
    json root = json::parse(R"({"tls": {"modo": "mtls", "ca_file": "relativa.crt", "cert_file": 3,
                                        "key_file": "/con\nsalto", "aviso_http_intervalo_s": 9}})");
    auto r = parse_tls_config(root, o.aviso, o.info);
    EXPECT_EQ(r.defectos, 4);
    EXPECT_EQ(r.cfg.ca_file, "/etc/argus-pki/ca.crt");
    EXPECT_EQ(r.cfg.cert_file, "/etc/argus-pki/etcd-server.crt");
    EXPECT_EQ(r.cfg.key_file, "/etc/argus-pki/etcd-server.key");
    EXPECT_EQ(r.cfg.aviso_http_intervalo_s, 60);
}

TEST(EtcdServerTls, TlsNoObjeto) {
    Salida o;
    auto r = parse_tls_config(json::parse(R"({"tls": "mtls"})"), o.aviso, o.info);
    EXPECT_EQ(r.cfg.modo, "mtls");
    EXPECT_EQ(r.defectos, 5);
    EXPECT_NE(o.aviso.str().find("tls no es un objeto"), std::string::npos);
}

// ── tabla authz ──────────────────────────────────────────────────────────────

TEST(EtcdServerAuthz, TablaPorDefectoValidaYAvisada) {
    Salida o;
    auto r = parse_authz(json::object(), o.aviso, o.info);
    EXPECT_EQ(r.defectos, 1);
    EXPECT_EQ(r.reglas.size(), 15u);
    EXPECT_NE(o.aviso.str().find("authz ausente"), std::string::npos);
    EXPECT_NE(o.info.str().find("[ETCD-AUTHZ] regla 1/15: GET /health permitir=cualquiera (DEFECTO: ausente)"),
              std::string::npos) << o.info.str();
}

TEST(EtcdServerAuthz, ReglaMalFormadaInvalidaLaTablaEntera) {
    const char* malas[] = {
        R"({"metodo": "PATCH", "ruta": "/x", "permitir": ["cualquiera"]})",
        R"({"metodo": "GET", "ruta": "x", "permitir": ["cualquiera"]})",
        R"({"metodo": "GET", "ruta": "/a/{c}/{c}", "permitir": ["cualquiera"]})",
        R"({"metodo": "GET", "ruta": "/health", "permitir": ["propio"]})",
        R"({"metodo": "GET", "ruta": "/health", "permitir": []})",
        R"({"metodo": "GET", "ruta": "/health", "permitir": ["ou:Admin"]})",
        R"({"metodo": "GET", "ruta": "/health", "permitir": ["todos"]})",
        R"({"metodo": "GET", "ruta": "/a//b", "permitir": ["cualquiera"]})",
        R"J({"metodo": "GET", "ruta": "/a/(.*)", "permitir": ["cualquiera"]})J",
    };
    for (const char* mala : malas) {
        Salida o;
        json root = json::parse(std::string(R"({"authz": {"reglas": [
            {"metodo": "GET", "ruta": "/health", "permitir": ["ou:admin"]}, )") + mala + "]}}");
        auto r = parse_authz(root, o.aviso, o.info);
        EXPECT_EQ(r.defectos, 1) << mala;
        EXPECT_EQ(r.reglas.size(), 15u) << mala;  // la tabla por defecto ENTERA, no la buena a medias
        EXPECT_NE(o.aviso.str().find("authz.reglas[1]"), std::string::npos) << mala << "\n" << o.aviso.str();
    }
}

TEST(EtcdServerAuthz, DenegarPorDefecto) {
    const auto t = tabla_defecto();
    const auto adm = id("admin", "admin");
    EXPECT_FALSE(permite(t, "GET", "/seed", adm));           // ruta borrada: sin regla
    EXPECT_FALSE(permite(t, "GET", "/secrets/keys", adm));   // ídem (casaría /secrets/{c} con c=keys: CN != keys)
    EXPECT_FALSE(permite(t, "DELETE", "/health", adm));
    EXPECT_FALSE(permite(t, "OPTIONS", "/health", adm));
    EXPECT_EQ(decidir(t, "GET", "/nada", adm).motivo, "ninguna regla casa (denegar por defecto)");
}

TEST(EtcdServerAuthz, PropioSoloSuCN) {
    const auto t = tabla_defecto();
    const auto sn = id("sniffer", "sniffer");
    EXPECT_TRUE(permite(t, "GET", "/secrets/sniffer", sn));
    EXPECT_FALSE(permite(t, "GET", "/secrets/ml-detector", sn));
    EXPECT_TRUE(permite(t, "POST", "/v1/heartbeat/sniffer", sn));
    EXPECT_FALSE(permite(t, "POST", "/v1/heartbeat/firewall-acl-agent", sn));
    EXPECT_TRUE(permite(t, "PUT", "/v1/config/sniffer", sn));
    EXPECT_FALSE(permite(t, "POST", "/secrets/rotate/sniffer", sn));  // rotar: solo admin
    EXPECT_FALSE(permite(t, "GET", "/components", sn));
    EXPECT_TRUE(permite(t, "GET", "/health", sn));
    EXPECT_TRUE(permite(t, "HEAD", "/health", sn));                   // HEAD = GET
    EXPECT_TRUE(permite(t, "POST", "/register", sn));                 // nombre == CN: en 4b.3
}

TEST(EtcdServerAuthz, InstanciaYRol) {
    // HA (B3): réplica sniffer-2 del rol sniffer: su clave es la suya (CN), no la de otra réplica
    const auto t = tabla_defecto();
    const auto s2 = id("sniffer-2", "sniffer");
    EXPECT_TRUE(permite(t, "GET", "/secrets/sniffer-2", s2));
    EXPECT_FALSE(permite(t, "GET", "/secrets/sniffer", s2));
    // el converter lee las claves válidas de cualquiera, pero no la activa ni rota
    const auto cv = id("bronze-to-gold-converter", "bronze-to-gold-converter");
    EXPECT_TRUE(permite(t, "GET", "/secrets/valid/ml-detector", cv));
    EXPECT_FALSE(permite(t, "GET", "/secrets/ml-detector", cv));
    EXPECT_FALSE(permite(t, "POST", "/secrets/rotate/ml-detector", cv));
    // admin: lo suyo, y no las claves de otros
    const auto adm = id("admin", "admin");
    EXPECT_TRUE(permite(t, "POST", "/secrets/rotate/ml-detector", adm));
    EXPECT_TRUE(permite(t, "PUT", "/v1/epoch", adm));
    EXPECT_TRUE(permite(t, "GET", "/components", adm));
    EXPECT_FALSE(permite(t, "GET", "/secrets/ml-detector", adm));
    // un OU que se llama como otro CN no da "propio"
    EXPECT_FALSE(permite(t, "GET", "/secrets/ml-detector", id("x", "ml-detector")));
}

TEST(EtcdServerAuthz, RutasRarasSeDeniegan) {
    const auto t = tabla_defecto();
    const auto sn = id("sniffer", "sniffer");
    for (const char* r : {"/secrets/sniffer/", "/secrets//sniffer", "/secrets/sniffer/x", "/secrets/Sniffer",
                          "/secrets/-sniffer", "/secrets/sniffer\n", "secrets/sniffer", "", "/config/sniffer/x"}) {
        EXPECT_FALSE(permite(t, "GET", r, sn)) << "[" << r << "]";
    }
}

TEST(EtcdServerAuthz, IdentidadNoValidaLoDeniegaTodo) {
    const auto t = tabla_defecto();
    Identidad mala;
    mala.motivo = "certificado sin OU";
    const auto d = decidir(t, "GET", "/health", mala);
    EXPECT_FALSE(d.permitido);
    EXPECT_EQ(d.motivo, "identidad no válida: certificado sin OU");
}

// ── identidad desde el certificado ──────────────────────────────────────────

TEST(EtcdServerIdentidad, CnYOu) {
    auto c = cert_con({{"OU", "sniffer"}, {"CN", "sniffer-2"}});
    const auto i = identidad_de_certificado(c.get());
    ASSERT_TRUE(i.valida) << i.motivo;
    EXPECT_EQ(i.cn, "sniffer-2");
    EXPECT_EQ(i.ou, "sniffer");
}

TEST(EtcdServerIdentidad, AmbiguosOMalFormadosNoValen) {
    struct Caso { std::vector<std::pair<std::string, std::string>> sujeto; const char* motivo; };
    const std::vector<Caso> casos = {
        {{{"CN", "sniffer"}}, "certificado sin OU"},
        {{{"OU", "sniffer"}}, "certificado sin CN"},
        {{{"OU", "sniffer"}, {"CN", "sniffer"}, {"CN", "admin"}}, "certificado con más de un CN"},
        {{{"OU", "sniffer"}, {"OU", "admin"}, {"CN", "sniffer"}}, "certificado con más de un OU"},
        {{{"OU", "sniffer"}, {"CN", "Sniffer"}}, "CN mal formado ([a-z0-9-]{1,63})"},
        {{{"OU", "sniffer"}, {"CN", "sniffer x"}}, "CN mal formado ([a-z0-9-]{1,63})"},
        {{{"OU", "admin\n"}, {"CN", "sniffer"}}, "OU mal formado ([a-z0-9-]{1,63})"},
        {{{"OU", "sniffer"}, {"CN", "sniffer\xc3\xa9"}}, "CN mal formado ([a-z0-9-]{1,63})"},
    };
    for (const auto& k : casos) {
        auto c = cert_con(k.sujeto);
        const auto i = identidad_de_certificado(c.get());
        EXPECT_FALSE(i.valida) << k.motivo;
        EXPECT_EQ(i.motivo, k.motivo);
        EXPECT_TRUE(i.cn.empty() || nombre_valido(i.cn));
    }
    EXPECT_EQ(identidad_de_certificado(nullptr).motivo, "sin certificado de cliente");
}

TEST(EtcdServerIdentidad, ParaLogQuitaControlesYAcota) {
    EXPECT_EQ(para_log("/a\nb\r\x1b"), "/a?b??");
    EXPECT_EQ(para_log(std::string(300, 'x')).size(), 259u);
}

// ── los JSON del repo y los defectos del código ─────────────────────────────

TEST(EtcdServerJsonRepo, TablaDeLosDosJsonIgualAlDefecto) {
    const std::string esperado = texto_tabla(tabla_defecto());
    for (const char* f : {"etcd-server.json", "etcd-server.etcd-vm.json"}) {
        Salida o;
        auto r = parse_authz(leer(f), o.aviso, o.info);
        EXPECT_EQ(r.defectos, 0) << f << "\n" << o.aviso.str();
        EXPECT_EQ(texto_tabla(r.reglas), esperado) << f;
    }
}

TEST(EtcdServerJsonRepo, TlsDefensorHttpYVmEtcdIgualAlDefecto) {
    Salida o1, o2;
    auto def = parse_tls_config(leer("etcd-server.json"), o1.aviso, o1.info);
    EXPECT_EQ(def.defectos, 0) << o1.aviso.str();
    EXPECT_EQ(def.cfg.modo, "http");  // transición del defender, hasta el paso 6
    auto vm = parse_tls_config(leer("etcd-server.etcd-vm.json"), o2.aviso, o2.info);
    EXPECT_EQ(vm.defectos, 0) << o2.aviso.str();
    const argus::etcdcfg::TlsConfig d{};
    EXPECT_EQ(vm.cfg.modo, d.modo);
    EXPECT_EQ(vm.cfg.ca_file, d.ca_file);
    EXPECT_EQ(vm.cfg.cert_file, d.cert_file);
    EXPECT_EQ(vm.cfg.key_file, d.key_file);
    EXPECT_EQ(vm.cfg.aviso_http_intervalo_s, d.aviso_http_intervalo_s);
    // fuera de tls, los dos JSON son iguales
    json a = leer("etcd-server.json"), b = leer("etcd-server.etcd-vm.json");
    a.erase("_doc"); b.erase("_doc");
    a["tls"].erase("modo"); b["tls"].erase("modo");
    a["almacen"].erase("modo"); b["almacen"].erase("modo");  // [ETCD-REGISTRO-D313] defender "memoria", VM "etcd"
    EXPECT_EQ(a, b);
}
