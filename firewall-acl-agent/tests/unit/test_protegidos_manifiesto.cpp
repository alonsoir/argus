// test_protegidos_manifiesto.cpp — [PROTEGIDOS-MANIFIESTO-D318] ADR-060 8e.1a. Standalone, CHECK propio.
// Clave desechable generada aquí (tests unitarios, DAY316). El formato de firma es el de Vault transit (vault:vN:<b64>);
// la compatibilidad real con Vault 2.2.1 se midió en el banco DAY318 (BACKLOG [PROTEGIDOS-PUBKEY-D318]).
#include "firewall/protegidos_manifiesto.hpp"

#include <sodium.h>

#include <cstdio>
#include <iostream>
#include <string>
#include <unistd.h>

using namespace mldefender::firewall;
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
