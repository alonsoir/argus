//===----------------------------------------------------------------------===//
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
// Etiqueta ctest: perf (necesita root).   make test-firewall-perf PROFILE=production   [ARGUS-GATE-PERF-D303-B]
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
