// common/include/argus/l1_feature_contract.hpp
//
// DAY 217 — DEBT-FEATURE-EXTRACTOR-L1-BROKEN-001
//
// FUENTE DE VERDAD del orden posicional de las 23 features de L1.
// Compartido por: sniffer (rellena), ml-detector (lee), synthetic_sniffer_injector (fabrica).
//
// ⚠️ EL CAMPO `general_attack_features = 102` DEL PROTOBUF ES `repeated double`:
//    POSICIONAL, SIN NOMBRES. Si productor y consumidor no comparten ESTE orden,
//    el modelo recibe basura ordenada y devuelve una constante confiada.
//    Es exactamente el bug que este fichero existe para impedir.
//
// ⚠️ NO REORDENAR. El orden viene de CIC-IDS2017 y está grabado en los árboles del
//    ONNX. Cambiarlo exige REENTRENAR el modelo.
//
// VALIDADO EXPERIMENTALMENTE (DAY 216): con estas 23 columnas, en este orden, sin
//    escalar, level1_attack_detector.onnx da 200/200 DDoS y 0/200 FP sobre
//    Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv.
//
// Anclado por test_l1_feature_contract: NAMES debe coincidir, elemento a elemento,
// con el campo `model_name` de sniffer/config/features/rf_23_features.json.

#pragma once

#include <array>
#include <cstddef>

namespace argus::l1 {

inline constexpr std::size_t FEATURE_COUNT = 23;

// Nombres EXACTOS de rf_23_features.json (campo `model_name`).
// Los espacios iniciales vienen del CSV original de CIC-IDS2017. NO LIMPIARLOS:
// son parte del contrato y el test los compara literalmente.
inline constexpr std::array<const char*, FEATURE_COUNT> NAMES = {
    " Packet Length Std",              //  0
    " Subflow Fwd Bytes",              //  1
    " Fwd Packet Length Max",          //  2
    " Avg Fwd Segment Size",           //  3
    " ACK Flag Count",                 //  4
    " Packet Length Variance",         //  5
    " PSH Flag Count",                 //  6
    "Bwd Packet Length Max",           //  7   (sin espacio — sic, así está en el CSV)
    " act_data_pkt_fwd",               //  8
    "Total Length of Fwd Packets",     //  9   (sin espacio — sic)
    " Fwd Packet Length Std",          // 10
    "Fwd Packets/s",                   // 11   (sin espacio — sic)
    " Subflow Bwd Bytes",              // 12
    " Destination Port",               // 13
    "Init_Win_bytes_forward",          // 14   (sin espacio — sic)
    "Subflow Fwd Packets",             // 15   (sin espacio — sic)
    " Fwd IAT Min",                    // 16
    " Packet Length Mean",             // 17
    " Total Length of Bwd Packets",    // 18
    " Bwd Packet Length Mean",         // 19
    " Bwd Packet Length Min",          // 20
    " Flow Duration",                  // 21
    " Flow Packets/s",                 // 22
};

// Índices con nombre, para que el sniffer rellene sin contar a mano.
enum Index : std::size_t {
    PACKET_LENGTH_STD          = 0,
    SUBFLOW_FWD_BYTES          = 1,
    FWD_PACKET_LENGTH_MAX      = 2,
    AVG_FWD_SEGMENT_SIZE       = 3,
    ACK_FLAG_COUNT             = 4,
    PACKET_LENGTH_VARIANCE     = 5,
    PSH_FLAG_COUNT             = 6,
    BWD_PACKET_LENGTH_MAX      = 7,
    ACT_DATA_PKT_FWD           = 8,
    TOTAL_LENGTH_FWD_PACKETS   = 9,
    FWD_PACKET_LENGTH_STD      = 10,
    FWD_PACKETS_PER_SEC        = 11,
    SUBFLOW_BWD_BYTES          = 12,
    DESTINATION_PORT           = 13,
    INIT_WIN_BYTES_FORWARD     = 14,
    SUBFLOW_FWD_PACKETS        = 15,
    FWD_IAT_MIN                = 16,
    PACKET_LENGTH_MEAN         = 17,
    TOTAL_LENGTH_BWD_PACKETS   = 18,
    BWD_PACKET_LENGTH_MEAN     = 19,
    BWD_PACKET_LENGTH_MIN      = 20,
    FLOW_DURATION              = 21,
    FLOW_PACKETS_PER_SEC       = 22,
};

}  // namespace argus::l1

// =====================================================================
// MAPA AL ENUM DEL SNIFFER (sniffer/include/feature_extractor.hpp)
// Verificado índice a índice contra el enum de 83, DAY 216.
//
//   L1 idx  contrato                      FeatureIndex del sniffer
//   ------  ----------------------------  ---------------------------------
//    0      Packet Length Std             PACKET_LEN_STD          (15)
//    1      Subflow Fwd Bytes             SUBFLOW_FWD_BYTES       (59)  ✅ existe
//    2      Fwd Packet Length Max         FWD_LEN_MAX             (33)
//    3      Avg Fwd Segment Size          AVG_FWD_SEGMENT_SIZE    (79)
//    4      ACK Flag Count                ACK_FLAG_COUNT          (21)
//    5      Packet Length Variance        PACKET_LEN_VAR          (16)
//    6      PSH Flag Count                PSH_FLAG_COUNT          (20)
//    7      Bwd Packet Length Max         BWD_LEN_MAX             (36)
//    8      act_data_pkt_fwd              🔴 NO EXISTE — hay que implementarlo
//    9      Total Length of Fwd Packets   FWD_LEN_TOT             (35)   [o SBYTES (3)]
//   10      Fwd Packet Length Std         FWD_LEN_STD             (57)
//   11      Fwd Packets/s                 SRATE                   (25)
//   12      Subflow Bwd Bytes             SUBFLOW_BWD_BYTES       (61)  ✅ existe
//   13      Destination Port              🟡 de la 5-tupla, no del enum
//   14      Init_Win_bytes_forward        INIT_FWD_WIN_BYTES      (68)  ✅ existe
//   15      Subflow Fwd Packets           SUBFLOW_FWD_PACKETS     (58)  ✅ existe
//   16      Fwd IAT Min                   FWD_IAT_MIN             (46)
//   17      Packet Length Mean            PACKET_LEN_MEAN         (14)
//   18      Total Length of Bwd Packets   BWD_LEN_TOT             (39)   [o DBYTES (4)]
//   19      Bwd Packet Length Mean        DMEAN                   (7)
//   20      Bwd Packet Length Min         BWD_LEN_MIN             (37)
//   21      Flow Duration                 DURATION                (0)
//   22      Flow Packets/s                FLOW_PKTS_PER_SEC       (75)
//
// ⚠️ AMBIGÜEDADES SIN RESOLVER (medir, no elegir):
//   idx 9  — FWD_LEN_TOT vs SBYTES: ¿son el mismo número? Verificar en
//            sniffer/src/userspace/feature_extractor.cpp antes de elegir.
//   idx 18 — BWD_LEN_TOT vs DBYTES: idem.
//   idx 8  — act_data_pkt_fwd = paquetes forward CON PAYLOAD. FlowStatistics tiene
//            `fwd_lengths` (vector de longitudes): contar los > header_len.
//            NO inventar el umbral: verificar qué mide CICFlowMeter.
// =====================================================================