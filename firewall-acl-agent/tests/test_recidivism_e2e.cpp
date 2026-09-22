// test_recidivism_e2e.cpp — RECIDIVISM-D276
// Test de ACEPTACION: requiere root (manipula un ipset real del kernel).
// No usa el ipset de produccion "blacklist" -- crea uno propio de prueba
// y lo destruye al final, para no interferir con nada mas.
//
// Que verifica, de extremo a extremo, sin mocks:
//   1) BatchProcessor::flush() escribe de verdad en el ipset del kernel.
//   2) El timeout de la entrada escala segun strike_durations_sec cuando
//      la misma IP reincide en flushes sucesivos.
//   3) Al superar permanent_after_strikes, la entrada queda sin timeout
//      (bloqueo permanente).
//
// Ejecucion (ver Makefile raiz): `make test-firewall-e2e` (usa
// `sudo ... ctest -L "e2e"`), o directamente como root:
//   sudo ./firewall-acl-agent/build-debug/test_recidivism_e2e
#include <gtest/gtest.h>
#include "firewall/batch_processor.hpp"
#include "firewall/ipset_wrapper.hpp"
#include <array>
#include <cstdio>
#include <cstdlib>  // std::system
#include <memory>
#include <regex>
#include <sstream>
#include <string>
#include <thread>
#include <chrono>
#include <unistd.h>  // getuid

using namespace mldefender::firewall;

namespace {

// Lanza un comando y devuelve su stdout. No usar con entrada no confiable
// -- aqui el unico dato interpolado es TEST_SET_NAME, fijo y controlado
// por este fichero.
std::string shell(const std::string& cmd) {
    std::array<char, 256> buf{};
    std::string out;
    FILE* pipe = popen(cmd.c_str(), "r");
    if (!pipe) return out;
    while (fgets(buf.data(), buf.size(), pipe) != nullptr) {
        out += buf.data();
    }
    pclose(pipe);
    return out;
}

// Busca "ip timeout N" en la salida de `ipset list` y devuelve N, o -1 si
// la ip no aparece (por ejemplo, si quedo con timeout 0 == permanente,
// `ipset list` no imprime "timeout" en absoluto para esa entrada).
int extract_timeout(const std::string& ipset_list_output, const std::string& ip) {
    std::regex re(ip + R"(\s+timeout\s+(\d+))");
    std::smatch m;
    if (std::regex_search(ipset_list_output, m, re)) {
        return std::stoi(m[1].str());
    }
    return -1;
}

bool entry_present(const std::string& ipset_list_output, const std::string& ip) {
    return ipset_list_output.find(ip) != std::string::npos;
}

constexpr const char* TEST_SET_NAME = "argus_test_recidivism_e2e";

}  // namespace

class RecidivismE2ETest : public ::testing::Test {
protected:
    void SetUp() override {
        if (getuid() != 0) {
            GTEST_SKIP() << "requiere root (manipula ipset real) -- "
                            "ejecutar via 'make test-firewall-e2e'";
        }
        // -exist: no falla si ya existiera de una corrida anterior mal
        // terminada. timeout 0 en la definicion del set = por defecto
        // permanente; cada entrada individual lleva su propio timeout.
        shell(std::string("ipset destroy ") + TEST_SET_NAME + " 2>/dev/null");
        int rc = std::system(
            (std::string("ipset create ") + TEST_SET_NAME +
             " hash:ip timeout 0 comment 2>&1").c_str());
        ASSERT_EQ(rc, 0) << "no se pudo crear el ipset de prueba "
                          << TEST_SET_NAME
                          << " -- ¿ipset instalado? ¿de verdad estamos "
                             "corriendo como root?";

        ipset_ = std::make_unique<IPSetWrapper>();
        // dry_run=false a proposito: este es el unico test del feature
        // que debe tocar el kernel de verdad -- el unitario (dry_run) ya
        // cubre la logica pura de compute_penalty_timeout.
        ipset_->set_dry_run(false);

        BatchProcessorConfig cfg;
        cfg.batch_size_threshold = 1;   // flush inmediato, 1 ip por batch
        cfg.max_pending_ips = 10;
        cfg.confidence_threshold = 0.0f;
        cfg.blacklist_ipset = TEST_SET_NAME;
        processor_ = std::make_unique<BatchProcessor>(*ipset_, cfg);

        RecidivismConfig rcfg;
        rcfg.enabled = true;
        rcfg.strike_durations_sec = {5, 10, 20};
        rcfg.permanent_after_strikes = 4;
        rcfg.quiet_period_reset = std::chrono::hours(999);  // no interfiere
        rcfg.max_tracked_ips = 1000;
        rcfg.overflow_log_path = "/tmp/argus_test_recidivism_e2e_overflow.log";
        processor_->set_recidivism_config(rcfg);
    }

    void TearDown() override {
        if (getuid() != 0) return;  // nada que limpiar si se hizo SKIP
        processor_.reset();
        ipset_.reset();
        shell(std::string("ipset destroy ") + TEST_SET_NAME + " 2>/dev/null");
    }

    std::string list_set() {
        return shell(std::string("ipset list ") + TEST_SET_NAME + " 2>&1");
    }

    std::unique_ptr<IPSetWrapper> ipset_;
    std::unique_ptr<BatchProcessor> processor_;
};

TEST_F(RecidivismE2ETest, FirstFlushAppliesFirstStrikeDuration) {
    const std::string ip = "203.0.113.11";
    processor_->add_ip(ip);
    processor_->flush();

    auto listing = list_set();
    ASSERT_TRUE(entry_present(listing, ip)) << listing;
    int timeout = extract_timeout(listing, ip);
    ASSERT_GT(timeout, 0);
    // strike 1 = 5s de configuracion; damos margen porque el timeout ya
    // esta contando hacia atras desde que se aplico.
    EXPECT_LE(timeout, 5);
    EXPECT_GE(timeout, 1);
}

TEST_F(RecidivismE2ETest, RepeatedOffenderEscalatesRealTimeout) {
    const std::string ip = "203.0.113.22";

    processor_->add_ip(ip);
    processor_->flush();
    auto after_strike1 = list_set();
    int t1 = extract_timeout(after_strike1, ip);
    ASSERT_GT(t1, 0) << after_strike1;

    processor_->add_ip(ip);
    processor_->flush();
    auto after_strike2 = list_set();
    int t2 = extract_timeout(after_strike2, ip);
    ASSERT_GT(t2, 0) << after_strike2;

    // strike 2 (10s) debe ser un castigo mayor que strike 1 (5s), aun con
    // el descuento normal del contador. Verificamos la escalada real en
    // el kernel, no solo en la funcion pura (eso ya lo hace el unitario).
    EXPECT_GT(t2, t1);
}

TEST_F(RecidivismE2ETest, PermanentAfterThresholdHasNoTimeoutInKernel) {
    const std::string ip = "203.0.113.33";

    for (int i = 0; i < 4; ++i) {
        processor_->add_ip(ip);
        processor_->flush();
    }

    auto listing = list_set();
    ASSERT_TRUE(entry_present(listing, ip)) << listing;
    // strike 4 == permanent_after_strikes: compute_penalty_timeout
    // devuelve 0. En un set con soporte de timeout, ipset SI imprime
    // "timeout 0" para esa entrada -- 0 es como el kernel representa
    // "sin expiracion" (permanente), no la ausencia del campo.
    EXPECT_EQ(extract_timeout(listing, ip), 0) << listing;
}
