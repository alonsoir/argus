#!/usr/bin/env python3
# d319_p8e3d0_etcd_server.py — DAY319, ADR-060 paso 8e.3d-0 [PROTEGIDOS-MANIFIESTO-D319] (decisión G-C de Alonso).
# etcd-server: GET /v1/protegidos/v/{n}, una versión del histórico (protegidos/v/<N>) tal cual, solo ou:argus-infra
# (tabla authz por defecto y los dos etcd-server*.json), para el diff y el deshacer de argus-infra. 400 si n no es un
# decimal >= 1 sin ceros a la izquierda de 64 bits, 404 si no existe, 503 sin hospital o almacén caído. Tests nuevos.
# Banco (Debian 12, GCC 12.2, production, native y skylake): etcd-server 8/8; 4 mutaciones detectadas.
# Uso: python3 ESTE.py --check RAIZ | --apply RAIZ   (todo o nada, idempotente, sha256 previo y final)
import hashlib, os, sys
OPS = []
# mod etcd-server/include/etcd_server/protegidos_servidor.hpp
_s0 = '70e662cd15f6822bea1513f390af4a368703540e1ee2d50b5ae821a9fdaac423'
_s1 = '2daa5c2783f0201e4304237da624186222218102730fd5352b534a9b99006bd3'
_t = []
_t.append(('//     protegidos/v/<N> = cada versión publicada, que no se vuelve a escribir.\n//   - PUT: verificar_documento (libs/protegidos) con la clave pública COMPILADA (la misma que el firewall): firma,\n',
           '//     protegidos/v/<N> = cada versión publicada, que no se vuelve a escribir.\n//   - GET /v1/protegidos/v/{n} (solo ou:argus-infra, 8e.3d-0): protegidos/v/<n> tal cual.\n//   - PUT: verificar_documento (libs/protegidos) con la clave pública COMPILADA (la misma que el firewall): firma,\n'))
_t.append(('    Respuesta obtener();\n    // PUT /v1/protegidos: 201 publicado; 400 formato, límites o planta; 403 firma u hospital; 409 versión no mayor que\n',
           '    Respuesta obtener();\n    // [PROTEGIDOS-MANIFIESTO-D319] 8e.3d-0 (decisión G-C de Alonso): GET /v1/protegidos/v/{n}, una versión del histórico\n    // (protegidos/v/<N>) tal cual, para que argus-infra haga diff y deshacer N (el contenido de N firmado como N+1).\n    // 200 con el sobre; 400 si n no es un decimal >= 1 sin ceros a la izquierda que quepa en 64 bits; 404 si esa\n    // versión no existe; 503 sin configurar o almacén no disponible. No verifica: quien lo pide verifica la firma.\n    Respuesta obtener_version(const std::string& n);\n    // PUT /v1/protegidos: 201 publicado; 400 formato, límites o planta; 403 firma u hospital; 409 versión no mayor que\n'))
OPS.append(('mod', 'etcd-server/include/etcd_server/protegidos_servidor.hpp', _s0, _s1, _t, 0o664))
# mod etcd-server/src/protegidos_servidor.cpp
_s0 = '9d56e87b7bb66544c4cf741a27bf1ef91da344fef4b1e5caa0ece6ddfa644a1b'
_s1 = '06a95927cc1d86bf72d2addba1b6d17b1c72e96f3c18d04745a35c296ea8e1fb'
_t = []
_t.append(('#include <cstdio>\n#include <map>\n',
           '#include <cstdio>\n#include <cstdlib>\n#include <map>\n'))
_t.append(('\nAlmacenProtegidos::Respuesta AlmacenProtegidos::publicar(const std::string& sobre, const std::string& quien) {\n',
           '\nAlmacenProtegidos::Respuesta AlmacenProtegidos::obtener_version(const std::string& n) {\n    if (hospital_id_.empty()) return {503, error_json("sin-configurar", "protegidos.hospital_id sin valor en etcd-server.json")};\n    // [PROTEGIDOS-MANIFIESTO-D319] decimal >= 1, sin ceros a la izquierda, que quepa en 64 bits (20 cifras como mucho)\n    static const std::string kMax = "18446744073709551615";\n    const bool cifras = !n.empty() && n.size() <= kMax.size() && n[0] != \'0\' &&\n                        std::all_of(n.begin(), n.end(), [](char c) { return c >= \'0\' && c <= \'9\'; });\n    if (!cifras || (n.size() == kMax.size() && n > kMax)) {\n        return {400, error_json("formato", "versión \'" + detalle_protegidos::saneado(n) +\n                                               "\' mal formada (entero decimal >= 1 sin ceros a la izquierda, 64 bits)")};\n    }\n    const uint64_t v = std::strtoull(n.c_str(), nullptr, 10);\n    std::lock_guard<std::mutex> l(m_);\n    std::string s;\n    const Estado e = almacen_->leer(clave_version(v), s);\n    if (e == Estado::Ok) return {200, s};\n    if (e == Estado::NoEncontrado) return {404, error_json("sin-version", "la versión " + n + " no está en el histórico")};\n    return {503, error_json("almacen", "almacén no disponible: " + almacen_->ultimo_error())};\n}\n\nAlmacenProtegidos::Respuesta AlmacenProtegidos::publicar(const std::string& sobre, const std::string& quien) {\n'))
OPS.append(('mod', 'etcd-server/src/protegidos_servidor.cpp', _s0, _s1, _t, 0o664))
# mod etcd-server/src/etcd_server.cpp
_s0 = '21d1bd253ad77429ac1f3ae838f792b25e429a456fcd8029fc75383b0d64f43d'
_s1 = '647d7dd21fe786d47d6111ce384430c703ac37ef2fb4baf789e87d05d2a958db'
_t = []
_t.append(('    });\n    server.Put("/v1/protegidos", [this, error, con_tls](const httplib::Request& req, httplib::Response& res) {\n',
           '    });\n    // [PROTEGIDOS-MANIFIESTO-D319] 8e.3d-0: una versión del histórico (solo ou:argus-infra, tabla authz): diff y deshacer\n    server.Get(R"(/v1/protegidos/v/([^/]+))", [this, error](const httplib::Request& req, httplib::Response& res) {\n        if (protegidos_ == nullptr) {\n            error(res, 503, "manifiesto de protegidos no disponible en este etcd-server");\n            return;\n        }\n        const auto r = protegidos_->obtener_version(req.matches[1]);\n        res.status = r.http;\n        res.set_content(r.cuerpo, "application/json");\n    });\n    server.Put("/v1/protegidos", [this, error, con_tls](const httplib::Request& req, httplib::Response& res) {\n'))
OPS.append(('mod', 'etcd-server/src/etcd_server.cpp', _s0, _s1, _t, 0o775))
# mod etcd-server/include/etcd_server/etcd_server_authz.hpp
_s0 = 'b559367598bd0a16d85fbc11c16a3945728007a18ea372866013e487c7ed4586'
_s1 = 'b13f0110fa1ad751195f1e0719ea51aa63d67fc9005809f84c510a55b137dbe6'
_t = []
_t.append(('  {"metodo": "GET",  "ruta": "/v1/protegidos",        "permitir": ["ou:firewall-acl-agent", "ou:argus-infra"]},\n  {"metodo": "PUT",  "ruta": "/v1/protegidos",        "permitir": ["ou:argus-infra"]}\n])";\n',
           '  {"metodo": "GET",  "ruta": "/v1/protegidos",        "permitir": ["ou:firewall-acl-agent", "ou:argus-infra"]},\n  {"metodo": "PUT",  "ruta": "/v1/protegidos",        "permitir": ["ou:argus-infra"]},\n  {"metodo": "GET",  "ruta": "/v1/protegidos/v/{c}",  "permitir": ["ou:argus-infra"]}\n])";\n'))
OPS.append(('mod', 'etcd-server/include/etcd_server/etcd_server_authz.hpp', _s0, _s1, _t, 0o664))
# mod etcd-server/config/etcd-server.json
_s0 = '865cb8007a6289331c5482badf20cbb996f4a05fa86d06514a240affd269685b'
_s1 = '5af4946cf8b3e84b16767c993a091f8bacc7ca3e6cd39601b1a3e780d0ac60a8'
_t = []
_t.append(('        ]\n      }\n',
           '        ]\n      },\n      {\n        "metodo": "GET",\n        "ruta": "/v1/protegidos/v/{c}",\n        "permitir": [\n          "ou:argus-infra"\n        ]\n      }\n'))
_t.append(('  "protegidos": {\n    "_doc": "[PROTEGIDOS-MANIFIESTO-D318] ADR-060 8e.3b. hospital_id: el hospital al que sirve ESTE etcd-server ([a-z0-9-], de 1 a 64); sin valor sano por defecto: ausente o mal formado = [CONFIG-DEFAULT] y GET/PUT /v1/protegidos responden 503. Ansible (make deploy-configs) lo escribe desde argus_hospital_id del inventario. GET /v1/protegidos da el sobre vigente (firewall-acl-agent, argus-infra); PUT /v1/protegidos solo con certificado OU=argus-infra: el etcd-server verifica firma (clave publica compilada, la misma que el firewall), formato, limites, hospital y version > la vigente antes de guardarlo en etcd (protegidos/vigente y protegidos/v/<N>).",\n    "hospital_id": "hospital-lab"\n',
           '  "protegidos": {\n    "_doc": "[PROTEGIDOS-MANIFIESTO-D318] ADR-060 8e.3b. hospital_id: el hospital al que sirve ESTE etcd-server ([a-z0-9-], de 1 a 64); sin valor sano por defecto: ausente o mal formado = [CONFIG-DEFAULT] y GET/PUT /v1/protegidos responden 503. Ansible (make deploy-configs) lo escribe desde argus_hospital_id del inventario. GET /v1/protegidos da el sobre vigente (firewall-acl-agent, argus-infra); PUT /v1/protegidos solo con certificado OU=argus-infra: el etcd-server verifica firma (clave publica compilada, la misma que el firewall), formato, limites, hospital y version > la vigente antes de guardarlo en etcd (protegidos/vigente y protegidos/v/<N>). [PROTEGIDOS-MANIFIESTO-D319] GET /v1/protegidos/v/{n} solo con certificado OU=argus-infra: la versi\\u00f3n n del hist\\u00f3rico tal cual (n: decimal >= 1 sin ceros a la izquierda; 404 si no existe), para el diff y el deshacer de argus-infra.",\n    "hospital_id": "hospital-lab"\n'))
OPS.append(('mod', 'etcd-server/config/etcd-server.json', _s0, _s1, _t, 0o775))
# mod etcd-server/config/etcd-server.smoke-enterprise.json
_s0 = 'ed343181bff0a545da6b8635358c7ff7770bb4a508e7379a29b7e8a1697a39e4'
_s1 = '6e3a1f2110d1455b7159aa31306879e0212bdbb8ba8eec953e9336054e3a3ff1'
_t = []
_t.append(('        ]\n      }\n',
           '        ]\n      },\n      {\n        "metodo": "GET",\n        "ruta": "/v1/protegidos/v/{c}",\n        "permitir": [\n          "ou:argus-infra"\n        ]\n      }\n'))
_t.append(('  "protegidos": {\n    "_doc": "[PROTEGIDOS-MANIFIESTO-D318] ADR-060 8e.3b. hospital_id: el hospital al que sirve ESTE etcd-server ([a-z0-9-], de 1 a 64); sin valor sano por defecto: ausente o mal formado = [CONFIG-DEFAULT] y GET/PUT /v1/protegidos responden 503. Ansible (make deploy-configs) lo escribe desde argus_hospital_id del inventario. GET /v1/protegidos da el sobre vigente (firewall-acl-agent, argus-infra); PUT /v1/protegidos solo con certificado OU=argus-infra: el etcd-server verifica firma (clave publica compilada, la misma que el firewall), formato, limites, hospital y version > la vigente antes de guardarlo en etcd (protegidos/vigente y protegidos/v/<N>).",\n    "hospital_id": "hospital-lab"\n',
           '  "protegidos": {\n    "_doc": "[PROTEGIDOS-MANIFIESTO-D318] ADR-060 8e.3b. hospital_id: el hospital al que sirve ESTE etcd-server ([a-z0-9-], de 1 a 64); sin valor sano por defecto: ausente o mal formado = [CONFIG-DEFAULT] y GET/PUT /v1/protegidos responden 503. Ansible (make deploy-configs) lo escribe desde argus_hospital_id del inventario. GET /v1/protegidos da el sobre vigente (firewall-acl-agent, argus-infra); PUT /v1/protegidos solo con certificado OU=argus-infra: el etcd-server verifica firma (clave publica compilada, la misma que el firewall), formato, limites, hospital y version > la vigente antes de guardarlo en etcd (protegidos/vigente y protegidos/v/<N>). [PROTEGIDOS-MANIFIESTO-D319] GET /v1/protegidos/v/{n} solo con certificado OU=argus-infra: la versi\\u00f3n n del hist\\u00f3rico tal cual (n: decimal >= 1 sin ceros a la izquierda; 404 si no existe), para el diff y el deshacer de argus-infra.",\n    "hospital_id": "hospital-lab"\n'))
OPS.append(('mod', 'etcd-server/config/etcd-server.smoke-enterprise.json', _s0, _s1, _t, 0o664))
# mod etcd-server/tests/test_etcd_server_authz.cpp
_s0 = '5fab795cfd7e3118d307f861cdc625a9743bf541b9b8a79256884aac1edd010f'
_s1 = 'e3e2cb5eff5bff84628b032be8667ea1cc991084d3d43dfb1dc7759f169c0226'
_t = []
_t.append(('    EXPECT_EQ(r.defectos, 1);\n    EXPECT_EQ(r.reglas.size(), 15u);  // [ADR045-FUERA-D316] 15 menos las dos de /v1/epoch; [D318] + las dos de /v1/protegidos\n    EXPECT_NE(o.aviso.str().find("authz ausente"), std::string::npos);\n    EXPECT_NE(o.info.str().find("[ETCD-AUTHZ] regla 1/15: GET /health permitir=cualquiera (DEFECTO: ausente)"),\n              std::string::npos) << o.info.str();\n',
           '    EXPECT_EQ(r.defectos, 1);\n    EXPECT_EQ(r.reglas.size(), 16u);  // [ADR045-FUERA-D316] 15 menos las dos de /v1/epoch; [D318] + las dos de /v1/protegidos; [D319] + /v1/protegidos/v/{c}\n    EXPECT_NE(o.aviso.str().find("authz ausente"), std::string::npos);\n    EXPECT_NE(o.info.str().find("[ETCD-AUTHZ] regla 1/16: GET /health permitir=cualquiera (DEFECTO: ausente)"),\n              std::string::npos) << o.info.str();\n'))
_t.append(('        EXPECT_EQ(r.defectos, 1) << mala;\n        EXPECT_EQ(r.reglas.size(), 15u) << mala;  // la tabla por defecto ENTERA, no la buena a medias\n        EXPECT_NE(o.aviso.str().find("authz.reglas[1]"), std::string::npos) << mala << "\\n" << o.aviso.str();\n',
           '        EXPECT_EQ(r.defectos, 1) << mala;\n        EXPECT_EQ(r.reglas.size(), 16u) << mala;  // la tabla por defecto ENTERA, no la buena a medias\n        EXPECT_NE(o.aviso.str().find("authz.reglas[1]"), std::string::npos) << mala << "\\n" << o.aviso.str();\n'))
_t.append(('    EXPECT_FALSE(permite(t, "GET", "/v1/protegidos/hospital-lab", fw));\n}\n',
           '    EXPECT_FALSE(permite(t, "GET", "/v1/protegidos/hospital-lab", fw));\n    // [PROTEGIDOS-MANIFIESTO-D319] 8e.3d-0: el histórico, SOLO argus-infra (diff y deshacer); el firewall no lo necesita\n    EXPECT_TRUE(permite(t, "GET", "/v1/protegidos/v/1", inf));\n    EXPECT_TRUE(permite(t, "GET", "/v1/protegidos/v/12345", inf));\n    EXPECT_FALSE(permite(t, "GET", "/v1/protegidos/v/1", fw));\n    EXPECT_FALSE(permite(t, "GET", "/v1/protegidos/v/1", adm));\n    EXPECT_FALSE(permite(t, "GET", "/v1/protegidos/v/1", sn));\n    EXPECT_FALSE(permite(t, "PUT", "/v1/protegidos/v/1", inf));     // el histórico no se escribe\n    EXPECT_FALSE(permite(t, "DELETE", "/v1/protegidos/v/1", inf));  // ni se borra\n    EXPECT_FALSE(permite(t, "GET", "/v1/protegidos/v", inf));\n    EXPECT_FALSE(permite(t, "GET", "/v1/protegidos/v/1/x", inf));\n}\n'))
OPS.append(('mod', 'etcd-server/tests/test_etcd_server_authz.cpp', _s0, _s1, _t, 0o664))
# mod etcd-server/tests/test_protegidos_servidor.cpp
_s0 = 'dc72ff6238b3255d1e5e3319f721747792bb749f0d673586a61c68da78f29d79'
_s1 = '313ad4022d99a8b76b0c56091e290c880bd1570182657541f38f760834764e7f'
_t = []
_t.append(('\nTEST(ProtegidosServidor, ClaveVersionOrdenaBien) {\n',
           '\nTEST(ProtegidosServidor, HistoricoPorVersion) {\n    // [PROTEGIDOS-MANIFIESTO-D319] 8e.3d-0: GET /v1/protegidos/v/{n}, para el diff y el deshacer de argus-infra\n    Banco b;\n    EXPECT_EQ(b.al->obtener_version("1").http, 404);   // nada publicado\n    const std::string s1 = b.firmado(1), s2 = b.firmado(2);\n    ASSERT_EQ(b.al->publicar(s1, "argus-infra").http, 201);\n    ASSERT_EQ(b.al->publicar(s2, "argus-infra").http, 201);\n    const auto g1 = b.al->obtener_version("1");\n    EXPECT_EQ(g1.http, 200);\n    EXPECT_EQ(g1.cuerpo, s1);                           // los bytes exactos: argus-infra verifica la misma firma\n    EXPECT_EQ(b.al->obtener_version("2").cuerpo, s2);\n    EXPECT_EQ(b.al->obtener().cuerpo, s2);              // el vigente no cambia por leer el histórico\n    const auto g3 = b.al->obtener_version("3");\n    EXPECT_EQ(g3.http, 404);\n    EXPECT_EQ(json::parse(g3.cuerpo)["motivo"], "sin-version");\n    for (const char* mal : {"0", "01", "", "-1", "1a", "abc", "18446744073709551616", "99999999999999999999",\n                            "123456789012345678901", " 1", "1 "}) {\n        const auto r = b.al->obtener_version(mal);\n        EXPECT_EQ(r.http, 400) << "\'" << mal << "\'";\n        EXPECT_EQ(json::parse(r.cuerpo)["motivo"], "formato") << mal;\n    }\n    EXPECT_EQ(b.al->obtener_version("18446744073709551615").http, 404);   // el máximo de 64 bits es válido\n    b.mem->simular_caido(true);\n    EXPECT_EQ(b.al->obtener_version("1").http, 503);\n    b.mem->simular_caido(false);\n    EXPECT_EQ(b.al->obtener_version("1").http, 200);\n}\n\nTEST(ProtegidosServidor, HistoricoSinHospital503) {\n    Banco b("");\n    EXPECT_EQ(b.al->obtener_version("1").http, 503);\n}\n\nTEST(ProtegidosServidor, ClaveVersionOrdenaBien) {\n'))
OPS.append(('mod', 'etcd-server/tests/test_protegidos_servidor.cpp', _s0, _s1, _t, 0o664))
# mod etcd-server/CMakeLists.txt
_s0 = '67243bbb63511367d3ea4e3fba1d8f905d3cba6a358980ba02e182444e180f62'
_s1 = '94c155ea6031cd71c824cd057b6a36798ca611b26b90ee01c527594e327bd6cb'
_t = []
_t.append(('    # versión no mayor, ya existe, firma, hospital, planta con duplicado, almacén caído, vigente que ya no verifica,\n    # sin configurar; clave desechable generada en el test (ayudantes de libs/protegidos/tests)\n    add_executable(test_protegidos_servidor tests/test_protegidos_servidor.cpp src/protegidos_servidor.cpp)\n',
           '    # versión no mayor, ya existe, firma, hospital, planta con duplicado, almacén caído, vigente que ya no verifica,\n    # sin configurar; histórico por versión (D319, 8e.3d-0); clave desechable generada en el test (ayudantes de\n    # libs/protegidos/tests)\n    add_executable(test_protegidos_servidor tests/test_protegidos_servidor.cpp src/protegidos_servidor.cpp)\n'))
OPS.append(('mod', 'etcd-server/CMakeLists.txt', _s0, _s1, _t, 0o775))


def sha(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def leer(p):
    with open(p, "rb") as f:
        return f.read().decode("utf-8")


def plan(raiz):
    """Devuelve [(ruta, contenido nuevo o None para borrar, modo, estado)] sin tocar nada; falla si algo no cuadra."""
    out, errores = [], []
    for tipo, r, s0, s1, dato, modo in OPS:
        p = os.path.join(raiz, r)
        hay = os.path.exists(p)
        actual = leer(p) if hay else None
        if tipo == "del":
            if not hay:
                out.append((r, None, 0, "ya aplicado"))
            elif sha(actual) == s0:
                out.append((r, None, 0, "borrar"))
            else:
                errores.append(f"{r}: sha256 {sha(actual)} (se espera {s0})")
            continue
        if hay and sha(actual) == s1:
            out.append((r, actual, modo, "ya aplicado"))
            continue
        if tipo == "new":
            if hay:
                errores.append(f"{r}: ya existe con otro contenido (sha256 {sha(actual)})")
            else:
                out.append((r, dato, modo, "crear"))
            continue
        if not hay:
            errores.append(f"{r}: no existe")
            continue
        if sha(actual) != s0:
            errores.append(f"{r}: sha256 {sha(actual)} (se espera {s0} antes o {s1} después)")
            continue
        t, pos = actual, 0
        for anc, nue in dato:
            if actual.count(anc) != 1:
                errores.append(f"{r}: un ancla aparece {actual.count(anc)} veces")
                break
            k = t.find(anc, pos)
            if k < 0:
                errores.append(f"{r}: ancla fuera de orden")
                break
            t = t[:k] + nue + t[k + len(anc):]
            pos = k + len(nue)
        else:
            if sha(t) != s1:
                errores.append(f"{r}: el resultado no da el sha256 esperado")
            else:
                out.append((r, t, None, "modificar"))
    if errores:
        for e in errores:
            print("[PARCHE] FALLA " + e)
        sys.exit(1)
    return out


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: --check RAIZ | --apply RAIZ")
        sys.exit(2)
    raiz = sys.argv[2]
    if not os.path.isfile(os.path.join(raiz, "Makefile")) or not os.path.isdir(os.path.join(raiz, ".git")):
        print(f"[PARCHE] FALLA {raiz} no parece la raíz del repo (sin Makefile o sin .git)")
        sys.exit(1)
    for _, r, s0, s1, _, _ in OPS:
        q = os.path.join(raiz, r)
        print(f"[PARCHE] {r}: sha256 previo {sha(leer(q)) if os.path.exists(q) else '(no existe)'}")
    p = plan(raiz)
    for r, _, _, estado in p:
        print(f"[PARCHE] {estado:12s} {r}")
    if sys.argv[1] == "--check":
        print("[PARCHE] --check OK: " + ("todo ya aplicado" if all(e == "ya aplicado" for *_, e in p) else
                                         "se puede aplicar"))
        return
    for r, t, modo, estado in p:
        if estado == "ya aplicado":
            continue
        q = os.path.join(raiz, r)
        if t is None:
            os.unlink(q)
            continue
        os.makedirs(os.path.dirname(q), exist_ok=True)
        tmp = q + ".parche.tmp"
        with open(tmp, "wb") as f:
            f.write(t.encode("utf-8"))
        if modo is not None:
            os.chmod(tmp, modo)
        else:
            os.chmod(tmp, os.stat(q).st_mode & 0o777)
        os.replace(tmp, q)
    for tipo, r, s0, s1, _, _ in OPS:
        q = os.path.join(raiz, r)
        if tipo == "del":
            print(f"[PARCHE] {r}: {'borrado' if not os.path.exists(q) else 'FALLA sigue ahí'}")
        else:
            final = sha(leer(q))
            print(f"[PARCHE] {r}")
            print(f"[PARCHE]   sha256 final  {final} {'OK' if final == s1 else 'FALLA'}")
    print("[PARCHE] --apply HECHO")


if __name__ == "__main__":
    main()
