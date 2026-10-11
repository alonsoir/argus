#!/usr/bin/env python3
"""DAY290 [DDOS-SNAP-D290] Foto determinista de los rasgos DDoS v2 en el hilo del anillo.
- FlowStatistics: suma e histograma incrementales de all_lengths (all_lengths no se toca).
- MLDefenderExtractor::ddos_v2_flow_snapshot: 5 rasgos de flujo con las MISMAS formulas que el lote
  (media exacta por suma; entropia con el mismo std::map y la misma acumulacion float).
- Hilo del anillo: tras add_packet, foto con with_flow_stats (sin copiar) + consulta de victima.
- Cola/lote llevan QueuedEvent {SimpleEvent, DdosFlowSnap, victima}; populate sobrescribe los 5
  rasgos antes de run_ml_detection y estampa la victima desde la foto. Foto invalida -> centinela.
- get_flow_stats_copy arrastra suma e histograma. Test test_ddos_flow_snap en CMake/ctest.
Requiere antes: sniffer/include/ddos_flow_snap.hpp y sniffer/tests/test_ddos_flow_snap.cpp.
Uso: python3 day290_patch_ddos_snap.py --check | --apply
Todo-o-nada: si algun anclaje no aparece exactamente una vez, no toca ningun fichero."""
import pathlib
import sys

ROOT = pathlib.Path("/vagrant")
MARK = "[DDOS-SNAP-D290]"
NEW_FILES = ["sniffer/include/ddos_flow_snap.hpp", "sniffer/tests/test_ddos_flow_snap.cpp"]
EDITS = []


def edit(path, old, new):
    EDITS.append((path, old, new))


# ---------------------------------------------------------------- ml_defender_features.hpp
P = "sniffer/include/ml_defender_features.hpp"
edit(P, '#include "time_window_aggregator.hpp"\n',
     '#include "time_window_aggregator.hpp"\n'
     '#include "ddos_flow_snap.hpp"  // [DDOS-SNAP-D290]\n'
     '#include <map>\n')
edit(P, "        ::protobuf::NetworkSecurityEvent& proto_event) const;\n\nprivate:\n",
     "        ::protobuf::NetworkSecurityEvent& proto_event) const;\n\n"
     "    // [DDOS-SNAP-D290] Foto O(k) de los 5 rasgos DDoS v2 de flujo (syn_ack_ratio,\n"
     "    // flow_completion_rate, flow_packet_count, mean_packet_size, packet_size_entropy) con las\n"
     "    // mismas formulas que extract_ddos_features, sobre los estadisticos incrementales del flujo.\n"
     "    DdosFlowSnap ddos_v2_flow_snapshot(const FlowStatistics& flow) const;\n\n"
     "private:\n")
edit(P, "    float calculate_entropy(const std::vector<uint32_t>& data) const;\n",
     "    float calculate_entropy(const std::vector<uint32_t>& data) const;\n"
     "    float calculate_entropy_from_hist(const std::map<uint32_t, uint32_t>& hist,\n"
     "                                      uint64_t total_count) const;  // [DDOS-SNAP-D290]\n")

# ---------------------------------------------------------------- flow_manager.hpp
P = "sniffer/include/flow_manager.hpp"
edit(P, "#include <vector>\n", "#include <vector>\n#include <map>  // [DDOS-SNAP-D290]\n")
edit(P, "    std::vector<uint32_t> all_lengths;  // For packet_len_mean/std/var\n",
     "    std::vector<uint32_t> all_lengths;  // For packet_len_mean/std/var\n"
     "    // [DDOS-SNAP-D290] Estadisticos incrementales de all_lengths para la foto DDoS v2:\n"
     "    // suma exacta (media identica a calculate_mean) e histograma ordenado (entropia identica a\n"
     "    // calculate_entropy, que tambien recorre un std::map por valor ascendente).\n"
     "    uint64_t sum_all_lengths = 0;\n"
     "    std::map<uint32_t, uint32_t> len_hist;\n")
edit(P, "        all_lengths.push_back(pkt.packet_len);\n",
     "        all_lengths.push_back(pkt.packet_len);\n"
     "        sum_all_lengths += pkt.packet_len;                    // [DDOS-SNAP-D290]\n"
     "        ++len_hist[static_cast<uint32_t>(pkt.packet_len)];\n")

# ---------------------------------------------------------------- sharded_flow_manager.cpp
P = "sniffer/src/flow/sharded_flow_manager.cpp"
edit(P, "        copy.fwd_header_lengths = it->second.stats.fwd_header_lengths;\n",
     "        copy.fwd_header_lengths = it->second.stats.fwd_header_lengths;\n"
     "        copy.sum_all_lengths = it->second.stats.sum_all_lengths;  // [DDOS-SNAP-D290]\n"
     "        copy.len_hist = it->second.stats.len_hist;\n")

# ---------------------------------------------------------------- ml_defender_features.cpp
P = "sniffer/src/userspace/ml_defender_features.cpp"
edit(P, "float MLDefenderExtractor::calculate_std_dev(const std::vector<uint32_t>& data) const {\n",
     "// [DDOS-SNAP-D290] Igual que calculate_entropy pero sobre el histograma incremental del flujo:\n"
     "// mismo std::map (orden ascendente), mismo total y la misma acumulacion en float -> mismo\n"
     "// resultado bit a bit si hist son las frecuencias de all_lengths y total == all_lengths.size().\n"
     "float MLDefenderExtractor::calculate_entropy_from_hist(const std::map<uint32_t, uint32_t>& hist,\n"
     "                                                       uint64_t total_count) const {\n"
     "    if (total_count == 0) return 0.0f;\n"
     "\n"
     "    float entropy = 0.0f;\n"
     "    float total = static_cast<float>(total_count);\n"
     "\n"
     "    for (const auto& [value, count] : hist) {\n"
     "        (void)value;\n"
     "        float probability = static_cast<float>(count) / total;\n"
     "        if (probability > 0.0f) {\n"
     "            entropy -= probability * std::log2(probability);\n"
     "        }\n"
     "    }\n"
     "\n"
     "    return entropy;\n"
     "}\n"
     "\n"
     "// [DDOS-SNAP-D290] Foto de los rasgos DDoS v2 de flujo. Se llama en el hilo del anillo DENTRO del\n"
     "// lock del shard (with_flow_stats): sin recorrer vectores; O(k), k = longitudes distintas.\n"
     "DdosFlowSnap MLDefenderExtractor::ddos_v2_flow_snapshot(const FlowStatistics& flow) const {\n"
     "    DdosFlowSnap s;\n"
     "    const uint64_t n = flow.get_total_packets();\n"
     "    s.valid = true;\n"
     "    s.syn_ack_ratio = extract_ddos_syn_ack_ratio(flow);\n"
     "    s.flow_completion_rate = extract_ddos_flow_completion_rate(flow);\n"
     "    s.flow_packet_count = static_cast<float>(n);\n"
     "    s.mean_packet_size = (n == 0) ? 0.0f\n"
     "        : static_cast<float>(flow.sum_all_lengths) / static_cast<float>(n);\n"
     "    s.packet_size_entropy = calculate_entropy_from_hist(flow.len_hist, n);\n"
     "    return s;\n"
     "}\n"
     "\n"
     "float MLDefenderExtractor::calculate_std_dev(const std::vector<uint32_t>& data) const {\n")

# ---------------------------------------------------------------- ring_consumer.hpp
P = "sniffer/include/ring_consumer.hpp"
edit(P, "struct EventBatch {\n    std::vector<SimpleEvent> events;\n",
     "// [DDOS-SNAP-D290] Lo que viaja del hilo del anillo al hilo de rasgos: el paquete y la foto de\n"
     "// sus rasgos DDoS v2 (flujo + ventana por victima) tomada en el instante del paquete.\n"
     "struct QueuedEvent {\n"
     "    SimpleEvent event{};\n"
     "    DdosFlowSnap flow{};\n"
     "    bool have_victim = false;  // false: tablero de victimas apagado\n"
     "    ::sniffer::DdosVictimLookup victim{};\n"
     "};\n"
     "\n"
     "struct EventBatch {\n"
     "    std::vector<QueuedEvent> events;  // [DDOS-SNAP-D290]\n")
edit(P, "    void process_event_features(const SimpleEvent& event);\n",
     "    void process_event_features(const QueuedEvent& queued);  // [DDOS-SNAP-D290]\n")
edit(P, "    void add_to_batch(const SimpleEvent& event);\n",
     "    void add_to_batch(const QueuedEvent& event);  // [DDOS-SNAP-D290]\n")
edit(P, "    void send_event_batch(const std::vector<SimpleEvent>& events);\n",
     "    void send_event_batch(const std::vector<QueuedEvent>& events);  // [DDOS-SNAP-D290]\n")
edit(P, "int buffer_index) const;\n",
     "int buffer_index,\n"
     "                                const QueuedEvent* queued = nullptr) const;  // [DDOS-SNAP-D290]\n")
edit(P, "    std::queue<SimpleEvent> processing_queue_;\n",
     "    std::queue<QueuedEvent> processing_queue_;  // [DDOS-SNAP-D290]\n"
     "    mutable std::atomic<uint64_t> ddos_snap_invalid_{0};  // [DDOS-SNAP-D290] fotos sin flujo\n")
edit(P, "    void stamp_victim_window(protobuf::NetworkSecurityEvent& ev, const SimpleEvent& e) const;\n",
     "    void stamp_victim_window(protobuf::NetworkSecurityEvent& ev, const SimpleEvent& e) const;\n"
     "    void stamp_victim_window_from(protobuf::NetworkSecurityEvent& ev, const SimpleEvent& e,\n"
     "                                  const ::sniffer::DdosVictimLookup& r) const;  // [DDOS-SNAP-D290]\n")

# ---------------------------------------------------------------- ring_consumer.cpp
P = "sniffer/src/userspace/ring_consumer.cpp"
edit(P, "    flow_manager.add_packet(flow_key, event);\n",
     "    flow_manager.add_packet(flow_key, event);\n"
     "\n"
     "    // [DDOS-SNAP-D290] Foto de los rasgos DDoS v2 en el instante del paquete, en este hilo:\n"
     "    // flujo (dentro del lock del shard, sin copiar) y ventana por victima del kernel.\n"
     "    DdosFlowSnap ddos_snap{};\n"
     "    flow_manager.with_flow_stats(flow_key, [&](const auto& fs) {\n"
     "        ddos_snap = ml_extractor_.ddos_v2_flow_snapshot(fs);\n"
     "    });\n"
     "    bool snap_have_victim = false;\n"
     "    ::sniffer::DdosVictimLookup snap_victim{};\n"
     "    if (victim_board_) {\n"
     "        snap_victim = victim_board_->lookup(static_cast<uint32_t>(event.dst_ip),\n"
     "                                            static_cast<uint32_t>(event.protocol));\n"
     "        snap_have_victim = true;\n"
     "    }\n")
edit(P, "    add_to_batch(event);\n",
     "    add_to_batch(QueuedEvent{event, ddos_snap, snap_have_victim, snap_victim});  // [DDOS-SNAP-D290]\n")
edit(P, "        SimpleEvent event;\n",
     "        QueuedEvent event;  // [DDOS-SNAP-D290]\n")
edit(P, "void RingBufferConsumer::process_event_features(const SimpleEvent& event) {\n",
     "void RingBufferConsumer::process_event_features(const QueuedEvent& queued) {  // [DDOS-SNAP-D290]\n"
     "    const SimpleEvent& event = queued.event;\n")
edit(P, "        populate_protobuf_event(event, proto_event, 0);\n",
     "        populate_protobuf_event(event, proto_event, 0, &queued);  // [DDOS-SNAP-D290]\n")
edit(P, "void RingBufferConsumer::send_event_batch(const std::vector<SimpleEvent>& events) {\n",
     "void RingBufferConsumer::send_event_batch(const std::vector<QueuedEvent>& events) {  // [DDOS-SNAP-D290]\n")
edit(P, "void RingBufferConsumer::add_to_batch(const SimpleEvent& event) {\n",
     "void RingBufferConsumer::add_to_batch(const QueuedEvent& event) {  // [DDOS-SNAP-D290]\n")
edit(P, "int buffer_index) const {\n",
     "int buffer_index,\n"
     "                                                 const QueuedEvent* queued) const {  // [DDOS-SNAP-D290]\n")
edit(P, "    const_cast<RingBufferConsumer*>(this)->run_ml_detection(proto_event);\n",
     "    // [DDOS-SNAP-D290] Rasgos DDoS v2 de flujo desde la foto del hilo del anillo (instante del\n"
     "    // paquete), nunca desde la copia tomada con retraso en este hilo. Foto invalida -> centinela.\n"
     "    if (queued) {\n"
     "        auto* dd = proto_event.mutable_network_features()->mutable_ddos_embedded();\n"
     "        if (queued->flow.valid) {\n"
     "            dd->set_syn_ack_ratio(queued->flow.syn_ack_ratio);\n"
     "            dd->set_flow_completion_rate(queued->flow.flow_completion_rate);\n"
     "            dd->set_flow_packet_count(queued->flow.flow_packet_count);\n"
     "            dd->set_mean_packet_size(queued->flow.mean_packet_size);\n"
     "            dd->set_packet_size_entropy(queued->flow.packet_size_entropy);\n"
     "        } else {\n"
     "            dd->set_syn_ack_ratio(MISSING_FEATURE_SENTINEL);\n"
     "            dd->set_flow_completion_rate(MISSING_FEATURE_SENTINEL);\n"
     "            dd->set_flow_packet_count(MISSING_FEATURE_SENTINEL);\n"
     "            dd->set_mean_packet_size(MISSING_FEATURE_SENTINEL);\n"
     "            dd->set_packet_size_entropy(MISSING_FEATURE_SENTINEL);\n"
     "            if (ddos_snap_invalid_.fetch_add(1, std::memory_order_relaxed) == 0) {\n"
     "                std::cerr << \"[DDOS-SNAP] WARNING: foto DDoS sin flujo en la tabla; se escriben \"\n"
     "                             \"centinelas (aviso unico, se siguen contando)\" << std::endl;\n"
     "            }\n"
     "        }\n"
     "    }\n"
     "    const_cast<RingBufferConsumer*>(this)->run_ml_detection(proto_event);\n")
edit(P, "    stamp_victim_window(proto_event, event);\n",
     "    if (queued) {  // [DDOS-SNAP-D290] la consulta se hizo en el hilo del anillo (foto)\n"
     "        if (queued->have_victim) stamp_victim_window_from(proto_event, event, queued->victim);\n"
     "    } else {\n"
     "        stamp_victim_window(proto_event, event);\n"
     "    }\n")
edit(P, "    if (!victim_board_) return;\n"
        "    const uint32_t dst = static_cast<uint32_t>(e.dst_ip);\n"
        "    const uint32_t proto = static_cast<uint32_t>(e.protocol);\n"
        "    const ::sniffer::DdosVictimLookup r = victim_board_->lookup(dst, proto);\n"
        "    if (!r.have_snapshot) return;\n",
     "    if (!victim_board_) return;\n"
     "    stamp_victim_window_from(ev, e, victim_board_->lookup(static_cast<uint32_t>(e.dst_ip),\n"
     "                                                          static_cast<uint32_t>(e.protocol)));\n"
     "}\n"
     "\n"
     "// [DDOS-SNAP-D290] Estampa una consulta ya hecha: el camino normal la toma en el hilo del anillo,\n"
     "// en el instante del paquete (foto), y la trae en el QueuedEvent.\n"
     "void RingBufferConsumer::stamp_victim_window_from(protobuf::NetworkSecurityEvent& ev,\n"
     "                                                  const SimpleEvent& e,\n"
     "                                                  const ::sniffer::DdosVictimLookup& r) const {\n"
     "    const uint32_t dst = static_cast<uint32_t>(e.dst_ip);\n"
     "    const uint32_t proto = static_cast<uint32_t>(e.protocol);\n"
     "    if (!r.have_snapshot) return;\n")

# ---------------------------------------------------------------- CMakeLists.txt (test)
P = "sniffer/CMakeLists.txt"
edit(P, 'message(STATUS "\U0001F9EA Unit Test: test_ring_consumer_protobuf configured (Day 46 - 40 features)")\n',
     'message(STATUS "\U0001F9EA Unit Test: test_ring_consumer_protobuf configured (Day 46 - 40 features)")\n'
     "\n"
     "# [DDOS-SNAP-D290] Foto DDoS v2 incremental == extraccion de lote de produccion, bit a bit\n"
     "add_executable(test_ddos_flow_snap\n"
     "        tests/test_ddos_flow_snap.cpp\n"
     "        src/flow/sharded_flow_manager.cpp\n"
     "        src/userspace/flow_manager.cpp\n"
     "        src/userspace/time_window_manager.cpp\n"
     "        src/userspace/time_window_aggregator.cpp\n"
     "        src/userspace/ml_defender_features.cpp\n"
     "        src/userspace/flow_tracker.cpp\n"
     "        src/userspace/dns_analyzer.cpp\n"
     "        src/userspace/ip_whitelist.cpp\n"
     "        ${PROTO_SOURCES}\n"
     ")\n"
     "target_include_directories(test_ddos_flow_snap PRIVATE\n"
     "        ${CMAKE_SOURCE_DIR}/include\n"
     "        ${CMAKE_SOURCE_DIR}/include/flow\n"
     "        ${CMAKE_SOURCE_DIR}/src\n"
     "        ${CMAKE_BINARY_DIR}/proto\n"
     "        ${ML_DEFENDER_DIR}/include\n"
     ")\n"
     "target_link_libraries(test_ddos_flow_snap\n"
     "        Threads::Threads\n"
     "        ${Protobuf_LIBRARIES}\n"
     ")\n"
     "add_test(NAME test_ddos_flow_snap COMMAND test_ddos_flow_snap)\n"
     'message(STATUS "\U0001F9EA Unit Test: test_ddos_flow_snap configured (DAY 290 - foto DDoS v2 incremental) [DDOS-SNAP-D290]")\n')


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print(__doc__)
        return 2
    for nf in NEW_FILES:
        p = ROOT / nf
        if not p.is_file() or MARK not in p.read_text(encoding="utf-8"):
            print(f"ABORTO: falta {nf} (o no lleva la marca); crealo antes")
            return 1
    files = sorted({p for p, _, _ in EDITS})
    for f in files:
        if not (ROOT / f).is_file():
            print(f"ABORTO: no existe {f}")
            return 1
    texts = {f: (ROOT / f).read_text(encoding="utf-8") for f in files}
    marked = [f for f in files if MARK in texts[f]]
    if len(marked) == len(files):
        print("YA APLICADO: la marca esta en todos los ficheros; no se toca nada")
        return 0
    if marked:
        print("ABORTO: estado inconsistente, la marca solo esta en: " + ", ".join(marked))
        return 1
    errores = []
    for i, (f, old, _) in enumerate(EDITS, 1):
        n = texts[f].count(old)
        if n != 1:
            primera = old.strip().splitlines()[0][:90]
            errores.append(f"  edicion {i:2d} {f}: aparece {n} veces -> {primera!r}")
    if errores:
        print("ABORTO: anclajes que no aparecen exactamente una vez (no se toca nada):")
        print("\n".join(errores))
        return 1
    if sys.argv[1] == "--check":
        print(f"OK: aplicable ({len(EDITS)} ediciones en {len(files)} ficheros, todas con 1 coincidencia)")
        return 0
    out = dict(texts)
    for i, (f, old, new) in enumerate(EDITS, 1):
        if out[f].count(old) != 1:
            print(f"ABORTO: la edicion {i} dejo de casar tras las anteriores ({f}); no se escribe nada")
            return 1
        out[f] = out[f].replace(old, new, 1)
    for f in files:
        (ROOT / f).write_text(out[f], encoding="utf-8")
    sin_marca = [f for f in files if MARK not in (ROOT / f).read_text(encoding="utf-8")]
    if sin_marca:
        print("ERROR: tras escribir, sin marca: " + ", ".join(sin_marca))
        return 1
    print(f"APLICADO: {len(EDITS)} ediciones en {len(files)} ficheros")
    return 0


if __name__ == "__main__":
    sys.exit(main())
