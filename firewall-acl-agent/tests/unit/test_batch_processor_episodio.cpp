// [DDOS-MITIGACION-B2-D302] DAY302 tanda b2-1: API por episodio de BatchProcessor.
// Todo en dry_run (sin root ni kernel). Un episodio = un strike; RENOVAR = escalon vigente sin strike y
// refresca last_seen; barrera de protegidos a la entrada y en el flush; latido flush_si_toca.
#include <gtest/gtest.h>
#include <chrono>
#include <memory>
#include <sstream>
#include <thread>
#include "firewall/batch_processor.hpp"
#include "firewall/ipset_wrapper.hpp"
#include "firewall/ddos_protegidos.hpp"

using namespace mldefender::firewall;
using Estado = ResultadoEpisodio::Estado;

namespace {
RecidivismConfig escalera_prueba() {
    RecidivismConfig cfg;
    cfg.strike_durations_sec = {60, 300, 3600};
    cfg.max_penalty_after_strikes = 10;
    cfg.quiet_period_reset = std::chrono::hours(999);
    return cfg;
}

RangosProtegidos intranet_lab() {
    std::ostringstream log;
    return construir_rangos_protegidos({}, {"192.168.100.0/24"}, {}, log);
}
}  // namespace

class EpisodioTest : public ::testing::Test {
protected:
    void SetUp() override { crear(BatchProcessorConfig{}); }
    void crear(const BatchProcessorConfig& bc) {
        processor_.reset();
        ipset_ = std::make_unique<IPSetWrapper>();
        ipset_->set_dry_run(true);  // nunca tocamos el kernel en estos tests
        processor_ = std::make_unique<BatchProcessor>(*ipset_, bc);
        processor_->set_recidivism_config(escalera_prueba());
    }
    std::unique_ptr<IPSetWrapper> ipset_;
    std::unique_ptr<BatchProcessor> processor_;
};

TEST_F(EpisodioTest, BloquearSumaUnStrikeYRenovarNo) {
    auto r = processor_->bloquear_episodio("198.51.100.50");
    EXPECT_EQ(r.estado, Estado::ENCOLADO);
    EXPECT_EQ(r.timeout_sec, std::optional<uint32_t>(60u));
    EXPECT_EQ(r.strikes, 1u);
    for (int i = 0; i < 3; ++i) {
        auto rr = processor_->renovar_episodio("198.51.100.50");
        EXPECT_EQ(rr.estado, Estado::ENCOLADO);
        EXPECT_EQ(rr.timeout_sec, std::optional<uint32_t>(60u)) << "RENOVAR no debe subir de escalon";
        EXPECT_EQ(rr.strikes, 1u) << "RENOVAR no debe sumar strike";
    }
    auto r2 = processor_->bloquear_episodio("198.51.100.50");  // episodio nuevo
    EXPECT_EQ(r2.timeout_sec, std::optional<uint32_t>(300u));
    EXPECT_EQ(r2.strikes, 2u);
    auto r3 = processor_->renovar_episodio("198.51.100.50");
    EXPECT_EQ(r3.timeout_sec, std::optional<uint32_t>(300u));
    EXPECT_EQ(r3.strikes, 2u);
}

TEST_F(EpisodioTest, RenovarSinEstadoUsaPrimerEscalonSinStrike) {
    auto r = processor_->renovar_episodio("198.51.100.9");  // desborde de max_origenes: nunca bloqueado
    EXPECT_EQ(r.estado, Estado::ENCOLADO);
    EXPECT_EQ(r.timeout_sec, std::optional<uint32_t>(60u));
    EXPECT_EQ(r.strikes, 0u);
    auto r2 = processor_->bloquear_episodio("198.51.100.9");
    EXPECT_EQ(r2.timeout_sec, std::optional<uint32_t>(60u));
    EXPECT_EQ(r2.strikes, 1u);
}

TEST_F(EpisodioTest, BarreraProtegidosALaEntrada) {
    processor_->set_rangos_protegidos(intranet_lab());
    auto r = processor_->bloquear_episodio("192.168.100.61");
    EXPECT_EQ(r.estado, Estado::PROTEGIDO);
    EXPECT_FALSE(r.timeout_sec.has_value());
    EXPECT_EQ(r.strikes, 0u);
    auto r2 = processor_->renovar_episodio("192.168.100.61");
    EXPECT_EQ(r2.estado, Estado::PROTEGIDO);
    EXPECT_EQ(processor_->rechazos_protegidos(), 2u);
    EXPECT_EQ(processor_->get_pending_count(), 0u) << "un protegido entro en la cola";
    auto r3 = processor_->bloquear_episodio("198.51.100.50");  // el atacante externo si entra
    EXPECT_EQ(r3.estado, Estado::ENCOLADO);
    EXPECT_EQ(r3.timeout_sec, std::optional<uint32_t>(60u));
}

TEST_F(EpisodioTest, IpInvalidaNoEntra) {
    auto r = processor_->bloquear_episodio("no-es-una-ip");
    EXPECT_EQ(r.estado, Estado::IP_INVALIDA);
    EXPECT_FALSE(r.timeout_sec.has_value());
    EXPECT_EQ(processor_->get_pending_count(), 0u);
}

TEST_F(EpisodioTest, BarreraEnElFlushCaminoViejo) {
    processor_->set_rangos_protegidos(intranet_lab());
    processor_->add_ip("192.168.100.61");  // camino viejo, sin barrera a la entrada
    processor_->add_ip("198.51.100.50");
    processor_->flush();
    EXPECT_EQ(processor_->get_pending_count(), 0u);
    EXPECT_EQ(processor_->rechazos_protegidos(), 1u) << "la 2.a puerta no paro al protegido";
}

TEST_F(EpisodioTest, DryRunFlushVaciaLaCola) {
    processor_->add_ip("198.51.100.20");
    processor_->flush();
    EXPECT_EQ(processor_->get_pending_count(), 0u)
        << "en dry_run el flush debe tener exito sin kernel ([DRYRUN-ADD-BATCH-D302])";
}

TEST_F(EpisodioTest, RenovarActualizaLastSeen) {
    auto cfg = escalera_prueba();
    cfg.quiet_period_reset = std::chrono::seconds(2);
    processor_->set_recidivism_config(cfg);
    EXPECT_EQ(processor_->bloquear_episodio("198.51.100.60").strikes, 1u);
    std::this_thread::sleep_for(std::chrono::milliseconds(1300));
    auto rr = processor_->renovar_episodio("198.51.100.60");
    EXPECT_EQ(rr.strikes, 1u);
    std::this_thread::sleep_for(std::chrono::milliseconds(1300));
    // 2,6 s desde el BLOQUEAR (> calma de 2 s) pero 1,3 s desde el RENOVAR: sin refresco seria escalon 0.
    auto r2 = processor_->bloquear_episodio("198.51.100.60");
    EXPECT_EQ(r2.strikes, 2u) << "RENOVAR no refresco last_seen: la calma conto desde el BLOQUEAR";
    EXPECT_EQ(r2.timeout_sec, std::optional<uint32_t>(300u));
}

TEST_F(EpisodioTest, FlushSiTocaPorTiempo) {
    BatchProcessorConfig bc;
    bc.batch_size_threshold = 1000;
    bc.batch_time_threshold = std::chrono::milliseconds(500);
    crear(bc);
    EXPECT_EQ(processor_->flush_si_toca(), 0u) << "cola vacia: no debe hacer nada";
    processor_->bloquear_episodio("198.51.100.30");
    ASSERT_EQ(processor_->get_pending_count(), 1u) << "se vacio antes de tiempo";
    std::this_thread::sleep_for(std::chrono::milliseconds(600));
    processor_->flush_si_toca();
    EXPECT_EQ(processor_->get_pending_count(), 0u) << "el latido no vacio la cola vencido el plazo";
}
