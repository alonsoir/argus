// test_batch_processor_recidivism.cpp — RECIDIVISM-D276 + DAY277-NEVER-PERMANENT
// Unit tests de compute_penalty_timeout / set_recidivism_config /
// dump_and_reset_strike_states. Sin root: IPSetWrapper en dry_run.
#include <gtest/gtest.h>
#include "firewall/batch_processor.hpp"
#include "firewall/ipset_wrapper.hpp"
#include <cstdio>
#include <fstream>
#include <optional>
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

bool file_exists(const std::string& path) {
    std::ifstream f(path);
    return f.good();
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
    cfg.max_penalty_after_strikes = 10;
    processor_->set_recidivism_config(cfg);

    EXPECT_EQ(processor_->compute_penalty_timeout("1.2.3.4"), std::optional<uint32_t>(60u));
}

TEST_F(RecidivismTest, EscalatesOnRepeatedStrikes) {
    RecidivismConfig cfg;
    cfg.strike_durations_sec = {60, 300, 3600};
    cfg.max_penalty_after_strikes = 10;
    cfg.quiet_period_reset = std::chrono::hours(999);
    processor_->set_recidivism_config(cfg);

    EXPECT_EQ(processor_->compute_penalty_timeout("1.2.3.4"), std::optional<uint32_t>(60u));
    EXPECT_EQ(processor_->compute_penalty_timeout("1.2.3.4"), std::optional<uint32_t>(300u));
    EXPECT_EQ(processor_->compute_penalty_timeout("1.2.3.4"), std::optional<uint32_t>(3600u));
    // Se queda en el ultimo escalon por debajo de max_penalty_after_strikes
    EXPECT_EQ(processor_->compute_penalty_timeout("1.2.3.4"), std::optional<uint32_t>(3600u));
}

TEST_F(RecidivismTest, DifferentIpsTrackedIndependently) {
    RecidivismConfig cfg;
    cfg.strike_durations_sec = {60, 300};
    processor_->set_recidivism_config(cfg);

    EXPECT_EQ(processor_->compute_penalty_timeout("1.1.1.1"), std::optional<uint32_t>(60u));
    EXPECT_EQ(processor_->compute_penalty_timeout("2.2.2.2"), std::optional<uint32_t>(60u));
    EXPECT_EQ(processor_->compute_penalty_timeout("1.1.1.1"), std::optional<uint32_t>(300u));
}

// DAY277: sustituye a PermanentAfterThreshold. El umbral da el castigo
// MAXIMO, nunca 0 (= permanente en ipset).
TEST_F(RecidivismTest, MaxPenaltyAfterThresholdIsNeverPermanent) {
    RecidivismConfig cfg;
    cfg.strike_durations_sec = {60};
    cfg.max_penalty_after_strikes = 3;
    cfg.max_penalty_sec = 7200;
    processor_->set_recidivism_config(cfg);

    EXPECT_EQ(processor_->compute_penalty_timeout("9.9.9.9"), std::optional<uint32_t>(60u));
    EXPECT_EQ(processor_->compute_penalty_timeout("9.9.9.9"), std::optional<uint32_t>(60u));
    auto t3 = processor_->compute_penalty_timeout("9.9.9.9");
    ASSERT_TRUE(t3.has_value());
    EXPECT_EQ(*t3, 7200u);
    // y sigue en el tope, nunca pasa a 0
    auto t4 = processor_->compute_penalty_timeout("9.9.9.9");
    ASSERT_TRUE(t4.has_value());
    EXPECT_EQ(*t4, 7200u);
}

// H4-D277: deshabilitado => nullopt (timeout por defecto del set), NO 0.
TEST_F(RecidivismTest, DisabledReturnsNulloptNotZero) {
    RecidivismConfig cfg;
    cfg.enabled = false;
    processor_->set_recidivism_config(cfg);

    EXPECT_FALSE(processor_->compute_penalty_timeout("5.5.5.5").has_value());
    EXPECT_FALSE(processor_->compute_penalty_timeout("5.5.5.5").has_value());
}

// H2-D277: con reincidencia deshabilitada, flush() NO debe meter nada en
// strike_states_. Observable: si el bug existiera, 3 flushes con
// max_tracked_ips=2 dejarian 3 entradas y la siguiente IP (ya habilitado)
// dispararia el volcado de overflow => existiria el fichero.
TEST_F(RecidivismTest, DisabledFlushDoesNotTrackIps) {
    const std::string overflow_path = "/tmp/test_recidivism_h2_overflow.log";
    std::remove(overflow_path.c_str());

    RecidivismConfig cfg;
    cfg.enabled = false;
    cfg.max_tracked_ips = 2;
    cfg.overflow_log_path = overflow_path;
    processor_->set_recidivism_config(cfg);

    // DAY277-H2-TEST-FIX: un flush fallido conserva pending_ips_ (medido), asi
    // que no se asume nada sobre su exito. El bucle de flush_internal (donde
    // vivia H2) recorre todas las IPs pendientes ANTES de llamar a add_batch.
    for (const char* ip : {"198.51.100.1", "198.51.100.2", "198.51.100.3"}) {
        processor_->add_ip(ip);
    }
    ASSERT_EQ(processor_->get_pending_count(), 3u)
        << "add_ip no encolo las 3 IPs -- el test no estaria probando nada";
    processor_->flush();

    cfg.enabled = true;
    processor_->set_recidivism_config(cfg);
    processor_->compute_penalty_timeout("198.51.100.4");

    EXPECT_FALSE(file_exists(overflow_path))
        << "flush() con enabled=false inserto IPs en strike_states_ (H2)";
    std::remove(overflow_path.c_str());
}

// Validacion: 0 en cualquier duracion => nunca permanente.
TEST_F(RecidivismTest, SanitizeZeroValuesNeverPermanent) {
    RecidivismConfig cfg;
    cfg.strike_durations_sec = {0, 0};
    cfg.max_penalty_sec = 0;
    cfg.max_penalty_after_strikes = 10;
    processor_->set_recidivism_config(cfg);

    auto t = processor_->compute_penalty_timeout("7.7.7.7");
    ASSERT_TRUE(t.has_value());
    EXPECT_GT(*t, 0u);
    EXPECT_LE(*t, kIpsetMaxTimeoutSec);
}

// Validacion: por encima del techo medido del kernel => se recorta al techo.
TEST_F(RecidivismTest, SanitizeClampsToKernelMax) {
    RecidivismConfig cfg;
    cfg.strike_durations_sec = {3000000};
    cfg.max_penalty_sec = 3000000;
    cfg.max_penalty_after_strikes = 10;
    processor_->set_recidivism_config(cfg);

    EXPECT_EQ(processor_->compute_penalty_timeout("8.8.4.4"),
              std::optional<uint32_t>(kIpsetMaxTimeoutSec));
}

// H5-D277: escalera vacia no debe provocar acceso fuera de rango.
TEST_F(RecidivismTest, EmptyDurationsDoesNotCrash) {
    RecidivismConfig cfg;
    cfg.strike_durations_sec = {};
    cfg.max_penalty_after_strikes = 10;
    processor_->set_recidivism_config(cfg);

    auto t = processor_->compute_penalty_timeout("6.6.6.6");
    ASSERT_TRUE(t.has_value());
    EXPECT_GT(*t, 0u);
}

// DAY277-H6: reintentos de un flush fallido NO suman strikes.
// En dry_run el set no existe -> add_batch devuelve SET_NOT_FOUND (medido en
// ipset_wrapper.cpp: set_exists_unlocked va antes del dry_run) -> flush falla
// y la IP sigue pendiente. Con el bug: 5 flushes = 5 strikes -> siguiente = 3600.
TEST_F(RecidivismTest, FailedFlushRetriesDoNotInflateStrikes) {
    RecidivismConfig cfg;
    cfg.strike_durations_sec = {60, 300, 3600};
    cfg.max_penalty_after_strikes = 10;
    cfg.quiet_period_reset = std::chrono::hours(999);
    processor_->set_recidivism_config(cfg);

    processor_->add_ip("198.51.100.77");
    for (int i = 0; i < 5; ++i) {
        processor_->flush();
    }
    ASSERT_EQ(processor_->get_pending_count(), 1u)
        << "el flush no fallo: el test no reproduce el reintento";

    // Una deteccion = un strike. La siguiente llamada debe ser el strike 2.
    EXPECT_EQ(processor_->compute_penalty_timeout("198.51.100.77"),
              std::optional<uint32_t>(300u));
}

TEST_F(RecidivismTest, OverflowDumpsToFileAndResets) {
    const std::string overflow_path = "/tmp/test_recidivism_overflow.log";
    std::remove(overflow_path.c_str());

    RecidivismConfig cfg;
    cfg.strike_durations_sec = {60, 300};
    cfg.max_tracked_ips = 2;
    cfg.overflow_log_path = overflow_path;
    processor_->set_recidivism_config(cfg);

    processor_->compute_penalty_timeout("10.0.0.1");
    processor_->compute_penalty_timeout("10.0.0.2");
    EXPECT_EQ(processor_->compute_penalty_timeout("10.0.0.3"), std::optional<uint32_t>(60u));

    std::string dumped = read_file(overflow_path);
    EXPECT_NE(dumped.find("10.0.0.1"), std::string::npos);
    EXPECT_NE(dumped.find("10.0.0.2"), std::string::npos);

    EXPECT_EQ(processor_->compute_penalty_timeout("10.0.0.1"), std::optional<uint32_t>(60u));

    std::remove(overflow_path.c_str());
}

TEST_F(RecidivismTest, OverflowDoesNotResetIfDumpFails) {
    RecidivismConfig cfg;
    cfg.strike_durations_sec = {60, 300};
    cfg.max_tracked_ips = 2;
    cfg.overflow_log_path = "/ruta/que/no/existe/overflow.log";
    processor_->set_recidivism_config(cfg);

    processor_->compute_penalty_timeout("10.0.0.1");
    processor_->compute_penalty_timeout("10.0.0.2");
    processor_->compute_penalty_timeout("10.0.0.3");
    EXPECT_EQ(processor_->compute_penalty_timeout("10.0.0.1"), std::optional<uint32_t>(300u));
}
