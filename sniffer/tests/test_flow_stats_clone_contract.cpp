// ============================================================================
// test_flow_stats_clone_contract.cpp — DAY 219
// DEBT-FLOWSTATS-COPY-AMPUTATED-001  (P0, PRE-FEDER)
// ============================================================================
// get_flow_stats_copy() (sharded_flow_manager.cpp:96) copia 26 de los 28
// campos de FlowStatistics, A MANO, en una lista escrita el dia que se
// escribio. Los 2 que faltan:
//
//     fwd_payload_lengths   (flow_manager.hpp:32)  — anadido DAY 218
//     time_windows          (flow_manager.hpp:62)  — unique_ptr, NUNCA copiado
//                            "// time_windows will be created by FlowStatistics()
//                             constructor"  ← sharded_flow_manager.cpp:145
//
// Y la ruta de PRODUCCION come de esa copia:
//     ring_consumer.cpp:809  get_flow_stats_copy(flow_key)
//     ring_consumer.cpp:817  populate_ml_defender_features(flow_stats, ...)
//
// LAS 5 FEATURES ROTAS DE L1 SON EXACTAMENTE LAS 5 QUE DEPENDEN DE ESOS 2 CAMPOS:
//
//     L1[ 1] Subflow Fwd Bytes      -> time_windows          (feature_extractor.cpp:334)
//     L1[ 8] act_data_pkt_fwd       -> fwd_payload_lengths
//     L1[12] Subflow Bwd Bytes      -> time_windows          (feature_extractor.cpp:344)
//     L1[14] Init_Win_bytes_forward -> time_windows          (feature_extractor.cpp:379)
//     L1[15] Subflow Fwd Packets    -> time_windows          (feature_extractor.cpp:329)
//
// No es correlacion. Es la causa. El "hardcodeo" del extractor fue el APANO
// ante unos ceros que nadie rastreo hasta aqui.
//
// ── EL VERDE FALSO QUE ESTE FICHERO DENUNCIA ────────────────────────────────
//
// test_sharded_flow_full_contract.cpp:219 hace:
//     ASSERT_NE(stats.time_windows, nullptr) << "debe estar inicializado";
// Y PASA. Porque FlowStatistics() (flow_manager.hpp:68) hace make_unique.
// El puntero no es nulo: apunta a un TimeWindowManager RECIEN NACIDO Y VACIO.
// :287 lo cuenta ademas como "populated_field".
//
// Un test de contrato COMPLETO que certifica como poblado el campo que se
// acaba de perder. Caso 18 del patron de falsa evidencia.
//
// Este test NO pregunta si el puntero existe. Pregunta por el CONTENIDO.
// ============================================================================
#include "flow_manager.hpp"
#include "flow/sharded_flow_manager.hpp"
#include "time_window_manager.hpp"
#include <gtest/gtest.h>

using namespace sniffer;
using namespace sniffer::flow;

namespace {

// Helpers IDENTICOS a test_feature_extractor.cpp (DAY 218). A proposito:
// si el helper diverge, el test mide otro flujo distinto y no compara nada.
SimpleEvent make_fwd_packet(uint32_t packet_len,
                            uint16_t payload_len,
                            uint64_t timestamp_ns,
                            uint8_t tcp_flags = TCP_FLAG_ACK) {
    SimpleEvent pkt{};
    pkt.src_ip        = 0xC0A80101;
    pkt.dst_ip        = 0xC0A80102;
    pkt.src_port      = 12345;
    pkt.dst_port      = 80;
    pkt.protocol      = 6;
    pkt.packet_len    = packet_len;
    pkt.ip_header_len = 20;
    pkt.l4_header_len = 20;
    pkt.payload_len   = payload_len;
    pkt.timestamp     = timestamp_ns;
    pkt.tcp_flags     = tcp_flags;
    return pkt;
}

SimpleEvent make_bwd_packet(uint32_t packet_len,
                            uint16_t payload_len,
                            uint64_t timestamp_ns) {
    SimpleEvent pkt = make_fwd_packet(packet_len, payload_len, timestamp_ns);
    // SimpleEvent es __attribute__((packed)): std::swap NO compila. Copia por valor.
    const uint32_t sip = pkt.src_ip;
    const uint16_t spt = pkt.src_port;
    pkt.src_ip   = pkt.dst_ip;
    pkt.dst_ip   = sip;
    pkt.src_port = pkt.dst_port;
    pkt.dst_port = spt;
    return pkt;
}

FlowKey make_key() {
    return FlowKey{
        .src_ip   = 0xC0A80101,
        .dst_ip   = 0xC0A80102,
        .src_port = 12345,
        .dst_port = 80,
        .protocol = 6
    };
}

}  // namespace

class FlowStatsCloneContract : public ::testing::Test {
protected:
    void SetUp() override {
        ShardedFlowManager::Config config{
            .shard_count         = 4,
            .max_flows_per_shard = 1000,
            .flow_timeout_ns     = 120'000'000'000ULL
        };
        ShardedFlowManager::instance().initialize(config);
        // ⚠️ HALLAZGO 2 (DAY 218): initialize() NO limpia flujos. El singleton
        // acumula entre tests del MISMO binario. Este fichero tiene UN test.
        // Al anadir el segundo: hace falta clear()/reset() aqui.
    }
};

// ============================================================================
// EL RED. Debe fallar HOY.
// ============================================================================
TEST_F(FlowStatsCloneContract, CopyPreservesEveryField) {
    auto& mgr = ShardedFlowManager::instance();
    const auto key = make_key();

    // 3 forward (2 con datos, 1 ACK puro), 2 backward con datos.
    mgr.add_packet(key, make_fwd_packet(1000, 960, 1'000'000'000ULL));
    mgr.add_packet(key, make_bwd_packet( 552, 512, 1'010'000'000ULL));
    mgr.add_packet(key, make_fwd_packet(  54,   0, 1'020'000'000ULL));  // ACK puro
    mgr.add_packet(key, make_bwd_packet(1000, 960, 1'030'000'000ULL));
    mgr.add_packet(key, make_fwd_packet( 552, 512, 1'040'000'000ULL));

    auto stats_opt = mgr.get_flow_stats_copy(key);
    ASSERT_TRUE(stats_opt.has_value()) << "el flujo no existe: el test no mide nada";
    const FlowStatistics& copy = stats_opt.value();

    // ── CONTROL: campos que SI se copian ────────────────────────────────────
    // Si ESTO falla, el test esta mal escrito y no vale. Verificar primero.
    EXPECT_EQ(copy.spkts, 3u);
    EXPECT_EQ(copy.dpkts, 2u);
    EXPECT_EQ(copy.fwd_lengths.size(), 3u);
    EXPECT_EQ(copy.bwd_lengths.size(), 2u);

    // ── CAMPO 27 — fwd_payload_lengths ──────────────────────────────────────
    EXPECT_EQ(copy.fwd_payload_lengths.size(), 3u)
        << "get_flow_stats_copy() NO copia fwd_payload_lengths. "
           "sharded_flow_manager.cpp:120 copia fwd_lengths y se olvida de este. "
           "=> L1[8] act_data_pkt_fwd = 0 SIEMPRE, en produccion.";

    // ── CAMPO 28 — time_windows ─────────────────────────────────────────────
    // Esto es lo que ya hace test_sharded_flow_full_contract.cpp:219.
    // PASA. Y NO PRUEBA NADA. El ctor crea un manager vacio.
    ASSERT_NE(copy.time_windows, nullptr)
        << "el puntero existe (lo crea el ctor) — esto NUNCA falla";

    // La pregunta correcta es por el CONTENIDO:
    EXPECT_GT(copy.time_windows->get_subflow_fwd_bytes_mean(), 0.0)
        << "TimeWindowManager llega VACIO => L1[1] Subflow Fwd Bytes = 0";
    EXPECT_GT(copy.time_windows->get_subflow_fwd_packets_mean(), 0.0)
        << "=> L1[15] Subflow Fwd Packets = 0";
    EXPECT_GT(copy.time_windows->get_subflow_bwd_bytes_mean(), 0.0)
        << "=> L1[12] Subflow Bwd Bytes = 0";
    EXPECT_GT(copy.time_windows->get_init_fwd_win_bytes(), 0u)
        << "init_fwd_bytes_ perdido => L1[14] Init_Win_bytes_forward = 0";
}