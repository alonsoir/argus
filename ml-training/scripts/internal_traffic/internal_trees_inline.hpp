// AUTO-GENERATED Internal Traffic Classification Trees
// Source: GenerateInternalCPPForest.py
// Model: Internal Traffic Classification
// Features: internal_connection_rate, service_port_consistency, protocol_regularity, packet_size_consistency, connection_duration_std, lateral_movement_score, service_discovery_patterns, data_exfiltration_indicators, temporal_anomaly_score, access_pattern_entropy
// Trees: 100
// Total Nodes: 940

#ifndef INTERNAL_TREES_INLINE_HPP
#define INTERNAL_TREES_INLINE_HPP

#include <array>
#include <cstdint>

struct InternalNode {
    int16_t feature_idx;     // Feature index for split
    float threshold;         // Split threshold (NORMALIZADO 0.0-1.0)
    int16_t left_child;      // Left child index  
    int16_t right_child;     // Right child index
    std::array<float, 2> value; // Class probabilities [benign, suspicious]
};


// Tree 0: 11 nodes
inline constexpr InternalNode tree_0[] = {
    {7, 0.2802479892309669f, 1, 8, {0.505675f, 0.494325f}},  // data_exfiltration_indicators <= 0.2802?
    {8, 0.597252807489987f, 2, 5, {0.9985664854176964f, 0.0014335145823035095f}},  // temporal_anomaly_score <= 0.5973?
    {5, 0.44620317706214185f, 3, 4, {0.999950495049505f, 4.950495049504951e-05f}},  // lateral_movement_score <= 0.4462?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.5f, 0.5f}},  // Leaf: P(suspicious)=0.5000
    {9, 0.4906301491582796f, 6, 7, {0.06666666666666667f, 0.9333333333333333f}},  // access_pattern_entropy <= 0.4906?
    {-2, -2.0f, -1, -1, {0.6666666666666666f, 0.3333333333333333f}},  // Leaf: P(suspicious)=0.3333
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {9, 0.3644732669236055f, 9, 10, {0.0013151239251390997f, 0.9986848760748609f}},  // access_pattern_entropy <= 0.3645?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 1: 13 nodes
inline constexpr InternalNode tree_1[] = {
    {6, 0.35155659541236056f, 1, 8, {0.498775f, 0.501225f}},  // service_discovery_patterns <= 0.3516?
    {8, 0.5986842460994888f, 2, 5, {0.9932879182528551f, 0.006712081747144861f}},  // temporal_anomaly_score <= 0.5987?
    {9, 0.3734616534421984f, 3, 4, {0.9989420654911839f, 0.001057934508816121f}},  // access_pattern_entropy <= 0.3735?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {2, 0.7131413621081795f, 6, 7, {0.008771929824561403f, 0.9912280701754386f}},  // protocol_regularity <= 0.7131?
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {0.5f, 0.5f}},  // Leaf: P(suspicious)=0.5000
    {7, 0.18562131310983465f, 9, 12, {0.0060391295667797966f, 0.9939608704332202f}},  // data_exfiltration_indicators <= 0.1856?
    {8, 0.318396450133931f, 10, 11, {0.983739837398374f, 0.016260162601626018f}},  // temporal_anomaly_score <= 0.3184?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.3333333333333333f, 0.6666666666666666f}},  // Leaf: P(suspicious)=0.6667
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 2: 13 nodes
inline constexpr InternalNode tree_2[] = {
    {5, 0.264852089486746f, 1, 4, {0.499125f, 0.500875f}},  // lateral_movement_score <= 0.2649?
    {9, 0.36917078061368935f, 2, 3, {0.9930653266331658f, 0.006934673366834171f}},  // access_pattern_entropy <= 0.3692?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {7, 0.1789223995457428f, 5, 6, {0.010099502487562188f, 0.9899004975124378f}},  // data_exfiltration_indicators <= 0.1789?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {2, 0.8508794334970861f, 7, 10, {0.0002512310320570797f, 0.999748768967943f}},  // protocol_regularity <= 0.8509?
    {8, 0.10355974713302636f, 8, 9, {0.00015078407720144752f, 0.9998492159227985f}},  // temporal_anomaly_score <= 0.1036?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {6, 0.4874843181564092f, 11, 12, {0.3333333333333333f, 0.6666666666666666f}},  // service_discovery_patterns <= 0.4875?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 3: 11 nodes
inline constexpr InternalNode tree_3[] = {
    {4, 0.0f, 1, 4, {0.50095f, 0.49905f}},  // connection_duration_std <= 0.0000?
    {9, 0.3669894295747502f, 2, 3, {0.9475286273372953f, 0.05247137266270474f}},  // access_pattern_entropy <= 0.3670?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {7, 0.20900238367741628f, 5, 8, {0.022120913847588457f, 0.9778790861524116f}},  // data_exfiltration_indicators <= 0.2090?
    {6, 0.5659687101011724f, 6, 7, {0.9906542056074766f, 0.009345794392523364f}},  // service_discovery_patterns <= 0.5660?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {8, 0.12205705379099314f, 9, 10, {0.00015894039735099338f, 0.999841059602649f}},  // temporal_anomaly_score <= 0.1221?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 4: 3 nodes
inline constexpr InternalNode tree_4[] = {
    {9, 0.36681991114366597f, 1, 2, {0.49475f, 0.50525f}},  // access_pattern_entropy <= 0.3668?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 5: 9 nodes
inline constexpr InternalNode tree_5[] = {
    {5, 0.27397365728136364f, 1, 4, {0.50325f, 0.49675f}},  // lateral_movement_score <= 0.2740?
    {9, 0.3691799148677586f, 2, 3, {0.9922935414905782f, 0.007706458509421767f}},  // access_pattern_entropy <= 0.3692?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {7, 0.18274162130553528f, 5, 6, {0.008648866093427868f, 0.9913511339065721f}},  // data_exfiltration_indicators <= 0.1827?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {6, 0.1860763677274829f, 7, 8, {0.00020285004310563416f, 0.9997971499568944f}},  // service_discovery_patterns <= 0.1861?
    {-2, -2.0f, -1, -1, {0.5714285714285714f, 0.42857142857142855f}},  // Leaf: P(suspicious)=0.4286
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 6: 15 nodes
inline constexpr InternalNode tree_6[] = {
    {7, 0.2811211426369137f, 1, 10, {0.500325f, 0.499675f}},  // data_exfiltration_indicators <= 0.2811?
    {1, 0.27285639257583416f, 2, 5, {0.9987007146069662f, 0.0012992853930338315f}},  // service_port_consistency <= 0.2729?
    {8, 0.524868973200868f, 3, 4, {0.08695652173913043f, 0.9130434782608695f}},  // temporal_anomaly_score <= 0.5249?
    {-2, -2.0f, -1, -1, {0.6666666666666666f, 0.3333333333333333f}},  // Leaf: P(suspicious)=0.3333
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {6, 0.6385388509811446f, 6, 9, {0.999749849909946f, 0.0002501500900540324f}},  // service_discovery_patterns <= 0.6385?
    {9, 0.5064572342330117f, 7, 8, {0.9998498949264485f, 0.00015010507355148604f}},  // access_pattern_entropy <= 0.5065?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {6, 0.1722364303629835f, 11, 12, {0.0014007704237330532f, 0.9985992295762669f}},  // service_discovery_patterns <= 0.1722?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {3, 0.8223327671625703f, 13, 14, {0.00015027048687637747f, 0.9998497295131237f}},  // packet_size_consistency <= 0.8223?
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
};


// Tree 7: 13 nodes
inline constexpr InternalNode tree_7[] = {
    {7, 0.2631686920133092f, 1, 4, {0.49705f, 0.50295f}},  // data_exfiltration_indicators <= 0.2632?
    {9, 0.41082872971681483f, 2, 3, {0.9991439218451003f, 0.0008560781548997886f}},  // access_pattern_entropy <= 0.4108?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {8, 0.2012644228716304f, 5, 8, {0.0020355476119551185f, 0.9979644523880449f}},  // temporal_anomaly_score <= 0.2013?
    {4, 0.0f, 6, 7, {0.972972972972973f, 0.02702702702702703f}},  // connection_duration_std <= 0.0000?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.6666666666666666f, 0.3333333333333333f}},  // Leaf: P(suspicious)=0.3333
    {6, 0.19282452251137913f, 9, 12, {0.0002486943546381497f, 0.9997513056453619f}},  // service_discovery_patterns <= 0.1928?
    {9, 0.16227215043491441f, 10, 11, {0.8333333333333334f, 0.16666666666666666f}},  // access_pattern_entropy <= 0.1623?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.5f, 0.5f}},  // Leaf: P(suspicious)=0.5000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 8: 13 nodes
inline constexpr InternalNode tree_8[] = {
    {8, 0.36620779871344955f, 1, 4, {0.4971f, 0.5029f}},  // temporal_anomaly_score <= 0.3662?
    {9, 0.3720801720259044f, 2, 3, {0.9925361843764183f, 0.0074638156235816225f}},  // access_pattern_entropy <= 0.3721?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {2, 0.8193869203317469f, 5, 8, {0.010063953200138814f, 0.9899360467998611f}},  // protocol_regularity <= 0.8194?
    {9, 0.36379913793471097f, 6, 7, {0.0017004251062765691f, 0.9982995748937235f}},  // access_pattern_entropy <= 0.3638?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {3, 0.34800147751107713f, 9, 10, {0.9602272727272727f, 0.03977272727272727f}},  // packet_size_consistency <= 0.3480?
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {8, 0.6006957549718742f, 11, 12, {0.9941176470588236f, 0.0058823529411764705f}},  // temporal_anomaly_score <= 0.6007?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.5f, 0.5f}},  // Leaf: P(suspicious)=0.5000
};


// Tree 9: 15 nodes
inline constexpr InternalNode tree_9[] = {
    {6, 0.33717368721176794f, 1, 6, {0.501425f, 0.498575f}},  // service_discovery_patterns <= 0.3372?
    {7, 0.341252238556016f, 2, 3, {0.9936118181364476f, 0.006388181863552428f}},  // data_exfiltration_indicators <= 0.3413?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {1, 0.5600331533108663f, 4, 5, {0.007751937984496124f, 0.9922480620155039f}},  // service_port_consistency <= 0.5600?
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {0.5f, 0.5f}},  // Leaf: P(suspicious)=0.5000
    {8, 0.217964198265827f, 7, 10, {0.0074137153734408654f, 0.9925862846265592f}},  // temporal_anomaly_score <= 0.2180?
    {7, 0.43247910288541774f, 8, 9, {0.9455782312925171f, 0.05442176870748299f}},  // data_exfiltration_indicators <= 0.4325?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {5, 0.07792321885031156f, 11, 12, {0.0004541784416633024f, 0.9995458215583367f}},  // lateral_movement_score <= 0.0779?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {9, 0.3636169788180531f, 13, 14, {0.00015143866733972742f, 0.9998485613326603f}},  // access_pattern_entropy <= 0.3636?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 10: 17 nodes
inline constexpr InternalNode tree_10[] = {
    {6, 0.32663816378794785f, 1, 6, {0.49615f, 0.50385f}},  // service_discovery_patterns <= 0.3266?
    {5, 0.4723218379519644f, 2, 5, {0.9951456310679612f, 0.0048543689320388345f}},  // lateral_movement_score <= 0.4723?
    {9, 0.37343796749738556f, 3, 4, {0.9997459994919989f, 0.000254000508001016f}},  // access_pattern_entropy <= 0.3734?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {5, 0.18037322701725875f, 7, 10, {0.008208069620253165f, 0.9917919303797469f}},  // lateral_movement_score <= 0.1804?
    {9, 0.3830155922981494f, 8, 9, {0.9418604651162791f, 0.05813953488372093f}},  // access_pattern_entropy <= 0.3830?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {1, 0.8177816675771574f, 11, 14, {0.00019948134849391582f, 0.9998005186515061f}},  // service_port_consistency <= 0.8178?
    {8, 0.16080857773831736f, 12, 13, {4.9892730629147335e-05f, 0.9999501072693708f}},  // temporal_anomaly_score <= 0.1608?
    {-2, -2.0f, -1, -1, {0.3333333333333333f, 0.6666666666666666f}},  // Leaf: P(suspicious)=0.6667
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {4, 0.0f, 15, 16, {0.3333333333333333f, 0.6666666666666666f}},  // connection_duration_std <= 0.0000?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 11: 9 nodes
inline constexpr InternalNode tree_11[] = {
    {7, 0.2791296074127925f, 1, 4, {0.501325f, 0.498675f}},  // data_exfiltration_indicators <= 0.2791?
    {9, 0.3825883862158007f, 2, 3, {0.9981057773789941f, 0.0018942226210059319f}},  // access_pattern_entropy <= 0.3826?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {8, 0.18888714370596535f, 5, 8, {0.0015045889964391394f, 0.9984954110035609f}},  // temporal_anomaly_score <= 0.1889?
    {1, 0.610590741832829f, 6, 7, {0.967741935483871f, 0.03225806451612903f}},  // service_port_consistency <= 0.6106?
    {-2, -2.0f, -1, -1, {0.5f, 0.5f}},  // Leaf: P(suspicious)=0.5000
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 12: 13 nodes
inline constexpr InternalNode tree_12[] = {
    {5, 0.2767001229974861f, 1, 4, {0.503025f, 0.496975f}},  // lateral_movement_score <= 0.2767?
    {9, 0.36917078061368935f, 2, 3, {0.9916981507257904f, 0.008301849274209584f}},  // access_pattern_entropy <= 0.3692?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {6, 0.18715648671608187f, 5, 8, {0.008650170991752162f, 0.9913498290082479f}},  // service_discovery_patterns <= 0.1872?
    {2, 0.6527445829498066f, 6, 7, {0.9811320754716981f, 0.018867924528301886f}},  // protocol_regularity <= 0.6527?
    {-2, -2.0f, -1, -1, {0.25f, 0.75f}},  // Leaf: P(suspicious)=0.7500
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {2, 0.8626764231326867f, 9, 12, {0.0008111533586818758f, 0.9991888466413181f}},  // protocol_regularity <= 0.8627?
    {1, 0.8352074957380226f, 10, 11, {0.00015219155844155844f, 0.9998478084415584f}},  // service_port_consistency <= 0.8352?
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
};


// Tree 13: 11 nodes
inline constexpr InternalNode tree_13[] = {
    {7, 0.28554229682005106f, 1, 4, {0.502675f, 0.497325f}},  // data_exfiltration_indicators <= 0.2855?
    {9, 0.3773758829306533f, 2, 3, {0.9979131471728113f, 0.002086852827188711f}},  // access_pattern_entropy <= 0.3774?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {8, 0.19849720636264614f, 5, 8, {0.0011572909328771259f, 0.9988427090671229f}},  // temporal_anomaly_score <= 0.1985?
    {5, 0.33625435742839715f, 6, 7, {0.84f, 0.16f}},  // lateral_movement_score <= 0.3363?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {9, 0.3296060133293228f, 9, 10, {0.00010076074361428788f, 0.9998992392563857f}},  // access_pattern_entropy <= 0.3296?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 14: 7 nodes
inline constexpr InternalNode tree_14[] = {
    {5, 0.27700550910699046f, 1, 4, {0.498775f, 0.501225f}},  // lateral_movement_score <= 0.2770?
    {9, 0.36917078061368935f, 2, 3, {0.9929711818455669f, 0.007028818154433176f}},  // access_pattern_entropy <= 0.3692?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {9, 0.3659643243244145f, 5, 6, {0.008614679812767652f, 0.9913853201872324f}},  // access_pattern_entropy <= 0.3660?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 15: 3 nodes
inline constexpr InternalNode tree_15[] = {
    {9, 0.3668527313425479f, 1, 2, {0.503825f, 0.496175f}},  // access_pattern_entropy <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 16: 23 nodes
inline constexpr InternalNode tree_16[] = {
    {1, 0.5466860193967356f, 1, 12, {0.5005f, 0.4995f}},  // service_port_consistency <= 0.5467?
    {4, 0.0f, 2, 5, {0.036028340284407816f, 0.9639716597155922f}},  // connection_duration_std <= 0.0000?
    {9, 0.36664856936819934f, 3, 4, {0.7016861219195849f, 0.29831387808041504f}},  // access_pattern_entropy <= 0.3666?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {5, 0.1809546060668589f, 6, 9, {0.009200209095661264f, 0.9907997909043388f}},  // lateral_movement_score <= 0.1810?
    {4, 0.0f, 7, 8, {0.9712643678160919f, 0.028735632183908046f}},  // connection_duration_std <= 0.0000?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {8, 0.14088554375346155f, 10, 11, {0.00036927621861152144f, 0.9996307237813885f}},  // temporal_anomaly_score <= 0.1409?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {3, 0.31273190736926204f, 13, 16, {0.9603960396039604f, 0.039603960396039604f}},  // packet_size_consistency <= 0.3127?
    {7, 0.18579229408797376f, 14, 15, {0.21076923076923076f, 0.7892307692307692f}},  // data_exfiltration_indicators <= 0.1858?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {8, 0.5514813427368896f, 17, 20, {0.9854491233482441f, 0.014550876651755874f}},  // temporal_anomaly_score <= 0.5515?
    {9, 0.38275662479938577f, 18, 19, {0.9991655366642328f, 0.0008344633357671847f}},  // access_pattern_entropy <= 0.3828?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {7, 0.2904898900799155f, 21, 22, {0.02909090909090909f, 0.9709090909090909f}},  // data_exfiltration_indicators <= 0.2905?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 17: 11 nodes
inline constexpr InternalNode tree_17[] = {
    {5, 0.2705962089507447f, 1, 4, {0.5068f, 0.4932f}},  // lateral_movement_score <= 0.2706?
    {9, 0.3691567022911989f, 2, 3, {0.9930758197734804f, 0.006924180226519611f}},  // access_pattern_entropy <= 0.3692?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {6, 0.2276538400448802f, 5, 8, {0.00975683736919266f, 0.9902431626308074f}},  // service_discovery_patterns <= 0.2277?
    {4, 0.0f, 6, 7, {0.9633507853403142f, 0.03664921465968586f}},  // connection_duration_std <= 0.0000?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {7, 0.12137052348097443f, 9, 10, {0.0004594180704441041f, 0.9995405819295559f}},  // data_exfiltration_indicators <= 0.1214?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 18: 11 nodes
inline constexpr InternalNode tree_18[] = {
    {6, 0.3470140075636796f, 1, 8, {0.50065f, 0.49935f}},  // service_discovery_patterns <= 0.3470?
    {7, 0.36681215647871346f, 2, 5, {0.9927716849451645f, 0.007228315054835494f}},  // data_exfiltration_indicators <= 0.3668?
    {5, 0.46534516941523973f, 3, 4, {0.999949779027722f, 5.02209722780233e-05f}},  // lateral_movement_score <= 0.4653?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.6666666666666666f, 0.3333333333333333f}},  // Leaf: P(suspicious)=0.3333
    {1, 0.6343122172888151f, 6, 7, {0.02702702702702703f, 0.972972972972973f}},  // service_port_consistency <= 0.6343?
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {7, 0.18562131310983465f, 9, 10, {0.005566700100300903f, 0.9944332998996991f}},  // data_exfiltration_indicators <= 0.1856?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 19: 3 nodes
inline constexpr InternalNode tree_19[] = {
    {9, 0.36688421909745816f, 1, 2, {0.501575f, 0.498425f}},  // access_pattern_entropy <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 20: 3 nodes
inline constexpr InternalNode tree_20[] = {
    {9, 0.36687508484338904f, 1, 2, {0.500675f, 0.499325f}},  // access_pattern_entropy <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 21: 11 nodes
inline constexpr InternalNode tree_21[] = {
    {7, 0.2796103655169589f, 1, 4, {0.4955f, 0.5045f}},  // data_exfiltration_indicators <= 0.2796?
    {9, 0.3774141380983671f, 2, 3, {0.9986879951556744f, 0.0013120048443255791f}},  // access_pattern_entropy <= 0.3774?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {6, 0.19529571863166031f, 5, 8, {0.001436852796908289f, 0.9985631472030917f}},  // service_discovery_patterns <= 0.1953?
    {2, 0.6210275377726386f, 6, 7, {0.875f, 0.125f}},  // protocol_regularity <= 0.6210?
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {2, 0.8530738975631603f, 9, 10, {4.962532876780309e-05f, 0.9999503746712322f}},  // protocol_regularity <= 0.8531?
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {0.5f, 0.5f}},  // Leaf: P(suspicious)=0.5000
};


// Tree 22: 17 nodes
inline constexpr InternalNode tree_22[] = {
    {6, 0.363293276580275f, 1, 8, {0.501225f, 0.498775f}},  // service_discovery_patterns <= 0.3633?
    {5, 0.4535379310149106f, 2, 7, {0.9915060600039738f, 0.008493939996026227f}},  // lateral_movement_score <= 0.4535?
    {8, 0.6737045715687404f, 3, 6, {0.9993991889050218f, 0.0006008110949782206f}},  // temporal_anomaly_score <= 0.6737?
    {9, 0.29759864033441197f, 4, 5, {0.9998497295131237f, 0.00015027048687637747f}},  // access_pattern_entropy <= 0.2976?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.25f, 0.75f}},  // Leaf: P(suspicious)=0.7500
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {8, 0.2164087314751165f, 9, 12, {0.004429232937386752f, 0.9955707670626133f}},  // temporal_anomaly_score <= 0.2164?
    {2, 0.5929544587917023f, 10, 11, {0.9021739130434783f, 0.09782608695652174f}},  // protocol_regularity <= 0.5930?
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {3, 0.8195823859588854f, 13, 16, {0.00025283171521035597f, 0.9997471682847896f}},  // packet_size_consistency <= 0.8196?
    {7, 0.19565501973695107f, 14, 15, {0.00010115314586283633f, 0.9998988468541372f}},  // data_exfiltration_indicators <= 0.1957?
    {-2, -2.0f, -1, -1, {0.5f, 0.5f}},  // Leaf: P(suspicious)=0.5000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {0.75f, 0.25f}},  // Leaf: P(suspicious)=0.2500
};


// Tree 23: 3 nodes
inline constexpr InternalNode tree_23[] = {
    {9, 0.3668527313425479f, 1, 2, {0.498625f, 0.501375f}},  // access_pattern_entropy <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 24: 3 nodes
inline constexpr InternalNode tree_24[] = {
    {9, 0.36688421909745816f, 1, 2, {0.493425f, 0.506575f}},  // access_pattern_entropy <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 25: 7 nodes
inline constexpr InternalNode tree_25[] = {
    {7, 0.292017878698106f, 1, 4, {0.499675f, 0.500325f}},  // data_exfiltration_indicators <= 0.2920?
    {9, 0.3774141380983671f, 2, 3, {0.998000799680128f, 0.001999200319872051f}},  // access_pattern_entropy <= 0.3774?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {9, 0.3618558034662962f, 5, 6, {0.0009503801520608243f, 0.9990496198479392f}},  // access_pattern_entropy <= 0.3619?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 26: 11 nodes
inline constexpr InternalNode tree_26[] = {
    {7, 0.2802479892309669f, 1, 8, {0.501875f, 0.498125f}},  // data_exfiltration_indicators <= 0.2802?
    {4, 0.0f, 2, 5, {0.9983069415396872f, 0.001693058460312718f}},  // connection_duration_std <= 0.0000?
    {5, 0.6164630171570127f, 3, 4, {0.9998503740648379f, 0.00014962593516209475f}},  // lateral_movement_score <= 0.6165?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {1, 0.5772499857763986f, 6, 7, {0.03125f, 0.96875f}},  // service_port_consistency <= 0.5772?
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {0.5f, 0.5f}},  // Leaf: P(suspicious)=0.5000
    {9, 0.36450475467851573f, 9, 10, {0.0013555577869263982f, 0.9986444422130736f}},  // access_pattern_entropy <= 0.3645?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 27: 3 nodes
inline constexpr InternalNode tree_27[] = {
    {9, 0.3668527313425479f, 1, 2, {0.5024f, 0.4976f}},  // access_pattern_entropy <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 28: 9 nodes
inline constexpr InternalNode tree_28[] = {
    {7, 0.2790723401997637f, 1, 4, {0.50025f, 0.49975f}},  // data_exfiltration_indicators <= 0.2791?
    {9, 0.42299883465041854f, 2, 3, {0.99855f, 0.00145f}},  // access_pattern_entropy <= 0.4230?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {6, 0.1674659228472715f, 5, 6, {0.00195f, 0.99805f}},  // service_discovery_patterns <= 0.1675?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {2, 0.8693330946865676f, 7, 8, {0.00015027048687637747f, 0.9998497295131237f}},  // protocol_regularity <= 0.8693?
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
};


// Tree 29: 13 nodes
inline constexpr InternalNode tree_29[] = {
    {7, 0.2807287473351332f, 1, 4, {0.499725f, 0.500275f}},  // data_exfiltration_indicators <= 0.2807?
    {9, 0.3774141380983671f, 2, 3, {0.998299489846954f, 0.0017005101530459137f}},  // access_pattern_entropy <= 0.3774?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {6, 0.19303996925953468f, 5, 8, {0.0014495651304608618f, 0.9985504348695391f}},  // service_discovery_patterns <= 0.1930?
    {3, 0.48541047749985405f, 6, 7, {0.9f, 0.1f}},  // packet_size_consistency <= 0.4854?
    {-2, -2.0f, -1, -1, {0.25f, 0.75f}},  // Leaf: P(suspicious)=0.7500
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {7, 0.28462817005116076f, 9, 12, {0.00010012014417300761f, 0.999899879855827f}},  // data_exfiltration_indicators <= 0.2846?
    {9, 0.6134175260387204f, 10, 11, {0.16666666666666666f, 0.8333333333333334f}},  // access_pattern_entropy <= 0.6134?
    {-2, -2.0f, -1, -1, {0.6666666666666666f, 0.3333333333333333f}},  // Leaf: P(suspicious)=0.3333
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 30: 15 nodes
inline constexpr InternalNode tree_30[] = {
    {6, 0.33594543646875336f, 1, 6, {0.499575f, 0.500425f}},  // service_discovery_patterns <= 0.3359?
    {8, 0.6120706394994379f, 2, 5, {0.9942931517821386f, 0.005706848217861433f}},  // temporal_anomaly_score <= 0.6121?
    {9, 0.3734616534421984f, 3, 4, {0.9996476923851225f, 0.0003523076148774473f}},  // access_pattern_entropy <= 0.3735?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {5, 0.17945482728154002f, 7, 10, {0.00604274870155813f, 0.9939572512984419f}},  // lateral_movement_score <= 0.1795?
    {9, 0.3794183442176998f, 8, 9, {0.8561151079136691f, 0.14388489208633093f}},  // access_pattern_entropy <= 0.3794?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {3, 0.8127135243005678f, 11, 14, {0.00010057832537088258f, 0.9998994216746291f}},  // packet_size_consistency <= 0.8127?
    {7, 0.2115304968712433f, 12, 13, {5.030434126465114e-05f, 0.9999496956587354f}},  // data_exfiltration_indicators <= 0.2115?
    {-2, -2.0f, -1, -1, {0.5f, 0.5f}},  // Leaf: P(suspicious)=0.5000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {0.16666666666666666f, 0.8333333333333334f}},  // Leaf: P(suspicious)=0.8333
};


// Tree 31: 13 nodes
inline constexpr InternalNode tree_31[] = {
    {7, 0.2851522590533562f, 1, 8, {0.49865f, 0.50135f}},  // data_exfiltration_indicators <= 0.2852?
    {4, 0.0f, 2, 5, {0.9984464267815977f, 0.0015535732184023255f}},  // connection_duration_std <= 0.0000?
    {9, 0.5412159637722306f, 3, 4, {0.9997490841571737f, 0.00025091584282631606f}},  // access_pattern_entropy <= 0.5412?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {3, 0.47816647274978236f, 6, 7, {0.037037037037037035f, 0.9629629629629629f}},  // packet_size_consistency <= 0.4782?
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {0.5f, 0.5f}},  // Leaf: P(suspicious)=0.5000
    {6, 0.20056092313426116f, 9, 12, {0.001147361069540058f, 0.99885263893046f}},  // service_discovery_patterns <= 0.2006?
    {3, 0.4665855223088477f, 10, 11, {0.8846153846153846f, 0.11538461538461539f}},  // packet_size_consistency <= 0.4666?
    {-2, -2.0f, -1, -1, {0.4f, 0.6f}},  // Leaf: P(suspicious)=0.6000
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 32: 3 nodes
inline constexpr InternalNode tree_32[] = {
    {9, 0.36688421909745816f, 1, 2, {0.5013f, 0.4987f}},  // access_pattern_entropy <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 33: 15 nodes
inline constexpr InternalNode tree_33[] = {
    {8, 0.3663278984002308f, 1, 8, {0.495975f, 0.504025f}},  // temporal_anomaly_score <= 0.3663?
    {7, 0.39800720994255495f, 2, 5, {0.9920562639141874f, 0.007943736085812588f}},  // data_exfiltration_indicators <= 0.3980?
    {2, 0.33506782793520934f, 3, 4, {0.9999489926039276f, 5.1007396072430504e-05f}},  // protocol_regularity <= 0.3351?
    {-2, -2.0f, -1, -1, {0.5f, 0.5f}},  // Leaf: P(suspicious)=0.5000
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {9, 0.46103662114321264f, 6, 7, {0.018867924528301886f, 0.9811320754716981f}},  // access_pattern_entropy <= 0.4610?
    {-2, -2.0f, -1, -1, {0.6f, 0.4f}},  // Leaf: P(suspicious)=0.4000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {5, 0.1676144925172887f, 9, 12, {0.011464716347104172f, 0.9885352836528958f}},  // lateral_movement_score <= 0.1676?
    {0, 0.0f, 10, 11, {0.9529914529914529f, 0.04700854700854701f}},  // internal_connection_rate <= 0.0000?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {9, 0.34386463652778443f, 13, 14, {0.00044995500449955f, 0.9995500449955005f}},  // access_pattern_entropy <= 0.3439?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 34: 9 nodes
inline constexpr InternalNode tree_34[] = {
    {7, 0.2802479892309669f, 1, 6, {0.498075f, 0.501925f}},  // data_exfiltration_indicators <= 0.2802?
    {6, 0.5590227928270841f, 2, 5, {0.9985945891682979f, 0.0014054108317020529f}},  // service_discovery_patterns <= 0.5590?
    {5, 0.5368094771095115f, 3, 4, {0.9998492310785003f, 0.0001507689214996482f}},  // lateral_movement_score <= 0.5368?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {9, 0.3644732669236055f, 7, 8, {0.0013946306719131345f, 0.9986053693280869f}},  // access_pattern_entropy <= 0.3645?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 35: 3 nodes
inline constexpr InternalNode tree_35[] = {
    {9, 0.3668513988985762f, 1, 2, {0.501725f, 0.498275f}},  // access_pattern_entropy <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 36: 17 nodes
inline constexpr InternalNode tree_36[] = {
    {6, 0.3629127220847095f, 1, 8, {0.499775f, 0.500225f}},  // service_discovery_patterns <= 0.3629?
    {5, 0.4680202401888819f, 2, 7, {0.9920785173375847f, 0.007921482662415305f}},  // lateral_movement_score <= 0.4680?
    {8, 0.6842230293454326f, 3, 6, {0.9994980675601064f, 0.0005019324398935904f}},  // temporal_anomaly_score <= 0.6842?
    {4, 0.0f, 4, 5, {0.9999497840715075f, 5.021592849251783e-05f}},  // connection_duration_std <= 0.0000?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.6666666666666666f, 0.3333333333333333f}},  // Leaf: P(suspicious)=0.3333
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {2, 0.8628562580263152f, 9, 16, {0.003914090726615817f, 0.9960859092733841f}},  // protocol_regularity <= 0.8629?
    {1, 0.8209124117168842f, 10, 13, {0.0006041687644748766f, 0.9993958312355251f}},  // service_port_consistency <= 0.8209?
    {8, 0.13013926323136493f, 11, 12, {0.00015111827523675195f, 0.9998488817247633f}},  // temporal_anomaly_score <= 0.1301?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {0, 0.0f, 14, 15, {0.9f, 0.1f}},  // internal_connection_rate <= 0.0000?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.5f, 0.5f}},  // Leaf: P(suspicious)=0.5000
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
};


// Tree 37: 3 nodes
inline constexpr InternalNode tree_37[] = {
    {9, 0.3668527313425479f, 1, 2, {0.498625f, 0.501375f}},  // access_pattern_entropy <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 38: 15 nodes
inline constexpr InternalNode tree_38[] = {
    {6, 0.33594543646875336f, 1, 8, {0.49585f, 0.50415f}},  // service_discovery_patterns <= 0.3359?
    {3, 0.21771323398642894f, 2, 5, {0.9930394431554525f, 0.0069605568445475635f}},  // packet_size_consistency <= 0.2177?
    {7, 0.33485828260002315f, 3, 4, {0.2073170731707317f, 0.7926829268292683f}},  // data_exfiltration_indicators <= 0.3349?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {9, 0.3670474434839919f, 6, 7, {0.9963026742301458f, 0.0036973257698541327f}},  // access_pattern_entropy <= 0.3670?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {1, 0.741238648224268f, 9, 12, {0.007237037771388916f, 0.992762962228611f}},  // service_port_consistency <= 0.7412?
    {7, 0.16504992450717476f, 10, 11, {0.001646788761914267f, 0.9983532112380857f}},  // data_exfiltration_indicators <= 0.1650?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {4, 0.0f, 13, 14, {0.837037037037037f, 0.16296296296296298f}},  // connection_duration_std <= 0.0000?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 39: 13 nodes
inline constexpr InternalNode tree_39[] = {
    {7, 0.2627418737150573f, 1, 10, {0.498725f, 0.501275f}},  // data_exfiltration_indicators <= 0.2627?
    {2, 0.4242848454941733f, 2, 5, {0.9988460766606462f, 0.001153923339353803f}},  // protocol_regularity <= 0.4243?
    {8, 0.3872388701636951f, 3, 4, {0.4722222222222222f, 0.5277777777777778f}},  // temporal_anomaly_score <= 0.3872?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {0, 0.0f, 6, 7, {0.9997989545637314f, 0.0002010454362685967f}},  // internal_connection_rate <= 0.0000?
    {-2, -2.0f, -1, -1, {0.5f, 0.5f}},  // Leaf: P(suspicious)=0.5000
    {9, 0.5292872941798681f, 8, 9, {0.9998994570681681f, 0.00010054293183189222f}},  // access_pattern_entropy <= 0.5293?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {9, 0.3644732669236055f, 11, 12, {0.001993223041658362f, 0.9980067769583416f}},  // access_pattern_entropy <= 0.3645?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 40: 3 nodes
inline constexpr InternalNode tree_40[] = {
    {9, 0.3668513988985762f, 1, 2, {0.50045f, 0.49955f}},  // access_pattern_entropy <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 41: 11 nodes
inline constexpr InternalNode tree_41[] = {
    {8, 0.3768906246969851f, 1, 8, {0.50075f, 0.49925f}},  // temporal_anomaly_score <= 0.3769?
    {7, 0.39166448561134964f, 2, 5, {0.9909095449777734f, 0.009090455022226662f}},  // data_exfiltration_indicators <= 0.3917?
    {4, 0.0f, 3, 4, {0.999748021972484f, 0.0002519780275160006f}},  // connection_duration_std <= 0.0000?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {2, 0.6967337227159667f, 6, 7, {0.0056179775280898875f, 0.9943820224719101f}},  // protocol_regularity <= 0.6967?
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {0.5f, 0.5f}},  // Leaf: P(suspicious)=0.5000
    {9, 0.3658705623459846f, 9, 10, {0.009560038039941939f, 0.990439961960058f}},  // access_pattern_entropy <= 0.3659?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 42: 9 nodes
inline constexpr InternalNode tree_42[] = {
    {6, 0.3331022968638458f, 1, 6, {0.49965f, 0.50035f}},  // service_discovery_patterns <= 0.3331?
    {8, 0.6120706394994379f, 2, 5, {0.9933864422065234f, 0.006613557793476627f}},  // temporal_anomaly_score <= 0.6121?
    {9, 0.3734707876962675f, 3, 4, {0.9993951308029638f, 0.0006048691970361409f}},  // access_pattern_entropy <= 0.3735?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {7, 0.18693953332928462f, 7, 8, {0.007933735841524873f, 0.9920662641584751f}},  // data_exfiltration_indicators <= 0.1869?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 43: 11 nodes
inline constexpr InternalNode tree_43[] = {
    {2, 0.6853764989075284f, 1, 8, {0.49855f, 0.50145f}},  // protocol_regularity <= 0.6854?
    {7, 0.24227085940683338f, 2, 5, {0.03267909230236812f, 0.9673209076976319f}},  // data_exfiltration_indicators <= 0.2423?
    {5, 0.47237911002905736f, 3, 4, {0.9864457831325302f, 0.01355421686746988f}},  // lateral_movement_score <= 0.4724?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {6, 0.15570785207729262f, 6, 7, {0.00030670142616163164f, 0.9996932985738384f}},  // service_discovery_patterns <= 0.1557?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {9, 0.3668527313425479f, 9, 10, {0.9751175845850402f, 0.024882415414959794f}},  // access_pattern_entropy <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 44: 15 nodes
inline constexpr InternalNode tree_44[] = {
    {2, 0.6759874431867979f, 1, 8, {0.49795f, 0.50205f}},  // protocol_regularity <= 0.6760?
    {7, 0.2183796436126101f, 2, 5, {0.0284862043251305f, 0.9715137956748695f}},  // data_exfiltration_indicators <= 0.2184?
    {3, 0.2566657359368223f, 3, 4, {0.9982332155477032f, 0.0017667844522968198f}},  // packet_size_consistency <= 0.2567?
    {-2, -2.0f, -1, -1, {0.5f, 0.5f}},  // Leaf: P(suspicious)=0.5000
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {5, 0.10028368829019702f, 6, 7, {0.0004092280935086194f, 0.9995907719064914f}},  // lateral_movement_score <= 0.1003?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {3, 0.3051076118444529f, 9, 12, {0.9728438521498617f, 0.027156147850138295f}},  // packet_size_consistency <= 0.3051?
    {7, 0.24096839587757585f, 10, 11, {0.27415730337078653f, 0.7258426966292135f}},  // data_exfiltration_indicators <= 0.2410?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {9, 0.3668527313425479f, 13, 14, {0.9888374485596708f, 0.011162551440329217f}},  // access_pattern_entropy <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 45: 11 nodes
inline constexpr InternalNode tree_45[] = {
    {5, 0.26613096597261776f, 1, 4, {0.498975f, 0.501025f}},  // lateral_movement_score <= 0.2661?
    {9, 0.3691799148677586f, 2, 3, {0.9929595172240382f, 0.00704048277596178f}},  // access_pattern_entropy <= 0.3692?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {2, 0.8228731460626777f, 5, 8, {0.010638826746209296f, 0.9893611732537907f}},  // protocol_regularity <= 0.8229?
    {9, 0.3643981240964643f, 6, 7, {0.0016564601947595622f, 0.9983435398052405f}},  // access_pattern_entropy <= 0.3644?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {9, 0.3765939136408384f, 9, 10, {0.9378238341968912f, 0.06217616580310881f}},  // access_pattern_entropy <= 0.3766?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 46: 3 nodes
inline constexpr InternalNode tree_46[] = {
    {9, 0.36687508484338904f, 1, 2, {0.498475f, 0.501525f}},  // access_pattern_entropy <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 47: 15 nodes
inline constexpr InternalNode tree_47[] = {
    {6, 0.3407397193211623f, 1, 8, {0.495625f, 0.504375f}},  // service_discovery_patterns <= 0.3407?
    {8, 0.5368971551274423f, 2, 5, {0.992789431222267f, 0.007210568777732957f}},  // temporal_anomaly_score <= 0.5369?
    {9, 0.5649920063425241f, 3, 4, {0.9996445076430857f, 0.00035549235691432633f}},  // access_pattern_entropy <= 0.5650?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {6, 0.14137080962500967f, 6, 7, {0.03546099290780142f, 0.9645390070921985f}},  // service_discovery_patterns <= 0.1414?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {2, 0.8520065483191808f, 9, 12, {0.006743355811186037f, 0.993256644188814f}},  // protocol_regularity <= 0.8520?
    {9, 0.36142947399182357f, 10, 11, {0.00114707495885492f, 0.9988529250411451f}},  // access_pattern_entropy <= 0.3614?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {6, 0.6656414823049703f, 13, 14, {0.9658119658119658f, 0.03418803418803419f}},  // service_discovery_patterns <= 0.6656?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 48: 9 nodes
inline constexpr InternalNode tree_48[] = {
    {7, 0.28494390069933456f, 1, 6, {0.5002f, 0.4998f}},  // data_exfiltration_indicators <= 0.2849?
    {5, 0.49463356990373203f, 2, 5, {0.99860048982856f, 0.001399510171439996f}},  // lateral_movement_score <= 0.4946?
    {4, 0.0f, 3, 4, {0.9998498648783906f, 0.0001501351216094485f}},  // connection_duration_std <= 0.0000?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {9, 0.3618086594947184f, 7, 8, {0.0014505076776871906f, 0.9985494923223128f}},  // access_pattern_entropy <= 0.3618?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 49: 3 nodes
inline constexpr InternalNode tree_49[] = {
    {9, 0.3668527313425479f, 1, 2, {0.5011f, 0.4989f}},  // access_pattern_entropy <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 50: 3 nodes
inline constexpr InternalNode tree_50[] = {
    {9, 0.36688421909745816f, 1, 2, {0.499475f, 0.500525f}},  // access_pattern_entropy <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 51: 11 nodes
inline constexpr InternalNode tree_51[] = {
    {5, 0.2847774798954098f, 1, 6, {0.49905f, 0.50095f}},  // lateral_movement_score <= 0.2848?
    {7, 0.3450332772000865f, 2, 3, {0.9896109085460266f, 0.010389091453973327f}},  // data_exfiltration_indicators <= 0.3450?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {8, 0.2071145721503263f, 4, 5, {0.014218009478672985f, 0.985781990521327f}},  // temporal_anomaly_score <= 0.2071?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {7, 0.1890727966990427f, 7, 8, {0.0074578307222583715f, 0.9925421692777416f}},  // data_exfiltration_indicators <= 0.1891?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {8, 0.10897784994815235f, 9, 10, {0.00015126304643775526f, 0.9998487369535622f}},  // temporal_anomaly_score <= 0.1090?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 52: 13 nodes
inline constexpr InternalNode tree_52[] = {
    {7, 0.2790723401997637f, 1, 4, {0.50125f, 0.49875f}},  // data_exfiltration_indicators <= 0.2791?
    {9, 0.3774141380983671f, 2, 3, {0.9985534716679968f, 0.0014465283320031924f}},  // access_pattern_entropy <= 0.3774?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {2, 0.8549703110798443f, 5, 10, {0.001553728949478749f, 0.9984462710505213f}},  // protocol_regularity <= 0.8550?
    {8, 0.2037308738472511f, 6, 9, {0.0005018065034122842f, 0.9994981934965878f}},  // temporal_anomaly_score <= 0.2037?
    {9, 0.45176321433977784f, 7, 8, {0.7692307692307693f, 0.23076923076923078f}},  // access_pattern_entropy <= 0.4518?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {0, 0.0f, 11, 12, {0.875f, 0.125f}},  // internal_connection_rate <= 0.0000?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 53: 7 nodes
inline constexpr InternalNode tree_53[] = {
    {6, 0.3470140075636796f, 1, 4, {0.5017f, 0.4983f}},  // service_discovery_patterns <= 0.3470?
    {9, 0.3670565777380611f, 2, 3, {0.9927824788451967f, 0.007217521154803385f}},  // access_pattern_entropy <= 0.3671?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {9, 0.3649952343173628f, 5, 6, {0.0061778001004520345f, 0.993822199899548f}},  // access_pattern_entropy <= 0.3650?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 54: 7 nodes
inline constexpr InternalNode tree_54[] = {
    {2, 0.6759598176769538f, 1, 4, {0.5029f, 0.4971f}},  // protocol_regularity <= 0.6760?
    {9, 0.36657041100996446f, 2, 3, {0.02994282275052663f, 0.9700571772494734f}},  // access_pattern_entropy <= 0.3666?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {9, 0.3668527313425479f, 5, 6, {0.972933904894826f, 0.02706609510517396f}},  // access_pattern_entropy <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 55: 13 nodes
inline constexpr InternalNode tree_55[] = {
    {5, 0.29035736942944085f, 1, 8, {0.49975f, 0.50025f}},  // lateral_movement_score <= 0.2904?
    {8, 0.5616198215668683f, 2, 5, {0.9890350877192983f, 0.010964912280701754f}},  // temporal_anomaly_score <= 0.5616?
    {4, 0.0f, 3, 4, {0.999043254947379f, 0.0009567450526209779f}},  // connection_duration_std <= 0.0000?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {6, 0.2542690154591977f, 6, 7, {0.01951219512195122f, 0.9804878048780488f}},  // service_discovery_patterns <= 0.2543?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {7, 0.18223864567135334f, 9, 10, {0.007323434991974318f, 0.9926765650080257f}},  // data_exfiltration_indicators <= 0.1822?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {1, 0.829750615438481f, 11, 12, {5.052801778586226e-05f, 0.9999494719822142f}},  // service_port_consistency <= 0.8298?
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {0.5f, 0.5f}},  // Leaf: P(suspicious)=0.5000
};


// Tree 56: 11 nodes
inline constexpr InternalNode tree_56[] = {
    {2, 0.6776760375271542f, 1, 4, {0.500625f, 0.499375f}},  // protocol_regularity <= 0.6777?
    {9, 0.3667338107180733f, 2, 3, {0.02893264041575055f, 0.9710673595842495f}},  // access_pattern_entropy <= 0.3667?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {7, 0.34948203543327694f, 5, 10, {0.9728837302381429f, 0.027116269761857114f}},  // data_exfiltration_indicators <= 0.3495?
    {3, 0.0928302322207523f, 6, 7, {0.9997943444730077f, 0.00020565552699228792f}},  // packet_size_consistency <= 0.0928?
    {-2, -2.0f, -1, -1, {0.5f, 0.5f}},  // Leaf: P(suspicious)=0.5000
    {0, 0.0f, 8, 9, {0.9998971510850561f, 0.00010284891494394734f}},  // internal_connection_rate <= 0.0000?
    {-2, -2.0f, -1, -1, {0.3333333333333333f, 0.6666666666666666f}},  // Leaf: P(suspicious)=0.6667
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 57: 9 nodes
inline constexpr InternalNode tree_57[] = {
    {7, 0.285616484569707f, 1, 4, {0.50065f, 0.49935f}},  // data_exfiltration_indicators <= 0.2856?
    {9, 0.3825883862158007f, 2, 3, {0.9980044898977302f, 0.001995510102269893f}},  // access_pattern_entropy <= 0.3826?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {6, 0.19303996925953468f, 5, 8, {0.0010523678276121273f, 0.9989476321723879f}},  // service_discovery_patterns <= 0.1930?
    {8, 0.3781522550702173f, 6, 7, {0.9130434782608695f, 0.08695652173913043f}},  // temporal_anomaly_score <= 0.3782?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 58: 11 nodes
inline constexpr InternalNode tree_58[] = {
    {7, 0.24943505042539965f, 1, 4, {0.50325f, 0.49675f}},  // data_exfiltration_indicators <= 0.2494?
    {9, 0.42299883465041854f, 2, 3, {0.999452300338578f, 0.0005476996614220275f}},  // access_pattern_entropy <= 0.4230?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {6, 0.1860763677274829f, 5, 6, {0.0028620204860413737f, 0.9971379795139587f}},  // service_discovery_patterns <= 0.1861?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {2, 0.8913243459207377f, 7, 10, {0.00030203876164107727f, 0.999697961238359f}},  // protocol_regularity <= 0.8913?
    {6, 0.20527887738927178f, 8, 9, {5.0352467270896274e-05f, 0.9999496475327291f}},  // service_discovery_patterns <= 0.2053?
    {-2, -2.0f, -1, -1, {0.14285714285714285f, 0.8571428571428571f}},  // Leaf: P(suspicious)=0.8571
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
};


// Tree 59: 3 nodes
inline constexpr InternalNode tree_59[] = {
    {9, 0.3668527313425479f, 1, 2, {0.501125f, 0.498875f}},  // access_pattern_entropy <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 60: 7 nodes
inline constexpr InternalNode tree_60[] = {
    {6, 0.349039198049837f, 1, 4, {0.49745f, 0.50255f}},  // service_discovery_patterns <= 0.3490?
    {9, 0.3697901040781688f, 2, 3, {0.9937274187073465f, 0.006272581292653553f}},  // access_pattern_entropy <= 0.3698?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {9, 0.3649952343173628f, 5, 6, {0.004732961339178956f, 0.995267038660821f}},  // access_pattern_entropy <= 0.3650?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 61: 3 nodes
inline constexpr InternalNode tree_61[] = {
    {9, 0.3668435970884787f, 1, 2, {0.496725f, 0.503275f}},  // access_pattern_entropy <= 0.3668?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 62: 15 nodes
inline constexpr InternalNode tree_62[] = {
    {5, 0.27424740881425386f, 1, 8, {0.501125f, 0.498875f}},  // lateral_movement_score <= 0.2742?
    {1, 0.358256491425411f, 2, 5, {0.9919516096780644f, 0.008048390321935613f}},  // service_port_consistency <= 0.3583?
    {7, 0.2332290110614457f, 3, 4, {0.2638888888888889f, 0.7361111111111112f}},  // data_exfiltration_indicators <= 0.2332?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {9, 0.3708458906041687f, 6, 7, {0.9972306143001007f, 0.0027693856998992953f}},  // access_pattern_entropy <= 0.3708?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {7, 0.17841942391156085f, 9, 10, {0.010102020404080815f, 0.9898979795959192f}},  // data_exfiltration_indicators <= 0.1784?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {2, 0.8225267209733221f, 11, 12, {0.00010103051121438674f, 0.9998989694887856f}},  // protocol_regularity <= 0.8225?
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {3, 0.5864181611508427f, 13, 14, {0.1f, 0.9f}},  // packet_size_consistency <= 0.5864?
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
};


// Tree 63: 13 nodes
inline constexpr InternalNode tree_63[] = {
    {7, 0.2851522590533562f, 1, 8, {0.50305f, 0.49695f}},  // data_exfiltration_indicators <= 0.2852?
    {8, 0.597252807489987f, 2, 7, {0.9981632247815727f, 0.0018367752184273232f}},  // temporal_anomaly_score <= 0.5973?
    {1, 0.14524989596588195f, 3, 4, {0.9998508204873198f, 0.0001491795126802586f}},  // service_port_consistency <= 0.1452?
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {4, 0.0f, 5, 6, {0.9999502685498309f, 4.973145016908693e-05f}},  // connection_duration_std <= 0.0000?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.5f, 0.5f}},  // Leaf: P(suspicious)=0.5000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {6, 0.19303996925953468f, 9, 12, {0.0007554391619661563f, 0.9992445608380338f}},  // service_discovery_patterns <= 0.1930?
    {4, 0.0f, 10, 11, {0.8823529411764706f, 0.11764705882352941f}},  // connection_duration_std <= 0.0000?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 64: 11 nodes
inline constexpr InternalNode tree_64[] = {
    {4, 0.0f, 1, 4, {0.500675f, 0.499325f}},  // connection_duration_std <= 0.0000?
    {9, 0.3671127157064479f, 2, 3, {0.9463485177151121f, 0.053651482284887926f}},  // access_pattern_entropy <= 0.3671?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {6, 0.23225604143769057f, 5, 8, {0.020514152168267984f, 0.979485847831732f}},  // service_discovery_patterns <= 0.2323?
    {9, 0.37159498709862904f, 6, 7, {0.9844155844155844f, 0.015584415584415584f}},  // access_pattern_entropy <= 0.3716?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {9, 0.3604879445363972f, 9, 10, {0.0008479067302596715f, 0.9991520932697403f}},  // access_pattern_entropy <= 0.3605?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 65: 11 nodes
inline constexpr InternalNode tree_65[] = {
    {7, 0.28494390069933456f, 1, 8, {0.502675f, 0.497325f}},  // data_exfiltration_indicators <= 0.2849?
    {6, 0.576690648864839f, 2, 5, {0.9987076250124267f, 0.0012923749875733174f}},  // service_discovery_patterns <= 0.5767?
    {9, 0.5574406080509411f, 3, 4, {0.9997511818860413f, 0.0002488181139586962f}},  // access_pattern_entropy <= 0.5574?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {9, 0.5086987205722527f, 6, 7, {0.08695652173913043f, 0.9130434782608695f}},  // access_pattern_entropy <= 0.5087?
    {-2, -2.0f, -1, -1, {0.6666666666666666f, 0.3333333333333333f}},  // Leaf: P(suspicious)=0.3333
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {6, 0.19076882444360876f, 9, 10, {0.0007544512624484458f, 0.9992455487375516f}},  // service_discovery_patterns <= 0.1908?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 66: 3 nodes
inline constexpr InternalNode tree_66[] = {
    {9, 0.3668527313425479f, 1, 2, {0.503875f, 0.496125f}},  // access_pattern_entropy <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 67: 3 nodes
inline constexpr InternalNode tree_67[] = {
    {9, 0.3668527313425479f, 1, 2, {0.499175f, 0.500825f}},  // access_pattern_entropy <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 68: 15 nodes
inline constexpr InternalNode tree_68[] = {
    {6, 0.33222913289919487f, 1, 4, {0.49495f, 0.50505f}},  // service_discovery_patterns <= 0.3322?
    {9, 0.3670565777380611f, 2, 3, {0.9948834853090173f, 0.005116514690982776f}},  // access_pattern_entropy <= 0.3671?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {1, 0.7421210944519763f, 5, 10, {0.007847976307996052f, 0.992152023692004f}},  // service_port_consistency <= 0.7421?
    {8, 0.16178132533847317f, 6, 7, {0.0024355087230975695f, 0.9975644912769024f}},  // temporal_anomaly_score <= 0.1618?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {7, 0.12137052348097443f, 8, 9, {0.00014945449110745777f, 0.9998505455088925f}},  // data_exfiltration_indicators <= 0.1214?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {2, 0.6587296317189044f, 11, 12, {0.7801418439716312f, 0.2198581560283688f}},  // protocol_regularity <= 0.6587?
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {5, 0.23259187540108725f, 13, 14, {0.9821428571428571f, 0.017857142857142856f}},  // lateral_movement_score <= 0.2326?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.3333333333333333f, 0.6666666666666666f}},  // Leaf: P(suspicious)=0.6667
};


// Tree 69: 11 nodes
inline constexpr InternalNode tree_69[] = {
    {6, 0.3628068252887097f, 1, 4, {0.500925f, 0.499075f}},  // service_discovery_patterns <= 0.3628?
    {9, 0.3670565777380611f, 2, 3, {0.9907094594594594f, 0.009290540540540541f}},  // access_pattern_entropy <= 0.3671?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {2, 0.8574193244866256f, 5, 8, {0.004830917874396135f, 0.9951690821256038f}},  // protocol_regularity <= 0.8574?
    {9, 0.3613979862369132f, 6, 7, {0.0007075352504169405f, 0.9992924647495831f}},  // access_pattern_entropy <= 0.3614?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {9, 0.5853470516119408f, 9, 10, {0.9647058823529412f, 0.03529411764705882f}},  // access_pattern_entropy <= 0.5853?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 70: 3 nodes
inline constexpr InternalNode tree_70[] = {
    {9, 0.3668435970884787f, 1, 2, {0.4988f, 0.5012f}},  // access_pattern_entropy <= 0.3668?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 71: 17 nodes
inline constexpr InternalNode tree_71[] = {
    {2, 0.6931821704276663f, 1, 10, {0.498975f, 0.501025f}},  // protocol_regularity <= 0.6932?
    {6, 0.27817761593776613f, 2, 7, {0.03518628030751035f, 0.9648137196924896f}},  // service_discovery_patterns <= 0.2782?
    {5, 0.2721482672472738f, 3, 4, {0.9655647382920111f, 0.03443526170798898f}},  // lateral_movement_score <= 0.2721?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {9, 0.35606098710119916f, 5, 6, {0.07407407407407407f, 0.9259259259259259f}},  // access_pattern_entropy <= 0.3561?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {9, 0.36652254821992825f, 8, 9, {0.0006644178677297352f, 0.9993355821322703f}},  // access_pattern_entropy <= 0.3665?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {4, 0.0f, 11, 14, {0.9765070022325959f, 0.0234929977674041f}},  // connection_duration_std <= 0.0000?
    {9, 0.38007569493184534f, 12, 13, {0.9948296365234476f, 0.005170363476552402f}},  // access_pattern_entropy <= 0.3801?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {9, 0.3622920210776114f, 15, 16, {0.010899182561307902f, 0.989100817438692f}},  // access_pattern_entropy <= 0.3623?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 72: 15 nodes
inline constexpr InternalNode tree_72[] = {
    {7, 0.2791296074127925f, 1, 4, {0.5021f, 0.4979f}},  // data_exfiltration_indicators <= 0.2791?
    {9, 0.3774141380983671f, 2, 3, {0.9985560645289783f, 0.0014439354710217088f}},  // access_pattern_entropy <= 0.3774?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {5, 0.1508923278811656f, 5, 8, {0.001456115685880699f, 0.9985438843141193f}},  // lateral_movement_score <= 0.1509?
    {1, 0.36788904943466205f, 6, 7, {0.7941176470588235f, 0.20588235294117646f}},  // service_port_consistency <= 0.3679?
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {2, 0.7920212218301538f, 9, 12, {0.00010059350165979277f, 0.9998994064983402f}},  // protocol_regularity <= 0.7920?
    {9, 0.43616224150061234f, 10, 11, {5.043373007867662e-05f, 0.9999495662699214f}},  // access_pattern_entropy <= 0.4362?
    {-2, -2.0f, -1, -1, {0.5f, 0.5f}},  // Leaf: P(suspicious)=0.5000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {2, 0.7931632855212117f, 13, 14, {0.018518518518518517f, 0.9814814814814815f}},  // protocol_regularity <= 0.7932?
    {-2, -2.0f, -1, -1, {0.5f, 0.5f}},  // Leaf: P(suspicious)=0.5000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 73: 17 nodes
inline constexpr InternalNode tree_73[] = {
    {8, 0.37927542285128757f, 1, 12, {0.5029f, 0.4971f}},  // temporal_anomaly_score <= 0.3793?
    {6, 0.5586796645435658f, 2, 9, {0.9915494358005666f, 0.008450564199433314f}},  // service_discovery_patterns <= 0.5587?
    {1, 0.19787196438391363f, 3, 4, {0.9995990778791219f, 0.00040092212087801946f}},  // service_port_consistency <= 0.1979?
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {3, 0.1577172014037167f, 5, 8, {0.9997994987468671f, 0.0002005012531328321f}},  // packet_size_consistency <= 0.1577?
    {3, 0.11751707344682816f, 6, 7, {0.3333333333333333f, 0.6666666666666666f}},  // packet_size_consistency <= 0.1175?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {2, 0.7050684646064537f, 10, 11, {0.006134969325153374f, 0.9938650306748467f}},  // protocol_regularity <= 0.7051?
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {0.5f, 0.5f}},  // Leaf: P(suspicious)=0.5000
    {6, 0.22289544758784885f, 13, 14, {0.008499723381783434f, 0.9915002766182166f}},  // service_discovery_patterns <= 0.2229?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {2, 0.9377541277270598f, 15, 16, {0.00020286033066233897f, 0.9997971396693377f}},  // protocol_regularity <= 0.9378?
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
};


// Tree 74: 3 nodes
inline constexpr InternalNode tree_74[] = {
    {9, 0.3668527313425479f, 1, 2, {0.5049f, 0.4951f}},  // access_pattern_entropy <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 75: 15 nodes
inline constexpr InternalNode tree_75[] = {
    {6, 0.35230735627952314f, 1, 8, {0.499825f, 0.500175f}},  // service_discovery_patterns <= 0.3523?
    {7, 0.35113187728106626f, 2, 5, {0.9921193076961444f, 0.007880692303855553f}},  // data_exfiltration_indicators <= 0.3511?
    {4, 0.0f, 3, 4, {0.9997989343520659f, 0.00020106564793405046f}},  // connection_duration_std <= 0.0000?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {6, 0.18457146123214785f, 6, 7, {0.0064516129032258064f, 0.9935483870967742f}},  // service_discovery_patterns <= 0.1846?
    {-2, -2.0f, -1, -1, {0.5f, 0.5f}},  // Leaf: P(suspicious)=0.5000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {1, 0.7783342016032375f, 9, 12, {0.005112525687935442f, 0.9948874743120646f}},  // service_port_consistency <= 0.7783?
    {7, 0.192455464137524f, 10, 11, {0.0018114118949381101f, 0.9981885881050618f}},  // data_exfiltration_indicators <= 0.1925?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {7, 0.26728596290813345f, 13, 14, {0.8571428571428571f, 0.14285714285714285f}},  // data_exfiltration_indicators <= 0.2673?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 76: 9 nodes
inline constexpr InternalNode tree_76[] = {
    {6, 0.3632453084033204f, 1, 4, {0.50365f, 0.49635f}},  // service_discovery_patterns <= 0.3632?
    {9, 0.3670565777380611f, 2, 3, {0.9925794004155536f, 0.0074205995844464235f}},  // access_pattern_entropy <= 0.3671?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {7, 0.18375104919209503f, 5, 6, {0.004144344486000202f, 0.9958556555139998f}},  // data_exfiltration_indicators <= 0.1838?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {5, 0.11344454548590785f, 7, 8, {5.074854097944684e-05f, 0.9999492514590206f}},  // lateral_movement_score <= 0.1134?
    {-2, -2.0f, -1, -1, {0.5f, 0.5f}},  // Leaf: P(suspicious)=0.5000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 77: 15 nodes
inline constexpr InternalNode tree_77[] = {
    {7, 0.26368005331026406f, 1, 8, {0.498175f, 0.501825f}},  // data_exfiltration_indicators <= 0.2637?
    {8, 0.597252807489987f, 2, 5, {0.9986953685583823f, 0.001304631441617743f}},  // temporal_anomaly_score <= 0.5973?
    {6, 0.5860517347724487f, 3, 4, {0.9998995025375609f, 0.00010049746243907341f}},  // service_discovery_patterns <= 0.5861?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.3333333333333333f, 0.6666666666666666f}},  // Leaf: P(suspicious)=0.6667
    {9, 0.576028306649153f, 6, 7, {0.14285714285714285f, 0.8571428571428571f}},  // access_pattern_entropy <= 0.5760?
    {-2, -2.0f, -1, -1, {0.8f, 0.2f}},  // Leaf: P(suspicious)=0.2000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {5, 0.1259176804794477f, 9, 10, {0.0011957550695032633f, 0.9988042449304967f}},  // lateral_movement_score <= 0.1259?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {5, 0.16758438719508903f, 11, 14, {0.00014962593516209475f, 0.9998503740648379f}},  // lateral_movement_score <= 0.1676?
    {7, 0.43200256745485416f, 12, 13, {0.25f, 0.75f}},  // data_exfiltration_indicators <= 0.4320?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 78: 15 nodes
inline constexpr InternalNode tree_78[] = {
    {5, 0.2726784237703326f, 1, 6, {0.5008f, 0.4992f}},  // lateral_movement_score <= 0.2727?
    {7, 0.38456342580131f, 2, 5, {0.9925473915870555f, 0.0074526084129445305f}},  // data_exfiltration_indicators <= 0.3846?
    {4, 0.0f, 3, 4, {0.999949609473419f, 5.039052658100277e-05f}},  // connection_duration_std <= 0.0000?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.5f, 0.5f}},  // Leaf: P(suspicious)=0.5000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {8, 0.24712060841312258f, 7, 10, {0.009396711151097116f, 0.9906032888489029f}},  // temporal_anomaly_score <= 0.2471?
    {9, 0.3867272026421177f, 8, 9, {0.9187817258883249f, 0.08121827411167512f}},  // access_pattern_entropy <= 0.3867?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {1, 0.8185353513803382f, 11, 14, {0.00035335689045936394f, 0.9996466431095407f}},  // service_port_consistency <= 0.8185?
    {2, 0.8926721957419446f, 12, 13, {0.00015147689977278465f, 0.9998485231002272f}},  // protocol_regularity <= 0.8927?
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.8f, 0.2f}},  // Leaf: P(suspicious)=0.2000
};


// Tree 79: 15 nodes
inline constexpr InternalNode tree_79[] = {
    {6, 0.3375908478231008f, 1, 8, {0.493875f, 0.506125f}},  // service_discovery_patterns <= 0.3376?
    {7, 0.37989450661756174f, 2, 5, {0.9933727930389032f, 0.006627206961096778f}},  // data_exfiltration_indicators <= 0.3799?
    {7, 0.341252238556016f, 3, 4, {0.9998981410746116f, 0.00010185892538833715f}},  // data_exfiltration_indicators <= 0.3413?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.6f, 0.4f}},  // Leaf: P(suspicious)=0.4000
    {2, 0.66812308240711f, 6, 7, {0.022727272727272728f, 0.9772727272727273f}},  // protocol_regularity <= 0.6681?
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {0.75f, 0.25f}},  // Leaf: P(suspicious)=0.2500
    {8, 0.217964198265827f, 9, 12, {0.005881480749270993f, 0.994118519250729f}},  // temporal_anomaly_score <= 0.2180?
    {5, 0.4191734253731406f, 10, 11, {0.9304347826086956f, 0.06956521739130435f}},  // lateral_movement_score <= 0.4192?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {7, 0.13529230345624185f, 13, 14, {0.0005964807634953773f, 0.9994035192365046f}},  // data_exfiltration_indicators <= 0.1353?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 80: 9 nodes
inline constexpr InternalNode tree_80[] = {
    {8, 0.3768906246969851f, 1, 6, {0.5012f, 0.4988f}},  // temporal_anomaly_score <= 0.3769?
    {7, 0.366946521057485f, 2, 3, {0.9910607271274471f, 0.008939272872552936f}},  // data_exfiltration_indicators <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {2, 0.7354129046354115f, 4, 5, {0.005555555555555556f, 0.9944444444444445f}},  // protocol_regularity <= 0.7354?
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {0.3333333333333333f, 0.6666666666666666f}},  // Leaf: P(suspicious)=0.6667
    {9, 0.3658705623459846f, 7, 8, {0.010162194633560273f, 0.9898378053664397f}},  // access_pattern_entropy <= 0.3659?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 81: 3 nodes
inline constexpr InternalNode tree_81[] = {
    {9, 0.3668998753141257f, 1, 2, {0.498175f, 0.501825f}},  // access_pattern_entropy <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 82: 3 nodes
inline constexpr InternalNode tree_82[] = {
    {9, 0.36682951876598824f, 1, 2, {0.502975f, 0.497025f}},  // access_pattern_entropy <= 0.3668?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 83: 3 nodes
inline constexpr InternalNode tree_83[] = {
    {9, 0.3668610065208985f, 1, 2, {0.49795f, 0.50205f}},  // access_pattern_entropy <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 84: 7 nodes
inline constexpr InternalNode tree_84[] = {
    {6, 0.33585248228313486f, 1, 4, {0.49975f, 0.50025f}},  // service_discovery_patterns <= 0.3359?
    {9, 0.3670565777380611f, 2, 3, {0.9943415122684026f, 0.005658487731597396f}},  // access_pattern_entropy <= 0.3671?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {9, 0.36502672207227316f, 5, 6, {0.006640039940089865f, 0.9933599600599101f}},  // access_pattern_entropy <= 0.3650?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 85: 3 nodes
inline constexpr InternalNode tree_85[] = {
    {9, 0.36682951876598824f, 1, 2, {0.499225f, 0.500775f}},  // access_pattern_entropy <= 0.3668?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 86: 19 nodes
inline constexpr InternalNode tree_86[] = {
    {8, 0.3770075666225313f, 1, 12, {0.4983f, 0.5017f}},  // temporal_anomaly_score <= 0.3770?
    {6, 0.5247757809294294f, 2, 9, {0.9914680050188206f, 0.008531994981179424f}},  // service_discovery_patterns <= 0.5248?
    {6, 0.45152463209861227f, 3, 6, {0.9996456772626038f, 0.00035432273739623404f}},  // service_discovery_patterns <= 0.4515?
    {5, 0.4478661812671757f, 4, 5, {0.9999493414387032f, 5.0658561296859166e-05f}},  // lateral_movement_score <= 0.4479?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.5f, 0.5f}},  // Leaf: P(suspicious)=0.5000
    {5, 0.5001859778363728f, 7, 8, {0.625f, 0.375f}},  // lateral_movement_score <= 0.5002?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {5, 0.16408839541013634f, 10, 11, {0.03550295857988166f, 0.9644970414201184f}},  // lateral_movement_score <= 0.1641?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {6, 0.22305546328290257f, 13, 16, {0.008816936488169365f, 0.9911830635118306f}},  // service_discovery_patterns <= 0.2231?
    {4, 0.0f, 14, 15, {0.9776536312849162f, 0.0223463687150838f}},  // connection_duration_std <= 0.0000?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {7, 0.10956186151434195f, 17, 18, {0.00010052271813429835f, 0.9998994772818657f}},  // data_exfiltration_indicators <= 0.1096?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 87: 3 nodes
inline constexpr InternalNode tree_87[] = {
    {9, 0.3668527313425479f, 1, 2, {0.49845f, 0.50155f}},  // access_pattern_entropy <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 88: 3 nodes
inline constexpr InternalNode tree_88[] = {
    {9, 0.36687508484338904f, 1, 2, {0.5029f, 0.4971f}},  // access_pattern_entropy <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 89: 3 nodes
inline constexpr InternalNode tree_89[] = {
    {9, 0.3668527313425479f, 1, 2, {0.502625f, 0.497375f}},  // access_pattern_entropy <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 90: 13 nodes
inline constexpr InternalNode tree_90[] = {
    {2, 0.6762178650529982f, 1, 10, {0.501925f, 0.498075f}},  // protocol_regularity <= 0.6762?
    {6, 0.24455927493745624f, 2, 7, {0.028283436136602978f, 0.971716563863397f}},  // service_discovery_patterns <= 0.2446?
    {8, 0.5201984946773784f, 3, 6, {0.9668989547038328f, 0.033101045296167246f}},  // temporal_anomaly_score <= 0.5202?
    {5, 0.378867736345563f, 4, 5, {0.9964093357271095f, 0.003590664272890485f}},  // lateral_movement_score <= 0.3789?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.3333333333333333f, 0.6666666666666666f}},  // Leaf: P(suspicious)=0.6667
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {9, 0.36656969219150604f, 8, 9, {0.0004647080084680126f, 0.999535291991532f}},  // access_pattern_entropy <= 0.3666?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {9, 0.3700395516153977f, 11, 12, {0.9727802981205443f, 0.027219701879455604f}},  // access_pattern_entropy <= 0.3700?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 91: 17 nodes
inline constexpr InternalNode tree_91[] = {
    {6, 0.3470140075636796f, 1, 10, {0.4996f, 0.5004f}},  // service_discovery_patterns <= 0.3470?
    {5, 0.4369001527363576f, 2, 7, {0.9919612542440583f, 0.008038745755941682f}},  // lateral_movement_score <= 0.4369?
    {8, 0.6737045715687404f, 3, 6, {0.9997483770318555f, 0.0002516229681445322f}},  // temporal_anomaly_score <= 0.6737?
    {9, 0.29756582013553f, 4, 5, {0.9998993356150594f, 0.00010066438494060802f}},  // access_pattern_entropy <= 0.2976?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.3333333333333333f, 0.6666666666666666f}},  // Leaf: P(suspicious)=0.6667
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {9, 0.44106253212460045f, 8, 9, {0.006369426751592357f, 0.9936305732484076f}},  // access_pattern_entropy <= 0.4411?
    {-2, -2.0f, -1, -1, {0.5f, 0.5f}},  // Leaf: P(suspicious)=0.5000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {2, 0.8434873373856867f, 11, 14, {0.005858201482074905f, 0.9941417985179251f}},  // protocol_regularity <= 0.8435?
    {7, 0.15098083775696572f, 12, 13, {0.0006040471156750226f, 0.9993959528843249f}},  // data_exfiltration_indicators <= 0.1510?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {3, 0.41941060658871115f, 15, 16, {0.9905660377358491f, 0.009433962264150943f}},  // packet_size_consistency <= 0.4194?
    {-2, -2.0f, -1, -1, {0.6666666666666666f, 0.3333333333333333f}},  // Leaf: P(suspicious)=0.3333
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
};


// Tree 92: 9 nodes
inline constexpr InternalNode tree_92[] = {
    {7, 0.2867582477643317f, 1, 4, {0.502225f, 0.497775f}},  // data_exfiltration_indicators <= 0.2868?
    {9, 0.3774141380983671f, 2, 3, {0.9983582906323069f, 0.0016417093676931497f}},  // access_pattern_entropy <= 0.3774?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {8, 0.20214213083802868f, 5, 8, {0.0010553294135383687f, 0.9989446705864616f}},  // temporal_anomaly_score <= 0.2021?
    {7, 0.5213502525044046f, 6, 7, {0.9130434782608695f, 0.08695652173913043f}},  // data_exfiltration_indicators <= 0.5214?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 93: 11 nodes
inline constexpr InternalNode tree_93[] = {
    {6, 0.32588562853065234f, 1, 8, {0.502325f, 0.497675f}},  // service_discovery_patterns <= 0.3259?
    {8, 0.5854787579972109f, 2, 5, {0.9951085600199651f, 0.004891439980034939f}},  // temporal_anomaly_score <= 0.5855?
    {5, 0.5716998513649035f, 3, 4, {0.9997993981945837f, 0.00020060180541624874f}},  // lateral_movement_score <= 0.5717?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {8, 0.6261606299927617f, 6, 7, {0.010526315789473684f, 0.9894736842105263f}},  // temporal_anomaly_score <= 0.6262?
    {-2, -2.0f, -1, -1, {0.5f, 0.5f}},  // Leaf: P(suspicious)=0.5000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {9, 0.36295105487887913f, 9, 10, {0.00781367392937641f, 0.9921863260706236f}},  // access_pattern_entropy <= 0.3630?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 94: 3 nodes
inline constexpr InternalNode tree_94[] = {
    {9, 0.3668610065208985f, 1, 2, {0.4995f, 0.5005f}},  // access_pattern_entropy <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 95: 7 nodes
inline constexpr InternalNode tree_95[] = {
    {7, 0.2798077120931756f, 1, 4, {0.505625f, 0.494375f}},  // data_exfiltration_indicators <= 0.2798?
    {9, 0.3774141380983671f, 2, 3, {0.9982214317474433f, 0.0017785682525566918f}},  // access_pattern_entropy <= 0.3774?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {6, 0.20056092313426116f, 5, 6, {0.001012196973531049f, 0.998987803026469f}},  // service_discovery_patterns <= 0.2006?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 96: 3 nodes
inline constexpr InternalNode tree_96[] = {
    {9, 0.3668527313425479f, 1, 2, {0.4996f, 0.5004f}},  // access_pattern_entropy <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 97: 3 nodes
inline constexpr InternalNode tree_97[] = {
    {9, 0.3668527313425479f, 1, 2, {0.49715f, 0.50285f}},  // access_pattern_entropy <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 98: 11 nodes
inline constexpr InternalNode tree_98[] = {
    {6, 0.33233795222011947f, 1, 8, {0.4994f, 0.5006f}},  // service_discovery_patterns <= 0.3323?
    {1, 0.24924118129698375f, 2, 3, {0.9951826575672421f, 0.004817342432757929f}},  // service_port_consistency <= 0.2492?
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {5, 0.46848226992704267f, 4, 7, {0.9982382845925404f, 0.0017617154074596065f}},  // lateral_movement_score <= 0.4685?
    {4, 0.0f, 5, 6, {0.9998991630533427f, 0.00010083694665725522f}},  // connection_duration_std <= 0.0000?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.3333333333333333f, 0.6666666666666666f}},  // Leaf: P(suspicious)=0.6667
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
    {9, 0.36504642821732836f, 9, 10, {0.007174172977281785f, 0.9928258270227183f}},  // access_pattern_entropy <= 0.3650?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Tree 99: 3 nodes
inline constexpr InternalNode tree_99[] = {
    {9, 0.36688421909745816f, 1, 2, {0.49995f, 0.50005f}},  // access_pattern_entropy <= 0.3669?
    {-2, -2.0f, -1, -1, {1.0f, 0.0f}},  // Leaf: P(suspicious)=0.0000
    {-2, -2.0f, -1, -1, {0.0f, 1.0f}},  // Leaf: P(suspicious)=1.0000
};


// Array de punteros a todos los árboles
inline constexpr InternalNode* internal_trees[] = {
    tree_0,
    tree_1,
    tree_2,
    tree_3,
    tree_4,
    tree_5,
    tree_6,
    tree_7,
    tree_8,
    tree_9,
    tree_10,
    tree_11,
    tree_12,
    tree_13,
    tree_14,
    tree_15,
    tree_16,
    tree_17,
    tree_18,
    tree_19,
    tree_20,
    tree_21,
    tree_22,
    tree_23,
    tree_24,
    tree_25,
    tree_26,
    tree_27,
    tree_28,
    tree_29,
    tree_30,
    tree_31,
    tree_32,
    tree_33,
    tree_34,
    tree_35,
    tree_36,
    tree_37,
    tree_38,
    tree_39,
    tree_40,
    tree_41,
    tree_42,
    tree_43,
    tree_44,
    tree_45,
    tree_46,
    tree_47,
    tree_48,
    tree_49,
    tree_50,
    tree_51,
    tree_52,
    tree_53,
    tree_54,
    tree_55,
    tree_56,
    tree_57,
    tree_58,
    tree_59,
    tree_60,
    tree_61,
    tree_62,
    tree_63,
    tree_64,
    tree_65,
    tree_66,
    tree_67,
    tree_68,
    tree_69,
    tree_70,
    tree_71,
    tree_72,
    tree_73,
    tree_74,
    tree_75,
    tree_76,
    tree_77,
    tree_78,
    tree_79,
    tree_80,
    tree_81,
    tree_82,
    tree_83,
    tree_84,
    tree_85,
    tree_86,
    tree_87,
    tree_88,
    tree_89,
    tree_90,
    tree_91,
    tree_92,
    tree_93,
    tree_94,
    tree_95,
    tree_96,
    tree_97,
    tree_98,
    tree_99
};

inline constexpr size_t INTERNAL_NUM_TREES = 100;
inline constexpr size_t INTERNAL_NUM_FEATURES = 10;

/// @brief Predice si el tráfico es benigno o sospechoso
/// @param features Array de features normalizadas [0.0-1.0]:
///   [0] internal_connection_rate
///   [1] service_port_consistency
///   [2] protocol_regularity
///   [3] packet_size_consistency
///   [4] connection_duration_std
///   [5] lateral_movement_score
///   [6] service_discovery_patterns
///   [7] data_exfiltration_indicators
///   [8] temporal_anomaly_score
///   [9] access_pattern_entropy
/// @return Probability of SUSPICIOUS traffic (0.0 to 1.0)
inline float internal_traffic_predict(const std::array<float, INTERNAL_NUM_FEATURES>& features) {
    float benign_prob = 0.0f;
    float suspicious_prob = 0.0f;
    
    for (size_t tree_idx = 0; tree_idx < INTERNAL_NUM_TREES; ++tree_idx) {
        const InternalNode* tree = internal_trees[tree_idx];
        size_t node_idx = 0;
        
        while (true) {
            const auto& node = tree[node_idx];
            
            if (node.feature_idx == -2) { // Leaf node
                benign_prob += node.value[0];
                suspicious_prob += node.value[1];
                break;
            }
            
            if (features[node.feature_idx] <= node.threshold) {
                node_idx = node.left_child;
            } else {
                node_idx = node.right_child;
            }
        }
    }
    
    // Return probability of SUSPICIOUS traffic (class 1)
    return suspicious_prob / INTERNAL_NUM_TREES;
}

#endif // INTERNAL_TREES_INLINE_HPP
