// ============================================================================
// test_feature_extractor.cpp — DAY 218
// ============================================================================
// LA PRIMERA SUITE DEL FeatureExtractor. Nunca existio.
//
// El componente que calcula las 83 features del sniffer — el que DAY 216
// descubrio que entrega 5 de 23 features L1 incorrectas — NO TENIA TEST.
// Ni uno. Ni registrado ni sin registrar.
//
// Esa es la respuesta a la pregunta de los 200 dias: el extractor roto no
// sobrevivio a los tests. Sobrevivio A LA AUSENCIA DE TESTS.
//
// Este fichero nace con act_data_pkt_fwd (feature L1 [8], la unica de las 23
// que no existia en el enum del sniffer). Las otras 83 iran entrando aqui,
// una a una. Piano piano.
//
// ── DOS SECCIONES, Y LA SEGUNDA ES LA QUE CUENTA ────────────────────────────
//
//   A) UNIDAD    — FlowStatistics a mano -> extractor -> valor.
//                  Verifica la ARITMETICA. Rapido, aislado.
//                  ⚠️  UN TEST ASI HABRIA PASADO EN VERDE CON LAS 5 FEATURES
//                      ROTAS. No prueba que el dato LLEGUE.
//
//   B) CONTRATO  — SimpleEvent -> FlowManager -> extract_features()
//                  -> features[ACT_DATA_PKT_FWD].
//                  Verifica la CADENA ENTERA: que payload_len se apila, que
//                  se apila ALINEADO, y que el extractor lo lee del sitio
//                  correcto. ESTE es el que habria cazado las 5 rotas.
//
// ── LA TRAMPA QUE ESTE TEST EXISTE PARA MATAR ───────────────────────────────
//
// La implementacion "obvia" de act_data_pkt_fwd era:
//
//     if (fwd_lengths[i] > fwd_header_lengths[i]) ++count;   // ❌ MAL
//
// packet_len INCLUYE Ethernet (sniffer.bpf.c:239 — data_end - data, XDP).
// total_header NO lo incluye (flow_manager.hpp:99 — ip_header_len + l4_header_len).
//
//     ACK puro:  packet_len = 14+20+20 = 54     total_header = 20+20 = 40
//                54 > 40  ⟹  "tiene payload"    ❌ FALSO
//
// Habria contado TODOS los paquetes forward, siempre. Un SPKTS con nombre de
// feature de CICFlowMeter. Un numero perfecto, perfectamente vacio.
//
// La solucion correcta NO RECONSTRUYE: usa SimpleEvent::payload_len, que el
// kernel ya calculo con los offsets REALES (sniffer.bpf.c:320-338), y que da
// 0 para un ACK puro POR CONSTRUCCION (payload_start == data_end).
//
// El test PureAcksGiveZero de la seccion B es el que mata esa trampa.
// ============================================================================
#include "feature_extractor.hpp"
#include "flow_manager.hpp"
#include "flow/sharded_flow_manager.hpp"
#include <gtest/gtest.h>

using namespace sniffer;
using namespace sniffer::flow;

namespace {

// ── Helper: paquete forward sintetico ────────────────────────────────────────
// packet_len y payload_len se pasan por separado A PROPOSITO: son datos
// independientes que el kernel calcula por separado. Acoplarlos aqui seria
// reintroducir la reconstruccion que este test existe para prevenir.
SimpleEvent make_fwd_packet(uint32_t packet_len,
                            uint16_t payload_len,
                            uint64_t timestamp_ns,
                            uint8_t tcp_flags = TCP_FLAG_ACK) {
    SimpleEvent pkt{};
    pkt.src_ip        = 0xC0A80101;   // 192.168.1.1
    pkt.dst_ip        = 0xC0A80102;   // 192.168.1.2
    pkt.src_port      = 12345;
    pkt.dst_port      = 80;
    pkt.protocol      = 6;            // TCP
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
    // SimpleEvent es __attribute__((packed)): no se pueden tomar referencias
    // a sus campos, asi que std::swap no vale. Copia por valor.
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

// ============================================================================
// SECCION A — UNIDAD: la aritmetica del extractor
// ============================================================================
// FlowStatistics construido a mano. NO prueba que el dato llegue del kernel.
// Solo prueba que, dado el vector correcto, la cuenta es correcta.
// ============================================================================

class FeatureExtractorUnitTest : public ::testing::Test {
protected:
    FeatureExtractor extractor;
};

TEST_F(FeatureExtractorUnitTest, ActDataPktFwd_CountsOnlyPacketsWithPayload) {
    FlowStatistics flow{};
    // 3 paquetes forward: dos con payload, uno ACK puro.
    flow.fwd_payload_lengths = {960, 0, 512};

    EXPECT_DOUBLE_EQ(extractor.extract_act_data_pkt_fwd(flow), 2.0)
        << "Debe contar solo los paquetes con payload_len > 0";
}

TEST_F(FeatureExtractorUnitTest, ActDataPktFwd_AllPureAcksGiveZero) {
    FlowStatistics flow{};
    // Cinco ACKs puros. Un handshake, un cierre, keepalives.
    flow.fwd_payload_lengths = {0, 0, 0, 0, 0};

    EXPECT_DOUBLE_EQ(extractor.extract_act_data_pkt_fwd(flow), 0.0)
        << "Un flujo de solo-ACKs NO tiene paquetes con datos";
}

TEST_F(FeatureExtractorUnitTest, ActDataPktFwd_EmptyFlowGivesZeroWithoutCrash) {
    FlowStatistics flow{};
    // Sin paquetes forward. No debe petar.
    EXPECT_DOUBLE_EQ(extractor.extract_act_data_pkt_fwd(flow), 0.0);
}

TEST_F(FeatureExtractorUnitTest, ActDataPktFwd_SinglePayloadByteCounts) {
    FlowStatistics flow{};
    // Frontera: 1 byte de payload YA es un paquete con datos.
    flow.fwd_payload_lengths = {1};

    EXPECT_DOUBLE_EQ(extractor.extract_act_data_pkt_fwd(flow), 1.0)
        << "payload_len == 1 cuenta. La frontera es > 0, no >= algo";
}

// ── El enum es POSICIONAL. Si alguien inserta en medio, todo se desplaza. ────
TEST_F(FeatureExtractorUnitTest, EnumContract_ActDataPktFwdIsLastAndCountIs84) {
    static_assert(FeatureExtractor::ACT_DATA_PKT_FWD == 83,
                  "ACT_DATA_PKT_FWD debe ser el indice 83 — AL FINAL del enum. "
                  "El enum es posicional y ddos_features (83 features) depende de el.");
    static_assert(FeatureExtractor::FEATURE_COUNT == 84,
                  "FEATURE_COUNT debe ser 84 tras anadir ACT_DATA_PKT_FWD");
    SUCCEED();
}

// ============================================================================
// SECCION B — CONTRATO: la cadena entera
// ============================================================================
// SimpleEvent -> FlowManager -> FlowStatistics -> extract_features() -> [83]
//
// ESTE es el test que importa. La seccion A pasaria en verde aunque el dato
// nunca llegara del kernel. Esta no.
// ============================================================================

class FeatureExtractorContractTest : public ::testing::Test {
protected:
    void SetUp() override {
        ShardedFlowManager::Config config{
            .shard_count         = 4,
            .max_flows_per_shard = 1000,
            .flow_timeout_ns     = 120'000'000'000ULL
        };
        ShardedFlowManager::instance().initialize(config);
    }

    FeatureExtractor extractor;
};

TEST_F(FeatureExtractorContractTest, PayloadLenReachesFeatureFromSimpleEvent) {
    auto& mgr = ShardedFlowManager::instance();
    const auto key = make_key();

    // 3 forward: dos con datos, uno ACK puro.
    mgr.add_packet(key, make_fwd_packet(1000,  960, 1'000'000'000ULL));
    mgr.add_packet(key, make_fwd_packet(  54,    0, 1'010'000'000ULL));  // ACK puro
    mgr.add_packet(key, make_fwd_packet( 552,  512, 1'020'000'000ULL));
    // 1 backward con datos — NO debe contar (la feature es solo forward).
    mgr.add_packet(key, make_bwd_packet(1000,  960, 1'030'000'000ULL));

    auto stats_opt = mgr.get_flow_stats_copy(key);
    ASSERT_TRUE(stats_opt.has_value()) << "El flujo debe existir tras add_packet";

    const auto features = extractor.extract_features(stats_opt.value());

    EXPECT_DOUBLE_EQ(features[FeatureExtractor::ACT_DATA_PKT_FWD], 2.0)
        << "payload_len debe viajar SimpleEvent -> FlowStatistics -> feature. "
           "Y solo los FORWARD deben contar.";
}

// ── EL TEST QUE MATA LA TRAMPA DE ETHERNET ──────────────────────────────────
TEST_F(FeatureExtractorContractTest, PureAcksGiveZero_KillsTheEthernetTrap) {
    auto& mgr = ShardedFlowManager::instance();
    const auto key = make_key();

    // Cuatro ACKs puros. packet_len = 54 (14 ETH + 20 IP + 20 TCP).
    // total_header = 40. La implementacion INGENUA haria 54 > 40 y contaria 4.
    // La correcta lee payload_len = 0 y cuenta 0.
    for (int i = 0; i < 4; ++i) {
        mgr.add_packet(key, make_fwd_packet(54, 0, 1'000'000'000ULL + i * 10'000'000ULL));
    }

    auto stats_opt = mgr.get_flow_stats_copy(key);
    ASSERT_TRUE(stats_opt.has_value());

    const auto features = extractor.extract_features(stats_opt.value());

    EXPECT_DOUBLE_EQ(features[FeatureExtractor::ACT_DATA_PKT_FWD], 0.0)
        << "REGRESION: si esto da 4, alguien ha reintroducido "
           "'fwd_lengths[i] > fwd_header_lengths[i]'. packet_len INCLUYE Ethernet "
           "(sniffer.bpf.c:239). total_header NO (flow_manager.hpp:99). "
           "USA payload_len.";
}

TEST_F(FeatureExtractorContractTest, AlignmentHolds_PayloadVectorTracksFwdLengths) {
    auto& mgr = ShardedFlowManager::instance();
    const auto key = make_key();

    // Alternar fwd y bwd. fwd_payload_lengths debe seguir alineado con
    // fwd_lengths indice a indice — mismo bloque if(is_fwd), mismo paquete.
    mgr.add_packet(key, make_fwd_packet(1000, 960, 1'000'000'000ULL));
    mgr.add_packet(key, make_bwd_packet( 552, 512, 1'010'000'000ULL));
    mgr.add_packet(key, make_fwd_packet(  54,   0, 1'020'000'000ULL));
    mgr.add_packet(key, make_bwd_packet(  54,   0, 1'030'000'000ULL));
    mgr.add_packet(key, make_fwd_packet( 552, 512, 1'040'000'000ULL));

    auto stats_opt = mgr.get_flow_stats_copy(key);
    ASSERT_TRUE(stats_opt.has_value());
    const auto& stats = stats_opt.value();

    ASSERT_EQ(stats.fwd_lengths.size(), stats.fwd_payload_lengths.size())
        << "Los dos vectores forward DEBEN tener el mismo tamano. Si divergen, "
           "el indice i de uno no corresponde al paquete i del otro.";
    EXPECT_EQ(stats.fwd_lengths.size(), 3u) << "3 paquetes forward, 2 backward";

    const auto features = extractor.extract_features(stats);
    EXPECT_DOUBLE_EQ(features[FeatureExtractor::ACT_DATA_PKT_FWD], 2.0);
}