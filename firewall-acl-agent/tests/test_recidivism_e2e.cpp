// test_recidivism_e2e.cpp — RECIDIVISM-D276 + DAY277-NEVER-PERMANENT
// Test de ACEPTACION: requiere root (manipula un ipset real del kernel).
// No usa el ipset de produccion "blacklist" -- crea uno propio de prueba
// y lo destruye al final, para no interferir con nada mas.
//
// Que verifica, de extremo a extremo, sin mocks:
//   1) BatchProcessor::flush() escribe de verdad en el ipset del kernel.
//   2) El timeout de la entrada escala segun strike_durations_sec cuando
//      la misma IP reincide en flushes sucesivos.
//   3) Al alcanzar max_penalty_after_strikes, la entrada lleva max_penalty_sec:
//      NUNCA timeout 0 (= permanente). Decision DAY277.
//   4) Con la reincidencia deshabilitada se aplica el timeout por defecto
//      del set (regresion H4 de D276: antes quedaba permanente).
//
// Ejecucion: `make test-firewall-e2e`, o como root:
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

// Devuelve N de "ip timeout N" en `ipset list`, o -1 si no aparece.
// (Medido DAY276: en un set con timeout, una entrada permanente se imprime
// como "timeout 0", asi que 0 aqui significa PERMANENTE.)
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
// DAY277: timeout por defecto del set de prueba != 0, para que ninguna
// entrada pueda quedar permanente "por accidente" via el default del set.
constexpr int TEST_SET_DEFAULT_TIMEOUT = 600;

}  // namespace

class RecidivismE2ETest : public ::testing::Test {
protected:
    void SetUp() override {
        if (getuid() != 0) {
            GTEST_SKIP() << "requiere root (manipula ipset real) -- "
                            "ejecutar via 'make test-firewall-e2e'";
        }
        shell(std::string("ipset destroy ") + TEST_SET_NAME + " 2>/dev/null");
        int rc = std::system(
            (std::string("ipset create ") + TEST_SET_NAME +
             " hash:ip timeout " + std::to_string(TEST_SET_DEFAULT_TIMEOUT) +
             " comment 2>&1").c_str());
        ASSERT_EQ(rc, 0) << "no se pudo crear el ipset de prueba "
                          << TEST_SET_NAME
                          << " -- ¿ipset instalado? ¿de verdad estamos "
                             "corriendo como root?";

        ipset_ = std::make_unique<IPSetWrapper>();
        ipset_->set_dry_run(false);

        BatchProcessorConfig cfg;
        cfg.batch_size_threshold = 1;
        cfg.max_pending_ips = 10;
        cfg.confidence_threshold = 0.0f;
        cfg.blacklist_ipset = TEST_SET_NAME;
        processor_ = std::make_unique<BatchProcessor>(*ipset_, cfg);

        rcfg_.enabled = true;
        rcfg_.strike_durations_sec = {5, 10, 20};
        rcfg_.max_penalty_after_strikes = 4;
        rcfg_.max_penalty_sec = 30;
        rcfg_.quiet_period_reset = std::chrono::hours(999);
        rcfg_.max_tracked_ips = 1000;
        rcfg_.overflow_log_path = "/tmp/argus_test_recidivism_e2e_overflow.log";
        processor_->set_recidivism_config(rcfg_);
    }

    void TearDown() override {
        if (getuid() != 0) return;
        processor_.reset();
        ipset_.reset();
        shell(std::string("ipset destroy ") + TEST_SET_NAME + " 2>/dev/null");
    }

    std::string list_set() {
        return shell(std::string("ipset list ") + TEST_SET_NAME + " 2>&1");
    }

    RecidivismConfig rcfg_;
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

    EXPECT_GT(t2, t1);
}

// DAY277: sustituye a PermanentAfterThresholdHasNoTimeoutInKernel.
TEST_F(RecidivismE2ETest, CappedAfterThresholdNeverPermanentInKernel) {
    const std::string ip = "203.0.113.33";

    for (int i = 0; i < 4; ++i) {
        processor_->add_ip(ip);
        processor_->flush();
    }

    auto listing = list_set();
    ASSERT_TRUE(entry_present(listing, ip)) << listing;
    int t = extract_timeout(listing, ip);
    EXPECT_GT(t, 0) << "timeout 0 en el kernel = PERMANENTE (prohibido DAY277)\n" << listing;
    EXPECT_LE(t, 30) << listing;   // max_penalty_sec
    EXPECT_GT(t, 20) << listing;   // por encima del ultimo escalon (20): es el tope, no el escalon
}

// DAY277 / H4: con la reincidencia deshabilitada, la entrada lleva el timeout
// por defecto del set. Con el bug de D276 aparecia "timeout 0" (permanente).
TEST_F(RecidivismE2ETest, DisabledUsesSetDefaultTimeoutNotPermanent) {
    rcfg_.enabled = false;
    processor_->set_recidivism_config(rcfg_);

    const std::string ip = "203.0.113.44";
    processor_->add_ip(ip);
    processor_->flush();

    auto listing = list_set();
    ASSERT_TRUE(entry_present(listing, ip)) << listing;
    int t = extract_timeout(listing, ip);
    EXPECT_GT(t, 0) << "H4: enabled=false dejo la IP PERMANENTE\n" << listing;
    EXPECT_LE(t, TEST_SET_DEFAULT_TIMEOUT) << listing;
}
