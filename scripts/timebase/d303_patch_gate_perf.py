#!/usr/bin/env python3
# DAY303 [ARGUS-GATE-PERF-D303]: gate del firewall sin Skipped y tests de rendimiento que miden y validan.
#  - fixture de IPSetWrapperTest a tests/unit/ipset_wrapper_fixture.hpp (movido tal cual)
#  - test_ipset_wrapper.cpp: 19 funcionales (fuera BatchAddPerformance y TestPerformance)
#  - test_ipset_wrapper_perf.cpp: BatchAddRestore1000 y TestLookupForkExec (no fallan por tiempo)
#  - tests/ctest_label_gate.sh: sudo ctest -L ETIQUETA -V; falla si ctest falla, 0 tests o cualquier saltado
#  - CMake: ejecutables ipset_wrapper_tests (e2e;root) e ipset_wrapper_perf_tests (perf;root)
#  - Makefile: test-components -LE 'root|perf'; test-firewall-e2e y test-firewall-perf via el script
# Uso (Mac, raiz del repo): python3 scripts/timebase/d303_patch_gate_perf.py --check | --apply
import difflib
import re
import sys
from pathlib import Path

MARCA = "[ARGUS-GATE-PERF-D303]"
FW = Path("firewall-acl-agent")
T = FW / "tests/unit/test_ipset_wrapper.cpp"
FIX = FW / "tests/unit/ipset_wrapper_fixture.hpp"
PERF = FW / "tests/unit/test_ipset_wrapper_perf.cpp"
GATE = FW / "tests/ctest_label_gate.sh"
CM = FW / "CMakeLists.txt"
MK = Path("Makefile")
HDR = FW / "include/firewall/ipset_wrapper.hpp"

if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
    print("uso: d303_patch_gate_perf.py --check | --apply")
    sys.exit(2)
MODO = sys.argv[1]
errores = []


def leer(p):
    return p.read_text(encoding="utf-8")


def unico(texto, trozo, donde):
    n = texto.count(trozo)
    if n != 1:
        errores.append(f"{donde}: se esperaba 1 aparicion de {trozo!r}, hay {n}")
    return n == 1


t, cm, mk, hdr = leer(T), leer(CM), leer(MK), leer(HDR)

ya = [str(p) for p in (FIX, PERF, GATE) if p.exists()]
ya += [str(p) for p, x in ((CM, cm), (MK, mk), (T, t)) if MARCA in x]
if ya:
    print("YA APLICADO (total o parcial), no se toca nada:", ya)
    sys.exit(1)

if "make_blacklist_config" not in hdr:
    errores.append(f"{HDR}: no declara make_blacklist_config (R1); el fixture movido no compilaria")
if "test-firewall-perf" in mk:
    errores.append("Makefile: ya existe test-firewall-perf")

# ---- 1. fixture -> header ---------------------------------------------------------------------------
INI = '#include "firewall/ipset_wrapper.hpp"\n'
FIN = '    static constexpr const char* TEST_SET_NAME_2 = "test_ipset_2";\n};\n'
t2 = t
fixture_hpp = ""
if unico(t, INI, str(T)) and unico(t, FIN, str(T)):
    i = t.index(INI)
    j = t.index(FIN) + len(FIN)
    bloque = t[i:j]
    if i >= j or "class IPSetWrapperTest" not in bloque or "generate_random_ips" not in bloque \
            or "#include <sstream>\n" not in bloque:
        errores.append(f"{T}: el bloque del fixture no tiene la forma esperada")
    else:
        bloque = bloque.replace("#include <sstream>\n",
                                "#include <sstream>\n#include <memory>\n#include <string>\n#include <vector>\n", 1)
        fixture_hpp = (
            "//===----------------------------------------------------------------------===//\n"
            "// ML Defender - Firewall ACL Agent\n"
            f"// ipset_wrapper_fixture.hpp - fixture IPSetWrapperTest compartido  {MARCA}\n"
            "// Movido tal cual desde test_ipset_wrapper.cpp para que lo usen los tests funcionales\n"
            "// (ipset_wrapper_tests, e2e;root) y los de rendimiento (ipset_wrapper_perf_tests, perf;root).\n"
            "// Requiere root: SetUp hace GTEST_SKIP sin root, y la puerta ctest_label_gate.sh FALLA si algo se salta.\n"
            "//===----------------------------------------------------------------------===//\n"
            "#pragma once\n\n" + bloque)
        t2 = t[:i] + ('#include "ipset_wrapper_fixture.hpp"  // ' + MARCA +
                      " fixture compartido con test_ipset_wrapper_perf.cpp\n") + t[j:]


# ---- 2. fuera los dos tests de rendimiento ----------------------------------------------------------
def cortar(texto, inicio, sentinela):
    if not unico(texto, inicio, str(T)):
        return texto
    a = texto.index(inicio)
    b = texto.find("\n}\n", a)
    if b < 0:
        errores.append(f"{T}: no encuentro el cierre de {inicio}")
        return texto
    b += 3
    if texto[b:b + 1] == "\n":
        b += 1
    trozo = texto[a:b]
    if sentinela not in trozo or trozo.count("TEST_F(") != 1:
        errores.append(f"{T}: el bloque de {inicio} no es el esperado")
        return texto
    return texto[:a] + texto[b:]


t2 = cortar(t2, "TEST_F(IPSetWrapperTest, BatchAddPerformance) {", "EXPECT_LT(duration_ms, 10)")
t2 = cortar(t2, "TEST_F(IPSetWrapperTest, TestPerformance) {", "EXPECT_LT(avg_us, 1)")
COM_OLD = "//   - Performance benchmarks (target: 1000 IPs in <10ms)\n"
if unico(t2, COM_OLD, str(T)):
    t2 = t2.replace(COM_OLD, "//   - Performance: en test_ipset_wrapper_perf.cpp (etiqueta perf) " + MARCA + "\n", 1)
n_tf = len(re.findall(r"^TEST_F\(IPSetWrapperTest,", t2, re.M))
if n_tf != 19:
    errores.append(f"{T}: tras el corte quedan {n_tf} TEST_F, se esperaban 19")

# ---- 3. test de rendimiento -------------------------------------------------------------------------
perf_cpp = r'''//===----------------------------------------------------------------------===//
// ML Defender - Firewall ACL Agent
// test_ipset_wrapper_perf.cpp - Medidas de rendimiento de IPSetWrapper   [ARGUS-GATE-PERF-D303]
//
// DAY303, decision de Alonso: estos tests dan NUMEROS del entorno donde corren (hoy, Vagrant/VirtualBox)
// y la medida tiene que ser coherente y correcta. NO fallan por tiempo: fallan solo si la medida no es
// valida (una operacion da error, el set no contiene lo esperado, una consulta responde al reves).
// Los umbrales se fijaran en hardware real, por instalacion (DEBT-FW-IPSET-PERF-TESTS-001).
//
// Que se mide: el camino real del wrapper, que lanza /sbin/ipset con fork+execv+waitpid (safe_exec).
//   - BatchAddRestore1000: add_batch de 1000 IPs = fichero temporal + UN proceso 'ipset restore -exist'.
//   - TestLookupForkExec:  test() = UN proceso 'ipset test' por consulta. NO es la consulta al hash del
//     kernel: aqui domina crear el proceso. test() devuelve bool: en una IP ausente un fallo del exec se
//     confundiria con "no esta"; las presentes, por el mismo camino, si lo detectan.
// Metodo: calentamiento descartado; cada muestra cronometrada sola con steady_clock; informe
// n/min/p50/p99/max/media en microsegundos (sin truncar) en lineas [PERF] y en RecordProperty (XML).
//
// Etiquetas ctest: perf;root.   make test-firewall-perf PROFILE=production
//===----------------------------------------------------------------------===//

#include "ipset_wrapper_fixture.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <string>
#include <unordered_set>
#include <vector>

namespace {

struct Resumen {
    size_t n = 0;
    double min_us = 0.0;
    double p50_us = 0.0;
    double p99_us = 0.0;
    double max_us = 0.0;
    double media_us = 0.0;
};

// Percentil por rango mas cercano (nearest-rank) sobre muestras ya ordenadas.
double percentil(const std::vector<double>& ordenadas, double p) {
    if (ordenadas.empty()) {
        return 0.0;
    }
    auto rango = static_cast<size_t>(std::ceil(p / 100.0 * static_cast<double>(ordenadas.size())));
    if (rango == 0) {
        rango = 1;
    }
    return ordenadas[rango - 1];
}

Resumen resumir(std::vector<double> muestras) {
    Resumen r;
    r.n = muestras.size();
    if (muestras.empty()) {
        return r;
    }
    std::sort(muestras.begin(), muestras.end());
    double suma = 0.0;
    for (double m : muestras) {
        suma += m;
    }
    r.min_us = muestras.front();
    r.max_us = muestras.back();
    r.p50_us = percentil(muestras, 50.0);
    r.p99_us = percentil(muestras, 99.0);
    r.media_us = suma / static_cast<double>(muestras.size());
    return r;
}

Resumen informar(const std::string& que, const std::string& clave,
                 const std::vector<double>& muestras, const std::string& nota) {
    const Resumen r = resumir(muestras);
    std::printf("[PERF] %s: n=%zu min=%.1f p50=%.1f p99=%.1f max=%.1f media=%.1f us | %s\n",
                que.c_str(), r.n, r.min_us, r.p50_us, r.p99_us, r.max_us, r.media_us, nota.c_str());
    std::fflush(stdout);
    ::testing::Test::RecordProperty(clave + "_n", std::to_string(r.n));
    ::testing::Test::RecordProperty(clave + "_min_us", std::to_string(r.min_us));
    ::testing::Test::RecordProperty(clave + "_p50_us", std::to_string(r.p50_us));
    ::testing::Test::RecordProperty(clave + "_p99_us", std::to_string(r.p99_us));
    ::testing::Test::RecordProperty(clave + "_max_us", std::to_string(r.max_us));
    ::testing::Test::RecordProperty(clave + "_media_us", std::to_string(r.media_us));
    return r;
}

double micros(steady_clock::duration d) {
    return duration<double, std::micro>(d).count();
}

}  // namespace

class IPSetWrapperPerfTest : public IPSetWrapperTest {};

//===----------------------------------------------------------------------===//
// add_batch de 1000 IPs: fichero temporal + un proceso 'ipset restore -exist'
//===----------------------------------------------------------------------===//
TEST_F(IPSetWrapperPerfTest, BatchAddRestore1000) {
    constexpr size_t N_IPS = 1000;
    constexpr size_t CALENTAMIENTO = 1;
    constexpr size_t MEDIDAS = 20;

    auto creado = wrapper_->create_set(make_blacklist_config(TEST_SET_NAME));
    ASSERT_TRUE(creado) << "create_set: " << creado.get_error().message;

    std::vector<double> muestras;
    muestras.reserve(MEDIDAS);
    for (size_t vuelta = 0; vuelta < CALENTAMIENTO + MEDIDAS; ++vuelta) {
        auto vaciado = wrapper_->flush_set(TEST_SET_NAME);
        ASSERT_TRUE(vaciado) << "flush_set, vuelta " << vuelta << ": " << vaciado.get_error().message;
        ASSERT_EQ(wrapper_->get_entry_count(TEST_SET_NAME), uint64_t{0})
            << "el set no quedo vacio antes de la vuelta " << vuelta;

        auto entradas = generate_random_ips(N_IPS);
        std::unordered_set<std::string> unicas;
        for (const auto& e : entradas) {
            unicas.insert(e.ip);
        }

        const auto t0 = steady_clock::now();
        auto resultado = wrapper_->add_batch(TEST_SET_NAME, entradas);
        const auto t1 = steady_clock::now();

        ASSERT_TRUE(resultado) << "add_batch, vuelta " << vuelta << ": " << resultado.get_error().message;
        ASSERT_EQ(wrapper_->get_entry_count(TEST_SET_NAME), static_cast<uint64_t>(unicas.size()))
            << "el set no contiene exactamente las IPs unicas del lote, vuelta " << vuelta;
        if (vuelta >= CALENTAMIENTO) {
            muestras.push_back(micros(t1 - t0));
        }
    }

    ASSERT_EQ(muestras.size(), MEDIDAS);
    const Resumen r = informar("add_batch 1000 IPs (fichero temporal + 1 proceso 'ipset restore -exist')",
                               "batch_add_1000", muestras,
                               "set vaciado antes de cada medida; 1 vuelta de calentamiento descartada");
    ASSERT_GT(r.min_us, 0.0) << "medida incoherente: duracion no positiva";
    std::printf("[PERF] add_batch 1000 IPs: %.0f IPs/s a p50\n", static_cast<double>(N_IPS) * 1e6 / r.p50_us);
    std::fflush(stdout);
}

//===----------------------------------------------------------------------===//
// test(): un proceso 'ipset test' por consulta, sobre un set de 10.000 IPs
//===----------------------------------------------------------------------===//
TEST_F(IPSetWrapperPerfTest, TestLookupForkExec) {
    constexpr size_t N_SET = 10000;
    constexpr size_t CALENTAMIENTO = 50;  // por tipo
    constexpr size_t CONSULTAS = 500;     // por tipo: 500 presentes + 500 ausentes

    auto creado = wrapper_->create_set(make_blacklist_config(TEST_SET_NAME));
    ASSERT_TRUE(creado) << "create_set: " << creado.get_error().message;

    auto entradas = generate_random_ips(N_SET);
    auto cargado = wrapper_->add_batch(TEST_SET_NAME, entradas);
    ASSERT_TRUE(cargado) << "add_batch de la carga: " << cargado.get_error().message;

    std::unordered_set<std::string> presentes;
    for (const auto& e : entradas) {
        presentes.insert(e.ip);
    }
    ASSERT_EQ(wrapper_->get_entry_count(TEST_SET_NAME), static_cast<uint64_t>(presentes.size()))
        << "la carga no dejo en el set las IPs unicas generadas";

    std::vector<std::string> lista_presentes(presentes.begin(), presentes.end());
    ASSERT_GE(lista_presentes.size(), CALENTAMIENTO + CONSULTAS);
    std::vector<std::string> ausentes;
    ausentes.reserve(CALENTAMIENTO + CONSULTAS);
    while (ausentes.size() < CALENTAMIENTO + CONSULTAS) {
        std::string ip = generate_random_ip();
        if (presentes.count(ip) == 0) {
            ausentes.push_back(std::move(ip));
        }
    }

    std::vector<double> m_presentes;
    std::vector<double> m_ausentes;
    std::vector<double> m_todas;
    size_t respuestas_erroneas = 0;
    for (size_t i = 0; i < CALENTAMIENTO + CONSULTAS; ++i) {
        for (int tipo = 0; tipo < 2; ++tipo) {
            const bool esperado = (tipo == 0);
            const std::string& ip = esperado ? lista_presentes[i] : ausentes[i];
            const auto t0 = steady_clock::now();
            const bool en_set = wrapper_->test(TEST_SET_NAME, ip);
            const auto t1 = steady_clock::now();
            if (en_set != esperado) {
                ++respuestas_erroneas;
                if (respuestas_erroneas <= 5) {
                    ADD_FAILURE() << "test(" << ip << ") devolvio " << en_set << ", se esperaba " << esperado;
                }
            }
            if (i >= CALENTAMIENTO) {
                const double us = micros(t1 - t0);
                (esperado ? m_presentes : m_ausentes).push_back(us);
                m_todas.push_back(us);
            }
        }
    }

    EXPECT_EQ(respuestas_erroneas, size_t{0}) << "medida invalida: consultas con respuesta incorrecta";
    const std::string nota = "set de " + std::to_string(presentes.size()) +
                             " IPs; 1 proceso 'ipset test' por consulta (fork+execv), NO el hash del kernel";
    const Resumen rp = informar("test() IP presente", "lookup_presente", m_presentes, nota);
    const Resumen ra = informar("test() IP ausente", "lookup_ausente", m_ausentes, nota);
    const Resumen rt = informar("test() todas", "lookup_todas", m_todas, nota);
    EXPECT_EQ(rp.n, CONSULTAS);
    EXPECT_EQ(ra.n, CONSULTAS);
    EXPECT_GT(rt.min_us, 0.0) << "medida incoherente: duracion no positiva";
}
'''

# ---- 4. puerta de ctest por etiqueta ----------------------------------------------------------------
gate_sh = r'''#!/usr/bin/env bash
# [ARGUS-GATE-PERF-D303] Puerta de ctest por etiqueta del firewall-acl-agent. Se ejecuta DENTRO del defender;
# la lanzan desde el Mac "make test-firewall-e2e" y "make test-firewall-perf" (PROFILE=production).
# FALLA (rc 1) si: ctest falla, no hay ningun test con la etiqueta, o aparece CUALQUIER test saltado
# (ctest "***Skipped" / "***Not Run" / "did not run", o gtest "[  SKIPPED ]"). Un saltado no es un pasado.
set -u
BUILD=${1:?uso: ctest_label_gate.sh BUILD_DIR ETIQUETA}
ETIQUETA=${2:?uso: ctest_label_gate.sh BUILD_DIR ETIQUETA}
LOG=/tmp/argus_ctest_${ETIQUETA}.log
cd "$BUILD" || { echo "[CTEST-GATE] FALLA: no existe $BUILD"; exit 1; }
echo "[CTEST-GATE] etiqueta=$ETIQUETA build=$BUILD log=$LOG"
sudo env LD_LIBRARY_PATH=/usr/local/lib ctest -L "$ETIQUETA" -V 2>&1 | tee "$LOG"
RC=${PIPESTATUS[0]}
TOTAL=$(LC_ALL=C awk '/tests failed out of/ {print $NF}' "$LOG" | tail -1)
SALT_CTEST=$(grep -c -E '\*\*\*(Skipped|Not Run)' "$LOG")
SALT_GTEST=$(grep -c -F '[  SKIPPED ]' "$LOG")
NO_RUN=$(grep -c -F 'did not run' "$LOG")
echo
echo "[CTEST-GATE] resumen etiqueta=$ETIQUETA rc_ctest=$RC tests=${TOTAL:-0} saltados_ctest=$SALT_CTEST saltados_gtest=$SALT_GTEST did_not_run=$NO_RUN"
if grep -q -F '[PERF]' "$LOG"; then
    echo "[CTEST-GATE] medidas:"
    grep -F '[PERF]' "$LOG" | sed 's/^[0-9]*: //'
fi
if [ "$RC" -ne 0 ] || [ -z "$TOTAL" ] || [ "$TOTAL" = "0" ] || [ "$SALT_CTEST" -ne 0 ] || [ "$SALT_GTEST" -ne 0 ] || [ "$NO_RUN" -ne 0 ]; then
    echo "[CTEST-GATE] FALLA ($ETIQUETA)"
    exit 1
fi
echo "[CTEST-GATE] PASA ($ETIQUETA): ${TOTAL} tests, 0 saltados"
'''

# ---- 5. CMake ----------------------------------------------------------------------------------------
cm2 = cm
pat_src = re.compile(r"^[ \t]*tests/unit/test_ipset_wrapper\.cpp[ \t]*\n", re.M)
if len(pat_src.findall(cm)) != 1:
    errores.append(f"{CM}: tests/unit/test_ipset_wrapper.cpp no aparece exactamente 1 vez")
else:
    cm2 = pat_src.sub("", cm2, count=1)
pat_gd = re.compile(r"^([ \t]*)gtest_discover_tests\(firewall_tests\)[ \t]*\n", re.M)
m = list(pat_gd.finditer(cm2))
if len(m) != 1:
    errores.append(f"{CM}: gtest_discover_tests(firewall_tests) no aparece exactamente 1 vez")
else:
    ind = m[0].group(1)
    bloque_cm = """
IND# MARCA IPSetWrapperTest fuera de firewall_tests: necesita root (ipset del kernel).
IND#   funcionales -> ipset_wrapper_tests       LABELS e2e;root  (make test-firewall-e2e; falla si algo se salta)
IND#   rendimiento -> ipset_wrapper_perf_tests  LABELS perf;root (make test-firewall-perf; mide, no falla por tiempo)
IND# test-components excluye root|perf: ningun Skipped por falta de root.
INDadd_executable(ipset_wrapper_tests
IND        tests/unit/test_ipset_wrapper.cpp
IND        tests/test_globals_stub.cpp
IND)
INDtarget_include_directories(ipset_wrapper_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src/core)
INDtarget_link_libraries(ipset_wrapper_tests PRIVATE firewall_core OpenSSL::Crypto GTest::gtest GTest::gtest_main)
INDgtest_discover_tests(ipset_wrapper_tests PROPERTIES LABELS "e2e;root")

INDadd_executable(ipset_wrapper_perf_tests
IND        tests/unit/test_ipset_wrapper_perf.cpp
IND        tests/test_globals_stub.cpp
IND)
INDtarget_include_directories(ipset_wrapper_perf_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src/core)
INDtarget_link_libraries(ipset_wrapper_perf_tests PRIVATE firewall_core OpenSSL::Crypto GTest::gtest GTest::gtest_main)
INDgtest_discover_tests(ipset_wrapper_perf_tests PROPERTIES LABELS "perf;root")
""".replace("IND", ind).replace("MARCA", MARCA)
    fin = m[0].end()
    cm2 = cm2[:fin] + bloque_cm + cm2[fin:]

# ---- 6. Makefile -------------------------------------------------------------------------------------
mk2 = mk
TC_OLD = 'cd $(FIREWALL_BUILD_DIR) && ctest --output-on-failure"'
TC_NEW = "cd $(FIREWALL_BUILD_DIR) && ctest -LE 'root|perf' --output-on-failure\""
if unico(mk2, TC_OLD, "Makefile (test-components)"):
    mk2 = mk2.replace(TC_OLD, TC_NEW, 1)
E2E_INI = "\ntest-firewall-e2e:\n"
E2E_FIN = "ctest -L \"e2e\" --output-on-failure'\n"
if unico(mk2, E2E_INI, "Makefile (test-firewall-e2e)"):
    a = mk2.index(E2E_INI) + 1
    b = mk2.find(E2E_FIN, a)
    if b < 0 or b - a > 600:
        errores.append("Makefile: no encuentro el final de la receta de test-firewall-e2e")
    else:
        b += len(E2E_FIN)
        nuevo = (
            "test-firewall-e2e:\n"
            "\t@echo \"🧪 firewall e2e (perfil=$(PROFILE), CON root): falla si algun test se salta  " + MARCA + "\"\n"
            "\t@vagrant ssh -c 'bash /vagrant/firewall-acl-agent/tests/ctest_label_gate.sh $(FIREWALL_BUILD_DIR) e2e'\n"
            "\n"
            ".PHONY: test-firewall-perf\n"
            "test-firewall-perf:\n"
            "\t@echo \"📏 firewall perf (perfil=$(PROFILE), CON root): mide y valida la medida; no falla por tiempo  " + MARCA + "\"\n"
            "\t@vagrant ssh -c 'bash /vagrant/firewall-acl-agent/tests/ctest_label_gate.sh $(FIREWALL_BUILD_DIR) perf'\n")
        mk2 = mk2[:a] + nuevo + mk2[b:]

# ---- informe / aplicacion ----------------------------------------------------------------------------
if errores:
    print("PARO: el patcher no toca nada.")
    for e in errores:
        print(" -", e)
    sys.exit(1)


def diff(p, viejo, nuevo):
    return "".join(difflib.unified_diff(viejo.splitlines(True), nuevo.splitlines(True),
                                        fromfile=f"a/{p}", tofile=f"b/{p}", n=2))


print(f"=== {MODO}: todas las anclas encontradas, 0 errores ===")
print(f"{T}: quedan {n_tf} TEST_F(IPSetWrapperTest,...)")
print(f"nuevos: {FIX} ({len(fixture_hpp.splitlines())} lineas), {PERF} ({len(perf_cpp.splitlines())} lineas), "
      f"{GATE} ({len(gate_sh.splitlines())} lineas)")
print(diff(CM, cm, cm2))
print(diff(MK, mk, mk2))
print(diff(T, t, t2))

if MODO == "--apply":
    FIX.write_text(fixture_hpp, encoding="utf-8")
    PERF.write_text(perf_cpp, encoding="utf-8")
    GATE.write_text(gate_sh, encoding="utf-8")
    GATE.chmod(0o755)
    T.write_text(t2, encoding="utf-8")
    CM.write_text(cm2, encoding="utf-8")
    MK.write_text(mk2, encoding="utf-8")
    print("APLICADO", MARCA)
