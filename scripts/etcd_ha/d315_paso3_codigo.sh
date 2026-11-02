#!/usr/bin/env bash
# [ETCD-ALMACEN-FATAL-D315] DEBT-ETCD-HA-TLS-RAFT-001 / DEBT-ANSIBLE-DEPLOY-CONFIGS-001, paso 3 (código del etcd-server).
#   Decisiones de Alonso DAY315: en modo etcd, almacen.endpoints, almacen.prefijo, almacen.ca_file, almacen.cert_file y
#   almacen.key_file NO tienen defecto (como vault_addrs en DAY314): ausentes o mal formados = [ETCD-ALMACEN-FATAL] y no
#   arranca; --check-config los cuenta (almacen_fatales=N). endpoints repetidos = mal formado. En modo memoria no se
#   usan: solo [CONFIG-DEFAULT] "no se usa en modo memoria".
#   Ficheros: etcd_server_almacen.hpp, src/main.cpp, tests/test_registro_componentes.cpp y el _doc de almacen en los
#   dos JSON del etcd-server (solo texto: ningún valor cambia).
#   Probado antes en el banco con g++-12 y las opciones de production (-O3 -march=native -DNDEBUG -flto): 16/16 y 22/22.
# No toca git. Uso (en el defender):  bash d315_paso3_codigo.sh --check [RAIZ]  |  bash d315_paso3_codigo.sh --apply [RAIZ]
set -euo pipefail
export LC_ALL=C
MODO=${1:-}
RAIZ=${2:-/vagrant}
case "$MODO" in --check|--apply) ;; *) echo "uso: $0 --check|--apply [RAIZ]"; exit 2 ;; esac
cd "$RAIZ"
E=etcd-server
declare -A SHA=(
  [$E/include/etcd_server/etcd_server_almacen.hpp]=9aafde81ad0f8f071ac746e07e41d1561a1a2530b0633c301765addcb0078a4a
  [$E/src/main.cpp]=0b81716973ee8058cfa991e3becfc8f73b51bd323c22bea9dbb9d7c25288f6c4
  [$E/tests/test_registro_componentes.cpp]=7cb4ed74e1840e5ff1f48aabe42c97f697bc02362a169d012d791d214e892035
  [$E/config/etcd-server.json]=0639d2affba5fd9ff1e06712859a83648f6b403a93c73e5e7abbec30af755e4b
  [$E/config/etcd-server.etcd-vm.json]=3bab613f5aa59353c473eb2ed7140416e8cae5bde0e52861ea07efc18b8cf494
)
DESPUES_VM=3fedf9add0db68a9f2e6ed9e45309d51a7591d348acbf26f950fca021ced210a
DESPUES_DEF=c2d9e0c0971f0da6fd1103a58ec6e4144e2e0c4407e0f740f493b951ed4d7048

if grep -q 'ETCD-ALMACEN-FATAL-D315' $E/include/etcd_server/etcd_server_almacen.hpp \
   && [ "$(sha256sum $E/config/etcd-server.etcd-vm.json | cut -d' ' -f1)" = "$DESPUES_VM" ]; then
  echo "[ETCD-ALMACEN-FATAL-D315] ya aplicado en $RAIZ: nada que hacer"; exit 0
fi
FALLOS=0
for f in "${!SHA[@]}"; do
  if [ ! -f "$f" ]; then echo "❌ falta $f"; FALLOS=$((FALLOS+1)); continue; fi
  h=$(sha256sum "$f" | cut -d' ' -f1)
  if [ "$h" = "${SHA[$f]}" ]; then echo "✅ $f (${h:0:16})"; else echo "❌ $f: sha256 $h, se esperaba ${SHA[$f]}"; FALLOS=$((FALLOS+1)); fi
done
if [ "$FALLOS" != 0 ]; then echo "[ETCD-ALMACEN-FATAL-D315] $FALLOS comprobaciones fallan: no se toca nada"; exit 1; fi
if [ "$MODO" = --check ]; then echo "[ETCD-ALMACEN-FATAL-D315] --check: todo listo para --apply"; exit 0; fi

python3 - "$PWD" <<'PY'
import json, sys, os

RAIZ = sys.argv[1]
H = os.path.join(RAIZ, "etcd-server/include/etcd_server/etcd_server_almacen.hpp")
M = os.path.join(RAIZ, "etcd-server/src/main.cpp")
T = os.path.join(RAIZ, "etcd-server/tests/test_registro_componentes.cpp")
J = [os.path.join(RAIZ, "etcd-server/config", f) for f in ("etcd-server.json", "etcd-server.etcd-vm.json")]


def cambiar(p, pares):
    s = open(p, encoding="utf-8").read()
    for viejo, nuevo in pares:
        n = s.count(viejo)
        assert n == 1, f"{p}: {viejo[:70]!r} aparece {n} veces"
        s = s.replace(viejo, nuevo)
    open(p, "w", encoding="utf-8").write(s)


# ------------------------------------------------------------------ cabecera
cambiar(H, [
    ("//   - Bloque \"almacen\" de etcd-server.json: modo (etcd | memoria), endpoints, ca_file, cert_file, key_file, prefijo,\n"
     "//     timeout_ms, aviso_intervalo_s. El JSON es la ley: ausente o mal formado -> defecto validado + [CONFIG-DEFAULT].\n",
     "//   - Bloque \"almacen\" de etcd-server.json: modo (etcd | memoria), endpoints, ca_file, cert_file, key_file, prefijo,\n"
     "//     timeout_ms, aviso_intervalo_s. El JSON es la ley: ausente o mal formado -> defecto validado + [CONFIG-DEFAULT].\n"
     "//   - [ETCD-ALMACEN-FATAL-D315] Excepción (decisión de Alonso DAY315, como vault_addrs en DAY314): en modo etcd,\n"
     "//     endpoints, prefijo, ca_file, cert_file y key_file NO tienen defecto. Ausentes o mal formados (endpoints\n"
     "//     repetidos incluidos) son [ETCD-ALMACEN-FATAL] y el etcd-server no arranca (--check-config lo cuenta). Los\n"
     "//     rellena Ansible por despliegue (DEBT-ANSIBLE-DEPLOY-CONFIGS-001): un prefijo con errata nunca cae en /argus/ en\n"
     "//     silencio, donde dos despliegues del mismo clúster se pisarían. En modo memoria no se usan: solo se avisa.\n"),
    ("// Defectos validados: iguales a etcd-server.etcd-vm.json (el del defender lleva modo \"memoria\": transición).\n"
     "struct AlmacenConfig {\n",
     "// Defectos validados: iguales a etcd-server.etcd-vm.json (el del defender lleva modo \"memoria\": transición).\n"
     "// [ETCD-ALMACEN-FATAL-D315] endpoints, ca_file, cert_file, key_file y prefijo NO se sustituyen por su defecto en modo\n"
     "// etcd: ausentes o mal formados son fatales. Su valor de abajo es el del JSON del lab y solo sirve de ejemplo.\n"
     "struct AlmacenConfig {\n"),
    ("struct ResultadoAlmacen {\n    AlmacenConfig cfg;\n    int defectos = 0;\n};\n",
     "struct ResultadoAlmacen {\n    AlmacenConfig cfg;\n    int defectos = 0;\n"
     "    std::vector<std::string> fatales;  // [ETCD-ALMACEN-FATAL-D315] en modo etcd: campos sin defecto ausentes o mal formados\n};\n"),
    # tras el modo: el lambda fatal
    ("""            o_modo = malo("modo", v, "\\"etcd\\" o \\"memoria\\"; una errata nunca rebaja a memoria", d.modo);
        }
    }

    std::string o_ep = "JSON";
    {
        const std::string fmt = "lista de 1 a 7 \\"https://IPv4:puerto\\"";
        const std::string def = nlohmann::json(d.endpoints).dump();
        if (!blk->contains("endpoints")) {
            o_ep = ausente("endpoints", fmt, def);
        } else {
            const auto& v = (*blk)["endpoints"];
            bool ok = v.is_array() && !v.empty() && v.size() <= 7;
            if (ok) {
                for (const auto& e : v) {
                    if (!e.is_string() || !detalle_almacen::endpoint_ok(e.get<std::string>())) ok = false;
                }
            }
            if (ok) {
                c.endpoints = v.get<std::vector<std::string>>();
            } else {
                o_ep = malo("endpoints", v, fmt, def);
            }
        }
    }

    auto ruta = [&](const char* clave, const std::string& def, std::string& out) -> std::string {
        out = def;
        if (!blk->contains(clave)) return ausente(clave, "ruta absoluta", def);
        const auto& v = (*blk)[clave];
        if (!v.is_string() || !detalle_almacen::ruta_ok(v.get<std::string>()))
            return malo(clave, v, "ruta absoluta, sin caracteres de control, hasta 4096", def);
        out = v.get<std::string>();
        return "JSON";
    };
""",
     """            o_modo = malo("modo", v, "\\"etcd\\" o \\"memoria\\"; una errata nunca rebaja a memoria", d.modo);
        }
    }
    // [ETCD-ALMACEN-FATAL-D315] campos del despliegue: sin defecto en modo etcd (fatal); en modo memoria no se usan y
    // solo se avisa
    const bool etcd = c.modo == "etcd";
    auto fatal = [&](const std::string& campo, const std::string& que, const std::string& formato) {
        std::string m = "almacen.";
        m += campo;
        m += ' ';
        m += que;
        m += " (";
        m += formato;
        m += ")";
        if (etcd) {
            r.fatales.push_back(m);
            aviso << "[ETCD-ALMACEN-FATAL] " << m << ": sin defecto (lo pone el inventario del despliegue); no se arranca"
                  << std::endl;
        } else {
            aviso << "[CONFIG-DEFAULT] " << m << ": no se usa en modo memoria" << std::endl;
            ++r.defectos;
        }
        return std::string(etcd ? "FATAL: " : "SIN USO: ") + que;
    };

    std::string o_ep = "JSON";
    {
        const std::string fmt = "lista de 1 a 7 \\"https://IPv4:puerto\\", sin repetir";
        if (!blk->contains("endpoints")) {
            o_ep = fatal("endpoints", "ausente", fmt);
        } else {
            const auto& v = (*blk)["endpoints"];
            bool ok = v.is_array() && !v.empty() && v.size() <= 7;
            std::vector<std::string> lista;
            if (ok) {
                for (const auto& e : v) {
                    if (!e.is_string() || !detalle_almacen::endpoint_ok(e.get<std::string>())) {
                        ok = false;
                        break;
                    }
                    for (const auto& x : lista) {
                        if (x == e.get<std::string>()) ok = false;
                    }
                    lista.push_back(e.get<std::string>());
                }
            }
            if (ok) {
                c.endpoints = lista;
            } else {
                o_ep = fatal("endpoints", "mal formado: " + v.dump(), fmt);
            }
        }
    }

    auto ruta = [&](const char* clave, std::string& out) -> std::string {
        const std::string fmt = "ruta absoluta, sin caracteres de control, hasta 4096";
        if (!blk->contains(clave)) return fatal(clave, "ausente", fmt);
        const auto& v = (*blk)[clave];
        if (!v.is_string() || !detalle_almacen::ruta_ok(v.get<std::string>()))
            return fatal(clave, "mal formado: " + v.dump(), fmt);
        out = v.get<std::string>();
        return "JSON";
    };
"""),
    ("""    const std::string o_ca = ruta("ca_file", d.ca_file, c.ca_file);
    const std::string o_cert = ruta("cert_file", d.cert_file, c.cert_file);
    const std::string o_key = ruta("key_file", d.key_file, c.key_file);
""",
     """    const std::string o_ca = ruta("ca_file", c.ca_file);
    const std::string o_cert = ruta("cert_file", c.cert_file);
    const std::string o_key = ruta("key_file", c.key_file);
"""),
    ("""        if (!blk->contains("prefijo")) {
            o_pre = ausente("prefijo", fmt, d.prefijo);
        } else {
            const auto& v = (*blk)["prefijo"];
            if (v.is_string() && detalle_almacen::prefijo_ok(v.get<std::string>())) {
                c.prefijo = v.get<std::string>();
            } else {
                o_pre = malo("prefijo", v, fmt, d.prefijo);
            }
        }
""",
     """        if (!blk->contains("prefijo")) {
            o_pre = fatal("prefijo", "ausente", fmt);
        } else {
            const auto& v = (*blk)["prefijo"];
            if (v.is_string() && detalle_almacen::prefijo_ok(v.get<std::string>())) {
                c.prefijo = v.get<std::string>();
            } else {
                o_pre = fatal("prefijo", "mal formado: " + v.dump(), fmt);
            }
        }
"""),
])

# ------------------------------------------------------------------ main.cpp
cambiar(M, [
    ("""    int almacen_ilegibles = 0;
    if (almacen_cfg.modo == "etcd") {
""",
     """    int almacen_ilegibles = 0;
    // [ETCD-ALMACEN-FATAL-D315] con campos fatales no se miran los ficheros (las rutas pueden ser las de ejemplo)
    const int almacen_fatales = static_cast<int>(leida_almacen.fatales.size());
    if (almacen_cfg.modo == "etcd" && almacen_fatales == 0) {
"""),
    ("""    } else {
        std::cerr << "[ETCD-ALMACEN-MEMORIA] almacen.modo=memoria""",
     """    } else if (almacen_cfg.modo == "memoria") {
        std::cerr << "[ETCD-ALMACEN-MEMORIA] almacen.modo=memoria"""),
    ("""        const bool limpio = fichero_ok && defectos == 0 && tls_ilegibles == 0 && almacen_ilegibles == 0 &&
                            claves_fatales == 0;""",
     """        const bool limpio = fichero_ok && defectos == 0 && tls_ilegibles == 0 && almacen_ilegibles == 0 &&
                            almacen_fatales == 0 && claves_fatales == 0;"""),
    ("""                  << ", ficheros_almacen_ilegibles=" << almacen_ilegibles << ", almacen_claves.modo=" """,
     """                  << ", ficheros_almacen_ilegibles=" << almacen_ilegibles << ", almacen_fatales=" << almacen_fatales
                  << ", almacen_claves.modo=" """),
    ("""    if (claves_fatales > 0) {
""",
     """    if (almacen_fatales > 0) {
        std::cerr << "[ETCD-ALMACEN-FATAL] " << almacen_fatales << " problemas en almacen de " << config_path
                  << ": el etcd-server no arranca (revisar con --check-config)" << std::endl;
        return 1;
    }
    if (claves_fatales > 0) {
"""),
])

# ------------------------------------------------------------------ tests
cambiar(T, [
    ("""TEST(AlmacenConfig, AusenteTodoDefecto) {
    std::ostringstream av, in;
    auto r = argus::etcdcfg::parse_almacen_config(json::object(), av, in);
    EXPECT_EQ(r.defectos, 9);
    EXPECT_EQ(r.cfg.modo, "etcd");
    EXPECT_EQ(r.cfg.endpoints, std::vector<std::string>{"https://127.0.0.1:2381"});
    EXPECT_EQ(r.cfg.reconexion_max_ms, 1000);
    EXPECT_NE(in.str().find("almacen.modo=etcd (DEFECTO: ausente)"), std::string::npos) << in.str();
}
""",
     """// [ETCD-ALMACEN-FATAL-D315] en modo etcd, endpoints, prefijo y las tres rutas no tienen defecto: fatales
TEST(AlmacenConfig, AusenteEnModoEtcdCincoFatales) {
    std::ostringstream av, in;
    auto r = argus::etcdcfg::parse_almacen_config(json::object(), av, in);
    EXPECT_EQ(r.cfg.modo, "etcd");
    EXPECT_EQ(r.fatales.size(), 5u) << av.str();
    EXPECT_EQ(r.defectos, 4) << av.str();  // modo, timeout_ms, aviso_intervalo_s, reconexion_max_ms
    EXPECT_EQ(r.cfg.reconexion_max_ms, 1000);
    EXPECT_NE(in.str().find("almacen.modo=etcd (DEFECTO: ausente)"), std::string::npos) << in.str();
    for (const char* campo : {"endpoints", "prefijo", "ca_file", "cert_file", "key_file"}) {
        EXPECT_NE(av.str().find(std::string("[ETCD-ALMACEN-FATAL] almacen.") + campo + " ausente"), std::string::npos)
            << campo << "\\n" << av.str();
    }
    EXPECT_NE(in.str().find("almacen.prefijo=/argus/ (FATAL: ausente)"), std::string::npos) << in.str();
    EXPECT_EQ(av.str().find("[CONFIG-DEFAULT] almacen.endpoints"), std::string::npos) << av.str();
}

TEST(AlmacenConfig, ModoMemoriaNoEsFatal) {
    std::ostringstream av, in;
    auto r = argus::etcdcfg::parse_almacen_config(json::parse(R"({"almacen": {"modo": "memoria"}})"), av, in);
    EXPECT_TRUE(r.fatales.empty()) << av.str();
    EXPECT_EQ(r.defectos, 8) << av.str();  // 5 sin uso + 3 enteros
    EXPECT_NE(av.str().find("almacen.endpoints ausente"), std::string::npos) << av.str();
    EXPECT_NE(av.str().find("no se usa en modo memoria"), std::string::npos) << av.str();
    EXPECT_NE(in.str().find("(SIN USO: ausente)"), std::string::npos) << in.str();
}

TEST(AlmacenConfig, EndpointsRepetidosEsFatal) {
    std::ostringstream av, in;
    auto r = argus::etcdcfg::parse_almacen_config(
        json{{"almacen", {{"endpoints", {"https://10.0.1.11:2381", "https://10.0.1.12:2381", "https://10.0.1.11:2381"}}}}},
        av, in);
    EXPECT_NE(av.str().find("[ETCD-ALMACEN-FATAL] almacen.endpoints mal formado"), std::string::npos) << av.str();
    EXPECT_NE(av.str().find("sin repetir"), std::string::npos) << av.str();
}
"""),
    ("""    EXPECT_EQ(r.defectos, 6) << av.str();
    EXPECT_EQ(r.cfg.endpoints[0], "https://127.0.0.1:2381");
    EXPECT_EQ(r.cfg.ca_file, "/etc/argus-pki/ca.crt");
    EXPECT_EQ(r.cfg.cert_file, "/a");
    EXPECT_EQ(r.cfg.prefijo, "/argus/");
    EXPECT_EQ(r.cfg.timeout_ms, 2000);
    EXPECT_EQ(r.cfg.reconexion_max_ms, 1000);
""",
     """    EXPECT_EQ(r.defectos, 3) << av.str();  // los tres enteros fuera de rango
    EXPECT_EQ(r.fatales.size(), 3u) << av.str();  // [ETCD-ALMACEN-FATAL-D315] endpoints, ca_file, prefijo
    EXPECT_EQ(r.cfg.cert_file, "/a");
    EXPECT_EQ(r.cfg.timeout_ms, 2000);
    EXPECT_EQ(r.cfg.reconexion_max_ms, 1000);
    for (const char* campo : {"endpoints", "ca_file", "prefijo"}) {
        EXPECT_NE(av.str().find(std::string("[ETCD-ALMACEN-FATAL] almacen.") + campo + " mal formado"), std::string::npos)
            << campo << "\\n" << av.str();
    }
"""),
    ("""        EXPECT_NE(a2.str().find("almacen.endpoints="), std::string::npos) << ep;
""",
     """        EXPECT_NE(a2.str().find("[ETCD-ALMACEN-FATAL] almacen.endpoints mal formado"), std::string::npos) << ep;
        EXPECT_FALSE(r2.fatales.empty()) << ep;
"""),
    ("""    EXPECT_EQ(r3.cfg.endpoints.size(), 2u);  // PR2: varios nodos
""",
     """    EXPECT_EQ(r3.cfg.endpoints.size(), 2u);  // PR2: varios nodos
    EXPECT_EQ(std::count_if(r3.fatales.begin(), r3.fatales.end(),
                            [](const std::string& f) { return f.rfind("almacen.endpoints", 0) == 0; }),
              0);
"""),
    ("""    EXPECT_EQ(def.defectos, 0) << a1.str();
    EXPECT_EQ(def.cfg.modo, "memoria");  // transición del defender, hasta el paso 6
""",
     """    EXPECT_EQ(def.defectos, 0) << a1.str();
    EXPECT_TRUE(def.fatales.empty()) << a1.str();
    EXPECT_EQ(def.cfg.modo, "memoria");  // transición del defender, hasta el paso 6
"""),
    ("""    EXPECT_EQ(vm.defectos, 0) << a2.str();
    const argus::etcdcfg::AlmacenConfig d{};
""",
     """    EXPECT_EQ(vm.defectos, 0) << a2.str();
    EXPECT_TRUE(vm.fatales.empty()) << a2.str();
    const argus::etcdcfg::AlmacenConfig d{};
"""),
])
s = open(T, encoding="utf-8").read()
if "#include <algorithm>" not in s:
    cambiar(T, [("#include <chrono>\n#include <fstream>\n", "#include <algorithm>\n#include <chrono>\n#include <fstream>\n")])

# ------------------------------------------------------------------ _doc de los dos JSON
VIEJO = 'endpoints: lista de 1 a 7 "https://IPv4:puerto". ca_file, cert_file, key_file: rutas absolutas (el CN del certificado es el usuario RBAC de etcd). prefijo: empieza y acaba en /, [a-z0-9-/], hasta 64.'
NUEVO = ('[ETCD-ALMACEN-FATAL-D315] endpoints, prefijo, ca_file, cert_file y key_file NO tienen defecto en modo etcd: '
         'ausentes o mal formados son [ETCD-ALMACEN-FATAL] y el etcd-server no arranca (en modo memoria no se usan). '
         'endpoints y prefijo los pone Ansible desde el inventario del despliegue (make deploy-configs). '
         'endpoints: lista de 1 a 7 "https://IPv4:puerto", sin repetir, con TODOS los miembros etcd del despliegue. '
         'ca_file, cert_file, key_file: rutas absolutas (el CN del certificado es el usuario RBAC de etcd). '
         'prefijo: empieza y acaba en /, [a-z0-9-/], hasta 64, sin //; uno por despliegue (p. ej. /argus/<hospital>/<planta>/).')
for p in J:
    txt = open(p, encoding="utf-8").read()
    d = json.loads(txt)
    assert txt == json.dumps(d, indent=2) + "\n", f"{p}: formato inesperado"
    doc = d["almacen"]["_doc"]
    assert doc.count(VIEJO) == 1, f"{p}: _doc de almacen sin el texto esperado"
    d["almacen"]["_doc"] = doc.replace(VIEJO, NUEVO)
    open(p, "w", encoding="utf-8").write(json.dumps(d, indent=2) + "\n")
print("p3_codigo: cabecera, main.cpp, test y _doc de los dos JSON cambiados")
PY

set +e; OK=0; MAL=0
chk() { if [ "$2" = 0 ]; then echo "✅ $1"; OK=$((OK+1)); else echo "❌ $1"; MAL=$((MAL+1)); fi; }
[ "$(sha256sum $E/config/etcd-server.etcd-vm.json | cut -d' ' -f1)" = "$DESPUES_VM" ];  chk "etcd-server.etcd-vm.json: solo cambia el _doc (sha256 ${DESPUES_VM:0:16})" $?
[ "$(sha256sum $E/config/etcd-server.json | cut -d' ' -f1)" = "$DESPUES_DEF" ];         chk "etcd-server.json: solo cambia el _doc (sha256 ${DESPUES_DEF:0:16})" $?
[ "$(grep -cE '(= |return )fatal\(' $E/include/etcd_server/etcd_server_almacen.hpp)" = 6 ];            chk "cabecera: 6 llamadas a fatal (endpoints x2, rutas x2, prefijo x2)" $?
grep -q 'almacen_fatales=' $E/src/main.cpp && grep -q '\[ETCD-ALMACEN-FATAL\] " << almacen_fatales' $E/src/main.cpp; chk "main.cpp: --check-config cuenta almacen_fatales y no arranca con fatales" $?
[ "$(grep -c '^TEST(AlmacenConfig' $E/tests/test_registro_componentes.cpp)" = 6 ];        chk "test: 6 casos AlmacenConfig (3 nuevos o renombrados)" $?
echo "[ETCD-ALMACEN-FATAL-D315] comprobaciones finales: $OK PASA, $MAL FALLA"
[ "$MAL" = 0 ]
