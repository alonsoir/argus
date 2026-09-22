// test_batch_processor_recidivism.cpp — RECIDIVISM-D276
// Unit tests de compute_penalty_timeout / dump_and_reset_strike_states.
// Logica pura sobre BatchProcessor: no se llama a flush()/add_batch(), no
// se toca el kernel ni hace falta root (IPSetWrapper en dry_run).
#include <gtest/gtest.h>
#include "firewall/batch_processor.hpp"
#include "firewall/ipset_wrapper.hpp"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

using namespace mldefender::firewall;

namespace {

std::string read_file(const std::string& path) {
    std::ifstream in(path);
    std::stringstream ss;
    ss << in.rdbuf();
    return ss.str();
}

}  // namespace

class RecidivismTest : public ::testing::Test {
protected:
    void SetUp() override {
        ipset_ = std::make_unique<IPSetWrapper>();
        ipset_->set_dry_run(true);  // nunca tocamos el kernel en estos tests
        processor_ = std::make_unique<BatchProcessor>(*ipset_);
    }

    std::unique_ptr<IPSetWrapper> ipset_;
    std::unique_ptr<BatchProcessor> processor_;
};

TEST_F(RecidivismTest, FirstStrikeUsesFirstDuration) {
    RecidivismConfig cfg;
    cfg.strike_durations_sec = {60, 300, 3600};
    cfg.permanent_after_strikes = 10;
    processor_->set_recidivism_config(cfg);

    EXPECT_EQ(processor_->compute_penalty_timeout("1.2.3.4"), 60u);
}

TEST_F(RecidivismTest, EscalatesOnRepeatedStrikes) {
    RecidivismConfig cfg;
    cfg.strike_durations_sec = {60, 300, 3600};
    cfg.permanent_after_strikes = 10;
    cfg.quiet_period_reset = std::chrono::hours(999);  // no interfiere en este test
    processor_->set_recidivism_config(cfg);

    EXPECT_EQ(processor_->compute_penalty_timeout("1.2.3.4"), 60u);    // 1a vez
    EXPECT_EQ(processor_->compute_penalty_timeout("1.2.3.4"), 300u);   // 2a vez
    EXPECT_EQ(processor_->compute_penalty_timeout("1.2.3.4"), 3600u);  // 3a vez
    // Se queda en la ultima duracion configurada si sigue reincidiendo
    // por debajo de permanent_after_strikes
    EXPECT_EQ(processor_->compute_penalty_timeout("1.2.3.4"), 3600u);  // 4a vez
}

TEST_F(RecidivismTest, DifferentIpsTrackedIndependently) {
    RecidivismConfig cfg;
    cfg.strike_durations_sec = {60, 300};
    processor_->set_recidivism_config(cfg);

    EXPECT_EQ(processor_->compute_penalty_timeout("1.1.1.1"), 60u);
    EXPECT_EQ(processor_->compute_penalty_timeout("2.2.2.2"), 60u);   // no hereda reincidencia de 1.1.1.1
    EXPECT_EQ(processor_->compute_penalty_timeout("1.1.1.1"), 300u);  // 1.1.1.1 si escala
}

TEST_F(RecidivismTest, PermanentAfterThreshold) {
    RecidivismConfig cfg;
    cfg.strike_durations_sec = {60};
    cfg.permanent_after_strikes = 3;
    processor_->set_recidivism_config(cfg);

    EXPECT_EQ(processor_->compute_penalty_timeout("9.9.9.9"), 60u);  // strike 1
    EXPECT_EQ(processor_->compute_penalty_timeout("9.9.9.9"), 60u);  // strike 2
    EXPECT_EQ(processor_->compute_penalty_timeout("9.9.9.9"), 0u);   // strike 3 = permanente
}

TEST_F(RecidivismTest, DisabledReturnsDefaultTimeout) {
    RecidivismConfig cfg;
    cfg.enabled = false;
    processor_->set_recidivism_config(cfg);

    EXPECT_EQ(processor_->compute_penalty_timeout("5.5.5.5"), 0u);
    EXPECT_EQ(processor_->compute_penalty_timeout("5.5.5.5"), 0u);  // nunca escala si esta deshabilitado
}

TEST_F(RecidivismTest, OverflowDumpsToFileAndResets) {
    const std::string overflow_path = "/tmp/test_recidivism_overflow.log";
    std::remove(overflow_path.c_str());

    RecidivismConfig cfg;
    cfg.strike_durations_sec = {60, 300};
    cfg.max_tracked_ips = 2;  // fuerza el overflow con pocas IPs
    cfg.overflow_log_path = overflow_path;
    processor_->set_recidivism_config(cfg);

    processor_->compute_penalty_timeout("10.0.0.1");
    processor_->compute_penalty_timeout("10.0.0.2");
    // La 3a IP distinta dispara el overflow: dump + reset ANTES de contarla
    EXPECT_EQ(processor_->compute_penalty_timeout("10.0.0.3"), 60u);  // trata a 10.0.0.3 como 1a vez

    std::string dumped = read_file(overflow_path);
    EXPECT_NE(dumped.find("10.0.0.1"), std::string::npos);
    EXPECT_NE(dumped.find("10.0.0.2"), std::string::npos);

    // Tras el reset, 10.0.0.1 vuelve a contar como 1a vez: el contador en
    // memoria se reinicio, pero la evidencia quedo en el fichero de volcado.
    EXPECT_EQ(processor_->compute_penalty_timeout("10.0.0.1"), 60u);

    std::remove(overflow_path.c_str());
}

TEST_F(RecidivismTest, OverflowDoesNotResetIfDumpFails) {
    RecidivismConfig cfg;
    cfg.strike_durations_sec = {60, 300};
    cfg.max_tracked_ips = 2;
    // Ruta invalida (directorio inexistente): el volcado debe fallar
    cfg.overflow_log_path = "/ruta/que/no/existe/overflow.log";
    processor_->set_recidivism_config(cfg);

    processor_->compute_penalty_timeout("10.0.0.1");
    processor_->compute_penalty_timeout("10.0.0.2");
    // La 3a IP dispara el intento de overflow, que FALLA al escribir.
    // Contrato: si el volcado falla, NO se resetea. Lo verificamos
    // indirectamente: si 10.0.0.1 hubiera sido reseteada, volveria a dar 60
    // en vez de escalar a 300.
    processor_->compute_penalty_timeout("10.0.0.3");
    EXPECT_EQ(processor_->compute_penalty_timeout("10.0.0.1"), 300u);
}
